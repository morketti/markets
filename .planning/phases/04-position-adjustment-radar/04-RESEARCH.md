---
phase: 4
phase_name: Position-Adjustment Radar
researched: 2026-05-03
domain: Pure-function deterministic multi-indicator overbought/oversold consensus with ADX trend-regime gating
confidence: HIGH
research_tier: normal
vault_status: not_attempted
vault_reads: []
---

# Phase 4: Position-Adjustment Radar — Research

**Researched:** 2026-05-03
**Domain:** Pure-function deterministic multi-indicator overbought/oversold scoring — pandas indicator math + ADX trend-regime gating + state ladder + action-hint mapping (no LLM, no I/O, no persistence)
**Confidence:** HIGH (every locked decision in CONTEXT.md is consistent with the existing codebase; no factual gaps; one CONTEXT.md threshold defaults table needs a small refinement that this research locks; everything else is decision-confirmation rather than decision-discovery.)

## CORRECTIONS TO CONTEXT.md

> CONTEXT.md is overwhelmingly correct. The locked decisions all stand. Three refinements (none material; all "lock the value" rather than "change the lock"):

| # | Topic | CONTEXT.md says | Research finds | Recommendation |
|---|-------|-----------------|----------------|----------------|
| 1 | MACD histogram scoring formula | "magnitude relative to recent trailing distribution (Z-score-style normalization recommended; research will lock the formula)" — explicitly deferred to research | Research locks **z-score over trailing 60 bars (≈ 3 months of trading days)**, clipped at ±2 stdevs and linearly mapped to [-1, +1]. Justification: matches MACD canonical reference range (~±2 sigma envelope), matches the z-score-vs-50-day-MA approach for the parallel z-score indicator, single-parameter tunable, robust to ticker price-scale (NVDA at $900 vs F at $12 don't bias the signal). Percentile-rank was the runner-up; rejected because it's harder to explain in evidence strings ("MACD histogram at 87th percentile" reads worse than "MACD histogram z=+1.4 — bullish momentum"). Raw histogram is rejected outright (Pitfall #3). | Lock z-score(60 bars), clip at ±2 stdevs, map (z / 2) → [-1, +1]. Module constant `MACD_HISTOGRAM_ZSCORE_BARS = 60`. Warm-up: needs MACD warm-up (34 bars) + 60 z-score bars = ~94 total. Below 94 bars, MACD sub-signal returns (0, None — same convention as Phase 3 helpers). |
| 2 | MIN_BARS_FOR_ANY_INDICATOR floor | "= 14 (Stochastic %K + Williams %R floor)" | Confirmed — Stochastic %K and Williams %R both use a 14-bar lookback and produce a valid value at exactly the 14th bar. Bollinger Bands needs 20 bars; RSI(14) needs 27 (= 2N-1, Wilder warm-up); z-score-vs-MA50 needs 50; MACD-with-z-score-normalization needs ~94. **MIN_BARS_FOR_ANY_INDICATOR=14 is correct.** Below 14 → data_unavailable. Between 14 and 19 → only Stochastic + Williams %R contribute; everything else returns (0, None). The graceful-degradation pattern is fine. | LOCK CONTEXT.md value as-is. The threshold defaults table is correct. |
| 3 | TREND_REGIME_DOWNWEIGHT value | "0.5 (mean-reversion indicators when ADX > 25)" — provisional | Confirmed at 0.5 with a defensible rationale — see Patterns #4 and Pitfall #2 below. Empirical reasoning: in trending markets RSI / Stochastic / Williams %R / BB position can stay pinned in oversold/overbought zones for weeks (multiple sources cite this — Schwab, Wikipedia, Lux Algo). Halving the weight keeps the signal in the consensus (so a strong trend-confirming z-score + MACD aren't drowning out a 50% RSI vote) but prevents 4 mean-reversion indicators from swamping 2 trend-following ones at the boundary. The value is tunable via `TREND_REGIME_DOWNWEIGHT` module constant — if v1.x evidence shows 0.5 is too aggressive (mean-reversion indicators underweighted in mild trends), drop to 0.7 in a single-line edit. | LOCK 0.5 with the rationale documented in the docstring. |

**Confidence:** HIGH on all three. None of these block planning; they're "lock the value" decisions that would otherwise re-litigate during implementation.

Everything else in CONTEXT.md — the schema, module layout, scoring philosophy, state ladder, action_hint mapping, empty-data UNIFORM RULE, threshold defaults, aggregation math, indicator list — is consistent with the existing codebase and should ship as locked.

## Summary

Phase 4 ships **one pure-function module** — Position-Adjustment Radar — that computes 6 mean-reversion / trend-following indicators against the per-ticker `Snapshot.prices.history` and emits a `PositionSignal` carrying state ∈ 5-state ladder, signed `consensus_score` ∈ [-1, +1], indicator-agreement `confidence` ∈ [0, 100], `action_hint` derived from state, per-indicator readings, and a trend-regime flag from ADX(14) > 25. Surface area: ~280 LOC of production Python (1 new module, ~80 LOC of helpers extracted from Phase 3 into a shared `_indicator_math.py`), ~450 LOC of tests, **zero new pip dependencies** (pandas + numpy already transitive via yfinance, same as Phase 3).

**The four research questions that drove this document and the locks they produced:**

1. **Indicator-library decision (deferred from Phase 3).** Hand-rolled wins. ~60 LOC of net-new indicator math (RSI 8 LOC, Bollinger position 6 LOC, Stochastic %K 5 LOC, Williams %R 5 LOC, MACD 12 LOC, z-score-vs-MA50 4 LOC, MACD z-score normalization 6 LOC) for 6 indicators. ta-lib bundles a C library (~5MB binary; cgohlke wheels for Windows are easy in 2026 but still a system-level dep posture); pandas-ta-classic (192 indicators, MIT, actively maintained — last release 0.5.44 April 2026) is the most defensible "if we change our minds later" option but wastes context on 186 unused indicators and a numba optional dep we'd never want. Hand-roll matches the Phase 3 03-03 precedent, defers the dep-choice debate one more phase (POSE is the pivot point — if Phase 4's indicators land cleanly, the dep-choice is resolved permanently against ta-lib / pandas-ta-classic), and preserves the keyless / single-source posture (every indicator's correctness is verifiable against StockCharts canonical references).

2. **Wilder smoothing reuse.** RSI(14) uses the same `pandas.Series.ewm(alpha=1/N, adjust=False).mean()` idiom Phase 3 already locked in `_adx_14`. Mathematical identity to Wilder's recursive formula confirmed against StockCharts ChartSchool. The `_adx_14` and `_build_df` helpers from `analysts/technicals.py` should be EXTRACTED into a new `analysts/_indicator_math.py` shared module in Wave 0 — this is the 4th time `_total_to_verdict` would be copied (already 3x across Phase 3) and the 2nd time `_build_df` would be copied. DRY trigger has fired.

3. **MACD histogram normalization.** Locked: **z-score over trailing 60 bars, clipped at ±2 stdevs, mapped linearly to [-1, +1]**. See CORRECTION #1 above for justification.

4. **Confidence formula.** Locked: `confidence = round(100 * (n_agreeing / n_active))` where `n_active` is the count of indicators that produced a non-None reading (graceful-degradation aware) AND `n_agreeing` counts indicators whose sub-signal sign matches the sign of `consensus_score`. **Edge case: indicators with sub-signal exactly 0 (within ±0.01) are treated as "abstaining" — they count toward `n_active` but NOT toward `n_agreeing`** (a near-zero indicator is genuinely indeterminate; counting it as "agrees with consensus" inflates confidence; counting it as "disagrees" deflates confidence; treating it as abstain is the calibrated choice). When `n_active < 2`, confidence is capped at 0 — single-indicator agreement is meaningless.

**Primary recommendation:** Three-wave plan structure — Wave 0 (refactor: extract `_build_df` + `_adx_14` + `_total_to_verdict` from `analysts/technicals.py` into `analysts/_indicator_math.py`; add `synthetic_oversold_history` + `synthetic_overbought_history` builders to `tests/analysts/conftest.py`; existing Phase 3 tests still pass). Wave 1 (`PositionSignal` + `PositionState` + `ActionHint` schema in `analysts/position_signal.py`; ~80 LOC + ~150 LOC tests). Wave 2 (`analysts/position_adjustment.py` with all 6 indicator helpers + `score()` + state mapping + action_hint mapping; ~280 LOC + ~450 LOC tests). The Wave 0 refactor is mechanical and low-risk (no behavior change; both Phase 3 technicals tests still pass after the move). Waves 1 and 2 can each parallelize across helpers but must serialize between waves (Wave 2 imports the schema from Wave 1).

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Output schema** is `PositionSignal` (NOT `AgentSignal`) at `analysts/position_signal.py` (or co-located in `analysts/position_adjustment.py` — planner decides). Fields: `ticker: str`, `computed_at: datetime`, `state: PositionState = "fair"`, `consensus_score: float ∈ [-1, +1] = 0.0`, `confidence: int ∈ [0, 100] = 0`, `action_hint: ActionHint = "hold_position"`, `indicators: dict[str, float | None]`, `evidence: list[str]` (≤10 items, ≤200 chars each), `data_unavailable: bool = False`, `trend_regime: bool = False`. `ConfigDict(extra="forbid")`. Ticker normalized via `analysts.schemas.normalize_ticker`.
- **5-state PositionState ladder:** `extreme_oversold | oversold | fair | overbought | extreme_overbought`. Strict `>` / `<` boundaries at ±0.6 / ±0.2.
- **4-state ActionHint ladder:** `consider_add | hold_position | consider_trim | consider_take_profits`. Mapping: extreme_oversold + oversold → consider_add; fair → hold_position; overbought → consider_trim; extreme_overbought → consider_take_profits.
- **Public surface:** `score(snapshot: Snapshot, config: TickerConfig, *, computed_at: Optional[datetime] = None) -> PositionSignal`. Pure function, no I/O, no module-level mutable state. Module-level threshold constants at the top.
- **Indicator list (6 + ADX gate):** RSI(14), Bollinger Bands position (`(close - SMA20) / (2 * stdev20)` — units of stdevs), z-score vs 50-day MA (`(close - SMA50) / stdev50`), Stochastic %K (14), Williams %R (14), MACD histogram (12/26/9 with z-score normalization). ADX(14) is the regime gate (already implemented in Phase 3).
- **Trend-regime gating:** ADX(14) > 25 → mean-reversion indicators (RSI, BB position, Stochastic %K, Williams %R) DOWNWEIGHTED to 0.5x. Trend-following indicators (z-score vs MA50, MACD histogram) RETAIN full weight. ADX < 20 OR ADX between 20-25 → all weights = 1.0 (no gating; avoids discontinuity at ADX=25).
- **Empty-data UNIFORM RULE:** `data_unavailable=True ⟹ state="fair", consensus_score=0.0, confidence=0, action_hint="hold_position"`. Indicator-readings dict carries None values. Per-branch evidence string ("snapshot data_unavailable=True", "prices snapshot missing", "prices.data_unavailable=True", "history has N bars; need ≥14 for any indicator"). MIN_BARS_FOR_ANY_INDICATOR = 14.
- **Threshold home:** module-level constants at top of `analysts/position_adjustment.py`. NO central `analysts/thresholds.py`. NO TOML/YAML config.
- **Determinism:** `now = computed_at if computed_at is not None else datetime.now(timezone.utc)` read ONCE at top of `score()`; helpers receive `now` as parameter. Same Pitfall #7 discipline as Phase 3 (locked by AST-walk test in 03-04 — Phase 4 should follow the same pattern, see Pitfall #6 below).
- **Provenance header (INFRA-07):** mandatory. References virattt's `risk_manager.py` for the multi-indicator-consensus aggregation pattern (even though virattt's risk manager is position-sizing-focused, not overbought/oversold-focused — this is a "structural pattern adapted from..." rather than a line-for-line port). Module is largely novel-to-this-project; the docstring states that.
- **No LLM / no I/O.** Phase 4 is deterministic Python end-to-end. Lite-mode (INFRA-02) compatible by construction.
- **Same evidence convention as AgentSignal.evidence:** embed metric, observed value, threshold or comparison. Examples in CONTEXT.md `<specifics>` block.

### Claude's Discretion

- **Indicator-library choice.** CONTEXT.md provisionally recommends hand-rolled; research locks this (see Pattern #1).
- **MACD histogram normalization formula.** CONTEXT.md defers to research; locked at z-score over 60 bars, clipped ±2 (see CORRECTION #1).
- **Confidence formula edge cases.** CONTEXT.md provides the base formula; research locks the near-zero indicator handling (see Pattern #6).
- **Module name** for `PositionSignal` — `analysts/position_signal.py` separate file vs co-located in `analysts/position_adjustment.py`. Recommend SEPARATE file (matches Phase 3's `analysts/signals.py` separation; lets future phases import the schema without paying the indicator-math import cost).
- **`_indicator_math.py` extraction.** CONTEXT.md recommends; research confirms (see Pattern #2 + Anti-Pattern #5).
- **Synthetic oversold/overbought history fixture parameter shape and location.** Recommend conftest.py (DRY across the Phase 4 test files; mirrors Phase 3 conftest.py shape). See Pattern #3.
- **Whether to add an optional `@model_validator(mode="after")` on `PositionSignal`** enforcing `data_unavailable=True ⟹ state=="fair" AND consensus_score==0.0 AND confidence==0 AND action_hint=="hold_position"` (analogue of Phase 3's AgentSignal invariant). Recommend INCLUDE — Phase 3's analog closes a class of bugs at zero schema-shape cost. See Pitfall #1.
- **MACD histogram lookback window for z-score normalization.** Recommend 60 bars (≈ 3 months); see CORRECTION #1.

### Deferred Ideas (OUT OF SCOPE)

- Per-sector / peer-relative overbought-oversold scoring — v1.x SEC-01.
- Per-ticker calibrated thresholds — v1.x territory.
- Volume-weighted indicators (OBV, MFI, A/D Line) — considered + rejected; revisit if accuracy is the limit.
- Multi-timeframe consensus (daily + weekly) — v1.x.
- Machine-learning regime classifier (replacing ADX gating) — v2.
- Real-time tick-level POSE — v1.x OND-01.
- Persona signal trend view ("position has been overbought 3 weeks") — v1.x TREND-01.
- action_hint refinement via sentiment / fundamentals overlay — Phase 7's job, NOT Phase 4's.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| POSE-01 | Position-Adjustment Analyzer computes multi-indicator consensus from RSI(14), Bollinger Bands position, z-score vs 50-day MA, Stochastic %K, Williams %R, MACD divergence | All 6 indicators expressible in `pandas.Series.rolling()` + `.ewm()` idioms (Patterns #1, #2, #5); canonical formulas verified against StockCharts ChartSchool for each. Min-bars warm-up table locked. |
| POSE-02 | Output `state` ∈ {extreme_oversold, oversold, fair, overbought, extreme_overbought}; `consensus_score` ∈ [-1, +1]; `confidence` reflects indicator agreement count | 5-state Literal + signed float aggregate locked verbatim from CONTEXT.md. Confidence formula locked via Pattern #6 with near-zero abstain-rule edge-case handling. |
| POSE-03 | ADX(14) > 25 triggers trend-regime gating: mean-reversion indicators are downweighted in scoring | TREND_REGIME_DOWNWEIGHT=0.5 locked (CORRECTION #3 above; see Pattern #4 + Pitfall #2). Reuses `_adx_14` from Phase 3 — extracted to `analysts/_indicator_math.py` in Wave 0 per Pattern #2. |
| POSE-04 | `action_hint` derived from state ∈ {consider_add, hold_position, consider_trim, consider_take_profits} | Fixed mapping locked verbatim from CONTEXT.md. Note: `consider_add` collapses extreme_oversold + oversold (no `strong_consider_add` tier — Phase 7 reads `confidence` and `consensus_score` to derive conviction band). |
| POSE-05 | Position-Adjustment output is the headline data structure powering the Morning Scan's primary lens | Schema is self-contained (PositionSignal carries ticker + computed_at + indicators dict + evidence) — Phase 6 deserializes via Pydantic round-trip; Phase 5 routine writes alongside the four AgentSignals; sort by `|consensus_score|` descending (per VIEW-02) is the headline ordering. |

## Reference Repo (virattt/ai-hedge-fund) File Mapping

The reference repo is **not present in this codespace** (verified via `find / -name ai-hedge-fund -type d` returning no results — same as Phase 3). Provenance comments must reference the canonical GitHub URLs.

| Our Phase 4 module | Reference source file | Adopt | Diverge |
|---------------------|---------------------|-------|---------|
| `analysts/position_adjustment.py` | `src/agents/risk_manager.py` (closest analog — multi-indicator aggregation, even though virattt's focus is position-sizing) | **Multi-indicator weighted aggregation** pattern: per-indicator sub-signal + weight; total = Σ(s × w) / Σ(w); regime-conditional weight overrides | virattt's risk_manager focuses on volatility-adjusted position sizing + correlation-based limit reduction; we focus on overbought/oversold consensus. The aggregation math is structurally identical (weighted mean of sub-signals); the inputs and intent differ. **Provenance header is "structural pattern adapted from..." rather than "ported from..."** — see Pattern #7. |
| `analysts/position_adjustment.py` (technicals indicator math) | `src/agents/technicals.py` | **Hand-rolled pandas indicator pattern** (locked by Phase 3 03-03) | Phase 3 already adapted technicals.py with extensive modifications. Phase 4 extends the pattern to RSI / BB / Stochastic / Williams %R / MACD without re-citing virattt; the `analysts/_indicator_math.py` extracted helpers are sufficient provenance. |
| `analysts/position_signal.py` | (no direct analog — virattt's signal/confidence/reasoning shape doesn't carry state ladder + action hint + indicator readings) | Pydantic schema discipline (extra="forbid" + field validators + ticker normalization) | New schema; provenance header notes "novel to this project — separate from AgentSignal because state ladder + action_hint + per-indicator dict don't fit AgentSignal's verdict-ladder shape". |

**Mandatory provenance header format** (matches Phase 3 / INFRA-07 precedent — single source of truth pattern from `analysts/technicals.py`):

```python
"""Position-Adjustment Radar — pure-function multi-indicator consensus scoring.

Aggregation pattern (multi-indicator weighted consensus + regime-conditional
weights) adapted from virattt/ai-hedge-fund/src/agents/risk_manager.py
(https://github.com/virattt/ai-hedge-fund/blob/main/src/agents/risk_manager.py).

Indicator math reuses the pandas hand-rolled pattern locked in
analysts/technicals.py (Phase 3 03-03) and shared via
analysts/_indicator_math.py.

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
  * confidence reflects INDICATOR AGREEMENT (n_agreeing / n_active),
    NOT magnitude — distinct from AgentSignal's confidence which mixes
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

The 6 Phase 4 indicators add ~60 LOC of net-new indicator math vs the 3
already shipped in Phase 3 (MA stack + momentum + ADX). Phase 4 is the
last opportunity to revisit the ta-lib / pandas-ta-classic decision —
locked here against. Acceptable scope for v1.
"""
```

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | ≥ 2.10 (already pinned, 2.13.3 in poetry.lock) | `PositionSignal` schema | Locked across project; v2 core is Rust; field/model_validator already used by AgentSignal |
| pandas | already transitive (3.0.2) | Indicator math (rolling, ewm, diff, std) | Already in poetry.lock via yfinance; zero new install; identical idioms to Phase 3 technicals |
| numpy | already transitive (2.4.4) | Math primitives (NaN handling, where, clip) | Already in poetry.lock via pandas |
| pytest / pytest-cov | already pinned | Tests | Standard project pattern |

### Stdlib (no new install)
| Module | Purpose | Note |
|--------|---------|------|
| `datetime` (with `timezone.utc`) | `computed_at` timestamps | Same UTC pattern as everywhere else |
| `typing.Literal` | PositionState (5-state) + ActionHint (4-state) Literals | Same pattern as `Verdict` / `AnalystId` in Phase 3 |
| `math` | (likely none — pandas handles all math; reserve `math` for evidence-string formatting if needed) | |

### Alternatives Considered

| Instead of | Could Use | Tradeoff | Recommendation |
|------------|-----------|----------|----------------|
| Hand-rolled pandas indicator math | **ta-lib** (`pip install ta-lib`; binary wheels from cgohlke since 0.6.5 / Oct 2025) | ta-lib has every TA indicator and is C-fast; bundles a 5MB+ C library. Wheels work on Windows / Mac / Linux for cpython 3.10-3.14 in 2026. Install posture is "system-level dep" — adds a wheel-availability axis to the lockfile and a CI matrix. ta-lib only wins at 100+ indicator scale; we have 6. | **Hand-roll.** ~60 LOC of net-new indicator math vs. taking on a C library we'll have to lock and verify wheel availability for across Python versions. Phase 3 03-RESEARCH.md already provisionally said "skip ta-lib, revisit at Phase 4"; Phase 4 confirms the skip. |
| Hand-rolled pandas indicator math | **pandas-ta-classic** (MIT, active fork, 192 indicators, last release 0.5.44 in April 2026, 270 GitHub stars, 73 forks) | MIT-licensed fork of original pandas-ta (which is unmaintained). Pure Python (with optional numba acceleration). Pulls in pandas + numpy (already there). Optional ta-lib acceleration on 34 core indicators when ta-lib installed. Indicator API is `df.ta.rsi(length=14)`. | **Skip.** We need exactly 6 of the 192 indicators; the other 186 are dead context. Hand-rolling 6 indicators is ~60 LOC; pandas-ta-classic is a new dep with versioning + breakage axis. Most importantly: hand-rolling matches the Phase 3 03-03 precedent and unifies the codebase posture. If we ship pandas-ta-classic in Phase 4, we'd want to retroactively migrate Phase 3 technicals to it — that's a refactor for v1.x at minimum. **Lock the dependency-choice debate against pandas-ta-classic permanently here.** |
| Hand-rolled MACD via `.ewm(span=N, adjust=False).mean()` | TA-Lib `MACD()` function | TA-Lib's MACD bundles the 12/26/9 logic; one function call. ~5 LOC saved. | **Hand-roll.** Saves 5 LOC at the cost of a C library dep. Not worth it. |
| Hand-rolled z-score | `scipy.stats.zscore` | Pulls scipy as transitive dep (~30MB on disk). | **Hand-roll** — `(close.iloc[-1] - rolling.mean()) / rolling.std()` is 1 line. |

**No new dependencies.** pyproject.toml is unchanged (vs. Phase 3 which added vaderSentiment). The lockfile is unchanged. Wave 0 is purely a refactor + fixture-add; Waves 1 and 2 add files but no deps.

## Architecture Patterns

### Recommended Module Structure (this phase only)

```
analysts/
├── schemas.py             # EXISTING — TickerConfig, Watchlist, normalize_ticker (no changes)
├── data/                  # EXISTING — Snapshot + sub-schemas (no changes)
├── signals.py             # EXISTING — AgentSignal + Verdict + AnalystId (no changes)
├── fundamentals.py        # EXISTING (no changes)
├── technicals.py          # EXISTING — _build_df + _adx_14 + _total_to_verdict EXTRACTED to _indicator_math.py in Wave 0; technicals.py imports them
├── news_sentiment.py      # EXISTING (no changes)
├── valuation.py           # EXISTING (no changes)
├── _indicator_math.py     # NEW (Wave 0) — shared _build_df + _adx_14 + _total_to_verdict (~80 LOC)
├── position_signal.py     # NEW (Wave 1) — PositionSignal + PositionState + ActionHint (~80 LOC)
└── position_adjustment.py # NEW (Wave 2) — score() + 6 indicator helpers + state/action_hint mapping (~280 LOC)

tests/analysts/
├── conftest.py            # MODIFIED (Wave 0) — add synthetic_oversold_history + synthetic_overbought_history builders
├── test_indicator_math.py # NEW (Wave 0) — coverage on the extracted helpers (~50 LOC, ~6 tests)
├── test_position_signal.py # NEW (Wave 1) — schema validation (~150 LOC, ~10-12 tests)
└── test_position_adjustment.py # NEW (Wave 2) — score() correctness (~450 LOC, ~25-30 tests)
```

**Wave 0 invariant:** existing Phase 3 tests (`test_technicals.py`, all 25 tests) must remain GREEN after the refactor. The refactor only moves helpers; technicals.py still contains the analyst-specific orchestration. `_total_to_verdict` is the only helper currently in 3 places (fundamentals, technicals, valuation) — see Anti-Pattern #5 for the DRY-trigger rationale.

**Coverage source already includes `analysts`** (verified in `pyproject.toml`) — no changes for new files.

### Pattern 1: Hand-rolled indicator math via pandas (locked from Phase 3)

**What:** Convert `snapshot.prices.history: list[OHLCBar]` to a `pandas.DataFrame` with `high`, `low`, `close` columns indexed by date, run all indicator math against it.

**Why:** Pandas + numpy already transitive via yfinance. `pandas.Series.rolling(N).mean()` for SMA, `.ewm(alpha=1/N, adjust=False).mean()` for Wilder smoothing, `.diff()` / `.shift()` / `.std()` / `.rolling().min()/max()` for everything else. Zero new deps.

**Example (RSI(14) — full 8 LOC):**

```python
# In analysts/position_adjustment.py
def _rsi_14(df: pd.DataFrame) -> Optional[float]:
    """Wilder RSI(14). Returns None below 27 bars (= 2N-1 warm-up).

    Source: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/relative-strength-index-rsi
    Wilder smoothing == pandas .ewm(alpha=1/14, adjust=False).mean() — identity
    locked in 03-RESEARCH.md and reused here.
    """
    if len(df) < RSI_MIN_BARS:  # 27
        return None
    delta = df["close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1.0 / RSI_PERIOD, adjust=False).mean()
    loss = (-delta).clip(lower=0).ewm(alpha=1.0 / RSI_PERIOD, adjust=False).mean()
    rs = gain.iloc[-1] / loss.iloc[-1] if loss.iloc[-1] != 0 else float("inf")
    rsi = 100.0 - (100.0 / (1.0 + rs)) if rs != float("inf") else 100.0
    return float(rsi) if not pd.isna(rsi) else None
```

**Other 5 indicators** follow the same shape (see Code Examples below).

### Pattern 2: Extract `_build_df` + `_adx_14` + `_total_to_verdict` to `analysts/_indicator_math.py` in Wave 0

**What:** A shared module containing the indicator helpers used by BOTH `analysts/technicals.py` (Phase 3) and `analysts/position_adjustment.py` (Phase 4). Mechanical move, zero behavior change.

**Why (the DRY trigger has fired):**
- `_total_to_verdict` is currently copied 3x: `analysts/fundamentals.py:179-188`, `analysts/technicals.py:271-280`, `analysts/valuation.py` (verified by reading 03-03-SUMMARY which calls this out: "DRY trigger waits for the third copy in 03-04 / 03-05; a shared analysts.verdict._total_to_verdict helper lands when refactoring becomes the cheaper path"). Phase 4 would be the 4th copy.
- `_build_df` is currently in `analysts/technicals.py:96-114`. Phase 4 needs the SAME function (sort by date, dropna on close). Copy-paste would be the 2nd instance.
- `_adx_14` is in `analysts/technicals.py:193-249`. Phase 4 reads ADX as the trend-regime gate input. Either Phase 4 imports `from analysts.technicals import _adx_14` (private import — bad) or duplicates ~60 LOC (worse) or extracts to shared module (right).

**The extraction is mechanical:**

```python
# Wave 0 task 1: create analysts/_indicator_math.py
"""Shared indicator math used across the analyst suite.

Extracted from analysts/technicals.py (Phase 3 03-03) when Phase 4 POSE
landed and the DRY trigger fired (4th copy of _total_to_verdict; 2nd copy
of _build_df; needed _adx_14 from a second consumer).

Public surface (semantic-public — single underscore prefix is project
convention for module-internal helpers, but these are imported by sibling
analyst modules):
    _build_df(history) -> pd.DataFrame
    _adx_14(df) -> Optional[float]
    _total_to_verdict(normalized) -> Verdict (re-exported via analysts.signals)
"""
from __future__ import annotations
from typing import Optional
import pandas as pd
from analysts.data.prices import OHLCBar
from analysts.signals import Verdict

ADX_PERIOD: int = 14
ADX_MIN_BARS: int = 27  # = 2*N - 1 — Wilder warm-up


def _build_df(history: list[OHLCBar]) -> pd.DataFrame:
    # Verbatim copy from analysts/technicals.py (no behavior change).
    ...


def _adx_14(df: pd.DataFrame) -> Optional[float]:
    # Verbatim copy from analysts/technicals.py (no behavior change).
    ...


def _total_to_verdict(normalized: float) -> Verdict:
    # Verbatim copy from analysts/{fundamentals,technicals,valuation}.py.
    ...
```

```python
# Wave 0 task 2: in analysts/technicals.py, replace inline definitions with imports
from analysts._indicator_math import _build_df, _adx_14, _total_to_verdict
```

**Test invariant:** All 25 Phase 3 technicals tests must PASS after the move. The refactor is line-equivalent; behavior is unchanged. Wave 0 closes when `pytest tests/analysts/test_technicals.py -v` is GREEN AND a new `tests/analysts/test_indicator_math.py` exists with ~6 tests covering the 3 extracted helpers (smoke + ADX warm-up + verdict tiering boundaries).

**Why this is right:**
- Single source of truth for the 3 helpers — no future drift between Phase 3 and Phase 4 implementations (e.g. someone tweaks `_total_to_verdict` thresholds in fundamentals.py, technicals stays the old behavior).
- Phase 4 imports become clean: `from analysts._indicator_math import _build_df, _adx_14`.
- Phase 5 / 6 / 7 may import `_total_to_verdict` for cross-cutting verdict tiering logic if needed.

**Risks (each addressed):**
- **Code-organization churn.** Mitigated by mechanical move — no API change for the public `score()` functions. Existing callers are unaffected.
- **Harder back-port to virattt patterns.** Each analyst module's provenance docstring still references its virattt source; the shared helpers are documented as our extraction. The shared module's docstring documents the extraction lineage.

### Pattern 3: Synthetic oversold/overbought history fixtures (Wave 0)

**What:** Add two new fixtures to `tests/analysts/conftest.py` for explicit overbought/oversold regression testing — `synthetic_oversold_history(n)` and `synthetic_overbought_history(n)`. Same module-level builder pattern as Phase 3's `synthetic_uptrend_history` / `synthetic_downtrend_history` / `synthetic_sideways_history`.

**Why in conftest.py (not Phase 4 test file's local helpers):**
- Phase 5 routine integration tests (eventually) may reuse these fixtures.
- Phase 6 frontend rendering tests for the morning-scan view may reuse them.
- The Phase 3 conftest pattern is established and well-tested; extending it is the established way to share builders across test files.

**Recommended formulas:**

```python
# Append to tests/analysts/conftest.py

def synthetic_oversold_history(
    n: int = 252,
    start: float = 200.0,
    daily_drift: float = -0.005,
    final_drop_bars: int = 5,
    final_drop_pct: float = 0.05,
) -> list[OHLCBar]:
    """n daily bars in a downtrend ending with a sharp drop — explicit oversold regime.

    Trend portion (first n - final_drop_bars bars): synthetic_downtrend_history shape
    (geometric drift + small bounded noise). Then the final final_drop_bars (default 5)
    bars drop an additional final_drop_pct (default 5%) to push RSI below 30, BB
    position below -1, Stochastic %K below 20, Williams %R below -80.

    Default 252 bars at -0.005 daily_drift → ~0.28x. Final 5 bars at -0.05 → close
    finishes at ~0.27x of start. This produces RSI ≈ 22-28, BB position ≈ -1.4 to -1.6,
    Stochastic %K ≈ 10-15, Williams %R ≈ -85 to -90.
    """

def synthetic_overbought_history(
    n: int = 252,
    start: float = 100.0,
    daily_drift: float = 0.005,
    final_pop_bars: int = 5,
    final_pop_pct: float = 0.05,
) -> list[OHLCBar]:
    """Mirror of synthetic_oversold_history. n bars in an uptrend ending with a sharp pop.
    Produces RSI ≈ 72-78, BB position ≈ +1.4 to +1.6, Stochastic %K ≈ 85-90,
    Williams %R ≈ -10 to -15.
    """
```

Both fixtures are deterministic (no random sources, same `(i % 5) - 2` noise pattern as the Phase 3 fixtures). The 5-bar final-shock parameter is tunable per test (callers can pass `final_drop_pct=0.10` for "extreme oversold" assertions).

**One additional fixture (recommended):**

```python
def synthetic_mean_reverting_history(
    n: int = 252,
    start: float = 150.0,
    amplitude: float = 0.10,
    period_bars: int = 50,
) -> list[OHLCBar]:
    """n daily bars oscillating around start with controlled period and amplitude.

    close[i] = start * (1 + amplitude * sin(2π i / period_bars)).

    Default amplitude=0.10 (vs sideways=0.02) is wide enough to trigger BB position
    extremes at peak/trough but mean-reverting enough to keep ADX < 20 (range regime).
    Useful for testing "mean-reversion indicators score correctly when ADX confirms
    range" path.
    """
```

This is a souped-up version of `synthetic_sideways_history` (period 50 bars vs 20, amplitude 10% vs 2%). The Phase 4 test for "BB position at lower band → oversold sub-signal" benefits from this fixture — it's a clean signal vs. the noise.

### Pattern 4: Multi-indicator weighted aggregation with regime-conditional weights

**What:** Each of the 6 indicators emits a sub-signal in [-1, +1] (negative = oversold, positive = overbought). Aggregation:

```python
# Locked aggregation skeleton (CONTEXT.md):

# Per-indicator sub-signal (negative = oversold, positive = overbought):
rsi_signal = _rsi_to_signal(rsi_value)        # (rsi - 50) / 50, clamped ±1
bb_signal = _bb_to_signal(bb_position)        # clamp(bb_position, -1, +1) — already in stdev units
zscore_signal = _zscore_to_signal(z)          # clamp(z / 2, -1, +1) — z=±2 maps to ±1
stoch_signal = _stoch_to_signal(stoch_k)      # (50 - stoch_k) / 50, clamped ±1 (sign-flipped)
williams_signal = _williams_to_signal(w_r)    # (w_r + 50) / 50, clamped ±1 (sign-flipped)
macd_signal = _macd_to_signal(macd_z)         # clamp(macd_z / 2, -1, +1) — z=±2 maps to ±1

# Regime-conditional weights:
if adx_value is not None and adx_value > ADX_TREND_ABOVE:  # 25
    # Mean-reversion indicators downweighted; trend-following keep full weight.
    weights = {
        "rsi_14":          0.5,  # mean-reversion → downweight
        "bb_position":     0.5,
        "stoch_k":         0.5,
        "williams_r":      0.5,
        "zscore_50":       1.0,  # trend-following → full weight
        "macd_histogram":  1.0,
    }
    trend_regime = True
else:
    # ADX < 20 OR ADX between 20-25: all weights at 1.0 (no gating).
    weights = {k: 1.0 for k in ("rsi_14", "bb_position", "stoch_k", "williams_r", "zscore_50", "macd_histogram")}
    trend_regime = False

# Build (signal, weight, evidence) triples — only for active indicators:
sub_signals: list[tuple[float, float, str]] = []
if rsi_value is not None: sub_signals.append((rsi_signal, weights["rsi_14"], rsi_evidence))
# ... same for others ...

if not sub_signals:
    return PositionSignal(... data_unavailable=True ...)

total_w = sum(w for _, w, _ in sub_signals)
consensus_score = sum(s * w for s, w, _ in sub_signals) / total_w  # ∈ [-1, +1]
```

**Why:** Same shape as virattt's risk_manager weighted-aggregation pattern; same shape as Phase 3 valuation.py's all-three blend. Familiar; well-tested. Regime-conditional weights are the only Phase 4-specific addition.

**Boundary discipline:** at ADX = 25.0 exactly, the `>` is False (no downweight). At ADX = 25.001, the `>` is True (downweight). The 20-25 ambiguous zone is handled by NOT downweighting in `<= 25` — the ADX_TREND_ABOVE check is the only regime threshold consulted. This matches Phase 3 technicals.py's `if adx_val > ADX_TREND_ABOVE:` boundary.

### Pattern 5: Per-indicator helper signature `(score, weight, evidence)` tuple

**What:** Each indicator helper returns a 3-tuple — (signed sub-signal in [-1, +1], weight in {0.5, 1.0}, evidence string or None). When the indicator is not yet computable (insufficient warm-up bars), returns `(0.0, 0.0, None)` — zero weight ensures the indicator doesn't pollute the aggregation.

**Why:** Mirrors Phase 3 fundamentals/technicals' `(score, evidence)` tuple but extends to weight-aware. The (score, weight, evidence) shape lets the aggregation loop be a single comprehension; each indicator helper is testable in isolation.

**Example skeleton:**

```python
def _rsi_to_subsignal(
    df: pd.DataFrame, *, weight: float
) -> tuple[float, float, Optional[str], Optional[float]]:
    """RSI(14) sub-signal. Returns (sub_signal, weight, evidence, raw_rsi).

    raw_rsi is returned for the indicators dict on PositionSignal. Returns
    (0.0, 0.0, None, None) when insufficient bars (<27).
    """
    rsi = _rsi_14(df)
    if rsi is None:
        return 0.0, 0.0, None, None
    sub_signal = max(-1.0, min(1.0, (rsi - 50.0) / 50.0))  # canonical linearization
    if rsi < RSI_OVERSOLD_BELOW:  # 30
        evidence = f"RSI(14) {rsi:.1f} — oversold (below {RSI_OVERSOLD_BELOW:.0f})"
    elif rsi > RSI_OVERBOUGHT_ABOVE:  # 70
        evidence = f"RSI(14) {rsi:.1f} — overbought (above {RSI_OVERBOUGHT_ABOVE:.0f})"
    else:
        evidence = f"RSI(14) {rsi:.1f} — neutral band"
    return sub_signal, weight, evidence, rsi
```

The 4-tuple variant `(sub_signal, weight, evidence, raw_value)` is recommended over the 3-tuple — `raw_value` populates the `indicators: dict[str, float | None]` field on PositionSignal without re-computing.

### Pattern 6: Confidence formula with abstain-rule for near-zero indicators

**What:** Confidence reflects indicator AGREEMENT, NOT magnitude. The formula:

```python
def _compute_confidence(
    sub_signals: list[tuple[float, float, str]],
    consensus_score: float,
    *,
    abstain_threshold: float = 0.01,
) -> int:
    """Confidence ∈ [0, 100] from indicator agreement count.

    Edge cases:
    - n_active < 2 → 0 (single-indicator agreement is meaningless)
    - Indicators with |sub_signal| < abstain_threshold (default 0.01) are
      ABSTAINING — they count toward n_active but NOT n_agreeing or n_disagreeing.
    - consensus_score with |x| < abstain_threshold → 0 (no consensus to agree
      with; would otherwise produce 100% agreement among abstainers).
    """
    n_active = len(sub_signals)
    if n_active < 2:
        return 0
    if abs(consensus_score) < abstain_threshold:
        return 0
    consensus_sign = 1.0 if consensus_score > 0 else -1.0
    n_agreeing = sum(
        1 for s, _, _ in sub_signals
        if abs(s) >= abstain_threshold and (s > 0) == (consensus_sign > 0)
    )
    return round(100 * n_agreeing / n_active)
```

**Why the abstain rule:**
- **Near-zero indicator behavior:** an RSI of 50 (sub-signal = 0.0) is genuinely indeterminate. Counting it as "agrees with bullish consensus" inflates confidence; counting it as "disagrees" deflates. Treating it as abstaining is the calibrated choice.
- **n_active < 2 cap:** if only 1 indicator was computable (small history), there's no consensus to score — emit confidence=0 with an explanatory evidence string ("only 1 indicator computable; consensus undefined"). This is a graceful-degradation case that downstream Phase 6 sort-by-confidence rendering needs to handle (those tickers go to the bottom).
- **`abstain_threshold = 0.01`:** small enough that real signals (e.g. RSI(14)=49 → sub-signal=-0.02) count as participating; large enough that float noise (1e-15-scale rounding) doesn't pollute. Tunable via constant.

**Example walkthrough:**
- 6 indicators all available, 4 oversold + 2 abstaining → consensus_score = -0.45 (strong oversold), n_active=6, n_agreeing=4 (the 2 abstainers excluded). confidence = round(100 * 4/6) = 67.
- 6 indicators all available, 5 oversold + 1 overbought (a divergence) → consensus_score = -0.30, n_active=6, n_agreeing=5. confidence = round(100 * 5/6) = 83.
- 3 indicators only (small history with Stochastic + Williams + RSI(14)), all oversold → consensus_score ≈ -0.5, n_active=3, n_agreeing=3. confidence = 100.
- 1 indicator only (very small history, only Stochastic %K computable) → confidence = 0 (n_active < 2 cap).
- 6 indicators, 3 oversold + 3 overbought (perfect divergence) → consensus_score ≈ 0.0 → confidence = 0 (abstain-threshold cap on consensus_score).

### Pattern 7: PositionSignal as PEER of AgentSignal, NOT subtype

**What:** PositionSignal is a separate Pydantic model — NOT a subclass of AgentSignal, NOT a Verdict-ladder analyst. CONTEXT.md locks this. Research confirms.

**Why:**
- **Field shapes diverge:** AgentSignal has `verdict: Verdict` (5-state directional ladder: strong_bullish..strong_bearish). PositionSignal has `state: PositionState` (5-state mean-reversion ladder: extreme_oversold..extreme_overbought). Forcing both into the same model would require a generic `state: str` field with a type discriminator — strictly worse than two clean models.
- **Action_hint is unique to PositionSignal.** AgentSignal doesn't have it; making it Optional on a shared base would dilute the contract.
- **Indicators dict is unique.** AgentSignal's `evidence: list[str]` carries everything; PositionSignal additionally has `indicators: dict[str, float | None]` for transparency / Phase 6 deep-dive.
- **trend_regime flag is unique.** Direct on PositionSignal; AgentSignal has no analog.
- **Phase 5 synthesizer benefits:** Phase 5 reads `[fundamentals_signal, technicals_signal, news_sentiment_signal, valuation_signal, position_signal]` as a list-of-mixed-types (4 AgentSignal + 1 PositionSignal). The synthesizer prompt template references each by NAME and FIELD; there's no place where "treat them all the same way" produces value. A shared base class would invite "let's add common methods" creep.
- **Phase 7 Decision-Support:** reads PositionSignal's `state` + `action_hint` + `confidence` directly; reads each AgentSignal's `verdict` + `confidence` + `evidence`. Different fields → different reads → no shared-base pull.

**Risks of NOT having a shared base:**
- ~30 LOC of duplicate validator code (ticker normalization, evidence cap). **Acceptable** — the validators are 5 lines each and the duplication makes each schema standalone-readable.
- **Mitigated by:** the duplicated validators are simple delegations to `analysts.schemas.normalize_ticker` and a stateless string-length check — trivial to keep in sync, and any drift would surface in tests immediately.

**Locked recommendation:** PEER, not subtype. Two clean Pydantic models. Cross-cutting test (`tests/analysts/test_invariants.py` has the precedent — Phase 3 added "always 4 AgentSignals" cross-cutting tests; Phase 4 should add an analog: "PositionSignal is always emitted alongside the 4 AgentSignals; data_unavailable=True snapshot → PositionSignal data_unavailable=True too").

### Anti-Patterns to Avoid

- **Importing `_adx_14` from `analysts.technicals`** (i.e. cross-module private import). **Use** `analysts._indicator_math` Wave 0 extraction. Keeps the technicals module's public surface clean (just `score()`) and the ADX function single-source.

- **Building a base class `BaseSignal(BaseModel)` for AgentSignal + PositionSignal to share.** Tempting; **rejected** per Pattern #7. The 30 LOC of validator duplication is cheaper than the dilution of contract.

- **Using `extra="allow"` on PositionSignal.** Locked to `extra="forbid"` per CONTEXT.md (matches AgentSignal). If a future analyst wants structured numbers, the right answer is a NEW field with explicit type.

- **Per-indicator helpers reading `datetime.now()`.** Compute `now` once at the top of `score()`; pass to helpers if needed (none of the 6 indicators currently need it — they're all timeless functions of OHLC history). Same Pitfall #7 discipline as Phase 3.

- **Building DataFrames inside the indicator loop.** Build `df = _build_df(history)` ONCE at the top of `score()`; pass to all 6 indicator helpers. Same Phase 3 pattern.

- **Mocking pandas operations in tests.** Pandas is fast and deterministic; mock-the-rolling-mean tests are pointless (the test would just assert the mock was called). Build synthetic OHLCBar lists, run real indicator math, assert on output. Phase 3 03-RESEARCH.md establishes this pattern.

- **Computing the indicator readings dict from the sub-signals.** The dict needs the RAW indicator value (RSI = 28.4, not the sub-signal -0.43). Indicator helpers MUST return both — see Pattern #5's 4-tuple variant.

- **Coupling `data_unavailable` invariant to caller convention.** Add the `@model_validator(mode="after")` on PositionSignal to enforce `data_unavailable=True ⟹ state="fair" AND consensus_score==0.0 AND confidence==0 AND action_hint=="hold_position"` at the schema layer. Same as Phase 3's AgentSignal invariant (locked in `analysts/signals.py:95-119`). See Pitfall #1.

- **Over-using the `evidence` list cap.** PositionSignal.evidence ≤ 10. Phase 4 emits at most 6 indicator-evidence strings + 1 ADX-regime string + 1 consensus-summary string = 8. Stay well within.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Wilder smoothing for RSI | Python loop with mutable accumulator | `pandas.Series.ewm(alpha=1/14, adjust=False).mean()` | Mathematical identity to Wilder's recursive formula (StockCharts canonical reference); pandas EMA is C-fast; avoids accumulator bugs. Locked by Phase 3 03-03's _adx_14 reuse. |
| Standard deviation for Bollinger Bands | Manual `sum((x - mean)**2 / N)**0.5` | `df["close"].rolling(20).std()` | Pandas C-extension; handles NaN propagation; identical idiom to the SMA call adjacent to it. |
| Z-score over rolling window | Manual `(x - mean) / std` with rolling tracking | `(close.iloc[-1] - close.rolling(50).mean().iloc[-1]) / close.rolling(50).std().iloc[-1]` | One pandas idiom; vectorized; single source of truth. |
| Percentage rank over trailing window (rejected for MACD; would have used `df["macd_hist"].rolling(60).rank(pct=True).iloc[-1]`) | Manual sort + index | (use z-score instead per CORRECTION #1) | We chose z-score over rank — but if rank were chosen, pandas' `.rolling().rank(pct=True)` would be the right tool. |
| EMA(12) and EMA(26) for MACD | Hand-rolled recursive smoothing | `df["close"].ewm(span=12, adjust=False).mean()` and `.ewm(span=26, adjust=False).mean()` | Standard pandas idiom; `span` parameter is the canonical MACD specification. |
| Pydantic ValidationError for evidence cap | Manual `if len(s) > 200: raise` outside the model | `@field_validator` + `Field(max_length=10)` (locked in CONTEXT.md schema) | Schema-as-source-of-truth. Same pattern as AgentSignal in Phase 3. |
| Verdict tiering helper | Inline 3-line if-elif chain in score() | `_total_to_verdict` extracted to `analysts/_indicator_math.py` (Wave 0) | DRY trigger fired (already 3 copies; 4th would be Phase 4). Single source of truth. |
| ADX(14) | Re-implement | Import from `analysts._indicator_math` (Wave 0) | Already shipped + tested in Phase 3 03-03; ~60 LOC of well-understood pandas math. |
| Linearization of bounded-range indicators | Conditional if-elif tiers | Single `clamp((x - midpoint) / half_range, -1, +1)` | RSI 0..100 with midpoint 50 → `(rsi - 50) / 50` clamped ±1. Williams %R -100..0 with midpoint -50 → `(w_r + 50) / 50` clamped ±1. Stochastic %K 0..100 with midpoint 50 (sign-flipped) → `(50 - stoch_k) / 50` clamped ±1. All same shape; ~3 LOC each. |

**Key insight:** Phase 4 deliberately avoids any TA-specific library. The 6 indicators are ~60 LOC of net-new pandas math (already shown in Pattern #1 + Code Examples below). Hand-rolling matches Phase 3 03-03's lock and unifies the codebase posture: every indicator's correctness is verifiable against StockCharts canonical references, no library version drift, no C-library posture.

## Common Pitfalls

### Pitfall 1: PositionSignal data_unavailable invariant drift
**What goes wrong:** Schema as locked in CONTEXT.md has `state: PositionState = "fair"` and `consensus_score: float = 0.0` defaults — they match the empty-data invariant. BUT if an analyst returns `PositionSignal(data_unavailable=True, state="extreme_oversold", consensus_score=-0.8, confidence=80, action_hint="consider_add", ...)` (i.e. populated despite no data), the schema accepts it. There is no model_validator enforcing the empty-data invariant.
**Why it happens:** The locked CONTEXT.md schema has no cross-field rule like "if data_unavailable then state='fair' AND consensus_score=0.0 AND confidence=0 AND action_hint='hold_position'". Easy to drift in implementation.
**How to avoid:**
1. **Plan-level convention:** every `score()` empty-data branch constructs PositionSignal with EXACTLY the four locked-CONTEXT.md defaults: `state="fair"` (omit, use default), `consensus_score=0.0` (omit), `confidence=0` (omit), `action_hint="hold_position"` (omit), `evidence=[reason]` (one string), `data_unavailable=True`, `trend_regime=False` (omit), `indicators={...all None values...}`.
2. **Add a `@model_validator(mode="after")` on PositionSignal** that asserts `data_unavailable=True ⟹ state=="fair" AND consensus_score==0.0 AND confidence==0 AND action_hint=="hold_position" AND trend_regime==False`. Same shape as Phase 3's AgentSignal invariant (`analysts/signals.py:95-119`). **Locked recommendation: include.** Three-line model validator, prevents a class of bugs, no schema-shape change.
3. **Test it:** `test_position_signal.py::test_data_unavailable_implies_fair_zero_invariants` enforces the contract. Same pattern as the AgentSignal `test_data_unavailable_invariant` in Phase 3.
**Warning signs:** A test passes `PositionSignal(data_unavailable=True, state="overbought", consensus_score=0.5)` and the schema accepts it.

### Pitfall 2: Trend-regime gating discontinuity at ADX=25
**What goes wrong:** A naive implementation `if adx > 25: weights = MEAN_REVERSION_DOWNWEIGHT_DICT else: weights = ALL_ONES_DICT` produces a discontinuity at the ADX=25 boundary — a ticker oscillating between ADX=24.5 and ADX=25.5 day-over-day flips its weights between full and half, jolting consensus_score by ~10-15%. CONTEXT.md addresses this by carving out an ambiguous zone (20-25) where all weights stay at 1.0; the discontinuity is now at ADX=25, but mean-reversion indicators only get downweighted ABOVE 25 — the boundary is one-sided, not bilateral. This is the right shape but worth documenting.
**Why it happens:** Hard-cutoff regime classifiers always have boundary discontinuities. The CONTEXT.md mitigation (ambiguous zone) is the standard fix. The remaining day-over-day jolt at ADX=25 exactly is acceptable in v1 — the alternative is a smooth interpolation (e.g. `weight = 1.0 - 0.5 * sigmoid((adx - 22.5) / 1.0)`) which adds complexity for marginal value.
**How to avoid:**
1. **Lock the ambiguous-zone behavior.** When `ADX <= 25`, all weights at 1.0. ONLY when `ADX > 25` do mean-reversion indicators downweight to 0.5. This matches Phase 3 technicals.py's `if adx_val > ADX_TREND_ABOVE:` boundary discipline (strict `>`, not `>=`).
2. **Document the discontinuity in the docstring.** A future maintainer wondering "why does this ticker flip-flop at ADX=25" should be able to read the answer in the source.
3. **Test it.** `test_position_adjustment.py::test_adx_24_no_downweight` and `test_adx_26_downweight_active` lock the boundary.
4. **v1.x ticket** for smooth-interpolation regime weighting if false-flapping at the boundary is an issue in production.
**Warning signs:** A ticker appears in the morning-scan POSE list one day and disappears the next day with no other input changes — check ADX values bracketing 25.

### Pitfall 3: MACD scale sensitivity across tickers
**What goes wrong:** Raw MACD histogram values scale with price level. A $900 stock (NVDA) might have MACD histogram of ±5; a $12 stock (F) might have ±0.05. Treating raw histogram values as comparable across tickers is a category error — the same nominal histogram value has wildly different significance.
**Why it happens:** MACD = EMA12(close) - EMA26(close), and signal_line = EMA9(MACD). Both terms scale with `close`. The histogram does too. Quant tools have known about this since the 1980s; the fix is normalization.
**How to avoid:**
1. **Z-score the MACD histogram over a trailing window of 60 bars.** Locked formula:
   ```python
   macd_line = ema12 - ema26
   signal_line = macd_line.ewm(span=9, adjust=False).mean()
   macd_hist = macd_line - signal_line
   # Z-score over trailing 60 bars:
   trailing_mean = macd_hist.rolling(60).mean().iloc[-1]
   trailing_std = macd_hist.rolling(60).std().iloc[-1]
   if trailing_std == 0 or pd.isna(trailing_std):
       return None  # or 0 — flat MACD region; can't z-score
   macd_z = (macd_hist.iloc[-1] - trailing_mean) / trailing_std
   sub_signal = max(-1.0, min(1.0, macd_z / 2.0))  # z=±2 → ±1
   ```
2. **Justify the 60-bar window in the docstring.** ≈ 3 months of trading days; long enough that one earnings cycle is in the window; short enough that the z-score is sensitive to the recent regime.
3. **Test cross-ticker comparability.** `test_position_adjustment.py::test_macd_scale_invariance` runs the analyst on `synthetic_overbought_history(start=10.0)` and `synthetic_overbought_history(start=1000.0)` and asserts `consensus_score` is within ±0.05 of itself — the absolute price level should not affect the verdict. The 100x scale difference is the test.
**Warning signs:** PositionSignal.indicators["macd_histogram"] absolute values vary wildly across tickers (e.g. AAPL macd=2.3, NVDA macd=8.7) but the `consensus_score` should NOT vary in lockstep.

### Pitfall 4: Confidence-vs-magnitude conflation (deliberate Phase 4 departure)
**What goes wrong:** Phase 3's AgentSignal `confidence = min(100, int(round(abs(normalized) * 100)))` mixes magnitude (how far from neutral) with directional consensus (whether the metrics agree). For a fundamentals analyst with 5 metrics where 3 are moderately bullish and 2 are mildly bearish, the aggregate is mildly bullish, the magnitude is small, and confidence ends up low — even though the indicators "agree" in some sense.

Phase 4 deliberately separates magnitude (carried by `consensus_score`) from confidence (carried by `confidence` = indicator agreement count). This is a design departure from Phase 3 — and a deliberate one — but a future contributor reading both modules might "fix" Phase 4 to match Phase 3's confidence formula, breaking the contract.
**Why it happens:** Pattern lock in Phase 3 sets the precedent. Phase 4's confidence semantics are different and need to be EXPLICITLY DOCUMENTED.
**How to avoid:**
1. **Lock the formula in Pattern #6 above.** `confidence = round(100 * (n_agreeing / n_active))` with abstain-rule edge cases.
2. **Document the departure in the docstring.** Specifically: "Phase 4 confidence is INDICATOR AGREEMENT (n_agreeing / n_active), distinct from AgentSignal's confidence which mixes magnitude with directional consensus. This is intentional. Phase 6 frontend renders BOTH `consensus_score` (signed magnitude) and `confidence` (agreement) — they're complementary, not redundant."
3. **Test the departure.** `test_position_adjustment.py::test_confidence_independent_of_magnitude` constructs a snapshot where consensus_score is small (e.g. -0.15) but all 6 indicators agree (n_agreeing=6, n_active=6) → confidence=100. Compare to Phase 3 fundamentals where the same magnitude would yield confidence=15. The two analysts have different confidence semantics — this test locks Phase 4's.
**Warning signs:** Confidence and consensus_score moving in lockstep across many tickers — that's the Phase 3 conflation pattern leaking back in.

### Pitfall 5: action_hint vs Phase 7 recommendation conflation
**What goes wrong:** A frontend developer building Phase 6 morning-scan view reads PositionSignal.action_hint and renders it as the user-facing "buy/sell/hold" recommendation. But action_hint is NOT the recommendation — it's a pre-recommendation hint that the Phase 7 synthesizer combines with persona signals + valuation + endorsements + thesis status to produce the final recommendation banner.
**Why it happens:** The string values look like recommendations ("consider_add", "consider_take_profits"). Without explicit boundary documentation, downstream code naturally treats them as final.
**How to avoid:**
1. **Crisply state the boundary in the docstring.** Quote: "action_hint is a PRE-RECOMMENDATION HINT computed from indicator state alone. It is NOT the final recommendation — Phase 7 Decision-Support synthesizes persona signals + valuation + endorsements + thesis status to produce the final recommendation banner. Phase 6 frontend rendering of POSE-lens action_hint is fine ('this ticker shows oversold consensus → consider_add'); rendering as a final user-facing buy/sell decision is wrong (Phase 7's job)."
2. **Reflect the boundary in the action_hint Literal.** All four values START with "consider_*" or end with "_position" — the wording alone signals "candidate", not "decision". `consider_add` (not `add` or `buy`); `consider_trim` / `consider_take_profits` (not `sell`); `hold_position` (not `hold`).
3. **Phase 6 frontend uses POSE state as the lens label, not the action.** Per VIEW-02 — the Position Adjustment lens shows `state` + `evidence` + `action_hint` together. The action_hint is a "what this lens suggests considering" prompt; the recommendation banner in Decision-Support (VIEW-10, Phase 7) is the actual call.
4. **Document in REQUIREMENTS.md** during planner roadmap-touch step: POSE-04's wording should clarify "action_hint is a pre-recommendation hint, not a final recommendation".
**Warning signs:** Phase 6 morning-scan UI mockups labeling the `action_hint` chip as "Recommendation" rather than "Hint" or "Suggested action".

### Pitfall 6: Determinism — `datetime.now()` reads in helper functions
**What goes wrong:** `score()` calls `datetime.now()` AND then internal helpers also call `datetime.now()` (e.g. for evidence-string formatting). Microsecond difference between the two times → snapshot-comparison tests flake.
**Why it happens:** Plausible refactor: an indicator helper computes "decay" or "recency" of an indicator reading. Currently NONE of the 6 indicators need `now` — they're timeless functions of OHLC history — but a future addition might.
**How to avoid:** **Read `datetime.now(timezone.utc)` exactly ONCE at the top of `score()`** — into local `now`, pass to helpers as a kwarg if needed. Same pattern as Phase 3 03-03 / 03-04 / 03-05 (locked by AST-walk test).
**Recommendation:** Phase 4 should ADD itself to the AST-walk test in 03-04 (`tests/analysts/test_invariants.py` likely has `test_no_datetime_now_in_helpers` or analog) — extend the test to include `analysts/position_adjustment.py`. Verify the test exists; if it doesn't, add one mirroring the Phase 3 pattern.
**Warning signs:** Tests asserting `signal.computed_at == fixture_dt` flake; tests using `freezegun` work but tests without it fail.

### Pitfall 7: Indicator warm-up NaN propagation (Phase 3 carry-forward)
**What goes wrong:** `df["close"].rolling(20).std().iloc[-1]` is `NaN` when `len(df) < 20` because the rolling window hasn't filled. Comparisons with NaN are `False` so no exception fires; sub-signal silently lands at 0 or worse, propagates into aggregation.
**Why it happens:** Same root as Phase 3 Pitfall #1. Each indicator helper MUST guard against insufficient bars BEFORE doing any pandas math.
**How to avoid:**
1. **Each indicator helper guards `len(df) < <min_bars>`** at the top:
   - RSI(14): `< 27`
   - Bollinger Bands(20): `< 20`
   - z-score-vs-MA50: `< 50`
   - Stochastic %K(14): `< 14`
   - Williams %R(14): `< 14`
   - MACD histogram (12/26/9 + 60-bar z-score): `< 94`
2. **When n < MIN_BARS_FOR_ANY_INDICATOR (14)**, return data_unavailable=True with the canonical evidence. Same as Phase 3 03-03 pattern.
3. **For each indicator, when `n` is below that indicator's threshold but ≥ MIN_BARS_FOR_ANY_INDICATOR**, the helper returns `(0.0, 0.0, None, None)` — zero weight, no evidence, None raw value. The aggregation skips it gracefully.
4. **`pd.isna()` checks on every `iloc[-1]`** to handle the flat-line corner case (e.g. `_rsi_14` where `loss.iloc[-1] == 0` → `rs = inf` → `rsi = 100` is correct; but `_bb_position` where `stdev20.iloc[-1] == 0` → divide-by-zero → NaN, return None).
**Warning signs:** Phase 3 03-RESEARCH.md Pitfall #1 already provides the canonical signs — verdict="fair" with confidence=0 for tickers that should clearly be over/oversold. Same diagnosis for Phase 4: NaN-leaking through to aggregation.

## Code Examples

Verified patterns from official sources + adapted to Phase 4 module structure.

### PositionSignal schema (with optional model_validator from Pitfall #1)

```python
# analysts/position_signal.py
"""PositionSignal — locked output schema for Phase 4 Position-Adjustment Radar.

Separate from AgentSignal because state ladder + action_hint + per-indicator
dict + trend_regime flag don't fit AgentSignal's verdict-ladder shape.
PEER-level, NOT subtype — see 04-RESEARCH.md Pattern #7.

Pydantic validators reuse:
  * ConfigDict(extra="forbid") — same discipline as AgentSignal.
  * Ticker normalization via analysts.schemas.normalize_ticker — same delegation
    pattern used in every analysts.data.* sub-schema.
  * Evidence cap (≤10 items, ≤200 chars each) — same as AgentSignal.
  * @model_validator(mode="after") enforces the data_unavailable=True invariant
    (state='fair' AND consensus_score=0.0 AND confidence=0 AND action_hint=
    'hold_position' AND trend_regime=False) — closes 04-RESEARCH.md Pitfall #1.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from analysts.schemas import normalize_ticker

PositionState = Literal[
    "extreme_oversold", "oversold", "fair", "overbought", "extreme_overbought"
]
ActionHint = Literal[
    "consider_add", "hold_position", "consider_trim", "consider_take_profits"
]


class PositionSignal(BaseModel):
    """Position-Adjustment Radar output — multi-indicator overbought/oversold consensus.

    Self-identifying — `ticker + computed_at` carry context so a serialized
    PositionSignal stands alone (mirrors AgentSignal). Phase 5 will JSON-
    serialize this alongside the four AgentSignals into
    data/YYYY-MM-DD/{ticker}.json.

    Defaults — state='fair', consensus_score=0.0, confidence=0,
    action_hint='hold_position', evidence=[], data_unavailable=False,
    trend_regime=False — match the canonical 'no opinion' shape an analyst
    emits when its inputs are present but truly inconclusive (state='fair'
    with non-zero confidence is meaningful: "we computed 6 indicators, they
    don't agree, leaning neither way").
    """

    model_config = ConfigDict(extra="forbid")

    ticker: str
    computed_at: datetime
    state: PositionState = "fair"
    consensus_score: float = Field(ge=-1.0, le=1.0, default=0.0)
    confidence: int = Field(ge=0, le=100, default=0)
    action_hint: ActionHint = "hold_position"
    indicators: dict[str, float | None] = Field(default_factory=dict)
    evidence: list[str] = Field(default_factory=list, max_length=10)
    data_unavailable: bool = False
    trend_regime: bool = False

    @field_validator("ticker", mode="before")
    @classmethod
    def _normalize_ticker_field(cls, v: object) -> str:
        norm = normalize_ticker(v) if isinstance(v, str) else None
        if norm is None:
            raise ValueError(f"invalid ticker {v!r}")
        return norm

    @field_validator("evidence")
    @classmethod
    def _evidence_strings_capped(cls, v: list[str]) -> list[str]:
        for s in v:
            if len(s) > 200:
                raise ValueError(
                    f"evidence string exceeds 200 chars (got {len(s)}): {s[:60]!r}..."
                )
        return v

    @model_validator(mode="after")
    def _data_unavailable_implies_fair_zero(self) -> "PositionSignal":
        """Schema-level invariant: data_unavailable=True ⟹ canonical no-opinion shape.

        Closes Pitfall #1 from 04-RESEARCH.md. Same pattern as AgentSignal's
        Phase 3 invariant (analysts/signals.py:_data_unavailable_implies_neutral_zero).
        """
        if self.data_unavailable:
            problems: list[str] = []
            if self.state != "fair":
                problems.append(f"state={self.state!r} (expected 'fair')")
            if self.consensus_score != 0.0:
                problems.append(f"consensus_score={self.consensus_score} (expected 0.0)")
            if self.confidence != 0:
                problems.append(f"confidence={self.confidence} (expected 0)")
            if self.action_hint != "hold_position":
                problems.append(f"action_hint={self.action_hint!r} (expected 'hold_position')")
            if self.trend_regime is not False:
                problems.append(f"trend_regime={self.trend_regime!r} (expected False)")
            if problems:
                raise ValueError(
                    f"data_unavailable=True invariant violated: {', '.join(problems)}"
                )
        return self
```

### RSI(14) helper (~10 LOC)

```python
# In analysts/position_adjustment.py
def _rsi_14(df: pd.DataFrame) -> Optional[float]:
    """Wilder RSI(14). Returns None below RSI_MIN_BARS (=27) or NaN result.

    Source: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/relative-strength-index-rsi
    """
    if len(df) < RSI_MIN_BARS:  # 27 = 2*N - 1
        return None
    delta = df["close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1.0 / RSI_PERIOD, adjust=False).mean()
    loss = (-delta).clip(lower=0).ewm(alpha=1.0 / RSI_PERIOD, adjust=False).mean()
    g, l = gain.iloc[-1], loss.iloc[-1]
    if pd.isna(g) or pd.isna(l):
        return None
    if l == 0.0:
        return 100.0  # all gains, no losses — RSI saturates to 100
    rs = g / l
    return float(100.0 - (100.0 / (1.0 + rs)))
```

### Bollinger Bands position helper (~7 LOC)

```python
def _bollinger_position(df: pd.DataFrame) -> Optional[float]:
    """Bollinger position: (close - SMA20) / (2 * stdev20) — units of stdev/2.

    Returns None below 20 bars or when stdev20 == 0 (flat-line).
    Range: typically [-1.5, +1.5]; ±1.0 maps to band edges (canonical).
    """
    if len(df) < BB_BARS:  # 20
        return None
    sma = df["close"].rolling(BB_BARS).mean().iloc[-1]
    std = df["close"].rolling(BB_BARS).std().iloc[-1]
    close = df["close"].iloc[-1]
    if pd.isna(sma) or pd.isna(std) or std == 0.0:
        return None
    return float((close - sma) / (2.0 * std))
```

**Note on canonical %B vs CONTEXT.md formula:** StockCharts canonical "%B" is `(close - lower_band) / (upper_band - lower_band)` which produces 0 at lower band, 0.5 at SMA, 1.0 at upper band. CONTEXT.md uses `(close - SMA20) / (2 * stdev20)` which produces 0 at SMA, ±1.0 at band edges. The two forms differ by an affine transform (CONTEXT.md_form = 2 * canonical_%B - 1). CONTEXT.md's form is the right choice for our consensus aggregation because it's signed and centered at 0 (matches the [-1, +1] sub-signal contract).

### z-score vs 50-day MA helper (~6 LOC)

```python
def _zscore_vs_ma50(df: pd.DataFrame) -> Optional[float]:
    """Z-score: (close - SMA50) / stdev50. Returns None below 50 bars or stdev=0."""
    if len(df) < ZSCORE_BARS:  # 50
        return None
    sma = df["close"].rolling(ZSCORE_BARS).mean().iloc[-1]
    std = df["close"].rolling(ZSCORE_BARS).std().iloc[-1]
    close = df["close"].iloc[-1]
    if pd.isna(sma) or pd.isna(std) or std == 0.0:
        return None
    return float((close - sma) / std)
```

### Stochastic %K helper (~6 LOC)

```python
def _stoch_k_14(df: pd.DataFrame) -> Optional[float]:
    """Stochastic %K(14): 100 * (close - low_14) / (high_14 - low_14). Range [0, 100].

    Source: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/stochastic-oscillator-fast-slow-and-full
    """
    if len(df) < STOCH_BARS:  # 14
        return None
    low_14 = df["low"].rolling(STOCH_BARS).min().iloc[-1]
    high_14 = df["high"].rolling(STOCH_BARS).max().iloc[-1]
    close = df["close"].iloc[-1]
    if pd.isna(low_14) or pd.isna(high_14) or high_14 == low_14:
        return None
    return float(100.0 * (close - low_14) / (high_14 - low_14))
```

### Williams %R helper (~6 LOC)

```python
def _williams_r_14(df: pd.DataFrame) -> Optional[float]:
    """Williams %R(14): -100 * (high_14 - close) / (high_14 - low_14). Range [-100, 0].

    Source: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/williams-r
    Williams %R is the signed inverse of Stochastic %K — same formula minus the
    sign flip and additive 100 shift.
    """
    if len(df) < WILLIAMS_BARS:  # 14
        return None
    low_14 = df["low"].rolling(WILLIAMS_BARS).min().iloc[-1]
    high_14 = df["high"].rolling(WILLIAMS_BARS).max().iloc[-1]
    close = df["close"].iloc[-1]
    if pd.isna(low_14) or pd.isna(high_14) or high_14 == low_14:
        return None
    return float(-100.0 * (high_14 - close) / (high_14 - low_14))
```

### MACD histogram with z-score normalization (~14 LOC)

```python
def _macd_histogram_zscore(df: pd.DataFrame) -> Optional[float]:
    """MACD histogram z-scored over trailing 60 bars.

    MACD = EMA12(close) - EMA26(close)
    signal = EMA9(MACD)
    histogram = MACD - signal
    z = (histogram[-1] - mean(histogram[-60:])) / std(histogram[-60:])

    Returns the z-score; clip+linearize to [-1, +1] happens in the sub-signal mapper.
    Returns None below MACD_MIN_BARS (94 = 26 + 9 + 60) or stdev=0.
    """
    if len(df) < MACD_MIN_BARS:  # 94
        return None
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    trailing_mean = histogram.rolling(MACD_HISTOGRAM_ZSCORE_BARS).mean().iloc[-1]
    trailing_std = histogram.rolling(MACD_HISTOGRAM_ZSCORE_BARS).std().iloc[-1]
    h = histogram.iloc[-1]
    if pd.isna(trailing_mean) or pd.isna(trailing_std) or trailing_std == 0.0:
        return None
    return float((h - trailing_mean) / trailing_std)
```

### Sub-signal linearization helpers (~3 LOC each)

```python
def _rsi_to_subsignal(rsi: float) -> float:
    """RSI ∈ [0, 100] → sub-signal ∈ [-1, +1]. RSI=50 maps to 0; RSI=0 to -1; RSI=100 to +1."""
    return max(-1.0, min(1.0, (rsi - 50.0) / 50.0))


def _bb_to_subsignal(bb: float) -> float:
    """BB position (already in stdev/2 units) → sub-signal ∈ [-1, +1]."""
    return max(-1.0, min(1.0, bb))


def _zscore_to_subsignal(z: float) -> float:
    """Z-score → sub-signal ∈ [-1, +1]. z=±2 maps to ±1."""
    return max(-1.0, min(1.0, z / 2.0))


def _stoch_to_subsignal(stoch_k: float) -> float:
    """Stochastic %K ∈ [0, 100] → sub-signal ∈ [-1, +1]. SIGN-FLIPPED: low %K = oversold = -1."""
    return max(-1.0, min(1.0, (50.0 - stoch_k) / 50.0))


def _williams_to_subsignal(w_r: float) -> float:
    """Williams %R ∈ [-100, 0] → sub-signal ∈ [-1, +1]. SIGN-FLIPPED: low %R = oversold = -1."""
    return max(-1.0, min(1.0, (w_r + 50.0) / 50.0))


def _macd_z_to_subsignal(macd_z: float) -> float:
    """MACD z-score → sub-signal ∈ [-1, +1]. z=±2 maps to ±1."""
    return max(-1.0, min(1.0, macd_z / 2.0))
```

### `_consensus_to_state` helper (verbatim from CONTEXT.md)

```python
def _consensus_to_state(score: float) -> PositionState:
    """Strict > / < boundaries — score=0.6 maps to 'overbought' (not 'extreme_overbought')."""
    if score < -0.6:
        return "extreme_oversold"
    if score < -0.2:
        return "oversold"
    if score > 0.6:
        return "extreme_overbought"
    if score > 0.2:
        return "overbought"
    return "fair"
```

### `_state_to_action_hint` helper (verbatim from CONTEXT.md)

```python
_STATE_TO_HINT: dict[PositionState, ActionHint] = {
    "extreme_oversold": "consider_add",
    "oversold": "consider_add",
    "fair": "hold_position",
    "overbought": "consider_trim",
    "extreme_overbought": "consider_take_profits",
}


def _state_to_action_hint(state: PositionState) -> ActionHint:
    return _STATE_TO_HINT[state]
```

### score() orchestration skeleton

```python
def score(
    snapshot: Snapshot,
    config: TickerConfig,
    *,
    computed_at: Optional[datetime] = None,
) -> PositionSignal:
    """Compute Position-Adjustment Radar; pure function; never raises for missing data.

    Returns
    -------
    PositionSignal
        Always non-None; ticker + computed_at always set. Empty / partial /
        short history produces the canonical data_unavailable=True signal.
    """
    now = computed_at if computed_at is not None else datetime.now(timezone.utc)
    ticker = snapshot.ticker

    # UNIFORM RULE 4-branch empty-data guard.
    if snapshot.data_unavailable:
        return PositionSignal(
            ticker=ticker, computed_at=now, data_unavailable=True,
            evidence=["snapshot data_unavailable=True"],
            indicators=_indicators_all_none(),
        )
    if snapshot.prices is None:
        return PositionSignal(
            ticker=ticker, computed_at=now, data_unavailable=True,
            evidence=["prices snapshot missing"],
            indicators=_indicators_all_none(),
        )
    if snapshot.prices.data_unavailable:
        return PositionSignal(
            ticker=ticker, computed_at=now, data_unavailable=True,
            evidence=["prices.data_unavailable=True"],
            indicators=_indicators_all_none(),
        )
    if not snapshot.prices.history:
        return PositionSignal(
            ticker=ticker, computed_at=now, data_unavailable=True,
            evidence=["prices history is empty"],
            indicators=_indicators_all_none(),
        )

    df = _build_df(snapshot.prices.history)  # imported from analysts._indicator_math
    n = len(df)
    if n < MIN_BARS_FOR_ANY_INDICATOR:  # 14
        return PositionSignal(
            ticker=ticker, computed_at=now, data_unavailable=True,
            evidence=[f"history has {n} bars; need ≥{MIN_BARS_FOR_ANY_INDICATOR} for any indicator"],
            indicators=_indicators_all_none(),
        )

    # Compute ADX(14) for trend-regime gating.
    adx_value = _adx_14(df)  # imported from analysts._indicator_math; returns Optional[float]
    trend_regime = adx_value is not None and adx_value > ADX_TREND_ABOVE  # 25

    # Per-indicator weights (regime-conditional).
    if trend_regime:
        weights = {
            "rsi_14": TREND_REGIME_DOWNWEIGHT, "bb_position": TREND_REGIME_DOWNWEIGHT,
            "stoch_k": TREND_REGIME_DOWNWEIGHT, "williams_r": TREND_REGIME_DOWNWEIGHT,
            "zscore_50": 1.0, "macd_histogram": 1.0,
        }
    else:
        weights = {k: 1.0 for k in ("rsi_14", "bb_position", "stoch_k", "williams_r", "zscore_50", "macd_histogram")}

    # Per-indicator helpers (each returns (sub_signal, weight, evidence, raw_value)
    # or (0.0, 0.0, None, None) when not yet computable).
    sub_signals: list[tuple[float, float, str]] = []
    indicators: dict[str, float | None] = {}

    for key, helper, sub_mapper in (
        ("rsi_14",        _rsi_14,                 _rsi_to_subsignal),
        ("bb_position",   _bollinger_position,     _bb_to_subsignal),
        ("zscore_50",     _zscore_vs_ma50,         _zscore_to_subsignal),
        ("stoch_k",       _stoch_k_14,             _stoch_to_subsignal),
        ("williams_r",    _williams_r_14,          _williams_to_subsignal),
        ("macd_histogram", _macd_histogram_zscore, _macd_z_to_subsignal),
    ):
        raw = helper(df)
        indicators[key] = raw
        if raw is None:
            continue
        sub_signal = sub_mapper(raw)
        evidence_str = _format_evidence(key, raw, sub_signal)
        sub_signals.append((sub_signal, weights[key], evidence_str))

    indicators["adx_14"] = adx_value

    # All 6 indicators short-warmup-skipped → emit data_unavailable=True with
    # explanatory evidence. (Reaches here only if 14 ≤ n < 14 — impossible —
    # OR if n ≥ 14 but every indicator returns None for some reason — defensive.)
    if not sub_signals:
        return PositionSignal(
            ticker=ticker, computed_at=now, data_unavailable=True,
            evidence=[f"history has {n} bars but no indicator was computable"],
            indicators=indicators,
        )

    total_w = sum(w for _, w, _ in sub_signals)
    consensus_score = sum(s * w for s, w, _ in sub_signals) / total_w
    consensus_score = max(-1.0, min(1.0, consensus_score))  # defensive clamp

    state = _consensus_to_state(consensus_score)
    action_hint = _state_to_action_hint(state)
    confidence = _compute_confidence(sub_signals, consensus_score)

    # Evidence assembly: per-indicator strings + ADX regime + summary.
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
    evidence.append(
        f"{n_agreeing} of {n_active} indicators agree ({state.replace('_', ' ')} consensus)"
        + ("; ADX trend regime active" if trend_regime else "")
    )
    evidence = evidence[:10]  # cap

    return PositionSignal(
        ticker=ticker, computed_at=now,
        state=state, consensus_score=consensus_score, confidence=confidence,
        action_hint=action_hint, indicators=indicators, evidence=evidence,
        trend_regime=trend_regime,
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-indicator overbought/oversold (e.g. "RSI < 30 = buy") | Multi-indicator consensus with regime gating | 2010s onward — academic + practitioner consensus | Multi-indicator approach reduces false-positive rate; ADX-gating addresses the well-known RSI-stays-oversold-in-trends problem (Schwab, Wikipedia, Lux Algo all cite this). |
| Raw MACD histogram cross-ticker comparison | Z-score normalized MACD histogram | TradingView indicator developer convention since ~2018 | Cross-ticker comparability — a bullish MACD reading on a $10 stock is comparable to a bullish reading on a $1000 stock. (TradingView "Institutional MACD (Z-Score Edition)" + ProRealCode published examples.) |
| Step-function regime classifier (ADX > 25 → fully trend; ADX < 25 → fully range) | Three-zone regime: trend (>25) / ambiguous (20-25) / range (<20) | Practitioner refinement | Avoids day-over-day regime flapping at the boundary; matches Phase 3 technicals.py's locked thresholds. |
| 3-state directional verdict (bullish/bearish/neutral) | 5-state directional + 5-state mean-reversion ladders | Project's CONTEXT.md decision (Phase 3 + Phase 4) | Captures magnitude useful for Phase 5 dissent calc (LLM-07 ≥30 confidence delta) and Phase 6 conviction-band rendering. |
| Hand-rolled or ta-lib for indicator math | pandas-native (`rolling`, `ewm`) — no TA library | Pandas EWM matures (~2018+) | Eliminates ta-lib system-dependency posture; sufficient for our 6 indicators. ta-lib only wins at 100+ indicator scale. |

**Deprecated/outdated:**
- Original pandas-ta: maintenance status flagged inactive — pandas-ta-classic (MIT, active fork) is the current community option if a TA library is needed. We chose hand-rolled instead.
- ta-lib pre-0.6.5: required manual C-library compilation. As of 2026 (cgohlke wheels, official PyPI wheels since Oct 2025), this is solved — but the system-level dep posture remains.
- "RSI < 30 = buy" naive interpretation: known-broken in trending markets; modern practice combines RSI with ADX or MA filters (or, like us, downweights it during ADX-confirmed trends).

## Open Questions

1. **Optional `@model_validator` on PositionSignal enforcing data_unavailable invariant?**
   - What we know: CONTEXT.md schema doesn't lock this validator; Pitfall #1 shows the invariant CAN drift; Phase 3's analog AgentSignal validator is shipped and tested.
   - What's unclear: whether the planner views the validator as scope creep.
   - Recommendation: **include it.** Same shape as the AgentSignal validator (~15 line model_validator); prevents a class of bugs at zero schema-shape change; mirrors Phase 3 precedent. Plan-Check can flag if the user objects.

2. **`_indicator_math.py` extraction in Wave 0 vs deferred to a follow-up plan?**
   - What we know: 4th copy of `_total_to_verdict` and 2nd copy of `_build_df` triggers DRY by project conventions; the refactor is mechanical (line-equivalent move) and Phase 3 tests stay green.
   - What's unclear: whether the planner views Wave 0 as "blocking" (Phase 4 Wave 1 imports the helpers) or "parallel" (Wave 1 could co-define them and refactor later).
   - Recommendation: **Wave 0 blocking.** Doing the refactor up-front is cheaper than doing it AFTER Phase 4 ships (when you'd have FOUR copies of `_total_to_verdict` to consolidate). Wave 0 is ~1 hour of work + zero behavior change. Plan should make Wave 1 explicitly depend on Wave 0.

3. **MACD histogram z-score window: 60 bars vs other?**
   - What we know: 60 bars ≈ 3 months of trading days; matches the z-score-vs-MA50 horizon for the parallel z-score indicator; long enough to span an earnings cycle, short enough to be sensitive to recent regime.
   - What's unclear: whether 60 is empirically the best choice. Alternatives: 90 bars (quarterly cycle including post-earnings drift); 30 bars (more sensitive); 252 bars (full year).
   - Recommendation: **lock 60 bars in v1.** The constant `MACD_HISTOGRAM_ZSCORE_BARS` is at the top of `analysts/position_adjustment.py` — tunable by editing the file and re-running tests. v1.x ticket if 60 turns out to over-/under-react.

4. **Add `synthetic_oversold_history` / `synthetic_overbought_history` to conftest.py vs Phase 4 test-file local helpers?**
   - What we know: Phase 3 conftest.py is the established home for shared synthetic builders (`synthetic_uptrend_history` etc.). Phase 5 / Phase 6 may eventually consume these fixtures.
   - What's unclear: whether conftest.py is the right home for fixtures specifically about overbought/oversold (a Phase-4-specific concept).
   - Recommendation: **conftest.py.** Phase 4 test files reuse Phase 3 fixtures; Phase 4 fixtures should live in the same place for symmetry. Future phases that test against extreme-regime histories (Phase 5 routine integration tests, Phase 6 frontend integration tests) get them for free.

5. **`PositionSignal` filename — `analysts/position_signal.py` vs co-located in `analysts/position_adjustment.py`?**
   - What we know: Phase 3 separated `analysts/signals.py` from the analyst modules. Phase 5/6/7 will import the schema; they shouldn't pay the indicator-math import cost.
   - What's unclear: whether splitting is overkill for a single schema file.
   - Recommendation: **separate file (`analysts/position_signal.py`).** Mirrors Phase 3's analysts/signals.py separation; lets Phase 6 frontend mocking import only the schema; keeps each file <100 LOC.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-cov 7.1.0 (already pinned in `[dependency-groups].dev`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]`, `addopts = "-ra --strict-markers"` |
| Quick run command | `uv run pytest tests/analysts -x` |
| Full suite command | `uv run pytest --cov` |
| Coverage gate (per project precedent) | ≥90% line / ≥85% branch on `analysts/{position_signal,position_adjustment,_indicator_math}.py` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| POSE-01 (RSI happy) | RSI(14)=22 on synthetic_oversold_history → sub_signal ≈ -0.56; oversold evidence present | unit | `pytest tests/analysts/test_position_adjustment.py::test_rsi_oversold -x` | Wave 2 |
| POSE-01 (RSI overbought) | RSI(14)=78 on synthetic_overbought_history → sub_signal ≈ +0.56; overbought evidence | unit | `pytest tests/analysts/test_position_adjustment.py::test_rsi_overbought -x` | Wave 2 |
| POSE-01 (BB position) | BB position < -1 on extreme oversold; > +1 on extreme overbought | unit | `pytest tests/analysts/test_position_adjustment.py::test_bb_position_extremes -x` | Wave 2 |
| POSE-01 (z-score-vs-MA50) | z-score < -1.5 on extreme oversold; > +1.5 on extreme overbought | unit | `pytest tests/analysts/test_position_adjustment.py::test_zscore_extremes -x` | Wave 2 |
| POSE-01 (Stochastic %K) | %K < 20 oversold; > 80 overbought | unit | `pytest tests/analysts/test_position_adjustment.py::test_stoch_k_extremes -x` | Wave 2 |
| POSE-01 (Williams %R) | %R < -80 oversold; > -20 overbought | unit | `pytest tests/analysts/test_position_adjustment.py::test_williams_r_extremes -x` | Wave 2 |
| POSE-01 (MACD histogram z-score) | MACD histogram z-score signed correctly + cross-ticker invariance | unit | `pytest tests/analysts/test_position_adjustment.py::test_macd_zscore_signed -x` AND `test_macd_scale_invariance -x` | Wave 2 |
| POSE-02 (5-state ladder) | consensus_score=-0.7 → state="extreme_oversold"; -0.4 → "oversold"; 0.0 → "fair"; 0.4 → "overbought"; 0.7 → "extreme_overbought" | unit | `pytest tests/analysts/test_position_adjustment.py::test_state_ladder -x` | Wave 2 |
| POSE-02 (state boundary discipline) | consensus_score=0.6 → "overbought" (NOT "extreme_overbought"; strict > boundary) | unit | `pytest tests/analysts/test_position_adjustment.py::test_state_boundary_strict -x` | Wave 2 |
| POSE-02 (consensus_score range) | consensus_score always ∈ [-1, +1] (defensive clamp) | unit | `pytest tests/analysts/test_position_adjustment.py::test_consensus_score_clamped -x` | Wave 2 |
| POSE-02 (confidence formula) | 6 indicators all agree → confidence=100; 4-of-6 agree → confidence=67; 2-of-6 agree → confidence=33 | unit | `pytest tests/analysts/test_position_adjustment.py::test_confidence_agreement_count -x` | Wave 2 |
| POSE-02 (confidence near-zero abstain) | indicator with sub-signal=0.0 doesn't count as agreeing | unit | `pytest tests/analysts/test_position_adjustment.py::test_confidence_abstain_rule -x` | Wave 2 |
| POSE-02 (confidence n_active < 2 cap) | only 1 indicator computable → confidence=0 | unit | `pytest tests/analysts/test_position_adjustment.py::test_confidence_single_indicator_zero -x` | Wave 2 |
| POSE-03 (ADX trend regime gating) | ADX=31 + 4 mean-reversion oversold + 0 trend-following → consensus_score weaker than ADX=15 case (because mean-reversion downweighted) | unit | `pytest tests/analysts/test_position_adjustment.py::test_adx_trend_downweights_mean_reversion -x` | Wave 2 |
| POSE-03 (ADX boundary at 25) | ADX=24.99 → trend_regime=False, all weights 1.0; ADX=25.01 → trend_regime=True, mean-rev downweighted | unit | `pytest tests/analysts/test_position_adjustment.py::test_adx_boundary_25 -x` | Wave 2 |
| POSE-03 (ADX ambiguous zone 20-25) | ADX=22 → trend_regime=False (no downweight); evidence string says "ambiguous regime" | unit | `pytest tests/analysts/test_position_adjustment.py::test_adx_ambiguous_zone -x` | Wave 2 |
| POSE-03 (ADX warm-up skip) | <27 bars → ADX=None; trend_regime=False; no downweight applied | unit | `pytest tests/analysts/test_position_adjustment.py::test_adx_warmup_no_gating -x` | Wave 2 |
| POSE-04 (action_hint mapping) | state=extreme_oversold → consider_add; oversold → consider_add; fair → hold_position; overbought → consider_trim; extreme_overbought → consider_take_profits | unit | `pytest tests/analysts/test_position_adjustment.py::test_state_to_action_hint_mapping -x` | Wave 2 |
| POSE-05 (regression: known oversold) | synthetic_oversold_history → state ∈ {oversold, extreme_oversold}; consensus_score < -0.2; action_hint == "consider_add" | unit | `pytest tests/analysts/test_position_adjustment.py::test_known_oversold_regression -x` | Wave 2 |
| POSE-05 (regression: known overbought) | synthetic_overbought_history → state ∈ {overbought, extreme_overbought}; consensus_score > +0.2; action_hint ∈ {consider_trim, consider_take_profits} | unit | `pytest tests/analysts/test_position_adjustment.py::test_known_overbought_regression -x` | Wave 2 |
| POSE-05 (regression: sideways) | synthetic_sideways_history → state="fair"; \|consensus_score\| < 0.3; action_hint=="hold_position" | unit | `pytest tests/analysts/test_position_adjustment.py::test_known_sideways_fair -x` | Wave 2 |
| Empty-data UNIFORM RULE (4 branches + 5th min-bars degenerate) | Each empty-data branch produces canonical no-opinion PositionSignal with distinct evidence | unit | `pytest tests/analysts/test_position_adjustment.py -k empty_data -x` | Wave 2 |
| Warm-up tiers | <14 bars → data_unavailable; 14-19 bars → only Stochastic + Williams; 20-26 → +BB; 27-49 → +RSI+ADX; 50-93 → +zscore; ≥94 → all 6 | unit | `pytest tests/analysts/test_position_adjustment.py::test_warmup_tiers -x` | Wave 2 |
| Determinism + computed_at | two calls with identical inputs → byte-identical PositionSignal model_dump_json | unit | `pytest tests/analysts/test_position_adjustment.py::test_deterministic -x` | Wave 2 |
| Provenance header (INFRA-07) | `virattt/ai-hedge-fund/src/agents/risk_manager.py` referenced in source | unit | `pytest tests/analysts/test_position_adjustment.py::test_provenance_header -x` | Wave 2 |
| No forbidden imports | NO `import pandas_ta`, `import talib`, `import ta_lib` | unit | `pytest tests/analysts/test_position_adjustment.py::test_no_ta_library_imports -x` | Wave 2 |
| Cross-cutting: PositionSignal alongside 4 AgentSignals | Phase 4 dark-snapshot test: snapshot.data_unavailable=True → PositionSignal.data_unavailable=True too (analog of AgentSignal cross-cutting test in test_invariants.py) | unit | `pytest tests/analysts/test_invariants.py::test_dark_snapshot_emits_pose_unavailable -x` | Wave 2 |
| PositionSignal schema (extra=forbid) | Unknown field rejected; evidence > 200 chars rejected; ≥ 11 evidence items rejected; consensus_score range -1 to +1 enforced; confidence range 0-100 enforced; ticker normalized | unit | `pytest tests/analysts/test_position_signal.py -x` | Wave 1 |
| PositionSignal data_unavailable invariant | data_unavailable=True with state='oversold' → ValidationError | unit | `pytest tests/analysts/test_position_signal.py::test_data_unavailable_invariant -x` | Wave 1 |
| PositionSignal round-trip | model_dump_json → json.loads → model_validate_json yields equal object | unit | `pytest tests/analysts/test_position_signal.py::test_json_round_trip -x` | Wave 1 |
| _indicator_math (extracted helpers) | _build_df sorts unsorted history; _adx_14 returns None < 27 bars; _total_to_verdict strict-> boundaries match Phase 3 | unit | `pytest tests/analysts/test_indicator_math.py -x` | Wave 0 |
| Phase 3 technicals tests still green after Wave 0 refactor | All 25 existing technicals tests pass after _build_df / _adx_14 / _total_to_verdict are imported from _indicator_math | unit | `pytest tests/analysts/test_technicals.py -x` | Wave 0 (regression) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/analysts -x` (target: < 5 sec for all analyst test files)
- **Per wave merge:** `uv run pytest --cov` (full repo suite + coverage gate ≥ 90%)
- **Phase gate:** Full suite green AND coverage ≥ 90% line / ≥ 85% branch on each new module before `/gmd:verify-work`

### Wave 0 Gaps

- [ ] **Refactor task:** Create `analysts/_indicator_math.py` with `_build_df` + `_adx_14` + `_total_to_verdict` extracted verbatim from `analysts/technicals.py`. Update `analysts/technicals.py` to import them. Verify Phase 3 technicals tests stay GREEN. (~80 LOC moved; zero behavior change.)
- [ ] **Test task:** Create `tests/analysts/test_indicator_math.py` with ~6 tests covering the 3 extracted helpers (smoke + ADX warm-up + verdict tiering boundaries).
- [ ] **Fixture task:** Append `synthetic_oversold_history`, `synthetic_overbought_history`, `synthetic_mean_reverting_history` builders to `tests/analysts/conftest.py` (~50 LOC). Fixtures must be deterministic (no random sources; same `(i % 5) - 2` noise pattern as Phase 3).
- [ ] **AST-walk extension:** If `tests/analysts/test_invariants.py` has a Pitfall #7 / determinism test that scans the analyst modules for forbidden `datetime.now()` calls in helpers, extend the file list to include `analysts/position_adjustment.py` once it exists. (Verify whether such a test exists; if not, this is a "nice to have" not a Wave 0 blocker.)

*(If no other Wave 0 gaps surface during planning: the above 4 are sufficient.)*

## Recommended Wave Structure

**Three waves. Wave 0 is the refactor + fixtures. Wave 1 is the schema. Wave 2 is the analyst.**

### Wave 0: Foundation (refactor + fixtures)

**Estimated effort:** 1 hour active execution. **Risk:** LOW (mechanical move; existing tests guard against regression).

**Plan name suggestion:** `04-01-foundation-PLAN.md`

**Tasks:**
1. **Extract `_build_df` + `_adx_14` + `_total_to_verdict` to `analysts/_indicator_math.py`.** Verbatim move; update `analysts/technicals.py` imports. Verify all 25 existing technicals tests stay GREEN.
2. **Add `tests/analysts/test_indicator_math.py`** with ~6 tests covering the 3 extracted helpers.
3. **Append `synthetic_oversold_history` / `synthetic_overbought_history` / `synthetic_mean_reverting_history` to `tests/analysts/conftest.py`.** Each fixture is deterministic (no randomness; same noise pattern as Phase 3 builders). Add ~3 round-trip tests in `tests/analysts/conftest_test.py` (or `tests/analysts/test_synthetic_fixtures.py`) verifying the new fixtures produce expected indicator readings (RSI < 30 on synthetic_oversold; RSI > 70 on synthetic_overbought; etc.).

**Wave 0 closeout criteria:**
- `pytest tests/analysts -v` passes (existing 25 technicals + 4 fundamentals + N news_sentiment + N valuation + 2 invariants + 6 _indicator_math + 3 fixture-roundtrip tests = ~50+ tests).
- Coverage on `analysts/_indicator_math.py` ≥ 90%/85%.
- No behavior change in `analysts/technicals.py` or `analysts/fundamentals.py` (the latter still inlines `_total_to_verdict` until WAVE 0 chooses to refactor — recommend keeping `analysts/fundamentals.py` and `analysts/valuation.py` import from `_indicator_math` too for full DRY).

### Wave 1: PositionSignal schema

**Estimated effort:** 1-2 hours active execution. **Risk:** LOW (schema-heavy; no math).

**Plan name suggestion:** `04-02-position-signal-PLAN.md`

**Tasks:**
1. **Create `analysts/position_signal.py`** with `PositionSignal` + `PositionState` Literal + `ActionHint` Literal + the optional `@model_validator(mode="after")` for the data_unavailable invariant (Pitfall #1).
2. **Create `tests/analysts/test_position_signal.py`** with ~10-12 tests covering:
   - Schema validation (`extra="forbid"` rejects unknown field; ticker normalization; evidence cap ≤10 / ≤200 chars; consensus_score range; confidence range; literal types for state and action_hint).
   - data_unavailable invariant: each violation case (state='oversold' + data_unavailable=True; consensus_score=0.5 + data_unavailable=True; etc.) raises ValidationError.
   - JSON round-trip: model_dump_json → json.loads → model_validate_json yields equal object.
   - Default values match the canonical no-opinion shape.

**Wave 1 closeout criteria:**
- `pytest tests/analysts/test_position_signal.py -v` passes.
- Coverage on `analysts/position_signal.py` ≥ 90%/85%.

### Wave 2: Position-Adjustment Radar implementation

**Estimated effort:** 4-6 hours active execution. **Risk:** MEDIUM (most lines + most assertions; multiple test paths).

**Plan name suggestion:** `04-03-position-adjustment-PLAN.md`

**Tasks (TDD-friendly breakdown):**
1. **Create `analysts/position_adjustment.py`** with provenance docstring, module-level constants, and skeleton `score()`.
2. **Implement 6 indicator helpers** — `_rsi_14`, `_bollinger_position`, `_zscore_vs_ma50`, `_stoch_k_14`, `_williams_r_14`, `_macd_histogram_zscore` (each ~6-14 LOC). Each helper returns Optional[float] (raw value or None for warm-up / flat-line).
3. **Implement 6 sub-signal mappers** — `_rsi_to_subsignal`, etc. (~3 LOC each).
4. **Implement `_consensus_to_state` + `_state_to_action_hint` + `_compute_confidence`.**
5. **Implement `_format_evidence(key, raw, sub_signal)`** that produces the canonical evidence string for each indicator (matches CONTEXT.md `<specifics>` examples).
6. **Wire `score()` orchestration** per the skeleton in Code Examples.
7. **Create `tests/analysts/test_position_adjustment.py`** with ~25-30 tests per the Phase Requirements → Test Map above.
8. **Extend `tests/analysts/test_invariants.py`** with `test_dark_snapshot_emits_pose_unavailable` (cross-cutting test analog of the AgentSignal one — locks the contract that PositionSignal follows the same UNIFORM RULE).

**Wave 2 closeout criteria:**
- `pytest tests/analysts -v` passes (full Phase 4 test suite + Phase 3 regressions).
- Coverage on `analysts/position_adjustment.py` ≥ 90%/85%.
- POSE-01..05 all marked complete in REQUIREMENTS.md.
- ROADMAP.md Phase 4 row marked complete.

### Why three waves vs one?

Three waves match the Phase 3 structure (foundation / Wave 1 schema-and-easy-analysts / Wave 2 math-heavy-analysts) and let the planner parallelize across files within each wave. Each wave has a clear closeout criterion. Three commits is light enough that the user reviewing the diff can read each wave in isolation.

**Alternative (one big plan):** would conflate the refactor with the new feature and make the diff harder to review. Not recommended.

## Sources

### Primary (HIGH confidence)
- StockCharts ChartSchool RSI — https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/relative-strength-index-rsi (Wilder formula; canonical 70/30 thresholds)
- StockCharts ChartSchool Stochastic Oscillator — https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/stochastic-oscillator-fast-slow-and-full (Fast/Slow/Full %K formulas; canonical 80/20 thresholds)
- StockCharts ChartSchool Williams %R — https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/williams-r (formula; canonical -80/-20 thresholds)
- StockCharts ChartSchool Bollinger Bands — https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/bollinger-bands (20-period SMA + 2 stdev formula)
- StockCharts ChartSchool %B — https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/b-indicator (canonical %B formula; explains the affine relationship to CONTEXT.md's BB position formula)
- StockCharts ChartSchool MACD-Histogram — https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/macd-histogram (12/26/9 standard parameters)
- StockCharts ChartSchool ADX — https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/average-directional-index-adx (Wilder smoothing; trend/range thresholds at 25/20)
- Wikipedia RSI — https://en.wikipedia.org/wiki/Relative_strength_index (Wilder formula; well-known limitation in trending markets)
- Wikipedia Williams %R — https://en.wikipedia.org/wiki/Williams_%25R (formula + interpretation)
- Wikipedia MACD — https://en.wikipedia.org/wiki/MACD (canonical formula; histogram = MACD - signal)
- pandas-ta-classic GitHub — https://github.com/xgboosted/pandas-ta-classic (MIT, 192 indicators, last release 0.5.44 in April 2026, 270 stars, actively maintained, optional ta-lib + numba accelerations)
- TA-Lib PyPI — https://pypi.org/project/TA-Lib/ (binary wheels available since 0.6.5 / Oct 2025; bundles C library; install posture)
- Existing project source — `analysts/technicals.py`, `analysts/fundamentals.py`, `analysts/signals.py`, `tests/analysts/conftest.py`, `analysts/data/{prices,snapshot}.py`, `pyproject.toml`, `poetry.lock`, `.planning/phases/03-analytical-agents-deterministic-scoring/03-RESEARCH.md`, `.planning/phases/03-analytical-agents-deterministic-scoring/03-03-SUMMARY.md`

### Secondary (MEDIUM confidence — verified across multiple sources)
- Schwab "Spot and Stick to Trends with ADX and RSI" — https://www.schwab.com/learn/story/spot-and-stick-to-trends-with-adx-and-rsi (combining ADX with RSI to filter false mean-reversion signals)
- Lux Algo RSI Overbought/Oversold — https://www.luxalgo.com/blog/rsi-overbought-and-oversold-signals-explained/ (RSI persisting in overbought/oversold zones in strong trends; multiple-timeframe + ADX-filter recommendation)
- TradingView Institutional MACD (Z-Score Edition) — https://www.tradingview.com/script/LeQQ4Y8W-Institutional-MACD-Z-Score-Edition-VolumeVigilante/ (z-score normalization for cross-instrument MACD comparability)
- ProRealCode MACD Z-Score — https://www.prorealcode.com/prorealtime-indicators/macd-z-score-standardized-value/ (rolling z-score formula for MACD)
- StatOasis ADX Guide — https://statoasis.com/post/how-to-use-the-adx-indicator-like-a-pro-step-by-step-guide (ADX > 25 trend regime; mean-reversion strategies suit weak-trend / ranging markets)
- FXNX ADX Strategy — https://fxnx.com/en/blog/adx-strategy-efficiency-filter-measure-trend-strength-like (ADX as a filter for choppy markets; breakouts with ADX < 20 often head-fake)
- virattt risk_manager.py (verified via WebFetch) — https://github.com/virattt/ai-hedge-fund/blob/main/src/agents/risk_manager.py (multi-indicator volatility-adjusted aggregation pattern; structurally similar to our consensus aggregation though intent differs)
- TC2000 RSI Wilder vs Cutler — https://help.tc2000.com/m/69404/l/747071-rsi-wilder-s-rsi (Wilder smoothing as the canonical RSI variant; explicit equivalence to EMA with α=1/N)

### Tertiary (LOW confidence — single source, cross-checked but flagged)
- Sling Academy ta-lib vs pandas-ta comparison — https://www.slingacademy.com/article/comparing-ta-lib-to-pandas-ta-which-one-to-choose/ (general install + indicator-count tradeoffs; reasonable but no peer review)
- TradingSim Bollinger BandWidth — https://www.tradingsim.com/blog/use-bollinger-band-width-indicator-call-major-tops-bottoms (BandWidth concept; mean-reversion application)

## Metadata

**Confidence breakdown:**
- PositionSignal schema: HIGH — direct mirror of CONTEXT.md + Phase 3 AgentSignal precedent; field types verified.
- Standard stack (pandas/numpy already transitive, no new deps): HIGH — verified poetry.lock has pandas 3.0.2 / numpy 2.4.4 from Phase 3 RESEARCH.md.
- Architecture / pure-function pattern: HIGH — direct mirror of established Phase 3 patterns.
- Indicator math (RSI, BB, Stochastic, Williams %R, z-score, MACD): HIGH — formulas verified against StockCharts canonical references for each.
- MACD histogram z-score normalization at 60 bars: MEDIUM — z-score over rolling window is industry-standard (TradingView, ProRealCode); 60-bar window is a tunable choice with reasonable justification but not empirically benchmarked. Tunable via module constant; v1.x ticket if 60 turns out to over-/under-react.
- TREND_REGIME_DOWNWEIGHT=0.5: MEDIUM — published practitioner consensus that mean-reversion indicators false-positive in trending markets (Schwab, Wikipedia, Lux Algo all confirm); the specific weight value 0.5 is a reasonable midpoint (compared to 0.0 = ignore entirely or 1.0 = no gating). Tunable via module constant; v1.x ticket if 0.5 is too aggressive in mild trends.
- Confidence formula with abstain rule: HIGH — well-defined (n_active < 2 cap and abstain-threshold edge cases explicitly handled); locked at the formula level.
- Wilder smoothing equivalence to pandas EMA(α=1/N): HIGH — published mathematical identity, cross-verified with StockCharts walkthrough; locked in Phase 3 03-RESEARCH.md and reused.
- Min-bars warm-up table: HIGH — each indicator's min-bars verified against canonical reference.
- _indicator_math.py extraction: HIGH — mechanical refactor; existing Phase 3 tests guard against regression.
- PositionSignal as PEER (not subtype) of AgentSignal: HIGH — field shapes diverge cleanly; Phase 5/7 consumers have no shared-base pull; Pattern #7 documents the rationale.
- pandas-ta-classic / ta-lib decision (against): HIGH — 6 indicators in ~60 LOC vs new dependency posture; Phase 3 03-RESEARCH.md provisionally said "skip; revisit at Phase 4"; Phase 4 confirms.
- virattt risk_manager.py source-file mapping: HIGH — verified via direct WebFetch.

**Research date:** 2026-05-03
**Valid until:** 2026-06-03 (30-day window — Phase 4 components are stable; primary risks are external library breakage which would surface as test failures rather than research-correctness issues; the indicator-library decision and threshold defaults are tunable via module constants without re-research)
