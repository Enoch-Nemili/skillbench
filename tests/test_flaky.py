"""Tests for the flaky-run script bundled with the repro-before-fix skill."""

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills/repro-before-fix/scripts/flaky.py"
spec = importlib.util.spec_from_file_location("flaky", SCRIPT)
flaky = importlib.util.module_from_spec(spec)
sys.modules["flaky"] = flaky
spec.loader.exec_module(flaky)

PY = sys.executable


def test_signature_is_last_nonempty_line():
    assert flaky.signature("collected 3\n\nAssertionError: boom\n\n") == "AssertionError: boom"
    assert flaky.signature("") == "(no output)"


def test_always_passes(capsys):
    assert flaky.main(["--runs", "3", "--", PY, "-c", "pass"]) == 0
    assert "3/3 passed: ALWAYS PASSES" in capsys.readouterr().out


def test_always_fails_groups_the_signature(capsys):
    code = flaky.main(["--runs", "3", "--", PY, "-c", "raise SystemExit('db gone')"])
    assert code == 1
    out = capsys.readouterr().out
    assert "0/3 passed: ALWAYS FAILS" in out
    assert "3x  exit 1: db gone" in out


def test_flaky_alternating_command(tmp_path):
    counter = tmp_path / "n"
    counter.write_text("0")
    script = (
        "import pathlib, sys\n"
        f"p = pathlib.Path({str(counter)!r})\n"
        "n = int(p.read_text()) + 1\n"
        "p.write_text(str(n))\n"
        "sys.exit(n % 2)\n"
    )
    report = flaky.run_many([PY, "-c", script], runs=4, timeout=30)
    assert report["verdict"] == "flaky"
    assert report["passed"] == 2


def test_timeout_counts_as_failure():
    report = flaky.run_many([PY, "-c", "import time; time.sleep(5)"], runs=1, timeout=0.2)
    assert report["verdict"] == "always fails"
    assert list(report["failure_signatures"]) == ["timed out after 0.2s"]


def test_usage_errors(capsys):
    assert flaky.main(["--runs", "3"]) == 2
    assert flaky.main(["--runs", "0", "--", PY, "-c", "pass"]) == 2
    assert flaky.main(["--", "definitely-not-a-real-command-xyz"]) == 2
