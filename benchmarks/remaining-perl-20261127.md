# Remaining Perl tools: measured changes and limits

This round examines the thirteen entrypoints previously listed without targeted work since the inventory baseline. All changes remain on `codex/common-tool-speed-round2`.

The frozen before version is `f7b152dfb10e674c65f2fa016409f61a65c7bedb`. Upstream is VCFtools `1f87a83402ffd17ea2723a456b7edf5d0a12db19895ac4fe52f9240468`. Each table row is a single end-to-end run per version; small differences may reflect run-to-run variation. Shared-module improvements already present in Before are included in comparisons against upstream; the Before column isolates this round's contribution.

Retained code commit: `3fafbf1069bdcd43fe8e9e71eca4af88b80cd450`. The [manifest](remaining-perl-20261127/manifest.json) records hashes for every measured snapshot. The final terminal-character guard in site-only parsing was measured in the ploidy continuation; earlier fill-fs rows retain their measured snapshot.

## Measured retained work

| Task | Original (s) | Before (s) | Measured candidate (s) | vs Original | vs Before | RSS Original → Before → candidate (MiB) | Full output |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| vcf-to-tab, 500 samples | 38.24 | 36.41 | 11.78 | 3.25× | 3.09× | 10.500 → 10.500 → 10.500 | Passed |
| vcf-to-tab, 2,504 samples | 209.43 | 203.69 | 65.68 | 3.19× | 3.10× | 11.250 → 12.000 → 11.250 | Passed |
| fill-fs, 500 samples, 1 MiB prefetch | 21.25 | 21.59 | 1.59 | 13.36× | 13.58× | 10.875 → 10.500 → 16.125 | Passed |
| fill-fs, 2,504 samples, 1 MiB prefetch | 26.85 | 27.02 | 6.10 | 4.40× | 4.43× | 10.875 → 11.250 → 16.500 | Passed |
| fill-ref-md5, chr22 reference | 3.33 | 3.26 | 0.85 | 3.92× | 3.84× | 54.109 → 53.988 → 54.082 | Passed |
| vcf-convert, 500-sample SNPs | 38.22 | 27.93 | 25.65 | 1.49× | 1.09× | 11.250 → 11.625 → 11.625 | Passed |
| vcf-phased-join, 500 samples | 6.07 | 5.98 | 5.33 | 1.14× | 1.12× | 64.500 → 64.500 → 64.500 | Passed |
| vcf-fix-ploidy, 500, pass-through | 1.08 | 1.08 | 0.34 | 3.18× | 3.18× | 10.500 → 10.875 → 10.500 | Passed |
| vcf-fix-ploidy, 2,504, pass-through | 4.81 | 4.78 | 1.07 | 4.50× | 4.47× | 12.000 → 11.625 → 12.000 | Passed |
| vcf-fix-ploidy, 500, active conversion | 41.63 | 43.15 | 42.02 | 0.99× | 1.03× | 10.500 → 10.875 → 10.875 | Passed |

The prefetch rows compare the old 1,024-base default against the new explicit `--reference-cache-size 1048576` setting. They are a memory/time tradeoff, not a default-mode speedup. Active ploidy conversion is effectively unchanged; the substantial gain applies to records outside the configured conversion regions. `fill-aa` has functional coverage but no ancestral-data timing claim. Most RSS values are unchanged, and reference prefetch increases them.

## Other measured cases

| Task | Original (s) | Before (s) | Measured candidate (s) | vs Original | vs Before | RSS Original → Before → candidate (MiB) | Full output |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| fill-fs, default cache, 500 | 26.82 | 24.26 | 24.47 | 1.10× | 0.99× | 10.875 → 10.875 → 10.875 | Passed |
| fill-fs, external mask, 100 kb | 56.59 | 56.76 | 53.94 | 1.05× | 1.05× | 10.875 → 10.875 → 10.500 | Passed |
| fill-an-ac, 500 | 30.43 | 21.51 | 21.64 | 1.41× | 0.99× | 10.500 → 10.125 → 10.500 | Passed |
| vcf-consensus, one selected sample | 1.03 | 1.01 | 1.07 | 0.96× | 0.94× | 14.625 → 14.625 → 14.625 | Passed |
| vcf-fix-newlines, CRLF, 500 | 0.08 | 0.08 | 0.08 | 1.00× | 1.00× | 6.000 → 6.000 → 6.000 | Passed |
| vcf-indel-stats, explicit interval | 0.21 | 0.21 | 0.21 | 1.00× | 1.00× | 10.125 → 10.125 → 10.125 | Passed |
| vcf-tstv, 500 | 0.19 | 0.19 | 0.18 | 1.06× | 1.06× | 6.000 → 6.000 → 5.625 | Passed |
| vcf-sort, shuffled 2,504, -p 1 | 1.27 | 1.20 | 1.20 | 1.06× | 1.00× | 9.195 → 9.445 → 9.352 | Passed |
| vcf-sort, shuffled 2,504, -p 4 | 1.21 | 1.21 | 1.21 | 1.00× | 1.00× | 15.250 → 15.094 → 15.285 | Passed |

Shared improvements already present in Before account for the `fill-an-ac` gain over upstream; this round made no new `fill-an-ac` change. The six entrypoints kept unchanged are `fill-an-ac`, `vcf-consensus`, `vcf-fix-newlines`, `vcf-indel-stats`, `vcf-sort` and `vcf-tstv`. Subsecond differences and the few-percent changes in these single runs are not evidence of new acceleration.

The discarded sort block-copy trial measured 0.35 → 0.35 s (500 samples) and 1.52 → 1.50 s (2,504). On shuffled real records, the existing one-thread and four-thread sort modes took 1.20 and 1.21 s in the retained implementation; reported RSS rose from 9.352 to 15.285 MiB. Both used a four-core allocation. A separate synthetic delayed-child check confirmed the wrapper waited for child completion before returning.

## Scope

| Tool | Finding and action |
| --- | --- |
| `vcf-to-tab` | Reuse exact rendered GT values within a record and use the existing read-only sample parser. Preserve sample sorting and partial output on errors. |
| `fill-aa` | Keep FORMAT/sample columns as opaque text when adding INFO/AA; do not allocate a field per sample. Covered by deterministic reference-lookup controls. No real ancestral-genome throughput claim. |
| `fill-fs` | Same opaque suffix representation. Add optional `--reference-cache-size` to amortize `samtools faidx` launches. Default remains 1,024 bases. Mask queries are unchanged. |
| `vcf-fix-ploidy` | Delay splitting sample columns until a region actually requires sample-level work. The real chr22 benchmark measures default-policy pass-through; active conversion is checked separately. |
| `vcf-convert` | Build the non-GT conversion field list once per record. GT-only records skip a per-sample conversion loop that performs no conversion. |
| `vcf-phased-join` | Cache exact GT allele splits within each overlapping site; retain sample iteration and floating-point accumulation order. |
| `fill-ref-md5` | Compute the same streamed digest with `Digest::MD5`, removing a separate MD5 process and pipe. Full decompressed VCF, header and dictionary comparison passed. |
| `vcf-sort` | Rejected block-transfer trial: 1.52 → 1.50 s at 2,504 samples is not useful evidence of a gain. Restored the existing implementation. Existing `-p` parallel sorting is measured separately. |
| `fill-an-ac` | Already uses shared genotype counting/formatting improvements. Remeasure against upstream, without claiming a new command-specific change. |
| `vcf-consensus` | Sequence edits and overlap handling depend on prior variants. No unverified parallel partitioning introduced. |
| `vcf-fix-newlines` | Simple streaming transformation. Keep legacy detection and no-conversion behavior; measure CRLF conversion. |
| `vcf-indel-stats` | Already advances an interval cursor. No repeated all-region scan to replace. Benchmark uses an explicit interval, not an invented exon annotation. |
| `vcf-tstv` | Already scans only the mandatory fields. No sample-genotype work to parallelize. |

The previous inventory counted work since commit `2b84214`, not every difference from upstream. That starting commit already contains changes to `vcf-fix-ploidy` and `vcf-phased-join`; their previous "untargeted" classification did not mean their source was identical to upstream.

## Inputs and measurement

The real VCF inputs are the retained 1000 Genomes Phase 3 GRCh37 chr22:20,000,001–21,000,000 slice: 22,382 records with 500 or 2,504 samples and GT-only FORMAT fields. Conversion uses the biallelic SNP subset. Phased joining uses overlapping consecutive blocks, preserving the source genotypes. Consensus uses one source sample and the SNP subset.

Reference sequence comes from [Ensembl's GRCh37 chromosome FASTA directory](https://ftp.ensembl.org/pub/grch37/current/fasta/homo_sapiens/dna/), chromosome 22 only. Downloading, subsetting, decompressing the reference and indexing are preparation, excluded from tool measurements. Timed runs include input reading/decompression, analysis and full output writing. Each result records its command, source snapshot, node, and Slurm job.

Wall time is GNU time's elapsed time. Peak RSS is its process/child maximum, **not summed concurrent process-tree memory**. The to-tab, reference/conversion, MD5, prefetch and final ploidy jobs use one allocated physical core. The broader audit (including phase joining, fill-an-ac, consensus and the lightweight commands) and shuffled-sort jobs allocate four physical cores equally to all versions. Those Perl commands remain serial; the sort rows explicitly distinguish `-p 1` and `-p 4`. No new Perl worker pool is claimed.

## Output checks

Comparison reads all output bytes, without sorting or dropping VCF headers, sample columns or duplicate records. Scientific outputs are not verified by hashes alone. Compressed reheader outputs are compared after decompression; headers and dictionaries are also compared. Exit codes must match, and successful test cases must actually exit successfully. Diagnostic comparison normalizes installation paths, source-line locations and process-specific Perl reference addresses only.

A fixed test clock is used identically for all versions in the audit to hold autogenerated source-header dates constant. It does not affect GNU time or scientific calculations. The initial small negative-input trial exposed missing address normalization in the harness. Reference preparation separately exposed a missing input index; sequential target selection fixed preparation without changing product code. Both failures are retained in the evidence.

The reference prefetch setting changes fetch granularity and can therefore change `samtools` truncation warnings near contig ends. Its output-identity claim is limited to the tested cases; default cache behavior is unchanged. More prefetch uses more memory, and it does not remove per-record external mask queries.

## Validation and disposition

The final source passed 111 deterministic cases against each of upstream and Before (222 pairwise comparisons across three Perl hash seeds). Cases cover IUPAC and errors, haploid/missing GT, rich sample fields, VCF versions, trailing fields and newline handling, masks and clustered flanks, phase overlaps and thresholds, ploidy pass-through/active regions, MD5 headers/dictionaries, and reference prefetch. The read-only/mutable parser suite passed 55 assertions. This is regression testing, not a fuzzing campaign or a proof over all inputs.

All real-data rows shown above passed full output comparison. The broadening is seven edited entrypoints plus the shared parser; six of the thirteen examined entrypoints retain their old command implementation. Including earlier rounds, the inventory now has 19 entrypoints with targeted source work and six without it. This count describes source coverage, not 19 independently demonstrated speedups.

Slurm jobs: 9657902 (to-tab and sort trial), 9658000 (three completed reference/conversion cases, then an indexed-input setup failure), 9658142 (successful MD5-only continuation), 9658143 (other commands), 9658114 (prefetch), 9658166 (shuffled sort), 9658330 (final site parser and ploidy), and 9658499 (sort child lifecycle). The final control results are under `site-parser/controls-*`; accounting includes superseded setup/launcher failures and cancelled dependencies.

Verified timed outputs were removed after comparison. A further 162,291,025 bytes of redundant prepared inputs and the duplicate reference were removed during final cleanup; canonical input VCFs and the usable GRCh37 reference remain. [Cleanup record](remaining-perl-20261127/cleanup.json).
