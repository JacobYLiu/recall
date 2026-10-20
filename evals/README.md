# Eval harness (spec Section 5)

A script, not a notebook. Each task is a folder under `tasks/`:

```
tasks/task-01/
  task.json      # {id, type, repo, prompt}
  test_patch.diff  # hidden tests, applied AFTER the agent commits
```

The runner resets the repo snapshot, runs the agent headlessly (approval
auto-granted, web lookup off), applies the test patch, runs the hidden
tests, and records: pass/fail, iterations to green, cost, latency,
budget exhaustions. Output: `results/results.json` + a Markdown table
for the README.

## Pinning repos

Pick 4 small, well-tested, pure-Python repos (spec Section 5) and record
exact names + commit hashes in `config.yaml` (copy `config.example.yaml`).
Keep each under ~20k lines so indexing and tests stay fast.

## Running

```bash
python -m evals.runner --config evals/config.yaml
```

Publish the first full run even if the pass rate is mediocre — then improve
one thing, re-run, and show both rows in the README.
