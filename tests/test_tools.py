"""Unit tests for the exact-match patch tool and the shell allowlist."""

import pytest

from recall.tools.files import apply_patch, read_file
from recall.tools.shell import run_allowlisted


def test_apply_patch_replaces_once(tmp_path):
    file = tmp_path / "mod.py"
    file.write_text("def f():\n    return 1\n")
    diff = apply_patch(str(file), "return 1", "return 2")
    assert "return 2" in file.read_text()
    assert "-    return 1" in diff and "+    return 2" in diff


def test_apply_patch_missing_target_raises(tmp_path):
    file = tmp_path / "mod.py"
    file.write_text("x = 1\n")
    with pytest.raises(ValueError, match="not found"):
        apply_patch(str(file), "y = 2", "y = 3")


def test_apply_patch_ambiguous_target_raises(tmp_path):
    file = tmp_path / "mod.py"
    file.write_text("x = 1\nx = 1\n")
    with pytest.raises(ValueError, match="matches 2 times"):
        apply_patch(str(file), "x = 1", "x = 2")


def test_read_file_line_range(tmp_path):
    file = tmp_path / "mod.py"
    file.write_text("a\nb\nc\nd\n")
    out = read_file(str(file), start=2, end=3)
    assert "b" in out and "c" in out and "a" not in out and "d" not in out


def test_shell_allowlist(tmp_path):
    assert isinstance(run_allowlisted(str(tmp_path), ["ls"]), str)
    with pytest.raises(PermissionError):
        run_allowlisted(str(tmp_path), ["rm", "-rf", "."])
    with pytest.raises(PermissionError):
        run_allowlisted(str(tmp_path), ["git", "push"])
