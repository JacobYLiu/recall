# Recall — a coding agent with persistent memory

A LangGraph coding agent that plans, edits, tests, and iterates on real
Python repositories — and **remembers the codebase across sessions**. When a
fact it stored turns out to be wrong, it doesn't silently overwrite: the new
fact wins, the old one is marked *superseded* with a pointer to its
replacement, and both stay auditable.

Nothing commits without a human approving the diff.

## Architecture

```
                 recall (long-term memory)
        ┌──────────────────────────────────────────┐
        │  Chroma code index   +   SQLite fact table │
        │  (embeddings)            (supersede,     │
        │                           never overwrite)│
        └───────────────▲──────────────────────────┘
                        │ facts + code chunks
   task ──► PLANNER ──► EXECUTOR ──► CRITIC ──approve──► APPROVAL GATE
              ▲            ▲            │              (human, interrupt())
              │            └──revise────┘                     │
              └──replan────┘                    approve ──► MEMORY WRITER
                                                   │          (write-back)
                              max 5 critic loops ───┘
                              hard cost ceiling · Docker sandbox ·
                              LangSmith trace on every run
```

- **Planner** decomposes the task before any edit; re-plans only when the
  critic says the plan itself was wrong.
- **Executor** runs one plan step at a time, inside a Docker sandbox. Edits
  are exact-match patches — diffs stay small and reviewable.
- **Critic** is independent: it runs the test suite and judges against the
  plan and test output, never the executor's own summary.
- **Approval gate** pauses the graph (LangGraph `interrupt()`) and shows the
  full diff. Rejection sends the run back with the reviewer's note.
- **Memory writer** extracts durable facts from approved runs only.

## Eval results

<!-- First full run goes here — publish it even if the number is mediocre,
     then show the delta after one improvement. See evals/README.md. -->

| Run | Date | Model | Pass rate (of 20) | Mean iterations | Mean cost/task |
|---|---|---|---|---|---|
| — | — | — | — | — | — |

Metrics per run: pass rate (broken out by bug fix / feature / refactor /
memory), iterations to green, cost and latency per task, budget
exhaustions — reported, not hidden.

## Quickstart

```bash
cp .env.example .env          # add ANTHROPIC_API_KEY (or OPENAI_API_KEY) + LANGSMITH_API_KEY
pip install -e ".[dev]"

recall index /path/to/repo                    # chunk + embed a repo
recall ask /path/to/repo "where is auth handled?"
recall run /path/to/repo "fix the failing boundary test"
recall facts /path/to/repo                    # what the agent remembers
```

## Repo layout

```
src/recall/
  state.py        typed graph state (checkpointed)
  graph.py        planner -> executor -> critic -> approval -> memory writer
  nodes/          planner, executor, critic, approval, memory_writer
  tools/          search (ripgrep + semantic), exact-match patch, pytest, allowlisted shell
  memory/         facts.py (SQLite, supersede policy) · index.py (Chroma) · recall.py
  sandbox/        Docker runner — one container per run, no host credentials
  cli.py          index / ask / run / facts
api/main.py       FastAPI backend (week 3: live node streaming + approve/reject UI)
evals/            20-task harness: task folders, runner, results table
tests/            unit tests — fact-store supersede policy first
```

## Failure modes observed

<!-- Spec deliverable: the two worst failure modes from real eval runs, and
     what changed because of them. Fill in after the first full run —
     interviewers ask for exactly this. -->

1. _TBD after first eval run._
2. _TBD after first eval run._

## Build status

- [x] Repo scaffold: graph, nodes, tools, memory layer, CLI
- [ ] Week 1: repo explorer + first end-to-end edit on a real repo, traced
- [ ] Week 2: critic loop, approval gate, memory write-back demo (session 2 uses a session-1 fact)
- [ ] Week 3: eval harness full run + FastAPI UI + deployed demo
