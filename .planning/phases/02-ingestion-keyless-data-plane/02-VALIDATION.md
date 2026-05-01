---
phase: 02
slug: ingestion-keyless-data-plane
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-01
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + pytest-cov 7.x |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest -x -q` |
| **Full suite command** | `uv run pytest --cov=analysts --cov=watchlist --cov=cli --cov=ingestion --cov-branch` |
| **Estimated runtime** | ~3 seconds (35 existing + ~25 new = ~60 tests, all offline-mocked) |

Wave 0 installs: `responses>=0.25` (HTTP mocking lib for ingestion tests). Existing pyproject.toml needs an entry under `[dependency-groups].dev`.

---

## Sampling Rate

- **After every task commit:** `uv run pytest -x -q`
- **After every plan wave:** Full suite + coverage gates
- **Before `/gmd:verify-work`:** Full suite must be green; coverage ≥90% on `ingestion/` module-by-module
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-W1-01 | 02-01 | 1 | DATA-06 (HTTP UA + retries) | unit | `uv run pytest tests/ingestion/test_http.py -v` | ❌ W0 | ⬜ pending |
| 2-W1-02 | 02-01 | 1 | DATA-06 (errors module) | unit | `uv run pytest tests/ingestion/test_errors.py -v` | ❌ W0 | ⬜ pending |
| 2-W1-03 | 02-01 | 1 | DATA-06 (Pydantic data schemas) | unit | `uv run pytest tests/ingestion/test_data_schemas.py -v` | ❌ W0 | ⬜ pending |
| 2-W2-01 | 02-02 | 2 | DATA-01 (yfinance prices happy) | unit | `uv run pytest tests/ingestion/test_prices.py::test_prices_happy -v` | ❌ W0 | ⬜ pending |
| 2-W2-02 | 02-02 | 2 | DATA-07 (yfinance empty → unavailable) | unit | `uv run pytest tests/ingestion/test_prices.py::test_prices_empty -v` | ❌ W0 | ⬜ pending |
| 2-W2-03 | 02-02 | 2 | DATA-08 (yahooquery fallback) | unit | `uv run pytest tests/ingestion/test_fallback.py -v` | ❌ W0 | ⬜ pending |
| 2-W2-04 | 02-02 | 2 | DATA-02 (fundamentals happy) | unit | `uv run pytest tests/ingestion/test_fundamentals.py::test_fund_happy -v` | ❌ W0 | ⬜ pending |
| 2-W2-05 | 02-02 | 2 | DATA-06 (fundamentals missing keys) | unit | `uv run pytest tests/ingestion/test_fundamentals.py::test_fund_missing -v` | ❌ W0 | ⬜ pending |
| 2-W2-06 | 02-03 | 2 | DATA-03 (EDGAR happy) | unit | `uv run pytest tests/ingestion/test_filings.py::test_filings_happy -v` | ❌ W0 | ⬜ pending |
| 2-W2-07 | 02-03 | 2 | DATA-03 (EDGAR 403 without UA) | unit | `uv run pytest tests/ingestion/test_filings.py::test_filings_403 -v` | ❌ W0 | ⬜ pending |
| 2-W2-08 | 02-03 | 2 | DATA-03 (EDGAR 429 retry) | unit | `uv run pytest tests/ingestion/test_filings.py::test_filings_429 -v` | ❌ W0 | ⬜ pending |
| 2-W2-09 | 02-04 | 2 | DATA-04 (Yahoo RSS parse) | unit | `uv run pytest tests/ingestion/test_news.py::test_yahoo_rss -v` | ❌ W0 | ⬜ pending |
| 2-W2-10 | 02-04 | 2 | DATA-04 (Google News parse) | unit | `uv run pytest tests/ingestion/test_news.py::test_google_news -v` | ❌ W0 | ⬜ pending |
| 2-W2-11 | 02-04 | 2 | DATA-04 (cross-source dedup) | unit | `uv run pytest tests/ingestion/test_news.py::test_dedup -v` | ❌ W0 | ⬜ pending |
| 2-W2-12 | 02-04 | 2 | DATA-04 (recency sort) | unit | `uv run pytest tests/ingestion/test_news.py::test_sort -v` | ❌ W0 | ⬜ pending |
| 2-W2-13 | 02-04 | 2 | DATA-04 (FinViz scrape) | unit | `uv run pytest tests/ingestion/test_news.py::test_finviz -v` | ❌ W0 | ⬜ pending |
| 2-W2-14 | 02-05 | 2 | DATA-05 (Reddit RSS parse) | unit | `uv run pytest tests/ingestion/test_social.py::test_reddit -v` | ❌ W0 | ⬜ pending |
| 2-W2-15 | 02-05 | 2 | DATA-05 (StockTwits trending) | unit | `uv run pytest tests/ingestion/test_social.py::test_trending -v` | ❌ W0 | ⬜ pending |
| 2-W2-16 | 02-05 | 2 | DATA-05 (StockTwits per-symbol) | unit | `uv run pytest tests/ingestion/test_social.py::test_per_symbol -v` | ❌ W0 | ⬜ pending |
| 2-W3-01 | 02-06 | 3 | (integration) refresh whole watchlist | integration | `uv run pytest tests/ingestion/test_refresh.py::test_full_refresh -v` | ❌ W0 | ⬜ pending |
| 2-W3-02 | 02-06 | 3 | DATA-07 (one bad ticker continues) | integration | `uv run pytest tests/ingestion/test_refresh.py::test_partial_failure -v` | ❌ W0 | ⬜ pending |
| 2-W3-03 | 02-06 | 3 | (manifest) schema validation | integration | `uv run pytest tests/ingestion/test_refresh.py::test_manifest -v` | ❌ W0 | ⬜ pending |
| 2-W3-04 | 02-06 | 3 | (snapshot) byte-identical determinism | integration | `uv run pytest tests/ingestion/test_refresh.py::test_determinism -v` | ❌ W0 | ⬜ pending |
| 2-W3-05 | 02-06 | 3 | (CLI) `markets refresh` end-to-end | unit | `uv run pytest tests/test_cli_refresh.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/ingestion/__init__.py` — package marker
- [ ] `tests/ingestion/fixtures/` — recorded JSON / XML / HTML fixtures (committed to repo, deterministic)
- [ ] `responses>=0.25` added to `[dependency-groups].dev` in pyproject.toml
- [ ] Fixture files for: yfinance happy, yfinance empty, yahooquery fallback, edgar submissions, edgar 403, edgar 429, yahoo RSS, google news RSS, finviz HTML, reddit RSS, stocktwits trending, stocktwits per-symbol

These are created lazily inside Plan 02-01 (the foundation plan). Plans 02-02 through 02-05 each contribute their own fixtures.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real-network smoke | All DATA-* | Live APIs evolve; recorded fixtures only confirm code shape | Run `uv run python scripts/smoke_ingest.py AAPL` after merging phase 2; expect a snapshot file with non-zero counts in news / filings / social |
| EDGAR 403 in prod | DATA-03 | Cannot reproduce real SEC 403 in tests; only mocked | Manually run smoke without UA env override; expect a NetworkError in logs |

The smoke script is NOT pytest-collected. It's a manual confirmation that prod APIs still work after a phase-2 ship.

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter (set by planner once plans cover every probe)

**Approval:** pending
