#!/usr/bin/env python3
"""
Check that a git repository is ready for a public release. Standard library only (3.11+).

    python release_check.py                 # the repo in the current folder
    python release_check.py path/to/repo --version 1.2.0
    python release_check.py --json

Each check prints PASS, FAIL, WARN or INFO; exit code 1 if anything FAILs.

What it checks:
  - project files: README, LICENSE, .gitignore, CI workflow (required); CHANGELOG, SECURITY,
    CONTRIBUTING, Dependabot, issue and PR templates (recommended)
  - README has install and usage sections and at least one badge
  - the release version (from --version, pyproject.toml or package.json) has a CHANGELOG
    entry and no git tag yet
  - no secrets or secret files are tracked (.env, private keys, cloud/API tokens)
  - no large tracked files; the working tree is clean
  - the commit authors (listed, so you can confirm every identity is yours)

It only reads the files in the current commit. Secrets that were committed and later
deleted still live in git history: scan history with a tool such as gitleaks.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

LARGE_FILE_MB = 5
SCAN_MAX_BYTES = 1_000_000

SECRET_FILES = re.compile(
    r"(^|/)(\.env(\.[^/]*)?|id_rsa|id_ed25519|.*\.pem|.*\.p12|.*\.key|credentials\.json)$"
)
SAFE_SECRET_FILES = re.compile(r"(^|/)\.env\.(example|sample|template)$")
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    "OpenAI/Anthropic-style key": re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{32,}\b"),
}
DB_URL_WITH_PASSWORD = re.compile(
    r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?)://[^:\s/]+:([^@\s]+)@"
)
PLACEHOLDER_PASSWORDS = {"password", "pass", "secret", "changeme", "postgres", "xxx", "****"}

INSTALL_HEADING = re.compile(
    r"^#{2,4}\s.*\b(install|installation|quick ?start|getting started|set ?up|run|running|serve|"
    r"deploy|development)\b",
    re.I | re.M,
)
USAGE_HEADING = re.compile(
    r"^#{2,4}\s.*\b(usage|how to use|examples?|use (it|a|the|this)|commands?|cli|api|"
    r"running)\b",
    re.I | re.M,
)
CODE_FENCE = re.compile(r"^```.*?^```", re.M | re.S)  # comments in code blocks aren't headings
BADGE = re.compile(r"!\[[^\]]*\]\(https?://[^)]*(badge|shields\.io)[^)]*\)", re.I)


@dataclass
class Check:
    name: str
    status: str  # PASS | FAIL | WARN | INFO
    detail: str


def git(repo: Path, *args: str) -> str:
    """Run a read-only git command (no index refresh, so it never writes to .git)."""
    out = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(repo), *args], capture_output=True, text=True
    )
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip() or f"git {' '.join(args)} failed")
    return out.stdout


def find(repo: Path, *names: str) -> Path | None:
    for name in names:
        matches = sorted(repo.glob(name))
        if matches:
            return matches[0]
    return None


def check_files(repo: Path) -> list[Check]:
    required = {
        "readme": ("README.md", "README.rst", "README"),
        "license": ("LICENSE", "LICENSE.*", "COPYING"),
        "gitignore": (".gitignore",),
        "ci": (".github/workflows/*.yml", ".github/workflows/*.yaml"),
    }
    recommended = {
        "changelog": ("CHANGELOG.md", "CHANGES.md", "HISTORY.md"),
        "security-policy": ("SECURITY.md", ".github/SECURITY.md"),
        "contributing": ("CONTRIBUTING.md", ".github/CONTRIBUTING.md"),
        "dependabot": (".github/dependabot.yml", ".github/dependabot.yaml", "renovate.json"),
        "issue-templates": (".github/ISSUE_TEMPLATE/*",),
        "pr-template": (".github/pull_request_template.md", ".github/PULL_REQUEST_TEMPLATE.md"),
    }
    checks = []
    for name, patterns in required.items():
        path = find(repo, *patterns)
        checks.append(
            Check(
                name,
                "PASS" if path else "FAIL",
                str(path.relative_to(repo)) if path else f"missing ({patterns[0]})",
            )
        )
    for name, patterns in recommended.items():
        path = find(repo, *patterns)
        checks.append(
            Check(
                name,
                "PASS" if path else "WARN",
                str(path.relative_to(repo)) if path else f"missing ({patterns[0]})",
            )
        )
    return checks


def check_readme(repo: Path) -> list[Check]:
    readme = find(repo, "README.md", "README.rst", "README")
    if not readme:
        return []
    text = CODE_FENCE.sub("", readme.read_text(encoding="utf-8", errors="replace"))
    return [
        Check(
            "readme-install",
            "PASS" if INSTALL_HEADING.search(text) else "WARN",
            "has an install/quick start section"
            if INSTALL_HEADING.search(text)
            else "no install or quick start heading",
        ),
        Check(
            "readme-usage",
            "PASS" if USAGE_HEADING.search(text) else "WARN",
            "has a usage section"
            if USAGE_HEADING.search(text)
            else "no usage or examples heading (fine if the quick start covers everyday use)",
        ),
        Check(
            "readme-badge",
            "PASS" if BADGE.search(text) else "WARN",
            "has a status badge" if BADGE.search(text) else "no CI or status badge",
        ),
    ]


def project_version(repo: Path) -> str | None:
    pyproject = repo / "pyproject.toml"
    if pyproject.is_file():
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        version = data.get("project", {}).get("version") or (
            data.get("tool", {}).get("poetry", {}).get("version")
        )
        if version:
            return str(version)
    package = repo / "package.json"
    if package.is_file():
        version = json.loads(package.read_text(encoding="utf-8")).get("version")
        if version:
            return str(version)
    return None


def check_version(repo: Path, version: str | None) -> list[Check]:
    explicit = version is not None
    version = version or project_version(repo)
    if not version:
        return [
            Check("version", "WARN", "no --version given and none found in pyproject/package.json")
        ]
    checks = [Check("version", "INFO", f"releasing {version}")]
    changelog = find(repo, "CHANGELOG.md", "CHANGES.md", "HISTORY.md")
    if changelog:
        text = changelog.read_text(encoding="utf-8", errors="replace")
        heading = re.compile(rf"^##\s*\[?v?{re.escape(version)}\]?", re.M)
        checks.append(
            Check(
                "changelog-entry",
                "PASS" if heading.search(text) else "FAIL",
                f"{changelog.name} has a {version} entry"
                if heading.search(text)
                else f"{changelog.name} has no '## [{version}]' entry",
            )
        )
    tags = set(git(repo, "tag", "--list").split())
    taken = sorted({f"v{version}", version} & tags)
    if not taken:
        checks.append(Check("tag-free", "PASS", f"v{version} not tagged yet"))
    elif explicit:
        checks.append(Check("tag-free", "FAIL", f"tag {taken[0]} already exists"))
    else:
        # Auditing a released repo: the project version is simply the last release.
        checks[0] = Check("version", "INFO", f"{version} is already released as {taken[0]}")
        checks = [c for c in checks if c.name != "changelog-entry"]
        checks.append(Check("tag-free", "INFO", "pass --version X.Y.Z to check the next release"))
    return checks


def check_tracked(repo: Path) -> list[Check]:
    files = [f for f in git(repo, "ls-files", "-z").split("\0") if f]
    secret_files = [f for f in files if SECRET_FILES.search(f) and not SAFE_SECRET_FILES.search(f)]
    leaks, db_urls, large = [], [], []
    for rel in files:
        path = repo / rel
        if not path.is_file():
            continue
        size = path.stat().st_size
        if size > LARGE_FILE_MB * 1024 * 1024:
            large.append(f"{rel} ({size / 1024 / 1024:.1f} MB)")
            continue
        if size > SCAN_MAX_BYTES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # binary file
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                leaks.append(f"{rel}: {label}")
        for password in DB_URL_WITH_PASSWORD.findall(text):
            if password.lower() not in PLACEHOLDER_PASSWORDS and not password.startswith(
                ("<", "$", "{")
            ):
                db_urls.append(rel)
                break

    checks = [
        Check(
            "secret-files",
            "FAIL" if secret_files else "PASS",
            ", ".join(secret_files) if secret_files else "no .env, key or credential files tracked",
        ),
        Check(
            "secrets-in-files",
            "FAIL" if leaks else "PASS",
            "; ".join(leaks) if leaks else f"no token patterns in {len(files)} tracked files",
        ),
    ]
    if db_urls:
        checks.append(
            Check(
                "database-urls",
                "WARN",
                "connection string with a password in: " + ", ".join(sorted(set(db_urls))),
            )
        )
    checks.append(
        Check(
            "large-files",
            "WARN" if large else "PASS",
            ", ".join(large) if large else f"nothing over {LARGE_FILE_MB} MB",
        )
    )
    return checks


def check_git_state(repo: Path) -> list[Check]:
    dirty = git(repo, "status", "--porcelain").strip()
    checks = [
        Check(
            "clean-tree",
            "WARN" if dirty else "PASS",
            f"{len(dirty.splitlines())} uncommitted change(s)" if dirty else "nothing uncommitted",
        )
    ]
    try:
        authors = sorted(set(git(repo, "log", "--format=%an <%ae>").splitlines()))
    except RuntimeError:
        authors = []  # no commits yet
    checks.append(
        Check(
            "authors",
            "INFO",
            f"{len(authors)} identit{'y' if len(authors) == 1 else 'ies'}: " + "; ".join(authors)
            if authors
            else "no commits yet",
        )
    )
    return checks


def run_checks(repo: Path, version: str | None = None) -> list[Check]:
    git(repo, "rev-parse", "--git-dir")  # raises if this isn't a git repo
    return (
        check_files(repo)
        + check_readme(repo)
        + check_version(repo, version)
        + check_tracked(repo)
        + check_git_state(repo)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a git repo is ready for a public release.")
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument("--version", help="version about to be released, e.g. 1.2.0")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    try:
        checks = run_checks(repo, args.version)
    except (RuntimeError, FileNotFoundError) as exc:
        print(f"error: {repo} is not a git repository ({exc})", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps([asdict(c) for c in checks], indent=2))
    else:
        for c in checks:
            print(f"{c.status:<4}  {c.name:<17}  {c.detail}")
        counts = {s: sum(c.status == s for c in checks) for s in ("FAIL", "WARN")}
        print(f"\n{counts['FAIL']} fail, {counts['WARN']} warn")
    return 1 if any(c.status == "FAIL" for c in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
