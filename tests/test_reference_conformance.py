"""
skillbench's errors should agree with the reference validator from the Agent Skills project
(`pip install skills-ref`). Skipped when it isn't installed.
"""

import pytest

from skillbench.lint import lint_skill

skills_ref = pytest.importorskip("skills_ref")

DESC = "Summarise a pull request into release notes. Use when the user asks for a changelog."

# (folder name, frontmatter, valid per spec?)
CASES = [
    ("release-notes", f"name: release-notes\ndescription: {DESC}", True),
    ("pdf2", f"name: pdf2\ndescription: {DESC}\nlicense: MIT", True),
    ("x", f"name: x\ndescription: {DESC}\ncompatibility: Needs git", True),
    ("x", f"name: x\ndescription: {DESC}\nmetadata:\n  author: me", True),
    ("x", f"name: x\ndescription: {DESC}\nallowed-tools: Bash(git:*) Read", True),
    ("résumé", f"name: résumé\ndescription: {DESC}", True),
    ("Release", f"name: Release\ndescription: {DESC}", False),
    ("-x", f"name: -x\ndescription: {DESC}", False),
    ("x-", f"name: x-\ndescription: {DESC}", False),
    ("a--b", f"name: a--b\ndescription: {DESC}", False),
    ("a_b", f"name: a_b\ndescription: {DESC}", False),
    ("a" * 65, f"name: {'a' * 65}\ndescription: {DESC}", False),
    ("folder", f"name: other\ndescription: {DESC}", False),
    ("x", "name: x", False),
    ("x", f"description: {DESC}", False),
    ("x", f"name: x\ndescription: {'d' * 1025}", False),
    ("x", f"name: x\ndescription: {DESC}\ncompatibility: {'c' * 501}", False),
    ("x", f"name: x\ndescription: {DESC}\nauthor: me", False),
]


@pytest.mark.parametrize(("folder", "frontmatter", "valid"), CASES)
def test_agrees_with_reference_validator(tmp_path, folder, frontmatter, valid):
    skill = tmp_path / folder
    skill.mkdir()
    (skill / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n# Steps\n", encoding="utf-8")

    reference_errors = skills_ref.validate(skill)
    our_errors = [f for f in lint_skill(skill) if f.severity == "error"]

    assert (not reference_errors) == valid, reference_errors
    assert (not our_errors) == valid, our_errors
