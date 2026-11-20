#!/usr/bin/env python3
"""Generate focused relatedness and LROH differential fixtures.

Use --out-dir DIR, then pass DIR to compare_outputs.py --extra-fixtures.
Each manifest lists its supported cases; bcf=true requests baseline conversion
and raw BCF-path comparisons as well as VCF and VCF.gz. LROH requires --chr.
The corpus preserves legacy missing-value and report-counter behavior rather
than asserting that those behaviors are biologically desirable.
"""

import argparse
import json
from pathlib import Path

from generate_fixtures import compress, digest, header, row


SAMPLES = tuple('S' + str(index + 1) for index in range(8))
LROH = ['--LROH', '--chr', '1']


def generate(out_dir):
    fixtures = []
    support_files = []

    def support(name, contents):
        path = out_dir / name
        path.write_text(contents, encoding='ascii')
        support_files.append({'path': name, 'bytes': path.stat().st_size,
                              'sha256': digest(path)})
        return name

    def case(name, args):
        return {'name': name, 'args': args}

    def add(name, description, records, cases, samples=SAMPLES, bcf=True):
        path = out_dir / (name + '.vcf')
        with path.open('w', encoding='ascii', newline='\n') as stream:
            stream.write(header(samples))
            for record in records:
                stream.write(record + '\n')
        compressed = compress(path)
        fixtures.append({'name': name, 'description': description,
                         'input': path.name, 'compressed_input': compressed.name,
                         'bytes': path.stat().st_size, 'sha256': digest(path),
                         'gzip_sha256': digest(compressed), 'bcf': bcf,
                         'cases': cases})

    keep = support('priority_keep_noncontiguous.txt', 'S2\nS5\nS8\n')
    remove = support('priority_remove_prefix.txt', 'S1\nS2\nS3\n')
    empty = support('priority_keep_absent.txt', 'ABSENT_SAMPLE\n')
    lroh_keep = support('priority_lroh_keep.txt', 'S1\nS3\nS5\nS8\n')

    relatedness_cases = []
    for label, flag in [('king', '--relatedness2'), ('yang', '--relatedness')]:
        for suffix, filters in [
            ('plain', []), ('noncontiguous', ['--keep', keep]),
            ('removed_prefix', ['--remove', remove]),
            ('last_only', ['--indv', 'S8']),
            ('genotype_filters', ['--minDP', '7', '--minGQ', '30',
                                  '--remove-filtered-geno-all']),
            ('no_sites', ['--minQ', '1000000']),
            ('no_individuals', ['--keep', empty]),
        ]:
            relatedness_cases.append(case(label + '_' + suffix, filters + [flag]))

    genotypes = [
        ['0/0', '0/1', '1/0', '1/1', './.', '0/.', './1', '0|1'],
        ['1/1', '1/0', '0/1', '0/0', '1|1', '1/.', './0', '1|0'],
        ['0/1', '0/0', '1/1', '0/1', '1/0', '0/0', '1/1', './.'],
        ['1/0', '1/1', '0/0', '1/0', '0/1', '1/1', '0/0', './.'],
        ['0/0'] * 8,
        ['1/1'] * 8,
        ['./.'] * 8,
        ['0/0', '1/1', '0/1', '1/0', '0/0', '1/1', '0/1', '1/0'],
    ]
    records = []
    for index, values in enumerate(genotypes):
        records.append(row((index + 1) * 10, 'GT:DP:GQ:FT', [
            gt + (':4:19:q10' if sample == index % 8 else ':12:60:PASS')
            for sample, gt in enumerate(values)]))
    records += [
        row(90, 'GT:DP:GQ:FT', ['0/2:12:60:PASS', '2/2:12:60:PASS'] +
            ['0/1:12:60:PASS'] * 6, alt='C,G'),
        row(100, 'GT:DP:GQ:FT', ['1:12:60:PASS'] + ['0/1:12:60:PASS'] * 7),
        row(110, 'GT:DP:GQ:FT', ['0/1:12:60:PASS'] * 8, chrom='2'),
    ]
    add('priority_relatedness_mixed',
        'Symmetric/reversed heterozygotes, missing calls, filtered genotypes, multiallelic and haploid skips, and noncontiguous masks.',
        records, relatedness_cases)

    for label, values in [('all_missing', ['./.'] * 8),
                          ('monomorphic_ref', ['0/0'] * 8),
                          ('monomorphic_alt', ['1/1'] * 8)]:
        add('priority_relatedness_' + label,
            'Zero denominators and diagonal/off-diagonal NaN formatting: ' + label + '.',
            [row(10, 'GT', values), row(20, 'GT', values)],
            [case('king', ['--relatedness2']), case('yang', ['--relatedness']),
             case('king_last_only', ['--indv', 'S8', '--relatedness2']),
             case('yang_last_only', ['--indv', 'S8', '--relatedness'])])
    add('priority_relatedness_single', 'One-element triangular allocation and diagonal output.',
        [row(10, 'GT', ['0/1']), row(20, 'GT', ['1/1']), row(30, 'GT', ['./.'])],
        [case('king', ['--relatedness2']), case('yang', ['--relatedness'])], samples=['S1'])
    add('priority_empty', 'Header-only input: empty statistics and no LROH observations.', [],
        [case('king', ['--relatedness2']), case('yang', ['--relatedness']), case('lroh', LROH)])
    add('priority_site_only', 'No genotype columns: matching required-genotype errors.',
        [row(10, None, [])],
        [case('king', ['--relatedness2']), case('yang', ['--relatedness']), case('lroh', LROH)],
        samples=[])

    lroh_cases = [
        case('lroh', LROH),
        case('lroh_noncontiguous', ['--keep', lroh_keep] + LROH),
        case('lroh_genotype_filters', ['--minDP', '7', '--minGQ', '30',
                                      '--remove-filtered-geno-all'] + LROH),
        case('lroh_no_sites', ['--minQ', '1000000'] + LROH),
        case('lroh_no_individuals', ['--keep', empty] + LROH),
    ]

    def tract_records(pattern, mixed=False):
        for index, heterozygous in enumerate(pattern):
            focal = '0/1' if heterozygous else '0/0'
            values = [focal] + ['0/1'] * 7
            if mixed:
                if index % 23 == 0:
                    values[0] = './.'
                if index % 29 == 0:
                    values[1] = '1'
                if index % 31 == 0:
                    values[2] = '0/.'
            values = [gt + (':4:19:q10' if mixed and (index + sample) % 17 == 0 else ':12:60:PASS')
                      for sample, gt in enumerate(values)]
            yield row((index + 1) * 1000, 'GT:DP:GQ:FT', values)

    for label, pattern, mixed in [
        ('bounded_tracts', [True] * 20 + [False] * 90 + [True] * 30 + [False] * 90 + [True] * 30, False),
        ('final_tract', [True] * 20 + [False] * 90 + [True] * 30 + [False] * 90, False),
        ('missing_and_filtered', [True] * 20 + [False] * 90 + [True] * 30 + [False] * 90, True),
        ('no_focal_hets', [False] * 90, False),
    ]:
        add('priority_lroh_' + label,
            'Nonempty LROH report covering ' + label.replace('_', ' ') + '.',
            tract_records(pattern, mixed), lroh_cases)

    add('priority_lroh_repeated_lookahead',
        'Focal sample has no heterozygotes but five separate autozygous regions; preserves repeated suffix additions in the reported count.',
        (row((index + 1) * 100000, 'GT', ['0/0'] +
             ['0/1' if (index // 60) % 2 == 0 else '1/1'] * 7)
         for index in range(600)),
        [case('lroh', LROH), case('lroh_noncontiguous', ['--keep', lroh_keep] + LROH)])

    add('priority_lroh_one_observation', 'One-observation forward/backward and final reporting path.',
        [row(10, 'GT', ['0/0'] + ['0/1'] * 7)], [case('lroh', LROH)])
    add('priority_lroh_zero_observations', 'Rows present but only missing or reference calls; no accepted observations.',
        [row(10, 'GT', ['./.'] * 8), row(20, 'GT', ['0/0'] * 8)], [case('lroh', LROH)])

    mixed_order = []
    pattern = [True] * 20 + [False] * 90 + [True] * 30 + [False] * 90
    for index, heterozygous in enumerate(pattern):
        pos = (index + 1) * 1000
        if index in (54, 94, 184):
            pos -= 1500  # Small backward step; avoids pathological large negative transition probabilities.
        if index in (64, 194):
            pos -= 1000  # Duplicate coordinate.
        mixed_order.append(row(pos, 'GT', ['0/1' if heterozygous else '0/0'] + ['0/1'] * 7))
        if index % 35 == 0:
            mixed_order.append(row(pos + 1, 'GT', ['0/1'] * 8, chrom='2'))
    add('priority_lroh_coordinate_order',
        'Duplicate/slightly backward coordinates and interleaved excluded chromosomes retain original observation order.',
        mixed_order, [case('lroh', LROH), case('lroh_other_chromosome', ['--LROH', '--chr', '2'])])
    return fixtures, support_files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', required=True, type=Path)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    fixtures, support_files = generate(args.out_dir)
    path = args.out_dir / 'manifest.json'
    path.write_text(json.dumps({'schema_version': 1, 'fixture_cwd': '.',
                                'fixtures': fixtures, 'support_files': support_files},
                               indent=2, sort_keys=True) + '\n', encoding='ascii')
    print(json.dumps({'manifest': str(path), 'fixtures': len(fixtures),
                      'cases': sum(len(item['cases']) for item in fixtures)}, sort_keys=True))


if __name__ == '__main__':
    main()
