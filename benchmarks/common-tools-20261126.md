# Common-tool benchmark: statistics and relatedness

Measured on Oscar on November 26, 2026. All commands use **one physical core**. Each comparison round uses one run per version; these measurements have no repetition-based uncertainty estimate. Input reading/decompression, analysis and complete output writing are included. Input preparation, compilation and output comparison are excluded.

All retained implementations share `codex/common-tool-speed-round2`. Main and the website's published data are unchanged.

## Wall time

| Command | Input samples | Original (s) | Before (s) | After (s) | Speedup vs original | Speedup vs before |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `vcf-stats` | 500 | 100.92 | 38.87 | 23.32 | 4.33× | 1.67× |
| `vcf-stats` | 2504 | 658.31 | 251.54 | 141.03 | 4.67× | 1.78× |
| `vcftools --relatedness2` | 500 | 35.09 | 14.27 | 1.37 | 25.61× | 10.42× |
| `vcftools --relatedness2` | 2,504 → keep 500 | 59.19 | 37.53 | 3.06 | 19.34× | 12.26× |
| `vcftools --relatedness` | 500 | 5.81 | 3.98 | 3.19 | 1.82× | 1.25× |
| `vcftools --relatedness` | 2,504 → keep 500 | 16.74 | 18.78 | 5.04 | 3.32× | 3.73× |

## Peak RSS

MiB, from GNU time maximum RSS divided by 1,024. For Perl, this is the maximum accounted process/child RSS rather than the sum of concurrent processes. There are no analysis workers in these runs.

| Command | Input samples | Original (MiB) | Before (MiB) | After (MiB) |
| --- | ---: | ---: | ---: | ---: |
| `vcf-stats` | 500 | 26.250 | 26.250 | 26.625 |
| `vcf-stats` | 2504 | 88.621 | 89.016 | 88.422 |
| `vcftools --relatedness2` | 500 | 11.250 | 7.125 | 7.125 |
| `vcftools --relatedness2` | 2,504 → keep 500 | 149.250 | 53.625 | 7.500 |
| `vcftools --relatedness` | 500 | 9.000 | 7.125 | 7.125 |
| `vcftools --relatedness` | 2,504 → keep 500 | 101.625 | 53.625 | 7.500 |

The large relatedness memory reduction applies to sample selection: both matrices now contain only the 500 retained individuals. The unfiltered 500-sample runs have essentially unchanged RSS relative to Before. Statistics improved in running time; these measurements do not demonstrate a substantial statistics-memory reduction.

## Input and versions

The input contains 22,382 actual [1000 Genomes Phase 3 chromosome 22](https://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/ALL.chr22.phase3_shapeit2_mvncall_integrated_v5b.20130502.genotypes.vcf.gz) records from GRCh37 `22:20000001-21000000`. The 500-sample file is a previously prepared subset of the 2,504-sample file. The selected relatedness case reads the full 2,504-sample input and applies `--keep` to those same 500 names. These authentic inputs contain GT-only FORMAT data; richer FORMAT fields are covered by functional checks, not these performance numbers. No duplicated variants or invented genotypes were used for timings.

- Original: upstream `1f87a83402ffd17ea2723a456b7edf5d80b4a22c`.
- Before source: `8de55035d2ea81db4bfa36e35903374b73f85d5f`. Its C++ source and configuration match the frozen `3ce1fa053bdfefcca858a48bc0eceeca397b419e` binary used here; source equality was checked.
- Relatedness2 change: `427af1b`.
- Yang relatedness change: `ac01e43`.
- Statistics group reuse: `b4bff75`; read-only parser change is recorded in this report's accompanying validation manifest.

Candidate native builds used GCC 11.5 and `CXXFLAGS=-O2`, retaining the compiler's native language mode. Binary SHA256, input SHA256, nodes, flags, exit codes, user/system CPU time and output sizes are in the JSON evidence. Perl hash ordering was fixed with `PERL_HASH_SEED=0` and `PERL_PERTURB_KEYS=0` for timed comparisons.

`--relatedness2` ran on node1830 (job 9656126); `--relatedness` ran on node1831 (9656192). Statistics ran on node1829: the first three-version job (9655803) tested group reuse, and the second (9656034) compared the same frozen Before against group reuse plus read-only parsing. The statistics Original column comes from the first job; the final Before/After columns come from the second. Each statistics job compared actual full output bytes; the unchanged Before establishes the equality chain to Original. This is not a fresh simultaneous Original/Before/final-After triplet.

## Changes

`--relatedness2` batches one machine word of accepted sites into per-individual heterozygous/homozygous masks. Bit-sliced homozygous allele IDs distinguish any nonnegative IDs without a hardcoded 0/1 assumption. Population counts replace the inner per-site pair loop. Temporary genotype memory is bounded independently of site count. Missing-call handling, accepted-site filtering, output order and the final formula are preserved.

Both relatedness estimators use compact indices for retained individuals. Yang's per-pair arithmetic and per-site floating-point accumulation order are unchanged. File output is buffered; standard output retains the original row-flush behavior.

`vcf-stats` reuses its existing genotype groups for shared/private and sample-counter updates, tracking sample multiplicity separately from filtered statistic destinations. Its CLI opts into `next_data_hash_readonly`: equal neighboring complete FORMAT strings can share a genotype hash within one record. Reuse keeps only the previous genotype and ends at the record boundary. Ordinary `next_data_hash` still returns independent mutable sample hashes. Consumers of the read-only method must not mutate its genotype hashes.

The first statistics change alone measured 29.06 seconds for 500 samples and 182.22 seconds for 2,504 samples. Those intermediate results are retained separately from the final parser measurements.

## Validation and cleanup

All reported scientific outputs passed full byte comparison, including row order and floating-point text. Native stderr was compared after normalizing only the executable version, output prefix and runtime line; log files were not treated as scientific output. Statistics stdout and stderr were compared without normalization.

Each native estimator passed six three-version controls (mixed genotypes, sample selection, genotype/site filtering, standard output, empty input and BCF) plus the two real-data comparisons: 24 successful process invocations per estimator. The relatedness block unit test compares scalar and packed counts around word boundaries, missing/partial calls, arbitrary homozygous allele IDs and the original double counter's precision limit. Both native builds passed `make check`.

Final statistics passed 30 existing CLI/API regression comparisons across three Perl hash seeds and 47 deterministic read-only parser assertions. The parser checks cover independent mutable records, sharing lifetime, sample selection, duplicate FORMAT tags, absent GT and malformed field counts/diagnostics. These checks do not establish equivalence for all possible inputs or external Perl API extensions. No fuzzing was run for this continuation.

Verified large outputs were removed after comparison. Inputs, frozen binaries, aggregate evidence and replay scripts remain. The scripts below record the Oscar job layout under `/jobtmp/zliu328/nuvcftools-common-tools-20261126`; they do not download new data.

- [Statistics final measurements](common-tools-20261126/stats-readonly.json), [intermediate measurements](common-tools-20261126/stats-groups.json)
- [Relatedness2 measurements](common-tools-20261126/relatedness2.json), [Yang measurements](common-tools-20261126/relatedness.json)
- [Validation manifest](common-tools-20261126/validation.json)
- Harnesses: [statistics](common-tools-20261126/stats-readonly.py), [statistics first step](common-tools-20261126/stats-groups.py), [relatedness2](common-tools-20261126/relatedness2.py), [Yang](common-tools-20261126/relatedness.py)
