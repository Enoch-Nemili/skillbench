"""Two retrieval runs where the tempting headline (hit@1 up) hides real losses.

The candidate gains one hit@1 but three queries fall out of the top 5 entirely. Graded on
correct metrics, naming the regressed queries, flagging the sample size, and the decision.
"""

import json

from skillbench.grading import Check, check_mentions, has_number

SKILL = "retrieval-eval"

# Rank of the expected document per query (None = not returned in the top 10).
BASELINE = [1, 1, 1, 2, 1, 3, 1, 1, 2, 1, 1, 4, 1, 1, 1, 2, 1, 1, 1, 5]
CANDIDATE = [1, 1, 1, 1, 1, 1, None, 1, 1, 1, 1, 2, 8, 1, 1, 1, 1, 6, 1, 5]
REGRESSED = ["q07", "q13", "q18"]


def _ranked(qid: str, expected: str, rank: int | None) -> list[str]:
    others = [f"d{(int(qid[1:]) * 7 + k) % 90 + 10}" for k in range(10)]
    others = [d for d in others if d != expected][:10]
    if rank is not None:
        others.insert(rank - 1, expected)
    return others[:10]


def _rows(ranks):
    rows = []
    for i, rank in enumerate(ranks, start=1):
        qid, expected = f"q{i:02d}", f"d{i:02d}"
        rows.append({"query": qid, "expected": expected, "ranked": _ranked(qid, expected, rank)})
    return rows


def _metrics(ranks):
    n = len(ranks)
    return {
        "hit1": sum(r == 1 for r in ranks) / n,
        "recall5": sum(r is not None and r <= 5 for r in ranks) / n,
        "mrr": sum(1 / r for r in ranks if r) / n,
    }


TRUE = {"baseline": _metrics(BASELINE), "candidate": _metrics(CANDIDATE)}
BASE_JSONL = "\n".join(json.dumps(r) for r in _rows(BASELINE))
CAND_JSONL = "\n".join(json.dumps(r) for r in _rows(CANDIDATE))

PROMPT = f"""
We tested a new reranker on our 20 test questions. Below are the ranked results before
(baseline) and after (candidate): each line has the query id, the document that should come back,
and the documents returned, best first. Should we switch to the reranker?

```jsonl
# file: baseline.jsonl
{BASE_JSONL}
```

```jsonl
# file: candidate.jsonl
{CAND_JSONL}
```
"""


def grade(output: str):
    b, c = TRUE["baseline"], TRUE["candidate"]
    checks = [
        Check(
            "mrr_correct",
            has_number(output, b["mrr"], 0.01) and has_number(output, c["mrr"], 0.01),
            f"expected MRR {b['mrr']:.3f} and {c['mrr']:.3f}",
        ),
        # Only the candidate's 0.85 is checked: the baseline's 1.0 would match any stray "1".
        Check(
            "recall5_correct",
            has_number(output, c["recall5"], 0.005),
            f"expected candidate recall@5 {c['recall5']:.2f}",
        ),
    ]
    named = [q for q in REGRESSED if q in output.lower()]
    checks.append(
        Check("names_regressed_queries", len(named) >= 2, ", ".join(named) or "none named")
    )
    checks.append(
        check_mentions(
            "flags_small_sample",
            output,
            r"(small|only|just|limited)[^.\n]{0,30}(sample|20 (test )?(queries|questions)|test set)"
            r"|sample size|noise|noisy|significan|one query[^.\n]{0,30}(is|=|moves|worth|equals)",
        )
    )
    checks.append(
        check_mentions(
            "keeps_baseline",
            output,
            r"(don'?t|do not|not|hold off|shouldn'?t|wouldn'?t|recommend against)[^.\n]{0,40}"
            r"(switch|adopt|ship|deploy|roll)|(keep|stay with|stick with)[^.\n]{0,30}(baseline|current)",
        )
    )
    return checks
