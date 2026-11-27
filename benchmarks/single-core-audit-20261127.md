# Single-core audit of all installed commands

Scope: the 24 scripts listed in `src/perl/Makefile.am`, plus the C++ `vcftools` executable. This is one optimization pass across every entrypoint, not a claim that every option has been optimized or measured. The numerical table is generated from the retained Oscar runs. Source changes stay on `codex/common-tool-speed-round2`.

| Command | Work in this pass / retained implementation | Boundary to preserve |
| --- | --- | --- |
| fill-aa | Reviewed the site-only reader and shared immutable FAI dictionary. No new command-specific change. | Reference cache boundaries, out-of-bounds behavior, original sample suffix. |
| fill-an-ac | Borrow owned input columns during decoding; defer worker dependencies. | Mutable genotype records remain independent; allele counts and formatting unchanged. |
| fill-fs | Defer worker dependencies. Retain interval lookup and bounded reference access. | Cluster windows and overlapping masks carry state; arbitrary record splitting is invalid. |
| fill-ref-md5 | Bounded sequence chunks instead of one digest call per FASTA line; defer worker dependencies. | Same sequence bytes, reference lengths, digest, dictionary and reheadered VCF. |
| vcf-annotate | Linear delimiter cursors in the shared genotype splitter; defer worker dependencies. Reviewed existing HWE count reuse and annotation interval index. | Preserve duplicate annotation order, overlap windows and warning sequence. |
| vcf-compare | Use the read-only genotype representation; defer worker dependencies. | Outer sample remapping must not mutate shared genotype values. |
| vcf-concat | Reviewed existing tournament merge and cached file heads. No new command-specific change. | `-s` is a sliding file window, not a global sort. |
| vcf-consensus | Linear delimiter cursors in the shared genotype splitter; reviewed existing prefix compaction after output wrapping. No new command-specific change. | Overlapping variants, reference case, coordinates and FASTA wrapping are stateful. |
| vcf-contrast | Linear delimiter cursors in the shared genotype splitter; defer worker dependencies. Retain exact background genotype/allele indexes. | PL scoring still compares likelihood vectors; GT-only gains do not establish PL performance. |
| vcf-convert | Borrow owned input columns; defer worker dependencies. | Decoded genotype hashes stay mutable and unshared. Missing values and VCF-version conversions retain their order. |
| vcf-fix-newlines | Bounded single-worker chunks with a carried CR; defer worker dependencies. | Existing initial detection/first-record behavior and CR/CRLF boundaries. |
| vcf-fix-ploidy | Linear delimiter cursors in the shared genotype splitter; defer worker dependencies; reviewed per-record ploidy and likelihood loops. | Likelihood tie-breaking, missing values and per-sample removal counts. No new likelihood algorithm is claimed. |
| vcf-indel-stats | Defer worker dependencies. Retain the existing monotone interval cursor. | Sorted-input checks and the original treatment of overlapping regions. |
| vcf-isec | Replace pairwise header checks with checks against the first accepted VCF; defer worker dependencies. | Same earliest mismatching pair and warning; non-VCF readers are skipped. Header check O(F²C) becomes O(FC). |
| vcf-merge | Defer worker dependencies. Reviewed existing merge selection and compact allele-index mappings. | Same-position grouping, REF padding, ALT ordering and Number=A/R/G remapping. |
| vcf-phased-join | Linear delimiter cursors in the shared genotype splitter; defer worker dependencies. Retain existing overlap scoring. | Phase decisions and accumulated overlap state cannot be partitioned at arbitrary records. |
| vcf-query | Defer worker dependencies. Reviewed existing FORMAT index/value caches and optional shared rendering templates. | Field-major diagnostics and sample-name insertion order. Default and opt-in template modes are distinct. |
| vcf-shuffle-cols | Compile the gather order once and join an array slice for complete rows; defer worker dependencies. | Undefined/truncated mappings retain original diagnostics; duplicate selections and first-column behavior remain. |
| vcf-sort | Raw-chunk forwarding trial showed no material gain and was reverted. GNU sort remains unchanged and runs with one thread. | Exact remaining bytes, sort keys, duplicate behavior and header position. |
| vcf-stats | Owned columns in the shared decoder and deferred worker dependencies. Retain direct serial counters. | Filter-specific counters, hash insertion order and unsorted dump output. |
| vcf-subset | Borrow owned input columns; defer worker dependencies. | Selected mutable genotype records, private-site checks, ALT trimming and sample order. |
| vcf-to-tab | Sort unique header sample names once, filter by actual record membership and borrow owned columns. | Missing/empty samples, duplicate names, IUPAC errors and first-record header output. |
| vcf-tstv | Direct serial accumulation through the same classification body; defer worker dependencies. | Original classification, counts and fixed output order. |
| vcf-validator | Defer IPC/selector modules to unique-message mode. Retain read-only record validation. | Diagnostic content/order/count, partial output and unique-message grouping. |
| vcftools | Reviewed shared genotype parsing, bitset LD and block-based frequency/relatedness storage; native source unchanged in this pass. Rebuild and measure six named modes. | Bitwise output ordering and floating-point reduction order. No extrapolation from six modes to every C++ option. |

No filename, sample identity, allele-frequency threshold or HG002-specific rule selects these paths. Ownership and complete-column guards are semantic preconditions. Repeated-field reuse already present in the branch is exact, but its benefit naturally varies with the input.

Formal evidence has limited scope: the SMT obligations concern stable reads, ordered output construction, newline state transitions, counter transitions, header equality, digest feed and delimiter cursor invariants. Connecting the source to those models remains a manual argument. End-to-end comparisons and malformed-input controls test the implementation; neither establishes whole-program equivalence for arbitrary Perl extensions, I/O failures or all biological inputs.

The shared genotype splitter now scans each delimiter range once, reducing its worst-case scanning cost from quadratic to linear in string length. All five installed callers were retested. This is an algorithmic bound improvement; their ordinary diploid end-to-end times did not materially improve.
