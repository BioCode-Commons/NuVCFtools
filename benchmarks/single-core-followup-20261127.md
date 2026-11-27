# Single-core follow-up: regressions and memory

Baseline: 97def7f8376923c2ca2b9147b35708d67069fc74. The original is the same frozen upstream installation used in the preceding all-tool table. Job 9693876 ran each command and all its children on one physical CPU at node1842.oscar.ccv.brown.edu. Input was 22,382 real 1000 Genomes chr22 variants with 500 samples and GT-only FORMAT. Preparation and comparison are excluded; input decompression, processing and complete output writing are included.

| Tool | Original s | Before s | Latest s | vs original | Before → latest tree RSS MiB | Output |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| vcf-indel-stats | 0.38 | 0.56 | 0.44 | 0.86× | 15.38 → 15.75 | Passed |
| vcf-fix-ploidy | 50.96 | 51.62 | 45.32 | 1.12× | 16.12 → 16.12 | Passed |
| vcf-stats | 120.05 | 29.79 | 29.94 | 4.01× | 26.21 → 15.38 | Passed |

Indel times are medians of three repeats; other rows are single runs. Fixed original/before/candidate order and unflushed caches limit precision. Tree RSS is sampled every 100 ms, can miss short peaks and double-counts shared pages; PSS and GNU time RSS are retained in JSON. For stats, GNU time max RSS confirms a reduction from 27.00 to 16.50 MiB (38.9%); upstream was 26.25 MiB. This kernel-accounted process/child high-water mark is not an aggregate tree peak.

Changes: indel-stats directly folds classified records at one worker, avoiding queue/diagnostic-envelope allocations; ploidy parses each sample field once for GT/PL/GL access; stats uses Data::Dumper’s sparse reference tracking instead of tracking every scalar. None is selected by a dataset identity or biological threshold.

Full stdout bytes and successful stderr (installation paths/source line numbers normalized) matched original and before in every timed case. The 248 Dumper controls cover aliases/cycles and both XS/Perl implementations; 46 targeted CLI controls and 30 stats/merge controls at each of one/four workers passed. One-worker failure cases retain primary diagnostics, exit and partial stdout checks.

Job 9693799 stopped at a diagnostic source-location difference; the test adopted the existing terminal-callsite normalization. Job 9693842 exposed an intermittent extra child-wait diagnostic in the preceding version on a four-worker malformed PL case. Those known failing-input cases remain tested at one worker, but are explicitly excluded at four workers (12 exclusions). Their evidence is retained; this pass does not claim to fix parallel cancellation.

Three abstract SMT obligations passed. The combined automatic first-delimiter proof timed out; delimiter discovery is covered by a manual induction argument, not claimed as an SMT success. Data::Dumper behavior relies on its documented contract plus differential checks. See [formal boundaries and source correspondence](../verification/single-core-followup-contracts.md). This is not whole-program verification.

Other priorities reviewed: fill-fs still launches tabix separately for each masked query; replacing that with a bounded bulk-query implementation needs tests for overlapping/duplicate masks, output order and partial failures. No such change is included here. Consensus and sort differences in the preceding subsecond cases are too small to establish a regression.

Validated generated outputs totaling 81,949,020 bytes were removed. Shared source datasets and the small failed-control evidence remain. Scheduler/build logs have trailing whitespace stripped for archival only; full compared data was not normalized that way.
