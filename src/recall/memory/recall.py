"""Recall: build the memory_context the planner sees (spec Section 2, step 1).

Combines active structured facts with relevant code chunks from the Chroma
index. Degrades gracefully to facts-only when Chroma is unavailable, so the
agent still runs on a fresh machine.
"""

from __future__ import annotations

from pathlib import Path

from recall.memory.facts import FactStore

MAX_FACTS = 15
MAX_CHUNKS = 6


def build_memory_context(
    store: FactStore,
    repo_path: str,
    task: str,
    chroma_dir: str | Path | None = None,
) -> str:
    sections: list[str] = []

    # Facts: keyword search on the task text, topped up with recent facts.
    seen: set[str] = set()
    facts = []
    for word in task.split():
        for fact in store.search_facts(repo_path, word, limit=5):
            if fact.id not in seen:
                seen.add(fact.id)
                facts.append(fact)
    if len(facts) < MAX_FACTS:
        for fact in store.active_facts(repo_path):
            if fact.id not in seen:
                seen.add(fact.id)
                facts.append(fact)
            if len(facts) >= MAX_FACTS:
                break
    if facts:
        lines = [f"- [{f.subject}] {f.claim} (confidence {f.confidence:.1f})" for f in facts]
        sections.append("Known facts about this codebase:\n" + "\n".join(lines))

    # Code chunks: semantic search, when the index exists.
    if chroma_dir is not None and Path(chroma_dir).exists():
        try:
            from recall.memory.index import CodeIndex

            chunks = CodeIndex(chroma_dir).query(task, k=MAX_CHUNKS)
            if chunks:
                body = "\n\n".join(f"# {c['file']}\n{c['text']}" for c in chunks)
                sections.append("Relevant code:\n" + body)
        except Exception:
            pass  # recall must never crash a run — facts-only is fine

    return "\n\n".join(sections)
