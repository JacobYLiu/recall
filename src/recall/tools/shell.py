"""Allowlisted shell tool (spec Section 1): git diff, git status, ls only.

No network, no package installs mid-run. Anything off the allowlist raises.
In production these run inside the Docker sandbox (recall.sandbox.runner);
the allowlist is enforced here regardless of where execution happens.
"""

from __future__ import annotations

import subprocess

ALLOWED_PREFIXES: tuple[tuple[str, ...], ...] = (
    ("git", "diff"),
    ("git", "status"),
    ("ls",),
)


def run_allowlisted(repo_path: str, argv: list[str], timeout: int = 60) -> str:
    if not any(tuple(argv[: len(prefix)]) == prefix for prefix in ALLOWED_PREFIXES):
        raise PermissionError(
            f"Command not on the allowlist: {' '.join(argv)}. "
            f"Allowed: {[' '.join(p) for p in ALLOWED_PREFIXES]}"
        )
    proc = subprocess.run(argv, cwd=repo_path, capture_output=True, text=True, timeout=timeout)
    return (proc.stdout + proc.stderr).strip()
