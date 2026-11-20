#!/usr/bin/env python3
"""Benchmark two normal vcftools binaries and compare every retained output.

Example:
  python3 tests/benchmark.py --baseline /path/to/baseline/vcftools \
    --candidate /path/to/candidate/vcftools --input /path/to/input.vcf \
    --out-dir /path/to/new-results --repeats 5 -- --maf 0.01 --freq

Additional input paths in the vcftools arguments must be absolute, because each
run uses its own working directory. The runner owns --out and the input option.
stdout and result files are compared byte for byte; stderr and result.log are
also compared, but their differences are reported as diagnostics, not ignored
or normalized. All raw files are retained. No timing shim is loaded.
"""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import statistics
import sys
import time


CHUNK_SIZE = 1024 * 1024
CAPTURE_FILES = {"stdout.bin", "stderr.bin", "result.log"}


def fingerprint(path):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(block)
            size += len(block)
    return {"bytes": size, "sha256": digest.hexdigest()}


def compare_files(left, right):
    """Compare actual bytes, including length, rather than trusting hashes."""
    left_exists = left.is_file()
    right_exists = right.is_file()
    result = {
        "baseline": fingerprint(left) if left_exists else None,
        "candidate": fingerprint(right) if right_exists else None,
        "equal": left_exists == right_exists,
        "first_difference_byte": None,
    }
    if not (left_exists and right_exists):
        return result
    offset = 0
    with left.open("rb") as first, right.open("rb") as second:
        while True:
            a = first.read(CHUNK_SIZE)
            b = second.read(CHUNK_SIZE)
            if a != b:
                shared = min(len(a), len(b))
                difference = next((i for i in range(shared) if a[i] != b[i]), shared)
                result["equal"] = False
                result["first_difference_byte"] = offset + difference
                return result
            if not a:
                return result
            offset += len(a)


def result_inventory(directory):
    # Only the known diagnostic/capture files are separated. Any unexpected
    # regular file remains part of the result comparison, whatever its suffix.
    return {
        str(path.relative_to(directory))
        for path in directory.rglob("*")
        if path.is_file() and str(path.relative_to(directory)) not in CAPTURE_FILES
    }


def compare_runs(baseline, candidate, repeat):
    left = Path(baseline["directory"])
    right = Path(candidate["directory"])
    left_files = result_inventory(left)
    right_files = result_inventory(right)
    result_files = {
        name: compare_files(left / name, right / name)
        for name in sorted(left_files | right_files)
    }
    stdout = compare_files(left / "stdout.bin", right / "stdout.bin")
    diagnostics = {
        name: compare_files(left / name, right / name)
        for name in ("stderr.bin", "result.log")
    }
    return {
        "repeat": repeat,
        "result_files": result_files,
        "only_in_baseline": sorted(left_files - right_files),
        "only_in_candidate": sorted(right_files - left_files),
        "result_files_equal": all(item["equal"] for item in result_files.values()),
        "stdout": stdout,
        "raw_results_equal": stdout["equal"]
        and all(item["equal"] for item in result_files.values()),
        "diagnostics": diagnostics,
        "diagnostics_equal": all(item["equal"] for item in diagnostics.values()),
        "return_codes_equal": baseline["return_code"] == candidate["return_code"],
        "both_succeeded": baseline["return_code"] == candidate["return_code"] == 0,
    }


def wait_for_child(pid):
    while True:
        try:
            return os.wait4(pid, 0)
        except InterruptedError:
            continue
        except KeyboardInterrupt:
            # Do not leave our benchmark process running after interruption.
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            os.wait4(pid, 0)
            raise


def run_one(binary, input_path, input_format, flags, directory, repeat, variant, environment):
    directory.mkdir(parents=True)
    argv = [str(binary), "--" + input_format, str(input_path), "--out", "result"] + flags
    with (directory / "stdout.bin").open("wb") as stdout, \
            (directory / "stderr.bin").open("wb") as stderr, \
            open(os.devnull, "rb") as stdin:
        actions = [
            (os.POSIX_SPAWN_DUP2, stdin.fileno(), 0),
            (os.POSIX_SPAWN_DUP2, stdout.fileno(), 1),
            (os.POSIX_SPAWN_DUP2, stderr.fileno(), 2),
        ]
        # No Python code runs in the child before exec. A Python fork child
        # would inherit the runner's RSS and could inflate a small CLI's peak.
        # This runner is sequential, so temporarily changing its cwd is safe.
        previous_directory = os.open(".", os.O_RDONLY)
        try:
            os.chdir(directory)
            started = time.monotonic()
            pid = os.posix_spawn(str(binary), argv, environment, file_actions=actions)
        except OSError as exc:
            stderr.write(("benchmark runner could not spawn child: " + str(exc) + "\n").encode())
            raise
        finally:
            os.fchdir(previous_directory)
            os.close(previous_directory)
        _, status, usage = wait_for_child(pid)
        wall_seconds = time.monotonic() - started
    # wait4 returns this specific child's usage; RUSAGE_CHILDREN would aggregate.
    rss_multiplier = 1 if sys.platform == "darwin" else 1024
    return {
        "repeat": repeat,
        "variant": variant,
        "directory": str(directory),
        "argv": argv,
        "pid": pid,
        "return_code": os.waitstatus_to_exitcode(status),
        "wall_seconds": wall_seconds,
        "user_seconds": usage.ru_utime,
        "system_seconds": usage.ru_stime,
        "peak_rss_bytes": usage.ru_maxrss * rss_multiplier,
        "ru_maxrss_raw": usage.ru_maxrss,
        "ru_maxrss_unit": "bytes" if sys.platform == "darwin" else "KiB",
    }


def summarize(runs):
    summary = {}
    for variant in ("baseline", "candidate"):
        selected = [run for run in runs if run["variant"] == variant]
        metrics = {}
        for metric in ("wall_seconds", "user_seconds", "system_seconds", "peak_rss_bytes"):
            values = [run[metric] for run in selected]
            if values:
                metrics[metric] = {
                    "median": statistics.median(values),
                    "min": min(values),
                    "max": max(values),
                    "values": values,
                }
        summary[variant] = {"runs": len(selected), "metrics": metrics}
    if all(summary[variant]["runs"] for variant in ("baseline", "candidate")):
        baseline = summary["baseline"]["metrics"]
        candidate = summary["candidate"]["metrics"]
        wall = candidate["wall_seconds"]["median"]
        memory = baseline["peak_rss_bytes"]["median"]
        summary["median_wall_speedup_baseline_over_candidate"] = (
            baseline["wall_seconds"]["median"] / wall if wall else None
        )
        summary["median_peak_rss_ratio_candidate_over_baseline"] = (
            candidate["peak_rss_bytes"]["median"] / memory if memory else None
        )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--input-format", choices=("vcf", "gzvcf", "bcf"), default="vcf")
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("vcftools_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if sys.platform not in ("darwin", "linux") or not all(
            hasattr(os, name) for name in ("wait4", "posix_spawn", "POSIX_SPAWN_DUP2")):
        parser.error("per-child peak RSS measurement requires macOS or Linux with os.posix_spawn and os.wait4")
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    args.baseline = args.baseline.resolve()
    args.candidate = args.candidate.resolve()
    args.input = args.input.resolve()
    args.out_dir = args.out_dir.resolve()
    for binary in (args.baseline, args.candidate):
        if "fixed-clock" in binary.name:
            parser.error("fixed-clock binaries are for equivalence checks only; benchmark the normal vcftools binary")
        if not binary.is_file() or not os.access(binary, os.X_OK):
            parser.error("not an executable file: " + str(binary))
    if not args.input.is_file():
        parser.error("input is not a regular file: " + str(args.input))
    flags = args.vcftools_args
    if flags and flags[0] == "--":
        flags = flags[1:]
    if any(flag in {"--out", "--vcf", "--gzvcf", "--bcf"} for flag in flags):
        parser.error("the runner supplies --out and the primary input option")
    environment = os.environ.copy()
    if any(environment.get(name) for name in ("LD_PRELOAD", "DYLD_INSERT_LIBRARIES")):
        parser.error("unset LD_PRELOAD and DYLD_INSERT_LIBRARIES; benchmark normal binaries without a timing shim")
    environment.update(LC_ALL="C", TZ="UTC")
    if args.out_dir.exists() and (not args.out_dir.is_dir() or any(args.out_dir.iterdir())):
        parser.error("--out-dir must be absent or empty; existing results will never be overwritten")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": 1,
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "platform": sys.platform,
        "baseline": {"path": str(args.baseline), **fingerprint(args.baseline)},
        "candidate": {"path": str(args.candidate), **fingerprint(args.candidate)},
        "input": {"path": str(args.input), "format": args.input_format, **fingerprint(args.input)},
        "vcftools_args": flags,
        "environment_overrides": {"LC_ALL": "C", "TZ": "UTC"},
        "repeats_requested": args.repeats,
        "warmup_runs": 0,
        "method": "sequential os.posix_spawn runs; alternating first variant; wall clock and per-child os.wait4 usage",
        "diagnostic_policy": "stderr.bin and result.log compared raw and reported separately; nothing normalized",
        "runs": [],
        "comparisons": [],
        "interrupted": False,
    }
    try:
        for repeat in range(1, args.repeats + 1):
            order = ("baseline", "candidate") if repeat % 2 else ("candidate", "baseline")
            pair = {}
            for variant in order:
                directory = args.out_dir / ("repeat-%02d" % repeat) / variant
                run = run_one(getattr(args, variant), args.input, args.input_format,
                              flags, directory, repeat, variant, environment)
                pair[variant] = run
                report["runs"].append(run)
                print("repeat %d/%d %s: %.4fs, peak RSS %d bytes, exit %d" % (
                    repeat, args.repeats, variant, run["wall_seconds"],
                    run["peak_rss_bytes"], run["return_code"]), flush=True)
            report["comparisons"].append(compare_runs(pair["baseline"], pair["candidate"], repeat))
    except KeyboardInterrupt:
        report["interrupted"] = True
    finally:
        report["summary"] = summarize(report["runs"])
        comparisons = report["comparisons"]
        complete = len(comparisons) == args.repeats and not report["interrupted"]
        report["all_raw_results_equal"] = complete and all(pair["raw_results_equal"] for pair in comparisons)
        report["all_diagnostics_equal"] = complete and all(pair["diagnostics_equal"] for pair in comparisons)
        report["all_runs_succeeded"] = complete and all(pair["both_succeeded"] for pair in comparisons)
        report["passed"] = report["all_raw_results_equal"] and report["all_runs_succeeded"]
        (args.out_dir / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Raw result bytes equal: %s; diagnostic bytes equal: %s; runs succeeded: %s" % (
        report["all_raw_results_equal"], report["all_diagnostics_equal"], report["all_runs_succeeded"]))
    print("Report: " + str(args.out_dir / "summary.json"))
    return 130 if report["interrupted"] else (0 if report["passed"] else 1)


if __name__ == "__main__":
    sys.exit(main())
