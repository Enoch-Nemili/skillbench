"""
Helpers for deterministic graders.

Graders never call a model. They look for evidence in the answer (named files, numbers,
specific findings) and, for code, run it. Running model-written code executes it on this
machine: it happens in a temporary folder with a timeout, but only run outcome evals with
providers you trust.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

from skillbench.outcomes import Check

_BLOCK = re.compile(r"```[^\n]*\n(.*?)```", re.S)
_FILE_HEADER = re.compile(r"^\s*(?:#|//)\s*file:\s*([\w./-]+)\s*$", re.I)


def code_blocks(output: str) -> list[str]:
    return _BLOCK.findall(output)


def extract_files(output: str) -> dict[str, str]:
    """Files from fenced blocks whose first line is `# file: name`. Later blocks win."""
    files = {}
    for block in code_blocks(output):
        first, _, rest = block.partition("\n")
        match = _FILE_HEADER.match(first)
        if match:
            files[Path(match.group(1)).name] = rest
    return files


def run_pytest(files: dict[str, str], timeout: float = 60) -> tuple[int, str]:
    """Write files into a fresh folder, run pytest there, return (exit code, output).

    Exit codes: 0 all passed, 1 some failed, 2+ collection error, interrupted or no tests.
    """
    with tempfile.TemporaryDirectory(prefix="skillbench-") as tmp:
        for name, content in files.items():
            (Path(tmp) / name).write_text(content, encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--rootdir", tmp],
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return 124, f"timed out after {timeout}s"
        return proc.returncode, (proc.stdout + proc.stderr)[-2000:]


def mentions(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.I | re.S) is not None


def check_mentions(name: str, text: str, pattern: str) -> Check:
    match = re.search(pattern, text, re.I | re.S)
    return Check(name, match is not None, match.group(0)[:80] if match else "not mentioned")


def numbers(text: str) -> list[float]:
    """Every number in the text; percentages are returned as fractions too (85% -> 85, 0.85)."""
    found = []
    for raw, pct in re.findall(r"(?<![\w.])(\d+(?:\.\d+)?)(\s*%)?", text):
        value = float(raw)
        found.append(value)
        if pct:
            found.append(value / 100)
    return found


def has_number(text: str, target: float, tolerance: float) -> bool:
    return any(abs(n - target) <= tolerance for n in numbers(text))


def code_check_suite(
    output: str, module_name: str, buggy_source: str, hidden_tests: str
) -> list[Check]:
    """Shared grader for 'fix this bug' tasks: is there a fix, a test, and does the test
    fail on the bug and pass on the fix (a real reproduction), and does the fix pass our tests?"""
    files = extract_files(output)
    fix = files.get(module_name)
    tests = {n: c for n, c in files.items() if n.startswith("test_") and n.endswith(".py")}
    checks = [Check("fix_provided", fix is not None, module_name if fix else "no fixed module")]
    if fix is not None:
        code, log = run_pytest({module_name: fix, "test_hidden.py": hidden_tests})
        checks.append(
            Check("fix_passes_hidden_tests", code == 0, log.splitlines()[-1] if log else "")
        )
    else:
        checks.append(Check("fix_passes_hidden_tests", False, "no fix to test"))
    checks.append(Check("test_written", bool(tests), ", ".join(tests) or "no test file"))
    if tests:
        code, log = run_pytest({module_name: buggy_source, **tests})
        # Exit code 1 = tests ran and failed. A collection error (2) fails for the wrong reason.
        checks.append(Check("test_fails_on_bug", code == 1, f"exit {code}"))
        if fix is not None:
            code, log = run_pytest({module_name: fix, **tests})
            checks.append(Check("test_passes_on_fix", code == 0, f"exit {code}"))
        else:
            checks.append(Check("test_passes_on_fix", False, "no fix"))
    else:
        checks.append(Check("test_fails_on_bug", False, "no test"))
        checks.append(Check("test_passes_on_fix", False, "no test"))
    return checks
