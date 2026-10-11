"""A version-number question with a breaking change hidden in a mixed release."""

import re

from skillbench.grading import Check, check_mentions

SKILL = "release-polish"

PROMPT = """
fetchkit is at 1.4.2. In this release we renamed the public function `load()` to `read()` (`load`
no longer exists), added a `timeout` argument to `read()`, and fixed a crash on empty responses.
What version should this be? Please also write the CHANGELOG entry.
"""

_SECTIONS = re.compile(
    r"^#{2,4}\s*(Added|Changed|Removed|Fixed|Deprecated|Security)\b", re.M | re.I
)


def grade(output: str):
    sections = {m.lower() for m in _SECTIONS.findall(output)}
    return [
        check_mentions("major_version", output, r"\b2\.0\.0\b"),
        Check("changelog_sections", len(sections) >= 2, ", ".join(sorted(sections)) or "none"),
        check_mentions(
            "breaking_called_out",
            output,
            r"breaking|migrat\w+|upgrad\w+ (note|guide|instructions)|replace `?load",
        ),
        check_mentions(
            "dated_heading", output, r"##\s*\[?2\.0\.0\]?\s*[-–—]\s*(\d{4}-\d{2}-\d{2}|YYYY-MM-DD)"
        ),
    ]
