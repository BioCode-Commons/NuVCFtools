# All tools versus upstream VCFtools

This is the pre-pool baseline report. See [the current 23-tool Perl round](parallel-perl-tools.md) for ordered-worker results and updated implementation coverage. The measurements below retain their original revisions and memory definitions.

Audited branch: `codex/common-tool-speed-round2`, source HEAD `2f4c35e2627c0bff2f9e6887e67779d437927d2c`. Upstream: `1f87a83402ffd17ea2723a456b7edf5d80b4a22c`.

There are **25 installed entrypoints: 24 Perl scripts and one C++ executable**. Twenty have at least one direct upstream timing comparison; five do not. Nineteen entrypoints have targeted source work since the inventory baseline, which is a different count from measured speedups. A changed shared parser does not establish a new result for every consumer.

**These are the latest available measurements for retained implementations, not a fresh benchmark of every command at the final HEAD.** The last Perl round used progressive snapshots; the final site-parser guard was timed only for ploidy. Earlier results retain the source, input, options, resources and validation limits in their linked reports. No speedups from separate rounds are multiplied together.

Wall time includes startup, input reading/decompression, analysis and complete output writing. Preparation/index building and output comparison are excluded. RSS is GNU time's maximum accounted process/child RSS in MiB, not the summed RAM of simultaneous processes. Most results are single runs; tiny differences do not establish acceleration. Most real inputs are 22,382 chr22 records with GT-only sample fields, not whole-genome or all-FORMAT benchmarks.

## Coverage of every installed tool

| Tool | Direct upstream performance evidence | Existing computation workers | Output-validation scope |
| --- | --- | --- | --- |
| `vcftools` | [18 configurations listed below](parallel-ld-20261126.md) | Only --geno-chisq --ld-threads N | Full scientific output passed in cited snapshots; not a claim about all options |
| `fill-aa` | [No ancestral-data timing](remaining-perl-20261127.md) | None | Deterministic reference controls against upstream; no real-data timed comparison |
| `fill-an-ac` | [1 configurations listed below](remaining-perl-20261127.md) | None | Full scientific output passed in cited snapshots; not a claim about all options |
| `fill-fs` | [4 configurations listed below](remaining-perl-20261127.md) | None | Full scientific output passed in cited snapshots; not a claim about all options |
| `fill-ref-md5` | [1 configurations listed below](remaining-perl-20261127.md) | None | Full scientific output passed in cited snapshots; not a claim about all options |
| `vcf-annotate` | [No direct upstream timing](intersection-interval-20261126.md) | None | Full bytes versus preceding Nu only |
| `vcf-compare` | [2 configurations listed below](perl-query-compare-20261121.md) | None | Full scientific output passed in cited snapshots; not a claim about all options |
| `vcf-concat` | [No direct upstream timing](common-speed-concat-20261126.md) | None | Full bytes versus preceding Nu only |
| `vcf-consensus` | [1 configurations listed below](remaining-perl-20261127.md) | None | Full scientific output passed in cited snapshots; not a claim about all options |
| `vcf-contrast` | [No direct upstream timing; synthetic performance only](contrast-background-index-20261126.md) | None | Previous Nu comparison excludes generated source header; not full raw-byte upstream validation |
| `vcf-convert` | [1 configurations listed below](remaining-perl-20261127.md) | None | Full scientific output passed in cited snapshots; not a claim about all options |
| `vcf-fix-newlines` | [1 configurations listed below](remaining-perl-20261127.md) | None | Full scientific output passed in cited snapshots; not a claim about all options |
| `vcf-fix-ploidy` | [3 configurations listed below](remaining-perl-20261127.md) | None | Full scientific output passed in cited snapshots; not a claim about all options |
| `vcf-indel-stats` | [1 configurations listed below](remaining-perl-20261127.md) | None | Full scientific output passed in cited snapshots; not a claim about all options |
| `vcf-isec` | [No direct upstream timing](intersection-interval-20261126.md) | None | Full bytes versus preceding Nu only |
| `vcf-merge` | [2 configurations listed below](merge-query-subset-20261126.md) | None | Full scientific output passed in cited snapshots; not a claim about all options |
| `vcf-phased-join` | [1 configurations listed below](remaining-perl-20261127.md) | None | Full scientific output passed in cited snapshots; not a claim about all options |
| `vcf-query` | [8 configurations listed below](merge-query-subset-20261126.md) | None | Full scientific output passed in cited snapshots; not a claim about all options |
| `vcf-shuffle-cols` | [1 configurations listed below](common-tool-speed-20261126.md) | None | Full scientific output passed in cited snapshots; not a claim about all options |
| `vcf-sort` | [2 configurations listed below](remaining-perl-20261127.md) | GNU sort -p N; existed upstream | Full scientific output passed in cited snapshots; not a claim about all options |
| `vcf-stats` | [2 configurations listed below](common-tools-20261126.md) | None | Full scientific output passed in cited snapshots; not a claim about all options |
| `vcf-subset` | [5 configurations listed below](common-tool-speed-20261126.md) | None | Full scientific output passed in cited snapshots; not a claim about all options |
| `vcf-to-tab` | [2 configurations listed below](remaining-perl-20261127.md) | None | Full scientific output passed in cited snapshots; not a claim about all options |
| `vcf-tstv` | [1 configurations listed below](remaining-perl-20261127.md) | None | Full scientific output passed in cited snapshots; not a claim about all options |
| `vcf-validator` | [1 configurations listed below](common-tool-speed-20261126.md) | None | Full scientific output passed in cited snapshots; not a claim about all options |

## Recorded end-to-end measurements

Original and Nu RSS are shown separately. “Nu” means the measured retained implementation, with the snapshot qualification above. Parallel LD compares one upstream core against the stated Nu core count. All rows passed scientific output comparison in their cited campaigns; details below explain equality chains and date handling.

| Tool/task | Input / mode | Original s | Nu s | Speedup | Original RSS MiB | Nu RSS MiB | Resources | Output / evidence |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| vcf-query sample + GT (default) | 500 samples | 52.20 | 17.28 | 3.02× | 10.875 | 10.875 | 1 / 1 physical cores (Original / measured Nu) | [Passed](merge-query-subset-20261126.md) |
| vcf-query sample + GT (--reuse-sample-templates) | 500 samples | 52.20 | 6.87 | 7.60× | 10.875 | 10.500 | 1 / 1 physical cores (Original / measured Nu) | [Passed](merge-query-subset-20261126.md) |
| vcf-query raw GT (default) | 500 samples | 24.20 | 11.78 | 2.05× | 10.500 | 10.500 | 1 / 1 physical cores (Original / measured Nu) | [Passed](merge-query-subset-20261126.md) |
| vcf-query raw GT (--reuse-sample-templates) | 500 samples | 24.20 | 5.92 | 4.09× | 10.500 | 10.500 | 1 / 1 physical cores (Original / measured Nu) | [Passed](merge-query-subset-20261126.md) |
| vcf-query sample + GT (default) | 2504 samples | 269.69 | 88.37 | 3.05× | 13.125 | 13.125 | 1 / 1 physical cores (Original / measured Nu) | [Passed](merge-query-subset-20261126.md) |
| vcf-query sample + GT (--reuse-sample-templates) | 2504 samples | 269.69 | 32.37 | 8.33× | 13.125 | 12.000 | 1 / 1 physical cores (Original / measured Nu) | [Passed](merge-query-subset-20261126.md) |
| vcf-query raw GT (default) | 2504 samples | 121.45 | 59.76 | 2.03× | 12.000 | 12.375 | 1 / 1 physical cores (Original / measured Nu) | [Passed](merge-query-subset-20261126.md) |
| vcf-query raw GT (--reuse-sample-templates) | 2504 samples | 121.45 | 28.41 | 4.27× | 12.000 | 11.625 | 1 / 1 physical cores (Original / measured Nu) | [Passed](merge-query-subset-20261126.md) |
| vcf-subset | 500 → half retained | 62.28 | 21.97 | 2.83× | 10.500 | 10.875 | 1 / 1 physical cores (Original / measured Nu) | [Passed](merge-query-subset-20261126.md) |
| vcf-merge | 500 samples, two input files | 80.20 | 41.58 | 1.93× | 14.625 | 14.250 | 1 / 1 physical cores (Original / measured Nu) | [Passed](merge-query-subset-20261126.md) |
| vcf-subset | 2504 → half retained | 323.36 | 108.55 | 2.98× | 12.000 | 11.625 | 1 / 1 physical cores (Original / measured Nu) | [Passed](merge-query-subset-20261126.md) |
| vcf-merge | 2504 samples, two input files | 533.13 | 281.75 | 1.89× | 15.375 | 15.750 | 1 / 1 physical cores (Original / measured Nu) | [Passed](merge-query-subset-20261126.md) |
| vcf-stats | 500 samples | 100.92 | 23.32 | 4.33× | 26.250 | 26.625 | 1 / 1 physical cores (Original / measured Nu) | [Passed](common-tools-20261126.md) |
| vcf-stats | 2504 samples | 658.31 | 141.03 | 4.67× | 88.621 | 88.422 | 1 / 1 physical cores (Original / measured Nu) | [Passed](common-tools-20261126.md) |
| vcftools --relatedness2 | 500 samples | 35.09 | 1.37 | 25.61× | 11.250 | 7.125 | 1 / 1 physical cores (Original / measured Nu) | [Passed](common-tools-20261126.md) |
| vcftools --relatedness2 | 2504 → keep 500 | 59.19 | 3.06 | 19.34× | 149.250 | 7.500 | 1 / 1 physical cores (Original / measured Nu) | [Passed](common-tools-20261126.md) |
| vcftools --relatedness | 500 samples | 5.81 | 3.19 | 1.82× | 9.000 | 7.125 | 1 / 1 physical cores (Original / measured Nu) | [Passed](common-tools-20261126.md) |
| vcftools --relatedness | 2504 → keep 500 | 16.74 | 5.04 | 3.32× | 101.625 | 7.500 | 1 / 1 physical cores (Original / measured Nu) | [Passed](common-tools-20261126.md) |
| vcftools --freq | 2504 samples | 4.72 | 2.98 | 1.58× | 5.625 | 5.250 | 1 / 1 physical cores (Original / measured Nu) | [Passed](common-tool-speed-20261126.md) |
| vcftools --missing-indv | 2504 samples | 4.57 | 3.06 | 1.49× | 5.625 | 5.250 | 1 / 1 physical cores (Original / measured Nu) | [Passed](common-tool-speed-20261126.md) |
| vcftools --missing-site | 2504 samples | 4.73 | 3.17 | 1.49× | 5.625 | 5.250 | 1 / 1 physical cores (Original / measured Nu) | [Passed](common-tool-speed-20261126.md) |
| vcftools --het | 2504 samples | 5.16 | 3.47 | 1.49× | 5.625 | 5.625 | 1 / 1 physical cores (Original / measured Nu) | [Passed](common-tool-speed-20261126.md) |
| vcftools VCF rewrite | 2504 samples | 17.81 | 7.06 | 2.52× | 5.625 | 5.625 | 1 / 1 physical cores (Original / measured Nu) | [Passed](common-tool-speed-20261126.md) |
| vcftools filter + rewrite | 2504 samples | 20.54 | 8.12 | 2.53× | 6.000 | 5.625 | 1 / 1 physical cores (Original / measured Nu) | [Passed](common-tool-speed-20261126.md) |
| vcf-validator | 100 samples | 19.70 | 12.62 | 1.56× | 10.500 | 10.500 | 1 / 1 physical cores (Original / measured Nu) | [Passed](common-tool-speed-20261126.md) |
| vcf-shuffle-cols | 2504 samples, reversed | 15.69 | 13.18 | 1.19× | 12.000 | 11.625 | 1 / 1 physical cores (Original / measured Nu) | [Passed](common-tool-speed-20261126.md) |
| vcftools --geno-r2 | 100 samples, 1 kb window | 5.01 | 0.84 | 5.96× | 4.875 | 11.250 | 1 / 1 physical cores (Original / measured Nu) | [Passed](common-tool-speed-20261126.md) |
| vcftools --hap-r2 | 100 samples, 1 kb window | 5.66 | 1.32 | 4.29× | 4.500 | 11.250 | 1 / 1 physical cores (Original / measured Nu) | [Passed](common-tool-speed-20261126.md) |
| vcftools --geno-chisq | 500 samples, 1 kb window | 159.09 | 6.97 | 22.82× | 5.625 | 5.625 | 1 / 1 physical cores (Original / measured Nu) | [Passed](parallel-ld-20261126.md) |
| vcftools --geno-chisq | 500 samples, 1 kb window | 159.09 | 2.62 | 60.72× | 5.625 | 6.805 | 1 / 4 physical cores (Original / measured Nu) | [Passed](parallel-ld-20261126.md) |
| vcftools --geno-chisq | 500 samples, 1 kb window | 159.09 | 1.88 | 84.62× | 5.625 | 11.652 | 1 / 8 physical cores (Original / measured Nu) | [Passed](parallel-ld-20261126.md) |
| vcftools --geno-chisq | 2504 samples, 1 kb window | 772.98 | 28.65 | 26.98× | 6.000 | 5.625 | 1 / 1 physical cores (Original / measured Nu) | [Passed](parallel-ld-20261126.md) |
| vcftools --geno-chisq | 2504 samples, 1 kb window | 772.98 | 10.20 | 75.78× | 6.000 | 8.020 | 1 / 4 physical cores (Original / measured Nu) | [Passed](parallel-ld-20261126.md) |
| vcftools --geno-chisq | 2504 samples, 1 kb window | 772.98 | 7.14 | 108.26× | 6.000 | 15.633 | 1 / 8 physical cores (Original / measured Nu) | [Passed](parallel-ld-20261126.md) |
| vcf-compare | 100 samples | 9.13 | 7.85 | 1.16× | 14.620 | 14.250 | 1 / 1 physical cores (Original / measured Nu) | [Passed](perl-query-compare-20261121.md) |
| vcf-compare | 400 samples | 34.85 | 29.43 | 1.18× | 14.620 | 14.620 | 1 / 1 physical cores (Original / measured Nu) | [Passed](perl-query-compare-20261121.md) |
| vcf-to-tab | 500 samples | 38.24 | 11.78 | 3.25× | 10.500 | 10.500 | 1 physical core per version | [Passed](remaining-perl-20261127.md) |
| vcf-to-tab | 2,504 samples | 209.43 | 65.68 | 3.19× | 11.250 | 11.250 | 1 physical core per version | [Passed](remaining-perl-20261127.md) |
| fill-fs | 500 samples, 1 MiB prefetch | 21.25 | 1.59 | 13.36× | 10.875 | 16.125 | 1 physical core per version | [Passed](remaining-perl-20261127.md) |
| fill-fs | 2,504 samples, 1 MiB prefetch | 26.85 | 6.10 | 4.40× | 10.875 | 16.500 | 1 physical core per version | [Passed](remaining-perl-20261127.md) |
| fill-ref-md5 | chr22 reference | 3.33 | 0.85 | 3.92× | 54.109 | 54.082 | 1 physical core per version | [Passed](remaining-perl-20261127.md) |
| vcf-convert | 500-sample SNPs | 38.22 | 25.65 | 1.49× | 11.250 | 11.625 | 1 physical core per version | [Passed](remaining-perl-20261127.md) |
| vcf-phased-join | 500 samples | 6.07 | 5.33 | 1.14× | 64.500 | 64.500 | 4 physical cores allocated per version; serial analysis except explicit sort -p setting | [Passed](remaining-perl-20261127.md) |
| vcf-fix-ploidy | 500, pass-through | 1.08 | 0.34 | 3.18× | 10.500 | 10.500 | 1 physical core per version | [Passed](remaining-perl-20261127.md) |
| vcf-fix-ploidy | 2,504, pass-through | 4.81 | 1.07 | 4.50× | 12.000 | 12.000 | 1 physical core per version | [Passed](remaining-perl-20261127.md) |
| vcf-fix-ploidy | 500, active conversion | 41.63 | 42.02 | 0.99× | 10.500 | 10.875 | 1 physical core per version | [Passed](remaining-perl-20261127.md) |
| fill-fs | default cache, 500 | 26.82 | 24.47 | 1.10× | 10.875 | 10.875 | 1 physical core per version | [Passed](remaining-perl-20261127.md) |
| fill-fs | external mask, 100 kb | 56.59 | 53.94 | 1.05× | 10.875 | 10.500 | 1 physical core per version | [Passed](remaining-perl-20261127.md) |
| fill-an-ac | 500 | 30.43 | 21.64 | 1.41× | 10.500 | 10.500 | 4 physical cores allocated per version; serial analysis except explicit sort -p setting | [Passed](remaining-perl-20261127.md) |
| vcf-consensus | one selected sample | 1.03 | 1.07 | 0.96× | 14.625 | 14.625 | 4 physical cores allocated per version; serial analysis except explicit sort -p setting | [Passed](remaining-perl-20261127.md) |
| vcf-fix-newlines | CRLF, 500 | 0.08 | 0.08 | 1.00× | 6.000 | 6.000 | 4 physical cores allocated per version; serial analysis except explicit sort -p setting | [Passed](remaining-perl-20261127.md) |
| vcf-indel-stats | explicit interval | 0.21 | 0.21 | 1.00× | 10.125 | 10.125 | 4 physical cores allocated per version; serial analysis except explicit sort -p setting | [Passed](remaining-perl-20261127.md) |
| vcf-tstv | 500 | 0.19 | 0.18 | 1.06× | 6.000 | 5.625 | 4 physical cores allocated per version; serial analysis except explicit sort -p setting | [Passed](remaining-perl-20261127.md) |
| vcf-sort | shuffled 2,504, -p 1 | 1.27 | 1.20 | 1.06× | 9.195 | 9.352 | 4 physical cores allocated per version; serial analysis except explicit sort -p setting | [Passed](remaining-perl-20261127.md) |
| vcf-sort | shuffled 2,504, -p 4 | 1.21 | 1.21 | 1.00× | 15.250 | 15.285 | 4 physical cores allocated per version; serial analysis except explicit sort -p setting | [Passed](remaining-perl-20261127.md) |
| vcf-subset, all samples | 100 samples | 29.39 | 10.96 | 2.68× | 10.500 | 10.500 | 1 physical core per version | [Passed](common-tool-speed-20261126.md) |
| vcf-subset, SNP/indel selection | 100 samples | 23.17 | 6.46 | 3.59× | 10.500 | 10.500 | 1 physical core per version | [Passed](common-tool-speed-20261126.md) |
| vcf-subset, private variants in 10 samples | 100 samples | 14.66 | 5.17 | 2.84× | 10.500 | 10.500 | 1 physical core per version | [Passed](common-tool-speed-20261126.md) |

The five unmeasured upstream comparisons appear in the coverage table with no invented timing, RSS or ratio. The machine-readable table is [all-tools-vs-upstream.json](all-tools-vs-upstream.json).

- Query's `--reuse-sample-templates` is opt-in; default and opt-in rows are separate.
- fill-fs's 1 MiB prefetch compares the old 1,024-base default with an explicit larger reference cache. The faster setting uses more RSS and can change contig-end truncation-warning granularity. It is not a default-mode gain.
- Ploidy pass-through and active genotype conversion are different tasks; active conversion did not speed up over upstream.
- Statistics and final parallel LD establish upstream output equality through an unchanged, byte-compared intermediate version. Their final timing and upstream timing are from different jobs, detailed in the reports.
- The 2,504-sample merge validation replay held the generated UTC date equal to Original and then matched all stdout bytes. The replay time is not substituted for the measured end-to-end time.
- Reported “Passed” covers complete scientific outputs, order and duplicates under each campaign's settings. Diagnostic normalization, where used, is described in the linked report. It is not proof of equality for all inputs.

## Parallelism audit at the recorded baseline

At upstream, **24/25 entrypoints have no computational worker pool**. GNU sort supplies the existing parallel computation for `vcf-sort`. At the recorded baseline, **23/25 have no computational worker pool**; `vcftools --geno-chisq` adds ordered workers. Other C++ modes remain serial.

The audit searched both upstream and current installed source for threads, fork, OpenMP, process-pool APIs and parallel options, and inspected the matches:

- `src/cpp/variant_file_ld_parallel.cpp` creates workers and joins them; `parameters.cpp` restricts `--ld-threads` to genotype chi-square file output.
- `src/perl/vcf-sort` forwards `-p` / `--parallel-sort` to external GNU sort. This is genuine parallel sorting, although the Perl wrapper has no worker pool.
- `src/perl/vcf-validator` uses one child in unique-message mode while the parent drains and deduplicates diagnostics. This does not distribute record validation among workers.
- Bundled `bgzf.c` contains pthread-based `bgzf_mt`, but there is no caller in either version's application source. Its presence is not evidence of active parallel compression.
- gzip, tabix, samtools and multi-input readers can run as child pipelines. This is distinct from splitting the analysis across workers. Running several independent tool invocations concurrently improves throughput, not the latency of a single invocation.

## First parallel targets

Prioritize independent record transforms: **vcf-to-tab, vcf-query and vcf-subset**, followed by merge only after defining compatible handling of positions spanning chunk boundaries. An ordered bounded process pool can retain one header, bounded in-flight data, exact record order, per-record diagnostics and error exits. Workers must reuse the existing transform and parser rather than implement a second set of VCF rules. Measure IPC, decompression, output writing, worker-inclusive memory and temporary disk use as part of end-to-end execution.

Statistics needs a separate deterministic reduction design. Phase joining, consensus and clustered flank annotation carry state across records; splitting arbitrary chunks would change their semantics. Short commands such as newline conversion and tstv should not acquire workers before input size and startup/I/O measurements justify them.

Fourfold acceleration for every tool is not supported by current results. For example, the retained shuffled-input sort takes 1.20 s with one sort thread and 1.21 s with four; RSS rises from 9.352 to 15.285 MiB. In contrast, larger chi-square LD improves from 28.65 s at one worker to 7.14 s at eight (4.01× additional gain). The 108.26× ratio to upstream includes earlier algorithm improvements and the increased core count.

## Provenance correction

Two earlier metadata locations contained a malformed upstream commit string. The valid upstream commit above is present in Git, and all 24 saved upstream installed Perl script SHA256 values match its source bytes. The identity audit is included in the JSON companion. This corrects source attribution only; no measurements or validation outcomes were changed. Original native binary identity remains in its original campaign manifests; this Perl audit does not infer a native binary identity from source hashes.
