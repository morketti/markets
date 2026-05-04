"""Tests for analysts/_indicator_math.py — shared indicator helpers.

Coverage map (per 04-01-foundation-PLAN.md):
  * `_build_df` — empty-history early return; sort_index defense against
    out-of-order input.
  * `_adx_14` — None below ADX_MIN_BARS (27); valid float at ≥27 bars;
    > 25 (trend regime) for synthetic_uptrend_history(252).
  * `_total_to_verdict` — strict > / < boundaries at ±0.6 / ±0.2 (parametrized
    over 10 cases including the boundary-exact values).

Phase 6 / Plan 06-01 extension:
  * `_ma_series` — series-form MA producing values byte-identical to
    technicals._ma_alignment's iloc[-1] math at the same window.
  * `_bb_series` — series-form (upper, lower) producing values byte-identical
    to position_adjustment._bollinger_position's iloc[-1] math.
  * `_rsi_series` — series-form Wilder RSI producing values byte-identical to
    position_adjustment._rsi_14's iloc[-1] math.
"""
from __future__ import annotations

import math
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
from tests.analysts.conftest import (
    synthetic_oversold_history,
    synthetic_overbought_history,
    synthetic_uptrend_history,
)


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


# ---------------------------------------------------------------------------
# Phase 6 / Plan 06-01: series-form helpers
#
# These helpers are byte-identical at iloc[-1] to the existing single-point
# computations used by analysts/technicals.py (MA20/MA50) and
# analysts/position_adjustment.py (Bollinger position, RSI14). The frontend
# (Phase 6 Wave 3 deep-dive chart overlays) reads the per-day series; the
# analyst verdicts read iloc[-1]. They MUST agree, so the chart never shows
# a different MA/BB/RSI than the verdicts use.
# ---------------------------------------------------------------------------


def test_ma_series_byte_identical_to_single_point() -> None:
    """_ma_series(prices, 20).iloc[-1] == close.rolling(20).mean().iloc[-1] (technicals scalar)."""
    from analysts._indicator_math import _ma_series

    df = _build_df(synthetic_uptrend_history(252))
    close = df["close"]

    # Single-point reference (matches analysts/technicals._ma_alignment line 106).
    expected_ma20 = close.rolling(20).mean().iloc[-1]
    expected_ma50 = close.rolling(50).mean().iloc[-1]

    actual_ma20_series = _ma_series(close, 20)
    actual_ma50_series = _ma_series(close, 50)

    assert isinstance(actual_ma20_series, pd.Series)
    assert isinstance(actual_ma50_series, pd.Series)
    assert len(actual_ma20_series) == len(close)
    # First (window-1) entries are NaN (warmup); position 19 is first real value.
    assert pd.isna(actual_ma20_series.iloc[18])
    assert not pd.isna(actual_ma20_series.iloc[19])

    # Byte-identical (within 1e-9) at iloc[-1].
    assert math.isclose(
        float(actual_ma20_series.iloc[-1]), float(expected_ma20), rel_tol=1e-9, abs_tol=1e-9
    )
    assert math.isclose(
        float(actual_ma50_series.iloc[-1]), float(expected_ma50), rel_tol=1e-9, abs_tol=1e-9
    )


def test_bb_series_byte_identical_to_single_point() -> None:
    """_bb_series(prices, 20, 2.0) at iloc[-1] reproduces position_adjustment._bollinger_position math.

    Note: _bollinger_position computes (close - sma) / (2*std) — a scaled
    POSITION value. _bb_series returns the (upper, lower) BAND values
    upper = sma + sigma*std, lower = sma - sigma*std. Both consume the
    SAME rolling sma + rolling std at iloc[-1]; this test asserts the
    rolling primitives are byte-identical so the chart shows the same
    bands the analyst uses to compute its position.
    """
    from analysts._indicator_math import _bb_series

    df = _build_df(synthetic_overbought_history(252))
    close = df["close"]

    # Reference primitives (same expressions as position_adjustment._bollinger_position).
    sma_ref = close.rolling(20).mean().iloc[-1]
    std_ref = close.rolling(20).std().iloc[-1]
    expected_upper = sma_ref + 2.0 * std_ref
    expected_lower = sma_ref - 2.0 * std_ref

    upper, lower = _bb_series(close, window=20, sigma=2.0)
    assert isinstance(upper, pd.Series)
    assert isinstance(lower, pd.Series)
    assert len(upper) == len(close)
    assert len(lower) == len(close)
    # First 19 entries are NaN (warmup).
    assert pd.isna(upper.iloc[18])
    assert pd.isna(lower.iloc[18])
    assert not pd.isna(upper.iloc[19])
    assert not pd.isna(lower.iloc[19])

    assert math.isclose(
        float(upper.iloc[-1]), float(expected_upper), rel_tol=1e-9, abs_tol=1e-9
    )
    assert math.isclose(
        float(lower.iloc[-1]), float(expected_lower), rel_tol=1e-9, abs_tol=1e-9
    )


def test_rsi_series_byte_identical_to_single_point() -> None:
    """_rsi_series(prices, 14).iloc[-1] reproduces position_adjustment._rsi_14 math.

    Wilder smoothing via .ewm(alpha=1/14, adjust=False). First 14 entries
    (delta requires 1 prior bar; ewm warmup) are NaN.
    """
    from analysts._indicator_math import _rsi_series

    df = _build_df(synthetic_oversold_history(252))
    close = df["close"]

    # Reference single-point computation — matches position_adjustment._rsi_14.
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1.0 / 14, adjust=False).mean()
    loss = (-delta).clip(lower=0).ewm(alpha=1.0 / 14, adjust=False).mean()
    g, l = gain.iloc[-1], loss.iloc[-1]
    if l == 0.0:
        expected_rsi = 100.0
    else:
        rs = g / l
        expected_rsi = 100.0 - (100.0 / (1.0 + rs))

    actual_series = _rsi_series(close, period=14)
    assert isinstance(actual_series, pd.Series)
    assert len(actual_series) == len(close)
    # First 14 entries are NaN (period warmup).
    assert pd.isna(actual_series.iloc[13])
    assert not pd.isna(actual_series.iloc[14])

    assert math.isclose(
        float(actual_series.iloc[-1]), float(expected_rsi), rel_tol=1e-9, abs_tol=1e-9
    )
