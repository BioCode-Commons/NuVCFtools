# Verification scope

`ordered_workers_model.py` checks explicit mathematical obligations using Z3. Run:

```sh
python3 -m venv /tmp/nuvcf-verification
/tmp/nuvcf-verification/bin/pip install z3-solver
/tmp/nuvcf-verification/bin/python verification/ordered_workers_model.py --output /tmp/nuvcf-proofs
```

It writes each negated claim as SMT-LIB and retains the solver's proof term and version. A result must be `unsat`; `unknown` is a failure, not a pass. This follows the [Z3 validity-checking convention](https://microsoft.github.io/z3guide/programming/Z3%20Python/Introduction/).

These are **manually modeled algorithm contracts, not a proof of the Perl programs**. There is no verified translation from Perl, no proof of the Perl interpreter, allocator, OS scheduler or Storable, and no independent proof checker in this workflow. The tests below connect those contracts to the actual implementation on bounded fixtures.

| Obligation | Implementation | Assumptions / unproved connection |
| --- | --- | --- |
| Integer counter partition | `NuOrderedCounters::add`, `snapshot`, `merge` | All updates are nonnegative integers and their sum fits signed 64-bit range. Every leaf is replayed once at the same path. Floating-point regrouping is excluded. |
| Earliest insertion order | Counter event log | Event order is input order; the first occurrence of each path is replayed before values. Perl hash iteration behavior is checked with multiple fixed hash seeds, not proved. |
| Queue submission bound and emitted prefix | `NuOrderedWorkers::run` | Only the queue head emits. Models a queue step, not signal delivery, fork failure, external subprocess cleanup or liveness. |
| Byte concatenation | Ordered stdout/stderr spools | Each task produces exactly its serial output and replay uses submission order. It does not prove task independence. |
| Successful validation memo | CLI `run_validation(readonly_genotypes=>1)` | Validation is pure for a fixed record/header and equal genotype data. Only successful built-in validations are reused. Header discovery, malformed diagnostics and custom API callbacks must retain serial behavior. |
| Three-block message candidate index | `vcf-validator` | Token blocks are disjoint and cover every token; token distance is at most two. The original complete comparison still selects the earliest matching message. |

Runtime checks compare full stdout, stderr (only source paths/callsite numbers normalized where specified), exit status, partial output and order. The relevant suites are `ordered_workers_regression.py`, `perl_stats_merge_regression.py`, `annotate_counts_regression.py`, `compare_index_regression.py`, and `validator_record_regression.py`. The latter also tests unknown fields, malformed fields, duplicate/unsorted positions, VCF versions and repeated erroneous genotypes. These checks are not universal equivalence claims.

Readonly genotype interning is confined to a single record and keyed by the complete sample text. Ordinary mutable parsing still returns independently writable hashes. Diagnostic-bearing malformed columns are parsed separately. `take_prepared_value` is an explicitly destructive, single-consumer API; the existing `prepared_value` accessor remains available for repeat access.
