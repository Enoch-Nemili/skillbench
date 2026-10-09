# Retrieval eval: <baseline> vs <candidate>

**Date:** <YYYY-MM-DD> · **Index:** <documents / chunks> · **Embedding model:** <name>

## Decision rule (written before the run)

> <e.g. Adopt the candidate only if MRR does not drop on either set and rises by at
> least 0.01 on one of them. Ties go to the simpler configuration.>

## Results

| Set | Queries | Config | hit@1 | recall@5 | MRR |
|---|---:|---|---:|---:|---:|
| plain-language | <n> | baseline | | | |
| plain-language | <n> | candidate | | | |
| exact-term | <n> | baseline | | | |
| exact-term | <n> | candidate | | | |

## Decision

<Adopted / rejected, and which line of the rule decided it.>

## Wins and losses

<Per-query changes from `retrieval_metrics.py compare`, with a one-line reason for each loss.>

## Limitations

- <Set size: one query = <100/n> points of hit@1.>
- <Known biases, e.g. long-document bias, and whether they are tracked.>
- <What this eval does not measure, e.g. answer quality, latency.>

## Reproduce

```bash
<exact commands to rebuild the index, produce the runs, and score them>
```
