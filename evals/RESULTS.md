# Eval results

Method and rules: [PROTOCOL.md](PROTOCOL.md). Raw answers for every run: [runs/](runs/).

- [Trigger evals](#summary): does the agent load the right skill?
- [Outcome evals](#outcome-evals): does loading it make the work better?

## Summary

| Router | Round 1 accuracy (52 cases × 3) | Hard-set accuracy (38 cases × 3) | Hard-set false triggers | Median latency |
|---|---:|---:|---:|---:|
| Keyword overlap (offline baseline) | 73% | 37% | 46% | – |
| `gemini-3.5-flash-lite` | **100%** (156/156) | **93%** (106/114) | 13% | 0.6 s |
| `gemini-3.8-flash` | incomplete (35 answers, all correct) | not run | – | 20 s (up to 77 s) |

Keyword baseline numbers are 1 trial (it is deterministic). Flash-lite's round-1 latency is not
reported: it was measured before a fix and included rate-limit waiting.

## Round 1: easy set

Flash-lite routed all 156 answers correctly, including implicit phrasings that never name the
skill and near misses like "What does MRR stand for?". It picked sensible distractors alongside
(`writing-coach` for an email, `git-workflow` for tagging a release) without crowding out the
right skill. A ceiling: the set can't show whether a description edit helps, which led to round 2.

## Round 2: hard set

| Case kind | Flash-lite accuracy |
|---|---:|
| multi-skill (needs two of our skills) | 15/15 |
| distractor is the right answer | 21/21 |
| terse | 18/18 |
| not in English (Spanish, Hindi, French) | 12/12 |
| long, context-heavy | 12/12 |
| confusable | 15/18 |
| conceptual questions near a skill | 13/18 |

**Predictions, checked:**

1. Accuracy drops below round 1: **confirmed** (100% → 93%).
2. `mcp-server-hardening` over-triggers on "build an MCP server": **wrong.** All 6 answers chose
   `mcp-builder` only.
3. Multi-skill cases are the weakest kind: **wrong.** 15/15, despite the router prompt saying
   most requests need zero or one skill.

**What actually failed:**

- `retrieval-eval` loaded for conceptual questions: "What's the difference between hit@1 and
  recall@5?" (3/3) and "Write a Python function that computes MRR" (2/3). Its description lists
  the metric names and says when to use it, but never when not to. All 5 of the hard set's
  false triggers come from this one skill.
- "The MCP server works on my machine but refuses connections inside Docker" went to
  `mcp-server-hardening` instead of `repro-before-fix` (3/3). Hardening is an allowed extra here,
  but the debugging skill was never loaded.

## Description experiments

Each experiment edits one description, re-runs `gemini-3.5-flash-lite` on both sets (3 trials),
and applies the rule fixed in PROTOCOL.md before the run. Rejected edits are reverted and
still reported.

### Experiment 1: tell `retrieval-eval` when not to load (rejected)

Added to the end of the description: *"Not for explaining what a metric means or writing a single
metric function on its own."*

| | Before | After | Rule | |
|---|---:|---:|---|---|
| Hard-set accuracy | 106/114 | 109/114 | at least 109 | met |
| Hard-set false triggers | 5/39 | **0/39** | (not a condition) | |
| `retrieval-eval` hard-set recall | 21/21 | 20/21 | must not drop | **failed** |
| `repro-before-fix` hard-set recall | 24/27 | 23/27 | must not drop | **failed** |
| Round-1 accuracy | 156/156 | 155/156 | unchanged | **failed** |

**Verdict: reverted.** The edit removed every false trigger it targeted (conceptual questions went
from 13/18 to 18/18), but recall slipped: "top-1 accuracy of our doc search: how do I even measure
that" no longer loaded the skill once in three tries, and one round-1 answer loaded
`repro-before-fix` for "Write unit tests for the new pagination helper". Each change is a single
answer, which is within noise for sets this size, and that is why the rule asks for no recall
loss at all: a precision gain paid for with recall is reported, not shipped.

Runs: `runs/*--967862e6.*` (edited catalog) against `runs/*--84aa81bb.*` (original).

## Outcome evals

`gemini-3.5-flash-lite`, temperature 0, 8 tasks (2 per skill) × with/without the skill × 3
trials = 48 answers, graded deterministically. Run: `runs/*--outcomes--e1381083.*`. Numbers are
after the two [grader fixes](#grader-fixes) below, which are reported separately.

| Skill | Fully passed, without → with | Mean check score | Pre-registered rule | Verdict |
|---|---:|---:|---|---|
| `repro-before-fix` | 0/6 → **6/6** | 40% → 100% | met | **helps** |
| `release-polish` | 1/6 → **5/6** | 51% → 96% | met | **helps** |
| `mcp-server-hardening` | 2/6 → 4/6 | 82% → 93% | failed: container review score fell 93% → 87% | no measured benefit |
| `retrieval-eval` | 0/6 → 0/6 | 37% → 63% | failed: no gain in full passes | no measured benefit |
| All | 3/24 → 15/24 | 53% → 88% | | |

**What the answers show:**

- `repro-before-fix`: without the skill, the model fixed both bugs correctly every time (6/6
  fixes pass the hidden tests) but never wrote a test. With it, all 6 answers wrote a test that
  fails on the original code and passes on the fix. Both are checked by running the code, not
  by reading it. The skill doesn't make the fix better; it adds the reproduction, which is its
  whole job.
- `release-polish`: the "ready to publish?" checklist went from 28% to 100%. Without the skill,
  no answer said to rotate the key in the committed `.env`, add a license, or give the README
  install and usage steps.
- `mcp-server-hardening`: the server review went from 0/3 to 3/3 full passes. The container
  review got slightly worse: with the skill, 2 of 3 answers missed that `COPY . .` copies the
  whole build context into the image (no `.dockerignore`); without it, 1 of 3 missed the API key
  baked in with `ENV`.
  The rule allows no score drop on either task, so this skill is not counted as helping.
- `retrieval-eval`: no full passes either way. With the skill, answers wrote JSONL queries in
  the right shape and fixed a decision rule up front, but none mentioned a held-out set and 2
  of 3 wrote fewer than 10 queries. On comparing two runs, the hard part was arithmetic: MRR
  was computed correctly 0/3 times without the skill and 1/3 with it. The skill's bundled
  scoring script would do that arithmetic, but scripts are not available in this setup.

**Predictions, checked:**

1. `repro-before-fix` shows the largest gain: **confirmed** (+6 full passes; next is
   `release-polish` at +4).
2. Without the hardening skill, reviews catch classic issues but miss MCP-specific ones:
   **confirmed.** DNS rebinding and token passthrough were missed in 3/3 answers; the other 5
   findings were caught every time.
3. Without `release-polish`, answers miss that a committed secret stays in git history:
   **mostly confirmed** (missed in 2 of 3).
4. With-skill answers are longer: **mostly confirmed**, 7 of 8 tasks. On the cart bug they got
   shorter (949 → 731 characters on average): a test and a fix, with less explanation.

### Grader fixes

Two graders were wrong and were fixed after the run ([amendment](PROTOCOL.md#amendment-two-grader-fixes-after-the-valid-run-reported-separately)).
The same 48 saved answers, graded three ways:

| | Original graders | Extraction fixed | Both fixed |
|---|---:|---:|---:|
| Fully passed, without → with | 12% → 38% | 12% → 62% | 12% → 62% |
| Mean check score, without → with | 40% → 62% | 50% → 86% | 53% → 88% |
| `repro-before-fix` full passes | 0/6 → 0/6 | 0/6 → 6/6 | 0/6 → 6/6 |
| `repro-before-fix` verdict | no measured benefit | helps | helps |
| Other verdicts | | unchanged | unchanged |

The extraction fix changes one verdict, so it deserves the most scrutiny. It applies to both
conditions, and without-skill answers gained too: their fixes are now found, run and pass the
hidden tests. The checks it unlocks run the code: a test only counts if it fails on the bug and
passes on the fix. Its limit: the new parser was tested on the layouts this model produced, and
another model may need more. The metric fix moves no pass/fail result.

### Known limits

One model, 3 trials, 2 tasks per skill: a difference of one or two runs is within noise. Six of
the eight tasks are graded by finding content in the answer, which a with-skill answer can echo
from the skill's text, so those scores are an upper bound. The skills, tasks and graders were
written by the same author.
