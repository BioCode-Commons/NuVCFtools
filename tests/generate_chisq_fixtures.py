#!/usr/bin/env python3
"""Generate expected-row chi-square fixtures for raw CLI comparisons."""
import argparse
import json
from pathlib import Path

from generate_fixtures import compress, digest, header, row


def alternate(n):
    return '.' if n == 1 else ','.join('<A%d>' % i for i in range(1, n))


def generate(directory):
    fixtures, support_files = [], []
    names = ['S%d' % (i + 1) for i in range(16)]

    def support(name, text):
        path = directory / name
        path.write_text(text, encoding='ascii')
        support_files.append({'path': name, 'sha256': digest(path)})
        return name

    keep = support('chisq_keep.txt', 'S1\nS3\nS6\nS12\nS15\n')
    absent = support('chisq_absent.txt', 'ABSENT\n')
    base = ['--geno-chisq']
    commands = [
        ('plain', base), ('kept', base + ['--keep', keep]),
        ('filtered', base + ['--minDP', '7', '--minGQ', '30', '--remove-filtered-geno-all']),
        ('ignored_r2_option', base + ['--min-r2', '0.2']),
        ('short_window', base + ['--ld-window-bp', '25']),
        ('snp_window', base + ['--ld-window', '2', '--ld-window-min', '2']),
        ('no_samples', base + ['--keep', absent]), ('no_sites', base + ['--minQ', '999999'])]

    def add(name, description, records, cases=commands, samples=names, bcf=True):
        path = directory / (name + '.vcf')
        with path.open('w', encoding='ascii') as stream:
            stream.write(header(samples))
            for record in records:
                stream.write(record + '\n')
        zipped = compress(path)
        fixtures.append({'name': name, 'description': description, 'input': path.name, 'compressed_input': zipped.name,
                         'sha256': digest(path), 'gzip_sha256': digest(zipped), 'bcf': bcf,
                         'cases': [{'name': name, 'args': flags} for name, flags in cases]})

    records = []
    for k, n in enumerate([1, 2, 3, 8, 2, 12, 3, 1]):
        values = []
        for i in range(len(names)):
            gt = '%d/%d' % ((i + k) % n, (i * 3 + k // 2) % n)
            if i == k: gt = './.'
            elif i == k + 1: gt = '0/.'
            values.append(gt + (':4:12:q10' if i % 5 == k % 5 else ':20:60:PASS'))
        records.append(row(10 + k * 10, 'GT:DP:GQ:FT', values, alt=alternate(n)))
    add('chisq_expected_dimensions', 'Changing, asymmetric and single-allele dimensions; missing halves and genotype/sample filters.', records)
    add('chisq_expected_zero_margins', 'Empty observations, a single observed cell, zero row/column totals and degenerate degrees of freedom.', [
        row(10, 'GT', ['./.'] * 16, alt=alternate(8)),
        row(20, 'GT', ['0/0'] * 16, alt=alternate(8)),
        row(30, 'GT', ['0/0' if i < 8 else '0/1' for i in range(16)], alt=alternate(3)),
        row(40, 'GT', ['1/1'] * 16, alt=alternate(2)),
        row(50, 'GT', ['./.' if i % 2 else '2/1' for i in range(16)], alt=alternate(3)),
    ], [('plain', base), ('ignored_r2_option', base + ['--min-r2', '0.5']), ('kept', base + ['--keep', keep])])
    add('chisq_expected_permuted', 'Unsorted and duplicate positions, chromosome revisits and reversed genotype order.', [
        row(pos, 'GT', ['%d/%d' % ((i + k) % n, (i * 3 + k) % n) for i in range(16)], chrom=chrom, alt=alternate(n))
        for k, (pos, chrom, n) in enumerate([(40, '1', 6), (10, '1', 3), (10, '1', 8), (20, '2', 2), (15, '1', 3), (70, '1', 2)])],
        [('plain', base), ('window', base + ['--ld-window-bp', '25']), ('minimum', base + ['--ld-window-bp-min', '5'])])
    add('chisq_expected_invalid_ids', 'Legacy positive out-of-range IDs map to zero; negative alleles are skipped.', [
        row(10, 'GT', ['0/0', '0/1', '1/0', '2/2', '9/0', '-2/0', '-1/0', './.'] * 2),
        row(20, 'GT', ['2/0', '1/2', '2/1', '9/9', '0/0', '0/1', '0/-2', './1'] * 2, alt=alternate(3)),
    ], [('plain', base), ('kept', base + ['--keep', keep])], bcf=False)
    add('chisq_expected_nondiploid', 'Haploid and polyploid calls retain original diploid skips and warnings.', [
        row(10, 'GT', ['0', '1', '0/1/1', '0/0', '0/1', '1/0', '1/1', './.'] * 2),
        row(20, 'GT', ['0/1', '1/1', '0', '0/1/1', '0/0', '1/0', '0/1', './.'] * 2),
    ], [('plain', base), ('kept', base + ['--keep', keep])], bcf=False)
    add('chisq_expected_late_error', 'A later bad genotype preserves header, diagnostics and private temporary data.', [
        row(10, 'GT', ['0/1'] * 16), row(20, 'GT', ['0/0', '0/1', '1/1', '1/0'] * 4),
        row(30, 'GT', ['bad'] + ['0/1'] * 15)], [('plain', base)], bcf=False)
    add('chisq_expected_empty', 'Insufficient-site path before matrix construction.', [], [('plain', base)])
    add('chisq_expected_no_genotypes', 'Required-genotype error before creating temporary data.', [row(10, None, [])],
        [('plain', base)], samples=[])
    (directory / 'manifest.json').write_text(json.dumps({'fixtures': fixtures, 'support_files': support_files}, indent=2) + '\n')
    return fixtures


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    fixtures = generate(args.out_dir)
    print(json.dumps({'fixtures': len(fixtures), 'commands': sum(len(f['cases']) for f in fixtures)}))
