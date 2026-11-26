# Intersection and interval annotation: algorithm and buffer changes

Baseline: `40d05e8` (NuVCFtools before this work). Candidate product code: `7635e30`, branch `codex/intersection-interval-index`. These measurements compare the two frozen revisions, not upstream VCFtools. Origin main was separately confirmed at `2b8421435a61a67ce39dcd48df3fd0b82d6d1a4c` during the work.

## Implementation

- Ordinary `vcf-isec` output uses an ordered tournament of file heads. Only a consumed head is refreshed, reducing selection work from O(records × files) to O(records × log(files)), after initialization. Equal positions retain input-file order. The reducer also preserves the legacy scan's false-valued position behavior. Split output keeps the original scan and full record layout.
- Intersection records no longer duplicate REF/ALT hash entries: original fields remain in the retained line. FORMAT and all sample columns are retained as one opaque suffix because intersection inspects only the first eight columns. This changes per-record sample scalar allocation from O(samples) to O(1); input/output byte processing and retained text remain proportional to actual line length. The split boundary follows the VCF column schema, not a size threshold.
- Annotation groups use a balanced index over sorted starts and subtree maximum endpoints. Queries report matching original row indexes and restore original annotation order before applying INFO lists and last-writer fields. One coordinate cell is cached: its hit set cannot change until a start is reached or an end is passed. Queries may arrive in arbitrary order. Index storage is O(intervals); uncached query traversal is conservatively O((hits + 1) × log(intervals)), plus result ordering. Repeated queries within a cached cell avoid traversal and sorting.
- Annotation retains sample columns as opaque text when the requested operations do not use them. Genotype statistics, FORMAT removal and user-defined filter expressions use full sample parsing. This is an operation dependency decision, not an input-specific fast path.

No worker threads were added: bounded single-process allocation and avoiding repeated work were more useful for these commands. Introducing parallelism would also add process/queue memory and ordering costs.

## Inputs and measurement

Oscar job **9638474**, node **node1827**, one allocated physical core, CPU binding enabled, 4 GiB allocation. Every scenario ran each revision three times on the same node; execution order alternated. Table values are medians. GNU time measures the complete Perl command, including startup, reading/decompression, computation and writing. Download, input preparation, bgzip/tabix index construction and output comparison are excluded. In-process tournament and interval-index construction are included in command time and RSS. Scientific output was written to files, not discarded.

Peak RSS is GNU time's maximum resident set size converted from KiB to MiB. Commands launch tabix/gunzip children; this metric is a maximum individual process RSS, not the simultaneous sum of a process tree. It must not be interpreted as total physical memory across all children. Small RSS changes near allocator granularity are not meaningful reductions.

Real input is the retained 1000 Genomes Phase 3 GRCh37 chr22:20,000,001–21,000,000 subset: 22,382 records, originally 100 selected samples, roughly 0.54 MiB compressed. Input identity is recorded in `input.json`. Two representations are measured: sites-only and all 100 original sample columns. Site sets are reproducibly derived from the same real records: every third record is shared and the rest are partitioned by input file number. This tests differing overlap sets without fabricating variants or genotypes. Cohort sample names and variant/genotype text are preserved. Derived inputs regenerate a minimal VCF header.

The windowed intersection uses the real records with `-w 10000` to exercise a large buffered cluster. It is a memory/scaling scenario, not a claim that this window is a typical default. Ordinary intersections and unions are reported alongside it.

Annotation uses 91 actual UCSC hg19 refGene transcript intervals overlapping that 1 Mb region, with 0-based transcript starts converted to 1-based inclusive starts. Both sites-only and cohort inputs are annotated. URL and downloaded-file SHA256 are in `annotation-input.json`. The small annotation interval count limits the potential algorithmic benefit on this dataset.

## End-to-end results

| Scenario | Before wall (s) | Candidate wall (s) | Speedup | Before RSS (MiB) | Candidate RSS (MiB) | RSS reduction | Output |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| sites-intersection-2 | 0.56 | 0.60 | 0.933× | 10.125 | 10.500 | -3.7% | Pass |
| sites-union-2 | 0.66 | 0.69 | 0.957× | 10.500 | 10.500 | 0.0% | Pass |
| sites-windowed-intersection-2 | 0.65 | 0.69 | 0.942× | 41.250 | 37.125 | 10.0% | Pass |
| sites-intersection-8 | 1.65 | 1.66 | 0.994× | 10.125 | 10.500 | -3.7% | Pass |
| sites-union-8 | 1.75 | 1.72 | 1.017× | 10.500 | 10.125 | 3.6% | Pass |
| sites-windowed-intersection-8 | 1.75 | 1.81 | 0.967× | 78.000 | 68.250 | 12.5% | Pass |
| sites-intersection-32 | 8.12 | 6.17 | 1.316× | 11.250 | 11.250 | 0.0% | Pass |
| sites-union-32 | 8.26 | 6.28 | 1.315× | 10.875 | 11.250 | -3.4% | Pass |
| sites-windowed-intersection-32 | 8.21 | 6.72 | 1.222× | 226.500 | 193.500 | 14.6% | Pass |
| cohort100-intersection-2 | 0.95 | 0.96 | 0.990× | 12.375 | 12.375 | 0.0% | Pass |
| cohort100-union-2 | 1.09 | 1.09 | 1.000× | 12.375 | 12.375 | 0.0% | Pass |
| cohort100-windowed-intersection-2 | 1.23 | 1.07 | 1.150× | 164.250 | 44.625 | 72.8% | Pass |
| cohort100-intersection-8 | 2.56 | 2.58 | 0.992× | 10.875 | 10.875 | 0.0% | Pass |
| cohort100-union-8 | 2.75 | 2.74 | 1.004× | 10.875 | 10.875 | 0.0% | Pass |
| cohort100-windowed-intersection-8 | 3.16 | 2.83 | 1.117× | 385.875 | 86.250 | 77.6% | Pass |
| cohort100-intersection-32 | 10.87 | 9.37 | 1.160× | 12.375 | 12.000 | 3.0% | Pass |
| cohort100-union-32 | 11.09 | 9.53 | 1.164× | 12.375 | 12.000 | 3.0% | Pass |
| cohort100-windowed-intersection-32 | 12.56 | 9.84 | 1.276× | 1272.750 | 254.617 | 80.0% | Pass |
| sites-annot | 0.51 | 0.50 | 1.020× | 10.875 | 11.250 | -3.4% | Pass |
| cohort100-annot | 0.86 | 0.79 | 1.089× | 10.875 | 11.250 | -3.4% | Pass |

The timing campaign compares complete result records, fields, tags and order after line-separator normalization. A second campaign then compares **unmodified stdout bytes**, including all headers, record separators and sample-list order: all 120 randomized CLI pairs and one replay of each of the 20 distinct real scenarios passed. No header removal, sorting, numeric tolerance or hash-only check is used in that second campaign. Stderr comparisons normalize only source paths/line locations and exclude GNU time telemetry.

Raw-byte validation began in Oscar job **9638611**. After 138 successful pairs, the duplicate UCSC download stalled during preparation; that job was intentionally cancelled. Job **9638905** reused the annotation archive already measured in the timing run after checking its complete SHA256, and completed the two remaining annotation comparisons. The combined raw-byte campaign contains 140 passing pairs. Its timings are validation metadata and are not mixed into the median table above.

## Differential testing and limits

The final Oscar campaign includes 120 randomized CLI pairs: 12 seeds, six intersection modes and four annotation modes. It covers duplicate positions, two chromosomes, window clustering, union/intersection/complement, first-file output, filters, phased/unphased and missing genotype text, FORMAT removal and AC/AN calculation. Sample columns are included in the generated fixtures. All timed pairs completed successfully and compared equal; the additional raw-byte campaign also passed all 140 comparisons.

The local algorithm probe passed 3,700 assertions: 500 randomized file-head order comparisons, 3,000 interval queries (including negative, inverted, overlapping, duplicate and empty ranges, inclusive endpoints and arbitrary query order), and 200 real reader reconstructions covering variable sample widths, trailing fields and an unterminated last line. Fuzzing here is reproducible randomized differential testing, not coverage-guided libFuzzer, ASan or a proof for every option/input. The changed product code is Perl. Split-output optimization is deliberately outside this change.

The first interval-tree experiment slowed this small real annotation task; caching coordinate cells was added before final measurement. Earlier intermediate jobs are not mixed into this table. Ordinary small-file intersections can still show little benefit: the parser and output cost can dominate head selection. Reported improvements should be read per scenario, rather than generalized to all VCFtools commands or full WGS inputs.

Source SHA256 verification checks both frozen script/module trees. Successful command outputs are deleted after byte comparison; generated/downloaded experiment inputs are removed after complete validation. Existing shared real input and original source snapshots are retained. Cleanup evidence is in `cleanup.json`; all machine-readable results and the harness are under `intersection-interval-20261126/`.


## Reproduction and evidence

`intersection-interval-20261126/run.py` is the timing harness and `benchmark.slurm` its Slurm wrapper. Place frozen `src/perl` trees in `before/` and `candidate/` below the run directory, and provide the retained real subset at the source path declared in the harness. `raw_validation.py` runs the same cases with one real-data replay each and unmodified stdout comparison. `resume_raw_annotation.py` records the cached-input resumption used for this campaign. `verify_sources.py` checks both trees against `source-manifest.json`.

The source dataset is [1000 Genomes Phase 3 chr22](https://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/ALL.chr22.phase3_shapeit2_mvncall_integrated_v5b.20130502.genotypes.vcf.gz). The small selected subset was retained from the earlier benchmark; it was not downloaded again. All per-case command arguments, repetitions and measurements are in `results.json`; compact medians are in `matrix.json`. `raw-validation/status.json` records the separate raw-byte campaign. `probe-summary.json` records the local 3,700-assertion probe. `final-accounting.txt` records actual Slurm terminal states, including the intentional cancellation during network preparation.
