# Genotype serialization end-to-end measurements

Candidate `00ba69c` versus `d8afd0b`; Oscar job **9647443**, node `node1827.oscar.ccv.brown.edu`. The VCF writer reuses the rendered GT string for adjacent equal decoded genotype/phase values within one record. Other FORMAT fields and each sample’s filters remain independent. Memory for this cache is constant per record.

22,382 authentic 1000 Genomes Phase 3 chr22 records, 2,504 samples (FORMAT=GT), one physical core. Three paired repetitions per command, alternating execution order. Medians below include startup, gzip reading, computation and writing. Preparation and comparison are outside the timer. RSS is GNU time maximum process RSS in MiB, not aggregate process-tree memory. This isolates serialization; the candidate does not yet include the separate decoded-field reuse change.

| Command | Before wall (s) | After wall (s) | Speedup | Before RSS (MiB) | After RSS (MiB) | Complete output |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| freq | 4.61 | 4.57 | 1.01× | 5.250 | 5.250 | Identical |
| missing | 4.36 | 4.29 | 1.02× | 5.250 | 5.625 | Identical |
| het | 5.05 | 4.99 | 1.01× | 5.625 | 5.625 | Identical |
| recode | 18.09 | 9.04 | 2.00× | 5.625 | 5.625 | Identical |
| filter | 19.66 | 10.40 | 1.89× | 5.625 | 5.625 | Identical |

All 15 real-data pairs exited successfully. Actual complete output files and stdout were compared bytewise. Stderr normalizes only the output-prefix path and runtime. Successful raw data outputs were deleted after comparison. Exact commands and individual results accompany this report.

An earlier randomized CLI run (9640286) encountered heap corruption in the before binary on a deliberately shortened sample row; the candidate happened to survive. That is not equivalent behavior or evidence of a fix. Its raw synthetic artifacts remain at the separate `nuvcftools-cpp-output-20261126` directory for diagnosis. The real-input performance run above is independent and contains no generated malformed inputs. The user stopped further fuzzing; no broader malformed-input safety claim is made.

The measured rewrite gain applies to this GT-only cohort and its GT repetition. It is not a universal 2× pipeline claim.
