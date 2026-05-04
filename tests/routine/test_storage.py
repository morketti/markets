"""Tests for routine.storage — three-phase atomic write per Pattern #4.

Locked behaviors verified:
  * _atomic_write_json: tempfile + os.replace + sort_keys=True; mkdir parents;
    no orphan .tmp on os.replace OSError.
  * write_daily_snapshot: per-ticker JSONs FIRST → _index.json SECOND →
    _status.json LAST. Per-ticker write OSError populates failed_tickers
    WITHOUT aborting the loop (LLM-08 cascade-prevention).
  * _index.json schema: {date, schema_version=1, run_started_at,
    run_completed_at, tickers (only completed), lite_mode,
    total_token_count_estimate}.
  * _status.json schema (LLM-08): {success, partial, completed_tickers,
    failed_tickers, skipped_tickers, llm_failure_count, lite_mode}.
  * llm_failure_count formula: count persona AgentSignals with
    data_unavailable=True + (1 per ticker where ticker_decision is None
    AND lite_mode=False).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Builder helpers — produce minimal valid TickerResult fixtures.
# ---------------------------------------------------------------------------

FROZEN_DT = datetime(2026, 5, 4, 13, 30, 0, tzinfo=timezone.utc)
RUN_STARTED = datetime(2026, 5, 4, 11, 0, 0, tzinfo=timezone.utc)
RUN_COMPLETED = datetime(2026, 5, 4, 11, 14, 32, tzinfo=timezone.utc)


def _make_agent_signal(ticker: str, analyst_id: str, *, data_unavailable: bool = False):
    from analysts.signals import AgentSignal

    if data_unavailable:
        return AgentSignal(
            ticker=ticker,
            analyst_id=analyst_id,
            computed_at=FROZEN_DT,
            verdict="neutral",
            confidence=0,
            evidence=["schema_failure"],
            data_unavailable=True,
        )
    return AgentSignal(
        ticker=ticker,
        analyst_id=analyst_id,
        computed_at=FROZEN_DT,
        verdict="bullish",
        confidence=70,
        evidence=["sample evidence"],
    )


def _make_position_signal(ticker: str):
    from analysts.position_signal import PositionSignal

    return PositionSignal(
        ticker=ticker, computed_at=FROZEN_DT,
        state="fair", consensus_score=0.05, confidence=60,
        action_hint="hold_position",
    )


def _make_ticker_decision(ticker: str):
    from synthesis.decision import DissentSection, TickerDecision, TimeframeBand

    return TickerDecision(
        ticker=ticker,
        computed_at=FROZEN_DT,
        recommendation="hold",
        conviction="medium",
        short_term=TimeframeBand(summary="ST summary", drivers=[], confidence=50),
        long_term=TimeframeBand(summary="LT summary", drivers=[], confidence=55),
        open_observation="",
        dissent=DissentSection(),
    )


def _make_ohlc_history(n: int = 180) -> list:
    """Build n synthetic OHLCBars ending at FROZEN_DT.date() (Phase 6 / Plan 06-01)."""
    from datetime import date, timedelta

    from analysts.data.prices import OHLCBar

    end = FROZEN_DT.date()
    bars: list = []
    base = 100.0
    for i in range(n):
        d = end - timedelta(days=n - 1 - i)
        c = base * (1.0 + 0.001 * i)  # gentle uptrend
        bars.append(
            OHLCBar(
                date=d,
                open=c * 0.998,
                high=c * 1.01,
                low=c * 0.99,
                close=c,
                volume=1_000_000 + i * 100,
            )
        )
    return bars


def _make_raw_headline(*, source: str = "yahoo-rss", title: str = "Apple beats", url: str = "https://x") -> dict:
    """Build a raw-headline dict matching ingestion/news.fetch_news(return_raw=True) shape."""
    return {
        "source": source,
        "published_at": "2026-05-04T10:00:00+00:00",
        "title": title,
        "url": url,
    }


def _make_ticker_result(
    ticker: str,
    *,
    n_personas_unavailable: int = 0,
    decision_present: bool = True,
    persona_count: int = 6,
    ohlc_history: list | None = None,
    headlines: list[dict] | None = None,
):
    """Build a minimal TickerResult with controllable persona/decision shape.

    Phase 6 / Plan 06-01: optional `ohlc_history` (list[OHLCBar]) and
    `headlines` (list[dict]) — used by new payload tests.
    """
    from routine.run_for_watchlist import TickerResult

    analytical = [
        _make_agent_signal(ticker, "fundamentals"),
        _make_agent_signal(ticker, "technicals"),
        _make_agent_signal(ticker, "news_sentiment"),
        _make_agent_signal(ticker, "valuation"),
    ]
    pos = _make_position_signal(ticker)
    persona_ids = ["buffett", "munger", "wood", "burry", "lynch", "claude_analyst"]
    personas = [
        _make_agent_signal(
            ticker, persona_ids[i],
            data_unavailable=(i < n_personas_unavailable),
        )
        for i in range(persona_count)
    ]
    decision = _make_ticker_decision(ticker) if decision_present else None
    kwargs: dict = {
        "ticker": ticker,
        "analytical_signals": analytical,
        "position_signal": pos,
        "persona_signals": personas,
        "ticker_decision": decision,
        "errors": [],
    }
    if ohlc_history is not None:
        kwargs["ohlc_history"] = ohlc_history
    if headlines is not None:
        kwargs["headlines"] = headlines
    return TickerResult(**kwargs)


# ---------------------------------------------------------------------------
# Test 1: _atomic_write_json — basic write + sort_keys serialization.
# ---------------------------------------------------------------------------

def test_atomic_write_json_creates_file_and_serializes_sort_keys(tmp_path: Path) -> None:
    """payload {b:1, a:2} → file content has 'a' before 'b' (sort_keys=True locked)."""
    from routine.storage import _atomic_write_json

    target = tmp_path / "out.json"
    payload = {"b": 1, "a": 2}
    _atomic_write_json(target, payload)

    text = target.read_text(encoding="utf-8")
    expected = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    assert text == expected
    # First key in the rendered output must be 'a' (sort_keys lock).
    a_idx = text.index('"a"')
    b_idx = text.index('"b"')
    assert a_idx < b_idx


# ---------------------------------------------------------------------------
# Test 2: _atomic_write_json — mkdir parents.
# ---------------------------------------------------------------------------

def test_atomic_write_json_creates_parent_dir(tmp_path: Path) -> None:
    """When parent dir doesn't exist, mkdir(parents=True) bootstraps it."""
    from routine.storage import _atomic_write_json

    target = tmp_path / "missing" / "subdir" / "out.json"
    assert not target.parent.exists()
    _atomic_write_json(target, {"x": 1})
    assert target.exists()
    assert target.parent.is_dir()


# ---------------------------------------------------------------------------
# Test 3: _atomic_write_json — no orphan .tmp on os.replace OSError.
# ---------------------------------------------------------------------------

def test_atomic_write_json_no_orphan_tmp_on_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """os.replace OSError → tmp file is unlinked; original raise propagates."""
    from routine import storage

    target = tmp_path / "out.json"

    def _fake_replace(src, dst):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(os, "replace", _fake_replace)
    monkeypatch.setattr(storage, "os", os)  # ensure storage uses patched os

    with pytest.raises(OSError, match="simulated replace failure"):
        storage._atomic_write_json(target, {"x": 1})

    # No orphan .tmp files in tmp_path.
    leftovers = [p for p in tmp_path.glob("*.tmp")]
    assert leftovers == [], f"orphan tmp files: {leftovers}"


# ---------------------------------------------------------------------------
# Test 4: write_daily_snapshot — three-phase write order.
# ---------------------------------------------------------------------------

def test_three_phase_write_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Per-ticker JSONs FIRST → _index.json SECOND → _status.json LAST (Pattern #4 lock)."""
    from routine import storage

    call_order: list[str] = []
    real_write = storage._atomic_write_json

    def _spy(path: Path, payload):
        call_order.append(path.name)
        return real_write(path, payload)

    monkeypatch.setattr(storage, "_atomic_write_json", _spy)

    results = [
        _make_ticker_result("AAPL"),
        _make_ticker_result("MSFT"),
        _make_ticker_result("NVDA"),
    ]
    storage.write_daily_snapshot(
        results,
        date_str="2026-05-04",
        run_started_at=RUN_STARTED,
        run_completed_at=RUN_COMPLETED,
        lite_mode=False,
        total_token_count_estimate=58_400,
        snapshots_root=tmp_path,
    )
    # Expected order: 3 per-ticker JSONs (any per-ticker order is fine — Pattern
    # #4 only locks the A→B→C phase boundaries, NOT per-ticker order); then
    # _index.json; then _status.json LAST.
    assert call_order[-2:] == ["_index.json", "_status.json"], (
        f"_index.json + _status.json must be the LAST two writes; got {call_order}"
    )
    # The first 3 writes must be the per-ticker JSONs.
    per_ticker = call_order[:3]
    assert sorted(per_ticker) == sorted(["AAPL.json", "MSFT.json", "NVDA.json"])


# ---------------------------------------------------------------------------
# Test 5: _index.json schema.
# ---------------------------------------------------------------------------

def test_index_json_schema(tmp_path: Path) -> None:
    """_index.json carries date + schema_version=1 + run timestamps + tickers + lite + tokens."""
    from routine import storage

    results = [_make_ticker_result("AAPL"), _make_ticker_result("MSFT")]
    storage.write_daily_snapshot(
        results,
        date_str="2026-05-04",
        run_started_at=RUN_STARTED,
        run_completed_at=RUN_COMPLETED,
        lite_mode=False,
        total_token_count_estimate=39_600,
        snapshots_root=tmp_path,
    )
    idx_path = tmp_path / "2026-05-04" / "_index.json"
    assert idx_path.exists()
    idx = json.loads(idx_path.read_text(encoding="utf-8"))
    assert idx["date"] == "2026-05-04"
    assert idx["schema_version"] == 1
    assert idx["run_started_at"] == RUN_STARTED.isoformat()
    assert idx["run_completed_at"] == RUN_COMPLETED.isoformat()
    assert sorted(idx["tickers"]) == ["AAPL", "MSFT"]
    assert idx["lite_mode"] is False
    assert idx["total_token_count_estimate"] == 39_600


# ---------------------------------------------------------------------------
# Test 6: _status.json happy-path schema (LLM-08).
# ---------------------------------------------------------------------------

def test_status_json_schema_success(tmp_path: Path) -> None:
    """5-ticker successful run → success=True; partial=lite_mode; failed/skipped empty."""
    from routine import storage

    results = [_make_ticker_result(t) for t in
               ("AAPL", "MSFT", "NVDA", "GOOG", "AMZN")]
    storage.write_daily_snapshot(
        results,
        date_str="2026-05-04",
        run_started_at=RUN_STARTED,
        run_completed_at=RUN_COMPLETED,
        lite_mode=False,
        total_token_count_estimate=99_000,
        snapshots_root=tmp_path,
    )
    status_path = tmp_path / "2026-05-04" / "_status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))

    # All 7 LLM-08 keys present.
    expected_keys = {
        "success", "partial", "completed_tickers", "failed_tickers",
        "skipped_tickers", "llm_failure_count", "lite_mode",
    }
    assert set(status.keys()) >= expected_keys

    assert status["success"] is True
    assert status["partial"] is False  # lite_mode=False, no failures
    assert sorted(status["completed_tickers"]) == [
        "AAPL", "AMZN", "GOOG", "MSFT", "NVDA",
    ]
    assert status["failed_tickers"] == []
    assert status["skipped_tickers"] == []
    assert status["llm_failure_count"] == 0
    assert status["lite_mode"] is False


# ---------------------------------------------------------------------------
# Test 7: failed_tickers populated on per-ticker OSError, loop continues.
# ---------------------------------------------------------------------------

def test_status_json_failed_tickers_populated_on_OSError(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If _atomic_write_json raises on the 2nd ticker, run continues for the 3rd."""
    from routine import storage

    real_write = storage._atomic_write_json
    call_count = {"n": 0}

    def _flaky_write(path: Path, payload):
        # Raise OSError ONLY when writing MSFT.json (the 2nd ticker).
        if path.name == "MSFT.json":
            raise OSError("disk full")
        call_count["n"] += 1
        return real_write(path, payload)

    monkeypatch.setattr(storage, "_atomic_write_json", _flaky_write)

    results = [
        _make_ticker_result("AAPL"),
        _make_ticker_result("MSFT"),
        _make_ticker_result("NVDA"),
    ]
    outcome = storage.write_daily_snapshot(
        results,
        date_str="2026-05-04",
        run_started_at=RUN_STARTED,
        run_completed_at=RUN_COMPLETED,
        lite_mode=False,
        total_token_count_estimate=58_400,
        snapshots_root=tmp_path,
    )

    # AAPL + NVDA written successfully; MSFT in failed_tickers.
    assert sorted(outcome.completed) == ["AAPL", "NVDA"]
    assert outcome.failed == ["MSFT"]

    # _status.json reflects the failure.
    status_path = tmp_path / "2026-05-04" / "_status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["success"] is False  # failed_tickers non-empty
    assert status["partial"] is True
    assert status["failed_tickers"] == ["MSFT"]
    assert sorted(status["completed_tickers"]) == ["AAPL", "NVDA"]


# ---------------------------------------------------------------------------
# Test 8: llm_failure_count from persona data_unavailable.
# ---------------------------------------------------------------------------

def test_llm_failure_count_persona_data_unavailable(tmp_path: Path) -> None:
    """2 of 6 personas data_unavailable=True on a single ticker → +2 to llm_failure_count."""
    from routine import storage

    results = [_make_ticker_result("AAPL", n_personas_unavailable=2)]
    storage.write_daily_snapshot(
        results,
        date_str="2026-05-04",
        run_started_at=RUN_STARTED,
        run_completed_at=RUN_COMPLETED,
        lite_mode=False,
        total_token_count_estimate=19_800,
        snapshots_root=tmp_path,
    )
    status = json.loads(
        (tmp_path / "2026-05-04" / "_status.json").read_text(encoding="utf-8"),
    )
    assert status["llm_failure_count"] == 2


# ---------------------------------------------------------------------------
# Test 9: llm_failure_count synthesizer failure outside lite mode.
# ---------------------------------------------------------------------------

def test_llm_failure_count_synthesizer_failure_outside_lite_mode(tmp_path: Path) -> None:
    """ticker_decision=None + lite_mode=False → +1 (synth failure). lite_mode=True → +0."""
    from routine import storage

    # Outside lite mode: synthesizer failure counts.
    results_a = [_make_ticker_result("AAPL", decision_present=False)]
    storage.write_daily_snapshot(
        results_a,
        date_str="2026-05-04",
        run_started_at=RUN_STARTED, run_completed_at=RUN_COMPLETED,
        lite_mode=False, total_token_count_estimate=19_800,
        snapshots_root=tmp_path,
    )
    status_a = json.loads(
        (tmp_path / "2026-05-04" / "_status.json").read_text(encoding="utf-8"),
    )
    assert status_a["llm_failure_count"] == 1  # synth-only failure

    # Inside lite mode: no decision is the design (skipped); not a failure.
    results_b = [_make_ticker_result("MSFT", decision_present=False, persona_count=0)]
    storage.write_daily_snapshot(
        results_b,
        date_str="2026-05-05",
        run_started_at=RUN_STARTED, run_completed_at=RUN_COMPLETED,
        lite_mode=True, total_token_count_estimate=0,
        snapshots_root=tmp_path,
    )
    status_b = json.loads(
        (tmp_path / "2026-05-05" / "_status.json").read_text(encoding="utf-8"),
    )
    assert status_b["llm_failure_count"] == 0
    assert status_b["lite_mode"] is True
    assert status_b["partial"] is True


# ---------------------------------------------------------------------------
# Test 10: round-trip per-ticker JSON.
# ---------------------------------------------------------------------------

def test_round_trip_per_ticker_json(tmp_path: Path) -> None:
    """Build TickerResult → write → read → assert key fields preserved.

    Phase 6 / Plan 06-01: per-ticker JSON schema_version bumped 1→2.
    """
    from routine import storage

    results = [_make_ticker_result("AAPL")]
    storage.write_daily_snapshot(
        results,
        date_str="2026-05-04",
        run_started_at=RUN_STARTED, run_completed_at=RUN_COMPLETED,
        lite_mode=False, total_token_count_estimate=19_800,
        snapshots_root=tmp_path,
    )
    body = json.loads(
        (tmp_path / "2026-05-04" / "AAPL.json").read_text(encoding="utf-8"),
    )
    assert body["ticker"] == "AAPL"
    assert body["schema_version"] == 2
    assert len(body["analytical_signals"]) == 4
    assert len(body["persona_signals"]) == 6
    assert body["ticker_decision"] is not None
    assert body["ticker_decision"]["recommendation"] == "hold"
    assert body["errors"] == []
    assert body["position_signal"] is not None
    assert body["position_signal"]["state"] == "fair"


# ---------------------------------------------------------------------------
# Test 11 (extra coverage): lite_mode=True propagates lite_mode field on _index.json.
# ---------------------------------------------------------------------------

def test_lite_mode_field_surfaces_in_index_and_status(tmp_path: Path) -> None:
    """lite_mode=True → both _index.json.lite_mode and _status.json.lite_mode are True."""
    from routine import storage

    results = [_make_ticker_result("AAPL", decision_present=False, persona_count=0)]
    storage.write_daily_snapshot(
        results,
        date_str="2026-05-04",
        run_started_at=RUN_STARTED, run_completed_at=RUN_COMPLETED,
        lite_mode=True, total_token_count_estimate=613_800,
        snapshots_root=tmp_path,
    )
    idx = json.loads(
        (tmp_path / "2026-05-04" / "_index.json").read_text(encoding="utf-8"),
    )
    status = json.loads(
        (tmp_path / "2026-05-04" / "_status.json").read_text(encoding="utf-8"),
    )
    assert idx["lite_mode"] is True
    assert status["lite_mode"] is True
    assert status["partial"] is True


# ---------------------------------------------------------------------------
# Test 12 (extra coverage): write_failure_status emits success=False shape.
# ---------------------------------------------------------------------------

def test_write_failure_status_emits_success_false(tmp_path: Path) -> None:
    """write_failure_status writes _status.json with success=False + error field."""
    from routine import storage

    storage.write_failure_status(
        snapshots_root=tmp_path,
        date_str="2026-05-04",
        run_started_at=RUN_STARTED,
        error_msg="boom: something went wrong",
    )
    status_path = tmp_path / "2026-05-04" / "_status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["success"] is False
    assert status["partial"] is True
    assert status["completed_tickers"] == []
    assert status["failed_tickers"] == []
    assert status["lite_mode"] is False
    assert "error" in status
    assert "boom" in status["error"]


# ---------------------------------------------------------------------------
# Test 13 (Nyquist gap-fill): both _status.json writers satisfy LLM-08
# minimum-key contract. Verifier Important finding #2 flagged the divergence
# between happy-path (write_daily_snapshot, 7 keys) and failure-path
# (write_failure_status, 9 keys) shapes. LLM-08 spec mandates 6 minimum keys:
# {success, partial, completed_tickers, failed_tickers, skipped_tickers,
# llm_failure_count}. Phase 6 frontend zod validation MUST tolerate either
# shape; this test pins both writers' contract conformance so a future
# refactor that adds/removes a top-level key from EITHER writer is caught.
# ---------------------------------------------------------------------------

LLM_08_MIN_KEYS = {
    "success",
    "partial",
    "completed_tickers",
    "failed_tickers",
    "skipped_tickers",
    "llm_failure_count",
    "lite_mode",
}


def test_status_json_both_writers_satisfy_llm_08_minimum_keys(
    tmp_path: Path,
) -> None:
    """Both write_daily_snapshot AND write_failure_status emit the LLM-08 keys.

    LLM-08 contract: _status.json MUST contain at minimum the 7 keys listed
    in LLM_08_MIN_KEYS. Two separate writers exist (happy-path
    write_daily_snapshot + failure-path write_failure_status); both MUST
    satisfy the contract independently so the Phase 6 frontend can assume
    these keys exist regardless of which path produced the file.

    Stage-2 verifier Important finding #2 documents the schema divergence
    (failure-path adds run_started_at + error; happy-path adds nothing
    extra). This test pins BOTH writers' minimum contract; a future change
    that drops `lite_mode` from the failure-path (for example) is caught.
    """
    from routine import storage

    # Happy-path writer.
    happy_dir = tmp_path / "happy"
    storage.write_daily_snapshot(
        [_make_ticker_result("AAPL")],
        date_str="2026-05-04",
        run_started_at=RUN_STARTED,
        run_completed_at=RUN_COMPLETED,
        lite_mode=False,
        total_token_count_estimate=19_800,
        snapshots_root=happy_dir,
    )
    happy_status = json.loads(
        (happy_dir / "2026-05-04" / "_status.json").read_text(encoding="utf-8"),
    )

    # Failure-path writer.
    failure_dir = tmp_path / "failure"
    storage.write_failure_status(
        snapshots_root=failure_dir,
        date_str="2026-05-04",
        run_started_at=RUN_STARTED,
        error_msg="entrypoint crash",
    )
    failure_status = json.loads(
        (failure_dir / "2026-05-04" / "_status.json").read_text(encoding="utf-8"),
    )

    # Both shapes MUST contain every LLM-08 minimum key.
    happy_missing = LLM_08_MIN_KEYS - set(happy_status.keys())
    failure_missing = LLM_08_MIN_KEYS - set(failure_status.keys())
    assert not happy_missing, (
        f"write_daily_snapshot _status.json missing LLM-08 keys: {happy_missing}"
    )
    assert not failure_missing, (
        f"write_failure_status _status.json missing LLM-08 keys: {failure_missing}"
    )

    # The keys' value types are consistent across both shapes (Phase 6 zod
    # can use a single base validator with optional extensions).
    for shape_name, status in (("happy", happy_status), ("failure", failure_status)):
        assert isinstance(status["success"], bool), shape_name
        assert isinstance(status["partial"], bool), shape_name
        assert isinstance(status["completed_tickers"], list), shape_name
        assert isinstance(status["failed_tickers"], list), shape_name
        assert isinstance(status["skipped_tickers"], list), shape_name
        assert isinstance(status["llm_failure_count"], int), shape_name
        assert isinstance(status["lite_mode"], bool), shape_name

    # The DIVERGENCE is also locked: failure-path includes 'error' +
    # 'run_started_at'; happy-path does not. If a future refactor unifies
    # the shapes, that's an INTENTIONAL contract change; this assertion
    # reminds the maintainer to update Phase 6 zod schemas in lockstep.
    assert "error" in failure_status
    assert "run_started_at" in failure_status
    assert "error" not in happy_status


# ---------------------------------------------------------------------------
# Phase 6 / Plan 06-01: per-ticker payload extensions
#
# The Wave 0 amendment extends the per-ticker JSON shape with 4 new fields:
#   * ohlc_history    — list of last 180 trading days
#   * indicators      — dict of 5 series aligned to ohlc_history dates
#   * headlines       — list of raw {source, published_at, title, url} dicts
#   * schema_version  — bumped 1→2
# Plus a new file at the repo root: data/_dates.json.
# ---------------------------------------------------------------------------


def test_per_ticker_payload_schema_version_is_2(tmp_path: Path) -> None:
    """schema_version in per-ticker JSON bumped 1→2 (Plan 06-01)."""
    from routine import storage

    results = [_make_ticker_result("AAPL", ohlc_history=_make_ohlc_history(180))]
    storage.write_daily_snapshot(
        results,
        date_str="2026-05-04",
        run_started_at=RUN_STARTED, run_completed_at=RUN_COMPLETED,
        lite_mode=False, total_token_count_estimate=19_800,
        snapshots_root=tmp_path,
    )
    body = json.loads(
        (tmp_path / "2026-05-04" / "AAPL.json").read_text(encoding="utf-8"),
    )
    assert body["schema_version"] == 2


def test_per_ticker_payload_contains_ohlc_history(tmp_path: Path) -> None:
    """payload['ohlc_history'] is a list of 180 dicts with the 6 OHLC keys.

    Frontend deep-dive chart (VIEW-06) reads this list directly to render the
    OHLC candles + overlays.
    """
    from routine import storage

    results = [_make_ticker_result("AAPL", ohlc_history=_make_ohlc_history(180))]
    storage.write_daily_snapshot(
        results,
        date_str="2026-05-04",
        run_started_at=RUN_STARTED, run_completed_at=RUN_COMPLETED,
        lite_mode=False, total_token_count_estimate=19_800,
        snapshots_root=tmp_path,
    )
    body = json.loads(
        (tmp_path / "2026-05-04" / "AAPL.json").read_text(encoding="utf-8"),
    )
    assert "ohlc_history" in body
    assert isinstance(body["ohlc_history"], list)
    assert len(body["ohlc_history"]) == 180
    for bar in body["ohlc_history"]:
        assert isinstance(bar, dict)
        assert set(bar.keys()) >= {"date", "open", "high", "low", "close", "volume"}
        assert isinstance(bar["date"], str)  # ISO date
        # Close strictly positive (OHLCBar invariant).
        assert isinstance(bar["close"], (int, float)) and bar["close"] > 0
        assert isinstance(bar["volume"], int)


def test_per_ticker_payload_contains_indicators_with_5_series(tmp_path: Path) -> None:
    """payload['indicators'] is a dict with 5 keys aligned to ohlc_history.

    Each series is a list of (float | None) where None marks the warmup
    period at the head: ma20 first 19 entries None, ma50 first 49, bb_upper +
    bb_lower first 19, rsi14 first 14.

    The frontend chart (Phase 6 Wave 3) layers these as overlays on the OHLC
    candles. Indicator math must be byte-identical to what the analyst verdicts
    use at iloc[-1] — locked by tests/analysts/test_indicator_math.py series
    helpers.
    """
    from routine import storage

    history = _make_ohlc_history(180)
    results = [_make_ticker_result("AAPL", ohlc_history=history)]
    storage.write_daily_snapshot(
        results,
        date_str="2026-05-04",
        run_started_at=RUN_STARTED, run_completed_at=RUN_COMPLETED,
        lite_mode=False, total_token_count_estimate=19_800,
        snapshots_root=tmp_path,
    )
    body = json.loads(
        (tmp_path / "2026-05-04" / "AAPL.json").read_text(encoding="utf-8"),
    )
    assert "indicators" in body
    assert isinstance(body["indicators"], dict)
    expected_keys = {"ma20", "ma50", "bb_upper", "bb_lower", "rsi14"}
    assert set(body["indicators"].keys()) >= expected_keys

    n = len(body["ohlc_history"])
    for key in expected_keys:
        series = body["indicators"][key]
        assert isinstance(series, list), f"{key} must be a list"
        assert len(series) == n, f"{key} length {len(series)} != ohlc_history length {n}"
        # Each entry is float OR None (None during warmup window).
        for v in series:
            assert v is None or isinstance(v, (int, float)), (
                f"{key} entries must be float-or-None"
            )

    # ma20 warmup: first 19 entries are None; entry 19 is the first real value.
    ma20 = body["indicators"]["ma20"]
    assert all(v is None for v in ma20[:19])
    assert ma20[19] is not None

    # ma50 warmup: first 49 None.
    ma50 = body["indicators"]["ma50"]
    assert all(v is None for v in ma50[:49])
    assert ma50[49] is not None

    # rsi14 warmup: first 14 None.
    rsi = body["indicators"]["rsi14"]
    assert all(v is None for v in rsi[:14])
    assert rsi[14] is not None

    # bb_upper / bb_lower warmup: first 19 None.
    for key in ("bb_upper", "bb_lower"):
        s = body["indicators"][key]
        assert all(v is None for v in s[:19])
        assert s[19] is not None


def test_per_ticker_payload_contains_headlines(tmp_path: Path) -> None:
    """payload['headlines'] is a list of raw-headline dicts with 4 required keys.

    Frontend deep-dive news feed (VIEW-08) groups by source and renders these
    directly. Sorted by published_at desc by virtue of fetch_news's existing
    _sort_by_recency pass.
    """
    from routine import storage

    raw_headlines = [
        _make_raw_headline(source="yahoo-rss", title="Apple beats Q1", url="https://y/1"),
        _make_raw_headline(source="google-news", title="AAPL guides up", url="https://g/2"),
        _make_raw_headline(source="finviz", title="AAPL analyst upgrade", url="https://f/3"),
    ]
    results = [
        _make_ticker_result(
            "AAPL", ohlc_history=_make_ohlc_history(60), headlines=raw_headlines
        )
    ]
    storage.write_daily_snapshot(
        results,
        date_str="2026-05-04",
        run_started_at=RUN_STARTED, run_completed_at=RUN_COMPLETED,
        lite_mode=False, total_token_count_estimate=19_800,
        snapshots_root=tmp_path,
    )
    body = json.loads(
        (tmp_path / "2026-05-04" / "AAPL.json").read_text(encoding="utf-8"),
    )
    assert "headlines" in body
    assert isinstance(body["headlines"], list)
    assert len(body["headlines"]) == 3
    for h in body["headlines"]:
        assert isinstance(h, dict)
        assert set(h.keys()) >= {"source", "published_at", "title", "url"}


def test_dates_index_written_at_repo_root(tmp_path: Path) -> None:
    """write_daily_snapshot writes data/_dates.json at the snapshots root.

    The frontend (Phase 6 Wave 1) fetches this single file to enumerate
    available snapshot dates without making N GitHub directory-listing calls.
    Sorted YYYY-MM-DD strings; populated by enumerating subfolders that
    contain a `_status.json`.
    """
    from routine import storage

    # Pre-create two prior date folders with _status.json sentinels.
    for prior_date in ("2026-04-01", "2026-04-30"):
        prior_folder = tmp_path / prior_date
        prior_folder.mkdir(parents=True, exist_ok=True)
        (prior_folder / "_status.json").write_text("{}", encoding="utf-8")

    # Now call write_daily_snapshot for 2026-05-04.
    results = [_make_ticker_result("AAPL", ohlc_history=_make_ohlc_history(60))]
    storage.write_daily_snapshot(
        results,
        date_str="2026-05-04",
        run_started_at=RUN_STARTED, run_completed_at=RUN_COMPLETED,
        lite_mode=False, total_token_count_estimate=19_800,
        snapshots_root=tmp_path,
    )

    dates_index_path = tmp_path / "_dates.json"
    assert dates_index_path.exists(), (
        f"data/_dates.json not written at snapshots root ({tmp_path})"
    )
    payload = json.loads(dates_index_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert "dates_available" in payload
    assert isinstance(payload["dates_available"], list)
    # All 3 dates present, sorted ascending.
    assert payload["dates_available"] == ["2026-04-01", "2026-04-30", "2026-05-04"]
    assert "updated_at" in payload
    assert isinstance(payload["updated_at"], str)
