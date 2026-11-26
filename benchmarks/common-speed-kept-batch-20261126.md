# Missingness batch decoding measurements

Candidate `38aeee1` versus C++ decoder `5a70977`; Oscar job **9647522**, node `node1807.oscar.ccv.brown.edu`, one physical core. Missingness statistics batch-decode only calls that pass both sample selection and genotype filtering. VCF uses neighboring-value reuse; the default BCF implementation follows the unchanged single-sample parse path. Already parsed requested values take the original parser path, preserving explicit setter behavior.

22,382 authentic 1000 Genomes Phase 3 chr22 records, 2,504 samples. Three alternating paired repetitions per VCF configuration. Medians below include startup, gzip input, statistics and writing. Input preparation and full comparison are outside GNU time. Peak process RSS is reported in MiB; it does not sum simultaneous child processes.

| Configuration | Before wall (s) | After wall (s) | Speedup | Before RSS (MiB) | After RSS (MiB) | Full output |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| missing-indv | 4.33 | 3.14 | 1.38× | 5.250 | 5.625 | Identical |
| missing-site | 4.53 | 3.28 | 1.38× | 5.250 | 5.250 | Identical |
| kept-indv | 3.14 | 2.58 | 1.22× | 5.250 | 5.250 | Identical |
| kept-site | 3.29 | 2.72 | 1.21× | 5.250 | 5.250 | Identical |
| filtered | 5.92 | 4.55 | 1.30× | 5.625 | 5.250 | Identical |

All 15 VCF pairs passed full scientific-output byte comparisons and successful exit checks. Two additional BCF comparisons of individual/site missingness also passed using the retained 100-sample cohort, converted outside the timer with the baseline native writer. Their sub-second timings are functional checks, not speed evidence. Diagnostic stderr normalizes only output-prefix paths and runtime. The native build’s existing C++ check passed (1/1). No new fuzzing was run for this change.

`kept-*` selects alternating actual sample names. `filtered` uses `--minGQ 5 --minDP 10`. The input contains GT only, so this tests absent quality/depth behavior rather than performance on rich FORMAT data. Excluded calls are never newly decoded; the output counts, missingness values and ordering remain compared as full bytes.
