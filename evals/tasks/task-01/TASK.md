# Task 01 — Bug fix: off-by-one / boundary error

**Pattern (spec Section 5, task #1):** instantiate against one of your pinned
repos. Find a core function with a boundary error (or introduce one at the
pinned commit and revert it in the snapshot), with a failing test that
already exists.

**To instantiate:**
1. Pick the target function and write the failing case.
2. Put the hidden test in `test_patch.diff` (applied after the agent commits).
3. Fill in `task.json` — `repo_snapshot` points at the snapshot dir from
   `evals/config.yaml`.
4. The prompt below is the exact text the agent receives — keep it honest:
   describe the symptom, not the fix.
