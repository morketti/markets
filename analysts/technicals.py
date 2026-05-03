"""Technicals analyst — pure-function deterministic scoring.

Adapted from virattt/ai-hedge-fund/src/agents/technicals.py
(https://github.com/virattt/ai-hedge-fund/blob/main/src/agents/technicals.py).

Modifications from the reference implementation:
  * SMA stacks (MA20 / MA50 / MA200) instead of EMA stacks (8/21/55) — per
    the 03-CONTEXT.md "Scoring Philosophy" decision. SMAs match the
    canonical stockcharts/finviz convention the user is more familiar with.
  * Min-bars warm-up guards added — virattt does NOT guard against short
    history, which would silently produce NaN at iloc[-1] and mark every
    cold-start ticker "neutral confidence 0" while quietly lying about
    data availability (see 03-RESEARCH.md Pitfall #1). Our guards explicitly
    flag the ticker as `data_unavailable=True` when there are fewer than 20
    bars (no indicator possible) and degrade gracefully when there are
    enough for some but not all indicators (e.g. < 200 omits MA200, < 27
    omits ADX entirely).
  * MA + momentum + ADX only — RSI / Bollinger Bands / Stochastic /
    Williams %R / MACD / Hurst belong to Phase 4 POSE-01..05 (the
    Position-Adjustment Radar). Phase 4 will revisit the ta-lib /
    pandas-ta-classic decision; for Phase 3 we hand-roll.
  * Pure pandas — no ta-lib, no pandas-ta, no pandas-ta-classic dependency.
    Pandas + numpy come transitively via yfinance (already in poetry.lock
    per 03-RESEARCH.md confirmation); DO NOT add pandas as a direct
    dependency in pyproject.toml.
  * Pure function `score(snapshot, config, *, computed_at=None) -> AgentSignal`
    replaces the reference's graph-node `ainvoke` — no I/O, no global
    state, no LangGraph dependency. Two calls with identical inputs
    produce identical signals (modulo computed_at when defaulted).
  * Empty-data UNIFORM RULE guard at the top: if any of
    `snapshot.data_unavailable`, `snapshot.prices is None`,
    `snapshot.prices.data_unavailable`, or `len(history) == 0` is true,
    return the canonical `data_unavailable=True` signal immediately.

Wilder smoothing reference: ADX uses pandas
`.ewm(alpha=1/14, adjust=False).mean()` which is mathematically identical
to Wilder's recursive formula
(https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/average-directional-index-adx).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import pandas as pd

from analysts.data.prices import OHLCBar
from analysts.data.snapshot import Snapshot
from analysts.schemas import TickerConfig
from analysts.signals import AgentSignal, Verdict

# ---------------------------------------------------------------------------
# Module-level constants — tunable by editing this file. Values from
# 03-CONTEXT.md "Threshold Defaults" + 03-RESEARCH.md ADX walkthrough.
# ---------------------------------------------------------------------------

# SMA periods (bars). MA200 needs 200 bars of history; absent below that.
MA_BARS: tuple[int, int, int] = (20, 50, 200)

# Momentum horizons: (label_months, lookback_bars, threshold). Threshold is
# the absolute % change above which the horizon contributes +1 (or below
# which it contributes -1). Weighted toward shorter windows by virtue of
# the threshold ladder: 5% over 1m is harder to clear than 15% over 6m.
MOMENTUM_HORIZONS: tuple[tuple[int, int, float], ...] = (
    (1, 21, 0.05),    # 1 month: 21 trading days, ±5%
    (3, 63, 0.10),    # 3 months: 63 trading days, ±10%
    (6, 126, 0.15),   # 6 months: 126 trading days, ±15%
)

# ADX thresholds. > ADX_TREND_ABOVE = trend regime; < ADX_RANGE_BELOW =
# range regime; in-between = ambiguous. The trend regime amplifies the
# directional vote when MA + momentum already point the same way.
ADX_PERIOD: int = 14
ADX_TREND_ABOVE: float = 25.0
ADX_RANGE_BELOW: float = 20.0

# ADX warm-up: Wilder smoothing needs 2*N - 1 bars (here 27) for the first
# valid value to settle. Below ADX_STABLE_BARS the value is mathematically
# valid but may swing — flagged in the evidence string.
ADX_MIN_BARS: int = 27
ADX_STABLE_BARS: int = 150

# Below this, no indicator is meaningful — return data_unavailable=True.
MIN_BARS_FOR_ANY_INDICATOR: int = 20

# Aggregation: max possible total = 1 (MA) + 3 (momentum) + 1 (ADX
# amplifier) = 5. Normalize the signed total to [-1, +1] by dividing.
_MAX_POSSIBLE_SCORE: int = 5


# ---------------------------------------------------------------------------
# DataFrame builder — list[OHLCBar] -> pandas DataFrame with high/low/close.
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
# Per-indicator helpers — each returns (score, evidence_or_None).
#   score in {-1, 0, +1}  — contribution to the aggregate
#   evidence in (str | None) — line for AgentSignal.evidence; None when the
#       indicator is not yet computable (e.g. < 50 bars for MA stack).
# ---------------------------------------------------------------------------


def _ma_alignment(df: pd.DataFrame) -> tuple[int, Optional[str]]:
    """Score MA stack alignment. Returns (score, evidence_or_None).

    < 50 bars: no MA stack possible (need ≥ 50 for MA50). Returns (0, None).
    50..199 bars: MA20 vs MA50 only; evidence notes "MA200 unavailable".
    ≥ 200 bars: full MA20 / MA50 / MA200 stack.
    """
    n = len(df)
    if n < 50:
        return 0, None
    ma20 = df["close"].rolling(20).mean().iloc[-1]
    ma50 = df["close"].rolling(50).mean().iloc[-1]
    if n < 200:
        if ma20 > ma50:
            return +1, (
                f"MA20 ({ma20:.1f}) > MA50 ({ma50:.1f}); "
                f"MA200 unavailable ({n} bars)"
            )
        if ma20 < ma50:
            return -1, (
                f"MA20 ({ma20:.1f}) < MA50 ({ma50:.1f}); "
                f"MA200 unavailable ({n} bars)"
            )
        return 0, f"MA20 ≈ MA50; MA200 unavailable ({n} bars)"
    ma200 = df["close"].rolling(200).mean().iloc[-1]
    if ma20 > ma50 > ma200:
        return +1, (
            f"MA20 ({ma20:.1f}) > MA50 ({ma50:.1f}) > MA200 "
            f"({ma200:.1f}) — bullish stack"
        )
    if ma20 < ma50 < ma200:
        return -1, (
            f"MA20 ({ma20:.1f}) < MA50 ({ma50:.1f}) < MA200 "
            f"({ma200:.1f}) — bearish stack"
        )
    return 0, (
        f"MA stack mixed (20={ma20:.1f}, 50={ma50:.1f}, 200={ma200:.1f})"
    )


def _momentum_one(
    df: pd.DataFrame,
    lookback_bars: int,
    threshold: float,
    label: str,
) -> tuple[int, Optional[str]]:
    """Score one momentum horizon. Returns (score, evidence_or_None).

    Returns (0, None) when fewer than `lookback_bars + 1` bars are available
    (cannot compute the percent change).
    """
    n = len(df)
    if n <= lookback_bars:
        return 0, None
    pct = (df["close"].iloc[-1] / df["close"].iloc[-1 - lookback_bars]) - 1.0
    if pct > threshold:
        return +1, (
            f"{label} momentum {pct * 100:+.1f}% "
            f"(above +{threshold * 100:.0f}%)"
        )
    if pct < -threshold:
        return -1, (
            f"{label} momentum {pct * 100:+.1f}% "
            f"(below -{threshold * 100:.0f}%)"
        )
    return 0, f"{label} momentum {pct * 100:+.1f}% (neutral band)"


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


def _adx_evidence(adx: Optional[float], n_bars: int) -> Optional[str]:
    """Format the ADX evidence string. Returns None when adx is None."""
    if adx is None:
        return None
    suffix = "" if n_bars >= ADX_STABLE_BARS else f" (ADX may be unstable, {n_bars} bars)"
    if adx > ADX_TREND_ABOVE:
        return f"ADX {adx:.0f} — trend regime{suffix}"
    if adx < ADX_RANGE_BELOW:
        return f"ADX {adx:.0f} — range regime{suffix}"
    return f"ADX {adx:.0f} — ambiguous regime{suffix}"


# ---------------------------------------------------------------------------
# Verdict tiering — same shape as analysts/fundamentals.py:_total_to_verdict.
# Strict > boundaries at 0.6 / 0.2 so a normalized value of exactly 0.6
# maps to "bullish" not "strong_bullish".
# ---------------------------------------------------------------------------


def _total_to_verdict(normalized: float) -> Verdict:
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
# Public scoring function
# ---------------------------------------------------------------------------


def score(
    snapshot: Snapshot,
    config: TickerConfig,
    *,
    computed_at: Optional[datetime] = None,
) -> AgentSignal:
    """Score technicals deterministically; pure function; never raises for missing data.

    Parameters
    ----------
    snapshot : Snapshot
        Per-ticker aggregate snapshot from the ingestion phase. The prices
        sub-field (snapshot.prices) is read for the OHLC history.
    config : TickerConfig
        Per-ticker configuration. Currently unused by this analyst (no
        per-ticker technical thresholds in v1) but accepted for parity with
        the AnalystId Literal contract — Phase 5 routine calls every analyst
        with the same (snapshot, config) signature.
    computed_at : datetime, optional
        UTC timestamp to stamp on the returned signal. Defaults to
        datetime.now(timezone.utc) — pin explicitly in tests for
        reproducible output.

    Returns
    -------
    AgentSignal
        Always non-None; analyst_id='technicals'. Never raises for missing
        data — empty / partial / short history produces the canonical
        data_unavailable=True signal per the UNIFORM RULE.
    """
    now = computed_at if computed_at is not None else datetime.now(timezone.utc)

    # UNIFORM RULE empty-data guard — four branches, all collapse to the
    # canonical data_unavailable signal. Order matters only for diagnostic
    # clarity (each branch emits a distinct evidence reason).
    if snapshot.data_unavailable:
        return AgentSignal(
            ticker=snapshot.ticker,
            analyst_id="technicals",
            computed_at=now,
            data_unavailable=True,
            evidence=["snapshot data_unavailable=True"],
        )
    if snapshot.prices is None:
        return AgentSignal(
            ticker=snapshot.ticker,
            analyst_id="technicals",
            computed_at=now,
            data_unavailable=True,
            evidence=["prices snapshot missing"],
        )
    if snapshot.prices.data_unavailable:
        return AgentSignal(
            ticker=snapshot.ticker,
            analyst_id="technicals",
            computed_at=now,
            data_unavailable=True,
            evidence=["prices.data_unavailable=True"],
        )
    if not snapshot.prices.history:
        return AgentSignal(
            ticker=snapshot.ticker,
            analyst_id="technicals",
            computed_at=now,
            data_unavailable=True,
            evidence=["prices history is empty"],
        )

    df = _build_df(snapshot.prices.history)
    n = len(df)

    # Min-bars guard — below this, no indicator is computable.
    if n < MIN_BARS_FOR_ANY_INDICATOR:
        return AgentSignal(
            ticker=snapshot.ticker,
            analyst_id="technicals",
            computed_at=now,
            data_unavailable=True,
            evidence=[
                f"history has {n} bars; need ≥{MIN_BARS_FOR_ANY_INDICATOR} for any indicator"
            ],
        )

    # Sub-scores: MA + 3 momentum horizons.
    sub: list[tuple[int, Optional[str]]] = []
    sub.append(_ma_alignment(df))
    for label_months, lookback, thresh in MOMENTUM_HORIZONS:
        sub.append(_momentum_one(df, lookback, thresh, f"{label_months}m"))

    # ADX is informational evidence (does not directly add to total) UNLESS
    # the trend regime confirms an existing directional vote — then it
    # amplifies by +1 / -1 once.
    adx_val = _adx_14(df)
    adx_str = _adx_evidence(adx_val, n)
    if adx_str is not None:
        sub.append((0, adx_str))
        if adx_val is not None and adx_val > ADX_TREND_ABOVE:
            stacks_total = sum(s for s, _ in sub[:4])  # MA + 3 momentum
            if stacks_total > 0:
                sub.append((+1, f"ADX-confirmed trend (ADX {adx_val:.0f} > {ADX_TREND_ABOVE:.0f})"))
            elif stacks_total < 0:
                sub.append((-1, f"ADX-confirmed trend (ADX {adx_val:.0f} > {ADX_TREND_ABOVE:.0f})"))

    total = sum(s for s, _ in sub)
    normalized = total / _MAX_POSSIBLE_SCORE
    # Defensive clamp — normalized must stay in [-1, +1] for the verdict
    # tiering helper. Internal math caps at 5/5 = 1.0 today; the clamp
    # survives any future indicator addition that could push beyond.
    if normalized > 1.0:
        normalized = 1.0
    elif normalized < -1.0:
        normalized = -1.0
    verdict = _total_to_verdict(normalized)
    confidence = min(100, int(round(abs(normalized) * 100)))
    # Cap evidence at 10 items at construction time. We generate ≤6 today,
    # well under, but the slice protects against future indicator additions.
    evidence = [s for _, s in sub if s is not None][:10]

    return AgentSignal(
        ticker=snapshot.ticker,
        analyst_id="technicals",
        computed_at=now,
        verdict=verdict,
        confidence=confidence,
        evidence=evidence,
    )
