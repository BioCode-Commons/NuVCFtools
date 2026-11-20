#!/usr/bin/env python3
"""Generate seven-path LD metadata/decode/lifetime compatibility fixtures."""
import argparse
import json
from pathlib import Path

from generate_fixtures import compress, digest, header, row


def generate(directory):
    fixtures, support_files = [], []
    names = ['S' + str(i + 1) for i in range(12)]
    calls = ['0|0', '0|1', '1|1', '1|0', '0|1', '0|0', '1|1', '1|0', '.|.', '0|.', '.|1', '0|1']

    def support(name, text):
        path = directory / name; path.write_text(text, encoding='ascii')
        support_files.append({'path': name, 'sha256': digest(path)})
        return name

    selected = support('ld_metadata_selected.txt', 'CHROM\tPOS\n1\t10\n1\t40\n2\t10\nX\t20\n')
    absent = support('ld_metadata_absent.txt', 'CHROM\tPOS\n1\t999999\n')
    all_selected = support('ld_metadata_all_selected.txt', 'CHROM\tPOS\n' + ''.join('1\t%d\n' % p for p in [10, 20, 30, 40, 50, 60]))
    keep = support('ld_metadata_keep.txt', 'S1\nS4\nS8\nS12\n')
    paths = [('hap', ['--hap-r2']), ('geno', ['--geno-r2']), ('chisq', ['--geno-chisq']),
             ('inter_hap', ['--interchrom-hap-r2']), ('inter_geno', ['--interchrom-geno-r2']),
             ('list_hap', ['--hap-r2-positions', selected]), ('list_geno', ['--geno-r2-positions', selected])]

    def cases(extra=(), subset=None):
        return [{'name': name, 'args': flags + list(extra)} for name, flags in paths if subset is None or name in subset]

    def add(name, description, records, commands, bcf=True):
        path = directory / (name + '.vcf')
        path.write_text(header(names) + ''.join(record + '\n' for record in records), encoding='ascii')
        zipped = compress(path)
        fixtures.append({'name': name, 'description': description, 'input': path.name,
                         'compressed_input': zipped.name, 'sha256': digest(path), 'gzip_sha256': digest(zipped),
                         'bcf': bcf, 'cases': commands})

    local = ['hap', 'geno', 'chisq', 'list_hap', 'list_geno']
    records = [row(pos, 'GT:DP:GQ:FT', [gt + (':3:12:q10' if (i + k) % 7 == 0 else ':20:60:PASS')
                                       for i, gt in enumerate(calls)], chrom=chrom)
               for k, (chrom, pos) in enumerate([('1', 10), ('1', 20), ('1', 40), ('1', 40), ('1', 5),
                    ('2', 10), ('2', 20), ('1', 50), ('X', 10), ('X', 20), ('X', 45), ('1', 60)])]
    mixed = cases()
    mixed += [{'name': c['name'] + '_distance', 'args': c['args']} for c in cases(['--ld-window-bp-min', '11', '--ld-window-bp', '31'], local)]
    mixed += [{'name': c['name'] + '_snp_min', 'args': c['args']} for c in cases(['--ld-window-min', '3', '--ld-window', '5'], local)]
    mixed += [{'name': c['name'] + '_filtered', 'args': c['args']} for c in cases(['--minDP', '7', '--minGQ', '30', '--remove-filtered-geno-all', '--keep', keep])]
    add('ld_metadata_mixed', 'Accepted/rejected candidates alternate; unsorted/duplicate positions, chromosome revisits, missing halves and filtering cover all seven paths.', records, mixed)
    same_chrom = [row(pos, 'GT', calls) for pos in [10, 20, 30, 40, 50, 60]]
    add('ld_metadata_all_local_accepted', 'All same-chromosome candidates satisfy default metadata gates; interchromosomal candidates all reject.', same_chrom, cases())
    add('ld_metadata_all_distance_rejected', 'Known payload sizes are consumed with no candidate genotype allocation; windows reject every local/list candidate.',
        same_chrom, cases(['--ld-window-bp-min', '999999'], local))
    add('ld_metadata_all_interchrom_accepted', 'Every pair joins different chromosomes, so both interchromosomal readers always decode.',
        [row(10, 'GT', calls, chrom=chrom) for chrom in ['1', '2', 'X']], cases(subset=['inter_hap', 'inter_geno']))
    add('ld_metadata_list_empty_sides', 'No selected anchor or no unselected target preserves header-only output and lazy arrays.', same_chrom,
        [{'name': kind + '_' + label, 'args': [flag, positions]} for kind, flag in [('hap', '--hap-r2-positions'), ('geno', '--geno-r2-positions')]
         for label, positions in [('no_anchors', absent), ('no_targets', all_selected)]])
    add('ld_metadata_chisq_multiallelic', 'Two-byte payloads with changing allele counts and selective windows.',
        [row(pos, 'GT', ['%d/%d' % ((i + k) % n, (i * 3 + k) % n) for i in range(12)],
             alt=','.join('<A%d>' % a for a in range(1, n))) for k, (pos, n) in enumerate([(10, 3), (20, 8), (40, 2), (50, 6), (70, 4)])],
        cases(subset=['chisq']) + [{'name': 'chisq_rejections', 'args': ['--geno-chisq', '--ld-window-bp-min', '11', '--ld-window-bp', '31']}])
    add('ld_metadata_late_error', 'A bad genotype after valid records preserves private temporary bytes and errors before cleanup.',
        same_chrom[:2] + [row(40, 'GT', ['bad'] + calls[1:])], cases(), bcf=False)
    add('ld_metadata_empty', 'Insufficient sites and empty position-list sides retain original exits and output.', [], cases())
    add('ld_metadata_long_last_record', 'Long final INFO staging buffers and entry are released only after input is consumed.',
        same_chrom[:2] + [row(40, 'GT', calls, info='LONG=' + 'L' * 131073)], cases())
    (directory / 'manifest.json').write_text(json.dumps({'fixtures': fixtures, 'support_files': support_files}, indent=2) + '\n')
    return fixtures


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args(); args.out_dir.mkdir(parents=True, exist_ok=False)
    fixtures = generate(args.out_dir)
    print(json.dumps({'fixtures': len(fixtures), 'commands': sum(len(f['cases']) for f in fixtures)}))
