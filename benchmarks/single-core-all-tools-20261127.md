# Single-core results for all 25 entrypoints

All 24 installed Perl commands and six named modes of the C++ executable were measured on Oscar. Every selected row passed complete output comparison against upstream VCFtools 1f87a83402ffd17ea2723a456b7edf5d80b4a22c. This is a tested-mode result, not equivalence for every input and option.

The follow-up retested indel-stats, ploidy and stats in job 9693876; their rows below supersede the earlier measurements. Other rows retain their original job IDs and timings: their executed code is unchanged. VcfStats.pm changed only for stats. [Follow-up results, controls and known parallel-error limitation](single-core-followup-20261127.md).

Each command and its children were pinned to one physical CPU. Most cases use 22,382 real 1000 Genomes chr22 variants with 500 or 2,504 samples and GT-only fields. The reference-based rows use GRCh37 sequence; fill-aa is an annotation fixture, not a claim that GRCh37 is the ancestral allele. Input derivation/indexing and comparison are excluded; startup, reading/decompression, processing and complete output writing are included.

The table combines frozen snapshots from the incremental checks. The original table’s command files matched its retained source exactly; the three updated rows match the follow-up source manifest. Shared modules also match, except the isolated split_gt change for commands that do not call it; all five installed callers were retested after that change. The exact byte checks and manual call-graph exception are recorded in [final-source-identity.json](single-core-all-tools-20261127/final-source-identity.json). Cases in a row ran on the same node. Rows on different nodes are not directly comparable. Most are single runs, in original/before/candidate order without cache eviction; ratios have no confidence intervals. MD5 and indel-stats show medians of three repeats.

| Tool | Tested task | Original s | Latest s | Speedup | Sampled tree RSS MiB, original → latest | GNU time max RSS MiB, original → latest | Output | Job |
| --- | --- | ---: | ---: | ---: | --- | --- | --- | --- |
| fill-aa | 500 samples; GRCh37 reference annotation fixture | 2.23 | 1.01 | 2.21× | 17.2 → 17.2 | 12.00 → 12.38 | Passed | 9691582 |
| fill-an-ac | 500 samples; AC/AN | 30.39 | 22.56 | 1.35× | 15.8 → 15.8 | 10.50 → 10.88 | Passed | 9691753 |
| fill-fs | 2,000 variants / 500 samples; flanks + VCF mask | 33.26 | 32.72 | 1.02× | 27.0 → 27.2 | 10.50 → 10.88 | Passed | 9691582 |
| fill-ref-md5 | chr22 digest and 2,504-sample VCF reheader; 3 repeats | 3.17 | 0.66 | 4.80× | 68.0 → 65.7 | 54.44 → 54.39 | Passed | 9691997 |
| vcf-annotate | 500 samples; HWE | 28.50 | 8.61 | 3.31× | 16.5 → 16.9 | 11.25 → 11.62 | Passed | 9692585 |
| vcf-compare | 500 samples; genotype comparison | 102.73 | 74.36 | 1.38× | 42.8 → 42.4 | 14.62 → 14.62 | Passed | 9691582 |
| vcf-concat | 128 interleaved files / 100 samples | 15.08 | 7.12 | 2.12× | 707.6 → 654.8 | 34.50 → 34.50 | Passed | 9691582 |
| vcf-consensus | 1 Mbp reference fragment | 0.77 | 0.79 | 0.97× | 32.3 → 31.1 | 14.62 → 14.62 | Passed | 9692585 |
| vcf-contrast | 100 samples; 10 foreground / 90 background | 24.19 | 7.58 | 3.19× | 12.8 → 13.5 | 10.12 → 10.88 | Passed | 9692585 |
| vcf-convert | 500 samples; SNPs to VCF 4.2 | 31.43 | 21.97 | 1.43× | 16.9 → 17.2 | 11.62 → 11.62 | Passed | 9691753 |
| vcf-fix-newlines | 2,504 samples; CRLF to LF | 0.31 | 0.29 | 1.07× | 6.8 → 7.1 | 5.62 → 6.38 | Passed | 9691582 |
| vcf-fix-ploidy | 500 samples; active haploid conversion | 50.96 | 45.32 | 1.12× | 16.1 → 16.1 | 10.50 → 10.50 | Passed | 9693876 |
| vcf-indel-stats | 500 samples; coordinate interval | 0.38 | 0.44 | 0.86× | 16.1 → 15.8 | 10.50 → 10.12 | Passed | 9693876 |
| vcf-isec | 128 interleaved files / 100 samples | 13.49 | 10.43 | 1.29× | 611.6 → 615.6 | 39.38 → 39.00 | Passed | 9691753 |
| vcf-merge | two sample partitions; 500 samples total | 97.00 | 51.98 | 1.87× | 41.6 → 42.4 | 14.62 → 14.62 | Passed | 9691582 |
| vcf-phased-join | two overlapping blocks; 500 samples | 6.08 | 5.42 | 1.12× | 80.2 → 80.2 | 64.50 → 64.88 | Passed | 9692585 |
| vcf-query | 2,504 samples; default sample + GT output | 316.67 | 103.90 | 3.05× | 15.4 → 16.1 | 12.75 → 13.50 | Passed | 9691582 |
| vcf-shuffle-cols | reverse 2,504 sample columns | 15.87 | 8.19 | 1.94× | 13.5 → 13.9 | 11.62 → 11.62 | Passed | 9691582 |
| vcf-sort | 500 samples; reversed records; one GNU sort thread | 0.27 | 0.26 | 1.04× | 24.4 → 24.8 | 9.38 → 9.38 | Passed | 9691582 |
| vcf-stats | 500 samples; default statistics | 120.05 | 29.94 | 4.01× | 15.0 → 15.4 | 26.25 → 16.50 | Passed | 9693876 |
| vcf-subset | 500 to 250 samples | 61.41 | 21.99 | 2.79× | 13.1 → 13.1 | 10.88 → 10.88 | Passed | 9691753 |
| vcf-to-tab | 500 samples | 46.36 | 12.39 | 3.74× | 15.8 → 16.1 | 10.50 → 10.88 | Passed | 9692654 |
| vcf-tstv | 2,504 samples | 1.01 | 1.01 | 1.00× | 11.2 → 11.2 | 6.00 → 6.00 | Passed | 9691582 |
| vcf-validator | 500 samples; default mode | 78.70 | 15.55 | 5.06× | 13.1 → 12.4 | 10.88 → 10.12 | Passed | 9691997 |
| vcftools | 500 samples; --freq | 0.87 | 0.54 | 1.61× | 6.0 → 6.0 | 4.88 → 4.88 | Passed | 9691753 |
| vcftools | 500 samples; --het | 0.87 | 0.56 | 1.55× | 6.4 → 6.0 | 5.25 → 4.88 | Passed | 9691753 |
| vcftools | 500 samples; --missing-indv | 0.80 | 0.55 | 1.45× | 6.4 → 6.0 | 5.25 → 4.88 | Passed | 9691753 |
| vcftools | 500 samples; --recode | 3.13 | 1.28 | 2.45× | 6.8 → 6.4 | 5.62 → 5.25 | Passed | 9691753 |
| vcftools | 500 samples; --relatedness2 | 34.65 | 1.96 | 17.68× | 12.0 → 8.2 | 10.88 → 7.12 | Passed | 9691753 |
| vcftools | 500 samples; --window-pi 10000 | 0.85 | 0.53 | 1.60× | 6.4 → 6.4 | 5.25 → 5.25 | Passed | 9691753 |

The first vcf-to-tab invocation in job 9691582 incorrectly supplied a filename to a stdin-only command. Upstream rejected that invocation before processing records. The corrected stdin run is recorded separately in job 9692654; the failed attempt is retained as harness evidence and is not used in any timing ratio.

The delimiter-cursor change is retained for its linear worst-case scan bound after all five caller checks passed. Ordinary diploid timings were effectively unchanged; no end-to-end speedup is claimed for that change.

The sampled tree RSS column is the maximum sampled sum of process-tree RSS at 100 ms intervals. It can miss a short-lived peak and counts shared pages in each process. GNU time max RSS is a kernel-accounted process/child high-water mark, not a sum over the tree; its column helps expose peaks missed by sampling. PSS is also retained in the [JSON](single-core-all-tools-20261127.json); they are different memory metrics. For example, isec opens many readers, so summed RSS is much higher than its PSS.

The C++ source is unchanged in this pass. Its speedups relative to upstream reflect earlier retained algorithm/data-structure work, not this pass’s Perl edits. It was rebuilt at -O2 -g; both native make-check programs passed. Before and candidate native labels use the same binary, so differences between those labels are run variation.

Retained changes in this pass include shared-decoder ownership, cached sample order, read-only comparison, compiled column gather, bounded newline/FASTA processing, direct serial tstv counters, linear isec header checking and deferred worker/validator dependencies. The [25-tool audit](single-core-audit-20261127.md) distinguishes changed code from reviewed, unchanged algorithms. The sort chunk-forwarding trial was reverted: three runs showed no material gain. Some tools remain near upstream speed or slower; no universal speedup is claimed.

Round 1 and 2 results are [decoder/sample order](single-thread-20261127.md) and [columns/stream processing](single-core-stream-20261127.md). Their before/candidate ratios describe those specific changes and are not multiplied into this table.

Validation compares actual full stdout bytes, not hashes alone, with order and duplicates retained. fill-ref-md5 additionally compares decompressed VCF, header and dictionary; gzip-container bytes are not an equality requirement. Successful stderr comparison normalizes installation paths and source line numbers; native elapsed-time log lines are also excluded. A fixed Perl clock equalizes generated provenance dates without changing the measured timer. Error/partial-output checks use the documented per-harness normalization rules. Archived build/scheduler logs have trailing whitespace stripped; their original and archived hashes are retained in log-normalization.json. This does not alter the execution output comparisons.

Thirteen abstract SMT obligations in the initial single-core pass returned unsat (four decoder/order, five stream/count, one header, two digest-feed checks and one delimiter-cursor invariant, including trial code). The source-to-model connection remains manual. These checks do not prove the complete Perl/C++ programs, arbitrary callbacks, I/O failure behavior or the digest library. See [module contracts](../verification/single-core-module-contracts.md) and the linked earlier contracts.

## Incremental changes

These comparisons isolate individual steps against the immediately preceding frozen version. Different rows use different baselines; their ratios must not be multiplied.

| Change | Before s | After s | Before → after RSS MiB | Evidence |
| --- | ---: | ---: | --- | --- |
| Deferred worker modules; query | 104.18 | 103.90 | 18.8 → 16.1 | 9691582 |
| Deferred worker modules; shuffle | 8.19 | 8.19 | 17.2 → 13.9 | 9691582 |
| Owned input columns; subset | 23.04 | 21.99 | 13.5 → 13.1 | 9691753 |
| Owned input columns; AC/AN | 23.43 | 22.56 | 16.1 → 15.8 | 9691753 |
| Owned input columns; convert | 22.90 | 21.97 | 17.2 → 17.2 | 9691753 |
| Linear header checks; isec | 10.78 | 10.43 | 609.0 → 615.6 | 9691753 |
| Deferred IPC modules; validator | 15.56 | 15.55 | 13.1 → 12.4 | 9691997 |
| Chunked FASTA digest; median of 3 | 0.86 | 0.66 | 65.8 → 65.7 | 9691997 |
| Delimiter cursors (retained); vcf-fix-ploidy | 42.27 | 42.10 | 16.5 → 15.8 | 9692585 |
| Delimiter cursors (retained); vcf-contrast | 7.66 | 7.58 | 13.1 → 13.5 | 9692585 |
| Delimiter cursors (retained); vcf-annotate | 8.52 | 8.61 | 17.2 → 16.9 | 9692585 |
| Delimiter cursors (retained); vcf-phased-join | 5.39 | 5.42 | 80.6 → 80.2 | 9692585 |
| Delimiter cursors (retained); vcf-consensus | 0.77 | 0.79 | 31.1 → 31.1 | 9692585 |

Small single-run differences, especially below one second, should be treated as run variation until repeated. The deferred-module changes were retained for memory savings even where runtime is unchanged.

After full comparison passed, the initial campaigns removed 6,772,551,720 bytes of generated outputs and 332,560,845 bytes of owned derived inputs/sidecars. Reused source datasets and original reference installations were retained. No website publication data or main branch was changed.
