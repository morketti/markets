---
phase: 02-ingestion-keyless-data-plane
plan: 05
subsystem: ingestion
tags: [social, reddit-rss, stocktwits, feedparser, responses, anonymous, tdd]

# Dependency graph
requires:
  - phase: 02-ingestion-keyless-data-plane
    plan: 01
    provides: ingestion.http.get_session (process-shared session), DEFAULT_TIMEOUT, analysts.data.social.{RedditPost, StockTwitsPost, SocialSignal}, analysts.schemas.normalize_ticker
provides:
  - ingestion.social.fetch_social (per-ticker SocialSignal aggregating Reddit RSS + StockTwits trending + per-symbol stream)
  - ingestion.social.{_fetch_reddit_search, _fetch_stocktwits_trending, _fetch_stocktwits_stream} (test-friendly internal seams)
  - ingestion.social.{REDDIT_SEARCH_URL, REDDIT_USER_AGENT, STOCKTWITS_TRENDING_URL, STOCKTWITS_STREAM_URL} (URL templates + dedicated Reddit UA)
affects: [02-06-refresh-orchestrator]

# Tech tracking
tech-stack:
  added: []   # all deps were locked in Plan 02-01 (feedparser, requests, responses already in pyproject)
  patterns:
    - "Per-request UA override on shared session (`session.get(url, headers={'User-Agent': REDDIT_USER_AGENT})`) — replaces shared session UA for THIS call only, leaves other ingestion modules unaffected"
    - "Per-source failure isolation: each `_fetch_*` returns [] on any failure; aggregator only sets `data_unavailable=True` when ALL sources empty AND ticker absent from trending"
    - "URL-template + responses-lib pattern: tests recreate the URL the implementation will hit via `.format(...)` so responses.add() matches exactly without duplicating the URL string"
    - "Sentiment whitelist normalization: defensive against StockTwits ever introducing novel sentiment values — anything outside {bullish, bearish} → None"
    - "Probe-ID test naming: test_reddit / test_trending / test_per_symbol map mechanically to VALIDATION.md probes 2-W2-14 / 2-W2-15 / 2-W2-16"

key-files:
  created:
    - ingestion/social.py
    - tests/ingestion/test_social.py
    - tests/ingestion/fixtures/reddit_search_aapl.xml
    - tests/ingestion/fixtures/stocktwits_trending.json
    - tests/ingestion/fixtures/stocktwits_aapl.json
  modified: []

key-decisions:
  - "REDDIT_USER_AGENT = 'markets/0.1 (anonymous research aggregator)' (descriptive, non-impersonating, no Reddit handle since we publish anonymously) — applied via per-request `headers=` kwarg so the shared session's EDGAR UA is preserved for other modules"
  - "Reddit subreddit extraction: primary path is regex `/r/([^/]+)/` against the entry's link; fallback is feedparser's `entry.tags[0].term` (Atom <category term=>) when the link doesn't carry the subreddit. Entries with neither are dropped (rather than guessed)"
  - "StockTwits sentiment normalization is whitelisted: `entities.sentiment.basic` ∈ {Bullish, Bearish} → lowercase Literal value; any other shape (novel value, null, missing, non-string) → None. This survives StockTwits adding 'Neutral' or similar without breaking the schema"
  - "_fetch_* functions return [] on ANY failure (HTTP-layer exception, non-200, non-JSON body, malformed payload). The aggregator decides `data_unavailable` by inspecting the three results — never by catching exceptions itself"
  - "Trending rank is 1-based position in the StockTwits trending list (matches user expectation: 'AAPL is #2 trending'). None when the ticker isn't in the list — even if the trending list itself fetched successfully"
  - "Invalid ticker input returns SocialSignal(ticker='INVALID', data_unavailable=True) without any HTTP calls — sentinel form that round-trips through Pydantic. Mirrors the `prices.py` pattern (Plan 02-02) for invalid-input handling"
  - "Defensive `except Exception` blocks around feedparser.parse() and Pydantic construction — feedparser is lenient but a single malformed entry must not poison the whole list. # noqa: BLE001 acknowledges the broad catch; logger.warning preserves audit trail"

patterns-established:
  - "Per-request header override for vendor-quirky UAs: shared session keeps the EDGAR-compliant UA; modules that need a different UA (Reddit) pass `headers={...}` per-call. Future plans hitting another UA-strict vendor (e.g. Twitter API v2) follow the same pattern."
  - "Aggregator+isolated-fetcher decomposition: top-level `fetch_social` decides combined behavior; `_fetch_reddit_search` / `_fetch_stocktwits_*` are independent and side-effect-isolated. Plan 02-06 orchestrator can mock at either level."
  - "Probe-ID test naming convention reaffirmed (test_reddit / test_trending / test_per_symbol) — verifier mechanically pairs tests with VALIDATION.md."

requirements-completed: [DATA-05]

# Metrics
duration: 5min
completed: 2026-05-01
---

# Phase 02 Plan 05: Social Ingestion Summary

**Anonymous social-signal fetch landing fetch_social(ticker) -> SocialSignal that aggregates Reddit search.rss across r/wallstreetbets+r/stocks+r/investing plus StockTwits trending + per-symbol stream — with Reddit per-call UA override and per-source failure isolation so a single upstream going dark never fails the whole signal.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-01T12:00:37Z
- **Completed:** 2026-05-01T12:05:12Z
- **Tasks:** 1 (auto, TDD: RED + GREEN)
- **Files created:** 5 (1 production module + 1 test file + 3 fixtures)
- **Files modified:** 0

## Accomplishments

- `ingestion/social.py` (334 lines) ships `fetch_social(ticker) -> SocialSignal` aggregating three anonymous endpoints:
  - **Reddit:** `https://www.reddit.com/search.rss?q={query}&sort=new&t=day` with `query = quote(f"{ticker} OR ${ticker}")` so cashtag and bare-ticker forms both match. Per-call header override sends `REDDIT_USER_AGENT="markets/0.1 (anonymous research aggregator)"` instead of the shared session's EDGAR UA (Pitfall #2). feedparser parses the Atom XML; subreddit is extracted from the entry's link via `/r/([^/]+)/` regex with a `<category term=>` fallback.
  - **StockTwits trending:** `https://api.stocktwits.com/api/2/trending/symbols.json` returns the global trending list; we extract `[s["symbol"].upper() for s in payload["symbols"]]` in fixture order so 1-based `trending_rank` is meaningful.
  - **StockTwits per-symbol:** `https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json` returns the latest 30 messages. We normalize `entities.sentiment.basic` to lowercase `"bullish"`/`"bearish"` (or `None` for any other shape) and slice `body` to 2000 chars (schema cap).
- **Per-source failure isolation:** any `_fetch_*` returns `[]` on HTTP-layer exception, non-200, non-JSON body, or malformed payload. `fetch_social` then sets `data_unavailable=True` ONLY when ALL three queries are empty AND the ticker is absent from trending — a partial outage on Reddit alone (or StockTwits alone) leaves the SocialSignal usable.
- **26 tests green** covering all three probes (2-W2-14, 2-W2-15, 2-W2-16) plus retry-exhaustion paths, malformed-body paths, partial-failure aggregation, invalid-ticker short-circuit, defensive Pydantic-rejection paths, and the long-title truncation behavior.
- **Coverage:** `ingestion/social.py` at **94% line / 96% branch** (gate ≥90% line / ≥85% branch). The remaining 11 missed lines are deeply defensive `except Exception` warning-log paths that would require monkeypatching `feedparser.parse` itself to exercise — over-fitting territory, not closed.
- **Plan-scoped suite:** `tests/ingestion/` 120/120 green — runs alongside Plan 02-04 (news) without collision (parallel-safety constraint observed).

## Task Commits

1. **Task 1 RED — failing tests for social signal aggregation:** `8ed1a9c` — 14 initial tests + 3 fixtures
2. **Task 1 GREEN — implement fetch_social + 11 coverage-completing tests:** `284c168` — `ingestion/social.py` + 11 additional tests for defensive paths

**Plan metadata commit:** added in the wrap-up step (covers SUMMARY.md, STATE.md, ROADMAP.md, REQUIREMENTS.md).

## Files Created/Modified

### Created
- `ingestion/social.py` (334 lines) — `fetch_social` + 3 internal seams + 4 module constants
- `tests/ingestion/test_social.py` (609 lines) — 26 tests (15 plan-required + 11 coverage-completing)
- `tests/ingestion/fixtures/reddit_search_aapl.xml` — 6-entry Atom feed across r/wallstreetbets, r/stocks, r/investing
- `tests/ingestion/fixtures/stocktwits_trending.json` — 5-symbol trending list (TSLA, AAPL, NVDA, GME, AMC)
- `tests/ingestion/fixtures/stocktwits_aapl.json` — 30-message stream with mixed Bullish/Bearish/null sentiment

### Modified
- _none_ — parallel-safety honored: only my plan's `files_modified` were touched. `pyproject.toml`, `ingestion/http.py`, `analysts/data/social.py`, etc. were left alone.

## Decisions Made

- **`REDDIT_USER_AGENT = "markets/0.1 (anonymous research aggregator)"`** — descriptive, non-impersonating, no Reddit handle (we publish anonymously per the project's keyless discipline). Applied via per-request `headers={...}` on `session.get()` so the shared session's EDGAR UA is preserved for other modules. requests merges request headers with session defaults; this override is scoped to the single call.
- **Subreddit extraction is two-tier** — primary regex `/r/([^/]+)/` against the entry link, fallback to `entry.tags[0].term` (Atom `<category term=>`). Entries that resolve neither are dropped silently (logged at INFO via the empty-loop), matching the "lenient parsing, strict output" pattern from the news.py / filings.py contracts.
- **Sentiment whitelist** — only `{"Bullish", "Bearish"}` lowercase to `{"bullish", "bearish"}`. Any other shape (novel value like "Neutral", non-dict `entities.sentiment`, non-string `basic`) becomes `None`. The whitelist survives StockTwits adding new sentiment classes without us cascading into a Pydantic ValidationError.
- **Trending rank is 1-based** — matches user-facing language ("AAPL is #2 trending"). The plan's interface block specified `index+1`; honored exactly.
- **Invalid ticker → sentinel SocialSignal** — `SocialSignal(ticker="INVALID", data_unavailable=True)` with empty collections, no HTTP calls. Mirrors Plan 02-02's `_unavailable("INVALID")` pattern in `prices.py`. Plan 02-06 orchestrator gets a uniform shape for "we tried, nothing came back" regardless of upstream availability.
- **`fetch_social` does NOT catch its own exceptions** — only the `_fetch_*` helpers swallow upstream weather. The aggregator's only branching is on the lengths of the returned lists and `ticker in trending`. This keeps the failure-isolation policy in one place (the helpers) and makes `fetch_social` itself trivially auditable.
- **Long-title behavior is truncate-not-reject** — `title[:500]` slices to the schema cap. Reddit titles routinely run long when users paste full headlines; rejecting the entry would lose information. (Plan locked schema cap at 500 chars; implementation respects it without dropping the post.)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added 11 coverage-completing tests beyond the plan's "~10"**
- **Found during:** Task 1 GREEN — initial 15 plan-listed tests gave 71% line / partial-branch coverage on `ingestion/social.py`, below the ≥90% line gate.
- **Issue:** The plan listed ~10 happy/sad path tests but didn't enumerate defensive paths (HTTP-layer exception via monkeypatch, non-dict top-level JSON, malformed-message dropping, subreddit-fallback to `<category>`, non-http link rejection, long-title truncation, `_parse_iso8601` bad-input cases).
- **Fix:** Added 11 targeted tests: `test_reddit_http_layer_exception`, `test_stocktwits_trending_http_layer_exception`, `test_stocktwits_stream_http_layer_exception`, `test_stocktwits_stream_malformed_json`, `test_stocktwits_trending_top_level_not_dict`, `test_stocktwits_trending_drops_malformed_entries`, `test_stocktwits_stream_top_level_not_dict`, `test_stocktwits_stream_drops_malformed_messages`, `test_reddit_drops_entries_without_subreddit_or_link`, `test_reddit_long_title_truncated_not_rejected`, `test_parse_iso8601_handles_bad_input`.
- **Files modified:** `tests/ingestion/test_social.py` (only; production module unchanged after RED-driven implementation).
- **Verification:** Coverage rose from 71% → 94% line / 96% branch — both gates exceeded.
- **Committed in:** `284c168` (GREEN — single commit covering implementation + coverage tests, since they're both part of "make GREEN pass at gate").

**2. [Rule 2 - Missing Critical] Added `test_reddit_malformed_xml_returns_empty` to lock the malformed-body contract**
- **Found during:** Task 1 RED writing — the plan listed retry-exhaustion (`test_reddit_429_returns_empty`) but not malformed-XML behavior. feedparser is famously lenient and will silently produce an empty entries list on garbage; without this test, a future contributor might add `raise` to the parse failure path and break the contract.
- **Fix:** Added `test_reddit_malformed_xml_returns_empty` asserting `[]` on `<not><valid></xml`.
- **Verification:** Test green; locks the "feedparser garbage in, [] out, no exception" contract.
- **Committed in:** `8ed1a9c` (RED).

---

**Total deviations:** 2 auto-fixed (both Rule 2 — missing-critical tests added to clear coverage gate / lock contracts).
**Impact:** Tightening only. Production code matches the plan's specification 1:1; the additions are all in test_social.py and were necessary to clear the ≥90% line / ≥85% branch gate the plan itself requires.

## Issues Encountered

- **`uv` PATH carry-over from STATE.md:** prepended `/c/Users/Mohan/AppData/Roaming/Python/Python314/Scripts:` to `PATH` in each `uv run` call, identical to Plans 02-01..02-04. No code change.
- **LF→CRLF warnings on `git add`:** Windows line-ending normalization. Cosmetic; harmless.
- **Parallel-safety with 02-04:** the running 02-04 plan had `ingestion/news.py` untracked at the start of execution and dropped the `tests/ingestion/test_news.py` RED commit before mine. I staged ONLY my files (`tests/ingestion/test_social.py`, `tests/ingestion/fixtures/reddit_*.xml`, `tests/ingestion/fixtures/stocktwits_*.json`, `ingestion/social.py`) and never `git add .` / `git add -A`. No collision; 02-04's working-tree changes remained untouched.

## Self-Check: PASSED

- [x] `ingestion/social.py` exists — FOUND (334 lines)
- [x] `tests/ingestion/test_social.py` exists — FOUND (609 lines)
- [x] `tests/ingestion/fixtures/reddit_search_aapl.xml` exists — FOUND (6 entries)
- [x] `tests/ingestion/fixtures/stocktwits_trending.json` exists — FOUND (5 symbols)
- [x] `tests/ingestion/fixtures/stocktwits_aapl.json` exists — FOUND (30 messages)
- [x] Commit `8ed1a9c` (RED) — FOUND
- [x] Commit `284c168` (GREEN) — FOUND
- [x] `uv run pytest tests/ingestion/test_social.py -v` — 26/26 green
- [x] `uv run pytest tests/ingestion/ -v` — 120/120 green (plan-scoped + parallel-running 02-04 + Wave 1)
- [x] `uv run pytest --cov=ingestion.social --cov-branch tests/ingestion/test_social.py` — 94% line / 96% branch (both gates cleared)
- [x] Probe coverage:
  - 2-W2-14 → `test_reddit` + `test_reddit_user_agent_is_non_default` ✓
  - 2-W2-15 → `test_trending` ✓
  - 2-W2-16 → `test_per_symbol` ✓
- [x] Anonymous discipline: no API keys, no OAuth tokens, no auth headers in any code path ✓
- [x] Reddit per-call UA override verified at the responses-lib boundary (`responses.calls[0].request.headers["User-Agent"] == REDDIT_USER_AGENT`) ✓

## Next Phase Readiness

- **Plan 02-06 (refresh orchestrator) unblocked from this side:** `from ingestion.social import fetch_social` is now a valid import returning a `SocialSignal` with the locked contract from Plan 02-01's schemas. The orchestrator can call it per-ticker, expect it to ALWAYS return (never raise), and treat `sig.data_unavailable=True` as "all three social sources down — surface in manifest.errors but keep the run moving".
- **Wave 2 status:** This plan + 02-04 (news) are the two parallel-execution plans for the social/news sources. With both green, Wave 2 is fully complete (02-02 prices, 02-03 filings, 02-04 news, 02-05 social).
- **No carry-overs / no blockers from this plan.**
- **DATA-05 marked complete in REQUIREMENTS.md** via the `requirements mark-complete` step.

---
*Phase: 02-ingestion-keyless-data-plane*
*Plan: 05-social*
*Completed: 2026-05-01*
