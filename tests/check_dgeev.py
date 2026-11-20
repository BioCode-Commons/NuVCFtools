#!/usr/bin/env python3
"""Check actual old/new eigen sorters and wrappers without float tolerances.

Compile both source revisions into one C++98 driver. Sorting comparisons include
NaN barriers, stable ties, signed zeros, infinities and overflowing magnitudes.
Finite matrix cases call the same linked LAPACK library through both wrappers.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


DRIVER = r'''
#include <stdint.h>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>
#include <vector>
using namespace std;

static uint32_t state = 19761120U;
static uint32_t next_value() { state = state * 1664525U + 1013904223U; return state; }
static unsigned long cases = 0;

static double bits(uint64_t value)
{
    double result;
    memcpy(&result, &value, sizeof(result));
    return result;
}

static bool same(const vector<double> &a, const vector<double> &b)
{
    return a.size() == b.size() && (a.empty() || memcmp(&a[0], &b[0], a.size()*sizeof(double)) == 0);
}

static void sort_case(const vector<double> &real, const vector<double> &imaginary)
{
    const int n = real.size();
    vector<double> ar=real, ai=imaginary, br=real, bi=imaginary;
    // A valid dummy pointer also covers the zero-length allocation path.
    double dummy=0;
    baseline_dgeev_sort(n ? &ar[0] : &dummy, n ? &ai[0] : &dummy, n);
    dgeev_sort(n ? &br[0] : &dummy, n ? &bi[0] : &dummy, n);
    if (!same(ar,br) || !same(ai,bi)) { cerr << "eigenvalue sort " << cases << '\n'; exit(1); }
    cases++;

    vector<vector<double> > a(n,vector<double>(n)), b=a;
    vector<double*> ap(n), bp(n);
    for (int i=0;i<n;i++)
    {
        for (int j=0;j<n;j++) a[i][j]=b[i][j]=bits(0x3ff0000000000000ULL+uint64_t(i)*n+j);
        ap[i]=&a[i][0]; bp[i]=&b[i][0];
    }
    ar=real; ai=imaginary; br=real; bi=imaginary;
    baseline_dgeev_sort(n ? &ar[0] : &dummy,n ? &ai[0] : &dummy,n ? &ap[0] : 0,n);
    dgeev_sort(n ? &br[0] : &dummy,n ? &bi[0] : &dummy,n ? &bp[0] : 0,n);
    if (!same(ar,br) || !same(ai,bi)) { cerr << "eigenvector values " << cases << '\n'; exit(1); }
    for (int i=0;i<n;i++) if (!same(a[i],b[i])) { cerr << "eigenvector columns " << cases << '\n'; exit(1); }
    cases++;
}

static void wrapper_case(int n,int mode,int seed)
{
    vector<vector<double> > h(n,vector<double>(n)), a=h,b=h;
    vector<double*> hp(n),ap(n),bp(n);
    vector<double> ar(n),ai(n),br(n),bi(n);
    for (int i=0;i<n;i++)
    {
        for (int j=0;j<n;j++)
        {
            if (mode==0) h[i][j]=(i==j ? (i%3)-1 : 0); // exact repeated eigenvalues
            else if (mode==1) h[i][j]=((i*7+j*3+seed)%11-5)/8.0;
            else if (mode==2) h[i][j]=((i+j+seed)%7-3)/8.0+(i==j ? n : 0);
            else h[i][j]=(i==j ? 1.0 : ((i+j)%2 ? -1.0 : 1.0));
        }
        hp[i]=&h[i][0]; ap[i]=&a[i][0]; bp[i]=&b[i][0];
    }
    baseline_dgeev(&hp[0],n,&ar[0],&ai[0]);
    dgeev(&hp[0],n,&br[0],&bi[0]);
    if (!same(ar,br) || !same(ai,bi)) { cerr << "values wrapper " << n << ',' << mode << ',' << seed << '\n'; exit(1); }
    cases++;
    baseline_dgeev(&hp[0],n,&ar[0],&ai[0],&ap[0]);
    dgeev(&hp[0],n,&br[0],&bi[0],&bp[0]);
    if (!same(ar,br) || !same(ai,bi)) { cerr << "vectors wrapper " << n << ',' << mode << ',' << seed << '\n'; exit(1); }
    for (int i=0;i<n;i++) if (!same(a[i],b[i])) { cerr << "wrapper columns " << n << ',' << mode << ',' << seed << '\n'; exit(1); }
    cases++;
}

int main()
{
    const double qnan=bits(0x7ff8000000000123ULL);
    const double infinity=numeric_limits<double>::infinity();
    const double values[]={0.,-0.,1.,-1.,2.,-2.,qnan,bits(0xfff8000000000456ULL),
        infinity,-infinity,1e308,-1e308,1e-300,-1e-300,
        numeric_limits<double>::denorm_min(),-numeric_limits<double>::denorm_min()};
    const unsigned int choices=sizeof(values)/sizeof(values[0]);
    // Four-category exhaustive ordering: different magnitude, equal signed
    // magnitudes, and a NaN that is a fixed barrier in the original bubble sort.
    const double small[]={1.,-1.,2.,qnan};
    unsigned int combinations=1;
    for(int n=0;n<=8;n++)
    {
        if(n)combinations*=4;
        for(unsigned int pattern=0;pattern<combinations;pattern++)
        {
            unsigned int code=pattern;
            vector<double> real(n),imaginary(n,0);
            for(int i=0;i<n;i++){real[i]=small[code%4];code/=4;}
            sort_case(real,imaginary);
        }
    }
    const unsigned long exhaustive=cases;
    for(int test=0;test<2500;test++)
    {
        int n=next_value()%65;
        vector<double> real(n),imaginary(n);
        for(int i=0;i<n;i++){real[i]=values[next_value()%choices];imaginary[i]=values[next_value()%choices];}
        sort_case(real,imaginary);
    }
    for(int n=33;n<=257;n=n*2-1)
        for(int mode=0;mode<5;mode++)
        {
            vector<double> real(n),imaginary(n,0);
            for(int i=0;i<n;i++)
                real[i]=(mode==0 ? i : mode==1 ? n-i : mode==2 ? i%3 : mode==3 ? (i%13==0 ? qnan : i) : 1.);
            sort_case(real,imaginary);
        }
    const unsigned long sorting=cases;
    for(int n=1;n<=24;n++)
        for(int mode=0;mode<4;mode++)
            for(int seed=0;seed<3;seed++) wrapper_case(n,mode,seed);
    cout << "{\"cases\":" << cases << ",\"exhaustive_sort_cases\":" << exhaustive
         << ",\"all_sort_cases\":" << sorting << ",\"lapack_wrapper_cases\":" << cases-sorting
         << ",\"passed\":true,\"byte_comparison\":\"memcmp of every double\"}\n";
}
'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--cxx', default='clang++')
    parser.add_argument('--lapack-framework', default='Accelerate')
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    old = args.baseline.resolve() / 'src/cpp/dgeev.cpp'
    new = args.candidate.resolve() / 'src/cpp/dgeev.cpp'
    baseline = re.sub(r'\b(dgeev|dgeev_sort|dgeev_ctof|dgeev_ftoc)\b', r'baseline_\1', old.read_text())
    source = args.out_dir.resolve() / 'dgeev_probe.cpp'
    source.write_text('#define HAVE_LIBLAPACK 1\n' + baseline.replace('#include "baseline_dgeev.h"', '#include "' + str(new.with_suffix('.h')) + '"')
                      + '\n' + new.read_text().replace('#include "dgeev.h"', '#include "' + str(new.with_suffix('.h')) + '"') + '\n' + DRIVER)
    executable = args.out_dir.resolve() / 'dgeev_probe'
    flags = ['-framework', args.lapack_framework] if args.lapack_framework else ['-llapack', '-lblas']
    command = [args.cxx, '-std=c++98', '-O2', str(source), *flags, '-o', str(executable)]
    compile_result = subprocess.run(command, capture_output=True)
    (args.out_dir / 'build.log').write_bytes(compile_result.stdout + compile_result.stderr)
    compile_result.check_returncode()
    import os
    env = dict(os.environ, VECLIB_MAXIMUM_THREADS='1')
    run = subprocess.run([str(executable)], capture_output=True, env=env)
    (args.out_dir / 'stdout').write_bytes(run.stdout)
    (args.out_dir / 'stderr').write_bytes(run.stderr)
    run.check_returncode()
    summary = json.loads(run.stdout)
    summary.update({'baseline_sha256': sha(old), 'candidate_sha256': sha(new),
                    'driver_sha256': sha(source), 'executable_sha256': sha(executable),
                    'compile_command': command, 'environment': {'VECLIB_MAXIMUM_THREADS': '1'},
                    'contract': 'Bit-exact Er, Ei and eigenvector matrices; same linked LAPACK and source sort definitions.',
                    'limitations': ['Finite matrix inputs to LAPACK only; malformed dimensions and arbitrary LAPACK failures excluded.',
                                    'Sorting fixtures include quiet NaN payloads, but signaling-NaN traps are not modeled.']})
    (args.out_dir / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({key: value for key, value in summary.items() if key in ('cases','passed','exhaustive_sort_cases','all_sort_cases','lapack_wrapper_cases')}))


if __name__ == '__main__':
    main()
