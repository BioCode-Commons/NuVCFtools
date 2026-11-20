#!/usr/bin/env python3
"""Generate bounded conversion, window-statistics and mask RAM workloads."""
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

    names = ['S1', 'S2', 'S3', 'S4']
    item = write('conversion-plink', names,
                 (row(i + 1, 'GT', ['0|1', '1|0', '0|0', '1|1']) for i in range(400000)),
                 ['--plink'], '400000 sites / 4 samples; long transposed output rows.')
    for name, args in [('012', ['--012']), ('ldhat', ['--ldhat', '--chr', '1']),
                       ('ldhat-geno', ['--ldhat-geno', '--chr', '1']),
                       ('ldhelmet', ['--ldhelmet', '--chr', '1'])]:
        workloads.append({**item, 'name': 'conversion-' + name, 'args': args})
    write('012-long-alleles', names,
          [row(1, 'GT', ['0/1', '1/0', '0/0', '1/1'], ref='A' * (1024 * 1024), alt='C' * (1024 * 1024)),
           row(2, 'GT', ['0/1', '1/0', '0/0', '1/1'])],
          ['--012'], 'A two-MiB allele record tests removal of the unused allele-vector copy.')

    names = ['S' + str(i + 1) for i in range(8)]
    values = ['0/0', '0/1', '0/1', '1/1', '0/1', '1/1', '1/1', '0/0']
    for label, sample_names in [('a', names[:4]), ('b', names[4:])]:
        (directory / ('population-' + label + '.txt')).write_text('\n'.join(sample_names) + '\n')
    fst = ['--weir-fst-pop', 'population-a.txt', '--weir-fst-pop', 'population-b.txt',
           '--fst-window-size', '10000', '--fst-window-step', '1000']
    item = write('window-pi', names,
                 (row(pos, 'GT', values, chrom=str(chrom))
                  for chrom in range(1, 5) for pos in (1000, 200000000)),
                 ['--window-pi', '10000', '--window-pi-step', '1000'],
                 'Four 200-Mb chromosomes, sparse records and 1-kb window steps; exposes bin allocation without large output.')
    workloads.append({**item, 'name': 'window-fst', 'args': fst})

    def revisits():
        yield row(200000000, 'GT', values, chrom='1')
        for chrom in range(2, 9):
            yield row(200000000, 'GT', values, chrom=str(chrom))
            yield row(1000, 'GT', values, chrom=str(chrom - 1))
        yield row(1000, 'GT', values, chrom='8')

    write('window-pi-revisited-chromosomes', names, revisits(),
          ['--window-pi', '10000', '--window-pi-step', '1000'],
          'Eight chromosome revisits exercise legacy bin shrinking and retained-capacity behavior.')

    mask = directory / 'long-mask.fa'
    mask.write_text('>1\n' + '0123456789' * 838861 + '\n', encoding='ascii')
    write('window-pi-long-mask', names,
          [row(1, 'GT', values), row(7000000, 'GT', values)],
          ['--window-pi', '9000000', '--mask', mask.name, '--mask-min', '9'],
          'One approximately 8-MiB mask line isolates removal of the decoded short-vector temporary.')

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
