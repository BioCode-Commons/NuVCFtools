#!/usr/bin/env python3
"""Generate deterministic Perl workloads before any measured process starts."""

import argparse
import json
from pathlib import Path

from check_perl_outputs import INDEL_DRIVER, PHASED_DRIVER, VALIDATOR_DRIVER, row, vcf


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.out_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    cases = []

    def add(name, script, data, arguments=(), driver=None, description=""):
        path = output / (name + ".input")
        path.write_bytes(data)
        entry = {"name": name, "script": script, "args": list(arguments),
                 "input": path.name, "description": description}
        if driver:
            driver_path = output / (name + ".pl")
            driver_path.write_text(driver)
            entry["driver"] = driver_path.name
        cases.append(entry)

    n = 2000
    samples = [f"sample_{(i * 743) % n:05}" for i in range(n)]
    dense_gts = ["0/1", "1|0", "0/0", "1/1", "./."] * (n // 5)
    add("tab-dense", "vcf-to-tab", vcf([row(i + 1, gts=dense_gts) for i in range(1000)], samples),
        description="2,000 samples x 1,000 variants; unsorted header names")
    sparse_gts = ["" if i % 100 else "0/1" for i in range(n)]
    sparse_gts[-1] = "0/0"
    add("tab-sparse", "vcf-to-tab", vcf([row(i + 1, gts=sparse_gts) for i in range(250)], samples),
        description="2,000 header samples, approximately 1% populated; legacy empty-column warnings retained")
    add("tab-dense-then-sparse", "vcf-to-tab", vcf([row(1, gts=dense_gts)] +
        [row(i + 2, gts=sparse_gts) for i in range(250)], samples),
        description="Complete first row followed by sparse rows; cached-key absence checks")
    duplicate_names = [f"sample_{i % 400:05}" for i in range(n)]
    add("tab-duplicate-header", "vcf-to-tab", vcf([row(i + 1, gts=dense_gts) for i in range(500)], duplicate_names),
        description="2,000 header columns with 400 distinct names; per-record fallback")
    repeated_ref = "A" * 19999 + "T"
    repeated_alt = "A" * 20000 + "T"
    pairs = [(repeated_ref, repeated_alt), (repeated_alt, repeated_ref)] * 200
    add("indel-long-repeat", "Vcf.pm", ("\n".join(a + "\t" + b for a, b in pairs) + "\n").encode(),
        driver=INDEL_DRIVER, description="400 classifications of 20 kb repeat alleles, insertion and deletion")
    short_pairs = [("A", "AT"), ("AT", "A"), ("AC", "GTA"), ("ACT", "AGGT"),
                   ("ACGT", "TGCAA"), ("ACCT", "ACT")] * 50000
    add("indel-short-control", "Vcf.pm", ("\n".join(a + "\t" + b for a, b in short_pairs) + "\n").encode(),
        driver=INDEL_DRIVER, description="300,000 short insertion, deletion, and complex-event pairs")
    nonrepeat = [("ACGT" * 250 + "T", "TGCA" * 250 + "AT"),
                 ("ACGT" * 250 + "T", "ACGT" * 249 + "TAGCAT")] * 2000
    add("indel-nonrepeat-control", "Vcf.pm", ("\n".join(a + "\t" + b for a, b in nonrepeat) + "\n").encode(),
        driver=INDEL_DRIVER, description="4,000 kilobase complex pairs; early/late mismatches without long repeated suffixes")
    add("annotate-long-repeat", "vcf-annotate", vcf([row(i + 1, repeated_ref, repeated_alt)
        for i in range(400)]), ["--fill-type"], description="Real annotate CLI with 400 long repeat insertions")
    messages = []
    for repeat in range(3):
        for i in range(300):
            words = [f"group{i}", f"position{i}", f"sample{i}"] + [f"context{k}" for k in range(189)]
            messages.append(" ".join(words))
    add("validator-unique-early", "vcf-validator", ("\n".join(messages) + "\n").encode(),
        driver=VALIDATOR_DRIVER, description="900 diagnostics, 300 distinct groups, third mismatch near start")
    blocks = []
    n = 2000
    for block in range(2):
        sites = []
        for pos in range(150):
            left = ["0|1"] * n
            right = ["1|0" if i % 3 else "0|1" for i in range(n)]
            if pos % 5 == 0:
                right[-10:] = ["0|2"] * 10
            sites.append([1 + pos + block * 200, "GT", left, right])
        blocks.append(sites)
    add("phase-overlap", "vcf-phased-join", json.dumps({"samples": n, "blocks": blocks}, separators=(",", ":")).encode(),
        driver=PHASED_DRIVER, description="Real flush_buffer/output_line/report_stats functions, 2,000 samples x 300 overlap sites")
    (output / "manifest.json").write_text(json.dumps(cases, indent=2) + "\n")
    print(json.dumps({"cases": len(cases), "manifest": str(output / "manifest.json")}))


if __name__ == "__main__":
    main()
