#!/usr/bin/env python3
"""Generate masked/unmasked window-pi RAM, overlap and control workloads."""
import argparse
import json
from pathlib import Path

from generate_fixtures import digest, header, row


def generate(directory):
    workloads, support_files = [], []
    samples = ['S' + str(i + 1) for i in range(8)]
    values = ['0/0', '0/1', '1/1', '1/0', '0/0', '0/1', '1/1', '0/1']

    def write(name, records, flags, description):
        path = directory / (name + '.vcf')
        with path.open('w', encoding='ascii', newline='\n') as stream:
            stream.write(header(samples))
            for record in records:
                stream.write(record + '\n')
        item = {'name': name, 'input': path.name, 'input_format': 'vcf', 'args': flags,
                'description': description, 'bytes': path.stat().st_size, 'sha256': digest(path)}
        workloads.append(item)
        return item

    def mask(name, length, line_width):
        path = directory / name
        chunk = ('0011223344' * ((line_width + 9) // 10))[:line_width]
        with path.open('w', encoding='ascii', newline='\n') as stream:
            stream.write('>1\n')
            for start in range(0, length, line_width):
                stream.write(chunk[:min(line_width, length - start)] + '\n')
        support_files.append({'path': name, 'bytes': path.stat().st_size, 'sha256': digest(path)})
        return name

    long_mask = mask('window_pi_mask_32m.fa', 32 * 1024 * 1024, 262144)
    write('window-pi-mask-memory', [row(1, 'GT', values), row(30000000, 'GT', values)],
          ['--window-pi', '33554432', '--mask', long_mask, '--mask-min', '9'],
          '32-MiB multiline mask; one output bin isolates packed-mask memory without a full-line 32-MiB string.')
    overlap_mask = mask('window_pi_mask_4m.fa', 4 * 1024 * 1024, 65536)
    write('window-pi-mask-overlap', (row(pos, 'GT', values) for pos in range(1, 4000001, 1000)),
          ['--window-pi', '200000', '--window-pi-step', '1000', '--mask', overlap_mask, '--mask-min', '9'],
          '4000 variant sites and overlapping 200-kb windows; rolling mask counts replace repeated scans.')
    write('window-pi-mask-tiled-control', (row(pos, 'GT', values) for pos in range(1, 4000001, 1000)),
          ['--window-pi', '1000', '--window-pi-step', '1000', '--mask', overlap_mask, '--mask-min', '9'],
          'Disjoint 1-kb windows control packing overhead when no mask overlap can be reused.')
    write('window-pi-dense-overlap', (row(pos, 'GT', values) for pos in range(20001, 40001)),
          ['--window-pi', '20000', '--window-pi-step', '1'],
          '20000 sites, each updating 20000 overlapping bins in the previous implementation; no mask.')
    write('window-pi-dense-tiled-control', (row(pos, 'GT', values) for pos in range(1, 100001)),
          ['--window-pi', '1000', '--window-pi-step', '1000'],
          '100000 sites and disjoint 1-kb windows; ordinary no-mask control with one original bin update per site.')
    write('window-pi-sparse-control',
          (row(pos, 'GT', values, chrom=str(chrom)) for chrom in range(1, 5) for pos in [1000, 200000000]),
          ['--window-pi', '10000', '--window-pi-step', '1000'],
          'Four sparse 200-Mb chromosomes; bin storage stays four unsigned-long values and output prefix work is measured.')
    sequence = [('1', 1), ('1', 200000000), ('2', 1), ('2', 200000000), ('1', 0),
                ('3', 1), ('1', 200000), ('2', 1), ('3', 100000), ('1', 2)]
    write('window-pi-revisit-control', (row(pos, 'GT', values, chrom=chrom) for chrom, pos in sequence),
          ['--window-pi', '10000', '--window-pi-step', '1000'],
          'Chromosome shrink-to-one, delayed re-expansion, retained bin0 and duplicate final output; no mask.')
    (directory / 'manifest.json').write_text(json.dumps({'workloads': workloads, 'support_files': support_files}, indent=2) + '\n')
    return workloads


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    print(json.dumps({'workloads': len(generate(args.out_dir))}))
