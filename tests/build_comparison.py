#!/usr/bin/env python3
"""Build identical-toolchain baseline/candidate binaries without Autotools.

This is a developer test helper. Production installation still uses configure
and make. LAPACK/PCA is disabled by default; explicitly enable the same library
in both builds with --lapack or --lapack-framework Accelerate.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess


def build(source, dest, cc, cxx, jobs, lapack_flags=()):
    dest.mkdir(parents=True, exist_ok=True)
    version = (source / '.tarball-version').read_text().strip()
    sources = sorted((source / 'src/cpp').glob('*.cpp')) + sorted((source / 'src/cpp').glob('*.c'))
    compiler_versions = {c: subprocess.check_output([c, '--version'], text=True) for c in (cc, cxx)}

    def compile_one(path):
        cpp = path.suffix == '.cpp'
        compiler = cxx if cpp else cc
        obj = dest / (path.stem + '.o')
        cmd = [compiler, '-O2', '-g']
        if cpp:
            cmd += ['-std=c++11', '-DPACKAGE_VERSION="' + version + '"']
        if lapack_flags:
            cmd += ['-DHAVE_LIBLAPACK=1']
        cmd += ['-c', str(path), '-o', str(obj)]
        digest = hashlib.sha256(path.read_bytes() + json.dumps(cmd).encode() + compiler_versions[compiler].encode())
        for header in sorted((source / 'src/cpp').glob('*.h')):
            digest.update(header.read_bytes())
        stamp = obj.with_suffix('.sha256')
        signature = digest.hexdigest()
        if obj.exists() and stamp.exists() and stamp.read_text() == signature:
            return cmd
        proc = subprocess.run(cmd, capture_output=True, text=True)
        obj.with_suffix('.build.log').write_text(proc.stdout + proc.stderr)
        if proc.returncode:
            raise RuntimeError('Build failed: ' + str(path) + '\n' + proc.stderr)
        stamp.write_text(signature)
        return cmd

    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        commands = list(pool.map(compile_one, sources))
    objects = [str(dest / (path.stem + '.o')) for path in sources]
    normal = [cxx, *objects, '-lz', *lapack_flags, '-o', str(dest / 'vcftools')]
    subprocess.run(normal, check=True, capture_output=True)
    shim = Path(__file__).resolve().with_name('fixed_time.c')
    subprocess.run([cc, '-O2', '-c', str(shim), '-o', str(dest / 'fixed_time.o')], check=True)
    fixed = [cxx, *objects, str(dest / 'fixed_time.o'), '-lz', *lapack_flags, '-o', str(dest / 'vcftools-fixed-clock')]
    subprocess.run(fixed, check=True, capture_output=True)
    metadata = {'source': str(source), 'compilers': compiler_versions, 'compile_commands': commands,
                'link_commands': [normal, fixed], 'pca': bool(lapack_flags),
                'lapack_link_flags': list(lapack_flags),
                'binaries': {name: hashlib.sha256((dest/name).read_bytes()).hexdigest()
                             for name in ('vcftools', 'vcftools-fixed-clock')}}
    (dest / 'build.json').write_text(json.dumps(metadata, indent=2) + '\n')
    return {'source': str(source), 'translation_units': len(sources), 'binaries': metadata['binaries']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--cc', default=os.environ.get('CC', 'cc'))
    parser.add_argument('--cxx', default=os.environ.get('CXX', 'c++'))
    parser.add_argument('--jobs', type=int, default=4)
    lapack = parser.add_mutually_exclusive_group()
    lapack.add_argument('--lapack', action='store_true', help='Enable PCA with -llapack -lblas')
    lapack.add_argument('--lapack-framework', metavar='NAME', help='Enable PCA with a macOS framework, e.g. Accelerate')
    args = parser.parse_args()
    lapack_flags = (['-framework', args.lapack_framework] if args.lapack_framework
                    else ['-llapack', '-lblas'] if args.lapack else [])
    for label, source in [('baseline', args.baseline), ('candidate', args.candidate)]:
        result = build(source.resolve(), args.out_dir.resolve()/label, args.cc, args.cxx, args.jobs, lapack_flags)
        print(json.dumps({'label': label, **result}), flush=True)
