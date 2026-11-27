# Merge, query and subset benchmark

Measured on Oscar on November 26, 2026, with one physical core per command. Each final comparison runs Original, Before and After once on the same node. Query also measures the final default mode separately. Independent jobs overlapped on shared nodes; there are no repeated-trial uncertainty estimates.

Wall time includes input reading/decompression, processing and complete output writing. Input splitting/compression/indexing and output comparison are excluded. No worker threads were added to these Perl commands.

## End-to-end wall time

Query rows below use the new opt-in `--reuse-sample-templates` flag. Default behavior is reported separately; the large query gains must not be attributed to the default command.

| Command | Input samples | Original (s) | Before (s) | After (s) | vs Original | vs Before |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| query: sample name + translated GT, reuse enabled | 500 | 52.20 | 18.81 | 6.87 | 7.60× | 2.74× |
| query: raw GT, reuse enabled | 500 | 24.20 | 12.43 | 5.92 | 4.09× | 2.10× |
| query: sample name + translated GT, reuse enabled | 2504 | 269.69 | 95.66 | 32.37 | 8.33× | 2.96× |
| query: raw GT, reuse enabled | 2504 | 121.45 | 62.00 | 28.41 | 4.27× | 2.18× |
| subset: retain half the samples | 500 | 62.28 | 22.97 | 21.97 | 2.83× | 1.05× |
| merge: two disjoint sample groups | 500 | 80.20 | 43.82 | 41.58 | 1.93× | 1.05× |
| subset: retain half the samples | 2504 | 323.36 | 115.88 | 108.55 | 2.98× | 1.07× |
| merge: two disjoint sample groups | 2504 | 533.13 | 295.29 | 281.75 | 1.89× | 1.05× |

## Default query mode

No template cache is enabled without the new flag. The shared field loop now iterates a sample-order array prepared once per invocation.

| Query output | Samples | Before (s) | Final default (s) | vs Before |
| --- | ---: | ---: | ---: | ---: |
| query: sample name + translated GT | 500 | 18.81 | 17.28 | 1.09× |
| query: raw GT | 500 | 12.43 | 11.78 | 1.06× |
| query: sample name + translated GT | 2504 | 95.66 | 88.37 | 1.08× |
| query: raw GT | 2504 | 62.00 | 59.76 | 1.04× |

## Peak RSS

MiB from GNU time maximum RSS divided by 1,024. This is the maximum accounted process/child RSS, not the sum of simultaneous Perl and decompression processes.

| Command | Samples | Original (MiB) | Before (MiB) | After (MiB) |
| --- | ---: | ---: | ---: | ---: |
| query: sample name + translated GT, reuse enabled | 500 | 10.875 | 10.875 | 10.500 |
| query: raw GT, reuse enabled | 500 | 10.500 | 10.500 | 10.500 |
| query: sample name + translated GT, reuse enabled | 2504 | 13.125 | 13.500 | 12.000 |
| query: raw GT, reuse enabled | 2504 | 12.000 | 12.375 | 11.625 |
| subset: retain half the samples | 500 | 10.500 | 10.875 | 10.875 |
| merge: two disjoint sample groups | 500 | 14.625 | 14.625 | 14.250 |
| subset: retain half the samples | 2504 | 12.000 | 11.625 | 11.625 |
| merge: two disjoint sample groups | 2504 | 15.375 | 15.375 | 15.750 |

The merge/subset changes produce small runtime improvements, without a substantial measured RAM reduction. Query template sharing reduces per-record template allocation when complete sample fields repeat. Its benefit depends on field repetition; these timings do not establish a universal speedup.

## Input and revisions

The input is 22,382 actual 1000 Genomes Phase 3 chromosome 22 records from GRCh37 `22:20000001-21000000`, with 500 or 2,504 samples. It contains GT-only FORMAT data. Merge reads two disjoint half-sample files prepared with bcftools; subset retains the first half of the input samples. Both commands retain every eligible record under their normal semantics. No invented or duplicated genotypes were used for these real-data timings.

- Original: upstream `1f87a83402ffd17ea2723a456b7edf5d80b4a22c`.
- Before: `e337a33bed983024349001bfdc16f46c89a07d50`.
- Retained implementation: `0e22d2861de3e7856b18b30e944cc5a36701a0e2` on `codex/common-tool-speed-round2`.
- Final query: job 9657111 on node2308; final merge/subset: job 9656967 on node1829.
- `PERL_HASH_SEED=0`, `PERL_PERTURB_KEYS=0`, `LC_ALL=C`; controls also use hash seeds 1 and 19.

The measured merge/subset snapshot and final source have identical `Vcf.pm`, `vcf-merge` and `vcf-subset` content; later query-only revisions do not affect those commands. Source SHA256, input SHA256, flags, user/system CPU time, exit status, output size and preparation time are recorded in the accompanying evidence.

## Implementation

`next_data_hash` reuses parsing of equal neighboring complete FORMAT strings within a record. Mutable callers receive independent hash copies, so changing one sample cannot alter another. The existing read-only interface retains shared hashes. Malformed field counts continue through ordinary parsing so each sample keeps its diagnostics. Cache lifetime ends at the record boundary.

`vcf-query --reuse-sample-templates` groups exactly equal complete sample strings within each record. Named FORMAT extraction and template assembly are reused; sample names are inserted at emission, preserving selected order and duplicate selections. The `*` expansion still runs per sample to retain diagnostics. Non-repeated templates are rendered directly. There are no dataset-specific identifiers, thresholds or genotype assumptions.

The optional cache changes template work from per-sample to per-distinct-field work, while output emission remains proportional to output size. It may cost more when every sample field is distinct, so the default renderer remains available and unchanged in semantics.

## Validation, rejected candidates and cleanup

Query, subset and the 500-sample merge passed complete streaming byte comparison against Original. The 2,504-sample merge crossed UTC midnight: only the generated source/sourceFiles header-key dates differed; records and all other header bytes matched. A validation-only candidate replay fixed the test clock to the Original run date and then matched the complete Original and Before stdout bytes, with no output normalization. The product source was unchanged, and replay timing is excluded from the matrix. Stderr was compared after replacing only installation paths, source-line locations and process-specific reference addresses where applicable. Outputs were compared as bytes, not accepted solely by hashes.

- 54 corrected query cases across three hash seeds each compare both final modes to Before: 108 comparisons. Normal cases explicitly require exit zero. Cases cover sample-name placement, raw/translated GT, field expansion, repeated tags, reordered/duplicate selections, region access, old-method compatibility and malformed rows.
- 18 subset cases cover selection, trimming, private variants, type filtering, replacement and uncalled rows across three seeds; all exit successfully and match Before.
- 30 existing stats/merge/API regression comparisons cover multi-allelic remapping, Number=A/G fields, missing samples and merge collapse modes.
- 55 ownership/parser assertions check record values, malformed-field diagnostics, duplicate FORMAT tags, sample selection, independent mutable hashes and cache lifetime.

An early formatter candidate replaced repeated array prepending with indexed assignment. It passed comparison but produced essentially no real-data improvement, so it was reverted. Always-on query template caching regressed on a deterministic distinct-field control; the cache is therefore opt-in. The final default query took 2.28 vs 2.37 seconds and 4.83 vs 5.04 seconds on two rich-FORMAT controls. Subset took 8.32 vs 8.01 seconds on that short control: the real GT-only improvements are not a claim that every FORMAT distribution is faster.

The first query test suite allowed matching nonzero exits. Some formats with an empty section hit the same pre-existing parser failure before exercising rendering. These were corrected to execute the intended path, and successful exits are now required for normal cases. The empty-section failure remains an explicit compatibility case. No new fuzzing campaign was run.

Large real-data outputs were removed after successful comparison, including the fixed-clock merge replay and full diagnosis of the original date-only differences. The original failing comparison statuses remain in the evidence rather than being relabeled as passing timed runs. Canonical inputs and the small prepared merge inputs remain for replay. Cleanup checks and the initial failed control diagnosis are retained with the evidence.

Evidence: [query](merge-query-subset-20261126/query.json), [merge/subset](merge-query-subset-20261126/merge-subset.json), [query controls](merge-query-subset-20261126/query-controls.json), [rich-field controls](merge-query-subset-20261126/final-validation.json), [manifest](merge-query-subset-20261126/manifest.json).

Replay scripts in that directory use the recorded Oscar input paths and frozen source directories. They include preparation and validation separately from command timing; they do not download inputs. Main and website publication data were not changed.
