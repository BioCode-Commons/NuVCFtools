# Concatenation head selection and index-only discovery

Implementation `b6c7263` versus the concat implementation at `9dc88f1` (the frozen before tree is the later integrated source, with no additional concat change). Oscar job **9648432**, node `node1838.oscar.ccv.brown.edu`, one physical core. Additional controls ran in job **9648554**.

The CLI owns one head per active input and selects the stable minimum with a tournament tree. Refresh costs O(log K) per emitted record after initialization; ties retain input-file order. EOF on the first active file still advances the original partial-sort window before other files advance. Header-only files and duplicate input paths remain supported. The legacy Reader path stays available for callers that do not enable the CLI tree.

Chromosome discovery calls the existing tabix index-list implementation without first creating an unused gzip input stream. Object-based `get_chromosomes` delegates to the same implementation and passed its additional control. There are no chromosome-length, coordinate-width or file-count thresholds for choosing the CLI algorithm.

## Actual-data measurements

22,382 original 1000 Genomes Phase 3 chr22 records and 100 samples were partitioned into contiguous or interleaved sorted shards. No genotype or allele values were generated. Inputs are the same paired files, with 2, 8, 32 or 128 shards. Bgzip/tabix preparation was excluded: the initial fixture preparation took 11.10 seconds and produced 5,925,038 bytes including indexes. Table medians use three paired repetitions for contiguous/32 and interleaved/128; other rows have one pair and are approximate. Timing includes startup, index discovery, reading, sorting and all stdout writing. RSS is GNU time peak process RSS in MiB, not summed simultaneous-child memory.

| Shard layout | Files | Before wall (s) | After wall (s) | Speedup | Before RSS (MiB) | After RSS (MiB) | Full bytes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| contiguous | 2 | 0.45 | 0.27 | 1.67× | 10.500 | 10.875 | Identical |
| contiguous | 8 | 0.64 | 0.54 | 1.19× | 11.625 | 11.625 | Identical |
| contiguous | 32 | 2.20 | 1.47 | 1.50× | 16.500 | 16.125 | Identical |
| contiguous | 128 | 8.41 | 5.52 | 1.52× | 34.875 | 34.500 | Identical |
| interleaved | 2 | 0.29 | 0.28 | 1.04× | 10.500 | 10.875 | Identical |
| interleaved | 8 | 0.76 | 0.57 | 1.33× | 11.250 | 12.000 | Identical |
| interleaved | 32 | 2.53 | 1.53 | 1.65× | 16.500 | 16.125 | Identical |
| interleaved | 128 | 9.08 | 5.26 | 1.73× | 34.500 | 34.875 | Identical |

## Checks and limits

Sixteen paired runs passed complete stdout byte comparisons and successful exits, including smaller active windows (2/8 on 32 files) and header-only files at the start/middle. Two more actual-data pairs passed for one input and a duplicated input path; the existing chromosome-list object interface also passed. Stderr normalizes source paths/line numbers only. Passed raw outputs are removed. No fuzzing was used.

The tree-only experiment also passed 16 paired checks, but its 128-file timing improvement was only about 15%; startup remained a major cost. Those measurements are separate and are not combined with this table. An initial index-only draft used the wrong Perl class name and failed before producing output; the class dispatch was corrected before committing, and all checks above use the corrected snapshot. Failed-draft artifacts remain separate.

This table is versus the preceding NuVCFtools implementation, not upstream VCFtools. It establishes performance on this small real region and these shard layouts, not a universal speedup for every concatenation.
