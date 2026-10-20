"""Executor node: runs ONE plan step per invocation.

Spec Section 1: all file writes and shell commands happen inside the Docker
sandbox (see recall.sandbox.runner). Edits are exact-match patches, never
whole-file rewrites, so diffs stay reviewable.

Week-1 state: context gathering (search + read) is wired; the LLM tool-calling
edit loop is the main TODO — see the marked block below.
"""

from __future__ import annotations

from recall.state import AgentState
from recall.tools import search


def executor_node(state: AgentState) -> dict:
    plan = state.get("plan", [])
    step_idx = state.get("current_step", 0)
    if step_idx >= len(plan):
        return {"status": "critiquing"}

    step = plan[step_idx]
    repo = state["repo_path"]

    # Gather context for this step: ranked file/line hits for the step text.
    hits = search.grep_search(repo, step.split(":")[0], max_results=10)
    files_touched = [h.file for h in hits]

    # TODO(week-1): the real edit loop.
    #   1. Build a tool-calling LLM (llm.bind_tools([...])) with:
    #      tools.files.read_file, tools.files.apply_patch,
    #      tools.tests.run_tests, tools.shell.run_allowlisted
    #   2. Let it work this single step, executing every tool call through
    #      recall.sandbox.runner so nothing touches the host directly.
    #   3. Collect the resulting diff into state["diff"] (git diff in sandbox)
    #      and the files actually edited into state["files_touched"].
    # Until then this node only reconnoiters, which is enough to exercise the
    # graph, the critic loop, and the approval gate.

    return {
        "current_step": step_idx + 1,
        "files_touched": files_touched,
        "status": "executing" if step_idx + 1 < len(plan) else "critiquing",
    }
