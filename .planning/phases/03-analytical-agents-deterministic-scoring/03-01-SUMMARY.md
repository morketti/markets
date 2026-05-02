---
phase: 03-analytical-agents-deterministic-scoring
plan: 01
subsystem: analysts
tags: [phase-3, schema, signals, foundation, tdd, wave-0-deps, docs-touch-up, agent-signal, vader, fixtures]

# Dependency graph
requires:
  - phase: 01-foundation-watchlist-per-ticker-config
    plan: 02
    provides: analysts.schemas.normalize_ticker (single-source-of-truth ticker normalizer), analysts.schemas.TickerConfig (per-ticker config consumed by every analyst)
  - phase: 02-ingestion-keyless-data-plane
    plan: 01
    provides: analysts.data.prices.OHLCBar (consumed by synthetic_*_history builders)
  - phase: 02-ingestion-keyless-data-plane
    plan: 06
    provides: analysts.data.snapshot.Snapshot (the per-ticker aggregate every analyst will score against — used directly by make_snapshot fixture)
  - phase: 02-ingestion-keyless-data-plane
    plan: 07
    provides: FundamentalsSnapshot.{analyst_target_mean, analyst_target_median, analyst_recommendation_mean, analyst_opinion_count} + 1y default price history (downstream Wave 2 prerequisites; not directly consumed in 03-01)
provides:
  - analysts.signals.AgentSignal (locked output contract — 5-state Verdict, 0-100 confidence, evidence list ≤10 items each ≤200 chars, data_unavailable bool, ticker normalization, @model_validator data-unavailable invariant)
  - analysts.signals.Verdict (Literal["strong_bullish", "bullish", "neutral", "bearish", "strong_bearish"])
  - analysts.signals.AnalystId (Literal["fundamentals", "technicals", "news_sentiment", "valuation"])
  - tests/analysts/__init__.py (package marker for pytest collection)
  - tests/analysts/conftest.py (frozen_now + make_ticker_config + make_snapshot fixtures; synthetic_uptrend_history / synthetic_downtrend_history / synthetic_sideways_history module-level builders)
  - tests/analysts/test_signals.py (24 tests covering schema shape, validators, invariants, JSON round-trip, byte-stable serialization)
  - tests/analysts/test_invariants.py (2 cross-cutting xfail-marked tests — flip green when 03-05 lands)
  - vaderSentiment >= 3.3, < 4 in [project.dependencies]
  - REQUIREMENTS.md ANLY-01..04 widened to 5-state ladder wording
  - ROADMAP.md Phase 3 corrected from "Five → Four" + populated 03-01..03-05 plan list
affects: [phase-3-plan-02-fundamentals-analyst, phase-3-plan-03-technicals-analyst, phase-3-plan-04-news-sentiment-analyst, phase-3-plan-05-valuation-analyst, phase-4-position-adjustment-radar (reuses fixture toolbox), phase-5-claude-routine (reads AgentSignal from disk via JSON)]

# Tech tracking
tech-stack:
  added:
    - "vaderSentiment>=3.3,<4 (MIT, ~126KB pure-Python lexicon, no transitive deps; locks the news/sentiment dependency at Wave 1 so Plan 03-04 can `from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer` without a Wave 0 reshuffle)"
  patterns:
    - "Schema-level invariant via @model_validator(mode='after'): data_unavailable=True ⟹ verdict='neutral' AND confidence=0 — error message names BOTH offending values for debuggability. Closes 03-RESEARCH.md Pitfall #4. Phase 5/6 consumers can rely on the contract without defensive checks."
    - "Public Literal types co-located with the model (Verdict + AnalystId at module level of analysts/signals.py) — every Wave 2 analyst module imports them as the single source of truth, no string duplication."
    - "Factory-fixture pattern over fixture-class pattern: make_ticker_config / make_snapshot return closures that accept keyword overrides, so test bodies read like `cfg = make_ticker_config(ticker='NVDA', thesis_price=900.0)` instead of building inheritance chains. 03-RESEARCH.md Pattern 2."
    - "Module-level deterministic synthetic-history builders: synthetic_uptrend_history / synthetic_downtrend_history / synthetic_sideways_history are NOT pytest fixtures — they're importable module functions so Wave 2 analyst test files can pin n explicitly (e.g. `synthetic_uptrend_history(252)` for MA200 coverage). Determinism contract: no random sources, two calls with identical args produce byte-identical OHLCBar lists."
    - "Strict xfail markers on cross-cutting invariant scaffold: @pytest.mark.xfail(strict=True) means the natural RED state during Wave 1 reports as XFAIL (exit code 0) AND an unexpected GREEN fails loudly — guards against a Wave 2 plan over-shipping or these markers being accidentally left in place after 03-05 closes."
    - "Provenance header on analysts/signals.py names the virattt source pattern AND enumerates our 6 modifications (5-state vs 3-state Verdict, evidence list vs reasoning string, extra='forbid', ticker normalization, data_unavailable bool, schema-level invariant)."

key-files:
  created:
    - analysts/signals.py (120 lines — AgentSignal + Verdict + AnalystId + invariant)
    - tests/analysts/__init__.py (0 lines — package marker)
    - tests/analysts/conftest.py (175 lines — fixture toolbox)
    - tests/analysts/test_signals.py (215 lines — 24 schema tests)
    - tests/analysts/test_invariants.py (111 lines — 2 xfail-marked cross-cutting tests)
  modified:
    - pyproject.toml (+1 line — vaderSentiment dependency)
    - .planning/REQUIREMENTS.md (4 hunks — ANLY-01..04 widened to 5-state ladder)
    - .planning/ROADMAP.md (Phase 3 row updated 'Five → Four', Phase 3 detail Goal updated, Plans list populated with 03-01..03-05)

key-decisions:
  - "AgentSignal schema enforces the data_unavailable invariant at the SCHEMA layer (not the caller), via @model_validator(mode='after'). Closes 03-RESEARCH.md Pitfall #4 — buggy analysts can never write a (data_unavailable=True, verdict='bullish', confidence=80) signal to disk. Error message names both offending values."
  - "Verdict + AnalystId Literal types live at module level of analysts/signals.py and are publicly re-imported by every Wave 2 analyst module + the cross-cutting test_invariants.py. Single source of truth — no string duplication of the 5 ladder values or the 4 analyst ids anywhere downstream."
  - "Tests/analysts/conftest.py exposes BOTH pytest fixtures (frozen_now / make_ticker_config / make_snapshot) AND module-level synthetic builders (synthetic_*_history). Pytest fixtures wrap the builders for the common case; tests call the builders directly when they need to pin n (e.g. 252 bars for MA200 warm-up coverage in 03-03)."
  - "Synthetic history builders use deterministic noise (no random.random()): noise term is `0.001 * ((i % 5) - 2)` for HLC variance and `i * 100` for volume drift. Two calls with identical args produce byte-identical OHLCBar lists — sets the determinism contract Wave 2 plans rely on for stable assertions."
  - "synthetic_sideways_history uses a 20-bar sin period at 2% amplitude (no drift) — designed to push ADX < 20 (range regime) so 03-03 can verify trend-gating fires in mean-reversion conditions. Constants chosen by the period/amplitude formula in CONTEXT.md, not by ADX-targeting iteration."
  - "test_invariants.py is committed AT WAVE 1 with @pytest.mark.xfail(strict=True) markers — the file collects cleanly even before 03-02..03-05 land (analyst-module imports are inside each test body, so ImportError during XFAIL is the expected RED state). Plan 03-05 explicitly removes the markers in its final task; the strict=True on each marker means an unexpected GREEN fails loudly so over-shipping in Wave 2 is caught immediately."
  - "ROADMAP.md Phase 3 row format extended in-place to mirror Phase 1's '(1/5 plans, In Progress)' precedent — manual edit, NOT via `gmd-tools roadmap update-plan-progress` because that command is known to mangle the descriptive row format (precedent set in Plan 02-07 closeout)."
  - "REQUIREMENTS.md ANLY-01..04 widening was a single docs commit — the schema's 5-state ladder is the source of truth and the requirement text now matches it. Old 'bullish/bearish/neutral verdict' wording removed from those four entries; surrounding requirement text untouched."
  - "vaderSentiment is added at Wave 1 (this plan) so Wave 2 plan 03-04 can import the package without a Wave 0 reshuffle. NO production code in 03-01 imports vaderSentiment — the dep is staged here as foundation work; the actual import lands in analysts/news_sentiment.py during Plan 03-04."
  - "Test file count: 24 tests in test_signals.py (above the plan's ≥16 floor — the @pytest.mark.parametrize over the 5 verdict literals expands into 5 separate test instances, plus 2 tightening tests added during execution: test_evidence_string_at_cap_ok pinning the 200-char inclusive boundary, and test_analyst_id_literal_rejects_unknown locking the AnalystId Literal at the schema layer)."

patterns-established:
  - "Schema-level invariant enforcement via @model_validator: when a Pydantic model has a multi-field correctness rule (data_unavailable ⟹ verdict + confidence both clamped), enforce it in the model not the caller. Future Phase 3+ schemas (PositionAdjustmentSignal in Phase 4, TickerDecision in Phase 5) follow this pattern."
  - "Public Literal-type co-location: when a Pydantic model uses Literal types that downstream callers need (Verdict, AnalystId), expose them at module level alongside the model so callers can `from analysts.signals import AgentSignal, Verdict, AnalystId` instead of poking at AgentSignal.__fields__['verdict'].annotation."
  - "Factory-fixture toolbox in conftest.py: builder closures (make_*) that take keyword overrides + module-level synthetic data generators (synthetic_*_history). Wave 2 analyst test files import both. POSE Phase 4 reuses the same toolbox."
  - "Cross-cutting invariant scaffolding via xfail-strict: ship integration-style tests at Wave 1 for the contract Wave 2 promises, mark them with @pytest.mark.xfail(strict=True), have the LAST Wave 2 plan remove the markers as its final task. Locks the contract in the test suite from day one without blocking CI on the not-yet-built modules."
  - "Wave 0 dependency staging: when a downstream wave needs a new dep that's hard to add later (e.g. vaderSentiment for 03-04), add it in the foundation plan with NO production import — the dep + lockfile entry survives even if the consuming wave is reordered."

requirements-completed: []  # ANLY-01..04 begin in Wave 2 plans 03-02..03-05; 03-01 ships only the foundation surface they consume

# Metrics
duration: prior-session
completed: 2026-05-02
---

# Phase 03 Plan 01: AgentSignal Schema + tests/analysts/ Foundation Summary

**Wave 1 / Foundation: ships the AgentSignal Pydantic schema (5-state Verdict ladder, 0-100 confidence, evidence list, schema-level data_unavailable invariant), the tests/analysts/ package + shared fixture toolbox (frozen_now, make_snapshot, make_ticker_config, three synthetic_*_history builders), the vaderSentiment dependency staged for 03-04, and the REQUIREMENTS.md / ROADMAP.md doc touch-ups that align requirement text with the locked 5-state schema. Cross-cutting invariant tests are committed under @pytest.mark.xfail(strict=True) markers — they flip GREEN naturally as the four Wave 2 analyst modules land, with Plan 03-05 removing the markers in its final task.**

## Performance

- **Duration:** Plan executed in a prior session before this closeout. The 7 task commits (`64d0d38` through `a09be56`) all landed between Phase 2 closeout (`dcb83cd`) and the start of this closeout session. Verification + SUMMARY/STATE/ROADMAP closeout in this session.
- **Tasks:** 6 (Task 1 chore for vaderSentiment; Task 2 test scaffold for fixtures; Task 3 TDD RED + GREEN for AgentSignal schema; Task 4 test scaffold for cross-cutting invariants; Tasks 5+6 docs touch-ups for REQUIREMENTS + ROADMAP)
- **Files created:** 5 (`analysts/signals.py`, `tests/analysts/__init__.py`, `tests/analysts/conftest.py`, `tests/analysts/test_signals.py`, `tests/analysts/test_invariants.py`)
- **Files modified:** 3 (`pyproject.toml` +1 line for vaderSentiment, `.planning/REQUIREMENTS.md` 4 hunks for ANLY-01..04 widening, `.planning/ROADMAP.md` for Phase 3 'Five → Four' + Plans list)

## Accomplishments

- **`analysts/signals.py` (120 lines)** ships the locked output contract for Phase 3 analysts. Public surface: `Verdict = Literal["strong_bullish", "bullish", "neutral", "bearish", "strong_bearish"]`, `AnalystId = Literal["fundamentals", "technicals", "news_sentiment", "valuation"]`, and `AgentSignal` (Pydantic v2, ConfigDict(extra="forbid")) with seven fields: `ticker` (normalized via `analysts.schemas.normalize_ticker`), `analyst_id`, `computed_at`, `verdict` (default `"neutral"`), `confidence` (default 0, range 0-100 enforced via `Field(ge=0, le=100)`), `evidence` (default empty list, `max_length=10` enforced via Field, per-string ≤200 chars enforced via custom `@field_validator`), `data_unavailable` (default False). The schema-level `@model_validator(mode="after")` enforces the locked invariant: `data_unavailable=True ⟹ verdict=='neutral' AND confidence==0` — error message names both offending values for debuggability. Provenance header names the virattt pattern source and enumerates the 6 modifications (5-state vs 3-state Verdict, evidence list vs reasoning string, extra='forbid', ticker normalization, data_unavailable bool, schema-level invariant).
- **`tests/analysts/conftest.py` (175 lines)** ships the shared fixture toolbox every Wave 2 analyst test file (03-02..03-05) imports. Three pytest fixtures: `frozen_now` (pinned UTC datetime `2026-05-01T13:30:00+00:00` — same value as Phase 2 fixtures use, so timestamps cross-pollinate), `make_ticker_config` (returns a closure that builds `TickerConfig(ticker="AAPL", **overrides)`), `make_snapshot` (returns a closure that builds `Snapshot(ticker="AAPL", fetched_at=frozen_now, **overrides)`). Three module-level synthetic-history builders (NOT pytest fixtures — importable directly so test bodies can pin n explicitly): `synthetic_uptrend_history(n=252, start=100.0, daily_drift=0.005)` (252-bar default, ~3.5x return — clearly bullish at every horizon), `synthetic_downtrend_history(n=252, start=200.0, daily_drift=-0.005)` (mirror, ~0.28x — clearly bearish), `synthetic_sideways_history(n=252, start=150.0, amplitude=0.02)` (sinusoidal range-bound — designed to push ADX < 20 / range regime). All three reject `n < 1` or `start <= 0` with `ValueError` for clear test-typo surfacing. Determinism contract: no `random.random()` calls — noise term is `0.001 * ((i % 5) - 2)` for HLC variance + `i * 100` for volume drift; two calls with identical args produce byte-identical lists.
- **`tests/analysts/test_signals.py` (215 lines)** ships 24 tests covering the AgentSignal schema (above the plan's ≥16 floor — the `@pytest.mark.parametrize` over 5 verdict values expands into 5 instances, plus 2 tightening tests added during execution). Coverage breakdown:
  - Shape: `test_signal_minimum_valid` (all four defaults applied), `test_verdict_5_state_accepts_all` (parametrized over the 5 ladder values), `test_verdict_literal_rejects_unknown`, `test_analyst_id_literal_rejects_unknown` (tightening test — locks AnalystId Literal)
  - Ticker normalization: `test_ticker_normalization` (`brk.b` → `BRK-B`), `test_ticker_invalid_raises` (`123!@#` → ValidationError with `('ticker',)` in loc)
  - Confidence range: `test_confidence_range_lo` (-1 fails), `test_confidence_range_hi` (101 fails), `test_confidence_accepts_0_and_100` (boundaries inclusive)
  - Evidence cap: `test_evidence_max_items` (11 items fails), `test_evidence_string_too_long` (201 chars fails), `test_evidence_string_at_cap_ok` (tightening test — 200 chars boundary inclusive), `test_evidence_empty_list_ok`
  - Extra fields: `test_extra_field_forbidden` (verifies `extra="forbid"`)
  - Data-unavailable invariant (closes Pitfall #4): `test_data_unavailable_invariant_violation_verdict` (data_unavailable=True + verdict="bullish" → ValidationError mentioning both fields), `test_data_unavailable_invariant_violation_confidence` (data_unavailable=True + confidence=80 → ValidationError mentioning both fields), `test_data_unavailable_clean_path` (data_unavailable=True + neutral + 0 + evidence string is valid)
  - Serialization: `test_json_round_trip` (`model_dump_json` → `model_validate_json` preserves equality), `test_byte_stable_serialization` (sort_keys + indent=2 + trailing newline pattern matches Phase 1 watchlist/loader.save_watchlist)
  - Public surface: `test_verdict_and_analyst_id_types_exposed` (smoke import)
- **`tests/analysts/test_invariants.py` (111 lines)** ships 2 cross-cutting integration-style tests under `@pytest.mark.xfail(reason=..., strict=True)` markers: `test_always_four_signals` (asserts every analyst returns an AgentSignal AND the four returned analyst_ids are exactly `{"fundamentals", "technicals", "news_sentiment", "valuation"}`) and `test_dark_snapshot_emits_four_unavailable` (asserts a dark snapshot — `data_unavailable=True, prices=None, fundamentals=None, news=[], social=None, filings=[]` — produces four signals with `data_unavailable=True, verdict="neutral", confidence=0`, exactly one explanatory evidence string each). The four analyst-module imports are inside each test body so the file COLLECTS cleanly even before 03-02..03-05 land — `ImportError` during XFAIL is the expected RED state. Plan 03-05 explicitly removes the markers in its final task; `strict=True` on each marker means an unexpected GREEN fails loudly so over-shipping in Wave 2 is caught immediately.
- **`pyproject.toml` +1 line** appends `"vaderSentiment>=3.3,<4",` to `[project.dependencies]`. The dep is staged here at Wave 1 with NO production import — Plan 03-04 (news/sentiment analyst, Wave 2) will add `from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer` to `analysts/news_sentiment.py`. Verification: `python -c "from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer; print(SentimentIntensityAnalyzer().polarity_scores('great quarter beats expectations'))"` returns `{'neg': 0.0, 'neu': 0.423, 'pos': 0.577, 'compound': 0.6249}`.
- **`.planning/REQUIREMENTS.md` 4 hunks** widen ANLY-01..04 from 3-state ("bullish/bearish/neutral verdict") to 5-state ("**5-state ladder verdict (strong_bullish | bullish | neutral | bearish | strong_bearish)** + confidence (0-100 int) + evidence list (≤10 items, each ≤200 chars)"). The schema is the source of truth; the requirement text now matches.
- **`.planning/ROADMAP.md` updated** in three places: (1) Phase Summary table row 14 — "Five Python analyst modules" → "Four Python analyst modules emit structured signals per ticker (5th is Phase 4 POSE)", (2) Phase 3 detail "Goal:" line — same wording fix with explicit POSE reference, (3) Phase 3 detail "Plans:" section populated with 5 checkbox entries (03-01..03-05) with brief objectives.
- **24 new schema tests + 2 xfail invariant tests committed; full repo regression preserved.** Targeted suite `pytest tests/analysts/test_signals.py` → 24/24 green. `pytest tests/analysts/test_invariants.py` → 2/2 XFAIL (exit 0). **Full repo `pytest`** → **212 passed + 2 xfailed** (up from 188 pre-existing tests at Phase 2 close: +24 schema tests, +2 xfail invariants). Coverage on `analysts/signals.py`: **100% line / 100% branch** (gate ≥90% / ≥85%).

## Task Commits

1. **Task 1 — chore: add vaderSentiment dependency for Phase 3 news/sentiment analyst:** `64d0d38` — pyproject.toml +1 line in `[project.dependencies]`. Verified: `python -c "from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer; ..."` returns the polarity-scores dict cleanly.
2. **Task 2 — test: scaffold tests/analysts/ package + shared fixture toolbox:** `201d617` — `tests/analysts/__init__.py` (empty package marker) + `tests/analysts/conftest.py` (175 lines: 3 fixtures + 3 synthetic_*_history builders + helper).
3. **Task 3 RED — test: failing tests for AgentSignal schema (5-state verdict, invariants, round-trip):** `fe5f973` — `tests/analysts/test_signals.py` with 24 tests; pytest fails at the import line because `analysts/signals.py` doesn't exist yet.
4. **Task 3 GREEN — feat: AgentSignal Pydantic schema with 5-state verdict + data_unavailable invariant:** `f03e3fe` — `analysts/signals.py` (120 lines: Verdict + AnalystId Literals + AgentSignal class with 7 fields + 2 field validators + 1 model_validator + provenance header). All 24 tests turn green.
5. **Task 4 — test: scaffold cross-cutting invariant tests (xfail until Wave 2 analysts ship):** `f0931a2` — `tests/analysts/test_invariants.py` with 2 tests under `@pytest.mark.xfail(strict=True)`. Pytest reports 2 XFAIL, exit code 0.
6. **Task 5 — docs: widen REQUIREMENTS ANLY-01..04 verdict wording to 5-state ladder:** `d7a6871` — 4 hunks in `.planning/REQUIREMENTS.md`. `grep -c "5-state ladder" .planning/REQUIREMENTS.md` returns 4; old "bullish/bearish/neutral" wording removed from those four entries.
7. **Task 6 — docs: correct ROADMAP Phase 3 'Five → Four' analyst count + populate plan list:** `a09be56` — Phase 3 row + Phase 3 Goal updated; Plans list populated with 5 checkbox entries. `grep -c "Four Python analyst" .planning/ROADMAP.md` returns 2; `grep -c "03-0[1-5].*PLAN.md" .planning/ROADMAP.md` returns 5.

**Plan metadata commit:** added in this closeout session (covers SUMMARY.md, STATE.md, ROADMAP.md plan-progress row).

## Files Created/Modified

### Created
- `analysts/signals.py` (120 lines)
- `tests/analysts/__init__.py` (0 lines — package marker)
- `tests/analysts/conftest.py` (175 lines)
- `tests/analysts/test_signals.py` (215 lines, 24 tests)
- `tests/analysts/test_invariants.py` (111 lines, 2 xfail-marked tests)

### Modified
- `pyproject.toml` (+1 line — `"vaderSentiment>=3.3,<4",` appended to `[project.dependencies]`)
- `.planning/REQUIREMENTS.md` (4 hunks — ANLY-01..04 widened to 5-state ladder)
- `.planning/ROADMAP.md` (Phase 3 row + Phase 3 detail Goal + Phase 3 Plans list)

## Decisions Made

- **Schema-level invariant enforcement via `@model_validator(mode="after")`** — the data_unavailable=True ⟹ verdict='neutral' AND confidence=0 rule is enforced in the model itself, not at caller convention. Closes 03-RESEARCH.md Pitfall #4. Means a buggy analyst can never write a `(data_unavailable=True, verdict='bullish', confidence=80)` signal to disk; Phase 5/6 consumers can rely on the contract without defensive checks. The error message names BOTH offending values (`verdict='bullish' (expected 'neutral'), confidence=80 (expected 0)`) so a debugging analyst author can see exactly what they sent.
- **Verdict + AnalystId Literal types co-located at module level** — every Wave 2 analyst module imports them as the single source of truth (`from analysts.signals import AgentSignal, Verdict, AnalystId`). No string duplication of the 5 ladder values or the 4 analyst ids anywhere downstream.
- **Factory-fixture pattern beats fixture-class pattern** — `make_ticker_config` and `make_snapshot` return closures that accept keyword overrides, so test bodies read like `cfg = make_ticker_config(ticker="NVDA", thesis_price=900.0)`. 03-RESEARCH.md Pattern 2.
- **Synthetic-history builders are MODULE-level, not pytest fixtures** — importable directly via `from tests.analysts.conftest import synthetic_uptrend_history` so Wave 2 test files can pin n explicitly (e.g. 252 bars for MA200 warm-up coverage in 03-03). Pytest fixtures wrap the builders for the common case; tests call the builders directly when they want to vary n.
- **Determinism contract on synthetic builders** — no `random.random()` calls; noise term is `0.001 * ((i % 5) - 2)` for HLC variance, `i * 100` for volume drift. Two calls with identical args produce byte-identical OHLCBar lists. Sets the determinism contract Wave 2 plans rely on for stable assertions.
- **`synthetic_sideways_history` parameters chosen by formula, not by ADX-targeting iteration** — 20-bar sin period at 2% amplitude (no drift) per the formula in 03-CONTEXT.md. By construction MA20 ≈ MA50 ≈ MA200 ≈ start and ADX < 20 (range regime), which is what 03-03 needs for trend-gating verification. No need to compute ADX during fixture authoring.
- **`test_invariants.py` ships AT WAVE 1 with strict xfail markers** — file collects cleanly even before 03-02..03-05 land (analyst-module imports inside each test body, so `ImportError` during XFAIL is the expected RED state). Plan 03-05 explicitly removes the markers in its final task; `strict=True` on each marker means an unexpected GREEN fails loudly so over-shipping in Wave 2 is caught immediately.
- **vaderSentiment is added at Wave 1 (this plan) with NO production import** — the dep + lockfile entry survives even if Wave 2 plans are reordered. Plan 03-04 (news/sentiment analyst) will land the actual `from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer` import during its execution.
- **ROADMAP.md plan-progress row updated MANUALLY**, not via `gmd-tools roadmap update-plan-progress 3`. Per the precedent set in Plan 02-07 closeout, that command is known to mangle the descriptive Phase Summary row format (replaces named cells with bare counters). Manual edit preserves the format that mirrors Phase 1 + Phase 2 in the table.
- **24 tests in test_signals.py exceeds the plan's ≥16 floor** — the `@pytest.mark.parametrize` over 5 verdict literals expands into 5 separate test instances, AND 2 tightening tests were added during execution (`test_evidence_string_at_cap_ok` to pin the 200-char inclusive boundary, `test_analyst_id_literal_rejects_unknown` to lock the AnalystId Literal at the schema layer). Plus a smoke test (`test_verdict_and_analyst_id_types_exposed`) confirming the public Literal types survive future refactors.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Missing Critical] Added `test_evidence_string_at_cap_ok` boundary test**
- **Found during:** Task 3 RED writing — the plan's `test_evidence_string_too_long` covers ">200 chars rejected" but the inclusive boundary at exactly 200 chars was unverified; off-by-one in either direction (using `>=` instead of `>`) would silently pass without it.
- **Fix:** Added one test that constructs `AgentSignal(..., evidence=["x" * 200])` and asserts it succeeds.
- **Verification:** Test green; locks the `len(s) > 200` predicate (NOT `>=`) at the schema-validator layer.
- **Committed in:** `fe5f973` (RED), `f03e3fe` (GREEN — already-correct schema passes the new boundary test).

**2. [Rule 2 — Missing Critical] Added `test_analyst_id_literal_rejects_unknown` Literal-coverage test**
- **Found during:** Task 3 RED writing — the plan covered Verdict literal rejection (`test_verdict_literal_rejects_unknown`) but not AnalystId. A typo'd id like `"fundamental"` (singular) would otherwise silently land if the Literal annotation drifted in the future.
- **Fix:** Added one test that constructs `AgentSignal(..., analyst_id="fundamental")` and asserts ValidationError.
- **Verification:** Test green; locks the AnalystId Literal at the schema layer the same way Verdict is locked.
- **Committed in:** `fe5f973` (RED), `f03e3fe` (GREEN).

---

**Total deviations:** 2 auto-fixed (both Rule 2 — additive boundary/coverage tests beyond the plan's ≥16 floor). **Impact:** Tightening only. Schema implementation matches the plan's specifications byte-for-byte; the additions are 2 extra tests that would have caught a future regression on the Literal annotations or the off-by-one boundary.

## Issues Encountered

- **None during this closeout session.** All 7 task commits had landed cleanly in a prior session before this closeout. Working tree was clean when this session started; verification confirmed all artifacts present at expected paths and shapes, all tests green at expected counts, all coverage gates cleared.
- **Phase 2 closeout's `gmd-tools roadmap update-plan-progress` warning carried forward:** that command is known to mangle the descriptive Phase Summary row format (precedent set in Plan 02-07 closeout); the row is being updated manually here instead.

## Self-Check: PASSED

- [x] `analysts/signals.py` exists — FOUND (120 lines)
- [x] `tests/analysts/__init__.py` exists — FOUND (0 lines, package marker)
- [x] `tests/analysts/conftest.py` exists — FOUND (175 lines)
- [x] `tests/analysts/test_signals.py` exists — FOUND (215 lines, 24 tests)
- [x] `tests/analysts/test_invariants.py` exists — FOUND (111 lines, 2 xfail-marked tests)
- [x] `pyproject.toml` lists `vaderSentiment>=3.3,<4` — VERIFIED via `grep -E "vaderSentiment" pyproject.toml`
- [x] `vaderSentiment` importable in venv — VERIFIED via `python -c "from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer; ..."`
- [x] REQUIREMENTS.md ANLY-01..04 widened to 5-state ladder — VERIFIED via `grep -c "5-state ladder" .planning/REQUIREMENTS.md` returns 4
- [x] ROADMAP.md says "Four Python analyst" (not "Five") — VERIFIED via `grep -c "Four Python analyst" .planning/ROADMAP.md` returns 2
- [x] ROADMAP.md Plans list has 5 entries (03-01..03-05) — VERIFIED via `grep -c "03-0[1-5].*PLAN.md" .planning/ROADMAP.md` returns 5
- [x] Commit `64d0d38` (Task 1 chore — vaderSentiment dep) — FOUND
- [x] Commit `201d617` (Task 2 test — fixture toolbox scaffold) — FOUND
- [x] Commit `fe5f973` (Task 3 RED — failing tests for AgentSignal) — FOUND
- [x] Commit `f03e3fe` (Task 3 GREEN — AgentSignal schema implementation) — FOUND
- [x] Commit `f0931a2` (Task 4 test — xfail invariant scaffold) — FOUND
- [x] Commit `d7a6871` (Task 5 docs — REQUIREMENTS widening) — FOUND
- [x] Commit `a09be56` (Task 6 docs — ROADMAP "Five → Four") — FOUND
- [x] `pytest tests/analysts/test_signals.py -q` — 24/24 green
- [x] `pytest tests/analysts/test_invariants.py -v` — 2/2 XFAIL (exit 0); strict=True markers active
- [x] `pytest -q` (full repo regression) — **212 passed + 2 xfailed** (up from 188 at Phase 2 close: +24 schema tests + 2 xfail invariants)
- [x] Coverage gate ≥90% line / ≥85% branch on `analysts/signals.py`: **100% line / 100% branch** ✓
- [x] AgentSignal round-trips through `model_dump_json` → `model_validate_json` byte-stable — VERIFIED via `test_json_round_trip` + `test_byte_stable_serialization`
- [x] Synthetic builders deterministic and importable — VERIFIED via `python -c "from tests.analysts.conftest import synthetic_uptrend_history, synthetic_downtrend_history, synthetic_sideways_history; up = synthetic_uptrend_history(252); ..."` returns up[-1].close=351.43 / dn[-1].close=56.55 / sw[-1].close=149.07
- [x] @model_validator data-unavailable invariant fires on both verdict AND confidence violations — VERIFIED via `test_data_unavailable_invariant_violation_verdict` + `test_data_unavailable_invariant_violation_confidence`
- [x] `extra="forbid"` discipline preserved — VERIFIED via `test_extra_field_forbidden`

### Expected-RED tests (NOT failures)

The 2 tests in `tests/analysts/test_invariants.py` are EXPECTED to be in XFAIL state at Wave 1 close — they exercise the contract every Wave 2 analyst plan promises but require all four analyst modules (`analysts/{fundamentals,technicals,news_sentiment,valuation}.py`) to be importable. The `@pytest.mark.xfail(strict=True)` markers on each:

- `tests/analysts/test_invariants.py::test_always_four_signals` — XFAIL (analyst modules don't exist yet; flips green when 03-05 lands)
- `tests/analysts/test_invariants.py::test_dark_snapshot_emits_four_unavailable` — XFAIL (same)

Plan 03-05 (the LAST Wave 2 plan to commit per the dependency graph) MUST remove the `@pytest.mark.xfail` markers in its final task — at that point both tests flip GREEN naturally as the four analyst modules exist and respect the dark-snapshot UNIFORM RULE. The `strict=True` on each marker means an unexpected GREEN before then fails loudly (a Wave 2 plan accidentally over-shipped or these markers were left in place after Wave 2 close).

## Next Phase Readiness

- **Phase 3 Wave 2 fully unblocked.** All four Wave 2 analyst plans (03-02 fundamentals, 03-03 technicals, 03-04 news_sentiment, 03-05 valuation) can now be executed in parallel — they all import `AgentSignal` + `Verdict` + `AnalystId` from `analysts.signals`, they all import the shared fixture toolbox (`make_snapshot`, `make_ticker_config`, `frozen_now`, `synthetic_*_history`) from `tests.analysts.conftest`, and the `vaderSentiment` dep needed by 03-04 is already in place.
- **03-04 (news/sentiment analyst) ships with no Wave 0 reshuffle** — the `vaderSentiment>=3.3,<4` dep is already in pyproject.toml. 03-04's first import line is `from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer` and it works without preamble.
- **03-05 (valuation analyst) wraps Wave 2** — its final task removes the `@pytest.mark.xfail(strict=True)` markers from `tests/analysts/test_invariants.py`. At that point the cross-cutting "always 4 signals" + "dark snapshot ⇒ 4 data_unavailable=True" invariants flip GREEN naturally. The strict markers guarantee that any Wave 2 plan accidentally over-shipping these contracts (or any plan leaving the markers in place after 03-05) fails loudly.
- **REQUIREMENTS.md ANLY-01..04 wording matches the locked schema** — Wave 2 plan-checker iterations won't snag on the 3-state vs 5-state mismatch that 03-CONTEXT.md flagged.
- **ROADMAP.md Phase 3 row + Goal + Plans list match the actual plan slate** — the "Five → Four" miscount is closed, and the 5 plans (03-01..03-05) are enumerated for traceability. The 5th analyst-style module (Position-Adjustment) is correctly attributed to Phase 4 / POSE.
- **No carry-overs / no blockers from this plan.** Wave 1 closes cleanly; the foundation surface every Wave 2 plan needs is now in place.

---
*Phase: 03-analytical-agents-deterministic-scoring*
*Plan: 01-signals*
*Completed: 2026-05-02*
