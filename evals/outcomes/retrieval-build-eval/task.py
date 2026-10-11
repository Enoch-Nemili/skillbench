"""An open-ended 'help me measure search' request. Graded on whether the answer produces a usable
eval: a query file with both plain-language and exact-term queries, named metrics, a rule fixed
in advance, and a held-out set."""

import json
import re

from skillbench.grading import Check, check_mentions, code_blocks

SKILL = "retrieval-eval"

PROMPT = """
Our support team's search over about 400 help-center articles feels hit-or-miss. Article titles
look like "Reset your password", "Error E1042: payment declined", "Configure SSO with Okta" and
"Export invoices as CSV". Help me set up a way to measure how good the search actually is.
"""

_EXACT = re.compile(r"\b[A-Z]{1,4}\d{2,}\b|\bSSO\b|\bOkta\b|\bCSV\b|\bSAML\b|\bAPI\b|\b2FA\b")


def _queries(output: str) -> list[dict]:
    rows = []
    for block in code_blocks(output):
        for line in block.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and "query" in row and "expected" in row:
                rows.append(row)
    return rows


def grade(output: str):
    rows = _queries(output)
    exact = [r for r in rows if _EXACT.search(str(r["query"]))]
    plain = len(rows) - len(exact)
    metrics = {m for m in ("hit@1", "recall@", "mrr") if m in output.lower()}
    return [
        Check("query_file", len(rows) >= 10, f"{len(rows)} JSONL queries with query/expected"),
        Check(
            "exact_and_plain",
            len(exact) >= 2 and plain >= 5,
            f"{len(exact)} exact-term, {plain} plain-language",
        ),
        Check("metrics_named", len(metrics) >= 2, ", ".join(sorted(metrics)) or "none"),
        check_mentions(
            "rule_fixed_in_advance",
            output,
            r"decision rule|before (you )?(run|look|see)|in advance|up ?front|pre-?regist"
            r"|fix(ed)? (the )?(rule|threshold|criteria)",
        ),
        check_mentions(
            "held_out_set",
            output,
            r"held[- ]?out|hold[- ]?out|don'?t tune on|separate (test|validation|evaluation) set"
            r"|overfit",
        ),
    ]
