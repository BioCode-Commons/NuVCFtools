# Genotype chi-square file buffering

Implementation `c8494dd` versus `9d0a0c5`, Oscar job **9648185**, node `node1837.oscar.ccv.brown.edu`, one physical core. The genotype chi-square table now uses the file buffer; explicit stdout still flushes each row. Calculation order and values are unchanged.

The retained authentic 1000 Genomes Phase 3 chr22 subset has 22,382 records and 100 samples. `--geno-chisq --ld-window-bp 1000` runs three alternating paired repetitions. GNU time includes startup, input, temporary staging, computation and output; preparation and full comparison are excluded.

| Mode | Before wall (s) | After wall (s) | Speedup | Before peak RSS (MiB) | After peak RSS (MiB) | Full bytes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| File (medians) | 5.99 | 3.19 | 1.88× | 4.875 | 4.875 | Identical |
| Stdout (one pair) | 6.12 | 6.37 | No speed claim | 4.500 | 4.875 | Identical |

All four pairs exited successfully and passed complete scientific file/stdout byte comparisons. Diagnostics normalize the output prefix and elapsed time only. Peak RSS is GNU time process RSS, not summed child-process RAM. File partial-result persistence on interruption changes with buffering; successful output and explicit stdout flush behavior are preserved. No fuzzing was performed.
