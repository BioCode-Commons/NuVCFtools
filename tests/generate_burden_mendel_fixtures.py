#!/usr/bin/env python3
"""Generate focused lazy-frequency-burden and Mendel exact-output fixtures."""
import argparse
import json
from pathlib import Path

from generate_fixtures import compress, digest, header, row


def generate(directory):
    fixtures, support_files = [], []
    names = ['S' + str(i + 1) for i in range(8)]

    def support(name, text):
        path = directory / name
        path.write_text(text, encoding='ascii')
        support_files.append({'path': name, 'sha256': digest(path)})
        return name

    def case(name, args):
        return {'name': name, 'args': args}

    def add(name, description, records, cases, samples=names, bcf=True):
        path = directory / (name + '.vcf')
        text = header(samples).replace('#CHROM\t', '##INFO=<ID=AA,Number=1,Type=String,Description="Ancestral allele">\n#CHROM\t')
        with path.open('w', encoding='ascii') as stream:
            stream.write(text)
            for record in records:
                stream.write(record + '\n')
        zipped = compress(path)
        fixtures.append({'name': name, 'description': description, 'input': path.name,
                         'compressed_input': zipped.name, 'sha256': digest(path),
                         'gzip_sha256': digest(zipped), 'bcf': bcf, 'cases': cases})

    keep = support('burden_keep.txt', 'S2\nS5\nS8\n')
    absent = support('burden_absent.txt', 'ABSENT\n')
    masks = [('plain', []), ('keep', ['--keep', keep]),
             ('genotype_filter', ['--minDP', '7', '--minGQ', '30', '--remove-filtered-geno-all']),
             ('derived', ['--derived']), ('derived_keep', ['--derived', '--keep', keep]),
             ('no_sites', ['--minQ', '1000000']), ('no_samples', ['--keep', absent])]
    burden_cases = [case(label + '_' + mode, flags + [mode]) for label, flags in masks
                    for mode in ('--indv-freq-burden', '--indv-freq-burden2', '--indv-burden')]
    calls = [
        ['0/0', '0/1', '1/0', '1/1', './.', '0/.', './1', '0|1'],
        ['1/1'] * 8, ['0/0'] * 8, ['./.'] * 8,
        ['0/2', '2/2', '1/2', '0/0', '1/1', '2/1', '0/.', './2'],
        ['0', '1', '.', '0/1', '1/1', '0/0', '0/1', '1/0'],
        ['0/1/2', '0/1', '1/1', '0/0', '1/0', '1/1', '0/1', '0/0'],
    ]
    records = []
    ancestors = ['A', 'c', '?', '.', 'G', 'A', 'A']
    for i, values in enumerate(calls):
        records.append(row((i + 1) * 10, 'GT:DP:GQ:FT',
                           [gt + (':4:19:q10' if j == i % 8 else ':12:60:PASS') for j, gt in enumerate(values)],
                           alt='C,G' if i in (4, 6) else 'C', info='DP=30;AA=' + ancestors[i]))
    records += [row(90, 'GT', ['0/1'] * 8, info='AA=T'),
                row(100, 'GT', ['0/1'] * 8, info='DP=30'),
                row(110, 'GT', ['1/1'] * 8, info='AA=C')]
    add('burden_mixed', 'Both homozygote-count modes, derived AA/warnings, missing/ploidy skips, noncontiguous masks and legacy output sample labels.',
        records, burden_cases, bcf=False)
    add('burden_mixed_bcf', 'BCF-convertible counterpart, excluding the unsupported polyploid row only.',
        [record for i, record in enumerate(records) if i != 6], burden_cases)
    add('burden_all_frequency_bins', 'Increasing then decreasing allele counts fill each frequency bin, including the last bin and repeated growth.',
        [row(i + 1, 'GT', ['0/0' if count <= 2 * j else '0/1' if count == 2 * j + 1 else '1/1'
                          for j in range(8)], info='AA=A')
         for i, count in enumerate(list(range(17)) + list(reversed(range(17))))],
        [case('alleles', ['--indv-freq-burden']), case('carriers', ['--indv-freq-burden2']),
         case('derived', ['--derived', '--indv-freq-burden']),
         case('keep_labels', ['--keep', keep, '--indv-freq-burden'])])
    add('burden_empty', 'Header-only all-zero matrices with unchanged header, dimensions and labels.', [],
        [case('alleles', ['--indv-freq-burden']), case('carriers', ['--indv-freq-burden2']),
         case('derived_keep', ['--derived', '--keep', keep, '--indv-freq-burden'])])
    add('burden_single_sample', 'One row, all three columns, missing and alternate-homozygote counts.',
        [row(i + 1, 'GT', [gt], info='AA=' + aa) for i, (gt, aa) in enumerate(
            [('0/1', 'A'), ('1/1', 'A'), ('./.', 'A'), ('1/1', 'C')])],
        [case('alleles', ['--indv-freq-burden']), case('carriers', ['--indv-freq-burden2']),
         case('derived', ['--derived', '--indv-freq-burden'])], samples=['S1'])
    add('burden_no_genotypes', 'Required-genotype error remains unchanged.', [row(10, None, [])],
        [case('alleles', ['--indv-freq-burden']), case('carriers', ['--indv-freq-burden2'])], samples=[])
    add('burden_late_parse_error', 'A bad genotype after earlier valid counters preserves partial header/error output.',
        [row(10, 'GT', ['0/1'] * 8), row(20, 'GT', ['bad'] + ['0/1'] * 7)],
        [case('alleles', ['--indv-freq-burden']), case('carriers', ['--indv-freq-burden2'])], bcf=False)

    def boundary_records(n, frequencies):
        return [row(i + 1, 'GT', ['0/0' if count <= 2 * j else '0/1' if count == 2 * j + 1 else '1/1'
                                  for j in range(n)], info='AA=A')
                for i, count in enumerate(frequencies)]

    for n, label, frequencies in [
            (128, 'tail_one', [255, 256, 255, 256]),
            (257, 'absent_middle', [1, 514, 1, 514]),
            (257, 'boundaries', [255, 256, 257, 511, 512, 514])]:
        add('burden_blocks_' + label,
            '256-bin block boundaries, exact final block length, omitted middle block zeros and sample masking.',
            boundary_records(n, frequencies),
            [case('alleles', ['--indv-freq-burden']), case('carriers', ['--indv-freq-burden2']),
             case('kept', ['--keep', keep, '--indv-freq-burden'])],
            samples=['S' + str(i + 1) for i in range(n)])

    ped = support('mendel_trios.ped', '# header\nF S3 S1 S2 1 0\nF S6 S4 S5 2 0\nF S8 S1 S2 1 0\n')
    ped_edges = support('mendel_edges.ped', '# header\n# comment\nF S3 S1 S2\nF S3 S1 S2\nF S4 S1\nF S5 S1 S1\nF S7 S7 S7\nF 0 S1 S2\nF S8 ABSENT S2\n')
    ped_absent = support('mendel_absent.ped', '# header\nF ABSENT S1 S2\n')
    ped_headerless = support('mendel_headerless.ped', 'F S8 S1 S2\nF S3 S1 S2\n')
    ped_no_newline = support('mendel_no_newline.ped', '# header\nF S3 S1 S2')
    mendel_cases = [case('trios', ['--mendel', ped]), case('ped_edges', ['--mendel', ped_edges]),
                    case('headerless', ['--mendel', ped_headerless]), case('no_final_newline', ['--mendel', ped_no_newline]),
                    case('missing_trio', ['--mendel', ped_absent]),
                    case('filter_trio_member', ['--mendel', ped, '--remove-indv', 'S1']),
                    case('filter_genotypes', ['--mendel', ped, '--minGQ', '30', '--minDP', '7']),
                    case('no_sites', ['--mendel', ped, '--minQ', '1000000'])]
    data = [
        ['0/0', '1/1', '0/1', '0/1', '0/1', '1/0', '0/0', '1/0'],
        ['0/0', '0/0', '1/1', '1/1', '1/1', '0/0', '1/1', '0/1'],
        ['0/1', '1/2', '2/0', '1/2', '0/2', '2/2', '0/0', '0/0'],
        ['0/0', './1', '0/1', '0/1', '0/.', '0/1', './.', '0/1'],
        ['1', '0', '0', '0/1/1', '0/0', '1/1', '0/0', '1'],
    ]
    add('mendel_varied', 'Parental Cartesian products, reversed child order, missing halves, ploidy, duplicate/repeated/partial PED records and filters.',
        [row((i + 1) * 10, 'GT:DP:GQ', [gt + (':4:19' if j == i % 8 else ':12:60') for j, gt in enumerate(values)], alt='C,G')
         for i, values in enumerate(data)], mendel_cases, bcf=False)
    add('mendel_varied_bcf', 'BCF-convertible parental/missing cases without the unsupported polyploid row.',
        [row((i + 1) * 10, 'GT:DP:GQ', [gt + (':4:19' if j == i % 8 else ':12:60') for j, gt in enumerate(values)], alt='C,G')
         for i, values in enumerate(data[:-1])], mendel_cases)
    add('mendel_signed_alleles', 'Exactly -1 is skipped; other negative and out-of-range integer IDs retain original membership semantics.',
        [row(10, 'GT', ['-2/-2', '0/0', '-2/0', '9/9', '0/0', '9/0', '2/2', '-2/-2'], alt='C,G'),
         row(20, 'GT', ['-2/-2', '0/0', '0/0', '9/9', '0/0', '1/0', '2/2', '-1/0'], alt='C,G')],
        [case('trios', ['--mendel', ped]), case('edges', ['--mendel', ped_edges])], bcf=False)
    (directory / 'manifest.json').write_text(json.dumps({'fixtures': fixtures, 'support_files': support_files}, indent=2) + '\n')
    return fixtures


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    fixtures = generate(args.out_dir)
    print(json.dumps({'fixtures': len(fixtures), 'commands': sum(len(f['cases']) for f in fixtures)}))
