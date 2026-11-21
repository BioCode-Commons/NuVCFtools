# Perl stats and merge benchmark

Measured on Oscar, November 21, 2026. Each command/configuration ran once per version, sequentially on the same node and physical core. These are end-to-end measurements, without profiling.

## Versions and changes

| Version | Commit |
| --- | --- |
| Original VCFtools | `1f87a83402ffd17ea2723a456b7edf5d80b4a22c` |
| NuVCFtools before this change | `c8f6c1288d7e40ceea9a24ef8f4835dcac264dfa` |
| NuVCFtools with this change | `6bec44c1c77e4df65342521dfd95f65af2e58ae0` |

`vcf-stats` groups identical genotypes within each record, calculates their allele contributions once, and applies them to each sample's statistics and filter groups. It also reuses genotype-level classification for shared/private counts. `vcf-merge` reuses genotype conversions within each source record and output record. AC/AN calculation counts genotype multiplicities before splitting their allele strings, preserving first-seen order and the existing first-two-alleles behavior.

All reuse ends at the current record. There are no sample-name, chromosome, dataset, allele-count or genotype-frequency thresholds. Speedup depends on how much genotype work is repeated; parsing, per-sample updates and output formatting remain. This change does not add threading.

## Running time

Seconds; preparation, indexing, correctness checks and output comparison are excluded. Startup, input reading/decompression, computation and output writing are included.

| Tool | Samples | Original (s) | Before (s) | After (s) | Speedup vs original | Speedup vs before | Full output comparison |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `vcf-stats` | 100 | 23.99 | 23.99 | 10.13 | 2.37× | 2.37× | Passed |
| `vcf-merge` | 100 | 21.33 | 21.26 | 12.82 | 1.66× | 1.66× | Passed |
| `vcf-stats` | 400 | 96.45 | 96.34 | 37.46 | 2.57× | 2.57× | Passed |
| `vcf-merge` | 400 | 76.45 | 76.11 | 41.36 | 1.85× | 1.84× | Passed |

## Peak RSS

MiB (GNU time maximum RSS divided by 1024). This includes child-process maxima accounted by GNU time; it is not a measurement of the sum of simultaneously resident processes. Small differences in these single measurements should not be interpreted as a memory optimization.

| Tool | Samples | Original (MiB) | Before (MiB) | After (MiB) |
| --- | ---: | ---: | ---: | ---: |
| `vcf-stats` | 100 | 13.500 | 13.875 | 13.500 |
| `vcf-merge` | 100 | 12.000 | 12.000 | 12.000 |
| `vcf-stats` | 400 | 22.875 | 24.000 | 23.250 |
| `vcf-merge` | 400 | 14.625 | 14.625 | 14.625 |

## Input and execution

- [1000 Genomes Phase 3 chromosome 22 VCF](https://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/ALL.chr22.phase3_shapeit2_mvncall_integrated_v5b.20130502.genotypes.vcf.gz), GRCh37 region `22:20000001-21000000`: 22,382 records, including 127 multiallelic records. The first 100 or 400 samples in header order were selected without changing genotypes. Merge joins two files containing disjoint halves of those samples.
- Source SHA-256: `a90c16c4ff2b3196476d506ae13cb3047fae8670163c7c932c4b0239aef3daf5`. Prepared input hashes are in [inputs.json](perl-stats-merge-20261121/inputs.json).
- Node `node1827.oscar.ccv.brown.edu`, Intel Xeon Platinum 8268 @ 2.90 GHz, one physical CPU (affinity `[3]`), Perl 5.40.0. Version order rotates across the four cases; there are no repeats or uncertainty estimates.
- Commands: `vcf-stats cohortN.vcf.gz` and `vcf-merge AN.vcf.gz BN.vcf.gz`, invoked through the same Perl runtime. Standard output goes to a regular file. Input compression and tabix indexing occur before measurement.
- Separate input preparation job: `9465132`, 287.96 seconds. Benchmark job: `9465327`. GNU time records wall time, user/system CPU time and peak RSS; raw measurements are in [summary.json](perl-stats-merge-20261121/summary.json).

This real-data input uses `FORMAT=GT`. The measured speedups apply to these tasks and inputs; richer FORMAT data were covered by correctness checks, not by these performance measurements.

## Validation

All four measured cases passed complete byte-for-byte comparison of both stdout and stderr against **both** Original and Before, including every output record, header, field order and numeric representation. No fields were stripped, sorted or normalized for comparison. `PERL_HASH_SEED=0` and `PERL_PERTURB_KEYS=0` were fixed because legacy output order follows Perl hash iteration. All processes exited successfully. Source identities were checked before and after the run.

The committed [regression runner](../tests/perl_stats_merge_regression.py) passed 60 final-source differential checks: ten cases, three hash seeds, and two reference versions. It covers missing and partial genotypes, phasing, haploid calls, multiple ALT alleles, differing REF lengths, sample selection, statistics filters, trim/missing/collapse merge options, sample-free VCFs, FORMAT DP/AD/FA/PL with Number R/A/G, and direct AC/AN and genotype-conversion API checks. The API probe includes leading-zero allele indices and preserves the legacy AC/AN handling of polyploid strings. These checks do not establish equivalence for every possible input or Perl API extension.

The unchanged upstream 75-test Perl suite returned **68/75 for both Before and After**, with the same failures: 14, 19, 25, 26, 27, 32 and 33. Six assertions first differ from old golden files in hash-dependent output ordering; direct three-version comparisons of those commands passed on all stdout/stderr bytes. Test 33 uses `do "fix-ploidy.txt"`; current Perl omits `.` from `@INC`, so the legacy test does not load its configuration. Repeating that command with the explicit `./fix-ploidy.txt` path produced identical complete outputs in all three versions. The product and upstream test were not changed to hide these failures.

Verified benchmark outputs and large prepared inputs were deleted after comparison. Checksums, timings, regression evidence and the frozen versions were retained. Main and the website's published benchmark data were not changed.
