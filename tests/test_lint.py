from pathlib import Path

import pytest

from skillbench.lint import lint_skill
from skillbench.skill import SkillParseError, discover, parse_skill_md

GOOD_DESC = "Summarise a pull request into release notes. Use when the user asks for a changelog."
REPO_SKILLS = Path(__file__).resolve().parents[1] / "skills"


def make_skill(root: Path, name: str, frontmatter: str, body: str = "# Do the thing\n") -> Path:
    folder = root / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n{body}", encoding="utf-8")
    return folder


def codes(folder: Path) -> list[str]:
    return [f.code for f in lint_skill(folder)]


# --- parsing -------------------------------------------------------------------------------


def test_parse_splits_frontmatter_and_body():
    fm, body, start = parse_skill_md("---\nname: a\ndescription: b\n---\nHello\n")
    assert fm == {"name": "a", "description": "b"}
    assert body == "Hello\n"
    assert start == 5


def test_parse_rejects_missing_frontmatter():
    with pytest.raises(SkillParseError) as exc:
        parse_skill_md("# just markdown\n")
    assert exc.value.code == "E101"


def test_parse_rejects_bad_yaml():
    with pytest.raises(SkillParseError) as exc:
        parse_skill_md("---\nname: [unclosed\n---\nbody\n")
    assert exc.value.code == "E102"


def test_parse_tolerates_bom_and_crlf():
    fm, body, _ = parse_skill_md("﻿---\r\nname: a\r\n---\r\nbody\r\n")
    assert fm == {"name": "a"}
    assert body == "body\r\n"


# --- a clean skill ---------------------------------------------------------------------------


def test_clean_skill_has_no_findings(tmp_path):
    folder = make_skill(tmp_path, "release-notes", f"name: release-notes\ndescription: {GOOD_DESC}")
    assert lint_skill(folder) == []


def test_repo_skills_are_clean():
    skills = discover([REPO_SKILLS])
    assert skills, "expected at least one skill in skills/"
    for folder in skills:
        assert lint_skill(folder) == [], folder


# --- name ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad", ["Release-Notes", "-release", "release-", "release--notes", "release_notes", "a" * 65]
)
def test_invalid_names(tmp_path, bad):
    folder = make_skill(tmp_path, bad, f"name: {bad}\ndescription: {GOOD_DESC}")
    assert "E111" in codes(folder)


def test_unicode_lowercase_name_is_allowed(tmp_path):
    folder = make_skill(tmp_path, "résumé-review", f"name: résumé-review\ndescription: {GOOD_DESC}")
    assert lint_skill(folder) == []


def test_name_must_match_folder(tmp_path):
    folder = make_skill(tmp_path, "release-notes", f"name: changelog\ndescription: {GOOD_DESC}")
    assert codes(folder) == ["E112"]


def test_missing_name(tmp_path):
    folder = make_skill(tmp_path, "x", f"description: {GOOD_DESC}")
    assert "E110" in codes(folder)


def test_reserved_word_in_name(tmp_path):
    folder = make_skill(tmp_path, "claude-helper", f"name: claude-helper\ndescription: {GOOD_DESC}")
    assert codes(folder) == ["W206"]


# --- description -----------------------------------------------------------------------------


def test_missing_description(tmp_path):
    folder = make_skill(tmp_path, "x", "name: x")
    assert codes(folder) == ["E120"]


def test_description_too_long(tmp_path):
    long_desc = "Use when the user asks. " + "x" * 1100
    folder = make_skill(tmp_path, "x", f"name: x\ndescription: {long_desc}")
    assert "E121" in codes(folder)


def test_description_without_when(tmp_path):
    desc = "Generates release notes from merged pull requests and commit messages in a repo."
    folder = make_skill(tmp_path, "x", f"name: x\ndescription: {desc}")
    assert codes(folder) == ["W203"]


def test_short_description(tmp_path):
    folder = make_skill(tmp_path, "x", "name: x\ndescription: Use when asked.")
    assert codes(folder) == ["W204"]


# --- optional fields -------------------------------------------------------------------------


def test_metadata_values_must_be_strings(tmp_path):
    folder = make_skill(
        tmp_path, "x", f"name: x\ndescription: {GOOD_DESC}\nmetadata:\n  version: 1.0"
    )
    assert codes(folder) == ["W210"]


def test_metadata_must_be_a_mapping(tmp_path):
    folder = make_skill(tmp_path, "x", f"name: x\ndescription: {GOOD_DESC}\nmetadata: v1")
    assert codes(folder) == ["E131"]


def test_unknown_field_is_an_error(tmp_path):
    folder = make_skill(tmp_path, "x", f"name: x\ndescription: {GOOD_DESC}\nauthor: me")
    assert codes(folder) == ["E104"]


def test_compatibility_too_long(tmp_path):
    folder = make_skill(
        tmp_path, "x", f"name: x\ndescription: {GOOD_DESC}\ncompatibility: {'y' * 501}"
    )
    assert codes(folder) == ["E130"]


# --- body ------------------------------------------------------------------------------------


def test_empty_body(tmp_path):
    folder = make_skill(tmp_path, "x", f"name: x\ndescription: {GOOD_DESC}", body="\n")
    assert codes(folder) == ["W208"]


def test_long_body(tmp_path):
    folder = make_skill(tmp_path, "x", f"name: x\ndescription: {GOOD_DESC}", body="line\n" * 501)
    assert codes(folder) == ["W201"]


def test_missing_reference_reports_line(tmp_path):
    body = "Intro\n\nRun `scripts/run.py` then read [guide](references/guide.md#setup).\n"
    folder = make_skill(tmp_path, "x", f"name: x\ndescription: {GOOD_DESC}", body=body)
    findings = lint_skill(folder)
    assert [f.code for f in findings] == ["W205", "W205"]
    assert {f.line for f in findings} == {7}


def test_existing_reference_and_urls_are_fine(tmp_path):
    body = "See [spec](https://agentskills.io) and `scripts/run.py`.\n"
    folder = make_skill(tmp_path, "x", f"name: x\ndescription: {GOOD_DESC}", body=body)
    (folder / "scripts").mkdir()
    (folder / "scripts" / "run.py").write_text("print(1)\n")
    assert lint_skill(folder) == []


def test_reference_outside_skill(tmp_path):
    body = "See [notes](../other/notes.md).\n"
    folder = make_skill(tmp_path, "x", f"name: x\ndescription: {GOOD_DESC}", body=body)
    assert codes(folder) == ["W209"]


# --- discovery -------------------------------------------------------------------------------


def test_discover_finds_nested_skills(tmp_path):
    make_skill(tmp_path / "pack", "a", "name: a\ndescription: d")
    make_skill(tmp_path / "pack", "b", "name: b\ndescription: d")
    found = discover([tmp_path / "pack", tmp_path / "pack" / "a"])
    assert [p.name for p in found] == ["a", "b"]


def test_no_skill_file(tmp_path):
    (tmp_path / "empty").mkdir()
    assert codes(tmp_path / "empty") == ["E100"]
