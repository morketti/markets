"""End-to-end integration tests for routine.entrypoint.main().

Mocks all external boundaries:
  * AsyncAnthropic (constructor + .messages.parse — via mock_anthropic_client)
  * subprocess.run (git CLI — via monkeypatch)
  * load_watchlist (returns synthesized fixture)
  * snapshot_loader (closure over a dict of mock Snapshots)
  * Path("data") / snapshots_root (via monkeypatch on entrypoint module)

Locked behaviors verified:
  * test_main_5_ticker_happy_path: 5 tickers; main() returns 0; 5 per-ticker
    JSONs + _index.json + _status.json land at tmp_path/{date}/; subprocess.run
    called 5 times for git; _status.json.success=True, lite_mode=False.
  * test_main_lite_mode_path: 35-ticker watchlist forces estimate>quota →
    lite_mode=True; per-ticker JSONs have persona_signals=[] and
    ticker_decision=null; _status.json.lite_mode=True, partial=True.
  * test_main_top_level_exception_returns_1: load_watchlist raises;
    main() returns 1; best-effort write_failure_status emits a _status.json
    with success=False + error field.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from analysts.data.snapshot import Snapshot
from analysts.schemas import TickerConfig, Watchlist
from analysts.signals import AgentSignal
from synthesis.decision import DissentSection, TickerDecision, TimeframeBand


FROZEN_DT = datetime(2026, 5, 4, 13, 30, 0, tzinfo=timezone.utc)


def _make_dark_snapshot(ticker: str) -> Snapshot:
    return Snapshot(ticker=ticker, fetched_at=FROZEN_DT, data_unavailable=True)


def _make_persona_signal(persona_id: str, ticker: str) -> AgentSignal:
    return AgentSignal(
        ticker=ticker,
        analyst_id=persona_id,
        computed_at=FROZEN_DT,
        verdict="bullish",
        confidence=70,
        evidence=["mock evidence"],
    )


def _make_decision(ticker: str) -> TickerDecision:
    return TickerDecision(
        ticker=ticker,
        computed_at=FROZEN_DT,
        recommendation="hold",
        conviction="medium",
        short_term=TimeframeBand(summary="ST", drivers=[], confidence=50),
        long_term=TimeframeBand(summary="LT", drivers=[], confidence=55),
        open_observation="",
        dissent=DissentSection(),
    )


def _build_watchlist(tickers: list[str]) -> Watchlist:
    return Watchlist(tickers={t: TickerConfig(ticker=t) for t in tickers})


# ---------------------------------------------------------------------------
# Test 1: 5-ticker happy-path end-to-end.
# ---------------------------------------------------------------------------

def test_main_5_ticker_happy_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_anthropic_client,
) -> None:
    """5-ticker run; mocks all I/O; exit 0; 5 JSONs + _index + _status emitted; git mocked."""
    from routine import entrypoint as ep_mod
    from routine import run_for_watchlist as rfw_mod

    tickers = ["AAPL", "MSFT", "NVDA", "GOOG", "AMZN"]
    watchlist = _build_watchlist(tickers)

    # Queue mock responses: per ticker, 6 personas + 1 synthesizer.
    # Note: synthesize() short-circuits on dark snapshot WITHOUT calling LLM,
    # so only personas (5 tickers * 6 = 30) consume queue items.
    persona_ids = ["buffett", "munger", "wood", "burry", "lynch", "claude_analyst"]
    for t in tickers:
        for pid in persona_ids:
            mock_anthropic_client.messages.queue_response(
                _make_persona_signal(pid, t),
            )

    # Stub load_watchlist on the entrypoint module.
    monkeypatch.setattr(ep_mod, "load_watchlist", lambda: watchlist)

    # Stub AsyncAnthropic on the run_for_watchlist module so the default
    # constructor returns our mock client.
    monkeypatch.setattr(
        rfw_mod, "AsyncAnthropic", lambda *a, **kw: mock_anthropic_client,
    )

    # Stub _default_snapshot_loader so per-ticker dark snapshots are returned.
    monkeypatch.setattr(
        rfw_mod, "_default_snapshot_loader", lambda t: _make_dark_snapshot(t),
    )

    # Stub subprocess.run for git_publish.
    git_calls: list[list[str]] = []
    import subprocess

    def _fake_run(cmd, **kwargs):
        git_calls.append(list(cmd))
        return subprocess.CompletedProcess(
            args=list(cmd), returncode=0, stdout="", stderr="",
        )

    from routine import git_publish as gp_mod
    monkeypatch.setattr(gp_mod.subprocess, "run", _fake_run)

    # Redirect snapshots_root to tmp_path by monkeypatching Path inside entrypoint.
    # Easiest: monkeypatch the SNAPSHOTS_ROOT constant if present, else inject
    # via a wrapper. We'll instead monkeypatch Path in entrypoint module's
    # namespace indirectly: rebind a module-level fn or constant.
    # Cleaner approach: monkeypatch ep_mod.Path so Path("data") returns tmp_path.

    real_path_init = Path.__init__

    class _RoutedPath(type(Path())):
        pass

    # Patch ep_mod.Path("data") behavior by intercepting at module level.
    # The entrypoint creates Path("data") for snapshots_root. We intercept by
    # replacing the Path symbol in ep_mod with a callable that maps "data" → tmp_path.
    real_Path = ep_mod.Path

    def _path_factory(arg):
        if arg == "data":
            return tmp_path
        return real_Path(arg)

    monkeypatch.setattr(ep_mod, "Path", _path_factory)

    # Run main().
    rc = ep_mod.main()

    assert rc == 0, "main() should return 0 on happy path"

    # Find the date folder (computed_at-based; today's UTC date).
    date_dirs = [d for d in tmp_path.iterdir() if d.is_dir()]
    assert len(date_dirs) == 1, f"expected 1 date folder, got {date_dirs}"
    date_dir = date_dirs[0]

    # 5 per-ticker JSONs + _index.json + _status.json = 7 files.
    files = sorted(p.name for p in date_dir.iterdir())
    assert "_index.json" in files
    assert "_status.json" in files
    for t in tickers:
        assert f"{t}.json" in files, f"{t}.json missing in {files}"

    # _status.json: success=True, lite_mode=False.
    status = json.loads((date_dir / "_status.json").read_text(encoding="utf-8"))
    assert status["success"] is True
    assert status["lite_mode"] is False
    assert sorted(status["completed_tickers"]) == sorted(tickers)
    assert status["failed_tickers"] == []

    # subprocess.run for git was called 5 times (fetch / pull / add / commit / push).
    assert len(git_calls) == 5
    assert git_calls[0][:3] == ["git", "fetch", "origin"]
    assert git_calls[4][:3] == ["git", "push", "origin"]


# ---------------------------------------------------------------------------
# Test 2: Lite-mode path — 35-ticker watchlist forces estimate > quota.
# ---------------------------------------------------------------------------

def test_main_lite_mode_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_anthropic_client,
) -> None:
    """35-ticker watchlist → estimate=693k > 600k quota → lite_mode=True; 0 LLM calls."""
    from routine import entrypoint as ep_mod
    from routine import run_for_watchlist as rfw_mod

    tickers = [
        "AAPL", "MSFT", "NVDA", "GOOG", "AMZN", "META", "TSLA", "JPM", "V", "JNJ",
        "PG", "HD", "MA", "CVX", "ABBV", "KO", "PFE", "PEP", "WMT", "BAC",
        "TMO", "COST", "DIS", "CRM", "ORCL", "NKE", "ADBE", "AMD", "NFLX", "INTC",
        "QCOM", "ADP", "UPS", "MCD", "BMY",
    ]
    assert len(tickers) == 35
    watchlist = _build_watchlist(tickers)

    monkeypatch.setattr(ep_mod, "load_watchlist", lambda: watchlist)
    monkeypatch.setattr(
        rfw_mod, "AsyncAnthropic", lambda *a, **kw: mock_anthropic_client,
    )
    monkeypatch.setattr(
        rfw_mod, "_default_snapshot_loader", lambda t: _make_dark_snapshot(t),
    )

    import subprocess

    def _fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(
            args=list(cmd), returncode=0, stdout="", stderr="",
        )

    from routine import git_publish as gp_mod
    monkeypatch.setattr(gp_mod.subprocess, "run", _fake_run)

    real_Path = ep_mod.Path

    def _path_factory(arg):
        if arg == "data":
            return tmp_path
        return real_Path(arg)

    monkeypatch.setattr(ep_mod, "Path", _path_factory)

    rc = ep_mod.main()
    assert rc == 0

    # Mock client should NOT have been called — lite mode skips LLM.
    assert len(mock_anthropic_client.messages.calls) == 0

    # Verify per-ticker JSON has persona_signals=[] and ticker_decision=null.
    date_dirs = [d for d in tmp_path.iterdir() if d.is_dir()]
    date_dir = date_dirs[0]
    aapl = json.loads((date_dir / "AAPL.json").read_text(encoding="utf-8"))
    assert aapl["persona_signals"] == []
    assert aapl["ticker_decision"] is None

    # _status.json: lite_mode=True, partial=True.
    status = json.loads((date_dir / "_status.json").read_text(encoding="utf-8"))
    assert status["lite_mode"] is True
    assert status["partial"] is True
    # _index.json: lite_mode=True.
    idx = json.loads((date_dir / "_index.json").read_text(encoding="utf-8"))
    assert idx["lite_mode"] is True


# ---------------------------------------------------------------------------
# Test 3: Top-level exception → exit 1 + best-effort failure _status.json.
# ---------------------------------------------------------------------------

def test_main_top_level_exception_returns_1(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """load_watchlist raises → main() returns 1; best-effort _status.json emitted."""
    from routine import entrypoint as ep_mod

    def _boom():
        raise FileNotFoundError("watchlist.json not found")

    monkeypatch.setattr(ep_mod, "load_watchlist", _boom)

    real_Path = ep_mod.Path

    def _path_factory(arg):
        if arg == "data":
            return tmp_path
        return real_Path(arg)

    monkeypatch.setattr(ep_mod, "Path", _path_factory)

    rc = ep_mod.main()
    assert rc == 1

    # Best-effort write_failure_status: a _status.json should exist with
    # success=False + error field.
    date_dirs = [d for d in tmp_path.iterdir() if d.is_dir()]
    assert len(date_dirs) == 1
    status_path = date_dirs[0] / "_status.json"
    assert status_path.exists()
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["success"] is False
    assert "error" in status
    assert "FileNotFoundError" in status["error"] or "watchlist" in status["error"]


# ---------------------------------------------------------------------------
# Coverage Test 4: Empty watchlist → exit 1 (no run executed).
# ---------------------------------------------------------------------------

def test_main_empty_watchlist_returns_1(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """load_watchlist returns empty Watchlist → main() returns 1 (nothing to do)."""
    from routine import entrypoint as ep_mod

    monkeypatch.setattr(ep_mod, "load_watchlist", lambda: Watchlist())

    real_Path = ep_mod.Path

    def _path_factory(arg):
        if arg == "data":
            return tmp_path
        return real_Path(arg)

    monkeypatch.setattr(ep_mod, "Path", _path_factory)

    rc = ep_mod.main()
    assert rc == 1
    # No date folder created (we returned before any write).
    date_dirs = [d for d in tmp_path.iterdir() if d.is_dir()]
    assert date_dirs == []


# ---------------------------------------------------------------------------
# Coverage Test 5: Failure-status write itself fails → still returns 1.
# ---------------------------------------------------------------------------

def test_main_failure_status_write_failure_does_not_crash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If write_failure_status itself raises, main() STILL returns 1 cleanly.

    The nested try/except in main()'s exception handler ensures the failure-
    status write can never crash the routine.
    """
    from routine import entrypoint as ep_mod

    monkeypatch.setattr(
        ep_mod, "load_watchlist",
        lambda: (_ for _ in ()).throw(RuntimeError("first failure")),
    )

    def _boom_write_failure(**kwargs):
        raise OSError("disk full during failure-status write")

    monkeypatch.setattr(ep_mod, "write_failure_status", _boom_write_failure)

    real_Path = ep_mod.Path

    def _path_factory(arg):
        if arg == "data":
            return tmp_path
        return real_Path(arg)

    monkeypatch.setattr(ep_mod, "Path", _path_factory)

    rc = ep_mod.main()
    assert rc == 1  # nested except absorbed the second failure
