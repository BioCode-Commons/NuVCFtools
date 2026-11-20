#!/usr/bin/env python3
"""Generate raw VCF-to-BCF differential fixtures and optional RAM workloads."""
import argparse
import json
from pathlib import Path

from generate_fixtures import compress, digest, header, row


def encoding_header(samples):
    text = header(samples)
    definitions = [
        '##FORMAT=<ID=IV,Number=.,Type=Integer,Description="Integer vector">',
        '##FORMAT=<ID=FV,Number=.,Type=Float,Description="Float vector">',
        '##FORMAT=<ID=CH,Number=1,Type=Character,Description="Character">',
        '##FORMAT=<ID=ST,Number=.,Type=String,Description="String">',
        '##FORMAT=<ID=SU,Number=.,Type=String,Description="Second string">',
        '##FORMAT=<ID=SV,Number=.,Type=String,Description="Third string">',
        '##FORMAT=<ID=SW,Number=.,Type=String,Description="Fourth string">',
    ]
    return text.replace('#CHROM', '\n'.join(definitions) + '\n#CHROM')


def fixtures(directory):
    items = []
    samples = ['S1', 'S2', 'S3', 'S4']
    keep = directory / 'encoding_keep.txt'
    keep.write_text('S1\nS3\n')
    commands = [
        {'name': 'raw_bcf', 'args': ['--recode-bcf', '--recode-INFO-all']},
        {'name': 'kept_bcf', 'args': ['--keep', keep.name, '--recode-bcf', '--recode-INFO-all']},
        {'name': 'filtered_bcf', 'args': ['--minDP', '7', '--minGQ', '30', '--recode-bcf', '--recode-INFO-all']},
        {'name': 'vcf_control', 'args': ['--recode', '--recode-INFO-all']},
    ]

    def add(name, records, description, bcf=True):
        path = directory / (name + '.vcf')
        path.write_text(encoding_header(samples) + '\n'.join(records) + '\n')
        zipped = compress(path)
        items.append({'name': name, 'description': description, 'input': path.name,
                      'compressed_input': zipped.name, 'sha256': digest(path),
                      'gzip_sha256': digest(zipped), 'bcf': bcf, 'cases': commands})

    add('encoding_mixed_columns', [
        row(10, 'GT:DP:GQ:IV:FV:CH:ST', ['0/1:8:40:126,-126:1.25,.:a:long',
                                        '1|0:7:30:127,-127:1e-30,1e30:b:',
                                        './.:6:29:32767,-32767:0,-0:c',
                                        '1:20:60:32768,-32768:inf,-inf:d:.']),
        row(20, 'ST:GT:FV:IV:GQ:DP', ['first:0/0:nan,2:2147483647,-2147483647:60:20',
                                     'second:0/1:.:.:30:7', 'third:1|1:3.5:1,2,3', '.']),
        row(30, 'GT:IV:ST:SU', ['0/1:1:a:b', '1/1:2:short', './.:3', '0|0:4::']),
        row(40, 'GT:ST:SU:SV', ['0/1:first:second:third', '.', '', '1|1:last']),
    ], 'Integer width edges, floats, variable vectors, reordered fields, absent trailing fields and whole-row missing resets.')
    add('encoding_column_inheritance', [
        row(10, 'GT:ST:SU:SV', ['0/1', '0/0:a:b:c', '1/1', '0/1:']),
        row(20, 'GT:ST:SU:SV', ['0/1:x:y:z', '0/0', '.', '1/1:last']),
        row(30, 'GT:ST:SU:SV', ['0/1:a:b:c', '', '0/0', '1/1::']),
        row(40, 'GT:ST:SU:SV', ['0/1:a:b:c', '0/0:q:r:s', '1/1', '.']),
    ], 'Legacy short-sample trailing tokens inherit from earlier samples, including empty initial fields and dot/empty resets.')
    add('encoding_duplicate_tags', [
        row(10, 'GT:ST:ST:IV', ['0/1:a:b:1', '0/0:c:d:127', '1/1:e:f:32767', './.:g:h:32768']),
        row(20, 'GT:IV:ST:ST', ['0/0:2:q:r', '0/1:.:s', '1/1', '.']),
    ], 'Duplicate non-GT FORMAT names retain their original positional encoding and parser map behavior.')
    add('encoding_unknown_last', [
        row(10, 'GT:ST:UNDECLARED', ['0/1:first:ignored', '0/0:second:x', '1/1:third', '.']),
        row(20, 'GT:ST:UNDECLARED', ['0/0:a:b', '0/1', '.', '1/1']),
    ], 'Trailing undefined FORMAT fields retain warning order, removal count and known fields.', bcf=False)
    add('encoding_long_fields', [
        row(10, 'GT:ST:SU:SV:SW', [gt + ':' + ':'.join(ch * size for ch in 'abcd')
                                   for gt, size in [('0/1', 16384), ('1/1', 4096), ('0/0', 31), ('./.', 1)]]),
        row(20, 'GT:ST:SU:SV:SW', ['0/1:a:b:c:d', '0/0', '.', '1/1:last']),
    ], 'Extended string lengths and large-to-small field transitions; raw compressed BCF byte comparison.')
    (directory / 'manifest.json').write_text(json.dumps({'fixtures': items}, indent=2) + '\n')
    return len(items)


def performance(directory):
    items = []

    def add(name, n, widths, repeats, description):
        path = directory / (name + '.vcf')
        names = ['S' + str(i + 1) for i in range(n)]
        with path.open('w') as out:
            out.write(encoding_header(names))
            format_names = ['ST', 'SU', 'SV', 'SW'][:len(widths)]
            values = ['0/1:' + ':'.join(chr(65 + i % 26) * width for width in widths) for i in range(n)]
            for i in range(repeats):
                out.write(row(i + 1, 'GT:' + ':'.join(format_names), values) + '\n')
        items.append({'name': name, 'input': path.name, 'input_format': 'vcf',
                      'args': ['--recode-bcf', '--recode-INFO-all'],
                      'description': description, 'bytes': path.stat().st_size, 'sha256': digest(path)})

    add('encoding-many-long-fields', 512, [4096, 4096, 4096, 4096], 3,
        '512 samples, four 4-KiB string FORMAT fields, three records; isolates removal of the N-by-F string matrix.')
    add('encoding-single-long-field', 512, [16384], 3,
        '512 samples, one 16-KiB string FORMAT field, three records; isolates whole-binary-copy removal.')
    add('encoding-many-short-fields', 4096, [8, 8, 8, 8], 40,
        '4096 samples, short string FORMAT columns, forty records; allocation/throughput control.')
    (directory / 'manifest.json').write_text(json.dumps({'workloads': items}, indent=2) + '\n')
    return len(items)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--performance', action='store_true')
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    print(json.dumps({'items': performance(args.out_dir) if args.performance else fixtures(args.out_dir)}))
