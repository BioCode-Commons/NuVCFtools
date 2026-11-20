#!/usr/bin/env python3
"""Compare complete CLI output bytes, diagnostics, file sets and exit codes.

Use the fixed-clock binaries from build_comparison.py for reproducible logs.
No output sorting, float tolerance, header stripping or log normalization.
"""
import argparse
import filecmp
import fnmatch
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return {'bytes': path.stat().st_size, 'sha256': h.hexdigest()}


def samples(path):
    with path.open() as stream:
        for line in stream:
            if line.startswith('#CHROM\t'):
                return line.rstrip('\r\n').split('\t')[9:]
    return []


def make_cases(args, inputs):
    cases = []
    modes = {
        'stats': [], 'freq': ['--freq'], 'counts': ['--counts'],
        'missing-indv': ['--missing-indv'], 'missing-site': ['--missing-site'],
        'depth': ['--depth'], 'site-depth': ['--site-depth'],
        'site-mean-depth': ['--site-mean-depth'], 'quality': ['--site-quality'],
        'hardy': ['--hardy'], 'het': ['--het'], 'site-pi': ['--site-pi'],
        'relatedness2': ['--relatedness2'],
        'recode': ['--recode', '--recode-INFO-all'],
        'filter-freq': ['--freq', '--maf', '0.05', '--mac', '1', '--hwe', '0.0001', '--max-missing', '0.25'],
        'filter-recode': ['--recode', '--recode-INFO-all', '--minGQ', '10', '--minDP', '3', '--maxDP', '60', '--remove-filtered-geno-all'],
        'all-filters': ['--recode', '--recode-INFO-all', '--minGQ', '10', '--minDP', '3', '--remove-filtered-geno-all', '--maf', '0.05', '--mac', '1', '--hwe', '0.0001', '--max-missing', '0.25'],
    }
    fixture_cases = {}
    for directory in [args.fixtures, *args.extra_fixtures]:
        manifest = json.loads((directory/'manifest.json').read_text())
        for fixture in manifest['fixtures']:
            if fixture['name'] in fixture_cases:
                raise ValueError('Duplicate fixture name: ' + fixture['name'])
            fixture_cases[fixture['name']] = (directory, fixture['cases'], fixture.get('bcf', False))
    for path in inputs:
        ident = path.stem
        zipped = args.out_dir / 'inputs' / (ident + '.vcf.gz')
        zipped.parent.mkdir(parents=True, exist_ok=True)
        zipped.write_bytes(gzip.compress(path.read_bytes(), mtime=0))
        names = samples(path)
        focused = path.parent in args.extra_fixtures
        local_modes = {} if focused else dict(modes)
        fixture_directory, declared, include_bcf = fixture_cases.get(ident, (path.parent, [], False))
        for entry in declared:
            # Resolve fixture-owned support files without changing either run's
            # relative output prefix or private working directory.
            flags = [str(fixture_directory/value) if (fixture_directory/value).is_file() else value
                     for value in entry['args']]
            local_modes['manifest-' + entry['name']] = flags
        if names and not focused:
            local_modes['exclude-recode'] = ['--recode', '--recode-INFO-all', '--remove-indv', names[-1], '--minDP', '3']
            local_modes['keep-relatedness'] = ['--relatedness2', '--indv', names[0]]
            local_modes['empty-relatedness'] = ['--relatedness2', '--minQ', '1000000']
            local_modes['random-subset'] = ['--recode', '--max-indv', '1']
        sources = [('vcf', path), ('gzvcf', zipped)]
        if focused and (include_bcf or ident in {'fst_multiallelic_valid', 'chisq_multiallelic', 'indel_histogram_mixed', 'random_sample_selection'}):
            conversion_dir = args.out_dir/'inputs'/(ident + '-bcf')
            conversion_dir.mkdir()
            converted = subprocess.run([str(args.baseline), '--vcf', str(path), '--recode-bcf', '--recode-INFO-all', '--out', 'reference'], cwd=conversion_dir, capture_output=True, env=args.env, timeout=30)
            (conversion_dir/'stdout').write_bytes(converted.stdout)
            (conversion_dir/'stderr').write_bytes(converted.stderr)
            if converted.returncode:
                raise RuntimeError('Baseline failed BCF fixture conversion: ' + ident)
            sources.append(('bcf', conversion_dir/'reference.recode.bcf'))
        for fmt, data in sources:
            for mode, flags in local_modes.items():
                cases.append({'name': f'{ident}/{fmt}/{mode}', 'input': str(data), 'format': fmt, 'args': flags})
            if not focused:
                for mode in ('freq', 'recode', 'site-depth', 'relatedness2'):
                    cases.append({'name': f'{ident}/{fmt}/{mode}-pipe', 'input': str(data), 'format': fmt, 'args': local_modes[mode] + ['--stdout'], 'stdin': True})
            else:
                for mode, flags in local_modes.items():
                    cases.append({'name': f'{ident}/{fmt}/{mode}-pipe', 'input': str(data), 'format': fmt, 'args': flags + ['--stdout'], 'stdin': True})

    example = args.source / 'examples/valid-4.1.vcf'
    conversion_dir = args.out_dir / 'conversion'
    conversion_dir.mkdir()
    command = [str(args.baseline), '--vcf', str(example), '--recode-bcf', '--recode-INFO-all', '--out', 'reference']
    converted = subprocess.run(command, cwd=conversion_dir, capture_output=True, env=args.env, timeout=30)
    (conversion_dir/'stdout').write_bytes(converted.stdout)
    (conversion_dir/'stderr').write_bytes(converted.stderr)
    if converted.returncode:
        raise RuntimeError('Baseline failed to prepare BCF fixture')
    bcf = conversion_dir / 'reference.recode.bcf'
    extra_modes = {
        **modes, 'recode-bcf': ['--recode-bcf', '--recode-INFO-all'],
        'recode-bcf-filter-genotype': ['--recode-bcf', '--recode-INFO-all', '--minGQ', '10', '--minDP', '3', '--remove-filtered-geno-all'],
        'recode-bcf-filter-all': ['--recode-bcf', '--recode-INFO-all', '--minGQ', '10', '--minDP', '3', '--maf', '0.05', '--mac', '1', '--hwe', '0.0001'],
        '012': ['--012'], 'plink': ['--plink'], 'plink-tped': ['--plink-tped'],
        'geno-depth': ['--geno-depth'], 'get-dp': ['--extract-FORMAT-info', 'DP'],
        'get-info': ['--get-INFO', 'AF'], 'singletons': ['--singletons'],
        'filter-summary': ['--FILTER-summary'], 'window-pi': ['--window-pi', '1000000'],
        'tajima': ['--TajimaD', '1000000'], 'tstv': ['--TsTv-summary'],
        'geno-r2': ['--geno-r2', '--ld-window-bp', '2000000'],
        'hap-r2': ['--hap-r2', '--ld-window-bp', '2000000'],
        'geno-chisq': ['--geno-chisq', '--ld-window-bp', '2000000'],
        'indel-histogram': ['--hist-indel-len'],
        'relatedness': ['--relatedness'],
        'lroh': ['--LROH'],
    }
    for mode in ('diff-indv', 'diff-site', 'diff-site-discordance', 'diff-indv-discordance', 'diff-discordance-matrix', 'diff-switch-error'):
        extra_modes[mode] = ['--diff', str(example), '--' + mode, '--minGQ', '10', '--minDP', '3', '--maf', '0.05']
    pop1 = args.out_dir/'inputs/pop1.txt'
    pop2 = args.out_dir/'inputs/pop2.txt'
    pop1.write_text('NA00001\nNA00002\n')
    pop2.write_text('NA00003\n')
    extra_modes['fst'] = ['--weir-fst-pop', str(pop1), '--weir-fst-pop', str(pop2)]
    extra_modes['window-fst'] = extra_modes['fst'] + ['--fst-window-size', '1000000']
    for fmt, data in [('vcf', example), ('gzvcf', args.out_dir/'inputs/valid-4.1.vcf.gz'), ('bcf', bcf)]:
        for mode, flags in extra_modes.items():
            for stdout in (False, True):
                cases.append({'name': f'extended/{fmt}/{mode}' + ('-stdout' if stdout else ''), 'input': str(data), 'format': fmt, 'args': flags + (['--stdout'] if stdout else [])})
    return cases


def execute(binary, case, dest, env, timeout):
    dest.mkdir(parents=True)
    (dest/'tmp').mkdir()
    command = [str(binary), '--' + case['format'], '-' if case.get('stdin') else case['input'], *case['args'], '--out', 'result', '--temp', 'tmp']
    with (dest/'stdout').open('wb') as stdout, (dest/'stderr').open('wb') as stderr:
        with (open(case['input'], 'rb') if case.get('stdin') else open(os.devnull, 'rb')) as stdin:
            proc = subprocess.run(command, cwd=dest, stdin=stdin, stdout=stdout, stderr=stderr, env=env, timeout=timeout)
    files = {p.name: digest(p) for p in sorted(dest.iterdir()) if p.is_file()}
    return {'exit': proc.returncode, 'files': files, 'command': command}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--fixtures', type=Path, required=True)
    parser.add_argument('--extra-fixtures', type=Path, action='append', default=[], help='Additional focused manifests; run only their declared cases')
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--timeout', type=float, default=30)
    parser.add_argument('--case-pattern', action='append', help='Run only matching case names (shell wildcards); repeat for alternatives')
    args = parser.parse_args()
    for name in ('baseline', 'candidate', 'source', 'fixtures', 'out_dir'):
        setattr(args, name, getattr(args, name).resolve())
    args.extra_fixtures = [path.resolve() for path in args.extra_fixtures]
    args.env = {**os.environ, 'LC_ALL': 'C', 'TZ': 'UTC'}
    args.out_dir.mkdir(parents=True, exist_ok=False)
    inputs = [args.source/'examples'/name for name in ('valid-4.1.vcf', 'valid-4.0.vcf', 'floats.vcf')]
    inputs += sorted(args.fixtures.glob('*.vcf'))
    for directory in args.extra_fixtures:
        inputs += sorted(directory.glob('*.vcf'))
    cases = make_cases(args, inputs)
    if args.case_pattern:
        cases = [case for case in cases if any(fnmatch.fnmatchcase(case['name'], pattern) for pattern in args.case_pattern)]
        if not cases:
            parser.error('no cases matched --case-pattern')
    results = []
    for i, case in enumerate(cases):
        directory = args.out_dir/'runs'/f'{i:04d}'
        baseline = execute(args.baseline, case, directory/'baseline', args.env, args.timeout)
        candidate = execute(args.candidate, case, directory/'candidate', args.env, args.timeout)
        same_files = baseline['files'].keys() == candidate['files'].keys()
        different = [name for name in baseline['files'].keys() | candidate['files'].keys()
                     if name not in baseline['files'] or name not in candidate['files']
                     or not filecmp.cmp(directory/'baseline'/name, directory/'candidate'/name, shallow=False)]
        equal = baseline['exit'] == candidate['exit'] and same_files and not different
        results.append({'case': case, 'equal': equal, 'different_files': different, 'directory': str(directory), 'baseline': baseline, 'candidate': candidate})
        if not equal:
            print(json.dumps({'FAIL': case['name'], 'different_files': different, 'exits': [baseline['exit'],candidate['exit']]}), flush=True)
        if (i+1) % 100 == 0:
            print(f'Compared {i+1}/{len(cases)} cases', flush=True)
    summary = {'cases': len(results), 'passed': sum(r['equal'] for r in results),
               'baseline_successes': sum(r['baseline']['exit'] == 0 for r in results),
               'baseline_nonzero': sum(r['baseline']['exit'] != 0 for r in results),
               'baseline_crashes': sum(r['baseline']['exit'] < 0 for r in results),
               'file_pairs': sum(len(r['baseline']['files']) for r in results),
               'clock': 'fixed_time.c linked in both executables; no output normalization',
               'failures': [r['case']['name'] for r in results if not r['equal']],
               'binaries': {'baseline': digest(args.baseline), 'candidate': digest(args.candidate)},
               'results': results}
    (args.out_dir/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='results'}, indent=2))
    return 0 if summary['passed'] == summary['cases'] and not summary['baseline_crashes'] else 1


if __name__ == '__main__':
    sys.exit(main())
