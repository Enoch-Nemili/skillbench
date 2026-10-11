"""
Outcome evals: does loading a skill make the work better?

Each task is a folder with a `task.py` that defines:

    SKILL = "repro-before-fix"          # the skill under test
    PROMPT = "..."                      # what the user asks; neutral: never asks for
                                        # the behaviour the skill adds
    def grade(output: str) -> list[Check]: ...   # deterministic checks on the model's answer

The same model answers every task twice per trial: once as a plain assistant ("without") and
once with the skill's SKILL.md body loaded as instructions ("with"). Answers are saved to a run
file (JSONL) as they arrive, so runs resume and can be re-graded later without new API calls.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import ModuleType

from skillbench.providers import Provider
from skillbench.skill import discover, load_skill

CONDITIONS = ("without", "with")
# Bumped when the harness changes how answers are produced, so old run files are not resumed.
# 2: answers are requested as plain text (run 1 had JSON output mode on by mistake).
HARNESS_VERSION = 2

BASE_SYSTEM = (
    "You are an experienced software engineer helping a colleague. Answer the request directly "
    "and completely. When you write code, put each file in a fenced code block whose first line "
    "is a comment naming the file, for example `# file: app.py`."
)
SKILL_SYSTEM = (
    "{base}\n\nYou have loaded the skill `{name}`. Follow its instructions for this request. "
    "Bundled scripts and reference files are not available here; apply their method yourself.\n\n"
    '<skill name="{name}">\n{body}\n</skill>'
)


@dataclass
class Check:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class Task:
    id: str
    skill: str
    prompt: str
    module: ModuleType
    source_hash: str

    def grade(self, output: str) -> list[Check]:
        return list(self.module.grade(output))


@dataclass
class Answer:
    task: str
    condition: str
    trial: int
    output: str
    seconds: float = 0.0
    error: str | None = None


@dataclass
class TaskResult:
    task: str
    skill: str
    runs: dict = field(default_factory=dict)  # condition -> list of {"passed", "score", "checks"}


def load_tasks(root: str | Path) -> list[Task]:
    tasks = []
    for path in sorted(Path(root).glob("*/task.py")):
        name = f"skillbench_task_{path.parent.name.replace('-', '_')}"
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        for attr in ("SKILL", "PROMPT", "grade"):
            if not hasattr(module, attr):
                raise ValueError(f"{path}: missing {attr}")
        tasks.append(
            Task(
                path.parent.name,
                module.SKILL,
                module.PROMPT.strip(),
                module,
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        )
    if not tasks:
        raise ValueError(f"no */task.py under {root}")
    return tasks


def skill_bodies(skill_paths: list[str]) -> dict[str, str]:
    return {load_skill(d).name: load_skill(d).body.strip() for d in discover(skill_paths)}


def system_prompt(condition: str, skill: str, bodies: dict[str, str]) -> str:
    if condition == "without":
        return BASE_SYSTEM
    return SKILL_SYSTEM.format(base=BASE_SYSTEM, name=skill, body=bodies[skill])


def run_hash(tasks: list[Task], bodies: dict[str, str]) -> str:
    """Changes when a task, a grader-adjacent prompt, a skill body or the system prompts change."""
    h = hashlib.sha256((BASE_SYSTEM + SKILL_SYSTEM + str(HARNESS_VERSION)).encode())
    for t in sorted(tasks, key=lambda t: t.id):
        h.update(t.id.encode() + t.source_hash.encode() + bodies.get(t.skill, "").encode())
    return h.hexdigest()[:8]


def run_path(out_dir: str | Path, provider: Provider, tasks: list[Task], bodies: dict) -> Path:
    model = re.sub(r"[^A-Za-z0-9._-]+", "_", provider.model)
    return Path(out_dir) / f"{provider.name}--{model}--outcomes--{run_hash(tasks, bodies)}.jsonl"


def load_answers(path: Path) -> list[Answer]:
    if not path.is_file():
        return []
    return [Answer(**json.loads(line)) for line in path.read_text().splitlines() if line.strip()]


def run(tasks, bodies, provider, trials, out_dir, progress=None) -> tuple[Path, list[Answer]]:
    missing = {t.skill for t in tasks} - set(bodies)
    if missing:
        raise ValueError(f"tasks reference skills that weren't found: {sorted(missing)}")
    provider.json_mode = False  # answers are prose and code, never forced into JSON
    path = run_path(out_dir, provider, tasks, bodies)
    path.parent.mkdir(parents=True, exist_ok=True)
    answers = load_answers(path)
    done = {(a.task, a.condition, a.trial) for a in answers}
    todo = [
        (t, c, n)
        for n in range(trials)
        for t in tasks
        for c in CONDITIONS
        if (t.id, c, n) not in done
    ]
    with path.open("a", encoding="utf-8") as fh:
        for i, (task, condition, trial) in enumerate(todo, 1):
            output = provider.complete(system_prompt(condition, task.skill, bodies), task.prompt)
            answer = Answer(task.id, condition, trial, output, provider.last_seconds)
            fh.write(json.dumps(asdict(answer)) + "\n")
            fh.flush()
            answers.append(answer)
            if progress:
                progress(i, len(todo), task, answer)
    return path, answers


def grade_all(tasks: list[Task], answers: list[Answer], trials: int) -> list[TaskResult]:
    by_id = {t.id: t for t in tasks}
    results = {t.id: TaskResult(t.id, t.skill) for t in tasks}
    for a in sorted(answers, key=lambda a: (a.task, a.condition, a.trial)):
        if a.task not in by_id or a.trial >= trials:
            continue
        checks = by_id[a.task].grade(a.output)
        passed = bool(checks) and all(c.passed for c in checks)
        score = sum(c.passed for c in checks) / len(checks) if checks else 0.0
        results[a.task].runs.setdefault(a.condition, []).append(
            {
                "trial": a.trial,
                "passed": passed,
                "score": round(score, 3),
                "checks": [asdict(c) for c in checks],
                "chars": len(a.output),
            }
        )
    return list(results.values())


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 3) if values else None


def summarize(results: list[TaskResult]) -> dict:
    """Per task, per skill and overall: pass rate and mean check score, with vs without."""

    def stats(runs):
        return {
            "n": len(runs),
            "pass_rate": _mean([float(r["passed"]) for r in runs]),
            "score": _mean([r["score"] for r in runs]),
            "chars": _mean([r["chars"] for r in runs]),
        }

    per_task = {r.task: {c: stats(r.runs.get(c, [])) for c in CONDITIONS} for r in results}
    by_skill: dict[str, dict[str, list]] = defaultdict(lambda: {c: [] for c in CONDITIONS})
    for r in results:
        for c in CONDITIONS:
            by_skill[r.skill][c].extend(r.runs.get(c, []))
    per_skill = {s: {c: stats(v[c]) for c in CONDITIONS} for s, v in sorted(by_skill.items())}
    overall = {c: stats([run for r in results for run in r.runs.get(c, [])]) for c in CONDITIONS}
    return {"per_task": per_task, "per_skill": per_skill, "overall": overall}


def _pct(x: float | None) -> str:
    return "–" if x is None else f"{x * 100:.0f}%"


def to_markdown(results: list[TaskResult], title: str) -> str:
    s = summarize(results)
    o = s["overall"]
    lines = [
        f"### {title}",
        "",
        f"Overall: tasks fully passed {_pct(o['without']['pass_rate'])} without the skill → "
        f"{_pct(o['with']['pass_rate'])} with it; mean check score "
        f"{_pct(o['without']['score'])} → {_pct(o['with']['score'])}.",
        "",
        "| Skill | Task | Passed without | Passed with | Checks without | Checks with |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for r in results:
        t = s["per_task"][r.task]
        w, k = t["without"], t["with"]
        lines.append(
            f"| `{r.skill}` | {r.task} | {_pct(w['pass_rate'])} ({w['n']}) | "
            f"{_pct(k['pass_rate'])} ({k['n']}) | {_pct(w['score'])} | {_pct(k['score'])} |"
        )
    lines += ["", "<details><summary>Failed checks</summary>", ""]
    for r in results:
        for condition in CONDITIONS:
            failed = {}
            for run_ in r.runs.get(condition, []):
                for c in run_["checks"]:
                    if not c["passed"]:
                        failed[c["name"]] = failed.get(c["name"], 0) + 1
            if failed:
                listed = ", ".join(f"{name} ×{n}" for name, n in sorted(failed.items()))
                lines.append(f"- {r.task} ({condition}): {listed}")
    lines += ["", "</details>"]
    return "\n".join(lines) + "\n"
