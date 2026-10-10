"""
Trigger evals: does an agent load the right skill for a request, and leave it alone otherwise?

At startup an agent sees only each skill's name and description. When a request arrives it
decides which skills to load. This module recreates that decision: the model gets the same
catalog (our skills plus realistic distractors, shuffled per trial so position doesn't
matter), one request, and returns the skills it would load as JSON.

Each answer is appended to a run file (JSONL) as soon as it arrives, so a run that stops on
a rate limit resumes where it left off, and the raw answers stay as evidence. The run file
name includes a hash of the catalog, so editing a description starts a fresh run instead of
mixing old and new answers.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from skillbench.providers import KeywordProvider, Provider
from skillbench.skill import discover, load_skill

SYSTEM_PROMPT = """You are the skill router of an AI coding agent. The agent has these skills \
installed. Each skill is a folder of instructions it can load. Like a real agent at startup, \
you see only each skill's name and description.

Skills:
{catalog}

Decide which skills the agent should load before handling the user's request. Load a skill \
only if its instructions would materially help with this request. Most requests need zero or \
one skill. Reply with JSON only, using exact skill names:
{{"skills": ["skill-name"]}}
or, if none apply:
{{"skills": []}}"""


@dataclass
class Case:
    id: str
    prompt: str
    expected: list[str]
    kind: str = ""


@dataclass
class Answer:
    case: str
    trial: int
    chosen: list[str]
    raw: str
    error: str | None = None
    seconds: float = 0.0


@dataclass
class Report:
    skills: list[str]
    answers: list[Answer]
    cases: dict[str, Case]
    per_skill: dict[str, dict] = field(default_factory=dict)
    summary: dict = field(default_factory=dict)
    by_kind: dict[str, dict] = field(default_factory=dict)
    mistakes: list[dict] = field(default_factory=list)


def load_cases(path: str | Path) -> list[Case]:
    cases = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            cases.append(Case(row["id"], row["prompt"], list(row["expected"]), row.get("kind", "")))
    ids = [c.id for c in cases]
    duplicates = [i for i, n in Counter(ids).items() if n > 1]
    if duplicates:
        raise ValueError(f"duplicate case ids: {duplicates}")
    return cases


def load_catalog(skill_paths: list[str], distractors: str | Path | None) -> tuple[list, list]:
    """(catalog of (name, description) for every skill shown, names of the skills under test)."""
    ours = []
    for folder in discover(skill_paths):
        skill = load_skill(folder)
        ours.append((skill.name, " ".join(skill.description.split())))
    extra = []
    if distractors:
        for line in Path(distractors).read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                extra.append((row["name"], row["description"]))
    names = [n for n, _ in ours]
    clash = set(names) & {n for n, _ in extra}
    if clash:
        raise ValueError(f"distractor names clash with skills: {sorted(clash)}")
    return ours + extra, names


def catalog_hash(catalog: list[tuple[str, str]]) -> str:
    text = "\n".join(f"{n}: {d}" for n, d in sorted(catalog)) + SYSTEM_PROMPT
    return hashlib.sha256(text.encode()).hexdigest()[:8]


def system_prompt(catalog: list[tuple[str, str]], seed: int) -> str:
    shuffled = list(catalog)
    random.Random(seed).shuffle(shuffled)
    return SYSTEM_PROMPT.format(catalog="\n".join(f"- {n}: {d}" for n, d in shuffled))


def parse_choice(raw: str, valid: set[str]) -> tuple[list[str], str | None]:
    """Skill names from the model's reply, and an error message if the reply was malformed."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            return [], "reply was not JSON"
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return [], "reply was not JSON"
    skills = data.get("skills") if isinstance(data, dict) else None
    if not isinstance(skills, list):
        return [], "reply had no 'skills' list"
    chosen = sorted({s for s in skills if isinstance(s, str) and s in valid})
    unknown = [s for s in skills if not (isinstance(s, str) and s in valid)]
    return chosen, (f"unknown skill names: {unknown}" if unknown else None)


def run_path(out_dir: str | Path, provider: Provider, catalog: list) -> Path:
    model = re.sub(r"[^A-Za-z0-9._-]+", "_", provider.model)
    return Path(out_dir) / f"{provider.name}--{model}--{catalog_hash(catalog)}.jsonl"


def load_answers(path: Path) -> list[Answer]:
    if not path.is_file():
        return []
    return [Answer(**json.loads(line)) for line in path.read_text().splitlines() if line.strip()]


def run(
    cases: list[Case],
    catalog: list[tuple[str, str]],
    provider: Provider,
    trials: int,
    out_dir: str | Path,
    progress=None,
) -> tuple[Path, list[Answer]]:
    """Ask the provider about every (case, trial) not already in the run file."""
    if isinstance(provider, KeywordProvider):
        provider.set_catalog(catalog)
    path = run_path(out_dir, provider, catalog)
    path.parent.mkdir(parents=True, exist_ok=True)
    answers = load_answers(path)
    done = {(a.case, a.trial) for a in answers}
    valid = {name for name, _ in catalog}
    todo = [(c, t) for t in range(trials) for c in cases if (c.id, t) not in done]
    with path.open("a", encoding="utf-8") as fh:
        for i, (case, trial) in enumerate(todo, 1):
            raw = provider.complete(system_prompt(catalog, seed=trial), case.prompt)
            chosen, error = parse_choice(raw, valid)
            answer = Answer(case.id, trial, chosen, raw, error, provider.last_seconds)
            fh.write(json.dumps(answer.__dict__) + "\n")
            fh.flush()
            answers.append(answer)
            if progress:
                progress(i, len(todo), case, answer)
    return path, answers


def _ratio(num: int, den: int) -> float | None:
    return round(num / den, 3) if den else None


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    middle = ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2
    return round(middle, 2)


def _f1(precision: float | None, recall: float | None) -> float | None:
    if precision is None or recall is None:
        return None
    total = precision + recall
    return round(2 * precision * recall / total, 3) if total else 0.0


def score(cases: list[Case], answers: list[Answer], skills: list[str]) -> Report:
    """Metrics over our skills only; picking a distractor counts as picking none of ours."""
    by_id = {c.id: c for c in cases}
    ours = set(skills)
    answers = [a for a in answers if a.case in by_id]
    report = Report(skills=skills, answers=answers, cases=by_id)

    counts = {s: Counter() for s in skills}
    kinds: dict[str, Counter] = defaultdict(Counter)
    exact = positives_hit = positives = negatives = false_triggers = 0
    for a in answers:
        case = by_id[a.case]
        got, want = set(a.chosen) & ours, set(case.expected)
        for s in skills:
            if s in got and s in want:
                counts[s]["tp"] += 1
            elif s in got:
                counts[s]["fp"] += 1
            elif s in want:
                counts[s]["fn"] += 1
        ok = got == want
        exact += ok
        kinds[case.kind or "-"]["n"] += 1
        kinds[case.kind or "-"]["ok"] += ok
        if want:
            positives += 1
            positives_hit += want <= got
        else:
            negatives += 1
            false_triggers += bool(got)
        if not ok:
            report.mistakes.append(
                {
                    "case": case.id,
                    "trial": a.trial,
                    "kind": case.kind,
                    "prompt": case.prompt,
                    "expected": sorted(want),
                    "chosen": sorted(set(a.chosen)),
                    "error": a.error,
                }
            )

    for s, c in counts.items():
        p = _ratio(c["tp"], c["tp"] + c["fp"])
        r = _ratio(c["tp"], c["tp"] + c["fn"])
        f1 = _f1(p, r)
        report.per_skill[s] = {
            "tp": c["tp"],
            "fp": c["fp"],
            "fn": c["fn"],
            "precision": p,
            "recall": r,
            "f1": f1,
        }

    trials_by_case: dict[str, set] = defaultdict(set)
    for a in answers:
        trials_by_case[a.case].add(tuple(sorted(set(a.chosen) & ours)))
    multi = [c for c in trials_by_case if sum(1 for a in answers if a.case == c) > 1]
    report.summary = {
        "answers": len(answers),
        "accuracy": _ratio(exact, len(answers)),
        "recall": _ratio(positives_hit, positives),
        "false_trigger_rate": _ratio(false_triggers, negatives),
        "parse_errors": sum(1 for a in answers if a.error),
        "consistency": _ratio(sum(len(trials_by_case[c]) == 1 for c in multi), len(multi)),
        "median_seconds": _median([a.seconds for a in answers]),
    }
    report.by_kind = {
        k: {"n": v["n"], "accuracy": _ratio(v["ok"], v["n"])} for k, v in kinds.items()
    }
    return report


def _pct(value: float | None) -> str:
    return "–" if value is None else f"{value * 100:.0f}%"


def to_markdown(report: Report, title: str) -> str:
    s = report.summary
    lines = [
        f"### {title}",
        "",
        f"{s['answers']} answers · accuracy {_pct(s['accuracy'])} · recall {_pct(s['recall'])} · "
        f"false triggers {_pct(s['false_trigger_rate'])} · parse errors {s['parse_errors']}"
        + (f" · consistency {_pct(s['consistency'])}" if s["consistency"] is not None else "")
        + (f" · median {s['median_seconds']} s/answer" if s.get("median_seconds") else ""),
        "",
        "| Skill | Precision | Recall | F1 | TP | FP | FN |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, m in report.per_skill.items():
        lines.append(
            f"| `{name}` | {_pct(m['precision'])} | {_pct(m['recall'])} | {_pct(m['f1'])} "
            f"| {m['tp']} | {m['fp']} | {m['fn']} |"
        )
    lines += ["", "| Case kind | Answers | Accuracy |", "|---|---:|---:|"]
    for kind, m in sorted(report.by_kind.items()):
        lines.append(f"| {kind} | {m['n']} | {_pct(m['accuracy'])} |")
    if report.mistakes:
        lines += [
            "",
            "<details><summary>Mistakes</summary>",
            "",
            "| Case | Expected | Chosen | Prompt |",
            "|---|---|---|---|",
        ]
        for m in report.mistakes:
            chosen = ", ".join(m["chosen"]) or "none"
            if m["error"]:
                chosen += f" ({m['error']})"
            lines.append(
                f"| {m['case']} | {', '.join(m['expected']) or 'none'} | {chosen} | {m['prompt']} |"
            )
        lines += ["", "</details>"]
    return "\n".join(lines) + "\n"
