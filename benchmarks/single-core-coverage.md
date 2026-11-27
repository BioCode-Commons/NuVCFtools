# Single-core optimization coverage

Scope: 24 installed Perl commands (including vcf-sort) and the vcftools C++ executable. C++ subcommands require separate cases; one case is not a claim for all its modes. All changes stay on codex/common-tool-speed-round2.

| Entry point | Current round | Evidence / next target |
| --- | --- | --- |
| fill-aa | Not yet measured in this single-core round | Audit algorithm and allocation cost; do not assume a new speedup |
| fill-an-ac | Not yet measured in this single-core round | Audit algorithm and allocation cost; do not assume a new speedup |
| fill-fs | Not yet measured in this single-core round | Audit algorithm and allocation cost; do not assume a new speedup |
| fill-ref-md5 | Not yet measured in this single-core round | Audit algorithm and allocation cost; do not assume a new speedup |
| vcf-annotate | Not yet measured in this single-core round | Audit algorithm and allocation cost; do not assume a new speedup |
| vcf-compare | Measured; full output passed | [Round 1](single-thread-20261127.md) |
| vcf-concat | Not yet measured in this single-core round | Audit algorithm and allocation cost; do not assume a new speedup |
| vcf-consensus | Not yet measured in this single-core round | Audit algorithm and allocation cost; do not assume a new speedup |
| vcf-contrast | Not yet measured in this single-core round | Audit algorithm and allocation cost; do not assume a new speedup |
| vcf-convert | Not yet measured in this single-core round | Audit algorithm and allocation cost; do not assume a new speedup |
| vcf-fix-newlines | Measured; full output passed | [Round 2](single-core-stream-20261127.md) |
| vcf-fix-ploidy | Not yet measured in this single-core round | Audit algorithm and allocation cost; do not assume a new speedup |
| vcf-indel-stats | Not yet measured in this single-core round | Audit algorithm and allocation cost; do not assume a new speedup |
| vcf-isec | Not yet measured in this single-core round | Audit algorithm and allocation cost; do not assume a new speedup |
| vcf-merge | Not yet measured in this single-core round | Audit algorithm and allocation cost; do not assume a new speedup |
| vcf-phased-join | Not yet measured in this single-core round | Audit algorithm and allocation cost; do not assume a new speedup |
| vcf-query | Not yet measured in this single-core round | Audit algorithm and allocation cost; do not assume a new speedup |
| vcf-shuffle-cols | Measured; full output passed | [Round 2](single-core-stream-20261127.md) |
| vcf-sort | Not yet measured in this single-core round | Audit algorithm and allocation cost; do not assume a new speedup |
| vcf-stats | Measured; full output passed | [Round 1](single-thread-20261127.md) |
| vcf-subset | Not yet measured in this single-core round | Audit algorithm and allocation cost; do not assume a new speedup |
| vcf-to-tab | Measured; full output passed | [Round 1](single-thread-20261127.md) |
| vcf-tstv | Measured; full output passed | [Round 2](single-core-stream-20261127.md) |
| vcf-validator | Measured; full output passed | [Round 1](single-thread-20261127.md) |
| vcftools | Not yet measured in this single-core round | Audit algorithm and allocation cost; do not assume a new speedup |
