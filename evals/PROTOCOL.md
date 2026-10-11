
---

# Round 2: hard cases

Round 1 hit a ceiling: `gemini-3.5-flash-lite` answered all 156 correctly (100% accuracy, 0% false
triggers, 100% consistency). A set nothing fails can't show whether a description edit helps, so
round 2 adds harder cases. Everything below was written and committed **before** any model saw
the new cases.

## Setup (fixed)

- Cases: `evals/triggers-hard.jsonl`, 38 requests: 5 needing two of our skills, 6 confusable
  (one skill is right but another is plausible), 7 where a distractor is right and none of ours
  is, 6 conceptual questions near a skill's topic, 6 terse or indirect, 4 not in English
  (Spanish, Hindi, French), 4 long and context-heavy.
- Cases may list `allowed` skills: loading one is not penalised, but every `expected` skill must
  be loaded. Used where a second skill is defensible (4 cases).
- Same catalog, routers (`gemini-3.5-flash-lite`, `gemini-3.8-flash`, keyword baseline),
  3 trials, temperature 0.

## Predictions (written before the run)

1. Accuracy drops below round 1 for both models.
2. `mcp-server-hardening` over-triggers on "build an MCP server" requests, because its
   description says "Use when the user builds ... an MCP server". Those cases are labelled
   "none of ours" (`mcp-builder` is the right skill).
3. Multi-skill cases are the weakest kind, partly because the router prompt says "Most requests
   need zero or one skill".

## Rule for changing a description (round 2)

A description edit is kept only if, over 3 trials on both Gemini models:

1. hard-set accuracy rises by at least 3 answers out of 114, and
2. no skill's recall drops on the hard set, and
3. round-1 accuracy stays where it was (no regression on the easy set).

Otherwise it is reverted, and the attempt is still reported.

## Amendment (written after the round-2 flash-lite results, before any description edit was tested)

`gemini-3.8-flash` can't support the description experiments: its median latency was about
77 s per answer, and repeated 503 "high demand" errors left it at 12 of 156 round-1 answers
after about an hour. A description edit also changes the catalog, which would split its run.
So:

- The 3.8-flash run stops here. Its partial answers are kept in `evals/runs/` and reported as
  incomplete; they are not used for any decision.
- Description edits are decided on `gemini-3.5-flash-lite` alone, with the same thresholds:
  hard-set accuracy up by at least 3 of 114 answers, no skill's hard-set recall down, and
  round-1 accuracy unchanged (156 of 156).
- One description is edited at a time, so each change in the numbers can be attributed.

---

# Round 3: outcome evals

Trigger evals ask whether the agent loads a skill. Outcome evals ask whether loading it makes
the work better. Written and committed **before** any model answered these tasks.

## Setup (fixed)

- Tasks: `evals/outcomes/*/task.py`, 2 per skill (8 total). Each prompt is neutral: it never
  asks for the behaviour the skill adds (the debugging tasks never mention tests, the review
  tasks never list what to look for).
- Conditions: the same model answers each task twice per trial, as a plain assistant
  (`without`) and with the skill's SKILL.md body loaded as instructions (`with`). Bundled
  scripts and references are not available in either condition.
- Model: `gemini-3.5-flash-lite`, 3 trials, temperature 0. That is 48 answers.
- Grading is deterministic and published with its own tests (`tests/test_outcome_graders.py`:
  every grader passes a hand-written good answer and fails a bad one). The two debugging tasks
  are graded by running the answer's code: its test must fail on the original bug, pass on its
  fix, and the fix must pass hidden tests.

## Predictions (written before the run)

1. `repro-before-fix` shows the largest gain: without the skill, answers mostly fix the code
   without a test that reproduces the bug; with it, they write that test first.
2. `mcp-server-hardening`: without the skill, reviews catch the classic issues (shell injection,
   path traversal) but miss MCP-specific ones (DNS rebinding, token passthrough).
3. `release-polish`: without the skill, answers miss that a committed secret stays in git history.
4. With-skill answers are longer.

## Rule for "the skill helps"

A skill is reported as helping only if, across its 2 tasks × 3 trials:

1. tasks fully passed rise by at least 2 of 6 runs, and
2. the mean check score does not drop on either task.

Otherwise it is reported as "no measured benefit". No task or grader is changed after the run;
if a grader turns out to be wrong, the fix and its effect on the numbers are reported separately.

## Known limits

- 6 of 8 tasks are graded by finding specific content in the answer. A with-skill answer can
  echo the skill's vocabulary ("held-out set", "DNS rebinding"). Naming a problem is necessary
  for a good review, not sufficient, so these scores are an upper bound on real improvement.
  The two debugging tasks are graded by execution and don't have this weakness.
- The skill text and the tasks were written by the same author.

## Amendment: first outcome run invalid (written before the re-run)

The first run (`runs/gemini--gemini-3.5-flash-lite--outcomes--83dc38b3.*`) is invalid and is not
interpreted. The Gemini provider always requested JSON output, a setting meant only for trigger
evals, so every outcome answer came back as a JSON object instead of prose and code blocks. The
graders found no code files to run, and JSON mode also corrupted the code itself (for example
`def:` with no function name). It failed both conditions alike, so it measured the harness,
not the skills.

Fix: outcome runs now request plain text (regression tests in `tests/test_providers.py` and
`tests/test_outcomes.py`), and the harness version is part of the run file name, so the re-run
starts fresh instead of resuming the broken file. Tasks, graders, predictions and the rule are
unchanged. The invalid run file is kept as evidence.
