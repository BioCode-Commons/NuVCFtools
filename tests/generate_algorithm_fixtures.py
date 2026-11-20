#!/usr/bin/env python3
"""Generate deterministic inputs for Phase 2 algorithm differential tests.

    python3 tests/generate_algorithm_fixtures.py --out-dir /tmp/algorithm-fixtures

Run only the manifest-declared cases, with the generated directory as cwd.
Prepend --vcf INPUT (or --gzvcf COMPRESSED_INPUT) and append --out PREFIX.
Some inputs deliberately exercise legacy handling of malformed values. Their
declared commands avoid unrelated consumers that cannot safely accept them.
Cases marked requires_fixed_time need the same time() value in both processes
because the existing --max-indv path seeds its RNG from time().
"""

import argparse
import json
from pathlib import Path

from generate_fixtures import compress, digest, header, row


SAMPLES = tuple("S" + str(index) for index in range(1, 9))
RECODE = ["--recode", "--recode-INFO-all"]
FST = ["--weir-fst-pop", "algorithm_population_a.txt",
       "--weir-fst-pop", "algorithm_population_b.txt"]


def case(name, args, requires_fixed_time=False):
    result = {"name": name, "args": args}
    if requires_fixed_time:
        result["requires_fixed_time"] = True
    return result


def generate(out_dir):
    fixtures = []
    support_files = []

    def support(name, contents):
        path = out_dir / name
        path.write_text(contents, encoding="ascii")
        support_files.append({"path": name, "bytes": path.stat().st_size,
                              "sha256": digest(path)})
        return name

    def add(name, description, records, cases, samples=SAMPLES):
        path = out_dir / (name + ".vcf")
        with path.open("wb") as stream:
            stream.write(header(samples).encode("ascii"))
            for record in records:
                stream.write((record + "\n").encode("ascii"))
        compressed = compress(path)
        fixtures.append({
            "name": name, "description": description, "input": path.name,
            "compressed_input": compressed.name, "bytes": path.stat().st_size,
            "sha256": digest(path), "gzip_sha256": digest(compressed),
            "cases": cases,
        })

    keep = support("algorithm_keep.txt", "S1\nS3\nS5\nS7\n")
    remove = support("algorithm_remove.txt", "S2\nS3\nS6\n")
    empty = support("algorithm_keep_empty.txt", "ABSENT_SAMPLE\n")
    support("algorithm_population_a.txt", "S1\nS2\nS3\nS4\n")
    support("algorithm_population_b.txt", "S5\nS6\nS7\nS8\n")
    fst_keep = support("algorithm_fst_keep.txt", "S1\nS2\nS3\nS5\nS6\nS7\n")

    selection_cases = []
    for name, selection, count in [
        ("all", [], 8), ("kept", ["--keep", keep], 4),
        ("removed", ["--remove", remove], 5),
        ("kept_removed", ["--keep", keep, "--remove", remove], 3),
    ]:
        for label, limit in [("zero", 0), ("one", 1), ("n", count),
                             ("above_n", count + 3)]:
            selection_cases.append(case(
                name + "_max_" + label,
                selection + ["--max-indv", str(limit)] + RECODE,
                requires_fixed_time=0 < limit < count,
            ))
    selection_cases += [
        case("max_disabled", ["--max-indv", "-1"] + RECODE),
        case("empty_before_zero", ["--keep", empty, "--max-indv", "0"] + RECODE),
        case("empty_before_one", ["--keep", empty, "--max-indv", "1"] + RECODE),
        case("one_frequency", ["--max-indv", "1", "--freq"], True),
    ]
    add("random_sample_selection", "Limits 0/1/N/>N with existing keep/remove masks and no eligible samples.", [
        row(10, "GT:DP:GQ:FT", [
            "0/0:10:60:PASS", "0/1:11:61:PASS", "1/1:12:62:PASS", "1/0:13:63:PASS",
            "./.:14:64:PASS", "0|1:15:65:PASS", "1|1:16:66:PASS", "0|0:17:67:PASS",
        ]),
        row(20, "GT:DP:GQ:FT", [
            "0/1:20:70:PASS", "1/1:21:71:PASS", "0/0:22:72:PASS", "./.:23:73:PASS",
            "1/0:24:74:PASS", "0|0:25:75:PASS", "0|1:26:76:PASS", "1|0:27:77:PASS",
        ]),
    ], selection_cases)

    overlap_points = support("algorithm_overlap_positions.txt",
                             "#CHROM\tPOS\n1\t12\n1\t10\n1\t12\n1\t16\n1\t21\n2\t10\n")
    absent_points = support("algorithm_overlap_absent.txt", "#CHROM\tPOS\nX\t999\n")
    overlap_cases = [
        case("keep_overlap", ["--positions-overlap", overlap_points] + RECODE),
        case("exclude_overlap", ["--exclude-positions-overlap", overlap_points] + RECODE),
        case("keep_absent_chromosome", ["--positions-overlap", absent_points] + RECODE),
        case("exclude_absent_chromosome", ["--exclude-positions-overlap", absent_points] + RECODE),
        case("overlap_then_sample_filters", ["--positions-overlap", overlap_points,
             "--keep", keep, "--minDP", "8"] + RECODE),
    ]
    add("overlap_boundaries", "Start/interior/final base hits, exclusive end misses, duplicate positions and absent chromosomes.", [
        row(9, "GT:DP", ["0/1:10"] * 8),
        row(10, "GT:DP", ["0/1:10"] * 8),
        row(11, "GT:DP", ["0/1:10"] * 8, ref="AA", alt="A"),
        row(13, "GT:DP", ["0/1:7"] * 8, ref="AAA", alt="A"),
        row(14, "GT:DP", ["0/1:8"] * 8, ref="AAA", alt="A"),
        row(17, "GT:DP", ["0/1:10"] * 8, ref="AAAA", alt="A"),
        row(20, "GT:DP", ["0/1:10"] * 8, ref="AAA", alt="A"),
        row(10, "GT:DP", ["0/1:10"] * 8, chrom="2"),
        row(10, "GT:DP", ["0/1:10"] * 8, chrom="X"),
    ], overlap_cases)

    long_points = support("algorithm_overlap_long.txt", "1\t66535\n1\t300000\n")
    add("overlap_large_ref", "Long REF exact final-base hit and exclusive-end miss without a large committed fixture.", [
        row(1000, "GT", ["0/1"] * 8, ref="A" * 65536, alt="A"),
        row(200000, "GT", ["0/1"] * 8, ref="A" * 100000, alt="A"),
        row(400000, "GT", ["0/1"] * 8),
    ], [
        case("keep_long_overlap", ["--positions-overlap", long_points] + RECODE),
        case("exclude_long_overlap", ["--exclude-positions-overlap", long_points] + RECODE),
    ])

    signed_points = support("algorithm_overlap_signed.txt",
                            "1\t-2147483648\n1\t-3\n1\t-2\n1\t-1\n1\t0\n1\t2147483646\n")
    intmax_point = support("algorithm_overlap_intmax.txt", "1\t2147483647\n")
    # The old loop promotes POS + REF.size() to size_t. Negative POS with a
    # shorter REF may never terminate; these negative spans end at zero or one.
    add("overlap_signed_positions", "Safely terminating negative POS and spans crossing INT_MAX, retaining legacy signed lookup behavior.", [
        row(-3, "GT", ["0/1"] * 8, ref="AAAA", alt="A"),
        row(-2, "GT", ["0/1"] * 8, ref="AA", alt="A"),
        row(-1, "GT", ["0/1"] * 8),
        row(0, "GT", ["0/1"] * 8),
        row(2147483645, "GT", ["0/1"] * 8, ref="AA", alt="A"),
        row(2147483646, "GT", ["0/1"] * 8, ref="AAA", alt="A"),
        row(2147483647, "GT", ["0/1"] * 8),
        row(2147483647, "GT", ["0/1"] * 8, ref="AA", alt="A"),
    ], [
        case("keep_signed_overlap", ["--positions-overlap", signed_points] + RECODE),
        case("exclude_signed_overlap", ["--exclude-positions-overlap", signed_points] + RECODE),
        case("keep_intmax_overlap", ["--positions-overlap", intmax_point] + RECODE),
        case("exclude_intmax_overlap", ["--exclude-positions-overlap", intmax_point] + RECODE),
    ])

    fst_cases = [
        case("fst", FST),
        case("windowed_fst", FST + ["--fst-window-size", "30", "--fst-window-step", "10"]),
        case("kept_fst", ["--keep", fst_keep] + FST),
        case("removed_fst", ["--remove", remove] + FST),
        case("genotype_filtered_fst", ["--minGQ", "20", "--minDP", "5",
             "--remove-filtered-geno-all"] + FST),
    ]
    valid_gts = [
        ("C,G,T", ["0/0", "0/1", "1/2", "2/2", "0/2", "2/1", "3/3", "1/3"]),
        ("C,G", ["1/0", "0/2", "2/1", "2/2", "0/0", "1/1", "1/2", "2/0"]),
        ("C,G,T,AA,AC,AG,AT,CA,CC,CG", ["10/0", "0/10", "10/10", "9/10", "1/2", "2/1", "3/3", "0/0"]),
        ("C", ["0|1", "1|0", "0/0", "1/1", "0/1", "1/0", "1|1", "0|0"]),
    ]
    add("fst_multiallelic_valid", "Homozygotes, both heterozygote orders, changing allele counts, phased calls and two-digit allele IDs.", [
        row(10 * (index + 1), "GT:DP:GQ:FT", [
            gt + (":4:19:q10" if sample == index else ":12:30:PASS")
            for sample, gt in enumerate(genotypes)
        ], alt=alt)
        for index, (alt, genotypes) in enumerate(valid_gts)
    ], fst_cases + [case("frequency", ["--freq"]), case("recode", RECODE)])

    edge_gts = [
        ["0/.", "./0", "./.", "1/1", "2/.", "./2", "1/2", "0/0"],
        ["0/9", "9/0", "9/9", "1/1", "1/9", "9/2", "1/2", "0/0"],
        ["-2/0", "0/-2", "-2/-2", "1/1", "-2/2", "2/-2", "1/2", "0/0"],
        ["-1/0", "0/-1", "9/.", "1/1", "./9", "9/8", "1/2", "0/0"],
        ["./."] * 8,
        ["0/0"] * 8,
        ["0/1", "1/0", "2/2", "1/1", "0/2", "2/0", "1/2", "0/0"],
    ]
    # Do not run --freq/--counts or frequency filters on out-of-range alleles:
    # a different baseline helper indexes its allele vector without bounds checks.
    add("fst_multiallelic_edge", "Half missing, -1 versus other negative IDs, out-of-range homozygotes and one valid/out-of-range heterozygote.", [
        row(10 * (index + 1), "GT:DP:GQ:FT", [
            gt + (":4:19:q10" if sample == index % 8 else ":12:30:PASS")
            for sample, gt in enumerate(genotypes)
        ], alt="C,G") for index, genotypes in enumerate(edge_gts)
    ], fst_cases)

    chisq_cases = [
        case("chisq", ["--geno-chisq"]),
        case("windowed_chisq", ["--geno-chisq", "--ld-window-bp", "25"]),
        case("kept_chisq", ["--keep", fst_keep, "--geno-chisq"]),
        case("filtered_chisq", ["--minDP", "5", "--minGQ", "20", "--geno-chisq"]),
    ]
    add("chisq_multiallelic", "Multiallelic genotype pairs in swapped order, missing/haploid samples and varying contingency table dimensions.", [
        row(10, "GT:DP:GQ", [gt + ":10:30" for gt in ["0/0", "0/1", "1/0", "1/1", "0/2", "2/0", "1/2", "2/2"]], alt="C,G"),
        row(20, "GT:DP:GQ", [gt + ":10:30" for gt in ["1/1", "1/0", "0/1", "0/0", "2/0", "0/2", "2/1", "2/2"]], alt="C,G"),
        row(30, "GT:DP:GQ", [gt + ":4:19" if index == 0 else gt + ":10:30" for index, gt in enumerate(["0/0", "1/1", "0/1", "1/0", "0/0", "1/1", "0/1", "1/0"])]),
        row(40, "GT:DP:GQ", [gt + ":10:30" for gt in ["./.", "0/.", "./2", "0/0", "1/2", "2/1", "1", "1/1"]], alt="C,G,T"),
    ], chisq_cases)
    # Out-of-range nonnegative genotype pairs previously used map::operator[],
    # which assigns them contingency-table index zero. Keep them below 128 to
    # avoid conflating this rule with signed int8_t temporary-file conversion.
    add("chisq_out_of_range", "Legacy genotype-index-zero behavior for positive out-of-range calls and exclusion of negative calls.", [
        row(10, "GT:DP:GQ", [gt + ":10:30" for gt in ["0/9", "9/0", "9/9", "0/0", "1/1", "0/1", "1/2", "2/2"]], alt="C,G"),
        row(20, "GT:DP:GQ", [gt + ":10:30" for gt in ["0/0", "1/1", "0/1", "1/0", "1/9", "9/1", "9/9", "1/1"]]),
        row(30, "GT:DP:GQ", [gt + ":10:30" for gt in ["-2/0", "0/-2", "./.", "0/0", "1/1", "0/1", "1/0", "1/1"]]),
    ], chisq_cases)

    histogram_cases = [
        case("histogram", ["--hist-indel-len"]),
        case("histogram_pass_sites", ["--remove-filtered-all", "--hist-indel-len"]),
        case("histogram_allele_filter", ["--max-alleles", "2", "--hist-indel-len"]),
    ]
    add("indel_histogram_mixed", "Negative/positive deltas, zero-bin SNPs, invariant/MNP sites, symbolic alleles and repeated lengths.", [
        row(10, "GT", ["0/1"] * 8, ref="AAAA", alt="A,AA,AAAAA,AAAAAA"),
        row(20, "GT", ["0/1"] * 8, ref="A", alt="C,G"),
        row(30, "GT", ["0/0"] * 8, ref="A", alt="."),
        row(40, "GT", ["0/1"] * 8, ref="AA", alt="CC"),
        row(50, "GT", ["0/1"] * 8, ref="A", alt="<DEL>,*,N,AT"),
        row(60, "GT", ["0/1"] * 8, ref="AAAA", alt="a,aa,aaaaaa", status="q10"),
        row(70, "GT", ["0/1"] * 8, ref="A", alt="A"),
        row(80, "GT", ["0/1"] * 8, ref="A", alt="A]2:20],<INS>"),
        row(90, "GT", ["0/1"] * 8, ref="A" * 33, alt="A"),
        row(100, "GT", ["0/1"] * 8, ref="A", alt="A" * 33),
    ], histogram_cases)
    add("indel_histogram_empty", "Header-only input and the empty histogram path.", [], histogram_cases)
    add("indel_histogram_zero_only", "No counted indels: SNPs, invariant and symbolic rows, including all-filtered output.", [
        row(10, "GT", ["0/1"] * 8, alt="C", status="q10"),
        row(20, "GT", ["0/0"] * 8, alt=".", status="q10"),
        row(30, "GT", ["0/1"] * 8, alt="<DEL>", status="q10"),
    ], histogram_cases)
    for name, negative, positive in [
        ("span_32", -16, 16), ("span_33", -16, 17), ("narrow", -1, 1),
    ]:
        # The histogram dispatch uses largest_len - smallest_len, including
        # zero. All cases preserve both endpoints after optional site filters.
        add("indel_histogram_" + name,
            "Histogram dispatch boundary/control: minimum %d, maximum %d, span %d."
            % (negative, positive, positive - negative), [
                row(10, "GT", ["0/1"] * 8, ref="A" * (1 - negative), alt="A"),
                row(20, "GT", ["0/1"] * 8, ref="A", alt="A" * (1 + positive)),
                row(30, "GT", ["0/1"] * 8, ref="A" * (1 - negative), alt="A", status="q10"),
                row(40, "GT", ["0/1"] * 8, ref="A", alt="A" * (1 + positive)),
                row(50, "GT", ["0/1"] * 8, alt="C"),
                row(60, "GT", ["0/0"] * 8, alt="."),
            ], histogram_cases)
    return fixtures, support_files


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    fixtures, support_files = generate(args.out_dir)
    manifest = {"schema_version": 1, "fixture_cwd": ".", "fixtures": fixtures,
                "support_files": support_files}
    destination = args.out_dir / "manifest.json"
    destination.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="ascii")
    print(json.dumps({"manifest": str(destination), "fixtures": len(fixtures),
                      "cases": sum(len(item["cases"]) for item in fixtures)}, sort_keys=True))


if __name__ == "__main__":
    main()
