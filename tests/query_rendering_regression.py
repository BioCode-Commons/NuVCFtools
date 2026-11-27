#!/usr/bin/env python3
"""Compare query rendering and diagnostics against a frozen Perl directory.

Uses the deterministic multi-FORMAT fixture from perl_stats_merge_regression.
Run on a compute node with bgzip/tabix available. No biological data is needed.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
from perl_stats_merge_regression import fixture, locations


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference', required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    fixture(root)
    formats = ['[%SAMPLE]', '[%GT%SAMPLE]', '[%SAMPLE%GT]', '[%GTR]',
               '[%SAMPLE:%GT:%DP]', '[%SAMPLE:%*=,]',
               '[%SAMPLE:%SAMPLE:%GT:%GT]', '[%PL:%FA:%AD:%GT]',
               '%CHROM:%POS[\\t%SAMPLE:%GTR]\\n']
    # The legacy parser requires nonempty before/after sections. Exercise
    # successful rendering here, and check its empty-section error separately.
    formats = ['%CHROM:%POS|'+fmt+'|\\n' for fmt in formats]
    cases = [(f'format-{i}', ['-f', fmt, str(root/'all.vcf.gz')])
             for i, fmt in enumerate(formats)]
    cases += [('selection', ['-c', 'S7,S2,S7', '-f', '%CHROM:%POS|[%SAMPLE:%DP:%GT]|\\n', str(root/'all.vcf.gz')]),
              ('region', ['-r', '22:20000011-20000300', str(root/'all.vcf.gz')]),
              ('old-method', ['--use-old-method', str(root/'all.vcf.gz')])]
    lines = (root/'all.vcf').read_text().splitlines(True)
    header = ''.join(line for line in lines if line.startswith('#'))
    row = next(line for line in lines if not line.startswith('#')).rstrip('\n').split('\t')
    for tag, values in [('extra', [x+':unexpected' for x in row[9:]]),
                        ('empty', ['']+row[10:]), ('short', row[9:-1]),
                        ('missing', ['.']*32), ('repeated', [row[9]]*32)]:
        path = root/(tag+'.vcf')
        path.write_text(header+'\t'.join(row[:9]+values)+'\n')
        cases.append((tag, ['-f', '%CHROM:%POS|[%SAMPLE:%GT:%*=,]|\\n', str(path)]))
    cases.append(('legacy-empty-section', ['-f', '[%GT]\\n', str(root/'all.vcf.gz')]))
    negative_cases = {'extra', 'empty', 'short', 'missing', 'legacy-empty-section'}
    results = []
    for seed in (0, 1, 19):
        for name, flags in cases:
            runs = []
            for label, source, extra in [('reference', args.reference, []), ('candidate', args.candidate, []),
                                         ('candidate-shared', args.candidate, ['--reuse-sample-templates'])]:
                bindir, libdir = locations(source)
                env = dict(os.environ, PERL5LIB=str(libdir), PERL_HASH_SEED=str(seed),
                           PERL_PERTURB_KEYS='0', LC_ALL='C')
                run = subprocess.run(['perl', str(bindir/'vcf-query')]+extra+flags,
                                     env=env, capture_output=True, timeout=60)
                # Only installation paths and changed source-line locations
                # differ legitimately; retain diagnostic order and counts.
                diagnostic = run.stderr.replace(str(libdir).encode(), b'<lib>')
                diagnostic = diagnostic.replace(str(bindir).encode(), b'<lib>')
                diagnostic = re.sub(rb' line \d+', b' line <source>', diagnostic)
                runs.append((run.returncode, run.stdout, diagnostic))
            passed = runs[0] == runs[1] == runs[2]
            if name not in negative_cases:
                passed = passed and runs[0][0] == 0
            results.append(dict(case=name, seed=seed, passed=passed, exit_codes=[r[0] for r in runs]))
            (root/'results.json').write_text(json.dumps(results, indent=2)+'\n')
            if not passed:
                for label, run in zip(('reference', 'candidate', 'candidate-shared'), runs):
                    (root/(name+'-'+label+'.stdout')).write_bytes(run[1])
                    (root/(name+'-'+label+'.stderr')).write_bytes(run[2])
                raise RuntimeError(f'{name} seed {seed}: output or diagnostic mismatch')
    print(json.dumps(dict(passed=True, cases=len(results))))


if __name__ == '__main__':
    main()
