# Retrieval eval methodology

Read this when writing a query set, choosing a decision rule, or explaining a surprising result.

## Writing queries that don't leak the answer

- Write the question the way a user who has *not* read the document would ask it.
  "What trick lets the model see words on both sides?" tests understanding;
  "bidirectional masked language model pre-training" copies the abstract and
  only tests string overlap.
- Spread queries across documents. If one document owns half the set, the metric
  mostly measures that document.
- Include a few queries whose answer sits in a short document next to a long one
  on the same topic. Long documents produce many chunks and win by volume
  ("long-document bias"); you want to see whether that happens.
- Exact-term queries should contain the term a keyword index would match: an id,
  acronym, function name, error code. These are where pure embedding search usually
  loses.
- Keep `expected` honest. If two documents both answer the query, list both:
  `"expected": ["a.pdf", "b.pdf"]`.

## Decision rules that hold up

A good rule is written before the run, names the metric, the set, and the margin.

| Situation | Example rule |
|---|---|
| Replacing a baseline | Adopt only if MRR does not drop on any set and rises ≥ 0.01 on at least one. |
| Picking a weight or k | Choose the value with the best MRR on the tuning set; report it once on the held-out set. |
| Adding latency (reranker) | Adopt only if hit@1 rises ≥ 3 points and p95 latency stays under the budget. |

Ties go to the simpler or cheaper configuration.

## Reading the numbers

- **hit@1**: did the first result answer it? Closest to what a user feels.
- **recall@k**: did the answer make it into what the LLM sees? This caps answer quality
  in RAG: the model can't use a chunk it never received.
- **MRR**: rewards putting the answer near the top; moves more smoothly than hit@1 on
  small sets.

With n queries, one query is worth 1/n of hit@1. Treat differences smaller than about
2/n as noise unless the per-query wins and losses tell a consistent story.

## Common failure labels

| Label | What it looks like | Usual fix |
|---|---|---|
| long-doc bias | Long document's chunks crowd out a short, better match | Cap chunks per document before ranking, or score at document level |
| vocabulary gap | Plain-language query misses keyword search | Hybrid fusion, query expansion |
| exact-term miss | Identifier query misses embedding search | Add keyword search (BM25 / Postgres FTS) |
| bad ground truth | Retrieved document is actually right | Fix `expected`, note it in the results |
| vague query | Several documents are equally right | Rewrite the query or accept multiple ids |

## Hybrid search in one paragraph

Reciprocal Rank Fusion (RRF) combines rankings without comparing raw scores:
each result gets `weight / (k + rank)` from each ranker, summed; k = 60 is the usual
constant. Fetch more candidates from each ranker (e.g. 20) than you return (e.g. 5)
so fusion has something to reorder. Tune the keyword weight with a rule like the
ones above; an equal-weight fusion is a baseline, not a default.
