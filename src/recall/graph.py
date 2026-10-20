"""Graph wiring (spec Section 1).

planner -> executor -> critic --approve--> approval --ok--> memory_writer -> END
                          ^          |                     |
                          |          +--revise-------------+  (rejection note)
                          +---revise (budget permitting)
                          +---replan--> planner

Every run is checkpointed to SQLite; the approval gate pauses via interrupt().
"""

from __future__ import annotations

import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from recall.config import Settings, load_settings
from recall.nodes.approval import approval_node
from recall.nodes.critic import critic_node
from recall.nodes.executor import executor_node
from recall.nodes.memory_writer import memory_writer_node
from recall.nodes.planner import planner_node
from recall.state import AgentState


def _route_after_critic(state: AgentState, settings: Settings) -> str:
    if state.get("iteration", 0) >= settings.max_iterations:
        return "budget"  # graceful stop, scored as a fail by the eval harness
    verdict = state.get("critic_verdict")
    if verdict == "approve":
        return "approval"
    if verdict == "replan":
        return "planner"
    return "executor"  # revise


def _route_after_approval(state: AgentState) -> str:
    return "memory_writer" if state.get("status") == "committing" else "executor"


def _budget_node(state: AgentState) -> dict:
    return {
        "status": "budget_exhausted",
        "error": (
            f"Iteration budget exhausted after {state.get('iteration', 0)} critic loops. "
            f"Last critic notes: {state.get('critic_notes', '')[:500]}"
        ),
    }


def build_graph(settings: Settings | None = None):
    settings = settings or load_settings()
    builder = StateGraph(AgentState)

    builder.add_node("planner", lambda s: planner_node(s, settings=settings))
    builder.add_node("executor", executor_node)
    builder.add_node("critic", critic_node)
    builder.add_node("approval", approval_node)
    builder.add_node("memory_writer", lambda s: memory_writer_node(s, settings=settings))
    builder.add_node("budget", _budget_node)

    builder.add_edge(START, "planner")
    builder.add_edge("planner", "executor")
    # Executor runs one step at a time; when the plan is done it hands to critic.
    builder.add_conditional_edges(
        "executor",
        lambda s: "critic" if s.get("status") == "critiquing" else "executor",
        {"critic": "critic", "executor": "executor"},
    )
    builder.add_conditional_edges(
        "critic",
        lambda s: _route_after_critic(s, settings),
        {"approval": "approval", "executor": "executor", "planner": "planner", "budget": "budget"},
    )
    builder.add_conditional_edges(
        "approval",
        _route_after_approval,
        {"memory_writer": "memory_writer", "executor": "executor"},
    )
    builder.add_edge("memory_writer", END)
    builder.add_edge("budget", END)

    # SqliteSaver.from_conn_string is a context manager in current
    # langgraph-checkpoint-sqlite — construct the saver on a real connection.
    conn = sqlite3.connect(str(settings.checkpoints_db), check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    return builder.compile(checkpointer=checkpointer)
