#!/usr/bin/env python3
"""
Run a command many times and say whether it always passes, always fails, or is flaky.
Standard library only.

    python flaky.py -- pytest -q tests/test_db.py::test_reconnect
    python flaky.py --runs 50 --timeout 30 -- python repro.py
    python flaky.py --json -- ./run_case.sh

A reproduction is only useful if it fails the same way every time. Use this before a fix
(to confirm the repro is reliable) and after it (to confirm the fix holds over many runs,
not just once).

Exit codes:
    0  passed every run
    1  failed every run (a reliable reproduction)
    3  flaky: some runs passed and some failed
    2  usage error
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections import Counter

SIGNATURE_CHARS = 160


def signature(output: str) -> str:
    """A short label for a failure: the last non-empty line of its output."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return lines[-1][:SIGNATURE_CHARS] if lines else "(no output)"


def run_once(cmd: list[str], timeout: float) -> tuple[bool, str, float]:
    start = time.perf_counter()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout:g}s", time.perf_counter() - start
    elapsed = time.perf_counter() - start
    if proc.returncode == 0:
        return True, "", elapsed
    return False, f"exit {proc.returncode}: {signature(proc.stdout + proc.stderr)}", elapsed


def run_many(cmd: list[str], runs: int, timeout: float) -> dict:
    results = [run_once(cmd, timeout) for _ in range(runs)]
    passed = sum(ok for ok, _, _ in results)
    failures = Counter(sig for ok, sig, _ in results if not ok)
    times = sorted(t for _, _, t in results)
    if passed == runs:
        verdict = "always passes"
    elif passed == 0:
        verdict = "always fails"
    else:
        verdict = "flaky"
    return {
        "command": cmd,
        "runs": runs,
        "passed": passed,
        "failed": runs - passed,
        "verdict": verdict,
        "failure_signatures": dict(failures.most_common()),
        "median_seconds": round(times[len(times) // 2], 3),
        "max_seconds": round(times[-1], 3),
    }


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--" not in argv:
        print("usage: flaky.py [--runs N] [--timeout S] [--json] -- COMMAND ...", file=sys.stderr)
        return 2
    split = argv.index("--")
    parser = argparse.ArgumentParser(description="Classify a command as passing, failing or flaky.")
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=120.0, help="seconds per run")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv[:split])
    cmd = argv[split + 1 :]
    if not cmd or args.runs < 1:
        print("error: give a command after -- and --runs >= 1", file=sys.stderr)
        return 2

    try:
        report = run_many(cmd, args.runs, args.timeout)
    except FileNotFoundError:
        print(f"error: command not found: {cmd[0]}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{report['passed']}/{report['runs']} passed: {report['verdict'].upper()}")
        print(f"median {report['median_seconds']}s, max {report['max_seconds']}s")
        for sig, count in report["failure_signatures"].items():
            print(f"  {count}x  {sig}")

    return {"always passes": 0, "always fails": 1, "flaky": 3}[report["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main())
