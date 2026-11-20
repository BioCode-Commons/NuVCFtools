#!/usr/bin/env python3
"""Generate paired VCF workloads for discordance counters without timing setup."""
import argparse
import json
from pathlib import Path

from generate_fixtures import digest, header, row


def generate(directory):
    workloads = []
    for name, n_samples, n_sites in [('diff-counts-many-sites', 2048, 1200),
                                    ('diff-counts-many-samples', 32768, 6)]:
        names = ['cohort_sample_%08d' % i for i in range(n_samples)]
        paths = [directory / (name + '.vcf'), directory / (name + '.reference')]
        for side, path in enumerate(paths):
            with path.open('w') as stream:
                stream.write(header(names))
                for i in range(n_sites):
                    values = [('0/0', '0/1', '1/0', '1/1', './.', '0/.')[(i + j + (side if j % 11 == 0 else 0)) % 6]
                              for j in range(n_samples)]
                    stream.write(row((i + 1) * 10, 'GT', values) + '\n')
        workloads.append({'name': name, 'input': paths[0].name, 'input_format': 'vcf',
                          'args': ['--diff', paths[1].name, '--diff-indv-discordance'],
                          'description': '%d samples / %d shared sites; missing halves and discordant calls.' % (n_samples, n_sites),
                          'sha256': digest(paths[0]), 'reference_sha256': digest(paths[1])})
    (directory / 'manifest.json').write_text(json.dumps({'workloads': workloads}, indent=2) + '\n')
    return workloads


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    print(json.dumps({'workloads': len(generate(args.out_dir))}))
