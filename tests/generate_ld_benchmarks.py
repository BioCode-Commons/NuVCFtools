#!/usr/bin/env python3
"""Generate bounded, deterministic workloads for the LD reader changes.

The manifest uses benchmark.py arguments. Resolve support-file paths against
the generated directory before invoking that sequential runner. These sizes
target subsecond-to-few-second baseline runs; actual timings are hardware
dependent. Generating the fixtures does not execute vcftools.
"""
import argparse
import json
from pathlib import Path
import random

from generate_fixtures import digest, header, row


def records(sample_count, sites_per_chrom, chromosomes, seed, alleles=2):
    """Include perfect linked pairs, varied calls, and deterministic missingness."""
    separator = '|' if alleles == 2 else '/'
    choices = [str(first) + separator + str(second)
               for first in range(alleles) for second in range(alleles)]
    alternate = ','.join(('C', 'G', 'T', 'AA', 'AC')[:alleles - 1])
    for chrom in chromosomes:
        # Replaying the seed gives interchromosomal cases actual high-r2 pairs
        # as well as the many independently generated pair comparisons.
        rng = random.Random(seed)
        linked = None
        for index in range(sites_per_chrom):
            if index % 8 == 1:
                values = linked
            else:
                values = [('.' + separator + '.') if rng.randrange(40) == 0
                          else choices[rng.randrange(len(choices))]
                          for _ in range(sample_count)]
                if index % 8 == 0:
                    linked = values
            yield row(index * 20 + 1, 'GT', values, chrom=chrom, alt=alternate)


def generate(directory):
    workloads = []
    support_files = []

    def write(name, samples, sites, chromosomes, seed, flags, description, alleles=2):
        path = directory / (name + '.vcf')
        names = ['S' + str(index + 1) for index in range(samples)]
        with path.open('w', encoding='ascii', newline='\n') as stream:
            stream.write(header(names))
            for record in records(samples, sites, chromosomes, seed, alleles):
                stream.write(record + '\n')
        workloads.append({'name': name, 'input': path.name, 'input_format': 'vcf',
                          'args': flags, 'description': description,
                          'samples': samples, 'sites': sites * len(chromosomes),
                          'alleles': alleles, 'seed': seed,
                          'bytes': path.stat().st_size, 'sha256': digest(path)})

    write('ld-genotype-128', 128, 2400, ('1',), 151,
          ['--geno-r2', '--ld-window', '48', '--ld-window-bp', '1000', '--min-r2', '0.5'],
          '2400 sites / 128 samples, 48-site standard genotype window; threshold limits output after calculation.')
    write('ld-haplotype-1024', 1024, 500, ('1',), 152,
          ['--hap-r2', '--ld-window', '24', '--ld-window-bp', '500', '--min-r2', '0.5'],
          '500 phased sites / 1024 samples, 24-site standard haplotype window; includes perfect linked pairs.')
    write('ld-interchromosomal-128', 128, 240, ('1', '2', 'X'), 153,
          ['--interchrom-geno-r2', '--min-r2', '0.5'],
          '720 sites / 128 samples on three chromosomes; exercises accepted cross-chromosome pairs and skipped same-chromosome payloads.')

    positions = directory / 'ld-selected-positions.txt'
    positions.write_text('CHROM\tPOS\n' + ''.join(
        chrom + '\t' + str(index * 20 + 1) + '\n'
        for chrom in ('1', '2', 'X') for index in range(0, 240, 12)), encoding='ascii')
    support_files.append({'path': positions.name, 'sha256': digest(positions)})
    write('ld-selected-haplotype-1024', 1024, 240, ('1', '2', 'X'), 154,
          ['--hap-r2-positions', positions.name, '--ld-window-bp', '120', '--min-r2', '0.5'],
          '60 selected sites versus 660 other sites / 1024 samples, three chromosomes, narrow 120-bp window; exposes decoding before chromosome/distance gates.')
    write('ld-chisq-six-alleles-128', 128, 1000, ('1',), 155,
          ['--geno-chisq', '--ld-window', '24'],
          '1000 six-allele sites / 128 samples, 24-site window; two-byte genotypes and 21-by-21 contingency tables, under 24000 result rows.',
          alleles=6)

    write('ld-genotype-65536', 65536, 12, ('1',), 156,
          ['--geno-r2', '--ld-window', '4'],
          '12 sites / 65536 samples; large-cohort control for decoded-vector RAM versus fixed reader overhead.')

    (directory / 'manifest.json').write_text(json.dumps(
        {'workloads': workloads, 'support_files': support_files}, indent=2) + '\n')
    return workloads


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    print(json.dumps({'workloads': len(generate(args.out_dir))}))


if __name__ == '__main__':
    main()
