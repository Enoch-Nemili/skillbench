"""Each grader must pass a hand-written good answer and fail a bad one, before any model is graded."""

from pathlib import Path

import pytest

from skillbench.grading import extract_files, has_number, numbers, run_pytest
from skillbench.outcomes import load_tasks

TASKS = {t.id: t for t in load_tasks(Path(__file__).resolve().parents[1] / "evals/outcomes")}


def failed(task_id, output):
    return {c.name for c in TASKS[task_id].grade(output) if not c.passed}


# --- helpers -------------------------------------------------------------------------------


def test_extract_files_reads_file_headers():
    out = "Fix:\n```python\n# file: a.py\nx = 1\n```\n```python\nno header\n```\n```js\n// file: b.js\ny\n```"
    assert extract_files(out) == {"a.py": "x = 1\n", "b.js": "y\n"}


def test_numbers_and_percentages():
    assert has_number("MRR went from 0.814 to 0.80", 0.7996, 0.01)
    assert 0.85 in numbers("recall@5 fell to 85%")
    assert not has_number("nothing here", 0.5, 0.01)


def test_run_pytest_exit_codes():
    ok = {
        "m.py": "def f():\n    return 1\n",
        "test_m.py": "from m import f\ndef test_f():\n    assert f() == 1\n",
    }
    bad = {**ok, "test_m.py": "from m import f\ndef test_f():\n    assert f() == 2\n"}
    broken = {**ok, "test_m.py": "import nope\ndef test_f():\n    pass\n"}
    assert run_pytest(ok)[0] == 0
    assert run_pytest(bad)[0] == 1
    assert run_pytest(broken)[0] == 2


def test_all_eight_tasks_load():
    assert len(TASKS) == 8
    assert {t.skill for t in TASKS.values()} == {
        "retrieval-eval",
        "mcp-server-hardening",
        "repro-before-fix",
        "release-polish",
    }


# --- repro-before-fix: graded by running code ----------------------------------------------

CART_FIX = """```python
# file: cart.py
def cart_total(items, discount_code=None):
    subtotal = sum(price * qty for price, qty in items)
    if discount_code == "SAVE10":
        subtotal *= 0.9
    return round(subtotal * 1.08, 2)
```"""
CART_TEST = """```python
# file: test_cart.py
from cart import cart_total

def test_save10_discount_applies_before_tax():
    assert cart_total([(50, 2)], "SAVE10") == 97.2
```"""
CART_WRONG_TEST = """```python
# file: test_cart.py
from cart import cart_total

def test_no_discount():
    assert cart_total([(50, 2)]) == 108.0
```"""


def test_cart_good_answer_passes_everything():
    assert failed("repro-cart-discount", CART_TEST + "\n" + CART_FIX) == set()


def test_cart_fix_without_test_fails_the_reproduction_checks():
    assert failed("repro-cart-discount", CART_FIX) == {
        "test_written",
        "test_fails_on_bug",
        "test_passes_on_fix",
    }


def test_cart_test_that_misses_the_bug_is_caught():
    assert failed("repro-cart-discount", CART_WRONG_TEST + "\n" + CART_FIX) == {"test_fails_on_bug"}


def test_cart_wrong_fix_fails_hidden_tests():
    wrong = CART_FIX.replace("subtotal *= 0.9", "subtotal -= 10")
    assert "fix_passes_hidden_tests" in failed("repro-cart-discount", CART_TEST + "\n" + wrong)


PAGE_GOOD = """```python
# file: test_paginator.py
from paginator import paginate

def test_first_page_starts_at_first_item():
    assert paginate(list(range(25)), 1, 10) == list(range(10))
```
```python
# file: paginator.py
def paginate(items, page, size):
    start = (page - 1) * size
    return items[start:start + size]
```"""


def test_pagination_good_and_bad():
    assert failed("repro-pagination", PAGE_GOOD) == set()
    only_fix = PAGE_GOOD.split("```\n```python\n")[1]
    assert "test_written" in failed("repro-pagination", "```python\n" + only_fix)


# --- mcp-server-hardening: graded on findings named ----------------------------------------

SERVER_REVIEW = """
Don't deploy this yet:
1. It binds 0.0.0.0 with no authentication, so anyone on the network can call every tool.
2. read_doc is open to path traversal: `../../etc/passwd` escapes /srv/docs.
3. fetch() is an SSRF hole: it can reach the cloud metadata endpoint at 169.254.169.254.
4. grep_logs uses shell=True with an f-string: command injection.
5. report() returns the full traceback plus the database URL, leaking credentials.
6. list_repos forwards the user's token to GitHub (token passthrough, forbidden by the MCP spec).
7. Nothing validates the Origin header, so DNS rebinding can reach it from a browser.
"""


def test_server_review_good_and_shallow():
    assert failed("mcp-review-server", SERVER_REVIEW) == set()
    shallow = "Looks fine overall. Maybe add logging and type hints."
    assert len(failed("mcp-review-server", shallow)) == 7


CONTAINER_REVIEW = """
- Don't use python:latest; pin the base image to a specific version or digest.
- Add a .dockerignore: `COPY . .` will copy your .env and .git into the image.
- The API key is baked into the image with ENV; anyone with the image can read it from docker history.
- Add a non-root USER.
- Publish the port on 127.0.0.1 only until the server has authentication.
"""


def test_container_review_good_and_shallow():
    assert failed("mcp-review-container", CONTAINER_REVIEW) == set()
    # "root" in an unrelated sense must not count as the finding.
    assert "runs_as_root" in failed(
        "mcp-review-container", "Find the root cause in the project root."
    )
    assert len(failed("mcp-review-container", "Use multi-stage builds to save space.")) == 5


# --- retrieval-eval ------------------------------------------------------------------------

COMPARE_GOOD = """
Decision rule (set before looking): switch only if MRR doesn't drop and recall@5 doesn't drop.

| | hit@1 | recall@5 | MRR |
|---|---|---|---|
| baseline | 0.70 | 1.00 | 0.814 |
| candidate | 0.75 | 0.85 | 0.800 |

Hit@1 rises by one query, but q07, q13 and q18 fall out of the top 5 (q07 disappears entirely).
With only 20 queries, one query is 5 points, so the hit@1 gain is noise. Don't switch yet.
"""


def test_compare_runs_good_and_tempting_wrong_answer():
    assert failed("retrieval-compare-runs", COMPARE_GOOD) == set()
    tempting = "Hit@1 goes from 70% to 75%, so the reranker is better. Ship it!"
    assert failed("retrieval-compare-runs", tempting) == {
        "mrr_correct",
        "recall5_correct",
        "names_regressed_queries",
        "flags_small_sample",
        "keeps_baseline",
    }


BUILD_GOOD = """Fix the decision rule before you run anything, and keep a held-out set you never tune on.
Track hit@1, recall@5 and MRR.
```jsonl
# file: queries.jsonl
{"query": "I forgot my password", "expected": "reset-password"}
{"query": "can't log in anymore", "expected": "reset-password"}
{"query": "my card keeps getting rejected", "expected": "payment-declined"}
{"query": "how do I get my bills as a spreadsheet", "expected": "export-invoices"}
{"query": "sign in with our company account", "expected": "configure-sso"}
{"query": "change the email on my account", "expected": "change-email"}
{"query": "E1042", "expected": "payment-declined"}
{"query": "Okta SSO setup", "expected": "configure-sso"}
{"query": "export CSV", "expected": "export-invoices"}
{"query": "where do refunds show up", "expected": "refunds"}
```"""


def test_build_eval_good_and_generic_advice():
    assert failed("retrieval-build-eval", BUILD_GOOD) == set()
    generic = "You could look at click-through rates and ask users for feedback."
    assert failed("retrieval-build-eval", generic) == {
        "query_file",
        "exact_and_plain",
        "metrics_named",
        "rule_fixed_in_advance",
        "held_out_set",
    }


# --- release-polish ------------------------------------------------------------------------

RELEASE_GOOD = """
1. .env is tracked: remove it, add it to .gitignore and rotate the API key now. It also stays in git
   history, so rewrite history with git filter-repo before the repo goes public.
2. Add a LICENSE file.
3. Add a CHANGELOG entry for 1.2.0.
4. Expand the README with install and usage examples.
5. Set up CI (GitHub Actions) so tests gate the release.
"""


def test_release_checklist_good_and_partial():
    assert failed("release-publish-checklist", RELEASE_GOOD) == set()
    partial = "Bump the version, build with `python -m build`, and upload with twine."
    assert failed("release-publish-checklist", partial) == {
        "env_secret_rotated",
        "history_cleaned",
        "license_added",
        "changelog_entry",
        "readme_quickstart",
        "ci_gate",
    }


SEMVER_GOOD = """This is a breaking change (load() was removed), so release **2.0.0**.

## [2.0.0] - 2026-10-11
### Changed
- **Breaking:** `load()` is now `read()`. Migration: replace `load(` with `read(`.
### Added
- `timeout` argument for `read()`.
### Fixed
- Crash on empty responses.
"""


@pytest.mark.parametrize(
    ("answer", "should_fail"),
    [
        (SEMVER_GOOD, set()),
        (
            "Release 1.5.0: it adds a feature. Changelog: renamed load to read, added timeout.",
            {"major_version", "changelog_sections", "breaking_called_out", "dated_heading"},
        ),
    ],
)
def test_semver(answer, should_fail):
    assert failed("release-semver", answer) == should_fail
