# Column-shuffle end-to-end measurements

Baseline `e01d039`; candidate `fc198ed` replaces per-column stdout calls with one output call per VCF row. Oscar job **9647476**, node `node1807.oscar.ccv.brown.edu`, one physical core. Sample mapping and per-field concatenation order are unchanged. The row buffer uses memory proportional to the current row, not the whole input.

The authentic 1000 Genomes Phase 3 chr22 subset contains 22,382 records. Three paired repetitions, alternating order; medians below include startup, gzip reading, reordering and writing. Template preparation and full comparison are outside the timer. RSS is GNU time maximum process RSS in MiB, not simultaneous process-tree memory.

| Samples | Order | Before wall (s) | After wall (s) | Speedup | Before RSS (MiB) | After RSS (MiB) | Complete stdout |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 100 | same | 0.80 | 0.68 | 1.18× | 10.500 | 10.500 | Identical |
| 100 | reverse | 0.79 | 0.67 | 1.18× | 10.500 | 10.500 | Identical |
| 2504 | same | 15.72 | 13.22 | 1.19× | 12.000 | 12.000 | Identical |
| 2504 | reverse | 15.70 | 13.30 | 1.18× | 12.000 | 12.000 | Identical |

All 12 paired invocations exited successfully. Complete stdout was compared bytewise, including the header and sample order. Diagnostic stderr normalizes source paths/line numbers only. Passed raw output files were deleted. This is a comparison against the already optimized task baseline, not upstream VCFtools. The sub-second 100-sample results are approximate; the 2,504-sample rows are the stronger timing evidence.
