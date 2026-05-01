---
phase: 02-ingestion-keyless-data-plane
plan: 01
subsystem: ingestion
tags: [pydantic, requests, urllib3-retry, responses, yfinance, yahooquery, edgar, rss, tdd]

# Dependency graph
requires:
  - phase: 01-foundation-watchlist-per-ticker-config
    provides: analysts.schemas.normalize_ticker (single source of truth for ticker normalization), watchlist.loader pattern (atomic save / sort_keys serialization)
provides:
  - ingestion.http.get_session (process-shared requests.Session with EDGAR-compliant UA + 3-retry HTTPAdapter on 429/5xx)
  - ingestion.http.polite_sleep (per-source min-interval helper with caller-owned state)
  - ingestion.http.{USER_AGENT, DEFAULT_TIMEOUT} (env-overridable / module constants)
  - ingestion.errors.{IngestionError, NetworkError, SchemaDriftError} (3-level exception hierarchy)
  - analysts.data.{PriceSnapshot, OHLCBar, FundamentalsSnapshot, FilingMetadata, Headline, RedditPost, StockTwitsPost, SocialSignal} (eight Pydantic schemas)
  - tests/ingestion/ scaffolding with session-scoped fixtures_dir fixture
affects: [02-02-prices-fundamentals, 02-03-edgar-filings, 02-04-news-rss, 02-05-social, 02-06-refresh-orchestrator]

# Tech tracking
tech-stack:
  added: [yfinance>=0.2.50, yahooquery>=2.3, requests>=2.31, feedparser>=6.0, beautifulsoup4>=4.12, responses>=0.25 (dev)]
  patterns:
    - "TDD RED→GREEN with separate commits per phase"
    - "Process-wide singleton requests.Session via lazy init + module-level _SESSION"
    - "urllib3 Retry(total=3, backoff_factor=0.3, status_forcelist=[429,500,502,503,504], allowed_methods={GET,HEAD}) mounted on HTTPAdapter"
    - "Caller-owned state dict for polite_sleep (no module singletons that bleed between tests)"
    - "field_validator(mode='before') delegating to module-level normalize_ticker — single source of truth across analysts/schemas + analysts/data"
    - "ConfigDict(extra='forbid') on every Pydantic model in analysts/data — defense against silent upstream additions"
    - "Probe-ID comments above each test (# Probe 2-W1-XX) for mechanical pairing with VALIDATION.md"

key-files:
  created:
    - ingestion/__init__.py
    - ingestion/errors.py
    - ingestion/http.py
    - analysts/data/__init__.py
    - analysts/data/prices.py
    - analysts/data/fundamentals.py
    - analysts/data/filings.py
    - analysts/data/news.py
    - analysts/data/social.py
    - tests/ingestion/__init__.py
    - tests/ingestion/conftest.py
    - tests/ingestion/test_http.py
    - tests/ingestion/test_errors.py
    - tests/ingestion/test_data_schemas.py
    - tests/ingestion/fixtures/.gitkeep
  modified:
    - pyproject.toml

key-decisions:
  - "USER_AGENT is read from MARKETS_USER_AGENT env var at module import time (default: EDGAR-compliant 'Markets Personal Research (mohanraval15@gmail.com)') — overridable per-process, not per-call"
  - "HTTPAdapter Retry uses raise_on_status=False so callers see the final response object (status code + body) when retries exhaust on 5xx; required by test_retry_gives_up_after_3 to assert response.status_code == 503"
  - "polite_sleep caller-owns the last_call dict — no module singletons that would bleed between tests"
  - "FilingMetadata.cik uses Field(pattern=r'^\\d{10}$') to enforce SEC zero-padded format; FilingMetadata.form_type Literal includes 'OTHER' as escape-hatch so EDGAR can return unknown forms (foreign S-3, etc.) without 500ing the fetch"
  - "Headline.url is plain str not pydantic.HttpUrl — Yahoo redirect URLs sometimes fail HttpUrl's strict checks; ingestion/news.py does its own minimum validation"
  - "Fundamentals metrics carry NO positivity constraint at the schema layer — FCF can be negative, ROE can be negative for losing firms, downstream sanity checks enforce ranges where math demands it"
  - "test_schemas_reject_non_string_ticker added to push branch coverage to 100% (covers `isinstance(v, str)` False path in every _normalize_ticker_field validator)"

patterns-established:
  - "Singleton HTTP session pattern: module-level `_SESSION: Optional[requests.Session] = None` + lazy `if _SESSION is not None: return _SESSION` short-circuit. Reset by importlib.reload() in env-override tests."
  - "TDD RED→GREEN dual-commit per task — RED commits failing tests; GREEN commits implementation that turns them green. Mirrors the plan-04 / plan-05 pattern from Phase 1."
  - "Probe-ID comments (`# Probe 2-W1-NN`) above each test function so the verifier can mechanically pair tests with VALIDATION.md probes."
  - "Pydantic v2 field_validator(mode='before') delegating to module-level normalize_ticker — exactly one regex pattern across the codebase."

requirements-completed: [DATA-06]

# Metrics
duration: 5min
completed: 2026-05-01
---

# Phase 02 Plan 01: Foundation Summary

**Shared requests.Session with EDGAR-compliant UA + 3-retry policy, three-class IngestionError hierarchy, and five Pydantic data schemas (prices/fundamentals/filings/news/social) — every Wave-2 plan can now import a single audited HTTP client and typed shapes**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-01T08:07:45Z
- **Completed:** 2026-05-01T08:12:49Z
- **Tasks:** 3 (all auto, all TDD)
- **Files created:** 15
- **Files modified:** 1 (pyproject.toml)

## Accomplishments

- `ingestion/http.py` ships `get_session()` returning a process-shared `requests.Session` with EDGAR-compliant `User-Agent` (env-overridable via `MARKETS_USER_AGENT`), `HTTPAdapter` mounted with `Retry(total=3, backoff_factor=0.3, status_forcelist=[429,500,502,503,504], allowed_methods={GET,HEAD}, raise_on_status=False)`, plus `DEFAULT_TIMEOUT=10.0` constant and `polite_sleep(source, last_call, min_interval)` helper.
- `ingestion/errors.py` ships the three-level exception hierarchy (`IngestionError` -> `NetworkError`, `SchemaDriftError`) so the Plan 02-06 orchestrator can `except IngestionError` once and branch on isinstance.
- `analysts/data/` sub-package ships eight Pydantic schemas across five domain modules. Every model uses `analysts.schemas.normalize_ticker` (no regex duplication), `ConfigDict(extra="forbid")` (no silent upstream-add tolerance), and the standard `ticker / fetched_at / source / data_unavailable` quadruple.
- `tests/ingestion/` scaffolding with session-scoped `fixtures_dir` fixture is in place; Wave-2 plans (02-02..02-05) can drop their recorded JSON / XML / HTML fixtures into `tests/ingestion/fixtures/` and read via `(fixtures_dir / "name").read_text()`.
- 34 new ingestion tests green (9 http + 2 errors + 23 schemas). Full suite 69/69 (35 phase-1 + 34 phase-2-W1).
- Coverage: `ingestion/errors.py` 100% line / 100% branch; `ingestion/http.py` 97% line / 91% branch; `analysts/data/*` 100% line / 100% branch. All exceed the ≥90% line / ≥85% branch gate.

## Task Commits

1. **Task 1: Scaffold ingestion/ + analysts/data/ + tests/ingestion/** — `0ffcabf` (chore)
2. **Task 2 RED: Failing tests for http session + error hierarchy** — `b370d9c` (test)
3. **Task 2 GREEN: Implement shared HTTP session + ingestion exception hierarchy** — `b58f932` (feat)
4. **Task 3 RED: Failing tests for analysts/data schemas** — `b206206` (test)
5. **Task 3 GREEN: Implement Pydantic schemas for ingested data** — `777ff28` (feat)

**Plan metadata commit:** added in the wrap-up step (covers SUMMARY.md, STATE.md, ROADMAP.md, REQUIREMENTS.md).

## Files Created/Modified

### Created
- `ingestion/__init__.py` — package marker
- `ingestion/errors.py` — `IngestionError` / `NetworkError` / `SchemaDriftError` (3 classes)
- `ingestion/http.py` — `USER_AGENT`, `DEFAULT_TIMEOUT`, `get_session()`, `polite_sleep()` (76 lines)
- `analysts/data/__init__.py` — re-exports of all eight schema types via `__all__`
- `analysts/data/prices.py` — `OHLCBar` + `PriceSnapshot`
- `analysts/data/fundamentals.py` — `FundamentalsSnapshot`
- `analysts/data/filings.py` — `FilingMetadata` (form_type Literal, CIK pattern)
- `analysts/data/news.py` — `Headline` (title 1-500 chars, dedup_key required)
- `analysts/data/social.py` — `RedditPost` + `StockTwitsPost` + `SocialSignal`
- `tests/ingestion/__init__.py` — package marker
- `tests/ingestion/conftest.py` — session-scoped `fixtures_dir` fixture
- `tests/ingestion/test_http.py` — 9 tests (probes 2-W1-01, 2-W1-02)
- `tests/ingestion/test_errors.py` — 2 tests (probe 2-W1-03 errors slice)
- `tests/ingestion/test_data_schemas.py` — 23 tests (probe 2-W1-03 schemas slice)
- `tests/ingestion/fixtures/.gitkeep` — directory marker

### Modified
- `pyproject.toml` — added 5 runtime deps (yfinance, yahooquery, requests, feedparser, beautifulsoup4) + 1 dev dep (responses); registered `ingestion` in `[tool.hatch.build.targets.wheel].packages` and `[tool.coverage.run].source`.

## Decisions Made

- **USER_AGENT env override** (Pitfall #2): `MARKETS_USER_AGENT` env var read at module import; default is the EDGAR-compliant `"Markets Personal Research (mohanraval15@gmail.com)"`. This is overridable per-process, not per-call — matches the locked architecture (single audited HTTP client).
- **`raise_on_status=False`** on the urllib3 Retry: callers see the final response object (status code + body) when retries exhaust on 5xx, so the orchestrator in Plan 02-06 can decide whether to mark `data_unavailable` vs raise `NetworkError` based on the concrete response. The probe `test_retry_gives_up_after_3` asserts `response.status_code == 503` after exhausted retries.
- **`allowed_methods=frozenset(["GET", "HEAD"])`**: never silently retry POST/PUT/PATCH — Phase 2 only does GETs, but locking this in defends against future code paths that might issue mutating calls.
- **Caller-owned `last_call: dict[str, float]` for `polite_sleep`**: no module-level singleton. Each refresh run owns its own clock so tests can pass fresh dicts and not leak state across runs. Mirror of the Phase-1 loader-style "no hidden global state" discipline.
- **Fundamentals carry NO positivity constraint at the schema layer**: free cash flow can legitimately be negative, ROE can be negative for losing firms, debt-to-equity can be 0 for unlevered companies. Pydantic enforces shape; downstream sanity checks (Plan 02-02 ingestion or analyst scoring in Phase 3) enforce ranges where math demands it.
- **`Headline.url` is plain `str` not `pydantic.HttpUrl`**: Yahoo redirect URLs sometimes fail HttpUrl's strict scheme/host checks even when the URL is functional. ingestion/news.py (Plan 02-04) will do its own minimum validation (must start with `http`).
- **`FilingMetadata.form_type` Literal includes `"OTHER"` escape-hatch**: EDGAR returns forms we don't enumerate (foreign S-3, etc.); rather than 500'ing the fetch, Plan 02-03 will map unknown forms to `"OTHER"`.
- **`ConfigDict(extra="forbid")` on every model**: silent additions to upstream payloads (Yahoo, EDGAR, Reddit) should surface as `ValidationError` in tests/CI, not slip through silently. Mirrors the Phase-1 schemas' strict mode.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added `raise_on_status=False` to Retry**
- **Found during:** Task 2 GREEN phase — initial Retry implementation without `raise_on_status=False` would have caused `test_retry_gives_up_after_3` to fail because urllib3 raises `MaxRetryError` instead of returning the final 503 response, but the plan explicitly accepts EITHER behavior. Setting `raise_on_status=False` makes the canonical behavior "return final response", which is more useful for the Plan 02-06 orchestrator.
- **Fix:** Added `raise_on_status=False` to the `Retry(...)` constructor.
- **Files modified:** `ingestion/http.py`
- **Verification:** `test_retry_gives_up_after_3` passes; assertion uses `r.status_code == 503` branch.
- **Committed in:** `b58f932`

**2. [Rule 2 - Missing Critical] Added `test_schemas_reject_non_string_ticker` to lift branch coverage to 100%**
- **Found during:** Task 3 GREEN coverage check — initial coverage was 95% line / 80% branch on `analysts/data/*`, below the ≥85% branch gate.
- **Issue:** Each `_normalize_ticker_field` validator's `normalize_ticker(v) if isinstance(v, str) else None` ternary had only the `isinstance(v, str)` True branch exercised — passing an int would have hit the False branch but no test did.
- **Fix:** Added `test_schemas_reject_non_string_ticker` covering all five schemas with `bad: object = 123`.
- **Files modified:** `tests/ingestion/test_data_schemas.py`
- **Verification:** Coverage rose to 100% line / 100% branch on `analysts.data`.
- **Committed in:** `777ff28`

**3. [Rule 3 - Blocking] Skipped `uv.lock` when staging Task 1 commit**
- **Found during:** Task 1 commit — `git add` warned `uv.lock` is gitignored.
- **Issue:** `.gitignore` includes `uv.lock` (project convention), so `uv sync` rewrote it but it must not be tracked.
- **Fix:** Staged only the files listed in the plan's `<files>` block; left `uv.lock` untracked.
- **Files modified:** none (gitignore observed)
- **Verification:** `git status` shows clean repo after Task 1 commit.
- **Committed in:** `0ffcabf` (no `uv.lock` in commit)

**4. [Rule 2 - Missing Critical] Added 4 extra tests beyond the plan's "~16 tests" estimate**
- **Found during:** Task 3 RED writing — the plan listed 16 schema tests; I wrote 23 to give better coverage of the data_unavailable / round-trip / negative-FCF / bad-CIK / bad-sentiment paths. All extras are happy-path-or-rejection tests (no scope creep). The plan's "~16" estimate was a lower bound — actual count was 22 in the RED commit + 1 added in GREEN = 23.
- **Fix:** None needed — extras are documented in test names and probe-ID comments.
- **Files modified:** `tests/ingestion/test_data_schemas.py`
- **Verification:** All 23 tests green; coverage gates exceeded.
- **Committed in:** `b206206` (RED) + `777ff28` (GREEN, +1 test)

---

**Total deviations:** 4 auto-fixed (1 Rule 1 bug, 2 Rule 2 missing-critical, 1 Rule 3 blocking)
**Impact on plan:** All deviations are tightening, not scope creep. Coverage gates exceeded; full suite green; downstream Wave-2 plans get a strictly better contract surface.

## Issues Encountered

- **`uv` not on PATH**: pre-existing per STATE.md; resolved by prepending `/c/Users/Mohan/AppData/Roaming/Python/Python314/Scripts/` to `PATH` in each `uv` bash call. No code change.
- **`uv.lock` in `.gitignore`**: project convention — sync rewrites it but it stays untracked. Confirmed by `cat .gitignore`. No deviation; just observed.
- **LF→CRLF warnings on `git add`**: Windows line-ending normalization. Cosmetic; harmless. Files commit and check out cleanly.

## Self-Check: PASSED

- [x] `pyproject.toml` exists and contains `yfinance` — FOUND
- [x] `ingestion/http.py` exists — FOUND (76 lines)
- [x] `ingestion/errors.py` exists — FOUND
- [x] `analysts/data/prices.py` exists — FOUND
- [x] `analysts/data/fundamentals.py` exists — FOUND
- [x] `analysts/data/filings.py` exists — FOUND
- [x] `analysts/data/news.py` exists — FOUND
- [x] `analysts/data/social.py` exists — FOUND
- [x] `tests/ingestion/test_http.py` exists — FOUND
- [x] `tests/ingestion/test_errors.py` exists — FOUND
- [x] `tests/ingestion/test_data_schemas.py` exists — FOUND
- [x] Commit `0ffcabf` (Task 1) — FOUND
- [x] Commit `b370d9c` (Task 2 RED) — FOUND
- [x] Commit `b58f932` (Task 2 GREEN) — FOUND
- [x] Commit `b206206` (Task 3 RED) — FOUND
- [x] Commit `777ff28` (Task 3 GREEN) — FOUND
- [x] `uv run pytest tests/ingestion/ -v` — 34/34 green
- [x] `uv run pytest -q` — 69/69 green (full suite)
- [x] `uv run pytest --cov=ingestion --cov=analysts.data --cov-branch tests/ingestion/` — 99% line / >90% branch overall, every file at or above gate
- [x] `uv run python -c "from ingestion.http import get_session; from ingestion.errors import IngestionError, NetworkError, SchemaDriftError; from analysts.data import PriceSnapshot, FundamentalsSnapshot, FilingMetadata, Headline, SocialSignal; print('imports ok')"` — clean

## Next Phase Readiness

- **Wave 2 unblocked**: Plans 02-02 (prices/fundamentals), 02-03 (EDGAR filings), 02-04 (news/RSS), 02-05 (social) can now run in parallel. Every contract they import is landed:
  - `from ingestion.http import get_session, polite_sleep, DEFAULT_TIMEOUT, USER_AGENT`
  - `from ingestion.errors import IngestionError, NetworkError, SchemaDriftError`
  - `from analysts.data import PriceSnapshot, OHLCBar, FundamentalsSnapshot, FilingMetadata, Headline, RedditPost, StockTwitsPost, SocialSignal`
- **Test scaffolding ready**: each Wave-2 plan drops its fixtures into `tests/ingestion/fixtures/` and reads via the session-scoped `fixtures_dir` fixture in `tests/ingestion/conftest.py`.
- **No carry-overs / no blockers**.
- **Probe IDs locked**: 2-W1-01, 2-W1-02, 2-W1-03 satisfied; pairing comments (`# Probe 2-W1-NN`) above each test function in test_http.py / test_errors.py / test_data_schemas.py.

---
*Phase: 02-ingestion-keyless-data-plane*
*Plan: 01-foundation*
*Completed: 2026-05-01*
