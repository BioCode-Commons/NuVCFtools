# Current retained optimizations versus upstream

This is an inventory of the latest available measurements for implementations retained on `codex/common-tool-speed-round2`, not a fresh all-command benchmark of one final commit. Rows marked **current** were measured in the merge/query/subset continuation. Other rows retain their earlier source revisions, inputs and output-validation scope; shared-module changes do not establish new timing or correctness results for every consumer.

The installation has **25 entrypoints: one C++ executable and 24 Perl scripts**. Nineteen entrypoints have targeted source work; six have not. Source coverage does not imply nineteen measured speedups. C++ analysis flags below are tasks within one executable, not additional installed tools.

## Remaining Perl tools: new measurements

These measurements use progressive snapshots retained in the branch, with upstream and frozen `f7b152d` controls. See [the complete report](remaining-perl-20261127.md) for scope, RSS, original/before timings, controls and rejected changes. In particular, ploidy gains apply to pass-through records, and fill-fs gains require the explicit larger cache.

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

## Direct upstream comparisons

All ratios below are measured upstream wall time divided by measured optimized wall time. They are not products of speedups from separate rounds. `Cores` is upstream / optimized; multi-core chi-square results therefore include a resource increase. RSS is the GNU-time process/child maximum, not summed process-tree memory.

| Tool/task | Input | Cores | Original (s) | Optimized (s) | Speedup | RSS original → optimized (MiB) | Evidence |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| `vcf-query sample + GT (default)` | 500 samples | 1 / 1 | 52.20 | 17.28 | 3.02× | 10.875 → 10.875 | [current](merge-query-subset-20261126.md) |
| `vcf-query sample + GT (--reuse-sample-templates)` | 500 samples | 1 / 1 | 52.20 | 6.87 | 7.60× | 10.875 → 10.500 | [current](merge-query-subset-20261126.md) |
| `vcf-query raw GT (default)` | 500 samples | 1 / 1 | 24.20 | 11.78 | 2.05× | 10.500 → 10.500 | [current](merge-query-subset-20261126.md) |
| `vcf-query raw GT (--reuse-sample-templates)` | 500 samples | 1 / 1 | 24.20 | 5.92 | 4.09× | 10.500 → 10.500 | [current](merge-query-subset-20261126.md) |
| `vcf-query sample + GT (default)` | 2504 samples | 1 / 1 | 269.69 | 88.37 | 3.05× | 13.125 → 13.125 | [current](merge-query-subset-20261126.md) |
| `vcf-query sample + GT (--reuse-sample-templates)` | 2504 samples | 1 / 1 | 269.69 | 32.37 | 8.33× | 13.125 → 12.000 | [current](merge-query-subset-20261126.md) |
| `vcf-query raw GT (default)` | 2504 samples | 1 / 1 | 121.45 | 59.76 | 2.03× | 12.000 → 12.375 | [current](merge-query-subset-20261126.md) |
| `vcf-query raw GT (--reuse-sample-templates)` | 2504 samples | 1 / 1 | 121.45 | 28.41 | 4.27× | 12.000 → 11.625 | [current](merge-query-subset-20261126.md) |
| `vcf-subset` | 500 → half retained | 1 / 1 | 62.28 | 21.97 | 2.83× | 10.500 → 10.875 | [current](merge-query-subset-20261126.md) |
| `vcf-merge` | 500 samples, two input files | 1 / 1 | 80.20 | 41.58 | 1.93× | 14.625 → 14.250 | [current](merge-query-subset-20261126.md) |
| `vcf-subset` | 2504 → half retained | 1 / 1 | 323.36 | 108.55 | 2.98× | 12.000 → 11.625 | [current](merge-query-subset-20261126.md) |
| `vcf-merge` | 2504 samples, two input files | 1 / 1 | 533.13 | 281.75 | 1.89× | 15.375 → 15.750 | [current](merge-query-subset-20261126.md) |
| `vcf-stats` | 500 samples | 1 / 1 | 100.92 | 23.32 | 4.33× | 26.250 → 26.625 | [prior snapshot](common-tools-20261126.md) |
| `vcf-stats` | 2504 samples | 1 / 1 | 658.31 | 141.03 | 4.67× | 88.621 → 88.422 | [prior snapshot](common-tools-20261126.md) |
| `vcftools --relatedness2` | 500 samples | 1 / 1 | 35.09 | 1.37 | 25.61× | 11.250 → 7.125 | [prior snapshot](common-tools-20261126.md) |
| `vcftools --relatedness2` | 2504 → keep 500 | 1 / 1 | 59.19 | 3.06 | 19.34× | 149.250 → 7.500 | [prior snapshot](common-tools-20261126.md) |
| `vcftools --relatedness` | 500 samples | 1 / 1 | 5.81 | 3.19 | 1.82× | 9.000 → 7.125 | [prior snapshot](common-tools-20261126.md) |
| `vcftools --relatedness` | 2504 → keep 500 | 1 / 1 | 16.74 | 5.04 | 3.32× | 101.625 → 7.500 | [prior snapshot](common-tools-20261126.md) |
| `vcftools --freq` | 2504 samples | 1 / 1 | 4.72 | 2.98 | 1.58× | 5.625 → 5.250 | [prior snapshot](common-tool-speed-20261126.md) |
| `vcftools --missing-indv` | 2504 samples | 1 / 1 | 4.57 | 3.06 | 1.49× | 5.625 → 5.250 | [prior snapshot](common-tool-speed-20261126.md) |
| `vcftools --missing-site` | 2504 samples | 1 / 1 | 4.73 | 3.17 | 1.49× | 5.625 → 5.250 | [prior snapshot](common-tool-speed-20261126.md) |
| `vcftools --het` | 2504 samples | 1 / 1 | 5.16 | 3.47 | 1.49× | 5.625 → 5.625 | [prior snapshot](common-tool-speed-20261126.md) |
| `vcftools VCF rewrite` | 2504 samples | 1 / 1 | 17.81 | 7.06 | 2.52× | 5.625 → 5.625 | [prior snapshot](common-tool-speed-20261126.md) |
| `vcftools filter + rewrite` | 2504 samples | 1 / 1 | 20.54 | 8.12 | 2.53× | 6.000 → 5.625 | [prior snapshot](common-tool-speed-20261126.md) |
| `vcf-validator` | 100 samples | 1 / 1 | 19.70 | 12.62 | 1.56× | 10.500 → 10.500 | [prior snapshot](common-tool-speed-20261126.md) |
| `vcf-shuffle-cols` | 2504 samples, reversed | 1 / 1 | 15.69 | 13.18 | 1.19× | 12.000 → 11.625 | [prior snapshot](common-tool-speed-20261126.md) |
| `vcftools --geno-r2` | 100 samples, 1 kb window | 1 / 1 | 5.01 | 0.84 | 5.96× | 4.875 → 11.250 | [prior snapshot](common-tool-speed-20261126.md) |
| `vcftools --hap-r2` | 100 samples, 1 kb window | 1 / 1 | 5.66 | 1.32 | 4.29× | 4.500 → 11.250 | [prior snapshot](common-tool-speed-20261126.md) |
| `vcftools --geno-chisq` | 500 samples, 1 kb window | 1 / 1 | 159.09 | 6.97 | 22.82× | 5.625 → 5.625 | [prior snapshot](parallel-ld-20261126.md) |
| `vcftools --geno-chisq` | 500 samples, 1 kb window | 1 / 4 | 159.09 | 2.62 | 60.72× | 5.625 → 6.805 | [prior snapshot](parallel-ld-20261126.md) |
| `vcftools --geno-chisq` | 500 samples, 1 kb window | 1 / 8 | 159.09 | 1.88 | 84.62× | 5.625 → 11.652 | [prior snapshot](parallel-ld-20261126.md) |
| `vcftools --geno-chisq` | 2504 samples, 1 kb window | 1 / 1 | 772.98 | 28.65 | 26.98× | 6.000 → 5.625 | [prior snapshot](parallel-ld-20261126.md) |
| `vcftools --geno-chisq` | 2504 samples, 1 kb window | 1 / 4 | 772.98 | 10.20 | 75.78× | 6.000 → 8.020 | [prior snapshot](parallel-ld-20261126.md) |
| `vcftools --geno-chisq` | 2504 samples, 1 kb window | 1 / 8 | 772.98 | 7.14 | 108.26× | 6.000 → 15.633 | [prior snapshot](parallel-ld-20261126.md) |
| `vcf-compare` | 100 samples | 1 / 1 | 9.13 | 7.85 | 1.16× | 14.620 → 14.250 | [prior snapshot](perl-query-compare-20261121.md) |
| `vcf-compare` | 400 samples | 1 / 1 | 34.85 | 29.43 | 1.18× | 14.620 → 14.620 | [prior snapshot](perl-query-compare-20261121.md) |

The 2,504-sample merge timed runs differed only in two auto-generated UTC date header names. A validation-only candidate replay used the Original date and matched Original and Before stdout byte for byte. Its time was not substituted into this table. Query template reuse is opt-in because distinct rich FORMAT fields can regress; the default mode is listed separately.

## Retained changes without a direct upstream timing comparison

These reports compare against a previous NuVCFtools revision. Their ratios must not be relabeled as speedups over upstream.

| Tool | Retained change | Available evidence |
| --- | --- | --- |
| `vcf-concat` | Ordered tournament and buffered source lifecycle | [Previous-version comparison](common-speed-concat-20261126.md) |
| `vcf-isec` | File-head tournament and opaque sample suffixes | [Previous-version comparison](intersection-interval-20261126.md) |
| `vcf-annotate` | Interval index and operation-dependent sample parsing | [Previous-version comparison](intersection-interval-20261126.md) |
| `vcf-contrast` | Background genotype membership index instead of foreground/background Cartesian comparisons | [Previous-version comparison](contrast-background-index-20261126.md) |

## Entry points without targeted optimization since the inventory baseline

`fill-an-ac`, `vcf-consensus`, `vcf-fix-newlines`, `vcf-indel-stats`, `vcf-sort`, `vcf-tstv`.

These were examined and measured in the [remaining Perl tool round](remaining-perl-20261127.md). `fill-an-ac` benefits from earlier shared-module work; no command-specific change was added. The rejected sort trial and the lack of gain from four sort threads are recorded there. `fill-aa` now has an opaque-suffix implementation and functional controls, but no real ancestral-genome timing claim.

## What changed

- Perl query: prepared sample iteration order and optional exact template sharing; sample names and selected order remain per output column.
- Perl merge/subset: independent mutable genotype hashes reuse parsing of identical neighboring complete sample fields.
- Perl statistics/validation: reuse genotype groups, read-only records and repeated GT/cardinality work.
- Multi-file tools: ordered file-head tournaments, opaque sample text and interval/background indexes where the operation permits them.
- C++ parsing/output: reuse requested genotype decodes and rendered values; buffer file output.
- LD: packed counts, decoded-site/workspace reuse, and optional ordered chi-square workers.
- Relatedness: bounded bit-sliced counts and matrices sized to retained samples.

No claim is made that every tool is faster or uses less memory. LD bitsets/workers increase peak RSS in several measured cases; the largest demonstrated reductions are selected-sample relatedness matrices. Main and website publication data were not changed.
