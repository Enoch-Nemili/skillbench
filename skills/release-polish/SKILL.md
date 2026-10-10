---
name: release-polish
description: Get a code repository ready for a public release or a tagged version - README that leads with what it does and how to run it, license, changelog and semantic version, security and contributing docs, CI and dependency updates, no tracked secrets, then a tag and release notes. Use when the user wants to publish, release, tag or open-source a repo, cut a version, write a changelog or release notes, or make a GitHub project look professional.
license: MIT
compatibility: The check script needs Python 3.11+ and git. Release commands use the GitHub CLI (gh); other hosts work the same way by hand.
metadata:
  author: Enoch Nemili
  version: "0.1.0"
  origin: Distilled from preparing PaperMind and other repos for v1.0.0
---

# Release polish

A reviewer decides in under a minute whether a repo is worth their time, from the README
and the front page alone. Release polish makes that minute count and makes the release
itself reproducible.

## Workflow

1. **Run the check first** to see where the repo stands:

   ```bash
   python scripts/release_check.py path/to/repo --version 1.0.0
   ```

   Fix every FAIL. Treat each WARN as a decision: fix it or know why not.

2. **Remove anything that must not ship.** Secrets in tracked files are a FAIL; rotate any
   key that was ever committed, even if it was deleted later, because it lives on in git
   history. Move config to environment variables, add a `.env.example` with placeholder
   values, and git-ignore `.env`. Remove generated files, large data and personal notes.

3. **Rewrite the README top-down** (see `references/readme.md`):
   name and one-line value, badges, a demo or result, quick start that works when pasted,
   usage, how it works, results with how they were measured, configuration, tests,
   project structure, roadmap, license. Every command in it must have been run.

4. **Add the project files** that answer a visitor's next questions: `LICENSE`,
   `CHANGELOG.md` (from `assets/CHANGELOG.md`), `SECURITY.md` (how to report a problem,
   the threat model), `CONTRIBUTING.md` (set up, test, open a PR), issue and PR templates,
   and Dependabot for dependencies and CI actions.

5. **Make CI the gate.** Lint, tests and a build run on every pull request and on main,
   with a status badge in the README. A release is cut only from a green main.

6. **Pick the version** with semantic versioning: breaking change → major, new feature →
   minor, fix → patch. Use `0.y.z` while the interface may still change; `1.0.0` means you
   will keep it stable. Write the CHANGELOG entry under that version, grouped into Added,
   Changed, Fixed, Security, linking issues and PRs.

7. **Tag and release from main** once the check passes:

   ```bash
   git switch main && git pull
   python scripts/release_check.py . --version 1.0.0
   gh release create v1.0.0 --title "v1.0.0: <headline>" --notes-file notes.md
   ```

   Write `notes.md` from `assets/release-notes.md`: a one-paragraph summary, highlights
   with numbers, upgrade notes, and a link to the full changelog.

8. **Finish the front page:** repository description, topics, website link, and a social
   preview image (1280×640) so shared links look intentional.

## Guardrails

- Don't claim what you haven't measured. Every number in the README or release notes
  needs a command that reproduces it.
- Check commit authorship before a public release (`release_check.py` lists every identity).
  Rewriting published history needs a force-push and breaks clones; do it before the
  first release, not after.
- Never delete a published tag or release to "fix" it; release a new patch version.
- Keep the README honest about status and limitations. A short "Limitations" or
  "Known issues" section earns more trust than it costs.
