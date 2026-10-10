# Writing a README that gets read

Read this when writing or restructuring a README for a release.

## Order

Visitors read top-down and stop early. Put what decides "is this worth my time?" first.

| Section | What it answers | Notes |
|---|---|---|
| Name + one line | What is it? | Say what it does for whom, not what it's built with. "Search your research papers from any AI assistant", not "A FastAPI + pgvector app". |
| Badges | Is it maintained and working? | CI status, release, license. Three or four; more is noise. |
| Demo or headline result | Does it work? | A GIF, screenshot or one measured number (e.g. "97% recall@5 on 36 labeled questions"). |
| Quick start | Can I run it in two minutes? | Copy-pasteable commands from a clean machine. Test them in a fresh clone. |
| Usage | How do I use it day to day? | The 3–5 most common tasks with real examples and real output. |
| How it works | Should I trust the design? | A short architecture diagram or paragraph; link deeper docs. |
| Results / evaluation | How good is it, measured how? | Table with the method, data size and the command that reproduces it. |
| Configuration | What can I change? | Table: variable, default, purpose. |
| Security | What can go wrong? | Threat model and controls, or a link to SECURITY.md. |
| Tests | How do I know a change didn't break it? | The command, and what is and isn't covered. |
| Project structure | Where is what? | A short annotated tree. |
| Roadmap / known issues | What's missing? | Link open issues. Honesty here builds trust. |
| Contributing, license, contact | How do I get involved? | One line each, linking the full files. |

## Style

- Lead with outcomes and numbers, not adjectives. "Cuts p95 latency from 820 ms to 140 ms"
  beats "blazing fast".
- One idea per paragraph, short sentences, code blocks for anything typed.
- Show real output under commands so readers know what success looks like.
- Use relative links for files in the repo so they work on forks and branches.
- Keep images under `docs/` and give them alt text.
- Don't document what the code doesn't do yet; put it in the roadmap.

## Before publishing

- Clone the repo into a temporary folder and follow the README exactly. Fix every step
  that needed knowledge you didn't write down.
- Check every link (`lychee` or the GitHub preview).
- Read it on a phone: wide tables and long lines are the usual problems.
