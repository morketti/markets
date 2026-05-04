---
phase: 06-frontend-mvp-morning-scan-deep-dive
plan: 01
type: tdd
wave: 0
depends_on: []
files_modified:
  - analysts/_indicator_math.py
  - ingestion/news.py
  - synthesis/decision.py
  - prompts/synthesizer.md
  - routine/storage.py
  - routine/run_for_watchlist.py
  - tests/analysts/test_indicator_math.py
  - tests/ingestion/test_news.py
  - tests/synthesis/test_decision.py
  - tests/routine/test_storage.py
  - tests/routine/test_run_for_watchlist.py
  - .planning/ROADMAP.md
autonomous: true
requirements: [INFRA-05]
gap_closure: false
tags: [phase-6, wave-0, amendment, storage, schema-version-bump, tdd]

must_haves:
  truths:
    - "analysts/_indicator_math.py exposes 3 series helpers `_ma_series(prices: pd.Series, window: int) -> pd.Series`, `_bb_series(prices: pd.Series, window: int = 20, sigma: float = 2.0) -> tuple[pd.Series, pd.Series]`, `_rsi_series(prices: pd.Series, period: int = 14) -> pd.Series` that produce values byte-identical to the existing single-point computations at iloc[-1]"
    - "ingestion/news.py `fetch_news(ticker)` return type changes from `list[Headline]` to `list[Headline]` PRESERVED; new public function `fetch_news_with_raw(ticker)` returns `tuple[list[Headline], list[dict]]` where the dict list is the raw `{source, published_at, title, url}` records used by Phase 6 storage — OR — fetch_news adds an optional `return_raw: bool=False` parameter that when True returns the tuple shape (planner's call; pick one — the simpler option is the optional-flag overload)"
    - "synthesis/decision.py exposes `ThesisStatus = Literal['intact', 'weakening', 'broken', 'improving', 'n/a']` at module level"
    - "synthesis/decision.py `TimeframeBand` model gains `thesis_status: ThesisStatus = 'n/a'` field (default 'n/a' so existing snapshots and lite-mode TimeframeBands deserialize without ValidationError)"
    - "synthesis/decision.py `TickerDecision.schema_version` default bumps from 1 to 2"
    - "prompts/synthesizer.md gains an instruction block under `### short_term: TimeframeBand` AND `### long_term: TimeframeBand` headers that tells the synthesizer to populate `thesis_status` per timeframe with one of the 5 enum values"
    - "routine/storage.py `_build_ticker_payload` writes 4 NEW fields into the per-ticker JSON: `ohlc_history` (list of last 180 trading days as `{date, open, high, low, close, volume}` dicts; ISO-date strings; numeric values), `indicators` (dict with 5 series aligned to ohlc_history dates: `ma20`, `ma50`, `bb_upper`, `bb_lower`, `rsi14`; each series is list of float-or-null aligned by index), `headlines` (list of `{source, published_at, title, url}` dicts; published_at is ISO 8601), `schema_version` bumps from 1 to 2"
    - "routine/storage.py writes a NEW file `data/_dates.json` at repo root (NOT inside the date folder) containing `{schema_version: 1, dates_available: [sorted YYYY-MM-DD strings], updated_at: ISO 8601 UTC}` — written via the same _atomic_write_json helper; populated by enumerating `data/*/` subfolders that contain a `_status.json`"
    - "routine/run_for_watchlist.py threads ohlc_history (180 trading days from yfinance) and headlines (raw RSS list from ingestion.news) through TickerResult so storage.py can persist them — minimal interface change; existing TickerResult fields preserved"
    - "ROADMAP.md Phase 6 success criterion #5 text updated from `2h/12h` to `< 6h / 6-24h / > 24h` to match REQUIREMENTS.md VIEW-11 (planner identifies the exact line in the existing ROADMAP.md and replaces only that line; do NOT rewrite the entire phase entry)"
    - "All Phase 1-5 existing tests stay GREEN after Wave 0 amendment — schema_version bump 1→2 is the ONLY breaking schema change; ThesisStatus default 'n/a' makes the field addition non-breaking for every existing TickerDecision deserialization"
    - "tests/analysts/test_indicator_math.py extended with `test_ma_series_byte_identical_to_single_point`, `test_bb_series_byte_identical_to_single_point`, `test_rsi_series_byte_identical_to_single_point` — each computes the series, takes iloc[-1], and asserts approx-equality (within 1e-9) to the existing scalar computation on the same fixture"
    - "tests/ingestion/test_news.py extended with `test_fetch_news_returns_raw_when_flag_set` (or equivalent depending on signature decision) — asserts the raw list shape is `list[dict]` with the 4 required keys"
    - "tests/synthesis/test_decision.py extended with: `test_thesis_status_literal_accepts_5_values` (parametrized over the 5 enum values), `test_thesis_status_default_is_na`, `test_timeframe_band_thesis_status_field_exists`, `test_schema_version_default_bumped_to_2`"
    - "tests/routine/test_storage.py extended with: `test_per_ticker_payload_contains_ohlc_history`, `test_per_ticker_payload_contains_indicators_with_5_series`, `test_per_ticker_payload_contains_headlines`, `test_per_ticker_payload_schema_version_is_2`, `test_dates_index_written_at_repo_root`"
    - "tests/routine/test_run_for_watchlist.py extended with `test_ticker_result_threads_ohlc_history_and_headlines` — asserts the new fields propagate from ingestion to storage"
    - "Final pytest count: ~639 baseline + ~20 new tests = ~659 tests, all GREEN"
  artifacts:
    - path: "analysts/_indicator_math.py"
      provides: "3 new series helpers (_ma_series, _bb_series, _rsi_series) appended; ALL existing functions preserved verbatim"
      min_lines: 220
    - path: "ingestion/news.py"
      provides: "fetch_news signature extended to optionally return raw headline dicts; existing dedup + sort behavior preserved"
      min_lines: 270
    - path: "synthesis/decision.py"
      provides: "ThesisStatus Literal added at module level; TimeframeBand.thesis_status field added with default 'n/a'; TickerDecision.schema_version default bumped 1→2"
      min_lines: 220
    - path: "prompts/synthesizer.md"
      provides: "thesis_status instruction added per timeframe (short_term + long_term); rest of prompt preserved verbatim"
      min_lines: 220
    - path: "routine/storage.py"
      provides: "_build_ticker_payload extended with 4 new fields; new _write_dates_index function; schema_version bumped 1→2; _dates.json written at repo root"
      min_lines: 280
    - path: "routine/run_for_watchlist.py"
      provides: "TickerResult threads ohlc_history (180 days) + headlines (raw list) through the per-ticker pipeline"
      min_lines: 240
    - path: "tests/analysts/test_indicator_math.py"
      provides: "+3 tests for byte-identical series-form helpers"
      min_lines: 110
    - path: "tests/ingestion/test_news.py"
      provides: "+1 test for raw-headlines return shape"
      min_lines: 100
    - path: "tests/synthesis/test_decision.py"
      provides: "+4 tests for ThesisStatus + thesis_status field + schema_version bump"
      min_lines: 100
    - path: "tests/routine/test_storage.py"
      provides: "+5 tests for new payload fields + dates index"
      min_lines: 200
    - path: "tests/routine/test_run_for_watchlist.py"
      provides: "+1 test for ohlc_history + headlines threading"
      min_lines: 100
    - path: ".planning/ROADMAP.md"
      provides: "Phase 6 success criterion #5 text corrected from 2h/12h to 6h/24h"
      min_lines: 280
  key_links:
    - from: "analysts/_indicator_math.py"
      to: "routine/storage.py"
      via: "import _ma_series, _bb_series, _rsi_series"
      pattern: "_ma_series|_bb_series|_rsi_series"
    - from: "routine/storage.py"
      to: "data/{date}/{TICKER}.json"
      via: "_atomic_write_json(_build_ticker_payload(r))"
      pattern: "ohlc_history|indicators|headlines"
    - from: "routine/storage.py"
      to: "data/_dates.json"
      via: "_write_dates_index helper called at end of write_daily_snapshot"
      pattern: "_dates\\.json|dates_available"
    - from: "synthesis/decision.py"
      to: "frontend zod schemas (Wave 1)"
      via: "schema_version: 2 contract"
      pattern: "schema_version.*=.*2"
---

<objective>
Wave 0 Phase 5 amendment — extend daily snapshot per-ticker JSONs to carry the data the Phase 6 frontend needs for OHLC chart overlays, news feed grouping, thesis-status filtering, and historical date selection. Bumps schema_version 1→2 with a non-breaking field addition (ThesisStatus default 'n/a'). Adds `data/_dates.json` repo-root index so the frontend can enumerate available dates with one fetch instead of GitHub directory listing.

Purpose: The frontend (Waves 1-4) reads what the backend writes. Today's snapshots don't carry ohlc_history, computed indicator series, raw headlines, or thesis_status — Wave 0 adds them so Waves 2-3 can render charts + news feed + Long-Term Thesis Status lens without inventing data. Also fixes a documentation bug in ROADMAP.md (Phase 6 success criterion #5 staleness thresholds).

Output: Modified Python modules + ~20 new tests + corrected ROADMAP.md. After Wave 0 the next routine run produces a v2 snapshot folder that the Wave 1 zod schemas validate against.
</objective>

<execution_context>
@C:/Users/Mohan/.claude/workflows/execute-plan.md
@C:/Users/Mohan/.claude/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-CONTEXT.md
@.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-RESEARCH.md
@.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-VALIDATION.md
@.planning/phases/05-claude-routine-wiring/05-06-SUMMARY.md

# Existing Python files this plan amends
@analysts/_indicator_math.py
@ingestion/news.py
@synthesis/decision.py
@prompts/synthesizer.md
@routine/storage.py
@routine/run_for_watchlist.py

<interfaces>
<!-- Key types and contracts the executor needs. Extracted from codebase. -->
<!-- Executor uses these directly — no exploration needed. -->

From synthesis/decision.py (current shape):
```python
DecisionRecommendation = Literal["add", "trim", "hold", "take_profits", "buy", "avoid"]
ConvictionBand = Literal["low", "medium", "high"]
Timeframe = Literal["short_term", "long_term"]

class TimeframeBand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(min_length=1, max_length=500)
    drivers: list[str] = Field(default_factory=list, max_length=10)
    confidence: int = Field(ge=0, le=100)
    # WAVE 0 ADDS: thesis_status: ThesisStatus = "n/a"

class TickerDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticker: str
    computed_at: datetime
    schema_version: int = 1   # WAVE 0 BUMPS TO 2
    recommendation: DecisionRecommendation
    conviction: ConvictionBand
    short_term: TimeframeBand
    long_term: TimeframeBand
    open_observation: str = Field(default="", max_length=500)
    dissent: DissentSection
    data_unavailable: bool = False
```

From routine/storage.py (current per-ticker payload):
```python
def _build_ticker_payload(r: "TickerResult") -> dict:
    return {
        "ticker": r.ticker,
        "schema_version": 1,                    # WAVE 0 BUMPS TO 2
        "analytical_signals": [...],
        "position_signal": {...},
        "persona_signals": [...],
        "ticker_decision": {...},
        "errors": list(r.errors),
        # WAVE 0 ADDS: "ohlc_history", "indicators", "headlines"
    }
```

From analysts/_indicator_math.py (existing helpers — Wave 0 ADDS series-form siblings, NOT replaces):
```python
ADX_PERIOD: int = 14
def _build_df(history: list[OHLCBar]) -> pd.DataFrame: ...
def _adx_14(df: pd.DataFrame) -> Optional[float]: ...
def _total_to_verdict(normalized: float) -> Verdict: ...

# WAVE 0 ADDS:
def _ma_series(prices: pd.Series, window: int) -> pd.Series: ...
def _bb_series(prices: pd.Series, window: int = 20, sigma: float = 2.0) -> tuple[pd.Series, pd.Series]: ...
def _rsi_series(prices: pd.Series, period: int = 14) -> pd.Series: ...
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Failing tests for series helpers + ThesisStatus + storage payload</name>
  <files>tests/analysts/test_indicator_math.py, tests/synthesis/test_decision.py, tests/routine/test_storage.py, tests/routine/test_run_for_watchlist.py, tests/ingestion/test_news.py</files>
  <behavior>
    All tests below FAIL initially (RED phase — that's the point):

    tests/analysts/test_indicator_math.py:
    - test_ma_series_byte_identical_to_single_point — fixture of 60-bar OHLCBar history; compute _ma_series(close_prices, 20).iloc[-1] vs the existing single-point MA20 computation in technicals.py; assert math.isclose with rel_tol=1e-9
    - test_bb_series_byte_identical_to_single_point — same pattern; assert (upper.iloc[-1], lower.iloc[-1]) match the existing single-point BB computation in position_adjustment.py
    - test_rsi_series_byte_identical_to_single_point — same pattern; assert _rsi_series(close, 14).iloc[-1] matches existing single-point RSI computation
    - All three tests use existing fixtures from tests/analysts/conftest.py (oversold_history / overbought_history / etc.)

    tests/synthesis/test_decision.py:
    - test_thesis_status_literal_accepts_5_values — parametrized over ['intact', 'weakening', 'broken', 'improving', 'n/a']; constructs TimeframeBand(summary='x', confidence=50, thesis_status=value); assert no ValidationError
    - test_thesis_status_rejects_invalid — TimeframeBand(thesis_status='garbage') raises ValidationError with 'thesis_status' in loc
    - test_thesis_status_default_is_na — TimeframeBand(summary='x', confidence=50).thesis_status == 'n/a'
    - test_schema_version_default_bumped_to_2 — TickerDecision(...minimal fields...).schema_version == 2

    tests/routine/test_storage.py:
    - test_per_ticker_payload_contains_ohlc_history — write a fixture TickerResult that includes 180 days of ohlc; assert payload['ohlc_history'] is a list of 180 dicts each with keys {'date','open','high','low','close','volume'}; date is ISO format string; values are float/int
    - test_per_ticker_payload_contains_indicators_with_5_series — assert payload['indicators'] is a dict with keys {'ma20','ma50','bb_upper','bb_lower','rsi14'}; each is a list of (float | None) aligned to len(ohlc_history); first 19 entries of ma20 are None (warmup); first 19 of bb_* are None; first 14 of rsi14 are None
    - test_per_ticker_payload_contains_headlines — assert payload['headlines'] is a list of dicts with keys {'source','published_at','title','url'}; sorted by published_at desc
    - test_per_ticker_payload_schema_version_is_2 — assert payload['schema_version'] == 2
    - test_dates_index_written_at_repo_root — call write_daily_snapshot under a tmp_path; create another date folder beforehand with a _status.json; assert tmp_path/'_dates.json' exists, parses to {'schema_version': 1, 'dates_available': [sorted YYYY-MM-DD strings], 'updated_at': ISO}

    tests/routine/test_run_for_watchlist.py:
    - test_ticker_result_threads_ohlc_history_and_headlines — fixture-replay style; assert TickerResult exposes ohlc_history (list[OHLCBar] or list[dict] — pick the simpler shape — recommend list[OHLCBar] for Pydantic discipline) AND headlines (list[dict]); assert both fields propagate to _build_ticker_payload output

    tests/ingestion/test_news.py:
    - test_fetch_news_with_raw_returns_tuple — call fetch_news(ticker, return_raw=True); assert isinstance(result, tuple); result[0] is list[Headline]; result[1] is list[dict] with 4 keys per dict
    - test_fetch_news_default_signature_unchanged — fetch_news(ticker) (no flag) returns list[Headline] (preserves existing call sites without modification)
  </behavior>
  <action>
    1. Create or extend the 5 test files above with the listed test functions.
    2. Use existing conftest fixtures wherever possible (tests/analysts/conftest.py has synthetic_oversold_history, etc.; tests/routine/conftest.py has TickerResult fixtures).
    3. For tests/routine/test_storage.py::test_dates_index_written_at_repo_root, use pytest's tmp_path fixture; create `tmp_path/data/2026-04-01/_status.json` and `tmp_path/data/2026-04-30/_status.json` BEFORE calling write_daily_snapshot for date 2026-05-01; assert tmp_path/data/_dates.json exists with all 3 dates sorted ascending.
    4. Run: `uv run pytest tests/analysts/test_indicator_math.py tests/synthesis/test_decision.py tests/routine/test_storage.py tests/routine/test_run_for_watchlist.py tests/ingestion/test_news.py -q` — confirm ALL new tests FAIL (this is the RED phase; if any pass spuriously something is wrong with the test).
    5. Commit with: `test(06-01): add failing tests for series helpers + ThesisStatus + storage payload`
  </action>
  <verify>
    <automated>uv run pytest tests/analysts/test_indicator_math.py tests/synthesis/test_decision.py tests/routine/test_storage.py tests/routine/test_run_for_watchlist.py tests/ingestion/test_news.py -q 2>&1 | tail -20</automated>
  </verify>
  <done>~20 new tests added across 5 files, all failing as expected (RED phase). Existing 639 baseline tests still pass. Commit landed with `test(06-01):` prefix.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement series helpers + ThesisStatus + storage payload extensions (GREEN)</name>
  <files>analysts/_indicator_math.py, synthesis/decision.py, prompts/synthesizer.md, ingestion/news.py, routine/storage.py, routine/run_for_watchlist.py</files>
  <behavior>
    GREEN phase: write minimum code to pass all RED tests from Task 1.

    Behavioral contracts (from RED tests):
    - _ma_series(prices, window) returns prices.rolling(window).mean()
    - _bb_series(prices, window=20, sigma=2.0) returns (mid + sigma*std, mid - sigma*std) where mid = rolling mean, std = rolling std
    - _rsi_series(prices, period=14) returns Wilder-smoothed RSI series; first `period` entries are NaN (then converted to None at JSON serialization)
    - TimeframeBand.thesis_status: ThesisStatus = "n/a" — Pydantic field with default
    - TickerDecision.schema_version: int = 2 — default bump
    - prompts/synthesizer.md: insert instruction "**`thesis_status`**: one of `intact | weakening | broken | improving | n/a`. Pick `intact` when..." under both ### short_term and ### long_term sections
    - ingestion/news.fetch_news gains optional return_raw: bool = False parameter; when True, returns (list[Headline], list[dict]); when False, preserves existing list[Headline] return
    - routine/storage._build_ticker_payload bumps schema_version to 2 and adds 3 new fields (ohlc_history, indicators, headlines) computed from r.ohlc_history + analysts/_indicator_math series helpers + r.headlines
    - routine/storage gains _write_dates_index helper that scans snapshots_root for subfolders containing _status.json and writes sorted dates to snapshots_root/_dates.json
    - routine/run_for_watchlist.TickerResult Pydantic model gains: ohlc_history: list[OHLCBar] = Field(default_factory=list) AND headlines: list[dict] = Field(default_factory=list)
    - routine/run_for_watchlist threads ohlc_history (from yfinance fetch already happening) + headlines (from new fetch_news_with_raw call) through the pipeline
  </behavior>
  <action>
    1. **analysts/_indicator_math.py** — append 3 functions at end of file. Use pandas .rolling for MA/BB; use Wilder smoothing (.ewm(alpha=1/N, adjust=False).mean()) for RSI to match existing _adx_14 pattern. Export the names in any module-level __all__ if present (file currently has no __all__; add one if you want — optional). DO NOT modify existing functions.
    2. **synthesis/decision.py** — add `ThesisStatus = Literal["intact", "weakening", "broken", "improving", "n/a"]` after the existing Literal definitions; add `thesis_status: ThesisStatus = "n/a"` field to TimeframeBand AFTER the confidence field (preserve order); change `schema_version: int = 1` to `schema_version: int = 2`. Update the docstring to reflect schema_version 2.
    3. **prompts/synthesizer.md** — find the `### short_term: TimeframeBand` section header; insert a new bullet under the existing `confidence` bullet:
       ```
       - **`thesis_status`** (one of `intact | weakening | broken | improving | n/a`): characterizes whether the long-term thesis is holding. For short_term: usually `n/a` unless tactical price action genuinely threatens or confirms the thesis (rare). Default `n/a` when uncertain.
       ```
       Repeat for the `### long_term: TimeframeBand` section, but the guidance differs: "For long_term: REQUIRED to choose one of `intact | weakening | broken | improving`; use `n/a` only when data_unavailable=True." Update the Output Schema section accordingly.
    4. **ingestion/news.py** — add `return_raw: bool = False` parameter to `fetch_news`; when True, also collect raw `{source, published_at, title, url}` dicts during aggregation (the headline objects already carry these; just `.model_dump(mode='json')` each); return tuple. When False, preserve existing return shape exactly.
    5. **routine/storage.py** — extend _build_ticker_payload:
       - Bump `"schema_version": 1` → `"schema_version": 2`
       - Add `"ohlc_history": [b.model_dump(mode='json') for b in r.ohlc_history]` (where r.ohlc_history is list[OHLCBar])
       - Add `"indicators": _compute_indicator_series(r.ohlc_history)` where the new private helper computes ma20, ma50, bb_upper, bb_lower, rsi14 series via the new analysts/_indicator_math helpers; converts NaN → None for JSON-safe serialization; aligned to ohlc_history dates 1:1
       - Add `"headlines": list(r.headlines)` (already list of dicts from fetch_news_with_raw)
       - Add new module-private function `_write_dates_index(snapshots_root: Path)` that: enumerates subfolders matching YYYY-MM-DD pattern that contain `_status.json`; writes `{schema_version: 1, dates_available: sorted_dates, updated_at: datetime.now(UTC).isoformat()}` to `snapshots_root/_dates.json` via _atomic_write_json
       - Call `_write_dates_index(snapshots_root)` at the end of `write_daily_snapshot` AFTER Phase C completes successfully
    6. **routine/run_for_watchlist.py** — extend TickerResult Pydantic model with the 2 new fields (default_factory=list); thread ohlc_history through from existing yfinance fetch (the data is already fetched for analytical signals — just retain it instead of dropping); thread headlines through by switching the call site from `fetch_news(ticker)` to `fetch_news(ticker, return_raw=True)` and capturing the raw list.
    7. Run: `uv run pytest tests/analysts/test_indicator_math.py tests/synthesis/test_decision.py tests/routine/test_storage.py tests/routine/test_run_for_watchlist.py tests/ingestion/test_news.py -q` — confirm ALL ~20 new tests now pass.
    8. Run: `uv run pytest -q` — confirm full suite ~659 tests all pass (no Phase 1-5 regression).
    9. Commit with: `feat(06-01): add ohlc_history + indicators + headlines + thesis_status + dates index to daily snapshots`
  </action>
  <verify>
    <automated>uv run pytest -q 2>&1 | tail -5</automated>
  </verify>
  <done>All ~20 new tests pass; Phase 1-5 baseline tests still pass; full suite ~659 tests GREEN; coverage on routine/storage.py + analysts/_indicator_math.py + synthesis/decision.py stays ≥90% line / ≥85% branch. Commit landed with `feat(06-01):` prefix.</done>
</task>

<task type="auto">
  <name>Task 3: Fix ROADMAP staleness threshold doc bug + Wave 0 close-out</name>
  <files>.planning/ROADMAP.md</files>
  <action>
    1. Open `.planning/ROADMAP.md`. Find Phase 6 entry (the row in Phase Summary table AND the detailed Phase 6 section). The detailed Phase 6 success criterion #5 currently reads (or words to that effect): "Staleness badge in header transitions GREEN/AMBER/RED based on snapshot age and `_status.json` partial-success state". This text is fine — verify it doesn't actually contain `2h/12h`. If it does, replace with `< 6h / 6-24h / > 24h` to match REQUIREMENTS.md VIEW-11.
    2. The CONTEXT.md notes ROADMAP.md "says 2h/12h — that's a documentation bug". Verify by greping ROADMAP.md for `2h` or `12h`. If absent, the doc bug is in some OTHER doc — search docs for `2h` near "staleness" or "GREEN" and patch that one too. If grep finds nothing, this task is a no-op AT THE DOC LEVEL — record this finding in the SUMMARY.
    3. Run: `grep -nE "2h|12h" .planning/ROADMAP.md .planning/PROJECT.md .planning/REQUIREMENTS.md` — should return zero hits referencing staleness thresholds; only currency-or-other context hits acceptable.
    4. Commit with: `docs(06-01): fix staleness threshold doc to match VIEW-11 (6h/24h, not 2h/12h)` (skip commit if step 2 found no doc bug to fix; record no-op in SUMMARY).
  </action>
  <verify>
    <automated>grep -nE "(2h|12h).*stale|stale.*(2h|12h)" .planning/ROADMAP.md .planning/PROJECT.md .planning/REQUIREMENTS.md 2>&1 ; echo "EXIT_CODE=$?"</automated>
  </verify>
  <done>ROADMAP.md (and any other doc that referenced 2h/12h) updated to 6h/24h to match VIEW-11. If the bug never existed in the doc, the SUMMARY records that finding. No tests run on this task — it's docs only.</done>
</task>

</tasks>

<verification>
- All 3 tasks complete; commits landed
- `uv run pytest -q` reports ~659 tests passing (no regression from 639 baseline)
- `data/_dates.json` writer covered by tests
- Schema version bump 1→2 covered by tests
- ThesisStatus Literal + TimeframeBand.thesis_status covered by tests
- Series-form helpers byte-identical to scalar versions on shared fixture
- ROADMAP staleness threshold matches REQUIREMENTS VIEW-11 (or no-op recorded)
</verification>

<success_criteria>
- [ ] analysts/_indicator_math.py exposes _ma_series, _bb_series, _rsi_series with byte-identical math to scalar siblings
- [ ] synthesis/decision.py: ThesisStatus Literal + TimeframeBand.thesis_status (default 'n/a') + TickerDecision.schema_version default = 2
- [ ] prompts/synthesizer.md: thesis_status instructions added per timeframe
- [ ] routine/storage.py: per-ticker JSON gains ohlc_history + indicators (5 series) + headlines; data/_dates.json written at repo root
- [ ] routine/run_for_watchlist.py: TickerResult threads ohlc_history + headlines through pipeline
- [ ] ingestion/news.py: fetch_news(return_raw=True) returns tuple; default signature preserved
- [ ] ROADMAP.md staleness threshold matches VIEW-11 (6h/24h)
- [ ] All ~659 tests pass; no Phase 1-5 regression; coverage gates ≥90% line / ≥85% branch on touched modules
- [ ] 3 commits landed with proper conventional-commit prefixes (test → feat → docs)
</success_criteria>

<output>
After completion, create `.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-01-SUMMARY.md` matching the Phase 1-5 SUMMARY template — sections: Plan Identity / Wave / Outcome / Files Touched / Tests Added / Coverage / Schema Bump / Doc Fix / Notes for Wave 1.
</output>
