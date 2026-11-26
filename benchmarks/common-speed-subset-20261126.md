# Common-tool speed round: subset

Baseline: `9dc88f1`. Candidate implementation: `d901ba5`. Oscar job **9639576**, node **node1830.oscar.ccv.brown.edu**, one physical core with CPU binding, 4 GiB allocation. This compares against the start of this continuous optimization task, not upstream VCFtools.

Subset computes the allele/type decision once per distinct GT within each record and reuses it for selected samples. GT text formatting is delayed until a selected sample requests it, preserving the private-background control flow and first error. No PL/AD payload or sample-specific data are reused between samples.

## End-to-end measurements

The retained 1000 Genomes Phase 3 GRCh37 chr22:20,000,001–21,000,000 subset contains 22,382 real records and 100 samples, with FORMAT=GT. Its full original header is retained. Commands include startup, gzip reading, computation and writing; input preparation and comparison are outside GNU time. Three paired repetitions per configuration, alternating revision order; table values are medians. RSS is the GNU time maximum process RSS in MiB, not a sum of simultaneously resident children. Small RSS changes are allocator granularity, not demonstrated memory savings.

| Configuration | Before wall (s) | After wall (s) | Speedup | Before RSS (MiB) | After RSS (MiB) | Equivalence |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| real-select10 | 3.62 | 2.66 | 1.36× | 10.500 | 10.500 | Pass |
| real-select100 | 20.62 | 9.32 | 2.21× | 10.125 | 10.500 | Pass |
| real-types100 | 19.30 | 5.56 | 3.47× | 10.125 | 10.500 | Pass |
| real-trim100 | 20.90 | 9.51 | 2.20× | 10.500 | 10.500 | Pass |
| real-private10 | 12.43 | 4.23 | 2.94× | 10.500 | 10.125 | Pass |

## Validation

Scientific stdout is compared as unmodified bytes, including headers and ordering. Diagnostic stderr normalizes only tool source paths/line numbers and Perl reference addresses in Carp stack traces. Exit status, message content/count/order and complete scientific outputs remain compared. Performance applies to this GT-only real input; rich FORMAT and malformed cases were correctness checks, not performance evidence.

96 randomized CLI pairs passed, plus all 15 real-data paired checks. The corpus includes missing calls, phase, varying ploidy, FORMAT variations and invalid input. The subset cases cover sample selection, type filtering, ALT trimming, replacement, private variants and Number=G/R payloads. Matching failures on deliberately invalid inputs count as diagnostic equivalence, not successful validation of those inputs. Real-data commands must exit successfully. No sampled-output or hash-only check substitutes for byte comparison.

The first harness attempts needed diagnostic-location normalization: validator `-u` prints stack locations into stdout; subset Carp traces contain process-specific reference addresses. Those adjustments change comparison of diagnostic metadata only. Product code was not changed to suppress an observed error. Original failed harness artifacts remain remote for audit.

Measurements and command options are in [common-speed-subset-20261126/status.json](common-speed-subset-20261126/status.json); the harness and Slurm wrapper are in that directory. This is randomized differential testing rather than a coverage-guided campaign or proof of all Perl API extensions.
