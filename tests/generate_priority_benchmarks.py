#!/usr/bin/env python3
"""Generate bounded relatedness and LROH workloads for the third pass.

All output must be retained and compared; these are complete CLI workloads.
The manifest can be consumed with benchmark.py, using its recorded arguments.
"""
import argparse
import json
from pathlib import Path

from generate_fixtures import digest, header, row


def generate(directory):
    workloads = []

    def write(name, samples, records, args, description):
        path = directory / (name + '.vcf')
        with path.open('w', encoding='ascii', newline='\n') as stream:
            stream.write(header(samples))
            for record in records:
                stream.write(record + '\n')
        item = {'name': name, 'input': path.name, 'input_format': 'vcf',
                'args': args, 'description': description,
                'bytes': path.stat().st_size, 'sha256': digest(path)}
        workloads.append(item)
        return item

    for label, n_samples, n_sites in [('matrix', 1200, 32), ('compute', 400, 2000)]:
        names = ['S' + str(i + 1) for i in range(n_samples)]

        def records(n_samples=n_samples, n_sites=n_sites):
            state = 29
            choices = ['0/0', '0/1', '1/0', '1/1', './.']
            for i in range(n_sites):
                genotypes = []
                for j in range(n_samples):
                    state = (1664525 * state + 1013904223) & 0xffffffff
                    genotypes.append(choices[(state >> 16) % len(choices)])
                yield row(i * 100 + 1, 'GT', genotypes)

        item = write('relatedness2-' + label, names, records(), ['--relatedness2'],
                     str(n_samples) + ' samples / ' + str(n_sites) + ' sites; missing and swapped heterozygous genotypes.')
        workloads.append({**item, 'name': 'relatedness-' + label, 'args': ['--relatedness']})

    names = ['S' + str(i + 1) for i in range(8)]
    # Coordinates remain inside signed int. S1 has no heterozygotes; changing
    # population heterozygosity creates repeated reported regions and lookahead.
    write('lroh-repeated-lookahead', names,
          (row(i * 80000 + 1, 'GT', ['0/0'] + (['0/1'] if (i // 60) % 2 == 0 else ['1/1']) * 7)
           for i in range(24000)),
          ['--LROH', '--chr', '1'],
          '24000 sites / 8 samples; focal sample homozygous throughout, alternating population heterozygosity every 60 sites.')
    write('lroh-ordinary-tracts', names,
          (row(i * 1000 + 1, 'GT', ['0/1' if i % 150 < 30 else '0/0'] + ['0/1'] * 7)
           for i in range(50000)),
          ['--LROH', '--chr', '1'],
          '50000 sites / 8 samples; homozygous tracts separated by focal heterozygotes.')

    (directory / 'manifest.json').write_text(json.dumps({'workloads': workloads}, indent=2) + '\n')
    return workloads


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    print(json.dumps({'workloads': len(generate(args.out_dir))}))


if __name__ == '__main__':
    main()
