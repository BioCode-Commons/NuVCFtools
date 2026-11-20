# NuVCFtools 算法审查与优化顺序

基线：`48d19c885e0bb90ad79266e782b3c7d21a80e14c`。范围：C++ 解析、过滤、统计、格式转换、diff、数值例程、BGZF，以及 Perl 模块和命令行脚本。按算法族归并辅助函数，不把每个 getter 列成独立算法。

约束是保留结果文件的原始字节、样本/记录顺序、统计定义、每个统计量内部的浮点运算顺序、缺失值处理、诊断和退出行为（计算调度变化及保证边界见各批说明），RAM 尽量不增加。下文复杂度来自静态代码分析；八批已实现项均有下述差分及性能证据；当前第八批处理 LROH 滚动 beta、posterior 复用及样本输入生命周期，以及 LD 元数据解码筛选和缓冲生命周期，其余仍为候选。复杂度改善不代表已测得的加速结果。

<!-- cumulative-performance:start -->
## 当前累计测量：原始版本 → 八批优化后的最终版本

本节重新使用同一原始 commit `48d19c885e0bb90ad79266e782b3c7d21a80e14c` 与当前最终源码做完整测量，**不相乘八批加速比例、不拼接不同增量基线的数字**。以下历史第一至第八批仍记录各批当时的增量效果；若要回答“相对最初版本一共快多少、RAM 少多少”，应引用本节和 [累计结果 JSON](../tests/results/cumulative-performance.json)。本次仅补充统一性能证据，没有增加第九批生产代码改动。

共 **51 个 C++ 完整 CLI 场景**与 **6 个 Perl 场景**，每个原版/最终版各五次，交替顺序串行运行。使用真实外部时钟和每个子进程自身的 wait4 峰值 RSS；PCA 使用匹配的 LAPACK 配置、相同数学库并固定 `VECLIB_MAXIMUM_THREADS=1`。表中是 wall time 与 RSS 的各自中位数；加速倍数为原版时间÷最终版时间，百分比为（最终版÷原版−1）×100%，所以**正百分比表示增加，负百分比表示减少**。MiB=1,048,576 字节。

全部场景的结果文件、stdout 与退出码对照通过，C++ 正常时钟的耗时诊断单独记录，不能把该字段声称为字节一致。Perl 固定 hash/日期/locale 环境，原始输出与诊断比较方法及 API 范围见下表与 JSON。性能测量独立于已有固定时钟回归：最终 C++ 已通过 **5,576** 个 CLI 用例、**14,859** 对原始文件、**963** 个匹配非零退出；这些是现有第八批兼容性证据，并非本轮重新执行或与 benchmark 次数相加的数字。

代表性结果如下；完整表同时保留每个控制组和回退项。

| 功能 | 场景 | 加速倍数 | 峰值 RSS：原版 → 最终版 | RSS 变化 |
| --- | --- | --- | --- | --- |
| 随机样本筛选 | `random-sample-marking` | 24.13× | 6.91 → 6.53 MiB | -5.43% |
| BED 包含过滤 | `bed-disjoint` | 18.99× | 2.14 → 2.16 MiB | +0.73% |
| 六十四等位 χ² | `chisq-matrix-64` | 9.74× | 89.61 → 45.62 MiB | -49.08% |
| LROH 长两样本链 | `lroh-beta-two-samples` | 1.43× | 290.64 → 158.42 MiB | -45.49% |
| 稀疏 frequency burden | `burden-rare-2000` | 1.03× | 33.62 → 4.52 MiB | -86.57% |
| windowed π 的大 mask | `window-pi-mask-memory` | 0.98× | 67.80 → 10.98 MiB | -83.80% |

这批数据中 7 个 C++ 场景、2 个 Perl 场景的耗时中位数增加；C++ 最大耗时百分比回退为 `relatedness-compute`：0.2561 → 0.2719 s（+6.19%）。最大 RSS 中位数增加为 `phase-overlap` 的 336 KiB（+0.24%）。短命令的启动时间和 RSS 以页为单位的波动也计入原始结果，不删去回退项，不声称所有工具或任意输入都更快、更省 RAM。

### C++ 完整命令累计结果（51 个场景）

| 场景 / 输入 | 测量范围 | 时间：原版 → 最终版 | 加速倍数 | 时间变化 | 峰值 RSS：原版 → 最终版 | RSS 变化 |
| --- | --- | --- | --- | --- | --- | --- |
| `relatedness2-matrix`: 1200 samples / 32 sites; missing and swapped heterozygous genotypes. | CLI | 2.8333 → 2.7593 s | 1.03× | -2.61% | 39.89 → 14.92 MiB | -62.59% |
| `relatedness2-compute`: 400 samples / 2000 sites; missing and swapped heterozygous genotypes. | CLI | 0.9202 → 0.6366 s | 1.45× | -30.83% | 6.73 → 3.56 MiB | -47.10% |
| `relatedness-matrix`: 1200 samples / 32 sites; missing and swapped heterozygous genotypes. | CLI | 1.0437 → 1.0428 s | 1.00× | -0.08% | 27.30 → 14.95 MiB | -45.22% |
| `relatedness-compute`: 400 samples / 2000 sites; missing and swapped heterozygous genotypes. | CLI | 0.2561 → 0.2719 s | 0.94× | +6.19% | 5.17 → 3.56 MiB | -31.12% |
| `lroh-ordinary-tracts`: 50000 sites / 8 samples; homozygous tracts separated by focal heterozygotes. | CLI | 0.0763 → 0.0399 s | 1.91× | -47.66% | 41.75 → 29.70 MiB | -28.85% |
| `lroh-beta-two-samples`: One million observations / two samples; long homozygous tracts and a large per-sample alpha/beta/posterior workspace; nonempty report. | CLI | 0.6967 → 0.4877 s | 1.43× | -30.00% | 290.64 → 158.42 MiB | -45.49% |
| `ld-metadata-local-geno`: Most same-chromosome distances and all cross-chromosome pairs reject; a nonempty tail of long-distance pairs remains. | CLI | 1.3606 → 0.0728 s | 18.68× | -94.65% | 2.28 → 2.31 MiB | +1.37% |
| `ld-metadata-local-hap`: Most same-chromosome distances and all cross-chromosome pairs reject; a nonempty tail of long-distance pairs remains. | CLI | 1.3956 → 0.0754 s | 18.52× | -94.60% | 2.28 → 2.31 MiB | +1.37% |
| `ld-metadata-local-chisq`: Two-byte six-allele payloads; same rejection pattern with real nonempty chi-square results. | CLI | 3.1865 → 0.1060 s | 30.07× | -96.67% | 2.47 → 2.41 MiB | -2.53% |
| `ld-metadata-inter-geno`: One large chromosome and two small ones reject most same-chromosome pairs while retaining cross-chromosome results. | CLI | 1.0769 → 0.1096 s | 9.83× | -89.82% | 2.28 → 2.30 MiB | +0.68% |
| `ld-metadata-inter-hap`: One large chromosome and two small ones reject most same-chromosome pairs while retaining cross-chromosome results. | CLI | 1.0846 → 0.1309 s | 8.28× | -87.93% | 2.31 → 2.33 MiB | +0.68% |
| `ld-metadata-list-geno`: 150 selected anchors versus 450 others; narrow distance and chromosome gates reject most payload decoding. | CLI | 0.8452 → 0.0661 s | 12.78× | -92.18% | 2.33 → 2.36 MiB | +1.34% |
| `ld-metadata-list-hap`: 150 selected anchors versus 450 others; narrow distance and chromosome gates reject most payload decoding. | CLI | 0.8498 → 0.0717 s | 11.85× | -91.56% | 2.33 → 2.36 MiB | +1.34% |
| `ld-metadata-local-accepted-control`: Every visited inner candidate passes metadata; ordinary packed-reader control. | CLI | 0.0264 → 0.0203 s | 1.31× | -23.40% | 1.91 → 1.97 MiB | +3.28% |
| `ld-metadata-wide-accepted`: Same 131072-sample input with accepted adjacent pairs; distinguishes lifetime savings from rejected-only arrays. | CLI | 0.0478 → 0.0412 s | 1.16× | -13.72% | 21.14 → 18.73 MiB | -11.38% |
| `chisq-matrix-64`: Complete diploid genotype chi-square with nonempty output; symmetric large matrices, swapped rectangular controls or ordinary repeated pairs. | CLI | 0.1060 → 0.0109 s | 9.74× | -89.73% | 89.61 → 45.62 MiB | -49.08% |
| `window-pi-mask-memory`: 32-MiB multiline mask; one output bin isolates packed-mask memory without a full-line 32-MiB string. | CLI | 2.9059 → 2.9654 s | 0.98× | +2.05% | 67.80 → 10.98 MiB | -83.80% |
| `window-pi-dense-overlap`: 20000 sites, each updating 20000 overlapping bins in the previous implementation; no mask. | CLI | 8.7848 → 0.0771 s | 114.01× | -99.12% | 4.55 → 3.78 MiB | -16.84% |
| `window-pi-dense-tiled-control`: 100000 sites and disjoint 1-kb windows; ordinary no-mask control with one original bin update per site. | CLI | 0.0661 → 0.0599 s | 1.10× | -9.37% | 1.89 → 1.91 MiB | +0.83% |
| `fst-64-alleles`: 6000 sites, 128 samples, four populations, 64 alleles per site. | CLI | 0.1493 → 0.1112 s | 1.34× | -25.54% | 2.08 → 2.09 MiB | +0.75% |
| `fst-2-alleles`: 6000 sites, 128 samples, four populations, 2 alleles per site. | CLI | 0.0404 → 0.0387 s | 1.04× | -4.15% | 2.03 → 2.05 MiB | +0.77% |
| `indel-histogram-broad`: 40000 records; length span 20000. | CLI | 0.0399 → 0.0126 s | 3.16× | -68.37% | 2.39 → 2.42 MiB | +1.31% |
| `indel-histogram-narrow`: 40000 records; length span 2. | CLI | 0.0130 → 0.0120 s | 1.08× | -7.65% | 2.25 → 2.30 MiB | +2.08% |
| `random-sample-marking`: 50000 samples, 25000 retained; measures membership marking, with selection-independent output. | CLI | 0.1231 → 0.0051 s | 24.13× | -95.86% | 6.91 → 6.53 MiB | -5.43% |
| `positions-overlap`: 10000 deletion records, REF length 3000, final-base hits in 10000 target positions. | CLI | 0.4603 → 0.0661 s | 6.96× | -85.64% | 2.23 → 2.27 MiB | +1.40% |
| `exclude-positions-overlap`: 10000 deletion records, REF length 3000, final-base hits in 10000 target positions. | CLI | 0.4460 → 0.0465 s | 9.59× | -89.57% | 2.25 → 2.27 MiB | +0.69% |
| `burden-rare-2000`: 2000 samples / 2000 singleton sites; every sample touched, only bin1 needed; full zero output retained. | CLI | 0.6478 → 0.6293 s | 1.03× | -2.85% | 33.62 → 4.52 MiB | -86.57% |
| `burden-rare-carriers-2000`: 2000 samples / 2000 singleton sites; every sample touched, only bin1 needed; full zero output retained. | CLI | 0.6522 → 0.6390 s | 1.02× | -2.03% | 33.66 → 4.52 MiB | -86.58% |
| `burden-all-blocks-1000`: Every sample touches every 256-bin block through rotated carrier windows; all rows allocate the full logical width. Dense allocation control without prefix-only row coverage. | CLI | 0.1293 → 0.1342 s | 0.96× | +3.80% | 9.84 → 9.89 MiB | +0.48% |
| `mendel-heterozygous`: 100 trios / 4000 sites; four unique parental products and occasional errors with nonempty output. | CLI | 0.0827 → 0.0465 s | 1.78× | -43.86% | 1.98 → 1.97 MiB | -0.79% |
| `diff-counts-many-samples`: 32768 samples / 6 shared sites; missing halves and discordant calls. | CLI | 0.1037 → 0.0799 s | 1.30× | -22.99% | 15.09 → 12.92 MiB | -14.39% |
| `diff-counts-many-sites`: 2048 samples / 1200 shared sites; missing halves and discordant calls. | CLI | 0.2736 → 0.1464 s | 1.87× | -46.48% | 3.06 → 2.97 MiB | -3.06% |
| `pca-512x1025`: Complete polymorphic diploid sites; ordinary PCA retains no M after unchanged Gram construction. | CLI | 0.2833 → 0.2357 s | 1.20× | -16.80% | 32.89 → 32.83 MiB | -0.19% |
| `pca-512x2048-no-normalisation`: Complete polymorphic diploid sites; ordinary PCA retains no M after unchanged Gram construction. | CLI | 0.3987 → 0.3316 s | 1.20× | -16.81% | 32.94 → 32.86 MiB | -0.24% |
| `encoding-many-long-fields`: 512 samples, four 4-KiB string FORMAT fields, three records; isolates removal of the N-by-F string matrix. | CLI | 0.1632 → 0.1569 s | 1.04× | -3.84% | 114.05 → 87.58 MiB | -23.21% |
| `encoding-many-short-fields`: 4096 samples, short string FORMAT columns, forty records; allocation/throughput control. | CLI | 0.0477 → 0.0429 s | 1.11× | -10.09% | 5.70 → 4.88 MiB | -14.52% |
| `encoding-single-long-field`: 512 samples, one 16-KiB string FORMAT field, three records; isolates whole-binary-copy removal. | CLI | 0.1626 → 0.1524 s | 1.07× | -6.24% | 121.47 → 94.64 MiB | -22.09% |
| `window-fst`: Four 200-Mb chromosomes, sparse records and 1-kb window steps; exposes bin allocation without large output. | CLI | 0.0410 → 0.0223 s | 1.84× | -45.70% | 49.39 → 32.55 MiB | -34.10% |
| `pca-loadings-memory`: Complete deterministic genotypes; four PCA SNP loadings, with normalisation. | CLI | 0.4270 → 0.4495 s | 0.95× | +5.28% | 69.08 → 55.38 MiB | -19.84% |
| `conversion-plink`: 400000 sites / 4 samples; long transposed output rows. | CLI | 0.8869 → 0.8944 s | 0.99× | +0.85% | 5.45 → 1.92 MiB | -64.76% |
| `conversion-012`: 400000 sites / 4 samples; long transposed output rows. | CLI | 0.8066 → 0.8124 s | 0.99× | +0.73% | 3.69 → 1.92 MiB | -47.88% |
| `conversion-ldhat`: 400000 sites / 4 samples; long transposed output rows. | CLI | 1.5029 → 1.5767 s | 0.95× | +4.91% | 2.86 → 1.97 MiB | -31.15% |
| `conversion-ldhat-geno`: 400000 sites / 4 samples; long transposed output rows. | CLI | 1.4124 → 1.3647 s | 1.03× | -3.38% | 2.83 → 1.95 MiB | -30.94% |
| `conversion-ldhelmet`: 400000 sites / 4 samples; long transposed output rows. | CLI | 1.3221 → 1.3106 s | 1.01× | -0.87% | 2.86 → 1.97 MiB | -31.15% |
| `bed-disjoint`: 40000 disjoint intervals and 20000 unsorted query sites, mixed hits/misses. | CLI | 0.5470 → 0.0288 s | 18.99× | -94.73% | 2.14 → 2.16 MiB | +0.73% |
| `bed-disjoint-exclude`: 40000 disjoint intervals and 20000 unsorted query sites, mixed hits/misses. | CLI | 0.5365 → 0.0319 s | 16.80× | -94.05% | 2.14 → 2.16 MiB | +0.73% |
| `bed-nested-misses`: 300000 nested intervals coalesce to one; 3000 queries outside every interval. | CLI | 0.8794 → 0.0573 s | 15.34× | -93.48% | 4.16 → 4.16 MiB | +0.00% |
| `vcf-long-info-kept`: An 8-MiB INFO record isolates full-row retention when genotype parsing is unnecessary. | CLI | 0.0095 → 0.0083 s | 1.15× | -13.07% | 64.39 → 56.41 MiB | -12.40% |
| `vcf-wide-samples`: 4096 samples, three approximately 8-MiB records with unused FORMAT data and active genotype filters. | CLI | 0.0239 → 0.0162 s | 1.48× | -32.31% | 70.19 → 54.11 MiB | -22.91% |
| `freq-vcf`: Full CLI workload: --freq | CLI | 0.5295 → 0.5142 s | 1.03× | -2.89% | 1.91 → 1.92 MiB | +0.82% |
| `filtered-freq-gz`: Full CLI workload: --freq --minGQ 10 --minDP 5 --remove-filtered-geno-all --maf 0.05 --mac 1 --hwe 0.0001 --max-missing 0.25 | CLI | 2.0771 → 1.6732 s | 1.24× | -19.45% | 5.08 → 5.11 MiB | +0.62% |

### Perl 累计结果（6 个场景，明确区分 CLI 与 API）

只有 `annotate-long-repeat` 测量完整 `vcf-annotate --fill-type` CLI。三个 `indel-*` 测量实际共享 `is_indel` / `event_type` API；`validator-unique-early` 测量真实 validator 分组函数；`phase-overlap` 测量真实 phased-join 函数，**不含 tabix/indexed CLI 集成**。API 加速不能直接解释成完整命令的加速，也不能推广为所有 `vcf-annotate` 模式。

| 场景 / 输入 | 测量范围 | 时间：原版 → 最终版 | 加速倍数 | 时间变化 | 峰值 RSS：原版 → 最终版 | RSS 变化 |
| --- | --- | --- | --- | --- | --- | --- |
| `indel-long-repeat`: 400 classifications of 20 kb repeat alleles, insertion and deletion | API | 2.1547 → 0.9605 s | 2.24× | -55.42% | 9.89 → 9.92 MiB | +0.32% |
| `indel-short-control`: 300,000 short insertion, deletion, and complex-event pairs | API | 0.8233 → 0.8320 s | 0.99× | +1.06% | 9.88 → 9.86 MiB | -0.16% |
| `indel-nonrepeat-control`: 4,000 kilobase complex pairs; early/late mismatches without long repeated suffixes | API | 0.2869 → 0.2811 s | 1.02× | -2.02% | 9.67 → 9.88 MiB | +2.10% |
| `annotate-long-repeat`: Real annotate CLI with 400 long repeat insertions | CLI | 1.0691 → 0.5118 s | 2.09× | -52.13% | 11.64 → 11.50 MiB | -1.21% |
| `validator-unique-early`: 900 diagnostics, 300 distinct groups, third mismatch near start | API | 1.3556 → 0.0727 s | 18.66× | -94.64% | 14.14 → 14.23 MiB | +0.66% |
| `phase-overlap`: Real flush_buffer/output_line/report_stats functions, 2,000 samples x 300 overlap sites | API | 4.1644 → 4.3987 s | 0.95× | +5.63% | 136.05 → 136.38 MiB | +0.24% |

范围与限制：这些是同机合成输入的有限测量，不能推导未知真实 pipeline 的端到端加速率。仍未直接重写的工具可能只受共享读取/解析帮助；已有优化也不代表覆盖该工具的每条函数路径。LROH 的 40N→16N+32 数组有效载荷公式不等于进程 RSS，N=1 时有效载荷反而增加 8 字节；LD 元数据筛选仍消费全部 payload 字节，不是 seek 绕过或减少物理 I/O。浮点计算调度变化、原版未定义行为、设备/资源失败、Perl 既有非确定性及缺失 tabix 的边界继续按下方各批说明处理。原始测量、命令、输入与二进制 SHA 保存在累计 JSON 及配套 verification 文件中。

## 历史增量优化记录（第一至第八批）

以下各批的性能基线、输入和测量时间分别记录，不能用某一批的增量数字代替上面的原始版本→最终版本结果。
<!-- cumulative-performance:end -->

## 已实现并验证的第一批

1. `vcf_file.cpp:314`：删除读行的临时 vector，直接赋值到可复用输出缓冲。
2. `vcf_entry.cpp:215`：仅在批量 genotype 解析入口复用已有 parsed 标志；单样本入口保持原实现，不引入新的持久缓存。
3. `variant_file_output.cpp:4646` 的 `--relatedness2`：删除仅在输出时使用的完整 phi 矩阵，逐单元计算相同 double 表达式。

2,038 组固定时钟差分测试通过，比较 5,725 对输出/捕获/日志文件；包括 321 组匹配的非零退出情况。正常时钟、交替运行顺序、每版五次的九组基准均通过结果文件逐字节比较。组合过滤耗时减少约 12%–20%；1,200 样本 relatedness2 的峰值 RSS 从 40.11 MiB 降至 27.53 MiB。普通任务仍有 0–48 KiB 的 RSS 中位数差异，不能承诺任何环境下绝不增加。详见 [测试方法](../tests/README.md) 和 [完整测量](../tests/results/first-pass.json)。

## 已实现并验证的第二批

记号：N=样本数，M=位点数，A=allele 数，G=群体数，B=BED 区间数，P=positions 数，I=indel 数，D=indel 长度跨度，S=被选样本数。复杂度一般不含共同的输入读取、过滤和必要输出成本。

以下五项已写入源码、独立复核并重新编译。包含第一批改动的第二批版本通过 2,394 组固定时钟差分测试，6,615 对结果/捕获/日志文件逐字节一致，321 组原版非零退出也保持一致；没有基线崩溃，临时目录均清空。正常时钟的 12 组基准每版各运行五次，全部结果文件一致。

本机合成数据中，随机抽样标记约 20.8×、长 REF overlap 约 6.8×、六等位 χ² 约 31.5×、64 等位 Fst 约 1.4×、宽跨度 indel 直方图约 3.2×；这些是用于暴露算法瓶颈的工作负载，不能当作普通 SNP pipeline 的整体收益。二等位 Fst 基本持平，部分任务 RSS 中位数增加 16–32 KiB；relatedness2 仍从 40.11 MiB 降至 27.53 MiB。详见 [第二批版本测量](../tests/results/algorithm-pass.json)，不同批次的二进制 SHA 分开记录。

| 已实现项 | 基线重复工作 | 本批实现 | RAM 与精确一致性边界 | 代码位置 |
| --- | --- | --- | --- | --- |
| 随机抽样后的成员标记 | shuffle 后逐样本扫描 S 个已选索引，O(NS) | 清空原包含标记，再按已选索引恢复，O(N+S) | 无新容器；随机种子、shuffle、截断及输出顺序全部保留 | `variant_file_filters.cpp:105–137` |
| positions-overlap | 对 REF 每个碱基执行 set 查找，O(REF长度×log P) | 在原 set 上 lower_bound，再比较区间终点，通常 O(log P) | 无新索引、不要求 VCF 有序；仅对非负 POS 且被访问位置不超过 INT_MAX 的范围使用新路径，其余保留原循环 | `entry_filters.cpp:522–573` |
| 通用 genotype χ² 的类别编号 | 每个样本、每个位点对重新构造两张 genotype map | 用原三角枚举的闭式编号，去掉建表成本 | 减少分配；使用 int64_t 中间运算，对越界 allele 保留旧 map 默认索引；负值跳过、expected 矩阵和全部浮点循环不变 | `variant_file_output.cpp:1077–1124` |
| Indel 长度直方图 | 每个可能长度都重新扫描 I 个 indel，O(ID) | 长度跨度 ≤32 时保留原逐长度扫描；更宽跨度原地排序后连续计数，O(I log I) | 跨度用 int64_t 计算，短 indel 不承担排序开销；无新大型容器，排序栈仍占 O(log I)；保留升序、长度 0 的 SNP 行、带符号计数转换和百分比表达式 | `variant_file_output.cpp:5244–5366` |
| Fst 的多 allele genotype 计数 | 每样本扫描 A 个 allele，统计部分 O(MGNA) | 直接更新 genotype 中最多两个 allele，O(MG(N+A)) | 复用原计数数组；保留旧的 -1 缺失判断，以及另一 allele 越界时仍计入有效 allele 的行为；Fst 公式及求和顺序不动 | `entry_getters.cpp:452–482` |

χ² 编号中，设 `a=min(gt1,gt2)`、`b=max(gt1,gt2)`，原枚举对应 `a*A-a*(a+1)/2+b`。实现扩大中间整数类型，并保留原来非标准 genotype 的索引行为。它减少的是查表工作，不是换一种统计检验；expected 矩阵尚未删除。原有 `N*(N+1)` 维度计算仍使用 int；本批扩大索引中间类型并未修复整个例程的大整数溢出边界。

## 已实现并验证的第三批

本批处理前一版报告中优先级最高的两个方向：relatedness 对称矩阵，以及 LROH 报告阶段的重复后缀扫描和小数组分配。最终代码已重新编译并通过 2,760 个固定时钟差分用例，7,500 对结果/捕获/日志文件逐字节一致，381 组原版非零退出也保持一致；没有基线崩溃或残留临时文件。差分基线仍是原始 commit，性能基线则为第二批已交付源码，以单独衡量本次收益。九组基准均每版运行五次，全部结果文件逐字节一致。

| 已实现项 | 本批实现 | 精确一致性与内存边界 | 代码位置 |
| --- | --- | --- | --- |
| Manichaikul relatedness2 | 两个计数矩阵仅保存含对角线的上三角；每个位点每对样本只计数一次，输出时读取对应的对称单元 | 每个单元仍按原位点顺序加 1，N_Aa 仍逐样本更新；保留原 genotype 过滤行为、分母中两个样本的顺序、完整 N×N 输出顺序和刷新时机；主体仍为 O(MN²) | `variant_file_output.cpp`：`output_indv_relatedness_Manichaikul` |
| Yang relatedness | 将原本只计算和输出的上三角紧凑存储，第 i 行保存 N-i 个 double | 只改变索引，不改变浮点表达式、每个单元的位点累计顺序、对角线变换或上三角输出；不新增索引表或 genotype 缓存 | `variant_file_output.cpp`：`output_indv_relatedness_Yang` |
| LROH 下个杂合位点查找 | 使用单调递增的 observation 游标，报告阶段查找从最坏 O(NM²) 降为 O(NM) | 每个正在处理的样本只增加 O(1) 标量状态；不改变 HMM 数值公式、归一化、阈值或区间生成。每次区间结束仍加上完整的前瞻距离，包括之前查找已扫过的位点，保留原计数方式 | `variant_file_output.cpp`：`output_LROH` |

本机合成数据的中位数（上一版 → 本版）：

| 场景 | 时间 | 峰值 RSS |
| --- | --- | --- |
| relatedness2，1,200 样本 / 32 位点 | 2.8110 → 2.7411 s | 27.30 → 14.92 MiB |
| Yang，1,200 样本 / 32 位点 | 1.0677 → 1.0642 s | 27.30 → 14.94 MiB |
| relatedness2，400 样本 / 2,000 位点 | 0.9315 → 0.6667 s | 5.16 → 3.55 MiB |
| Yang，400 样本 / 2,000 位点 | 0.2715 → 0.2787 s | 5.17 → 3.55 MiB |
| LROH 重复查找，8 样本 / 24,000 位点 | 0.0379 → 0.0209 s | 20.69 → 15.98 MiB |
| LROH 常规区间，8 样本 / 50,000 位点 | 0.0772 → 0.0417 s | 41.23 → 29.58 MiB |

Yang 的计算组耗时约增加 2.6%，内存约减少 31%；这项改动主要收益是内存。未改动的 frequency/missingness/χ² 对照组有 16–64 KiB 的 RSS 中位数增量，不能承诺所有调用中 RAM 绝不增加。LROH 独立报告模型另覆盖 349,525 个短模式、224 个确定性随机模式、512 个整数坐标边界模式及 6 个长模式；模型只验证报告循环，实际 HMM 输出由 CLI 差分覆盖。详见 [本批完整结果及 SHA](../tests/results/priority-pass.json)。

矩阵的理论有效载荷如下，假设 `sizeof(double)==8`，N 为 header 中的总样本数；vector 对象、分配器开销、其他数组及进程 RSS 不包含在内。这些是存储布局推导，不是峰值 RAM 实测值。

| Estimator | 原始基线 | 第二批版本 | 第三批版本 |
| --- | --- | --- | --- |
| Manichaikul | 24N² 字节：phi 加两个计数矩阵 | 16N² 字节：两个计数矩阵 | 8N(N+1) 字节：两个含对角线的上三角 |
| Yang | 16N² 字节 | 16N² 字节 | 8N(N+1) 字节 |

LROH 游标按 observation 顺序前进，因此不依赖坐标已排序或唯一。不存在后续杂合位点时仍使用最后一个 observation 的坐标，并计入余下完整距离；最终区域的输出分支保持原样。原有有符号计数溢出的边界并未修复。同时，p_trans 的每个四元素 vector、alpha/beta 的每个二元素 vector 已改成固定长度 double 行，去掉每个 observation 的独立 heap 分配；保持零初始化、double 类型、索引及全部 HMM 算式。没有提高项目的 C++ 标准要求。滚动 beta 在第三批结束时仍是后续候选，现已在第八批实现并单独验证。

## 已实现并验证的第四批

本批扩大到格式转换、窗口统计和 PCA SNP loadings 路径，没有继续修改 relatedness 或 LROH。下列改动已按常规与 LAPACK 启用配置分别验证；性能对照使用第三批交付源码，差分对照仍使用原始 commit。

| 已实现项 | 本批实现 | 精确一致性与内存边界 | 代码位置 |
| --- | --- | --- | --- |
| PED、012、LDhat phased/unphased、LDhelmet 临时行拼接 | 五条转换路径共用 8 KiB 缓冲分段复制第一行，替代完整长行 string | 每次按实际字节数写出，保留内嵌 NUL、首个换行边界及原位置的 endl；临时行拼接工作区从 O(行长) 降到 O(1)，同时打开的临时文件数量未改 | `variant_file_format_convert.cpp`：`copy_temporary_row` 及五个转换函数 |
| 012 与 LDhelmet 的 allele 复制 | 012 删除未使用的 allele 列表副本；LDhelmet 在首个保留样本处懒加载一次，再供该位点其他样本复用 | 不在零保留样本时额外解析；不改变基因型判断、allele 字符串或输出顺序。LDhelmet 的相同列表复制由 O(MNA) 降为 O(MA) | `output_as_012_matrix`、`output_as_LDhelmet` |
| Windowed Fst 与 windowed π 的 bin 存储 | 每个四元素 bin 改为固定长度行，去掉 bin 自身的 vector 对象和独立 heap 分配 | Fst 保留 double，π 保留 unsigned long；零初始化、resize 次序、重现染色体时的旧缩短行为、索引及所有整数/浮点累计顺序不变。没有采用前缀和或差分累计 | `variant_file_output.cpp`：两个 `output_windowed_*` 函数 |
| Windowed π 的 mask 解码 | 直接扩展目标 mask 并转换写入，删除每行的 vector&lt;short&gt; 副本 | 保留原 char → short → char 转换、换行处理和 mask 阈值规则；移除 sizeof(short)×当前行长度的临时数据（本平台为每字符 2 字节），不改变已有 mask 缓存或过滤器状态 | `output_windowed_nucleotide_diversity` |
| PCA SNP loadings 的 genotype IDs | 已来自 int genotype 和的 ids 矩阵改用 int 保存，参与载荷计算时转回 double | M、Gram 矩阵、特征值求解器和全部数值公式不动。在 double 为 8 字节、int 为 4 字节时，ids 数据有效载荷减半；M+ids 两矩阵合计从约 16MN 降到 12MN 字节，减少 25%，不等于整进程 RSS 下降比例 | `output_PCA_SNP_loadings` |

第四批使用两个独立构建配置做逐字节对照：

| 配置 | 通过用例 | 结果/捕获/日志文件对 | 匹配的非零退出 |
| --- | ---: | ---: | ---: |
| 常规构建，PCA 未启用 | 3,470 | 9,644 | 587 |
| PCA 启用构建 | 210 | 519 | 90 |
| 两配置合计 | 3,680 | 10,163 | 677 |

以上合计不是同一个二进制的一套用例；两个配置各自与对应的原始基线构建比较。另有 180 项临时行复制 helper 检查全部通过。转换测试覆盖首行长度边界、长 allele、空行/空输入、样本筛选、CRLF、无末尾换行和晚期解析错误；窗口统计覆盖重叠及回退步长、稀疏坐标、无序/重复位点、染色体重现与多种 mask 字节。晚期转换错误仍可能像原版一样留下临时文件，没有把这类错误路径改成清理后退出。

本轮 13 组正常时钟基准每版运行五次，全部结果文件逐字节一致。实测中位数（上一版 → 本版）：

| 场景 | 时间 | 峰值 RSS |
| --- | --- | --- |
| PLINK PED，40 万位点 / 4 样本 | 0.8530 → 0.8788 s | 5.47 → 1.92 MiB |
| 012，同输入 | 0.8060 → 0.8312 s | 3.69 → 1.92 MiB |
| LDhat phased | 1.4950 → 1.4327 s | 2.86 → 1.95 MiB |
| LDhat unphased | 1.3856 → 1.4088 s | 2.83 → 1.94 MiB |
| LDhelmet | 1.3153 → 1.3460 s | 2.86 → 1.95 MiB |
| Windowed π，4 条稀疏 200-Mb 染色体 | 0.0482 → 0.0300 s | 44.73 → 26.33 MiB |
| Windowed Fst，同输入 | 0.0407 → 0.0216 s | 49.34 → 32.48 MiB |
| Windowed π，约 8-MiB 单行 mask | 0.7302 → 0.7436 s | 58.05 → 42.03 MiB |
| PCA SNP loadings，10 万位点 / 32 样本 | 0.4257 → 0.4104 s | 69.08 → 55.39 MiB |

导出任务的主要收益是 RAM；时间变化从约减少 4.2% 到增加 3.1%，不能全部称为加速。长 allele 的 012 对照峰值 RAM 未下降（增加 32 KiB），染色体重现的 π 对照内存基本相同。PCA 使用两版相同的 Accelerate 库并固定 VECLIB_MAXIMUM_THREADS=1；不据此声称跨数学库版本结果一致。12 个晚期错误用例每版保留共 152 个私有临时文件，额外按原始内容核对一致，仅忽略随机临时文件名；主结果、日志和退出码未作归一化。[本批完整测量与二进制 SHA](../tests/results/memory-pass.json)。

PCA 原版对未过滤的负 genotype 和可能只向部分 M 行写入数据，造成不等长行，随后按统一 N_sites 读取时存在越界风险。本批不修复该行为；PCA 对照使用显式缺失过滤覆盖有定义的路径，并保留原版的报错路径。不能将 ids 类型缩减理解成已经修复 PCA 的缺失值处理。

## 已实现并验证的第五批：重复扫描与反证检查

这次重新做了三类扫描：沿 LD/过滤/Perl 调用链查重复工作；追踪每行、每区间和每 genotype 容器的生存期；由另一位审查者独立推导边界等价性，再用反例和真实输出检查。新增发现包括 VCF 的整行保留副本、共享 Vcf.pm 的冗余后缀扫描，而不只实施之前表格中的局部候选。

| 已实现项 | 改动及复杂度 | 保持的行为与 RAM 边界 |
| --- | --- | --- |
| BED 区间查询 | 原三分支谓词等价编码为闭区间，在原 deque 内排序并合并重叠区间；每位点由 O(B) 扫描变为 O(log B)，不新增第二份索引 | 正向 [a,b) 式输入编码为整数闭区间 [a+1,b]；a≥b 时编码为 [b,a]，保留旧零长和反向区间行为。保留首行跳过、EOF 日志计数、最长 REF/ALT 跨度和无序 VCF；删除每位点新建的 min_ui。峰值仍可能出现在合并之前 |
| 7 条 LD 路径的临时读取 | 用固定 4 KiB 缓冲批读 genotype 字节，最后一字节仍按原方式读取 | 在完整 header、普通文件流及默认 exception mask 下，已测 EOF 截断的解码、陈旧字节行为和最终 gcount/stream 状态保持；任意 I/O 异常及原版零 payload 未初始化行为不在此结论内。不缓存全部位点，不改窗口或配对顺序 |
| LD 解码缓冲表示 | 两个 pair<int,int> 数组改为 pair<short,short>，计算时仍经过原 int 局部变量 | 本机两数组有效载荷从 16N 降到 8N 字节；short 能精确容纳原 signed/unsigned char 解码域。数值内核和浮点累加不动；另有 4 KiB 固定读取栈，小 N 不保证峰值下降 |
| VCF 行所有权 | 去掉 entry::line 的完整 VCF 行副本，用每对象空行标志供过滤器读取；原字符串与 stream 仍拥有内容 | 减少一个最大行长的保留 vector；BCF 的原始字节 vector 不动。构造/空 reset、交错 diff 对象、NUL、CRLF、截断行和长行转短行均检查 |
| Vcf.pm::is_indel | 计算保持原结果所需的后缀扫描上限；前后缀重叠已经证明 indel 后不再遍历剩余重复序列 | 返回 tuple、旧 off-by-one 访问、event_type 缓存语义不改，无新数据大小容器；不是另一种 normalization 或左对齐算法 |
| vcf-validator | 某既有类别出现第三个不同 token 后停止该候选比较 | 保留原候选顺序及首个匹配，不建立额外分类索引 |
| vcf-phased-join | 每个位点两项 log 在首次对应分支使用时懒计算复用 | 保留原加法顺序和不会执行 log 的分支，log(0) 错误行号不变；实测整体时间接近不变，不能把减少 log 次数说成整体大幅加速 |

常规构建 **3,852** 个用例、**10,599** 对文件通过；另一个 LAPACK 配置 **210** 个用例、**519** 对文件通过。合计 **4,062** 个用例、**11,118** 对结果/捕获/日志文件逐字节一致，**715** 个匹配的非零退出、没有基线崩溃。固定时钟仅控制日志/RNG，不删除或排序任何输出。所有 3,852 个常规用例的私有临时文件也额外比较：28 个用例保留共 172 个文件/版本，原始内容一致，仅随机私有文件名不参与配对。

独立检查包括 **849,674** 次 BED 原谓词与索引查询比较、**6,392** 项实际 LD reader 检查（C++98、signed/unsigned char 两种构建），以及 **20** 项真实 VCF/BCF 对象 reset/所有权检查。五个修改的 C++ 翻译单元通过 C++98 语法检查，包含 PCA 启用代码；没有提高项目语言标准。

Perl 最终确定性矩阵固定相同路径、时钟及 HASH_SEED=0/1/17、PERTURB_KEYS=0：**180** 个完整原始输出相等，**15** 个基线自身不稳定，**0** 个确定性差异。不稳定项包含 Carp 的内存地址，不计入字节一致性通过数。非零 hash perturb 的审计单独保存，并用多次原版重放识别旧 header/警告顺序随机性，既不排序输出也不改生产随机行为。phased-join 覆盖实际 flush_buffer/output_line/report_stats API；未安装 tabix，不能宣称已经完成其索引文件 CLI 集成测试。annotate、stats、validator 和 to-tab 另有实际 CLI 覆盖。

13 组 C++ 基准与 6 组保留改动相关的 Perl 基准各版交替五次，所有结果字节和退出码相同。C++ 用正常时钟，含耗时的诊断单列；Perl 固定日期/hash 环境，用外部单调时钟和 wait4 测量。实测中位数：

| 场景 | 时间（第四批 → 第五批） | 峰值 RSS |
| --- | --- | --- |
| BED：4 万区间 / 2 万无序位点 | 0.5155 → 0.0289 s | 2.14 → 2.16 MiB |
| BED：30 万嵌套区间 / 3,000 个未命中位点 | 0.8469 → 0.0566 s | 4.12 → 4.16 MiB |
| Genotype LD：128 样本 / 2,400 位点 | 0.1299 → 0.0749 s | 1.84 → 1.94 MiB |
| Haplotype LD：1,024 样本 / 500 位点 | 0.1955 → 0.1127 s | 2.00 → 2.09 MiB |
| 跨染色体 LD：128 样本 / 720 位点 | 0.2448 → 0.1207 s | 1.84 → 1.91 MiB |
| SNP-list LD：1,024 样本 / 720 位点 | 0.2603 → 0.1136 s | 2.05 → 2.11 MiB |
| Genotype LD：65,536 样本 / 12 位点 | 0.0465 → 0.0352 s | 11.84 → 10.89 MiB |
| 8-MiB INFO 行 / kept-sites | 0.0090 → 0.0080 s | 64.36 → 56.38 MiB |
| 4,096 样本 / 约 8-MiB FORMAT 行 | 0.0166 → 0.0152 s | 62.12 → 54.09 MiB |
| Perl annotate：400 个 20-kb 重复 allele | 1.0334 → 0.4809 s | 11.70 → 11.69 MiB |
| Perl validator 分组 API：900 条长诊断 | 1.1966 → 0.0714 s | 14.19 → 14.20 MiB |

小型 C++ 工作负载仍出现 16–96 KiB RSS 增量，Perl 独立分类 API 的增量为 160 KiB；不能承诺所有调用 RAM 绝不增加。长行 VCF 约减少 8 MiB，65,536 样本 LD 约减少 0.95 MiB。普通过滤对照耗时 1.6541 → 1.6609 s，变化约 0.4%；短/非重复 indel 控制组时间基本持平。上述是单机合成数据，不能视作通用 pipeline 加速比例。

**已撤回的试验**：vcf-to-tab 固定样本顺序缓存，密集输入约快 4%，但稀疏输入变慢约 2%–3%，重复 header 对照 RSS 增加约 240 KiB。最终文件恢复为第四批原文；测试和原始实验结果保留，以免下一轮重新尝试同一路线。

**第五批结束时暂缓的方向（χ² 已在第七批、保留读取行为的 LD 解码筛选已在第八批处理）**：LD 先读元数据再跳过不合格 payload（需明确临时 I/O 失败契约）；χ² 删除 expected 矩阵（需保持每次 double 舍入）；AF/AC 只在相邻过滤步骤共享计数（公共可变 mask 使全局缓存不安全）；merge 的 ALT 集合交集、annotate 活动区间及 SnpCluster 单调窗口（需完整 tabix 集成和原覆盖顺序验证）。VcfStats 已有按记录缓存，不再叠加跨记录缓存。Vcf4_0::event_type 还有旧 allele 缓存键行为，例如 REF=AA、ALT=AAA 后 ALT=A 可能读回插入分类；修复会改变原输出，不能混入此补丁。positions/BED 共享 map 的某些组合本身存在数组初始化越界风险，同样保留并单列。

[第五批全部测量、源码和二进制 SHA](../tests/results/interval-ld-perl-pass.json) · [复现方法](../tests/README.md)。

## 已实现并验证的第六批：新函数路径与密集反例

本批沿剩余候选重新扫描了统计输出、两文件 diff、VCF→BCF 编码与数值辅助函数。先查多余树索引和完整矩阵，再查缓冲生存期，最后独立复核原版的特殊行为。没有继续修改 relatedness、LD 或 BED。Perl 源码与第五批完全相同，其既有验证记录单独保留，未加入本次通过数。

| 已实现项 | 改动与收益来源 | 一致性和 RAM 边界 |
| --- | --- | --- |
| `output_indv_freq_burden` 两种命令 | 原 N×(2N+1) 整数矩阵改为每块 256 项、按需分配；每块只分配一次，末块精确到剩余项数 | 不省略零值或输出列；保留两个 allele 的更新顺序、derived AA、mask 和原样本标签行为。稀疏数据少存未使用计数；最坏密集数据仍为 O(N²)，另有指针目录和分配器开销 |
| `output_mendel_inconsistencies` | 每 trio/site 的四项 set 改为直接检查两个孩子 allele 能否分别来自父母 | 无新容器；保留恰好 -1 的缺失跳过规则、其他负 ID 的旧成员判断及 PED/输出顺序 |
| `output_discordance_by_indv` | 用与原名字 map 顺序一一对应的计数 vector 替代第二棵 map | 热循环计数查找由 O(log N) 降为 O(1)，去掉第二份字符串/tree nodes；原名字排序、重复映射覆盖、allele 分支和除法不变 |
| `get_allele_counts` | 在调用者已有 vector 中清零并计数，删除临时数组及末尾复制 | 整数类型、mask 和更新次序不变；不引入跨记录或跨过滤步骤缓存 |
| `vcf_entry::parse_FORMAT` | 普通长度输入从 N×F 字符串矩阵改为一列 N 个字符串及 N 个游标；按原字段顺序编码 | 特别保留短 sample 继承前一 sample 尾字段的旧行为、空字段和尾冒号；超长字符串回到旧 splitter 路径。删除矩阵副本，不改变数字编码器 |
| `vcf_entry::print_bcf` | 直接只读已编码的 FORMAT 字节缓冲，删除整份副本 | 保留解析断言、字段/样本排列、BGZF 块和压缩参数；比较的是压缩后的原始字节 |
| 普通 `output_PCA` | 原 Gram 矩阵计算及除法全部结束后释放 M，再分配求解所需矩阵 | 未改为流式累计，不改变任何浮点表达式或累加次序；SNP loadings 后续仍需 M，保留该矩阵 |
| 两个 DGEEV wrapper 和排序 overload | JOBVL=N 使用 dummy VL；不取右向量时也用 dummy VR。排序改为索引排序后每行重排一次，含向量时最坏 O(N³) 降为 O(N²+N log N) | 求解器、维度和 WORK 不变。NaN 为不能跨越的分界，同值以旧索引排序，保留 quiet-NaN payload、signed zero 和同值顺序；多用 N 个 int 和排序栈。未触页的旧大数组不一定表现为 RSS 下降 |

最终源码的常规构建 **4,526** 个用例、LAPACK 构建 **210** 个用例全部通过：共 **4,736** 个用例、**12,774** 对原始结果/捕获/日志文件一致，**857** 个匹配的非零退出，没有基线崩溃。两种构建各自与原始 commit 的对应构建比较；固定时钟控制日志与 RNG，不排序或删除输出。新增 corpus 覆盖 diff 的样本 union/映射覆盖/缺失、burden 的 255/256/257/511/512/514 边界及未分配中间块、Mendel 的多类 PED，以及 VCF/VCF.gz/BCF、stdin 和错误前的部分输出。

额外检查实际 FORMAT 编码函数 **61,398** 个场景，包含原始 FORMAT 字节和压缩 BGZF record；测试副本把超长回退阈值降到 3，又通过同样 **61,398** 个场景。后者只验证回退函数体，未实际分配超过 2 GiB 的字符串。实际 DGEEV 源码共 **180,378** 项 double 原始内存比较通过，其中 **179,802** 项排序、**576** 项同库 wrapper；另有独立 burden 模型 **680,287** 次计数更新和 **12,285** 项分配上界检查，以及 **46,656** 项 Mendel 成员比较。模型不冒充 CLI 测试或进程 RAM 实测。五个修改的 C++ 翻译单元通过启用 PCA 的 C++98 语法检查。

全部 4,736 个 CLI 用例还核对了私有临时文件：28 个用例每版留下 172 个文件，原始内容一致，仅随机私有文件名不参与配对。公共输出和诊断没有这种豁免。

性能基线为冻结的第五批交付版。18 组完整 CLI 工作负载按交替顺序每版五次、串行运行；所有结果文件、stdout 和退出码一致，正常时钟的耗时诊断单列。PCA 两版均使用相同 Accelerate，VECLIB_MAXIMUM_THREADS=1。以下均为单机合成数据中位数，不能外推为任意 pipeline 的加速比例：

| 场景 | 时间（第五批 → 第六批） | 峰值 RSS |
| --- | --- | --- |
| Frequency burden，2,000 样本 / 2,000 个 singleton 位点 | 0.6386 → 0.6470 s | 33.64 → 4.48 MiB |
| Frequency burden2，同输入 | 0.6316 → 0.6277 s | 33.66 → 4.50 MiB |
| Frequency burden，2,000 样本 / 空输入 | 0.5040 → 0.5158 s | 33.48 → 2.14 MiB |
| 频率 1..2,000 递增的密集对照 | 0.1939 → 0.1918 s | 9.91 → 6.56 MiB |
| 每个样本触及每一块，1,000 样本 | 0.1312 → 0.1372 s | 9.88 → 9.89 MiB |
| 每块均触及、最后一块仅一个计数，512 样本 | 0.0396 → 0.0387 s | 4.52 → 4.06 MiB |
| Discordance，2,048 样本 / 1,200 位点 | 0.3239 → 0.1379 s | 3.03 → 2.95 MiB |
| Discordance，32,768 样本 / 6 位点 | 0.0983 → 0.0742 s | 14.66 → 12.92 MiB |
| VCF→BCF，512 样本 / 四个长字符串字段 | 0.1657 → 0.1578 s | 106.02 → 87.56 MiB |
| VCF→BCF，512 样本 / 一个长字符串字段 | 0.1612 → 0.1569 s | 113.39 → 94.58 MiB |
| VCF→BCF，4,096 样本 / 短字段 | 0.0489 → 0.0432 s | 5.52 → 4.84 MiB |
| Mendel，100 个 trio / 4,000 位点，杂合父母 | 0.0918 → 0.0567 s | 1.97 → 1.95 MiB |
| Mendel，同规模纯合父母对照 | 0.0901 → 0.0468 s | 1.95 → 1.95 MiB |
| PCA，512 样本 / 1,025 位点 | 0.2892 → 0.2375 s | 34.86 → 32.83 MiB |
| PCA，512 样本 / 2,048 位点，no-norm | 0.4004 → 0.3362 s | 34.91 → 32.86 MiB |
| 小 PCA 对照 | 0.0052 → 0.0039 s | 6.50 → 6.44 MiB |
| PCA SNP loadings 对照 | 0.4170 → 0.4039 s | 55.39 → 55.38 MiB |
| VCF.gz 普通过滤对照 | 1.6724 → 1.7089 s | 5.12 → 5.11 MiB |

排序 helper 另有四组每版五次的实测，完整二进制 Er/Ei/Evecs、stderr 和退出码一致。时间包含进程启动、矩阵初始化及原始 double 写出，不能直接等同于整个 PCA 的加速：

| 实际排序函数场景 | 时间 | 峰值 RSS |
| --- | --- | --- |
| sort-ascending-512 | 0.5276 → 0.0081 s | 7.58 → 7.56 MiB |
| sort-ascending-768 | 0.6664 → 0.0072 s | 10.16 → 10.17 MiB |
| sort-already-ordered-512 | 0.0046 → 0.0045 s | 7.55 → 7.56 MiB |
| sort-ties-512 | 0.2002 → 0.0047 s | 7.55 → 7.56 MiB |

**已撤回的计数存储试验**：首次按需扩张连续行的版本使稀有输入 RAM 从约 33.7 MiB 降至 2.3 MiB，但密集输入从 9.91 MiB 升到 13.73 MiB；旧内存块被释放后仍可能留在分配器中。最终换为不复制、不替换既有计数块的固定分块布局，并额外加入“每个样本触及每一块”的两组密集对照。撤回版源码差异和测量单独归档，不混入最终收益。固定分块仍有指针和分配器元数据，不能保证所有输入的 RAM 都下降；表格完整保留实测增加和速度回退。

**第六批结束时的剩余方向（χ²/windowed π 已在第七批，LROH/LD 解码筛选已在第八批处理）**：χ² expected 矩阵消除、windowed π 的整数窗口累计和 mask 滚动计数、LROH 滚动 beta、LD 元数据跳过与 Perl 活动区间/多文件 merge，仍值得继续验证。它们分别涉及浮点舍入、旧整数/窗口边界、HMM 缩放次序、I/O 失败行为或尚未具备的 tabix 集成。普通 PCA 流式 Gram 路线仍受原版缺失数据产生短 M 行的越界问题影响，未在此批顺手修正。资源耗尽、已有未定义行为、跨数学库和 signaling-NaN trap 不属于本次有限测试的保证范围。

[第六批测量、源码和二进制 SHA](../tests/results/burden-encoding-eigen-pass.json) · [复现命令及测试限制](../tests/README.md)。

## 已实现并验证的第七批：χ² expected 与 windowed π

本批只修改两个统计路径所在的 `variant_file_output.cpp`，针对上一轮尚未覆盖的 expected 矩阵与 windowed π 重复计算；没有继续改 relatedness、PCA、BCF 编码或 Perl。另一个审查者独立复核了窗口差分、染色体重访和字符边界，实际函数探针与完整 CLI 对照分别验证。

| 已实现项 | 改动与复杂度 | 精确输出及 RAM 边界 |
| --- | --- | --- |
| `calc_geno_chisq` expected 存储 | 保留一行 G1 个 double，计算该行后按原列顺序使用；不再保存 G0×G1 个 expected | G0=A0(A0+1)/2、G1=A1(A1+1)/2；按本机 double 为 8 字节，expected 有效载荷由 8G0G1 降至 8G1 字节。observed 矩阵仍保留。expected 先写 double 存储再读取，所有零行/零列的 expected 计算也保留；边际和、总和、`pow`、χ² 累加顺序、dof 和 gamma 不变 |
| windowed π 范围累计 | 四个 unsigned-long bin 改存差分，每个位点只更新 first 和 last 两端；输出用局部前缀和恢复 | 单个位点从 K 个重叠窗口更新降为 O(1)，每次染色体输出有 O(B) 前缀扫描；四列 bin 内存仍为 O(B)，没有增加第二份数组。保留整数模运算和原坐标表达式；最终 double 除法完全相同 |
| windowed π mask 存储 | 按原 char→short→char 转换及 threshold/invert 保存 keep bit | 本机 mask 有效载荷约为原 char 数组的 1/8；读取文件、过滤器、字符串容量和染色体扫描仍存在，不能声称整个进程 RAM 缩为 1/8 |
| windowed π mask 查询 | 在相邻的单调重叠输出区间中减掉移出的部分、加上新进入的部分 | 典型有序重叠查询不再逐窗口扫描完整 mask 范围；只增加常数状态，不建 prefix 数组。空区间、端点回退、unsigned 回绕和不相交区间均重置独立计数 |

原染色体重访会把 bins 缩为一项而保留 bin0。差分实现重新扩展时在 bin1 加入 `-bin0` 抵消项，避免把旧 bin0 传播到新窗口；输出仅使用局部前缀和，不改写差分数组，因此重复染色体名称仍输出相同的最终数组。输出阶段另用只读引用避免反复查找染色体 map。没有合并两个看似相同的站点计数，因为原 signed cast 在极端范围可能破坏这种等价性。

最终源码的常规构建 **4,850** 个用例、LAPACK 构建 **210** 个用例全部通过：合计 **5,060** 个用例、**13,578** 对原始结果/捕获/日志文件一致，**889** 个匹配的非零退出，没有基线崩溃。两种配置分别对照原始 commit，固定时钟仅控制日志和 RNG。新增 χ² corpus 为 8 个 fixture / 21 条命令，windowed π 为 9 个 fixture / 38 条命令，经 VCF、VCF.gz、适用的 BCF、文件和 stdin 路径展开；覆盖矩形 contingency table、零边际、缺失与旧越界 allele 映射、过滤、错误前部分输出、无序及重复坐标、染色体重访、负/大坐标、二进制 mask、阈值和反转。

实际 χ² 函数在 C++98 `-O0`、`-O2` 下各通过 **37,551** 个场景，逐字节比较 χ²、dof、pval 的 double，还核对样本计数、最终浮点异常标志及 errno。使用相同 gamma 与普通 FE_TONEAREST 非陷阱环境；未用容差。windowed π 实际 helper 在 default、signed-char、unsigned-char 三种 C++98 构建中各通过 **132,620** 次区间更新、**16,397,384** 次 bin 值比较、**8,192** 次字符判定和 **3,379,458** 次滚动区间比较。各构建单独计数，不把 helper 检查冒充完整 CLI 用例。整份修改的 C++ 翻译单元也通过启用 PCA 的 C++98 语法检查。

全部 5,060 个 CLI 用例额外核对私有临时文件：36 个用例每版保留 180 个文件，内容一致，只忽略随机私有文件名。公共输出、诊断和退出码没有归一化。

性能基线是冻结的第六批交付版。15 组完整命令按交替顺序每版五次、串行运行，所有结果文件和 stdout 字节及退出码一致；正常时钟的耗时诊断单列。单机合成数据的中位数如下，大矩阵与高重叠窗口用于暴露目标算法瓶颈，不能当作普通 pipeline 的整体加速比例：

| 场景 | 时间（第六批 → 第七批） | 峰值 RSS |
| --- | --- | --- |
| χ²：64×64 allele，256 样本 / 2 位点 | 0.0161 → 0.0110 s | 89.17 → 45.61 MiB |
| χ²：96×96 allele，256 样本 / 2 位点 | 0.0726 → 0.0432 s | 440.50 → 221.36 MiB |
| χ²：2×96 allele，矩形宽表 | 0.0022 → 0.0020 s | 2.34 → 2.33 MiB |
| χ²：96×2 allele，矩形高表 | 0.0024 → 0.0022 s | 2.61 → 2.38 MiB |
| χ²：二等位常规对照 | 0.1120 → 0.1027 s | 1.94 → 2.00 MiB |
| χ²：六等位常规对照 | 0.0295 → 0.0270 s | 1.98 → 2.03 MiB |
| windowed π：32-MiB 多行 mask，单窗口 | 2.9354 → 2.9938 s | 66.78 → 10.98 MiB |
| windowed π：4-MiB mask，200-kb 重叠窗口 | 0.5798 → 0.3865 s | 10.58 → 3.62 MiB |
| windowed π：同 mask，1-kb 不重叠窗口 | 0.3787 → 0.3819 s | 10.58 → 3.66 MiB |
| windowed π：20,000 位点 / 20,000-bin 重叠，无 mask | 8.9387 → 0.0849 s | 3.73 → 3.78 MiB |
| windowed π：100,000 位点，不重叠，无 mask | 0.0615 → 0.0586 s | 1.86 → 1.91 MiB |
| windowed π：四条稀疏 200-Mb 染色体 | 0.0297 → 0.0054 s | 26.34 → 26.36 MiB |
| windowed π：染色体重访对照 | 0.0030 → 0.0031 s | 14.09 → 14.11 MiB |
| 未改动 windowed Fst 对照 | 0.0215 → 0.0224 s | 32.50 → 32.53 MiB |
| 未改动 VCF.gz 过滤对照 | 1.6798 → 1.6683 s | 5.09 → 5.14 MiB |

本轮实测的最大 RSS 中位数增加为 **64 KiB**，所有增加和耗时回退均保留在表中。χ² 的 observed 矩阵及无 mask 的 π bins 没有缩减；主要 RAM 收益来自 expected 行复用和 mask 位存储。非重叠、稀疏、矩形以及未改动的控制组单列，避免只展示有利数据。

兼容性限制：expected 计算与 χ² 计算现在按行交错，因此不承诺浮点陷阱或资源耗尽时的指令级失败时机。实际结果适用于已测平台和普通有定义路径，不能推广为任意编译器、超额精度架构或数学库的普遍保证。原有 signed 坐标/计数溢出、非法索引及 mask 解析的既有未定义边界不在本次修复范围；未改变统计定义、阈值、窗口或输出顺序。

这两个方向在第七批已从候选转为已实现。当时保留的 LROH 滚动 beta 和 LD 元数据筛选已在下述第八批实现；真正 seek 跳过 payload 读取、Perl 活动区间与多文件 merge 仍需独立验证读取失败语义及 tabix 集成边界。

[第七批测量、源码和二进制 SHA](../tests/results/chisq-window-pi-pass.json) · [复现命令](../tests/README.md)。

## 已实现并验证的第八批：LROH 滚动 beta 与 LD 元数据筛选

本批继续处理第七批结束时保留的两个高优先级方向，生产改动限于 `variant_file.cpp`、`variant_file.h` 和 `variant_file_output.cpp`。LROH 减少 HMM 工作数组和已完成样本的存活内存；七条局部、跨染色体及指定位点 LD 路径在元数据筛选失败时省去 genotype 解码。没有修改统计公式、阈值、报告格式或 pair 输出顺序，也没有继续改 relatedness 或 Perl。

| 已实现项 | 改动与复杂度 | 精确输出及 RAM 边界 |
| --- | --- | --- |
| LROH 滚动 beta | 后向递推只保留当前和下一行，共两个固定宽度 double 行 | 按原公式、索引、每次 double 存储和逐行缩放次序计算；不重算 transition，不改为 log-space 或近似算法 |
| LROH posterior 复用 alpha | 完成全部 forward 计算后，在 backward 阶段将该行 posterior 写入已失效的 `alpha[i][0]`；右侧原表达式先完整求值 | 原 alpha/beta/posterior 工作数组有效载荷为 40N 字节，现在为 16N+32 字节（本机 double 为 8 字节，N 为当前样本 observation 数）；N≥2 时减少，N=1 时数组有效载荷为 40→48 字节。该公式不含 vector 元数据，也不是整个进程 RSS。报告仍按原正向顺序读取相同的 double 值 |
| LROH 样本输入生命周期 | 每个样本的普通及最终区域报告结束后释放其 emission、transition、position 和 heterozygote 数组 | 只在最后一次使用后释放；后续样本不再与这些已完成数组同时存活。总输入观察值仍预先保留，allocator 也可能保留已释放页，因此不能把有效载荷直接等同 RSS |
| LD 元数据优先筛选 | 先读染色体、坐标及所需 allele 元数据，再使用原条件决定是否解码 payload；未通过的候选不写 decoded genotype | 拒绝的 payload 字节仍全部消费，保持原有 4-KiB 分块及最后 1-byte 请求，包括 short read 后的失败请求；没有 seek 跳过，不宣称减少文件读取字节或物理 I/O |
| LD 延后分配与输入缓冲释放 | 第二个 genotype vector 在首个被接受候选才分配；SNP-list anchor 在实际遍历时分配；输入 entry 和三个字节 staging 缓冲在原输入关闭及错误检查后释放 | 被接受的 decoder 完整覆盖向量；无全位点缓存、无与 payload 同尺寸的 skip 缓冲。static mask 和转换器共享缓冲保持不变 |

最终源码的常规核心回归 **4,990** 个用例、独立 LD 元数据 corpus **376** 个用例，以及匹配 LAPACK 配置的 **210** 个用例全部通过；两个常规 corpus 的 case 名称无重叠。合计 **5,576** 个用例、**14,859** 对原始结果/捕获/日志文件一致，**963** 个匹配非零退出，没有基线崩溃。完整 CLI 基线仍是原始 commit `48d19c885e0bb90ad79266e782b3c7d21a80e14c`，固定时钟只控制日志和 RNG，结果、诊断与退出码没有归一化。

新增 LROH corpus 为 11 个 fixture / 25 条命令，包含实际非空区域、长缩放链、不同样本 observation 数、首样本全部缺失而后续样本有报告、零/单 observation、过滤、坐标重复/倒序、末行无换行及解析错误。LD corpus 为 9 个 fixture / 65 条命令，覆盖七条路径、所有候选被接受/被拒绝、重复及无序坐标、染色体重访、窗口边界、缺失/多等位数据及错误前输出；经 VCF、VCF.gz、适用 BCF、文件和 stdin 路径展开。上一轮 corpus 继续参加累计回归，没有把历史执行次数叠加为当前用例。

实际 LROH kernel 在 C++98 `-O0`、`-O2` 下每版各通过 **30,688** 个场景、**553,039** 个 observation。无插桩版本逐字节比较 posterior doubles，插桩版本还比较所有 alpha/beta doubles，并确认其 posterior 与无插桩版本相同；最终浮点异常标志和 errno 一致。包含穷举短序列、随机数据、长缩放链、带 payload 的 quiet NaN、无穷、signed zero 和 subnormal；没有 float 容差。

实际 LD reader 的 signed-char、unsigned-char C++98 构建每版各通过 **3,774** 个场景、**4,017,286** 次 `ifstream::read` 请求比较，包括 **1,437** 个仅跳过解码场景、**1,632** 个短 payload、**1,910** 个异常设置或注入 fault 场景（分类可重叠）。检查 metadata、被接受 genotype 字节、每次请求长度/顺序、最终 rdstate/gcount/位置/剩余字节和是否抛出；拒绝专用 vector 保持未分配。该 trace 是 C++ 流读取请求，**不是 OS syscall 或物理磁盘读取追踪**。另有 **6,392** 个原 reader 对照场景保持通过。两份修改的 C++ 翻译单元及头文件通过启用 PCA 的 C++98 语法检查。

全部 **5,576** 个 CLI 用例额外检查私有临时文件：**36** 个用例有残留，每版共 **180** 个文件，其完整字节 multiset 相同；只忽略随机私有文件名，公共文件名和内容不变。

性能基线是冻结的第七批交付版，与上述原始 CLI 基线区分。**22** 组完整命令（6 个 LROH、14 个 LD、2 个未改动控制）每版五次、交替顺序串行运行；无并行构建/测试干扰，用各子进程自己的 wait4 峰值 RSS。所有结果文件、stdout 字节及退出码一致，正常时钟的耗时诊断单独保留。下面逐项列出所有中位数，包括耗时及 RAM 回退；合成数据用于暴露瓶颈，不能当成普通 pipeline 整体加速比例。

| 场景（名称对应 JSON） | 输入与控制目的 | 时间（第七批 → 第八批） | 峰值 RSS |
| --- | --- | --- | --- |
| `filtered-freq-gz-control` | Unchanged control. | 1.6490 → 1.6717 s | 5.11 → 5.14 MiB |
| `ld-metadata-chisq-accepted-control` | Every visited two-byte candidate passes metadata; six-allele numerical work retained. | 0.0142 → 0.0141 s | 2.06 → 2.05 MiB |
| `ld-metadata-inter-accepted-control` | All three pairs are interchromosomal and accepted; startup-scale control. | 0.0022 → 0.0020 s | 1.94 → 1.92 MiB |
| `ld-metadata-inter-geno` | One large chromosome and two small ones reject most same-chromosome pairs while retaining cross-chromosome results. | 0.4178 → 0.1098 s | 2.31 → 2.31 MiB |
| `ld-metadata-inter-hap` | One large chromosome and two small ones reject most same-chromosome pairs while retaining cross-chromosome results. | 0.4426 → 0.1303 s | 2.34 → 2.33 MiB |
| `ld-metadata-list-accepted-control` | One anchor versus 255 targets, all accepted; verifies no rejected-pair assumption is needed. | 0.0050 → 0.0050 s | 2.00 → 1.98 MiB |
| `ld-metadata-list-geno` | 150 selected anchors versus 450 others; narrow distance and chromosome gates reject most payload decoding. | 0.3221 → 0.0659 s | 2.38 → 2.36 MiB |
| `ld-metadata-list-hap` | 150 selected anchors versus 450 others; narrow distance and chromosome gates reject most payload decoding. | 0.3316 → 0.0682 s | 2.38 → 2.36 MiB |
| `ld-metadata-local-accepted-control` | Every visited inner candidate passes metadata; ordinary packed-reader control. | 0.0223 → 0.0216 s | 1.97 → 1.97 MiB |
| `ld-metadata-local-chisq` | Two-byte six-allele payloads; same rejection pattern with real nonempty chi-square results. | 0.9307 → 0.1060 s | 2.44 → 2.41 MiB |
| `ld-metadata-local-geno` | Most same-chromosome distances and all cross-chromosome pairs reject; a nonempty tail of long-distance pairs remains. | 0.5254 → 0.0739 s | 2.36 → 2.31 MiB |
| `ld-metadata-local-hap` | Most same-chromosome distances and all cross-chromosome pairs reject; a nonempty tail of long-distance pairs remains. | 0.5335 → 0.0778 s | 2.33 → 2.33 MiB |
| `ld-metadata-long-staging-chisq` | A 16-MiB final INFO row precedes 64-allele observed-matrix allocation; measures release of input entry/staging before numerical work. | 0.0220 → 0.0221 s | 142.94 → 142.97 MiB |
| `ld-metadata-wide-accepted` | Same 131072-sample input with accepted adjacent pairs; distinguishes lifetime savings from rejected-only arrays. | 0.0402 → 0.0398 s | 19.72 → 18.72 MiB |
| `ld-metadata-wide-rejected` | 131072 samples; all candidates reject, exposing lazy second-vector allocation and released input staging. Header-only result is intentional. | 0.0447 → 0.0371 s | 19.70 → 18.72 MiB |
| `lroh-beta-asymmetric-missing` | One million sites / three samples; first sample has half the observations, so releasing its inputs precedes the later large alpha allocation; nonempty focal report. | 0.5517 → 0.5293 s | 205.25 → 189.94 MiB |
| `lroh-beta-eight-samples` | 200000 observations / eight equally sized sample histories; controls shared-input storage and early release with nonempty tracts. | 0.1732 → 0.1645 s | 124.48 → 119.80 MiB |
| `lroh-beta-empty-control` | Header-only input; zero-observation branches and logging remain unchanged. | 0.0018 → 0.0018 s | 1.86 → 1.86 MiB |
| `lroh-beta-ordinary-control` | 50000 observations / eight samples; ordinary tract control matching the earlier workload shape. | 0.0422 → 0.0433 s | 30.14 → 29.73 MiB |
| `lroh-beta-single-sample-control` | A single entirely heterozygous sample exercises repeated scaling and an empty final region list. | 0.0037 → 0.0036 s | 2.41 → 2.33 MiB |
| `lroh-beta-two-samples` | One million observations / two samples; long homozygous tracts and a large per-sample alpha/beta/posterior workspace; nonempty report. | 0.5243 → 0.4906 s | 173.69 → 158.42 MiB |
| `window-pi-dense-tiled-control` | Unchanged control. | 0.0587 → 0.0594 s | 1.89 → 1.89 MiB |

LROH 两样本长链 RSS 为 **173.69 → 158.42 MiB**，不同 observation 数的三样本为 **205.25 → 189.94 MiB**，等长八样本为 **124.48 → 119.80 MiB**。常规 LROH 控制耗时 **0.0422 → 0.0433 s**（约增加 2.5%），虽有 RAM 收益但没有在每个控制组都提速。

七个高拒绝比例 LD 场景加速约 **3.4–8.8x**，来源是省去解码和不必要的 decoded-vector 写入；payload 仍照常读完。宽样本、被接受的控制 RSS 为 **19.72 → 18.72 MiB**。16-MiB 最后 INFO 行与 64-allele χ² 的生命周期场景为 **142.94 → 142.97 MiB**（增加 32 KiB），**没有测到峰值 RSS 收益**：提前释放缓冲不一定降低整个命令的最高峰；本次没有逐阶段测量 RSS，无法区分解析峰值与分配器留存各自的影响。本轮所有场景中的最大 RSS 中位数增加为 **32 KiB**；所有增加和耗时回退均保留在表中。

兼容性限制：LROH posterior 现在逆序并与 beta 交错求值，单个 recurrence/posterior 的算式和存储不变；实际 kernel 使用 FE_TONEAREST、非陷阱浮点环境，不承诺 trap 时机、异步改变舍入模式或未测试超额精度架构。旧版在零或负的归一化和上可能无限循环，相关多位点探针输入排除而未修复。LD 探针使用完整 header、实际 EOF、payload 请求处注入 badbit，并分别检查默认、badbit-only 和 failbit/eofbit/badbit 异常 mask；旧 packed reader 在非零样本但无任何 payload 字节时读取未初始化 char，该既有未定义情形排除。失败记录后不再继续进入旧 malformed next-header 路径；不声称穷尽任意设备故障。既有 signed 溢出、非法索引、其他 malformed-input 未定义行为、资源耗尽及指令级失败时序仍不在有限证据保证内。

LROH 滚动 beta 和保留读取行为的 LD 元数据解码筛选现已从候选转为已实现。**真正通过 seek 避开 payload 读取仍暂缓**，因为会改变现有读取失败语义；不能把本轮解码优化称为该方案已实现。Perl 活动区间、多文件 merge 和更多索引算法仍需 tabix 集成、原覆盖顺序及收益证据，未在本批改动。

[第八批测量、源码和二进制 SHA](../tests/results/lroh-ld-metadata-pass.json) · [复现命令](../tests/README.md)。

## C++ 读取、过滤、合并与转换

| 算法族 | 当前结构 / 优化判断 | 一致性与内存边界 |
| --- | --- | --- |
| VCF 读取与分词 | O(输入字节)，但同一行经 vector、string、stringstream 多次复制。第一批去掉读行临时副本，第五批进一步去掉 entry 的未使用整行副本；token spans 仍为后续候选 | 有降低 RAM 的空间，但需保留尾空白、CRLF、EOF、超长行以及空字段语义 |
| FORMAT schema 与通用字段提取 | 每行重新建 FORMAT map；每个字段重新扫描样本文本 | 可只复用上一种 schema，或扫描原字符串定位字段；不能引入无界缓存，也不能改变重复 tag 的索引规则 |
| 简单 ID、FILTER、染色体、QUAL、allele 类型筛选 | 通常是线性扫描加 set/map 查询；收益主要在少分配和少查找 | 保持过滤器顺序；提前返回可能跳过原来的错误、警告或有状态操作 |
| positions 精确集合 / overlap | 构建 O(P log P)，精确查询 O(log P)；第二批已实现带整数边界回退的 overlap 范围查询 | 仍使用原 set；紧凑排序数组可能减少节点内存，但读入所有重复值后再去重可能抬高峰值 RAM |
| BED overlap | 第五批已原地并集后二分，每位点 O(log B)，删除 min_ui | 不要求有序 VCF，保留旧零长/反向区间谓词。嵌套、零长度、重复区间和无序 VCF 必须验证；位点跨度仍按旧代码中最长 REF/ALT 字符串计算 |
| mask / thinning | 流式 mask 和依赖上一保留位置的贪心 thinning，接近线性 | 保留跨行、跨染色体状态；不能直接分片并行或改变无序输入行为 |
| GQ/DP/FT、MAF/MAC/HWE/phase | 多次 O(N) 扫描，第一批复用批量解析 | 下一步可共享过滤完成后的整数计数；不能复用过滤前的 counts，也不能因一个 unphased 样本提前跳过其余样本的错误检查 |
| keep/exclude 样本 | 一次性 set 查询 O(N log S)，通常不是主要热循环 | 保留 keep/exclude 顺序和重复样本名行为；无需优先增加索引 |
| 两文件位点 diff | 两个输入流前进，基本 O(M1+M2)，已经节省 RAM | 全文件 hash join 或重新排序会增加 RAM，改变重复位置匹配与输出顺序 |
| diff 样本计数 | 第六批已用原 map 顺序对应的 vector 替代第二棵计数树 | 热循环单次计数查找为 O(1)，保留名字顺序、重复映射覆盖及完整输出 |
| diff allele/switch | 同 allele 字典已有整数比较路径；switch error 保存前一状态 | 可减少不同字典时的 allele 字符串复制；需保留 missing、N、相位和染色体边界，不能任意分块 |
| PED/012/LDhat/LDhelmet 转置 | 第四批已实现固定 8 KiB 缓冲拼接首行；仍有 O(N) 或 O(2N) 个同时打开的临时流 | 进一步可研究有预算的外部磁盘转置，不改成整个 N×M 矩阵驻内存。有限错误测试不能证明所有中途磁盘故障下的行为 |
| LDhelmet allele 列表 | 第四批已在首个保留样本处懒加载并按位点复用，相同列表复制成本降为 O(MA) | 保留零保留样本时不新增解析的行为；012 中未使用的 allele 副本也已删除 |
| TPED、IMPUTE、BEAGLE、INFO/FORMAT 导出 | 大多 O(MN) 或与输出字节数线性，已经流式 | 减少临时分配；保留 BEAGLE 的浮点变换及序列化。输出本身不能被算法优化省略 |
| VCF→BCF 编码 | 第六批普通长度路径改为一列字符串及游标，并删除完整 FORMAT binary 副本 | 编码宽度、missing/vector-end、header IDX、字段顺序及短行继承不变；超长字段使用旧 splitter；数字编码中的中间数组仍可继续研究 |
| BCF 解码 / header 字典 | 解码已是定长 O(1) 或字段长度线性；header 是一次性处理 | 优先少复制和复用迭代器；不要共享可变 header，或改变重复 ID、IDX 和重打印顺序 |
| BGZF 输出 | 每块重新初始化和释放 zlib 状态 | deflateReset 可研究，但保留相同库、参数、块切分、EOF；持有状态更久可能增加峰值 RAM。换压缩库或参数不能只验证解压内容 |
| 压缩输入 | CLI 的 VCF/BCF 读取分别走 gzgets/gzread | 仅改 bgzf.c 的 inflate 不会加速当前输入；线程预取和 BGZF_MT 需要额外缓冲，不是零 RAM 成本 |

普通结果文件的 `endl` 不能全局替换：错误路径使用 `exit()`，局部流析构不会执行，删除刷新会丢失原本已写出的部分输出。临时文件也有写入后未关闭就重新打开读取的路径。

## C++ 统计与数值算法

| 算法族 | 当前复杂度 / 候选 | 精确输出限制 |
| --- | --- | --- |
| frequency / counts / 深度 / missingness | 通常 O(MN)，已接近读取所有 genotype 的下界 | 第六批 get_allele_counts 已直接复用调用者数组；跨过滤步骤计数缓存仍须另验，不更换统计定义 |
| het / 普通 burden | O(M(N+A))，每样本 O(N) 累计 | 可将位点不变量移出样本循环，仍保留每样本按位点的累计顺序和 AA/missing 规则 |
| frequency burden | 第六批按需分配 256 项计数块；输出仍完整 N×(2N+1) | 稀疏输入大幅少存整数；最坏密集空间仍为 O(N²)，额外指针目录和分配器开销已测；连续增长路线已因密集 RSS 回退而撤回 |
| HWE 精确检验 | genotype 统计 O(N)，稀有 allele 拷贝数 r 上的递推 O(r)，工作区 O(r) | 原算法本来就是高效精确递推。可研究工作区复用、同位点结果复用；不能改为 χ² 近似、截断尾部或重排求和 |
| SNP density / 位点质量 / kept/removed / 默认统计 | 通常 O(M+B) 或 O(M)，流式或按窗口累计 | 排序输入专用 streaming fast path 可省 bins，但需保留空窗口、染色体重现和原错误行为 |
| hap/genotype r² | 每个位点对 O(N) | 位编码/popcount 需要证明 missing、ploidy、整数范围与旧核函数一致；优先消除不必要读取，不先替换数值公式 |
| 局部 / 跨染色体 / 指定位点 LD | 第五批有界批读与紧凑 genotype；第八批先筛选元数据，拒绝 payload 只消费、不解码，并缩短 buffer 生命周期；P 对最坏仍 O(PN) | 保持全部 payload 字节、读取请求和原 pair 顺序，惰性分配第二向量。真正 seek 绕过 payload 仍暂缓；双指针/chromosome 索引还需覆盖无序输入、重复坐标和窗口边界。无全文件 genotype 缓存 |
| genotype χ² | 第二批已实现闭式类别编号；第七批将 expected 矩阵缩为一个 double 行，保留 observed | 保留 double 存储、边际/总和、pow、χ² 累计顺序和 gamma；普通浮点环境下的实际函数字节与 CLI 输出均已验证 |
| EM r² | 当前实现报未实现错误 | 实现 EM 属于新增功能，不是保持现有行为的性能优化 |
| hapcount | BED 扫描可能 O(MB)；haplotype vector 为 map key，复制和比较昂贵 | 当前位点早于后续 bin 时可停止扫描；稳定引用可避免 key 大复制。先处理下述基线 use-after-free |
| singletons / doubletons | 每个目标 allele 再扫样本，最坏 O(MAN) | 一次扫描记录 owner 可到 O(M(N+A))，但需要 O(A) 工作区；必须保留旧 owner 搜索只检查 include_indv 的行为 |
| FILTER / TsTv / TsTv-by-count | 大多线性或 map 查询，QUAL 版本已有前后缀累计 | 小型直接查表可减少字符串和 map 操作；排序 tie、未知模型警告和 allele 类型处理不变 |
| Fst / windowed Fst | 多群体、多 allele 计数加窗口累计；第二批已实现直接 allele 计数，第四批将 windowed Fst 的四元素 bin 内联存储 | 浮点统计公式和窗口累计不变；窗口和不能直接改成前缀和或并行归约 |
| site π / TajimaD | 主要 O(M(N+A))，另有窗口输出与 O(N) 常数初始化 | 已基本线性；保留 TajimaD 原来从首个非空 bin 开始继续输出零 SNP bins 的行为 |
| windowed π | 第七批已原位存储四列 unsigned-long 差分、mask keep 位图及滚动区间计数；每位点的窗口更新 O(1)，每次染色体输出前缀扫描 O(B) | 无第二份 bin 或 prefix 数组；保留无序输入、重访 bin0、重复染色体输出、整数模运算和最终 double 除法。不能把此整数变换套到 Fst 的浮点和 |
| LROH | 第三批已实现 next-het 单调游标和固定宽度 double 行；第八批 beta 仅两行、posterior 复用 alpha，并在报告后释放样本输入 | 主体复杂度仍 O(MN)，当前样本 alpha/beta/posterior 有效载荷 40N → 16N+32 字节；保持逐行缩放、公式、阈值和报告顺序。逆序 posterior 的普通非陷阱环境已做实际 kernel 字节对照；Viterbi/log-space 不是字节兼容替换 |
| Manichaikul / Yang relatedness | 主体 O(MN²)，矩阵 O(N²)；第三批已实现上三角存储，并去掉 Manichaikul 的对称重复计数 | 第一批删除 phi 的收益继续保留；保留原缺失/过滤逻辑和每对样本的累计次序，两种 estimator 的输出规模仍有 N² 下界 |
| PCA / SNP loadings | O(MN²+N³)，数据和 Gram matrix 占 O(MN+N²)；第四批已将 SNP loadings 的 ids 从 double 改为 int | 第六批已在原 Gram 计算后提前释放普通 PCA 的 M；逐位点 Gram 累计仍是候选；需保留每个单元累计顺序，并独立解决原版缺失数据导致的不等长 M 行问题。本批没有改求解器、PCA 方法或缺失值处理 |
| DGEEV 辅助 | 第六批已实现 NaN 分段的稳定索引排序和一次列重排，含向量时 O(N²+N log N)；不用的向量数组改为 dummy | ties、quiet NaN payload、signed zero 及同库 wrapper 已逐 double 字节验证；保留 WORK、库、维度，额外 N 个 int 的 RAM 也计入实测 |
| Mendel | 第六批用直接父母 allele 判断替代每 trio/site 四元素 set；主体仍 O(M(N+T)) | 保留旧负 ID/missing 规则。PED 的 O(TN) 初始映射仍可优化，需保留重复名字取首次匹配 |
| gamma / log-gamma | 固定系数加级数/连分式，O(迭代数)、O(1) RAM | 不替换数学库、容差、收敛判定或尾概率表达式。相同参数的有限复用必须独立核对原始浮点结果 |

## Perl：3 个模块与 26 个主脚本

这里 K=输入文件数，R=全部输入记录数，F=FORMAT 字段数，U=allele 数，C=当前活动注释/窗口记录数，L=序列长度。第五批已实现 is_indel 后缀界限、phased-join log 复用和 validator 提前停止；to-tab 缓存已实测撤回，其余仍为候选。

| 算法族 / 脚本 | 当前成本与候选 | 精确一致性与 RAM 条件 |
| --- | --- | --- |
| Vcf.pm 解析 / formatter | 每行构造 INFO/FORMAT/sample hash，单记录约 O(NF) 内存；格式化还会重算标签和排序 | 减少重复切分；不能直接原样透传，因为旧 formatter 的输出本身可能不同。已有 set_samples、每记录 haplotype/event 缓存，不应重复发明 |
| Vcf.pm Number=A/G / normalization / validation | Number=G 可有 U² 项；normalization 做共同前后缀裁剪；验证会更新部分 header 状态 | 复用当前记录的 allele 映射；保留 allele/PL/GL 顺序。共同前后缀裁剪不是参考序列左对齐，不能用另一 normalization 工具替代 |
| VcfStats.pm / vcf-stats | 多个样本分组和分类遍历；多碱基替换分类可在每样本重复，约 O(MNL) | 同位点分类复用；报告分段写出可减少完整输出字符串 RAM。保持 hash 插入、诊断和输出次序 |
| FaSlice.pm / fill-aa / tab-to-vcf | 已有参考块缓存，缓存 miss 才启动 faidx；命令结果先存行数组再拼字符串 | 流式拼接减少两份块数据；fill-aa 可研究释放已结束染色体缓存，但须保留乱序重访和失败语义 |
| fill-ref-md5 | 参考序列以 faidx→md5sum 流式处理，已不把全序列留在 RAM | 基本达到读取参考字节下界，优先级低 |
| vcf-merge / vcf-isec / vcf-compare / vcf-concat 的 merge 模式 | 每取一条记录线性查看 K 个 head，调度 O(RK) | 先缓存已解析 head，再研究稳定最小堆 O(R log K)，复用 O(K) head 状态；必须保留同坐标输入顺序、重复事件匹配及错误前部分输出 |
| vcf-isec 活动窗口 / vcf-compare 事件等价 | isec 窗口随最后记录延伸；compare 构造变异序列做候选比较，可能 O(事件数²×L) | 保留传递式聚类，不改成固定起点窗口。序列长度/签名筛选可少做完整比较，但额外索引须计入 RAM，最终仍完整比较 |
| vcf-sort / 普通 vcf-concat | 外部排序 O(R log R)，支持磁盘空间；普通 concat 已顺序流式 | 低优先级；不能改 locale、version sort、同 key tie-break 或增加 stable 选项。加并行度通常有内存代价 |
| vcf-annotate 匹配 | 每条 VCF 扫当前整个重叠注释组，最坏 O(M×注释数)，反复 normalization | 有界 normalization 复用、活动区间扫描；保持最后覆盖规则、ID 合并、端点及 normalization 后匹配，不建无界全注释缓存 |
| vcf-annotate 窗口过滤 / HWE | SnpGap/GapWin/SnpCluster 反复扫 buffer，最坏 O(MC)；HWE 已用精确递推 | 单调边界和运行计数可减少扫描；现有较严格 indel 边界、filter 链、HWE 求和顺序不可变 |
| fill-fs | 每输出位点、每个 mask 文件执行 tabix，进程启动次数可到 M×mask数 | 有界块查询或排序流扫描潜力大；需保留 BED/VCF 坐标、覆盖顺序、大小写、错误及中途输出，不能直接把 tabix 换掉 |
| vcf-phased-join | 重叠区保存 C×N genotype；同位点相同的两项 log 在各样本重复计算 | 首个有效样本处懒计算并复用两项 log，调用由 O(MN) 到 O(M)，仅两个 scalar；不能提前引入原来不会发生的 log(0)，不变更累加顺序 |
| vcf-consensus / vcf-haplotypes 序列输出 | 流式变异叠加，但每输出 60 碱基就删除 buffer 前缀；haplotypes 对两个单倍型重复提取 GT | 用 offset 遍历后一次删除已输出前缀；复用当前样本 GT。保持 60 列换行、冲突、插删坐标和全部输出字节 |
| vcf-haplotypes GFF | 按碱基位置稀疏数组、splice、按跨度 flush | 稀疏 feature/端点表示可省时省 RAM，是较大重构；需要同时比较 FASTA 和变异后的 feature 坐标/排序 |
| vcf-contrast | 前景×背景比较中反复 split PL，约 O(M×前景数×背景数×PL长度) | 有界复用 PL 解析；不能把当前判定简化成集合差，不能让 Perl 数组与原字符串长期双存抬高 RAM |
| vcf-query | 每记录每请求 tag 找 FORMAT index，每样本多次从头取字段 | 上一种 FORMAT 的有界索引；一次扫描取多个字段，保留模板次序、重复 tag 首次匹配、缺失和空值 |
| vcf-to-tab | 每个位点重新排序样本名，O(MN log N)；固定顺序缓存已在第五批实测并撤回 | 密集收益不足以抵消稀疏回退和额外 RAM；当前保留原实现。不能将同一路线再次当作未经尝试的高优先级项 |
| fill-an-ac / vcf-subset | AC/AN 重算主要 O(MN)；普通 subset 已跳过未选样本，private 模式仍需其他样本 | 保留 INFO 重排、private 判定、trim-ALT 及相关字段重映射；不能无条件忽略被删除样本 |
| vcf-convert / vcf-fix-ploidy | convert 主要 O(MNF)；fix-ploidy 已排序区间并用单调游标，但区域×样本 ploidy 可占 O(区域数×N) | 每个当前 FORMAT 编译处理计划；ploidy 可分离区域→性别和样本→性别，减少复制。保持默认值、缺失/重复样本、region 比较和报错顺序 |
| vcf-indel-stats / vcf-shuffle-cols / vcf-tstv / vcf-fix-newlines | 已分别采用区间游标、一次 header 映射、必要列扫描、流式换行转换 | 大多接近输入/输出下界，低优先级；保留 exon 边界、同名列、混合换行检测窗口和文件尾行为 |
| vcf-validator | unique 错误聚类逐个比较已有类别和 token | 出现第 3 个不同 token 即停止该候选比较，O(1) 额外 RAM；保持候选顺序和首个匹配。再加类别索引需要另算内存 |

Perl 的 phased-join log 懒复用和 validator 提前停止已完成；to-tab 固定样本排序缓存因实测收益不合适而撤回。merge/isec/compare 的稳定堆和 annotate/fill-fs 查询批处理潜力更大，但边界验证成本明显更高。

Perl 原版并不总是确定性输出：旧 `vcf-query --use-old-method` 的 `%*` 输出在前一轮六次独立运行中得到六个不同 SHA；merge/annotate 多处直接遍历 hash，VcfStats 的 `.dump` 未设置 Sortkeys，Vcf.pm 还插入当前日期。固定 Perl 版本、hash 环境和时钟能建立测试条件，但不能保证恢复任意历史随机顺序；不能先给输出排序再宣称字节兼容。

## 不应混入性能补丁的基线问题

以下是静态源码发现，尚未用专门的 sanitizer 用例验证：

- `output_haplotype_count` 在 `delete e` 后仍读取 `e->include_indv`（约 `variant_file_output.cpp:1370–1379`）。
- `output_TsTv_by_quality` 为累计数组分配 Q+1 个元素，但在末端读取 idx+1（约 `3324–3344`）。

这些模式存在未定义行为风险，不能据此承诺所有输入上基线都可逐字节重现。应分别建立复现、确定预期行为，再做独立修复；本批优化没有夹带修复或改变统计含义。

## 方法替换的边界与依据

- 不通过调整 MAF、missingness、LD 窗口、样本数、位点数来制造加速。
- 不以浮点容差、排序、删除 header 或仅比较解压文本代替原始字节比较。
- 不默认采用 GPU、随机 PCA、换 BLAS/SVD、近似 HWE、不同 kinship estimator、重排浮点归约、全矩阵缓存或改压缩参数。
- [Wigginton 等的原始 HWE 算法及代码](https://csg.sph.umich.edu/abecasis/Exact/index.html)说明这里已有精确递推方法；[KING 原始论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC3025716/)区分不同关系估计器，不能把换估计器当作同结果加速。
- [Netlib DGEEV 文档](https://netlib.org/lapack/explore-html/d4/d68/group__geev_ga7d8afe93d23c5862e238626905ee145e.html)说明 JOBVL=N 时不访问 VL；[zlib 手册](https://zlib.net/manual.html)说明 deflateReset 保留内部存储。这些契约支持候选方向，不能代替本仓库的逐字节和峰值 RSS 验证。
