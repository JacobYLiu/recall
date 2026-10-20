"""Codebase search tool (spec Section 1): ripgrep + semantic search.

Executor-only. Returns ranked file/line hits. Stdlib only — ripgrep is
invoked as a subprocess, with a pure-Python fallback when rg is absent.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SearchHit:
    file: str  # path relative to the repo root
    line: int
    text: str


def grep_search(repo_path: str, pattern: str, max_results: int = 50) -> list[SearchHit]:
    """Literal/regex search over the repo. Empty pattern -> no hits."""
    if not pattern.strip():
        return []
    repo = Path(repo_path)
    if shutil.which("rg"):
        proc = subprocess.run(
            ["rg", "--no-heading", "--line-number", "--max-count", "5", "-e", pattern, "."],
            cwd=repo, capture_output=True, text=True, timeout=60,
        )
        hits = []
        for line in proc.stdout.splitlines():
            parts = line.split(":", 2)
            if len(parts) == 3 and parts[1].isdigit():
                hits.append(SearchHit(file=parts[0], line=int(parts[1]), text=parts[2].strip()))
            if len(hits) >= max_results:
                break
        return hits
    return _python_grep(repo, pattern, max_results)


def _python_grep(repo: Path, pattern: str, max_results: int) -> list[SearchHit]:
    try:
        regex = re.compile(pattern)
    except re.error:
        regex = re.compile(re.escape(pattern))
    hits: list[SearchHit] = []
    for path in sorted(repo.rglob("*.py")):
        if any(part in {".git", "__pycache__", ".venv"} for part in path.parts):
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, start=1):
            if regex.search(line):
                hits.append(SearchHit(str(path.relative_to(repo)), i, line.strip()))
                if len(hits) >= max_results:
                    return hits
    return hits


def semantic_search(repo_path: str, query: str, k: int = 8, chroma_dir=None) -> list[dict]:
    """Semantic search over the Chroma code index. Returns [] if no index exists."""
    if chroma_dir is None or not Path(chroma_dir).exists():
        return []
    from recall.memory.index import CodeIndex

    return CodeIndex(chroma_dir).query(query, k=k)
