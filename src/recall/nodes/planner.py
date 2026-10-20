"""Planner node: recall memory, then decompose the task before any edit.

Spec Section 1: the planner prevents random-walk editing. It re-plans ONLY
when the critic reports the plan itself was wrong (verdict == "replan").
"""

from __future__ import annotations

from recall.llm import get_llm, llm_available
from recall.memory.facts import FactStore
from recall.memory.recall import build_memory_context
from recall.state import AgentState

PLANNER_PROMPT = """You are the planner for a coding agent working in the repo at {repo_path}.

Task: {task}

What long-term memory recalls about this codebase:
{memory_context}

Produce a numbered plan: files to inspect, the change to make, tests to run.
Be specific about file paths. Do not write code — plan only.
Respond with one step per line, no preamble."""


def planner_node(state: AgentState, *, settings=None) -> dict:
    from recall.config import load_settings

    settings = settings or load_settings()

    # 1. Recall (spec Section 2): facts + code chunks injected before planning.
    memory_context = state.get("memory_context") or build_memory_context(
        store=FactStore(settings.facts_db),
        repo_path=state["repo_path"],
        task=state["task"],
    )

    # 2. Plan. Falls back to a stub plan when no API key is configured, so the
    #    graph can be smoke-tested end-to-end without spending tokens.
    if llm_available():
        llm = get_llm(settings.model)
        prompt = PLANNER_PROMPT.format(
            repo_path=state["repo_path"],
            task=state["task"],
            memory_context=memory_context or "(nothing recalled)",
        )
        response = llm.invoke(prompt)
        text = response.content if isinstance(response.content, str) else str(response.content)
        plan = [line.strip(" -") for line in text.splitlines() if line.strip()]
        # TODO(week-1): switch to structured output (a Plan pydantic model via
        # llm.with_structured_output) instead of line-splitting free text.
    else:
        plan = [
            f"Explore the codebase for code relevant to: {state['task']}",
            "Make the smallest change that satisfies the task",
            "Run the test suite",
        ]

    return {
        "plan": plan,
        "current_step": 0,
        "memory_context": memory_context,
        "status": "executing",
    }
