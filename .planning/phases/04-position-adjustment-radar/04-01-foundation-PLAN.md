---
phase: 04-position-adjustment-radar
plan: 01
type: tdd
wave: 1
depends_on: []
files_modified:
  - analysts/_indicator_math.py
  - analysts/fundamentals.py
  - analysts/technicals.py
  - analysts/valuation.py
  - tests/analysts/conftest.py
  - tests/analysts/test_indicator_math.py
  - tests/analysts/test_synthetic_fixtures.py
autonomous: true
requirements: [POSE-01, POSE-03]
provides:
  - "analysts/_indicator_math.py — shared `_build_df`, `_adx_14`, `_total_to_verdict` helpers (verbatim extraction from analysts/technicals.py + analysts/fundamentals.py + analysts/valuation.py; zero behavior change)"
  - "Module-level constants ADX_PERIOD=14, ADX_TREND_ABOVE=25.0, ADX_RANGE_BELOW=20.0, ADX_MIN_BARS=27, ADX_STABLE_BARS=150 living in analysts/_indicator_math.py — re-imported by analysts/technicals.py for backwards compatibility"
  - "analysts/fundamentals.py + analysts/technicals.py + analysts/valuation.py refactored to `from analysts._indicator_math import _total_to_verdict` (and analysts/technicals.py also imports `_build_df`, `_adx_14`) — single source of truth, no drift between Phase 3 implementations"
  - "tests/analysts/conftest.py extended with synthetic_oversold_history, synthetic_overbought_history, synthetic_mean_reverting_history module-level builders (deterministic, no random sources, same `(i % 5) - 2` noise pattern as Phase 3 Wave 1 builders)"
  - "tests/analysts/test_indicator_math.py — ~6 tests covering the 3 extracted helpers (smoke + ADX warm-up boundary at 27 bars + verdict tiering strict-> boundaries at ±0.6/±0.2)"
  - "tests/analysts/test_synthetic_fixtures.py — ~3 tests verifying the new fixtures produce expected qualitative shapes (oversold history's last close < first close; overbought history's last close > first close; mean-reverting history oscillates around start)"
  - "Phase 3 regression invariant: all 25 existing tests in tests/analysts/test_technicals.py + 18 in test_fundamentals.py + 12 in test_valuation.py + 2 in test_invariants.py PASS unchanged after the refactor"
tags: [phase-4, foundation, refactor, dry-trigger, fixtures, tdd, wave-0, no-behavior-change]

must_haves:
  truths:
    - "analysts/_indicator_math.py exists and exports `_build_df`, `_adx_14`, `_total_to_verdict` plus the ADX_* / MIN_BARS_FOR_ANY_INDICATOR-related constants — module is importable without circular-import errors from any analyst module"
    - "analysts/fundamentals.py replaces its inline `_total_to_verdict` (lines 179-188) with `from analysts._indicator_math import _total_to_verdict` — no other behavior change"
    - "analysts/technicals.py replaces its inline `_build_df` (lines 96-114), `_adx_14` (lines 193-249), and `_total_to_verdict` (lines 271-280) with `from analysts._indicator_math import _build_df, _adx_14, _total_to_verdict` — no other behavior change"
    - "analysts/valuation.py replaces its inline `_total_to_verdict` (line 94) with `from analysts._indicator_math import _total_to_verdict` — no other behavior change"
    - "All 25 existing tests in tests/analysts/test_technicals.py PASS unchanged (regression invariant)"
    - "All 18 existing tests in tests/analysts/test_fundamentals.py PASS unchanged"
    - "All 12 existing tests in tests/analysts/test_valuation.py PASS unchanged"
    - "Both cross-cutting tests in tests/analysts/test_invariants.py PASS (still GREEN after refactor — same contract)"
    - "synthetic_oversold_history(252) produces a last-bar close < 50% of start (sustained downtrend + final-shock-drop pattern); RSI(14) computed against this fixture lands < 30 — explicit oversold regime"
    - "synthetic_overbought_history(252) produces a last-bar close > 200% of start; RSI(14) computed against this fixture lands > 70 — explicit overbought regime"
    - "synthetic_mean_reverting_history(252, period_bars=50, amplitude=0.10) oscillates symmetrically around start; ADX(14) computed against this fixture lands < 20 (range regime); BB position can swing to ±1.5 at peaks/troughs"
    - "All 3 new synthetic fixtures are deterministic — two calls with identical kwargs produce byte-identical OHLCBar lists (no random sources)"
    - "Coverage on analysts/_indicator_math.py ≥ 90% line / ≥ 85% branch (achievable via the 6 dedicated tests + transitive coverage from existing Phase 3 test suites)"
  artifacts:
    - path: "analysts/_indicator_math.py"
      provides: "shared `_build_df`, `_adx_14`, `_total_to_verdict` + ADX-related module-level constants. ~80-100 LOC including docstrings."
      min_lines: 80
    - path: "tests/analysts/test_indicator_math.py"
      provides: "≥6 tests covering the 3 extracted helpers (build_df sorts unsorted history + dropna; adx_14 returns None < 27 bars + valid float ≥ 27 bars; total_to_verdict strict-> boundaries at ±0.6/±0.2 with extreme_oversold/oversold/neutral/bullish/strong_bullish all hit by parametrized cases)"
      min_lines: 60
    - path: "tests/analysts/test_synthetic_fixtures.py"
      provides: "≥3 round-trip tests verifying synthetic_oversold_history (last close < 0.5x start), synthetic_overbought_history (last close > 2x start), synthetic_mean_reverting_history (oscillates around start, len matches n)"
      min_lines: 30
    - path: "tests/analysts/conftest.py"
      provides: "appends synthetic_oversold_history, synthetic_overbought_history, synthetic_mean_reverting_history module-level builders to the existing file (preserves all existing fixtures + builders)"
      min_lines: 250
  key_links:
    - from: "analysts/_indicator_math.py"
      to: "analysts/data/prices.OHLCBar (input contract for _build_df)"
      via: "type hint + iteration; no new dependency surface"
      pattern: "from analysts\\.data\\.prices import OHLCBar"
    - from: "analysts/_indicator_math.py"
      to: "analysts/signals.Verdict (return type of _total_to_verdict)"
      via: "type import; preserves the Phase 3 Verdict Literal contract"
      pattern: "from analysts\\.signals import Verdict"
    - from: "analysts/fundamentals.py + analysts/technicals.py + analysts/valuation.py"
      to: "analysts._indicator_math (single source of truth for the 3 helpers)"
      via: "import-only refactor — line-equivalent move, no logic change"
      pattern: "from analysts\\._indicator_math import"
    - from: "tests/analysts/conftest.py"
      to: "analysts.data.prices.OHLCBar (builders construct OHLCBar lists)"
      via: "module-level builders extend existing pattern (synthetic_uptrend/downtrend/sideways)"
      pattern: "synthetic_(oversold|overbought|mean_reverting)_history"
    - from: "tests/analysts/test_indicator_math.py"
      to: "analysts._indicator_math (the unit under test)"
      via: "imports each extracted helper; parametrized boundary tests"
      pattern: "from analysts\\._indicator_math import"
---

<objective>
Wave 0 / Foundation: extract three helpers from the Phase 3 analyst modules into a new shared `analysts/_indicator_math.py` module, append three synthetic-history builders to the existing `tests/analysts/conftest.py`, and ship dedicated test coverage for both. ZERO behavior change in Phase 3 — every existing test must stay GREEN. This plan unblocks Phase 4 Wave 1 (PositionSignal schema) and Wave 2 (position_adjustment.py analyst) which depend on the shared `_build_df` + `_adx_14` helpers and the new synthetic fixtures for explicit overbought/oversold regression testing.

Purpose: the DRY trigger has fired four times. `_total_to_verdict` is currently copied 3x verbatim across `analysts/fundamentals.py:179-188`, `analysts/technicals.py:271-280`, and `analysts/valuation.py:94` — Phase 4 would be the 4th copy. `_build_df` is in `analysts/technicals.py:96-114` only, but Phase 4's `position_adjustment.py` needs the SAME pandas DataFrame builder (sort by date, dropna on close, high/low/close columns). `_adx_14` is in `analysts/technicals.py:193-249`; Phase 4 reads ADX as the trend-regime gate input. Three options: (a) Phase 4 imports `from analysts.technicals import _adx_14` (cross-module private import — bad smell), (b) Phase 4 duplicates ~60 LOC of Wilder-smoothing pandas math (worse — drift risk), (c) extract to a shared module (right). Per 04-RESEARCH.md Pattern #2, option (c) is the locked path.

The synthetic-fixture work also lands here so Wave 2's regression tests have explicit overbought/oversold history shapes to assert against. The three new builders are appended to the existing `tests/analysts/conftest.py` — not a new file — to mirror the Phase 3 conftest pattern (single home for shared synthetic builders; Phase 5/6/7 inherit them for free).

The refactor is mechanical and low-risk: all moved code is line-equivalent; the existing 57+ Phase 3 tests guard against any behavior drift; the import-replacement diff is small and surgical.

Output: analysts/_indicator_math.py (~80-100 LOC including provenance docstring + 3 helpers + 5 ADX-related constants); analysts/{fundamentals, technicals, valuation}.py with the 3 inline helper definitions replaced by imports (no other lines mutated); tests/analysts/conftest.py extended with 3 new builders (~80 LOC appended; all existing fixtures preserved); tests/analysts/test_indicator_math.py (~60-80 LOC, ≥6 tests, all GREEN); tests/analysts/test_synthetic_fixtures.py (~40-50 LOC, ≥3 tests, all GREEN); full Phase 3 regression suite GREEN.
</objective>

<execution_context>
@C:/Users/Mohan/.claude/workflows/execute-plan.md
@C:/Users/Mohan/.claude/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/04-position-adjustment-radar/04-CONTEXT.md
@.planning/phases/04-position-adjustment-radar/04-RESEARCH.md
@.planning/phases/03-analytical-agents-deterministic-scoring/03-03-SUMMARY.md
@.planning/phases/03-analytical-agents-deterministic-scoring/03-05-SUMMARY.md

# Existing patterns to mirror — these are the ground truth for the extraction
@analysts/fundamentals.py
@analysts/technicals.py
@analysts/valuation.py
@analysts/signals.py
@analysts/data/prices.py
@tests/analysts/conftest.py
@tests/analysts/test_technicals.py
@tests/analysts/test_invariants.py

<interfaces>
<!-- Existing _total_to_verdict — 3 verbatim copies in Phase 3.
     analysts/fundamentals.py:179-188 -->

```python
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
```

<!-- analysts/technicals.py:271-280 — IDENTICAL to fundamentals copy.
     analysts/valuation.py:94      — IDENTICAL.
     Strict > / < boundaries at 0.6 / 0.2 (lock per 03-RESEARCH.md). -->

<!-- Existing _build_df — analysts/technicals.py:96-114, ONE copy. -->

```python
def _build_df(history: list[OHLCBar]) -> pd.DataFrame:
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
```

<!-- Existing _adx_14 — analysts/technicals.py:193-249, ~60 LOC of Wilder math.
     Returns Optional[float]; None below 27 bars OR on NaN at iloc[-1]. -->

<!-- Existing module-level constants in analysts/technicals.py:73-84 that
     belong with _adx_14 (move with it):
       ADX_PERIOD: int = 14
       ADX_TREND_ABOVE: float = 25.0
       ADX_RANGE_BELOW: float = 20.0
       ADX_MIN_BARS: int = 27
       ADX_STABLE_BARS: int = 150
     analysts/technicals.py keeps a re-export shim:
       from analysts._indicator_math import (
           ADX_PERIOD, ADX_TREND_ABOVE, ADX_RANGE_BELOW,
           ADX_MIN_BARS, ADX_STABLE_BARS,
       )
     so external callers (none today, but defensively) and tests that
     read these names continue to work. -->

<!-- Existing synthetic builders to mirror — tests/analysts/conftest.py:83-135 -->

```python
def synthetic_uptrend_history(n=252, start=100.0, daily_drift=0.005) -> list[OHLCBar]: ...
def synthetic_downtrend_history(n=252, start=200.0, daily_drift=-0.005) -> list[OHLCBar]: ...
def synthetic_sideways_history(n=252, start=150.0, amplitude=0.02) -> list[OHLCBar]: ...
```

<!-- Internal helper used by all three: _build_ohlc_bars — clamps c<=0 to 0.01,
     o = c*0.998, h = c*1.01, low = c*0.99, v = 1_000_000 + i*100. -->

<!-- NEW conftest.py builders this plan APPENDS — same _build_ohlc_bars
     internal pattern, deterministic noise via close_fn closure: -->

```python
def synthetic_oversold_history(
    n: int = 252,
    start: float = 200.0,
    daily_drift: float = -0.005,
    final_drop_bars: int = 5,
    final_drop_pct: float = 0.05,
) -> list[OHLCBar]:
    """n daily bars in a downtrend ending with a sharp drop — explicit oversold regime.

    Trend portion (first n - final_drop_bars bars): synthetic_downtrend_history shape
    (geometric drift + small bounded noise). Final final_drop_bars (default 5) bars
    drop an additional final_drop_pct (default 5%) cumulatively to push RSI < 30,
    BB position < -1, Stoch %K < 20, Williams %R < -80.
    """
    drop_start_index = n - final_drop_bars

    def _close(i: int, prev: float, _start: float) -> float:
        if i < drop_start_index:
            return prev * (1.0 + daily_drift) + 0.001 * ((i % 5) - 2)
        return prev * (1.0 - final_drop_pct) + 0.001 * ((i % 5) - 2)

    return _build_ohlc_bars(n, start, close_fn=_close)


def synthetic_overbought_history(
    n: int = 252,
    start: float = 100.0,
    daily_drift: float = 0.005,
    final_pop_bars: int = 5,
    final_pop_pct: float = 0.05,
) -> list[OHLCBar]:
    """Mirror of synthetic_oversold_history. n daily bars in an uptrend ending with a
    sharp pop. Produces RSI > 70, BB position > +1, Stoch %K > 80, Williams %R > -20.
    """
    pop_start_index = n - final_pop_bars

    def _close(i: int, prev: float, _start: float) -> float:
        if i < pop_start_index:
            return prev * (1.0 + daily_drift) + 0.001 * ((i % 5) - 2)
        return prev * (1.0 + final_pop_pct) + 0.001 * ((i % 5) - 2)

    return _build_ohlc_bars(n, start, close_fn=_close)


def synthetic_mean_reverting_history(
    n: int = 252,
    start: float = 150.0,
    amplitude: float = 0.10,
    period_bars: int = 50,
) -> list[OHLCBar]:
    """n daily bars oscillating around start with controlled period and amplitude.

    close[i] = start * (1 + amplitude * sin(2π i / period_bars)).

    Default amplitude=0.10 (vs sideways=0.02) is wide enough to push BB position
    to ±1.5 at peaks/troughs but mean-reverting enough that ADX(14) < 20 (range
    regime). Useful for testing "mean-reversion indicators score correctly when
    ADX confirms range" path.
    """
    def _close(i: int, _prev: float, s: float) -> float:
        return s * (1.0 + amplitude * math.sin(2.0 * math.pi * i / period_bars))

    return _build_ohlc_bars(n, start, close_fn=_close)
```
</interfaces>

<implementation_sketch>
<!-- The new analysts/_indicator_math.py file — verbatim move of three helpers
     plus their colocated constants. Provenance docstring documents the
     extraction lineage. -->

```python
"""Shared indicator math used across the analyst suite.

Extracted from analysts/technicals.py (Phase 3 / 03-03) and
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
# ADX module constants — moved from analysts/technicals.py:73-84
# ---------------------------------------------------------------------------
ADX_PERIOD: int = 14
ADX_TREND_ABOVE: float = 25.0
ADX_RANGE_BELOW: float = 20.0
ADX_MIN_BARS: int = 27        # = 2*N - 1, Wilder warm-up
ADX_STABLE_BARS: int = 150    # below this, evidence flags possible instability


# ---------------------------------------------------------------------------
# DataFrame builder — verbatim move from analysts/technicals.py:96-114
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
# Wilder ADX(14) — verbatim move from analysts/technicals.py:193-249
# ---------------------------------------------------------------------------
def _adx_14(df: pd.DataFrame) -> Optional[float]:
    """Wilder ADX(14). Returns None below ADX_MIN_BARS (27) or NaN result."""
    if len(df) < ADX_MIN_BARS:
        return None
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
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
    dx = 100.0 * (plus_di - minus_di).abs() / di_sum
    adx = dx.ewm(alpha=alpha, adjust=False).mean()
    val = adx.iloc[-1]
    if pd.isna(val):
        return None
    return float(val)


# ---------------------------------------------------------------------------
# Verdict tiering — verbatim move from analysts/{fundamentals,technicals,valuation}.py.
# Strict > / < boundaries at 0.6 / 0.2 (locked Phase 3 03-CONTEXT.md).
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
```

<!-- The 3 caller refactors are import-only changes:

analysts/fundamentals.py:
  REMOVE lines 179-188 (the inline _total_to_verdict definition)
  ADD:    from analysts._indicator_math import _total_to_verdict
  (adjacent to existing imports near top of file)

analysts/technicals.py:
  REMOVE lines 73-84 (ADX_* + ADX_MIN_BARS + ADX_STABLE_BARS constants)
  REMOVE lines 96-114 (_build_df definition)
  REMOVE lines 193-249 (_adx_14 definition)
  REMOVE lines 271-280 (_total_to_verdict definition)
  ADD:    from analysts._indicator_math import (
              ADX_PERIOD, ADX_TREND_ABOVE, ADX_RANGE_BELOW,
              ADX_MIN_BARS, ADX_STABLE_BARS,
              _build_df, _adx_14, _total_to_verdict,
          )
  (Note: _adx_evidence stays in technicals.py — it's tightly coupled to
   the technicals analyst's evidence-string formatting and only used by
   technicals.score(). DON'T move _adx_evidence.)

analysts/valuation.py:
  REMOVE line 94 area (the inline _total_to_verdict definition)
  ADD:    from analysts._indicator_math import _total_to_verdict
-->

<!-- tests/analysts/conftest.py — APPEND the three new builders after
     synthetic_sideways_history (line 135). Each builder reuses the existing
     _build_ohlc_bars internal helper (lines 45-80). No new imports needed.

     DETERMINISM ASSERTION (in module docstring update or as inline comment):
     "synthetic_oversold_history / synthetic_overbought_history /
      synthetic_mean_reverting_history use the SAME deterministic noise pattern
      as the Phase 3 builders: 0.001 * ((i % 5) - 2) HLC variance, 1_000_000 + i*100
      volume drift. NO random sources. Two calls with identical kwargs produce
      byte-identical OHLCBar lists." -->

<!-- tests/analysts/test_indicator_math.py (NEW) — ≥6 tests:

  1. test_build_df_empty_history_returns_empty_df
  2. test_build_df_sorts_unsorted_input — feed dates [d3, d1, d2]; assert .index is monotonic
  3. test_adx_14_returns_none_below_min_bars — feed synthetic_uptrend_history(20); assert _adx_14(df) is None
  4. test_adx_14_returns_float_at_min_bars_and_above — feed synthetic_uptrend_history(27); assert isinstance(_adx_14(df), float)
  5. test_adx_14_uptrend_high_value — feed synthetic_uptrend_history(252); assert _adx_14(df) > 25 (trend regime)
  6. test_total_to_verdict_strict_boundaries — parametrize:
       (0.7, "strong_bullish"), (0.6, "bullish"), (0.5, "bullish"),
       (0.21, "bullish"), (0.2, "neutral"), (0.0, "neutral"),
       (-0.2, "neutral"), (-0.21, "bearish"), (-0.6, "bearish"),
       (-0.7, "strong_bearish")
     Verifies the strict > / < boundaries (NOT >=).
-->

<!-- tests/analysts/test_synthetic_fixtures.py (NEW) — ≥3 tests:

  1. test_synthetic_oversold_history_qualitative —
       bars = synthetic_oversold_history(252)
       assert len(bars) == 252
       assert bars[-1].close < bars[0].close * 0.5   # sustained downtrend + drop
       assert all(b.high > b.close > b.low > 0 for b in bars)
       assert all(b.high > 0 and b.volume > 0 for b in bars)

  2. test_synthetic_overbought_history_qualitative — mirror:
       assert bars[-1].close > bars[0].close * 2.0
       (monotonic up-with-final-pop)

  3. test_synthetic_mean_reverting_history_oscillates —
       bars = synthetic_mean_reverting_history(252, period_bars=50, amplitude=0.10)
       closes = [b.close for b in bars]
       assert len(closes) == 252
       # oscillates symmetrically around start (=150.0)
       assert abs(sum(closes)/len(closes) - 150.0) < 5.0   # mean ≈ start
       assert max(closes) > 150.0 * 1.05                    # peak above
       assert min(closes) < 150.0 * 0.95                    # trough below

  4. (optional) test_synthetic_fixtures_deterministic — call each builder twice
       with identical args; assert byte-equality of the OHLCBar lists.
-->
</implementation_sketch>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Extract `_build_df` + `_adx_14` + `_total_to_verdict` to analysts/_indicator_math.py (RED → GREEN)</name>
  <files>analysts/_indicator_math.py, analysts/fundamentals.py, analysts/technicals.py, analysts/valuation.py, tests/analysts/test_indicator_math.py</files>
  <behavior>
    Mechanical extraction. The three helpers move verbatim into a new shared module; the three analyst modules import them; the existing 57+ Phase 3 tests serve as the behavioral regression guard. Six dedicated tests in `tests/analysts/test_indicator_math.py` lock the public surface of the new module.

    The constants `ADX_PERIOD`, `ADX_TREND_ABOVE`, `ADX_RANGE_BELOW`, `ADX_MIN_BARS`, `ADX_STABLE_BARS` move WITH `_adx_14` because they are tightly coupled (the function literally references `ADX_MIN_BARS` and `ADX_PERIOD`). `analysts/technicals.py` keeps a re-export line so any code that reads (e.g.) `technicals.ADX_TREND_ABOVE` continues to work.

    `_adx_evidence` (analysts/technicals.py:252-261) does NOT move. It's tightly coupled to technicals' evidence-string formatting and is only called from `technicals.score()`. Phase 4's `position_adjustment.py` will write its own ADX evidence formatter (different wording: "trend regime; mean-reversion indicators downweighted" vs technicals' "trend regime").

    Tests in `tests/analysts/test_indicator_math.py` (≥6):

    SMOKE / SHAPE:
    - test_build_df_empty_history_returns_empty_df: `_build_df([])` returns a DataFrame with 3 columns ["high", "low", "close"] and len==0. No crash.
    - test_build_df_sorts_unsorted_input: feed a 5-bar OHLCBar list with dates [d3, d1, d4, d2, d5]; assert resulting df.index is monotonically increasing AND all 5 bars present in the original order's close values, just re-indexed.

    ADX WARM-UP:
    - test_adx_14_returns_none_below_min_bars: build df from synthetic_uptrend_history(20); assert `_adx_14(df) is None`. Boundary is 27.
    - test_adx_14_returns_none_at_26_bars: synthetic_uptrend_history(26); `_adx_14(df) is None`. (Boundary discipline: < 27 is None.)
    - test_adx_14_returns_float_at_27_bars_uptrend: synthetic_uptrend_history(27); `isinstance(_adx_14(df), float)`. NOTE: at exactly 27 bars the value may be small (warm-up not stable) but it MUST be a float, not None.
    - test_adx_14_uptrend_252bars_trend_regime: synthetic_uptrend_history(252); assert `_adx_14(df) > 25.0` (sustained uptrend → ADX firmly in trend regime).

    VERDICT TIERING (strict > / < boundaries):
    - test_total_to_verdict_strict_boundaries: parametrize over 10 (input, expected) tuples. Critical boundary cases:
        - 0.6 → "bullish" (NOT "strong_bullish") — strict > 0.6 fails
        - 0.21 → "bullish"
        - 0.2 → "neutral" — strict > 0.2 fails
        - -0.2 → "neutral"
        - -0.21 → "bearish"
        - -0.6 → "bearish" (NOT "strong_bearish")
        Plus 0.7 → "strong_bullish", -0.7 → "strong_bearish", 0.0 → "neutral".

    All 6+ tests pass against the new module. Phase 3 regression tests (57+) also pass after the import refactor (no behavior change).
  </behavior>
  <action>
    RED:
    1. Write `tests/analysts/test_indicator_math.py` with the ≥6 tests as specified. Imports:
       ```python
       import pytest
       import pandas as pd
       from analysts._indicator_math import _build_df, _adx_14, _total_to_verdict
       from tests.analysts.conftest import synthetic_uptrend_history
       ```
       Use `pytest.mark.parametrize` for `test_total_to_verdict_strict_boundaries`. For `test_build_df_sorts_unsorted_input`, build a small list of 5 OHLCBars with explicit out-of-order dates; the test verifies sort_index() works.
    2. Run `poetry run pytest tests/analysts/test_indicator_math.py -x -q` → ImportError on `analysts._indicator_math` (module does not exist).
    3. Commit (RED): `test(04-01): add failing tests for shared analysts._indicator_math helpers (build_df / adx_14 / total_to_verdict)`

    GREEN:
    4. Create `analysts/_indicator_math.py` per the implementation_sketch:
       - Provenance docstring (~25 lines) explaining the extraction lineage.
       - Imports: `from __future__ import annotations`; `from typing import Optional`; `import pandas as pd`; `from analysts.data.prices import OHLCBar`; `from analysts.signals import Verdict`.
       - 5 module-level constants: `ADX_PERIOD`, `ADX_TREND_ABOVE`, `ADX_RANGE_BELOW`, `ADX_MIN_BARS`, `ADX_STABLE_BARS`.
       - `_build_df(history)` — verbatim copy from `analysts/technicals.py:96-114`.
       - `_adx_14(df)` — verbatim copy from `analysts/technicals.py:193-249`.
       - `_total_to_verdict(normalized)` — verbatim copy from any of the 3 callers (they're identical).
    5. Refactor `analysts/fundamentals.py`:
       - Add: `from analysts._indicator_math import _total_to_verdict` (alongside existing imports near top of file).
       - Remove the inline `def _total_to_verdict(...)` block (lines 179-188 — verify exact line numbers in your editor; the function and its docstring/comment).
       - No other lines mutated.
    6. Refactor `analysts/technicals.py`:
       - Add: `from analysts._indicator_math import (ADX_PERIOD, ADX_TREND_ABOVE, ADX_RANGE_BELOW, ADX_MIN_BARS, ADX_STABLE_BARS, _build_df, _adx_14, _total_to_verdict)` (split across multiple lines per project style).
       - Remove the 5 module-level ADX constants (lines 73-84 — but keep `MA_BARS`, `MOMENTUM_HORIZONS`, `MIN_BARS_FOR_ANY_INDICATOR`, `_MAX_POSSIBLE_SCORE` which are technicals-specific).
       - Remove `_build_df` definition (lines 96-114).
       - Remove `_adx_14` definition (lines 193-249).
       - Remove `_total_to_verdict` definition (lines 271-280 + comment block immediately above at 264-270).
       - DO NOT remove `_adx_evidence` (lines 252-261) — it stays.
       - DO NOT remove the section header comments (`# DataFrame builder ...`, `# Verdict tiering ...`) UNLESS they become orphaned. Keep file readable.
       - No other lines mutated.
    7. Refactor `analysts/valuation.py`:
       - Add: `from analysts._indicator_math import _total_to_verdict` (alongside existing imports near top of file).
       - Remove the inline `def _total_to_verdict(...)` block at line 94.
       - No other lines mutated.
    8. Run `poetry run pytest tests/analysts/test_indicator_math.py -v` → all 6+ tests green.
    9. Coverage: `poetry run pytest --cov=analysts._indicator_math --cov-branch tests/analysts/test_indicator_math.py` → ≥90% line / ≥85% branch.
    10. Phase 3 regression: `poetry run pytest tests/analysts/ -v` → all existing 57+ tests still GREEN. Specifically:
        - `tests/analysts/test_technicals.py` — all 25 tests pass (regression invariant).
        - `tests/analysts/test_fundamentals.py` — all 18 tests pass.
        - `tests/analysts/test_valuation.py` — all 12 tests pass.
        - `tests/analysts/test_invariants.py` — both cross-cutting tests pass (still GREEN; the contract is unchanged).
        - `tests/analysts/test_signals.py` — all schema tests pass (unaffected).
        - `tests/analysts/test_news_sentiment.py` — all tests pass (unaffected; doesn't use the moved helpers).
    11. Full repo regression: `poetry run pytest -x -q` → all green.
    12. Sanity grep: `grep -n "def _total_to_verdict" analysts/*.py` should ONLY surface `analysts/_indicator_math.py:N: def _total_to_verdict(...)` (zero copies in fundamentals.py / technicals.py / valuation.py).
    13. Commit (GREEN): `refactor(04-01): extract _build_df + _adx_14 + _total_to_verdict to analysts/_indicator_math.py (DRY trigger fired; zero behavior change)`
  </action>
  <verify>
    <automated>poetry run pytest tests/analysts/test_indicator_math.py -v && poetry run pytest --cov=analysts._indicator_math --cov-branch tests/analysts/test_indicator_math.py && poetry run pytest tests/analysts/ -v && poetry run pytest -x -q && python -c "from analysts._indicator_math import _build_df, _adx_14, _total_to_verdict, ADX_PERIOD, ADX_TREND_ABOVE, ADX_RANGE_BELOW, ADX_MIN_BARS, ADX_STABLE_BARS; assert ADX_PERIOD == 14 and ADX_TREND_ABOVE == 25.0 and ADX_RANGE_BELOW == 20.0 and ADX_MIN_BARS == 27 and ADX_STABLE_BARS == 150; print('OK')"</automated>
  </verify>
  <done>analysts/_indicator_math.py shipped with the 3 helpers + 5 ADX constants; analysts/{fundamentals, technicals, valuation}.py refactored to import from the shared module (no other behavior change); ≥6 dedicated tests green; coverage ≥90% line / ≥85% branch on the new module; all 57+ existing Phase 3 tests still GREEN; full repo regression GREEN; sanity grep confirms zero `def _total_to_verdict` outside `analysts/_indicator_math.py`; both commits (RED + GREEN) landed.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Append synthetic_oversold / overbought / mean_reverting builders to conftest.py + qualitative fixture tests (RED → GREEN)</name>
  <files>tests/analysts/conftest.py, tests/analysts/test_synthetic_fixtures.py</files>
  <behavior>
    Append three new module-level builders to the existing `tests/analysts/conftest.py` (preserving every existing fixture, builder, and the module docstring). Each new builder reuses the internal `_build_ohlc_bars` helper (already in conftest.py at lines 45-80) — no duplication of the OHLCBar construction logic.

    Determinism contract (existing conftest.py docstring already states this; extend if needed): each new builder uses NO random sources. The deterministic-noise pattern `0.001 * ((i % 5) - 2)` carries over from the Phase 3 builders. Two calls with identical kwargs produce byte-identical OHLCBar lists.

    Tests in `tests/analysts/test_synthetic_fixtures.py` (≥3, ideally 4):

    QUALITATIVE SHAPES:
    - test_synthetic_oversold_history_qualitative:
        ```python
        bars = synthetic_oversold_history(252)
        assert len(bars) == 252
        assert bars[-1].close < bars[0].close * 0.5    # sustained -0.5% daily + final -5% drops
        for b in bars:
            assert b.high > b.close > b.low > 0
            assert b.volume > 0
        ```
    - test_synthetic_overbought_history_qualitative:
        ```python
        bars = synthetic_overbought_history(252)
        assert len(bars) == 252
        assert bars[-1].close > bars[0].close * 2.0    # sustained +0.5% daily + final +5% pops
        for b in bars:
            assert b.high > b.close > b.low > 0
        ```
    - test_synthetic_mean_reverting_history_oscillates:
        ```python
        bars = synthetic_mean_reverting_history(252, period_bars=50, amplitude=0.10)
        closes = [b.close for b in bars]
        assert len(closes) == 252
        mean_close = sum(closes) / len(closes)
        assert abs(mean_close - 150.0) < 5.0          # oscillates symmetrically around start
        assert max(closes) > 150.0 * 1.05             # peak at +5% above start
        assert min(closes) < 150.0 * 0.95             # trough at 5% below start
        ```

    DETERMINISM:
    - test_synthetic_fixtures_deterministic:
        ```python
        for builder in (synthetic_oversold_history, synthetic_overbought_history, synthetic_mean_reverting_history):
            bars1 = builder(60)
            bars2 = builder(60)
            assert bars1 == bars2     # OHLCBar __eq__ uses Pydantic field equality
        ```
  </behavior>
  <action>
    RED:
    1. Write `tests/analysts/test_synthetic_fixtures.py` with the ≥3 tests above. Imports:
       ```python
       from tests.analysts.conftest import (
           synthetic_oversold_history,
           synthetic_overbought_history,
           synthetic_mean_reverting_history,
       )
       ```
    2. Run `poetry run pytest tests/analysts/test_synthetic_fixtures.py -x -q` → ImportError (the three new builders don't exist yet).
    3. Commit (RED): `test(04-01): add failing tests for synthetic_oversold / overbought / mean_reverting fixtures`

    GREEN:
    4. Edit `tests/analysts/conftest.py`:
       - APPEND the three new builders after `synthetic_sideways_history` (current last builder, ends at ~line 135). DO NOT remove or modify any existing fixture or builder.
       - Each builder follows the implementation_sketch's pattern exactly: define a `close_fn` closure, call `_build_ohlc_bars(n, start, close_fn=...)`.
       - For `synthetic_oversold_history`: the close_fn applies `daily_drift=-0.005` for the first `n - final_drop_bars` bars, then `(1 - final_drop_pct)` for the last `final_drop_bars` bars. Default `final_drop_bars=5`, `final_drop_pct=0.05`. Default `start=200.0`, `daily_drift=-0.005`.
       - For `synthetic_overbought_history`: mirror with `daily_drift=+0.005`, final pop `(1 + final_pop_pct)`. Default `start=100.0`, `final_pop_bars=5`, `final_pop_pct=0.05`.
       - For `synthetic_mean_reverting_history`: `close_fn = lambda i, _prev, s: s * (1.0 + amplitude * math.sin(2π i / period_bars))`. Default `start=150.0`, `amplitude=0.10`, `period_bars=50`. Note this is a souped-up version of `synthetic_sideways_history` (period 50 bars vs 20, amplitude 10% vs 2%).
       - Each new builder gets a docstring explaining its purpose and default qualitative shape (mirror the existing docstrings).
    5. Update the conftest.py module docstring's "Module-level builders" enumeration to include the three new names (preserves the index of public surface).
    6. Run `poetry run pytest tests/analysts/test_synthetic_fixtures.py -v` → all tests green.
    7. Phase 3 regression: `poetry run pytest tests/analysts/ -v` → all existing tests still GREEN (the new builders don't affect any existing fixture or test).
    8. Full repo regression: `poetry run pytest -x -q` → all green.
    9. Determinism spot-check: `poetry run python -c "from tests.analysts.conftest import synthetic_oversold_history; b1 = synthetic_oversold_history(252); b2 = synthetic_oversold_history(252); assert b1 == b2; print('deterministic OK', b1[-1].close)"`.
    10. Commit (GREEN): `test(04-01): add synthetic_oversold / overbought / mean_reverting builders to conftest.py + qualitative fixture tests`
  </action>
  <verify>
    <automated>poetry run pytest tests/analysts/test_synthetic_fixtures.py -v && poetry run pytest tests/analysts/ -v && poetry run pytest -x -q && poetry run python -c "from tests.analysts.conftest import synthetic_oversold_history, synthetic_overbought_history, synthetic_mean_reverting_history; assert len(synthetic_oversold_history(252)) == 252; assert len(synthetic_overbought_history(252)) == 252; assert len(synthetic_mean_reverting_history(252)) == 252; b1 = synthetic_oversold_history(60); b2 = synthetic_oversold_history(60); assert b1 == b2; print('OK')"</automated>
  </verify>
  <done>tests/analysts/conftest.py extended with 3 new deterministic builders (existing fixtures preserved); module docstring updated to enumerate them; tests/analysts/test_synthetic_fixtures.py committed with ≥3 qualitative + 1 determinism test, all GREEN; existing Phase 3 tests unaffected; both commits (RED + GREEN) landed.</done>
</task>

</tasks>

<verification>
- 2 tasks, 4 commits (RED + GREEN per task). TDD discipline preserved.
- Coverage gate: ≥90% line / ≥85% branch on `analysts/_indicator_math.py`.
- Phase 3 regression invariant: ALL existing tests in `tests/analysts/test_technicals.py` (25), `test_fundamentals.py` (18), `test_valuation.py` (12), `test_invariants.py` (2), `test_signals.py`, `test_news_sentiment.py` MUST stay GREEN. The refactor is line-equivalent; behavior is unchanged.
- New tests added: ≥6 in `test_indicator_math.py` + ≥3 in `test_synthetic_fixtures.py` = ≥9 new green tests.
- Sanity grep: `grep -n "def _total_to_verdict" analysts/*.py` returns ONLY `analysts/_indicator_math.py` (zero other copies).
- Sanity grep: `grep -n "def _build_df\|def _adx_14" analysts/*.py` returns ONLY `analysts/_indicator_math.py`.
- ADX module constants (`ADX_PERIOD`, `ADX_TREND_ABOVE`, `ADX_RANGE_BELOW`, `ADX_MIN_BARS`, `ADX_STABLE_BARS`) live in `analysts/_indicator_math.py`; `analysts/technicals.py` imports them (preserves any external references).
- `_adx_evidence` stays in `analysts/technicals.py` — NOT moved (technicals-specific evidence formatter).
- New synthetic builders (synthetic_oversold_history / synthetic_overbought_history / synthetic_mean_reverting_history) are deterministic (no random sources); two calls with identical kwargs produce byte-identical OHLCBar lists.
- Phase 4 Wave 1 + Wave 2 unblocked: PositionSignal schema (Wave 1 / 04-02) imports nothing from this plan but the synthetic fixtures are available; Position-Adjustment Radar analyst (Wave 2 / 04-03) imports `_build_df` + `_adx_14` from `analysts._indicator_math` and consumes the three synthetic fixtures for regression testing.

## Cross-Scope Risks

_vault_status=budget_exhausted; re-run /gmd:plan-phase --replan after vault-maintain_
</verification>

<success_criteria>
1. `analysts/_indicator_math.py` exists, imports cleanly, exports `_build_df` + `_adx_14` + `_total_to_verdict` + 5 ADX-related constants.
2. `analysts/{fundamentals, technicals, valuation}.py` refactored to import the shared helpers — no inline copies remain.
3. `analysts/technicals.py` keeps `_adx_evidence` inline (technicals-specific formatter).
4. ≥6 tests in `tests/analysts/test_indicator_math.py`, all GREEN; coverage ≥90% line / ≥85% branch on the new module.
5. ≥3 tests in `tests/analysts/test_synthetic_fixtures.py`, all GREEN; determinism spot-check passes.
6. `tests/analysts/conftest.py` extended with `synthetic_oversold_history`, `synthetic_overbought_history`, `synthetic_mean_reverting_history`. All existing fixtures preserved.
7. Phase 3 regression suite (57+ tests across 6 test files) stays GREEN — zero behavior change in the analyst modules.
8. Full repo regression: `poetry run pytest -x -q` exits 0.
9. Sanity greps confirm single-source-of-truth: zero `def _total_to_verdict` / `def _build_df` / `def _adx_14` outside `analysts/_indicator_math.py`.
10. Phase 4 Wave 1 (04-02 PositionSignal) and Wave 2 (04-03 Position-Adjustment analyst) unblocked.
</success_criteria>

<output>
After completion, create `.planning/phases/04-position-adjustment-radar/04-01-SUMMARY.md` summarizing the 4 commits, naming the extracted module's public surface (3 helpers + 5 constants), the 3 new synthetic builders, and the regression invariant (Phase 3 stayed GREEN). Reference 04-02 (PositionSignal schema) and 04-03 (Position-Adjustment analyst) as downstream consumers.

Update `.planning/STATE.md` Recent Decisions with a 04-01 entry naming: `analysts/_indicator_math.py` extraction (DRY trigger fired; 4th copy of `_total_to_verdict` consolidated; 2nd consumer of `_build_df` + `_adx_14` unblocked); 3 new synthetic-history builders for explicit overbought/oversold + mean-reverting regression tests; Phase 3 regression invariant held (57+ tests still green); Wave 1 (04-02) ready to launch.
</output>
