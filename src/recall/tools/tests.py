"""Test execution tool (spec Section 1): pytest, output captured into state.

A failing run is data for the critic, not a crash — this tool returns a
TestResult either way and only raises on infrastructure errors.
"""

from __future__ import annotations

import re
import subprocess
import sys

from recall.state import TestResult

DEFAULT_TIMEOUT = 600


def run_tests(repo_path: str, target: str | None = None, timeout: int = DEFAULT_TIMEOUT) -> TestResult:
    """Run pytest in repo_path (optionally a single file/test)."""
    command = [sys.executable, "-m", "pytest", "-q"]
    if target:
        command.append(target)
    try:
        proc = subprocess.run(
            command, cwd=repo_path, capture_output=True, text=True, timeout=timeout
        )
        output = (proc.stdout + proc.stderr).strip()
        passed = proc.returncode == 0
    except subprocess.TimeoutExpired:
        output = f"pytest timed out after {timeout}s"
        passed = False
    return TestResult(
        command=" ".join(command),
        passed=passed,
        summary=_summarize(output, passed),
        output=output,
    )


def _summarize(output: str, passed: bool) -> str:
    match = re.search(r"(\d+ passed[^\n]*|\d+ failed[^\n]*|no tests ran)", output)
    if match:
        return match.group(0).strip()
    return "passed" if passed else "failed (no pytest summary line found)"
