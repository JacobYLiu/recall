"""Structured long-term fact store — SQLite, stdlib only (spec Section 2).

A fact is a durable statement about a codebase: where something lives, a
convention, a decision and why. Each fact carries its source run, a
timestamp, and a confidence.

Contradiction policy — supersede, never silently overwrite:
a newer fact that conflicts with a stored one wins; the older fact is
marked superseded with a pointer to its replacement, and both stay
queryable. Stale facts are the failure mode reviewers probe; the audit
trail (fact_history) is the answer.
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Fact:
    id: str
    repo: str
    subject: str
    claim: str
    source_run: str
    confidence: float
    created_at: float
    superseded_by: str | None = None  # fact id of the replacement, if superseded

    @property
    def active(self) -> bool:
        return self.superseded_by is None


_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id            TEXT PRIMARY KEY,
    repo          TEXT NOT NULL,
    subject       TEXT NOT NULL,
    claim         TEXT NOT NULL,
    source_run    TEXT NOT NULL,
    confidence    REAL NOT NULL DEFAULT 0.8,
    created_at    REAL NOT NULL,
    superseded_by TEXT REFERENCES facts(id)
);
CREATE INDEX IF NOT EXISTS idx_facts_repo_subject ON facts(repo, subject);
"""


class FactStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # -- writes ---------------------------------------------------------

    def add_fact(
        self,
        repo: str,
        subject: str,
        claim: str,
        source_run: str,
        confidence: float = 0.8,
        supersede_conflicts: bool = False,
    ) -> Fact:
        """Insert a fact. With supersede_conflicts=True, any ACTIVE fact for the
        same repo+subject with a different claim is marked superseded by this
        one (the spec's contradiction policy)."""
        fact = Fact(
            id=uuid.uuid4().hex[:12],
            repo=repo,
            subject=subject,
            claim=claim,
            source_run=source_run,
            confidence=confidence,
            created_at=time.time(),
        )
        if supersede_conflicts:
            for old in self.find_conflicts(repo, subject, claim):
                self._conn.execute(
                    "UPDATE facts SET superseded_by = ? WHERE id = ?", (fact.id, old.id)
                )
        self._conn.execute(
            "INSERT INTO facts (id, repo, subject, claim, source_run, confidence,"
            " created_at, superseded_by) VALUES (?, ?, ?, ?, ?, ?, ?, NULL)",
            (fact.id, fact.repo, fact.subject, fact.claim, fact.source_run,
             fact.confidence, fact.created_at),
        )
        self._conn.commit()
        return fact

    # -- reads ----------------------------------------------------------

    def find_conflicts(self, repo: str, subject: str, new_claim: str) -> list[Fact]:
        """Active facts on the same subject whose claim differs from new_claim.

        Week-2 upgrade (spec Section 2): match on embedding similarity of the
        subject plus an LLM consistency check, not exact subject strings.
        """
        rows = self._conn.execute(
            "SELECT * FROM facts WHERE repo = ? AND subject = ?"
            " AND superseded_by IS NULL AND claim != ?",
            (repo, subject, new_claim),
        ).fetchall()
        return [self._to_fact(r) for r in rows]

    def active_facts(self, repo: str) -> list[Fact]:
        rows = self._conn.execute(
            "SELECT * FROM facts WHERE repo = ? AND superseded_by IS NULL"
            " ORDER BY created_at",
            (repo,),
        ).fetchall()
        return [self._to_fact(r) for r in rows]

    def fact_history(self, repo: str, subject: str) -> list[Fact]:
        """Full chain for a subject — superseded facts included, oldest first."""
        rows = self._conn.execute(
            "SELECT * FROM facts WHERE repo = ? AND subject = ? ORDER BY created_at",
            (repo, subject),
        ).fetchall()
        return [self._to_fact(r) for r in rows]

    def search_facts(self, repo: str, query: str, limit: int = 10) -> list[Fact]:
        """Substring search over subject+claim (active facts only).

        The semantic counterpart lives in the Chroma tier; this is the
        structured lookup used by recall when embeddings are unavailable.
        """
        like = f"%{query}%"
        rows = self._conn.execute(
            "SELECT * FROM facts WHERE repo = ? AND superseded_by IS NULL"
            " AND (subject LIKE ? OR claim LIKE ?) ORDER BY created_at DESC LIMIT ?",
            (repo, like, like, limit),
        ).fetchall()
        return [self._to_fact(r) for r in rows]

    # -- internals ------------------------------------------------------

    @staticmethod
    def _to_fact(row: sqlite3.Row) -> Fact:
        return Fact(
            id=row["id"],
            repo=row["repo"],
            subject=row["subject"],
            claim=row["claim"],
            source_run=row["source_run"],
            confidence=row["confidence"],
            created_at=row["created_at"],
            superseded_by=row["superseded_by"],
        )

    def close(self) -> None:
        self._conn.close()
