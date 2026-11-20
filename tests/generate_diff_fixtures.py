#!/usr/bin/env python3
"""Generate exact-output cases for individual discordance counter storage."""
import argparse
import json
from pathlib import Path
import subprocess

from generate_fixtures import compress, digest, header, row


def generate(directory, baseline=None):
    fixtures, support_files = [], []
    left_names = ['zeta', 'alpha', 'mid', 'left', 'same', 'half', 'missing', 'last']
    right_names = ['missing', 'renamed', 'zeta', 'right', 'half', 'same', 'last']
    left_calls = ['0/1', '1/0', '0/0', '1/1', './.', '0/.', './.', '1|0']
    right_calls = ['./.', '0/1', '1/0', '0/0', './1', './.', '0|1']

    def write_vcf(name, names, records):
        path = directory / name
        path.write_text(header(names) + '\n'.join(records) + ('\n' if records else ''))
        return path

    def support(name, content):
        path = directory / name
        path.write_text(content)
        support_files.append({'path': name, 'sha256': digest(path)})
        return name

    mapping = support('diff_names.txt', '# source target\nrenamed alpha\nright mid\nrenamed discarded\nrenamed alpha\n')
    keep = support('diff_keep.txt', 'zeta\nalpha\nrenamed\nhalf\nlast\n')
    left_records, right_records = [], []
    for i in range(12):
        left_gt = left_calls[i % 8:] + left_calls[:i % 8]
        right_gt = right_calls[i % 7:] + right_calls[:i % 7]
        chrom = '1' if i < 8 else '2'
        left_records.append(row((i + 1) * 10, 'GT:DP:GQ', [g + ':12:60' for g in left_gt], chrom=chrom,
                                ref='N' if i == 2 else 'A', alt='C,G' if i == 4 else 'C'))
        right_records.append(row((i + 1) * 10 + (5 if i in (1, 6) else 0), 'GT:DP:GQ',
                                 [g + (':2:10' if j % 2 else ':12:60') for j, g in enumerate(right_gt)],
                                 chrom=chrom, ref='G' if i == 5 else 'A', alt='G,C' if i == 4 else 'C'))
    right = write_vcf('diff_right.reference', right_names, right_records)
    zipped = compress(right)
    support_files += [{'path': p.name, 'sha256': digest(p)} for p in (right, zipped)]
    modes = [('vcf', '--diff', right.name), ('gzvcf', '--gzdiff', zipped.name)]
    if baseline:
        converted = subprocess.run([str(baseline), '--vcf', str(right.resolve()), '--recode-bcf',
                                    '--recode-INFO-all', '--out', str((directory / 'diff_right').resolve())],
                                   capture_output=True, timeout=30)
        if converted.returncode:
            raise RuntimeError('Baseline could not prepare diff BCF reference: ' + converted.stderr.decode())
        bcf = directory / 'diff_right.recode.bcf'
        modes.append(('bcf', '--diff-bcf', bcf.name))
        support_files.append({'path': bcf.name, 'sha256': digest(bcf)})

    def case(name, args):
        return {'name': name, 'args': args}

    def add(name, description, records, names, cases, bcf=True):
        path = write_vcf(name + '.vcf', names, records)
        compressed = compress(path)
        fixtures.append({'name': name, 'description': description, 'input': path.name,
                         'compressed_input': compressed.name, 'sha256': digest(path),
                         'gzip_sha256': digest(compressed), 'bcf': bcf, 'cases': cases})

    cases = []
    for label, flag, target in modes:
        for suffix, extra in [('', []), ('_mapped', ['--diff-indv-map', mapping]),
                              ('_keep_mapped', ['--keep', keep, '--diff-indv-map', mapping]),
                              ('_genotype_filters', ['--minDP', '7', '--minGQ', '30']),
                              ('_no_sites', ['--minQ', '9999']),
                              ('_remove', ['--remove-indv', 'zeta'])]:
            cases.append(case(label + suffix, [flag, target, '--diff-indv-discordance'] + extra))
    add('diff_counter_union', 'Unsorted sample names, union-only names, remapping overwrite, allele-string fallback, N REF, missing halves and filters.',
        left_records, left_names, cases)
    add('diff_counter_duplicate_names', 'Duplicate main header names retain the original final-index map overwrite.',
        left_records, ['zeta', 'alpha', 'mid', 'left', 'same', 'half', 'missing', 'zeta'],
        [case('mapped', ['--diff', right.name, '--diff-indv-discordance', '--diff-indv-map', mapping])], bcf=False)
    add('diff_counter_empty', 'No records, but every combined sample still emits its zero counters and legacy NaN.',
        [], left_names, [case('empty', ['--diff', right.name, '--diff-indv-discordance'])])
    add('diff_counter_all_missing', 'All-missing main calls still preserve half-missing versus fully missing comparisons.',
        [row((i + 1) * 10, 'GT', ['./.'] * 8, chrom='1' if i < 8 else '2') for i in range(12)],
        left_names, [case('missing', ['--diff', right.name, '--diff-indv-discordance'])])
    add('diff_counter_order_error', 'Existing chromosome-order failure diagnostics and output timing.',
        [row(10, 'GT', left_calls, chrom='X'), row(20, 'GT', left_calls, chrom='1')],
        left_names, [case('error', ['--diff', right.name, '--diff-indv-discordance'])])
    (directory / 'manifest.json').write_text(json.dumps({'fixtures': fixtures, 'support_files': support_files}, indent=2) + '\n')
    return fixtures


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, help='Optional baseline binary to prepare a raw BCF reference')
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    items = generate(args.out_dir, args.baseline.resolve() if args.baseline else None)
    print(json.dumps({'fixtures': len(items), 'commands': sum(len(item['cases']) for item in items)}))
