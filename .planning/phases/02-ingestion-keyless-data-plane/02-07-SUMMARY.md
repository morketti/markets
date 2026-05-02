---
phase: 02-ingestion-keyless-data-plane
plan: 07
subsystem: ingestion
tags: [phase-2-amendment, schema-additive, fundamentals, prices, prerequisite-for-phase-3, valuation-input, technicals-warmup, tdd]

# Dependency graph
requires:
  - phase: 02-ingestion-keyless-data-plane
    plan: 01
    provides: analysts.data.fundamentals.FundamentalsSnapshot (extra="forbid" Pydantic model with Optional[float] metric fields), analysts.schemas.normalize_ticker
  - phase: 02-ingestion-keyless-data-plane
    plan: 02
    provides: ingestion.fundamentals.fetch_fundamentals (yfinance .info → FundamentalsSnapshot with _safe_float coercion + canonical-marker data_unavailable check), ingestion.prices.fetch_prices (yfinance primary + yahooquery fallback, period kwarg)
provides:
  - "FundamentalsSnapshot.analyst_target_mean / analyst_target_median / analyst_recommendation_mean / analyst_opinion_count (4 new Optional fields — additive, backward-compatible with serialized snapshots from Plan 02-06)"
  - "ingestion.fundamentals._safe_int helper (Optional[int] coercion mirroring _safe_float — rejects bools, NaN, inf, non-numeric strings; floors floats toward zero)"
  - "ingestion.fundamentals.fetch_fundamentals reads info['targetMeanPrice'], info['targetMedianPrice'], info['recommendationMean'], info['numberOfAnalystOpinions'] via _safe_float / _safe_int and passes them through to FundamentalsSnapshot (NOT in canonical-marker check — analyst-consensus fields are advisory metadata)"
  - "ingestion.prices.fetch_prices default period bumped from '3mo' (~63 trading bars) to '1y' (~252 trading bars) — unlocks MA200 / 6m momentum / stable ADX in Phase 3 technicals analyst (ANLY-02) without per-call period overrides"
affects: [phase-3-analytical-agents (consumes the 4 new analyst-consensus fields in Phase 3 valuation analyst tertiary blend; consumes the longer history in Phase 3 technicals analyst MA200 / 6m momentum / stable ADX)]

# Tech tracking
tech-stack:
  added: []   # zero new dependencies — pure additive change to existing modules
  patterns:
    - "Additive Pydantic v2 schema extension with `extra='forbid'` discipline preserved: 4 new Optional fields appended after `market_cap` so JSON sort_keys output ordering stays compatible with Plan 02-06 serialized snapshots (new fields are alphabetically AFTER existing canonical fields)"
    - "Symmetric helper pair: `_safe_int` mirrors `_safe_float` exactly — same bool / NaN / inf rejection, no string-numeric parsing (parity with _safe_float's defensive posture). Floats with no fractional part floor cleanly via `int(v)` (e.g., 42.0 → 42); fractional floats also truncate toward zero by Python semantics. Pydantic v2's int_from_float coercion at model boundary further rejects fractional floats (e.g., 42.5) at construction time, so the helper's truncation is a defense-in-depth layer rather than the primary gate."
    - "Advisory-vs-canonical separation: canonical_missing = pe is None AND market_cap is None remains the SOLE data_unavailable predicate. The 4 new analyst-consensus fields are advisory metadata — populated when present, None when absent, and never influence whether the snapshot is marked data_unavailable. (Obscure tickers can legitimately lack analyst coverage on healthy days; using their absence as a breakage signal would mis-flag every small-cap.)"
    - "One-character default-arg change with documented rationale: `fetch_prices(*, period: str = '1y')` (was `'3mo'`). Existing callers that pin `period=` explicitly are unaffected. Docstring updated to point at Phase 3 RESEARCH Pitfall #1 for the bar-count math (MA200=200, 6m momentum=126, stable ADX=~150)."

key-files:
  created: []   # all changes are edits to existing files
  modified:
    - analysts/data/fundamentals.py (+21 lines — 4 new Optional fields with Plan 02-07 inline comments + module docstring update)
    - ingestion/fundamentals.py (+51 lines, -1 line — `_safe_int` helper, 4 new `_safe_float` / `_safe_int` reads, 4 new constructor kwargs, module docstring update)
    - ingestion/prices.py (+13 lines, -3 lines — default `period` flipped from `"3mo"` to `"1y"`, docstring rationale paragraph added pointing at Phase 3 RESEARCH Pitfall #1)
    - tests/ingestion/test_fundamentals.py (+241 lines — 9 new tests across schema additions and ingestion behavior)
    - tests/ingestion/test_prices.py (+39 lines — 2 new tests for default-period behavior)

key-decisions:
  - "Additive append, not insert: the 4 new fields go AFTER `market_cap` (line 41) on FundamentalsSnapshot, not interleaved. Rationale: JSON serialization with `sort_keys=True` (mandated by ingestion.refresh._write_snapshot) puts fields in alphabetical order regardless of class-body order, so insertion position is cosmetic — but appending at the end keeps `git blame` clean for the existing fields and matches the convention from Plan 02-01."
  - "_safe_int rejects strings outright (no string-numeric parsing). _safe_float behaves the same way. Locking parity here means a future schema-drift failure mode (yfinance starts returning '42' instead of 42 for a count field) surfaces as None rather than silently parsing — which keeps the data_unavailable / per-field-None signal trustworthy for downstream consumers."
  - "_safe_int floors floats toward zero via `int(v)` rather than rounding. yfinance occasionally returns 42.0 for `numberOfAnalystOpinions` (whole-number floats around stale-cache records); flooring those gets the right int answer. Genuine fractional floats (42.7) are rare for count fields, but if they occur the floor is harmless — and at the model boundary Pydantic v2's int_from_float rejects 42.5 outright with ValidationError, so the helper's truncation is just a safety net."
  - "Analyst-consensus fields are NOT part of the canonical-marker data_unavailable check. The check stays `pe is None AND market_cap is None`. Reason: small-cap and obscure tickers legitimately have zero analyst coverage on healthy days — using analyst absence as a breakage signal would mis-flag every tickers without Wall Street coverage. Phase 3's valuation analyst handles missing analyst data via tertiary-blend fallback to thesis_price / target_multiples (per 03-RESEARCH.md / 03-CONTEXT.md), not via data_unavailable propagation."
  - "fetch_prices default period bumped to '1y' (~252 trading bars), not '6mo' (~126 bars) or '2y' (~504 bars). '1y' is the smallest period that satisfies ALL Phase 3 technicals warmup requirements simultaneously (MA200 needs 200 bars, 6m momentum needs 126, stable ADX needs ~150), with a small margin for weekends/holidays. Larger periods buy nothing for the analyst (MA200 doesn't get smarter past 200 bars) but cost ~3KB extra per snapshot per ticker; '1y' is the right floor."
  - "Plan 02-06 ingestion.refresh.fetch_prices call site is implicitly updated by this default change: ingestion/refresh.py line ~95 calls `fetch_prices(ticker)` without a period kwarg, so the orchestrator now writes 1y of bars per snapshot instead of 3mo. No code change needed in refresh.py — the default-arg bump is transparent. Existing 02-06 tests pass period explicitly when they care about it (none do — they monkeypatch fetch_prices entirely), so they're unaffected."
  - "test_fundamentals_snapshot_opinion_count_float_coercion documents Pydantic v2's actual behavior at the schema boundary: 42.0 coerces cleanly to 42 (no fractional loss), 42.5 raises ValidationError (Pydantic's int_from_float prevents silent truncation by default). This pins the contract so a future Pydantic upgrade can't silently flip it. The test was originally drafted as 'either 42.5 → 42 OR Pydantic rejects' — settled on rejection per the actual run."
  - "Tests exercise the 4 new ingestion reads via the existing yfinance.Ticker monkeypatch pattern (mock_ticker.info = {...}) — no new fixture files required. The 4 happy-path / partial / missing / non-numeric scenarios match the structure of the existing test_fund_happy / test_fund_missing / test_fund_partial / test_fund_handles_non_numeric_values tests so the new tests slot in alongside the existing 7 and feel like part of the same suite."

patterns-established:
  - "Phase amendment as a same-phase plan, not a Phase 3 prologue: when downstream phases discover prerequisite gaps in earlier-phase code, the right home is a small additive plan in the earlier phase (here, 02-07 inside 02-ingestion-keyless-data-plane) rather than a Phase 3 plan that backfills schemas. Keeps Phase 3 plans pure-function pure (zero schema or ingestion work) and keeps the 'who owns what' boundary clean."
  - "Cross-phase dependency expressed via plan frontmatter: Phase 3 plan 03-05 declares `depends_on: [02-07]` so the wave/dependency graph captures the prerequisite explicitly. Same convention can be used in any future phase that uncovers a prerequisite gap in earlier-phase output."
  - "Helper function symmetry as defensive contract: when adding a new typed coercion helper (_safe_int alongside _safe_float), mirror the older helper's exact rejection set (None, bools, NaN, inf, non-numeric strings) and lock it with a unit test that enumerates every case. Future helpers (_safe_bool, _safe_str, etc.) will follow the same pattern."
  - "Default-arg bump as a one-character backward-compat change: when a sane new default emerges from downstream requirements (here, '1y' for Phase 3 technicals warmup), bump the default ONLY and update the docstring to point at the rationale doc. Existing callers that pinned the old default explicitly stay green; the change is invisible to them and beneficial to anyone using the default."

requirements-completed: [DATA-01, DATA-02]   # carried forward from PLAN.md frontmatter; both were already marked complete in REQUIREMENTS.md from Plan 02-02. This plan extends their behavior (adds analyst-consensus fields to DATA-02 fundamentals; bumps default history depth for DATA-01 prices) without changing the requirements' coverage status — DATA-01 / DATA-02 stay [x].

# Metrics
duration: ~6min (5 commits across one TDD-discipline session)
completed: 2026-05-02
---

# Phase 02 Plan 07: Fundamentals Analyst-Consensus Fields + Prices History-Depth Bump Summary

**Phase 2 amendment — additive schema + ingestion change required by Phase 3. Adds four analyst-consensus fields (analyst_target_mean / analyst_target_median / analyst_recommendation_mean / analyst_opinion_count) to FundamentalsSnapshot and populates them from yfinance .info via _safe_float / _safe_int helpers in fetch_fundamentals. Bumps fetch_prices default period from "3mo" (~63 trading bars) to "1y" (~252 trading bars) so Phase 3's technicals analyst has sufficient warm-up history for MA200 / 6m momentum / stable ADX without per-call period overrides. Pure additive change — zero new dependencies, zero new files, zero behavioral break for existing callers.**

## Performance

- **Duration:** ~6 min total across 5 commits (Task 1 RED + GREEN, Task 2 GREEN, Task 3 RED + GREEN — Task 2 RED was rolled into Task 1 RED since both schema-shape and ingestion-population tests landed together in `a4672f1`)
- **Tasks:** 3 (auto, TDD: RED + GREEN per task)
- **Files created:** 0 (all changes are additive edits to existing files)
- **Files modified:** 5 (`analysts/data/fundamentals.py`, `ingestion/fundamentals.py`, `ingestion/prices.py`, `tests/ingestion/test_fundamentals.py`, `tests/ingestion/test_prices.py`)

## Accomplishments

- **`analysts/data/fundamentals.py` (+21 lines, total 65 lines)** — appended 4 new Optional fields after `market_cap`:
  - `analyst_target_mean: Optional[float] = None` — Wall Street price target mean (USD).
  - `analyst_target_median: Optional[float] = None` — Wall Street price target median (USD; less skewed than mean).
  - `analyst_recommendation_mean: Optional[float] = None` — Yahoo's 1.0..5.0 scale (1=strong_buy, 2=buy, 3=hold, 4=underperform, 5=strong_sell). Phase 3's valuation analyst re-bins to {-1, 0, +1}.
  - `analyst_opinion_count: Optional[int] = None` — number of analysts in the consensus (informational; downstream weighting can use this to dampen low-coverage tickers).
  - All 4 fields default to `None`, preserving backward compatibility with existing serialized snapshots from Plan 02-06. `ConfigDict(extra="forbid")` discipline preserved (locked by `test_fundamentals_snapshot_extra_forbid_still_active`).
  - Module docstring extended with a paragraph naming the 4 new fields and pointing at Phase 3's valuation analyst (ANLY-04) as the consumer.
- **`ingestion/fundamentals.py` (+51 lines, -1 line, total 180 lines)** — three changes:
  - **New `_safe_int(v) -> Optional[int]` helper** mirrors `_safe_float`'s defensive posture: rejects None, bools, NaN, inf, non-numeric strings; accepts plain ints; truncates floats toward zero via `int(v)` (yfinance occasionally returns 42.0 for count fields around stale-cache records). Unit-tested directly via `test_safe_int_helper` against the full input matrix (None / True / False / 42 / -3 / 0 / 42.7 / 42.0 / "5" / "N/A" / NaN / inf / -inf).
  - **4 new reads in `fetch_fundamentals`** wired through to the FundamentalsSnapshot constructor:
    - `info.get("targetMeanPrice")` → `_safe_float` → `analyst_target_mean`
    - `info.get("targetMedianPrice")` → `_safe_float` → `analyst_target_median`
    - `info.get("recommendationMean")` → `_safe_float` → `analyst_recommendation_mean`
    - `info.get("numberOfAnalystOpinions")` → `_safe_int` → `analyst_opinion_count`
  - **`canonical_missing` predicate UNCHANGED** — still `pe is None AND market_cap is None`. The 4 new fields are advisory metadata; their absence does NOT influence `data_unavailable`. (Locked by `test_fetch_fundamentals_handles_missing_analyst_fields` — canonical fields present + all 4 analyst fields absent → `data_unavailable=False`.)
- **`ingestion/prices.py` (+13 lines, -3 lines, total 257 lines)** — `fetch_prices` default `period` flipped from `"3mo"` to `"1y"`. Docstring updated to:
  1. Name the new default in the public-surface docstring.
  2. Explain the rationale (~252 trading bars; enough for MA200 / 6m momentum / stable ADX in Phase 3) inline at the parameter docstring.
  3. Note that callers passing `period=` explicitly are unaffected.
  Existing tests that monkeypatch `yfinance.Ticker` and never inspect `period` kwarg pass through unchanged. The Plan 02-06 orchestrator (`ingestion/refresh.py`) calls `fetch_prices(ticker)` without `period` so it now persists 1y of bars per snapshot — a transparent benefit, not a behavior change requiring 02-06 test updates.
- **11 new tests** added across the two existing test files (29 plan-07-relevant tests in total when including the previously-shipped 18 in tests/ingestion/test_fundamentals.py + tests/ingestion/test_prices.py prior to this plan):
  - **Schema additions (4 tests, in `tests/ingestion/test_fundamentals.py`):**
    - `test_fundamentals_snapshot_accepts_analyst_fields_when_provided` — all 4 fields populate + round-trip through `model_dump(mode="json")`.
    - `test_fundamentals_snapshot_accepts_analyst_fields_when_omitted` — defaults to None; existing fields still work; `data_unavailable=False`.
    - `test_fundamentals_snapshot_opinion_count_float_coercion` — locks Pydantic v2's behavior: 42.0 → 42 cleanly; 42.5 → ValidationError (no silent truncation).
    - `test_fundamentals_snapshot_extra_forbid_still_active` — `extra_unknown_field=1` raises ValidationError after the additive change.
  - **Ingestion population (5 tests, in `tests/ingestion/test_fundamentals.py`):**
    - `test_fetch_fundamentals_populates_analyst_fields` — yfinance .info has all 4 keys → all 4 snapshot fields populated correctly; canonical fields still work.
    - `test_fetch_fundamentals_handles_missing_analyst_fields` — keys absent → fields None; `data_unavailable=False` (canonical fields present).
    - `test_fetch_fundamentals_handles_partial_analyst_fields` — only `targetMeanPrice` present → that one populates, others None (per-field independence).
    - `test_fetch_fundamentals_handles_non_numeric_analyst_fields` — string "N/A" + inf + NaN + bool → all 4 coerce to None via `_safe_float` / `_safe_int`; `data_unavailable=False` (canonical fields present).
    - `test_safe_int_helper` — direct unit test of `_safe_int` enumerating None / True / False / 42 / -3 / 0 / 42.7 / 42.0 / "5" / "N/A" / NaN / inf / -inf.
  - **Default-period bump (2 tests, in `tests/ingestion/test_prices.py`):**
    - `test_fetch_prices_default_period_is_1y` — `fetch_prices("AAPL")` (no kwarg) calls `history(period="1y")`.
    - `test_fetch_prices_explicit_period_still_honored` — `fetch_prices("AAPL", period="6mo")` calls `history(period="6mo")` (override still works).
- **Targeted suite (29 tests in `tests/ingestion/test_fundamentals.py` + `tests/ingestion/test_prices.py`)** all green per orchestrator pre-condition: `python -m pytest tests/ingestion/test_fundamentals.py tests/ingestion/test_prices.py -q` → "29 passed in 2.61s".
- **Full repo suite:** `python -m pytest -q` → **188/188 green** (1222.58s wall — slow on this Windows host but no failures, no errors). Phase 1 + Phase 2 W1+W2+W3 + Plan 02-07 amendment all integrate cleanly. Up from 177/177 at the close of Plan 02-06 → +11 tests, all green.

## Task Commits

1. **Task 1 RED — failing tests for FundamentalsSnapshot analyst-consensus fields:** `a4672f1` — appended the 4 schema-shape tests + 5 ingestion-population tests + `test_safe_int_helper` to `tests/ingestion/test_fundamentals.py`. (RED state: 9 tests fail with AttributeError or "extra not allowed" on construction; `_safe_int` import resolves to ImportError until the helper lands.)
2. **Task 1 GREEN — add 4 analyst-consensus fields to FundamentalsSnapshot:** `7ba8b49` — `analysts/data/fundamentals.py`: 4 new Optional fields appended after `market_cap`; module docstring updated. (After this commit: the 4 schema-shape tests + `test_fundamentals_snapshot_extra_forbid_still_active` pass; the 5 ingestion-population tests still fail because `fetch_fundamentals` doesn't populate the new fields yet.)
3. **Task 2 GREEN — populate analyst-consensus fields in fetch_fundamentals:** `6b55cda` — `ingestion/fundamentals.py`: `_safe_int` helper added; 4 new `_safe_float`/`_safe_int` reads on `info.get("targetMeanPrice")` etc.; 4 new constructor kwargs on `FundamentalsSnapshot(...)`. After this commit, all 9 fundamentals tests + the existing 7 (test_fund_happy / test_fund_missing / test_fund_partial / test_fund_yfinance_raises / test_fund_normalizes_ticker / test_fund_invalid_ticker_returns_unavailable / test_fund_handles_non_numeric_values) are green.
4. **Task 3 RED — expect fetch_prices default period='1y':** `23fde2f` — appended 2 tests to `tests/ingestion/test_prices.py` (`test_fetch_prices_default_period_is_1y` + `test_fetch_prices_explicit_period_still_honored`). RED state: the default-period test fails because `fetch_prices`'s default is still `"3mo"` (assertion `mock_ticker.history.assert_called_once_with(period="1y")` fires).
5. **Task 3 GREEN — bump fetch_prices default period from 3mo to 1y:** `1715208` — `ingestion/prices.py`: signature changed `period: str = "3mo"` → `period: str = "1y"`; docstring updated to name the new default and link Phase 3 RESEARCH Pitfall #1 inline. After this commit, both new tests + every existing prices test (which all monkeypatch yfinance.Ticker without inspecting `period`) green.

**Plan metadata commit:** added in this Phase-2 closeout pass (covers SUMMARY.md, STATE.md, ROADMAP.md update).

## Files Created/Modified

### Created
*(none — all changes are additive edits to existing files)*

### Modified
- `analysts/data/fundamentals.py` (+21 lines — 4 new Optional fields after `market_cap` + module docstring update; final size 65 lines)
- `ingestion/fundamentals.py` (+51 lines, -1 line — `_safe_int` helper next to `_safe_float`, 4 new reads in `fetch_fundamentals`, 4 new constructor kwargs, module docstring update; final size 180 lines)
- `ingestion/prices.py` (+13 lines, -3 lines — default `period` flipped to `"1y"` + docstring rationale paragraph; final size 257 lines)
- `tests/ingestion/test_fundamentals.py` (+241 lines — 9 new tests appended after the existing 7; final size 401 lines)
- `tests/ingestion/test_prices.py` (+39 lines — 2 new tests appended after the existing 12; final size 302 lines)

## Decisions Made

- **Additive append, not insert** — the 4 new fields go AFTER `market_cap` on FundamentalsSnapshot rather than being interleaved. JSON serialization with `sort_keys=True` (mandated by `ingestion.refresh._write_snapshot`) sorts fields alphabetically regardless of class-body order, so insertion position is cosmetic. Appending keeps `git blame` clean for the existing fields and matches the convention from Plan 02-01 schema files.
- **`_safe_int` rejects strings outright (no string-numeric parsing)** — `_safe_float` behaves the same way. Locking parity here means a future schema-drift failure mode (yfinance starts returning `'42'` instead of `42` for a count field) surfaces as `None` rather than silently parsing — which keeps the data_unavailable / per-field-None signal trustworthy for downstream consumers. If yfinance ever does emit string counts, we want a quiet None plus a debug-log opportunity, not a silent string→int that hides the upstream change.
- **`_safe_int` floors floats toward zero via `int(v)`, not rounding** — yfinance occasionally returns `42.0` for `numberOfAnalystOpinions` (whole-number floats around stale-cache records); flooring those gets the right int answer. Genuine fractional floats (42.7) are rare for count fields, but if they occur the floor is harmless. At the model boundary Pydantic v2's `int_from_float` rejects 42.5 outright with `ValidationError`, so the helper's truncation is a defense-in-depth layer; the schema-level rejection catches the ambiguous fractional case before it becomes a snapshot field.
- **Analyst-consensus fields are NOT part of the canonical-marker `data_unavailable` check** — the check stays `pe is None AND market_cap is None`. Reason: small-cap and obscure tickers legitimately have zero analyst coverage on healthy days. Using analyst absence as a breakage signal would mis-flag every Russell-2000 ticker without Wall Street coverage. Phase 3's valuation analyst handles missing analyst data via tertiary-blend fallback to `thesis_price` / `target_multiples` (per `03-RESEARCH.md`), not via `data_unavailable` propagation. The `data_unavailable` predicate stays focused on whole-source breakage detection (Pitfall #1: yfinance returns `{}` on a silent-breakage day → both `pe` AND `marketCap` absent → snapshot is unrecoverable).
- **`fetch_prices` default period bumped to `'1y'`, not `'6mo'` or `'2y'`** — `'1y'` is the smallest period satisfying ALL Phase 3 technicals warm-up requirements simultaneously: MA200 needs 200 bars, 6m momentum needs 126, stable ADX needs ~150. ~252 trading bars in 1y leaves a small margin for weekends/holidays. Larger periods buy nothing for the analyst (MA200 doesn't get smarter past 200 bars) but cost ~3KB extra per snapshot per ticker. `'1y'` is the right floor.
- **Plan 02-06 orchestrator implicitly benefits** — `ingestion/refresh.py` calls `fetch_prices(ticker)` without a `period` kwarg, so the orchestrator now persists 1y of bars per snapshot instead of 3mo. No code change needed in `refresh.py`. Existing 02-06 tests pass `period` explicitly when they care (none do — they monkeypatch `fetch_prices` entirely), so they're unaffected. The default-arg bump is a transparent improvement.
- **`test_fundamentals_snapshot_opinion_count_float_coercion` documents Pydantic v2's actual behavior at the schema boundary** — 42.0 coerces cleanly to 42 (no fractional loss), 42.5 raises `ValidationError` (Pydantic's `int_from_float` prevents silent truncation by default). This pins the contract so a future Pydantic upgrade can't silently flip it to "always truncate" or "always reject ints from floats". The test was originally drafted as "either 42.5 → 42 OR Pydantic rejects" — settled on rejection per the actual run, locked in code.
- **Tests reuse the existing `yfinance.Ticker` monkeypatch pattern** — `mock_ticker.info = {...}` from the existing test_fund_happy / test_fund_missing tests. No new fixture files required. The 4 happy / partial / missing / non-numeric scenarios slot in alongside the existing 7 tests and feel like part of the same suite. This kept the test-file diff focused on new behavior coverage rather than fixture plumbing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Cosmetic] Task 1 RED commit (`a4672f1`) bundled the failing tests for BOTH Task 1 (schema) AND Task 2 (ingestion population) plus `test_safe_int_helper`**
- **Found during:** Task 1 RED writing — the test file structure naturally co-located all 9 new tests since they share the existing `mock_ticker = MagicMock(); mock_ticker.info = {...}` pattern from Plan 02-02. Splitting them across two RED commits would have meant duplicating the import block at the top of the file and re-stating identical fixture setup in both commits.
- **Issue:** The plan specified separate Task 1 RED and Task 2 RED commits. Actual sequence collapsed them: `a4672f1` includes failing tests for both tasks; `7ba8b49` (Task 1 GREEN — schema fields) made the 4 schema-shape tests + `extra_forbid` test green while the 5 ingestion-population tests stayed red until `6b55cda` (Task 2 GREEN — `_safe_int` + 4 reads) shipped.
- **Fix:** Documented the collapse in this SUMMARY (here) and in the commit messages. TDD discipline preserved: every implementation commit was preceded by failing tests on disk; the schema-impl commit `7ba8b49` did NOT make all tests green (the 5 ingestion tests still failed because `fetch_fundamentals` didn't populate the new fields and `_safe_int` didn't exist).
- **Verification:** Verified by re-running `pytest tests/ingestion/test_fundamentals.py -k "analyst_fields or safe_int"` at HEAD~3 (after `7ba8b49`) — 5 tests still fail (analyst_fields population + safe_int helper). The RED state was preserved in the working tree even though the commit boundary moved.
- **Committed in:** `a4672f1` (combined RED), `7ba8b49` (Task 1 GREEN — schema only), `6b55cda` (Task 2 GREEN — ingestion population).
- **Impact:** Cosmetic on commit boundaries; zero impact on the failing-test → passing-test sequence. Same shape as Plan 02-06's deviation #1 (combined RED) — both deviations are TDD-discipline preserved with cleaner commit ergonomics.

---

**Total deviations:** 1 cosmetic (combined Task 1 + Task 2 RED commit, with TDD discipline preserved).
**Impact:** Tightening only. Production code matches the plan's `must_haves` exactly: 4 new Optional schema fields, `_safe_int` helper alongside `_safe_float`, 4 new yfinance .info reads in `fetch_fundamentals`, default `period` flipped to `"1y"`, 11 new tests across schema + ingestion + prices-default behaviors.

## Issues Encountered

- **Full-repo `python -m pytest -q` runtime ~20 minutes (1222.58s)** — yfinance / yahooquery / requests imports + responses-lib mocking framework + 188 tests on Windows. Per-test runtime is sub-millisecond once imports warm; the wall-clock cost is dominated by initial import / fixture setup. Not a regression — Plan 02-06 reported similar wall-clock characteristics. No optimization needed at this stage; pytest-xdist could trim it later if it becomes an annoyance during Phase 3 development.
- **`uv` PATH carry-over** — same as every prior Phase 2 plan; `uv` not on PATH so plan-07 commits were authored with `python -m pytest` (poetry/uv-runner-agnostic). The orchestrator's pre-condition note explicitly noted `python -m pytest` works (poetry is NOT on PATH).
- **No yfinance / yahooquery / requests dependency changes** — pure additive change to existing modules. `pyproject.toml` untouched.
- **No `data/` snapshot files re-generated** — Plan 02-06 didn't seed any committed data/ fixtures, and Plan 02-07's schema is backward-compatible (all 4 new fields default to None on construction), so any existing serialized snapshots from a 02-06 run would round-trip cleanly through the new schema without re-generation. No data-migration step needed.

## Self-Check: PASSED

- [x] `analysts/data/fundamentals.py` exists with 4 new analyst-consensus fields — FOUND (65 lines; lines 53-56 contain `analyst_target_mean` / `analyst_target_median` / `analyst_recommendation_mean` / `analyst_opinion_count` declarations)
- [x] `ingestion/fundamentals.py` exists with `_safe_int` helper + 4 new `info.get()` reads — FOUND (180 lines; `_safe_int` at lines 74-96; 4 reads at lines 152-155; 4 constructor kwargs at lines 175-178)
- [x] `ingestion/prices.py` exists with default `period="1y"` — FOUND (257 lines; signature at line 213: `def fetch_prices(ticker: str, *, period: str = "1y") -> PriceSnapshot:`)
- [x] `tests/ingestion/test_fundamentals.py` exists with 9 new analyst-field / safe_int tests — FOUND (401 lines; 9 new tests at lines 182-401 under "Plan 02-07 amendment" header)
- [x] `tests/ingestion/test_prices.py` exists with 2 new default-period tests — FOUND (302 lines; 2 new tests at lines 270-301 under "Plan 02-07 amendment" header)
- [x] Commit `a4672f1` (Task 1 RED — failing tests for FundamentalsSnapshot analyst-consensus fields) — FOUND in `git log --oneline`
- [x] Commit `7ba8b49` (Task 1 GREEN — add 4 analyst-consensus fields to FundamentalsSnapshot) — FOUND in `git log --oneline`
- [x] Commit `6b55cda` (Task 2 GREEN — populate analyst-consensus fields in fetch_fundamentals) — FOUND in `git log --oneline`
- [x] Commit `23fde2f` (Task 3 RED — expect fetch_prices default period='1y') — FOUND in `git log --oneline`
- [x] Commit `1715208` (Task 3 GREEN — bump fetch_prices default period from 3mo to 1y) — FOUND in `git log --oneline`
- [x] `python -m pytest tests/ingestion/test_fundamentals.py tests/ingestion/test_prices.py -q` → 29 passed (per orchestrator pre-condition: "29 passed in 2.61s")
- [x] `python -m pytest -q` → **188/188 green** (1222.58s wall; Phase 1 + Phase 2 W1+W2+W3 + Plan 02-07 amendment all integrate cleanly; +11 tests vs Plan 02-06 close)
- [x] `must_haves.truths` from PLAN.md verified by reading the 5 modified files:
  - 4 new Optional fields on FundamentalsSnapshot — VERIFIED (analysts/data/fundamentals.py lines 53-56)
  - `fetch_fundamentals` populates 3 fields via `_safe_float` from targetMeanPrice/targetMedianPrice/recommendationMean — VERIFIED (ingestion/fundamentals.py lines 152-154)
  - `fetch_fundamentals` populates `analyst_opinion_count` via NEW `_safe_int` helper from numberOfAnalystOpinions — VERIFIED (ingestion/fundamentals.py line 155)
  - All 4 keys missing or non-numeric → 4 fields are None, `data_unavailable` logic unchanged — VERIFIED via `test_fetch_fundamentals_handles_missing_analyst_fields` + `test_fetch_fundamentals_handles_non_numeric_analyst_fields` (both green)
  - `fetch_prices` default `period` is `'1y'` — VERIFIED (ingestion/prices.py line 213)
  - Existing tests pinning `period='3mo'` explicitly still pass — VERIFIED (no existing tests pinned the default; the bump is invisible to them)
  - Existing Phase 2 refresh orchestrator tests still green — VERIFIED via the 188/188 full-repo run (includes tests/ingestion/test_refresh.py)
- [x] `must_haves.artifacts` from PLAN.md verified — all 4 artifact paths exist with line counts at or above the `min_lines` floors
- [x] `must_haves.key_links` from PLAN.md verified by Grep:
  - `analyst_target_mean=` / `analyst_recommendation_mean=` / `analyst_opinion_count=` constructor kwargs in `ingestion/fundamentals.py` — VERIFIED (lines 175-178)
  - `targetMeanPrice` / `targetMedianPrice` / `recommendationMean` / `numberOfAnalystOpinions` `info.get()` calls in `ingestion/fundamentals.py` — VERIFIED (lines 152-155)
- [x] No production source files modified beyond the 5 listed in PLAN.md — VERIFIED via `git show --stat a4672f1 7ba8b49 6b55cda 23fde2f 1715208`
- [x] `extra="forbid"` Pydantic discipline preserved post-amendment — VERIFIED via `test_fundamentals_snapshot_extra_forbid_still_active` (green)

## Next Phase Readiness

- **Phase 2 is COMPLETE — all 7 plans shipped.** 02-01 foundation, 02-02 prices/fundamentals, 02-03 EDGAR filings, 02-04 news, 02-05 social, 02-06 refresh orchestrator, 02-07 fundamentals analyst-consensus + prices history-depth bump (this plan). DATA-01..08 all marked `[x]` in REQUIREMENTS.md (DATA-01 / DATA-02 carried forward unchanged from Plan 02-02 — this amendment extended their behavior without changing their coverage status).
- **Phase 3 (Analytical Agents) is fully unblocked from this side.** The valuation analyst (ANLY-04, plan 03-05) can now read `snapshot.fundamentals.analyst_target_mean` directly without `getattr(..., None)` defensive code; the technicals analyst (ANLY-02, plan 03-02) gets ~252 trading bars by default (sufficient for MA200 / 6m momentum / stable ADX) without per-call `period=` overrides at every fetch site. Phase 3 plans depending on `02-07` declared via `depends_on: [02-07]` in their frontmatter — the cross-phase dependency graph captures the prerequisite explicitly.
- **Phase 5 (Claude Routine) unblocked.** The routine entrypoint can now call `run_refresh` and rely on snapshots having both the longer history (1y bars) AND the analyst-consensus metadata available at the per-ticker JSON level. No additional ingestion work needed for Phase 5 to consume the schema.
- **Phase 8 (Mid-Day Refresh) unblocked.** The Vercel Python serverless function can call `fetch_prices(ticker)` with no kwarg and get ~252 bars for chart rendering; calling `fetch_fundamentals(ticker)` returns the 4 new analyst-consensus fields if Yahoo populated them. Same surface as Phase 5 routine, same defaults.
- **No carry-overs / no blockers from this plan.** Phase 2 closes cleanly. Next: Phase 3 kickoff (`/gmd:execute-phase 3`).

---
*Phase: 02-ingestion-keyless-data-plane*
*Plan: 07-fundamentals-analyst-fields*
*Completed: 2026-05-02*
