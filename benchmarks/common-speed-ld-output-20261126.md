# LD table file buffering measurements

Implementation `9d0a0c5` versus integrated C++ source `9bd6ad8`; Oscar job **9648098**, node `node2304.oscar.ccv.brown.edu`, one physical core. Genotype and haplotype LD tables use the regular output file buffer instead of forcing a flush after every row. Explicit stdout mode retains the previous row flush behavior. Pair selection, counts, numerical calculations and formatting are unchanged.

Input: authentic 1000 Genomes Phase 3 chr22:20,000,001–21,000,000, 22,382 records and 100 samples, `--ld-window-bp 1000`. Three paired repetitions with alternating order; medians include process startup, gzip input, temporary files, computation and writing. No download, compilation or output comparison is timed. RSS is GNU time maximum process RSS in MiB.

| Output | Mode | Before wall (s) | After wall (s) | Speedup | Before RSS (MiB) | After RSS (MiB) | Full bytes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| geno-r2 | file | 3.23 | 0.73 | 4.42× | 11.250 | 10.875 | Identical |
| geno-r2 | stdout (one pair) | 3.24 | 3.17 | 1.02× | 10.875 | 10.875 | Identical |
| hap-r2 | file | 3.67 | 1.14 | 3.22× | 11.250 | 11.250 | Identical |
| hap-r2 | stdout (one pair) | 3.80 | 3.80 | 1.00× | 10.875 | 11.250 | Identical |

All eight actual-data pairs exited successfully and passed actual complete output-file/stdout byte comparisons. Stderr normalizes only the output prefix and reported runtime. Successful raw outputs were removed. The stdout controls show that the file-output improvement comes from flush policy, not a changed LD calculation. These are incremental gains over the previously optimized bitset/decoder implementation, not a fresh upstream comparison.

File output is buffered; partial files after an interrupted or failed process need not have the former per-row persistence. Successful results and explicit stdout flushing are the compared behavior. No additional fuzzing was performed.
