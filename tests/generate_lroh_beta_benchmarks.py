#!/usr/bin/env python3
"""Generate LROH rolling-beta RAM workloads and complete-command controls."""
import argparse
import json
from pathlib import Path

from generate_fixtures import digest, header, row


def generate(directory):
    workloads = []

    def write(name, samples, records, description):
        p = directory / (name + '.vcf')
        with p.open('w', encoding='ascii', newline='\n') as out:
            out.write(header(samples))
            for record in records:
                out.write(record + '\n')
        workloads.append({'name': name, 'input': p.name, 'input_format': 'vcf',
                          'args': ['--LROH', '--chr', '1'], 'description': description,
                          'bytes': p.stat().st_size, 'sha256': digest(p)})

    write('lroh-beta-two-samples', ['S1', 'S2'],
          (row(i * 100 + 1, 'GT', ['0/1' if i % 500 < 50 else '0/0', '0/1']) for i in range(1000000)),
          'One million observations / two samples; long homozygous tracts and a large per-sample alpha/beta/posterior workspace; nonempty report.')
    names = ['S' + str(i + 1) for i in range(8)]
    write('lroh-beta-eight-samples', names,
          (row(i * 1000 + 1, 'GT', ['0/1' if i % 150 < 30 else '0/0'] + ['0/1'] * 7) for i in range(200000)),
          '200000 observations / eight equally sized sample histories; controls shared-input storage and early release with nonempty tracts.')
    write('lroh-beta-asymmetric-missing', ['S1', 'S2', 'S3'],
          (row(i * 100 + 1, 'GT', ['0/1' if i < 500000 else './.', '0/0', '0/1']) for i in range(1000000)),
          'One million sites / three samples; first sample has half the observations, so releasing its inputs precedes the later large alpha allocation; nonempty focal report.')
    write('lroh-beta-ordinary-control', names,
          (row(i * 1000 + 1, 'GT', ['0/1' if i % 150 < 30 else '0/0'] + ['0/1'] * 7) for i in range(50000)),
          '50000 observations / eight samples; ordinary tract control matching the earlier workload shape.')
    write('lroh-beta-single-sample-control', ['S1'],
          (row(i * 1000 + 1, 'GT', ['0/1']) for i in range(4096)),
          'A single entirely heterozygous sample exercises repeated scaling and an empty final region list.')
    write('lroh-beta-empty-control', names, [],
          'Header-only input; zero-observation branches and logging remain unchanged.')
    (directory / 'manifest.json').write_text(json.dumps({'workloads': workloads}, indent=2) + '\n')
    return workloads


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    print(json.dumps({'workloads': len(generate(args.out_dir))}))
