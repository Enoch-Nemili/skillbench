---
name: repro-before-fix
description: Debug by reproducing a bug as a failing test before changing any code, then find the root cause, make the smallest fix, and keep the test as a regression guard. Covers flaky failures, "works on my machine" differences, and git bisect. Use when the user reports a bug, a crash, an error message, a failing or flaky test, a regression, or asks why something broke or stopped working.
license: MIT
compatibility: The flaky-run script needs Python 3.11+. The workflow applies to any language and test runner.
metadata:
  author: Enoch Nemili
  version: "0.1.0"
  origin: Distilled from bugs found and fixed in PaperMind and skillbench
---

# Reproduce before you fix

A fix without a reproduction is a guess. The order is fixed: **see it fail, understand
why, change one thing, see it pass, keep the test.**

## Workflow

1. **Capture the symptom exactly.** The full error text, the command that produced it,
   versions, environment and inputs. Write down expected vs actual in one sentence each.
   Don't paraphrase the error; the exact text is what you search for and assert on.

2. **Reproduce it as an automated check.** Prefer a failing test in the project's own test
   suite; otherwise a script that exits non-zero. Shrink it: remove inputs, steps and
   config until removing anything more makes the failure disappear.
   - Run it and **watch it fail for the reason in step 1**. A test that fails for a
     different reason (import error, wrong fixture) proves nothing.
   - Check it fails reliably: `python scripts/flaky.py --runs 20 -- <command>`.
     "Always fails" is a usable reproduction. "Flaky" means the cause involves timing,
     ordering, randomness or shared state; see `references/techniques.md`.

3. **Can't reproduce it?** Diff the environments instead of guessing: versions, env vars,
   config files, data, OS, time zone, network, caches. Change your side one difference at
   a time until it fails. If an older version worked, `git bisect run <command>` finds the
   commit that broke it.

4. **Find the root cause, not the nearest symptom.** Ask why until the answer is a
   decision in code or config, not "it threw". Confirm the cause with a prediction:
   "if this is the cause, then X will also happen", then check X.

5. **Make the smallest fix that addresses the cause.** No drive-by refactors in the same
   change. If the right fix is large, land a minimal one now and open an issue for the
   rest.

6. **Prove it.** The reproduction now passes, the full test suite passes, and for anything
   flaky, `flaky.py` reports "always passes" over many runs. Then revert the fix
   locally and confirm the test fails again: a test that passes either way guards nothing.

7. **Record it.** Keep the test. Write the cause, fix and evidence in the commit or pull
   request using `assets/bug-report-template.md`, and link the issue.

## Guardrails

- Never weaken or delete an assertion, add a retry, or raise a timeout to make a failure
  go away unless the root cause says that is the fix, and say so.
- Verify the tool actually ran. A green check from a linter, type checker or test run that
  silently skipped (failed install, wrong path, zero tests collected) is not evidence.
- Read the error before searching the web. Most errors say what is wrong.
- When the bug is in a dependency, reproduce it against the dependency directly, then
  work around it in your code with a comment linking the upstream issue.

## Example

A long-running MCP server's first search after an idle night failed with
`AdminShutdown: terminating connection due to administrator command`.
- Reproduce: restart Postgres between two queries in a test; the second query fails
  every time.
- Cause: the connection pool reused a connection the database had closed when it
  auto-suspended.
- Fix: `pool_pre_ping=True` and `pool_recycle=300` on the engine. The test passes, and
  stays as the regression guard.
