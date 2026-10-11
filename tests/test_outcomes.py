import json
from pathlib import Path

import pytest

from skillbench import outcomes
from skillbench.cli import main
from skillbench.providers import Provider, ProviderError

REPO = Path(__file__).resolve().parents[1]

TASK = """
from skillbench.grading import check_mentions
SKILL = "{skill}"
PROMPT = "Do the thing."
def grade(output):
    return [
        check_mentions("said_magic", output, r"magic"),
        check_mentions("said_word", output, r"word"),
    ]
"""


class EchoSkill(Provider):
    """Says 'magic word' only when the skill is in its system prompt."""

    name = "echo"

    def __init__(self, fail_after=None):
        super().__init__("m1")
        self.calls, self.fail_after = 0, fail_after

    def _complete(self, system, user):
        if self.fail_after is not None and self.calls >= self.fail_after:
            raise ProviderError("quota exhausted")
        self.calls += 1
        return "magic word" if "<skill" in system else "magic"


@pytest.fixture
def setup(tmp_path):
    skills = tmp_path / "skills" / "demo"
    skills.mkdir(parents=True)
    (skills / "SKILL.md").write_text(
        "---\nname: demo\ndescription: Demo skill. Use when testing.\n---\nSay the magic word.\n"
    )
    tasks = tmp_path / "tasks" / "t1"
    tasks.mkdir(parents=True)
    (tasks / "task.py").write_text(TASK.format(skill="demo"))
    return tmp_path


def test_with_vs_without(setup):
    tasks = outcomes.load_tasks(setup / "tasks")
    bodies = outcomes.skill_bodies([str(setup / "skills")])
    assert "Say the magic word." in outcomes.system_prompt("with", "demo", bodies)
    assert "<skill" not in outcomes.system_prompt("without", "demo", bodies)

    path, answers = outcomes.run(tasks, bodies, EchoSkill(), 2, setup / "out")
    assert len(answers) == 4
    summary = outcomes.summarize(outcomes.grade_all(tasks, answers, 2))
    assert summary["per_task"]["t1"]["with"] == {
        "n": 2,
        "pass_rate": 1.0,
        "score": 1.0,
        "chars": 10.0,
    }
    assert summary["per_task"]["t1"]["without"]["pass_rate"] == 0.0
    assert summary["per_task"]["t1"]["without"]["score"] == 0.5
    md = outcomes.to_markdown(outcomes.grade_all(tasks, answers, 2), "demo run")
    assert "t1 (without): said_word ×2" in md


def test_resume_and_stop(setup):
    tasks = outcomes.load_tasks(setup / "tasks")
    bodies = outcomes.skill_bodies([str(setup / "skills")])
    with pytest.raises(ProviderError):
        outcomes.run(tasks, bodies, EchoSkill(fail_after=3), 3, setup / "out")
    provider = EchoSkill()
    _, answers = outcomes.run(tasks, bodies, provider, 3, setup / "out")
    assert provider.calls == 3 and len(answers) == 6


def test_run_hash_changes_with_the_skill_body(setup):
    tasks = outcomes.load_tasks(setup / "tasks")
    a = outcomes.run_hash(tasks, {"demo": "v1"})
    assert a != outcomes.run_hash(tasks, {"demo": "v2"})


def test_unknown_skill_is_an_error(setup):
    (setup / "tasks" / "t2").mkdir()
    (setup / "tasks" / "t2" / "task.py").write_text(TASK.format(skill="nope"))
    tasks = outcomes.load_tasks(setup / "tasks")
    with pytest.raises(ValueError, match="nope"):
        outcomes.run(tasks, outcomes.skill_bodies([str(setup / "skills")]), EchoSkill(), 1, setup)


def test_repo_tasks_match_repo_skills():
    tasks = outcomes.load_tasks(REPO / "evals/outcomes")
    bodies = outcomes.skill_bodies([str(REPO / "skills")])
    assert {t.skill for t in tasks} <= set(bodies)
    for t in tasks:  # the prompt must not ask for what the skill adds
        assert "test" not in t.prompt.lower().split("```")[0] or t.skill != "repro-before-fix"


def test_cli_refuses_keyword_provider(capsys):
    assert main(["outcomes", str(REPO / "skills"), "--provider", "keyword"]) == 2
    assert "need a model" in capsys.readouterr().err


def test_cli_json_with_scripted_provider(setup, monkeypatch, capsys):
    monkeypatch.setattr("skillbench.cli.make_provider", lambda *a, **k: EchoSkill())
    code = main(
        [
            "outcomes",
            str(setup / "skills"),
            "--tasks",
            str(setup / "tasks"),
            "--model",
            "m1",
            "--trials",
            "1",
            "--out",
            str(setup / "out"),
            "--json",
        ]
    )
    assert code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["overall"]["with"]["pass_rate"] == 1.0


def test_outcome_runs_never_use_json_mode(setup):
    """Regression: the first outcome run was invalid because answers were forced into JSON."""
    tasks = outcomes.load_tasks(setup / "tasks")
    bodies = outcomes.skill_bodies([str(setup / "skills")])
    provider = EchoSkill()
    assert provider.json_mode is True
    outcomes.run(tasks, bodies, provider, 1, setup / "out")
    assert provider.json_mode is False
