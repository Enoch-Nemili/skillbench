
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
