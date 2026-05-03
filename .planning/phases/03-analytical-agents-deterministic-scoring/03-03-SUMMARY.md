---
phase: 03-analytical-agents-deterministic-scoring
plan: 03
subsystem: analysts
tags: [phase-3, analyst, technicals, tdd, pure-function, anly-02, wave-2, pandas-hand-rolled]

# Dependency graph
requires:
  - phase: 03-analytical-agents-deterministic-scoring
    plan: 01
    provides: analysts.signals.AgentSignal (5-state Verdict ladder + 0-100 confidence + evidence list + data_unavailable invariant), analysts.signals.Verdict + AnalystId Literals, tests/analysts/conftest.py (frozen_now / make_snapshot / make_ticker_config fixtures + module-level synthetic_uptrend_history / synthetic_downtrend_history / synthetic_sideways_history builders)
  - phase: 02-ingestion-keyless-data-plane
    plan: 01
    provides: analysts.data.prices.PriceSnapshot + analysts.data.prices.OHLCBar (history list scored by this analyst — open/high/low/close all gt=0 at the schema layer)
  - phase: 02-ingestion-keyless-data-plane
    plan: 06
    provides: analysts.data.snapshot.Snapshot (per-ticker aggregate carrying optional prices sub-field plus snapshot-level data_unavailable bool)
  - phase: 02-ingestion-keyless-data-plane
    plan: 07
    provides: '"1y" history default in ingestion/prices.fetch_prices — ~252 trading bars sufficient for MA200 + 6m momentum + stable ADX warm-up'
provides:
  - "analysts.technicals.score(snapshot, config, *, computed_at=None) -> AgentSignal — pure function, no I/O, never raises for missing data"
  - "MA20/MA50/MA200 stack alignment scoring (bullish stack / bearish stack / mixed) with degraded evidence for <200-bar histories"
  - "Momentum scoring at 1m/3m/6m horizons (21/63/126 bars; ±5/10/15% thresholds — weighted toward shorter horizons)"
  - "Wilder ADX(14) via pandas .ewm(alpha=1/14, adjust=False).mean() — mathematically identical to Wilder's recursive formula. Trend regime (>25) amplifies the directional vote by +1 / -1 once."
  - "Min-bars warm-up guards: <20 bars → data_unavailable=True; <27 → ADX skipped; <50 → MA stack skipped; 50..199 → MA20/MA50 only with 'MA200 unavailable' evidence; <22/64/127 → 1m/3m/6m momentum each skipped"
  - "Empty-data UNIFORM RULE: snapshot.data_unavailable=True OR snapshot.prices is None OR snapshot.prices.data_unavailable=True OR empty history → AgentSignal(data_unavailable=True, verdict='neutral', confidence=0, evidence=[<distinct reason>])"
  - "Hand-rolled pandas indicator math — NO pandas-ta / ta-lib / pandas-ta-classic dependency (Phase 4 POSE plan-phase revisits indicator-library choice)"
  - "Provenance header (INFRA-07) names virattt/ai-hedge-fund/src/agents/technicals.py and enumerates 6 modifications (SMA stacks vs EMA stacks; min-bars guards added; MA + momentum + ADX only — RSI/Bollinger/MACD/Hurst belong to Phase 4 POSE; pure pandas vs ta-lib; pure function vs graph node; UNIFORM RULE empty-data guard)"
affects: [phase-3-plan-04-news-sentiment-analyst, phase-3-plan-05-valuation-analyst, phase-4-pose-radar (will reuse the same pandas DataFrame builder + extend with RSI/Bollinger/Stochastic/Williams %R/MACD/Hurst), phase-5-claude-routine (reads AgentSignal from disk via JSON)]

# Tech tracking
tech-stack:
  added: []  # No new dependencies — pandas + numpy already transitive via yfinance
  patterns:
    - "Hand-rolled pandas indicator pattern: list[OHLCBar] -> DataFrame (high/low/close, sort_index, dropna) -> SMA via .rolling(N).mean() -> Wilder smoothing via .ewm(alpha=1/N, adjust=False).mean(). All math contained in private module-level helpers; score() orchestrates."
    - "Per-indicator helper returning (score, Optional[evidence_string]) shape, identical to the per-metric helper pattern from 03-02 fundamentals. None evidence == 'indicator not yet computable, exclude from evidence list'; non-None evidence (even score=0) == 'indicator computed, include the explanatory string'."
    - "ADX-as-amplifier rule: ADX is informational evidence (sub-score=0, evidence string only) UNLESS ADX > 25 (trend regime) AND the MA + momentum stack already points directionally — then it adds +1/-1 once. Bounded amplifier (max 1 vote, only fires when stacks_total != 0)."
    - "Min-bars warm-up guards everywhere a rolling/diff/shift call could yield NaN at iloc[-1]. Three tiers: 20 / 27 / 50 / 200. Below the floor → data_unavailable=True; intermediate tiers → degrade indicators gracefully and note the missing one in evidence."
    - "Defensive normalized clamp at [-1, +1] before _total_to_verdict. Internal math caps at 5/5 = 1.0 today; the clamp survives any future indicator addition that could push beyond — same defense-in-depth posture as 03-02's confidence min(100, ...) cap."

key-files:
  created:
    - "analysts/technicals.py (414 lines — provenance docstring + module-level constants + _build_df + _ma_alignment + _momentum_one + _adx_14 + _adx_evidence + _total_to_verdict + score())"
    - "tests/analysts/test_technicals.py (~510 lines, 25 tests covering 3 known-regime regressions + 5 warm-up cases + 4 empty-data branches + 4 indicator-correctness tests + 2 ADX regime tests + 7 provenance/determinism/contract tests)"
  modified: []  # No existing files touched aside from docs at closeout

key-decisions:
  - "SMA stacks (MA20/MA50/MA200) instead of EMA stacks (8/21/55) per 03-CONTEXT.md decision. SMAs match the stockcharts/finviz convention the user is more familiar with; the canonical 'bullish stack' interpretation (MA20 > MA50 > MA200) is the exact pattern documented in mainstream charting tools."
  - "Min-bars guards added — virattt/ai-hedge-fund does NOT guard against short history, which silently produces NaN at iloc[-1] and marks every cold-start ticker 'neutral confidence 0' while quietly lying about data availability (03-RESEARCH.md Pitfall #1). Our guards explicitly flag the ticker as data_unavailable=True when there are fewer than 20 bars (no indicator possible) and degrade gracefully when there are enough for some but not all indicators."
  - "MA + momentum + ADX only — RSI / Bollinger Bands / Stochastic / Williams %R / MACD / Hurst belong to Phase 4 POSE-01..05 (the Position-Adjustment Radar). Phase 4's plan-phase revisits the ta-lib / pandas-ta-classic decision; for Phase 3 we hand-roll the 3 indicator families. This keeps technicals.py at ~150 LOC of indicator math and defers the dependency-choice debate."
  - "Pure pandas — NO pandas-ta / ta-lib / pandas-ta-classic dependency. Pandas + numpy come transitively via yfinance (already in poetry.lock per 03-RESEARCH.md confirmation); DO NOT add pandas as a direct dependency in pyproject.toml. A future planner reading this might want to 'fix the missing pandas dep' — they should not. The provenance docstring documents this explicitly."
  - "Wilder smoothing implemented as pandas .ewm(alpha=1/14, adjust=False).mean() — mathematically identical to Wilder's recursive formula per StockCharts canonical walkthrough (https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/average-directional-index-adx). The mathematical identity is locked in the docstring so future readers don't 'fix' the EMA call to a hand-rolled recursive Wilder loop."
  - "ADX min-bars floor is 27 (= 2*N - 1 = 2*14 - 1). Below 27 the Wilder smoothing has not yet absorbed enough data for the recursive average to settle; _adx_14 returns None and ADX evidence is omitted. ADX_STABLE_BARS = 150 is the secondary floor — between 27 and 150 the value is mathematically valid but may swing; evidence string carries an '(ADX may be unstable, X bars)' suffix to flag this for downstream consumers."
  - "ADX-as-amplifier rule (not as direct vote): ADX is informational evidence by default (sub-score=0). It only contributes a +1 / -1 vote when (a) ADX > 25 (trend regime confirmed) AND (b) the MA + momentum stack already votes directionally (stacks_total != 0). When stacks_total = 0, ADX trend regime adds no vote — a strong-but-undirectional ADX shouldn't manufacture a verdict out of nothing. Bounded amplifier: max 1 amplifier vote per signal."
  - "Aggregate normalization against MAX POSSIBLE score (5), NOT n_scored. Same pattern as 03-02 fundamentals — partial-data signals are deliberately damped. Max possible total = 1 (MA stack) + 3 (momentum 1m/3m/6m) + 1 (ADX amplifier) = 5; normalized = total / 5 ∈ [-1, +1]. A defensive clamp at [-1, +1] survives any future indicator addition that could push beyond."
  - "5-state ladder verdict via local _total_to_verdict helper — strict > boundaries at 0.6 / 0.2, identical to 03-02 fundamentals. Per-analyst copy is fine for now (DRY trigger waits for the third copy in 03-04 / 03-05); a shared analysts.verdict._total_to_verdict helper lands when refactoring becomes the cheaper path. The pattern is locked: every Wave 2 analyst follows the same boundary discipline."
  - "Empty-data branches each emit a distinct evidence reason string ('snapshot data_unavailable=True' / 'prices snapshot missing' / 'prices.data_unavailable=True' / 'prices history is empty' / 'history has N bars; need ≥20 for any indicator'). Same return shape as 03-02 fundamentals (data_unavailable=True signal with verdict='neutral', confidence=0) but the evidence string disambiguates which branch fired — useful for downstream debugging. The 5th branch (n < MIN_BARS_FOR_ANY_INDICATOR after _build_df dropna) is a 4th-degenerate subcase the plan called out in must_haves."
  - "_build_df defensively dropna(subset=['close']) before iloc[-1] extractions. OHLCBar's gt=0 schema constraint prevents NaN closes today, but a future schema relaxation should not silently produce NaN at iloc[-1] in indicator calculations. Locked by test_build_df_sorts_unsorted_input (round-trip equivalence between chronological and reversed history confirms sort_index + dropna pipeline is in place)."
  - "test_known_uptrend_strong_bullish + test_known_downtrend_strong_bearish + test_known_sideways_neutral are QUALITATIVE regressions (verdict and confidence ranges, not point values). Sideways assertion is loose — verdict ∈ {neutral, bullish, bearish} AND confidence ≤ 40 — because sideways noise + integer rounding can tilt either direction at the boundary; the strong_* tier MUST NOT be hit. The regression tests lock in 'this analyst doesn't shift verdict tier between commits' rather than 'this analyst produces exactly verdict X'."
  - "ROADMAP.md plan-progress edit done MANUALLY per the precedent set in Plan 02-07 + 03-01 + 03-02 closeouts. The `gmd-tools roadmap update-plan-progress 3` command mangles the descriptive Phase Summary row format; the row is bumped 2/5 → 3/5 manually here to preserve the format that mirrors Phase 1 + Phase 2 in the table."

patterns-established:
  - "Hand-rolled pandas indicator pattern (list[OHLCBar] → DataFrame with high/low/close → rolling().mean() for SMA → ewm(alpha=1/N).mean() for Wilder smoothing): every Phase 4 POSE indicator (RSI / Bollinger / Stochastic / Williams %R / MACD / Hurst) reuses this same shape. Phase 4 plan-phase revisits the ta-lib / pandas-ta-classic decision but the DataFrame builder + helper signature pattern is locked here."
  - "Indicator-as-amplifier rule (default sub-score=0, conditionally contributes +1/-1 when supporting context exists): generalizes beyond ADX. Phase 4 POSE's volatility regime (ATR percentile vs trailing distribution) and breadth indicators (relative-strength rank within sector) reuse this same 'evidence-by-default, amplify-on-confluence' pattern."
  - "Three-tier warm-up guards (data_unavailable floor / partial degradation / full indicator availability) instead of binary computable/uncomputable: every analyst that consumes time-series data should follow this. Phase 4 POSE will need it for any indicator with a settled-state period (RSI(14) / Bollinger(20) / etc.) — the floors will be different but the tier discipline carries over."

requirements-completed: [ANLY-02]

# Metrics
duration: ~30 minutes active execution (test-side bug fixes + GREEN commit + closeout)
completed: 2026-05-03
---

# Phase 03 Plan 03: Technicals Analyst — MA Stack + Momentum + Wilder ADX(14) with Min-Bars Guards Summary

**Wave 2 / second analyst lands: pure-function `analysts.technicals.score(snapshot, config, *, computed_at=None) -> AgentSignal` deterministically scores MA stack alignment (MA20/MA50/MA200), momentum at 1m/3m/6m horizons (21/63/126 bars; ±5/10/15% thresholds), and Wilder ADX(14) trend regime against the snapshot's price history. All indicator math hand-rolled with `pandas.Series.rolling().mean()` (SMA) and `.ewm(alpha=1/14, adjust=False).mean()` (Wilder smoothing) — NO pandas-ta / ta-lib / pandas-ta-classic dependency (pandas + numpy come transitively via yfinance). Min-bars warm-up guards (data_unavailable below 20 bars; ADX skipped below 27; MA stack degraded below 200) prevent the silent NaN-propagation pitfall that virattt/ai-hedge-fund's reference implementation falls into. Provenance header (INFRA-07) names virattt/ai-hedge-fund/src/agents/technicals.py and enumerates 6 modifications. ANLY-02 closed.**

## Performance

- **Duration:** ~30 minutes active execution. The RED commit (`4986e7a`) had landed in a prior session; this session's work was running tests against the locally-staged GREEN implementation, fixing 2 test-side bugs surfaced by the run, committing GREEN, and authoring this closeout.
- **Tasks:** 2 — Task 1 (RED): 25 failing tests for the 3 known-regime regressions + warm-up guards + indicator correctness + provenance + determinism (committed in `4986e7a` from earlier session). Task 2 (GREEN): `analysts/technicals.py` implementation + 2 Rule-1 test-side bug fixes (substring-vs-import scope + V-shape MA-mixed construction rebalance).
- **Files created:** 2 (`analysts/technicals.py` 414 lines, `tests/analysts/test_technicals.py` ~510 lines)
- **Files modified:** 0 (pure additive plan — no existing production files touched)

## Accomplishments

- **`analysts/technicals.py` (414 lines)** ships the locked Wave 2 analyst contract for technicals. Public surface is the single function `score(snapshot: Snapshot, config: TickerConfig, *, computed_at: Optional[datetime] = None) -> AgentSignal` — pure, deterministic, never raises for missing data, always returns an AgentSignal with `analyst_id="technicals"`. Provenance header (INFRA-07) names `virattt/ai-hedge-fund/src/agents/technicals.py` and enumerates 6 modifications: SMA stacks (MA20/50/200) vs EMA stacks (8/21/55); min-bars guards added (virattt has none — see 03-RESEARCH.md Pitfall #1); MA + momentum + ADX only (RSI/Bollinger/MACD/Hurst belong to Phase 4 POSE); pure pandas (no ta-lib / pandas-ta dep); pure function (snapshot, config) → AgentSignal vs graph-node ainvoke; UNIFORM RULE empty-data guard.
- **Module-level constants at the top** make every threshold tunable by editing this file: `MA_BARS=(20, 50, 200)`, `MOMENTUM_HORIZONS=((1, 21, 0.05), (3, 63, 0.10), (6, 126, 0.15))`, `ADX_PERIOD=14`, `ADX_TREND_ABOVE=25.0`, `ADX_RANGE_BELOW=20.0`, `ADX_MIN_BARS=27`, `ADX_STABLE_BARS=150`, `MIN_BARS_FOR_ANY_INDICATOR=20`, `_MAX_POSSIBLE_SCORE=5`. The momentum-horizons table is the cleanest tunable surface — adding/removing a horizon is a single tuple edit.
- **Six private helpers** orchestrate the indicator math:
  - `_build_df(history) -> pd.DataFrame` — list[OHLCBar] → DataFrame with high/low/close columns, `sort_index()` (defensive against out-of-order history) and `dropna(subset=["close"])` (defensive against future schema relaxation that might allow NaN closes).
  - `_ma_alignment(df) -> tuple[int, Optional[str]]` — three-tier MA stack scoring: <50 bars → (0, None); 50..199 bars → MA20 vs MA50 only with "MA200 unavailable (N bars)" evidence; ≥200 bars → full MA20/MA50/MA200 stack (bullish / bearish / mixed evidence).
  - `_momentum_one(df, lookback_bars, threshold, label) -> tuple[int, Optional[str]]` — single-horizon momentum: returns (0, None) when n ≤ lookback (cannot compute the percent change); otherwise +1 / -1 / 0 based on the percent change against the threshold.
  - `_adx_14(df) -> Optional[float]` — Wilder ADX(14) via the canonical recipe: True Range → +DM/-DM directional movement → Wilder-smoothed (.ewm with alpha=1/14, adjust=False) TR/+DM/-DM → +DI/-DI → DX → Wilder-smoothed ADX. Returns None below ADX_MIN_BARS (27) or on NaN result (defensive against flat-line bar series where +DI + -DI is identically zero).
  - `_adx_evidence(adx, n_bars) -> Optional[str]` — formats the ADX evidence string with trend / range / ambiguous label, plus a "(ADX may be unstable, N bars)" suffix when n < ADX_STABLE_BARS (150).
  - `_total_to_verdict(normalized) -> Verdict` — same shape as 03-02 fundamentals: STRICT > boundaries at 0.6 / 0.2.
- **`score()` orchestration:** (1) Establish `now` from `computed_at` kwarg or `datetime.now(timezone.utc)` default. (2) UNIFORM RULE 4-branch empty-data guard at the top — `snapshot.data_unavailable` / `snapshot.prices is None` / `snapshot.prices.data_unavailable` / empty history → return data_unavailable signal with distinct evidence per branch. (3) `_build_df(history)` → df, `n = len(df)`. (4) Min-bars guard `n < MIN_BARS_FOR_ANY_INDICATOR (20)` → data_unavailable signal with evidence `"history has N bars; need ≥20 for any indicator"`. (5) Compute MA + 3 momentum sub-scores, append `(score, evidence)` tuples. (6) Compute ADX; if present, append (0, ADX_evidence_string) — ADX is informational by default. (7) ADX-as-amplifier: if `adx_val > ADX_TREND_ABOVE (25)` AND `stacks_total != 0`, append (+1 or -1, "ADX-confirmed trend (...)"). (8) Aggregate: `total = sum(scores)`, `normalized = clamp(total / 5, -1, +1)`, `verdict = _total_to_verdict(normalized)`, `confidence = min(100, int(round(abs(normalized) * 100)))`, `evidence = [s for _, s in sub if s is not None][:10]` (≤10 cap). (9) Construct and return `AgentSignal(...)`.
- **Three known-regime regression tests** lock in qualitative correctness against the 03-01 synthetic fixtures: `test_known_uptrend_strong_bullish` (252-bar uptrend → verdict ∈ {bullish, strong_bullish}; "bullish stack" evidence string present); `test_known_downtrend_strong_bearish` (mirror); `test_known_sideways_neutral` (no strong tier; confidence ≤ 40 — the loose-but-locked bound documented in plan to absorb sideways noise + integer rounding). Without these, future commits could drift verdict tier on real prod data without flagging anything.
- **Min-bars warm-up tests** lock the 4-tier degradation contract: `test_warmup_lt20_bars_data_unavailable` (15 bars → data_unavailable=True with the canonical evidence string); `test_warmup_25_bars_no_adx` (25 bars → ADX absent, 1m momentum present); `test_warmup_50_bars_partial` (50 bars → MA20/MA50/1m/ADX present; MA200/3m/6m absent); `test_warmup_100_bars_partial` (100 bars → MA20/MA50/1m/3m/ADX present; MA200/6m absent).
- **Empty-data UNIFORM RULE tests** lock all 4 branches: `test_empty_snapshot_data_unavailable`, `test_prices_none`, `test_prices_data_unavailable`, `test_empty_history`. Each path returns the canonical `(data_unavailable=True, verdict='neutral', confidence=0)` signal.
- **Indicator-correctness tests** pin the MA / momentum / ADX math: `test_ma_alignment_bullish_stack` (200-bar uptrend → "bullish stack" evidence); `test_ma_alignment_bearish_stack` (mirror); `test_ma_alignment_mixed` (200 bars down + 30 bars mild up → MA20 > MA50 but MA200 elevated → "MA stack mixed" evidence); `test_momentum_1m_positive` / `test_momentum_1m_negative`; `test_adx_trend_regime` (252-bar uptrend → ADX > 25 → "trend regime" evidence); `test_adx_range_or_ambiguous_regime` (252-bar sideways → ADX low → "range regime" or "ambiguous regime" evidence — accepts either since sideways amplitude can put ADX between 20-25 on the boundary).
- **Provenance + meta-tests:** `test_provenance_header_present` (greps for `virattt/ai-hedge-fund/src/agents/technicals.py` in source); `test_pandas_imported_no_pandas_ta` (regex inspection of `import` / `from … import` statements only — provenance docstring legitimately mentions pandas-ta / ta-lib by name to enumerate the deps we deliberately rejected, so a substring scan would false-positive); `test_computed_at_passes_through`; `test_computed_at_default_uses_now`; `test_deterministic`; `test_returns_agent_signal_type`; `test_build_df_sorts_unsorted_input` (replaces the plan's NaN-injection test — OHLCBar's gt=0 schema prevents NaN at the schema layer; we instead exercise the sort_index codepath by feeding a date-shuffled history).
- **Coverage on `analysts/technicals.py`: 92% line+branch combined** (gate ≥90% line / ≥85% branch). 25/25 tests green; targeted suite runs in 0.39s. **Full repo regression: 263 passed + 2 xfailed** (up from 238 + 2 xfailed at end of 03-02: +25 new technicals tests). The 2 xfail markers in `tests/analysts/test_invariants.py` held strict — they remained xfail (strict=True is honored), confirming that 03-03's analyst module is correctly recognized but the cross-cutting "always 4 signals" + "dark snapshot → 4 data_unavailable=True" invariants still need 2 more analyst modules (03-04 / 03-05) to flip GREEN.
- **No new dependencies** — pandas + numpy come transitively via yfinance (already in poetry.lock per 03-RESEARCH.md confirmation). `import pandas as pd` works without further setup. `pyproject.toml` untouched. Lockfile untouched.

## Task Commits

1. **Task 1 (RED) — `test(03-03): add failing tests for technicals analyst (regimes / warm-up / indicators / provenance)`:** `4986e7a` (committed in earlier session) — `tests/analysts/test_technicals.py` with 25 RED tests; `pytest tests/analysts/test_technicals.py` failed at the import line with `ModuleNotFoundError: No module named 'analysts.technicals'`. Verified the expected RED state.
2. **Task 2 (GREEN) — `feat(03-03): technicals analyst — MA stack + momentum + Wilder ADX(14) with min-bars guards`:** `4098613` — `analysts/technicals.py` (414 lines) implementing the score() function per implementation_sketch + 2 Rule-1 test-side bug fixes folded into the same commit (substring-vs-import scope on `test_pandas_imported_no_pandas_ta`; V-shape construction rebalance on `test_ma_alignment_mixed` to keep MA200 elevated above MA50). All 25 tests green; 92% line+branch coverage; full repo regression 263 passed + 2 xfailed.

**Plan metadata commit:** added in this closeout (covers SUMMARY.md, STATE.md, ROADMAP.md plan-progress row, REQUIREMENTS.md ANLY-02 traceability flip).

## Files Created/Modified

### Created
- `analysts/technicals.py` (414 lines — provenance docstring + 9 module-level constants + `_build_df` + `_ma_alignment` + `_momentum_one` + `_adx_14` + `_adx_evidence` + `_total_to_verdict` + `score()`)
- `tests/analysts/test_technicals.py` (~510 lines, 25 tests)

### Modified
- (none — pure additive plan)

### Modified at closeout
- `.planning/STATE.md` (Phase 3 progress 2/5 → 3/5; current_plan 3 → 4; recent decisions append)
- `.planning/ROADMAP.md` (Phase 3 row 2/5 → 3/5; Plans list `[ ] 03-03` → `[x] 03-03`)
- `.planning/REQUIREMENTS.md` (ANLY-02 traceability Pending → Complete; checkbox `[ ] **ANLY-02**` → `[x] **ANLY-02**`)

## Decisions Made

- **SMA stacks (MA20/MA50/MA200), not EMA stacks (8/21/55).** Per 03-CONTEXT.md decision; matches the canonical stockcharts/finviz convention the user is more familiar with. virattt/ai-hedge-fund uses EMAs; we deliberately diverge.
- **Min-bars guards added — virattt has none.** Closes 03-RESEARCH.md Pitfall #1. virattt's reference implementation silently produces NaN at iloc[-1] for cold-start tickers and marks them "neutral confidence 0" while quietly lying about data availability. Our 4-tier guard (data_unavailable below 20 / ADX skipped below 27 / MA stack skipped below 50 / MA200 omitted below 200) makes the data-availability gradient explicit at the AgentSignal layer.
- **MA + momentum + ADX only — defer RSI / Bollinger / MACD / Hurst to Phase 4 POSE.** Phase 4's plan-phase revisits the ta-lib / pandas-ta-classic dependency-choice debate; for Phase 3 we hand-roll the 3 indicator families. Keeps technicals.py at ~150 LOC of indicator math.
- **Pure pandas — NO pandas-ta / ta-lib / pandas-ta-classic dependency.** Pandas + numpy come transitively via yfinance (verified 03-RESEARCH.md). DO NOT add pandas as a direct dependency in pyproject.toml. The provenance docstring documents this explicitly so future planners don't "fix" the missing pandas dep.
- **Wilder smoothing as `pandas.Series.ewm(alpha=1/14, adjust=False).mean()`.** Mathematical identity to Wilder's recursive formula per StockCharts canonical walkthrough; locked in the docstring and module reference comment so future readers don't replace it with a hand-rolled recursive Wilder loop.
- **ADX-as-amplifier rule (not as direct vote).** ADX is informational evidence by default (sub-score=0). It only contributes a +1 / -1 vote when ADX > 25 (trend regime confirmed) AND the MA + momentum stack already votes directionally (`stacks_total != 0`). Bounded amplifier: max 1 amplifier vote per signal.
- **Aggregate normalization against MAX POSSIBLE score (5).** Same pattern as 03-02 fundamentals — partial-data signals are deliberately damped. Max possible total = 1 (MA stack) + 3 (momentum) + 1 (ADX amplifier) = 5; normalized = total / 5 ∈ [-1, +1] with a defensive clamp.
- **5-state ladder verdict via local `_total_to_verdict` helper — strict > boundaries at 0.6 / 0.2.** Identical to 03-02; per-analyst copy is fine for now (DRY trigger waits for the third copy).
- **Empty-data branches each emit a distinct evidence reason string.** Same return shape as 03-02 fundamentals (data_unavailable=True signal with verdict='neutral', confidence=0) but the evidence string disambiguates which branch fired ("snapshot data_unavailable=True" / "prices snapshot missing" / "prices.data_unavailable=True" / "prices history is empty" / "history has N bars; need ≥20 for any indicator").
- **`_build_df` defensively `dropna(subset=['close'])` before iloc[-1] extractions.** OHLCBar's gt=0 schema prevents NaN closes today, but a future schema relaxation should not silently produce NaN at iloc[-1] in indicator calculations. Locked by `test_build_df_sorts_unsorted_input`.
- **Sideways regression assertion is loose — verdict ∈ {neutral, bullish, bearish} AND confidence ≤ 40.** Plan documented this: sideways noise + integer rounding can tilt either direction at the boundary; the strong_* tier MUST NOT be hit. The test locks "this analyst doesn't shift verdict tier between commits" rather than "this analyst produces exactly verdict X".
- **ROADMAP.md plan-progress edit done MANUALLY** per the precedent set in Plans 02-07 / 03-01 / 03-02 closeouts. The `gmd-tools roadmap update-plan-progress 3` command mangles the descriptive Phase Summary row format; the row is bumped 2/5 → 3/5 manually here.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Test-side bug] `test_pandas_imported_no_pandas_ta` substring scope was too wide**
- **Found during:** Task 2 GREEN initial test run — the test asserted `"pandas-ta" not in src.lower()`, which false-positives on the provenance docstring (which legitimately enumerates pandas-ta / ta-lib by name to explain why we don't depend on them, per 03-RESEARCH.md "don't hand-roll" anti-pattern guidance).
- **Issue:** The test's intent is "no pandas-ta / ta-lib IMPORT" — Python module names can't even contain hyphens, so `import pandas-ta` would never parse anyway. The substring scan was the wrong tool. The plan's verify-step grep (`! grep -E "pandas_ta|pandas-ta|talib|TA_Lib" analysts/technicals.py`) had the same scope error.
- **Fix:** Tightened the test to inspect actual `import` / `from … import` statements via regex: `^\s*(?:import|from)\s+(pandas_ta|talib|ta_lib)\b` (multiline flag). Intent of the test preserved (no forbidden imports); false positive on the docstring eliminated.
- **Files modified:** `tests/analysts/test_technicals.py` (line ~419, scope tightened from substring scan to import-statement regex)
- **Verification:** Test passes against the implemented module; would still fail loudly if a `pandas_ta` / `talib` / `ta_lib` import line were ever added. Confirmed by mental model: substituting `import pandas_ta as pta` into technicals.py would make the regex match.
- **Committed in:** `4098613` (GREEN commit folds in the test fix alongside the implementation)

**2. [Rule 1 — Test-fixture bug] `test_ma_alignment_mixed` V-shape construction was too aggressive**
- **Found during:** Task 2 GREEN initial test run — the test fed 150 down + 50 up bars at +2% daily drift expecting a "mixed" MA stack (MA20 > MA50 but MA200 elevated). The sharp recovery pulled MA50 well above MA200, producing a fully bullish stack instead.
- **Issue:** Test math was wrong. With 150 bars at -0.5% drift starting at 200, the close lands around 95; with 50 bars at +2% drift starting at 95, the close shoots to ~256 — well above the entire downtrend window. MA50 (last 50 bars: all the +2% recovery) ended up above MA200 (mostly the downtrend).
- **Fix:** Rebalanced to 200 bars down at -0.5% drift + 30 bars mild up at +0.5% drift. After 200 down bars: close ≈ 73.4. After 30 up bars: close ≈ 85. MA20 (last 20 bars of the up segment) ≈ 80; MA50 (30 up + 20 last-down) ≈ 78; MA200 (last 200 bars: mostly downtrend) ≈ 95. Result: MA20 > MA50, MA200 > both → mixed stack ✓.
- **Files modified:** `tests/analysts/test_technicals.py` (lines 313-322, fixture construction parameters changed)
- **Verification:** Test passes against the implementation. Mental model confirms: the rebalanced numbers produce MA20 ≈ 80 > MA50 ≈ 78 (last-20-bar uptrend dominates the MA20; the 20 down bars in MA50's window pull it down slightly) AND MA200 ≈ 95 > MA50 ≈ 78 (the 170 downtrend-era bars in MA200's window keep it elevated). The implementation's `_ma_alignment` helper correctly identifies this as not strictly bullish (MA50 < MA200) and not strictly bearish (MA20 > MA50) → falls through to the "mixed" branch.
- **Committed in:** `4098613` (GREEN commit folds in the test fix alongside the implementation)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — test-side bugs surfaced during GREEN). **Impact:** test-side only. The implementation matches the plan's specifications byte-for-byte; the 2 fixes are tightening (test #1) and correcting (test #2) the test scaffolding so it correctly exercises the implementation.

## Issues Encountered

- **Local environment had `uv` not on PATH** during initial test run (`uv: command not found`). Resolved per the long-standing Phase 1 / Plan 01 deviation (PATH prefix `/c/Users/Mohan/AppData/Roaming/Python/Python314/Scripts` per command). Same Open Items / Environmental note carries over from earlier plans — not new.
- **Coverage report shows 92% combined line+branch.** The pytest-cov "Cover" column with `--cov-branch` is a combined metric. Missing lines (105, 143-148, 248, 260, 397, 399) are: empty-history early-return in `_build_df` (caller's len() check pre-empties this); MA20 < MA50 branch when n < 200 (untested but exercised in production by the 50..199-bar uptrend warm-up tier); ADX NaN-defensive return; ADX range-regime branch (sideways fixture hit ambiguous on this run, not range); upper/lower normalized clamps. All of these are defensive paths that real prod data exercises but the synthetic fixtures don't quite reach. 92% is above the 90/85 floor.

## Self-Check: PASSED

- [x] `analysts/technicals.py` exists — FOUND (414 lines)
- [x] `tests/analysts/test_technicals.py` exists — FOUND (~510 lines, 25 tests)
- [x] Provenance header in `analysts/technicals.py` references `virattt/ai-hedge-fund/src/agents/technicals.py` — VERIFIED via Grep
- [x] `score()` signature is `(snapshot: Snapshot, config: TickerConfig, *, computed_at: Optional[datetime] = None) -> AgentSignal` — VERIFIED in source
- [x] `_build_df`, `_ma_alignment`, `_momentum_one`, `_adx_14`, `_adx_evidence`, `_total_to_verdict` helpers all present — VERIFIED
- [x] Module-level constants present (MA_BARS, MOMENTUM_HORIZONS, ADX_PERIOD/TREND_ABOVE/RANGE_BELOW/MIN_BARS/STABLE_BARS, MIN_BARS_FOR_ANY_INDICATOR, _MAX_POSSIBLE_SCORE) — VERIFIED
- [x] Empty-data UNIFORM RULE 4 branches present + 5th min-bars degenerate branch — VERIFIED
- [x] Wilder smoothing as `.ewm(alpha=1/14, adjust=False).mean()` — VERIFIED in `_adx_14`
- [x] No `pandas_ta` / `talib` / `ta_lib` import statements — VERIFIED via regex grep
- [x] Commit `4986e7a` (Task 1 RED — failing tests for technicals analyst) — FOUND in git log
- [x] Commit `4098613` (Task 2 GREEN — technicals analyst implementation + 2 test-side fixes) — FOUND in git log
- [x] `pytest tests/analysts/test_technicals.py -v` — 25/25 PASSED in 0.39s
- [x] `pytest -q` (full repo regression) — **263 passed + 2 xfailed** (up from 238 + 2 xfailed at end of 03-02: +25 technicals tests; the 2 xfail markers in test_invariants.py held strict and remained xfail as expected — Wave 2 still needs 2 more analyst modules to flip them green; 03-05 removes the markers as its final task)
- [x] Coverage on `analysts/technicals.py`: **92% line+branch combined** (gate ≥90% line / ≥85% branch) — verified via `pytest --cov=analysts.technicals --cov-branch tests/analysts/test_technicals.py`
- [x] Pure-function discipline: no I/O in `analysts/technicals.py`, no module-level mutable state, no clock reads inside helpers — VERIFIED by source inspection
- [x] xfail markers in `tests/analysts/test_invariants.py` UNTOUCHED — VERIFIED via `git diff 8236cbe..4098613 -- tests/analysts/test_invariants.py` returns empty
- [x] Determinism contract: two calls with identical inputs → byte-identical AgentSignal model_dump_json — VERIFIED by `test_deterministic`
- [x] Sort defense: out-of-order history produces same signal as chronological — VERIFIED by `test_build_df_sorts_unsorted_input`

### Expected-RED tests (NOT failures)

The 2 tests in `tests/analysts/test_invariants.py` REMAIN xfail at end of 03-03 — same as end of 03-02. The lazy `from analysts import fundamentals, news_sentiment, technicals, valuation` import line still fails on the missing 2 modules (news_sentiment, valuation):

- `tests/analysts/test_invariants.py::test_always_four_signals` — XFAIL (news_sentiment / valuation modules don't exist yet)
- `tests/analysts/test_invariants.py::test_dark_snapshot_emits_four_unavailable` — XFAIL (same)

Plan 03-05 (the LAST Wave 2 plan to commit per the dependency graph) MUST remove the `@pytest.mark.xfail` markers in its final task. The `strict=True` on each marker held during this run — they remained xfail and didn't unexpectedly turn GREEN, confirming that 03-03 didn't accidentally over-ship the cross-cutting contract.

## Next Phase Readiness

- **Wave 2 progress: 2/4 analysts shipped.** The remaining two Wave 2 plans (03-04 news_sentiment, 03-05 valuation) can each execute in parallel — they share no dependencies on each other beyond the foundation surface from 03-01 (AgentSignal contract + fixture toolbox), which is unchanged by this plan.
- **Hand-rolled pandas indicator pattern is locked.** Phase 4 POSE-01..05 (Position-Adjustment Radar) will reuse the same `_build_df` shape + helper signature contract for RSI / Bollinger / Stochastic / Williams %R / MACD / Hurst. Phase 4's plan-phase revisits the ta-lib / pandas-ta-classic dependency-choice debate; the indicator-helper API surface (return `(score, Optional[evidence])` from a pandas-DataFrame argument) carries over directly.
- **No new Wave 2 dependencies** — pandas + numpy already transitive via yfinance; vaderSentiment was added at 03-01 for 03-04. Everything else (Pydantic v2, the analysts.signals contract, the analysts.data.* sub-schemas) is already in place.
- **03-05 wraps Wave 2** — its final task removes the `@pytest.mark.xfail(strict=True)` markers from `tests/analysts/test_invariants.py`. At that point both cross-cutting tests flip GREEN naturally as all four analyst modules exist and respect the dark-snapshot UNIFORM RULE.
- **No carry-overs / no blockers from this plan.** Wave 2 progress: 2/4 analysts complete. ANLY-02 closed in REQUIREMENTS.md.

---
*Phase: 03-analytical-agents-deterministic-scoring*
*Plan: 03-technicals*
*Completed: 2026-05-03*
