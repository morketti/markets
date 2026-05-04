# novel-to-this-project — DRY-extracted indicator helpers (Phase 4 / Plan 04-01).
"""Shared indicator math used across the analyst suite.

Extracted from analysts/technicals.py (Phase 3 / Plan 03-03) and
analysts/{fundamentals,valuation}.py when the Phase 4 Position-Adjustment
Radar landed and the DRY trigger fired (4th copy of `_total_to_verdict`;
2nd consumer of `_build_df`; 2nd consumer of `_adx_14`).

Public surface (semantic-public — single underscore prefix is project
convention for module-internal helpers, but these are imported by sibling
analyst modules):

    _build_df(history)       -> pd.DataFrame    # high/low/close, sorted, dropna
    _adx_14(df)              -> Optional[float] # Wilder ADX(14); None < 27 bars
    _total_to_verdict(x)     -> Verdict         # 5-state ladder, strict > / <

Module-level constants (also imported by callers):

    ADX_PERIOD            = 14
    ADX_TREND_ABOVE       = 25.0
    ADX_RANGE_BELOW       = 20.0
    ADX_MIN_BARS          = 27   (= 2*N - 1, Wilder warm-up)
    ADX_STABLE_BARS       = 150  (below this, evidence flags ADX may be unstable)

Wilder smoothing is implemented as `pandas.Series.ewm(alpha=1/N, adjust=False).mean()` —
mathematically identical to Wilder's recursive recipe per StockCharts ChartSchool
(https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/average-directional-index-adx).

This module's existence is mechanical — it contains NO new logic vs. what
already shipped in Phase 3. Tests in tests/analysts/test_indicator_math.py
lock the public surface; tests in tests/analysts/test_technicals.py +
test_fundamentals.py + test_valuation.py + test_invariants.py serve as the
behavioral regression guard against extraction drift.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from analysts.data.prices import OHLCBar
from analysts.signals import Verdict

# ---------------------------------------------------------------------------
# ADX module constants — moved verbatim from analysts/technicals.py
# ---------------------------------------------------------------------------

ADX_PERIOD: int = 14
ADX_TREND_ABOVE: float = 25.0
ADX_RANGE_BELOW: float = 20.0
ADX_MIN_BARS: int = 27        # = 2*N - 1, Wilder warm-up
ADX_STABLE_BARS: int = 150    # below this, evidence flags possible instability


# ---------------------------------------------------------------------------
# DataFrame builder — verbatim move from analysts/technicals.py
# ---------------------------------------------------------------------------


def _build_df(history: list[OHLCBar]) -> pd.DataFrame:
    """Construct a DataFrame indexed by date with high/low/close columns.

    Sorts by date (defensive against out-of-order history lists) and drops
    rows whose close is NaN (defensive — OHLCBar's gt=0 schema constraint
    prevents NaN closes today, but a future schema relaxation should not
    silently produce NaN at iloc[-1] in indicator calculations).
    """
    if not history:
        return pd.DataFrame(columns=["high", "low", "close"])
    df = pd.DataFrame(
        {
            "high": [b.high for b in history],
            "low": [b.low for b in history],
            "close": [b.close for b in history],
        },
        index=pd.to_datetime([b.date for b in history]),
    ).sort_index()
    return df.dropna(subset=["close"])


# ---------------------------------------------------------------------------
# Wilder ADX(14) — verbatim move from analysts/technicals.py
# ---------------------------------------------------------------------------


def _adx_14(df: pd.DataFrame) -> Optional[float]:
    """Wilder ADX(14). Returns None below ADX_MIN_BARS (27) or on NaN result.

    Implementation walks through the canonical Wilder recipe using pandas
    primitives:
      1. True Range: max(high - low, |high - prev_close|, |low - prev_close|)
      2. +DM / -DM directional movement (positive when up-move dominates).
      3. Wilder-smooth (.ewm with alpha = 1/N, adjust=False) TR / +DM / -DM.
      4. +DI / -DI = 100 * smoothed +DM / smoothed TR (and likewise for -DI).
      5. DX = 100 * |+DI - -DI| / (+DI + -DI).
      6. ADX = Wilder-smoothed DX.

    Returns the latest ADX value as a float, or None if it computes to NaN
    (which can happen when +DI + -DI is identically zero — a flat-line bar
    series — or when not enough bars have accumulated).
    """
    if len(df) < ADX_MIN_BARS:
        return None
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)

    # True Range
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    # Directional Movement
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = pd.Series(0.0, index=df.index).where(
        ~((up_move > down_move) & (up_move > 0)), up_move
    )
    minus_dm = pd.Series(0.0, index=df.index).where(
        ~((down_move > up_move) & (down_move > 0)), down_move
    )

    alpha = 1.0 / ADX_PERIOD
    atr = tr.ewm(alpha=alpha, adjust=False).mean()
    plus_di = 100.0 * plus_dm.ewm(alpha=alpha, adjust=False).mean() / atr
    minus_di = 100.0 * minus_dm.ewm(alpha=alpha, adjust=False).mean() / atr

    di_sum = plus_di + minus_di
    # Avoid divide-by-zero on flat bars; the resulting NaN is filtered below.
    dx = 100.0 * (plus_di - minus_di).abs() / di_sum
    adx = dx.ewm(alpha=alpha, adjust=False).mean()
    val = adx.iloc[-1]
    # NaN-defensive: pd.isna handles both numpy NaN and pandas NA.
    if pd.isna(val):
        return None
    return float(val)


# ---------------------------------------------------------------------------
# Verdict tiering — verbatim move from analysts/{fundamentals,technicals,
# valuation}.py. Strict > / < boundaries at 0.6 / 0.2 (locked Phase 3
# 03-CONTEXT.md). Reusable across every analyst that aggregates [-1, +1]
# normalized signals into the canonical 5-state ladder.
# ---------------------------------------------------------------------------


def _total_to_verdict(normalized: float) -> Verdict:
    """Map a normalized aggregate in [-1, +1] to the 5-state Verdict ladder.

    Strict > / < boundaries (NOT >=) — `normalized=0.6` maps to `bullish`,
    NOT `strong_bullish`; `normalized=0.2` maps to `neutral`, NOT `bullish`.
    Forces "strong" verdicts to require GENUINELY strong consensus.
    """
    if normalized > 0.6:
        return "strong_bullish"
    if normalized > 0.2:
        return "bullish"
    if normalized < -0.6:
        return "strong_bearish"
    if normalized < -0.2:
        return "bearish"
    return "neutral"


# ---------------------------------------------------------------------------
# Phase 6 / Plan 06-01: series-form helpers (Wave 0 amendment)
#
# The Phase 6 frontend (Wave 3 deep-dive chart) needs MA / BB / RSI rendered
# as overlays across 180 days of OHLC history. The analyst verdicts
# (technicals, position_adjustment) consume only iloc[-1] of these series.
# These helpers expose the FULL series so storage can persist them — and
# they MUST produce byte-identical values at iloc[-1] vs the existing
# scalar computations so the chart never disagrees with the verdict math.
#
# Locked by tests/analysts/test_indicator_math.py:
#   * test_ma_series_byte_identical_to_single_point
#   * test_bb_series_byte_identical_to_single_point
#   * test_rsi_series_byte_identical_to_single_point
# Each test computes the series, takes iloc[-1], and asserts approx-equality
# (within 1e-9) to the corresponding existing scalar computation in
# analysts/technicals.py / analysts/position_adjustment.py.
# ---------------------------------------------------------------------------


def _ma_series(prices: pd.Series, window: int) -> pd.Series:
    """Simple moving average series (rolling mean over `window` bars).

    Byte-identical at iloc[-1] to `prices.rolling(window).mean().iloc[-1]`
    used in analysts/technicals._ma_alignment. First (window-1) entries are
    NaN (warmup); position window-1 onwards are real values.

    Returns a pd.Series of the same length as `prices`, with the same index.
    """
    return prices.rolling(window).mean()


def _bb_series(
    prices: pd.Series,
    window: int = 20,
    sigma: float = 2.0,
) -> tuple[pd.Series, pd.Series]:
    """Bollinger Bands (upper, lower) over `window` bars at `sigma` standard deviations.

    upper = SMA(window) + sigma * stdev(window)
    lower = SMA(window) - sigma * stdev(window)

    Byte-identical primitives at iloc[-1] vs analysts/position_adjustment._bollinger_position
    (which derives a SCALED POSITION value from the same SMA + stdev rolling pair).
    First (window-1) entries are NaN (warmup); position window-1 onwards are
    real values.

    Returns (upper, lower) as a tuple of pd.Series, each the same length and
    index as `prices`.
    """
    sma = prices.rolling(window).mean()
    std = prices.rolling(window).std()
    upper = sma + sigma * std
    lower = sma - sigma * std
    return upper, lower


def _rsi_series(prices: pd.Series, period: int = 14) -> pd.Series:
    """Wilder-smoothed RSI series over `period` bars.

    RSI = 100 - 100 / (1 + RS) where RS = gain_ewm / loss_ewm. Wilder's
    smoothing is implemented as `.ewm(alpha=1/N, adjust=False).mean()` —
    mathematically identical to the recursive recipe per StockCharts
    ChartSchool RSI walkthrough. Byte-identical at iloc[-1] to
    analysts/position_adjustment._rsi_14 which uses the same formulation.

    First `period` entries are NaN (delta needs 1 prior bar; ewm warmup
    produces values from index `period` onwards). Returns a pd.Series the
    same length and index as `prices`.

    Edge cases:
      * Where loss_ewm == 0 (all-gains warmup), RS → ∞ and RSI saturates
        to 100. pandas handles this via inf in the division; we leave it
        as inf in the series and let downstream JSON-serializers coerce
        to None or 100 as appropriate. _rsi_14 (scalar) clamps to 100.0
        explicitly — at iloc[-1], real-world data rarely hits l == 0 with
        14+ bars of history, so the series form returns the same finite
        value the scalar form does.
    """
    delta = prices.diff()
    gain = delta.clip(lower=0).ewm(alpha=1.0 / period, adjust=False).mean()
    loss = (-delta).clip(lower=0).ewm(alpha=1.0 / period, adjust=False).mean()
    rs = gain / loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi
