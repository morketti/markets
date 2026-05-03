"""Tests for analysts/_indicator_math.py — shared indicator helpers.

Coverage map (per 04-01-foundation-PLAN.md):
  * `_build_df` — empty-history early return; sort_index defense against
    out-of-order input.
  * `_adx_14` — None below ADX_MIN_BARS (27); valid float at ≥27 bars;
    > 25 (trend regime) for synthetic_uptrend_history(252).
  * `_total_to_verdict` — strict > / < boundaries at ±0.6 / ±0.2 (parametrized
    over 10 cases including the boundary-exact values).
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from analysts._indicator_math import (
    ADX_MIN_BARS,
    ADX_PERIOD,
    ADX_RANGE_BELOW,
    ADX_STABLE_BARS,
    ADX_TREND_ABOVE,
    _adx_14,
    _build_df,
    _total_to_verdict,
)
from analysts.data.prices import OHLCBar
from tests.analysts.conftest import synthetic_uptrend_history


# ---------------------------------------------------------------------------
# _build_df
# ---------------------------------------------------------------------------


def test_build_df_empty_history_returns_empty_df() -> None:
    """Empty input → empty DataFrame with the canonical 3 columns."""
    df = _build_df([])
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0
    assert list(df.columns) == ["high", "low", "close"]


def test_build_df_sorts_unsorted_input() -> None:
    """Out-of-order history is sorted by date in the resulting DataFrame."""
    base = date(2026, 1, 1)
    # Build 5 bars but feed them in shuffled date order.
    bars = [
        OHLCBar(date=base + timedelta(days=2), open=99.8, high=101.0, low=99.0, close=100.0, volume=1_000_000),
        OHLCBar(date=base + timedelta(days=0), open=99.8, high=101.0, low=99.0, close=100.5, volume=1_000_100),
        OHLCBar(date=base + timedelta(days=4), open=99.8, high=101.0, low=99.0, close=101.0, volume=1_000_200),
        OHLCBar(date=base + timedelta(days=1), open=99.8, high=101.0, low=99.0, close=100.2, volume=1_000_300),
        OHLCBar(date=base + timedelta(days=3), open=99.8, high=101.0, low=99.0, close=100.7, volume=1_000_400),
    ]
    df = _build_df(bars)
    assert len(df) == 5
    # Index must be monotonically increasing after sort_index.
    assert df.index.is_monotonic_increasing


# ---------------------------------------------------------------------------
# _adx_14 — warm-up boundary discipline
# ---------------------------------------------------------------------------


def test_adx_14_returns_none_below_min_bars() -> None:
    """20-bar history → _adx_14 returns None (need ≥27 for Wilder warm-up)."""
    df = _build_df(synthetic_uptrend_history(20))
    assert _adx_14(df) is None


def test_adx_14_returns_none_at_26_bars() -> None:
    """26-bar history → still None (boundary discipline: < 27 fails)."""
    df = _build_df(synthetic_uptrend_history(26))
    assert _adx_14(df) is None


def test_adx_14_returns_float_at_27_bars() -> None:
    """27-bar history → valid float (warm-up boundary just met)."""
    df = _build_df(synthetic_uptrend_history(27))
    val = _adx_14(df)
    assert val is not None
    assert isinstance(val, float)


def test_adx_14_uptrend_252bars_trend_regime() -> None:
    """Sustained 252-bar uptrend → ADX firmly in trend regime (> 25)."""
    df = _build_df(synthetic_uptrend_history(252))
    val = _adx_14(df)
    assert val is not None
    assert val > 25.0


# ---------------------------------------------------------------------------
# _total_to_verdict — strict boundary discipline
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "normalized,expected",
    [
        (0.7, "strong_bullish"),
        (0.61, "strong_bullish"),
        (0.6, "bullish"),  # strict > 0.6 fails
        (0.5, "bullish"),
        (0.21, "bullish"),
        (0.2, "neutral"),  # strict > 0.2 fails
        (0.0, "neutral"),
        (-0.2, "neutral"),  # strict < -0.2 fails
        (-0.21, "bearish"),
        (-0.6, "bearish"),  # strict < -0.6 fails
        (-0.61, "strong_bearish"),
        (-0.7, "strong_bearish"),
    ],
)
def test_total_to_verdict_strict_boundaries(normalized: float, expected: str) -> None:
    """Verdict ladder uses STRICT > / < boundaries (NOT >=)."""
    assert _total_to_verdict(normalized) == expected


# ---------------------------------------------------------------------------
# Module constants — value lock
# ---------------------------------------------------------------------------


def test_adx_constants_are_locked() -> None:
    """ADX module constants must match the Phase 3 03-03 locked values."""
    assert ADX_PERIOD == 14
    assert ADX_TREND_ABOVE == 25.0
    assert ADX_RANGE_BELOW == 20.0
    assert ADX_MIN_BARS == 27
    assert ADX_STABLE_BARS == 150
