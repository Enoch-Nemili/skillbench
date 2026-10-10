"""Command line entry point: `skillbench lint`, `skillbench triggers`, `skillbench models`."""

from __future__ import annotations

import argparse
import json
import sys

from skillbench import __version__
from skillbench.lint import lint_skill
from skillbench.providers import ProviderError, make_provider
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

    trig = sub.add_parser("triggers", help="measure whether a model picks the right skill")
    trig.add_argument("paths", nargs="+", help="skill folders, or folders that contain skills")
    trig.add_argument("--provider", default="keyword", help="keyword (offline), gemini or ollama")
    trig.add_argument("--model", help="model id, e.g. from `skillbench models`")
    trig.add_argument("--cases", default="evals/triggers.jsonl")
    trig.add_argument(
        "--distractors",
        default="evals/distractors.jsonl",
        help="other skills to show alongside yours ('' for none)",
    )
    trig.add_argument("--trials", type=int, default=1, help="answers per case (catalog reshuffled)")
    trig.add_argument("--temperature", type=float, default=0.0)
    trig.add_argument("--rpm", type=float, help="max requests per minute (gemini default 5)")
    trig.add_argument("--out", default="evals/runs", help="folder for run files and reports")
    trig.add_argument("--min-accuracy", type=float, help="exit 1 if accuracy is below this (0-1)")
    trig.add_argument("--json", action="store_true", help="print metrics as JSON")

    models = sub.add_parser("models", help="list the models a provider offers you")
    models.add_argument("--provider", default="gemini")

    args = parser.parse_args(argv)
    if args.command == "lint":
        return _lint(args.paths, args.format, args.strict)
    if args.command == "models":
        return _models(args.provider)
    return _triggers(args)


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


def _models(provider_name: str) -> int:
    try:
        provider = make_provider(provider_name, model="list")
        names = provider.list_models()
    except ProviderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print("\n".join(names) if names else f"{provider_name} lists no models")
    return 0


def _triggers(args: argparse.Namespace) -> int:
    from pathlib import Path

    from skillbench import triggers

    try:
        cases = triggers.load_cases(args.cases)
        catalog, ours = triggers.load_catalog(args.paths, args.distractors or None)
        provider = make_provider(args.provider, args.model, args.temperature, args.rpm)
    except (OSError, ValueError, ProviderError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not ours:
        print(f"no SKILL.md found under: {' '.join(args.paths)}", file=sys.stderr)
        return 2

    def progress(i, total, case, answer):
        got = set(answer.chosen) & set(ours)
        ok = set(case.expected) <= got <= set(case.expected) | set(case.allowed)
        mark = "ok " if ok else "MISS"
        print(
            f"[{i}/{total}] {mark} {case.id}: {', '.join(answer.chosen) or 'none'}", file=sys.stderr
        )

    case_set = Path(args.cases).stem
    path = triggers.run_path(args.out, provider, catalog, case_set)
    incomplete = None
    try:
        path, answers = triggers.run(
            cases, catalog, provider, args.trials, args.out, progress, case_set
        )
    except ProviderError as exc:
        incomplete = str(exc)
        answers = triggers.load_answers(path)

    report = triggers.score(cases, [a for a in answers if a.trial < args.trials], ours)
    title = (
        f"{provider.name} · {provider.model} · {case_set} · {args.trials} trial(s) · "
        f"catalog {path.stem[-8:]}"
    )
    markdown = triggers.to_markdown(report, title)
    if answers:
        path.with_suffix(".md").write_text(markdown, encoding="utf-8")

    if args.json:
        print(
            json.dumps(
                {
                    "run": str(path),
                    "summary": report.summary,
                    "per_skill": report.per_skill,
                    "by_kind": report.by_kind,
                },
                indent=2,
            )
        )
    else:
        print(markdown)
        print(f"answers: {path}\nreport:  {Path(path).with_suffix('.md')}")

    if incomplete:
        print(f"\nstopped early: {incomplete}", file=sys.stderr)
        return 3
    accuracy = report.summary["accuracy"] or 0.0
    if args.min_accuracy is not None and accuracy < args.min_accuracy:
        print(
            f"accuracy {accuracy:.3f} is below --min-accuracy {args.min_accuracy}", file=sys.stderr
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
