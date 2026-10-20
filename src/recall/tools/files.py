"""File read/edit tools (spec Section 1). Stdlib only.

Edits are exact-match patches — never whole-file rewrites — so every change
produces a small, reviewable diff. A patch must match EXACTLY ONCE in the
file; ambiguous or missing matches raise instead of guessing.
"""

from __future__ import annotations

import difflib
from pathlib import Path


def read_file(path: str, start: int | None = None, end: int | None = None) -> str:
    """Read a file, optionally a 1-based inclusive line range, with line numbers."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    lo = (start or 1) - 1
    hi = end or len(lines)
    selected = lines[lo:hi]
    return "\n".join(f"{lo + i + 1:>5}  {line}" for i, line in enumerate(selected))


def apply_patch(path: str, old: str, new: str) -> str:
    """Replace the single exact occurrence of `old` with `new`. Returns a unified diff."""
    file = Path(path)
    before = file.read_text(encoding="utf-8")
    count = before.count(old)
    if count == 0:
        raise ValueError(f"Patch target not found in {path}")
    if count > 1:
        raise ValueError(
            f"Patch target matches {count} times in {path} — include more context so it is unique"
        )
    after = before.replace(old, new, 1)
    file.write_text(after, encoding="utf-8")
    return make_unified_diff(before, after, str(path))


def make_unified_diff(before: str, after: str, path: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )
