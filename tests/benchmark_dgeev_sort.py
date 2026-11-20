#!/usr/bin/env python3
"""Measure actual DGEEV sorting source and compare complete binary outputs.

Compiles one tiny driver per source revision before measurements. Each measured
child initializes its data, calls the actual eigenvector sorter, and writes all
Er/Ei/Evecs doubles. Times include startup, input initialization and binary output;
they are not whole-PCA timings. Five alternating posix_spawn/wait4 runs measure
each child's own peak RSS without inherited Python fork memory.
"""
import argparse
import filecmp
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time


DRIVER = r'''
#include "dgeev.h"
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <stdint.h>
#include <vector>
using namespace std;
int main(int argc,char **argv)
{
    if(argc!=4) return 2;
    const int n=atoi(argv[1]);
    const int mode=atoi(argv[2]);
    const int iterations=atoi(argv[3]);
    vector<double> real(n),imaginary(n);
    vector<vector<double> > vectors(n,vector<double>(n));
    vector<double*> rows(n);
    for(int i=0;i<n;i++) rows[i]=&vectors[i][0];
    for(int iteration=0;iteration<iterations;iteration++)
    {
        for(int i=0;i<n;i++)
        {
            real[i]=mode==0 ? i+1 : mode==1 ? n-i : (i%7)-3;
            imaginary[i]=(mode==2 && i%2 ? -0.0 : 0.0);
            for(int j=0;j<n;j++)
            {
                const uint64_t value=0x3ff0000000000000ULL+uint64_t(i)*n+j;
                memcpy(&vectors[i][j],&value,sizeof(double));
            }
        }
        dgeev_sort(&real[0],&imaginary[0],&rows[0],n);
    }
    if(fwrite(&real[0],sizeof(double),n,stdout)!=(size_t)n) return 3;
    if(fwrite(&imaginary[0],sizeof(double),n,stdout)!=(size_t)n) return 3;
    for(int i=0;i<n;i++) if(fwrite(&vectors[i][0],sizeof(double),n,stdout)!=(size_t)n) return 3;
    return ferror(stdout) ? 3 : 0;
}
'''


def fingerprint(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(data)
    return {'bytes': path.stat().st_size, 'sha256': h.hexdigest()}


def build(source, destination, cxx, lapack_flags):
    destination.mkdir(parents=True)
    driver = destination / 'sort_driver.cpp'
    driver.write_text(DRIVER)
    executable = destination / 'sort_driver'
    code = source / 'src/cpp/dgeev.cpp'
    command = [cxx, '-std=c++98', '-O2', '-DHAVE_LIBLAPACK=1', '-I', str(code.parent),
               str(driver), str(code), *lapack_flags, '-o', str(executable)]
    result = subprocess.run(command, capture_output=True)
    (destination / 'build.log').write_bytes(result.stdout + result.stderr)
    result.check_returncode()
    return {'executable': str(executable), 'source': str(code), 'source_fingerprint': fingerprint(code),
            'executable_fingerprint': fingerprint(executable), 'compile_command': command}


def run(binary, directory, case, env):
    directory.mkdir(parents=True)
    command = [binary, str(case['n']), str(case['mode']), str(case['iterations'])]
    with open(os.devnull, 'rb') as stdin, (directory / 'stdout.bin').open('wb') as stdout, (directory / 'stderr.bin').open('wb') as stderr:
        actions = [(os.POSIX_SPAWN_DUP2, stdin.fileno(), 0), (os.POSIX_SPAWN_DUP2, stdout.fileno(), 1),
                   (os.POSIX_SPAWN_DUP2, stderr.fileno(), 2)]
        started = time.monotonic()
        pid = os.posix_spawn(binary, command, env, file_actions=actions)
        _, status, usage = os.wait4(pid, 0)
        wall = time.monotonic() - started
    return {'directory': str(directory), 'exit': os.waitstatus_to_exitcode(status),
            'wall_seconds': wall, 'user_seconds': usage.ru_utime, 'system_seconds': usage.ru_stime,
            'peak_rss_bytes': usage.ru_maxrss * (1 if sys.platform == 'darwin' else 1024),
            'stdout': fingerprint(directory / 'stdout.bin'), 'stderr': fingerprint(directory / 'stderr.bin')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--cxx', default='clang++')
    parser.add_argument('--lapack-framework', default='Accelerate')
    args = parser.parse_args()
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    flags = ['-framework', args.lapack_framework] if args.lapack_framework else ['-llapack', '-lblas']
    binaries = {label: build(source.resolve(), out / label, args.cxx, flags)
                for label, source in [('baseline', args.baseline), ('candidate', args.candidate)]}
    env = dict(os.environ, LC_ALL='C', TZ='UTC', VECLIB_MAXIMUM_THREADS='1')
    cases = [
        {'name': 'sort-ascending-512', 'n': 512, 'mode': 0, 'iterations': 2},
        {'name': 'sort-ascending-768', 'n': 768, 'mode': 0, 'iterations': 1},
        {'name': 'sort-already-ordered-512', 'n': 512, 'mode': 1, 'iterations': 2},
        {'name': 'sort-ties-512', 'n': 512, 'mode': 2, 'iterations': 2},
    ]
    results = []
    for case in cases:
        runs = {'baseline': [], 'candidate': []}
        comparisons = []
        for repeat in range(args.repeats):
            order = ['baseline', 'candidate'] if repeat % 2 == 0 else ['candidate', 'baseline']
            for label in order:
                item = run(binaries[label]['executable'], out / case['name'] / ('run-' + str(repeat + 1)) / label, case, env)
                runs[label].append(item)
                print(case['name'], repeat + 1, label, item['wall_seconds'], item['peak_rss_bytes'], flush=True)
            a, b = runs['baseline'][-1], runs['candidate'][-1]
            comparisons.append({'repeat': repeat + 1, 'exit_equal': a['exit'] == b['exit'],
                                'both_succeeded': a['exit'] == b['exit'] == 0,
                                'stdout_equal': filecmp.cmp(Path(a['directory']) / 'stdout.bin', Path(b['directory']) / 'stdout.bin', shallow=False),
                                'stderr_equal': filecmp.cmp(Path(a['directory']) / 'stderr.bin', Path(b['directory']) / 'stderr.bin', shallow=False)})
        medians = {label: {metric: statistics.median(r[metric] for r in items)
                           for metric in ['wall_seconds', 'user_seconds', 'system_seconds', 'peak_rss_bytes']}
                   for label, items in runs.items()}
        passed = all(all(c[key] for key in ['exit_equal', 'both_succeeded', 'stdout_equal', 'stderr_equal']) for c in comparisons)
        results.append({'case': case, 'runs': runs, 'comparisons': comparisons, 'medians': medians, 'passed': passed})
        summary = {'binaries': binaries, 'repeats': args.repeats, 'environment': {'VECLIB_MAXIMUM_THREADS': '1'},
                   'workloads': results, 'passed': all(x['passed'] for x in results),
                   'scope': 'Actual sorting functions; includes process startup, deterministic matrix initialization and complete binary output. Not an end-to-end PCA speed claim.'}
        (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
