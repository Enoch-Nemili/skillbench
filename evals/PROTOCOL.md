# Trigger eval protocol

Written and committed **before** any LLM results were seen, so the results can't shape the rules.

## Setup (fixed)

- Cases: `evals/triggers.jsonl` (52 requests: 10 per skill, 12 that need no skill).
- Catalog: the 4 skills plus `evals/distractors.jsonl` (8 distractors), shuffled per trial.
- Routers:
  - `gemini-3.8-flash` (current Gemini Flash)
  - `gemini-3.5-flash-lite` (smaller and cheaper, to see whether a small router copes)
  - keyword overlap (offline baseline, already run: 73% accuracy)
- 3 trials per case per model, temperature 0. Model IDs are pinned, not `-latest` aliases,
  so a run can be repeated.
- The test cases are frozen for this round. A case is changed only if its label is wrong, and
  any change is listed in the results with the reason.

## What gets reported

Per model: accuracy, recall, false-trigger rate, per-skill precision/recall, consistency
across trials, parse errors, and every mistake.

## Rule for changing a skill description

Descriptions are what routers see, so the likely fix for a weak skill is a better description.
A description edit is **kept** only if, on both Gemini models over 3 trials:

1. accuracy rises by at least 3 answers out of 156 (about 2 points), and
2. no skill's recall drops, and
3. the false-trigger rate does not rise.

Otherwise the edit is reverted and the attempt is still reported. Editing a description changes
the catalog hash, so before and after runs are kept as separate files in `evals/runs/`.

## Known limits

- 52 cases is small: one case is about 2 points of accuracy.
- The cases were written by the skills' author, so they may favour the descriptions'
  wording. Near misses and implicit phrasings are there to push against that.
- The router is a single model call shown a catalog, which approximates, but isn't identical
  to, how a specific agent product chooses skills.
