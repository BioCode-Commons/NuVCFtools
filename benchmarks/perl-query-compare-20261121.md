# Perl query and compare benchmark

Oscar, November 21, 2026. Final code at `54ee384e01a28f067de7160d617c2df7cec56dfe`; previous NuVCFtools at `be50ce72d8ec05894317e385d9fd6d7802f18d70`; original VCFtools at `1f87a83402ffd17ea2723a456b7edf5d80b4a22c`.

`vcf-query` copies its output template directly, reuses repeated FORMAT field extraction within each record, and writes one assembled string per record rather than one print per sample. `vcf-compare` reuses parsed genotype signatures, allele sorting and variant classification within each locus. All caches end at that locus. The source has no data-set-specific rule or thread pool.

## Running time

Seconds. Each version/configuration ran once, sequentially on the same Oscar node and physical core. GNU time measured startup through completion, including read/decompression, compute, and output. Preparation, input indexing, regression checks and output comparison were excluded.

| Tool | Samples | Original (s) | Before (s) | After (s) | Speedup vs original | Speedup vs before | Full output comparison |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `vcf-query` | 100 | 6.79 | 6.81 | 3.71 | 1.83× | 1.84× | Passed |
| `vcf-compare` | 100 | 9.13 | 9.15 | 7.85 | 1.16× | 1.17× | Passed |
| `vcf-query` | 400 | 27.70 | 27.68 | 15.16 | 1.83× | 1.83× | Passed |
| `vcf-compare` | 400 | 34.85 | 35.14 | 29.43 | 1.18× | 1.19× | Passed |

## Peak RSS

MiB; GNU time maximum RSS, not summed process-tree RAM.

| Tool | Samples | Original (MiB) | Before (MiB) | After (MiB) |
| --- | ---: | ---: | ---: | ---: |
| `vcf-query` | 100 | 10.50 | 10.50 | 10.50 |
| `vcf-compare` | 100 | 14.62 | 14.25 | 14.25 |
| `vcf-query` | 400 | 10.88 | 10.88 | 10.88 |
| `vcf-compare` | 400 | 14.62 | 14.62 | 14.62 |

## Input and validation

- [1000 Genomes Phase 3 chromosome 22 VCF](https://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/ALL.chr22.phase3_shapeit2_mvncall_integrated_v5b.20130502.genotypes.vcf.gz), GRCh37 `22:20000001-21000000`, 22,382 records. The first 100 or 400 header samples were selected. `query` used `%CHROM\t%POS[\t%SAMPLE=%GTR]\n`; `compare` used `-g` with a second indexed file retaining alternating real records.
- Source SHA-256 `a90c16c4ff2b3196476d506ae13cb3047fae8670163c7c932c4b0239aef3daf5`. Prepared file hashes are in [inputs.json](perl-query-compare-20261121/inputs.json). The real-data FORMAT is GT only; rich FORMAT behavior was checked separately.
- Final job `9466305` ran on `node1829.oscar.ccv.brown.edu` with CPU affinity `[26]`. Version order rotated across cases. One run per version and configuration; no confidence interval is available.
- All four final cases passed byte-for-byte comparison of **complete stdout and stderr** against both Original and Before. No normalization. All commands exited successfully and candidate file identities were checked before and after timing. `PERL_HASH_SEED=0` and `PERL_PERTURB_KEYS=0` held legacy hash order constant.
- [Regression details](perl-query-compare-20261121/regression.json): 16 synthetic three-version comparisons across two hash seeds. Cases cover basic and rich query fields, selected samples, plain VCF, genotype comparison, sample subset, filters and position-only comparison. Fixture includes multiple ALT alleles, different REF lengths, missing and phased genotypes, and DP/AD/FA/PL fields. These checks do not prove equivalence for every input.

An earlier exploratory candidate (`0892c8e`, job `9465537`) cached only the sorted allele lists and made `compare` slower. Its measured data are retained separately, and it is not used in the final speedup table. A second candidate (`0c9b776`, job `9465789`) also cached repeated genotype parsing and improved both tools. The final candidate adds per-record FORMAT field reuse in `query`. Comparisons between these two jobs should not be treated as paired replicates.

The final input preparation job was `9466304`. Verified large inputs and outputs were deleted after comparison; hashes and timing metadata remain. This report is branch-local and does not update the website's published benchmark data.
