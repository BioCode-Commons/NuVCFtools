# Smaller comparison queues and counter logs

Job **9686952**, node `node1907.oscar.ccv.brown.edu`. Retained product source: **candidate19**, identified by [SHA256 manifest](parallel-memory-20261127/candidate19-sha256.json). Before: `08629211e5d02f34b213f669d7192547b9ec6137` (candidate17). Original VCFtools: `1f87a83402ffd17ea2723a456b7edf5d80b4a22c`. All work stays on `codex/common-tool-speed-round2`.

## Retained results

Each setting ran once in the same allocation. Nu uses 16 workers; original is serial. Defaults remain one worker and a 4 MiB batch. The 500-sample 1000 Genomes chr22 input is real GT-only data. Compare uses two separately named copies of the same indexed input. Results do not establish performance for every FORMAT distribution or option.

| Tool | Original s | Before Nu s | Retained Nu s | Original / retained | RSS MiB, original → before → retained | PSS MiB, original → before → retained | Full output |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| vcf-compare | 102.38 | 15.32 | 15.37 | 6.66× | 42.4 → 441.3 → 371.0 | 34.6 → 246.3 → 175.6 | Byte-identical |
| vcf-stats | 119.82 | 6.40 | 6.18 | 19.39× | 15.4 → 239.6 → 224.5 | 12.3 → 115.2 → 98.5 | Byte-identical |

Compare PSS fell 28.7%; stats PSS fell 14.5%. Compare time was effectively unchanged (15.32→15.37 s); stats changed from 6.40→6.18 s. Single runs cannot establish a small speed gain. Parallel execution still uses more memory than the serial original.

Wall time includes input reading/decompression, computation, process startup/spooling and complete output writing. Input/index preparation and output validation are excluded. RSS and PSS sample the whole process tree, including readers and workers, every 100 ms; short peaks can be missed. Summed RSS double-counts shared pages; PSS apportions them.

## What changed

- `vcf-compare` releases the raw line after prepared text and diagnostics take ownership. It retains original input-byte counts, preserving batch boundaries, INDEL early-stop behavior and error ordering.
- `NuOrderedCounters` replaces one three-element Perl array per insertion event with two packed native unsigned integer indices and a separate key array. Keys preserve byte/Unicode flags and embedded NULs. Node 0 is the root; created child nodes are positive, so zero marks a leaf. Worker spools stay within one machine/runtime.

No dataset-specific allele/sample rule, new default, or worker-count reduction was introduced. Only compare and stats use this counter module. Other tool implementations are unchanged in the retained product.

## Attribution and rejected parser experiment

Candidate18 removes duplicate queue text; candidate19 also packs counter indices. Candidate20 additionally avoids temporary sample arrays during packed-column preparation. Candidate20 passed output checks, but its small timing differences and inconsistent memory changes did not justify retaining another parser path. Its patch and test harness are kept as [experiment evidence](parallel-memory-20261127/rejected-parser/), outside production code.

| Tool / source | Seconds | RSS MiB | PSS MiB |
| --- | ---: | ---: | ---: |
| vcf-compare / before | 15.32 | 441.3 | 246.3 |
| vcf-compare / queue text only | 15.20 | 373.4 | 178.1 |
| vcf-compare / retained queue + counters | 15.37 | 371.0 | 175.6 |
| vcf-compare / rejected parser experiment | 15.09 | 370.3 | 174.2 |
| vcf-stats / before | 6.40 | 239.6 | 115.2 |
| vcf-stats / retained queue + counters | 6.18 | 224.5 | 98.5 |
| vcf-stats / rejected parser experiment | 6.02 | 224.3 | 99.1 |

The four additional end-to-end cases below evaluate candidate20, **not the retained product**. Subset selects 250 of 500 samples; convert uses the existing SNP subset. All settings compared complete output before deletion.

| Tool | Original s | Before Nu16 s | Experiment Nu16 s | Before → experiment RSS MiB | Before → experiment PSS MiB | Full output |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| vcf-to-tab | 46.73 | 2.72 | 2.54 | 172.7 → 189.4 | 70.3 → 72.0 | Byte-identical |
| fill-an-ac | 36.68 | 3.85 | 3.83 | 205.2 → 204.7 | 79.2 → 79.6 | Byte-identical |
| vcf-subset | 74.01 | 3.82 | 3.65 | 205.1 → 200.5 | 80.0 → 79.6 | Byte-identical |
| vcf-convert | 37.96 | 3.71 | 3.60 | 194.9 → 194.8 | 77.2 → 77.4 | Byte-identical |

## Verification

Full stdout bytes, order and duplicates are compared against original output. Stderr is checked after normalizing source paths/callsite numbers. Diagnostic regression tests also normalize process-specific Perl reference addresses only in unquoted stack-frame arguments; actual diagnostic messages and record text remain intact. Generated source-header timestamps use a fixed Perl clock; performance timers are real.

Job 9686952 passed 12,336 packed-parser cases, 72 comparison diagnostic cases at 1/4 workers and three hash seeds, 21 comparison cases at each of 1/4 workers, 469 ordered-worker cases, and 30 stats/merge cases at each of 1/4/16 workers. Queue ownership and packed-event tests check actual storage/replay, Unicode/NUL keys and detached repeated merges. These controls tested candidate20; the retained candidate19 was then checked independently in job **9687555**. All 42 comparison cases, 72 diagnostic cases, 90 stats/merge cases, 469 ordered-worker cases and the three ownership/layout controls passed against the retained code. The 34 product Perl files match candidate19’s recorded hashes.

Nine abstract SMT obligations passed, including 32/64-bit event-index pairing. These handwritten models do not prove whole-program Perl equivalence or the implementation of pack/unpack. There is no verified translation or independent proof checker. See [verification scope](../verification/README.md).

Job 9686277 stopped before performance measurements because a new diagnostic test compared random Carp reference addresses. Its failing stdout, diagnostic content and exit codes matched; evidence was retained. The corrected harness then ran in job 9686952. This was a test-comparison defect, not a product-output mismatch.

## Disk handling

Inputs/indexes are reused. Low-space and per-tool output-budget guards stop measurements and preserve unverified output. Timeout/budget termination targets only the measurement process group. All completed measured outputs were deleted after full comparisons: 1010346298 bytes. Small manifests, timings, control results and failed-run evidence remain; biological input/output is not exported.

[Machine-readable results](parallel-memory-20261127.json) · [Harnesses and evidence](parallel-memory-20261127/) · [23-command worklist](memory-worklist.md) · [Previous measurements](parallel-state-memory-20261127.md)
