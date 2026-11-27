# Single-core follow-up contracts

## Sample field parsing

Within one `vcf-fix-ploidy` sample, GT, PL and GL are read from the same unmodified string. Splitting that string once at every colon with trailing empty fields retained gives the same tokens as repeated `get_field` scans. An empty string denotes one empty field; a requested index beyond the token vector denotes `.`. The optimized reads precede all replacements. Replacement order, version-dependent missing-field errors, likelihood selection and per-sample counters are unchanged. No genotype, sample identity or dataset-specific threshold selects this implementation. The temporary vector is bounded by one sample column, not by the cohort.

For a token containing no colon, the first colon in `token : remainder` is at the token length. The substring before it is the token; the substring after it is the remaining string. Induction repeats that argument through every colon and emits the final token even when empty. The SMT model checks extraction at these token boundaries and the final tail for arbitrary character sequences; correspondence between Perl `split`, `index`, and that tokenization remains manual. An attempted combined automatic first-delimiter/string proof timed out and is recorded as `unknown`, not a successful proof.

## Serial indel state transitions

A nonempty line returned by the CLI's line reader occupies a singleton serial batch in the preceding implementation. Preparation updates the chromosome/position cursor; classification computes the same ordered list of allele lengths; accumulation updates the same counters and interval cursor. The direct serial loop performs those three operations in that order without creating queue and diagnostic-envelope objects. Records skipped by preparation remain skipped. The parallel branch retains ordered batches and uses the same classification and accumulation callbacks.

The recursive-fold SMT obligation shows that folding two singleton mapped records equals two direct state transitions, without assuming that reduction is commutative or associative. Induction extends this to the input sequence. Source correspondence, diagnostics, I/O failures and arbitrary callback substitution are not machine-verified. CLI controls compare malformed/unsorted input, partial stdout, error body and exit status at one worker; only source locations and Carp stack metadata are normalized. Successful real-data outputs are compared as complete bytes.

## Sparse serializer bookkeeping

`VcfStats::dump` creates a fresh Data::Dumper instance through `Dumper` and returns only its text. Nothing reads or reuses that instance's `Seen` map. A dynamically scoped `Sparseseen=1` requests that the library omit scalar bookkeeping entries when it knows they have only one reference; reference-bearing values still participate in alias/cycle detection. The previous setting is restored on return or exception. This changes auxiliary data structures, not the statistics tree or traversal/format options.

This relies on Data::Dumper's documented `Sparseseen` contract (the installed `perldoc Data::Dumper`), not a proof of its XS or Perl implementation. The differential suite exercises XS and pure-Perl serialization, shared hashes/scalar references, cycles, undefined/zero/text values, and Purity/Terse settings: 248 cases. The full CLI stats controls also cover filters, sample subsets and dumps.

## Observed baseline limitation

The preceding revision intermittently adds `Wait for worker …: No child processes` while cancelling parallel workers after a malformed PL error. Job 9693842 observed this on the baseline, with the same primary error, exit code and partial stdout on both versions. This pass does not claim to fix that cancellation behavior. All single-worker error controls remain mandatory; known error cases are explicitly excluded from four-worker byte-equality claims and recorded in `excluded.json`. Valid four-worker cases are still compared. No diagnostic text is silently dropped to hide this limitation.
