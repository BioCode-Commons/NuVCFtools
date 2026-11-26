# Reusable LD chi-square workspace

The genotype chi-square kernel now uses one contiguous observed-count buffer and reuses its scratch storage across site pairs. Genotypes are read-only, state belongs to the caller, and accumulation and formatting order are retained. The existing member-function interface remains available. This is a single-threaded change; parallel scheduling has not been implemented.

Candidate source: `0578c677e6d95ac2fad1fa0ff1831e4f9098b9ba`. Before executable: the buffered LD candidate `c8494dd775eb98667e91b9ddda213d254b938410`. The other C++ sources are unchanged between that build and the integrated base `8165318`. Binary and compiled source hashes accompany this report. Build **9649371** and benchmark **9649376** completed with exit 0 on Oscar; benchmark node was `node1812.oscar.ccv.brown.edu`, one bound physical core, GCC 11.5 with `-O2`.

Input: retained 1000 Genomes Phase 3 GRCh37 chr22:20,000,001–21,000,000, 22,382 actual records and 100 samples, FORMAT=GT. Wall time includes startup, decompression, parsing/filtering, staging, pair calculation and writing. Compilation, input preparation and comparison are excluded. RSS is GNU time peak process RSS.

| Case | Before (s) | Candidate (s) | Speedup | RSS before / candidate (MiB) | Full output |
| --- | ---: | ---: | ---: | --- | --- |
| 1 kb window, median of 3 | 3.24 | 2.52 | 1.29× | 4.875 / 4.875 | Identical |
| 1 kb window, stdout, once | 6.31 | 5.58 | 1.13× | 4.875 / 4.875 | Identical |
| 10 kb window, once | 27.62 | 22.03 | 1.25× | 4.875 / 4.500 | Identical |
| 1 kb window, biallelic only, once | 3.15 | 2.51 | 1.25× | 4.875 / 4.875 | Identical |

All six pairs (12 executions) succeeded. The harness compares every scientific output file and stdout byte and matching file sets. Stderr differs only by normalized output prefixes and runtime text. Successful raw outputs were deleted after comparison; retained input was not changed. The 10 kb output was 232,861,989 bytes per execution and was also compared in full.

These gains are relative to the preceding optimized version, not upstream. Do not multiply them into the separate upstream speedups. The one-run RSS difference does not establish a RAM reduction. No additional fuzzing was performed; this result does not resolve the previously recorded malformed-input failure.

[Measurements and harness](common-speed-ld-workspace-20261126/)
