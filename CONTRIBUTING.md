# Contributing

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest && ruff check . && ruff format --check . && skillbench lint --strict skills/
```

CI runs the same checks on every pull request.

## Adding or changing a skill

1. `skillbench lint --strict skills/` passes.
2. Add trigger cases to [`evals/triggers.jsonl`](evals/triggers.jsonl): explicit, implicit and
   contextual requests that should load it, and near misses that shouldn't.
3. Add two outcome tasks under [`evals/outcomes/`](evals/outcomes/). The prompt must not ask for
   what the skill adds. Each grader gets tests in `tests/test_outcome_graders.py`: a
   hand-written good answer passes and a bad one fails, before any model is graded.

## Changing a description, a task or a grader

Results here are pre-registered. Before re-running a model, write the prediction and the
decision rule in [`evals/PROTOCOL.md`](evals/PROTOCOL.md) and commit it. Rejected changes are
reported, not dropped. If a grader turns out to be wrong, fix it and report the numbers before
and after (see [grader fixes](evals/RESULTS.md#grader-fixes)); `skillbench grade` re-scores
saved answers without new API calls.

## Pull requests

One change per pull request, linked to an issue, squash-merged once CI is green.
