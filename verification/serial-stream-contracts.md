# Serial stream contracts

`serial_stream_models.py` emits SMT-LIB and proofs with Z3. Five negated contracts are unsatisfiable; source correspondence is a manual review, not verified compilation.

- CRLF: reference prefix length q is 0 or 1; candidate pending-CR is equivalent to q=1. Every byte transition emits identical bytes and preserves that relation. Both begin empty and flush the same unmatched CR at EOF. This gives induction for arbitrary byte streams in the model. The implementation processes chunks using the existing CRLF substitution and holds a trailing CR. Only the supported CR and CRLF delimiters are claimed, not arbitrary overlapping delimiters.
- CR: each byte maps CR to LF and leaves other bytes unchanged. Concatenating this byte map preserves output.
- Columns: bounded, defined gather indices, including repeated indices, select the same strings in the same order as incremental tab-appending. The model instantiates four mapped columns; the repeated concatenation argument is structural. Undefined/truncated mappings retain the existing implementation path and are tested separately.
- Counts: equal nonnegative counters remain equal after the same increment, within signed 64-bit bounds. Classification order is unchanged; model-to-Perl connection and native numeric limits remain assumptions.

The initial newline detection, first-record handling, output failures, Perl diagnostics and worker scheduling are outside these SMT models. Differential tests cover representative boundaries, malformed inputs and one/four-worker execution; they are tests, not proofs.
