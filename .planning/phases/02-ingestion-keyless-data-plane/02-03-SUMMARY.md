---
phase: 02-ingestion-keyless-data-plane
plan: 03
subsystem: ingestion
tags: [edgar, sec, filings, cik, requests, responses, tdd, ua-compliance]

# Dependency graph
requires:
  - phase: 02-ingestion-keyless-data-plane
    plan: 01
    provides: ingestion.http.get_session (UA-compliant shared session + 3-retry adapter), ingestion.errors.{NetworkError, SchemaDriftError}, analysts.data.FilingMetadata
  - phase: 01-foundation-watchlist-per-ticker-config
    provides: analysts.schemas.normalize_ticker (single source of truth for ticker normalization)
provides:
  - ingestion.filings.lookup_cik (ticker -> 10-digit zero-padded CIK; in-process cached)
  - ingestion.filings.fetch_filings (ticker -> list[FilingMetadata]; default forms 10-K/10-Q/8-K)
  - ingestion.filings.{EDGAR_TICKERS_URL, EDGAR_SUBMISSIONS_URL} (URL templates for testing)
affects: [02-06-refresh-orchestrator]

# Tech tracking
tech-stack:
  added: []  # No new dependencies; Plan 02-01 already locked requests/responses
  patterns:
    - "In-process whole-index cache for ticker->CIK (single fetch fills _CIK_CACHE for the run)"
    - "Polite-sleep gate at 110ms (10 req/s ceiling per SEC fair-access policy)"
    - "Per-row defensive try/except around date.fromisoformat + FilingMetadata(...) — log and skip a single bad row, never fail the whole fetch"
    - "Form-type Literal escape-hatch: unknown EDGAR forms map to 'OTHER' instead of raising ValidationError"
    - "UA-header verification at the responses-lib boundary (request.headers introspection in tests)"
    - "Retry exhaustion: register the mocked URL N+1 times in tests so the urllib3 retry adapter sees consistent responses across all 4 attempts"

key-files:
  created:
    - ingestion/filings.py (252 lines — lookup_cik + _populate_cik_cache + fetch_filings)
    - tests/ingestion/test_filings.py (550 lines — 22 tests including 3 probes)
    - tests/ingestion/fixtures/edgar_company_tickers.json (5-ticker index — AAPL/NVDA/BRK-B/MSFT/AMZN)
    - tests/ingestion/fixtures/edgar_submissions_aapl.json (25 filings: 1x10-K, 4x10-Q, 11x8-K, plus DEF 14A/S-3/S-8/4/144)
    - tests/ingestion/fixtures/edgar_403.txt (paraphrased SEC fair-access denial body)
  modified: []

key-decisions:
  - "Index cache populated wholesale on first call (the index is ~1MB / <30k entries — caching the full mapping in one shot is cheaper than per-ticker round-trips and matches the orchestrator's expected access pattern of ~30-50 watchlist tickers per refresh)"
  - "_CIK_CACHE is module-level mutable state; tests reset via an autouse fixture that clears _CIK_CACHE + _LAST_CALL before AND after each test (mirrors the discipline in Plan 02-01 for module singletons)"
  - "Unknown ticker (CIK lookup miss) returns [] not an error — some watchlist entries may legitimately not file with EDGAR (foreign issuers, ETFs, non-public proxies). The orchestrator in 02-06 treats [] as 'no filings, move on' rather than 'data_unavailable'"
  - "Bad filingDate row is logged + skipped, not fatal — defends against EDGAR returning a partially-malformed array without nuking the entire ticker's filing history"
  - "Form-type 'OTHER' escape-hatch from analysts/data/filings.py is exercised: an unknown form passed through forms=(...) maps to OTHER and validates cleanly. Default forms tuple stays ('10-K','10-Q','8-K') per DATA-03"
  - "Polite-sleep state is module-level here (not caller-owned) — filings.py is the SOLE owner of EDGAR's politeness budget across the process. Tests clear via autouse fixture; production code only ever touches it from this one module"
  - "403 raises NetworkError with full diagnostic (CIK + UA header sent + SEC docs link); the orchestrator catches IngestionError and marks data_unavailable=True so the morning scan keeps moving even when EDGAR goes dark"
  - "schema-drift detection has TWO levels: 'filings' missing AND 'filings.recent' missing both raise SchemaDriftError with distinct diagnostic messages"

requirements-completed: [DATA-03]

# Metrics
duration: 3min 25sec
completed: 2026-05-01
---

# Phase 02 Plan 03: EDGAR Filings Summary

**SEC EDGAR filings ingestion with UA-compliance probe and CIK-cache hardening — `fetch_filings(ticker)` returns a typed list of recent 10-K/10-Q/8-K metadata, gracefully degrades on 403 (UA non-compliance) and 429 (retry-then-succeed), and never blows up on a single malformed row.**

## Performance

- **Duration:** ~3m 25s (RED to GREEN to coverage-pass)
- **Started:** 2026-05-01T10:45:42Z
- **Completed:** 2026-05-01T10:49:07Z
- **Tasks:** 1 (TDD-styled — single task with RED + GREEN sub-commits)
- **Files created:** 5
- **Files modified:** 0

## Accomplishments

- `ingestion/filings.py` ships the public surface Plan 02-06 will import: `lookup_cik(ticker) -> Optional[str]` (10-digit zero-padded), `fetch_filings(ticker, *, forms=("10-K","10-Q","8-K"), limit=20) -> list[FilingMetadata]`, plus `EDGAR_TICKERS_URL` / `EDGAR_SUBMISSIONS_URL` URL templates exposed for testing.
- 22 tests green: 4 lookup_cik tests (happy, unknown, cache, dotted-ticker normalization), 7 fetch_filings happy-path / contract tests, 3 probe-mapped tests (2-W2-06 happy, 2-W2-07 403, 2-W2-08 429-retry), and 8 coverage / hardening tests covering schema-drift edges, malformed entries, bad dates, retry-exhaustion on 500, and unknown-form mapping.
- Coverage on `ingestion/filings.py`: **98% line / 100% branch** (gate is ≥90% line / ≥85% branch). The 3 missed lines are the per-row `ValidationError` defensive log+skip path, which is reachable only via runtime EDGAR data corruption — covered functionally by the bad-filing-date test, but the specific Pydantic-validation branch is unexercised because we don't have a fixture row that parses as a date but fails FilingMetadata's other constraints.
- Three EDGAR fixtures committed: `edgar_company_tickers.json` (5 tickers — AAPL/NVDA/BRK-B/MSFT/AMZN with the real SEC index shape), `edgar_submissions_aapl.json` (25 filings spanning 10-K/10-Q/8-K/DEF 14A/S-3/S-8/4/144 across 16 months), `edgar_403.txt` (the paraphrased fair-access denial body SEC returns).
- Plan-scoped suite: 77/77 tests green in `tests/ingestion/`. Full-repo suite: 112/112 green.
- Zero real network: every HTTP path is mocked via the `responses` library and verified at the request-headers boundary.

## Task Commits

1. **RED — Failing tests + fixtures** — `04b0316` (test)
2. **GREEN — Implement EDGAR filings fetch** — `0fe0171` (feat)

**Plan metadata commit:** added in the wrap-up step (covers SUMMARY.md, STATE.md, ROADMAP.md, REQUIREMENTS.md).

## Files Created/Modified

### Created
- `ingestion/filings.py` (252 lines) — module docstring cites Pitfall #2 + DATA-03; constants `EDGAR_TICKERS_URL`, `EDGAR_SUBMISSIONS_URL`, `_CIK_CACHE`, `_LAST_CALL`, `_MIN_INTERVAL=0.11`, `_KNOWN_FORM_TYPES`; functions `lookup_cik`, `_populate_cik_cache`, `fetch_filings`.
- `tests/ingestion/test_filings.py` (550 lines) — 22 tests with autouse cache-reset fixture; probe-id mappings in test docstrings.
- `tests/ingestion/fixtures/edgar_company_tickers.json` — 5-ticker SEC index fixture.
- `tests/ingestion/fixtures/edgar_submissions_aapl.json` — 25-filing AAPL submissions JSON with the parallel-arrays shape.
- `tests/ingestion/fixtures/edgar_403.txt` — non-empty fair-access denial body for the 403 probe.

### Modified
- *None.* This plan touched only its allowed parallel-safety files (filings.py, test_filings.py, edgar_*.json, edgar_*.txt). pyproject.toml, http.py, errors.py, prices.py, fundamentals.py, news.py, social.py, analysts/data/* are owned by other plans and were NOT touched.

## Decisions Made

- **In-process whole-index cache for ticker→CIK** (Pitfall #2 / locked architecture): The SEC company_tickers index is fetched ONCE per process and cached in `_CIK_CACHE`. The orchestrator (Plan 02-06) hits 30-50 tickers per refresh; one full-index pull + 30-50 dict lookups beats 30-50 per-ticker round-trips by a wide margin. NO disk cache in this plan — that's a 02-06 enhancement if morning-refresh latency demands it.
- **`_CIK_CACHE` and `_LAST_CALL` are module-level**: Unlike the polite_sleep contract from Plan 02-01 (which is caller-owned-state), filings.py is the SOLE owner of EDGAR's politeness budget across the process. Module-level state is correct here; tests reset via autouse fixture.
- **Unknown ticker → `[]` not error**: Watchlist may include foreign issuers, ETFs, or trust units that don't file with EDGAR. The orchestrator treats `[]` as "no EDGAR filings, move on" rather than `data_unavailable=True`. The orchestrator's downstream agents (Phase 3 analysts) will see an empty filings list and score accordingly.
- **Bad row is logged + skipped, not fatal** (Pitfall #1 — silent upstream breakage): If EDGAR returns a single row with `filingDate="not-a-date"` or some other corruption, we log a warning and skip THAT ROW — the rest of the ticker's filings history is preserved. This is the same defensive discipline used in Plan 02-02's missing-key tolerance.
- **Form-type `"OTHER"` escape-hatch** (consumed from Plan 02-01 schema decision): The default `forms=("10-K","10-Q","8-K")` filter is what enforces DATA-03's user-visible contract; the schema's wider Literal (DEF 14A/S-1/20-F/6-K/OTHER) gives the function flexibility to surface less common forms when a future caller passes them via `forms=(...)`. Unknown forms passed-through map to `"OTHER"` and validate cleanly.
- **403 diagnostic includes UA header sent**: The error message names the exact header the session is using (`session.headers.get('User-Agent')`) so a future maintainer debugging "EDGAR is 403'ing" can immediately confirm whether the env override is active or the default value is in flight.
- **Two-level schema-drift detection**: We check both `"filings" not in payload` AND `"recent" not in payload["filings"]` separately so the diagnostic message names the precise key that's missing. This is a small thing but it'll save 30 minutes the day EDGAR ships a v2 endpoint that wraps `recent` under a different sub-key.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added 8 coverage / hardening tests beyond the planned 9**
- **Found during:** Initial GREEN coverage check.
- **Issue:** Plan listed 9 tests; with only those 9, `ingestion/filings.py` coverage came in at **79% line / unknown branch**, below the ≥90% / ≥85% gate. Missing branches: the entire error-path section (index 500 / non-JSON / non-dict / malformed entries / submissions 500 / submissions non-JSON / missing `filings.recent` / bad filingDate / unknown-form-mapped-to-OTHER).
- **Fix:** Added 8 additional tests covering invalid-ticker (no network), index 500/non-JSON/list-shape, malformed entries, submissions 500/non-JSON/missing recent, bad filingDate, and unknown-form OTHER mapping. Plus 2 contract-tightening tests not strictly needed for coverage (`test_lookup_cik_normalizes_dotted_ticker`, `test_filings_respects_limit`).
- **Files modified:** `tests/ingestion/test_filings.py`
- **Verification:** Coverage rose to **98% line / 100% branch** on `ingestion/filings.py` — gate cleared with margin.
- **Committed in:** `0fe0171` (alongside the GREEN implementation, since the missing tests were caught at the coverage-gate step right after the initial impl, not as a separate RED).

**2. [Rule 3 - Blocking] urllib3 Retry adapter required N+1 mocked responses for retry-exhaustion tests**
- **Found during:** Writing `test_lookup_cik_index_500_raises_network_error` and `test_filings_500_raises_network_error`.
- **Issue:** A single `responses.add(..., status=500)` call doesn't model the retry-exhaustion path because urllib3's `Retry(total=3)` adapter from Plan 02-01 makes 4 attempts (initial + 3 retries) and the responses-lib needs each one mocked separately — otherwise after attempt 1 the test sees `ConnectionError: no more requests registered`.
- **Fix:** Register the same mocked URL 4 times via a `for _ in range(4)` loop. The shared session retries through all 4, finally returns 500, and our code raises NetworkError as expected.
- **Files modified:** `tests/ingestion/test_filings.py` (only)
- **Verification:** Both 500-retry tests pass cleanly.
- **Committed in:** `0fe0171`

---

**Total deviations:** 2 auto-fixed (1 Rule 2 missing-critical for coverage gate, 1 Rule 3 blocking for the retry-adapter test mechanic). Both are tightening, not scope creep — the plan's "9 tests" was a lower bound and the coverage gate is what drove the final count to 22.

## Issues Encountered

- **`uv` not on PATH**: pre-existing per STATE.md; resolved by prepending `/c/Users/Mohan/AppData/Roaming/Python/Python314/Scripts/` to `PATH` in each `uv` bash call. Same workaround as every previous plan in this phase.
- **LF→CRLF warnings on `git add`**: Windows line-ending normalization. Cosmetic; harmless.
- **`.planning/config.json` had a stale `_auto_chain_active` flag** in the working tree (modified but not part of this plan's scope) — left untouched per parallel-safety constraints.

## Self-Check: PASSED

- [x] `ingestion/filings.py` exists — FOUND (252 lines, ≥70 min)
- [x] `tests/ingestion/test_filings.py` exists — FOUND (550 lines, ≥60 min)
- [x] `tests/ingestion/fixtures/edgar_company_tickers.json` exists — FOUND (5 tickers including BRK-B with hyphen form)
- [x] `tests/ingestion/fixtures/edgar_submissions_aapl.json` exists — FOUND (25 filings, parallel-arrays shape, dates desc 2026-04-30 → 2025-01-15)
- [x] `tests/ingestion/fixtures/edgar_403.txt` exists — FOUND (non-empty)
- [x] Commit `04b0316` (RED) — FOUND
- [x] Commit `0fe0171` (GREEN) — FOUND
- [x] `uv run pytest tests/ingestion/test_filings.py -v` — 22/22 green
- [x] `uv run pytest tests/ingestion/ -q` — 77/77 green
- [x] `uv run pytest -q` — 112/112 green (full suite)
- [x] `uv run pytest --cov=ingestion.filings --cov-branch tests/ingestion/test_filings.py` — 98% line / 100% branch (gate ≥90%/≥85%)
- [x] Probe 2-W2-06 → `test_filings_happy` (named in test docstring)
- [x] Probe 2-W2-07 → `test_filings_403` (named in test docstring)
- [x] Probe 2-W2-08 → `test_filings_429_retry` (named in test docstring)
- [x] UA header verified at responses-lib boundary on BOTH endpoints (`test_lookup_cik_happy` for tickers, `test_filings_happy` for submissions)
- [x] Parallel-safety constraint observed: only `ingestion/filings.py`, `tests/ingestion/test_filings.py`, and `tests/ingestion/fixtures/edgar_*` touched. `pyproject.toml`, `ingestion/http.py`, `ingestion/errors.py`, `analysts/data/*`, `ingestion/prices.py`, `ingestion/fundamentals.py`, `ingestion/news.py`, `ingestion/social.py` UNTOUCHED.

## Next Phase Readiness

- **Plan 02-06 unblocked on the EDGAR axis**: `from ingestion.filings import fetch_filings` is now available. The orchestrator wraps the call in `try/except IngestionError`; on `NetworkError` (403/500/timeout) it sets `data_unavailable=True` on the per-ticker filings slice; on `SchemaDriftError` it pages a human and continues. Empty list is the no-filings happy path.
- **DATA-03 satisfied**: 10-K/10-Q/8-K from EDGAR with compliant User-Agent. Mark as complete in REQUIREMENTS.md.
- **Probes locked**: 2-W2-06, 2-W2-07, 2-W2-08 all satisfied with named tests + docstring probe-id comments.
- **Wave 2 status (after this plan)**: 02-02 (prices/fundamentals) ✓, 02-03 (filings) ✓. 02-04 (news/RSS) and 02-05 (social) running in parallel; 02-06 (orchestrator) gates on all four.
- **No carry-overs / no blockers** for downstream consumers.

---
*Phase: 02-ingestion-keyless-data-plane*
*Plan: 03-edgar-filings*
*Completed: 2026-05-01*
