"""A repo snapshot with planted release blockers. Graded on which blockers the answer catches."""

from skillbench.grading import Check, check_mentions, mentions

SKILL = "release-polish"

SNAPSHOT = """\
$ git ls-files
.env
CHANGELOG.md
README.md
pyproject.toml
src/fetchkit/__init__.py
src/fetchkit/client.py
tests/test_client.py

$ git tag
v1.0.0
v1.1.0

$ cat .env
FETCHKIT_API_KEY=example-live-key-do-not-share

$ grep version pyproject.toml
version = "1.2.0"

$ head -5 CHANGELOG.md
# Changelog

## [1.1.0] - 2026-08-02
### Added
- Retries with exponential backoff

$ cat README.md
# fetchkit

A tiny HTTP client.
"""

PROMPT = f"""
We want to publish fetchkit v1.2.0 on GitHub and PyPI today. Here's a snapshot of the repo.
What do we need to do?

```text
{SNAPSHOT}```
"""


def grade(output: str):
    return [
        Check(
            "env_secret_rotated",
            mentions(output, r"\.env") and mentions(output, r"rotat|revok|regenerat|invalidat"),
            ".env flagged and key rotated" if mentions(output, r"rotat|revok") else "no rotation",
        ),
        check_mentions(
            "history_cleaned",
            output,
            r"git history|filter-repo|\bbfg\b|rewrit\w* (the )?history|lives on in|still in (the )?history",
        ),
        check_mentions("license_added", output, r"licen[cs]e"),
        check_mentions(
            "changelog_entry",
            output,
            r"changelog[^\n]{0,120}1\.2\.0|1\.2\.0[^\n]{0,120}changelog|##\s*\[?1\.2\.0",
        ),
        check_mentions(
            "readme_quickstart",
            output,
            r"readme[^\n]{0,160}(install|usage|quick ?start|example)"
            r"|(install|usage|quick ?start)[^\n]{0,160}readme",
        ),
        check_mentions("ci_gate", output, r"\bci\b|github actions|workflow|continuous integration"),
    ]
