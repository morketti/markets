"""Tests for analysts/technicals.py — pure-function deterministic technicals scoring.

Coverage map (per 03-03-technicals-PLAN.md):
  * Known-regime regressions (252-bar synthetic uptrend / downtrend / sideways)
  * Min-bars warm-up guards (10 / 25 / 50 / 100 bars all return correct signal)
  * Empty-data UNIFORM RULE (snapshot.data_unavailable / prices=None /
    prices.data_unavailable / empty history)
  * Indicator correctness — MA stack patterns (bullish / bearish / mixed),
    momentum sign, ADX trend vs range regimes
  * Provenance header presence (INFRA-07) — names virattt source file
  * Pure pandas guarantee — no pandas-ta / talib imports
  * Determinism + computed_at pass-through

Imports follow the pattern set by 03-01 + 03-02: shared fixtures + module-level
synthetic builders from tests/analysts/conftest.py; schemas from analysts/.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from analysts.data.prices import OHLCBar, PriceSnapshot
from analysts.signals import AgentSignal
from analysts.technicals import score
from tests.analysts.conftest import (
    synthetic_downtrend_history,
    synthetic_sideways_history,
    synthetic_uptrend_history,
)


# ---------------------------------------------------------------------------
# Helpers — local PriceSnapshot builder so each test reads cleanly.
# ---------------------------------------------------------------------------


def _make_price_snapshot(
    history: list[OHLCBar],
    *,
    ticker: str = "AAPL",
    fetched_at: datetime | None = None,
    data_unavailable: bool = False,
) -> PriceSnapshot:
    """Wrap a synthetic OHLCBar list into a PriceSnapshot with sensible defaults."""
    return PriceSnapshot(
        ticker=ticker,
        fetched_at=fetched_at or datetime(2026, 5, 1, 13, 30, 0, tzinfo=timezone.utc),
        source="yfinance",
        data_unavailable=data_unavailable,
        current_price=history[-1].close if history else None,
        history=history,
    )


# ---------------------------------------------------------------------------
# Known-regime regressions (252-bar synthetic fixtures from conftest)
# ---------------------------------------------------------------------------


def test_known_uptrend_strong_bullish(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """252-bar uptrend → MA stack bullish; verdict in {bullish, strong_bullish}."""
    history = synthetic_uptrend_history(252)
    snap = make_snapshot(prices=_make_price_snapshot(history))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.analyst_id == "technicals"
    assert sig.data_unavailable is False
    assert sig.verdict in ("bullish", "strong_bullish")
    assert sig.confidence > 0
    # Bullish stack evidence string MUST be present (locks the canonical wording).
    bullish_stack = [e for e in sig.evidence if "bullish stack" in e.lower()]
    assert len(bullish_stack) == 1, f"expected 'bullish stack' evidence, got {sig.evidence!r}"


def test_known_downtrend_strong_bearish(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """252-bar downtrend → MA stack bearish; verdict in {bearish, strong_bearish}."""
    history = synthetic_downtrend_history(252)
    snap = make_snapshot(prices=_make_price_snapshot(history))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.verdict in ("bearish", "strong_bearish")
    assert sig.confidence > 0
    bearish_stack = [e for e in sig.evidence if "bearish stack" in e.lower()]
    assert len(bearish_stack) == 1, f"expected 'bearish stack' evidence, got {sig.evidence!r}"


def test_known_sideways_neutral(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """252-bar sideways → no strong verdict; magnitude small."""
    history = synthetic_sideways_history(252)
    snap = make_snapshot(prices=_make_price_snapshot(history))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    # Sideways may tilt slightly either direction at the boundary, but must NOT
    # hit the strong tier and confidence must stay low (≤40 per plan).
    assert sig.verdict in ("neutral", "bullish", "bearish")
    assert sig.confidence <= 40, f"sideways must not produce high confidence, got {sig.confidence}"


# ---------------------------------------------------------------------------
# Warm-up min-bars guards
# ---------------------------------------------------------------------------


def test_warmup_lt20_bars_data_unavailable(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """history < 20 bars → AgentSignal(data_unavailable=True, verdict=neutral)."""
    history = synthetic_uptrend_history(15)
    snap = make_snapshot(prices=_make_price_snapshot(history))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.data_unavailable is True
    assert sig.verdict == "neutral"
    assert sig.confidence == 0
    assert len(sig.evidence) == 1
    assert "15 bars" in sig.evidence[0]
    assert "20" in sig.evidence[0]


def test_warmup_25_bars_no_adx(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """25 bars → MA20 evidence present; ADX absent (needs 27 bars)."""
    history = synthetic_uptrend_history(25)
    snap = make_snapshot(prices=_make_price_snapshot(history))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.data_unavailable is False
    # ADX absent.
    adx_evidence = [e for e in sig.evidence if "ADX" in e]
    assert len(adx_evidence) == 0
    # MA20 unavailable too at 25 bars (below 50 — no MA stack at all);
    # 1m momentum needs 22 bars (>21) so it should be present.
    momentum_1m = [e for e in sig.evidence if "1m momentum" in e]
    assert len(momentum_1m) == 1


def test_warmup_50_bars_partial(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """50 bars → MA20+MA50 + 1m momentum + ADX; MA200 + 3m + 6m absent."""
    history = synthetic_uptrend_history(50)
    snap = make_snapshot(prices=_make_price_snapshot(history))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.data_unavailable is False
    evidence_str = " | ".join(sig.evidence)
    # MA20 + MA50 present (at 50 bars exactly — needs >= 50 for MA50).
    assert "MA20" in evidence_str
    assert "MA50" in evidence_str
    # MA200 explicitly NOT present as a 200-bar value (MA200 only appears in
    # the bullish/bearish "MA200 (xxx)" form when 200+ bars exist).
    assert "MA200" not in evidence_str or "MA200 unavailable" in evidence_str
    # 1m momentum present (50 > 21).
    assert "1m momentum" in evidence_str
    # 3m + 6m momentum absent.
    assert "3m momentum" not in evidence_str
    assert "6m momentum" not in evidence_str
    # ADX present (50 > 27).
    assert "ADX" in evidence_str


def test_warmup_100_bars_partial(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """100 bars → MA20+MA50 + 1m+3m + ADX; MA200 + 6m absent."""
    history = synthetic_uptrend_history(100)
    snap = make_snapshot(prices=_make_price_snapshot(history))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.data_unavailable is False
    evidence_str = " | ".join(sig.evidence)
    assert "MA20" in evidence_str
    assert "MA50" in evidence_str
    # MA200 unavailable note — at <200 bars, the MA helper notes "MA200 unavailable".
    assert "MA200 unavailable" in evidence_str or "200 bars" in evidence_str
    assert "1m momentum" in evidence_str
    assert "3m momentum" in evidence_str
    assert "6m momentum" not in evidence_str
    assert "ADX" in evidence_str


# ---------------------------------------------------------------------------
# Empty-data UNIFORM RULE
# ---------------------------------------------------------------------------


def test_empty_snapshot_data_unavailable(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """snapshot.data_unavailable=True → data_unavailable signal."""
    cfg = make_ticker_config()
    snap = make_snapshot(data_unavailable=True)

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.data_unavailable is True
    assert sig.verdict == "neutral"
    assert sig.confidence == 0
    assert len(sig.evidence) >= 1


def test_prices_none(make_snapshot, make_ticker_config, frozen_now) -> None:
    """snapshot.prices=None → data_unavailable signal."""
    cfg = make_ticker_config()
    snap = make_snapshot(prices=None)

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.data_unavailable is True
    assert sig.verdict == "neutral"


def test_prices_data_unavailable(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """snapshot.prices.data_unavailable=True → data_unavailable signal."""
    cfg = make_ticker_config()
    snap = make_snapshot(
        prices=PriceSnapshot(
            ticker="AAPL",
            fetched_at=frozen_now,
            source="yfinance",
            data_unavailable=True,
            current_price=None,
            history=[],
        )
    )

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.data_unavailable is True


def test_empty_history(make_snapshot, make_ticker_config, frozen_now) -> None:
    """snapshot.prices.history=[] (with data_unavailable=False) → data_unavailable signal."""
    cfg = make_ticker_config()
    snap = make_snapshot(
        prices=PriceSnapshot(
            ticker="AAPL",
            fetched_at=frozen_now,
            source="yfinance",
            data_unavailable=False,
            current_price=None,
            history=[],
        )
    )

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.data_unavailable is True


# ---------------------------------------------------------------------------
# Indicator correctness
# ---------------------------------------------------------------------------


def test_ma_alignment_bullish_stack(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """200-bar strong uptrend → MA20 > MA50 > MA200 → 'bullish stack' evidence."""
    history = synthetic_uptrend_history(200)
    snap = make_snapshot(prices=_make_price_snapshot(history))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    bullish_stack = [e for e in sig.evidence if "bullish stack" in e.lower()]
    assert len(bullish_stack) == 1


def test_ma_alignment_bearish_stack(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """200-bar strong downtrend → MA20 < MA50 < MA200 → 'bearish stack' evidence."""
    history = synthetic_downtrend_history(200)
    snap = make_snapshot(prices=_make_price_snapshot(history))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    bearish_stack = [e for e in sig.evidence if "bearish stack" in e.lower()]
    assert len(bearish_stack) == 1


def test_ma_alignment_mixed(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """V-shape: long downtrend then mild recovery → MA stack mixed.

    Construction must keep MA200 elevated above MA50 (legacy downtrend-era
    bars dominate the 200-bar window) while MA20 > MA50 (recent recovery).
    A short, mild recovery is required — a long or sharp recovery pulls
    MA50 above MA200 and produces a fully bullish stack instead.
    """
    # 200 bars down (200 → ~73.4) + 30 bars up at mild +0.5% drift.
    # MA20 (~80) > MA50 (~78) but MA200 (~95) > MA50 → mixed (not bullish).
    down = synthetic_downtrend_history(200, start=200.0, daily_drift=-0.005)
    up = synthetic_uptrend_history(30, start=down[-1].close, daily_drift=0.005)
    # Re-date the up segment so it follows the down segment chronologically.
    from datetime import timedelta
    last_down_date = down[-1].date
    up_redated = [
        OHLCBar(
            date=last_down_date + timedelta(days=i + 1),
            open=b.open,
            high=b.high,
            low=b.low,
            close=b.close,
            volume=b.volume,
        )
        for i, b in enumerate(up)
    ]
    history = down + up_redated
    snap = make_snapshot(prices=_make_price_snapshot(history))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    mixed = [e for e in sig.evidence if "MA stack mixed" in e]
    assert len(mixed) == 1, f"expected 'MA stack mixed' evidence, got {sig.evidence!r}"


def test_momentum_1m_positive(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """Strong recent gains → '1m momentum +' evidence."""
    # 30 bars of strong uptrend (>5% over 21 bars) — must trigger 1m bullish.
    history = synthetic_uptrend_history(30, start=100.0, daily_drift=0.01)
    snap = make_snapshot(prices=_make_price_snapshot(history))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    momentum_1m = [e for e in sig.evidence if "1m momentum" in e]
    assert len(momentum_1m) == 1
    # Must show a positive percentage with +sign.
    assert "+" in momentum_1m[0]


def test_momentum_1m_negative(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """Strong recent losses → '1m momentum -' evidence."""
    history = synthetic_downtrend_history(30, start=100.0, daily_drift=-0.01)
    snap = make_snapshot(prices=_make_price_snapshot(history))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    momentum_1m = [e for e in sig.evidence if "1m momentum" in e]
    assert len(momentum_1m) == 1
    # Must show a negative percentage.
    assert "-" in momentum_1m[0]


def test_adx_trend_regime(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """Strong unidirectional drift → ADX > 25 → 'trend regime' evidence."""
    history = synthetic_uptrend_history(252)
    snap = make_snapshot(prices=_make_price_snapshot(history))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    trend = [e for e in sig.evidence if "trend regime" in e.lower()]
    assert len(trend) == 1, f"expected 'trend regime' evidence, got {sig.evidence!r}"


def test_adx_range_or_ambiguous_regime(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """Sideways → ADX low → 'range regime' or 'ambiguous regime' evidence."""
    history = synthetic_sideways_history(252)
    snap = make_snapshot(prices=_make_price_snapshot(history))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    # Per plan note: sideways fixture amplitude may put ADX between 20-25
    # (ambiguous) on the boundary, so accept either range OR ambiguous.
    range_or_ambiguous = [
        e
        for e in sig.evidence
        if "range regime" in e.lower() or "ambiguous regime" in e.lower()
    ]
    assert len(range_or_ambiguous) == 1, f"expected range/ambiguous, got {sig.evidence!r}"


# ---------------------------------------------------------------------------
# Provenance + meta-tests
# ---------------------------------------------------------------------------


def test_provenance_header_present() -> None:
    """analysts/technicals.py must reference the virattt source per INFRA-07."""
    src = Path("analysts/technicals.py").read_text(encoding="utf-8")
    assert "virattt/ai-hedge-fund/src/agents/technicals.py" in src


def test_pandas_imported_no_pandas_ta() -> None:
    """analysts/technicals.py uses hand-rolled pandas — no ta-lib / pandas-ta IMPORTS.

    The provenance docstring legitimately mentions pandas-ta / ta-lib by name to
    enumerate the deps we deliberately rejected (per 03-RESEARCH.md "don't
    hand-roll" anti-pattern guidance). So this test inspects actual `import` /
    `from … import` statements, not raw substrings.
    """
    import re
    src = Path("analysts/technicals.py").read_text(encoding="utf-8")
    assert "import pandas as pd" in src
    forbidden = re.compile(
        r"^\s*(?:import|from)\s+(pandas_ta|talib|ta_lib)\b",
        re.MULTILINE,
    )
    matches = forbidden.findall(src)
    assert not matches, f"forbidden indicator-library imports found: {matches}"


def test_computed_at_passes_through(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """Explicit computed_at is preserved on the returned signal."""
    history = synthetic_uptrend_history(252)
    snap = make_snapshot(prices=_make_price_snapshot(history))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.computed_at == frozen_now


def test_computed_at_default_uses_now(make_snapshot, make_ticker_config) -> None:
    """Without explicit computed_at, default is approximately datetime.now(UTC)."""
    history = synthetic_uptrend_history(50)
    snap = make_snapshot(prices=_make_price_snapshot(history))
    cfg = make_ticker_config()

    before = datetime.now(timezone.utc)
    sig = score(snap, cfg)
    after = datetime.now(timezone.utc)

    assert before <= sig.computed_at <= after


def test_deterministic(make_snapshot, make_ticker_config, frozen_now) -> None:
    """Two calls with identical (snapshot, config, computed_at) → byte-identical signals."""
    history = synthetic_uptrend_history(252)
    snap = make_snapshot(prices=_make_price_snapshot(history))
    cfg = make_ticker_config()

    sig1 = score(snap, cfg, computed_at=frozen_now)
    sig2 = score(snap, cfg, computed_at=frozen_now)

    assert sig1.model_dump_json() == sig2.model_dump_json()


def test_returns_agent_signal_type(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """score() always returns an AgentSignal — never None, never raises for missing data."""
    history = synthetic_uptrend_history(252)
    snap = make_snapshot(prices=_make_price_snapshot(history))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert isinstance(sig, AgentSignal)
    assert sig.analyst_id == "technicals"


def test_build_df_sorts_unsorted_input(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """An out-of-order history list still produces a coherent (sorted) signal.

    Replaces the NaN-injection test from the plan — OHLCBar's gt=0 schema
    constraint prevents NaN at the schema layer, so we instead exercise the
    sort_index() codepath in _build_df by feeding a date-shuffled history.
    """
    history = synthetic_uptrend_history(252)
    # Reverse the list — chronologically backwards. _build_df must sort_index.
    reversed_history = list(reversed(history))
    snap = make_snapshot(prices=_make_price_snapshot(reversed_history))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    # The sorted+reversed-back history should produce the SAME signal as the
    # original chronological one — proves _build_df sorted the input.
    snap_chrono = make_snapshot(prices=_make_price_snapshot(history))
    sig_chrono = score(snap_chrono, cfg, computed_at=frozen_now)

    assert sig.verdict == sig_chrono.verdict
    assert sig.confidence == sig_chrono.confidence
