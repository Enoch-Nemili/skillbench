---
name: retrieval-eval
description: Measure retrieval quality for a RAG or search system with hit@1, recall@k and MRR, and decide between configurations (semantic vs keyword vs hybrid, chunk size, reranker, fusion weight) with a rule fixed before the run. Use when the user asks whether retrieval got better or worse, wants to compare search setups, tune a RAG pipeline, or build a retrieval eval set.
license: MIT
compatibility: Needs Python 3.11+. The scoring script uses only the standard library.
metadata:
  author: Enoch Nemili
  version: "0.1.0"
  origin: Distilled from the PaperMind hybrid-search evaluation
---

# Retrieval eval

Turn "search feels better" into numbers someone else can check. The output is a
results file with a table, the decision rule, the decision, and the known limitations.

## Workflow

1. **Pin down what "right" means.** Pick the unit the system returns and the unit
   you judge: usually a document id even when the index stores chunks. Write it down.

2. **Build two query sets before running anything.** Semantic and keyword search fail
   in different ways, so test both:
   - *plain-language* queries: paraphrases a user would type, with few words copied
     from the source;
   - *exact-term* queries: identifiers, acronyms, error codes, rare names.

   Aim for 20–30 plain-language and 10 exact-term queries. Store each as one JSONL line:
   `{"query": ..., "expected": ...}`. See `references/methodology.md` for how to write
   queries that don't leak the answer.

3. **Fix the decision rule before the first run** and write it into the results file.
   Example: *adopt the candidate only if MRR does not drop on either set and rises by
   at least 0.01 on one of them.* Choosing the rule after seeing numbers is how
   evals end up confirming whatever was already believed.

4. **Run the baseline and the candidate on the same queries.** Save each run as JSONL
   with a `ranked` list (ids, best first) added to every query line. Keep the runs:
   they are the evidence.

5. **Score and compare** with the bundled script:

   ```bash
   python scripts/retrieval_metrics.py score runs/baseline.jsonl --k 5
   python scripts/retrieval_metrics.py compare runs/baseline.jsonl runs/hybrid.jsonl --k 5
   ```

   `compare` lists per-query wins and losses. Read the losses: one regression
   explained is worth more than a small average gain.

6. **Look at every miss** and label why it failed (wrong document ranked first,
   right document only in long-document chunks, query too vague, ground truth
   wrong). Fix ground-truth errors in the query file and note it; never fix them
   by quietly dropping the query.

7. **Write the results file** from `assets/results-template.md`: setup, the rule,
   the table, the decision, wins and losses, limitations. Report the numbers that
   argue against the decision too.

## Guardrails

- Never tune on the queries you report. If you iterate on settings, hold back a
  set you score only once at the end.
- Small sets swing a lot: with 30 queries one query moves hit@1 by 3.3 points.
  Say so instead of reporting a 2-point gain as an improvement.
- A score near 100% means the set is too easy; add harder queries before trusting it.
- Report the run date, index size, and model or embedding names next to the table.
