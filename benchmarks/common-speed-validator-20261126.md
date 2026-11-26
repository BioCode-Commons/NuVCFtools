# Common-tool speed round: validator

Baseline: `9dc88f1`. Candidate implementation: `d802f36`. Oscar job **9639463**, node **node1827.oscar.ccv.brown.edu**, one physical core with CPU binding, 4 GiB allocation. This compares against the start of this continuous optimization task, not upstream VCFtools.

The validator reuses GT tokens within each record, while still validating every sample and invoking every FORMAT handler. Number=G cardinality is calculated only if a field actually requests it. Unknown-header mutation and sample diagnostics remain in the original validation loop.

## End-to-end measurements

The retained 1000 Genomes Phase 3 GRCh37 chr22:20,000,001–21,000,000 subset contains 22,382 real records and 100 samples, with FORMAT=GT. Its full original header is retained. Commands include startup, gzip reading, computation and writing; input preparation and comparison are outside GNU time. Three paired repetitions per configuration, alternating revision order; table values are medians. RSS is the GNU time maximum process RSS in MiB, not a sum of simultaneously resident children. Small RSS changes are allocator granularity, not demonstrated memory savings.

| Configuration | Before wall (s) | After wall (s) | Speedup | Before RSS (MiB) | After RSS (MiB) | Equivalence |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| real100 | 18.13 | 12.45 | 1.46× | 10.125 | 10.500 | Pass |

## Validation

Both stdout and stderr are diagnostic streams here; only tool source paths/line numbers are normalized. Exit status, message content/count/order and complete scientific outputs remain compared. Performance applies to this GT-only real input; rich FORMAT and malformed cases were correctness checks, not performance evidence.

60 randomized CLI pairs passed, plus all 3 real-data paired checks. The corpus includes missing calls, phase, varying ploidy, FORMAT variations and invalid input. The validator cases cover legacy VCF versions and `-d`/`-u`. Matching failures on deliberately invalid inputs count as diagnostic equivalence, not successful validation of those inputs. Real-data commands must exit successfully. No sampled-output or hash-only check substitutes for byte comparison.

The first harness attempts needed diagnostic-location normalization: validator `-u` prints stack locations into stdout; subset Carp traces contain process-specific reference addresses. Those adjustments change comparison of diagnostic metadata only. Product code was not changed to suppress an observed error. Original failed harness artifacts remain remote for audit.

Measurements and command options are in [common-speed-validator-20261126/status.json](common-speed-validator-20261126/status.json); the harness and Slurm wrapper are in that directory. This is randomized differential testing rather than a coverage-guided campaign or proof of all Perl API extensions.
