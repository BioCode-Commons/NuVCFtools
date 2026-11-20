#!/usr/bin/env python3
"""Generate reproducible inputs for byte-for-byte differential VCFtools tests.

    python3 tests/generate_fixtures.py --out-dir /tmp/vcftools-fixtures
    python3 tests/generate_fixtures.py --out-dir /tmp/vcftools-fixtures \
        --performance --sites 20000 --samples 100 --seed 17

The manifest records relative paths, SHA-256 hashes, and suggested command
arguments. Run cases with the output directory as cwd: prepend --vcf INPUT
(or --gzvcf COMPRESSED_INPUT) and append --out PREFIX. Cases deliberately do
not assert that malformed inputs succeed: compare the baseline exit status,
diagnostics and artifacts, including failures. No baseline output is rewritten
or normalized. The optional performance file is written one record at a time.
"""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil


SAMPLES = ("S1", "S2", "S3", "S4")
FILTERS = [
    "--minGQ", "20", "--minDP", "5", "--maxDP", "50",
    "--remove-filtered-geno-all", "--maf", "0.05", "--max-missing", "0.25",
]
COMMON_CASES = [
    {"name": "frequency", "args": ["--freq"]},
    {"name": "counts", "args": ["--counts"]},
    {"name": "missing_individual", "args": ["--missing-indv"]},
    {"name": "missing_site", "args": ["--missing-site"]},
    {"name": "individual_depth", "args": ["--depth"]},
    {"name": "site_depth", "args": ["--site-mean-depth"]},
    {"name": "recode", "args": ["--recode", "--recode-INFO-all"]},
    {"name": "filtered_frequency", "args": FILTERS + ["--freq"]},
    {"name": "filtered_recode", "args": FILTERS + ["--recode", "--recode-INFO-all"]},
    {"name": "mean_depth_then_genotype_depth", "args": [
        "--min-meanDP", "1", "--max-meanDP", "100", "--minDP", "5",
        "--maxDP", "50", "--site-depth",
    ]},
    {"name": "phase_then_frequency", "args": ["--phased", "--freq"]},
    {"name": "named_genotype_filter", "args": [
        "--remove-filtered-geno", "q10", "--recode", "--recode-INFO-all",
    ]},
    {"name": "allele_count_after_filters", "args": FILTERS + [
        "--mac", "1", "--max-missing-count", "3", "--counts",
    ]},
    {"name": "hardy_after_filters", "args": FILTERS + ["--hardy"]},
    {"name": "relatedness2", "args": ["--relatedness2"]},
    {"name": "kept_relatedness2", "args": ["--keep", "keep_standard.txt", "--relatedness2"]},
    {"name": "removed_relatedness2", "args": ["--remove", "remove_standard.txt", "--relatedness2"]},
    {"name": "kept_filtered_frequency", "args": ["--keep", "keep_standard.txt"] + FILTERS + ["--freq"]},
    {"name": "removed_frequency", "args": ["--remove", "remove_standard.txt", "--freq"]},
    {"name": "two_population_fst", "args": [
        "--weir-fst-pop", "population_a.txt", "--weir-fst-pop", "population_b.txt",
    ]},
]


def header(samples=SAMPLES):
    """Fixed headers intentionally contain no timestamps or host-specific paths."""
    lines = [
        "##fileformat=VCFv4.2",
        "##source=NuVCFtools-differential-fixture",
        '##contig=<ID=1,length=2147483647>',
        '##contig=<ID=2,length=2147483647>',
        '##contig=<ID=X,length=2147483647>',
        '##FILTER=<ID=q10,Description="Quality below ten">',
        '##FILTER=<ID=LowDP,Description="Low depth">',
        '##INFO=<ID=DP,Number=1,Type=Integer,Description="Site depth">',
        '##INFO=<ID=FLAG,Number=0,Type=Flag,Description="Test flag">',
        '##INFO=<ID=LONG,Number=1,Type=String,Description="Long field">',
        '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">',
        '##FORMAT=<ID=GQ,Number=1,Type=Float,Description="Genotype quality">',
        '##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Read depth">',
        '##FORMAT=<ID=FT,Number=1,Type=String,Description="Genotype filter">',
        '##FORMAT=<ID=XX,Number=1,Type=String,Description="Unused field">',
    ]
    columns = "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO"
    if samples:
        columns += "\tFORMAT\t" + "\t".join(samples)
    return "\n".join(lines + [columns]) + "\n"


def row(pos, fmt, values, chrom="1", ref="A", alt="C", qual="60",
        status="PASS", info="DP=30;FLAG"):
    fields = [chrom, str(pos), "v" + str(pos), ref, alt, qual, status, info]
    if fmt is not None:
        fields += [fmt] + list(values)
    return "\t".join(fields)


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def compress(path):
    # Fixed mtime and omitted original filename prevent gzip header variability.
    target = path.with_name(path.name + ".gz")
    with path.open("rb") as source, target.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as dest:
            shutil.copyfileobj(source, dest, length=1024 * 1024)
    return target


def generate_adversarial(out_dir):
    fixtures = []
    for name, contents in {
        "keep_standard.txt": "S1\nS3\n",
        "remove_standard.txt": "S2\n",
        "population_a.txt": "S1\nS2\n",
        "population_b.txt": "S3\nS4\n",
    }.items():
        (out_dir / name).write_text(contents, encoding="ascii")

    def add(name, description, rows, samples=SAMPLES, newline="\n",
            final_newline=True, suffix="", cases=None):
        path = out_dir / (name + ".vcf")
        with path.open("wb") as stream:
            stream.write(header(samples).replace("\n", newline).encode("ascii"))
            for index, item in enumerate(rows):
                ending = newline if final_newline or index < len(rows) - 1 else ""
                stream.write((item + suffix + ending).encode("ascii"))
        compressed = compress(path)
        fixtures.append({
            "name": name, "description": description, "input": path.name,
            "compressed_input": compressed.name, "bytes": path.stat().st_size,
            "sha256": digest(path), "gzip_sha256": digest(compressed),
            "cases": COMMON_CASES if cases is None else cases,
        })

    ordinary = [
        row(10, "GT:GQ:DP:FT", ["0/0:60:10:PASS", "0/1:20:5:PASS", "1|1:19:51:q10", "./.:.:.:."]),
        row(20, "DP:FT:GT:GQ", ["7:PASS:1/0:21.5", "0:LowDP:0/1:40", "50:PASS:1|1:20", ".:.:.|.:."]),
        row(30, "FT:GQ:DP:GT", ["PASS:90:30:1/1", "q10;LowDP:10:1:0/1", ".:20:5:0|0", "PASS:30:12:1|0"]),
        row(40, "GQ:GT:FT:DP", ["20:0/1:PASS:5", "21:1/1:PASS:50", "19:0/0:q10:4", "30:./.:.:."]),
        row(50, "GT:GQ:DP:FT", ["0/1:20:5:PASS", "1/1:50:50:PASS", "0/0:19.5:4:q10", "0/1:40:51:LowDP"], status="q10"),
        row(60, "GT:GQ:DP:FT", ["0/1:30:10:PASS"] * 4, ref="a", alt="ac"),
        row(70, "GT:GQ:DP:FT", ["0/2:30:10:PASS", "1/2:40:15:PASS", "2|2:50:20:PASS", "0/0:60:25:PASS"], alt="C,G"),
        row(80, "GT:GQ:DP:FT", ["./.:.:.:."] * 4, chrom="2", qual="."),
        row(90, "GT:GQ:DP:FT", ["0/0:60:10:PASS", "0/1:50:12:PASS", "1/1:40:14:PASS", "0|1:30:16:PASS"], chrom="2"),
    ]
    add("filter_interactions", "Changing field order, phase, site/genotype filters, threshold boundaries, multiallelic sites and row reset.", ordinary)

    absent = [
        row(100, "GT:GQ:DP:FT", ["0/1", "0/0:30", "1/1:40:12", "."]),
        row(110, "GT:GQ:DP:FT", ["0/1:30:12:", "0/0::7:PASS", "1/1:.:.:.", "./.:20::q10"]),
        row(120, "DP:GT:GQ:FT", ["10:0/1", ".:./.:.:.", "12:1/1:30:PASS", "4:0/0"]),
        row(130, "GQ:DP:FT", ["30:10:PASS", "20:5:PASS", ".:.:.", "10:2:q10"]),
        row(140, "GT", ["0/1", "1|1", ".", "./."]),
        row(150, ".", ["."] * 4),
        row(160, "GT:GQ:DP:FT", ["0/1:30:12:PASS", "0/0:40:8:PASS", "1|1:50:20:PASS", "0|1:60:9:PASS"]),
    ]
    add("missing_format_fields", "Absent tags, missing GT, truncated samples, empty values, omitted FT and recovery to complete fields.", absent)
    add("empty_sample_column", "Malformed empty interior sample column; compare existing diagnostics and behavior.", [
        row(170, "GT:GQ:DP:FT", ["0/1:30:10:PASS", "", "1/1:40:20:PASS", "0/0:50:30:PASS"]),
    ])
    add("duplicate_format_tags", "Malformed duplicate tag names preserve existing last-index behavior.", [
        row(180, "GT:DP:GQ:DP:FT", ["0/1:2:40:10:PASS", "1/1:80:30:4:q10", "0/0:5:20:50:PASS", "./.:.:.:.:."]),
        row(190, "GT:GT:GQ:DP:FT", ["0/0:0/1:40:10:PASS", "1/1:0/0:30:20:PASS", "0|1:1|1:20:30:PASS", "./.:./.:.:.:."]),
    ])
    add("haploid_and_partial_missing", "Haploid, phased/unphased diploid, partially missing GT and multi-digit allele indexes.", [
        row(200, "GT:GQ:DP:FT", ["0:30:10:PASS", "1:40:20:PASS", ".:.:.:.", "1:50:15:PASS"], chrom="X"),
        row(210, "GT:GQ:DP:FT", ["./1:30:10:PASS", "0/.:40:20:PASS", ".|1:20:5:PASS", "0|.:.:.:."], chrom="X"),
        row(220, "GT:GQ:DP:FT", ["0/10:30:10:PASS", "10|10:40:20:PASS", "10:50:30:PASS", "./.:.:.:."], chrom="X", alt="C,G,T,AA,AC,AG,AT,CA,CG,CT"),
    ])
    add("polyploid_error", "Unsupported triploid genotype must retain baseline error and exit status.", [
        row(230, "GT:GQ:DP:FT", ["0/1/1:30:10:PASS", "0/0:40:20:PASS", "1/1:50:30:PASS", "0/1:60:40:PASS"]),
    ])
    add("late_polyploid_error", "Valid records precede unsupported GT; compare partial files and diagnostics as well as exit status.", ordinary[:2] + [
        row(231, "GT:GQ:DP:FT", ["0/0:30:10:PASS", "1/1:40:20:PASS", "0/1:50:30:PASS", "0|1|1:60:40:PASS"]),
    ])
    add("relatedness_zero_heterozygosity", "All called genotypes are homozygous; exercise zero relatedness denominators and absent samples.", [
        row(232, "GT:GQ:DP:FT", ["0/0:30:10:PASS", "1/1:40:20:PASS", "./.:.:.:.", "0/0:60:40:PASS"]),
        row(233, "GT:GQ:DP:FT", ["1/1:30:10:PASS", "0/0:40:20:PASS", "./.:.:.:.", "1/1:60:40:PASS"]),
        row(234, "GT:GQ:DP:FT", ["0/0:30:10:PASS", "0/0:40:20:PASS", "./.:.:.:.", "0/0:60:40:PASS"]),
    ])
    add("relatedness_all_missing", "No called alleles or heterozygotes for any sample.", [
        row(235, "GT:GQ:DP:FT", ["./.:.:.:."] * 4),
        row(236, "GT:GQ:DP:FT", [".|.:.:.:."] * 4),
    ])
    add("duplicate_sample_names", "Duplicate names retain baseline header, selection, pair ordering and error behavior.", ordinary[:2], samples=("S1", "S1", "S3", "S4"))
    excluded_cases = [
        {"name": "removed_malformed_frequency", "args": ["--remove-indv", "BAD", "--freq"]},
        {"name": "removed_malformed_filtered_recode", "args": ["--remove-indv", "BAD"] + FILTERS + ["--recode", "--recode-INFO-all"]},
        {"name": "removed_malformed_depth", "args": ["--remove-indv", "BAD", "--depth"]},
        {"name": "kept_samples_frequency", "args": ["--keep", "keep_samples.txt", "--freq"]},
    ]
    add("excluded_malformed_sample", "Excluded sample contains unsupported GT; lazy-parsing changes must not suppress baseline failures.", [
        row(240, "GT:GQ:DP:FT", ["0/1:30:10:PASS", "1/1:40:20:PASS", "0/1/1:1:1:q10"]),
    ], samples=("GOOD1", "GOOD2", "BAD"), cases=excluded_cases)
    (out_dir / "keep_samples.txt").write_text("GOOD1\nGOOD2\n", encoding="ascii")
    add("early_rejected_malformed_site", "Early site filters should preserve whether later genotype parsing is reached.", [
        row(250, "GT:GQ:DP:FT", ["0/1/1:30:10:PASS"] * 4, qual="5", status="q10"),
        row(260, "GT:GQ:DP:FT", ["0/1:30:10:PASS"] * 4),
    ], cases=[
        {"name": "site_filter_before_gt", "args": ["--remove-filtered-all", "--freq"]},
        {"name": "quality_filter_before_gt", "args": ["--minQ", "10"] + FILTERS + ["--recode", "--recode-INFO-all"]},
        {"name": "without_early_filter", "args": ["--freq"]},
    ])

    add("crlf", "CRLF headers and data lines.", ordinary[:4], newline="\r\n")
    add("trailing_whitespace", "Trailing spaces and tabs, including CRLF data lines.", ordinary[:4], newline="\r\n", suffix=" \t  \t")
    add("no_final_newline", "Final record ends at EOF rather than a newline.", ordinary[:4], final_newline=False)
    add("trailing_empty_lines", "Whitespace-only lines after the last record.", ordinary[:2] + ["", " \t ", ""])
    add("header_only", "Valid header with zero variants.", [])
    add("sites_only", "Eight-column VCF without FORMAT or samples.", [row(270, None, [], info="DP=30")], samples=())

    # Cross gzgets' 1 MiB chunk boundary in INFO and in a sample FORMAT field.
    long_text = "ACGT" * (1024 * 1024 // 4 + 19)
    add("long_records", "Two records over 1 MiB, long INFO/sample values, short sentinel record, EOF without newline.", [
        row(280, "GT:GQ:DP:FT", ["0/1:30:10:PASS"] * 4, info="LONG=" + long_text),
        row(290, "GT:XX:GQ:DP:FT", ["0/1:" + long_text + ":30:10:PASS"] + ["1/1:short:40:20:PASS"] * 3),
        row(300, "GT:GQ:DP:FT", ["0/0:60:8:PASS", "0/1:50:9:PASS", "1|1:40:10:PASS", "./.:.:.:."]),
    ], final_newline=False)
    return fixtures


def generate_performance(out_dir, sites, samples, seed, gzip_output):
    path = out_dir / "performance.vcf"
    state = seed & ((1 << 64) - 1)
    orders = (("GT", "GQ", "DP", "FT"), ("DP", "GT", "FT", "GQ"))
    names = ["S%d" % (i + 1) for i in range(samples)]
    with path.open("w", encoding="ascii", newline="\n") as stream:
        stream.write(header(names))
        for site in range(sites):
            order = orders[(site // 257) % len(orders)]
            genotypes = []
            for _ in range(samples):
                # Explicit LCG avoids reliance on a Python-version-specific RNG.
                state = (state * 6364136223846793005 + 1442695040888963407) & ((1 << 64) - 1)
                fields = {
                    "GT": ("0/0", "0/1", "1/1", "0|1")[(state >> 4) % 4],
                    "GQ": str((state >> 10) % 100),
                    "DP": str((state >> 18) % 80),
                    "FT": "q10" if state % 29 == 0 else "PASS",
                }
                if state % 31 == 0:
                    fields.update(GT="./.", GQ=".", DP=".", FT=".")
                genotypes.append(":".join(fields[tag] for tag in order))
            stream.write(row(site + 1, ":".join(order), genotypes, info="DP=30") + "\n")
    result = {
        "name": "performance", "input": path.name, "sites": sites,
        "samples": samples, "seed": seed, "bytes": path.stat().st_size,
        "sha256": digest(path), "cases": COMMON_CASES,
    }
    if gzip_output:
        compressed = compress(path)
        result.update(compressed_input=compressed.name, gzip_sha256=digest(compressed))
    return result


def positive_int(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--performance", action="store_true", help="also stream performance.vcf")
    parser.add_argument("--sites", type=positive_int, default=20000)
    parser.add_argument("--samples", type=positive_int, default=100)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--gzip-performance", action="store_true", help="also gzip the optional performance file")
    args = parser.parse_args()
    if args.gzip_performance and not args.performance:
        parser.error("--gzip-performance requires --performance")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version": 1, "fixture_cwd": ".", "fixtures": generate_adversarial(args.out_dir)}
    if args.performance:
        manifest["performance"] = generate_performance(args.out_dir, args.sites, args.samples, args.seed, args.gzip_performance)
    destination = args.out_dir / "manifest.json"
    destination.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="ascii")
    print(json.dumps({"manifest": str(destination), "fixtures": len(manifest["fixtures"]), "performance": args.performance}, sort_keys=True))


if __name__ == "__main__":
    main()
