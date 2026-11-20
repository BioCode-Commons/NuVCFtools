#!/usr/bin/env python3
"""Generate complete ordinary-PCA inputs for retained-M lifetime measurements."""
import argparse
import json
from pathlib import Path
import random

from generate_fixtures import digest, header, row


def generate(directory):
    workloads = []
    for name, count, sites, normalise in [
            ('pca-512x1025', 512, 1025, True),
            ('pca-512x2048-no-normalisation', 512, 2048, False),
            ('pca-small-control', 16, 1000, True)]:
        names = ['S' + str(i + 1) for i in range(count)]
        path = directory / (name + '.vcf')
        rng = random.Random(77123)
        with path.open('w', encoding='ascii') as stream:
            stream.write(header(names))
            for position in range(sites):
                values = [['0/0', '0/1', '1/1'][rng.randrange(3)] for _ in range(count)]
                # These ensure every site is polymorphic, including small controls.
                values[0], values[1] = '0/0', '1/1'
                stream.write(row(position + 1, 'GT', values) + '\n')
        workloads.append({'name': name, 'input': path.name, 'input_format': 'vcf',
                          'args': ['--pca' if normalise else '--pca-no-norm'],
                          'samples': count, 'sites': sites, 'bytes': path.stat().st_size,
                          'sha256': digest(path), 'configuration': 'lapack',
                          'description': 'Complete polymorphic diploid sites; ordinary PCA retains no M after unchanged Gram construction.'})
    (directory / 'manifest.json').write_text(json.dumps({'workloads': workloads}, indent=2) + '\n')
    return workloads


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    print(json.dumps({'workloads': len(generate(args.out_dir))}))
