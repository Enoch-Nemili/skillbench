"""Tests for the script bundled with the retrieval-eval skill."""

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/retrieval-eval/scripts/retrieval_metrics.py"
spec = importlib.util.spec_from_file_location("retrieval_metrics", SCRIPT)
rm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rm)


def row(query, expected, ranked):
    return {"query": query, "expected": expected, "ranked": ranked}


def test_first_hit_rank():
    assert rm.first_hit_rank(["a", "b", "c"], "b") == 2
    assert rm.first_hit_rank(["a", "a", "b"], "b") == 3
    assert rm.first_hit_rank(["a"], "z") is None
    assert rm.first_hit_rank(["a", "b"], ["z", "b"]) == 2


def test_score():
    rows = [
        row("q1", "a", ["a", "b"]),  # rank 1
        row("q2", "b", ["a", "b"]),  # rank 2
        row("q3", "c", ["a", "b"]),  # miss
        row("q4", "d", ["x"] * 5 + ["d"]),  # rank 6: outside top 5
    ]
    result = rm.score(rows, k=5)
    assert result["hit@1"] == pytest.approx(0.25)
    assert result["recall@5"] == pytest.approx(0.5)
    assert result["mrr"] == pytest.approx((1 + 0.5 + 0 + 1 / 6) / 4)
    assert result["misses"] == ["q3", "q4"]


def test_compare_wins_and_losses():
    base = [row("q1", "a", ["b", "a"]), row("q2", "b", ["b"]), row("q3", "c", ["c"])]
    cand = [row("q1", "a", ["a"]), row("q2", "b", ["a", "b"]), row("q3", "c", ["c"])]
    result = rm.compare(base, cand)
    assert [w["query"] for w in result["wins"]] == ["q1"]
    assert [loss["query"] for loss in result["losses"]] == ["q2"]
    assert result["delta"]["mrr"] == pytest.approx(0.0)


def test_compare_rejects_different_query_sets():
    with pytest.raises(ValueError, match="different queries"):
        rm.compare([row("q1", "a", ["a"])], [row("q2", "a", ["a"])])


def test_cli_score_json(tmp_path, capsys):
    run = tmp_path / "run.jsonl"
    run.write_text("\n".join(json.dumps(r) for r in [row("q", "a", ["a"])]) + "\n")
    assert rm.main(["score", str(run), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["hit@1"] == 1.0


def test_cli_reports_bad_file(tmp_path, capsys):
    run = tmp_path / "run.jsonl"
    run.write_text('{"query": "q"}\n')
    assert rm.main(["score", str(run)]) == 2
    assert "missing" in capsys.readouterr().err
