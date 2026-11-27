# Single-core column handling and comparison

Job **9689540**, node `node1925.oscar.ccv.brown.edu`. Before: `00d2c3588e802d4947d49508f537d48fe7c6c5e0`; candidate22 is identified by its [source manifest](single-thread-20261127/candidate22-sha256.json). Original VCFtools: `1f87a83402ffd17ea2723a456b7edf5d80b4a22c`. Each measured command and its children were pinned to one physical CPU. Defaults remain one worker.

Input: 22,382 real 1000 Genomes chr22 variants, 500 samples, GT-only fields. Compare uses two separately named copies of the same indexed input. Validator uses its default mode. Each setting ran once in the same allocation; small differences need repetition before being treated as stable improvements. Rich FORMAT correctness is tested separately, but its performance is not established here.

| Tool | Original s | Before s | Candidate s | Before / candidate | Original / candidate | Tree RSS MiB, original → before → candidate | Output |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| vcf-to-tab | 45.97 | 15.71 | 12.38 | 1.27× | 3.71× | 15.8 → 18.8 → 19.1 | Byte-identical |
| vcf-compare | 102.60 | 88.31 | 75.15 | 1.18× | 1.37× | 42.8 → 45.8 → 45.8 | Byte-identical |
| vcf-stats | 121.18 | 31.41 | 30.06 | 1.04× | 4.03× | 20.2 → 20.2 → 19.9 | Byte-identical |
| vcf-validator | 94.13 | 20.22 | 18.89 | 1.07× | 4.98× | 13.1 → 13.1 → 12.8 | Byte-identical |

Wall time includes reading/decompression, computation, startup and full output writing. Index preparation and validation are excluded. Process-tree RSS/PSS are sampled every 100 ms, so brief peaks can be missed; RSS double-counts shared pages, PSS apportions them. GNU time accounting and PSS are retained in the JSON. Main gains are to-tab (21.2% less time) and compare (14.9% less time); stats and validator changes are smaller. Memory is approximately unchanged.

## Changes and attribution

- Internal readers reuse their fresh column array during decoding. Public `next_prepared_hash` calls still snapshot by default; owned-array decoding requires stable input throughout the call.
- To-tab sorts unique header sample names once per processing context and filters by actual record membership. Missing/empty fields and duplicate names retain their previous output behavior.
- Compare uses the existing read-only genotype decoder. Column remapping changes only the outer name map; shared genotype hashes are not mutated. Savings from interning depend on repeated complete fields.

Array reuse alone measured 15.66 s for to-tab versus 15.71 s before, and 85.61 s for compare versus 88.31 s before. Combined results above add sample ordering and read-only comparison respectively. Stats and validator use the array change only. No dataset-specific threshold, new CLI default or additional worker was introduced. These measurements do not replace earlier multicore results with a newly measured multicore claim.

## Verification

Full stdout bytes are compared against the original for every setting, including intermediate versions. Successful-run stderr is compared after normalizing installation paths and source line locations. Generated source-header timestamps are fixed only for comparison; timing clocks remain real. Perl hash seed/perturbation are fixed in the harness.

Controls passed: 1,344 decoded-record combinations across VCF 3.3/4.0/4.1/4.2; 128 to-tab cases covering empty/missing samples, duplicate headers, headerless input, IUPAC, malformed GT, partial output and 1/4 workers; 42 comparison cases; 72 comparison diagnostic cases; 60 stats/merge cases; 360 validator cases; and 469 ordered-worker cases.

Job 9689345 stopped before timing because a diagnostic test compared internal Carp frames changed by the read-only helper. Exit status, partial stdout and error body matched. The corrected test explicitly excludes internal call frames and retains error bodies, exit codes and complete stdout; its mode is recorded in each result. Ordinary output equivalence is not inferred from that exclusion.

Four SMT obligations passed for stable column reads, filtered ordering/prefix preservation and reuse of a pure decoder. They are abstract contracts with manual source-to-model assumptions, not a whole-program proof. See [contracts and limitations](../verification/single-thread-contracts.md).

## Cleanup

192568420 bytes of measured outputs were removed only after full comparisons passed. Reusable input/index files, failed-test evidence and small timing/control metadata remain. No biological input/output is copied into this report.

[Raw measurements](single-thread-20261127.json) · [Harnesses and metadata](single-thread-20261127/) · [Previous memory work](parallel-memory-20261127.md)
