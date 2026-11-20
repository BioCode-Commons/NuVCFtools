#!/usr/bin/env python3
"""Generate complete CLI fixtures for rolling-beta and LROH buffer lifetimes."""
import argparse
import json
from pathlib import Path

from generate_fixtures import compress, digest, header, row


def generate(directory):
    fixtures, support_files = [], []
    names = ['S' + str(i + 1) for i in range(8)]
    command = ['--LROH', '--chr', '1']

    def support(name, contents):
        p = directory / name
        p.write_text(contents, encoding='ascii')
        support_files.append({'path': name, 'sha256': digest(p)})
        return name

    keep = support('lroh_beta_keep.txt', 'S1\nS3\nS8\n')
    empty = support('lroh_beta_absent.txt', 'ABSENT\n')

    def case(name, args):
        return {'name': name, 'args': args}

    cases = [case('all', command), case('kept', ['--keep', keep] + command),
             case('genotypes', ['--minDP', '5', '--minGQ', '30', '--remove-filtered-geno-all'] + command),
             case('no_sites', ['--minQ', '999999'] + command), case('no_samples', ['--keep', empty] + command)]

    def add(name, description, records, commands=cases, samples=names, bcf=True, final_newline=True):
        p = directory / (name + '.vcf')
        with p.open('w', encoding='ascii', newline='\n') as out:
            out.write(header(samples))
            pending = None
            for record in records:
                if pending is not None:
                    out.write(pending + '\n')
                pending = record
            if pending is not None:
                out.write(pending + ('\n' if final_newline else ''))
        gz = compress(p)
        fixtures.append({'name': name, 'description': description, 'input': p.name,
                         'compressed_input': gz.name, 'bytes': p.stat().st_size,
                         'sha256': digest(p), 'gzip_sha256': digest(gz), 'bcf': bcf, 'cases': commands})

    def calls(index, heterogeneous=False):
        result = ['0/1' if index % 160 < 25 else '0/0'] + ['0/1'] * 7
        if heterogeneous:
            if index > 250: result[0] = './.'
            if index % 7 == 0: result[1] = './.'
            if index % 11 == 0: result[2] = '0/.'
            if index % 13 == 0: result[3] = '1'
            if index % 17 == 0: result[4] = '1/2'
            result[5] = './.'
        return [gt + (':2:12:q10' if (index + j) % 19 == 0 else ':20:60:PASS')
                for j, gt in enumerate(result)]

    add('lroh_beta_long_renormalization', 'Long accepted chains, multiple reported tracts, backward renormalization and terminal reporting.',
        (row(i * 1000 + 1, 'GT:DP:GQ:FT', calls(i)) for i in range(4096)))
    add('lroh_beta_asymmetric_observations', 'Different per-sample observation counts, empty sample, missing halves, ploidy, multiallelic calls and completed-input release.',
        (row(i * 1000 + 1, 'GT:DP:GQ:FT', calls(i, True), alt='C,G') for i in range(640)))
    add('lroh_beta_terminal_one', 'One observation can exceed the posterior threshold in a large heterozygous cohort; exercises actual final-region output.',
        [row(10, 'GT', ['0/0'] + ['0/1'] * 127)], [case('all', command), case('kept', ['--keep', keep] + command)],
        samples=['S' + str(i + 1) for i in range(128)])
    add('lroh_beta_no_observations', 'No accepted observations for reference-only or all-missing records.',
        [row(10, 'GT', ['0/0'] * 8), row(20, 'GT', ['./.'] * 8)], cases[:2])
    add('lroh_beta_header_only', 'No observations and repeated per-sample logging without work arrays.', [], cases[:2])
    add('lroh_beta_missing_sample', 'First sample has zero observations while later samples still generate a nonempty report.',
        (row(i * 1000 + 1, 'GT', ['./.', '0/0'] + ['0/1'] * 6) for i in range(256)), cases[:2])
    add('lroh_beta_coordinate_edges', 'Small backward steps, duplicate positions, nonpositive first positions and excluded chromosome records preserve transition construction.',
        (row((i * 1000 + 1) - (1500 if i in [29, 199] else 1000 if i in [44, 211] else 1 if i == 0 else 0),
             'GT', ['0/1' if i % 150 < 25 else '0/0'] + ['0/1'] * 7,
             chrom='2' if i % 113 == 0 else '1') for i in range(384)),
        [case('all', command), case('other_chr', ['--LROH', '--chr', '2'])], bcf=False)
    add('lroh_beta_signed_alleles', 'Negative allele IDs are skipped while positive IDs retain original heterozygosity classification.',
        (row(i * 1000 + 1, 'GT', ['-2/0' if i % 17 == 0 else '9/9'] + ['0/1'] * 7)
         for i in range(128)), cases[:2], bcf=False)
    add('lroh_beta_late_error', 'A bad genotype follows valid accumulated observations; compare the original partial header and diagnostics.',
        [row(1, 'GT', ['0/0'] + ['0/1'] * 7), row(1001, 'GT', ['bad'] + ['0/1'] * 7)],
        [case('all', command)], bcf=False)
    add('lroh_beta_no_final_newline', 'Input ending immediately after the last genotype preserves observation and final-report behavior.',
        (row(i * 1000 + 1, 'GT', ['0/0'] + ['0/1'] * 7) for i in range(128)),
        [case('all', command)], final_newline=False)
    add('lroh_beta_no_genotypes', 'Required-genotype failure before any HMM storage.',
        [row(10, None, [])], [case('all', command)], samples=[])
    (directory / 'manifest.json').write_text(json.dumps({'fixtures': fixtures, 'support_files': support_files}, indent=2) + '\n')
    return fixtures


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    fixtures = generate(args.out_dir)
    print(json.dumps({'fixtures': len(fixtures), 'commands': sum(len(f['cases']) for f in fixtures)}))
