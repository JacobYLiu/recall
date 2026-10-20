"""Typed graph state (spec Section 1).

State is carried through every node and checkpointed by LangGraph, so a
crashed or paused run resumes from the last completed node.
"""

from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

RunStatus = Literal[
    "planning",
    "executing",
    "critiquing",
    "awaiting_approval",
    "committing",
    "done",
    "failed",
    "budget_exhausted",
]

CriticVerdict = Literal["approve", "revise", "replan"]


class TestResult(TypedDict, total=False):
    command: str
    passed: bool
    summary: str  # e.g. "3 passed, 1 failed"
    output: str  # captured stdout/stderr (tail)


class AgentState(TypedDict, total=False):
    # Inputs
    task: str
    repo_path: str

    # Planner
    plan: list[str]
    current_step: int

    # Executor
    files_touched: Annotated[list[str], operator.add]
    diff: str

    # Critic
    test_results: list[TestResult]
    critic_notes: str
    critic_verdict: CriticVerdict | None

    # Control
    iteration: int
    status: RunStatus
    error: str | None

    # Memory (spec Section 2)
    memory_context: str  # facts + code chunks injected before planning
