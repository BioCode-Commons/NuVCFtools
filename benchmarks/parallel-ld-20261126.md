# Ordered parallel genotype chi-square LD

`--geno-chisq --ld-threads N` distributes independent site pairs across workers. Input parsing and filtering remain serial. Each worker owns genotype buffers, a calculation workspace and its streams. Temporary output is framed by the outer-site index and merged in the original row order. No entire pair table is held in memory; temporary disk space grows with the output. The default is one worker. Multiworker execution requires file output; stdout retains the serial interface.

## Larger actual-data comparison

Input: 22,382 actual records from 1000 Genomes Phase 3 GRCh37 chr22:20,000,001–21,000,000, with 500 or 2,504 samples and FORMAT=GT. This is five or 25 times the genotype volume of the earlier 100-sample LD test, not a whole-genome benchmark. Both use a 1,000 bp LD window. The 500-sample subset preparation took 2.147 seconds and produced 1,213,934 compressed bytes; preparation and compilation are excluded from the measurements below. Per-run LD staging, temporary output, ordered merging and final writing are included.

Both larger-data matrices used the same Oscar node, `node1849`, with physical-core binding. Each version/core setting ran once in these larger-data matrices. Upstream was measured in job **9650573**; the final compiler configuration and preceding optimized version were measured in the following job **9651007**. Each setting was measured once; the compiler revisions ran in sequential jobs without paired repetitions. Ratios below divide the actual measurements; they do not multiply component speedups.

| Samples | Upstream wall (s), 1 core | Upstream peak RSS (MiB) | Previous optimized wall (s), 1 core | Previous peak RSS (MiB) |
| ---: | ---: | ---: | ---: | ---: |
| 500 | 159.09 | 5.625 | 6.78 | 5.625 |
| 2504 | 772.98 | 6.000 | 27.79 | 5.625 |

| Samples | Final cores | Wall (s) | vs upstream | vs previous optimized | vs final 1 core | Peak RSS (MiB) | Process CPU (s) | Step core-hours |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 500 | 1 | 6.97 | 22.82× | 0.97× | 1.00× | 5.625 | 6.92 | 0.00194 |
| 500 | 4 | 2.62 | 60.72× | 2.59× | 2.66× | 6.805 | 7.83 | 0.00291 |
| 500 | 8 | 1.88 | 84.62× | 3.61× | 3.71× | 11.652 | 8.81 | 0.00418 |
| 2504 | 1 | 28.65 | 26.98× | 0.97× | 1.00× | 5.625 | 28.51 | 0.00796 |
| 2504 | 4 | 10.20 | 75.78× | 2.72× | 2.81× | 8.020 | 29.79 | 0.01133 |
| 2504 | 8 | 7.14 | 108.26× | 3.89× | 4.01× | 15.633 | 31.18 | 0.01587 |

RSS is peak resident memory of the C++ process, including its threads. Process CPU is user plus system time. Step core-hours are assigned step cores × tool wall / 3,600; the Slurm job reserved eight cores across the sequence, so this is not the total billed allocation. Threading trades some extra memory, temporary I/O and CPU work for lower elapsed time.

## Identity and validation

- Upstream: `1f87a83402ffd17ea2723a456b7edf5d80b4a22c`.
- Previous optimized source: `0578c677e6d95ac2fad1fa0ff1831e4f9098b9ba` (reusable chi-square workspace).
- Initial parallel source: `088474f17ed0bd40ac680e559951275be099aabd`, build **9650383**.
- Final source: `3ce1fa053bdfefcca858a48bc0eceeca397b419e`, build **9650768**. It preserves the compiler's language mode and checks C++11 thread support instead of overriding the mode. Native GCC 11.5, `-O2 -pthread`.

The first larger-data job compares complete scientific files, stdout and normalized diagnostics among upstream, the previous optimized binary and the initial parallel binary. The final job compares complete files again against that same frozen previous binary on the same inputs. Thus final equality to upstream is established through this shared, byte-checked reference; upstream was not rerun for the compiler-only adjustment. Hashes identify inputs and executables and do not replace byte comparisons. Successful raw outputs were removed after each comparison; inputs, metadata and failed-run evidence were retained.

Seven functional cases cover ordinary LD, SNP/base window bounds, filters and thinning, BCF, two sites, an empty window and unsorted input. Each passed with the previous executable and final 1/4/8-worker executable (28 executions). Eight additional checks cover invalid CLI values, unsupported output modes, output write failure and descriptor exhaustion; worker temporary files were cleaned after the induced failures. Existing native tests passed in both builds. No new fuzzing was run.

The initial final-build controls job **9650937** exited because the harness wrongly required the old undefined behavior described below to fail on every run. All candidate comparisons had passed. Audit **9650994** verified the recorded exits/cleanup checks and re-compared the retained path-test output bytes; the incorrect old-crash requirement was removed. Both the failed harness run and the audit are retained.

## Temporary filename defect

The old chi-square path allocated `char tmpname[new_tmp.size()]` and then copied a string plus its terminating zero into it. A 96-byte template triggered an empty staging file and eventual memory exhaustion during the first controls job **9650434**. A bounded replay also stalled; another replay happened to succeed, as undefined behavior can do. The candidate allocates the actual string length plus the terminator using a vector and passes the same path/output regression in serial and parallel mode. It does not branch on path length. This correction covers the chi-square call site; it does not claim that every legacy temporary-file caller or the previously recorded malformed-input bug has been fixed.

## Compiler-mode check and limits

A separate three-order comparison (**9650801**) examined the apparent one-thread regression. On 500 samples with local temporary storage, median wall times were 5.37 s for the preceding binary, 5.85 s when C++11 mode was forced, and 5.53 s when the compiler mode was preserved. All outputs matched. The final build uses the latter configuration. The larger-data final table above records its measured one-core performance; parallel gains should not be described as a universal single-thread improvement.

Only genotype chi-square LD has this new worker option. The timings do not establish a speedup for other commands, other FORMAT layouts or an entire chromosome/genome. Parallel peak RSS is higher than serial in these tests; this change is not a general RAM reduction. [Measurements, identities and harnesses](parallel-ld-20261126/).
