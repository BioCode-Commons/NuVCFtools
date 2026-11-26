# Background genotype indexing for vcf-contrast

Before: `e03af7b`; candidate implementation: `7fd430b`, branch `codex/contrast-background-index`.

The GT path now accumulates ordered genotype membership, sorted genotype membership and the background allele union once per site. It retains neither per-background allele arrays nor repeated foreground/background comparisons. Ordered membership preserves the original asymmetric allele sorting. Missing backgrounds and foregrounds retain their original exclusion rules; PL calculations retain their existing algorithm.

For fixed ploidy, GT comparison work changes from O(records × foreground × background) to expected O(records × (foreground + background)) with Perl hashes. This is expected hash complexity, not a worst-case bound. Storage follows distinct background genotypes and alleles; overall process RSS did not materially change in this experiment.

## End-to-end measurements

Local Apple M1, arm64, one Perl process, uncompressed synthetic VCF; 300 records per size. Both revisions run through the complete CLI including startup, parsing and output. Three repetitions per revision; table shows medians. Wall time is measured around the process; maximum process RSS is from macOS `/usr/bin/time -l`, converted from bytes to MiB. Includes no index preparation. These are scaling examples, not representative WGS measurements or speedups over upstream VCFtools. Oscar was unavailable because its SSH control session had expired.

All background samples are 0/0 and foreground samples 2/2 in these scaling examples, exercising the complete nonmatching comparison. These genotype values are fixture data, not implementation conditions. The experiment demonstrates removal of the Cartesian comparison; mixed GT/PL inputs are covered by differential testing.

| Foreground + background | Before wall (s) | Candidate wall (s) | Speedup | Before RSS (MiB) | Candidate RSS (MiB) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 16 + 16 | 0.0950 | 0.0487 | 1.95× | 10.203 | 10.156 |
| 64 + 64 | 0.8842 | 0.1190 | 7.43× | 10.281 | 10.297 |
| 128 + 128 | 3.2516 | 0.2091 | 15.55× | 10.406 | 10.328 |

## Differential testing

40 CLI comparisons passed: five reproducible generator seeds, 400 records each (2,000 generated records), four flag combinations and two hash seeds. Cases include missing and partially missing GTs, phased and unphased calls, haploid/diploid/polyploid calls, FORMAT reordering, PL-bearing records, FILTER exclusion, novelty-only output and minimum depth. The benchmark's 18 process runs also passed output comparison.

The test compares stdout bytes after removing only the generated `##source=` provenance line. It retains record order, INFO order and sample-list order. Exit codes and stderr agree after removing timing telemetry and normalizing only source path/line locations. Random PL cases produce existing numeric warnings for missing likelihoods in both revisions; this change does not repair those warnings. No new mismatch or process failure was found. This is deterministic randomized differential testing, not coverage-guided libFuzzer or an ASan memory-safety campaign (the changed code is Perl).

Reproduce on macOS:

```sh
python3 tests/contrast_differential.py --before /path/to/before --after /path/to/candidate --output /tmp/contrast-results
```

Generated VCF fixtures are deleted after successful comparisons. Machine-readable measurements: [results.json](contrast-background-index-20261126/results.json).

## Next priorities

Usage ranking is a working assumption; this repository has no user telemetry. Filtering/subsetting, summaries, merge/query and intersections are broader workflow candidates than specialist haplotype or pedigree functions. Prioritize measured end-to-end time and RSS over loop counts.

1. Multi-input intersection: stable minimum-head heap; preserve ties, clusters, chromosome resets and split-output behavior. Expect improvement as file count grows.
2. Interval annotation: ordered interval reporting with original record order; avoid repeatedly scanning large overlap groups. Match emission itself remains proportional to hits.
3. fill-fs: persistent mask readers and active intervals instead of a tabix process per variant/mask. Measure child processes as well as the Perl process.
4. Shared parsing: request only fields used by the command, with a bounded lifetime. Focus on allocation/RSS and byte scans; do not claim asymptotic savings where full output requires reading every field.
5. Thread orchestration: introduce bounded work queues only after a measured parallel section is identified. Preserve order and include all workers in memory accounting.

Fst range updates are lower priority for strict byte equivalence: changing floating-point accumulation order can change printed results. PCA and pairwise relatedness also contain work required by their requested outputs; nested loops alone do not demonstrate avoidable complexity.
