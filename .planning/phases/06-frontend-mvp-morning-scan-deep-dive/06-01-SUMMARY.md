---
phase: 06-frontend-mvp-morning-scan-deep-dive
plan: 01
subsystem: storage
tags: [phase-6, wave-0, amendment, storage, schema-version-bump, tdd, indicators, ohlc, headlines, thesis-status, dates-index]

# Dependency graph
requires:
  - phase: 05-claude-routine-wiring
    provides: routine.storage three-phase atomic write (Pattern #4) + per-ticker JSON shape; routine.run_for_watchlist TickerResult orchestrator; ingestion.news fetch_news; analysts._indicator_math scalar helpers; synthesis.decision TickerDecision schema
provides:
  - per-ticker JSON shape extended with 4 new fields (ohlc_history, indicators, headlines, schema_version=2)
  - data/_dates.json repo-root index for frontend date selector
  - analysts/_indicator_math series-form helpers (_ma_series, _bb_series, _rsi_series) byte-identical at iloc[-1] to scalar verdict math
  - synthesis/decision.ThesisStatus Literal + TimeframeBand.thesis_status field (default 'n/a')
  - prompts/synthesizer.md thesis_status instructions per timeframe
  - ingestion/news.fetch_news(return_raw=True) optional tuple-return shape
  - routine/run_for_watchlist.TickerResult.ohlc_history + .headlines fields threaded through pipeline
affects: [06-02-frontend-scaffold, 06-03-morning-scan, 06-04-deep-dive, 06-05-polish-responsive]

# Tech tracking
tech-stack:
  added: []  # No new dependencies — pure Python amendment using existing pandas + Pydantic
  patterns:
    - "Series-form indicator helpers byte-identical to scalar siblings at iloc[-1] (frontend overlays never disagree with verdict math)"
    - "Phase D _dates.json index regeneration AFTER Phase C _status.json sentinel (Pattern #4 extended)"
    - "Snapshot-as-source-of-truth threading (no double-fetch of news/OHLC) — keyless data plane discipline preserved"
    - "Non-breaking schema bump via default-value-on-new-field ('n/a' default for ThesisStatus)"
    - "Optional flag overloads for additive return-shape changes (fetch_news return_raw=True)"

key-files:
  created: []
  modified:
    - "analysts/_indicator_math.py — appended _ma_series + _bb_series + _rsi_series (scalar helpers preserved verbatim)"
    - "synthesis/decision.py — ThesisStatus Literal + TimeframeBand.thesis_status default 'n/a' + TickerDecision.schema_version default bumped 1→2"
    - "prompts/synthesizer.md — thesis_status instructions added per timeframe; output schema schema_version reference 1→2"
    - "ingestion/news.py — fetch_news gains optional return_raw flag; default signature preserved"
    - "routine/run_for_watchlist.py — TickerResult gains ohlc_history (list[OHLCBar]) + headlines (list[dict]) fields; threaded through _run_one_ticker from Snapshot"
    - "routine/storage.py — _build_ticker_payload gains 3 new fields + schema_version=2; new _compute_indicator_series + _write_dates_index helpers; Phase D added after Phase C"
    - "tests/analysts/test_indicator_math.py — 3 byte-identical series tests + 1 RED-phase RSI warmup spec correction (rule 1)"
    - "tests/ingestion/test_news.py — 2 raw-headlines tuple-return tests"
    - "tests/synthesis/test_decision.py — 5 ThesisStatus tests + 3 schema_version assertion bumps 1→2"
    - "tests/routine/test_storage.py — 5 new payload + dates-index tests + 1 three_phase_write_order extension for Phase D"
    - "tests/routine/test_run_for_watchlist.py — 1 TickerResult threading test"

key-decisions:
  - "Schema version bump 1→2 is the ONLY breaking change; all 4 new fields have safe defaults so the bump is non-breaking for unmodified callers"
  - "ThesisStatus default 'n/a' makes the field addition non-breaking for every existing TickerDecision deserialization (v1 snapshots have no thesis_status; reading them with v2 schema doesn't ValidationError)"
  - "Series helpers compute math identically to scalar siblings via shared pandas primitives (.rolling, .ewm) — locked by 3 byte-identical-at-iloc[-1] tests"
  - "ohlc_history + headlines threaded via the existing Snapshot the analytical signals already consume (no double-fetch); deviates from plan's explicit 'switch fetch_news call to return_raw=True' but preserves keyless data plane discipline (PROJECT.md)"
  - "Phase D _dates.json regeneration runs AFTER Phase C _status.json sentinel so today's date is included in the enumeration"
  - "Task 3 ROADMAP doc-bug fix is a NO-OP — plan-checker confirmed no 2h/12h text actually exists in ROADMAP.md / PROJECT.md / REQUIREMENTS.md (the doc bug was inferred from user-visible language only). Recorded here per the plan's instruction."

patterns-established:
  - "Series-form indicator helpers in analysts/_indicator_math.py mirror scalar siblings; when a new indicator joins the verdict path, add a series-form sibling so the frontend chart overlay can use the same math"
  - "Per-ticker JSON shape is the contract; schema_version bumps when ANY field shape changes; defaults on new fields make the bump non-breaking for downstream consumers"
  - "Repo-root index files (e.g. _dates.json) regenerate from disk state after the per-date sentinel lands so they always reflect committed snapshots, not in-progress writes"

requirements-completed: []  # INFRA-05 is multi-part (Vercel deploy + read-from-raw.githubusercontent.com); Wave 0 satisfies the storage-amendment prerequisite but the requirement itself flips Complete only after Wave 4 deploys to Vercel and the frontend reads real GitHub raw URLs. INFRA-05 stays Pending in REQUIREMENTS.md.

# Metrics
duration: 11min
completed: 2026-05-04
---

# Phase 6 Plan 01: Storage Amendment Summary

**Per-ticker JSON gains ohlc_history (180 days) + 5 indicator series (MA20/MA50/BB upper-lower/RSI14) + raw headlines + thesis_status with schema_version bumped 1→2; repo-root data/_dates.json index lets the frontend enumerate snapshot dates with one fetch.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-05-04T13:45:31Z
- **Completed:** 2026-05-04T13:55:55Z
- **Tasks:** 3 (Task 3 was a no-op-and-record per plan; 0 commits)
- **Files modified:** 12 (6 source, 5 test, 1 prompt)

## Accomplishments

- 3 series-form indicator helpers in `analysts/_indicator_math.py` (`_ma_series`, `_bb_series`, `_rsi_series`) producing values byte-identical to existing scalar verdict math at `iloc[-1]` — locked by 3 dedicated tests
- `TimeframeBand.thesis_status: ThesisStatus` field added (5-value Literal, default `'n/a'`) — drives Phase 6 Wave 3 Long-Term Thesis Status lens (VIEW-04); default makes the field addition non-breaking for v1 snapshots
- `TickerDecision.schema_version` default bumped 1→2; per-ticker JSON shape gains `ohlc_history` + `indicators` (5 series aligned 1:1 to dates) + `headlines` (raw dicts)
- New `routine.storage._write_dates_index` helper writes `data/_dates.json` at repo root by enumerating `_status.json`-bearing date subfolders — sorted ascending, regenerated each run
- `ingestion.news.fetch_news` gains optional `return_raw=True` flag returning `tuple[list[Headline], list[dict]]` — default signature preserved exactly so existing callers (`ingestion/refresh.py:98`) stay compatible
- `routine.run_for_watchlist.TickerResult` gains `ohlc_history` + `headlines` fields threaded from the already-loaded `Snapshot` (no double-fetch — keyless data plane discipline)
- `prompts/synthesizer.md` gains `thesis_status` instruction per timeframe (`short_term` defaults to `n/a`, `long_term` REQUIRED to choose intact/weakening/broken/improving) and Output Schema reflects `schema_version: 2`
- 20 new tests added; full repo: **659 tests passing** (639 baseline + 20 net new); coverage: `synthesis/decision.py` 100%, `analysts/_indicator_math.py` 97%, `routine/storage.py` 93%, `routine/run_for_watchlist.py` 89%, `ingestion/news.py` 80%

## Task Commits

1. **Task 1: Failing tests for series helpers + ThesisStatus + storage payload (RED)** — `8ea6252` (test)
2. **Task 2: Implement series helpers + ThesisStatus + storage payload extensions (GREEN)** — `1646356` (feat)
3. **Task 3: Fix ROADMAP staleness threshold doc bug** — NO-OP (no commit) — see Deviations below

## Files Created/Modified

- `analysts/_indicator_math.py` — appended 3 series helpers (`_ma_series`, `_bb_series`, `_rsi_series`); existing scalar helpers preserved verbatim
- `synthesis/decision.py` — `ThesisStatus` Literal + `TimeframeBand.thesis_status` field + `TickerDecision.schema_version` default bumped 1→2
- `prompts/synthesizer.md` — `thesis_status` instructions per timeframe; Output Schema schema_version reference 1→2
- `ingestion/news.py` — `fetch_news` gains optional `return_raw` flag returning tuple
- `routine/run_for_watchlist.py` — `TickerResult` gains `ohlc_history` + `headlines` fields threaded via `Snapshot`
- `routine/storage.py` — `_build_ticker_payload` extended (4 new fields, schema_version=2); new `_compute_indicator_series` + `_write_dates_index` helpers; Phase D added after Phase C
- `tests/analysts/test_indicator_math.py` — 3 byte-identical series tests
- `tests/ingestion/test_news.py` — 2 raw-headlines return-shape tests
- `tests/synthesis/test_decision.py` — 5 ThesisStatus tests; 3 existing schema_version assertions flipped 1→2
- `tests/routine/test_storage.py` — 5 new payload + dates-index tests; 1 phase-write-order extension for Phase D
- `tests/routine/test_run_for_watchlist.py` — 1 TickerResult threading test

## Decisions Made

- **Schema version bump strategy:** Only `TickerDecision.schema_version` and the per-ticker JSON `schema_version` flip 1→2. The `_dates.json` and `_index.json` schemas remain at `schema_version: 1` since they don't gain new fields. Frontend zod schemas (Wave 1) will assert per-ticker `schema_version: z.literal(2)`; v1 snapshots become invalid by design (forces a Phase 5 re-run before frontend renders).
- **Snapshot-as-source-of-truth:** `routine.run_for_watchlist._run_one_ticker` threads `ohlc_history` + `headlines` from the already-loaded `Snapshot` (which `position_adjustment.score` and `news_sentiment.score` already consume), instead of calling `ingestion.news.fetch_news(return_raw=True)` separately as the plan suggested. Preserves the keyless data plane discipline (PROJECT.md) — no double-fetch — and keeps `run_for_watchlist` purely an orchestrator with zero direct I/O. The `fetch_news(return_raw=True)` API is still implemented as required by the plan/tests; it's available for any future caller (e.g. Phase 8's mid-day refresh) that doesn't have a pre-loaded `Snapshot`.
- **Phase D positioning:** `_write_dates_index` runs AFTER `_status.json` (Phase C sentinel), not before. Reason: enumerating `_status.json`-bearing folders at this point includes today's date in the result. If `_dates.json` ran before `_status.json`, today's folder wouldn't yet have its sentinel and would be excluded.
- **NaN/inf coercion in indicators series:** `_series_to_jsonable` converts both NaN (warmup window) and inf (RSI saturation edge) to `None` for JSON-safety. The frontend zod schema can declare `(number | null)` and stay strict.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Original RED-phase test mis-asserted RSI warmup count**
- **Found during:** Task 2 (GREEN — first test run after implementation)
- **Issue:** The Task 1 (RED) test `test_rsi_series_byte_identical_to_single_point` and the storage test `test_per_ticker_payload_contains_indicators_with_5_series` both asserted that the first 14 entries of the RSI series are NaN/None. This is mathematically incorrect for `pandas.Series.ewm(adjust=False, alpha=1/14).mean()` — pandas EWM is well-defined from the first delta onward, so only position 0 (where `.diff()` produces NaN) is NaN. The scalar `_rsi_14` in `position_adjustment.py` separately refuses to RETURN a value below `RSI_MIN_BARS=27` (the analyst-level warmup discipline), but the underlying EWM math is computed throughout. The frontend chart can choose to hide the first ~27 entries to match analyst warmup; storage emits them as real values.
- **Fix:** Updated both tests to assert `series[0] is None` and `series[1] is not None` (the actual EWM-on-diff behavior). Added a clarifying comment in the storage test explaining the difference between series-level math vs analyst-level warmup discipline.
- **Files modified:** `tests/analysts/test_indicator_math.py`, `tests/routine/test_storage.py`
- **Verification:** `_rsi_series.iloc[-1]` byte-identical to `_rsi_14`'s scalar return (within 1e-9) confirmed by the GREEN test pass; the warmup-window assertion is now correct for the actual pandas semantics.
- **Committed in:** `1646356` (Task 2 GREEN commit)

**2. [Rule 1 — Bug] `test_three_phase_write_order` did not account for new Phase D _dates.json write**
- **Found during:** Task 2 (GREEN — full focused test suite first pass)
- **Issue:** The existing test asserted `call_order[-2:] == ["_index.json", "_status.json"]` (Pattern #4: `_status.json` is the LAST write). After adding Phase D `_write_dates_index` invocation, `_dates.json` is now the actual last write — Pattern #4's `_status.json` sentinel is still the LAST WRITE INSIDE the date folder, but `_dates.json` (at repo root, not inside the folder) follows it.
- **Fix:** Updated the assertion to `call_order[-3:] == ["_index.json", "_status.json", "_dates.json"]` and clarified the docstring that Phase D extends Pattern #4 with a 4th write (the repo-root index) AFTER the per-folder sentinel. The Phase 6 frontend reads `_status.json` first to verify a folder is finalized; `_dates.json` provides the cross-folder enumeration.
- **Files modified:** `tests/routine/test_storage.py`
- **Verification:** Test passes after the assertion update; Pattern #4 sentinel discipline preserved (`_status.json` is still LAST inside the date folder; `_dates.json` is at the parent level).
- **Committed in:** `1646356` (Task 2 GREEN commit)

**3. [Rule 1 — Blocking] `uv` command not available on Windows; substituted `.venv/Scripts/pytest.exe`**
- **Found during:** Task 1 (initial baseline test count)
- **Issue:** Plan + VALIDATION.md specify `uv run pytest -q` for verification commands, but `uv` is not installed on this machine. Project has a `.venv` directly (created by some other Python setup); `pytest.exe` is available at `C:/Users/Mohan/markets/.venv/Scripts/pytest.exe`.
- **Fix:** Substituted `.venv/Scripts/pytest.exe` for all test invocations during execution. Behavior is identical — same Python interpreter, same dependencies, same pytest config. Out-of-scope for this plan to install `uv` (would require user action and is not a Phase 6 concern).
- **Files modified:** None (test invocation only).
- **Verification:** All 659 tests pass via `.venv/Scripts/pytest.exe`. Same numerical result the plan expected from `uv run pytest`.
- **Committed in:** N/A (toolchain-only deviation; not committed).

### Plan-Specified No-Op (Task 3)

**Task 3: ROADMAP staleness threshold doc fix — NO-OP**

The plan's Task 3 instructed: "Fix the ROADMAP.md `2h/12h` staleness threshold to `< 6h / 6-24h / > 24h` to match REQUIREMENTS.md VIEW-11. If grep finds nothing, this task is a no-op AT THE DOC LEVEL — record this finding in the SUMMARY."

**Verification:** Ran `grep -nE "(2h|12h).*stale|stale.*(2h|12h)" .planning/ROADMAP.md .planning/PROJECT.md .planning/REQUIREMENTS.md` — exit code 1, zero matches. Also ran a broader `grep -rnE "2h|12h"` across the same files — zero matches. The staleness doc bug described in `06-CONTEXT.md` ("ROADMAP.md text says 2h/12h — that's a documentation bug") does not actually exist in the doc. ROADMAP.md success criterion #5 reads: "Staleness badge in header transitions GREEN/AMBER/RED based on snapshot age and `_status.json` partial-success state" — no specific thresholds named. REQUIREMENTS.md VIEW-11 carries the canonical `< 6h / 6-24h / > 24h` thresholds. The two are consistent (REQUIREMENTS.md is the source of truth for thresholds; ROADMAP.md just describes the badge transition).

**Action:** No commit. Task 3 verify command passes (zero matches). The CONTEXT.md statement was the user's recollection at planning time; plan-checker (called pre-execution) had already noted the discrepancy — this SUMMARY records the resolution.

---

**Total deviations:** 3 auto-fixed (2 RED-phase test-spec bugs found during GREEN; 1 toolchain substitution) + 1 plan-specified no-op
**Impact on plan:** All auto-fixes correct test specifications to match actual library semantics or new write-order. No scope creep. The deviation from "thread headlines via fetch_news(return_raw=True) inside run_for_watchlist" to "thread headlines via the pre-loaded Snapshot" is the more disciplined design (no double-fetch); the `fetch_news(return_raw=True)` API is still implemented as required by the test suite.

## Issues Encountered

None — TDD discipline held throughout (RED → GREEN → docs); no blockers; no architectural decisions needed.

## User Setup Required

None — pure Python amendment. The next routine run will produce v2 snapshots automatically; the frontend (Phase 6 Waves 1-4) will then validate against v2 zod schemas. Existing v1 snapshots in `data/YYYY-MM-DD/` (if any from Phase 5 dev runs) will be schema-mismatched and trigger the "schema upgrade required — re-run today's routine" banner that Phase 6 Wave 1 will implement.

## Next Phase Readiness

**Ready for Plan 06-02 (Frontend Scaffold, Wave 1):**
- `data/YYYY-MM-DD/{TICKER}.json` carries the v2 shape with all 4 new fields
- `data/_dates.json` at repo root for the date-selector single-fetch
- `synthesis.decision.ThesisStatus` Literal exposes the 5 enum values for frontend zod codegen
- `prompts/synthesizer.md` instructs the LLM to populate `thesis_status` per timeframe
- All Phase 1-5 tests still GREEN (zero regression)

**Locks for Wave 1 zod schemas:**
- Per-ticker JSON: `schema_version: z.literal(2)`
- `TimeframeBand.thesis_status: z.enum(["intact", "weakening", "broken", "improving", "n/a"])`
- `indicators` keys: `ma20 | ma50 | bb_upper | bb_lower | rsi14` — each `z.array(z.number().nullable())` aligned to `ohlc_history` length
- `headlines[].source`: free-string (currently `yahoo-rss | google-news | finviz` but extensible)

**No blockers for Wave 1.** Wave 0 closes complete.

## Self-Check: PASSED

Verified at completion:

| Claim | Verification |
|---|---|
| 3 series helpers in `_indicator_math.py` | `grep -nE "^def _(ma|bb|rsi)_series" analysts/_indicator_math.py` → 3 matches |
| `ThesisStatus` Literal exposed | `grep -n "ThesisStatus = Literal" synthesis/decision.py` → match |
| `thesis_status` field on TimeframeBand | `grep -n "thesis_status: ThesisStatus" synthesis/decision.py` → match |
| `schema_version: int = 2` | `grep -n "schema_version: int = 2" synthesis/decision.py` → match |
| `fetch_news(return_raw)` parameter | `grep -n "return_raw" ingestion/news.py` → match |
| `TickerResult.ohlc_history + .headlines` | `grep -nE "ohlc_history\|headlines" routine/run_for_watchlist.py` → matches |
| `_compute_indicator_series` + `_write_dates_index` | `grep -nE "^def _(compute_indicator_series|write_dates_index)" routine/storage.py` → 2 matches |
| Per-ticker payload `schema_version: 2` | `grep -n "\"schema_version\": 2" routine/storage.py` → match |
| Phase D `_write_dates_index(snapshots_root)` invocation | `grep -n "_write_dates_index(snapshots_root)" routine/storage.py` → match |
| Commits exist | `git log --oneline -3` shows `1646356` (feat), `8ea6252` (test) |
| All 659 tests pass | `.venv/Scripts/pytest.exe -q` → `659 passed` |

---
*Phase: 06-frontend-mvp-morning-scan-deep-dive*
*Completed: 2026-05-04*
