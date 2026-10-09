"""Command line entry point: `skillbench lint skills/`."""

from __future__ import annotations

import argparse
import json
import sys

from skillbench import __version__
from skillbench.lint import lint_skill
from skillbench.skill import discover


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="skillbench", description="Lint and evaluate Agent Skills (SKILL.md folders)."
    )
    parser.add_argument("--version", action="version", version=f"skillbench {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    lint = sub.add_parser("lint", help="check skills against the Agent Skills spec")
    lint.add_argument("paths", nargs="+", help="skill folders, or folders that contain skills")
    lint.add_argument("--format", choices=["text", "json"], default="text")
    lint.add_argument("--strict", action="store_true", help="fail on warnings too")

    args = parser.parse_args(argv)
    return _lint(args.paths, args.format, args.strict)


def _lint(paths: list[str], fmt: str, strict: bool) -> int:
    skills = discover(paths)
    if not skills:
        print(f"no SKILL.md found under: {' '.join(paths)}", file=sys.stderr)
        return 2

    results = {str(d): lint_skill(d) for d in skills}
    findings = [f for fs in results.values() for f in fs]
    errors = sum(f.severity == "error" for f in findings)
    warnings = len(findings) - errors

    if fmt == "json":
        print(
            json.dumps(
                {
                    "skills": len(skills),
                    "errors": errors,
                    "warnings": warnings,
                    "findings": [f.to_dict() for f in findings],
                },
                indent=2,
            )
        )
    else:
        for directory, fs in results.items():
            status = (
                "ok" if not fs else ("FAIL" if any(f.severity == "error" for f in fs) else "warn")
            )
            print(f"{status:>4}  {directory}")
            for f in fs:
                where = f"{f.path}:{f.line}" if f.line else str(f.path)
                print(f"      {f.code} {f.severity}: {f.message}  ({where})")
        print(f"\n{len(skills)} skill(s), {errors} error(s), {warnings} warning(s)")

    return 1 if errors or (strict and warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
