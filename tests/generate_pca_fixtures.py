#!/usr/bin/env python3
"""Generate deterministic, baseline-defined PCA fixtures and optional workloads.

Use with compare_outputs.py --extra-fixtures and LAPACK-enabled binaries.
Unfiltered negative genotype sums are deliberately excluded: the baseline skips
their M elements but later indexes every row through N_sites, an existing
out-of-bounds condition. Explicit --max-missing 1 cases remove such sites first.
"""
import argparse
import json
from pathlib import Path

from generate_fixtures import compress, digest, header, row


SAMPLES = tuple('S' + str(i + 1) for i in range(8))
GENOTYPES = ('0/0', '0/1', '1/1')


def generated_records(samples, sites, seed=491, multiple_chromosomes=False):
    """LCG high bits avoid short correlated genotype cycles across samples."""
    state = seed
    for index in range(sites):
        values = []
        for sample in range(samples):
            state = (1664525 * state + 1013904223) & 0xffffffff
            genotype = GENOTYPES[(state >> 16) % 3]
            if (index + sample) % 7 == 0:
                genotype = genotype.replace('/', '|')
            values.append(genotype)
        chromosome = ('1', '2', 'X')[(index // 17) % 3] if multiple_chromosomes else '1'
        yield row(index * 10 + 1, 'GT', values, chrom=chromosome)


def generate(out_dir):
    fixtures, support_files = [], []

    def support(name, text):
        path = out_dir / name
        path.write_text(text, encoding='ascii')
        support_files.append({'path': name, 'bytes': path.stat().st_size,
                              'sha256': digest(path)})
        return name

    def case(name, flags):
        return {'name': name, 'args': flags}

    def add(name, description, records, cases, samples=SAMPLES):
        path = out_dir / (name + '.vcf')
        with path.open('w', encoding='ascii', newline='\n') as stream:
            stream.write(header(samples))
            for record in records:
                stream.write(record + '\n')
        compressed = compress(path)
        fixtures.append({'name': name, 'description': description, 'input': path.name,
                         'compressed_input': compressed.name, 'bcf': True,
                         'bytes': path.stat().st_size, 'sha256': digest(path),
                         'gzip_sha256': digest(compressed), 'cases': cases})

    keep = support('pca_keep_noncontiguous.txt', 'S1\nS3\nS6\nS8\n')
    remove = support('pca_remove_prefix.txt', 'S1\nS2\n')
    empty = support('pca_keep_absent.txt', 'ABSENT_SAMPLE\n')
    full_cases = [case('pca', ['--pca']), case('pca_no_norm', ['--pca-no-norm'])]
    full_cases += [case('loadings_' + str(count), ['--pca-snp-loadings', str(count)])
                   for count in (0, 1, 2, len(SAMPLES))]
    full_cases += [
        case('kept_pca', ['--keep', keep, '--pca']),
        case('kept_pca_no_norm', ['--keep', keep, '--pca-no-norm']),
        case('kept_loadings', ['--keep', keep, '--pca-snp-loadings', '4']),
        case('removed_loadings', ['--remove', remove, '--pca-snp-loadings', '2']),
        case('last_only_loadings', ['--indv', 'S8', '--pca-snp-loadings', '1']),
        case('no_individuals', ['--keep', empty, '--pca-snp-loadings', '1']),
    ]
    add('pca_complete', 'Complete deterministic genotypes, changing phase and multiple chromosomes.',
        generated_records(8, 96, multiple_chromosomes=True), full_cases)

    missing_records = []
    for index, record in enumerate(generated_records(8, 80, seed=739)):
        fields = record.split('\t')
        if index % 13 == 0:
            fields[9 + index % 8] = './.'
        if index % 17 == 0:
            fields[9 + (index + 1) % 8] = '0/.'
        missing_records.append('\t'.join(fields))
    add('pca_explicit_missing_filter',
        'Missing and partial-missing sites are removed before the baseline matrix construction.',
        missing_records, [
            case('pca_filtered', ['--max-missing', '1', '--pca']),
            case('pca_no_norm_filtered', ['--max-missing', '1', '--pca-no-norm']),
            case('loadings_filtered', ['--max-missing', '1', '--pca-snp-loadings', '2']),
            case('kept_loadings_filtered', ['--keep', keep, '--max-missing', '1', '--pca-snp-loadings', '2']),
        ])

    half_missing = []
    for index, record in enumerate(generated_records(8, 80, seed=971)):
        fields = record.split('\t')
        if index % 5 == 0:
            fields[9 + index % 8] = '1/.' if index % 2 else './1'
        half_missing.append('\t'.join(fields))
    add('pca_half_missing_nonnegative_sum',
        'Only 1/. and ./1 partial calls; their legacy integer sum is zero, so retained matrix rows remain complete.',
        half_missing, [case('pca', ['--pca']), case('pca_no_norm', ['--pca-no-norm']),
                       case('loadings', ['--pca-snp-loadings', '2'])])

    monomorphic = list(generated_records(8, 40, seed=313))
    monomorphic += [row(1000, 'GT', ['0/0'] * 8), row(1010, 'GT', ['1/1'] * 8)]
    add('pca_skipped_monomorphic', 'Monomorphic sites are skipped while remaining rows stay aligned.',
        monomorphic, [case('pca', ['--pca']), case('loadings', ['--pca-snp-loadings', '2'])])

    errors = [case('pca', ['--pca']), case('pca_no_norm', ['--pca-no-norm']),
              case('loadings', ['--pca-snp-loadings', '1'])]
    add('pca_few_sites', 'No more retained sites than samples: exits before constructing the matrix.',
        generated_records(8, 4), errors)
    add('pca_no_observations', 'Header-only input exits before constructing the matrix.', [], errors)
    add('pca_no_polymorphism', 'All sites are skipped before the site-count error.',
        [row(i + 1, 'GT', ['0/0'] * 8) for i in range(20)], errors)
    haploid = list(generated_records(8, 20))
    haploid.append(row(1000, 'GT', ['1'] + ['0/1'] * 7))
    add('pca_ploidy_error', 'Late haploid record errors before matrix construction and loadings output.', haploid, errors)
    multi = list(generated_records(8, 20))
    multi.append(row(1000, 'GT', ['0/2', '1/2'] + ['0/1'] * 6, alt='C,G'))
    add('pca_allele_error', 'Explicit allele-filter override exposes the legacy PCA biallelic error.',
        multi, [case('pca', ['--pca', '--max-alleles', '3']),
                case('loadings', ['--pca-snp-loadings', '2', '--max-alleles', '3'])])
    return fixtures, support_files


def performance(directory):
    workloads = []
    for label, samples, sites, seed in [('pca-loadings-memory', 32, 100000, 491),
                                        ('pca-loadings-small', 8, 2000, 739)]:
        path = directory / (label + '.vcf')
        names = ['S' + str(i + 1) for i in range(samples)]
        with path.open('w', encoding='ascii', newline='\n') as stream:
            stream.write(header(names))
            for record in generated_records(samples, sites, seed):
                stream.write(record + '\n')
        workloads.append({'name': label, 'input': path.name, 'input_format': 'vcf',
                          'args': ['--pca-snp-loadings', '4'], 'samples': samples,
                          'sites': sites, 'bytes': path.stat().st_size, 'sha256': digest(path),
                          'description': 'Complete deterministic genotypes; four PCA SNP loadings, with normalisation.'})
    (directory / 'manifest.json').write_text(json.dumps({'workloads': workloads}, indent=2) + '\n')
    return workloads


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--performance', action='store_true', help='Generate only the two benchmark workloads')
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    if args.performance:
        print(json.dumps({'workloads': len(performance(args.out_dir))}))
    else:
        fixtures, support_files = generate(args.out_dir)
        (args.out_dir / 'manifest.json').write_text(json.dumps({'schema_version': 1, 'fixture_cwd': '.',
                                                              'fixtures': fixtures, 'support_files': support_files}, indent=2) + '\n')
        print(json.dumps({'fixtures': len(fixtures), 'cases': sum(len(item['cases']) for item in fixtures)}))


if __name__ == '__main__':
    main()
