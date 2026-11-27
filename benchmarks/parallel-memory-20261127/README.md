# Evidence for packed queues and column preparation

See the [report](../parallel-memory-20261127.md). Before is branch commit `08629211e5d02f34b213f669d7192547b9ec6137` (candidate17).

- Candidate18 only removes duplicated raw text from comparison queues.
- Candidate19 additionally packs counter event indices. This is the retained product.
- Candidate20 is a rejected experiment that additionally scans packed columns. Its diagnostic harness also normalizes process-specific reference addresses in unquoted Carp frame arguments.
- Job 9686277 stopped in the new diagnostic test before benchmarking, because reference addresses were initially compared literally.
- Job 9686952 completed the corrected controls and the six-tool measurements, including intermediate versions for attribution.

Source manifests identify frozen files. `metadata/` contains status/comparison outcomes, control summaries and timings. Full biological output/input is not exported. Formal files are abstract contracts, with [explicit limitations](../../verification/README.md).

Job 9687555 passed the corrected semantic controls against retained candidate19. `metadata/retained19-controls/` and `metadata/run-9687555.out` record those results.

Published stderr log copies omit trailing blank lines; original local/remote logs are retained.
