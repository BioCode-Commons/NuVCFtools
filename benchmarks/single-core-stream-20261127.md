# Single-core stream and column handling

Measured on Oscar node1829, Slurm 9691160. Three sequential runs per version, each pinned to one physical CPU. The original is VCFtools 1f87a834; before is e393337; candidate source hashes are retained beside the harness. Input: 22,382 real 1000 Genomes chromosome 22 variants, 2,504 samples, GT-only. CRLF conversion input and reverse sample header were prepared separately.

| Command | Original (s) | Before (s) | Candidate (s) | Speedup vs original | Sampled RSS original / before / candidate (MiB) | Full output |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| vcf-shuffle-cols | 13.16 | 11.54 | 6.89 | 1.91× | 13.5 / 17.2 / 17.2 | Passed |
| vcf-fix-newlines | 0.33 | 0.49 | 0.34 | 0.97× | 7.1 / 11.2 / 10.9 | Passed |
| vcf-tstv | 0.82 | 1.00 | 0.87 | 0.94× | 11.2 / 15.4 / 15.8 | Passed |

Times and memory are medians of three runs. RSS is the sum across the sampled process tree at 100 ms intervals, not an exact kernel peak. The short conversion and tstv runs should be read as small absolute changes; tstv remains slower than upstream. Compression/decompression, startup, input and output are included. Input preparation is excluded.

Column shuffling compiles the permutation once and joins an array slice for complete rows. Missing mappings and truncated rows retain the original diagnostic path. Newline conversion uses bounded chunks with a carried CR at CRLF boundaries, after the existing initial line/detection behavior. The tstv serial path accumulates directly using the same classification body as workers.

All 27 measured commands exited successfully. Entire stdout files were compared bytewise, and stderr was compared after source-path/line normalization. The 84 stream controls and 469 worker controls passed. Successful large outputs and the generated CRLF input were removed after comparison; cleanup totals are in the metadata.

Five abstract SMT checks returned unsat. They check the CRLF state relation and final flush, CR mapping, ordered column concatenation and counter transitions under their stated bounds. They do not prove the Perl interpreter, regex engine, or whole commands. See [contracts](../verification/serial-stream-contracts.md).
