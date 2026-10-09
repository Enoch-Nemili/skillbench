import json

from skillbench.cli import main

DESC = "Summarise a pull request into release notes. Use when the user asks for a changelog."


def write(tmp_path, name, frontmatter):
    folder = tmp_path / name
    folder.mkdir()
    (folder / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n# Steps\n", encoding="utf-8")
    return folder


def test_clean_skill_exits_zero(tmp_path, capsys):
    write(tmp_path, "notes", f"name: notes\ndescription: {DESC}")
    assert main(["lint", str(tmp_path)]) == 0
    assert "1 skill(s), 0 error(s), 0 warning(s)" in capsys.readouterr().out


def test_error_exits_one(tmp_path):
    write(tmp_path, "notes", f"name: wrong\ndescription: {DESC}")
    assert main(["lint", str(tmp_path)]) == 1


def test_warning_fails_only_with_strict(tmp_path):
    write(tmp_path, "notes", "name: notes\ndescription: Use when asked for notes.")
    assert main(["lint", str(tmp_path)]) == 0
    assert main(["lint", "--strict", str(tmp_path)]) == 1


def test_json_output(tmp_path, capsys):
    write(tmp_path, "notes", "name: notes")
    main(["lint", "--format", "json", str(tmp_path)])
    report = json.loads(capsys.readouterr().out)
    assert report["errors"] == 1
    assert report["findings"][0]["code"] == "E120"


def test_nothing_found(tmp_path):
    assert main(["lint", str(tmp_path)]) == 2
