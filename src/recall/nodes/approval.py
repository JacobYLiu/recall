"""Approval gate (spec Section 3): nothing commits until a human approves.

Uses LangGraph interrupt() — the graph pauses here, checkpointed, and resumes
when the caller supplies a decision. Rejection returns the run to the
executor with the reviewer's note attached.
"""

from __future__ import annotations

from langgraph.types import interrupt

from recall.state import AgentState


def approval_node(state: AgentState) -> dict:
    decision = interrupt(
        {
            "task": state["task"],
            "diff": state.get("diff", ""),
            "files_touched": state.get("files_touched", []),
            "test_summary": state.get("critic_notes", ""),
            # Expected resume payload: {"approved": bool, "note": str | None}
        }
    )
    if decision and decision.get("approved"):
        return {"status": "committing"}
    note = (decision or {}).get("note") or "Rejected by reviewer without a note."
    return {
        "status": "executing",
        "critic_verdict": "revise",
        "critic_notes": f"Reviewer rejected the change: {note}",
        "current_step": 0,
    }
