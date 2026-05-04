---
phase: 08-mid-day-refresh-resilience
plan: 01
subsystem: api

tags:
  - vercel
  - python-serverless
  - basehttprequesthandler
  - jsonl
  - provenance
  - pre-commit
  - resilience
  - yfinance
  - yahooquery
  - rss
  - feedparser

requires:
  - phase: 02-ingestion
    provides: ingestion.prices.fetch_prices + ingestion.news.fetch_news (return_raw=True) — keyless data plane reused verbatim by api/refresh.py
  - phase: 05-claude-routine-wiring
    provides: routine/llm_client._log_failure JSONL atomic-append pattern (memory_log mirrors); run_for_watchlist per-ticker pipeline + AgentSignal shape

provides:
  - api/refresh.py — Vercel Python serverless handler exposing GET /api/refresh?ticker=X
  - vercel.json (repo root) — function config maxDuration=30
  - frontend/vercel.json — SPA rewrite narrowed to /((?!api/).*) so /api/* requests are NOT silently rewritten to /index.html
  - routine/memory_log.py — append_memory_record() atomic JSONL writer (INFRA-06)
  - routine/run_for_watchlist.py Phase E hook — one record per (ticker, persona) per non-lite run
  - scripts/check_provenance.py — INFRA-07 enforcement walker over analysts/, routine/, synthesis/, ingestion/, api/, scripts/, prompts/personas/*.md, prompts/synthesizer.md
  - .pre-commit-config.yaml — local hook entry for the provenance check
  - 13 tests in tests/api/test_refresh.py covering happy + 4 failure modes + headline serialization + do_GET integration + ticker normalization
  - 13 tests in tests/routine/test_memory_log.py covering JSONL contract + schema strictness
  - 3 Phase E integration tests appended to tests/routine/test_run_for_watchlist.py
  - 13 tests in tests/scripts/test_check_provenance.py covering 3 marker forms + scan limit + recursion + main exit codes
  - 2 prices resilience tests + 1 news resilience test (REFRESH-04 backend portion)

affects:
  - 08-02-frontend-refresh-PLAN.md — backend response shape locked; frontend zod schema mirrors verbatim
  - any v1.x phase reading memory/historical_signals.jsonl (TREND-01 / TREND-02)
  - all future plans — provenance check now runs in pre-commit + intended for CI

tech-stack:
  added: []  # zero new runtime deps; all stdlib (BaseHTTPRequestHandler, urllib.parse, http.server, re, json, pathlib)
  patterns:
    - "Vercel Python serverless: BaseHTTPRequestHandler subclass named `handler` (lowercase) + sys.path bootstrap to import sibling top-level packages (api/refresh.py uses Path(__file__).resolve().parents[1])"
    - "Pure builder + thin handler: `_build_response(path) -> (dict, int)` is the test surface; do_GET() is HTTP plumbing only"
    - "Response envelope shape lock: success has `current_price` field + `error: false implicit`; full-failure shape DROPS `current_price` + adds `error: True` (frontend dispatch via inspecting envelope, not status code)"
    - "Memory log atomic-append: same discipline as routine/llm_client._log_failure (mkdir parents=True; mode='a'; json.dumps sort_keys=True; one record per line)"
    - "Phase E hook: gated by `if result.persona_signals:` which naturally skips lite_mode AND per-ticker pipeline failures (both leave the list empty)"
    - "Provenance markers (INFRA-07): 3 accepted forms (Pattern adapted from <ref>/<path>, Adapted from <ref>/<path>, novel-to-this-project) — case-insensitive on the keyword phrases; first 30 lines; in EITHER comment syntax (# / <!-- -->) OR plain text inside a docstring"

key-files:
  created:
    - api/refresh.py — 181 LOC; Vercel Python serverless handler
    - vercel.json — repo-root function config
    - routine/memory_log.py — 103 LOC; INFRA-06 JSONL writer
    - scripts/check_provenance.py — 186 LOC; INFRA-07 walker
    - scripts/__init__.py — package marker (empty)
    - .pre-commit-config.yaml — local hook entry
    - tests/api/__init__.py — package marker
    - tests/api/test_refresh.py — 408 LOC; 13 tests
    - tests/routine/test_memory_log.py — 309 LOC; 13 tests
    - tests/scripts/__init__.py — package marker
    - tests/scripts/test_check_provenance.py — 242 LOC; 13 tests
  modified:
    - frontend/vercel.json — SPA rewrite narrowed /(.*) -> /((?!api/).*)
    - routine/run_for_watchlist.py — added memory_log_path kwarg + Phase E hook + import
    - tests/routine/test_run_for_watchlist.py — appended 3 Phase E tests
    - tests/ingestion/test_prices.py — appended 2 explicit resilience tests (yfinance throws → yahooquery rescues; both throw → data_unavailable)
    - tests/ingestion/test_news.py — appended 1 explicit resilience test (all RSS broken → empty result, never raises)
    - .gitignore — memory/historical_signals.jsonl + memory/llm_failures.jsonl
    - 22 production files received `# novel-to-this-project` markers as part of the codebase audit pass (Task 3)

key-decisions:
  - "Loosened provenance regex from comment-form-only (#/<!--) to also accept marker text inside docstrings (case-insensitive on the keyword phrases). Existing Phase 3 analyst modules already document `Adapted from virattt/ai-hedge-fund/...` inside docstrings; a strict comment-only regex would have required either duplicating provenance or a 9-file edit churn. Loose regex still requires the <ref>/<path> token so it cannot accept generic prose."
  - "Plan's <interfaces> block documented `fetch_news(return_raw=True) -> (headlines, sentiment_score)`; the actual Phase 6 / Plan 06-01 signature is `(list[Headline], list[dict])` where the dict list carries the {source, published_at, title, url} 4-key shape. api/refresh.py uses the actual shape — the raw dict list IS what the frontend wants, no conversion needed."
  - "parse_qs(keep_blank_values=True) is load-bearing — without the flag `?ticker=` (empty value) becomes indistinguishable from no query string at all; both shapes need different error markers (invalid-ticker vs missing-ticker-param)."
  - "Provenance markers prepended ABOVE module docstrings (line 1) rather than inside them so the SCAN_LINE_LIMIT=30 window catches them even when docstrings grow."

patterns-established:
  - "Vercel Python serverless adapter pattern: handler class + pure builder; tests target the builder, do_GET is exercised via 2 MagicMock-based integration tests"
  - "Provenance audit: `python scripts/check_provenance.py` is a CI-runnable single-shot gate; future PRs adding a tracked file under DEFAULT_ROOTS or MD_TARGETS without a marker fail the pre-commit hook"
  - "Resilience tests as characterization tests: the 2 prices + 1 news resilience tests pass on first add (RED-skip) — they document existing behavior under the REFRESH-04 lock so a future regression that breaks ingestion forgiveness fails loudly"

requirements-completed: [REFRESH-01, INFRA-06, INFRA-07]

# REFRESH-04 backend portion is complete (2 prices resilience + 1 news resilience tests added; api/refresh.py
# error envelope locked). Full REFRESH-04 closure waits for 08-02 frontend resilience spec.

duration: 47min
started: 2026-05-04T18:00Z
completed: 2026-05-04T18:48Z
---

# Phase 08 Plan 01: Backend Refresh + Memory Log + Provenance Summary

**Vercel Python serverless `/api/refresh` (BaseHTTPRequestHandler + sys.path bootstrap; locked happy/partial/full-failure envelopes), per-(ticker, persona) JSONL memory log mirroring `_log_failure` discipline, and INFRA-07 provenance walker accepting 3 marker forms across 6 source roots — plus the load-bearing `frontend/vercel.json` SPA-rewrite narrowing to `/((?!api/).*)` so `/api/*` requests stop silently returning the SPA shell.**

## Performance

- **Duration:** ~47 min
- **Started:** 2026-05-04T18:00:00Z
- **Completed:** 2026-05-04T18:48:00Z
- **Tasks:** 3
- **Files modified:** 12 created + 5 modified + 22 audit-pass marker prepends = 39 file changes

## Accomplishments

- `api/refresh.py` (181 LOC) — Vercel Python serverless handler with sys.path bootstrap (so `from ingestion.prices import fetch_prices` resolves under Vercel's runtime). Pure `_build_response(path) -> (dict, int)` builder is the primary test surface; `class handler(BaseHTTPRequestHandler).do_GET` is thin HTTP plumbing. NO LLM imports, NO CORS headers (same-origin lock), NO new runtime dependencies.
- 3 locked response shapes implemented: success (with `current_price` + `price_timestamp` + `recent_headlines`), partial (price OK + RSS empty → `errors: ["rss-unavailable"]`), full-failure (price unavailable → `error: true`, NO `current_price` field).
- `vercel.json` at repo root configures `api/refresh.py` `maxDuration=30` (10× typical execution; well under the 300s Hobby cap researcher confirmed).
- **Load-bearing SPA-rewrite narrowing** in `frontend/vercel.json`: `/(.*)` → `/((?!api/).*)`. Without this fix `/api/refresh?ticker=AAPL` silently returns the SPA HTML shell with no error from Vercel's routing layer.
- `routine/memory_log.py` (103 LOC) — `append_memory_record(*, date, ticker, persona_id, verdict, confidence, evidence_count, log_path=None)` mirrors the `_log_failure` atomic-append discipline verbatim. Schema validation raises `ValueError` on date format / ticker case / verdict ladder / 0–100 confidence / 0–10 evidence_count violations.
- `routine/run_for_watchlist.py` Phase E hook fires at the watchlist-loop level after each `TickerResult` is appended. Gated by `if result.persona_signals:` which naturally skips lite_mode (no persona signals) AND per-ticker pipeline failures. Memory log failures are non-fatal (logger.warning + continue).
- `scripts/check_provenance.py` (186 LOC) walks DEFAULT_ROOTS (analysts/, routine/, synthesis/, ingestion/, api/, scripts/) + MD_TARGETS (prompts/personas + prompts/synthesizer.md) accepting 3 marker forms within the first 30 lines (regex is case-insensitive on the keyword phrases; accepts comment OR docstring location).
- Codebase audit: 22 project-original modules + 6 prompt files received `# novel-to-this-project` (or `<!-- novel-to-this-project -->` for markdown) markers. `python scripts/check_provenance.py` exits 0 against 48 scanned files.
- `.pre-commit-config.yaml` local hook entry: developers running `pre-commit install` get the gate before commit; CI invocation is the authoritative backstop.
- 2 explicit prices resilience tests + 1 news resilience test characterize the existing `data_unavailable=True` graceful-failure contract under the REFRESH-04 lock.

## Task Commits

Each task followed RED→GREEN TDD discipline:

1. **Task 1 (api/refresh.py + vercel.json + SPA narrowing)**:
   - `0cd223d` — `test(08-01): add failing tests for api/refresh.py Vercel handler` (13 tests)
   - `4bbcd76` — `feat(08-01): implement api/refresh.py Vercel handler + vercel.json + SPA narrowing`
2. **Task 2 (routine/memory_log + Phase E hook)**:
   - `43de55e` — `test(08-01): add failing tests for routine/memory_log + Phase E hook` (16 tests)
   - `ecf6dd3` — `feat(08-01): add routine/memory_log + Phase E hook in run_for_watchlist`
3. **Task 3 (scripts/check_provenance + .pre-commit + ingestion resilience + audit)**:
   - `a04687f` — `test(08-01): add provenance check tests + ingestion resilience tests` (13 + 3 tests)
   - `dd396e1` — `feat(08-01): scripts/check_provenance.py + .pre-commit-config + audit-pass markers`

**Plan metadata commit:** (this SUMMARY) — to be written after STATE.md / ROADMAP.md / REQUIREMENTS.md updates.

## Files Created/Modified

### Created (12)
- `api/refresh.py` — Vercel Python handler + pure builder
- `vercel.json` — repo-root function config (maxDuration=30)
- `routine/memory_log.py` — INFRA-06 JSONL writer
- `scripts/__init__.py` + `scripts/check_provenance.py` — INFRA-07 walker + CLI
- `.pre-commit-config.yaml` — local hook entry
- `tests/api/__init__.py` + `tests/api/test_refresh.py` — 13 tests
- `tests/routine/test_memory_log.py` — 13 tests
- `tests/scripts/__init__.py` + `tests/scripts/test_check_provenance.py` — 13 tests
- `.planning/phases/08-mid-day-refresh-resilience/08-01-backend-refresh-SUMMARY.md` (this file)

### Modified (5 + 28 audit-pass markers)
- `frontend/vercel.json` — SPA rewrite narrowed
- `routine/run_for_watchlist.py` — `memory_log_path` kwarg + Phase E hook + docstring
- `tests/routine/test_run_for_watchlist.py` — appended 3 Phase E tests
- `tests/ingestion/test_prices.py` — appended 2 resilience tests
- `tests/ingestion/test_news.py` — appended 1 resilience test
- `.gitignore` — `memory/historical_signals.jsonl` + `memory/llm_failures.jsonl`
- 28 markers prepended (22 .py + 6 .md): analysts/{position_signal, schemas, _indicator_math, data/__init__, data/filings, data/fundamentals, data/news, data/prices, data/snapshot, data/social}.py; ingestion/{__init__, errors, filings, fundamentals, http, manifest, news, prices, refresh, social}.py; routine/{__init__, storage}.py; synthesis/{__init__, dissent}.py; prompts/personas/{buffett, burry, lynch, munger, wood}.md; prompts/synthesizer.md.

## Decisions Made

- **Provenance regex loosening (case + location).** The plan's strict comment-only regex (`#\s*Pattern adapted from\s+\S+/`) didn't match the existing Phase 3 analyst documentation pattern (`Adapted from virattt/ai-hedge-fund/src/agents/...` inside docstrings, capitalized "Adapted"). Two options: (a) duplicate provenance with `# Adapted from ...` comments above existing docstring text, or (b) loosen the regex to accept docstring location and case-insensitive keyword. Chose (b) — the marker text carries the information; the comment syntax is incidental. Still requires the `<ref>/<path>` token so the regex cannot accept generic prose. This is captured in the `_PY_MARKERS` / `_MD_MARKERS` regex compilation in `scripts/check_provenance.py`.
- **`fetch_news(return_raw=True)` actual signature vs plan.** The plan's `<interfaces>` block claimed `(headlines, sentiment_score)` but the Phase 6 / Plan 06-01 implementation returns `(list[Headline], list[dict])` where the dict list is the `{source, published_at, title, url}` 4-key shape the frontend uses. `api/refresh.py` consumes the dict list directly — it IS the locked frontend shape. No conversion needed.
- **`parse_qs(keep_blank_values=True)` is load-bearing.** Without the flag `?ticker=` (empty value) becomes indistinguishable from no query string at all (both produce `parse_qs result == {}`). The plan locks two distinct error markers (`missing-ticker-param` vs `invalid-ticker`) so the flag is non-negotiable.
- **Memory log shape uses `analyst_id` from `AgentSignal` directly** (e.g. `"buffett"`, `"claude_analyst"`) — no remapping. This means the JSONL is queryable by the canonical persona ID a frontend trend view would use without an additional lookup table.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] `parse_qs` empty-value handling missed `invalid-ticker` test path**
- **Found during:** Task 1 GREEN — initial implementation parsed the query string with default `parse_qs(...)` flags. `?ticker=` (empty) → `parse_qs` returns `{}` (empty values dropped by default), so the `"ticker" not in query` branch fired and returned `missing-ticker-param` instead of `invalid-ticker`. Test 3 (`test_invalid_ticker`) failed.
- **Fix:** Added `keep_blank_values=True` to `parse_qs` and a comment explaining why (distinguish "empty value present" from "key absent entirely").
- **Files modified:** `api/refresh.py`
- **Verification:** All 13 api/ tests green.
- **Committed in:** `4bbcd76` (Task 1 GREEN commit)

**2. [Rule 1 — Bug] Provenance regex too strict for existing Phase 3 docstrings**
- **Found during:** Task 3 codebase audit pass.
- **Issue:** Initial regex `#\s*Pattern adapted from\s+\S+/` etc. required the `#` comment prefix. But Phase 3 analyst modules already document `Adapted from virattt/ai-hedge-fund/src/agents/x.py` INSIDE module docstrings (no `#`). 8 analyst modules + the 4 already-marked Phase 3 modules would have falsely failed the audit.
- **Fix:** Loosened the regex to accept the marker text in EITHER comment form OR docstring location, and made the keyword phrases case-insensitive (`[Aa]dapted from`, `[Pp]attern adapted from`). Still requires the `<ref>/<path>` token (`\S+/`) so it cannot accept generic prose like "Adapted to the project's needs".
- **Files modified:** `scripts/check_provenance.py`
- **Verification:** All 13 provenance tests still green; live audit went from 44 → 0 offenders after this loosening + 28 marker prepends.
- **Committed in:** `dd396e1` (Task 3 GREEN commit)

**3. [Rule 3 — Blocking] `uv` not available in project venv**
- **Found during:** Plan-level verify step.
- **Issue:** VALIDATION.md specifies `uv run pytest ...` but the project venv does not have `uv` installed (Python 3.14 venv with pytest installed directly).
- **Fix:** Substituted `python -m pytest ...` (the venv's Python is on PATH via `/c/Users/Mohan/markets/.venv/Scripts/python`). Identical test execution; just bypasses `uv`'s wrapper layer.
- **Files modified:** None (process-only deviation).
- **Verification:** Same test counts pass via either invocation.
- **Committed in:** N/A (no file changes).

---

**Total deviations:** 3 auto-fixed (2 Rule 1 bugs, 1 Rule 3 blocking). All necessary for correctness. No scope creep.

**Impact on plan:** All locked behaviors implemented exactly as the CONTEXT.md decisions specified. The provenance regex loosening is the only material policy change — and it preserves the strict `<ref>/<path>` requirement so the gate remains meaningful.

## Issues Encountered

- **22 + 6 audit-pass markers needed.** The codebase had 44 files lacking explicit provenance markers (after the regex loosening, still 30). Added markers categorized by function: schemas + ingestion adapters + package markers + persona prompts as `novel-to-this-project` (project-original); existing analyst modules with `Adapted from virattt/...` already in docstrings now match the loosened regex without duplication. Resolved.
- **`parse_qs` default behavior surprise.** Documented in deviation #1; resolved with `keep_blank_values=True`.

## User Setup Required

None — no external service configuration required for Wave 0 backend. Wave 1 (08-02) frontend integration tests against the function (production deploy verification + cold-start measurement) deferred per VALIDATION.md "Manual-Only Verifications" table — those land after Wave 1 ships.

## Next Phase Readiness

- **Backend Wave 0 complete.** Wave 1 (08-02 frontend integration) is unblocked — the locked response shapes are documented in api/refresh.py + tests/api/test_refresh.py, the `frontend/src/schemas/refresh.ts` zod schema can mirror the Python envelope verbatim.
- **REFRESH-01 closed.** Vercel function shape locked.
- **REFRESH-04 backend half closed.** 2 prices + 1 news resilience tests characterize the existing graceful-failure contract; api/refresh.py error envelope tested across 4 failure modes. Frontend resilience.spec.ts (Wave 1) closes the full REFRESH-04 acceptance.
- **INFRA-06 closed.** memory_log + Phase E hook + .gitignore + 13 tests + 3 integration tests.
- **INFRA-07 closed.** check_provenance.py + .pre-commit-config + 13 tests + codebase clean (48 files scanned, 0 offenders).
- **No blockers for Wave 1.** Wave 1 unit tests can mock `/api/refresh` with the exact envelope shapes locked by tests/api/test_refresh.py; the resilience.spec.ts e2e test can hit a deployed preview function or a local mock.

## Self-Check: PASSED

- `api/refresh.py` exists ✓
- `vercel.json` (root) exists ✓
- `frontend/vercel.json` rewrite narrowed ✓ (verified by inspection)
- `routine/memory_log.py` exists ✓
- `routine/run_for_watchlist.py` Phase E hook present ✓ (verified via `grep "append_memory_record"`)
- `scripts/check_provenance.py` exists ✓
- `.pre-commit-config.yaml` exists ✓
- All 6 task commits exist in git log: `0cd223d`, `4bbcd76`, `43de55e`, `ecf6dd3`, `a04687f`, `dd396e1` ✓
- `python scripts/check_provenance.py` exits 0 against the live codebase (48 files scanned) ✓
- Full Python pytest suite: 704 passed (659 baseline + 45 new tests) ✓
- Plan-level verify command: 87 passed (api/ 13 + memory_log 13 + run_for_watchlist 26 incl. 3 Phase E + check_provenance 13 + prices 22 incl. 2 resilience + news 26 incl. 1 resilience — boundaries vary by file but ALL green) ✓

---

*Phase: 08-mid-day-refresh-resilience*
*Plan: 01*
*Completed: 2026-05-04*
