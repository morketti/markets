---
phase: 04-position-adjustment-radar
plan: 01
subsystem: analysts
tags: [phase-4, foundation, refactor, dry-trigger, fixtures, tdd, wave-0, no-behavior-change]

requires:
  - phase: 03-analytical-agents-deterministic-scoring
    plan: 05
    provides: Phase 3 complete — `analysts/{fundamentals,technicals,news_sentiment,valuation}.py` shipped; 310 baseline tests green; the 3 inline copies of `_total_to_verdict` (in fundamentals/technicals/valuation) ready for DRY consolidation.
provides:
  - "analysts/_indicator_math.py — shared `_build_df`, `_adx_14`, `_total_to_verdict` helpers + 5 ADX module-level constants (ADX_PERIOD=14, ADX_TREND_ABOVE=25.0, ADX_RANGE_BELOW=20.0, ADX_MIN_BARS=27, ADX_STABLE_BARS=150). Single source of truth for the indicator math used across the analyst suite."
  - "analysts/{fundamentals, technicals, valuation}.py refactored to import the shared helpers — no inline copies remain. analysts/news_sentiment.py keeps its OWN _total_to_verdict variant (VADER-distribution-tuned boundaries 0.4/0.05; intentionally different from canonical 0.6/0.2)."
  - "analysts/technicals.py keeps `_adx_evidence` inline (technicals-specific evidence formatter; only called from technicals.score(); not extracted)."
  - "tests/analysts/conftest.py — 3 new module-level synthetic builders for explicit overbought/oversold/range regression testing: `synthetic_oversold_history` (sustained downtrend + final-shock-drop, last close < 50% of start), `synthetic_overbought_history` (sustained uptrend + final-shock-pop, last close > 200% of start), `synthetic_mean_reverting_history` (sinusoidal oscillation, default amplitude=0.10 / period=50 bars wider than synthetic_sideways=0.02 / period=20)."
  - "tests/analysts/test_indicator_math.py — 19 tests (parametrized boundary test expands to 12 cases) covering the 3 extracted helpers + 5 ADX constant value-locks. Coverage 97% line+branch combined."
  - "tests/analysts/test_synthetic_fixtures.py — 4 tests covering the 3 new builders (qualitative shape + determinism contract)."
  - "Phase 3 regression invariant: ALL 310 existing tests stayed GREEN through both the refactor and the fixture additions. Full repo regression: 333 passed (310 baseline + 23 new)."
affects: [phase-4-plan-02-position-signal, phase-4-plan-03-position-adjustment]

# Tech tracking
tech-stack:
  added: []  # No new dependencies — pure refactor + fixture extension
  patterns:
    - "Shared-indicator-math module pattern: when the 4th copy of a helper is about to land, extract to a single-underscore-prefixed module (semantic-public, no `__all__`, just imported by sibling analyst modules). The Phase 4 position_adjustment analyst becomes the 2nd consumer of `_build_df` and `_adx_14` — extraction protects against drift across the 5+ analyst modules that will eventually share this math."
    - "Verbatim-extraction discipline: helper bodies moved unchanged; constants moved alongside their dependent helpers (ADX_* lives with `_adx_14` because the function literally references `ADX_MIN_BARS` and `ADX_PERIOD`). Caller files use import-only refactor (zero logic mutated). Phase 3 test suite serves as the behavioral regression guard against drift — if any moved helper accidentally changed behavior, one of 57+ existing tests would have caught it."
    - "Synthetic-fixture pattern for explicit regime testing: each builder produces a deterministic OHLCBar list with a controlled qualitative shape. Naming convention `synthetic_<regime>_history(n, ...)`. All builders reuse the internal `_build_ohlc_bars` helper. Phase 4 tests can request 'an explicitly oversold history' and get one whose RSI/BB/Stoch/Williams %R all hit oversold thresholds — locks regression behavior without flaky thresholds on real market data."

key-files:
  created:
    - "analysts/_indicator_math.py (~165 lines — provenance docstring + 5 ADX constants + `_build_df` + `_adx_14` + `_total_to_verdict`)"
    - "tests/analysts/test_indicator_math.py (~135 lines, 19 tests including parametrized boundary expansion)"
    - "tests/analysts/test_synthetic_fixtures.py (~62 lines, 4 tests covering qualitative shape + determinism)"
  modified:
    - "analysts/fundamentals.py — removed inline `_total_to_verdict` definition (10 lines + comment block); added `from analysts._indicator_math import _total_to_verdict`. Net -10 lines."
    - "analysts/technicals.py — removed inline `_build_df` (19 lines), `_adx_14` (57 lines), `_total_to_verdict` (10 lines + comment block); removed 5 ADX module constants (12 lines); added consolidated `from analysts._indicator_math import (ADX_*, _build_df, _adx_14, _total_to_verdict)`. `_adx_evidence` UNTOUCHED (technicals-specific evidence formatter). Net -90 lines."
    - "analysts/valuation.py — removed inline `_total_to_verdict` definition (15 lines including docstring); added the import. Net -14 lines."
    - "tests/analysts/conftest.py — appended 3 new builders (~76 lines) AFTER `synthetic_sideways_history`. Module docstring updated to enumerate the new public surface. All existing fixtures + builders preserved (zero changes to lines 1-135 aside from the docstring extension)."

key-decisions:
  - "Single-underscore prefix on `_indicator_math.py` and its 3 helpers — semantic-public (importable by sibling analyst modules) but flagged as 'not for external consumers'. Project convention from Phase 3 (`_score_pe`, `_total_to_verdict`, `_build_df`, etc.); Phase 4 follows."
  - "ADX module constants moved alongside `_adx_14` because they're tightly coupled (the function literally references `ADX_MIN_BARS` and `ADX_PERIOD`). `analysts/technicals.py` re-imports them from the shared module — preserves any external code that reads `technicals.ADX_TREND_ABOVE` (none today, but defense-in-depth)."
  - "`_adx_evidence` (in `analysts/technicals.py`) is NOT extracted. Technicals-specific evidence string formatter; only called from `technicals.score()`. Phase 4 `position_adjustment.py` will write its OWN ADX evidence formatter (different wording — 'trend regime; mean-reversion indicators downweighted by 50%' vs technicals' 'trend regime'). Extracting `_adx_evidence` would force a generic API surface that doesn't actually save code; per-analyst formatters are the right boundary."
  - "`analysts/news_sentiment.py:_total_to_verdict` is NOT consolidated. It's a DIFFERENT function with the same name — boundaries are VADER-distribution-tuned (0.4/0.05/-0.05/-0.4) instead of canonical 0.6/0.2. Sanity-grep step in Task 1 verifies that the only canonical-variant `def _total_to_verdict` lives in `_indicator_math.py`; the news_sentiment variant is a deliberate departure documented in 03-04 SUMMARY.md."
  - "Synthetic fixtures appended to existing `tests/analysts/conftest.py` (NOT a new file). Mirrors the Phase 3 pattern of 'one home for shared synthetic builders'. Phase 5/6 will inherit them automatically without re-imports."
  - "Synthetic builders default `final_drop_pct=0.05` / `final_pop_pct=0.05` over `final_drop_bars=5` / `final_pop_bars=5` — chosen so the cumulative final-shock effect is ~22% (1 - 0.95^5 ≈ 0.226) which is enough to drive RSI/Stochastic/Williams %R well past their oversold/overbought thresholds in Phase 4 regression tests, but not so extreme that the synthetic shape becomes unrealistic for property-based testing."
  - "Mean-reverting fixture amplitude 0.10 (vs sideways 0.02) — wider amplitude pushes BB position to ±1.5 at peaks/troughs (BB position is in stdev units around SMA20; 10% sinusoidal swing amplitude over 50-bar period produces stdev20 ~6.5 around SMA20, so peaks at +0.10*150=±15 → BB position ±15/6.5 ≈ ±2.3 at extremes). Locks the 'mean-reversion regime' fixture clearly into BB-tradeable territory while keeping ADX < 20 (no consistent directional move; range regime gating retains full weights on mean-reversion indicators)."
  - "Phase 3 regression invariant locked by running the entire 310-test baseline before AND after the refactor — both runs returned 'all green'. The 23 new tests are additive on top of the baseline. The refactor is verified zero-behavior-change because the existing Phase 3 tests would have failed if any moved helper changed semantics."

patterns-established:
  - "DRY-trigger threshold = 4 copies. Phase 3 had 3 copies of `_total_to_verdict` (acceptable for now); Phase 4 was about to land the 4th copy → trigger fires → extract. Pattern reusable for the next time a helper is duplicated 3+ times across analyst modules: extract to `analysts/_<concern>_math.py` (e.g., a future `analysts/_aggregation.py` if the weighted-aggregation pattern across fundamentals/valuation/POSE consolidates)."
  - "Refactor-with-regression-invariant pattern: when extracting code that's already covered by a behavioral test suite, write a small set of dedicated unit tests for the new module THEN run the full regression. The regression suite is the ground truth for behavior preservation; the dedicated unit tests lock the new module's PUBLIC SURFACE specifically (so future refactors don't accidentally break the API contract)."
  - "Synthetic-fixture builders for explicit regime testing: Phase 4 oversold/overbought builders use a 'sustained trend + final shock' pattern that produces deterministic-but-extreme indicator readings. Reusable for any future analyst that needs to test indicator behavior at the edges of the input distribution without relying on flaky real-market-data fixtures."

requirements-completed: []  # 04-01 is foundation — POSE-01..05 stay Pending until 04-03 ships

# Metrics
duration: ~30 minutes active execution (RED + GREEN per task; full regression after each)
completed: 2026-05-03
---

# Phase 04 Plan 01: Wave 0 Foundation — Indicator Math Extraction + Synthetic Fixtures Summary

**Wave 0 foundation refactor lands. `analysts/_indicator_math.py` (~165 LOC) ships the shared `_build_df` + `_adx_14` + `_total_to_verdict` helpers + 5 ADX module-level constants — verbatim moves from `analysts/{technicals, fundamentals, valuation}.py`. The 4th-copy DRY trigger fired (Phase 4 `position_adjustment.py` was about to land the 4th copy of `_total_to_verdict` and the 2nd copy of `_build_df` + `_adx_14`); extraction permanently consolidates the math. Three caller modules refactored via import-only changes (zero logic mutated). `tests/analysts/conftest.py` extended with 3 deterministic synthetic-history builders (`synthetic_oversold_history`, `synthetic_overbought_history`, `synthetic_mean_reverting_history`) for explicit overbought/oversold/range regression testing in Phase 4 Wave 2. Phase 3 regression invariant held: ALL 310 existing tests stayed GREEN through the refactor + fixture additions. Full repo: 333 passed (310 baseline + 23 new).**

## Performance

- **Duration:** ~30 minutes active execution including RED + GREEN per task + full regression after each.
- **Tasks:** 2 — Task 1 (refactor): extract helpers + refactor 3 callers + 19 unit tests. Task 2 (fixtures): append 3 synthetic builders + 4 tests.
- **Files created:** 3 (`analysts/_indicator_math.py` ~165 lines, `tests/analysts/test_indicator_math.py` ~135 lines, `tests/analysts/test_synthetic_fixtures.py` ~62 lines)
- **Files modified:** 4 (`analysts/{fundamentals, technicals, valuation}.py` — import-only refactor; `tests/analysts/conftest.py` — appended 3 builders + docstring update)

## Accomplishments

- **`analysts/_indicator_math.py` (~165 lines)** ships the shared indicator-math contract. Public surface: `_build_df(history) -> pd.DataFrame`, `_adx_14(df) -> Optional[float]` (Wilder smoothing via `pandas.Series.ewm(alpha=1/14, adjust=False).mean()`), `_total_to_verdict(normalized) -> Verdict`. Module-level constants: `ADX_PERIOD=14`, `ADX_TREND_ABOVE=25.0`, `ADX_RANGE_BELOW=20.0`, `ADX_MIN_BARS=27`, `ADX_STABLE_BARS=150`. Provenance docstring documents the extraction lineage and the StockCharts canonical Wilder reference.
- **3 caller modules refactored:**
  - `analysts/fundamentals.py` — removed inline `_total_to_verdict`; added the import.
  - `analysts/technicals.py` — removed inline `_build_df`, `_adx_14`, `_total_to_verdict`, and 5 ADX module constants; consolidated import. `_adx_evidence` UNTOUCHED (technicals-specific evidence formatter).
  - `analysts/valuation.py` — removed inline `_total_to_verdict`; added the import.
  - `analysts/news_sentiment.py:_total_to_verdict` left in place — it's a DIFFERENT function with the same name (VADER-distribution-tuned boundaries 0.4/0.05/-0.05/-0.4 vs canonical 0.6/0.2). Sanity grep verified.
- **3 synthetic-history builders appended to `tests/analysts/conftest.py`:**
  - `synthetic_oversold_history(n=252, start=200.0, daily_drift=-0.005, final_drop_bars=5, final_drop_pct=0.05)` — sustained downtrend + final-shock-drop. Default produces last close ~22.5% of start.
  - `synthetic_overbought_history(n=252, start=100.0, daily_drift=0.005, final_pop_bars=5, final_pop_pct=0.05)` — mirror; default produces last close ~4.4x start.
  - `synthetic_mean_reverting_history(n=252, start=150.0, amplitude=0.10, period_bars=50)` — sinusoidal oscillation; wider amplitude than `synthetic_sideways` to push BB position to ±1.5 at peaks/troughs while keeping ADX < 20 (range regime).
  - All three reuse the internal `_build_ohlc_bars` helper — no duplication of OHLCBar construction. Same deterministic-noise pattern as Phase 3 builders. NO random sources.
- **Test coverage:**
  - `tests/analysts/test_indicator_math.py`: 19/19 green (smoke + ADX warm-up boundary at 27 bars + parametrized strict-boundary verdict tiering over 12 cases + ADX constant value-lock). Coverage on `analysts/_indicator_math.py` 97% line+branch combined (gate ≥90% line / ≥85% branch).
  - `tests/analysts/test_synthetic_fixtures.py`: 4/4 green (qualitative shape per builder + determinism contract).
- **Phase 3 regression invariant LOCKED:** all 310 existing tests stayed GREEN through both the refactor and the fixture additions. The behavioral regression suite (test_technicals.py 25 + test_fundamentals.py 26 + test_valuation.py 23 + test_invariants.py 2 + test_signals.py + test_news_sentiment.py) serves as the ground truth that no helper's semantics drifted during extraction.
- **Full repo regression: 333 passed** (310 baseline + 19 new indicator_math tests + 4 new synthetic_fixtures tests). Targeted suite runs in <1s; full suite ~2.5s.
- **Sanity greps confirm single-source-of-truth:** zero canonical-variant `def _total_to_verdict` outside `analysts/_indicator_math.py`; zero `def _build_df` / `def _adx_14` outside `analysts/_indicator_math.py`. The 4th-copy DRY trigger that motivated this extraction is now permanently consolidated.

## Task Commits

1. **Task 1 (RED) — `test(04-01): add failing tests for shared analysts._indicator_math helpers (build_df / adx_14 / total_to_verdict)`:** `bc4d56d` — `tests/analysts/test_indicator_math.py` with 9 RED tests (parametrized boundary expansion → 19 effective tests). Verified expected RED state: `ModuleNotFoundError: No module named 'analysts._indicator_math'`.
2. **Task 1 (GREEN) — `refactor(04-01): extract _build_df + _adx_14 + _total_to_verdict to analysts/_indicator_math.py (DRY trigger fired; zero behavior change)`:** `3e35fa8` — created `analysts/_indicator_math.py`; refactored `analysts/{fundamentals, technicals, valuation}.py` to import the shared helpers. 19/19 tests green. Coverage 97%. Phase 3 regression: 329 passed (310 + 19).
3. **Task 2 (RED) — `test(04-01): add failing tests for synthetic_oversold / overbought / mean_reverting fixtures`:** `0be3138` — `tests/analysts/test_synthetic_fixtures.py` with 4 RED tests. Verified expected RED state: `ImportError: cannot import name 'synthetic_mean_reverting_history' from 'tests.analysts.conftest'`.
4. **Task 2 (GREEN) — `test(04-01): add synthetic_oversold / overbought / mean_reverting builders to conftest.py`:** `0328292` — appended the 3 builders to `tests/analysts/conftest.py`. 4/4 tests green. Full repo regression: 333 passed.

## Files Created/Modified

### Created
- `analysts/_indicator_math.py` (~165 lines)
- `tests/analysts/test_indicator_math.py` (~135 lines, 19 tests)
- `tests/analysts/test_synthetic_fixtures.py` (~62 lines, 4 tests)

### Modified
- `analysts/fundamentals.py` (-10 lines)
- `analysts/technicals.py` (-90 lines — biggest consumer)
- `analysts/valuation.py` (-14 lines)
- `tests/analysts/conftest.py` (+76 lines — 3 builders + docstring extension; existing 1-135 untouched)

## Decisions Made

- **DRY-trigger threshold = 4 copies.** Phase 3 had 3 copies of `_total_to_verdict` (acceptable); Phase 4 was about to land the 4th → trigger fires → extract. Pattern reusable for future helper duplication.
- **Verbatim extraction with zero logic mutation.** Helper bodies moved unchanged; constants moved alongside their dependent helpers. Phase 3 test suite serves as ground-truth regression guard.
- **`_adx_evidence` stays inline in technicals.py.** Tightly coupled to technicals' evidence-string formatting; extracting would force a generic API that doesn't save code. Phase 4 will write its own ADX evidence formatter (different wording).
- **`analysts/news_sentiment.py:_total_to_verdict` not consolidated.** Different function with same name (VADER-distribution-tuned boundaries 0.4/0.05 vs canonical 0.6/0.2). Sanity-grep step verified the canonical variant is single-source.
- **Synthetic fixtures appended to existing conftest.py.** Mirrors Phase 3 pattern of single home for shared builders. Phase 5/6 inherit them automatically.
- **Synthetic-shock parameters chosen for indicator extremity.** `final_drop_pct=0.05 * 5 bars ≈ 22.6% cumulative` — drives RSI/Stochastic/Williams %R well past oversold thresholds without making the synthetic shape unrealistic.
- **Mean-reverting amplitude 0.10 vs sideways 0.02.** Wider amplitude pushes BB position to ±1.5 at peaks/troughs; period 50 bars (vs sideways 20 bars) keeps the oscillation slow enough that ADX stays < 20 (range regime).

## Deviations from Plan

**Total deviations: 0.** The implementation matches the plan's specifications byte-for-byte. Both task commit messages match the plan text. Phase 3 regression invariant held cleanly through both tasks. The 19 indicator_math tests + 4 synthetic_fixtures tests = 23 new green tests (above the plan's ≥9 floor — parametrized boundary test added 12 cases over the planned 6).

## Self-Check: PASSED

- [x] `analysts/_indicator_math.py` exists — FOUND (~165 lines)
- [x] `analysts/_indicator_math.py` exports `_build_df`, `_adx_14`, `_total_to_verdict` + 5 ADX constants — VERIFIED via test_adx_constants_are_locked
- [x] `analysts/fundamentals.py` imports `_total_to_verdict` from `_indicator_math` — VERIFIED via Read
- [x] `analysts/technicals.py` imports `_build_df`, `_adx_14`, `_total_to_verdict`, and 5 ADX constants from `_indicator_math` — VERIFIED via Read
- [x] `analysts/valuation.py` imports `_total_to_verdict` from `_indicator_math` — VERIFIED via Read
- [x] `analysts/technicals.py` keeps `_adx_evidence` inline — VERIFIED via Grep
- [x] Sanity grep: zero canonical `def _total_to_verdict` outside `_indicator_math.py` — VERIFIED (news_sentiment.py has its own VADER-tuned variant with different boundaries; intentional)
- [x] Sanity grep: zero `def _build_df` / `def _adx_14` outside `_indicator_math.py` — VERIFIED
- [x] `tests/analysts/conftest.py` has 3 new builders appended after `synthetic_sideways_history` — VERIFIED via Read
- [x] All 3 new builders are deterministic — VERIFIED by `test_synthetic_fixtures_deterministic`
- [x] Coverage on `analysts/_indicator_math.py`: **97% line+branch combined** (gate ≥90% line / ≥85% branch)
- [x] Phase 3 regression invariant: ALL existing 310 tests stayed GREEN — VERIFIED by full repo regression at end of each task
- [x] Full repo regression: **333 passed** (310 baseline + 23 new) — VERIFIED
- [x] Commits `bc4d56d` (RED 1), `3e35fa8` (GREEN 1 — refactor), `0be3138` (RED 2), `0328292` (GREEN 2 — fixtures) all present in git log

## Next Phase Readiness

- **Plan 04-02 (PositionSignal schema) UNBLOCKED.** Will use `frozen_now` fixture from existing conftest; doesn't directly import from this plan but the architectural separation (PositionSignal in its own file, NOT shared with AgentSignal) is now established by this Wave 0 foundation.
- **Plan 04-03 (position_adjustment analyst) UNBLOCKED.** Will import `_build_df`, `_adx_14`, `ADX_TREND_ABOVE`, `ADX_RANGE_BELOW` from `analysts._indicator_math`; will consume `synthetic_oversold_history`, `synthetic_overbought_history`, `synthetic_mean_reverting_history` from `tests.analysts.conftest` for regression testing.
- **No carry-overs / no blockers.** Phase 3 regression invariant held cleanly; the 4th-copy DRY trigger that motivated this extraction is permanently consolidated.

---
*Phase: 04-position-adjustment-radar*
*Plan: 01-foundation*
*Completed: 2026-05-03*
