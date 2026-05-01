---
phase: 02-ingestion-keyless-data-plane
plan: 07
type: tdd
wave: 0
depends_on: [02-02]
files_modified:
  - analysts/data/fundamentals.py
  - ingestion/fundamentals.py
  - ingestion/prices.py
  - tests/ingestion/test_fundamentals.py
  - tests/ingestion/test_prices.py
autonomous: true
requirements: [DATA-01, DATA-02]
provides:
  - "FundamentalsSnapshot.analyst_target_mean / analyst_target_median / analyst_recommendation_mean / analyst_opinion_count (4 new Optional fields)"
  - "ingestion.fundamentals.fetch_fundamentals reads info['targetMeanPrice'], info['targetMedianPrice'], info['recommendationMean'], info['numberOfAnalystOpinions'] via _safe_float / _safe_int"
  - "ingestion.prices.fetch_prices default period bumped from '3mo' to '1y' (~252 trading days — unlocks MA200 / 6m momentum / stable ADX in Phase 3 technicals)"
tags: [phase-2-amendment, schema-additive, fundamentals, prices, prerequisite-for-phase-3, valuation-input, technicals-warmup, tdd]

must_haves:
  truths:
    - "FundamentalsSnapshot accepts 4 new Optional fields without rejecting existing snapshots (additive schema change — backward-compatible)"
    - "fetch_fundamentals populates analyst_target_mean / analyst_target_median / analyst_recommendation_mean from info['targetMeanPrice'] / info['targetMedianPrice'] / info['recommendationMean'] when present"
    - "fetch_fundamentals populates analyst_opinion_count from info['numberOfAnalystOpinions'] when present (int, not float — separate coercion via _safe_int helper)"
    - "When all 4 analyst-consensus keys are missing or non-numeric, the four new fields are None and existing data_unavailable logic is unchanged"
    - "fetch_prices default period is '1y' — produces ~252 trading bars, sufficient for MA200 + 6m momentum + stable ADX downstream"
    - "Existing Phase 2 tests that pin period='3mo' explicitly still pass (they pass period kwarg explicitly; default change is invisible to them)"
    - "Existing Phase 2 refresh orchestrator tests (tests/ingestion/test_refresh.py) still green — additive schema change does not break Snapshot validation or sort_keys serialization"
  artifacts:
    - path: "analysts/data/fundamentals.py"
      provides: "4 new Optional[float | int] fields on FundamentalsSnapshot"
      min_lines: 50
    - path: "ingestion/fundamentals.py"
      provides: "fetch_fundamentals reads 4 new yfinance .info keys; helper _safe_int for opinion_count"
      min_lines: 130
    - path: "ingestion/prices.py"
      provides: "fetch_prices default period='1y'"
      min_lines: 200
    - path: "tests/ingestion/test_fundamentals.py"
      provides: "5+ new tests covering happy / partial / all-missing / non-numeric paths for the 4 fields"
      min_lines: 50
  key_links:
    - from: "ingestion/fundamentals.py"
      to: "analysts/data/fundamentals.py:FundamentalsSnapshot"
      via: "constructor kwargs (analyst_target_mean=..., analyst_target_median=..., analyst_recommendation_mean=..., analyst_opinion_count=...)"
      pattern: "analyst_target_mean=|analyst_recommendation_mean=|analyst_opinion_count="
    - from: "ingestion/fundamentals.py"
      to: "yfinance.Ticker(t).info"
      via: "info.get('targetMeanPrice'), info.get('targetMedianPrice'), info.get('recommendationMean'), info.get('numberOfAnalystOpinions')"
      pattern: "targetMeanPrice|targetMedianPrice|recommendationMean|numberOfAnalystOpinions"
---

<objective>
Phase 2 amendment — additive schema + ingestion change required by Phase 3 ANLY-04 (valuation analyst). Adds four analyst-consensus fields to FundamentalsSnapshot and populates them from yfinance .info in fetch_fundamentals. Also bumps fetch_prices default period from "3mo" to "1y" so Phase 3 technicals analyst (ANLY-02) has enough bars for MA200 / 6m momentum / stable ADX without per-call period overrides.

Purpose: Phase 3 valuation analyst's tertiary blend tier reads `snapshot.fundamentals.analyst_target_mean`. That field does not exist today (verified via Read of analysts/data/fundamentals.py). Without this amendment, valuation.score() would either AttributeError or have to defensively `getattr(..., None)` everywhere. Phase 2 amendment is the right home — keeps Phase 3 plans pure-function pure (no schema or ingestion work). Bumping fetch_prices default to "1y" is a tiny additive change that unlocks the technicals analyst's full feature set; existing tests pass period explicitly so they're unaffected.

Output: 4 new fields on FundamentalsSnapshot (3 Optional[float] + 1 Optional[int]); fetch_fundamentals populates them via _safe_float / _safe_int; fetch_prices default flipped to "1y"; 5+ new tests covering happy + partial + missing paths. All existing Phase 2 tests remain green.

This plan is Phase 3's Wave 0 dependency (in dependency terms) but lives in the Phase 2 directory because the changes ARE Phase 2 schema/ingestion concerns. Phase 3 plan 03-05 (valuation analyst) declares `depends_on: [02-07]` to express the cross-phase ordering.
</objective>

<execution_context>
@/home/codespace/.claude/get-magic-done/workflows/execute-plan.md
@/home/codespace/.claude/get-magic-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/02-ingestion-keyless-data-plane/02-02-SUMMARY.md
@.planning/phases/02-ingestion-keyless-data-plane/02-06-SUMMARY.md
@.planning/phases/03-analytical-agents-deterministic-scoring/03-CONTEXT.md
@.planning/phases/03-analytical-agents-deterministic-scoring/03-RESEARCH.md

# Files this plan modifies
@analysts/data/fundamentals.py
@ingestion/fundamentals.py
@ingestion/prices.py

<interfaces>
<!-- Existing FundamentalsSnapshot shape (analysts/data/fundamentals.py): -->

```python
class FundamentalsSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticker: str
    fetched_at: datetime
    source: Literal["yfinance", "yahooquery"]
    data_unavailable: bool = False
    pe: Optional[float] = None
    ps: Optional[float] = None
    pb: Optional[float] = None
    roe: Optional[float] = None
    debt_to_equity: Optional[float] = None
    profit_margin: Optional[float] = None
    free_cash_flow: Optional[float] = None
    market_cap: Optional[float] = None
    # ticker normalizer (existing)
```

<!-- New fields to add — additive at the end of the field list to preserve sort_keys output ordering across existing tests: -->

```python
    # NEW (Plan 02-07): yfinance analyst consensus fields. Read via
    # info.get("targetMeanPrice") etc. with _safe_float / _safe_int coercion.
    # Consumed in Phase 3 by analysts/valuation.py (tertiary blend tier).
    analyst_target_mean: Optional[float] = None
    analyst_target_median: Optional[float] = None
    analyst_recommendation_mean: Optional[float] = None    # 1.0=strong_buy ... 5.0=strong_sell
    analyst_opinion_count: Optional[int] = None
```

<!-- Existing fetch_fundamentals canonical-marker check (ingestion/fundamentals.py line 115):
       canonical_missing = pe is None and market_cap is None
     This logic is UNCHANGED — analyst-consensus fields don't influence data_unavailable.
     They're additive metadata. -->

<!-- Existing _safe_float helper (ingestion/fundamentals.py lines 41-60):
       Returns Optional[float]; rejects bools; rejects NaN/inf; passes ints/floats. -->

<!-- New helper (this plan adds):
       _safe_int(v: Any) -> Optional[int]: same defensive coercion as _safe_float
       but for integer fields (numberOfAnalystOpinions). Rejects bools, NaN, inf,
       non-numeric strings. -->

<!-- Existing fetch_prices signature (ingestion/prices.py line 207):
       def fetch_prices(ticker: str, *, period: str = "3mo") -> PriceSnapshot
     Change: default "3mo" → "1y". Docstring update to match. Phase 3 RESEARCH.md
     Pitfall #1 explains the why: ADX stable ~150 bars, MA200 needs 200, 6m
     momentum needs 126; "3mo" ≈ 63 — too few. -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Schema + tests — FundamentalsSnapshot 4 new analyst-consensus fields</name>
  <files>analysts/data/fundamentals.py, tests/ingestion/test_fundamentals.py</files>
  <behavior>
    Additive Pydantic v2 field additions. Each new field is Optional, defaults to None, no validators (the orchestrator and downstream analysts handle missing data via the same Optional pattern as pe/ps/pb).

    Tests to add to tests/ingestion/test_fundamentals.py (note: this file already exists from Plan 02-02; this task APPENDS to it):

    - test_fundamentals_snapshot_accepts_analyst_fields_when_provided: construct FundamentalsSnapshot with all 4 new fields populated (analyst_target_mean=180.5, analyst_target_median=185.0, analyst_recommendation_mean=2.1, analyst_opinion_count=42); assert each field round-trips via model_dump(mode="json").
    - test_fundamentals_snapshot_accepts_analyst_fields_when_omitted: construct without any of the 4 new fields; assert all default to None; assert existing data_unavailable / pe / ps fields still work.
    - test_fundamentals_snapshot_rejects_invalid_opinion_count_type: opinion_count=42.5 (float) — Pydantic v2 strict-int by default coerces; verify project's coercion behavior matches expectations (`Optional[int]` typically allows float→int coercion). Either lock "42.5 coerces to 42" or "Pydantic rejects". Document the chosen behavior.
    - test_fundamentals_snapshot_extra_forbid_still_active: construct with `extra_unknown_field=1` → expect ValidationError on extra field (`extra="forbid"` discipline preserved).
  </behavior>
  <action>
    RED:
    1. Append the 4 tests above to `tests/ingestion/test_fundamentals.py`. Imports needed: `from analysts.data.fundamentals import FundamentalsSnapshot`; `from datetime import datetime, timezone`; `from pydantic import ValidationError`; `import pytest`.
    2. Run `uv run pytest tests/ingestion/test_fundamentals.py -x -q -k "analyst_fields or opinion_count"` → 4 tests fail with AttributeError or "extra not allowed" (because the fields don't exist yet on the schema).
    3. Commit: `test(02-07): add failing tests for FundamentalsSnapshot analyst-consensus fields`

    GREEN:
    4. Edit `analysts/data/fundamentals.py`:
       - Append 4 new fields after `market_cap` (preserves alphabetical sort_keys output ordering — new fields are alphabetically AFTER existing ones in JSON output):
         ```python
             # NEW (Plan 02-07): yfinance analyst consensus fields. Optional;
             # populated by ingestion/fundamentals.py from info["targetMeanPrice"]
             # etc. Consumed in Phase 3 by analysts/valuation.py (tertiary blend).
             analyst_target_mean: Optional[float] = None
             analyst_target_median: Optional[float] = None
             analyst_recommendation_mean: Optional[float] = None
             analyst_opinion_count: Optional[int] = None
         ```
       - Update module docstring to mention the new fields' purpose (one short paragraph).
    5. Run `uv run pytest tests/ingestion/test_fundamentals.py -x -q -k "analyst_fields or opinion_count"` → 4 green.
    6. Run full Phase 2 ingestion suite to verify no regression on existing tests: `uv run pytest tests/ingestion/test_fundamentals.py -v` → all green (existing + 4 new).
    7. Run refresh orchestrator suite to verify Snapshot serialization still works (extra="forbid" + new fields):
       `uv run pytest tests/ingestion/test_refresh.py -v` → all green (the additive change MUST NOT break existing Snapshot round-trip tests).
    8. Commit: `feat(02-07): add 4 analyst-consensus fields to FundamentalsSnapshot`
  </action>
  <verify>
    <automated>uv run pytest tests/ingestion/test_fundamentals.py -v &amp;&amp; uv run pytest tests/ingestion/test_refresh.py -v</automated>
  </verify>
  <done>4 new fields on FundamentalsSnapshot; 4+ new tests green; existing 23+ Phase 2 ingestion tests green; refresh orchestrator round-trip still passes (additive change is backward-compatible).</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: ingestion/fundamentals.py — populate the 4 new fields from yfinance .info</name>
  <files>ingestion/fundamentals.py, tests/ingestion/test_fundamentals.py</files>
  <behavior>
    Augment fetch_fundamentals to read 4 additional keys from `info`:
    - `targetMeanPrice` → `analyst_target_mean` (via _safe_float)
    - `targetMedianPrice` → `analyst_target_median` (via _safe_float)
    - `recommendationMean` → `analyst_recommendation_mean` (via _safe_float; 1.0=strong_buy..5.0=strong_sell scale)
    - `numberOfAnalystOpinions` → `analyst_opinion_count` (via NEW _safe_int helper)

    Add `_safe_int(v) -> Optional[int]` helper. Defensive coercion mirrors _safe_float: rejects bools, NaN/inf, non-numeric strings; accepts ints; FLOORS floats to int (e.g., 42.7 → 42; defensive against yfinance occasionally returning floats for count fields).

    Existing `data_unavailable` logic (canonical_missing = pe is None and market_cap is None) is UNCHANGED — the 4 new fields are advisory metadata, not part of the data_unavailable predicate.

    Tests to add (appended to tests/ingestion/test_fundamentals.py):

    - test_fetch_fundamentals_populates_analyst_fields: monkeypatch yfinance.Ticker so .info returns a dict with all 4 keys present (targetMeanPrice=180.5, targetMedianPrice=185.0, recommendationMean=2.1, numberOfAnalystOpinions=42). Call fetch_fundamentals("AAPL"); assert all 4 fields on the returned FundamentalsSnapshot are populated correctly.
    - test_fetch_fundamentals_handles_missing_analyst_fields: monkeypatch .info to omit all 4 keys (only pe / market_cap / etc. present). Call fetch_fundamentals; assert all 4 new fields are None; assert data_unavailable=False (canonical pe / market_cap present).
    - test_fetch_fundamentals_handles_partial_analyst_fields: only `targetMeanPrice` present; other 3 missing. Assert analyst_target_mean populated, other 3 None.
    - test_fetch_fundamentals_handles_non_numeric_analyst_fields: targetMeanPrice="N/A" (string), recommendationMean=float("nan"), numberOfAnalystOpinions=True (bool — `isinstance(True, int)` is True but we explicitly reject bools). Assert all 4 are None (via _safe_float / _safe_int defensive coercion).
    - test_safe_int_helper: unit-test the _safe_int helper directly: inputs (None, True, False, 42, 42.7, -3, "5", float("nan"), float("inf")) → outputs (None, None, None, 42, 42, -3, None, None, None). Document the floor behavior for floats.
  </behavior>
  <action>
    RED:
    1. Append the 5 tests above to `tests/ingestion/test_fundamentals.py`. Use `monkeypatch.setattr("yfinance.Ticker", ...)` or `unittest.mock.patch("yfinance.Ticker")`. The existing test file already has the monkeypatch pattern — mirror it.
    2. Run `uv run pytest tests/ingestion/test_fundamentals.py -x -q -k "analyst_fields or safe_int"` → 5 tests fail (fetch_fundamentals doesn't populate the new fields; _safe_int doesn't exist).
    3. Commit: `test(02-07): add failing tests for fetch_fundamentals analyst-consensus reads`

    GREEN:
    4. Edit `ingestion/fundamentals.py`:
       - Add `_safe_int` helper next to `_safe_float`:
         ```python
         def _safe_int(v: Any) -> Optional[int]:
             """Coerce a yfinance .info value to int — None if not a finite number.

             Same defensive posture as _safe_float: rejects bools (Python treats
             True/False as int subclasses), rejects NaN/inf, rejects non-numeric
             strings. Floors floats to int (yfinance occasionally returns floats
             for count fields).
             """
             if v is None or isinstance(v, bool):
                 return None
             if isinstance(v, int):
                 return v
             if isinstance(v, float):
                 if v != v or v == float("inf") or v == float("-inf"):
                     return None
                 return int(v)  # floor (truncate toward zero for positives)
             return None
         ```
       - In `fetch_fundamentals`, after the existing `_safe_float` reads, add 4 new reads:
         ```python
             analyst_target_mean = _safe_float(info.get("targetMeanPrice"))
             analyst_target_median = _safe_float(info.get("targetMedianPrice"))
             analyst_recommendation_mean = _safe_float(info.get("recommendationMean"))
             analyst_opinion_count = _safe_int(info.get("numberOfAnalystOpinions"))
         ```
       - Pass these as kwargs to the FundamentalsSnapshot constructor at the bottom of the function.
       - Module docstring updated to list the 4 new keys read.
    5. Run `uv run pytest tests/ingestion/test_fundamentals.py -v` → all green.
    6. Coverage on the modified file: `uv run pytest --cov=ingestion.fundamentals --cov-branch tests/ingestion/test_fundamentals.py` → ≥90% line / ≥85% branch.
    7. Full repo regression: `uv run pytest -x -q` → 177+ tests still green (additive change).
    8. Commit: `feat(02-07): populate analyst-consensus fields in fetch_fundamentals`
  </action>
  <verify>
    <automated>uv run pytest tests/ingestion/test_fundamentals.py -v &amp;&amp; uv run pytest --cov=ingestion.fundamentals --cov-branch tests/ingestion/test_fundamentals.py &amp;&amp; uv run pytest -x -q</automated>
  </verify>
  <done>fetch_fundamentals populates all 4 new fields from yfinance .info; _safe_int helper covers bool / NaN / inf / string / float-floor cases; coverage ≥90/85 on ingestion/fundamentals.py; full repo suite green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: ingestion/prices.py — bump default period from "3mo" to "1y"</name>
  <files>ingestion/prices.py, tests/ingestion/test_prices.py</files>
  <behavior>
    Tiny one-character change to the function default + docstring sync. Existing tests that pass `period=` explicitly are unaffected; tests that rely on the default change to "1y" expectations.

    Why: Phase 3 RESEARCH.md Pitfall #1 — "3mo" yields ~63 trading days; MA200 needs 200, 6m momentum needs 126, stable ADX needs ~150. "1y" yields ~252 — enough for everything Phase 3 technicals analyst computes. Cost: ~3KB extra per snapshot per ticker, negligible at 50-ticker watchlist.

    Tests:
    - test_fetch_prices_default_period_is_1y: monkeypatch yfinance.Ticker.history to capture the period kwarg passed in. Call fetch_prices("AAPL") (no period kwarg). Assert history was called with period="1y".
    - test_fetch_prices_explicit_period_still_honored: call fetch_prices("AAPL", period="6mo"); assert history called with period="6mo" (default override still works).
    - Update any existing test that asserts about `period="3mo"` defaults — flip expectation to "1y". (Most existing Plan 02-02 tests should pass period="3mo" explicitly when they care; verify by reading the file.)
  </behavior>
  <action>
    RED:
    1. Read tests/ingestion/test_prices.py to enumerate any test that assumes the default is "3mo". Update those expectations to "1y" inline (rare — most tests pass period explicitly).
    2. Add the 2 new tests above. Use the existing yfinance.Ticker monkeypatch pattern from Plan 02-02 (the test file already has fixtures for this).
    3. Run `uv run pytest tests/ingestion/test_prices.py -x -q` → 2 new tests fail (default still "3mo"); any old test that asserted "3mo" default still passes (we update the assertion in the same RED commit).
    4. Commit: `test(02-07): expect fetch_prices default period='1y'`

    GREEN:
    5. Edit `ingestion/prices.py`:
       - Change line 207 signature from `def fetch_prices(ticker: str, *, period: str = "3mo") -> PriceSnapshot:` to `def fetch_prices(ticker: str, *, period: str = "1y") -> PriceSnapshot:`.
       - Update docstring (lines around 220-227): change "default `\"3mo\"` (~60 trading days)" to "default `\"1y\"` (~252 trading days — enough for MA200 / 6m momentum / stable ADX in downstream Phase 3 analytics; bumped in Plan 02-07)".
    6. Run `uv run pytest tests/ingestion/test_prices.py -v` → all green.
    7. Run refresh orchestrator suite: `uv run pytest tests/ingestion/test_refresh.py -v` — refresh.py calls `fetch_prices(ticker)` without period kwarg, so the new default kicks in. Verify still green.
    8. Run full repo: `uv run pytest -x -q` → 177+ tests green.
    9. Coverage on prices.py: `uv run pytest --cov=ingestion.prices --cov-branch tests/ingestion/test_prices.py` → ≥90/85 (single line change, coverage shouldn't move).
    10. Commit: `feat(02-07): bump fetch_prices default period from 3mo to 1y`
  </action>
  <verify>
    <automated>uv run pytest tests/ingestion/test_prices.py -v &amp;&amp; uv run pytest tests/ingestion/test_refresh.py -v &amp;&amp; uv run pytest -x -q &amp;&amp; uv run pytest --cov=ingestion.prices --cov-branch tests/ingestion/test_prices.py</automated>
  </verify>
  <done>fetch_prices default period flipped to "1y"; new test verifies the default; existing tests with explicit period= unaffected; refresh orchestrator + full repo regression green.</done>
</task>

</tasks>

<verification>
- All 3 tasks ship as TDD RED→GREEN cycles with separate commits.
- Coverage gate: ≥90% line / ≥85% branch on `analysts/data/fundamentals.py` (no logic, schema-only — should remain at 100%) and `ingestion/fundamentals.py` (new _safe_int helper + 4 new reads — should remain ≥90%).
- Full repo regression: 177+ tests green at HEAD after all 3 commits land.
- No backward-compat break: existing snapshots written by Plan 02-06 round-trip cleanly through the new schema (4 new Optional fields default to None; old JSON files validate cleanly).
- ROADMAP.md update: Phase 2 now has 7 plans; flip plans list entry for 02-07 from `[ ]` to `[x]` after Task 3 commits.
</verification>

<success_criteria>
1. `analysts/data/fundamentals.py` ships 4 new Optional fields (`analyst_target_mean`, `analyst_target_median`, `analyst_recommendation_mean`, `analyst_opinion_count`) with `extra="forbid"` discipline preserved.
2. `ingestion/fundamentals.py:fetch_fundamentals` reads 4 new yfinance .info keys via `_safe_float` / `_safe_int` and passes them through to the constructed `FundamentalsSnapshot`.
3. `ingestion/prices.py:fetch_prices` default `period` is `"1y"`.
4. 9+ new tests across the 3 tasks (4 schema + 5 ingestion) all green.
5. Full Phase 1 + Phase 2 regression suite green at HEAD (177+ tests).
6. Coverage gates met on every touched file (`analysts/data/fundamentals.py`, `ingestion/fundamentals.py`, `ingestion/prices.py`).
7. Phase 3 plan 03-05 (valuation analyst) can now read `snapshot.fundamentals.analyst_target_mean` directly without `getattr` defensive code — gate cleared for Wave 2 of Phase 3.
</success_criteria>

<output>
After completion, create `.planning/phases/02-ingestion-keyless-data-plane/02-07-SUMMARY.md` summarizing the 3 commits and pointing to Phase 3's 03-05 (valuation) as the downstream consumer.

Update `.planning/ROADMAP.md` Phase 2 plan list — append `- [x] 02-07-fundamentals-analyst-fields-PLAN.md — Phase 2 amendment for Phase 3 valuation prerequisite`.

Update `.planning/STATE.md` Recent Decisions with a 02-07 entry (Phase 2 amendment, prerequisite for Phase 3 ANLY-04).
</output>
