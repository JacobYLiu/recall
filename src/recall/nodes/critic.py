"""Critic node: independent verification — never grades the executor's summary.

Spec Section 1: runs targeted tests, then the full suite, and judges against
the plan and the test output. Verdicts:
  approve -> approval gate
  revise  -> back to executor with a specific failure to fix
  replan  -> back to planner (the plan itself was wrong)
"""

from __future__ import annotations

from recall.state import AgentState
from recall.tools import tests as tests_tool

MAX_OUTPUT_CHARS = 4000  # keep critic notes focused; full output lives in the trace


def critic_node(state: AgentState) -> dict:
    result = tests_tool.run_tests(state["repo_path"])
    history = [*state.get("test_results", []), result]
    iteration = state.get("iteration", 0) + 1

    if result["passed"]:
        return {
            "test_results": history,
            "iteration": iteration,
            "critic_verdict": "approve",
            "critic_notes": f"Suite green: {result['summary']}",
            "status": "awaiting_approval",
        }

    # TODO(week-2): LLM judgment pass — classify the failure as
    #   revise (implementation wrong, plan fine) vs replan (plan wrong),
    # using the plan + the failing output below, instead of always "revise".
    notes = (
        f"Tests failing ({result['summary']}). Fix the specific failure; "
        f"do not restart the task.\n--- output tail ---\n{result['output'][-MAX_OUTPUT_CHARS:]}"
    )
    return {
        "test_results": history,
        "iteration": iteration,
        "critic_verdict": "revise",
        "critic_notes": notes,
        "status": "executing",
    }
