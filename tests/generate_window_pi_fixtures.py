#!/usr/bin/env python3
"""Generate focused exact-output cases for window-pi range and mask changes."""
import argparse
import json
from pathlib import Path

from generate_fixtures import compress, digest, header, row


def generate(directory):
    fixtures, support_files = [], []
    samples = ['S' + str(i + 1) for i in range(8)]
    values = ['0/0', '0/1', '1/1', '1/0', '0/0', '0/1', '1/1', '0/1']

    def support(name, contents):
        path = directory / name
        path.write_bytes(contents if isinstance(contents, bytes) else contents.encode('ascii'))
        support_files.append({'path': name, 'bytes': path.stat().st_size, 'sha256': digest(path)})
        return name

    def case(name, args):
        return {'name': name, 'args': args}

    def add(name, description, records, cases, bcf=True):
        path = directory / (name + '.vcf')
        path.write_text(header(samples) + ''.join(record + '\n' for record in records), encoding='ascii')
        zipped = compress(path)
        fixtures.append({'name': name, 'description': description, 'input': path.name,
                         'compressed_input': zipped.name, 'bytes': path.stat().st_size,
                         'sha256': digest(path), 'gzip_sha256': digest(zipped), 'bcf': bcf, 'cases': cases})

    base_cases = [case('overlap', ['--window-pi', '20', '--window-pi-step', '3']),
                  case('tiled', ['--window-pi', '20', '--window-pi-step', '20']),
                  case('unit', ['--window-pi', '1', '--window-pi-step', '1']),
                  case('invalid_step', ['--window-pi', '20', '--window-pi-step', '100']),
                  case('nonpositive_step', ['--window-pi', '20', '--window-pi-step', '-1'])]
    add('window_pi_ranges', 'Overlap, exact boundaries, gaps, duplicates and descending positions without a mask.',
        [row(pos, 'GT', values) for pos in [1, 2, 19, 20, 21, 40, 20, 20, 199, 3, 401]], base_cases)
    add('window_pi_revisits', 'Retained bin0 must be canceled after chromosome revisit; old final arrays print on every chromosome occurrence.',
        [row(pos, 'GT', values, chrom=chrom) for chrom, pos in [
            ('1', 1), ('1', 61), ('2', 3), ('2', 80), ('1', 0),
            ('3', 1), ('1', 0), ('1', 50), ('2', 2), ('1', 7), ('3', 80), ('2', 61)]],
        base_cases, bcf=False)
    add('window_pi_empty_ranges', 'Zero/negative coordinates produce empty bin ranges while still triggering original allocation/reset behavior.',
        [row(pos, 'GT', values, chrom=chrom) for chrom, pos in [
            ('1', 0), ('1', -1), ('1', 1), ('2', 0), ('1', -5), ('1', 21)]],
        base_cases[:3], bcf=False)
    add('window_pi_large_coordinates', 'Large signed coordinates with bounded bin counts and unchanged unsigned output endpoint expressions.',
        [row(pos, 'GT', values) for pos in [1, 1073741823, 1073741824, 2147483646, 2147483647]],
        [case('wide', ['--window-pi', '1073741824', '--window-pi-step', '1000000000']),
         case('max_width', ['--window-pi', '2147483647', '--window-pi-step', '2147483647'])])
    keep = support('window_pi_keep.txt', 'S2\nS5\nS8\n')
    records = [row(i + 1, 'GT:DP:GQ', [gt + (':2:10' if j == i % 8 else ':20:60') for j, gt in enumerate(gts)], alt='C,G')
               for i, gts in enumerate([values, ['0/0'] * 8, ['1/1'] * 8,
                   ['0/2', '2/2', '1/2', '0/0', '1/1', './1', '0/.', './.'],
                   ['./.'] * 8, ['0', '1', '.', '0/1', '0/0', '1/1', '0/1', '0/0']])]
    add('window_pi_filtered', 'Missing halves, multiallelic, monomorphic, haploid and genotype/sample filtering.', records,
        [case('all', ['--window-pi', '5', '--window-pi-step', '1']),
         case('genotypes', ['--window-pi', '5', '--window-pi-step', '1', '--minDP', '5', '--minGQ', '30']),
         case('samples', ['--window-pi', '5', '--window-pi-step', '1', '--keep', keep]),
         case('none', ['--window-pi', '5', '--window-pi-step', '1', '--minQ', '1000000'])])
    add('window_pi_empty', 'No bin or mask rows produced for header-only input.', [], base_cases[:2])
    add('window_pi_late_error', 'A malformed genotype follows valid bin updates; original diagnostics/output timing remains.',
        [row(1, 'GT', values), row(40, 'GT', values), row(50, 'GT', ['bad'] + values[1:])], base_cases[:2], bcf=False)

    masks = [
        ('binary', support('window_pi_binary_mask.fa', b'>1 description\n' + (b'00\x00\x80\xff\r129/:;A!~' * 24) + b' \t\n')),
        ('multiline', support('window_pi_multiline_mask.fa', '>1\n' + '0123456789' * 16 + '\n\n' + '0011' * 64 + '\r\n>2\n' + '0011' * 128 + '\n')),
        ('short', support('window_pi_short_mask.fa', '>1\n' + '00112233' * 8 + '\n')),
        ('repeated_header', support('window_pi_repeated_header.fa', '>1\n' + '0011' * 64 + '\n>1\n' + '9999' * 64 + '\n')),
    ]
    mask_cases = []
    for label, name in masks:
        for suffix, args in [('default', ['--mask', name]),
                             ('negative', ['--mask', name, '--mask-min', '-1']),
                             ('inverse', ['--invert-mask', name, '--mask-min', '4'])]:
            mask_cases.append(case(label + '_' + suffix, args + ['--window-pi', '64', '--window-pi-step', '7']))
    add('window_pi_mask_bytes', 'Packed masks preserve char narrowing for binary bytes, CR/NUL, thresholds, inversion and clipping.',
        [row(pos, 'GT', values) for pos in [1, 2, 3, 4, 5, 8, 15, 16, 30, 61, 62, 63, 64, 65, 99, 127, 128, 159, 160, 161, 200, 240]], mask_cases)
    add('window_pi_mask_gaps', 'Sparse emitting windows force rolling counter gaps and clipped/empty ranges.',
        [row(pos, 'GT', values) for pos in [1, 8, 150, 160, 240]],
        [case('disjoint', ['--window-pi', '16', '--window-pi-step', '16', '--mask', masks[1][1], '--mask-min', '9']),
         case('overlap', ['--window-pi', '64', '--window-pi-step', '7', '--mask', masks[1][1], '--mask-min', '9']),
         case('empty_mask_selection', ['--window-pi', '64', '--window-pi-step', '7', '--mask', masks[1][1], '--mask-min', '-129'])])
    manifest = {'fixtures': fixtures, 'support_files': support_files}
    (directory / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return fixtures


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    fixtures = generate(args.out_dir)
    print(json.dumps({'fixtures': len(fixtures), 'commands': sum(len(f['cases']) for f in fixtures)}))
