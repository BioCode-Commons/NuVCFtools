# C++ cpp-reader end-to-end measurements

Implementation `d8afd0b` versus `d802f36`; Oscar job **9639845**, node `node1830.oscar.ccv.brown.edu`. An owned row cursor replaces tab extraction through a string stream. Each entry retains independent storage for interleaved comparisons.

## Measurements

22,382 authentic 1000 Genomes Phase 3 chr22 records, 2,504 samples (FORMAT=GT), one physical core. Three paired repetitions per command, alternating revision order. Medians below include startup, gzip input, computation and writing. Preparation and full byte comparison are outside the timer. GNU time maximum process RSS is reported in MiB; it is not the sum of simultaneous child RSS. This is an incremental comparison, not a fresh upstream VCFtools comparison.

| Command | Before wall (s) | After wall (s) | Speedup | Before RSS (MiB) | After RSS (MiB) | Full output |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| freq | 4.15 | 3.94 | 1.05× | 5.250 | 5.250 | Identical |
| missing | 3.83 | 3.73 | 1.03× | 5.625 | 5.250 | Identical |
| het | 4.53 | 4.33 | 1.05× | 5.625 | 5.625 | Identical |
| recode | 15.52 | 15.51 | 1.00× | 5.625 | 5.625 | Identical |
| filter | 16.72 | 16.84 | 0.99× | 5.625 | 5.625 | Identical |

## Validation and limits

All 15 real-data comparisons exited successfully. Complete output files and stdout were compared as actual bytes, with no sampled records or hash-only substitute. Stderr comparison normalizes only output-prefix paths and the reported runtime. Command options, individual measurements and raw comparison verdicts are in the accompanying status file. Successful data outputs were removed after comparison.

The cursor-specific ASan/UBSan libFuzzer test completed 1,508,659 executions before fuzzing was stopped at the user’s request. It compared extraction and EOF/reset behavior with `std::getline`. The 120 initial randomized CLI pairs often terminated early because the original C++ parser rejects polyploid GT; they are not evidence of successful processing of 120 valid datasets.

The cursor alone provides small gains and no demonstrated RSS reduction; VCF rewriting is neutral and the filtered rewrite was slightly slower. It is retained here as the measured baseline for the subsequent decoder work, not presented as a large standalone speedup.
