# Exact-output and memory checks

These checks compare the CLI with unmodified commit
`48d19c885e0bb90ad79266e782b3c7d21a80e14c`. They require Python 3, C/C++
compilers, and zlib. They do not download data or install dependencies.

The final original-to-eighth-pass performance comparison is recorded in
[`results/cumulative-performance.json`](results/cumulative-performance.json).
It contains 51 complete C++ CLI workloads and six Perl workloads (one complete
CLI and five module/script API workloads), with five alternating serial runs
per version. Entries record workload arguments, selected raw measurements,
wall-time and peak-RSS medians, and byte-comparison status. C++ input/binary
hashes and Perl source/configuration metadata are retained in the report.
The workload inputs and benchmark helpers are described in the relevant
sections below. Four timing rechecks retain their initial observations and
document the selection rule. These cumulative ratios compare the original
directly with the final sources; do not multiply the historical per-pass ratios.
Normal-clock C++ timing diagnostics are tracked separately from result bytes;
the fixed-clock regression suite below compares complete raw outputs and logs.

## Build both versions with identical settings

Use an unmodified checkout or source snapshot for `--baseline`:

```sh
python3 tests/build_comparison.py \
  --baseline /path/to/unmodified/NuVCFtools \
  --out-dir /tmp/nuvcf-build --cc clang --cxx clang++
```

The helper records compiler versions, flags and binary hashes. It uses `-O2`,
the same package version, and no fast-math options for both builds. It is a
test helper, not a replacement for the documented Autotools installation.
Optional LAPACK/PCA is disabled by default. The separate PCA checks below enable
the same library for both versions.

Each version has two executables:

- `vcftools`: normal production code, used for timing and memory measurements.
- `vcftools-fixed-clock`: the same object files linked with `fixed_time.c`,
  used only for deterministic regression comparisons. The fixed clock controls
  runtime log entries and the existing random-subset seed. It does not replace
  any parsing, filtering, calculation, or output function.

## Compare exact bytes

```sh
python3 tests/generate_fixtures.py --out-dir /tmp/nuvcf-fixtures
python3 tests/generate_algorithm_fixtures.py --out-dir /tmp/nuvcf-algorithm-fixtures
python3 tests/generate_priority_fixtures.py --out-dir /tmp/nuvcf-priority-fixtures
python3 tests/generate_memory_fixtures.py --out-dir /tmp/nuvcf-memory-fixtures
python3 tests/compare_outputs.py \
  --baseline /tmp/nuvcf-build/baseline/vcftools-fixed-clock \
  --candidate /tmp/nuvcf-build/candidate/vcftools-fixed-clock \
  --fixtures /tmp/nuvcf-fixtures \
  --extra-fixtures /tmp/nuvcf-algorithm-fixtures \
  --extra-fixtures /tmp/nuvcf-priority-fixtures \
  --extra-fixtures /tmp/nuvcf-memory-fixtures --out-dir /tmp/nuvcf-comparison
```

Use a new comparison directory on each run. The runner compares exit codes,
the set of top-level output files, and every byte of those files, stdout,
stderr and logs. It does not sort rows, remove headers, normalize diagnostics,
or allow floating-point differences. BCF is compared as raw compressed bytes.
Private scratch files under `tmp/` are not part of the output-file contract.

The matrix covers VCF, gzipped VCF, BCF, stdin/stdout, compound genotype/site
filters, frequency, depth, missingness, recoding, relatedness, Fst, selected LD
and conversion operations, and diff operations. Generated adversarial inputs
cover absent/reordered/duplicate FORMAT tags, partial missing values, haploid
and unsupported polyploid calls, excluded malformed samples, CRLF, trailing
whitespace, no final newline, and records longer than 1 MiB. Error cases compare
partial result files as well as diagnostics and exit codes. A matching error
does not imply the malformed input is supported.

The additional algorithm corpus runs only its declared commands. It covers
random sample limits with prior keep/remove masks, overlap endpoints and signed
coordinate boundaries, multiallelic Fst counts, chi-square genotype indexes,
and indel histogram spans of 2, 32, 33 and 64. Valid examples also pass through
BCF; intentionally malformed allele and coordinate cases remain VCF/VCF.gz.
The original RNG is seeded from time, so selected-sample comparisons require
the fixed-clock executables as shown above.

For selected cases, repeat `--case-pattern`, for example:

```sh
python3 tests/compare_outputs.py \
  --baseline /tmp/nuvcf-build/baseline/vcftools-fixed-clock \
  --candidate /tmp/nuvcf-build/candidate/vcftools-fixed-clock \
  --fixtures /tmp/nuvcf-fixtures --out-dir /tmp/nuvcf-selected \
  --case-pattern 'extended/*/recode-bcf-filter*' \
  --case-pattern 'extended/*/diff-*'
```

This finite corpus is regression evidence, not a proof for every possible
input, compiler, architecture or optional feature. The Perl suite is outside
this matrix, and PCA uses the separate enabled build below. The fifth pass changed
three Perl source files; its separate checks and nondeterminism limits are
described below. The sixth pass makes no further Perl source changes.

## Measure speed and peak RAM

Generate performance inputs separately from the small regression fixtures:

```sh
python3 tests/generate_fixtures.py --out-dir /tmp/nuvcf-performance \
  --performance --sites 80000 --samples 128 --seed 17 --gzip-performance
python3 tests/benchmark.py \
  --baseline /tmp/nuvcf-build/baseline/vcftools \
  --candidate /tmp/nuvcf-build/candidate/vcftools \
  --input /tmp/nuvcf-performance/performance.vcf.gz --input-format gzvcf \
  --out-dir /tmp/nuvcf-benchmark --repeats 5 -- \
  --freq --minGQ 10 --minDP 5 --remove-filtered-geno-all \
  --maf 0.05 --mac 1 --hwe 0.0001 --max-missing 0.25
```

The benchmark uses normal clocks. Runs are sequential and alternate which
version runs first; do not run other builds or benchmarks concurrently. Timing
includes process startup and exit. There is no warmup phase. `posix_spawn`
avoids a Python pre-exec memory footprint, and `wait4` measures the specific
child's peak RSS (macOS bytes, Linux KiB converted to bytes). Reports retain
individual measurements and median/min/max, not just a selected best run.

All result files and stdout are compared byte for byte on each repeat. Real
runtime logs can differ: their raw bytes and differences are retained and
reported separately, without normalization. `passed` in a benchmark report
means result bytes match and every process succeeded; exact diagnostic-byte
compatibility is checked separately by the fixed-clock regression suite.

The changes do not introduce a new persistent parsing cache. `--relatedness2`
no longer retains an unused N-by-N double result matrix; its two count matrices
remain, so memory complexity is still quadratic. Peak RSS also includes code,
libraries and allocator behavior; small page-sized differences must be reported
instead of claiming an absolute RAM guarantee for every invocation.

The second pass also removes repeated sample membership searches, per-base
position lookups and per-sample genotype maps. Fst updates at most two counters
per genotype. The broad-span histogram sorts its existing vector in place;
this requires logarithmic stack space, but no additional data-sized container.

Generate the nine algorithm workloads with:

```sh
python3 tests/generate_algorithm_benchmarks.py --out-dir /tmp/nuvcf-algorithm-performance
```

Its `manifest.json` records each input, description and argument list. Run
`benchmark.py` on each input using the same build and five repeats as above;
resolve any support-file arguments against the generated directory first.
For example:

```sh
python3 tests/benchmark.py \
  --baseline /tmp/nuvcf-build/baseline/vcftools \
  --candidate /tmp/nuvcf-build/candidate/vcftools \
  --input /tmp/nuvcf-algorithm-performance/positions-overlap.vcf --input-format vcf \
  --out-dir /tmp/nuvcf-overlap-benchmark --repeats 5 -- \
  --positions-overlap /tmp/nuvcf-algorithm-performance/overlap-points.txt --kept-sites
```

The random-selection performance workload writes kept sites, whose contents do
not depend on which samples were selected. The fixed-clock corpus separately
checks the exact selected genotypes. Broad indel and long-REF overlap workloads
deliberately expose scaling bottlenecks; their speedups are not representative
of an ordinary biallelic SNP pipeline. Biallelic Fst/chi-square and narrow indels
serve as controls.

## Relatedness and LROH pass

The priority corpus adds 15 fixtures with 60 declared commands, exercised as
VCF, VCF.gz and BCF, with file and stdin/stdout paths. Cases cover triangular
matrix diagonals, symmetric counts, noncontiguous sample selection, missing or
filtered genotypes, zero denominators, empty inputs, and required-genotype
errors. LROH fixtures produce actual bounded and final regions, including a
homozygous focal sample with several separate regions. The latter checks that
the full suffix count is still added on every region exit. Coordinate-order
and missing-value cases preserve the original observation order.

Generate the third-pass workloads with:

```sh
python3 tests/generate_priority_benchmarks.py --out-dir /tmp/nuvcf-priority-performance
```

The manifest contains two sample/site sizes for both relatedness estimators
and two LROH scenarios. To isolate this pass, build an unchanged second-pass
source snapshot with the same compiler flags and pass its normal executable
as `benchmark.py --baseline`. The recorded regression still compares the
complete final implementation against the original repository commit.

Both relatedness estimators now store upper-triangle double rows of length
N-i. Their two-matrix payload is 8N(N+1) bytes, versus 16N² after the second pass.
Manichaikul also evaluates each symmetric pair once, while still emitting all
N² rows. Yang preserves its upper-triangle output and all floating-point sums.
LROH adds one integer cursor. Its transition rows now store four doubles
inline, and alpha/beta rows store two doubles inline, removing per-observation
heap allocations. Element types, zero initialization, indexing and all HMM
arithmetic expressions remain unchanged; the helper also compiles as C++98.

The reporting-loop model checks are supplementary algorithm evidence, not an
HMM benchmark. The measured CLI workload includes parsing, HMM computations,
matrix accumulation and all output costs; it can therefore show less benefit
than the improvement in one inner loop.

## Conversion, window and PCA memory pass

The memory corpus adds 16 fixtures and 120 declared commands for PLINK PED,
012, phased/unphased LDhat, LDhelmet, windowed Fst and windowed pi. It exercises
long-row chunk boundaries, empty input, filtered samples/genotypes, long alleles,
late parser errors, sparse windows, chromosome revisits, masks and line endings.
Some original converter error paths leave private scratch files behind; the
runner retains these rather than claiming that all temporary directories empty.

Probe the actual bounded copier, including injected stream failures, with:

```sh
python3 tests/check_temporary_rows.py --out-dir /tmp/nuvcf-row-probe
```

This extracts the production helper and compiles it as C++98, comparing bytes,
remaining input, stream state and flush counts against getline plus string
insertion. It does not replace the complete CLI checks.

Generate conversion/window performance inputs separately:

```sh
python3 tests/generate_memory_benchmarks.py --out-dir /tmp/nuvcf-memory-performance
```

The manifest includes five converters sharing 400,000 sites, a long-allele 012
case, sparse genomic windows, chromosome revisits and one approximately 8-MiB
mask line. Resolve support-file arguments against that directory before calling
`benchmark.py`. Long rows now use a single 8-KiB stack buffer; window bins store
four values inline. Window types, resize order and every numerical expression
remain unchanged. The mask decoder removes a line-sized short-vector copy.

### LAPACK-enabled comparisons

On macOS, build both versions with the same Accelerate library:

```sh
python3 tests/build_comparison.py \
  --baseline /path/to/unmodified/NuVCFtools \
  --out-dir /tmp/nuvcf-lapack-build --cc clang --cxx clang++ \
  --lapack-framework Accelerate
python3 tests/generate_pca_fixtures.py --out-dir /tmp/nuvcf-pca-fixtures
VECLIB_MAXIMUM_THREADS=1 python3 tests/compare_outputs.py \
  --baseline /tmp/nuvcf-lapack-build/baseline/vcftools-fixed-clock \
  --candidate /tmp/nuvcf-lapack-build/candidate/vcftools-fixed-clock \
  --fixtures /tmp/nuvcf-fixtures --extra-fixtures /tmp/nuvcf-pca-fixtures \
  --out-dir /tmp/nuvcf-pca-comparison --case-pattern 'pca_*/*'
```

For systems providing LAPACK/BLAS libraries, `--lapack` selects `-llapack -lblas`
instead of a framework. These recorded measurements use Accelerate; they do not
establish equivalence across different numerical libraries. The PCA corpus has
nine fixtures and 35 commands, exercised as VCF/VCF.gz/BCF and pipes. It includes
ordinary PCA controls, SNP loadings, noncontiguous sample selection, explicit
missing-site filtering and errors before matrix construction. The SNP-loading
genotype matrix now stores int sums instead of double sums; the existing use
converts the same exact values back to double.

The original PCA implementation can read beyond short M rows when negative
genotype sums are retained. This existing undefined behavior is outside the
compatibility claim; complete retained data and explicit `--max-missing 1`
filtering are tested. This pass does not change that missing-data behavior.

Generate the two PCA workloads with:

```sh
python3 tests/generate_pca_fixtures.py --performance --out-dir /tmp/nuvcf-pca-performance
```

Use LAPACK-enabled previous-pass and candidate executables for these benchmarks,
with `VECLIB_MAXIMUM_THREADS=1` set for both. Normal builds are used for the other
workloads. The result manifest distinguishes both configurations and baseline
source/binary hashes.

Historical measurements are in `results/first-pass.json`,
`results/algorithm-pass.json` and `results/priority-pass.json`. The fourth-pass
combined implementation is recorded in `results/memory-pass.json`, with distinct
regression/performance baseline and candidate hashes.

## Fifth-pass interval, LD, record ownership and Perl checks

Generate the focused corpus and add it to the original comparison command:

```sh
python3 tests/generate_interval_ld_fixtures.py --out-dir /tmp/nuvcf-interval-ld
# Add --extra-fixtures /tmp/nuvcf-interval-ld to compare_outputs.py.
python3 tests/check_bed_intervals.py --output /tmp/bed-model.json
python3 tests/check_ld_readers.py --baseline /path/to/unmodified/NuVCFtools \
  --source . --out-dir /tmp/ld-readers --cxx clang++
python3 tests/check_entry_reset.py --baseline-source /path/to/unmodified/NuVCFtools \
  --baseline-objects /tmp/nuvcf-build/baseline --candidate-source . \
  --candidate-objects /tmp/nuvcf-build/candidate --out-dir /tmp/entry-reset
```

The LD probe extracts actual source definitions and checks signed and unsigned
char builds in C++98, including partial payloads and final stream state. Headers
must be complete; the original uninitialized packed-byte case with zero available
payload is excluded. The reset driver links real matching objects and headers.
Do not mix objects from a different source revision.

```sh
python3 tests/check_perl_outputs.py --baseline /path/to/unmodified/NuVCFtools \
  --candidate . --out-dir /tmp/perl-final --matrix 0:0,1:0,17:0
# Optional nondeterminism audit, kept separate from passing exact cases:
python3 tests/check_perl_outputs.py --baseline /path/to/unmodified/NuVCFtools \
  --candidate . --out-dir /tmp/perl-hash-audit --matrix 0:1,0:2,1:2,17:2 \
  --baseline-replays 10 --case annotate-window-4.1 --case annotate-window-4.2 \
  --case validator-warning-groups
```

Perl runs at identical physical script paths and keeps original source line
numbers. Every byte, file set and exit status is compared; no sorting or warning
normalization occurs. Baseline-self-unstable ASLR diagnostics/hash iteration are
reported as inconclusive and excluded from equality counts. A candidate matching
one original replay is supporting evidence about nondeterminism, not a universal
byte-equivalence guarantee. The phased-join harness loads actual subroutines and
preserves their source locations; it is not a tabix indexed-file CLI test.

For incremental performance, build the previous fourth-pass delivery as baseline:

```sh
python3 tests/generate_ld_benchmarks.py --out-dir /tmp/ld-performance
python3 tests/generate_interval_memory_benchmarks.py --out-dir /tmp/interval-memory
# Run each manifest workload with benchmark.py, resolving support files absolutely.
python3 tests/generate_perl_benchmarks.py --out-dir /tmp/perl-performance
python3 tests/benchmark_perl.py --baseline /path/to/fourth-pass/NuVCFtools \
  --candidate . --fixtures /tmp/perl-performance --out-dir /tmp/perl-bench --repeats 5
```

Perl generation/copying/hashing are outside the measured interval. Sequential
posix_spawn/wait4 measures each process's wall time and peak RSS; the clock shim
stabilizes emitted dates, not the external monotonic wall timer. Hash settings,
Perl configuration and source hashes are recorded in metadata.json. The four
`tab-*` measurements in the delivered experimental report used a subsequently
reverted sample-order cache; the final vcf-to-tab source equals the fourth pass.
The six accepted-scope Perl workloads and 13 C++ workloads are recorded separately
in `results/interval-ld-perl-pass.json`, including all RAM increases and controls.

## Sixth-pass burden, encoding, discordance and eigen checks

The sixth pass uses the original commit for regression comparisons and the
unchanged fifth-pass delivery for incremental performance comparisons. Keep
those baselines separate. The historical sixth-pass measurements, source hashes, limitations
and retained or rejected experiments are recorded in
`results/burden-encoding-eigen-pass.json`. Previous result files describe their
historical implementations. No Perl production source changes in this pass.

Build the original and current sources with the normal build command above.
Generate the new focused fixtures, using that original executable to prepare
the second-file BCF reference for the diff tests:

```sh
python3 tests/generate_diff_fixtures.py --out-dir /tmp/nuvcf-diff-fixtures \
  --baseline /tmp/nuvcf-build/baseline/vcftools-fixed-clock
python3 tests/generate_burden_mendel_fixtures.py \
  --out-dir /tmp/nuvcf-burden-mendel-fixtures
python3 tests/generate_encoding_fixtures.py --out-dir /tmp/nuvcf-encoding-fixtures
python3 tests/compare_outputs.py \
  --baseline /tmp/nuvcf-build/baseline/vcftools-fixed-clock \
  --candidate /tmp/nuvcf-build/candidate/vcftools-fixed-clock \
  --fixtures /tmp/nuvcf-fixtures \
  --extra-fixtures /tmp/nuvcf-algorithm-fixtures \
  --extra-fixtures /tmp/nuvcf-priority-fixtures \
  --extra-fixtures /tmp/nuvcf-memory-fixtures \
  --extra-fixtures /tmp/nuvcf-interval-ld \
  --extra-fixtures /tmp/nuvcf-diff-fixtures \
  --extra-fixtures /tmp/nuvcf-burden-mendel-fixtures \
  --extra-fixtures /tmp/nuvcf-encoding-fixtures \
  --out-dir /tmp/nuvcf-sixth-comparison
```

The earlier sections generate the five pre-existing fixture directories used
here. New output directories are required. The diff corpus covers mapped and
union-only sample names, duplicate names, missing halves, different allele
dictionaries, empty inputs and existing order errors. Burden/Mendel cases cover
frequency counts, homozygote modes, ancestral alleles, masks, pedigree matching
and the original exact `-1` missing-value rule. Encoding cases cover width
boundaries, reordered and duplicate FORMAT tags, short sample rows, whole-row
missing values and long strings. Full BCF output is compared as raw compressed
bytes, including framing and headers; decompressed equivalence is insufficient.
Exit statuses, partial outputs and fixed-clock diagnostics remain in the same
strict comparison, with no output sorting or floating-point tolerance.

Run the actual FORMAT encoder and writer through matching built objects:

```sh
python3 tests/check_format_encoding.py \
  --baseline-source /path/to/unmodified/NuVCFtools \
  --baseline-objects /tmp/nuvcf-build/baseline \
  --candidate-source . --candidate-objects /tmp/nuvcf-build/candidate \
  --out-dir /tmp/nuvcf-format-probe
python3 tests/check_format_encoding.py \
  --baseline-source /path/to/unmodified/NuVCFtools \
  --baseline-objects /tmp/nuvcf-build/baseline \
  --candidate-source . --candidate-objects /tmp/nuvcf-build/candidate \
  --out-dir /tmp/nuvcf-format-fallback-probe --fallback-threshold 3
python3 tests/check_burden_mendel.py --output /tmp/nuvcf-burden-mendel-model.json
```

The normal FORMAT probe links real `parse_FORMAT` and `print_bcf` code. It
compares all raw FORMAT bytes and a compressed BGZF record stream; that stream
contains records without a BCF file header, so the complete CLI checks remain
necessary. Exhaustive small token patterns specifically verify the original
short-row behavior: trailing fields inherit earlier samples' values, while a
whole `.` or empty sample resets them. The production implementation falls back
to the old splitter and matrix when a genotype string reaches `INT_MAX` bytes
or the FORMAT count exceeds `INT_MAX`, preserving the old splitter's integer
conversions. The second probe compiles a separate source copy in which only
that threshold becomes 3. This exercises the same fallback body and records its
source hash; it does not allocate or test a string near the actual `INT_MAX` boundary and
does not modify the production source.

The burden/Mendel script is an independent algorithm model, not a replacement
for actual CLI tests. It checks ordered counter updates, block boundaries and
the parental genotype product. Defined-input limits remain: allele indices must
be in range, original signed counters and `2*N` dimensions must not overflow,
and the original overfull FORMAT-token write remains outside the equivalence
claim. Unknown FORMAT tags at the beginning or middle are compared in the
encoder probe without invoking the separate legacy writer indexing issue.
The block matrix allocates each counter block once; dense counter payload is
bounded by the original matrix, but pointer directories and allocator overhead
can increase dense-case RSS. Resource-exhaustion timing is not an exact-output
guarantee.

The DGEEV probe compiles both actual source versions into one C++98 driver and
compares every result double by its bytes:

```sh
python3 tests/check_dgeev.py --baseline /path/to/unmodified/NuVCFtools \
  --candidate . --out-dir /tmp/nuvcf-dgeev-probe --cxx clang++ \
  --lapack-framework Accelerate
```

Use `--lapack-framework ''` for `-llapack -lblas` instead. This is separate from
the build helper's `--lapack` option. The sorting probe includes stable ties,
signed zeros, quiet NaN barriers, infinities and overflowing magnitudes; finite
matrix cases call the same LAPACK library through both wrappers. It does not
model signaling-NaN traps, invalid dimensions or arbitrary solver failures.
Also repeat the earlier LAPACK-enabled PCA CLI comparison against its matching
original build. Keep the library and `VECLIB_MAXIMUM_THREADS=1` identical between
versions. Existing ragged PCA rows from unfiltered negative genotype sums remain
outside the defined-input claim; use complete retained matrices or explicit
missing-site filtering as in the existing PCA corpus.

For performance, build the fifth-pass snapshot and the current source in fresh
normal and LAPACK-enabled directories, then generate workloads separately:

```sh
python3 tests/build_comparison.py --baseline /path/to/fifth-pass/NuVCFtools \
  --candidate . --out-dir /tmp/nuvcf-sixth-performance-build \
  --cc clang --cxx clang++
python3 tests/build_comparison.py --baseline /path/to/fifth-pass/NuVCFtools \
  --candidate . --out-dir /tmp/nuvcf-sixth-performance-lapack \
  --cc clang --cxx clang++ --lapack-framework Accelerate
python3 tests/generate_diff_benchmarks.py --out-dir /tmp/nuvcf-diff-performance
python3 tests/generate_burden_mendel_benchmarks.py \
  --out-dir /tmp/nuvcf-burden-mendel-performance
python3 tests/generate_encoding_fixtures.py --performance \
  --out-dir /tmp/nuvcf-encoding-performance
python3 tests/generate_eigen_benchmarks.py --out-dir /tmp/nuvcf-eigen-performance
```

Run each manifest entry with `benchmark.py` and the normal-clock executables,
five alternating repeats, and a new output directory. Resolve relative support
paths such as the diff reference and pedigree against that manifest's directory.
The PCA entries require the LAPACK-enabled pair and one library thread; the
other entries use the normal pair. For example:

```sh
python3 tests/benchmark.py \
  --baseline /tmp/nuvcf-sixth-performance-build/baseline/vcftools \
  --candidate /tmp/nuvcf-sixth-performance-build/candidate/vcftools \
  --input /tmp/nuvcf-encoding-performance/encoding-many-long-fields.vcf \
  --input-format vcf --out-dir /tmp/nuvcf-encoding-benchmark --repeats 5 -- \
  --recode-bcf --recode-INFO-all
python3 tests/benchmark_dgeev_sort.py --baseline /path/to/fifth-pass/NuVCFtools \
  --candidate . --out-dir /tmp/nuvcf-sort-benchmarks --repeats 5 \
  --cxx clang++ --lapack-framework Accelerate
```

The burden workloads include sparse and empty matrices, increasing frequency
coverage, and explicit controls in which every sample touches every block,
including a one-counter final block. Those controls expose dense-case overhead
that sparse inputs cannot reveal. The sort benchmark uses the actual sorters
and writes complete binary eigenvalues and eigenvectors. Its time includes
process startup, matrix initialization and output; it is not an end-to-end PCA
speed claim. Avoid concurrent builds, checks or other benchmarks during measured
runs. Retain all increases as well as reductions in runtime and peak RSS.

## Seventh-pass chi-square and windowed pi checks

The seventh pass uses the original commit for complete CLI regressions and the
frozen sixth-pass source for incremental performance measurements and focused
function probes. The historical seventh-pass evidence, source/binary hashes and measured RAM
increases or decreases are in `results/chisq-window-pi-pass.json`. Earlier JSON
files remain historical records. No Perl production source changes in this pass;
its earlier nondeterminism and tabix limitations still apply.

Build the original and current sources in matching normal and LAPACK configurations:

```sh
python3 tests/build_comparison.py --baseline /path/to/unmodified/NuVCFtools \
  --candidate . --out-dir /tmp/nuvcf-seventh-build --cc clang --cxx clang++
python3 tests/build_comparison.py --baseline /path/to/unmodified/NuVCFtools \
  --candidate . --out-dir /tmp/nuvcf-seventh-lapack --cc clang --cxx clang++ \
  --lapack-framework Accelerate
python3 tests/generate_chisq_fixtures.py --out-dir /tmp/nuvcf-chisq-fixtures
python3 tests/generate_window_pi_fixtures.py --out-dir /tmp/nuvcf-window-pi-fixtures
```

Generate the earlier corpus directories with the commands above. When preparing
the diff reference BCF, use the original executable from this build. Then run
the cumulative corpus, adding both new fixture directories:

```sh
python3 tests/compare_outputs.py \
  --baseline /tmp/nuvcf-seventh-build/baseline/vcftools-fixed-clock \
  --candidate /tmp/nuvcf-seventh-build/candidate/vcftools-fixed-clock \
  --fixtures /tmp/nuvcf-fixtures \
  --extra-fixtures /tmp/nuvcf-algorithm-fixtures \
  --extra-fixtures /tmp/nuvcf-priority-fixtures \
  --extra-fixtures /tmp/nuvcf-memory-fixtures \
  --extra-fixtures /tmp/nuvcf-interval-ld \
  --extra-fixtures /tmp/nuvcf-diff-fixtures \
  --extra-fixtures /tmp/nuvcf-burden-mendel-fixtures \
  --extra-fixtures /tmp/nuvcf-encoding-fixtures \
  --extra-fixtures /tmp/nuvcf-chisq-fixtures \
  --extra-fixtures /tmp/nuvcf-window-pi-fixtures \
  --out-dir /tmp/nuvcf-seventh-comparison
VECLIB_MAXIMUM_THREADS=1 python3 tests/compare_outputs.py \
  --baseline /tmp/nuvcf-seventh-lapack/baseline/vcftools-fixed-clock \
  --candidate /tmp/nuvcf-seventh-lapack/candidate/vcftools-fixed-clock \
  --fixtures /tmp/nuvcf-fixtures --extra-fixtures /tmp/nuvcf-pca-fixtures \
  --case-pattern 'pca_*/*' --out-dir /tmp/nuvcf-seventh-pca-comparison
```

The chi-square fixtures cover changing and asymmetric genotype-category counts,
zero margins, absent observations, missing halves, legacy out-of-range allele
IDs, filters, non-diploid calls, ordering and partial/error outputs. The CLI
always calls this calculation with `min_pval=-1.0`: `--min-r2` cases are
ignored-option controls, not evidence for a CLI p-value filter. Windowed-pi
fixtures cover overlapping and tiled windows, unsorted/duplicate positions,
chromosome revisits, retained bin zero, empty update ranges, large coordinates,
mask clipping and gaps, binary mask bytes, thresholds and inversion. Applicable
VCF/VCF.gz/BCF and stdin paths are compared without sorting, floating tolerance
or output normalization. The original executable supplies BCF conversions;
fixtures that cannot safely be converted explicitly disable that preparation.
Exit status, complete file sets, partial output and fixed-clock diagnostics are
part of the raw-byte comparison.

The chi-square change replaces the complete expected matrix with one reusable
double row. Each expected value is still written to double storage before use;
the observed matrix, row/column totals, chi-square addition order, `pow`, degrees
of freedom and gamma calls stay unchanged. All expected cells, including zero
margins, are evaluated. Computation of expected values now interleaves with the
chi-square loop one row at a time, so instruction-level floating-trap timing
and allocation-failure timing are outside the compatibility evidence.

```sh
python3 tests/check_chisq.py --baseline /path/to/sixth-pass/NuVCFtools \
  --candidate . --out-dir /tmp/nuvcf-chisq-probe --cxx clang++
python3 tests/check_window_pi.py --baseline /path/to/sixth-pass/NuVCFtools \
  --candidate . --out-dir /tmp/nuvcf-window-pi-probe --cxx clang++
```

The chi-square probe extracts actual old/new functions and links the unchanged
gamma implementation. Each C++98 build (`-O0` and `-O2`) checks the same 37,551
inputs: ordered short genotype sequences, all 3x3 contingency tables with cell
counts 0/1/2, randomized dimensions and missing/invalid IDs, and large rectangular
or empty cases. It compares the raw bytes of chi-square, degrees of freedom and
p-value, including NaNs; integer counts, final floating exception flags and
errno also match. The environment uses nontrapping `FE_TONEAREST`. These are two
builds of the same input corpus, not 75,102 independent inputs. Existing signed
dimension/count overflow, mismatched vector lengths and untested excess-precision
architectures are outside the checks.

The windowed-pi probe extracts the actual new helpers and the previous range
loop with identifier adaptations. It builds C++98 `-O2` with default, signed
and unsigned char settings. Each configuration performs 132,620 range updates,
16,397,384 bin-value comparisons, 8,192 mask-predicate comparisons and 3,379,458
rolling-range comparisons. The three configurations reuse the same corpus.
It checks unsigned-long modular wrap, chromosome shrink-to-one and delayed
regrowth, repeated local prefix scans, every input byte with thresholds and
inversion, and unsigned endpoint wrap without allocating a multi-GiB mask.
These helper checks do not test the mask-file parser or replace the CLI corpus.

Windowed pi retains the same four unsigned-long counters per bin. Range
differences replace repeated bin updates, and a local prefix value reconstructs
each bin during output without mutating the stored differences. A chromosome
revisit retains the original bin-zero value and duplicate-output behavior.
Only the output-stage mask representation changes to packed keep decisions;
the original char-to-short-to-char narrowing occurs before threshold/inversion.
Rolling counts use constant extra state, with rescans for disjoint or backward
ranges and resets for empty ranges. There is no full mask prefix-count array.
The mask payload reduction is not an eightfold whole-process RSS claim. Original
signed-overflow/invalid-index behavior and resource exhaustion remain excluded.

For incremental performance, build the sixth-pass delivery as baseline in
fresh directories and generate workloads before measuring:

```sh
python3 tests/build_comparison.py --baseline /path/to/sixth-pass/NuVCFtools \
  --candidate . --out-dir /tmp/nuvcf-seventh-performance-build \
  --cc clang --cxx clang++
python3 tests/build_comparison.py --baseline /path/to/sixth-pass/NuVCFtools \
  --candidate . --out-dir /tmp/nuvcf-seventh-performance-lapack \
  --cc clang --cxx clang++ --lapack-framework Accelerate
python3 tests/generate_chisq_benchmarks.py --out-dir /tmp/nuvcf-chisq-performance
python3 tests/generate_window_pi_benchmarks.py --out-dir /tmp/nuvcf-window-pi-performance
python3 tests/benchmark.py \
  --baseline /tmp/nuvcf-seventh-performance-build/baseline/vcftools \
  --candidate /tmp/nuvcf-seventh-performance-build/candidate/vcftools \
  --input /tmp/nuvcf-chisq-performance/chisq-matrix-64.vcf \
  --input-format vcf --out-dir /tmp/nuvcf-chisq-matrix-64-benchmark \
  --repeats 5 -- --geno-chisq
```

Run the other manifest workloads in the same way, resolving mask-file arguments
against the manifest directory. Chi-square workloads include 64/96-allele large
matrices, both 2-by-96 and 96-by-2 orientations, and biallelic/six-allele controls.
Windowed-pi workloads isolate a 32-MiB multiline mask, overlapping and tiled
mask windows, dense overlapping updates, ordinary tiled updates, sparse bins
and chromosome revisits. Use normal builds for these commands; any retained
PCA controls require the matching LAPACK pair with
`VECLIB_MAXIMUM_THREADS=1` for both versions.

All measurements use five sequential, alternating runs per version, normal
clocks and each child's own `wait4` peak RSS. Do not run generation, builds,
probes or another benchmark concurrently. Raw result files, stdout and exit
codes must match; elapsed-time diagnostics are retained separately without
rewriting. Keep dense, sparse and unchanged controls, and report all measured
increases along with improvements.

## Eighth-pass rolling LROH and LD metadata checks

The eighth pass compares complete CLI behavior with the original commit and
uses the frozen seventh-pass delivery for incremental performance and focused
kernel/reader probes. Keep those baselines separate. Current measurements,
source/binary hashes and limitations are in `results/lroh-ld-metadata-pass.json`;
the earlier result files describe their historical implementations. Perl source
is unchanged in this pass.

Build both original and candidate sources with matching configurations, then
generate the new corpora:

```sh
python3 tests/build_comparison.py --baseline /path/to/unmodified/NuVCFtools \
  --candidate . --out-dir /tmp/nuvcf-eighth-build --cc clang --cxx clang++
python3 tests/build_comparison.py --baseline /path/to/unmodified/NuVCFtools \
  --candidate . --out-dir /tmp/nuvcf-eighth-lapack --cc clang --cxx clang++ \
  --lapack-framework Accelerate
python3 tests/generate_lroh_beta_fixtures.py --out-dir /tmp/nuvcf-lroh-beta-fixtures
python3 tests/generate_ld_metadata_fixtures.py --out-dir /tmp/nuvcf-ld-metadata-fixtures
```

Generate all earlier fixture directories using the preceding sections. The diff
reference BCF must be prepared with the original executable. Add both new
directories to the full regression rather than testing only the modified paths:

```sh
python3 tests/compare_outputs.py \
  --baseline /tmp/nuvcf-eighth-build/baseline/vcftools-fixed-clock \
  --candidate /tmp/nuvcf-eighth-build/candidate/vcftools-fixed-clock \
  --fixtures /tmp/nuvcf-fixtures \
  --extra-fixtures /tmp/nuvcf-algorithm-fixtures \
  --extra-fixtures /tmp/nuvcf-priority-fixtures \
  --extra-fixtures /tmp/nuvcf-memory-fixtures \
  --extra-fixtures /tmp/nuvcf-interval-ld \
  --extra-fixtures /tmp/nuvcf-diff-fixtures \
  --extra-fixtures /tmp/nuvcf-burden-mendel-fixtures \
  --extra-fixtures /tmp/nuvcf-encoding-fixtures \
  --extra-fixtures /tmp/nuvcf-chisq-fixtures \
  --extra-fixtures /tmp/nuvcf-window-pi-fixtures \
  --extra-fixtures /tmp/nuvcf-lroh-beta-fixtures \
  --extra-fixtures /tmp/nuvcf-ld-metadata-fixtures \
  --out-dir /tmp/nuvcf-eighth-comparison
VECLIB_MAXIMUM_THREADS=1 python3 tests/compare_outputs.py \
  --baseline /tmp/nuvcf-eighth-lapack/baseline/vcftools-fixed-clock \
  --candidate /tmp/nuvcf-eighth-lapack/candidate/vcftools-fixed-clock \
  --fixtures /tmp/nuvcf-fixtures --extra-fixtures /tmp/nuvcf-pca-fixtures \
  --case-pattern 'pca_*/*' --out-dir /tmp/nuvcf-eighth-pca-comparison
```

LROH fixtures include long renormalizing chains with nonempty reports, unequal
per-sample histories, a one-observation cohort that emits a final tract, empty
histories, missing halves and non-diploid calls, filters, mild coordinate
backtracking, late errors and an input without its final newline. Existing
priority fixtures continue covering ordinary and repeated-lookahead reports.
The LD corpus adds 9 fixtures and 65 commands for metadata acceptance and
rejection across all seven paths;
complete CLI output, sample/position order, warnings, partial artifacts and exit
codes remain part of the same raw-byte comparison. Applicable VCF, VCF.gz, BCF
and stdin routes are exercised. Fixed clocks control diagnostics and RNG; no
sorting, numeric tolerance or output normalization is permitted.

Run the actual arithmetic and reader probes against the seventh-pass source:

```sh
python3 tests/check_lroh_beta.py --baseline /path/to/seventh-pass/NuVCFtools \
  --candidate . --out-dir /tmp/nuvcf-lroh-beta-probe --cxx clang++
python3 tests/check_ld_metadata.py --baseline /path/to/seventh-pass/NuVCFtools \
  --candidate . --out-dir /tmp/nuvcf-ld-metadata-probe --cxx clang++
python3 tests/check_ld_readers.py --baseline /path/to/unmodified/NuVCFtools \
  --source . --out-dir /tmp/nuvcf-eighth-ld-readers --cxx clang++
```

The LROH probe extracts actual arithmetic blocks. Each C++98 `-O0`/`-O2` build
checks the same 30,688 cases covering 553,039 observations: 27,993 exhaustive
short sequences, 2,500 randomized cases, 15 long renormalizing chains and 180
special-value cases. Uninstrumented variants compare raw posterior doubles.
Additional instrumented variants capture every alpha and beta double, and must
retain the uninstrumented posterior bytes, final floating exception flags and
errno. Quiet-NaN payloads, signed zero, infinities and supported denormals are
included. This is two builds of the same corpus, not twice as many independent
inputs. Full CLI tests separately cover observation collection, reporting and
the lifetime of released buffers.

The forward alpha pass and each backward beta expression retain their original
double storage, multiplication/addition order, transition/emission indices and
normalization loops. Two fixed beta rows replace the full matrix. Once a site's
posterior is computed, it overwrites the now-dead first alpha component; reporting
reads those stored posteriors in the original ascending order. On the measured
platform, alpha/beta/posterior workspace changes from `40*N_obs` bytes to
`16*N_obs + 32` bytes, excluding vector metadata and other observations. This is
an allocation bound, not a process-RSS prediction. It saves payload for two or
more observations; the array payload for one observation is eight bytes larger.
After each sample's complete
report, its emission, transition, position and heterozygosity buffers are released.

Posterior evaluation now runs backwards and interleaves with beta computation.
The probe uses nontrapping `FE_TONEAREST`; instruction-level floating-trap timing,
asynchronous rounding changes and untested excess-precision architectures are
outside the evidence. The original normalization loop can fail to terminate on
zero/negative rows; those pathological multi-site inputs and existing integer
overflow are not repaired by this optimization.

LD metadata rejection omits genotype decoding, not physical payload reads. The
discard path consumes the same bounded read requests and final one-byte read,
including the original short-read/failure sequence. It does not seek past a
rejected payload or introduce an all-site cache. Pairing decisions and warnings
retain their original order. Partner genotype vectors are allocated on first
accepted use; SNP-list anchors are allocated when traversed. Completed input
entries and staging buffers are released before temporary-file analysis.

The metadata reader probe extracts actual definitions and traces `ifstream::read`
calls in C++98 signed-char and unsigned-char builds. Each build checks the same
3,774 cases and 4,017,286 read requests, including 1,437 skip-only cases, 1,632
short-payload cases and 1,910 exception/fault cases; those categories can overlap.
It compares metadata, accepted genotype values, read-request lengths and order,
final stream state, `gcount`, position, remaining bytes and thrown status. This
traces C++ stream requests, not operating-system calls or storage-device traffic.
The separate original-reader probe retains the earlier raw decoder comparisons.
Rejected-only candidate vectors must
remain unallocated. Complete headers, actual EOF, injected payload `badbit` and
selected exception masks are covered; a failed record ends the probe before a
malformed next header. This is neither arbitrary storage-device fault injection
nor a complete CLI test. The old packed-reader uninitialized case with no payload
byte available is excluded. Resource-exhaustion timing and other pre-existing
undefined behavior remain outside a universal compatibility claim.

For incremental performance, build the seventh-pass delivery as baseline and
generate all inputs before any timed run:

```sh
python3 tests/build_comparison.py --baseline /path/to/seventh-pass/NuVCFtools \
  --candidate . --out-dir /tmp/nuvcf-eighth-performance-build \
  --cc clang --cxx clang++
python3 tests/generate_lroh_beta_benchmarks.py --out-dir /tmp/nuvcf-lroh-beta-performance
python3 tests/generate_ld_metadata_benchmarks.py --out-dir /tmp/nuvcf-ld-metadata-performance
python3 tests/benchmark.py \
  --baseline /tmp/nuvcf-eighth-performance-build/baseline/vcftools \
  --candidate /tmp/nuvcf-eighth-performance-build/candidate/vcftools \
  --input /tmp/nuvcf-lroh-beta-performance/lroh-beta-two-samples.vcf \
  --input-format vcf --out-dir /tmp/nuvcf-lroh-beta-two-samples-benchmark \
  --repeats 5 -- --LROH --chr 1
```

Run every manifest workload with its exact arguments, resolving support-file
paths against that manifest's directory. LROH measurements include long two-sample
histories, equal-size cohorts, asymmetric missing histories, ordinary tracts,
single-sample and empty controls. LD measurements must retain both rejection-heavy
and accepted-pair controls; skipping decode is not a claim of reduced physical
I/O. Use five sequential alternating runs per version, each child's own `wait4`
peak RSS and normal external wall clocks. Do not run builds, generation, probes
or other benchmarks concurrently. Compare complete result files, stdout and exit
codes; retain raw elapsed-time diagnostics separately. Report time and RAM
regressions along with gains.
