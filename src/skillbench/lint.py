"""
Static checks for a skill folder.

Errors (E...) break the Agent Skills spec (the same rules as the reference validator,
`skills-ref validate`): a skills-compatible agent may refuse to load the
skill. Warnings (W...) are quality problems: the skill loads, but the agent may never pick it,
or it wastes context every time it does.

Spec: https://agentskills.io/specification
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from skillbench.skill import SKILL_FILE, Skill, SkillParseError, load_skill

NAME_MAX = 64
DESCRIPTION_MAX = 1024
COMPATIBILITY_MAX = 500
BODY_MAX_LINES = 500
BODY_MAX_TOKENS = 5000
DESCRIPTION_MIN = 50
CHARS_PER_TOKEN = 4  # rough rule of thumb for English text; good enough for a budget check

KNOWN_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
RESERVED_WORDS = ("anthropic", "claude")

# Phrases that tell the agent WHEN to use a skill, which is what it matches requests against.
_WHEN = re.compile(
    r"\b(use (it |this( skill)? )?(when|for|to|if|after|before|while)|when (the )?(user|you)|"
    r"whenever|triggers? (on|when))\b",
    re.IGNORECASE,
)
_XML_TAG = re.compile(r"<[A-Za-z/][^>]*>")
# Relative file mentions in the body: Markdown links and `scripts/...`-style code spans.
_LINK = re.compile(r"\]\(([^)\s#]+)(?:#[^)]*)?\)")
_RESOURCE = re.compile(r"`((?:scripts|references|assets)/[^`\s]+)`")


@dataclass(frozen=True)
class Finding:
    code: str
    message: str
    path: Path
    line: int | None = None

    @property
    def severity(self) -> str:
        return "error" if self.code.startswith("E") else "warning"

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "path": str(self.path),
            "line": self.line,
        }


def lint_skill(directory: str | Path) -> list[Finding]:
    directory = Path(directory)
    skill_file = directory / SKILL_FILE
    if not skill_file.is_file():
        return [Finding("E100", f"no {SKILL_FILE} in this folder", directory)]
    try:
        skill = load_skill(directory)
    except SkillParseError as exc:
        return [Finding(exc.code, str(exc), skill_file, 1)]
    except UnicodeDecodeError:
        return [Finding("E103", "SKILL.md is not valid UTF-8", skill_file)]

    findings: list[Finding] = []
    for check in (_check_name, _check_description, _check_optional_fields, _check_body):
        findings.extend(check(skill))
    return findings


def _check_name(skill: Skill) -> list[Finding]:
    f = skill.skill_file
    name = skill.frontmatter.get("name")
    if name is None:
        return [Finding("E110", "frontmatter is missing 'name'", f)]
    if not isinstance(name, str) or not name:
        return [Finding("E111", "'name' must be a non-empty string", f)]
    out = []
    if len(name) > NAME_MAX:
        out.append(Finding("E111", f"'name' is {len(name)} chars (max {NAME_MAX})", f))
    name = unicodedata.normalize("NFKC", name)
    if name != name.lower() or not all(c.isalnum() or c == "-" for c in name):
        out.append(
            Finding(
                "E111", f"'name' {name!r} may only use lowercase letters, digits and hyphens", f
            )
        )
    if name.startswith("-") or name.endswith("-") or "--" in name:
        out.append(
            Finding("E111", f"'name' {name!r} can't start or end with '-' or contain '--'", f)
        )
    folder = unicodedata.normalize("NFKC", skill.directory.resolve().name)
    if name != folder:
        out.append(Finding("E112", f"'name' {name!r} must match its folder name {folder!r}", f))
    if any(word in name for word in RESERVED_WORDS):
        out.append(
            Finding(
                "W206",
                f"'name' contains a reserved word ({', '.join(RESERVED_WORDS)}); "
                "Claude's platforms reject it",
                f,
            )
        )
    return out


def _check_description(skill: Skill) -> list[Finding]:
    f = skill.skill_file
    desc = skill.frontmatter.get("description")
    if desc is None:
        return [Finding("E120", "frontmatter is missing 'description'", f)]
    if not isinstance(desc, str) or not desc.strip():
        return [Finding("E120", "'description' must be a non-empty string", f)]
    out = []
    if len(desc) > DESCRIPTION_MAX:
        out.append(
            Finding("E121", f"'description' is {len(desc)} chars (max {DESCRIPTION_MAX})", f)
        )
    if len(desc.strip()) < DESCRIPTION_MIN:
        out.append(
            Finding(
                "W204",
                f"'description' is only {len(desc.strip())} chars; agents pick skills "
                "from this text alone, so say what it does and when to use it",
                f,
            )
        )
    if not _WHEN.search(desc):
        out.append(
            Finding(
                "W203",
                "'description' doesn't say when to use the skill "
                "(e.g. 'Use when the user asks to ...')",
                f,
            )
        )
    if _XML_TAG.search(desc):
        out.append(Finding("W207", "'description' contains XML/HTML tags", f))
    return out


def _check_optional_fields(skill: Skill) -> list[Finding]:
    f = skill.skill_file
    fm = skill.frontmatter
    out = []
    for key in sorted(set(fm) - KNOWN_FIELDS):
        out.append(
            Finding(
                "E104", f"unknown frontmatter field {key!r} (put custom data under 'metadata')", f
            )
        )
    if "license" in fm and not isinstance(fm["license"], str):
        out.append(Finding("E132", "'license' must be a string", f))
    if "compatibility" in fm:
        value = fm["compatibility"]
        if not isinstance(value, str) or not value.strip():
            out.append(Finding("E130", "'compatibility' must be a non-empty string", f))
        elif len(value) > COMPATIBILITY_MAX:
            out.append(
                Finding(
                    "E130", f"'compatibility' is {len(value)} chars (max {COMPATIBILITY_MAX})", f
                )
            )
    if "metadata" in fm:
        value = fm["metadata"]
        if not isinstance(value, dict):
            out.append(Finding("E131", "'metadata' must be a mapping of keys to values", f))
        elif not all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
            out.append(
                Finding(
                    "W210",
                    "'metadata' values should be strings; quote numbers and booleans "
                    '(version: "1.0") so every YAML loader reads them the same way',
                    f,
                )
            )
    if "allowed-tools" in fm and not isinstance(fm["allowed-tools"], str):
        out.append(Finding("E133", "'allowed-tools' must be a space-separated string", f))
    return out


def _check_body(skill: Skill) -> list[Finding]:
    f = skill.skill_file
    body = skill.body
    if not body.strip():
        return [Finding("W208", "SKILL.md has no instructions after the frontmatter", f)]
    out = []
    lines = body.count("\n") + (0 if body.endswith("\n") else 1)
    if lines > BODY_MAX_LINES:
        out.append(
            Finding(
                "W201",
                f"body is {lines} lines (keep under {BODY_MAX_LINES}; move detail into "
                "references/ so it loads only when needed)",
                f,
            )
        )
    tokens = len(body) // CHARS_PER_TOKEN
    if tokens > BODY_MAX_TOKENS:
        out.append(
            Finding(
                "W202",
                f"body is ~{tokens} tokens (keep under {BODY_MAX_TOKENS}); it is loaded "
                "into context every time the skill runs",
                f,
            )
        )
    out.extend(_check_references(skill))
    return out


def _check_references(skill: Skill) -> list[Finding]:
    out = []
    root = skill.directory.resolve()
    for offset, line in enumerate(skill.body.splitlines()):
        targets = _LINK.findall(line) + _RESOURCE.findall(line)
        for target in dict.fromkeys(targets):  # unique, in order
            if "://" in target or target.startswith(("mailto:", "/")):
                continue
            resolved = (root / target).resolve()
            line_no = skill.body_start_line + offset
            if not resolved.is_relative_to(root):
                out.append(
                    Finding(
                        "W209",
                        f"reference {target!r} points outside the skill folder",
                        skill.skill_file,
                        line_no,
                    )
                )
            elif not resolved.exists():
                out.append(
                    Finding(
                        "W205",
                        f"referenced file {target!r} does not exist",
                        skill.skill_file,
                        line_no,
                    )
                )
    return out
