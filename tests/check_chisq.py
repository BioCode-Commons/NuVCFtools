#!/usr/bin/env python3
"""Compare actual old/new genotype chi-square functions by their raw double bytes.

The extracted definitions retain their real genotype representation, indexing,
loop bodies and gamma implementation. This is a function probe, not a substitute
for complete CLI checks. Default builds exercise both -O0 and -O2 in C++98.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


DRIVER = r'''
#include <algorithm>
#include <cerrno>
#include <cmath>
#include <cstring>
#include <cstdlib>
#include <fenv.h>
#include <iostream>
#include <limits>
#include <map>
#include <stdint.h>
#include <utility>
#include <vector>
#include "gamma.h"
using namespace std;
struct result { double chisq,dof,pval; int count,flags,error; };
'''

MAIN = r'''
static unsigned long cases=0;
static uint32_t state=771991U;
static uint32_t next_value() { state=state*1664525U+1013904223U; return state; }
static void check(const vector<pair<int,int> > &left,const vector<pair<int,int> > &right,int n0,int n1)
{
    result a=baseline::run(left,right,n0,n1), b=candidate::run(left,right,n0,n1);
    if(memcmp(&a.chisq,&b.chisq,sizeof(double)) || memcmp(&a.dof,&b.dof,sizeof(double)) ||
       memcmp(&a.pval,&b.pval,sizeof(double)) || a.count!=b.count || a.flags!=b.flags || a.error!=b.error)
    {
        cerr<<"Mismatch case="<<cases<<" alleles="<<n0<<','<<n1<<" samples="<<left.size()<<'\n';
        cerr<<a.chisq<<' '<<b.chisq<<' '<<a.dof<<' '<<b.dof<<' '<<a.pval<<' '<<b.pval<<'\n';
        cerr<<a.flags<<' '<<b.flags<<' '<<a.error<<' '<<b.error<<'\n'; exit(1);
    }
    cases++;
}
int main()
{
    if(fesetround(FE_TONEAREST)) return 2;
    vector<pair<int,int> > left,right;
    const pair<int,int> calls[]={make_pair(0,0),make_pair(0,1),make_pair(1,1),make_pair(-1,-1),make_pair(2,0)};
    unsigned int patterns=1;
    for(int n=0;n<=3;n++)
    {
        left.resize(n);right.resize(n);
        for(unsigned int pattern=0;pattern<patterns;pattern++)
        {
            unsigned int code=pattern;
            for(int i=0;i<n;i++) { left[i]=calls[code%5];code/=5;right[i]=calls[code%5];code/=5; }
            check(left,right,2,2);
        }
        patterns*=25;
    }
    const unsigned long sequence_cases=cases;
    // Enumerate every 3x3 biallelic contingency table with cell count 0, 1 or 2.
    for(unsigned int table=0;table<19683;table++)
    {
        unsigned int code=table;left.clear();right.clear();
        for(int i=0;i<3;i++) for(int j=0;j<3;j++)
        {
            unsigned int count=code%3;code/=3;
            for(unsigned int k=0;k<count;k++) { left.push_back(calls[i]);right.push_back(calls[j]); }
        }
        check(left,right,2,2);
    }
    const unsigned long table_cases=cases-sequence_cases;
    // Sparse/zero margins, missing halves, reversed genotypes and legacy invalid IDs.
    const int dimensions[]={1,2,3,4,6,8,12};
    for(int a=0;a<7;a++) for(int b=0;b<7;b++) for(int trial=0;trial<32;trial++)
    {
        const int n0=dimensions[a],n1=dimensions[b];
        const unsigned int n=next_value()%97;left.resize(n);right.resize(n);
        for(unsigned int i=0;i<n;i++)
        {
            left[i]=make_pair(int(next_value()%(n0+3))-1,int(next_value()%(n0+3))-1);
            right[i]=make_pair(int(next_value()%(n1+3))-1,int(next_value()%(n1+3))-1);
            if(i%7==0) left[i].first=-2;
            if(i%11==0) right[i].second=32767;
        }
        check(left,right,n0,n1);
    }
    const unsigned long randomized_cases=cases-sequence_cases-table_cases;
    const int large[][2]={{32,32},{64,64},{2,96},{96,2},{1,64},{64,1}};
    for(unsigned int a=0;a<sizeof(large)/sizeof(large[0]);a++)
    {
        const int n0=large[a][0],n1=large[a][1];
        for(int mode=0;mode<4;mode++)
        {
            const int n=mode==0 ? 0 : mode==1 ? 1 : 257;
            left.resize(n);right.resize(n);
            for(int i=0;i<n;i++)
            {
                left[i]=make_pair((i*7)%n0,(i*3+mode)%n0);
                right[i]=make_pair((i*11)%n1,(i*5+mode)%n1);
                if(mode==3 && i%3) left[i]=make_pair(-1,0);
            }
            check(left,right,n0,n1);
        }
    }
    cout<<"{\"cases\":"<<cases<<",\"sequence_cases\":"<<sequence_cases
        <<",\"contingency_tables\":"<<table_cases<<",\"randomized_cases\":"<<randomized_cases
        <<",\"large_cases\":"<<cases-sequence_cases-table_cases-randomized_cases<<"}\n";
}
'''


def definition(text, marker):
    start = text.index(marker)
    opening = text.index('{', start)
    level = 1
    end = opening + 1
    while level:
        level += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def source_body(source, namespace):
    text = (source / 'src/cpp/variant_file_output.cpp').read_text()
    function = definition(text, 'void variant_file::calc_geno_chisq(')
    function = function.replace('variant_file::calc_geno_chisq', 'calc_geno_chisq', 1)
    helper = (definition(text, 'static int genotype_pair_index(')
              if 'static int genotype_pair_index(' in text else '')
    genotype = 'ld_genotype' if 'vector<ld_genotype>' in function else 'pair<int,int>'
    return '\nnamespace ' + namespace + ' {\ntypedef pair<short,short> ld_genotype;\n' + helper + '\n' + function + r'''
result run(const vector<pair<int,int> > &left,const vector<pair<int,int> > &right,int n0,int n1)
{
    vector<GENOTYPE > a(left.begin(),left.end()),b(right.begin(),right.end());
    result r;
    r.chisq=r.dof=r.pval=-999.;r.count=-999;
    feclearexcept(FE_ALL_EXCEPT);errno=0;
    calc_geno_chisq(a,b,n0,n1,r.chisq,r.dof,r.pval,r.count);
    r.error=errno;r.flags=fetestexcept(FE_ALL_EXCEPT);
    return r;
}
}
'''.replace('GENOTYPE', genotype)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--cxx', default='clang++')
    args = parser.parse_args()
    baseline, candidate, directory = args.baseline.resolve(), args.candidate.resolve(), args.out_dir.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    gamma = candidate / 'src/cpp/gamma.cpp'
    for name in ('gamma.cpp', 'gamma.h'):
        assert (baseline / 'src/cpp' / name).read_bytes() == (candidate / 'src/cpp' / name).read_bytes()
    driver = directory / 'chisq_probe.cpp'
    driver.write_text(DRIVER + source_body(baseline, 'baseline') + source_body(candidate, 'candidate') + MAIN)
    builds = []
    for optimization in ('-O0', '-O2'):
        executable = directory / ('probe-' + optimization[1:])
        command = [args.cxx, '-std=c++98', optimization, '-I', str(gamma.parent), str(driver), str(gamma), '-o', str(executable)]
        compiled = subprocess.run(command, capture_output=True)
        (directory / (optimization[1:] + '-build.log')).write_bytes(compiled.stdout + compiled.stderr)
        compiled.check_returncode()
        result = subprocess.run([str(executable)], capture_output=True)
        (directory / (optimization[1:] + '-stdout')).write_bytes(result.stdout)
        (directory / (optimization[1:] + '-stderr')).write_bytes(result.stderr)
        result.check_returncode()
        builds.append({'optimization': optimization, 'compile_command': command, 'executable_sha256': digest(executable),
                       'result': json.loads(result.stdout), 'stderr_sha256': hashlib.sha256(result.stderr).hexdigest()})
    assert builds[0]['result'] == builds[1]['result']
    summary = {'passed': True, 'cases_per_build': builds[0]['result']['cases'], 'builds': builds,
               'baseline_source_sha256': digest(baseline / 'src/cpp/variant_file_output.cpp'),
               'candidate_source_sha256': digest(candidate / 'src/cpp/variant_file_output.cpp'),
               'baseline_function_sha256': hashlib.sha256(source_body(baseline, 'baseline').encode()).hexdigest(),
               'candidate_function_sha256': hashlib.sha256(source_body(candidate, 'candidate').encode()).hexdigest(),
               'gamma_sha256': digest(gamma), 'driver_sha256': digest(driver),
               'comparison': 'memcmp of chisq, dof and pval doubles; integer sample counts, final floating exception flags and errno also equal.',
               'rounding_mode': 'FE_TONEAREST, nontrapping',
               'limits': ['Extracted real functions, not complete CLI output.',
                          'Existing signed dimension/count overflow and mismatched input-vector lengths excluded.',
                          'Valid positive dimensions; empty observations and invalid allele IDs retaining legacy index-zero behavior included.',
                          'No claim for signaling/trapping floating environments, excess-precision architectures not run here or different math libraries.']}
    (directory / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({'passed': True, 'cases_per_build': summary['cases_per_build'], 'builds': len(builds)}))


if __name__ == '__main__':
    main()
