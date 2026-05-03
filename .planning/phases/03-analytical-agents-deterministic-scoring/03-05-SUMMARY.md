---
phase: 03-analytical-agents-deterministic-scoring
plan: 05
subsystem: analysts
tags: [phase-3, analyst, valuation, tdd, pure-function, anly-04, wave-2-closeout, cross-phase-dep]

# Dependency graph
requires:
  - phase: 03-analytical-agents-deterministic-scoring
    plan: 01
    provides: analysts.signals.AgentSignal (5-state Verdict ladder + 0-100 confidence + evidence list + data_unavailable invariant), tests/analysts/conftest.py + tests/analysts/test_invariants.py xfail scaffold
  - phase: 02-ingestion-keyless-data-plane
    plan: 07
    provides: 'analysts.data.fundamentals.FundamentalsSnapshot.{analyst_target_mean, analyst_target_median, analyst_recommendation_mean, analyst_opinion_count} fields (Phase 2 amendment, Optional[float|int]; populated by ingestion/fundamentals.py from yfinance info["targetMeanPrice"]/etc.)'
  - phase: 02-ingestion-keyless-data-plane
    plan: 06
    provides: analysts.data.snapshot.Snapshot (per-ticker aggregate carrying optional prices + fundamentals sub-fields plus snapshot-level data_unavailable bool)
  - phase: 01-foundation-watchlist-per-ticker-config
    plan: 02
    provides: analysts.schemas.{TickerConfig.thesis_price, TickerConfig.target_multiples, FundamentalTargets.{pe_target, ps_target, pb_target}} — user's per-ticker valuation overrides
provides:
  - "analysts.valuation.score(snapshot, config, *, computed_at=None) -> AgentSignal — pure function, 3-tier blend with explicit precedence, never raises for missing data"
  - "Tier 1 (W_THESIS=1.0): config.thesis_price vs snapshot.prices.current_price"
  - "Tier 2 (W_TARGETS=0.7 each): config.target_multiples.{pe_target, ps_target, pb_target} vs snapshot.fundamentals.{pe, ps, pb}"
  - "Tier 3 (W_CONSENSUS=0.5): snapshot.fundamentals.analyst_target_mean vs current_price (REQUIRES 02-07)"
  - "_signed_gap(anchor, current) linearization saturated at GAP_SATURATION=0.5 (50% premium / 50% discount = ±1)"
  - "Density-weighted confidence: density = min(1.0, total_w / 2.2). Saturates at 1.0 when 2+ tiers active with multiple multiples; ~0.45 when only thesis_price set. confidence = min(100, int(round(abs(aggregate) * 100 * density)))"
  - "Empty-data UNIFORM RULE (4 short-circuit branches): snapshot.data_unavailable / prices=None / prices.data_unavailable / current_price None or ≤0 → AgentSignal(data_unavailable=True, evidence=['no current price'])"
  - "None-configured UNIFORM RULE: when ALL three tiers absent → AgentSignal(data_unavailable=True, evidence=['no thesis_price, no target_multiples, no consensus'])"
  - "Provenance header (INFRA-07) names virattt/ai-hedge-fund/src/agents/valuation.py with explicit methods divergence (DCF/Owner Earnings/EV/EBITDA/Residual Income → thesis_price/target_multiples/yfinance consensus) and cross-phase 02-07 dependency note"
  - "Wave 2 closeout — removes @pytest.mark.xfail markers from tests/analysts/test_invariants.py; both cross-cutting invariant tests flip green naturally"
affects: [phase-5-claude-routine (reads AgentSignal from disk via JSON), phase-6-frontend-deep-dive (renders evidence list), phase-7-decision-support (synthesizer reads all 4 analyst signals)]

# Tech tracking
tech-stack:
  added: []  # No new dependencies
  patterns:
    - "Multi-method weighted aggregation with active-method weight selection: when a method's value is missing or ≤ 0, exclude from weights and recompute total_weight from remaining methods. Adapted verbatim from virattt/ai-hedge-fund (only the methods themselves diverge)."
    - "Density-weighted confidence: more active methods → higher confidence. Pattern: density = min(1.0, total_w / SATURATION); confidence = round(abs(aggregate) * 100 * density). Reusable across any analyst that aggregates multiple optional sub-signals — Phase 4 POSE will use it for indicator-consensus confidence (more indicators agreeing → higher confidence)."
    - "Hard cross-phase dependency with explicit attribute read (no getattr-defensive): fail loudly at AttributeError if a future change reverts the depended-on amendment. Locks the contract; prevents silent degradation. Pattern reusable for any analyst that depends on a Phase-2-amendment ingestion field."
    - "Per-tier sub-signal collection as list[tuple[float, float, str]] (signal, weight, evidence): structurally enforces that every contributing tier emits exactly one evidence string AND the (signal, weight) pair used in aggregation. Reusable for any analyst with multiple optional sub-signals."

key-files:
  created:
    - "analysts/valuation.py (~250 lines — provenance docstring + 4 module-level constants + _signed_gap + _total_to_verdict + score())"
    - "tests/analysts/test_valuation.py (~520 lines, 23 tests covering 02-07 dep / 4 thesis-only / 4 targets-only / 3 consensus-only / 1 all-three blend / 1 none-configured / 4 empty-data / 1 density-confidence / 4 determinism+provenance+meta)"
  modified:
    - "tests/analysts/test_invariants.py — xfail markers removed; file-header docstring shortened to reflect post-Wave-2 state; both cross-cutting invariant tests flip GREEN naturally"

key-decisions:
  - "Three-tier blend with explicit precedence (W_THESIS=1.0 > W_TARGETS=0.7 > W_CONSENSUS=0.5) per 03-CONTEXT.md scoring philosophy. Thesis_price is highest-trust because it encodes domain-specific work the user did themselves; target_multiples is medium-trust because it depends on the user's choice of P/E etc. heuristic; consensus is lowest-trust because sell-side anchoring drift is a known artifact. The strict precedence is encoded in the weights, not in any short-circuit logic — all available tiers contribute proportionally, but the higher-weight tiers dominate the aggregate."
  - "Each multiple in target_multiples (pe / ps / pb) contributes its own sub-signal at weight W_TARGETS=0.7. Locks the design that 'a user setting all three multiples gets 3 sub-signals at the targets tier', not '1 sub-signal at the targets tier'. Density-weighted confidence rewards setting more multiples — encourages the user to encode their full thesis."
  - "_signed_gap(anchor, current) saturates at GAP_SATURATION=0.5 — a 50% premium clips the sub-signal at -1.0, a 50% discount at +1.0. Linear in between. Tunable; locked by test_thesis_only_strong_undervalued (current=100, thesis=200 → saturated at +1.0 → strong_bullish verdict). The saturation prevents extreme outliers (e.g., a thesis_price set 10x current price by typo) from dominating the aggregate."
  - "Density-weighted confidence: density = min(1.0, total_w / 2.2). Saturation point chosen so 2+ tiers active with multiple multiples saturate near 1.0; only-thesis or only-pe-target gives density ≈ 0.45 / 0.32. Locked by test_density_bonus_more_tiers_more_confidence — same per-tier signed gap, more active tiers → higher confidence. The denominator 2.2 is empirically tuned: with all 3 tiers maxed (thesis 1.0 + 3 multiples * 0.7 + consensus 0.5 = 3.6), density saturates well before the maximum, encoding the design intent that '2+ agreeing tiers should give high confidence even if not every multiple is set'."
  - "Cross-phase 02-07 dependency is HARD — `snapshot.fundamentals.analyst_target_mean` read directly (no getattr-defensive). If 02-07 is reverted, this analyst fails at attribute access on the Tier 3 branch. Intentional — silent degradation (Tier 3 quietly returns None and the analyst proceeds with Tier 1 + Tier 2 only) would mask the regression. The fail-loud contract is locked by `test_02_07_dependency_present` which asserts `analyst_target_mean in FundamentalsSnapshot.model_fields`."
  - "Empty-data UNIFORM RULE has 4 short-circuit branches at the top (snapshot.data_unavailable / prices=None / prices.data_unavailable / current_price None or ≤0), all returning the same canonical `(data_unavailable=True, verdict='neutral', confidence=0, evidence=['no current price'])` signal. Unlike fundamentals (3 distinct evidence strings) or news_sentiment (3 filter-based reasons), valuation collapses to a single 'no current price' message — the 4 branches are all subcases of the same root cause (no anchor to compare against). Distinguishing them in evidence offered no debugging value because the user can verify by inspecting snapshot.prices directly."
  - "None-configured UNIFORM RULE returns evidence=['no thesis_price, no target_multiples, no consensus']. Distinct from the empty-data case because the issue here is configuration (the user hasn't set up any anchor) rather than data ingestion (snapshot has no current price). Locked by test_none_configured_data_unavailable."
  - "Verdict tiering reuses the strict > 0.6 / 0.2 boundaries from fundamentals + technicals (NOT the VADER-tuned 0.4 / 0.05 from news_sentiment). Reason: valuation's _signed_gap output naturally spans [-1, +1] when GAP_SATURATION=0.5 is hit; the strict > 0.6 / 0.2 boundaries match this distribution. The DRY trigger for a shared analysts.verdict._total_to_verdict has now fired (3 copies in fundamentals/technicals/valuation) but extraction to a shared module is deferred to v1.x — for now the per-analyst copy keeps each module self-contained, and the boundary values are documented alongside the boundary call site."
  - "Wave 2 closeout: tests/analysts/test_invariants.py xfail markers removed in the same plan that ships the last analyst module. The strict=True markers held throughout Wave 2 — they did NOT unexpectedly turn GREEN at any earlier plan, confirming that no Wave 2 plan accidentally over-shipped the cross-cutting contracts. With all four modules shipped, the markers come off cleanly. The 2 cross-cutting tests (`test_always_four_signals`, `test_dark_snapshot_emits_four_unavailable`) flip GREEN naturally — verified by running test_invariants.py on its own (2 passed, 0 xfailed) and then full repo regression (310 passed, 0 xfailed; up from 285 + 2 xfailed at end of 03-04: +23 valuation tests + 2 invariants flipping from xfail → pass)."
  - "ROADMAP.md plan-progress edit done MANUALLY per the precedent set in Plans 02-07 / 03-01..03-04 closeouts. The `gmd-tools roadmap update-plan-progress 3` command mangles the descriptive Phase Summary row format; the row is bumped 4/5 → 5/5 (Phase 3 → Complete) manually here."

patterns-established:
  - "Multi-method weighted aggregation with density-weighted confidence: pattern reusable across any analyst with multiple optional sub-signals. Phase 4 POSE-01..05 will use it for indicator-consensus confidence (more indicators agreeing → higher confidence; the consensus_score and confidence fields in CONTEXT.md threshold defaults map directly). Phase 5 synthesizer can use it to weight per-persona signals."
  - "Hard cross-phase dependency with explicit attribute read: fail loudly if depended-on amendment is reverted. Pattern locked by `test_02_07_dependency_present` — asserts the depended-on field is in `FundamentalsSnapshot.model_fields`. Reusable for any future analyst that depends on a Phase-2-amendment field."
  - "Per-tier sub-signal collection (`sub: list[tuple[float, float, str]]`): structurally enforces that every contributing tier emits exactly one evidence string AND the (signal, weight) pair used in aggregation. The `if not sub: ...` defensive check at the end of all tier collection is the canonical 'no tiers configured' guard."
  - "Wave-closeout pattern (last plan removes the xfail markers): the strict=True markers in test_invariants.py held through 4 Wave 2 plans, never accidentally flipping GREEN; the LAST plan removes them and the integration tests flip GREEN naturally. Pattern reusable for any future Phase that has cross-cutting invariants requiring multiple plans to ship before the contract is enforceable."

requirements-completed: [ANLY-04]

# Metrics
duration: ~30 minutes active execution (RED + GREEN + Wave 2 closeout + closeout)
completed: 2026-05-03
---

# Phase 03 Plan 05: Valuation Analyst — 3-Tier Blend with Density-Weighted Confidence Summary

**Wave 2 / fourth and FINAL analyst lands: pure-function `analysts.valuation.score(snapshot, config, *, computed_at=None) -> AgentSignal` deterministically scores current price against three valuation anchors with explicit precedence weights — Tier 1 (W_THESIS=1.0): config.thesis_price; Tier 2 (W_TARGETS=0.7 each): config.target_multiples.{pe_target, ps_target, pb_target} vs snapshot.fundamentals.{pe, ps, pb}; Tier 3 (W_CONSENSUS=0.5): snapshot.fundamentals.analyst_target_mean vs current_price (REQUIRES 02-07). Each tier scored via `_signed_gap(anchor, current)` linearization saturated at GAP_SATURATION=0.5 (50% premium / 50% discount = ±1). Density-weighted confidence rewards multiple agreeing tiers — `density = min(1.0, total_w / 2.2)` saturates at 1.0 when 2+ tiers active with multiple multiples; ~0.45 when only thesis_price set. Empty-data UNIFORM RULE: no current price OR none of the 3 tiers configured → AgentSignal(data_unavailable=True). Cross-phase dependency on Plan 02-07 is HARD — `snapshot.fundamentals.analyst_target_mean` read directly (no getattr-defensive); locked by dedicated `test_02_07_dependency_present`. Provenance header (INFRA-07) names virattt/ai-hedge-fund/src/agents/valuation.py with explicit methods divergence (DCF/Owner Earnings/EV/EBITDA/Residual Income → thesis_price/target_multiples/yfinance consensus). **Wave 2 closeout: tests/analysts/test_invariants.py @pytest.mark.xfail markers REMOVED in this plan's Task 3; both cross-cutting invariant tests (`test_always_four_signals`, `test_dark_snapshot_emits_four_unavailable`) flip GREEN naturally as all four analyst modules now exist and respect the dark-snapshot UNIFORM RULE.** ANLY-04 closes; **Phase 3 / Wave 2 analyst implementation COMPLETE: ANLY-01..04 all `[x]`, 4/4 analyst modules shipped, 0 xfailed remaining.**

## Performance

- **Duration:** ~30 minutes active execution including TDD RED + GREEN + Wave 2 closeout (xfail removal) + this SUMMARY closeout.
- **Tasks:** 3 — Task 1 (RED): 23 failing tests covering 02-07 dep / each tier alone / blend / none-set / empty-data / density-confidence / determinism+provenance+meta. Task 2 (GREEN): implement `analysts/valuation.py` (all 23 tests green on first try). Task 3 (Wave 2 closeout): remove `@pytest.mark.xfail(strict=True, ...)` markers from `tests/analysts/test_invariants.py` and verify both cross-cutting tests flip green naturally.
- **Files created:** 2 (`analysts/valuation.py` ~250 lines, `tests/analysts/test_valuation.py` ~520 lines)
- **Files modified:** 1 (`tests/analysts/test_invariants.py` — xfail markers removed; file-header docstring shortened to post-Wave-2 state)

## Accomplishments

- **`analysts/valuation.py` (~250 lines)** ships the locked Wave 2 final-analyst contract. Public surface: `score(snapshot: Snapshot, config: TickerConfig, *, computed_at: Optional[datetime] = None) -> AgentSignal` — pure, deterministic, never raises for missing data, always returns an AgentSignal with `analyst_id="valuation"`. Provenance header (INFRA-07) names `virattt/ai-hedge-fund/src/agents/valuation.py` and explicitly documents the methods divergence (virattt: DCF + Owner Earnings + EV/EBITDA + Residual Income; we: thesis_price + target_multiples + yfinance consensus per 03-CONTEXT.md scoring philosophy). The multi-method weighted aggregation pattern carries over verbatim — only the methods themselves differ.
- **Module-level constants** make every tier weight + saturation parameter tunable: `W_THESIS=1.0`, `W_TARGETS=0.7`, `W_CONSENSUS=0.5`, `GAP_SATURATION=0.5`, `DENSITY_SATURATION=2.2`. Tunable by editing this file; tests pin the exact formulas via test_thesis_only_strong_undervalued (saturation), test_density_bonus_more_tiers_more_confidence (density math).
- **Two private helpers** orchestrate the math:
  - `_signed_gap(anchor, current) -> float` — returns `s = clamp(-delta / GAP_SATURATION, -1, +1)` where `delta = (current - anchor) / anchor`. Positive = current below anchor (bullish); negative = current above anchor (bearish). 50% premium / discount saturates at ±1.
  - `_total_to_verdict(normalized) -> Verdict` — same shape as fundamentals + technicals: strict > boundaries at 0.6 / 0.2.
- **`score()` orchestration:** (1) Establish `now` from `computed_at` kwarg or default. (2) Empty-data UNIFORM RULE 4-branch guard at the top — `snapshot.data_unavailable` / `prices is None` / `prices.data_unavailable` / `current_price None or ≤ 0` → return data_unavailable signal with evidence `["no current price"]`. (3) Read `current = snapshot.prices.current_price` and `fund = snapshot.fundamentals` (may be None). (4) Iterate three tiers in fixed order — Tier 1 (thesis_price), Tier 2 (target_multiples.pe/ps/pb), Tier 3 (consensus) — each yields zero or more `(signal, weight, evidence)` tuples in `sub`. (5) None-configured UNIFORM RULE: `if not sub` → return data_unavailable signal with evidence `["no thesis_price, no target_multiples, no consensus"]`. (6) Aggregate: `total_w = sum(weights)`, `aggregate = weighted_avg(signals)`, `verdict = _total_to_verdict(aggregate)`, `density = min(1.0, total_w / DENSITY_SATURATION)`, `confidence = min(100, int(round(abs(aggregate) * 100 * density)))`. (7) Construct and return `AgentSignal(...)` with `evidence[:10]` cap.
- **Cross-phase 02-07 dependency locked by `test_02_07_dependency_present`** — asserts `analyst_target_mean / analyst_target_median / analyst_recommendation_mean / analyst_opinion_count` all appear in `FundamentalsSnapshot.model_fields`. If 02-07 is ever reverted (e.g., by a future schema-cleanup PR that removes "unused" fields), this test fails loudly. The Tier 3 code path reads `fund.analyst_target_mean` directly — no getattr-defensive — so silent regression is impossible.
- **Density-confidence math locked by `test_density_bonus_more_tiers_more_confidence`** — same per-tier signed gap, more active tiers → higher confidence. Snapshot A (thesis-only): `total_w = 1.0`, density ≈ 0.45. Snapshot B (thesis + pe + consensus): `total_w = 1.0 + 0.7 + 0.5 = 2.2`, density saturates at 1.0. So the same `aggregate` magnitude gives B a confidence ~2.2x higher than A — the design intent that "agreeing anchors should give the user higher conviction" is structurally enforced.
- **All-tier path verified:** `test_all_three_bullish` confirms the 3-tier blend produces evidence strings from each tier (thesis_price + P/E + consensus all appear in `evidence`). The order of evidence matches the iteration order: thesis → multiples → consensus. Phase 6 frontend can render the evidence list in this order without further re-sorting.
- **Empty-data UNIFORM RULE thoroughly tested:** `test_no_current_price` (prices=None), `test_current_price_none` (prices.current_price=None), `test_prices_data_unavailable` (prices.data_unavailable=True), `test_snapshot_data_unavailable_true`. All four return the canonical `(data_unavailable=True, verdict='neutral', confidence=0, evidence=['no current price'])` signal — single evidence reason because the 4 branches are all subcases of the same root cause (no anchor to compare against).
- **None-configured UNIFORM RULE verified by `test_none_configured_data_unavailable`** — when the user hasn't set thesis_price, hasn't set target_multiples, AND fund.analyst_target_mean is None, the analyst returns the canonical `(data_unavailable=True, evidence=['no thesis_price, no target_multiples, no consensus'])` signal. Distinct from the empty-data case (which is about ingestion failure) — this surface is about user configuration, and the evidence tells the user what to do (set at least one anchor).
- **Coverage on `analysts/valuation.py`: 100% line / 100% branch** (gate ≥90% line / ≥85% branch). 23/23 tests green; targeted suite runs in 0.04s.
- **Wave 2 closeout — `tests/analysts/test_invariants.py` xfail markers REMOVED.** With all four Wave 2 analyst modules shipped (fundamentals + technicals + news_sentiment + valuation), both cross-cutting invariant tests flip GREEN naturally:
  - `test_always_four_signals` — exactly 4 AgentSignals produced; analyst_id set covers all 4 canonical Literal values.
  - `test_dark_snapshot_emits_four_unavailable` — dark snapshot (data_unavailable=True / prices=None / fundamentals=None / news=[] / social=None / filings=[]) → 4 signals all with `data_unavailable=True`, `verdict='neutral'`, `confidence=0`, exactly one evidence string each.
  The strict=True markers held throughout Wave 2 — they did NOT unexpectedly turn GREEN at any earlier plan, confirming that no Wave 2 plan accidentally over-shipped the cross-cutting contracts.
- **Full repo regression: 310 passed, 0 xfailed** (up from 285 + 2 xfailed at end of 03-04: +23 valuation tests + 2 invariants flipping from xfail → pass). Phase 3 / Wave 2 analyst implementation is COMPLETE.
- **No new dependencies** — uses only stdlib (`datetime`, `typing.Optional`) plus the analysts.signals contract from 03-01, the analysts.data.snapshot.Snapshot from 02-06, and the analysts.schemas.{TickerConfig, FundamentalTargets} from 01-02.
- **No existing files modified** in production paths — purely additive aside from the documented xfail-marker removal in test_invariants.py.

## Task Commits

1. **Task 1 (RED) — `test(03-05): add failing tests for valuation analyst (3-tier blend + density confidence + 02-07 dep)`:** `037324e` — `tests/analysts/test_valuation.py` with 23 RED tests; pre-flight check confirmed 02-07 at HEAD via `FundamentalsSnapshot.model_fields` assertion BEFORE running the test scaffold; pytest then failed with `ModuleNotFoundError: No module named 'analysts.valuation'` on the per-test-method imports — verified the expected RED state.
2. **Task 2 (GREEN) — `feat(03-05): valuation analyst — thesis/targets/consensus 3-tier blend with density-weighted confidence`:** `e89b293` — `analysts/valuation.py` (~250 lines) implementing the score() function per implementation_sketch. ALL 23 tests green on first try (no Rule-1 test-side fixes needed — unique among Wave 2 plans, where 03-03 had 2 test fixes, 03-04 had 1, 03-02 had 2 coverage tests added). Coverage 100% line / 100% branch.
3. **Task 3 (Wave 2 closeout) — `test(03-05): close Wave 2 — remove xfail markers from test_invariants.py (all 4 analyst modules shipped)`:** `36f3912` — removed both `@pytest.mark.xfail(strict=True, reason=...)` decorators from `test_always_four_signals` and `test_dark_snapshot_emits_four_unavailable`; shortened the file-header docstring to reflect post-Wave-2 state. Both tests passed on first run (no analyst-module bugs surfaced by the integration tests). Full repo regression 310 passed, 0 xfailed.

**Plan metadata commit:** added in this closeout (covers SUMMARY.md, STATE.md Recent Decisions + Phase 3 → Complete, ROADMAP.md plan-progress row 4/5 → 5/5 + Phase 3 row → Complete, REQUIREMENTS.md ANLY-04 traceability flip).

## Files Created/Modified

### Created
- `analysts/valuation.py` (~250 lines — provenance docstring + 5 module-level constants + `_signed_gap` + `_total_to_verdict` + `score()`)
- `tests/analysts/test_valuation.py` (~520 lines, 23 tests)

### Modified
- `tests/analysts/test_invariants.py` (xfail markers removed; file-header docstring shortened)

### Modified at closeout
- `.planning/STATE.md` (Phase 3 progress 4/5 → 5/5 / Complete; current_plan 5 → completed; recent decisions append; Phase Status table row → Complete)
- `.planning/ROADMAP.md` (Phase 3 row 4/5 → 5/5 / Complete; Plans list `[ ] 03-05` → `[x] 03-05`; Phase Summary row Complete + completion date)
- `.planning/REQUIREMENTS.md` (ANLY-04 traceability Pending → Complete; checkbox `[ ] **ANLY-04**` → `[x] **ANLY-04**`)

## Decisions Made

- **Three-tier blend with explicit precedence weights (1.0 / 0.7 / 0.5).** Encoded in weights, not in short-circuit logic — all available tiers contribute proportionally.
- **Per-multiple sub-signals at the targets tier.** Each of pe / ps / pb yields its own sub-signal at W_TARGETS=0.7. Density-weighted confidence rewards setting more multiples — encourages the user to encode their full thesis.
- **`_signed_gap` linearization saturated at GAP_SATURATION=0.5.** 50% premium / discount clips at ±1.0 — prevents extreme outliers (e.g. thesis_price set 10x current price by typo) from dominating the aggregate.
- **Density-weighted confidence: density = min(1.0, total_w / 2.2).** Saturates at 1.0 when 2+ tiers active with multiple multiples; ~0.45 when only thesis_price set. Locked by test_density_bonus_more_tiers_more_confidence.
- **Cross-phase 02-07 dependency is HARD — direct attribute read.** Fail loudly at AttributeError if 02-07 reverts; locked by `test_02_07_dependency_present`.
- **Empty-data UNIFORM RULE collapses 4 branches to a single 'no current price' evidence string.** Distinguishing them offered no debugging value.
- **None-configured UNIFORM RULE is distinct from empty-data UNIFORM RULE.** Different root cause (config vs ingestion); different evidence string ("no thesis_price, no target_multiples, no consensus" — tells the user what to do).
- **Verdict tiering reuses strict > 0.6 / 0.2 boundaries from fundamentals/technicals.** DRY trigger has now fired (3 copies); shared `analysts.verdict._total_to_verdict` deferred to v1.x.
- **Wave 2 closeout: xfail markers removed in the same plan that ships the last analyst.** Strict=True markers held throughout Wave 2 — verified by the regression-watching pattern.
- **ROADMAP.md plan-progress edit done MANUALLY** per precedent.

## Deviations from Plan

**Total deviations: 0.** The implementation matches the plan's specifications byte-for-byte. All 23 tests passed on first GREEN run; no Rule-1 test-side fixes needed (unique among Wave 2 plans). The Wave 2 closeout (Task 3) ran clean — both cross-cutting invariant tests flipped GREEN on first run with no analyst-module bug surfaced.

The clean run is partially attributable to the 4 prior Wave 2 plans having locked the patterns (UNIFORM RULE empty-data guard, per-tier helper signature shape, strict > verdict boundaries, ROADMAP.md manual update precedent) — by the time 03-05 lands, the surface area for novel test bugs is small.

## Issues Encountered

- (none)

## Self-Check: PASSED

- [x] `analysts/valuation.py` exists — FOUND (~250 lines)
- [x] `tests/analysts/test_valuation.py` exists — FOUND (~520 lines, 23 tests)
- [x] Provenance header in `analysts/valuation.py` references `virattt/ai-hedge-fund/src/agents/valuation.py` AND mentions 02-07 cross-phase dep — VERIFIED via Grep
- [x] `score()` signature is `(snapshot: Snapshot, config: TickerConfig, *, computed_at: Optional[datetime] = None) -> AgentSignal` — VERIFIED in source
- [x] `_signed_gap`, `_total_to_verdict` helpers present — VERIFIED
- [x] Module-level constants present (W_THESIS / W_TARGETS / W_CONSENSUS / GAP_SATURATION / DENSITY_SATURATION) — VERIFIED
- [x] Three-tier iteration in score() in fixed precedence order (thesis → multiples → consensus) — VERIFIED
- [x] Cross-phase 02-07 read: `fund.analyst_target_mean` direct attribute access — VERIFIED in source AND `test_02_07_dependency_present` passes
- [x] Empty-data UNIFORM RULE 4 branches present — VERIFIED in source
- [x] None-configured UNIFORM RULE present (`if not sub: ...`) — VERIFIED in source
- [x] Density-weighted confidence math — VERIFIED in source AND `test_density_bonus_more_tiers_more_confidence` passes
- [x] Commit `037324e` (Task 1 RED — failing tests for valuation analyst) — FOUND in git log
- [x] Commit `e89b293` (Task 2 GREEN — analysts/valuation.py implementation) — FOUND in git log
- [x] Commit `36f3912` (Task 3 — Wave 2 closeout, xfail markers removed) — FOUND in git log
- [x] `pytest tests/analysts/test_valuation.py -v` — 23/23 PASSED in 0.04s
- [x] `pytest tests/analysts/test_invariants.py -v` — 2/2 PASSED, 0 xfailed (markers REMOVED)
- [x] `pytest -q` (full repo regression) — **310 passed, 0 xfailed** (up from 285 + 2 xfailed at end of 03-04: +23 valuation tests + 2 invariants flipping from xfail → pass)
- [x] Coverage on `analysts/valuation.py`: **100% line / 100% branch** (gate ≥90% line / ≥85% branch)
- [x] Pure-function discipline: no I/O, no module-level mutable state, no clock reads inside helpers — VERIFIED by source inspection
- [x] xfail markers in `tests/analysts/test_invariants.py` REMOVED — VERIFIED via Grep
- [x] Determinism contract: two calls with identical inputs → byte-identical AgentSignal model_dump_json — VERIFIED by `test_deterministic`

### Wave 2 Closeout: PASSED

The 2 cross-cutting invariant tests in `tests/analysts/test_invariants.py` flipped GREEN naturally upon xfail-marker removal:

- `test_always_four_signals` — PASSED (4 AgentSignals produced; analyst_id set is `{'fundamentals', 'technicals', 'news_sentiment', 'valuation'}`)
- `test_dark_snapshot_emits_four_unavailable` — PASSED (dark snapshot → 4 signals all with data_unavailable=True, verdict='neutral', confidence=0, exactly 1 evidence string each)

The strict=True markers held throughout Wave 2 (Plans 03-02 / 03-03 / 03-04 / 03-05) — they did NOT unexpectedly turn GREEN at any earlier plan, confirming that no Wave 2 plan accidentally over-shipped the cross-cutting contracts. With all four analyst modules shipped, the markers come off cleanly.

## Next Phase Readiness

- **Phase 3 / Wave 2 analyst implementation COMPLETE.** All four analyst modules shipped: `analysts/{fundamentals, technicals, news_sentiment, valuation}.py`. ANLY-01 / ANLY-02 / ANLY-03 / ANLY-04 all `[x]` in REQUIREMENTS.md.
- **Phase 3 plans: 5/5 complete** (03-01 signals scaffold + 03-02 fundamentals + 03-03 technicals + 03-04 news_sentiment + 03-05 valuation). The xfail markers from the Wave 1 scaffold are gone; the integration-style cross-cutting invariants are now standard tests.
- **Phase 4 (Position-Adjustment Radar) unblocked.** POSE-01..05 indicators (RSI / Bollinger / Stochastic / Williams %R / MACD / Hurst) reuse the hand-rolled pandas indicator pattern from 03-03 + the multi-method weighted aggregation pattern from 03-05. Phase 4's plan-phase will revisit the ta-lib / pandas-ta-classic dependency-choice debate.
- **Phase 5 (Claude Routine Wiring) partially unblocked.** Phase 5's synthesizer reads the 4 AgentSignals per ticker as deterministic input alongside the LLM personas. The contract is now stable: every (snapshot, config) input produces exactly 4 AgentSignals with the canonical `analyst_id` Literal set, all respecting the data_unavailable UNIFORM RULE for missing-data paths. Phase 5's plan-phase research can now look at Claude Code routine constraints (cron syntax, output format, quota visibility) without worrying about the analyst contract drifting underneath.
- **No carry-overs / no blockers from this plan.** Wave 2 progress: 4/4 analysts complete. Phase 3: 5/5 plans complete.

---
*Phase: 03-analytical-agents-deterministic-scoring*
*Plan: 05-valuation*
*Completed: 2026-05-03*
*Wave 2 closed; Phase 3 complete.*
