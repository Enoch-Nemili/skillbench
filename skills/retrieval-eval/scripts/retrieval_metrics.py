#!/usr/bin/env python3
"""
Score a retrieval run, or compare two runs, from JSONL files. Standard library only.

Each line of a run file is one query:

    {"query": "how does BERT mask tokens", "expected": "bert.pdf", "ranked": ["bert.pdf", "t5.pdf"]}

- expected: the id that SHOULD come back (string), or a list of ids where any one counts.
- ranked:   the ids your system returned, best first. Duplicates are fine (e.g. several
            chunks from the same document); only the first occurrence counts.

Usage:
    python retrieval_metrics.py score run.jsonl [--k 5] [--json]
    python retrieval_metrics.py compare baseline.jsonl candidate.jsonl [--k 5] [--json]

Metrics:
    hit@1     share of queries whose #1 result is right
    recall@k  share of queries with a right result anywhere in the top k
    mrr       mean of 1/rank of the first right result (0 when it never appears)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def first_hit_rank(ranked: list[str], expected: str | list[str]) -> int | None:
    """1-based position of the first right result, or None if it never appears."""
    wanted = {expected} if isinstance(expected, str) else set(expected)
    for position, item in enumerate(ranked, start=1):
        if item in wanted:
            return position
    return None


def load_run(path: str | Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            missing = {"query", "expected", "ranked"} - set(row)
            if missing:
                raise ValueError(f"{path}:{line_no}: missing {sorted(missing)}")
            rows.append(row)
    if not rows:
        raise ValueError(f"{path}: no queries")
    return rows


def score(rows: list[dict], k: int = 5) -> dict:
    ranks = [first_hit_rank(r["ranked"], r["expected"]) for r in rows]
    n = len(rows)
    return {
        "n": n,
        "hit@1": sum(r == 1 for r in ranks) / n,
        f"recall@{k}": sum(r is not None and r <= k for r in ranks) / n,
        "mrr": sum(1 / r for r in ranks if r) / n,
        "misses": [row["query"] for row, r in zip(rows, ranks, strict=True) if r is None or r > k],
    }


def compare(baseline: list[dict], candidate: list[dict], k: int = 5) -> dict:
    """Per-query wins and losses by reciprocal rank, plus metric deltas."""
    base_by_query = {r["query"]: r for r in baseline}
    cand_by_query = {r["query"]: r for r in candidate}
    if set(base_by_query) != set(cand_by_query):
        only = set(base_by_query) ^ set(cand_by_query)
        raise ValueError(f"runs cover different queries, e.g. {sorted(only)[:3]}")

    wins, losses = [], []
    for query, b in base_by_query.items():
        rb = first_hit_rank(b["ranked"], b["expected"])
        rc = first_hit_rank(cand_by_query[query]["ranked"], cand_by_query[query]["expected"])
        rr_b, rr_c = (1 / rb if rb else 0.0), (1 / rc if rc else 0.0)
        if rr_c > rr_b:
            wins.append({"query": query, "baseline_rank": rb, "candidate_rank": rc})
        elif rr_c < rr_b:
            losses.append({"query": query, "baseline_rank": rb, "candidate_rank": rc})

    sb, sc = score(baseline, k), score(candidate, k)
    metrics = [m for m in sb if m not in ("n", "misses")]
    return {
        "n": sb["n"],
        "baseline": {m: sb[m] for m in metrics},
        "candidate": {m: sc[m] for m in metrics},
        "delta": {m: sc[m] - sb[m] for m in metrics},
        "wins": wins,
        "losses": losses,
    }


def _print_score(result: dict) -> None:
    print(f"queries: {result['n']}")
    for name, value in result.items():
        if name not in ("n", "misses"):
            print(f"{name:>10}: {value:.3f}")
    if result["misses"]:
        print("\nmissed (no right result in top k):")
        for query in result["misses"]:
            print(f"  - {query}")


def _print_compare(result: dict) -> None:
    print(f"queries: {result['n']}\n")
    print(f"{'metric':>10}  {'baseline':>8}  {'candidate':>9}  {'delta':>7}")
    for name, base in result["baseline"].items():
        print(
            f"{name:>10}  {base:8.3f}  {result['candidate'][name]:9.3f}  "
            f"{result['delta'][name]:+7.3f}"
        )
    for label in ("wins", "losses"):
        print(f"\n{label} ({len(result[label])}):")
        for row in result[label]:
            print(f"  {row['baseline_rank']} -> {row['candidate_rank']}  {row['query']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("score", help="metrics for one run")
    s.add_argument("run")
    c = sub.add_parser("compare", help="baseline vs candidate on the same queries")
    c.add_argument("baseline")
    c.add_argument("candidate")
    for p in (s, c):
        p.add_argument("--k", type=int, default=5)
        p.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    try:
        if args.command == "score":
            result = score(load_run(args.run), args.k)
            printer = _print_score
        else:
            result = compare(load_run(args.baseline), load_run(args.candidate), args.k)
            printer = _print_compare
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        printer(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
