# Single-thread representation contracts

These are source-level arguments, not machine-checked proofs of the Perl programs.

## Column ownership experiment

`prepare_data_columns` allocates a fresh array in the built-in reader. Internal callers may let `next_prepared_hash` read that array directly while it remains stable. Decoding writes output scalars/arrays/hashes and does not write the input array. The public default still takes a snapshot; only the explicit owned-array call opts into borrowing. This argument assumes the caller does not mutate the owned array during decoding, including through callbacks. It does not establish equivalence for subclasses that violate that ownership contract.

## Sample ordering

For the CLI reader, sample names are fixed by the header (or the reader's initial inferred columns). A decoded record's genotype keys form a subset of these names; empty fields can omit keys, and duplicate names collapse in the hash. Sorting the unique header names once and filtering by membership in each record yields the same lexical order as sorting that record's keys. The header output still uses the first record's actual keys. Empty fields, absent samples and partial output on errors keep their previous behavior. Cost changes from sorting on every record to one sort per processing context plus a linear membership scan per record; each forked batch has its own context.

## Read-only comparison

`cmp_genotypes` reads GT/DP/GL values and changes only the outer sample-name map during remapping. `parse_haplotype` writes a record-level cache, not the genotype entries. Equal complete, well-formed genotype fields can therefore share the existing read-only parser representation. Malformed fields retain individual parsing/diagnostics. Mutable parser callers are unchanged. Memory/time savings depend on how often complete fields repeat; no dataset or allele-specific threshold is used.

The regression harness compares normal full stdout and error-body/exit/partial-stdout behavior. Internal Carp frames are not treated as a stable API when a helper call changes; this exclusion is explicit in those diagnostic test results. End-to-end successful benchmark outputs are compared as full byte streams. Neither the tests nor these arguments establish equivalence for all possible inputs.

`single_thread_models.py` checks four small SMT obligations: stable array reads, order of selected header entries, prefix preservation on an append/filter step, and reuse of a pure decoder on equal complete fields. The source-to-model connection is manual. In particular, the model assumes stable arrays, lexical header order represented by increasing keys, and a pure genotype decoder; it does not prove these assumptions about Perl or arbitrary user callbacks. Solver proof terms are retained, without an independent proof checker.
