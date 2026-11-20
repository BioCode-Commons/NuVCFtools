#!/usr/bin/env python3
"""Generate BED lookup and whole-record-copy workloads, one row at a time."""
import argparse
import json
from pathlib import Path

from generate_fixtures import digest, header, row


def generate(directory):
    workloads = []
    samples = ['S1', 'S2', 'S3', 'S4']
    calls = ['0|0', '0|1', '1|0', '1|1']

    def write(name, records, args, description, names=samples):
        path = directory / (name + '.vcf')
        with path.open('w', encoding='ascii') as stream:
            stream.write(header(names))
            for record in records:
                stream.write(record + '\n')
        item = {'name': name, 'input': path.name, 'input_format': 'vcf', 'args': args,
                'description': description, 'bytes': path.stat().st_size, 'sha256': digest(path)}
        workloads.append(item)
        return item

    bed = directory / 'disjoint.bed'
    with bed.open('w') as stream:
        stream.write('# header\n')
        for i in range(40000):
            stream.write('1\t%d\t%d\n' % (i * 10, i * 10 + 5))
    item = write('bed-disjoint', (row(i * 31 % 400000 + 1, 'GT', calls) for i in range(20000)),
                 ['--bed', bed.name, '--kept-sites'],
                 '40000 disjoint intervals and 20000 unsorted query sites, mixed hits/misses.')
    workloads.append({**item, 'name': 'bed-disjoint-exclude', 'args': ['--exclude-bed', bed.name, '--kept-sites']})

    nested = directory / 'nested.bed'
    with nested.open('w') as stream:
        stream.write('# header\n')
        for i in range(300000):
            stream.write('1\t%d\t%d\n' % (i, 1000000 - i))
    write('bed-nested-misses', (row(2000000 + i, 'GT', calls) for i in range(3000)),
          ['--bed', nested.name, '--kept-sites'],
          '300000 nested intervals coalesce to one; 3000 queries outside every interval.')

    long_info = 'LONG=' + 'A' * (8 * 1024 * 1024)
    item = write('vcf-long-info-kept', [row(10, 'GT', calls), row(20, 'GT', calls, info=long_info),
                                     row(30, 'GT', calls)], ['--kept-sites'],
                 'An 8-MiB INFO record isolates full-row retention when genotype parsing is unnecessary.')
    workloads.append({**item, 'name': 'bed-nested-long-row',
                      'args': ['--bed', nested.name, '--kept-sites'],
                      'description': 'Large BED is loaded before an 8-MiB VCF row, exposing retained interval and row buffers.'})
    names = ['S' + str(i + 1) for i in range(4096)]
    values = [calls[i % 4] + ':12:60:' + 'A' * 2048 for i in range(len(names))]
    write('vcf-wide-samples', (row((i + 1) * 10, 'GT:DP:GQ:XX', values) for i in range(3)),
          ['--minDP', '7', '--minGQ', '30', '--freq'],
          '4096 samples, three approximately 8-MiB records with unused FORMAT data and active genotype filters.', names)
    (directory / 'manifest.json').write_text(json.dumps({'workloads': workloads}, indent=2) + '\n')
    return workloads


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    print(json.dumps({'workloads': len(generate(args.out_dir))}))
