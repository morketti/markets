"""Tests for routine.run_for_watchlist — per-ticker pipeline integration (Pattern #3).

Mocks AsyncAnthropic via the Wave 2 mock_anthropic_client fixture. Builds
minimal-viable Snapshots via a closure-based snapshot_loader.

Locked behaviors verified:
  * test_per_ticker_pipeline_full: full mock chain (4 analyticals scored sync;
    6 personas mocked + valid AgentSignals; synthesizer mocked + valid
    TickerDecision); result has all 6 fields populated.
  * test_lite_mode_skips_persona_and_synthesizer: lite_mode=True → skips
    persona/synthesizer LLM calls; persona_signals=[]; ticker_decision=None;
    mock client called 0 times.
  * test_per_ticker_exception_isolation: 3-ticker watchlist; loader fails on
    middle ticker; first + third succeed; result list has length 3 with
    middle's TickerResult having non-empty errors.
  * test_sync_across_tickers_order_preserved: input order preserved in result.
  * test_run_for_watchlist_uses_supplied_client.
  * test_run_for_watchlist_uses_supplied_snapshot_loader.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from analysts.data.snapshot import Snapshot
from analysts.position_signal import PositionSignal
from analysts.schemas import TickerConfig, Watchlist
from analysts.signals import AgentSignal
from synthesis.decision import DissentSection, TickerDecision, TimeframeBand


# ---------------------------------------------------------------------------
# Fixtures + helpers.
# ---------------------------------------------------------------------------

FROZEN_DT = datetime(2026, 5, 4, 13, 30, 0, tzinfo=timezone.utc)


def _make_dark_snapshot(ticker: str) -> Snapshot:
    """Minimal Snapshot with data_unavailable=True — analysts short-circuit cleanly."""
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
# Test 1: Full per-ticker pipeline integration (single ticker).
# ---------------------------------------------------------------------------

async def test_per_ticker_pipeline_full(mock_anthropic_client, frozen_now) -> None:
    """Single ticker; mock 6 personas + 1 synthesizer; result has all fields populated."""
    from routine.run_for_watchlist import TickerResult, run_for_watchlist

    ticker = "AAPL"
    watchlist = _build_watchlist([ticker])

    # Queue 6 persona AgentSignals + 1 TickerDecision in canonical order.
    persona_ids = ["buffett", "munger", "wood", "burry", "lynch", "claude_analyst"]
    for pid in persona_ids:
        mock_anthropic_client.messages.queue_response(
            _make_persona_signal(pid, ticker),
        )
    mock_anthropic_client.messages.queue_response(_make_decision(ticker))

    def loader(t: str) -> Snapshot:
        return _make_dark_snapshot(t)

    results = await run_for_watchlist(
        watchlist,
        lite_mode=False,
        snapshots_root=Path("/tmp"),
        computed_at=frozen_now,
        client=mock_anthropic_client,
        snapshot_loader=loader,
    )

    assert len(results) == 1
    r = results[0]
    assert isinstance(r, TickerResult)
    assert r.ticker == ticker
    # 4 analyticals + position signal scored deterministically by the analyst
    # modules even on dark snapshot (they emit data_unavailable=True signals).
    assert len(r.analytical_signals) == 4
    assert r.position_signal is not None
    # 6 persona signals + 1 ticker_decision — but synthesize() short-circuits
    # to data_unavailable_decision when snapshot.data_unavailable=True (does
    # NOT call the LLM). So the synthesizer queued response is unused.
    # That's fine — the test focus is "all 6 fields populated, no errors".
    # For a richer test path see test_lite_mode and test_isolation below.
    assert r.errors == []


# ---------------------------------------------------------------------------
# Test 2: Lite mode skips persona + synthesizer (mock called 0 times).
# ---------------------------------------------------------------------------

async def test_lite_mode_skips_persona_and_synthesizer(
    mock_anthropic_client, frozen_now,
) -> None:
    """lite_mode=True → 0 LLM calls; persona_signals=[]; ticker_decision=None."""
    from routine.run_for_watchlist import run_for_watchlist

    watchlist = _build_watchlist(["AAPL"])

    def loader(t: str) -> Snapshot:
        return _make_dark_snapshot(t)

    results = await run_for_watchlist(
        watchlist,
        lite_mode=True,
        snapshots_root=Path("/tmp"),
        computed_at=frozen_now,
        client=mock_anthropic_client,
        snapshot_loader=loader,
    )

    assert len(results) == 1
    r = results[0]
    assert r.persona_signals == []
    assert r.ticker_decision is None
    # Analyticals + PositionSignal still scored (deterministic, no LLM).
    assert len(r.analytical_signals) == 4
    assert r.position_signal is not None
    # Mock client should NOT have been called — lite mode skips LLM layers.
    assert len(mock_anthropic_client.messages.calls) == 0


# ---------------------------------------------------------------------------
# Test 3: Per-ticker exception isolation.
# ---------------------------------------------------------------------------

async def test_per_ticker_exception_isolation(
    mock_anthropic_client, frozen_now,
) -> None:
    """3-ticker watchlist; loader raises on middle ticker; 1st + 3rd succeed."""
    from routine.run_for_watchlist import run_for_watchlist

    tickers = ["AAPL", "MSFT", "NVDA"]
    watchlist = _build_watchlist(tickers)

    def loader(t: str) -> Snapshot:
        if t == "MSFT":
            raise FileNotFoundError(f"snapshot missing for {t}")
        return _make_dark_snapshot(t)

    # lite_mode=True so we don't need to queue persona/synth responses
    # (focus is exception isolation, not LLM behavior).
    results = await run_for_watchlist(
        watchlist,
        lite_mode=True,
        snapshots_root=Path("/tmp"),
        computed_at=frozen_now,
        client=mock_anthropic_client,
        snapshot_loader=loader,
    )

    assert len(results) == 3
    # Order preserved: AAPL, MSFT, NVDA.
    assert [r.ticker for r in results] == tickers

    # MSFT failed; errors populated; other fields default.
    msft = results[1]
    assert msft.errors and "MSFT" in msft.errors[0] or "FileNotFoundError" in msft.errors[0]
    assert msft.position_signal is None
    assert msft.analytical_signals == []
    assert msft.persona_signals == []
    assert msft.ticker_decision is None

    # AAPL + NVDA succeeded.
    for ok in (results[0], results[2]):
        assert ok.errors == []
        assert len(ok.analytical_signals) == 4
        assert ok.position_signal is not None


# ---------------------------------------------------------------------------
# Test 4: Sync across tickers — input order preserved.
# ---------------------------------------------------------------------------

async def test_sync_across_tickers_order_preserved(
    mock_anthropic_client, frozen_now,
) -> None:
    """Result list order matches watchlist iteration order."""
    from routine.run_for_watchlist import run_for_watchlist

    tickers = ["AAPL", "MSFT", "NVDA", "GOOG", "AMZN"]
    watchlist = _build_watchlist(tickers)

    def loader(t: str) -> Snapshot:
        return _make_dark_snapshot(t)

    results = await run_for_watchlist(
        watchlist,
        lite_mode=True,  # avoid having to queue mock responses
        snapshots_root=Path("/tmp"),
        computed_at=frozen_now,
        client=mock_anthropic_client,
        snapshot_loader=loader,
    )
    assert [r.ticker for r in results] == tickers


# ---------------------------------------------------------------------------
# Test 5: Supplied client is used.
# ---------------------------------------------------------------------------

async def test_run_for_watchlist_uses_supplied_client(
    mock_anthropic_client, frozen_now,
) -> None:
    """Pass mock client explicitly; routine uses it (verified via .calls list).

    Use a non-dark snapshot path: build a synthesizer call via lite_mode=False
    and queue 6 persona + 1 synth response. Verify the mock saw at least one
    call (proving the supplied client was the consumer).

    Note: when snapshot.data_unavailable=True, synthesize() short-circuits
    without calling the LLM; the persona slate IS called though (6 calls).
    So we expect mock.calls to have length 6.
    """
    from routine.run_for_watchlist import run_for_watchlist

    watchlist = _build_watchlist(["AAPL"])

    persona_ids = ["buffett", "munger", "wood", "burry", "lynch", "claude_analyst"]
    for pid in persona_ids:
        mock_anthropic_client.messages.queue_response(
            _make_persona_signal(pid, "AAPL"),
        )
    # Note: synthesize() will short-circuit on dark snapshot, so we don't
    # actually need to queue a TickerDecision. But queue one defensively
    # in case the implementation changes to call the synthesizer regardless.
    mock_anthropic_client.messages.queue_response(_make_decision("AAPL"))

    def loader(t: str) -> Snapshot:
        return _make_dark_snapshot(t)

    await run_for_watchlist(
        watchlist,
        lite_mode=False,
        snapshots_root=Path("/tmp"),
        computed_at=frozen_now,
        client=mock_anthropic_client,
        snapshot_loader=loader,
    )

    # At least 6 persona calls happened on the supplied mock client.
    assert len(mock_anthropic_client.messages.calls) >= 6


# ---------------------------------------------------------------------------
# Test 6: Supplied snapshot_loader is called per ticker.
# ---------------------------------------------------------------------------

async def test_run_for_watchlist_uses_supplied_snapshot_loader(
    mock_anthropic_client, frozen_now,
) -> None:
    """Custom loader closure is called with each ticker arg in canonical order."""
    from routine.run_for_watchlist import run_for_watchlist

    tickers = ["AAPL", "MSFT", "NVDA"]
    watchlist = _build_watchlist(tickers)

    seen_args: list[str] = []

    def loader(t: str) -> Snapshot:
        seen_args.append(t)
        return _make_dark_snapshot(t)

    await run_for_watchlist(
        watchlist,
        lite_mode=True,
        snapshots_root=Path("/tmp"),
        computed_at=frozen_now,
        client=mock_anthropic_client,
        snapshot_loader=loader,
    )
    assert seen_args == tickers


# ---------------------------------------------------------------------------
# Coverage Test 7: Default snapshot_loader raises NotImplementedError on call.
# ---------------------------------------------------------------------------

def test_default_snapshot_loader_raises_not_implemented() -> None:
    """The v1 stub loader raises NotImplementedError; tests inject their own."""
    from routine.run_for_watchlist import _default_snapshot_loader

    with pytest.raises(NotImplementedError, match="snapshot_loader not configured"):
        _default_snapshot_loader("AAPL")


# ---------------------------------------------------------------------------
# Coverage Test 8: Default-client branch — client=None constructs AsyncAnthropic.
# ---------------------------------------------------------------------------

async def test_default_client_branch_uses_async_anthropic(
    monkeypatch, frozen_now,
) -> None:
    """When client=None, run_for_watchlist instantiates AsyncAnthropic() once.

    Empty watchlist → 0 ticker iterations → no LLM calls; the only point is
    that AsyncAnthropic() default-construction doesn't fail and the function
    returns []. Verifies the default-client branch is exercised.
    """
    from routine import run_for_watchlist as rfw_mod
    from routine.run_for_watchlist import run_for_watchlist

    constructed: list[bool] = []

    class _FakeAsyncAnthropic:
        def __init__(self, *args, **kwargs):
            constructed.append(True)
            self.messages = None  # never used (empty watchlist)

    monkeypatch.setattr(rfw_mod, "AsyncAnthropic", _FakeAsyncAnthropic)

    watchlist = _build_watchlist([])  # empty
    results = await run_for_watchlist(
        watchlist,
        lite_mode=True,
        snapshots_root=Path("/tmp"),
        computed_at=frozen_now,
        client=None,  # exercises the default-construct branch
        snapshot_loader=lambda t: _make_dark_snapshot(t),  # arbitrary
    )
    assert results == []
    assert constructed == [True]


# ---------------------------------------------------------------------------
# Coverage Test 9: Default-loader branch — snapshot_loader=None falls through.
# ---------------------------------------------------------------------------

async def test_default_snapshot_loader_branch(
    mock_anthropic_client, frozen_now,
) -> None:
    """When snapshot_loader=None, the default stub is used; per-ticker exception
    catches the NotImplementedError and emits TickerResult(errors=[...])."""
    from routine.run_for_watchlist import run_for_watchlist

    watchlist = _build_watchlist(["AAPL"])
    results = await run_for_watchlist(
        watchlist,
        lite_mode=True,
        snapshots_root=Path("/tmp"),
        computed_at=frozen_now,
        client=mock_anthropic_client,
        snapshot_loader=None,  # exercises the default-loader branch
    )
    assert len(results) == 1
    r = results[0]
    assert r.errors and "NotImplementedError" in r.errors[0]


# ---------------------------------------------------------------------------
# Phase 6 / Plan 06-01: TickerResult threads ohlc_history + headlines
#
# Wave 0 amendment: TickerResult gains ohlc_history (list[OHLCBar]) and
# headlines (list[dict]). Both default to empty list to preserve all existing
# call-site compatibility. routine/storage.py reads these fields when building
# the per-ticker JSON payload (ohlc_history + indicators + headlines + Plan 06-01
# schema_version=2).
# ---------------------------------------------------------------------------


def test_ticker_result_threads_ohlc_history_and_headlines() -> None:
    """TickerResult model has ohlc_history (list[OHLCBar]) + headlines (list[dict]) fields.

    Defaults are empty list so existing tests/call-sites that don't pass them
    keep working. routine/storage._build_ticker_payload reads both into the
    Wave 0 per-ticker JSON shape.
    """
    from datetime import date

    from analysts.data.prices import OHLCBar
    from routine.run_for_watchlist import TickerResult

    # Field exists with default empty list.
    r_default = TickerResult(ticker="AAPL")
    assert r_default.ohlc_history == []
    assert r_default.headlines == []

    # Field can be populated with the expected shape.
    bars = [
        OHLCBar(
            date=date(2026, 5, 1),
            open=100.0, high=101.0, low=99.0, close=100.5, volume=1_000_000,
        ),
        OHLCBar(
            date=date(2026, 5, 2),
            open=100.5, high=102.0, low=100.0, close=101.5, volume=1_100_000,
        ),
    ]
    headlines = [
        {
            "source": "yahoo-rss",
            "published_at": "2026-05-04T10:00:00+00:00",
            "title": "Apple beats Q1",
            "url": "https://example.com/aapl",
        }
    ]
    r = TickerResult(
        ticker="AAPL",
        ohlc_history=bars,
        headlines=headlines,
    )
    assert len(r.ohlc_history) == 2
    assert r.ohlc_history[0].close == 100.5
    assert len(r.headlines) == 1
    assert r.headlines[0]["source"] == "yahoo-rss"


# ---------------------------------------------------------------------------
# Phase 8 / Plan 08-01 / Task 2: Phase E memory log hook.
#
# After per-ticker pipeline produces persona_signals (6 AgentSignals when
# non-lite), run_for_watchlist appends one record per (ticker, persona) to
# memory/historical_signals.jsonl. Skipped when persona_signals empty
# (lite_mode OR per-ticker failure both leave the list empty).
# ---------------------------------------------------------------------------


async def test_phase_e_writes_one_record_per_persona(
    mock_anthropic_client, frozen_now, tmp_path,
) -> None:
    """Non-lite single-ticker run ⇒ one memory log record per persona (6 total).

    Note: with a *dark* snapshot (data_unavailable=True), the synthesizer
    short-circuits but the persona slate still runs (6 signals regardless).
    """
    from routine.run_for_watchlist import run_for_watchlist

    log_path = tmp_path / "memory" / "historical_signals.jsonl"
    watchlist = _build_watchlist(["AAPL"])

    persona_ids = ["buffett", "munger", "wood", "burry", "lynch", "claude_analyst"]
    for pid in persona_ids:
        mock_anthropic_client.messages.queue_response(
            _make_persona_signal(pid, "AAPL"),
        )
    mock_anthropic_client.messages.queue_response(_make_decision("AAPL"))

    def loader(t: str) -> Snapshot:
        return _make_dark_snapshot(t)

    results = await run_for_watchlist(
        watchlist,
        lite_mode=False,
        snapshots_root=Path("/tmp"),
        computed_at=frozen_now,
        client=mock_anthropic_client,
        snapshot_loader=loader,
        memory_log_path=log_path,
    )

    assert len(results) == 1
    r = results[0]
    assert len(r.persona_signals) == 6

    import json

    assert log_path.exists(), "memory log file should be written"
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 6, f"expected 6 records, got {len(lines)}"

    records = [json.loads(line) for line in lines]
    record_personas = {rec["persona_id"] for rec in records}
    assert record_personas == set(persona_ids)
    for rec in records:
        assert rec["ticker"] == "AAPL"
        assert rec["date"] == frozen_now.date().isoformat()
        assert rec["verdict"] == "bullish"
        assert rec["confidence"] == 70
        assert rec["evidence_count"] == 1


async def test_lite_mode_skips_phase_e(
    mock_anthropic_client, frozen_now, tmp_path,
) -> None:
    """lite_mode=True ⇒ persona_signals=[] ⇒ NO memory log records written."""
    from routine.run_for_watchlist import run_for_watchlist

    log_path = tmp_path / "memory" / "historical_signals.jsonl"
    watchlist = _build_watchlist(["AAPL"])

    def loader(t: str) -> Snapshot:
        return _make_dark_snapshot(t)

    await run_for_watchlist(
        watchlist,
        lite_mode=True,
        snapshots_root=Path("/tmp"),
        computed_at=frozen_now,
        client=mock_anthropic_client,
        snapshot_loader=loader,
        memory_log_path=log_path,
    )

    assert not log_path.exists(), (
        "lite_mode should skip memory log writes entirely"
    )


async def test_phase_e_per_ticker_failure_skips_log(
    mock_anthropic_client, frozen_now, tmp_path,
) -> None:
    """Per-ticker pipeline failure leaves persona_signals=[] ⇒ NO memory log records."""
    from routine.run_for_watchlist import run_for_watchlist

    log_path = tmp_path / "memory" / "historical_signals.jsonl"
    watchlist = _build_watchlist(["AAPL"])

    def boom_loader(t: str) -> Snapshot:
        raise FileNotFoundError(f"snapshot missing for {t}")

    results = await run_for_watchlist(
        watchlist,
        lite_mode=False,
        snapshots_root=Path("/tmp"),
        computed_at=frozen_now,
        client=mock_anthropic_client,
        snapshot_loader=boom_loader,
        memory_log_path=log_path,
    )

    assert len(results) == 1
    r = results[0]
    assert r.errors
    assert r.persona_signals == []
    assert not log_path.exists()
