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

This branch adds ordered worker processes to 19 Perl commands. It also changes genotype decoding, statistics reduction and multi-file selection; see the [implementation inventory](benchmarks/parallel-perl-tools.md). Four of the 23 previously serial Perl commands still have no computation worker pool. More workers do not improve every task.

<a id="benchmarks"></a>

## Benchmarks <sup><sub>[↑ Contents](#contents)</sub></sup>

The [single-core results](benchmarks/single-thread-20261127.md) reduced to-tab and compare time by 21.2% and 14.9% against the preceding branch version on the measured case. The [latest memory results](benchmarks/parallel-memory-20261127.md) reduce compare and stats PSS by 28.7% and 14.5% at 16 workers, with runtime approximately unchanged. The [preceding measurements](benchmarks/parallel-state-memory-20261127.md) cover annotate, compare, validator, stats, merge and fill-aa. Earlier branch measurements are recorded in the [23-tool Perl comparison](benchmarks/parallel-perl-tools.md), including full output checks, wall time, worker-inclusive memory and cases that did not improve. The [earlier all-entrypoint report](benchmarks/all-tools-vs-upstream.md) also covers C++ commands and GNU sort. These branch results have not been published to the BioCode Commons website.

<a id="ai-use-and-review"></a>

## AI use and review <sup><sub>[↑ Contents](#contents)</sub></sup>

Codex drafted this README and implemented the branch changes. The linked reports describe the tests and measured output comparisons; they do not establish equivalence for every input or option.

<a id="questions-and-contributions"></a>

## Questions and contributions <sup><sub>[↑ Contents](#contents)</sub></sup>

Use [NuVCFtools issues](https://github.com/BioCode-Commons/NuVCFtools/issues) for bug reports and feature requests. For a bug report, include the commit, command, and a small example that reproduces the result.

<a id="acknowledgments-and-references"></a>

## Acknowledgments and references <sup><sub>[↑ Contents](#contents)</sub></sup>

Adam Auton and Anthony Marcketta developed the upstream executable. Petr Danecek developed the Perl module. VCFtools is distributed under the [GNU Lesser General Public License v3](LICENSE).

Danecek P et al. *The variant call format and VCFtools*. Bioinformatics 27(15), 2156–2158 (2011). [Paper](https://doi.org/10.1093/bioinformatics/btr330) · [VCFtools project](https://vcftools.github.io/)
