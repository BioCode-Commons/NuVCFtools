#!/usr/bin/env python3
"""Generate focused conversion and window-statistics differential inputs.

Run with --out-dir DIR, then pass DIR to compare_outputs.py --extra-fixtures.
Cases deliberately preserve legacy errors and malformed-mask interpretation.
Only fixtures marked bcf=true should be converted to BCF by the test runner.
"""
import argparse
import json
from pathlib import Path

from generate_fixtures import compress, digest, header, row


SAMPLES = tuple('S' + str(i + 1) for i in range(8))
CONVERSIONS = [
    ('plink', ['--plink']), ('012', ['--012']),
    ('ldhat', ['--ldhat', '--chr', '1']),
    ('ldhat_geno', ['--ldhat-geno', '--chr', '1']),
    ('ldhelmet', ['--ldhelmet', '--chr', '1']),
]


def generate(out_dir):
    fixtures, support_files = [], []

    def case(name, args):
        return {'name': name, 'args': args}

    def support(name, contents):
        path = out_dir / name
        path.write_bytes(contents.encode('ascii'))
        support_files.append({'path': name, 'bytes': path.stat().st_size,
                              'sha256': digest(path)})
        return name

    def add(name, description, records, cases, samples=SAMPLES,
            newline='\n', final_newline=True, bcf=True):
        path = out_dir / (name + '.vcf')
        with path.open('wb') as stream:
            stream.write(header(samples).replace('\n', newline).encode('ascii'))
            pending = None
            for record in records:
                if pending is not None:
                    stream.write((pending + newline).encode('ascii'))
                pending = record
            if pending is not None:
                stream.write((pending + (newline if final_newline else '')).encode('ascii'))
        zipped = compress(path)
        fixtures.append({'name': name, 'description': description,
                         'input': path.name, 'compressed_input': zipped.name,
                         'bytes': path.stat().st_size, 'sha256': digest(path),
                         'gzip_sha256': digest(zipped), 'bcf': bcf, 'cases': cases})

    keep = support('memory_keep_noncontiguous.txt', 'S2\nS5\nS8\n')
    absent = support('memory_keep_absent.txt', 'ABSENT_SAMPLE\n')
    pop_a = support('memory_population_a.txt', 'S1\nS2\nS3\nS4\n')
    pop_b = support('memory_population_b.txt', 'S5\nS6\nS7\nS8\n')
    genotype_filters = ['--minDP', '7', '--minGQ', '30', '--remove-filtered-geno-all']
    basic_conversions = [case(name, flags) for name, flags in CONVERSIONS]
    conversion_cases = []
    for suffix, filters in [('', []), ('_kept', ['--keep', keep]),
                            ('_genotype_filters', genotype_filters),
                            ('_no_samples', ['--keep', absent]),
                            ('_no_sites', ['--minQ', '1000000'])]:
        conversion_cases += [case(name + suffix, filters + flags)
                             for name, flags in CONVERSIONS]

    def format_calls(values, bad_sample=-1):
        return [gt + (':4:19:q10' if i == bad_sample else ':12:60:PASS')
                for i, gt in enumerate(values)]

    mixed = [
        row(10, 'GT:DP:GQ:FT', format_calls(['0|0', '0|1', '1|0', '1|1', '.|.', '0|.', '.|1', '1|0'])),
        row(20, 'GT:DP:GQ:FT', format_calls(['0/0', '0/1', '1/0', '1/1', './.', '0/.', './1', '1/0'], 1)),
        row(30, 'GT:DP:GQ:FT', format_calls(['0', '1', '.', '0|1', '1|1', '0|0', '0|1', '1|0'])),
        row(40, 'GT:DP:GQ:FT', format_calls(['0|2', '1|2', '2|1', '2|2', '0|0', '1|1', '0|1', '1|0']), alt='C,G'),
        row(50, 'GT:DP:GQ:FT', format_calls(['0|1'] * 8), ref='A', alt='AT'),
        row(60, 'GT:DP:GQ:FT', format_calls(['1|0'] * 8), ref='AA', alt='CC'),
        row(70, 'GT:DP:GQ:FT', format_calls(['0|1'] * 8), chrom='2'),
    ]
    add('memory_conversion_mixed',
        'Five transposed formats with phased/unphased, partial missing, haploid, multiallelic and noncontiguous sample paths.',
        mixed, conversion_cases)
    add('memory_conversion_crlf', 'CRLF input retains format-specific row contents.',
        mixed[:2], basic_conversions, newline='\r\n')
    add('memory_conversion_no_final_newline', 'Final source record lacks its newline.',
        mixed[:2], basic_conversions, final_newline=False)
    add('memory_conversion_long_alleles', 'Long allele text contributes to PED row lengths; other formats retain their original filters.',
        [row(1, 'GT', ['0|1', '1|0'], ref='A' * 8191, alt='C' * 8192),
         row(2, 'GT', ['1|1', '0|0'], ref='AC', alt='GT')],
        basic_conversions, samples=['S1', 'S2'])
    add('memory_conversion_empty', 'Header-only input exercises empty temporary rows and headers.',
        [], basic_conversions)
    add('memory_conversion_late_error',
        'Valid records precede an unsupported triploid call; compare partial artifacts and errors. Temporary files can remain after the original exit().',
        mixed[:1] + [row(20, 'GT:DP:GQ:FT', format_calls(['0|1'] * 8)),
                     row(30, 'GT:DP:GQ:FT', format_calls(['0|1|1'] + ['0|1'] * 7))],
        basic_conversions, bcf=False)

    for n_sites in (1, 4095, 8190, 8191, 8192, 16382):
        add('memory_conversion_boundary_' + str(n_sites),
            'Two phased samples and %d sites exercise one-character LD rows and two/four-byte matrix/PED rows around the 8191-character chunk boundary.' % n_sites,
            (row(i + 1, 'GT', ['0|1' if i % 2 else '1|0', '1|1' if i % 3 else '0|0'])
             for i in range(n_sites)), basic_conversions, samples=['S1', 'S2'])

    fst = ['--weir-fst-pop', pop_a, '--weir-fst-pop', pop_b]
    window_cases = []
    for name, window, step in [('overlap', 20, 10), ('adjacent', 20, 20),
                               ('zero_step', 20, 0), ('oversize_step', 20, 40)]:
        window_cases.append(case('pi_' + name, ['--window-pi', str(window), '--window-pi-step', str(step)]))
        window_cases.append(case('fst_' + name, fst + ['--fst-window-size', str(window), '--fst-window-step', str(step)]))
    for name, filters in [('genotype_filters', genotype_filters),
                          ('noncontiguous', ['--keep', keep]),
                          ('no_samples', ['--keep', absent]),
                          ('no_sites', ['--minQ', '1000000'])]:
        window_cases.append(case('pi_' + name, filters + ['--window-pi', '20', '--window-pi-step', '10']))
        window_cases.append(case('fst_' + name, filters + fst + ['--fst-window-size', '20', '--fst-window-step', '10']))

    values = ['0|0', '0|1', '1|1', '0|0', '1|1', '1|0', '0|1', '1|1']
    windows = [row(pos, 'GT:DP:GQ:FT', format_calls(values, i % 8))
               for i, pos in enumerate((1, 9, 10, 11, 19, 20, 21, 39, 40, 41, 19999, 20000))]
    windows += [
        row(20001, 'GT:DP:GQ:FT', format_calls(['0|2', '1|2', '2|2', '0|1', '0|0', '2|0', '1|1', '2|1']), alt='C,G'),
        row(20002, 'GT:DP:GQ:FT', format_calls(['0'] + values[1:])),
        row(20003, 'GT:DP:GQ:FT', format_calls(['.|.'] * 8)),
        row(20004, 'GT:DP:GQ:FT', format_calls(['0|0'] * 8)),
    ]
    add('memory_windows_sparse', 'Boundary coordinates, many empty bins, multiallelic/missing/haploid calls and filtering.', windows, window_cases)
    reordered = [row(pos, 'GT', values, chrom=chrom)
                 for chrom, pos in [('1', 10), ('1', 120), ('1', 30), ('1', 30),
                                    ('2', 15), ('2', 220), ('1', 45), ('1', 90)]]
    add('memory_windows_reappearing_chromosome',
        'Unsorted/duplicate coordinates and chromosome reappearance preserve legacy bin shrinking and repeated chromosome output.',
        reordered, window_cases[:8])
    add('memory_windows_empty', 'Header-only window statistics.', [], window_cases[:4])

    mask_multiline = support('memory_mask_multiline.fa',
                             '>1 description\n' + ('0001122399' * 3 + '0') + '\n' +
                             ('0190' * 32) + ' \t\n>2\n' + ('0011' * 40) + '\n')
    mask_long = support('memory_mask_long.fa', '>1\n' + ('00112233445566778899' * 410) + '\n')
    # Keep header lines LF-terminated so the chromosome ID remains exactly 1;
    # CR on data lines is intentionally part of the original mask decoding.
    mask_crlf = support('memory_mask_crlf.fa', '>1 description\n' + '00001111' * 16 + '\r\n' + '0123456789' * 16 + '\r\n')
    mask_odd = support('memory_mask_odd_ascii.fa', '>1\n' + ('0123456789/:;A!~ ' * 20) + '\n')
    mask_cases = []
    for label, mask in [('multiline', mask_multiline), ('long', mask_long),
                        ('crlf', mask_crlf), ('odd_ascii', mask_odd)]:
        for suffix, flags in [('default', ['--mask', mask]),
                              ('threshold', ['--mask', mask, '--mask-min', '4']),
                              ('inverse', ['--invert-mask', mask, '--mask-min', '4'])]:
            mask_cases.append(case('pi_mask_' + label + '_' + suffix,
                                   flags + ['--window-pi', '40', '--window-pi-step', '10']))
    add('memory_window_pi_masks', 'Mask decoding across short/long data lines, inversion, threshold, CR and non-digit ASCII values.',
        [row(pos, 'GT', values) for pos in (1, 2, 8, 16, 30, 31, 32, 33, 50, 99, 100, 101)], mask_cases)
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
                      'cases': sum(len(f['cases']) for f in fixtures)}, sort_keys=True))


if __name__ == '__main__':
    main()
