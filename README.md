<div align="center">

# NuVCFtools

**NuVCFtools is the BioCode Commons edition of VCFtools, a C++ and Perl toolkit for filtering and analyzing genetic variants.**

<a id="contents"></a>

<p align="center">
  <a href="#quick-start">Quick start</a> &nbsp;·&nbsp;
  <a href="#usage-and-parameters">Usage</a> &nbsp;·&nbsp;
  <a href="#implementation-status-and-roadmap">Implementation Status and Roadmap</a> &nbsp;·&nbsp;
  <a href="#benchmarks">Benchmarks</a>
  <br>
  <a href="#ai-use-and-review">AI use and review</a> &nbsp;·&nbsp;
  <a href="#questions-and-contributions">Questions and contributions</a> &nbsp;·&nbsp;
  <a href="#acknowledgments-and-references">References</a>
</p>

</div>

---

<a id="quick-start"></a>

## Quick start <sup><sub>[↑ Contents](#contents)</sub></sup>

### 1. Build

Building from Git requires C and C++ compilers, Make, Autoconf, Automake, pkg-config, Perl and the zlib development files.

```sh
git clone https://github.com/BioCode-Commons/NuVCFtools.git
cd NuVCFtools
./autogen.sh
./configure
make
```

### 2. Calculate allele frequencies

Run the compiled executable on the [included example VCF](examples/valid-4.1.vcf).

```sh
./src/cpp/vcftools --vcf examples/valid-4.1.vcf --freq --out example
```

The command writes per-site allele frequencies to `example.frq`.

<a id="usage-and-parameters"></a>

## Usage and parameters <sup><sub>[↑ Contents](#contents)</sub></sup>

| Task | Options | Output |
| --- | --- | --- |
| Calculate allele frequencies at each site | `--freq` | `.frq` |
| Report missing genotypes by sample | `--missing-indv` | `.imiss` |
| Write variants from one chromosome | `--chr CHROM --recode` | `.recode.vcf` |

Select the input with `--vcf FILE`, `--gzvcf FILE` or `--bcf FILE`. Use `--out PREFIX` to name the output files. See the [VCFtools manual](https://vcftools.github.io/man_latest.html) for the full option list.

<a id="implementation-status-and-roadmap"></a>

## Implementation Status and Roadmap <sup><sub>[↑ Contents](#contents)</sub></sup>

NuVCFtools starts from [upstream commit `1f87a83`](https://github.com/vcftools/vcftools/commit/1f87a83402ffd17ea2723a456b7edf5d80b4a22c). The initial import includes the [C++ executable source](src/cpp), the [Perl tools](src/perl) and the [upstream examples](examples). The executable is named `vcftools`.

The first optimization pass removes an intermediate VCF line copy, reuses already parsed genotype fields across bulk filtering/output passes, and removes an unused quadratic result matrix from `--relatedness2`. It preserves the existing formulas, calculation order, output formatting and error-path flushing. See the [comparison and benchmark instructions](tests/README.md).

The second pass replaces repeated random-sample membership searches with direct marking, per-base position overlap queries with guarded range lookups, and per-sample chi-square genotype maps with an equivalent index formula. It also counts Fst alleles directly and uses an in-place sort for broad indel length histograms while retaining the original scan for spans of at most 32. The statistical formulas and floating-point accumulation order remain unchanged.

The third pass stores both relatedness estimators in upper-triangle rows and evaluates each symmetric Manichaikul pair once, while preserving their original output order. LROH reuses a monotonic next-heterozygote cursor and replaces tiny heap-allocated HMM rows with fixed-width double rows. All numerical expressions, initialization and legacy report counting remain unchanged.

The fourth pass targets eight different functions: five format converters, windowed Fst, windowed pi and PCA SNP loadings. Converters copy temporary rows through an 8-KiB buffer; window bins store fixed-width values inline; mask decoding avoids a line-sized short-vector copy. PCA loadings stores exact integer genotype sums compactly. It also removes an unused 012 allele copy and reuses LDhelmet alleles within a site.

The fifth pass indexes BED intervals in place, reads LD payloads in bounded blocks, halves decoded LD genotype storage, and removes an unused retained VCF row copy. Shared Perl indel classification stops redundant suffix scans; validator grouping stops after its third mismatch; phased joins lazily reuse site-level logarithms. A sample-order cache experiment was measured and reverted because sparse-input costs did not justify its dense-input benefit.

The sixth pass expands to frequency burden, Mendelian checks, individual discordance, allele-count buffers, FORMAT encoding and PCA/DGEEV. Burden counters use lazy fixed-size blocks; the first contiguous-growth design was rejected after dense RSS increased. FORMAT encoding keeps one string column and token cursors, preserving legacy short-row inheritance. PCA releases its completed genotype matrix before solver allocations; DGEEV sorts a stable permutation within non-NaN runs and omits unused eigenvector arrays. Numerical accumulation order and compression settings remain unchanged.

The seventh pass keeps only one double row of chi-square expectations instead of the full expected matrix. Windowed pi uses in-place unsigned range differences, a packed mask of the exact original keep decisions, and rolling counts for overlapping emitted windows. It preserves legacy chromosome-revisit bin retention and repeated output. No extra all-window prefix array is added, and statistical expressions remain unchanged.

The eighth pass keeps two rolling LROH beta rows, stores each unchanged posterior in the completed alpha row, and releases each sample's observation buffers after its final report use. Alpha/beta/posterior payload changes from 40N to 16N+32 bytes on this platform, decreasing for N≥2; whole-process memory also includes all other data. Seven LD paths reject candidates using metadata before genotype decoding, allocate the second genotype vector lazily, and release completed input staging before pair calculations. Rejected payloads are still read in the same request sequence: this removes decoding and writes, not input bytes or physical I/O.

A [C++ and Perl algorithm audit (Chinese)](docs/algorithm-audit.zh-CN.md) distinguishes these implemented changes from future candidates and records their compatibility and memory limits.

<a id="benchmarks"></a>

## Benchmarks <sup><sub>[↑ Contents](#contents)</sub></sup>

<!-- cumulative-performance:start -->
The current cumulative comparison measures the original commit `48d19c885e0bb90ad79266e782b3c7d21a80e14c` directly against the final implementation after all eight passes. It contains 51 complete C++ CLI workloads and 6 Perl workloads, with five alternating serial runs per version. These are newly measured original-to-final ratios, not multiplied incremental speedups. All result-byte and exit-code comparisons pass; normal-clock C++ timing diagnostics remain separate.

Representative cumulative gains include sample selection (24.13×), BED inclusion (18.99×) and the 64-allele chi-square workload (9.74×). Long two-sample LROH peak RSS is 290.64 → 158.42 MiB; sparse frequency burden is 33.62 → 4.52 MiB; large-mask windowed pi is 67.80 → 10.98 MiB. These are synthetic workload results, not universal pipeline gains. The largest C++ time regression is `relatedness-compute`: 0.2561 → 0.2719 s (+6.19%). The largest RSS median increase is 336 KiB (+0.24%) in `phase-overlap`. Every control and regression remains in the full tables.

The Perl set contains one complete `vcf-annotate --fill-type` CLI workload and five actual module/script API workloads. Validator and phased-join API measurements are not complete CLI benchmarks; indexed phased-join integration with tabix remains untested. Existing fixed-clock compatibility evidence remains 5,576 C++ CLI cases, 14,859 raw file pairs and 963 matching nonzero exits; the performance rerun adds no production changes and is not added to those regression counts.

[Current cumulative results and hashes](tests/results/cumulative-performance.json) · [All C++ and Perl benchmark tables](docs/algorithm-audit.zh-CN.md) · [Reproduce checks](tests/README.md).

The following per-pass measurements are historical incremental comparisons. Their baseline versions differ from the cumulative comparison above.
<!-- cumulative-performance:end -->

The historical eighth pass was measured against the seventh-pass delivery, with five alternating serial runs per version. Long two-sample LROH RSS changed from 173.69 → 158.42 MiB; asymmetric missingness from 205.25 → 189.94 MiB. Seven high-rejection LD workloads improved 3.4–8.8x, while all payload bytes were still consumed. The wide accepted-pair control changed from 19.72 → 18.72 MiB. The long-INFO/chi-square lifetime case showed no peak-RSS improvement (142.94 → 142.97 MiB, +32 KiB); stage-specific RSS was not measured. Ordinary LROH time changed from 0.0422 → 0.0433 s. All 22 complete-command benchmarks preserve result bytes and exits, and the full audit retains all controls and time/RSS regressions. The largest RSS median increase was 32 KiB.

Final eighth-pass regression passed 5,576 CLI cases and 14,859 raw file pairs against the original commit across matching normal/LAPACK configurations, including 963 matching nonzero exits. LROH kernel probes compare raw posterior, alpha and beta doubles, final floating exception flags and errno in 30,688 cases per C++98 -O0/-O2 build. LD probes check 3,774 cases and 4,017,286 ifstream::read requests per signed/unsigned-char build, including short payloads and exception masks; these are stream requests, not OS or device-I/O traces. Fixed-clock diagnostics remain byte-exact; normal-clock timing diagnostics are retained separately. LROH posterior evaluation now runs backwards, so floating-trap timing is outside the evidence. Existing undefined behavior and arbitrary resource/device failures are not covered by a universal equivalence claim.

[Historical eighth-pass results and hashes](tests/results/lroh-ld-metadata-pass.json) · [Detailed audit](docs/algorithm-audit.zh-CN.md) · [Reproduce checks](tests/README.md).

The historical seventh pass was measured against the sixth-pass delivery, with five alternating runs per version. The 96-by-96-allele chi-square case reduced peak RSS from 440.50 to 221.36 MiB; windowed pi with a 32-MiB multiline mask reduced it from 66.78 to 10.98 MiB. Window-bin storage itself is unchanged. All 15 complete-command benchmarks retain identical result bytes, with ordinary, nonoverlapping, sparse and asymmetric controls reported separately. The largest RSS median increase was 64 KiB; all timings and regressions are recorded in the audit.

That seventh-pass regression passed 5,060 CLI cases and 13,578 raw file pairs across two matching build configurations against the original commit, including 889 matching nonzero exits. Chi-square probes compare raw double bytes, final errno and floating exception flags in 37,551 scenarios per -O0/-O2 build. Actual window helpers are separately checked under default, signed-char and unsigned-char modes. Fixed-clock diagnostics remain unchanged; normal-clock benchmark timing differences are retained separately. Finite tests cover ordinary defined-input behavior, not floating traps, pre-existing undefined behavior or all resource failures.

[Historical seventh-pass results and hashes](tests/results/chisq-window-pi-pass.json) · [Detailed audit](docs/algorithm-audit.zh-CN.md) · [Reproduce checks](tests/README.md).

The historical sixth pass was measured against the fifth-pass delivery with five alternating runs per version. The 2,000-sample singleton burden case reduced peak RSS from 33.64 to 4.48 MiB; long FORMAT encoding reduced it from 106.02 to 87.56 MiB. Fully dense burden controls explicitly touch every block of every row. Dense pointer/allocator overhead remains, and the largest CLI RSS median increase in this corpus was 16 KiB. See all timings and regressions in the audit rather than treating memory improvements as universal speedups.

Final C++ regression passed 4,736 cases and 12,774 raw file pairs across two matched builds against the original commit, including 857 matching errors. All 18 CLI performance workloads preserve result bytes. Actual FORMAT functions pass 61,398 cases plus a separate forced-fallback variant; actual DGEEV source passes 180,378 checks, including 576 wrapper cases. Four sorting benchmarks compare complete binary double outputs and are kept separate from whole-PCA measurements. Fixed-clock regressions compare diagnostics unchanged; normal-clock benchmark timings remain in separate diagnostics. Finite tests do not establish equivalence for baseline undefined behavior or all resource-failure paths. Perl source and its prior limitations are unchanged this pass.

[Historical sixth-pass results and hashes](tests/results/burden-encoding-eigen-pass.json) · [Detailed audit](docs/algorithm-audit.zh-CN.md) · [Reproduce checks](tests/README.md).

The historical fifth pass was measured against the fourth-pass delivery, with five alternating runs per version. BED query workloads improved about 15–18x, tested LD workloads about 1.3–2.3x, and annotate on long repeated alleles about 2.1x. Long VCF records saved approximately 8 MiB peak RSS; a 65,536-sample LD case saved approximately 0.95 MiB. Small workloads still showed increases of 16–160 KiB. These are synthetic measurements, not universal guarantees.

C++ regression passed 4,062 cases and 11,118 raw file pairs across two matched build configurations, including 715 matching errors. Independent checks cover 849,674 BED comparisons, 6,392 actual LD-reader cases and 20 actual entry reset/ownership cases. Final controlled Perl comparison has 180 equal cases, 15 pre-existing unstable cases and 0 deterministic differences. Unstable ASLR/hash outputs are not counted as exact-output passes; indexed phased-join coverage is limited to actual subroutines without tabix. All 13 C++ and six retained-scope Perl benchmark workloads preserve result bytes.

[Historical fifth-pass results and rejected experiments](tests/results/interval-ld-perl-pass.json) · [Detailed audit](docs/algorithm-audit.zh-CN.md) · [Reproduce checks](tests/README.md).

The historical fourth pass was measured against the previously delivered third pass, with the same compiler, library configuration and five alternating runs per version. The main gains are reduced peak RAM:

| Workload | Previous peak RAM | Current peak RAM |
| --- | --- | --- |
| PLINK PED, 400,000 sites / 4 samples | 5.47 MiB | 1.92 MiB |
| 012 matrix, same input | 3.69 MiB | 1.92 MiB |
| LDhat phased/unphased and LDhelmet, same input | 2.83–2.86 MiB | 1.94–1.95 MiB |
| Windowed pi, four sparse 200-Mb chromosomes | 44.73 MiB | 26.33 MiB |
| Windowed Fst, same input | 49.34 MiB | 32.48 MiB |
| Windowed pi with an approximately 8-MiB mask line | 58.05 MiB | 42.03 MiB |
| PCA SNP loadings, 100,000 sites / 32 samples | 69.08 MiB | 55.39 MiB |

All 13 fourth-pass benchmark workloads passed byte-exact result comparisons. Converter median times ranged from about 4.2% shorter to 3.1% longer; windowed pi/Fst took 0.0482/0.0407 s before and 0.0300/0.0216 s after. PCA loadings took 0.4257 -> 0.4104 s. The long-allele 012 case did not reduce measured peak RSS (a 32-KiB increase), and the chromosome-revisit pi case retained approximately the same peak RAM. These are synthetic measurements, not universal guarantees.

Fourth-pass normal-build regression passed 3,470 cases and 9,644 raw file pairs; a separate LAPACK-enabled regression passed 210 cases and 519 pairs. Each compares against its matching original-commit build, with fixed clocks and matching exit codes, including 677 combined error cases. The two configurations total 3,680 cases and 10,163 file pairs. Another 180 checks cover actual copier boundaries and injected read failures. The normal-clock benchmark diagnostics are retained separately.

PCA tests use the same Accelerate library and complete retained matrices or explicit missing-site filtering. The original unfiltered negative-genotype-sum path can create short matrix rows and has existing undefined behavior; this pass does not repair or claim compatibility for that path. [Historical fourth-pass results, limitations and hashes](tests/results/memory-pass.json) · [Reproduce all checks](tests/README.md).

The historical third pass was measured against the previously delivered second-pass version, using the same Apple Clang 21 `-O2` build on macOS arm64. Times and peak RSS below are medians of five sequential runs per version:

| Workload | Previous time | Current time | Previous peak RAM | Current peak RAM |
| --- | --- | --- | --- | --- |
| Relatedness2, 1,200 samples / 32 sites | 2.8110 s | 2.7411 s | 27.30 MiB | 14.92 MiB |
| Yang relatedness, 1,200 samples / 32 sites | 1.0677 s | 1.0642 s | 27.30 MiB | 14.94 MiB |
| Relatedness2, 400 samples / 2,000 sites | 0.9315 s | 0.6667 s | 5.16 MiB | 3.55 MiB |
| Yang relatedness, 400 samples / 2,000 sites | 0.2715 s | 0.2787 s | 5.17 MiB | 3.55 MiB |
| LROH repeated lookahead, 8 samples / 24,000 sites | 0.0379 s | 0.0209 s | 20.69 MiB | 15.98 MiB |
| LROH ordinary tracts, 8 samples / 50,000 sites | 0.0772 s | 0.0417 s | 41.23 MiB | 29.58 MiB |

All nine third-pass benchmark workloads passed exact result-byte comparisons. That implementation also passed 2,760 fixed-clock differential cases against the original commit, comparing 7,500 file pairs and matching exit codes, including 381 matching errors. This includes VCF, VCF.gz, BCF, pipes, partial/error outputs and actual nonempty LROH reports. No output normalization or float tolerance was used.

The Yang compute case traded about 2.6% longer median runtime for 31% lower peak RSS; the other matrix case was close to unchanged in time. Unchanged frequency/missingness/chi-square controls had peak-RSS differences of 16–64 KiB. These single-machine synthetic measurements do not establish universal speedups, byte equivalence for every possible input, or an absolute RAM nonincrease. Runtime logs in normal-clock benchmarks are retained and reported separately from the fixed-clock diagnostic comparisons. [Historical third-pass results and hashes](tests/results/priority-pass.json).

Historical second-pass synthetic benchmarks against commit `48d19c8`, using Apple Clang 21 with `-O2` on macOS arm64, produced the following medians over five runs per version:

| Workload | Baseline time | Optimized time | Baseline peak RAM | Optimized peak RAM |
| --- | --- | --- | --- | --- |
| Random sample marking, 50,000 samples / 25,000 retained | 0.1249 s | 0.0060 s | 6.91 MiB | 6.73 MiB |
| Position overlap, 10,000 records / REF length 3,000 | 0.4380 s | 0.0645 s | 2.27 MiB | 2.30 MiB |
| Genotype chi-square, 200 sites / 96 samples / 6 alleles | 0.5565 s | 0.0176 s | 2.00 MiB | 2.00 MiB |
| Fst, 6,000 sites / 128 samples / 64 alleles | 0.1522 s | 0.1089 s | 2.09 MiB | 2.08 MiB |
| Indel histogram, 40,000 records / length span 20,000 | 0.0392 s | 0.0123 s | 2.41 MiB | 2.39 MiB |
| Filtered frequency, VCF.gz, 128 samples / 80,000 sites | 2.0527 s | 1.6490 s | 5.09 MiB | 5.11 MiB |
| Relatedness2, 1,200 samples / 32 sites | 2.6574 s | 2.6523 s | 40.11 MiB | 27.53 MiB |

In the historical second pass, all result files matched byte for byte in all 12 measured workloads. That fixed-clock differential suite passed 2,394 cases, comparing 6,615 pairs of result/capture/log files and matching exit codes, including 321 nonzero-exit cases. Fixed clocks control runtime diagnostics and the original random seed without deleting fields; normal benchmark logs retain real elapsed time and are reported separately.

The long-REF, broad-indel and multiallelic workloads deliberately expose algorithmic bottlenecks. Their speedups should not be extrapolated to an ordinary SNP pipeline, and the short timings include process startup. Biallelic Fst and individual missingness controls were close to baseline; the narrow-indel control did not regress. Some tasks showed peak-RSS median increases of 16–32 KiB. These changes introduce no new data-sized container, but in-place sorting uses logarithmic stack space, and an absolute RAM guarantee is not established for every invocation.

[Historical second-pass measurements](tests/results/algorithm-pass.json) · [Historical first pass](tests/results/first-pass.json) · [Reproduce the checks](tests/README.md).

<a id="ai-use-and-review"></a>

## AI use and review <sup><sub>[↑ Contents](#contents)</sub></sup>

Codex drafted this README. The initial import preserves the upstream implementation.

<a id="questions-and-contributions"></a>

## Questions and contributions <sup><sub>[↑ Contents](#contents)</sub></sup>

Use [NuVCFtools issues](https://github.com/BioCode-Commons/NuVCFtools/issues) for bug reports and feature requests. For a bug report, include the commit, command, and a small example that reproduces the result.

<a id="acknowledgments-and-references"></a>

## Acknowledgments and references <sup><sub>[↑ Contents](#contents)</sub></sup>

Adam Auton and Anthony Marcketta developed the upstream executable. Petr Danecek developed the Perl module. VCFtools is distributed under the [GNU Lesser General Public License v3](LICENSE).

Danecek P et al. *The variant call format and VCFtools*. Bioinformatics 27(15), 2156–2158 (2011). [Paper](https://doi.org/10.1093/bioinformatics/btr330) · [VCFtools project](https://vcftools.github.io/)
