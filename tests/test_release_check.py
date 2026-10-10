"""Tests for the release-readiness script bundled with the release-polish skill."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/release-polish/scripts/release_check.py"
spec = importlib.util.spec_from_file_location("release_check", SCRIPT)
rc = importlib.util.module_from_spec(spec)
sys.modules["release_check"] = rc
spec.loader.exec_module(rc)

GIT_ENV = {
    "GIT_AUTHOR_NAME": "Test Author",
    "GIT_AUTHOR_EMAIL": "author@example.com",
    "GIT_COMMITTER_NAME": "Test Author",
    "GIT_COMMITTER_EMAIL": "author@example.com",
}
README = """# demo

[![CI](https://github.com/o/r/actions/workflows/ci.yml/badge.svg)](https://github.com/o/r)

## Quick start

pip install demo

## Usage

demo run
"""


def sh(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A release-ready repo with one commit."""
    for key, value in GIT_ENV.items():
        monkeypatch.setenv(key, value)
    files = {
        "README.md": README,
        "LICENSE": "MIT",
        ".gitignore": ".env\n",
        "CHANGELOG.md": "# Changelog\n\n## [1.0.0] - 2026-10-10\n",
        "SECURITY.md": "report to me",
        "CONTRIBUTING.md": "open a PR",
        "pyproject.toml": '[project]\nname = "demo"\nversion = "1.0.0"\n',
        ".env.example": "DATABASE_URL=postgresql://user:password@localhost/db\n",
        ".github/workflows/ci.yml": "name: CI\n",
        ".github/dependabot.yml": "version: 2\n",
        ".github/ISSUE_TEMPLATE/bug.yml": "name: Bug\n",
        ".github/pull_request_template.md": "## What\n",
    }
    for rel, text in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    sh(tmp_path, "init", "-q", "-b", "main")
    sh(tmp_path, "add", ".")
    sh(tmp_path, "commit", "-q", "-m", "init")
    return tmp_path


def commit(repo, rel, text):
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    sh(repo, "add", "-f", rel)
    sh(repo, "commit", "-q", "-m", f"add {rel}")


def statuses(repo, version=None):
    return {c.name: c.status for c in rc.run_checks(repo, version)}


def test_ready_repo_has_no_fail_or_warn(repo):
    result = statuses(repo)
    assert "FAIL" not in result.values()
    assert "WARN" not in result.values()
    assert result["changelog-entry"] == "PASS"


def test_missing_required_and_recommended_files(repo):
    sh(repo, "rm", "-q", "LICENSE", "SECURITY.md")
    sh(repo, "commit", "-q", "-m", "remove")
    result = statuses(repo)
    assert result["license"] == "FAIL"
    assert result["security-policy"] == "WARN"


def test_version_without_changelog_entry_fails(repo):
    assert statuses(repo, "1.1.0")["changelog-entry"] == "FAIL"


def test_reusing_a_released_version_fails(repo):
    sh(repo, "tag", "v1.0.0")
    assert statuses(repo, "1.0.0")["tag-free"] == "FAIL"


def test_auditing_an_already_released_repo_is_not_a_failure(repo):
    sh(repo, "tag", "v1.0.0")
    checks = {c.name: c for c in rc.run_checks(repo)}
    assert checks["tag-free"].status == "INFO"
    assert "already released as v1.0.0" in checks["version"].detail


def test_tracked_env_file_fails(repo):
    commit(repo, ".env", "TOKEN=abc\n")
    assert statuses(repo)["secret-files"] == "FAIL"


def test_token_patterns_fail(repo):
    fake_aws = "AKIA" + "ABCDEFGHIJKLMNOP"  # built at runtime so this file holds no key
    fake_github = "ghp_" + "a" * 36
    commit(repo, "config.py", f'KEY = "{fake_aws}"\nGH = "{fake_github}"\n')
    checks = {c.name: c for c in rc.run_checks(repo)}
    assert checks["secrets-in-files"].status == "FAIL"
    assert "AWS access key" in checks["secrets-in-files"].detail
    assert "GitHub token" in checks["secrets-in-files"].detail


def test_new_google_key_format_fails(repo):
    fake = "AQ." + "Ab8" + "x" * 45  # built at runtime so this file holds no key
    commit(repo, "settings.py", f'GEMINI = "{fake}"\n')
    checks = {c.name: c for c in rc.run_checks(repo)}
    assert "Google auth key" in checks["secrets-in-files"].detail


def test_database_url_with_real_password_warns(repo):
    commit(repo, "settings.py", 'URL = "postgresql://app:Xk92hd!s@db.example.com/prod"\n')
    assert statuses(repo)["database-urls"] == "WARN"


def test_placeholder_database_url_is_fine(repo):
    assert "database-urls" not in statuses(repo)


def test_comments_inside_code_blocks_are_not_headings(repo):
    commit(repo, "README.md", "# demo\n\n```bash\n# Install it\npip install demo\n```\n")
    assert statuses(repo)["readme-install"] == "WARN"


@pytest.mark.parametrize("heading", ["## Quickstart", "### Serve it over HTTP", "## Setup"])
def test_common_quick_start_headings(repo, heading):
    commit(repo, "README.md", f"# demo\n\n{heading}\n\nsteps\n")
    assert statuses(repo)["readme-install"] == "PASS"


def test_readme_without_sections_or_badge_warns(repo):
    commit(repo, "README.md", "# demo\n\nIt does things.\n")
    result = statuses(repo)
    assert result["readme-install"] == result["readme-usage"] == result["readme-badge"] == "WARN"


def test_dirty_tree_warns(repo):
    (repo / "README.md").write_text(README + "\nmore\n")
    assert statuses(repo)["clean-tree"] == "WARN"


def test_authors_are_listed(repo):
    checks = {c.name: c for c in rc.run_checks(repo)}
    assert "Test Author <author@example.com>" in checks["authors"].detail


def test_main_exit_codes(repo, tmp_path_factory, capsys):
    assert rc.main([str(repo)]) == 0
    commit(repo, ".env", "X=1\n")
    assert rc.main([str(repo)]) == 1
    not_a_repo = tmp_path_factory.mktemp("plain")
    assert rc.main([str(not_a_repo)]) == 2
