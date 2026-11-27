# Perl tool memory worklist

The scope below is the 23 commands in the [Perl comparison](parallel-perl-tools.md). A command's worker setting does not imply all its modes are independent. C++ subcommands and GNU-sort-backed `vcf-sort` retain their separate evidence in the [all-entrypoint report](all-tools-vs-upstream.md).

This is a source audit and worklist, not a performance claim. Keep measurements tied to exact inputs/options and frozen source manifests. Do not treat SIMD, more workers or smaller batches as automatic improvements.

| Command | Current storage / execution | Next useful target or constraint |
| --- | --- | --- |
| fill-aa | Serial; reference sequence chunks and shared immutable FAI metadata | Measure sequence-cache residency across many contigs; preserve first-query errors and out-of-bounds diagnostics. |
| fill-an-ac | Ordered workers; mutable genotype records | Packed-column experiment rejected after small, inconsistent gains; inspect mutable-record ownership next. |
| fill-fs | Parent maintains ordered variant/mask window; workers format prepared records | Measure mask-window and per-worker reference chunk residency; splitting arbitrary coordinate intervals changes boundary behavior. |
| fill-ref-md5 | Missing contigs are independent tasks; external reference readers | Measure multiple missing contigs; a one-contig fixture cannot assess parallel scaling. |
| vcf-annotate | Workers for record-local modes; ordered cursors for annotation/window filters | Window-state ownership remains the obstacle for broader parallel modes. |
| vcf-compare | Parent groups positions; worker-local counters; ordered replay | Duplicate queue text removed and counter indices packed: PSS −28.7% this round. |
| vcf-concat | Ordered source-head tree; sliding open-file window and external readers | Reader count/buffer overhead; retain the exact `-s` window, file ties and diagnostic order. |
| vcf-consensus | Sequential reference/variant stream and output buffer | Bound FASTA buffering while retaining overlaps, case, wrapping and offsets; no measured new change yet. |
| vcf-contrast | GT membership indexes; PL mode retains per-background data | Profile PL mode separately; preserve score/tie rules before regrouping arithmetic. |
| vcf-convert | Ordered workers; mutable records | Packed-column experiment rejected; no shared mutable sample hashes. |
| vcf-fix-newlines | Ordered batches; per-record newline conversion | For cheap transformations fork/spool cost can exceed the work; inspect chunk representation before adding concurrency. |
| vcf-fix-ploidy | Ordered record workers | Batch wrapper and temporary genotype allocations; retain policy interval semantics. |
| vcf-indel-stats | Ordered batches; interval/read state stays ordered | Existing subsecond case does not establish a compute hotspot; measure a useful indel-rich task first. |
| vcf-isec | Exact membership structures per group; ordered output | Distinct-key storage and reader buffers; preserve multiplicities, file order and split-mode behavior. |
| vcf-merge | Compact queued genotypes; reader metadata inherited once | Previous round reduced sampled PSS 253→141 MiB at 16 workers; next measure current-position expansion on rich FORMAT data. |
| vcf-phased-join | Workers score overlaps; ordered floating-point accumulation | Overlap storage; do not reorder floating-point additions or randomization state. |
| vcf-query | Array parser; shared rendering templates for equal full sample fields | Per-record sample/output-template storage for mostly distinct fields. |
| vcf-shuffle-cols | Ordered raw-line batches and column permutation | Per-record arrays and output copies; permutation and missing-column behavior must remain exact. |
| vcf-stats | Read-only genotype sharing; ordered integer reduction | Packed event indices reduced PSS 14.5%; measure distinct FORMAT fields separately. |
| vcf-subset | Mutable selected-sample records | Packed-column experiment rejected; private-allele mode still needs excluded samples. |
| vcf-to-tab | Read-only records; ordered formatting | Packed-column experiment rejected; output volume may dominate after parsing is reduced. |
| vcf-tstv | Small record-local work | Prior measured case is subsecond; process overhead dominated, so more workers are not a justified next step. |
| vcf-validator | Serial; successful validation reuse and ordered message grouping | Rich FORMAT/diagnostic-heavy cases, rather than adding worker heaps to a low-memory clean-input path. |

For each retained change: run bounded semantic checks, preserve complete output bytes/order/duplicates, compare actual outputs end to end, and record wall time plus whole-process-tree RSS/PSS. Keep index construction outside tool measurements. Diagnostic normalization must be explicit and limited to runtime/source metadata, not biological values. SMT models cover only their stated contracts; they are not whole-program proofs.

Delete large outputs after full comparison passes. Preserve failed output until the discrepancy is understood; retain small metadata, harnesses and source identities. Reuse input/index files rather than creating another full dataset copy for each tool.
