# Phase 4: Position-Adjustment Radar — Context

**Gathered:** 2026-05-03
**Status:** Ready for planning

<domain>
## Phase Boundary

One pure-function Python module — Position-Adjustment Radar — that consumes the per-ticker `Snapshot` produced by Plan 02-06 and emits one `PositionSignal` (NOT an `AgentSignal` — see Decisions) carrying a multi-indicator overbought/oversold consensus, an action hint, and ADX-based trend-regime gating. Operates as the headline data structure powering the Morning Scan's primary lens (POSE-05). No LLM, no I/O, no persistence. Pure deterministic scoring callable from any context (Phase 5 routine, Phase 8 mid-day refresh, unit tests).

**Out of phase boundary** (do NOT include here):

- Phase 3 analyst signals (fundamentals / technicals / news_sentiment / valuation) — already shipped. Phase 3 technicals is MA + momentum + ADX trend regime ONLY; oscillator-consensus + Bollinger + z-score live HERE.
- LLM persona slate, Synthesizer, `TickerDecision`, `_status.json`, scheduling — Phase 5.
- Frontend rendering of POSE output — Phase 6.
- Decision-Support recommendation banner (buy/trim/hold/take_profits) — Phase 7. Phase 4 emits `action_hint` ∈ {consider_add, hold_position, consider_trim, consider_take_profits}; Phase 7 synthesizes the final recommendation across POSE + persona signals + valuation.
- Mid-day refresh wiring — Phase 8.

**Roadmap reconciliation:** ROADMAP.md Phase 4 calls this "Position-Adjustment Radar" with 6 indicators (RSI(14), Bollinger Bands position, z-score vs 50-day MA, Stochastic %K, Williams %R, MACD divergence) plus ADX(14) for trend-regime gating. REQUIREMENTS.md POSE-01 enumerates the same 6 indicators. Both are consistent.

</domain>

<decisions>
## Implementation Decisions

### Output Schema (LOCKED — separate from AgentSignal)

```python
# analysts/position_adjustment.py (or analysts/pose.py — name TBD by planner)
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from analysts.schemas import normalize_ticker

PositionState = Literal[
    "extreme_oversold", "oversold", "fair", "overbought", "extreme_overbought"
]
ActionHint = Literal[
    "consider_add", "hold_position", "consider_trim", "consider_take_profits"
]


class PositionSignal(BaseModel):
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
    trend_regime: bool = False  # True when ADX(14) > 25 — mean-reversion indicators downweighted

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
                raise ValueError("evidence string exceeds 200 chars")
        return v
```

- **NOT an `AgentSignal`.** PositionSignal carries different fields (state ladder vs verdict ladder, action_hint, per-indicator readings, trend_regime flag) — forcing it into AgentSignal's shape would either lose information or pollute the AgentSignal contract. Phase 5 synthesizer reads PositionSignal alongside the four AgentSignals as a peer-level input, not as a fifth AgentSignal.
- **5-state ladder for `state`** (extreme_oversold..extreme_overbought) mirrors the fundamentals/technicals 5-state pattern but oriented around mean-reversion rather than directional verdict.
- **`consensus_score: float` ∈ [-1, +1]** — signed continuous magnitude underlying the discrete `state` ladder. Negative = oversold, positive = overbought.
- **`confidence: int` ∈ [0, 100]** — reflects indicator AGREEMENT count (more indicators concurring → higher confidence), NOT signal magnitude. Distinct from AgentSignal's confidence which mixes magnitude with directional consensus.
- **`indicators: dict[str, float | None]`** — per-indicator raw readings for transparency / Phase 6 deep-dive rendering. Keys: `"rsi_14"`, `"bb_position"`, `"zscore_50"`, `"stoch_k"`, `"williams_r"`, `"macd_histogram"`, `"adx_14"`. None when warm-up bars insufficient.
- **`action_hint: ActionHint`** — derived from state via fixed mapping. NOT a final recommendation (that's Phase 7's job); a pre-recommendation hint that the Phase 7 synthesizer combines with persona + valuation signals.
- **`trend_regime: bool`** — True when ADX(14) > 25. Phase 4 mean-reversion indicators (RSI / BB / Stochastic / Williams %R) are DOWNWEIGHTED in scoring when this is True — they false-positive in trending markets (POSE-03). MACD divergence + z-score retain full weight.
- **`evidence: list[str]`** — same shape as AgentSignal: ≤10 items, each ≤200 chars. Each evidence string explains one indicator's contribution.
- **`data_unavailable: bool`** — UNIFORM RULE: when too few bars for ANY indicator OR snapshot.prices None / data_unavailable / current_price None → `data_unavailable=True, state="fair", consensus_score=0.0, confidence=0, action_hint="hold_position", indicators={...with None values...}, evidence=[<reason>]`.

### Module Layout

- `analysts/position_adjustment.py` — `score(snapshot: Snapshot, config: TickerConfig, *, computed_at: Optional[datetime] = None) -> PositionSignal`. Pure function, no I/O, no module-level mutable state. Module-level threshold constants at the top.
- `analysts/position_signal.py` (OR co-located in position_adjustment.py — planner decides) — `PositionSignal`, `PositionState`, `ActionHint` types.
- Public surface: same shape as Phase 3 analysts (`score(snapshot, config, *, computed_at=None) -> SignalType`).
- Pattern reuse: identical to Phase 3 analyst signature. The `now = computed_at if computed_at is not None else datetime.now(timezone.utc)` discipline carries over (Pitfall #7 from Phase 3 — locked by AST-walk test).

### Indicator Math (LOCKED — 6 indicators + ADX gate)

| Indicator | Formula | Warm-up bars | Signal direction |
|-----------|---------|--------------|------------------|
| **RSI(14)** | Wilder smoothing of avg gain / avg loss; RSI = 100 - (100 / (1 + RS)) | 27 (= 2N - 1) | Mean-reversion: <30 oversold, >70 overbought |
| **Bollinger Bands position** | (close - SMA20) / (2 * stdev20). 0 = at SMA, ±1 = at band | 20 | Mean-reversion: <-1 below lower band, >+1 above upper band |
| **z-score vs 50-day MA** | (close - SMA50) / stdev50 | 50 | Trend-following: positive z = above MA (bullish if confirmed), negative z = below MA |
| **Stochastic %K** | 100 * (close - low_14) / (high_14 - low_14). Range [0, 100] | 14 | Mean-reversion: <20 oversold, >80 overbought |
| **Williams %R** | -100 * (high_14 - close) / (high_14 - low_14). Range [-100, 0] | 14 | Mean-reversion: <-80 oversold, >-20 overbought |
| **MACD histogram** | (EMA12 - EMA26) - signal_line(EMA9 of MACD). Sign + magnitude | ~34 (26+9-1) | Trend-following: histogram > 0 momentum up, < 0 momentum down |
| **ADX(14)** | Wilder ADX (already implemented in Phase 3 technicals.py) | 27 | Regime gate: > 25 trend, < 20 range, between ambiguous |

**Pandas dependency posture:** Same as Phase 3 — pandas + numpy come transitively via yfinance (already in lockfile). DO NOT add pandas as direct dependency. Hand-rolled `.rolling()` + `.ewm()` math, ~30-50 LOC per indicator helper.

**Indicator-library decision (the deferred-from-Phase-3 question):** Plan-phase research will revisit ta-lib / pandas-ta-classic / hand-rolled. Provisional decision pending research: hand-rolled (continues the 03-03 technicals pattern; avoids new dep). The 6 Phase 4 indicators add ~150 LOC of indicator math vs the 3 already shipped — acceptable for v1 scope.

### Trend-Regime Gating (LOCKED concept; weight values TBD by research)

When `ADX(14) > 25` (trend regime confirmed):
- Mean-reversion indicators (RSI, BB position, Stochastic %K, Williams %R) — DOWNWEIGHTED to ~0.5x in `consensus_score` aggregation. They false-positive in trending markets ("oversold" readings persist for weeks while price keeps falling).
- Trend-following indicators (z-score vs 50-day MA, MACD histogram) — RETAIN full weight. They're the "stay with the trend" voice.

When `ADX(14) < 20` (range regime):
- All 6 indicators retain full weight; mean-reversion signals are accurate in range markets.

When `ADX(14)` is between 20-25 (ambiguous):
- All weights at 1.0 (no gating). Avoid arbitrary discontinuity at ADX=25.

`trend_regime: bool` field on PositionSignal is True when ADX > 25; evidence string carries `"ADX 31 — trend regime; mean-reversion indicators downweighted"` so frontend rendering can flag it.

### State Ladder Mapping

`consensus_score` → `state` via strict-> boundaries (mirrors fundamentals/technicals 5-state ladder pattern but for mean-reversion sign):

```python
def _consensus_to_state(score: float) -> PositionState:
    if score < -0.6: return "extreme_oversold"
    if score < -0.2: return "oversold"
    if score >  0.6: return "extreme_overbought"
    if score >  0.2: return "overbought"
    return "fair"
```

**Strict > / < boundaries** (NOT >=) — same discipline as Phase 3 analysts. `consensus_score=0.6` maps to `overbought`, NOT `extreme_overbought`.

### action_hint Derivation (LOCKED mapping)

| state | action_hint |
|-------|-------------|
| extreme_oversold | consider_add |
| oversold | consider_add |
| fair | hold_position |
| overbought | consider_trim |
| extreme_overbought | consider_take_profits |

Note: `consider_add` collapses extreme_oversold + oversold (no `strong_consider_add` tier — Phase 7 reads `confidence` and `consensus_score` to derive conviction band). `consider_trim` is the moderate version of `consider_take_profits` per the user's risk-management language preference.

### Empty / Partial Data Handling (UNIFORM RULE)

Same shape as Phase 3 — emit a canonical `data_unavailable=True` signal with one explanatory evidence string per branch:

- `snapshot.data_unavailable=True` → `data_unavailable=True, evidence=["snapshot data_unavailable=True"]`.
- `snapshot.prices is None` → `evidence=["prices snapshot missing"]`.
- `snapshot.prices.data_unavailable=True` → `evidence=["prices.data_unavailable=True"]`.
- `len(history) < MIN_BARS_FOR_ANY_INDICATOR` (= 14, the smallest indicator warm-up) → `evidence=["history has N bars; need ≥14 for any indicator"]`.
- Otherwise compute; per-indicator None readings degrade gracefully (indicator skipped from aggregate, evidence string not emitted for that indicator).

**Invariant:** `consensus_score=0.0` when `data_unavailable=True` (matches AgentSignal data_unavailable invariant pattern).

### Threshold Configuration

Module-level constants at top of `analysts/position_adjustment.py`:
- `RSI_OVERSOLD_BELOW=30`, `RSI_OVERBOUGHT_ABOVE=70`.
- `STOCH_OVERSOLD_BELOW=20`, `STOCH_OVERBOUGHT_ABOVE=80`.
- `WILLIAMS_OVERSOLD_BELOW=-80`, `WILLIAMS_OVERBOUGHT_ABOVE=-20`.
- `BB_OVERSOLD_BELOW=-1.0`, `BB_OVERBOUGHT_ABOVE=+1.0` (units: stdevs from SMA20).
- `ZSCORE_OVERSOLD_BELOW=-1.5`, `ZSCORE_OVERBOUGHT_ABOVE=+1.5`.
- `ADX_TREND_ABOVE=25.0`, `ADX_RANGE_BELOW=20.0` (matches Phase 3 technicals.py).
- `TREND_REGIME_DOWNWEIGHT=0.5` (mean-reversion indicators when ADX > 25).
- `MIN_BARS_FOR_ANY_INDICATOR=14` (Stochastic %K + Williams %R floor).

No central `analysts/thresholds.py`, no TOML config — same posture as Phase 3.

### Provenance

- `analysts/position_adjustment.py` carries header comment naming source. Possible references: `virattt/ai-hedge-fund/src/agents/risk_manager.py` (multi-indicator consensus pattern, even though virattt's risk manager focuses on position sizing rather than overbought/oversold). Research will identify the closest reference; otherwise this module is novel-to-this-project and the docstring states that explicitly.

### Testing Surface

- `tests/analysts/test_position_signal.py` (or co-located in `test_position_adjustment.py`) — `PositionSignal` schema validation, ticker normalization, evidence cap, state literal, consensus_score range.
- `tests/analysts/test_position_adjustment.py` — at minimum: 6 known-regime regressions (synthetic uptrend / synthetic downtrend / synthetic sideways / synthetic mean-reverting / synthetic post-crash / synthetic post-spike); per-indicator correctness tests; warm-up min-bars guards; trend-regime gating verification (high ADX downweights RSI etc.); state ↔ action_hint mapping; empty-data UNIFORM RULE; determinism + provenance.
- All tests pure-function: build a `Snapshot` + `TickerConfig` fixture (reuse `synthetic_*_history` builders from Phase 3 conftest), call `score(...)`, assert on returned `PositionSignal`. No filesystem, no network.

### Dependencies (new)

- **None planned.** pandas + numpy already transitive. The indicator-library decision (ta-lib / pandas-ta-classic / hand-rolled) is research-driven; provisional answer is hand-rolled (zero new deps).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`analysts.schemas.normalize_ticker`** — `PositionSignal.ticker` uses the same `field_validator(mode="before")` pattern locked across the codebase.
- **`analysts.data.snapshot.Snapshot`** — locked input contract from Plan 02-06; carries `prices`, `fundamentals`, `filings`, `news`, `social`, plus `data_unavailable` and `errors`. Phase 4 reads `snapshot.prices.history` (list[OHLCBar]) and `snapshot.prices.current_price`.
- **`analysts.data.prices.OHLCBar`** — `date / open / high / low / close / volume` per-bar schema. All 4 OHLC fields are gt=0 at the schema layer.
- **`analysts/technicals.py`** — Phase 3 already ships `_build_df`, `_adx_14`, `_total_to_verdict` helpers + module-level constants (`ADX_PERIOD`, `ADX_TREND_ABOVE`, `ADX_RANGE_BELOW`, `ADX_MIN_BARS`, `ADX_STABLE_BARS`). Phase 4 SHOULD share or copy these helpers — DRY trigger has already fired (this is the 4th time `_total_to_verdict` would be copied; the 5th time `_build_df` would be copied). Recommend: extract `_build_df` and `_adx_14` from `analysts/technicals.py` into a shared `analysts/_indicator_math.py` module in Wave 0 of Phase 4. This is a low-risk refactor (no behavior change, both tests still pass) and cleans up the indicator-helper duplication once and for all.
- **`tests/analysts/conftest.py`** — `synthetic_uptrend_history` / `synthetic_downtrend_history` / `synthetic_sideways_history` builders shipped in Phase 3 / Plan 03-01 are directly reusable. Phase 4 may want to add `synthetic_mean_reverting_history` (oscillating around a central price with controlled period + amplitude) for explicit overbought/oversold regression testing.

### Established Patterns

- **Pure-function `score(snapshot, config, *, computed_at=None) -> SignalType`** — locked across all 4 Phase 3 analysts. Phase 4 follows.
- **Module-level threshold constants at the top, tunable by editing the file** — same posture as Phase 3.
- **Empty-data UNIFORM RULE with distinct evidence reason per branch** — Phase 3 pattern, locks here too.
- **`now` read ONCE at top of score(); helpers receive `now` as parameter (Pitfall #7)** — locked by AST-walk test in 03-04. Phase 4 follows the same discipline.
- **Provenance header naming source file** — INFRA-07; mandatory.
- **Hand-rolled pandas indicator math** — Phase 3 pattern; `.rolling()` for SMA, `.ewm(alpha=1/N, adjust=False)` for Wilder smoothing. RSI / Stochastic / Williams %R / MACD all expressible in this idiom.
- **Min-bars warm-up guards everywhere a rolling/diff/shift call could yield NaN at iloc[-1]** — Phase 3 03-03 pattern; Phase 4 follows.

### Integration Points

- **Phase 5 routine** reads PositionSignal alongside the four AgentSignals when building the per-ticker snapshot JSON. POSE-05 says "Position-Adjustment output is the headline data structure powering the Morning Scan's primary lens" — Phase 6 reads it from disk.
- **Phase 7 Decision-Support** reads PositionSignal `state` + `action_hint` + `confidence` to derive the final recommendation banner alongside persona + valuation signals.
- **Phase 8 mid-day refresh** may call `position_adjustment.score(...)` on freshly-fetched intraday prices; same pure-function contract.

### Constraints from Existing Architecture

- **Keyless** — no new external API calls; pure pandas math.
- **No LangGraph / no LLM** in this phase — Phase 4 is deterministic Python.
- **Lite-mode (INFRA-02) compatible** — Phase 4 is lite-mode-friendly by construction (no LLM, no quota).

</code_context>

<specifics>
## Specific Ideas

### `PositionSignal.evidence` — Format Convention (not enforced by schema)

Same convention as AgentSignal.evidence — embed metric, value, threshold or comparison:

```
"RSI(14) 28.4 — oversold (below 30)"
"Bollinger position -1.3 — below lower band by 0.3 stdevs"
"z-score vs MA50: -1.7 — extended below trend"
"Stochastic %K 18.5 — oversold (below 20)"
"Williams %R -82 — oversold (below -80)"
"MACD histogram -1.42 — bearish momentum (negative)"
"ADX 31 — trend regime; mean-reversion indicators downweighted by 50%"
"4 of 6 indicators agree (oversold consensus); ADX trend regime active"
```

Frontend in Phase 6 renders these as bullets in the Position-Adjustment lens.

### Threshold Defaults (starting values, may be tuned by research)

- **RSI(14):** <30 oversold, >70 overbought (canonical Wilder thresholds).
- **Bollinger Bands position (units of stdev):** <-1.0 oversold, >+1.0 overbought (1 stdev = canonical band edge).
- **z-score vs 50-day MA:** <-1.5 oversold, >+1.5 overbought (~7% of bars; tunable by research).
- **Stochastic %K:** <20 oversold, >80 overbought (canonical thresholds).
- **Williams %R:** <-80 oversold, >-20 overbought (canonical thresholds; Williams %R is signed inverse of Stochastic).
- **MACD histogram:** sign indicates direction; magnitude relative to recent trailing distribution (Z-score-style normalization recommended; research will lock the formula).
- **ADX(14):** > 25 trend regime, < 20 range regime, between ambiguous (matches Phase 3 technicals).

### Aggregation Math — `consensus_score`

Each of the 6 indicators emits a sub-signal in [-1, +1] (negative = oversold, positive = overbought). Aggregation:

```python
sub_signals: list[tuple[float, float]] = []  # (signal, weight)
# RSI: linearize RSI ∈ [0, 100] to [-1, +1] via (RSI - 50) / 50, clamp to ±1.
# BB position: clamp BB ∈ [-2, +2] to [-1, +1].
# z-score: clamp to ±1 at z = ±2.
# Stochastic: linearize %K ∈ [0, 100] to [-1, +1] via (50 - %K) / 50 (sign flip — low %K = oversold).
# Williams %R: linearize ∈ [-100, 0] to [-1, +1] via (Williams + 50) / 50 (sign flip).
# MACD histogram: sign of histogram → direction; magnitude normalized by trailing stdev → scaled.

# Trend-regime gating
if adx > 25:
    sub_signals_with_weights = [
        (rsi_signal, 0.5), (bb_signal, 0.5), (stoch_signal, 0.5), (williams_signal, 0.5),
        (zscore_signal, 1.0), (macd_signal, 1.0),
    ]
else:
    sub_signals_with_weights = [(s, 1.0) for s in all_six]

total_w = sum(w for _, w in active_signals)
consensus_score = sum(s * w for s, w in active_signals) / total_w  # in [-1, +1]
```

Confidence reflects AGREEMENT count (how many indicators have the same sign as `consensus_score`):
```python
confidence = round(100 * (n_agreeing / n_active))
```
Distinct from AgentSignal's `confidence = round(abs(aggregate) * 100 * density)` — Phase 4 confidence is about how unanimous the indicators are, not how strong the average reading is.

### Determinism

Same as Phase 3 — `score(...)` is deterministic given identical inputs (`Snapshot`, `TickerConfig`). `now = computed_at if computed_at is not None else datetime.now(timezone.utc)` read ONCE at top of score(); helpers receive `now` as parameter.

### File Sizes Expected

- `analysts/position_adjustment.py`: ~250-350 lines (provenance docstring + threshold constants + DataFrame builder + 6 indicator helpers + `_consensus_to_state` + `_state_to_action_hint` + `_aggregate` + `score()`).
- `analysts/_indicator_math.py` (if extracted): ~80 lines (`_build_df` + `_adx_14` + `_wilder_smooth` shared helpers).
- `tests/analysts/test_position_adjustment.py`: ~400-500 lines (~25-30 tests covering 6 known-regime regressions + 6 per-indicator correctness + warm-up guards + trend-regime gating + state mapping + action_hint mapping + empty-data + determinism + provenance).

</specifics>

<deferred>
## Deferred Ideas

- **Per-sector / peer-relative overbought/oversold scoring** ("AAPL RSI 30 vs sector median 50"). Requires accumulated historical snapshots; revisit at v1.x SEC-01.
- **Per-ticker calibrated thresholds.** Some tickers oscillate wider than others; tuning thresholds per ticker would tighten the false-positive rate. v1.x territory.
- **Volume-weighted indicators (OBV, MFI, A/D Line).** Considered + deferred — adding 3 more indicators bloats the consensus calculation without clear evidence they reduce false-positives. Revisit if RSI/BB/Stochastic consensus is the limiting factor in Phase 7 recommendation accuracy.
- **Multi-timeframe consensus (daily + weekly).** Daily-only for v1 (matches the 1-year history depth from Plan 02-07). Weekly POSE could come in v1.x.
- **Machine-learning-based regime classifier** (replacing ADX-based gating with a learned classifier). v2 territory; ADX is the well-understood baseline.
- **Real-time tick-level POSE** (recompute on every tick). v1.x OND-01 territory; daily-and-mid-day refresh is sufficient for v1.
- **Persona signal trend view** ("position has been overbought for 3 weeks"). v1.x TREND-01; needs the memory layer (Phase 8 INFRA-06).
- **action_hint refinement via sentiment / fundamentals overlay.** Phase 7's job — Phase 4's action_hint is purely indicator-driven.

</deferred>

---

*Phase: 04-position-adjustment-radar*
*Context gathered: 2026-05-03*
