#!/usr/bin/env python3
"""Generate sparse/dense burden RAM and Mendel hot-loop workloads without running them."""
import argparse
import json
from pathlib import Path

from generate_fixtures import digest, header, row


def generate(directory):
    workloads, support_files = [], []

    def write(name, names, records, args, description):
        path = directory / (name + '.vcf')
        with path.open('w', encoding='ascii') as stream:
            stream.write(header(names))
            for record in records:
                stream.write(record + '\n')
        item = {'name': name, 'input': path.name, 'input_format': 'vcf', 'args': args,
                'description': description, 'bytes': path.stat().st_size, 'sha256': digest(path)}
        workloads.append(item)
        return item

    n = 2000
    names = ['S' + str(i + 1) for i in range(n)]
    item = write('burden-rare-2000', names,
                 (row(i + 1, 'GT', ['0/1' if j == i % n else '0/0' for j in range(n)]) for i in range(2000)),
                 ['--indv-freq-burden'], '2000 samples / 2000 singleton sites; every sample touched, only bin1 needed; full zero output retained.')
    workloads.append({**item, 'name': 'burden-rare-carriers-2000', 'args': ['--indv-freq-burden2']})
    write('burden-empty-2000', names, [], ['--indv-freq-burden'],
          '2000 samples / no records; all output bins remain present but require no counters.')
    n = 1000
    names = ['S' + str(i + 1) for i in range(n)]
    write('burden-full-frequency-control', names,
          (row(count, 'GT', ['0/0' if count <= 2 * j else '0/1' if count == 2 * j + 1 else '1/1'
                            for j in range(n)]) for count in range(1, 2 * n + 1)),
          ['--indv-freq-burden'], '1000 samples, every allele-count bin1..2000 visited in increasing order; forces dense rows and repeated growth.')

    def all_blocks_records(n):
        block_width = 256
        n_blocks = (2 * n) // block_width + 1
        touched = [set() for _ in range(n)]
        pos = 0
        for block in range(n_blocks):
            count = min((block + 1) * block_width - 1, 2 * n)
            carriers = (count + 1) // 2
            for rotation in range(0, n, carriers):
                values = []
                for sample in range(n):
                    rank = (sample - rotation) % n
                    copies = max(0, min(2, count - 2 * rank))
                    values.append('1/1' if copies == 2 else '0/1' if copies == 1 else '0/0')
                    if copies:
                        touched[sample].add(block)
                pos += 1
                yield row(pos, 'GT', values)
        assert all(len(blocks) == n_blocks for blocks in touched)

    for n, name in [(1000, 'burden-all-blocks-1000'), (512, 'burden-tail-block-512')]:
        write(name, ['S' + str(i + 1) for i in range(n)], all_blocks_records(n),
              ['--indv-freq-burden'],
              'Every sample touches every 256-bin block through rotated carrier windows; all rows allocate the full logical width. '
              + ('Final block holds exactly one counter.' if n == 512 else 'Dense allocation control without prefix-only row coverage.'))

    trios = 100
    names = [role + str(i) for i in range(trios) for role in ('F', 'M', 'C')]
    ped = directory / 'benchmark_trios.ped'
    ped.write_text('# header\n' + ''.join('family%d C%d F%d M%d\n' % (i, i, i, i) for i in range(trios)))
    support_files.append({'path': ped.name, 'sha256': digest(ped)})
    def mendel_records(homozygous=False):
        for pos in range(4000):
            values = []
            for i in range(trios):
                parental = '0/0' if homozygous else '0/1'
                values += [parental, parental, '2/2' if (pos + i) % 101 == 0 else parental]
            yield row(pos + 1, 'GT', values, alt='C,G')
    write('mendel-heterozygous', names, mendel_records(), ['--mendel', ped.name],
          '100 trios / 4000 sites; four unique parental products and occasional errors with nonempty output.')
    write('mendel-homozygous-control', names, mendel_records(True), ['--mendel', ped.name],
          '100 trios / 4000 sites; old set deduplicates to one product, with occasional nonempty errors.')
    (directory / 'manifest.json').write_text(json.dumps({'workloads': workloads, 'support_files': support_files}, indent=2) + '\n')
    return workloads


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    print(json.dumps({'workloads': len(generate(args.out_dir))}))
