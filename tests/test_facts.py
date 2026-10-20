"""Unit tests for the fact store — the supersede policy is the differentiator,
so it is tested first (spec Section 2). Stdlib only: runs with no API keys
and no heavy deps installed.
"""

from recall.memory.facts import FactStore


def make_store(tmp_path) -> FactStore:
    return FactStore(tmp_path / "facts.sqlite3")


def test_add_and_list_active(tmp_path):
    store = make_store(tmp_path)
    store.add_fact("repo", "auth", "auth uses JWT middleware in app/auth.py", "run-1")
    active = store.active_facts("repo")
    assert len(active) == 1
    assert active[0].claim.startswith("auth uses JWT")
    assert active[0].active


def test_supersede_marks_old_and_keeps_history(tmp_path):
    store = make_store(tmp_path)
    old = store.add_fact("repo", "auth", "auth uses sessions", "run-1")
    new = store.add_fact(
        "repo", "auth", "auth uses JWT middleware", "run-2", supersede_conflicts=True
    )
    active = store.active_facts("repo")
    assert [f.id for f in active] == [new.id]

    history = store.fact_history("repo", "auth")
    assert len(history) == 2
    by_id = {f.id: f for f in history}
    assert by_id[old.id].superseded_by == new.id  # pointer to the replacement
    assert by_id[new.id].superseded_by is None


def test_same_claim_is_not_a_conflict(tmp_path):
    store = make_store(tmp_path)
    store.add_fact("repo", "auth", "auth uses JWT", "run-1")
    store.add_fact("repo", "auth", "auth uses JWT", "run-2", supersede_conflicts=True)
    # Identical claim re-asserted: find_conflicts only matches DIFFERING
    # claims, so nothing is superseded and no conflict is reported.
    # (Dedup of identical re-assertions is a week-2 refinement.)
    assert store.find_conflicts("repo", "auth", "auth uses JWT") == []
    assert len(store.active_facts("repo")) == 2


def test_search_facts(tmp_path):
    store = make_store(tmp_path)
    store.add_fact("repo", "testing", "tests run with pytest -q", "run-1")
    store.add_fact("repo", "style", "prefer factory functions over classes", "run-1")
    hits = store.search_facts("repo", "pytest")
    assert len(hits) == 1
    assert hits[0].subject == "testing"


def test_facts_are_repo_scoped(tmp_path):
    store = make_store(tmp_path)
    store.add_fact("repo-a", "auth", "uses JWT", "run-1")
    assert store.active_facts("repo-b") == []
