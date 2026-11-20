#!/usr/bin/env python3
"""Generate LD metadata rejection, accepted controls and input-lifetime workloads."""
import argparse
import json
from pathlib import Path

from generate_fixtures import digest, header, row


def generate(directory):
    workloads, support_files = [], []

    def records(samples, chromosomes, alleles=2, long_final=0):
        total = sum(count for _, count in chromosomes)
        index = 0
        for chrom, sites in chromosomes:
            for site in range(sites):
                values = ['%d|%d' % ((i + site // 2) % alleles, (i // 3 + site // 2) % alleles) for i in range(samples)]
                index += 1
                yield row(site * 20 + 1, 'GT', values, chrom=chrom,
                          alt=','.join('<A%d>' % a for a in range(1, alleles)),
                          info='LONG=' + 'L' * long_final if index == total and long_final else 'DP=30;FLAG')

    def write(name, samples, chromosomes, flags, description, alleles=2, long_final=0):
        path = directory / (name + '.vcf')
        with path.open('w', encoding='ascii', newline='\n') as stream:
            stream.write(header(['S%d' % (i + 1) for i in range(samples)]))
            for record in records(samples, chromosomes, alleles, long_final): stream.write(record + '\n')
        item = {'name': name, 'input': path.name, 'input_format': 'vcf', 'args': flags,
                'samples': samples, 'sites': sum(n for _, n in chromosomes), 'alleles': alleles,
                'description': description, 'bytes': path.stat().st_size, 'sha256': digest(path)}
        workloads.append(item)
        return item

    def alias(item, name, flags, description=None):
        workloads.append({**item, 'name': name, 'args': flags,
                          'description': description if description is not None else item['description']})

    item = write('ld-metadata-local-geno', 2048, [('1', 160), ('2', 160), ('X', 160)],
                 ['--geno-r2', '--ld-window-bp-min', '3000'],
                 'Most same-chromosome distances and all cross-chromosome pairs reject; a nonempty tail of long-distance pairs remains.')
    alias(item, 'ld-metadata-local-hap', ['--hap-r2', '--ld-window-bp-min', '3000'])
    write('ld-metadata-local-chisq', 2048, [('1', 160), ('2', 160), ('X', 160)],
          ['--geno-chisq', '--ld-window-bp-min', '3000'],
          'Two-byte six-allele payloads; same rejection pattern with real nonempty chi-square results.', alleles=6)
    item = write('ld-metadata-inter-geno', 2048, [('1', 400), ('2', 8), ('X', 8)], ['--interchrom-geno-r2'],
                 'One large chromosome and two small ones reject most same-chromosome pairs while retaining cross-chromosome results.')
    alias(item, 'ld-metadata-inter-hap', ['--interchrom-hap-r2'])

    positions = directory / 'ld_metadata_positions.txt'
    positions.write_text('CHROM\tPOS\n' + ''.join('%s\t%d\n' % (chrom, site * 20 + 1)
                         for chrom in ['1', '2', 'X'] for site in range(0, 200, 4)), encoding='ascii')
    support_files.append({'path': positions.name, 'sha256': digest(positions)})
    item = write('ld-metadata-list-geno', 2048, [('1', 200), ('2', 200), ('X', 200)],
                 ['--geno-r2-positions', positions.name, '--ld-window-bp', '40'],
                 '150 selected anchors versus 450 others; narrow distance and chromosome gates reject most payload decoding.')
    alias(item, 'ld-metadata-list-hap', ['--hap-r2-positions', positions.name, '--ld-window-bp', '40'])

    write('ld-metadata-local-accepted-control', 256, [('1', 256)], ['--geno-r2', '--ld-window', '24'],
          'Every visited inner candidate passes metadata; ordinary packed-reader control.')
    write('ld-metadata-chisq-accepted-control', 256, [('1', 100)], ['--geno-chisq', '--ld-window', '24'],
          'Every visited two-byte candidate passes metadata; six-allele numerical work retained.', alleles=6)
    write('ld-metadata-inter-accepted-control', 256, [('1', 1), ('2', 1), ('X', 1)], ['--interchrom-hap-r2'],
          'All three pairs are interchromosomal and accepted; startup-scale control.')
    one = directory / 'ld_metadata_one_position.txt'; one.write_text('CHROM\tPOS\n1\t1\n', encoding='ascii')
    support_files.append({'path': one.name, 'sha256': digest(one)})
    write('ld-metadata-list-accepted-control', 256, [('1', 256)], ['--geno-r2-positions', one.name],
          'One anchor versus 255 targets, all accepted; verifies no rejected-pair assumption is needed.')

    item = write('ld-metadata-wide-rejected', 131072, [('1', 8)], ['--geno-r2', '--ld-window-bp-min', '100000'],
                 '131072 samples; all candidates reject, exposing lazy second-vector allocation and released input staging. Header-only result is intentional.')
    alias(item, 'ld-metadata-wide-accepted', ['--geno-r2', '--ld-window', '1'],
          'Same 131072-sample input with accepted adjacent pairs; distinguishes lifetime savings from rejected-only arrays.')
    write('ld-metadata-long-staging-chisq', 256, [('1', 2)], ['--geno-chisq'],
          'A 16-MiB final INFO row precedes 64-allele observed-matrix allocation; measures release of input entry/staging before numerical work.',
          alleles=64, long_final=16 * 1024 * 1024)
    (directory / 'manifest.json').write_text(json.dumps({'workloads': workloads, 'support_files': support_files}, indent=2) + '\n')
    return workloads


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args(); args.out_dir.mkdir(parents=True, exist_ok=False)
    print(json.dumps({'workloads': len(generate(args.out_dir))}))
