"""CLI entry point.

  recall index <repo>                 chunk + embed a repo into the Chroma index
  recall ask <repo> "where is X?"     codebase search (grep + semantic)
  recall run <repo> "task..."         run the agent graph on a task
  recall facts <repo>                 list active long-term facts for a repo

`run` pauses at the approval gate (LangGraph interrupt) and asks before
anything is treated as final — in the CLI you are the human in the loop.
"""

from __future__ import annotations

import argparse
import sys
import uuid

from recall.config import load_settings


def cmd_index(args) -> int:
    from recall.memory.index import CodeIndex

    settings = load_settings()
    count = CodeIndex(settings.chroma_dir).index_repo(args.repo)
    print(f"Indexed {count} chunks from {args.repo} -> {settings.chroma_dir}")
    return 0


def cmd_ask(args) -> int:
    from recall.tools import search

    settings = load_settings()
    question = " ".join(args.question)
    hits = search.grep_search(args.repo, question, max_results=10)
    for hit in hits:
        print(f"{hit.file}:{hit.line}: {hit.text}")
    chunks = search.semantic_search(args.repo, question, chroma_dir=settings.chroma_dir)
    for chunk in chunks:
        print(f"\n--- {chunk['file']} (semantic) ---\n{chunk['text'][:600]}")
    if not hits and not chunks:
        print("No hits. For semantic results, index the repo first: recall index <repo>")
    return 0


def cmd_facts(args) -> int:
    from recall.memory.facts import FactStore

    settings = load_settings()
    store = FactStore(settings.facts_db)
    facts = store.active_facts(args.repo)
    if not facts:
        print(f"No facts stored for {args.repo} yet.")
        return 0
    for fact in facts:
        print(f"- [{fact.subject}] {fact.claim}  (from: {fact.source_run})")
    return 0


def cmd_run(args) -> int:
    from langgraph.types import Command

    from recall.graph import build_graph

    settings = load_settings()
    graph = build_graph(settings)
    config = {"configurable": {"thread_id": args.thread or uuid.uuid4().hex[:8]}}
    task = " ".join(args.task)

    result = graph.invoke({"task": task, "repo_path": args.repo, "iteration": 0}, config)

    # Approval gate: the graph pauses with an interrupt payload.
    while result.get("__interrupt__"):
        payload = result["__interrupt__"][0].value
        print("\n=== APPROVAL GATE ===")
        print(f"Task: {payload['task']}")
        print(f"Tests: {payload['test_summary']}")
        print(f"Files touched: {', '.join(payload['files_touched']) or '(none)'}")
        print(payload["diff"] or "(no diff captured yet — executor edit loop is a TODO)")
        answer = input("Approve? [y/N] ").strip().lower()
        note = None if answer == "y" else input("Rejection note for the agent: ").strip()
        result = graph.invoke(
            Command(resume={"approved": answer == "y", "note": note}), config
        )

    print(f"\nFinal status: {result.get('status')}")
    if result.get("error"):
        print(result["error"])
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="recall", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("index", help="chunk + embed a repo into the Chroma index")
    p.add_argument("repo")
    p.set_defaults(func=cmd_index)

    p = sub.add_parser("ask", help="search a repo (grep + semantic)")
    p.add_argument("repo")
    p.add_argument("question", nargs="+")
    p.set_defaults(func=cmd_ask)

    p = sub.add_parser("run", help="run the agent on a task")
    p.add_argument("repo")
    p.add_argument("task", nargs="+")
    p.add_argument("--thread", help="resume an existing checkpointed run by thread id")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("facts", help="list active long-term facts for a repo")
    p.add_argument("repo")
    p.set_defaults(func=cmd_facts)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
