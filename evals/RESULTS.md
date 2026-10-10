# Trigger eval results

Method and rules: [PROTOCOL.md](PROTOCOL.md). Raw answers for every run: [runs/](runs/).

## Summary

| Router | Round 1 accuracy (52 cases × 3) | Hard-set accuracy (38 cases × 3) | Hard-set false triggers | Median latency |
|---|---:|---:|---:|---:|
| Keyword overlap (offline baseline) | 73% | 37% | 46% | – |
| `gemini-3.5-flash-lite` | **100%** (156/156) | **93%** (106/114) | 13% | 0.6 s |
| `gemini-3.8-flash` | incomplete (12 answers, all correct) | not run | – | ~77 s |

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

Pending: see PROTOCOL.md for the rule.
