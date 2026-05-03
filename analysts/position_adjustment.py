"""Position-Adjustment Radar — pure-function multi-indicator consensus scoring.

Aggregation pattern (multi-indicator weighted consensus + regime-conditional
weights) adapted from virattt/ai-hedge-fund/src/agents/risk_manager.py
(https://github.com/virattt/ai-hedge-fund/blob/main/src/agents/risk_manager.py).

Indicator math reuses the pandas hand-rolled pattern locked in
analysts/technicals.py (Phase 3 03-03) and shared via
analysts/_indicator_math.py (Wave 0 / Plan 04-01).

Modifications from the reference implementation:
  * Multi-indicator OVERBOUGHT/OVERSOLD consensus (POSE-01..05) instead of
    risk_manager's volatility-adjusted POSITION SIZING — same aggregation
    skeleton, different inputs and intent.
  * 6 indicators: RSI(14) / Bollinger position / z-score-vs-MA50 / Stochastic %K /
    Williams %R / MACD histogram (z-score normalized over 60 bars).
  * ADX(14) > 25 → mean-reversion indicators downweighted to 0.5x;
    trend-following indicators retain full weight; ambiguous zone (20-25)
    keeps all weights at 1.0 (no discontinuity at ADX=25).
  * 5-state PositionState ladder + 4-state ActionHint mapping derived from
    state — separate from AgentSignal's Verdict ladder.
  * confidence reflects INDICATOR AGREEMENT (n_agreeing / n_active), NOT
    magnitude — distinct from AgentSignal's confidence which mixes
    magnitude with directional consensus.
  * Pure function `score(snapshot, config, *, computed_at=None) -> PositionSignal`
    replaces virattt's graph-node ainvoke.
  * Empty-data UNIFORM RULE guard at the top — same shape as Phase 3 analysts.

Hand-rolled pandas math: NO ta-lib, NO pandas-ta, NO pandas-ta-classic
dependency. Pandas + numpy come transitively via yfinance (already in
poetry.lock per 03-RESEARCH.md). DO NOT add pandas as a direct dependency.

Wilder smoothing for RSI uses pandas .ewm(alpha=1/14, adjust=False).mean() —
mathematically identical to Wilder's recursive recipe, verified against
StockCharts ChartSchool RSI walkthrough
(https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/relative-strength-index-rsi).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Optional

import pandas as pd

from analysts._indicator_math import (
    ADX_RANGE_BELOW,
    ADX_TREND_ABOVE,
    _adx_14,
    _build_df,
)
from analysts.data.snapshot import Snapshot
from analysts.position_signal import ActionHint, PositionSignal, PositionState
from analysts.schemas import TickerConfig

# ---------------------------------------------------------------------------
# Module-level threshold constants (locked per 04-CONTEXT.md + 04-RESEARCH.md
# CORRECTION #1). Tunable by editing this file.
# ---------------------------------------------------------------------------

# RSI(14) — canonical Wilder thresholds (StockCharts canonical reference).
RSI_PERIOD: int = 14
RSI_MIN_BARS: int = 27                # = 2*N - 1, Wilder warm-up
RSI_OVERSOLD_BELOW: float = 30.0
RSI_OVERBOUGHT_ABOVE: float = 70.0

# Bollinger Bands position — units of stdev/2; ±1 = canonical band edge.
BB_BARS: int = 20
BB_OVERSOLD_BELOW: float = -1.0
BB_OVERBOUGHT_ABOVE: float = 1.0

# Z-score vs 50-day MA — ±1.5 corresponds to ~7% of bars.
ZSCORE_BARS: int = 50
ZSCORE_OVERSOLD_BELOW: float = -1.5
ZSCORE_OVERBOUGHT_ABOVE: float = 1.5

# Stochastic %K — canonical 14-bar lookback + 80/20 thresholds.
STOCH_BARS: int = 14
STOCH_OVERSOLD_BELOW: float = 20.0
STOCH_OVERBOUGHT_ABOVE: float = 80.0

# Williams %R — canonical 14-bar lookback + -80/-20 thresholds.
WILLIAMS_BARS: int = 14
WILLIAMS_OVERSOLD_BELOW: float = -80.0
WILLIAMS_OVERBOUGHT_ABOVE: float = -20.0

# MACD histogram — 12/26/9 with 60-bar z-score normalization (CORRECTION #1).
MACD_FAST_PERIOD: int = 12
MACD_SLOW_PERIOD: int = 26
MACD_SIGNAL_PERIOD: int = 9
MACD_HISTOGRAM_ZSCORE_BARS: int = 60
# Warm-up: slow EMA(26) + signal EMA(9) ≈ 34 bars + 60 z-score window = 94.
MACD_MIN_BARS: int = 94

# Trend-regime gate — when ADX(14) > ADX_TREND_ABOVE (25), mean-reversion
# indicators are downweighted to TREND_REGIME_DOWNWEIGHT (0.5).
TREND_REGIME_DOWNWEIGHT: float = 0.5

# Floor — below 14 bars, NO indicator is computable. Stochastic %K + Williams %R
# share the smallest warm-up.
MIN_BARS_FOR_ANY_INDICATOR: int = 14

# State ladder boundaries — strict > / < (NOT >=) per Phase 3 discipline.
STATE_EXTREME_OVERSOLD: float = -0.6
STATE_OVERSOLD: float = -0.2
STATE_OVERBOUGHT: float = 0.2
STATE_EXTREME_OVERBOUGHT: float = 0.6

# Confidence formula — abstain rule + n_active cap.
CONFIDENCE_ABSTAIN_THRESHOLD: float = 0.01

# Indicator key list (used in indicators dict + agreement counting).
INDICATOR_KEYS: tuple[str, ...] = (
    "rsi_14",
    "bb_position",
    "zscore_50",
    "stoch_k",
    "williams_r",
    "macd_histogram",
)


# ---------------------------------------------------------------------------
# 6 indicator helpers — each returns Optional[float] (raw indicator value or
# None when warm-up insufficient or flat-line / NaN result).
# ---------------------------------------------------------------------------


def _rsi_14(df: pd.DataFrame) -> Optional[float]:
    """Wilder RSI(14). Returns None below 27 bars or NaN result."""
    if len(df) < RSI_MIN_BARS:
        return None
    delta = df["close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1.0 / RSI_PERIOD, adjust=False).mean()
    loss = (-delta).clip(lower=0).ewm(alpha=1.0 / RSI_PERIOD, adjust=False).mean()
    g, l = gain.iloc[-1], loss.iloc[-1]
    if pd.isna(g) or pd.isna(l):
        return None
    if l == 0.0:
        return 100.0  # all gains, no losses → RSI saturates
    rs = g / l
    return float(100.0 - (100.0 / (1.0 + rs)))


def _bollinger_position(df: pd.DataFrame) -> Optional[float]:
    """(close - SMA20) / (2 * stdev20). Units: stdev/2; ±1 ≈ band edge."""
    if len(df) < BB_BARS:
        return None
    sma = df["close"].rolling(BB_BARS).mean().iloc[-1]
    std = df["close"].rolling(BB_BARS).std().iloc[-1]
    close = df["close"].iloc[-1]
    if pd.isna(sma) or pd.isna(std) or std == 0.0:
        return None
    return float((close - sma) / (2.0 * std))


def _zscore_vs_ma50(df: pd.DataFrame) -> Optional[float]:
    """(close - SMA50) / stdev50. Returns None below 50 bars or stdev=0."""
    if len(df) < ZSCORE_BARS:
        return None
    sma = df["close"].rolling(ZSCORE_BARS).mean().iloc[-1]
    std = df["close"].rolling(ZSCORE_BARS).std().iloc[-1]
    close = df["close"].iloc[-1]
    if pd.isna(sma) or pd.isna(std) or std == 0.0:
        return None
    return float((close - sma) / std)


def _stoch_k_14(df: pd.DataFrame) -> Optional[float]:
    """Stochastic %K(14): 100 * (close - low_14) / (high_14 - low_14). Range [0, 100]."""
    if len(df) < STOCH_BARS:
        return None
    low_14 = df["low"].rolling(STOCH_BARS).min().iloc[-1]
    high_14 = df["high"].rolling(STOCH_BARS).max().iloc[-1]
    close = df["close"].iloc[-1]
    if pd.isna(low_14) or pd.isna(high_14) or high_14 == low_14:
        return None
    return float(100.0 * (close - low_14) / (high_14 - low_14))


def _williams_r_14(df: pd.DataFrame) -> Optional[float]:
    """Williams %R(14): -100 * (high_14 - close) / (high_14 - low_14). Range [-100, 0]."""
    if len(df) < WILLIAMS_BARS:
        return None
    low_14 = df["low"].rolling(WILLIAMS_BARS).min().iloc[-1]
    high_14 = df["high"].rolling(WILLIAMS_BARS).max().iloc[-1]
    close = df["close"].iloc[-1]
    if pd.isna(low_14) or pd.isna(high_14) or high_14 == low_14:
        return None
    return float(-100.0 * (high_14 - close) / (high_14 - low_14))


def _macd_histogram_zscore(df: pd.DataFrame) -> Optional[float]:
    """MACD histogram z-scored over trailing MACD_HISTOGRAM_ZSCORE_BARS bars."""
    if len(df) < MACD_MIN_BARS:
        return None
    ema_fast = df["close"].ewm(span=MACD_FAST_PERIOD, adjust=False).mean()
    ema_slow = df["close"].ewm(span=MACD_SLOW_PERIOD, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=MACD_SIGNAL_PERIOD, adjust=False).mean()
    histogram = macd_line - signal_line
    trailing_mean = histogram.rolling(MACD_HISTOGRAM_ZSCORE_BARS).mean().iloc[-1]
    trailing_std = histogram.rolling(MACD_HISTOGRAM_ZSCORE_BARS).std().iloc[-1]
    h = histogram.iloc[-1]
    if (
        pd.isna(h)
        or pd.isna(trailing_mean)
        or pd.isna(trailing_std)
        or trailing_std == 0.0
    ):
        return None
    return float((h - trailing_mean) / trailing_std)


# ---------------------------------------------------------------------------
# 6 sub-signal mappers — linearize raw indicator value to [-1, +1].
# Sign convention: negative = oversold, positive = overbought.
# ---------------------------------------------------------------------------


def _rsi_to_subsignal(rsi: float) -> float:
    return max(-1.0, min(1.0, (rsi - 50.0) / 50.0))


def _bb_to_subsignal(bb: float) -> float:
    return max(-1.0, min(1.0, bb))


def _zscore_to_subsignal(z: float) -> float:
    return max(-1.0, min(1.0, z / 2.0))


def _stoch_to_subsignal(stoch_k: float) -> float:
    """Low %K = oversold = -1; high %K = overbought = +1."""
    return max(-1.0, min(1.0, (stoch_k - 50.0) / 50.0))


def _williams_to_subsignal(w_r: float) -> float:
    """Low %R (-100) = oversold = -1; high %R (0) = overbought = +1."""
    return max(-1.0, min(1.0, (w_r + 50.0) / 50.0))


def _macd_z_to_subsignal(macd_z: float) -> float:
    return max(-1.0, min(1.0, macd_z / 2.0))


# ---------------------------------------------------------------------------
# State ladder + action_hint mapping
# ---------------------------------------------------------------------------


def _consensus_to_state(score: float) -> PositionState:
    """Strict > / < boundaries — score=0.6 maps to 'overbought', not 'extreme_overbought'."""
    if score < STATE_EXTREME_OVERSOLD:   # < -0.6
        return "extreme_oversold"
    if score < STATE_OVERSOLD:           # < -0.2
        return "oversold"
    if score > STATE_EXTREME_OVERBOUGHT: # > +0.6
        return "extreme_overbought"
    if score > STATE_OVERBOUGHT:         # > +0.2
        return "overbought"
    return "fair"


_STATE_TO_HINT: dict[PositionState, ActionHint] = {
    "extreme_oversold": "consider_add",
    "oversold": "consider_add",
    "fair": "hold_position",
    "overbought": "consider_trim",
    "extreme_overbought": "consider_take_profits",
}


def _state_to_action_hint(state: PositionState) -> ActionHint:
    return _STATE_TO_HINT[state]


# ---------------------------------------------------------------------------
# Confidence formula — n_agreeing / n_active with abstain rule.
# ---------------------------------------------------------------------------


def _compute_confidence(
    sub_signals: list[tuple[float, float, str]],
    consensus_score: float,
) -> int:
    """Confidence ∈ [0, 100] from indicator agreement count.

    Edge cases:
      * n_active < 2 → 0 (single-indicator agreement is meaningless)
      * |consensus_score| < CONFIDENCE_ABSTAIN_THRESHOLD → 0 (no consensus)
      * Indicators with |sub_signal| < threshold count toward n_active but
        NOT n_agreeing (abstain rule).
    """
    n_active = len(sub_signals)
    if n_active < 2:
        return 0
    if abs(consensus_score) < CONFIDENCE_ABSTAIN_THRESHOLD:
        return 0
    consensus_positive = consensus_score > 0
    n_agreeing = sum(
        1
        for s, _, _ in sub_signals
        if abs(s) >= CONFIDENCE_ABSTAIN_THRESHOLD
        and (s > 0) == consensus_positive
    )
    return round(100 * n_agreeing / n_active)


# ---------------------------------------------------------------------------
# Evidence formatter — one canonical string per indicator key.
# ---------------------------------------------------------------------------


def _format_evidence(key: str, raw: float, sub_signal: float) -> str:
    if key == "rsi_14":
        if raw < RSI_OVERSOLD_BELOW:
            return f"RSI(14) {raw:.1f} — oversold (below {RSI_OVERSOLD_BELOW:.0f})"
        if raw > RSI_OVERBOUGHT_ABOVE:
            return f"RSI(14) {raw:.1f} — overbought (above {RSI_OVERBOUGHT_ABOVE:.0f})"
        return f"RSI(14) {raw:.1f} — neutral band"
    if key == "bb_position":
        if raw < BB_OVERSOLD_BELOW:
            return f"Bollinger position {raw:+.2f} — below lower band"
        if raw > BB_OVERBOUGHT_ABOVE:
            return f"Bollinger position {raw:+.2f} — above upper band"
        return f"Bollinger position {raw:+.2f} — within bands"
    if key == "zscore_50":
        if raw < ZSCORE_OVERSOLD_BELOW:
            return f"z-score vs MA50: {raw:+.2f} — extended below trend"
        if raw > ZSCORE_OVERBOUGHT_ABOVE:
            return f"z-score vs MA50: {raw:+.2f} — extended above trend"
        return f"z-score vs MA50: {raw:+.2f} — near trend"
    if key == "stoch_k":
        if raw < STOCH_OVERSOLD_BELOW:
            return (
                f"Stochastic %K {raw:.1f} — oversold "
                f"(below {STOCH_OVERSOLD_BELOW:.0f})"
            )
        if raw > STOCH_OVERBOUGHT_ABOVE:
            return (
                f"Stochastic %K {raw:.1f} — overbought "
                f"(above {STOCH_OVERBOUGHT_ABOVE:.0f})"
            )
        return f"Stochastic %K {raw:.1f} — neutral"
    if key == "williams_r":
        if raw < WILLIAMS_OVERSOLD_BELOW:
            return (
                f"Williams %R {raw:.0f} — oversold "
                f"(below {WILLIAMS_OVERSOLD_BELOW:.0f})"
            )
        if raw > WILLIAMS_OVERBOUGHT_ABOVE:
            return (
                f"Williams %R {raw:.0f} — overbought "
                f"(above {WILLIAMS_OVERBOUGHT_ABOVE:.0f})"
            )
        return f"Williams %R {raw:.0f} — neutral"
    if key == "macd_histogram":
        direction = "bullish" if sub_signal > 0 else "bearish"
        return f"MACD histogram z={raw:+.2f} — {direction} momentum"
    return f"{key} {raw}"  # defensive fallback (shouldn't hit)


# ---------------------------------------------------------------------------
# Helper: indicators dict with all None values (for empty-data path).
# ---------------------------------------------------------------------------


def _indicators_all_none() -> dict[str, float | None]:
    return {key: None for key in INDICATOR_KEYS} | {"adx_14": None}


# ---------------------------------------------------------------------------
# Public scoring function
# ---------------------------------------------------------------------------


def score(
    snapshot: Snapshot,
    config: TickerConfig,
    *,
    computed_at: Optional[datetime] = None,
) -> PositionSignal:
    """Compute Position-Adjustment Radar; pure function; never raises for missing data."""
    now = computed_at if computed_at is not None else datetime.now(timezone.utc)
    ticker = snapshot.ticker

    # UNIFORM RULE — empty-data 4-branch guard + 5th min-bars guard.
    if snapshot.data_unavailable:
        return PositionSignal(
            ticker=ticker,
            computed_at=now,
            data_unavailable=True,
            evidence=["snapshot data_unavailable=True"],
            indicators=_indicators_all_none(),
        )
    if snapshot.prices is None:
        return PositionSignal(
            ticker=ticker,
            computed_at=now,
            data_unavailable=True,
            evidence=["prices snapshot missing"],
            indicators=_indicators_all_none(),
        )
    if snapshot.prices.data_unavailable:
        return PositionSignal(
            ticker=ticker,
            computed_at=now,
            data_unavailable=True,
            evidence=["prices.data_unavailable=True"],
            indicators=_indicators_all_none(),
        )
    if not snapshot.prices.history:
        return PositionSignal(
            ticker=ticker,
            computed_at=now,
            data_unavailable=True,
            evidence=["prices history is empty"],
            indicators=_indicators_all_none(),
        )

    df = _build_df(snapshot.prices.history)
    n = len(df)
    if n < MIN_BARS_FOR_ANY_INDICATOR:
        return PositionSignal(
            ticker=ticker,
            computed_at=now,
            data_unavailable=True,
            evidence=[
                f"history has {n} bars; "
                f"need ≥{MIN_BARS_FOR_ANY_INDICATOR} for any indicator"
            ],
            indicators=_indicators_all_none(),
        )

    # ADX — trend-regime gate input (also recorded in indicators dict).
    adx_value = _adx_14(df)
    trend_regime = adx_value is not None and adx_value > ADX_TREND_ABOVE

    if trend_regime:
        weights = {
            "rsi_14": TREND_REGIME_DOWNWEIGHT,
            "bb_position": TREND_REGIME_DOWNWEIGHT,
            "stoch_k": TREND_REGIME_DOWNWEIGHT,
            "williams_r": TREND_REGIME_DOWNWEIGHT,
            "zscore_50": 1.0,
            "macd_histogram": 1.0,
        }
    else:
        weights = {key: 1.0 for key in INDICATOR_KEYS}

    # Per-indicator (helper, sub-mapper) lookup table.
    helper_table: list[
        tuple[str, Callable[[pd.DataFrame], Optional[float]], Callable[[float], float]]
    ] = [
        ("rsi_14", _rsi_14, _rsi_to_subsignal),
        ("bb_position", _bollinger_position, _bb_to_subsignal),
        ("zscore_50", _zscore_vs_ma50, _zscore_to_subsignal),
        ("stoch_k", _stoch_k_14, _stoch_to_subsignal),
        ("williams_r", _williams_r_14, _williams_to_subsignal),
        ("macd_histogram", _macd_histogram_zscore, _macd_z_to_subsignal),
    ]

    sub_signals: list[tuple[float, float, str]] = []
    indicators: dict[str, float | None] = {}

    for key, helper, sub_mapper in helper_table:
        raw = helper(df)
        indicators[key] = raw
        if raw is None:
            continue
        sub_signal = sub_mapper(raw)
        evidence_str = _format_evidence(key, raw, sub_signal)
        sub_signals.append((sub_signal, weights[key], evidence_str))

    indicators["adx_14"] = adx_value

    # Defensive — should be unreachable when n ≥ 14 (Stoch + Williams compute
    # at exactly 14 bars). If any helper unexpectedly returns None for all
    # indicators, emit data_unavailable with explanatory evidence.
    if not sub_signals:
        return PositionSignal(
            ticker=ticker,
            computed_at=now,
            data_unavailable=True,
            evidence=[f"history has {n} bars but no indicator was computable"],
            indicators=indicators,
        )

    total_w = sum(w for _, w, _ in sub_signals)
    consensus_score = sum(s * w for s, w, _ in sub_signals) / total_w
    # Defensive clamp — float arithmetic can drift outside [-1, +1].
    consensus_score = max(-1.0, min(1.0, consensus_score))

    state = _consensus_to_state(consensus_score)
    action_hint = _state_to_action_hint(state)
    confidence = _compute_confidence(sub_signals, consensus_score)

    # Evidence assembly: per-indicator strings + ADX regime + consensus summary.
    evidence: list[str] = [e for _, _, e in sub_signals]
    if adx_value is not None:
        if trend_regime:
            evidence.append(
                f"ADX {adx_value:.0f} — trend regime; mean-reversion indicators "
                f"downweighted by {int((1 - TREND_REGIME_DOWNWEIGHT) * 100)}%"
            )
        elif adx_value < ADX_RANGE_BELOW:
            evidence.append(f"ADX {adx_value:.0f} — range regime")
        else:
            evidence.append(f"ADX {adx_value:.0f} — ambiguous regime")
    n_active = len(sub_signals)
    n_agreeing = round(confidence * n_active / 100) if confidence > 0 else 0
    summary_suffix = "; ADX trend regime active" if trend_regime else ""
    evidence.append(
        f"{n_agreeing} of {n_active} indicators agree "
        f"({state.replace('_', ' ')} consensus){summary_suffix}"
    )
    evidence = evidence[:10]  # cap (we generate ≤ 8)

    return PositionSignal(
        ticker=ticker,
        computed_at=now,
        state=state,
        consensus_score=consensus_score,
        confidence=confidence,
        action_hint=action_hint,
        indicators=indicators,
        evidence=evidence,
        trend_regime=trend_regime,
    )
