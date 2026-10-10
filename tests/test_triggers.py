import json
from pathlib import Path

import pytest

from skillbench import triggers
from skillbench.cli import main
from skillbench.providers import KeywordProvider, Provider, ProviderError
from skillbench.triggers import Answer, Case

REPO = Path(__file__).resolve().parents[1]
CATALOG = [
    ("alpha", "Do alpha things. Use when the user asks about alpha."),
    ("beta", "Do beta things. Use when the user asks about beta."),
    ("other", "A distractor skill."),
]
OURS = ["alpha", "beta"]


class ScriptedProvider(Provider):
    """Answers from a dict of prompt -> skills; can fail after N calls."""

    name = "scripted"

    def __init__(self, answers, fail_after=None):
        super().__init__("m1")
        self.answers, self.calls, self.fail_after = answers, 0, fail_after

    def _complete(self, system, user):
        if self.fail_after is not None and self.calls >= self.fail_after:
            raise ProviderError("quota exhausted")
        self.calls += 1
        return json.dumps({"skills": self.answers.get(user, [])})


# --- parsing and prompts -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "chosen", "error"),
    [
        ('{"skills": ["alpha"]}', ["alpha"], None),
        ('```json\n{"skills": ["beta", "alpha"]}\n```', ["alpha", "beta"], None),
        ('Sure! {"skills": []} hope that helps', [], None),
        ('{"skills": ["alpha", "gamma"]}', ["alpha"], "unknown skill names: ['gamma']"),
        ("I would load alpha", [], "reply was not JSON"),
        ('{"choice": "alpha"}', [], "reply had no 'skills' list"),
    ],
)
def test_parse_choice(raw, chosen, error):
    assert triggers.parse_choice(raw, {"alpha", "beta", "other"}) == (chosen, error)


def test_system_prompt_lists_every_skill_and_shuffles_by_seed():
    prompts = {triggers.system_prompt(CATALOG, seed) for seed in range(6)}
    assert len(prompts) > 1
    assert triggers.system_prompt(CATALOG, 3) == triggers.system_prompt(CATALOG, 3)
    for name, desc in CATALOG:
        assert f"- {name}: {desc}" in next(iter(prompts))


def test_catalog_hash_changes_with_descriptions():
    edited = [("alpha", "Different words."), *CATALOG[1:]]
    assert triggers.catalog_hash(CATALOG) != triggers.catalog_hash(edited)
    assert triggers.catalog_hash(CATALOG) == triggers.catalog_hash(list(reversed(CATALOG)))


def test_repo_catalog_and_cases_load():
    catalog, ours = triggers.load_catalog([str(REPO / "skills")], REPO / "evals/distractors.jsonl")
    cases = triggers.load_cases(REPO / "evals/triggers.jsonl")
    assert len(ours) == 4
    assert {c.expected[0] for c in cases if c.expected} == set(ours)
    assert sum(1 for c in cases if not c.expected) >= 10


def test_duplicate_case_ids_are_rejected(tmp_path):
    path = tmp_path / "cases.jsonl"
    row = json.dumps({"id": "a", "prompt": "p", "expected": []})
    path.write_text(f"{row}\n{row}\n")
    with pytest.raises(ValueError, match="duplicate"):
        triggers.load_cases(path)


# --- scoring -------------------------------------------------------------------------------


def test_score_metrics():
    cases = [
        Case("a1", "about alpha", ["alpha"], "explicit"),
        Case("b1", "about beta", ["beta"], "implicit"),
        Case("n1", "unrelated", [], "unrelated"),
        Case("n2", "near miss", [], "near-miss"),
    ]
    answers = [
        Answer("a1", 0, ["alpha"], ""),
        Answer("b1", 0, ["alpha"], ""),  # wrong skill: fp for alpha, fn for beta
        Answer("n1", 0, ["other"], ""),  # a distractor counts as none of ours: correct
        Answer("n2", 0, ["beta"], ""),  # false trigger
    ]
    report = triggers.score(cases, answers, OURS)
    assert report.summary["accuracy"] == 0.5
    assert report.summary["recall"] == 0.5
    assert report.summary["false_trigger_rate"] == 0.5
    assert report.per_skill["alpha"] == {
        "tp": 1,
        "fp": 1,
        "fn": 0,
        "precision": 0.5,
        "recall": 1.0,
        "f1": 0.667,
    }
    assert report.per_skill["beta"]["recall"] == 0.0
    assert report.by_kind["unrelated"]["accuracy"] == 1.0
    assert [m["case"] for m in report.mistakes] == ["b1", "n2"]


def test_median_latency():
    cases = [Case("a1", "x", ["alpha"])]
    answers = [Answer("a1", t, ["alpha"], "", None, s) for t, s in enumerate([1.0, 9.0, 2.0, 4.0])]
    assert triggers.score(cases, answers, OURS).summary["median_seconds"] == 3.0


def test_consistency_across_trials():
    cases = [Case("a1", "x", ["alpha"]), Case("b1", "y", ["beta"])]
    answers = [
        Answer("a1", 0, ["alpha"], ""),
        Answer("a1", 1, ["alpha"], ""),
        Answer("b1", 0, ["beta"], ""),
        Answer("b1", 1, [], ""),
    ]
    assert triggers.score(cases, answers, OURS).summary["consistency"] == 0.5


def test_markdown_report_lists_mistakes():
    cases = [Case("a1", "about alpha", ["alpha"], "explicit")]
    report = triggers.score(cases, [Answer("a1", 0, [], "", "reply was not JSON")], OURS)
    md = triggers.to_markdown(report, "test run")
    assert "### test run" in md
    assert "| a1 | alpha | none (reply was not JSON) | about alpha |" in md


# --- running -------------------------------------------------------------------------------


def test_run_resumes_and_adds_trials(tmp_path):
    cases = [Case("a1", "about alpha", ["alpha"]), Case("n1", "unrelated", [])]
    provider = ScriptedProvider({"about alpha": ["alpha"]})
    path, answers = triggers.run(cases, CATALOG, provider, 1, tmp_path)
    assert provider.calls == 2 and len(answers) == 2

    _, answers = triggers.run(cases, CATALOG, provider, 1, tmp_path)
    assert provider.calls == 2  # everything was already answered

    _, answers = triggers.run(cases, CATALOG, provider, 2, tmp_path)
    assert provider.calls == 4 and len(answers) == 4
    assert len(path.read_text().splitlines()) == 4


def test_run_keeps_answers_when_the_provider_stops(tmp_path):
    cases = [Case(f"c{i}", f"p{i}", []) for i in range(3)]
    with pytest.raises(ProviderError):
        triggers.run(cases, CATALOG, ScriptedProvider({}, fail_after=2), 1, tmp_path)
    path = triggers.run_path(tmp_path, ScriptedProvider({}), CATALOG)
    assert len(triggers.load_answers(path)) == 2


def test_keyword_baseline_is_deterministic():
    provider = KeywordProvider()
    provider.set_catalog(CATALOG)
    assert json.loads(provider.complete("", "tell me about alpha things")) == {"skills": ["alpha"]}
    assert json.loads(provider.complete("", "zebra")) == {"skills": []}


# --- command line --------------------------------------------------------------------------


def test_cli_keyword_run_writes_answers_and_report(tmp_path, capsys):
    code = main(
        [
            "triggers",
            str(REPO / "skills"),
            "--provider",
            "keyword",
            "--cases",
            str(REPO / "evals/triggers.jsonl"),
            "--distractors",
            str(REPO / "evals/distractors.jsonl"),
            "--out",
            str(tmp_path),
            "--json",
        ]
    )
    assert code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["summary"]["answers"] == 52
    assert Path(result["run"]).with_suffix(".md").is_file()


def test_cli_min_accuracy_gate(tmp_path):
    args = [
        "triggers",
        str(REPO / "skills"),
        "--cases",
        str(REPO / "evals/triggers.jsonl"),
        "--distractors",
        str(REPO / "evals/distractors.jsonl"),
        "--out",
        str(tmp_path),
    ]
    assert main([*args, "--min-accuracy", "0.99"]) == 1
    assert main([*args, "--min-accuracy", "0.1"]) == 0


def test_cli_requires_a_model_for_real_providers(tmp_path, capsys):
    assert main(["triggers", str(REPO / "skills"), "--provider", "ollama"]) == 2
    assert "--model is required" in capsys.readouterr().err


def test_allowed_skills_are_not_penalised():
    cases = [
        Case("r1", "recall dropped overnight", ["beta"], "confusable", ["alpha"]),
        Case("n1", "explain a concept", [], "near-miss", ["alpha"]),
    ]
    answers = [
        Answer("r1", 0, ["beta", "alpha"], ""),  # expected + allowed: correct
        Answer("r1", 1, ["alpha"], ""),  # allowed alone misses the expected skill
        Answer("n1", 0, ["alpha"], ""),  # allowed on a negative: not a false trigger
    ]
    report = triggers.score(cases, answers, OURS)
    assert [m["trial"] for m in report.mistakes] == [1]
    assert report.per_skill["alpha"]["fp"] == 0
    assert report.per_skill["beta"] == {
        "tp": 1,
        "fp": 0,
        "fn": 1,
        "precision": 1.0,
        "recall": 0.5,
        "f1": 0.667,
    }
    assert report.summary["false_trigger_rate"] == 0.0


def test_a_skill_cannot_be_expected_and_allowed(tmp_path):
    path = tmp_path / "cases.jsonl"
    path.write_text(json.dumps({"id": "x", "prompt": "p", "expected": ["a"], "allowed": ["a"]}))
    with pytest.raises(ValueError, match="both expected and allowed"):
        triggers.load_cases(path)


def test_run_files_are_separated_by_case_set(tmp_path):
    provider = ScriptedProvider({})
    default = triggers.run_path(tmp_path, provider, CATALOG)
    hard = triggers.run_path(tmp_path, provider, CATALOG, "triggers-hard")
    assert default.name == f"scripted--m1--{triggers.catalog_hash(CATALOG)}.jsonl"
    assert hard.name == f"scripted--m1--triggers-hard--{triggers.catalog_hash(CATALOG)}.jsonl"
