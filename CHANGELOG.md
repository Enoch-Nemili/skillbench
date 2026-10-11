# Changelog

All notable changes to this project. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.0.0] - 2026-10-11

First stable release: four Agent Skills for AI-infrastructure work, and the harness that
measures them (a spec linter, trigger evals and outcome evals) with pre-registered results.

### Added
- `skillbench lint`: checks SKILL.md folders against the Agent Skills spec. Its errors agree
  with the reference validator (`skills-ref`) on 18 conformance cases; warnings W201–W210 catch
  quality problems the spec allows. `--strict` and `--format json`.
- Skills: `retrieval-eval`, `mcp-server-hardening` (#4), `repro-before-fix` (#6) and
  `release-polish` (#8), each with a bundled script, references and assets.
- `skillbench triggers`: does a model load the right skill? Gemini, Ollama and an offline
  keyword baseline, 8 distractor skills, resumable runs (#10). `gemini-3.5-flash-lite` scored
  100% on 52 cases and 93% on a pre-registered hard set; the keyword baseline scored 73% and
  37% (#11, #15, #16).
- Description experiment 1, rejected by its pre-registered rule and reported anyway (#17).
- `skillbench outcomes`: the same model with and without each skill, scored by deterministic
  graders; the debugging tasks are graded by running the code (#19). `repro-before-fix` went
  from 0/6 to 6/6 full passes and `release-polish` from 1/6 to 5/6; the other two skills show
  no measured benefit under the rule (#22).
- `skillbench grade`: re-grades a saved outcome run with no API calls (#22).
- CI: tests on Python 3.11 and 3.14, ruff and `skillbench lint --strict` on every pull
  request (#2).

### Fixed
- A slow Gemini reply raised a bare timeout and ended the run; it is now retried (#12).
- Reported latency included the rate limiter's wait (#13).
- Outcome answers were forced into JSON, invalidating the first outcome run (#20).
- Graders missed code files the model wrote without the requested fence layout (#22).

[Unreleased]: https://github.com/Enoch-Nemili/skillbench/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Enoch-Nemili/skillbench/releases/tag/v1.0.0
