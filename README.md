# skillbench

[![CI](https://github.com/Enoch-Nemili/skillbench/actions/workflows/ci.yml/badge.svg)](https://github.com/Enoch-Nemili/skillbench/actions/workflows/ci.yml)

**Agent Skills that come with evidence.**

A small pack of [Agent Skills](https://agentskills.io) for AI-infrastructure work, plus the
harness that checks them: a linter for the open SKILL.md spec, trigger evals (does the agent
pick the right skill?) and outcome evals (does the work get better with it?).

Each skill is distilled from a project that was built and measured first. `retrieval-eval`, for
example, is the method used to tune [PaperMind](https://github.com/Enoch-Nemili/papermind)'s
hybrid search.

> **Status:** linter, 4 skills, trigger and outcome evals with results. v1.0.0 next.

## Skills

| Skill | What it does | Comes from |
|---|---|---|
| [`retrieval-eval`](skills/retrieval-eval/SKILL.md) | Scores a RAG/search system with hit@1, recall@k and MRR and picks between configurations using a decision rule fixed before the run. Bundles a stdlib scoring/compare script. | PaperMind hybrid search |
| [`mcp-server-hardening`](skills/mcp-server-hardening/SKILL.md) | Reviews an MCP server against a 34-point checklist tied to the MCP spec (bind address, auth, Origin/DNS rebinding, token passthrough, path and URL limits, secrets, container) and probes the running server to prove it. | PaperMind's HTTP mode and auth |
| [`repro-before-fix`](skills/repro-before-fix/SKILL.md) | Debugs by turning a bug into a failing test first, then root cause, smallest fix, and a kept regression test. Covers flaky failures, environment diffs and `git bisect`; bundles a script that runs a command N times and classifies it as passing, failing or flaky. | Bugs fixed in PaperMind (dead pool connections, DNS rebinding) |
| [`release-polish`](skills/release-polish/SKILL.md) | Takes a repo from working to releasable: README order that leads with value and a tested quick start, license, changelog and semver, security and contributing docs, CI gate, tag and release notes. Bundles a read-only checker for missing files, changelog/tag mismatches, tracked secrets and large files. | Preparing PaperMind and other repos for v1.0.0 |

A skill is a folder with a `SKILL.md` (YAML frontmatter + instructions) and optional
`scripts/`, `references/` and `assets/`. Agents read only each skill's name and description at
startup and load the rest when a task matches, so the description has to say *when* to use it.

### Use a skill

Copy the folder into wherever your agent looks for skills, for example:

```bash
cp -r skills/retrieval-eval ~/.claude/skills/        # Claude Code (personal skills)
cp -r skills/retrieval-eval .agents/skills/          # project-level, for agents that read it
```

## The linter

```bash
pip install -e ".[dev]"
skillbench lint skills/
```

```
  ok  skills/retrieval-eval

1 skill(s), 0 error(s), 0 warning(s)
```

**Errors** break the [spec](https://agentskills.io/specification), so an agent may refuse to load
the skill. They match the reference validator (`skills-ref validate`): a conformance test runs
both on the same 18 cases and checks they agree.

| Code | Check |
|---|---|
| E100–E104 | `SKILL.md` exists, has frontmatter, valid YAML, no unknown fields |
| E110–E112 | `name`: present, ≤ 64 chars, lowercase/digits/hyphens, no leading, trailing or double hyphen, matches its folder |
| E120–E121 | `description`: present, ≤ 1024 chars |
| E130–E133 | `compatibility` ≤ 500 chars, `metadata` is a mapping, `license` and `allowed-tools` are strings |

**Warnings** are quality problems the spec allows but agents trip on:

| Code | Check |
|---|---|
| W201 / W202 | Body over 500 lines or ~5,000 tokens (it's loaded every time the skill runs) |
| W203 / W204 | Description doesn't say *when* to use the skill, or is too short to match on |
| W205 / W209 | A file mentioned in the body doesn't exist, or points outside the skill |
| W206 / W207 | Name uses a reserved word (`claude`, `anthropic`); description contains XML tags |
| W208 / W210 | Empty body; `metadata` values that aren't strings |

`--format json` for machine output, `--strict` to fail on warnings (used in CI).

## Trigger evals

A skill only helps if the agent loads it for the right requests and leaves it alone for the rest.
Agents decide from each skill's name and description alone, so that's what gets tested.

**Method.** [`evals/triggers.jsonl`](evals/triggers.jsonl) holds 52 requests: 10 per skill
(explicit, implicit and contextual phrasings, most never naming the skill) and 12 that should
load none of them (6 unrelated, 6 near misses such as "What does MRR stand for?"). For each
request, a model sees the same catalog an agent would: the 4 skills plus 8 realistic
[distractors](evals/distractors.jsonl) (including `mcp-builder`, a near neighbour of
`mcp-server-hardening`), shuffled per trial. It answers with the skills it would load, as JSON.

Metrics cover our skills only: per-skill precision and recall, accuracy (exactly the right set),
recall on requests that need a skill, and the false-trigger rate on requests that don't. Every
answer is saved in [`evals/runs/`](evals/runs/), so runs can be audited, and a run stopped by a
rate limit resumes where it left off.

```bash
skillbench triggers skills/                                        # offline keyword baseline
skillbench models --provider gemini                                # models your key can use
skillbench triggers skills/ --provider gemini --model MODEL_ID --trials 3
skillbench triggers skills/ --provider ollama --model qwen3:8b --trials 3
```

Gemini reads `GEMINI_API_KEY` from the environment or a git-ignored `.env`.

**Results** ([full write-up](evals/RESULTS.md))

| Router | Round 1 (52 cases × 3) | Hard set (38 cases × 3) | Hard-set false triggers | Median latency |
|---|---:|---:|---:|---:|
| Keyword overlap (offline baseline) | 73% | 37% | 46% | – |
| `gemini-3.5-flash-lite` | **100%** | **93%** | 13% | 0.6 s |

Round 1 hit a ceiling, so a [pre-registered](evals/PROTOCOL.md) hard set followed: multi-skill,
confusable, terse, non-English and long requests, plus cases where a distractor is the right
answer. Two of its three predictions were wrong. The real weak spot: `retrieval-eval` loads
for conceptual questions about metrics ("What's the difference between hit@1 and recall@5?"),
which accounts for every hard-set false trigger. A first description fix removed all of them but
cost one answer of recall on each of two skills, so the pre-registered rule rejected it
([experiment 1](evals/RESULTS.md#experiment-1-tell-retrieval-eval-when-not-to-load-rejected)).

## Outcome evals

Loading the right skill only matters if the answer gets better. Each skill has 2 tasks in
[`evals/outcomes/`](evals/outcomes/), written so the prompt never asks for what the skill adds
(the bug reports never mention tests). The same model answers each task with and without the
skill's instructions, and deterministic graders score the answers. The two debugging tasks are
graded by running the code: the answer's test must fail on the original bug and pass on its
fix, and the fix must pass hidden tests.

```bash
skillbench outcomes skills/ --provider gemini --model MODEL_ID --trials 3
skillbench grade evals/runs/RUN.jsonl      # re-grade saved answers, no API calls
```

**Results** for `gemini-3.5-flash-lite`, 3 trials ([full write-up](evals/RESULTS.md#outcome-evals)):

| Skill | Fully passed, without → with | Mean check score | Verdict |
|---|---:|---:|---|
| `repro-before-fix` | 0/6 → **6/6** | 40% → 100% | **helps** |
| `release-polish` | 1/6 → **5/6** | 51% → 96% | **helps** |
| `mcp-server-hardening` | 2/6 → 4/6 | 82% → 93% | no measured benefit |
| `retrieval-eval` | 0/6 → 0/6 | 37% → 63% | no measured benefit |

Verdicts follow a [rule fixed before the run](evals/PROTOCOL.md#rule-for-the-skill-helps): at
least 2 more full passes and no score drop on either task. Without `repro-before-fix` the model
fixed both bugs every time but never wrote a test; with it, every answer wrote a test that
fails on the bug. `mcp-server-hardening` fixed the server review (0/3 → 3/3) but scored slightly
lower on the container review, so it doesn't count. Two graders were fixed after the run; the
before and after numbers are [reported separately](evals/RESULTS.md#grader-fixes).

## Roadmap

- [x] Linter for the SKILL.md spec, with reference-validator conformance tests
- [x] Skill 1: `retrieval-eval`
- [x] Skill 2: `mcp-server-hardening`
- [x] Skill 3: `repro-before-fix`
- [x] Skill 4: `release-polish`
- [x] Trigger eval harness: 52 labeled requests, distractor skills, Gemini/Ollama/keyword routers, resumable runs
- [x] Trigger results: round 1 (ceiling) and a pre-registered hard set
- [x] Description fix measured against the hard set (experiment 1, rejected by the rule)
- [x] Outcome evals: the same tasks with and without the skill, scored by deterministic checks
- [x] CI: tests, ruff and `skillbench lint --strict` on every push and pull request
- [x] Results tables in this README
- [ ] v1.0.0

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check . && ruff format --check .
skillbench lint --strict skills/
```

## License

MIT
