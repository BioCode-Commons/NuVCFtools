# C++ genotype-runs end-to-end measurements

Implementation `5a70977` versus `d8afd0b`; Oscar job **9640270**, node `node1827.oscar.ccv.brown.edu`. Bulk genotype parsing reuses decoded values from the previous decoded sample only when its complete sample text and requested field mask are identical. Every sample keeps independent values and filter state.

## Measurements

22,382 authentic 1000 Genomes Phase 3 chr22 records, 2,504 samples (FORMAT=GT), one physical core. Three paired repetitions per command, alternating revision order. Medians below include startup, gzip input, computation and writing. Preparation and full byte comparison are outside the timer. GNU time maximum process RSS is reported in MiB; it is not the sum of simultaneous child RSS. This is an incremental comparison, not a fresh upstream VCFtools comparison.

| Command | Before wall (s) | After wall (s) | Speedup | Before RSS (MiB) | After RSS (MiB) | Full output |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| freq | 4.61 | 3.15 | 1.46× | 5.250 | 5.250 | Identical |
| missing | 4.36 | 4.32 | 1.01× | 5.250 | 5.250 | Identical |
| het | 5.05 | 3.59 | 1.41× | 5.625 | 5.625 | Identical |
| recode | 18.08 | 16.46 | 1.10× | 5.625 | 5.625 | Identical |
| filter | 19.64 | 17.58 | 1.12× | 5.625 | 5.625 | Identical |

## Validation and limits

All 15 real-data comparisons exited successfully. Complete output files and stdout were compared as actual bytes, with no sampled records or hash-only substitute. Stderr comparison normalizes only output-prefix paths and the reported runtime. Command options, individual measurements and raw comparison verdicts are in the accompanying status file. Successful data outputs were removed after comparison.

The targeted decoder ASan/UBSan test completed 264,624 executions before the user stopped further fuzzing. It compared bulk parsing with unchanged single-sample parsing, including differing prior field masks, FORMAT changes, resets and sample-owned state. These are bounded generated inputs, not exhaustive verification.

The native randomized CLI harness recorded 280 passing pairs. Its deliberately short rows can reach pre-existing undefined behavior: a separate serializer experiment subsequently found a heap failure in the before binary on one such input. Those malformed cases are retained for diagnosis and are excluded from performance claims. No claim is made that malformed-input memory safety is established or that this issue has been fixed.

The missingness command uses individual parsing and gains almost nothing from this bulk-path change. Real-input GT repetition affects the amount of reuse; no dataset-specific values, thresholds or genotypes are hardcoded.
