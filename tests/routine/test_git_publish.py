"""Tests for routine.git_publish — 5-step git CLI sequence per Pattern #11.

Locked behaviors verified:
  * 5 subprocess.run calls in fixed order:
      1. git fetch origin main
      2. git pull --rebase --autostash origin main
      3. git add data/{date_str}/
      4. git commit -m "data: snapshot {date_str}"
      5. git push origin main
  * Each call uses check=True, capture_output=True, text=True, timeout=60,
    cwd=str(repo_root).
  * fetch / pull / push failures each → CalledProcessError propagates.
  * Anti-pattern lock: source MUST NOT contain "git add -A".
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import pytest


def _make_completed_proc(returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout="", stderr="",
    )


# ---------------------------------------------------------------------------
# Test 1: happy-path 5 subprocess.run calls in order.
# ---------------------------------------------------------------------------

def test_happy_path_5_subprocess_calls_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """commit_and_push fires exactly 5 subprocess.run calls in fixed order."""
    from routine import git_publish

    calls: list[list[str]] = []

    def _fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        return _make_completed_proc()

    monkeypatch.setattr(git_publish.subprocess, "run", _fake_run)

    git_publish.commit_and_push("2026-05-04")

    assert len(calls) == 5
    assert calls[0] == ["git", "fetch", "origin", "main"]
    assert calls[1] == ["git", "pull", "--rebase", "--autostash", "origin", "main"]
    assert calls[2] == ["git", "add", "data/2026-05-04/"]
    assert calls[3] == ["git", "commit", "-m", "data: snapshot 2026-05-04"]
    assert calls[4] == ["git", "push", "origin", "main"]


# ---------------------------------------------------------------------------
# Test 2: subprocess kwargs locked.
# ---------------------------------------------------------------------------

def test_subprocess_kwargs_locked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each call uses check=True, capture_output=True, text=True, timeout=60, cwd."""
    from routine import git_publish

    seen_kwargs: list[dict[str, Any]] = []

    def _fake_run(cmd, **kwargs):
        seen_kwargs.append(dict(kwargs))
        return _make_completed_proc()

    monkeypatch.setattr(git_publish.subprocess, "run", _fake_run)

    git_publish.commit_and_push("2026-05-04", repo_root=Path("/tmp/myrepo"))

    assert len(seen_kwargs) == 5
    for kw in seen_kwargs:
        assert kw.get("check") is True
        assert kw.get("capture_output") is True
        assert kw.get("text") is True
        assert kw.get("timeout") == 60
        assert kw.get("cwd") == str(Path("/tmp/myrepo"))


# ---------------------------------------------------------------------------
# Test 3: fetch failure raises CalledProcessError; subsequent commands NOT run.
# ---------------------------------------------------------------------------

def test_fetch_failure_raises_called_process_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """First subprocess.run raises CalledProcessError → propagates; 0 subsequent calls."""
    from routine import git_publish

    calls: list[list[str]] = []

    def _fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        if len(calls) == 1:
            raise subprocess.CalledProcessError(
                returncode=128, cmd=list(cmd), stderr="fetch failed",
            )
        return _make_completed_proc()

    monkeypatch.setattr(git_publish.subprocess, "run", _fake_run)

    with pytest.raises(subprocess.CalledProcessError) as exc_info:
        git_publish.commit_and_push("2026-05-04")

    # Only the fetch call was attempted.
    assert len(calls) == 1
    assert calls[0] == ["git", "fetch", "origin", "main"]
    assert exc_info.value.returncode == 128


# ---------------------------------------------------------------------------
# Test 4: pull --rebase failure raises.
# ---------------------------------------------------------------------------

def test_pull_rebase_failure_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Second subprocess.run (pull --rebase --autostash) raises → propagates."""
    from routine import git_publish

    calls: list[list[str]] = []

    def _fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        if len(calls) == 2:
            raise subprocess.CalledProcessError(
                returncode=1, cmd=list(cmd), stderr="rebase conflict",
            )
        return _make_completed_proc()

    monkeypatch.setattr(git_publish.subprocess, "run", _fake_run)

    with pytest.raises(subprocess.CalledProcessError):
        git_publish.commit_and_push("2026-05-04")

    # fetch + pull attempted; nothing else.
    assert len(calls) == 2


# ---------------------------------------------------------------------------
# Test 5: push failure raises (first 4 succeed).
# ---------------------------------------------------------------------------

def test_push_failure_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """5th subprocess.run (push) raises → propagates after first 4 succeed."""
    from routine import git_publish

    calls: list[list[str]] = []

    def _fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        if len(calls) == 5:
            raise subprocess.CalledProcessError(
                returncode=1, cmd=list(cmd), stderr="push rejected",
            )
        return _make_completed_proc()

    monkeypatch.setattr(git_publish.subprocess, "run", _fake_run)

    with pytest.raises(subprocess.CalledProcessError):
        git_publish.commit_and_push("2026-05-04")

    assert len(calls) == 5
    assert calls[4] == ["git", "push", "origin", "main"]


# ---------------------------------------------------------------------------
# Test 6: anti-pattern source-grep — `git add -A` MUST NOT be in source.
# ---------------------------------------------------------------------------

def test_no_git_add_dash_A_in_source() -> None:
    """Pattern #11 anti-pattern lock: `git add -A` (or `git add .`) MUST NOT appear."""
    src_path = Path(__file__).resolve().parent.parent.parent / "routine" / "git_publish.py"
    src = src_path.read_text(encoding="utf-8")

    # Strict: `git add -A` should not appear anywhere (string or list form).
    assert "git add -A" not in src
    # `git add .` (with dot) is also banned by Pattern #11.
    # Match `"."` standalone (not `data/`).
    assert not re.search(r"['\"]\\.[\"']\s*[,\]]", src), (
        "git_publish.py must not pass '.' to `git add` (anti-pattern)"
    )

    # Locked positive markers — pull + rebase + autostash present.
    assert "--rebase" in src
    assert "--autostash" in src
    assert "git" in src and "fetch" in src and "push" in src
