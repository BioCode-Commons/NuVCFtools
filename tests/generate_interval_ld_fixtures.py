#!/usr/bin/env python3
"""Generate exact-output tests for BED interval indexing and every LD reader path."""
import argparse
import json
import random
from pathlib import Path

from generate_fixtures import compress, digest, header, row


def generate(directory):
    fixtures, support_files = [], []
    samples = ['S' + str(i + 1) for i in range(8)]

    def support(name, contents):
        path = directory / name
        path.write_text(contents, encoding='ascii')
        support_files.append({'path': name, 'sha256': digest(path)})
        return name

    def case(name, flags):
        return {'name': name, 'args': flags}

    def add(name, description, records, cases, names=samples, bcf=True):
        path = directory / (name + '.vcf')
        with path.open('w', encoding='ascii') as stream:
            stream.write(header(names))
            for record in records:
                stream.write(record + '\n')
        zipped = compress(path)
        fixtures.append({'name': name, 'description': description, 'input': path.name,
                         'compressed_input': zipped.name, 'sha256': digest(path),
                         'gzip_sha256': digest(zipped), 'bcf': bcf, 'cases': cases})

    bed = support('interval_edges.bed', '# deliberately skipped header\n'
                  '1\t10\t20\n1\t20\t20\n1\t40\t30\n1\t12\t18\n'
                  '1\t50\t60\n1\t50\t60\n1\t-8\t-3\n'
                  '2\t3\t7\n2\t7\t9\nX\t100\t101\n')
    bed_no_newline = support('interval_no_newline.bed', '# header\n1\t10\t20\n1\t40\t30')
    bed_headerless = support('interval_headerless.bed', '1\t1\t100000\n1\t10\t20\n')
    bed_extreme = support('interval_extreme.bed', '# header\n1\t-2147483648\t-2147483647\n'
                          '1\t2147483646\t2147483647\n2\t2147483647\t-2147483648\n')
    absent = support('interval_absent.bed', '# header\nabsent\t1\t9\n')
    keep = support('ld_keep.txt', 'S2\nS5\nS8\n')
    positions = support('ld_selected_positions.txt', 'CHROM\tPOS\n1\t10\n1\t40\n2\t20\nX\t30\n')
    gt = ['0|0', '0|1', '1|0', '1|1', '.|.', '0|.', '.|1', '1|0']
    records = [row(pos, 'GT', gt) for pos in (0, 9, 10, 11, 19, 20, 21, 29, 30, 31, 39, 40, 41, 49, 50, 60, 61)]
    records += [row(8, 'GT', gt, ref='AAAA'), row(25, 'GT', gt, alt='C' * 7),
                row(45, 'GT', gt, alt='C,' + 'G' * 10), row(2, 'GT', gt, chrom='2'),
                row(9, 'GT', gt, chrom='2'), row(10, 'GT', gt, chrom='2'),
                row(100, 'GT', gt, chrom='X'), row(101, 'GT', gt, chrom='X'),
                row(20, 'GT', gt)]
    rng = random.Random(905)
    rng.shuffle(records)
    bed_cases = []
    for label, path in [('edges', bed), ('no_newline', bed_no_newline),
                        ('headerless', bed_headerless), ('absent', absent)]:
        for flag in ('--bed', '--exclude-bed'):
            bed_cases.append(case(label + flag, [flag, path, '--recode', '--recode-INFO-all']))
    bed_cases += [case('bed_then_genotype_filters', ['--bed', bed, '--minDP', '7', '--freq']),
                  case('no_sites_before_loader', ['--chr', 'absent', '--bed', bed, '--kept-sites'])]
    add('bed_unsorted_spans', 'Nested/duplicate/adjacent/zero/reversed ranges, longest ALT, unsorted VCF, header skipping and EOF entry count.', records, bed_cases)
    add('bed_signed_boundaries', 'Signed coordinates and INT32 limits with unchanged allele-span casts.',
        [row(pos, 'GT', gt, chrom=chrom, ref=ref)
         for chrom, pos, ref in [('1', -2147483648, 'A'), ('1', -2147483647, 'A'),
                                 ('1', -7, 'AAA'), ('1', -3, 'A'), ('1', -2, 'A'),
                                 ('1', 2147483646, 'AAA'), ('1', 2147483647, 'A'),
                                 ('2', -10, 'A'), ('2', 2147483647, 'A')]],
        [case('extreme_include', ['--bed', bed_extreme, '--kept-sites']),
         case('extreme_exclude', ['--exclude-bed', bed_extreme, '--kept-sites']),
         case('negative_edges', ['--bed', bed, '--recode'])], bcf=False)

    modes = [('geno', ['--geno-r2']), ('hap', ['--hap-r2']),
             ('chisq', ['--geno-chisq']), ('inter_geno', ['--interchrom-geno-r2']),
             ('inter_hap', ['--interchrom-hap-r2']),
             ('list_geno', ['--geno-r2-positions', positions]),
             ('list_hap', ['--hap-r2-positions', positions])]
    ld_cases = []
    for name, flags in modes:
        for label, extra in [('', []), ('_keep', ['--keep', keep]),
                              ('_filtered', ['--minGQ', '30', '--minDP', '7', '--remove-filtered-geno-all']),
                              ('_window', ['--ld-window', '4', '--ld-window-min', '2', '--ld-window-bp', '35', '--ld-window-bp-min', '10']),
                              ('_threshold', ['--min-r2', '0.25'])]:
            ld_cases.append(case(name + label, flags + extra))
    phased = []
    for i, (chrom, pos) in enumerate([('1', 10), ('1', 20), ('1', 40), ('2', 10), ('2', 20),
                                    ('2', 30), ('1', 30), ('X', 30), ('X', 20), ('1', 40)]):
        values = [gt[(j + i) % len(gt)] + (':4:19:q10' if j == i % 8 else ':12:60:PASS') for j in range(8)]
        phased.append(row(pos, 'GT:DP:GQ:FT', values, chrom=chrom))
    add('ld_all_paths_unsorted', 'Every LD mode, chromosome revisits, duplicate/reversed positions, missing calls, sample and genotype masks.', phased, ld_cases)
    unusual = [['0|0', '0|1', '1|0', '1|1', '0|3', '3|1', '-2|0', '0|-2'],
               ['127/0', '128/0', '254/0', '255/0', '256/0', '-2/0', '0/.', './1'],
               ['0', '1', '.', '0/1/1', '0/0', '1/1', './.', '0/1'],
               ['0/0'] * 8, ['./.'] * 8]
    add('ld_byte_domain', 'Packed masking, signed-byte casts, out-of-range IDs, haploid/polyploid and all-missing/constant columns.',
        [row((i + 1) * 10, 'GT', values) for i, values in enumerate(unusual)],
        [case(name, flags) for name, flags in modes if name in ('geno', 'chisq', 'inter_geno', 'list_geno')], bcf=False)
    add('ld_multiallelic_rows', 'Large-reader allele counts vary by record; includes missing genotype halves.',
        [row((i + 1) * 10, 'GT', [str(j % (i + 2)) + '/' + str((j + i) % (i + 2)) for j in range(8)],
             alt=','.join('C' * (j + 1) for j in range(i + 1))) for i in range(5)],
        [case('chisq', ['--geno-chisq']), case('chisq_window', ['--geno-chisq', '--ld-window', '2'])])
    for count in (4095, 4096, 4097, 8193):
        names = ['S' + str(i + 1) for i in range(count)]
        add('ld_block_' + str(count), 'Packed and two-byte payload boundaries with a following record.',
            [row((i + 1) * 10, 'GT', [gt[(i + j) % 4] for j in range(count)]) for i in range(3)],
            [case('geno', ['--geno-r2']), case('hap', ['--hap-r2']), case('chisq', ['--geno-chisq'])], names=names)
    (directory / 'manifest.json').write_text(json.dumps({'fixtures': fixtures, 'support_files': support_files}, indent=2) + '\n')
    return fixtures


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    items = generate(args.out_dir)
    print(json.dumps({'fixtures': len(items), 'commands': sum(len(item['cases']) for item in items)}))
