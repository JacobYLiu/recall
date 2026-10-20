"""Chroma code index (spec Section 2): chunked, embedded repo files.

Re-indexed on commit so semantic search reflects the current tree.
Chroma is imported lazily — the rest of the memory layer works without it.
"""

from __future__ import annotations

from pathlib import Path

CHUNK_LINES = 120
CHUNK_OVERLAP = 20
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules", ".recall"}


def chunk_text(text: str, chunk_lines: int = CHUNK_LINES, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split file text into overlapping line windows."""
    lines = text.splitlines()
    if not lines:
        return []
    step = max(1, chunk_lines - overlap)
    return ["\n".join(lines[i : i + chunk_lines]) for i in range(0, len(lines), step)]


class CodeIndex:
    def __init__(self, persist_dir: str | Path, collection: str = "code"):
        import chromadb  # lazy: heavy dependency, only needed for semantic search

        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._client.get_or_create_collection(collection)

    def index_repo(self, repo_path: str | Path, extensions: tuple[str, ...] = (".py",)) -> int:
        """Chunk + embed every matching file under repo_path. Returns chunk count."""
        repo = Path(repo_path)
        count = 0
        for path in sorted(repo.rglob("*")):
            if path.is_dir() or path.suffix not in extensions:
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            count += self.index_file(path, repo)
        return count

    def index_file(self, path: Path, repo_root: Path) -> int:
        rel = str(path.relative_to(repo_root))
        chunks = chunk_text(path.read_text(encoding="utf-8", errors="ignore"))
        if not chunks:
            return 0
        self._collection.upsert(
            ids=[f"{rel}::{i}" for i in range(len(chunks))],
            documents=chunks,
            metadatas=[{"file": rel, "chunk": i} for i in range(len(chunks))],
        )
        return len(chunks)

    def index_files(self, repo_path: str | Path, files: list[str]) -> int:
        """Re-index specific files (called by the memory writer after a commit)."""
        repo = Path(repo_path)
        return sum(self.index_file(repo / f, repo) for f in files if (repo / f).exists())

    def query(self, text: str, k: int = 8) -> list[dict]:
        result = self._collection.query(query_texts=[text], n_results=k)
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        return [{"text": d, **m} for d, m in zip(docs, metas)]
