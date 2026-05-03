---
phase: 03-analytical-agents-deterministic-scoring
plan: 02
subsystem: analysts
tags: [phase-3, analyst, fundamentals, tdd, pure-function, anly-01, wave-2]

# Dependency graph
requires:
  - phase: 03-analytical-agents-deterministic-scoring
    plan: 01
    provides: analysts.signals.AgentSignal (5-state Verdict ladder + 0-100 confidence + evidence list + data_unavailable invariant), analysts.signals.Verdict + AnalystId Literals, tests/analysts/conftest.py (frozen_now / make_snapshot / make_ticker_config fixtures)
  - phase: 02-ingestion-keyless-data-plane
    plan: 01
    provides: analysts.data.fundamentals.FundamentalsSnapshot (5 scored metrics — pe, ps, roe, debt_to_equity, profit_margin — plus data_unavailable bool)
  - phase: 02-ingestion-keyless-data-plane
    plan: 06
    provides: analysts.data.snapshot.Snapshot (per-ticker aggregate carrying optional fundamentals sub-field plus snapshot-level data_unavailable bool)
  - phase: 01-foundation-watchlist-per-ticker-config
    plan: 02
    provides: analysts.schemas.TickerConfig + FundamentalTargets (per-ticker pe_target / ps_target overrides — pb_target carried but ignored in v1 since FundamentalsSnapshot has no pb scoring path)
provides:
  - "analysts.fundamentals.score(snapshot, config, *, computed_at=None) -> AgentSignal — pure function, no I/O, no module-level mutable state, never raises for missing data"
  - "Per-config (FundamentalTargets.pe_target / ps_target) + hard-coded fallback band scoring across 5 metrics: P/E, P/S, ROE, debt/equity, profit_margin"
  - "5-state ladder verdict via _total_to_verdict(normalized) helper — strict > boundaries at 0.6 / 0.2 (so normalized=0.6 maps to bullish NOT strong_bullish — locked by test_5_state_ladder_bullish_partial)"
  - "Per-metric isolation: a None input on any metric contributes 0 to aggregate AND emits no evidence string, but the other 4 metrics still score normally"
  - "Empty-data UNIFORM RULE: snapshot.data_unavailable=True OR snapshot.fundamentals=None OR snapshot.fundamentals.data_unavailable=True returns AgentSignal(data_unavailable=True, verdict='neutral', confidence=0, evidence=[<reason>])"
  - "Defensive case: when all 5 metrics are None despite snapshot.fundamentals.data_unavailable=False, return data_unavailable signal with evidence='all 5 fundamentals metrics missing' (closes the upstream-bug branch)"
  - "Module-level threshold constants at top of analysts/fundamentals.py (PE_BULLISH_BELOW=15.0, PE_BEARISH_ABOVE=30.0, PS/ROE/DE/PM bands, PER_CONFIG_BAND=0.20, _MAX_POSSIBLE_SCORE=5) — tunable by editing this file"
  - "Provenance header (INFRA-07) names virattt/ai-hedge-fund/src/agents/fundamentals.py and enumerates 6 modifications (5-metric vs 13-metric, per-config target_multiples overrides, module-level constants vs inline literals, 5-state vs 3-state Verdict, pure function vs graph node, UNIFORM RULE empty-data guard)"
affects: [phase-3-plan-03-technicals-analyst, phase-3-plan-04-news-sentiment-analyst, phase-3-plan-05-valuation-analyst, phase-5-claude-routine (reads AgentSignal from disk via JSON)]

# Tech tracking
tech-stack:
  added: []  # No new dependencies — uses only stdlib + Pydantic v2 + the analysts.signals contract from 03-01
  patterns:
    - "Pure-function analyst pattern locked: score(snapshot, config, *, computed_at=None) -> AgentSignal. No I/O, no module-level mutable state, no clock reads inside helpers, never raises for missing data. The next 3 Wave 2 analysts (03-03 / 03-04 / 03-05) follow this exact shape."
    - "Per-metric helper pattern: each `_score_<metric>(value, [target]) -> tuple[int, Optional[str]]` returns (score in {-1, 0, +1}, evidence string OR None). None evidence == 'metric was not readable, do not include in evidence list'. Non-None evidence (even with score=0) == 'metric was readable, include the explanatory string'. Pattern keeps per-metric isolation explicit at the helper boundary."
    - "Per-config override gating: the helper signature differentiates metrics that CAN take per-config overrides (P/E, P/S — both helpers accept Optional[target]) from metrics that CAN'T (ROE / D/E / profit_margin — no target parameter). When the FundamentalTargets schema gains roe_target / de_target / pm_target in some future v1.x, only the helper signatures change, not the orchestration in score()."
    - "Verdict tiering as a private helper: _total_to_verdict(normalized: float) -> Verdict isolates the 5-state ladder mapping. Strict > boundaries at 0.6 and 0.2 chosen deliberately so that normalized=0.6 (3/5 bullish) maps to 'bullish' not 'strong_bullish' — locked by test_5_state_ladder_bullish_partial. Reusable shape for the next 3 Wave 2 analysts (each will copy this helper or import it once a thresholds module emerges in v1.x)."
    - "Aggregate normalization against MAX POSSIBLE score (5), not n_scored: partial-data signals are deliberately damped. A single +1 metric out of 5 (with 4 None) gives normalized=0.2 (boundary 'neutral'), not normalized=1.0 (strong_bullish). Matches the per-metric isolation contract — missing data shouldn't be amplified."
    - "Empty-data UNIFORM RULE guard at function top: 3 short-circuit branches in priority order (snapshot.data_unavailable -> fundamentals=None -> fundamentals.data_unavailable=True), each emitting a distinct evidence reason string for diagnostic clarity. The defensive 4th branch (n_scored == 0 after sub-scoring) catches the upstream-bug case where data_unavailable=False but every metric is None."

key-files:
  created:
    - "analysts/fundamentals.py (265 lines — provenance docstring + 11 module-level constants + 5 per-metric helpers + _total_to_verdict + score() function)"
    - "tests/analysts/test_fundamentals.py (392 lines, 26 tests covering happy / fallback / per-metric isolation / 3 empty-data branches / 5-state ladder edges / provenance / computed_at / ticker normalization / determinism)"
  modified: []  # No existing files touched — this is a pure additive plan

key-decisions:
  - "Aggregate normalization divides by max possible score (5), NOT by n_scored (count of readable metrics). Means partial-data signals are damped: 1 bullish + 4 None = normalized 0.2 (boundary, neutral) rather than 1.0 (strong_bullish). Matches the per-metric isolation contract — missing data shouldn't be amplified into a strong verdict. Locked by test_per_metric_isolation_pe_missing (4/5 bullish + 1 None -> verdict='strong_bullish' with confidence 80, NOT 100) and the implicit test that wasn't written but the math guarantees: 1 bullish + 4 None -> normalized 0.2 -> neutral."
  - "5-state ladder boundaries are STRICT > (not >=). Means normalized=0.6 (3/5 bullish from test_5_state_ladder_bullish_partial) maps to 'bullish' not 'strong_bullish'; normalized=0.2 maps to 'neutral' not 'bullish'. Forces the 'strong' verdicts to require GENUINELY strong consensus (≥4/5 directional). The boundary case is locked by test_5_state_ladder_bullish_partial; the symmetric bearish boundary by test_5_state_ladder_bearish_partial."
  - "Per-metric helper signatures explicitly differentiate metrics that take per-config overrides from those that don't. _score_pe and _score_ps accept Optional[target]; _score_roe / _score_de / _score_pm do not. Avoids the temptation to pass `None` for unsupported metrics (which would silently work but mislead readers about the FundamentalTargets schema surface). When a future v1.x amends FundamentalTargets to add roe_target etc., the helper signatures change in lockstep."
  - "Empty-data branches each emit a distinct evidence reason string ('snapshot data_unavailable=True' / 'fundamentals snapshot missing' / 'fundamentals.data_unavailable=True' / 'all 5 fundamentals metrics missing'). Same return shape (data_unavailable=True signal with verdict='neutral', confidence=0) but the evidence string disambiguates which branch fired — useful when debugging downstream consumers that see a data_unavailable signal and want to know WHY."
  - "All evidence strings stay well under the 200-char per-string cap (longest is ~60 chars in practice — 'P/E 30.0 vs target 20 — overvalued by 50%'). Evidence list count tops out at 5 (one per metric), well under the AgentSignal max_length=10 cap. The two AgentSignal hard caps (≤10 items, ≤200 chars/item) are not load-bearing for this analyst — left as defense in depth."
  - "Per-config band is symmetric ±20% around the user's target. Means pe_target=20 + actual pe=22 (10% above) is still 'near target' (score 0); pe=24 (20% above, on boundary) is also 'near target'; pe=24.01 (>20%) flips to 'overvalued'. Symmetric simplifies user reasoning ('I set my pe_target = my fair-value estimate; ±20% is the no-action zone') and matches the symmetric strict-boundary discipline of the 5-state ladder helper."
  - "computed_at follows 03-01 AgentSignal contract exactly: explicit kwarg override (for reproducible test assertions) OR datetime.now(timezone.utc) default (for production callers). The default branch is exercised by test_computed_at_default_uses_now (asserts before <= signal.computed_at <= after). Pure-function discipline preserved — no module-level clock state, no global side effects."
  - "Confidence is min(100, int(round(abs(normalized) * 100))). The min() cap is defensive (max possible normalized is exactly 1.0 with 5/5 directional, and round(100.0) is exactly 100, so the cap never fires from internal math — it's there to survive any future refactor that loosens the normalizer). Test_5_state_ladder_strong_bullish locks confidence==100 at the all-5-bullish edge."
  - "26 tests committed (above plan's >=18 floor). The 3 extra tests over the plan-suggested 23 are: test_returns_agent_signal_type (smoke that score() returns AgentSignal type), test_determinism_two_calls_identical (two identical calls produce identical model_dump), and the 2 added during execution to clear the coverage gate (test_per_config_ps_bearish_overvalued + test_per_config_ps_neutral_within_band — without them coverage stayed at 96% line / 98% branch, above the gate but the 2 untested branches were real per-config P/S behaviors the plan promised)."
  - "Module-level _MAX_POSSIBLE_SCORE = 5 is a private constant (leading underscore) used by the normalizer. Kept private because it's a derivation (== number of metrics scored), not a tunable threshold. Future amendments that change the metric list MUST update this constant in the same commit — the normalizer would silently wrong-result if metric count changed but the divisor didn't."
  - "ROADMAP.md plan-progress edit done MANUALLY per the precedent set in Plan 02-07 + 03-01 closeouts. The `gmd-tools roadmap update-plan-progress 3` command mangles the descriptive Phase Summary row format (replaces named cells with bare counters), so the row is bumped 1/5 -> 2/5 manually here to preserve the format that mirrors Phase 1 + Phase 2 in the table."
  - "ANLY-01 traceability table entry in REQUIREMENTS.md flipped Pending -> Complete. Wave 2's other three analyst plans (03-03 / 03-04 / 03-05) will close the remaining ANLY-02 / ANLY-03 / ANLY-04 entries; the cross-cutting xfail invariants in tests/analysts/test_invariants.py remain xfail (strict=True held — verified by the regression run) and will flip GREEN naturally when 03-05 ships and removes the markers as its final task."

patterns-established:
  - "Pure-function analyst score() with empty-data UNIFORM RULE guard at top: every Wave 2 analyst module follows this exact shape. The 3-branch guard (snapshot.data_unavailable / sub-field None / sub-field.data_unavailable=True) generalizes — technicals checks snapshot.prices, news_sentiment checks snapshot.news, valuation checks all of (snapshot.prices, snapshot.fundamentals, config.thesis_price, config.target_multiples). Distinct evidence reason strings per branch help downstream debugging."
  - "Per-metric helper returning (score, Optional[evidence_string]) with None-evidence meaning 'not readable, exclude from evidence list': makes per-metric isolation explicit at the helper signature, not buried in score() orchestration. Reused by 03-04 (per-headline VADER score returning None when headline is undated and gets dropped from recency window) and 03-05 (per-tier valuation contribution returning None when that tier wasn't configured)."
  - "Strict > boundaries on the 5-state ladder helper (instead of >=): forces 'strong' verdicts to require ≥4/5 directional consensus (not ≥3/5). Keeps the strong tiers from over-firing on 60/40 splits. Reused verbatim by 03-03 / 03-04 / 03-05 — eventually a shared analysts.verdict._total_to_verdict helper lands when the second analyst module copies it (DRY trigger), but the per-analyst copy is fine for now."
  - "Aggregate normalization against MAX POSSIBLE score (constant divisor), NOT against n_scored (variable divisor): damps partial-data signals, matches the per-metric isolation contract. Pattern reused by 03-03 (3 sub-scores: MA stack, momentum, ADX trend gating — divisor = 3) and 03-05 (3 tiers: thesis_price, target_multiples, consensus — divisor = 3)."

requirements-completed: [ANLY-01]

# Metrics
duration: ~2 hours active execution (TDD RED + GREEN + 2 coverage-clearing tests + closeout)
completed: 2026-05-03
---

# Phase 03 Plan 02: Fundamentals Analyst — 5-Metric Per-Config + Fallback Band Scoring Summary

**Wave 2 / first analyst lands: pure-function `analysts.fundamentals.score(snapshot, config, *, computed_at=None) -> AgentSignal` deterministically scores P/E, P/S, ROE, debt/equity, profit margin against per-`TickerConfig.target_multiples` overrides (when set) or hard-coded fallback bands; emits one AgentSignal per call with 5-state ladder verdict + 0-100 confidence + per-metric evidence list. Per-metric isolation (missing one metric does not poison the others), empty-data UNIFORM RULE (3 short-circuit branches each emitting a distinct reason string), and module-level tunable threshold constants are all locked at the schema layer. Provenance header (INFRA-07) names virattt/ai-hedge-fund/src/agents/fundamentals.py and enumerates 6 modifications. ANLY-01 closed.**

## Performance

- **Duration:** ~2 hours active execution including TDD RED + GREEN + 2 coverage-clearing P/S tests + closeout. (The full-suite regression wall clock was inflated by stalled python processes from earlier sessions; the actual test suite runs in well under 1 minute.)
- **Tasks:** 2 — Task 1 (RED): write 24 failing tests; Task 2 (GREEN): implement analysts/fundamentals.py + add 2 supplementary P/S tests to clear coverage gate.
- **Files created:** 2 (`analysts/fundamentals.py` 265 lines, `tests/analysts/test_fundamentals.py` 392 lines)
- **Files modified:** 0 (this is a pure additive plan — no existing files touched aside from the docs touch-ups in this closeout)

## Accomplishments

- **`analysts/fundamentals.py` (265 lines)** ships the locked Wave 2 analyst contract for fundamentals. Public surface is the single function `score(snapshot: Snapshot, config: TickerConfig, *, computed_at: Optional[datetime] = None) -> AgentSignal` — pure, deterministic, never raises for missing data, always returns an AgentSignal with `analyst_id="fundamentals"`. Provenance header (INFRA-07) names `virattt/ai-hedge-fund/src/agents/fundamentals.py` and enumerates 6 modifications (5-metric vs 13-metric; per-`TickerConfig.target_multiples` overrides; module-level threshold constants; 5-state Verdict; pure function vs graph node; UNIFORM RULE empty-data guard).
- **Module-level threshold constants at the top of the file** make every directional band tunable by editing this file: `PE_BULLISH_BELOW=15.0`, `PE_BEARISH_ABOVE=30.0`, `PS_BULLISH_BELOW=2.0`, `PS_BEARISH_ABOVE=8.0`, `ROE_BULLISH_ABOVE=0.15`, `ROE_BEARISH_BELOW=0.05`, `DE_BULLISH_BELOW=0.5`, `DE_BEARISH_ABOVE=1.5`, `PM_BULLISH_ABOVE=0.15`, `PM_BEARISH_BELOW=0.05`, `PER_CONFIG_BAND=0.20`, `_MAX_POSSIBLE_SCORE=5`. ROE / profit_margin are decimal (0.15 == 15%), matching the FundamentalsSnapshot field convention.
- **Five private per-metric helpers** (`_score_pe`, `_score_ps`, `_score_roe`, `_score_de`, `_score_pm`) each return `tuple[int, Optional[str]]` — score in {-1, 0, +1} plus an optional evidence string. None evidence means "metric was not readable, do not include in evidence list"; non-None evidence (even with score=0) means "metric was readable, include the explanatory string". `_score_pe` and `_score_ps` accept an optional `target` parameter (drawn from `config.target_multiples.pe_target` / `.ps_target`); `_score_roe` / `_score_de` / `_score_pm` have no target parameter (FundamentalTargets schema does not carry roe_target / de_target / pm_target in v1).
- **Per-config band is symmetric ±20%** around the user's stated target: `target * 0.8 < pe < target * 1.2` is "near target" (score 0); `pe < target * 0.8` is "undervalued" (+1); `pe > target * 1.2` is "overvalued" (-1). Wording in evidence strings is "P/E 15.0 vs target 20 — undervalued by 25%". Fallback path (target is None — either `config.target_multiples=None` or `pe_target=None` inside `FundamentalTargets`) uses module-level bands: `pe < PE_BULLISH_BELOW` is "below 15 bullish band", `pe > PE_BEARISH_ABOVE` is "above 30 bearish band", in between is "neutral band".
- **`_total_to_verdict(normalized: float) -> Verdict`** maps the normalized aggregate to the 5-state ladder using STRICT > boundaries (not >=) at 0.6 and 0.2: `normalized > 0.6` → `strong_bullish`; `normalized > 0.2` → `bullish`; `normalized < -0.6` → `strong_bearish`; `normalized < -0.2` → `bearish`; otherwise `neutral`. Strict boundaries are locked by `test_5_state_ladder_bullish_partial` (3/5 bullish → normalized=0.6 → bullish, NOT strong_bullish) and `test_5_state_ladder_bearish_partial` (-2/5 bearish → normalized=-0.4 → bearish).
- **`score()` orchestration:** (1) Establish `now` from `computed_at` kwarg or `datetime.now(timezone.utc)` default. (2) UNIFORM RULE 3-branch guard at the top — `snapshot.data_unavailable=True` → return data_unavailable signal with evidence `["snapshot data_unavailable=True"]`; `snapshot.fundamentals is None` → evidence `["fundamentals snapshot missing"]`; `snapshot.fundamentals.data_unavailable=True` → evidence `["fundamentals.data_unavailable=True"]`. (3) Read `pe_target` / `ps_target` from `config.target_multiples` (Optional). (4) Run 5 per-metric helpers, collect `(score, evidence)` tuples. (5) Defensive 4th branch — `n_scored == 0` (every metric None despite snapshot.fundamentals.data_unavailable=False) → return data_unavailable signal with evidence `["all 5 fundamentals metrics missing"]`. (6) Aggregate: `total = sum(scores)`, `normalized = total / _MAX_POSSIBLE_SCORE` (5), `verdict = _total_to_verdict(normalized)`, `confidence = min(100, int(round(abs(normalized) * 100)))`, `evidence = [e for _, e in sub if e is not None]`. (7) Construct and return `AgentSignal(...)`.
- **Per-metric isolation** is structurally enforced — a None metric input contributes 0 to the aggregate AND emits no evidence string, but the other 4 metrics still score normally. Locked by `test_per_metric_isolation_pe_missing` (pe=None + 4 bullish other metrics → verdict='strong_bullish' with confidence=80; evidence list has 4 strings, none mentioning P/E). Aggregate normalization divides by `_MAX_POSSIBLE_SCORE` (5), NOT by `n_scored` (count of readable metrics) — so partial-data signals are deliberately damped (1 bullish + 4 None → normalized=0.2 → neutral, NOT strong_bullish).
- **`tests/analysts/test_fundamentals.py` (392 lines, 26 tests)** ships above the plan's ≥18 floor. Coverage breakdown:
  - Per-config (target_multiples) path: `test_per_config_pe_bullish_undervalued`, `test_per_config_pe_bearish_overvalued`, `test_per_config_pe_neutral_within_band`, `test_per_config_ps_bullish_undervalued`, `test_per_config_ps_bearish_overvalued`, `test_per_config_ps_neutral_within_band` (the last 2 added during execution to clear coverage gate)
  - Fallback band path: `test_fallback_pe_bullish`, `test_fallback_pe_bearish`, `test_fallback_pe_neutral`, `test_fallback_path_when_only_ps_target_set` (verifies P/E falls through to fallback when only ps_target is set in FundamentalTargets)
  - Per-metric isolation: `test_per_metric_isolation_pe_missing` (4 bullish + pe=None → strong_bullish confidence=80, no P/E evidence string), `test_per_metric_isolation_all_missing` (5 None + data_unavailable=False → defensive data_unavailable signal)
  - Empty-data UNIFORM RULE (3 branches): `test_empty_data_snapshot_data_unavailable_true`, `test_empty_data_fundamentals_none`, `test_empty_data_fundamentals_data_unavailable_true`
  - 5-state ladder mapping: `test_5_state_ladder_strong_bullish` (5/5 bullish → strong_bullish, confidence=100), `test_5_state_ladder_strong_bearish`, `test_5_state_ladder_neutral` (5 in neutral band → neutral, confidence=0, evidence=5 strings), `test_5_state_ladder_bullish_partial` (3/5 bullish → bullish, confidence=60 — the boundary case for the strict > 0.6 check), `test_5_state_ladder_bearish_partial`
  - Provenance + meta: `test_provenance_header_present` (greps for `virattt/ai-hedge-fund/src/agents/fundamentals.py` in source), `test_computed_at_passes_through`, `test_computed_at_default_uses_now`, `test_ticker_normalized_in_signal` (snapshot.ticker='brk.b' → signal.ticker=='BRK-B' via AgentSignal field validator), `test_returns_agent_signal_type`, `test_determinism_two_calls_identical` (two calls with identical inputs → identical model_dump)
- **Coverage on `analysts/fundamentals.py`: 100% line / 100% branch** (gate ≥90% / ≥85%). 26/26 tests green; targeted suite runs in 0.07s. **Full repo regression: 238 passed + 2 xfailed** (up from 212 passed + 2 xfailed at end of 03-01: +26 fundamentals tests). The 2 xfail markers in `tests/analysts/test_invariants.py` held strict — they remained xfail (strict=True is honored), confirming that 03-02's analyst module is correctly recognized but the cross-cutting "always 4 signals" + "dark snapshot → 4 data_unavailable=True" invariants still need 3 more analyst modules (03-03 / 03-04 / 03-05) to flip GREEN.
- **No new dependencies** — uses only stdlib (`datetime`, `typing.Optional`) plus the analysts.signals contract from 03-01 and the existing analysts.data.snapshot.Snapshot + analysts.schemas.TickerConfig. Pyproject.toml untouched. Lockfile untouched.
- **No existing files modified** — this is a pure additive plan. The two docs touched in closeout (`.planning/STATE.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`) are project-state files, not production code or schema.

## Task Commits

1. **Task 1 (RED) — `test(03-02): add failing tests for fundamentals analyst (happy / fallback / per-metric / empty / 5-state ladder)`:** `a887176` — tests/analysts/test_fundamentals.py with 24 RED tests; `python -m pytest tests/analysts/test_fundamentals.py` fails at the import line with `ModuleNotFoundError: No module named 'analysts.fundamentals'`. Verified the expected RED state.
2. **Task 2 (GREEN) — `feat(03-02): fundamentals analyst — 5-metric per-config + fallback band scoring with 5-state verdict`:** `ef8af69` — analysts/fundamentals.py (265 lines) implementing the score() function per implementation_sketch + 2 supplementary P/S tests (`test_per_config_ps_bearish_overvalued`, `test_per_config_ps_neutral_within_band`) added to clear the coverage gap on lines 116-119 (per-config P/S overvalued and near-target branches). All 26 tests green; 100% line / 100% branch coverage; full repo regression 238 passed + 2 xfailed.

**Plan metadata commit:** added in this closeout (covers SUMMARY.md, STATE.md, ROADMAP.md plan-progress row, REQUIREMENTS.md ANLY-01 traceability flip).

## Files Created/Modified

### Created
- `analysts/fundamentals.py` (265 lines — provenance docstring + 12 module-level constants + 5 per-metric helpers + _total_to_verdict + score())
- `tests/analysts/test_fundamentals.py` (392 lines, 26 tests)

### Modified
- (none — pure additive plan)

### Modified at closeout
- `.planning/STATE.md` (Phase 3 progress 1/5 → 2/5; current_plan 2 → 3; recent decisions append)
- `.planning/ROADMAP.md` (Phase 3 row 1/5 → 2/5; Plans list `[ ] 03-02` → `[x] 03-02`)
- `.planning/REQUIREMENTS.md` (ANLY-01 traceability Pending → Complete; checkbox `[ ] **ANLY-01**` → `[x] **ANLY-01**`)

## Decisions Made

- **Aggregate normalization divides by max possible score (5), NOT by n_scored.** Means a single bullish metric out of 5 (with 4 None) gives normalized=0.2 (boundary, neutral) rather than 1.0 (strong_bullish). Damps partial-data signals — matches the per-metric isolation contract that "missing one metric doesn't poison the others" (and conversely, "1 readable bullish metric isn't enough to call the verdict strong_bullish either"). Locked by `test_per_metric_isolation_pe_missing` (4/5 bullish → confidence 80, NOT 100).
- **5-state ladder boundaries are STRICT > (not >=).** `normalized=0.6` (3/5 bullish) maps to `'bullish'` not `'strong_bullish'`; `normalized=0.2` maps to `'neutral'` not `'bullish'`. Forces "strong" verdicts to require GENUINELY strong consensus (≥4/5 directional). Boundary cases locked by `test_5_state_ladder_bullish_partial` and `test_5_state_ladder_bearish_partial`.
- **Per-metric helper signatures explicitly differentiate metrics that take per-config overrides from those that don't.** `_score_pe` and `_score_ps` accept `Optional[target]`; `_score_roe` / `_score_de` / `_score_pm` have no target parameter. Avoids passing `None` for unsupported metrics (which would silently work but mislead readers about the FundamentalTargets schema surface — the schema currently has only pe_target / ps_target / pb_target, and pb is unused in v1 since FundamentalsSnapshot has no pb scoring path). When a future v1.x amends FundamentalTargets to add roe_target etc., the helper signatures change in lockstep.
- **Empty-data branches each emit a distinct evidence reason string.** Same return shape (data_unavailable=True signal with verdict='neutral', confidence=0) but the evidence string disambiguates which of the 4 paths fired ("snapshot data_unavailable=True" / "fundamentals snapshot missing" / "fundamentals.data_unavailable=True" / "all 5 fundamentals metrics missing"). Useful when debugging downstream consumers that see a data_unavailable signal and want to know WHY without re-walking the analyst's branches.
- **Per-config band is symmetric ±20% around the user's target.** Means `pe_target=20 + actual pe=22` (10% above) is still "near target" (score 0); `pe=24` (20% above, exactly on boundary) is also "near target" (since the helper uses `>` strict, not `>=`); `pe=24.01` flips to "overvalued". Symmetric simplifies user reasoning ("I set pe_target = my fair-value estimate; ±20% is the no-action zone") and matches the symmetric strict-boundary discipline of the 5-state ladder helper.
- **`computed_at` follows 03-01 AgentSignal contract exactly:** explicit kwarg override (for reproducible test assertions) OR `datetime.now(timezone.utc)` default (for production callers). Default branch is exercised by `test_computed_at_default_uses_now` (asserts `before <= signal.computed_at <= after`). Pure-function discipline preserved — no module-level clock state, no global side effects, no helper-internal time reads.
- **Confidence cap is `min(100, int(round(abs(normalized) * 100)))`.** The min() cap is defensive — max possible normalized is exactly 1.0 with 5/5 directional, and `round(100.0) == 100`, so the cap never fires from internal math. It survives any future refactor that loosens the normalizer (e.g. weighted aggregation that could produce normalized > 1.0). `test_5_state_ladder_strong_bullish` locks `confidence == 100` at the all-5-bullish edge.
- **26 tests committed (above plan's ≥18 floor).** The plan suggested 18 named test functions; we committed 24 in the RED commit, then added 2 P/S coverage-clearing tests in the GREEN commit (`test_per_config_ps_bearish_overvalued`, `test_per_config_ps_neutral_within_band`) — without them the coverage stayed at 96% line / 98% branch (above the gate, but the 2 untested branches are real per-config P/S behaviors the plan promised). The other 6 over-the-floor tests are the 5 5-state-ladder edges (planned) plus `test_returns_agent_signal_type` + `test_determinism_two_calls_identical` (smoke + determinism guards added during RED writing).
- **Module-level `_MAX_POSSIBLE_SCORE = 5` is a private constant** (leading underscore) used by the normalizer. Kept private because it's a derivation (== number of metrics scored), not a tunable threshold. Future amendments that change the metric list MUST update this constant in the same commit — the normalizer would silently wrong-result if metric count changed but the divisor didn't (e.g. if v1.x adds a 6th metric without bumping `_MAX_POSSIBLE_SCORE`, every 5/5 bullish signal would normalize to 5/6 = 0.83 → still strong_bullish, but every bullish boundary would shift).
- **ROADMAP.md plan-progress edit done MANUALLY** per the precedent set in Plan 02-07 + 03-01 closeouts. The `gmd-tools roadmap update-plan-progress 3` command mangles the descriptive Phase Summary row format (replaces named cells with bare counters); the row is bumped 1/5 → 2/5 manually here to preserve the format that mirrors Phase 1 + Phase 2 in the table. Plans-list checkbox `[ ] 03-02-fundamentals-PLAN.md` flipped to `[x]`.
- **ANLY-01 traceability table entry in REQUIREMENTS.md flipped Pending → Complete** AND the checkbox `- [ ] **ANLY-01**` flipped to `- [x] **ANLY-01**`. The remaining ANLY-02 / ANLY-03 / ANLY-04 entries stay Pending — Wave 2's other three analyst plans (03-03 / 03-04 / 03-05) will close them. The 2 cross-cutting xfail invariants in `tests/analysts/test_invariants.py` remain xfail (strict=True held — verified by the regression run) and will flip GREEN naturally when 03-05 ships and removes the markers as its final task.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added `test_per_config_ps_bearish_overvalued` + `test_per_config_ps_neutral_within_band` to clear coverage gate**
- **Found during:** Task 2 GREEN coverage check — `python -m pytest --cov=analysts.fundamentals --cov-branch tests/analysts/test_fundamentals.py` reported 96% line / 98% branch with lines 116-119 of `analysts/fundamentals.py` uncovered (the per-config P/S overvalued return, the per-config P/S near-target return, and the corresponding evidence strings).
- **Issue:** The plan named only `test_per_config_ps_bullish_undervalued` for the per-config P/S path, leaving the overvalued + near-target branches untested. Coverage was above the 90/85 gate but real per-config behaviors the plan promised in `must_haves.truths` ("Per-config path: when config.target_multiples.pe_target is set, P/E < target * 0.8 → +1 contribution; > target * 1.2 → -1 contribution; within ±20% → 0" — the SAME 3-band shape applies to P/S per the helper symmetry) were unverified.
- **Fix:** Added 2 mirror tests for P/S — `test_per_config_ps_bearish_overvalued` (ps_target=5 + actual ps=8 → overvalued evidence) and `test_per_config_ps_neutral_within_band` (ps_target=5 + actual ps=5.5 → near target evidence).
- **Files modified:** `tests/analysts/test_fundamentals.py` (+34 lines)
- **Verification:** Coverage re-ran at 100% line / 100% branch; both new tests green.
- **Committed in:** `ef8af69` (GREEN commit folds in the test additions alongside the implementation)

---

**Total deviations:** 1 auto-fixed (Rule 2 — additive coverage tightening that closes the per-config P/S parity gap with the per-config P/E coverage). **Impact:** Tightening only. Implementation matches the plan's specifications byte-for-byte; the addition is 2 extra tests that lock per-config P/S parity with per-config P/E (the helper symmetry was always there; the tests now witness it).

## Issues Encountered

- **Local environment had stalled python processes from earlier sessions** (8+ python.exe procs accumulated during the conversation, holding file locks and competing for CPU). The full-suite pytest run wall clock was inflated to 9h 14m as a result; the actual test suite runs in well under 1 minute when no other procs compete (verified by the targeted-subdir run: `pytest tests/analysts -q` → 50 passed + 2 xfailed in 0.07s). No test failures or behavioral issues — pure environment performance noise. Closeout cleanup will leave the working tree clean, no orphan procs.
- **Phase 2 closeout's `gmd-tools roadmap update-plan-progress` warning carried forward** — that command is known to mangle the descriptive Phase Summary row format (precedent set in Plan 02-07 + Plan 03-01 closeouts); the row is being updated manually here instead.

## Self-Check: PASSED

- [x] `analysts/fundamentals.py` exists — FOUND (265 lines, 12624 bytes)
- [x] `tests/analysts/test_fundamentals.py` exists — FOUND (392 lines, 17906 bytes)
- [x] Provenance header in `analysts/fundamentals.py` references `virattt/ai-hedge-fund/src/agents/fundamentals.py` — VERIFIED via Grep on line 3
- [x] `score()` signature is `(snapshot: Snapshot, config: TickerConfig, *, computed_at: Optional[datetime] = None) -> AgentSignal` — VERIFIED in source
- [x] All 5 metric helpers present (`_score_pe`, `_score_ps`, `_score_roe`, `_score_de`, `_score_pm`) — VERIFIED
- [x] `_total_to_verdict` private helper present — VERIFIED
- [x] Module-level constants present (PE / PS / ROE / DE / PM bands + PER_CONFIG_BAND + `_MAX_POSSIBLE_SCORE`) — VERIFIED
- [x] Empty-data UNIFORM RULE 3 branches present (snapshot.data_unavailable / fundamentals=None / fundamentals.data_unavailable) — VERIFIED
- [x] Defensive 4th branch (n_scored == 0 → all 5 missing reason) — VERIFIED
- [x] Commit `a887176` (Task 1 RED — failing tests for fundamentals analyst) — FOUND in git log
- [x] Commit `ef8af69` (Task 2 GREEN — fundamentals analyst implementation + 2 P/S coverage tests) — FOUND in git log
- [x] `python -m pytest tests/analysts/test_fundamentals.py -v` — 26/26 PASSED in 0.04s
- [x] `python -m pytest tests/analysts -q` — 50 passed + 2 xfailed in 0.07s (24 from 03-01 test_signals + 26 from 03-02 test_fundamentals + 2 xfail invariants held strict)
- [x] `python -m pytest -q` (full repo regression) — **238 passed + 2 xfailed** (up from 212 + 2 xfailed at end of 03-01: +26 fundamentals tests; the 2 xfail markers in test_invariants.py held strict and remained xfail as expected)
- [x] Coverage on `analysts/fundamentals.py`: **100% line / 100% branch** (gate ≥90% / ≥85%) — verified via `python -m pytest --cov=analysts.fundamentals --cov-branch tests/analysts/test_fundamentals.py`
- [x] Pure-function discipline: no I/O in `analysts/fundamentals.py`, no module-level mutable state, no clock reads inside helpers — VERIFIED by source inspection
- [x] xfail markers in `tests/analysts/test_invariants.py` UNTOUCHED — VERIFIED via `git diff f470357..ef8af69 -- tests/analysts/test_invariants.py` returns empty
- [x] Determinism contract: two calls with identical inputs → identical AgentSignal — VERIFIED by `test_determinism_two_calls_identical`

### Expected-RED tests (NOT failures)

The 2 tests in `tests/analysts/test_invariants.py` REMAIN xfail at end of 03-02 — they exercise the contract every Wave 2 analyst plan promises but require all four analyst modules (`analysts/{fundamentals,technicals,news_sentiment,valuation}.py`) to be importable. With only fundamentals shipped, the lazy `from analysts import fundamentals, news_sentiment, technicals, valuation` import line still fails on the missing 3 modules — XFAIL is the expected RED state for the next 3 plans:

- `tests/analysts/test_invariants.py::test_always_four_signals` — XFAIL (technicals / news_sentiment / valuation modules don't exist yet)
- `tests/analysts/test_invariants.py::test_dark_snapshot_emits_four_unavailable` — XFAIL (same)

Plan 03-05 (the LAST Wave 2 plan to commit per the dependency graph) MUST remove the `@pytest.mark.xfail` markers in its final task. The `strict=True` on each marker held during this run — they remained xfail and didn't unexpectedly turn GREEN, confirming that 03-02 didn't accidentally over-ship the cross-cutting contract.

## Next Phase Readiness

- **Wave 2 progress: 1/4 analysts shipped.** The remaining three Wave 2 plans (03-03 technicals, 03-04 news_sentiment, 03-05 valuation) can each execute in parallel — they share no dependencies on each other beyond the foundation surface from 03-01 (AgentSignal contract + fixture toolbox), which is unchanged by this plan. Each will follow the same pure-function `score(snapshot, config, *, computed_at=None) -> AgentSignal` shape established here.
- **`analysts/fundamentals.py` is the template every other Wave 2 analyst follows in shape.** The 3-branch UNIFORM RULE empty-data guard, the per-metric helpers returning `(score, Optional[evidence])`, the strict > 5-state ladder boundaries, and the aggregate-against-max-possible normalization all generalize: 03-03 has 3 sub-scores (MA stack, momentum, ADX trend gating — divisor = 3); 03-04 has per-headline VADER aggregation (recency + source weighting); 03-05 has 3 tiers (thesis_price, target_multiples, consensus — divisor = 3 with explicit tier precedence).
- **No new Wave 2 dependencies** — vaderSentiment was added at 03-01 for 03-04; everything else (Pydantic v2, the analysts.signals contract, the analysts.data.* sub-schemas) is already in place.
- **03-05 wraps Wave 2** — its final task removes the `@pytest.mark.xfail(strict=True)` markers from `tests/analysts/test_invariants.py`. At that point both cross-cutting tests flip GREEN naturally as all four analyst modules exist and respect the dark-snapshot UNIFORM RULE. The strict markers continue to guarantee that any Wave 2 plan accidentally over-shipping these contracts (or any plan leaving the markers in place after 03-05) fails loudly.
- **No carry-overs / no blockers from this plan.** Wave 2 progress: 1/4 analysts complete. ANLY-01 closed in REQUIREMENTS.md.

---
*Phase: 03-analytical-agents-deterministic-scoring*
*Plan: 02-fundamentals*
*Completed: 2026-05-03*
