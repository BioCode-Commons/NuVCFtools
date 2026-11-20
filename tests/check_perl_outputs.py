#!/usr/bin/env python3
"""Compare Perl tools without changing any emitted bytes.

Both revisions run sequentially at the same script/module/input/output paths.
The same clock override and hash environment are applied before Perl compiles
either revision. A baseline replay exposes pre-existing nondeterminism.
phased-join's real flush_buffer/output_line/report_stats functions are loaded
without its tabix-dependent command-line entry point; this is API coverage,
not an indexed-file integration test. Source line numbers are retained.
"""

import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys


CLOCK = "BEGIN { *CORE::GLOBAL::time = sub () { 1700000000 }; }\n1;\n"
LOADER = r'''
sub load_functions {
    my ($file) = @_;
    open my $fh, '<', $file or die "$file: $!";
    local $/; my $source = <$fh>; close $fh;
    $source =~ s{^my \$opts = parse_params\(\);.*?^exit;}{my $s=$&; $s =~ s/[^\n]/ /g; $s}mse
        or die "Cannot locate entry point in $file";
    eval qq{#line 1 "$file"\n} . $source;
    die $@ if $@;
}
'''
VALIDATOR_DRIVER = LOADER + r'''
load_functions('src/vcf-validator');
my $opts = { known_lines=>[] };
while (my $line=<STDIN>) { print_or_discard_line($opts,$line); }
print_summary($opts);
'''
INDEL_DRIVER = r'''
use strict; use warnings; use Vcf;
my $vcf = Vcf->new(version=>'4.2');
while (my $line=<STDIN>) {
    chomp $line; my ($ref,$alt)=split(/\t/,$line,-1);
    print join("\t", $vcf->is_indel($ref,$alt)), "\n";
    print join("\t", $vcf->event_type($ref,$alt)), "\n";
}
'''
PHASED_DRIVER = LOADER + r'''
use JSON::PP; use Vcf;
load_functions('src/vcf-phased-join');
local $/; my $data=decode_json(<STDIN>);
my $n=$data->{samples};
my $vcf=Vcf->new(version=>'4.2');
$vcf->{columns}=[qw(CHROM POS ID REF ALT QUAL FILTER INFO FORMAT), map { "S$_" } 0..$n-1];
my $opts={ nsamples=>$n, vcf=>$vcf, swapped=>[(-1)x$n], phasing_set=>[(0)x$n],
    phased_blocks=>[(0)x$n], broken_blocks=>[(0)x$n], breakpoints=>[],
    file1=>'left.vcf', file2=>'right.vcf', log_fh=>\*STDERR, out_fh=>\*STDOUT,
    min_PQ=>0.6, min_join_quality=>10, min_BP=>1 };
for my $block (@{$data->{blocks}}) {
    my @buffer;
    for my $site (@$block) {
        my ($pos,$format,$left,$right)=@$site;
        push @buffer, [[1,$pos,'.','A','C,G',50,'PASS','.',$format,@$left],
                      [1,$pos,'.','A','C,G',50,'PASS','.',$format,@$right]];
    }
    flush_buffer($opts,$vcf,\@buffer);
}
report_stats($opts);
'''


def vcf(records, samples=("z", "a", "m"), version="4.2"):
    header = [f"##fileformat=VCFv{version}", '##reference=test',
              '##contig=<ID=1,length=1000000>',
              '##INFO=<ID=AF,Number=A,Type=Float,Description="Frequency">',
              '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">',
              '##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Depth">',
              '##FILTER=<ID=q10,Description="Low quality">']
    columns = ["CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO"]
    if samples:
        columns += ["FORMAT", *samples]
    return ("\n".join([*header, "#" + "\t".join(columns),
                       *("\t".join(map(str, row)) for row in records)]) + "\n").encode()


def row(pos, ref="A", alt="C", fmt="GT", gts=("0/1", "1|0", "./."), info="."):
    return ["1", pos, ".", ref, alt, 50, "PASS", info, fmt, *gts]


def make_cases():
    cases = []

    def add(name, script, data, args=(), driver=None):
        cases.append({"name": name, "script": script, "input": data,
                      "args": list(args), "driver": driver})

    valid = vcf([row(1), row(2, alt="C,G", gts=("1/2", "0", "./1")),
                 row(3, fmt="GT:DP", gts=("0/0:5", "1/1:8", ".:0"))])
    add("tab-varied-genotypes", "vcf-to-tab", valid)
    add("tab-iupac", "vcf-to-tab", vcf([row(1), row(2, ref="C", alt="G,T")]), ["-i"])
    add("tab-iupac-error", "vcf-to-tab", vcf([row(1, ref="AA", alt="A")]), ["-i"])
    add("tab-changing-sample-keys", "vcf-to-tab", vcf([
        row(1), row(2, gts=("", "0/1", "1/1")),
        row(3, gts=("0/0", "", "1/1")), row(4),
        row(5, fmt="DP", gts=("5", "3", "8"))]))
    add("tab-short-row", "vcf-to-tab", vcf([row(1), row(2, gts=("0/0",))]))
    add("tab-extra-row", "vcf-to-tab", vcf([row(1, gts=("0/0", "0/1", "1/1", "0/0"))]))
    add("tab-empty", "vcf-to-tab", vcf([]))
    add("tab-no-samples", "vcf-to-tab", vcf([row(1)[:8]], samples=()))
    add("tab-crlf", "vcf-to-tab", valid.replace(b"\n", b"\r\n"))
    add("tab-no-final-newline", "vcf-to-tab", valid.rstrip(b"\n"))
    add("tab-duplicate-samples", "vcf-to-tab", vcf([
        row(1), row(2, gts=("", "0/0", "1/1")),
        row(3, gts=("1/1", "0/0", ""))], samples=("x", "a", "x")))
    add("tab-first-row-missing", "vcf-to-tab", vcf([
        row(1, gts=("", "0/1", "1/1")), row(2),
        row(3, gts=("0/0", "", "1/1"))]))
    add("tab-fake-column-names", "vcf-to-tab", b"##fileformat=VCFv4.2\n#\n1\t1\t.\tA\tC\t50\tPASS\t.\tGT\t0/0\t0/1\n")
    add("validator-valid", "vcf-validator", valid)
    add("validator-unique-valid", "vcf-validator", valid, ["-u", "input.dat"])
    warnings = vcf([row(i // 2 + 1, fmt="GT:DP", gts=("0/1:-2", "0/2:3", "./.:wrong"))
                    for i in range(20)])
    add("validator-warning-groups", "vcf-validator", warnings, ["-u", "-d", "input.dat"])
    add("validator-invalid-columns", "vcf-validator", vcf([row(1, gts=("0/1",))]), ["-u", "input.dat"])
    messages = ["", "one", "one two", "one two three", "  one two three"]
    rng = random.Random(9381)
    base = [f"word{i}" for i in range(80)]
    for differences in range(6):
        for _ in range(20):
            words = base[:]
            for index in rng.sample(range(len(words)), differences):
                words[index] = f"variant{rng.randrange(8)}"
            messages.append(" ".join(words))
    messages += messages[::3]
    add("validator-token-thresholds", "vcf-validator", ("\n".join(messages) + "\n").encode(), driver=VALIDATOR_DRIVER)
    strings = [""] + ["".join(items) for n in range(1, 7) for items in itertools.product("AC", repeat=n)]
    pairs = list(itertools.product(strings, repeat=2))
    pairs += [("A" * n + "T", "A" * (n + d) + "T")
              for n in (1, 2, 10, 100, 1000) for d in (1, 3, 20)]
    pairs += [(b, a) for a, b in pairs[-15:]]
    pairs += [(a, b) for a in ("N", "ACN", "<DEL>", "*") for b in ("", "N", "AC", "ACNN")]
    add("indel-exhaustive", "Vcf.pm", ("\n".join(a + "\t" + b for a, b in pairs) + "\n").encode(), driver=INDEL_DRIVER)
    for n in (1, 2, 3, 9, 32):
        for mode in ("match", "swap", "homo", "unphased", "different", "mixed"):
            blocks = []
            for block in range(2):
                sites = []
                for pos in range(1, 7):
                    choices = [("0|1", "0|1"), ("0|1", "1|0"), ("0|0", "0|0"),
                               ("0/1", "1/0"), ("0|1", "0|2"), ("0", "1"), (".|.", ".|.")]
                    selected = {"match": 0, "swap": 1, "homo": 2,
                                "unphased": 3, "different": 4}.get(mode, 0)
                    pairs_at_site = [choices[(i + pos + block) % len(choices)] if mode == "mixed"
                                     else choices[selected] for i in range(n)]
                    sites.append([pos + block * 10, "GT", [p[0] for p in pairs_at_site],
                                  [p[1] for p in pairs_at_site]])
                blocks.append(sites)
            add(f"phase-{n}-{mode}", "vcf-phased-join", json.dumps({"samples": n, "blocks": blocks}).encode(), driver=PHASED_DRIVER)
    add("phase-empty-buffer", "vcf-phased-join", b'{"samples":3,"blocks":[[]]}', driver=PHASED_DRIVER)
    records = [row(1, "A" * 80 + "T", "A" * 81 + "T"),
               row(3, "A" * 81 + "T", "A" * 80 + "T"), row(5),
               row(8, "ACT", "ATT"), row(20, "G", "A,T")]
    for version in ("4.0", "4.1", "4.2"):
        add("annotate-indels-" + version, "vcf-annotate", vcf(records, version=version), ["--fill-type"])
        add("annotate-window-" + version, "vcf-annotate", vcf(records, version=version), ["-f", "SnpGap=5/GapWin=3"])
        add("annotate-snpgap-" + version, "vcf-annotate", vcf(records, version=version), ["-f", "SnpGap=5"])
        add("annotate-gapwin-" + version, "vcf-annotate", vcf(records, version=version), ["-f", "GapWin=3"])
        add("stats-indels-" + version, "vcf-stats", vcf(records, version=version), ["input.dat", "-p", "result/stats"])
    return cases


def fingerprint(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def source_fingerprints(source):
    return {str(path.relative_to(source)): fingerprint(path.read_bytes())
            for path in sorted((source / "src/perl").rglob("*")) if path.is_file()}


def compare(left, right):
    differences = {}
    for name in sorted(set(left) | set(right)):
        a, b = left.get(name), right.get(name)
        if a != b:
            differences[name] = {"baseline": fingerprint(a) if a is not None else None,
                                 "candidate": fingerprint(b) if b is not None else None}
    return differences


def execute(source, case, runtime, destination, env):
    shutil.rmtree(runtime / "src", ignore_errors=True)
    shutil.copytree(source / "src/perl", runtime / "src")
    shutil.rmtree(runtime / "result", ignore_errors=True)
    (runtime / "result").mkdir()
    (runtime / "input.dat").write_bytes(case["input"])
    if case["driver"]:
        (runtime / "driver.pl").write_text(case["driver"])
        script = "driver.pl"
    else:
        script = "src/" + case["script"]
    command = ["perl", "-I.", "-Isrc", "-MFixedClock", script, *case["args"]]
    run = subprocess.run(command, input=case["input"], cwd=runtime, env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
    files = {"stdout.bin": run.stdout, "stderr.bin": run.stderr,
             "exit.txt": str(run.returncode).encode()}
    files.update({str(path.relative_to(runtime)): path.read_bytes()
                  for path in sorted((runtime / "result").rglob("*")) if path.is_file()})
    for name, contents in files.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--matrix", default="0:0,1:0,17:0")
    parser.add_argument("--baseline-replays", type=int, default=1,
                        help="Additional original-process runs to identify existing nondeterminism")
    parser.add_argument("--case", action="append", default=[])
    args = parser.parse_args()
    if args.baseline_replays < 1:
        parser.error("--baseline-replays must be at least 1")
    output = args.out_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    runtime = output / "runtime"
    runtime.mkdir(exist_ok=True)
    (runtime / "FixedClock.pm").write_text(CLOCK)
    cases = [case for case in make_cases() if not args.case or any(part in case["name"] for part in args.case)]
    source_hashes = {"baseline": source_fingerprints(args.baseline.resolve()),
                     "candidate": source_fingerprints(args.candidate.resolve())}
    results = []
    for setting in args.matrix.split(","):
        seed, perturb = setting.split(":")
        env = dict(os.environ, PERL_HASH_SEED=seed, PERL_PERTURB_KEYS=perturb, LC_ALL="C", TZ="UTC")
        env.pop("PERL5OPT", None)
        env.pop("PERL5LIB", None)
        for case in cases:
            base = output / f"seed-{seed}-perturb-{perturb}" / case["name"]
            left = execute(args.baseline.resolve(), case, runtime, base / "baseline", env)
            replays = [execute(args.baseline.resolve(), case, runtime,
                               base / f"baseline-replay-{i + 1}", env)
                       for i in range(args.baseline_replays)]
            right = execute(args.candidate.resolve(), case, runtime, base / "candidate", env)
            unstable = {}
            for replay in replays:
                unstable.update(compare(left, replay))
            differences = compare(left, right)
            stable_differences = {name: value for name, value in differences.items() if name not in unstable}
            status = "different" if stable_differences else "baseline-unstable" if unstable else "equal"
            results.append({"case": case["name"], "seed": seed, "perturb": perturb,
                            "scope": "deterministic" if perturb == "0" else "hash-perturbation-audit",
                            "status": status, "baseline_replay_differences": unstable,
                            "stable_stream_differences": stable_differences,
                            "candidate_matches_baseline_run": [i for i, replay in enumerate([left, *replays])
                                                               if not compare(replay, right)],
                            "baseline_runs": len(replays) + 1,
                            "differences": differences, "exit": left["exit.txt"].decode(),
                            "baseline": {name: fingerprint(data) for name, data in left.items()}})
            if status != "equal":
                print(f"{setting} {case['name']}: {status}", flush=True)
    summary = {"baseline": str(args.baseline.resolve()), "candidate": str(args.candidate.resolve()),
               "source_fingerprints": source_hashes,
               "clock_epoch": 1700000000, "raw_bytes_compared": True,
               "counts": {status: sum(r["status"] == status for r in results)
                          for status in ("equal", "different", "baseline-unstable")}, "results": results}
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary["counts"], sort_keys=True))
    return 1 if summary["counts"]["different"] else 0


if __name__ == "__main__":
    sys.exit(main())
