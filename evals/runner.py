"""Eval harness runner (spec Section 5) — skeleton.

Per task: reset snapshot -> run agent headlessly (auto-approve) -> apply
hidden test patch -> run hidden tests -> record metrics -> results table.

TODO(week-3): wire run_agent_headless to recall.graph once the executor's
edit loop lands; pull token/cost accounting from LangSmith run metadata.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path


def load_tasks(tasks_dir: Path) -> list[dict]:
    tasks = []
    for folder in sorted(tasks_dir.iterdir()):
        meta_file = folder / "task.json"
        if meta_file.exists():
            tasks.append({**json.loads(meta_file.read_text()), "folder": folder})
    return tasks


def reset_snapshot(snapshot_dir: Path) -> None:
    """Restore the pinned repo snapshot to a clean state."""
    subprocess.run(["git", "checkout", "--", "."], cwd=snapshot_dir, check=True)
    subprocess.run(["git", "clean", "-fd"], cwd=snapshot_dir, check=True)


def run_agent_headless(repo_path: Path, prompt: str, config: dict) -> dict:
    """Run the graph with approval auto-granted and web lookup off.

    Returns final state metrics: iterations used, status.
    TODO(week-3): invoke recall.graph.build_graph with a Command(resume=
    {"approved": True}) loop on interrupts; read cost from LangSmith.
    """
    raise NotImplementedError("Wire to recall.graph in week 3 (see evals/README.md)")


def apply_test_patch(repo_path: Path, patch_file: Path) -> None:
    subprocess.run(["git", "apply", str(patch_file)], cwd=repo_path, check=True)


def score_task(task: dict, config: dict) -> dict:
    started = time.time()
    repo_path = Path(task["repo_snapshot"])
    reset_snapshot(repo_path)
    metrics = run_agent_headless(repo_path, task["prompt"], config)
    apply_test_patch(repo_path, task["folder"] / "test_patch.diff")
    proc = subprocess.run(
        ["python", "-m", "pytest", "-q"], cwd=repo_path, capture_output=True, text=True
    )
    return {
        "id": task["id"],
        "type": task["type"],
        "passed": proc.returncode == 0,
        "iterations": metrics.get("iterations"),
        "cost_usd": metrics.get("cost_usd"),
        "latency_s": round(time.time() - started, 1),
        "budget_exhausted": metrics.get("status") == "budget_exhausted",
    }


def results_table(results: list[dict]) -> str:
    passed = sum(r["passed"] for r in results)
    lines = [
        f"Pass rate: {passed}/{len(results)}",
        "",
        "| Task | Type | Passed | Iterations | Cost | Latency |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['id']} | {r['type']} | {'yes' if r['passed'] else 'no'} "
            f"| {r['iterations']} | {r['cost_usd']} | {r['latency_s']}s |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="evals/config.yaml")
    parser.add_argument("--tasks", default="evals/tasks")
    parser.add_argument("--out", default="evals/results")
    args = parser.parse_args()

    tasks = load_tasks(Path(args.tasks))
    print(f"Loaded {len(tasks)} tasks. Runner wiring lands in week 3 — see evals/README.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
