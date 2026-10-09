"""
Load an Agent Skill from disk.

A skill is a folder with a SKILL.md file. SKILL.md starts with YAML frontmatter between two
`---` lines (name, description, ...) followed by Markdown instructions (the "body"):

    my-skill/
      SKILL.md          <- required
      scripts/          <- optional: code the agent can run
      references/       <- optional: docs the agent reads only when needed
      assets/           <- optional: templates, data files

Spec: https://agentskills.io/specification
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

SKILL_FILE = "SKILL.md"

# Frontmatter = everything between the opening `---` and the next line that is only `---`.
_FRONTMATTER = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)


class SkillParseError(ValueError):
    """SKILL.md exists but can't be split into frontmatter + body."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass
class Skill:
    directory: Path
    frontmatter: dict
    body: str
    body_start_line: int  # 1-based line in SKILL.md where the body begins

    @property
    def name(self) -> str | None:
        value = self.frontmatter.get("name")
        return value if isinstance(value, str) else None

    @property
    def description(self) -> str | None:
        value = self.frontmatter.get("description")
        return value if isinstance(value, str) else None

    @property
    def skill_file(self) -> Path:
        return self.directory / SKILL_FILE


def parse_skill_md(text: str) -> tuple[dict, str, int]:
    """Split SKILL.md text into (frontmatter dict, body, body start line)."""
    text = text.removeprefix("﻿")  # tolerate a UTF-8 BOM
    match = _FRONTMATTER.match(text)
    if not match:
        raise SkillParseError(
            "E101", "SKILL.md must start with YAML frontmatter between two '---' lines"
        )
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise SkillParseError("E102", f"frontmatter is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise SkillParseError("E102", "frontmatter must be a YAML mapping (key: value pairs)")
    body = text[match.end() :]
    body_start_line = text[: match.end()].count("\n") + 1
    return data, body, body_start_line


def load_skill(directory: str | Path) -> Skill:
    directory = Path(directory)
    text = (directory / SKILL_FILE).read_text(encoding="utf-8")
    frontmatter, body, start = parse_skill_md(text)
    return Skill(directory=directory, frontmatter=frontmatter, body=body, body_start_line=start)


def discover(paths: list[str | Path]) -> list[Path]:
    """Find skill folders. Each path may be a skill folder or a folder containing skills."""
    found: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_file() and path.name == SKILL_FILE:
            path = path.parent
        if (path / SKILL_FILE).is_file():
            found.append(path)
        elif path.is_dir():
            found.extend(sorted(p.parent for p in path.rglob(SKILL_FILE)))
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in found:
        if path.resolve() not in seen:
            seen.add(path.resolve())
            unique.append(path)
    return unique
