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


_FENCE = re.compile(r"^\s*```")
_BARE_FENCE = re.compile(r"^\s*```\s*$")


def _header(line: str) -> str | None:
    match = _FILE_HEADER.match(line)
    return Path(match.group(1)).name if match else None


def _trim_prose(name: str, lines: list[str]) -> list[str]:
    """An unfenced file runs until the next header or fence, so prose after it can tag along.
    For Python, keep the longest prefix ending at a blank line that compiles."""
    while lines and not lines[-1].strip():
        lines = lines[:-1]
    if not name.endswith(".py"):
        return lines
    cuts = [len(lines)] + [i for i in range(len(lines) - 1, 0, -1) if not lines[i].strip()]
    for cut in cuts:
        try:
            compile("\n".join(lines[:cut]), name, "exec")
            return lines[:cut]
        except (SyntaxError, ValueError):
            continue
    return lines  # nothing compiles: keep it all and let the tests fail on the real code


def extract_files(output: str) -> dict[str, str]:
    """Files the answer writes, named by a `# file: name` (or `// file: name`) header line.

    Accepted layouts (models were asked for the first one but produce all three):
      1. a fenced block whose first line is the header;
      2. the header on its own line, then a fenced block;
      3. the header, then unfenced code up to the next header or fence.
    Fenced blocks without a header are ignored. Later files with the same name win.
    """
    lines = output.splitlines()
    files: dict[str, str] = {}
    pending: str | None = None  # a header seen just before a fence
    i = 0
    while i < len(lines):
        line = lines[i]
        if _FENCE.match(line):
            end = next((j for j in range(i + 1, len(lines)) if _FENCE.match(lines[j])), len(lines))
            body = lines[i + 1 : end]
            name = _header(body[0]) if body else None
            if name:
                body = body[1:]
            name = name or pending
            if name:
                files[name] = "\n".join(body) + "\n"
            pending = None
            i = end + 1
            continue
        name = _header(line)
        if name:
            nxt = next((j for j in range(i + 1, len(lines)) if lines[j].strip()), len(lines))
            if nxt < len(lines) and _FENCE.match(lines[nxt]):
                pending = name  # layout 2
                i = nxt
                continue
            stops = (
                j for j in range(i + 1, len(lines)) if _header(lines[j]) or _FENCE.match(lines[j])
            )
            end = next(stops, len(lines))
            body = _trim_prose(name, lines[i + 1 : end])
            if body:
                files[name] = "\n".join(body) + "\n"
            # A bare ``` right after unfenced code is a stray closing fence, not a new block.
            i = end + 1 if end < len(lines) and _BARE_FENCE.match(lines[end]) else end
            continue
        if line.strip():
            pending = None
        i += 1
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
