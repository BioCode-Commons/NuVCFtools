# Ordered comparison and lower-memory Perl workers

Follow-up: [smaller comparison queues and counter logs](parallel-memory-20261127.md).

Branch: `codex/common-tool-speed-round2`. Previous Nu: `1e80e428e3fff2ef3fad249e03ce22443b2364f6` (product files match candidate13). Original VCFtools: `1f87a83402ffd17ea2723a456b7edf5d80b4a22c`. Most rows use candidate16; compare uses candidate17 after removing serial counter-dispatch overhead. Both source manifests are retained. Main job 9670442 ran on `node2335.oscar.ccv.brown.edu`.

Each tool comparison ran once per configuration on one Oscar allocation, using up to 16 physical cores. Inputs contain 22,382 real 1000 Genomes chr22 variants and 500 samples (GT-only fields). Compare uses two separately named copies of the same indexed VCF to exercise genotype comparison; it is a different case from the earlier 128-file position-only result. The fill-aa fixture uses GRCh37 as an annotation reference, not an ancestral-allele truth set.

Wall time covers startup, input/decompression, processing, temporary spooling and complete output. BGZF/index preparation and output verification are excluded. RSS/PSS sample the whole process tree every 100 ms, including workers and external readers. They can miss short-lived peaks. RSS counts shared pages repeatedly; PSS apportions shared pages. Neither column is a measurement of Python/Perl object allocation alone.

## Original versus this candidate

New Nu uses 16 workers for stats, merge, annotate and compare; validator and fill-aa remain serial. A worker limit does not imply every core stays busy. Defaults remain one worker.

| Tool / case | Original seconds | Nu seconds | Speedup | RSS MiB, original → Nu | PSS MiB, original → Nu | Full output |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `vcf-stats` | 100.80 | 5.51 | 18.29× | 22.9 → 240.4 | 21.2 → 117.3 | Passed |
| `vcf-merge` | 79.07 | 10.97 | 7.21× | 41.6 → 202.6 | 33.4 → 140.7 | Passed |
| `vcf-annotate` | 28.89 | 1.01 | 28.60× | 16.9 → 223.6 | 11.8 → 77.1 | Passed |
| `vcf-compare` | 84.80 | 12.93 | 6.56× | 42.0 → 443.4 | 34.7 → 248.7 | Passed |
| `vcf-validator` | 78.35 | 16.87 | 4.64× | 21.1 → 22.1 | 12.8 → 12.9 | Passed |
| `fill-aa` | 1.84 | 0.78 | 2.36× | 17.2 → 19.5 | 12.7 → 13.7 | Passed |

## Previous measured implementation versus this candidate

Stats and merge compare the previous branch at 16 workers against candidate16 at 16 workers. Annotate compares previous serial against candidate16 workers. Compare uses its separate follow-up job and compares candidate16 workers against candidate17 workers. Validator and fill-aa compare serial implementations.

| Tool | Previous Nu seconds | New Nu seconds | Previous → new RSS MiB | Previous → new PSS MiB |
| --- | ---: | ---: | ---: | ---: |
| `vcf-stats` | 5.55 | 5.51 | 261.0 → 240.4 | 138.0 → 117.3 |
| `vcf-merge` | 11.44 | 10.97 | 326.7 → 202.6 | 253.3 → 140.7 |
| `vcf-annotate` | 8.61 | 1.01 | 16.9 → 223.6 | 11.9 → 77.1 |
| `vcf-compare` | 13.29 | 12.93 | 441.4 → 443.4 | 246.4 → 248.7 |
| `vcf-validator` | 48.73 | 16.87 | 21.1 → 22.1 | 13.0 → 12.9 |
| `fill-aa` | 0.77 | 0.78 | 16.9 → 19.5 | 12.6 → 13.7 |

The compare follow-up is job 9671590 on `node2335.oscar.ccv.brown.edu`. Its candidate16 serial path measured 98.16 seconds; direct counters in candidate17 measured 73.94 seconds. The earlier candidate16 compare measurements are retained in the JSON. The JSON also retains original, previous serial, previous 16-worker (where available), new serial, new 4-worker and new 16-worker measurements. Speedups include earlier optimizations as well as this round. Single-run differences are not confidence intervals.

## Why parallel RAM increased

Job 9669524 measured the previous candidate before changes. For stats with 4 MiB batches, one worker used 17.0 MiB PSS; the 16-worker setting reached 137.9 MiB PSS and 267.5 MiB RSS. At the PSS peak, 127.9 MiB was private memory across the process tree. Most Perl worker processes held roughly 7–11 MiB private each. Shared-page accounting explains part of the RSS increase; independent process heaps and task state explain a substantial real increase. This run does not separate every allocator/object category or prove absence of a leak.

Changing only the batch target to 256 KiB reduced PSS to 120.8 MiB and measured wall time from 6.36 to 5.49 seconds, while summed RSS rose to 283.6 MiB. The peak had more concurrent processes. This is diagnostic evidence, not a new default: small batches can increase fork/reduction overhead on other tasks.

The final same-job 16-worker stats comparison reduced sampled PSS from 138.0 to 117.3 MiB (15%) and merge from 253.3 to 140.7 MiB (44%). Merge sampled RSS fell from 326.7 to 202.6 MiB (38%). These are measured process-tree peaks, not allocated-object totals. Concrete changes remove per-position copies of merge-reader metadata, serialize counter nodes without another array per leaf, release consumed queue payloads, allocate diagnostic slots only when present, and share equal complete genotype hashes only through the read-only API. Mutable callers keep separate hashes. Interning benefits depend on repeated complete genotype fields; this GT-only case does not establish the same memory reduction for mostly distinct, rich FORMAT data. Batch bytes measure input size, not the expanded Perl heap, and an indivisible record/group may exceed the target. The process model still has independent Perl heaps; this work does not make 16 workers consume single-process RAM.

## The six previously serial commands

| Tool | Result / remaining boundary |
| --- | --- |
| annotate | Ordered workers for record-local operations, including AC/AN/HWE/ICF, normalization and tag removal. Annotation cursors, window filters and user callbacks remain serial and reject `--workers >1`. |
| compare | Ordered position-group workers and integer counter reduction, preserving first insertion order. Grouping, input checks and column inference stay in the parent. Reference-cache sequence comparison (`-R`) remains serial. |
| validator | Record-local sharing and reuse of successful built-in genotype validations. Unknown-field discovery and per-sample error diagnostics retain order. No validator worker path is claimed. |
| fill-aa | Shares immutable FAI length dictionaries across readers of the same file, after each reader’s original first fetch. Sequence chunks and first-query diagnostic state remain independent. The 32-reader test retains one dictionary instead of 32; the single-chromosome benchmark does not quantify a multi-contig RAM saving. |
| concat | Inspected: merge-sort already uses a tournament tree; indexed external readers contribute to memory. No new worker implementation or new performance claim in this round. Splitting its sliding source window is not equivalent to arbitrary global merging. |
| consensus | Inspected: variant overlaps, output case, wrapping and reference offsets share stream state. No new worker implementation or new performance claim in this round. |

There are now 19 of the 23 commands with worker support in at least one mode. Validator, fill-aa, concat and consensus remain serial. This is not a claim that every option combination is parallel.

## Validation and formal limits

Full stdout bytes are compared, retaining order and duplicates. Stderr preserves message content/order/counts; source paths and callsite line numbers are normalized. Generated source-header timestamps use a fixed Perl clock; measured wall clocks are real. All configurations in each retained row must pass before large outputs are removed.

Controls cover 469 ordered-worker cases, 111 remaining-command cases, 30 stats/merge cases at each of 1/4/16 workers, 21 comparison cases at each of 1/4 workers (including 5,460 head combinations per hash seed), 360 validator cases, 72 annotation cases, reference metadata/first-query diagnostics and explicit queue-payload lifetime. These are bounded tests, not a proof for every input.

Seven Z3 checks returned unsat for negated abstract contracts: integer regrouping within a 64-bit nonoverflow bound, first-insertion order, submission bounds, prefix emission, byte concatenation, pure successful-validation reuse, and the three-block candidate-index property. The models are handwritten and are not a verified translation of the Perl code. See [verification scope](../verification/README.md); whole-program formal equivalence has not been established.

## Run history and cleanup

Job 9670116 (candidate14) passed stats, merge and annotate, then stopped because the original compare input lacked a tabix index. Dependent job 9670282 was cancelled without running. Job 9670442 prepared an isolated BGZF/index pair and ran candidate16. Job 9671590 rechecked compare after removing dynamic counter-path construction from the serial hot loop; it repeats the comparison regression controls and measures original, candidate16 and candidate17. No other tool was rerun. The input-preparation failure is not reported as a product failure or an equivalence failure. Raw failure artifacts remain on Oscar; verified large outputs are deleted after comparison. Source inputs are retained.

[Machine-readable results](parallel-state-memory-20261127.json) · [Harnesses and evidence](parallel-state-memory-20261127/) · [Previous 23-command table](parallel-perl-tools.md)
