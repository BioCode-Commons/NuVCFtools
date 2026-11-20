#!/usr/bin/env python3
"""Generate bounded, deterministic workloads for the algorithm optimizations.

The manifest contains benchmark.py flags. Support paths are relative to this
directory; resolve them before invoking benchmark.py. Random sample selection
is measured with --kept-sites so results do not depend on the clock-seeded RNG.
Exact selected-sample equality is tested separately with a fixed clock.
"""
import argparse
import itertools
import json
from pathlib import Path

from generate_fixtures import digest, header, row


def generate(directory):
    workloads = []

    def write(name, samples, records, flags, description):
        path = directory / (name + '.vcf')
        with path.open('w', encoding='ascii', newline='\n') as stream:
            stream.write(header(samples))
            for record in records:
                stream.write(record + '\n')
        workloads.append({'name': name, 'input': path.name, 'input_format': 'vcf',
                          'args': flags, 'description': description,
                          'bytes': path.stat().st_size, 'sha256': digest(path)})

    names = ['S' + str(i + 1) for i in range(50000)]
    write('random-sample-marking', names,
          (row(i + 1, 'GT', ['0/1'] * len(names)) for i in range(4)),
          ['--max-indv', '25000', '--kept-sites'],
          '50000 samples, 25000 retained; measures membership marking, with selection-independent output.')

    names = ['S1', 'S2']
    points = directory / 'overlap-points.txt'
    points.write_text(''.join('1\t' + str(i * 10000 + 4000) + '\n' for i in range(10000)), encoding='ascii')
    records = (row(i * 10000 + 1001, 'GT', ['0/1', '0/0'], ref='A' * 3000, alt='A')
               for i in range(10000))
    write('positions-overlap', names, records,
          ['--positions-overlap', points.name, '--kept-sites'],
          '10000 deletion records, REF length 3000, final-base hits in 10000 target positions.')
    workloads.append({**workloads[-1], 'name': 'exclude-positions-overlap',
                      'args': ['--exclude-positions-overlap', points.name, '--kept-sites']})

    names = ['S' + str(i + 1) for i in range(128)]
    populations = []
    for group in range(4):
        path = directory / ('population-' + str(group) + '.txt')
        path.write_text('\n'.join(names[group * 32:(group + 1) * 32]) + '\n', encoding='ascii')
        populations.extend(['--weir-fst-pop', path.name])
    alleles = [''.join(p) for p in itertools.product('ACGT', repeat=3)]
    for count in (2, 64):
        def fst_records(count=count):
            for i in range(6000):
                genotypes = [str((j + i) % count) + '/' + str((j * 3 + i // 7) % count)
                             for j in range(len(names))]
                yield row(i * 10 + 1, 'GT', genotypes, ref=alleles[0], alt=','.join(alleles[1:count]))
        write('fst-' + str(count) + '-alleles', names, fst_records(), populations,
              '6000 sites, 128 samples, four populations, ' + str(count) + ' alleles per site.')

    names = ['S' + str(i + 1) for i in range(96)]
    for count in (2, 6):
        def chisq_records(count=count):
            for i in range(200):
                genotypes = [str((j * 7 + i) % count) + '/' + str((j + i // 3) % count)
                             for j in range(len(names))]
                yield row(i * 10 + 1, 'GT', genotypes, ref=alleles[0], alt=','.join(alleles[1:count]))
        write('chisq-' + str(count) + '-alleles', names, chisq_records(),
              ['--geno-chisq', '--ld-window', '15'],
              '200 sites, 96 samples, 15-site LD window, ' + str(count) + ' alleles per site.')

    for broad in (False, True):
        def histogram_records(broad=broad):
            for i in range(40000):
                delta = (10000 if broad and i < 2 else 1) * (1 if i % 2 else -1)
                yield row(i + 1, 'GT', ['0/1'], ref='A' * (1 + max(0, -delta)),
                          alt='A' * (1 + max(0, delta)))
        write('indel-histogram-' + ('broad' if broad else 'narrow'), ['S1'], histogram_records(),
              ['--hist-indel-len'], '40000 records; length span ' + ('20000' if broad else '2') + '.')

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
