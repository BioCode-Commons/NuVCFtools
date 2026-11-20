#!/usr/bin/env python3
"""Compare actual previous/current LROH kernels without floating tolerances.

Extract both kernel blocks from output_LROH. Uninstrumented copies compare raw
posteriors; separately instrumented copies also capture every alpha/beta row.
The latter must produce the same posteriors and final fenv/errno as the former.
This is not a full CLI test or a claim about trapping/nonterminating inputs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


DRIVER = r'''
#include <vector>
#include <utility>
#include <iostream>
#include <cmath>
#include <cstring>
#include <stdint.h>
#include <limits>
#include <fenv.h>
#include <errno.h>
#include <cstdlib>
using namespace std;
@ROW@
struct result {
    vector<lroh_double_row<2> > forward,backward;
    vector<double> posterior;
    int flags,error;
    result() : flags(0),error(0) {}
};
typedef vector<pair<double,double> > emissions;
typedef vector<lroh_double_row<4> > transitions;
static uint32_t state=19821103U;
static uint32_t random_value() { state=1664525U*state+1013904223U; return state; }
static unsigned long cases=0, sites=0;
static double bits(uint64_t value) { double d; memcpy(&d,&value,sizeof(d)); return d; }
static bool same(const vector<double> &a,const vector<double> &b) {
    return a.size()==b.size() && (a.empty() || memcmp(&a[0],&b[0],a.size()*sizeof(double))==0);
}
static bool same_rows(const vector<lroh_double_row<2> > &a,const vector<lroh_double_row<2> > &b) {
    if(a.size()!=b.size()) return false;
    for(size_t i=0;i<a.size();i++)
        if(memcmp(a[i].values,b[i].values,2*sizeof(double))!=0) return false;
    return true;
}
@FUNCTIONS@
static void check(const emissions &e,const transitions &t) {
    result a=baseline_plain(e,t),b=candidate_plain(e,t);
    result ac=baseline_captured(e,t),bc=candidate_captured(e,t);
    if(!same(a.posterior,b.posterior) || !same(a.posterior,ac.posterior) || !same(b.posterior,bc.posterior)
       || !same_rows(ac.forward,bc.forward) || !same_rows(ac.backward,bc.backward)
       || a.flags!=b.flags || a.error!=b.error || a.flags!=ac.flags || a.error!=ac.error
       || b.flags!=bc.flags || b.error!=bc.error) {
        cerr<<"LROH mismatch at case "<<cases<<" with "<<e.size()<<" observations\n";
        exit(1);
    }
    cases++; sites+=e.size();
}
static lroh_double_row<4> transition(int mode,unsigned int i) {
    lroh_double_row<4> t;
    if(mode==0) { t[0]=t[3]=1.; }
    else if(mode==1) { t[0]=.9;t[1]=.05;t[2]=.1;t[3]=.95; }
    else {
        const double r=(i%11+1)/10000.;
        const double probability=1.-exp(-8.*r);
        t[0]=1.-.05*probability;t[1]=.95*probability;
        t[2]=.05*probability;t[3]=1.-.95*probability;
    }
    return t;
}
int main() {
    if(fesetround(FE_TONEAREST)!=0) return 2;
    const pair<double,double> choices[]={make_pair(.01,.5),make_pair(.99,.5),
        make_pair(.01,1.),make_pair(.99,1.),make_pair(1e-30,1e-31),make_pair(.01,.99)};
    for(unsigned int n=0;n<=5;n++) {
        unsigned int count=1;for(unsigned int i=0;i<n;i++) count*=6;
        for(unsigned int code=0;code<count;code++) for(int mode=0;mode<3;mode++) {
            emissions e(n);transitions t(n);unsigned int digits=code;
            for(unsigned int i=0;i<n;i++) { e[i]=choices[digits%6];digits/=6;t[i]=transition(mode,i); }
            check(e,t);
        }
    }
    const unsigned long exhaustive=cases;
    for(unsigned int k=0;k<2500;k++) {
        unsigned int n=random_value()%257;emissions e(n);transitions t(n);
        for(unsigned int i=0;i<n;i++) {
            const double h=(random_value()%1001)/1000.;
            const bool het=(random_value()%3)==0;
            e[i]=make_pair(het?.01:.99,het?h:1.-h);
            t[i]=transition(2,i+random_value()%200);
        }
        check(e,t);
    }
    const unsigned long randomized=cases-exhaustive;
    // Long positive chains repeatedly enter the original renormalization loops.
    for(unsigned int n=1023;n<=16384;n=n*2+1) for(int mode=0;mode<3;mode++) {
        emissions e(n);transitions t(n);
        for(unsigned int i=0;i<n;i++) { e[i]=choices[(i/29+i%3)%6];t[i]=transition(mode,i); }
        check(e,t);
    }
    const unsigned long long_cases=cases-exhaustive-randomized;
    // Quiet NaNs, infinities, zeros and denormals are tested without feeding
    // both-zero rows into multi-site kernels, whose baseline scale loop stalls.
    const double special[]={0.,-0.,numeric_limits<double>::denorm_min(),1e-300,
        1e-20,1e-19,1.,numeric_limits<double>::infinity(),
        bits(0x7ff8000000000042ULL),bits(0xfff8000000000099ULL)};
    for(unsigned int i=0;i<10;i++) for(unsigned int j=0;j<10;j++) {
        emissions e(1,make_pair(special[i],special[j]));transitions t(1);
        check(e,t);
    }
    for(unsigned int i=0;i<10;i++) for(unsigned int n=2;n<=17;n+=5) {
        emissions e(n,make_pair(.99,.5));transitions t(n);
        for(unsigned int j=0;j<n;j++) t[j]=transition(2,j);
        e[n/2]=make_pair(special[i],.75);check(e,t);
        e[n/2]=make_pair(.75,special[i]);check(e,t);
    }
    cout<<"{\"cases\":"<<cases<<",\"observations\":"<<sites
        <<",\"exhaustive_sequences\":"<<exhaustive<<",\"randomized_cases\":"<<randomized
        <<",\"long_cases\":"<<long_cases<<",\"special_cases\":"<<cases-exhaustive-randomized-long_cases<<"}\n";
}
'''


def kernel(source):
    text = (source / 'src/cpp/variant_file_output.cpp').read_text()
    function = text[text.index('void variant_file::output_LROH('):]
    start = function.index('\t\tvector<lroh_double_row<2> > alpha(N_obs);')
    return function[start:function.index('\n\t\t// Generate output', start)]


def wrapper(code, name, captured):
    candidate = 'current_beta' in code
    if captured:
        if candidate:
            code = code.replace('\t\t// Only adjacent backward rows are live.',
                                '\t\tr.forward = alpha;\n\t\t// Only adjacent backward rows are live.', 1)
            code = code.replace('\t\tlast_beta[1] = 1.0;',
                                '\t\tlast_beta[1] = 1.0;\n\t\tr.backward[N_obs-1] = last_beta;', 1)
            code = code.replace('\t\t\talpha[i][0] = alpha[i][0] * current_beta[0]',
                                '\t\t\tr.backward[i] = current_beta;\n\t\t\talpha[i][0] = alpha[i][0] * current_beta[0]', 1)
        else:
            code = code.replace('\t\tbeta[N_obs-1][0] = 1.0;',
                                '\t\tr.forward = alpha;\n\t\tbeta[N_obs-1][0] = 1.0;', 1)
            code = code.replace('\t\t// Calculate probability of each site being autozygous',
                                '\t\tr.backward = beta;\n\t\t// Calculate probability of each site being autozygous', 1)
    return ('static result ' + name + '(const emissions &emission,const transitions &transition) {\n'
            'result r;const int N_obs=emission.size();if(!N_obs) return r;const unsigned int ui=0;\n'
            'vector<emissions> p_emission(1,emission);vector<transitions> p_trans(1,transition);\n'
            + ('r.backward.resize(N_obs);\n' if captured else '')
            + 'feclearexcept(FE_ALL_EXCEPT);errno=0;\n' + code
            + '\nr.flags=fetestexcept(FE_ALL_EXCEPT);r.error=errno;\n'
            + ('r.posterior.resize(N_obs);for(int i=0;i<N_obs;i++) r.posterior[i]=alpha[i][0];\n'
               if candidate else 'r.posterior=p_auto;\n') + 'return r;\n}\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--cxx', default='clang++')
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    old, new = kernel(args.baseline.resolve()), kernel(args.candidate.resolve())
    text = (args.candidate / 'src/cpp/variant_file_output.cpp').read_text()
    start = text.index('template<unsigned int Width>\nstruct lroh_double_row')
    row = text[start:text.index('\n};', start) + 3]
    functions = ''.join(wrapper(code, label + suffix, capture) for label, code in [('baseline', old), ('candidate', new)]
                        for suffix, capture in [('_plain', False), ('_captured', True)])
    driver = args.out_dir.resolve() / 'lroh_beta_probe.cpp'
    driver.write_text(DRIVER.replace('@ROW@', row).replace('@FUNCTIONS@', functions))
    builds = []
    for optimization in ['-O0', '-O2']:
        executable = args.out_dir.resolve() / ('probe-' + optimization[1:])
        command = [args.cxx, '-std=c++98', optimization, str(driver), '-o', str(executable)]
        build = subprocess.run(command, capture_output=True)
        (args.out_dir / (optimization[1:] + '.build.log')).write_bytes(build.stdout + build.stderr)
        build.check_returncode()
        run = subprocess.run([str(executable)], capture_output=True, timeout=60)
        (args.out_dir / (optimization[1:] + '.stdout')).write_bytes(run.stdout)
        (args.out_dir / (optimization[1:] + '.stderr')).write_bytes(run.stderr)
        run.check_returncode()
        builds.append({'optimization': optimization, 'compile_command': command, 'result': json.loads(run.stdout),
                       'executable_sha256': digest(executable), 'stderr_sha256': hashlib.sha256(run.stderr).hexdigest()})
    assert builds[0]['result'] == builds[1]['result']
    summary = {'passed': True, 'cases_per_build': builds[0]['result']['cases'], 'builds': builds,
               'baseline_source_sha256': digest(args.baseline / 'src/cpp/variant_file_output.cpp'),
               'candidate_source_sha256': digest(args.candidate / 'src/cpp/variant_file_output.cpp'),
               'baseline_kernel_sha256': hashlib.sha256(old.encode()).hexdigest(),
               'candidate_kernel_sha256': hashlib.sha256(new.encode()).hexdigest(),
               'driver_sha256': digest(driver),
               'comparison': 'Raw posterior doubles from uninstrumented extracted kernels; instrumented variants additionally compare every alpha and beta double and must retain the same posterior bytes, final fenv flags and errno.',
               'rounding_mode': 'FE_TONEAREST, nontrapping',
               'limits': ['Actual arithmetic blocks only; full CLI corpus separately checks observation collection, reports and buffer lifetimes.',
                          'The baseline can loop forever when a normalization row is exactly zero or negative; such multi-site inputs are excluded, not repaired.',
                          'Quiet NaN payloads are checked; signaling-NaN traps, asynchronous rounding-mode changes and untested excess-precision architectures are outside the evidence.',
                          'Posterior evaluation now runs backwards and interleaves with beta; instruction-level floating-trap and allocation-failure timing are not guaranteed.']}
    (args.out_dir / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({'passed': True, 'cases_per_build': summary['cases_per_build'], 'builds': len(builds)}))


if __name__ == '__main__':
    main()
