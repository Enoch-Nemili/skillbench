# skillbench

[![CI](https://github.com/Enoch-Nemili/skillbench/actions/workflows/ci.yml/badge.svg)](https://github.com/Enoch-Nemili/skillbench/actions/workflows/ci.yml)

**Agent Skills that come with evidence.**

A small pack of [Agent Skills](https://agentskills.io) for AI-infrastructure work, plus the
harness that checks them: a linter that enforces the open SKILL.md spec today, and trigger and
outcome evals (does the agent pick the skill, and does the work get better with it?) on the way.

Each skill is distilled from a project that was built and measured first. `retrieval-eval`, for
example, is the method used to tune [PaperMind](https://github.com/Enoch-Nemili/papermind)'s
hybrid search.

> **Status:** v0.1: linter and first skills. Evals are being built next; see the roadmap.

## Skills

| Skill | What it does | Comes from |
|---|---|---|
| [`retrieval-eval`](skills/retrieval-eval/SKILL.md) | Scores a RAG/search system with hit@1, recall@k and MRR and picks between configurations using a decision rule fixed before the run. Bundles a stdlib scoring/compare script. | PaperMind hybrid search |
| [`mcp-server-hardening`](skills/mcp-server-hardening/SKILL.md) | Reviews an MCP server against a 34-point checklist tied to the MCP spec (bind address, auth, Origin/DNS rebinding, token passthrough, path and URL limits, secrets, container) and probes the running server to prove it. | PaperMind's HTTP mode and auth |

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

## Roadmap

- [x] Linter for the SKILL.md spec, with reference-validator conformance tests
- [x] Skill 1: `retrieval-eval`
- [x] Skill 2: `mcp-server-hardening`
- [ ] Skills 3–4: reproduce-before-fix debugging, release polish
- [ ] Trigger evals: should-trigger / shouldn't-trigger prompts per skill → precision and recall
- [ ] Outcome evals: the same tasks with and without the skill, scored by deterministic checks
- [x] CI: tests, ruff and `skillbench lint --strict` on every push and pull request
- [ ] Results table in this README, v1.0.0

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
