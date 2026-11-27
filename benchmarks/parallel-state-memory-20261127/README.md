# Evidence for the 2026-11-27 worker and memory changes

The report is [one directory above](../parallel-state-memory-20261127.md). Source SHA256 manifests identify the exact frozen candidates; they do not replace output comparison.

- `memory_diagnosis.py`: job 9669524, previous candidate13, batch and worker memory measurements.
- `run14.py`: job 9670116, three completed comparisons followed by a missing-index failure in the original compare command.
- `run15.py`: job 9670282, cancelled before execution because its dependency failed.
- `run16.py`: job 9670442, dedicated input/index preparation followed by six comparisons.
- `run17.py`: job 9671590, compare-only follow-up removing serial counter-path overhead; candidate16 is the before version.
- `formal/`: seven abstract SMT obligations, solver proof terms and results; see [scope](../../verification/README.md).
- `metadata/`: run status, comparison outcomes, control-suite summaries and timing metadata. Biological inputs and output records are not included.

Large measured outputs are removed only after full byte comparison passes. Failed-run output remains on Oscar. Index preparation is timed separately and excluded from the tool timings and memory measurements.
