#!/usr/bin/env python3
"""Generate chi-square matrix RAM, asymmetry and ordinary-input controls."""
import argparse
import json
from pathlib import Path

from generate_fixtures import digest, header, row
from generate_chisq_fixtures import alternate


def generate(directory):
    workloads = []
    cases = [
        ('chisq-matrix-64', 256, [64, 64], 2, []),
        ('chisq-matrix-96', 256, [96, 96], 2, []),
        ('chisq-asymmetric-wide', 512, [2, 96], 2, []),
        ('chisq-asymmetric-tall', 512, [96, 2], 2, []),
        ('chisq-biallelic-control', 128, [2], 1500, ['--ld-window', '20']),
        ('chisq-six-allele-control', 128, [6], 300, ['--ld-window', '20']),
    ]
    for name, samples, dimensions, sites, flags in cases:
        path = directory / (name + '.vcf')
        with path.open('w', encoding='ascii') as stream:
            stream.write(header(['S%d' % (i + 1) for i in range(samples)]))
            for site in range(sites):
                n = dimensions[site % len(dimensions)]
                values = ['%d/%d' % ((sample + site) % n, ((sample // 3) * (site % 5 + 1) + site) % n)
                          for sample in range(samples)]
                stream.write(row(site + 1, 'GT', values, alt=alternate(n)) + '\n')
        workloads.append({'name': name, 'input': path.name, 'input_format': 'vcf', 'args': ['--geno-chisq'] + flags,
                          'samples': samples, 'sites': sites, 'allele_counts': dimensions, 'bytes': path.stat().st_size,
                          'sha256': digest(path), 'configuration': 'normal',
                          'description': 'Complete diploid genotype chi-square with nonempty output; symmetric large matrices, swapped rectangular controls or ordinary repeated pairs.'})
    (directory / 'manifest.json').write_text(json.dumps({'workloads': workloads}, indent=2) + '\n')
    return workloads


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    print(json.dumps({'workloads': len(generate(args.out_dir))}))
