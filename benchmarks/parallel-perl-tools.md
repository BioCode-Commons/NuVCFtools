# Ordered Perl workers and data-layout results

This is the earlier 17-worker-command snapshot. See the [follow-up measurements](parallel-state-memory-20261127.md) for newer stats/merge memory figures, annotate/compare workers and validator/fill-aa changes. The tables below retain their original measured versions and cases.

Branch: `codex/common-tool-speed-round2`. Upstream VCFtools: `1f87a83402ffd17ea2723a456b7edf5d80b4a22c`; pre-pool Nu: `92c7721ec154339aed5638b2142a39e49fa54f56`. The source snapshots and Slurm jobs are listed below. These are successive development snapshots, **not a rerun of all tools at one final commit**.

The scope is the 23 Perl commands that previously lacked a computation worker pool. Seventeen now accept ordered workers; six remain serial. The C++ executable and `vcf-sort` are outside this count and retain their [previous measurements](all-tools-vs-upstream.md).

Each row uses its own original-versus-candidate comparison on the same allocated Oscar node, once per setting. Original and pre-pool Nu use one physical core. Worker settings use up to 4 or 16 physical cores (`--hint=nomultithread`, taskset affinity). They are process limits, not a claim that every task keeps that many cores busy. Inputs are real 1000 Genomes chr22 records, normally 22,382 variants, with the sample selections below. They are not whole-genome or all-FORMAT benchmarks.

Wall time includes tool startup, reading/decompression, analysis, worker output spooling and complete final output writing. Dataset/index preparation and output comparison are outside that timer. Peak process-tree RSS and PSS are sampled every 100 ms, including workers and external readers; sampling can miss a short-lived peak. Summed RSS counts shared pages more than once. PSS apportions those pages. GNU time maximum single-process RSS is retained in the JSON but is not substituted for worker-inclusive memory.

## Original versus measured Nu

Nu uses the 16-worker measurement where available, otherwise its serial measurement. This rule includes regressions; the table does not select the fastest repetition or multiply speedups from separate rounds.

| Tool / input | Original s | Nu s | Max workers | Speedup | Tree RSS MiB, original → Nu | Nu tree PSS MiB | Full output |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `fill-aa` — GRCh37 annotation fixture, 500 samples | 1.85 | 0.80 | 1 | 2.31× | 19.88 → 17.25 | 12.46 | Passed |
| `fill-an-ac` — 500 samples | 30.73 | 3.27 | 16 | 9.40× | 15.38 → 205.54 | 83.47 | Passed |
| `fill-fs` — 2,000 variants / 500 samples, VCF mask, 64 KiB batches | 29.46 | 2.52 | 16 | 11.69× | 27.27 → 221.56 | 38.12 | Passed |
| `fill-ref-md5` — chr22, one uncached contig | 3.05 | 0.83 | 16 | 3.67× | 67.94 → 78.73 | 63.46 | Passed |
| `vcf-annotate` — HWE, 500 samples | 29.03 | 8.70 | 1 | 3.34× | 16.88 → 16.50 | 12.04 | Passed |
| `vcf-compare` — 128 interleaved files / 100 samples | 11.71 | 8.37 | 1 | 1.40× | 606.00 → 611.64 | 180.51 | Passed |
| `vcf-concat` — merge-sort 128 files / 100 samples | 11.67 | 5.16 | 1 | 2.26× | 708.00 → 646.12 | 180.96 | Passed |
| `vcf-consensus` — 1 Mbp unwrapped FASTA fragment | 0.93 | 0.92 | 1 | 1.01× | 31.88 → 31.88 | 25.76 | Passed |
| `vcf-contrast` — 100 samples, 10 foreground / 90 background | 24.81 | 2.75 | 16 | 9.02× | 13.12 → 73.48 | 40.64 | Passed |
| `vcf-convert` — biallelic SNPs, 500 samples | 37.66 | 3.63 | 16 | 10.37× | 16.88 → 200.07 | 80.39 | Passed |
| `vcf-fix-newlines` — CRLF input, 500 samples | 0.09 | 0.20 | 16 | 0.45× | not captured → 15.75 | 13.09 | Passed |
| `vcf-fix-ploidy` — active chr22 haploid conversion, 500 samples | 43.33 | 4.24 | 16 | 10.22× | 16.12 → 215.50 | 81.84 | Passed |
| `vcf-indel-stats` — 500 samples, explicit coordinate interval | 0.32 | 0.35 | 16 | 0.91× | 15.38 → 19.50 | 14.94 | Passed |
| `vcf-isec` — two interleaved files / 100 samples | 0.64 | 0.83 | 16 | 0.77× | 31.12 → 52.12 | 43.58 | Passed |
| `vcf-merge` — two sample partitions, 500 total samples | 94.00 | 13.15 | 16 | 7.15× | 41.62 → 328.15 | 253.56 | Passed |
| `vcf-phased-join` — overlapping chr22 blocks, 500 samples | 7.30 | 6.45 | 16 | 1.13× | 80.62 → 140.26 | 78.53 | Passed |
| `vcf-query` — default sample + GT output, 2,504 samples | 258.27 | 6.75 | 16 | 38.26× | 15.38 → 295.54 | 117.92 | Passed |
| `vcf-shuffle-cols` — reverse 2,504 sample columns | 12.97 | 1.34 | 16 | 9.68× | 14.25 → 208.86 | 71.42 | Passed |
| `vcf-stats` — 500 samples | 120.62 | 6.37 | 16 | 18.94× | 15.00 → 263.39 | 141.19 | Passed |
| `vcf-subset` — 500 → 250 samples | 62.37 | 3.31 | 16 | 18.84× | 13.50 → 207.62 | 83.14 | Passed |
| `vcf-to-tab` — 2,504 samples | 216.13 | 7.82 | 16 | 27.64× | 16.88 → 215.81 | 87.75 | Passed |
| `vcf-tstv` — 2,504 samples | 0.82 | 0.91 | 16 | 0.90× | 10.88 → 31.38 | 15.51 | Passed |
| `vcf-validator` — unique-message mode, 500 samples | 92.53 | 56.98 | 1 | 1.62× | 21.43 → 21.13 | 12.95 | Passed |

23/23 tools have a completed direct upstream comparison in this round; 11 selected settings reach 4× and 0 reach 100×. These counts apply only to the listed inputs and options.

`fill-aa` uses real GRCh37 reference sequence as a software annotation fixture, not an ancestral-allele truth set. The indel interval is an explicit analysis region, not an exon annotation. The MD5 input has only one contig, so it cannot demonstrate multi-contig parallel scaling. Subsecond changes are not reliable evidence of a speedup.

## Separating earlier changes from worker gains

All columns below are from the same row/job. “Before” is the one-core pre-pool Nu version; blank worker columns mean that command remains serial.

| Tool | Before s | Nu 1 worker s | Nu 4 workers s | Nu 16 workers s | Job / snapshot |
| --- | ---: | ---: | ---: | ---: | --- |
| `fill-aa` | 0.80 | 0.80 | — | — | 9664175 / candidate11 |
| `fill-an-ac` | 22.06 | 24.00 | 6.63 | 3.27 | 9663857 / candidate9 |
| `fill-fs` | 29.28 | 29.75 | 7.89 | 2.52 | 9664325 / candidate11 |
| `fill-ref-md5` | 0.84 | 0.88 | 0.87 | 0.83 | 9663274 / candidate3 |
| `vcf-annotate` | 29.18 | 8.70 | — | — | 9664175 / candidate11 |
| `vcf-compare` | 11.43 | 8.37 | — | — | 9664074 / candidate10 |
| `vcf-concat` | 5.22 | 5.16 | — | — | 9664175 / candidate11 |
| `vcf-consensus` | 0.93 | 0.92 | — | — | 9663765 / candidate8 |
| `vcf-contrast` | 7.32 | 7.67 | 2.76 | 2.75 | 9664175 / candidate11 |
| `vcf-convert` | 25.68 | 27.34 | 7.48 | 3.63 | 9664350 / candidate13 |
| `vcf-fix-newlines` | 0.09 | 0.16 | 0.20 | 0.20 | 9663274 / candidate3 |
| `vcf-fix-ploidy` | 43.36 | 42.71 | 12.07 | 4.24 | 9664175 / candidate11 |
| `vcf-indel-stats` | 0.32 | 0.50 | 0.30 | 0.35 | 9664175 / candidate11 |
| `vcf-isec` | 0.73 | 0.93 | 0.84 | 0.83 | 9663765 / candidate8 |
| `vcf-merge` | 48.81 | 52.02 | 15.93 | 13.15 | 9664074 / candidate10 |
| `vcf-phased-join` | 6.45 | 6.58 | 6.44 | 6.45 | 9664074 / candidate10 |
| `vcf-query` | 84.94 | 85.15 | 22.52 | 6.75 | 9663274 / candidate3 |
| `vcf-shuffle-cols` | 11.35 | 11.25 | 3.12 | 1.34 | 9663274 / candidate3 |
| `vcf-stats` | 27.31 | 31.78 | 15.41 | 6.37 | 9664350 / candidate13 |
| `vcf-subset` | 22.01 | 23.70 | 6.64 | 3.31 | 9664175 / candidate11 |
| `vcf-to-tab` | 66.14 | 74.77 | 19.48 | 7.82 | 9663857 / candidate9 |
| `vcf-tstv` | 0.81 | 0.91 | 0.87 | 0.91 | 9663274 / candidate3 |
| `vcf-validator` | 55.97 | 56.98 | — | — | 9663765 / candidate8 |

## What changed

- The worker engine limits in-flight batches, replays stdout/stderr in input order, reduces integer counts in that same order, and removes consumed temporary files. It forks per batch; this has measurable cost for short commands. `--workers` defaults to 1 and `--worker-batch-bytes` to 4,194,304. A single record/group may exceed that byte target, so it is not a strict RAM cap.
- Prepared input queues store tab-delimited bytes instead of a Perl scalar for every sample. Merge queues use a per-record dictionary of complete decoded genotype fields plus variable-length encoded column/dictionary indexes; mutable sample hashes are expanded only for the current output position.
- Statistics workers record first-key insertion order separately from integer counters. The parent replays that order before adding values, preserving the legacy unsorted dump. Phase scoring keeps per-site floating-point addition order in the parent.
- Multi-file comparison uses an ordered tournament: source-head selection changes from a scan over K files to an O(log K) update. Exact sequence intersections use full-string hash keys scoped to a group; file ties and the legacy pairwise-intersection condition are retained.
- HWE stores only reachable parity states. Annotation reuses pure genotype parsing for identical complete sample fields within one record; sample counting remains in original order. Malformed absent fields retain per-sample diagnostics.
- Unique validator messages use three disjoint token-block indexes to find candidates within two token differences, then perform the original full comparison in insertion order. This preserves the greedy grouping rule; skewed blocks can still produce a linear candidate scan. The clean-input run does not demonstrate a new speedup from this index.
- Consensus advances an output cursor before removing the emitted prefix. The measured 0.93 versus 0.92 seconds provides no useful end-to-end speedup evidence; this is not reported as an asymptotic claim about Perl string deletion.

## Worker coverage and remaining work

Ordered workers are available for: `fill-an-ac`, `fill-fs`, `fill-ref-md5`, `vcf-contrast`, `vcf-convert`, `vcf-fix-newlines`, `vcf-fix-ploidy`, `vcf-indel-stats`, `vcf-isec`, `vcf-merge`, `vcf-phased-join`, `vcf-query`, `vcf-shuffle-cols`, `vcf-stats`, `vcf-subset`, `vcf-to-tab`, `vcf-tstv`.

`vcf-query --use-old-method` and `vcf-isec --split` reject worker counts above one. MD5 parallelizes missing contigs; phased-join parallelizes overlap scoring, not split/randomization mode. These are not claims that every mode of a command is parallel.

| Still serial | Current work / remaining constraint |
| --- | --- |
| `vcf-annotate` | Genotype parse reuse and HWE layout measured. Annotation cursors, user filters and window filters still share ordered state. |
| `vcf-compare` | Source selection and sequence intersections improved. Genotype/statistics reduction remains serial. |
| `vcf-validator` | Message candidate index added; header discovery, duplicate/sorted warnings and custom field handlers need ordered state. |
| `vcf-consensus` | Output-buffer change measured without material gain. Variant overlap handling, sequence case and wrapping remain stateful. |
| `vcf-concat` | Existing ordered source-head tree retained and now compared directly with upstream. Ordered decompression/copy remains serial at the Perl layer. |
| `fill-aa` | Reference cache and diagnostic behavior retained. A previous naive worker-cache partition changed warning multiplicity and was removed. |

## Scheduling and memory trials

The default 4 MiB batch produced no fill-fs acceleration on the 2,000-record mask task (29.92 s original, 30.86 s with 16 workers). With an explicit 64 KiB batch, job 9664325 compared 29.46 s original against 2.52 s with 16 workers, with full output equality. This is the setting in the main table; the default is unchanged.

Earlier object-heavy queues had sampled 16-worker RSS of 1,016 MiB for to-tab, 1,153 MiB for fill-an-ac, 1,196 MiB for merge and 1,204 MiB for stats. Packed queues/indices reduced them substantially; use the final rows above. Those memory comparisons span separate jobs and are not paired timing replicates. Worker-inclusive memory is still higher than the original one-core process in most parallel rows.

## Validation and provenance

“Passed” requires actual complete output byte comparison, preserving order and duplicates; hashes alone are not used for equivalence. Diagnostics retain content/order/counts with installation paths and changed callsite line numbers normalized where documented by the harness. The MD5 case compares decompressed VCF bytes, full header and dictionary rather than gzip-container bytes. A fixed Perl clock equalizes generated source timestamps in job 9664175; measured wall clocks remain real.

Deterministic controls cover rich FORMAT fields, VCF version/case handling, empty and unterminated records, trailing tabs, haploid/polyploid and malformed genotypes, partial output on errors, interval/window boundaries, multiple hash seeds, worker ordering and cleanup. Suites include 469 ordered-worker cases, 111 remaining-tool controls, 30 stats/merge cases at each of 1/4/16 workers, 81 stateful cases, 72 annotation cases, 3,380 bitwise HWE results, 60 FASTA flush states, 5,460 source-head combinations per hash seed, and 5,491 validator-message inputs per hash seed. These are bounded compatibility tests, not a proof for all inputs and not a new fuzzing campaign.

Job 9663136 failed a diagnostic callsite comparison before recording benchmark timings. The harness was corrected to distinguish source location from error content, then subsequent runs validated partial output and exit codes. Job 9663374 completed merge but stopped because its isec fixture had incompatible sample columns; the replacement uses interleaved shards with matching columns. Superseded trial outputs are not substituted for newer measurements.

Large per-case outputs are removed only after all requested variants pass byte comparison. Failure outputs remain available on Oscar. Reusable input/index files are retained. The JSON companion contains job/node identities, source manifests, resource settings, all five measurements where applicable, and cleanup byte counts.

[Machine-readable results](parallel-perl-tools.json) · [Harnesses and source manifests](parallel-perl-tools/)
