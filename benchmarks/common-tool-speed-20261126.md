# NuVCFtools common-tool speed round

Fifteen actual-data tasks passed complete output comparisons against upstream VCFtools and the start of this optimization round. All three revisions ran once per task on the same node and bound physical core. These are fresh comparisons, not historical timing ratios. Component experiments linked below provide three paired repetitions for the individual changes.

- Upstream VCFtools: `1f87a83402ffd17ea2723a456b7edf5d80b4a22c`.
- Round baseline: `9dc88f1f3c0ccd8da067b80bf1bab7acaba0adbc`. The C++ baseline snapshot was built at `d802f36`, whose C++ source is identical to that baseline.
- Common-command candidate: `9bd6ad8a7cdc940ae1a702a6bbc77ac23d834976`; job **9647879**, node `node1934.oscar.ccv.brown.edu`.
- LD candidate: `c8494dd775eb98667e91b9ddda213d254b938410`; job **9648253**, node `node1938.oscar.ccv.brown.edu`. This adds the three LD file-flush changes; the other command implementations are unchanged.

## End-to-end results

Input is the retained 1000 Genomes Phase 3 GRCh37 chr22:20,000,001–21,000,000 cohort: 22,382 actual records, with either 100 or 2,504 samples and FORMAT=GT. Wall time includes startup, reading/decompression, computation, temporary files and writing. Download, input preparation, compilation and output comparison are excluded. Each timing here is one run, so small differences should not be treated as a stable effect.

RSS is GNU time peak process RSS in MiB, shown as **upstream / baseline / candidate**. It is not the sum of simultaneous child processes. The changes improve speed; these results do not demonstrate a general RAM reduction.

| Command/task | Input samples | Upstream (s) | Baseline (s) | Candidate (s) | vs upstream | vs baseline | Peak RSS (MiB) | Full output |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `--freq` | 2504 | 4.72 | 4.87 | 2.98 | 1.58× | 1.63× | 5.625 / 5.250 / 5.250 | Identical |
| `--missing-indv` | 2504 | 4.57 | 4.47 | 3.06 | 1.49× | 1.46× | 5.625 / 5.250 / 5.250 | Identical |
| `--missing-site` | 2504 | 4.73 | 4.75 | 3.17 | 1.49× | 1.50× | 5.625 / 5.250 / 5.250 | Identical |
| `--het` | 2504 | 5.16 | 5.27 | 3.47 | 1.49× | 1.52× | 5.625 / 5.625 / 5.625 | Identical |
| VCF rewrite | 2504 | 17.81 | 17.95 | 7.06 | 2.52× | 2.54× | 5.625 / 5.625 / 5.625 | Identical |
| Filter + VCF rewrite | 2504 | 20.54 | 19.49 | 8.12 | 2.53× | 2.40× | 6.000 / 6.000 / 5.625 | Identical |
| `vcf-validator` | 100 | 19.70 | 17.95 | 12.62 | 1.56× | 1.42× | 10.500 / 10.125 / 10.500 | Identical |
| `vcf-subset`, all samples | 100 | 29.39 | 24.50 | 10.96 | 2.68× | 2.24× | 10.500 / 10.500 / 10.500 | Identical |
| `vcf-subset`, SNP/indel selection | 100 | 23.17 | 22.21 | 6.46 | 3.59× | 3.44× | 10.500 / 10.500 / 10.500 | Identical |
| `vcf-subset`, private variants in 10 samples | 100 | 14.66 | 14.75 | 5.17 | 2.84× | 2.85× | 10.500 / 10.500 / 10.500 | Identical |
| `vcf-stats` | 100 | 24.38 | 10.15 | 10.13 | 2.41× | 1.00× | 13.500 / 13.500 / 13.875 | Identical |
| `vcf-shuffle-cols`, reverse sample order | 2504 | 15.69 | 15.74 | 13.18 | 1.19× | 1.19× | 12.000 / 12.000 / 11.625 | Identical |
| `--geno-r2`, 1 kb window | 100 | 5.01 | 2.93 | 0.84 | 5.96× | 3.49× | 4.875 / 10.875 / 11.250 | Identical |
| `--hap-r2`, 1 kb window | 100 | 5.66 | 3.53 | 1.32 | 4.29× | 2.67× | 4.500 / 10.875 / 11.250 | Identical |
| `--geno-chisq`, 1 kb window | 100 | 34.99 | 5.56 | 3.18 | 11.00× | 1.75× | 4.875 / 4.875 / 4.875 | Identical |

`vcf-stats` is a regression control: its improvement over upstream predates this round, and it changed little against the round baseline. Exact arguments and all three measurements accompany this report. No speedup was extrapolated or multiplied across experiments.

## Changes retained

- Validator: reuse per-record GT tokens and calculate Number=G cardinality only when requested. Every sample and FORMAT handler still runs.
- Subset: reuse genotype classification and delay GT formatting until a selected sample needs it; sample-specific fields remain independent.
- C++ VCF parser: own the row cursor and reuse decoded neighboring sample values under identical field requests. Missingness uses this batch path only for selected, unfiltered calls.
- VCF writer: reuse the rendered GT for neighboring equal genotype/phase values. Other FORMAT values and filters are still per sample.
- Column shuffle: write each assembled row once.
- LD tables: buffer file writes; explicit stdout keeps the previous per-row flushes. Failed or interrupted files need not retain the old per-row persistence.

The shared Perl hash-slice experiment passed its comparisons but was slightly slower for stats, validation and rewriting. It was reverted. No dataset-specific genotype values or cutoffs were introduced.

## Output checks and limits

The harness compares actual complete scientific files and stdout bytes, checks matching file sets and successful exits, and removes passed raw outputs. Hashes are supplementary identities, not a substitute for comparison. Diagnostic stderr normalizes only output paths, source locations, displayed build version, runtime and Perl reference addresses. Perl comparisons fix `PERL_HASH_SEED=0`, `PERL_PERTURB_KEYS=0` and `LC_ALL=C`.

These are GT-only cohort measurements, not performance evidence for every FORMAT layout or option. Further fuzzing was stopped at the user’s request. An earlier deliberately shortened sample row caused heap corruption in a before binary; its separate synthetic artifacts are retained, and this report does not claim that issue is fixed or that malformed-input safety is established.

## Component evidence

- [validator](common-speed-validator-20261126.md)
- [subset](common-speed-subset-20261126.md)
- [cpp-reader](common-speed-cpp-reader-20261126.md)
- [genotype-runs](common-speed-genotype-runs-20261126.md)
- [cpp-output](common-speed-cpp-output-20261126.md)
- [shuffle](common-speed-shuffle-20261126.md)
- [kept-batch](common-speed-kept-batch-20261126.md)
- [ld-output](common-speed-ld-output-20261126.md)

## Concat follow-up

The [concat experiment](common-speed-concat-20261126.md) passed 16 actual-data pairs, two additional input-lifecycle pairs and the existing chromosome-list object interface. For interleaved 128-file input, medians were 9.08 → 5.26 seconds (1.73×); for contiguous 32-file input, 2.20 → 1.47 seconds (1.50×). These compare against the previous concat implementation, not upstream, and are separate from the 15-task table above.
