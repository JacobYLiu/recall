"""FastAPI backend (spec Section 4, week 3).

Week-3 deliverable: submit a task, watch nodes execute live (WebSocket
stream of graph events), inspect the diff, approve or reject. This skeleton
wires /health and the run-creation shape; the streaming + approval resume
land in week 3 — see TODOs.
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Recall — coding agent with persistent memory")


class RunRequest(BaseModel):
    repo_path: str
    task: str


class ApprovalRequest(BaseModel):
    approved: bool
    note: str | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/runs")
def create_run(req: RunRequest) -> dict:
    """Start a graph run in the background; returns the thread id.

    TODO(week-3): run the graph with astream_events, publish node events to
    the WebSocket below, and persist the thread so /approve can resume it
    after the approval interrupt fires.
    """
    thread_id = uuid.uuid4().hex[:12]
    return {"thread_id": thread_id, "status": "started", "task": req.task}


@app.post("/runs/{thread_id}/approve")
def approve_run(thread_id: str, req: ApprovalRequest) -> dict:
    """Resume a paused run with the reviewer's decision.

    TODO(week-3): graph.invoke(Command(resume={...}), config=thread_id).
    """
    return {"thread_id": thread_id, "received": req.model_dump(), "status": "todo"}


# TODO(week-3): @app.websocket("/ws/runs/{thread_id}") — stream node events
# (on_chain_start/end per node) so the UI shows the graph working live.
