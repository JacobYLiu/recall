"""Memory writer node: runs after a commit is approved (spec Section 2).

Extracts durable facts from the run and writes them to long-term memory.
Only facts tied to an APPROVED change are stored. Contradictions never
silently overwrite — the newer fact wins and the older one is marked
superseded with a pointer to its replacement (see recall.memory.facts).
"""

from __future__ import annotations

from recall.memory.facts import FactStore
from recall.state import AgentState

EXTRACT_PROMPT = """From this completed coding run, extract durable facts about the codebase —
conventions, where things live, decisions and why. One fact per line as:
subject | claim
Only facts that will still matter in a future session. No task narration.

Task: {task}
Diff:
{diff}
"""


def memory_writer_node(state: AgentState, *, settings=None) -> dict:
    from recall.config import load_settings
    from recall.llm import get_llm, llm_available

    settings = settings or load_settings()
    store = FactStore(settings.facts_db)
    repo = state["repo_path"]
    source_run = state.get("task", "")[:80]

    candidates: list[tuple[str, str]] = []
    if llm_available() and state.get("diff"):
        llm = get_llm(settings.model)
        response = llm.invoke(
            EXTRACT_PROMPT.format(task=state["task"], diff=state["diff"][:6000])
        )
        text = response.content if isinstance(response.content, str) else str(response.content)
        for line in text.splitlines():
            if "|" in line:
                subject, claim = (part.strip() for part in line.split("|", 1))
                if subject and claim:
                    candidates.append((subject, claim))
    # TODO(week-2): replace the "same subject" conflict check in
    # FactStore.check_conflicts with embedding similarity + an LLM
    # consistency check, per spec Section 2.

    for subject, claim in candidates:
        # find_conflicts returns active facts on the same subject whose claim
        # differs — those get superseded inside add_fact.
        store.add_fact(
            repo=repo,
            subject=subject,
            claim=claim,
            source_run=source_run,
            supersede_conflicts=True,
        )

    # TODO(week-2): re-index changed files into the Chroma code index
    # (recall.memory.index.CodeIndex.index_files) so search reflects the commit.
    return {"status": "done"}
