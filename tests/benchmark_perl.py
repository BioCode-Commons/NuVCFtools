#!/usr/bin/env python3
"""Alternate real Perl processes and compare all output bytes, including errors.

posix_spawn/wait4 measures each child independently; parent fixture preparation,
file copying, output hashing and comparison are outside the timed interval.
Both revisions use identical physical paths, environment and fixed clock.
No output is normalized. See manifest descriptions for API versus CLI coverage.
"""

import argparse
import filecmp
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time

from check_perl_outputs import CLOCK, source_fingerprints


def fingerprint(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def execute(source, runtime, destination, case, env):
    shutil.rmtree(runtime / "src", ignore_errors=True)
    shutil.copytree(source / "src/perl", runtime / "src")
    shutil.rmtree(runtime / "result", ignore_errors=True)
    (runtime / "result").mkdir()
    command = ["perl", "-I.", "-Isrc", "-MFixedClock",
               "driver.pl" if case.get("driver") else "src/" + case["script"], *case["args"]]
    previous = os.getcwd()
    os.chdir(runtime)
    try:
        actions = [(os.POSIX_SPAWN_OPEN, 0, "input.dat", os.O_RDONLY, 0),
                   (os.POSIX_SPAWN_OPEN, 1, "stdout.bin", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600),
                   (os.POSIX_SPAWN_OPEN, 2, "stderr.bin", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)]
        start = time.perf_counter()
        pid = os.posix_spawnp("perl", command, env, file_actions=actions)
        _, status, usage = os.wait4(pid, 0)
        wall = time.perf_counter() - start
    finally:
        os.chdir(previous)
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("stdout.bin", "stderr.bin"):
        shutil.copyfile(runtime / name, destination / name)
    shutil.copytree(runtime / "result", destination / "result")
    exit_code = os.waitstatus_to_exitcode(status)
    (destination / "exit.txt").write_text(str(exit_code))
    return {"directory": str(destination), "wall_seconds": wall,
            "user_seconds": usage.ru_utime, "system_seconds": usage.ru_stime,
            "peak_rss_bytes": usage.ru_maxrss * (1 if sys.platform == "darwin" else 1024),
            "exit_code": exit_code,
            "files": {str(path.relative_to(destination)): fingerprint(path)
                      for path in sorted(destination.rglob("*")) if path.is_file()}}


def compare(first, second):
    a, b = Path(first["directory"]), Path(second["directory"])
    return [name for name in sorted(set(first["files"]) | set(second["files"]))
            if name not in first["files"] or name not in second["files"]
            or not filecmp.cmp(a / name, b / name, shallow=False)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--metadata-only", action="store_true",
                        help="Record metadata for an existing run without launching workloads")
    args = parser.parse_args()
    output = args.out_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    runtime = output / "runtime"
    runtime.mkdir(exist_ok=True)
    (runtime / "FixedClock.pm").write_text(CLOCK)
    fixtures = args.fixtures.resolve()
    cases = [case for case in json.loads((fixtures / "manifest.json").read_text())
             if not args.case or case["name"] in args.case]
    env = dict(os.environ, PERL_HASH_SEED="17", PERL_PERTURB_KEYS="0", LC_ALL="C", TZ="UTC")
    env.pop("PERL5OPT", None)
    env.pop("PERL5LIB", None)
    sources = {"baseline": args.baseline.resolve(), "candidate": args.candidate.resolve()}
    metadata = {"baseline": str(sources["baseline"]), "candidate": str(sources["candidate"]),
                "source_fingerprints": {name: source_fingerprints(path) for name, path in sources.items()},
                "perl_config": subprocess.check_output(["perl", "-V"], env=env).decode(),
                "environment": {key: env[key] for key in ("PERL_HASH_SEED", "PERL_PERTURB_KEYS", "LC_ALL", "TZ")},
                "removed_environment": ["PERL5OPT", "PERL5LIB"], "clock_override": CLOCK,
                "clock_epoch": 1700000000, "recorded_after_run": args.metadata_only,
                "measurement": "posix_spawnp/wait4; each child peak RSS; fixture preparation excluded",
                "source_paths_shared_between_revisions": True, "output_normalized": False}
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    if args.metadata_only:
        return 0
    results = []
    for case in cases:
        shutil.copyfile(fixtures / case["input"], runtime / "input.dat")
        if case.get("driver"):
            shutil.copyfile(fixtures / case["driver"], runtime / "driver.pl")
        runs = {"baseline": [], "candidate": []}
        comparisons = []
        for repeat in range(args.repeats):
            order = ("baseline", "candidate") if repeat % 2 == 0 else ("candidate", "baseline")
            for revision in order:
                destination = output / case["name"] / f"repeat-{repeat + 1}" / revision
                run = execute(sources[revision], runtime, destination, case, env)
                runs[revision].append(run)
                print(f"{case['name']} {repeat + 1} {revision}: {run['wall_seconds']:.3f}s, {run['peak_rss_bytes']} bytes RSS", flush=True)
            comparisons.append({"repeat": repeat + 1,
                                "differing_files": compare(runs["baseline"][-1], runs["candidate"][-1])})
        medians = {revision: {metric: statistics.median(run[metric] for run in runs[revision])
                             for metric in ("wall_seconds", "user_seconds", "system_seconds", "peak_rss_bytes")}
                   for revision in runs}
        results.append({"case": case, "runs": runs, "medians": medians, "comparisons": comparisons,
                        "baseline_replay_differences": [compare(runs["baseline"][0], run)
                                                        for run in runs["baseline"][1:]]})
        (output / "summary.json").write_text(json.dumps(results, indent=2) + "\n")
    return 1 if any(c["differing_files"] for r in results for c in r["comparisons"]) else 0


if __name__ == "__main__":
    sys.exit(main())
