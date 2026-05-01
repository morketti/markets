---
phase: 02
phase_name: ingestion-keyless-data-plane
generated: 2026-05-01
generator: orchestrator-yolo (researcher agent socket-dropped at ~9min)
requirements: [DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DATA-07, DATA-08]
---

# Phase 2 Research — Ingestion (Keyless Data Plane)

## Goal Recap

System fetches all needed data for any ticker without API keys, with sanity checks and fallbacks. Output: typed Pydantic objects ready for downstream personas.

## Locked Architecture (from PROJECT.md, do NOT relitigate)

- **Keyless** — `yfinance` + `yahooquery` + SEC EDGAR + RSS only. No API keys ever.
- **Snapshot DB** — ingestion writes JSON snapshots to `snapshots/` in the repo, committed to GitHub. No SQLite, no Postgres.
- **Pydantic v2** — every ingestion module produces validated objects.
- **stdlib-first** — pull in third-party only where stdlib genuinely doesn't suffice.
- **uv** for dep management.

## Data-Source Notes (Pitfall-aware)

### yfinance (DATA-01, DATA-02, DATA-06, DATA-07)

- Use `yfinance.Ticker(symbol)` and access `.history()`, `.info`, `.fast_info`, `.financials`, `.quarterly_financials`, `.balance_sheet`, `.cashflow`.
- **Pitfall #1 — silent breakage**: yfinance scrapes Yahoo's web UI. Yahoo periodically changes its endpoints, returning 200 with empty payloads. **Sanity-check every result**: price > 0, OHLC dict has the expected keys, `.history()` returns a non-empty DataFrame.
- The `info` dict has been deprecated/unstable since 0.2.40+. Prefer `fast_info` for current price, market cap, volume; fall back to `info` only for fundamentals like trailingPE.
- Pin a known-good version in pyproject (`yfinance>=0.2.50,<0.3`) and let renovate/dependabot bump explicitly so silent breakage surfaces as a CI failure, not a user surprise.
- yfinance hits Yahoo via `requests`. Internally it caches per-Ticker but does NOT rate-limit aggressively; for a 50-ticker watchlist run sequentially with `time.sleep(0.2)` between tickers (or use `yfinance.download()` for the bulk-history path).

### yahooquery fallback (DATA-08)

- `yahooquery.Ticker(symbol).price` returns the same shape Yahoo produces server-side for v7 quote endpoint — different code path than yfinance, so when one is broken the other often still works.
- Use it as a strict fallback: only call yahooquery if `_fetch_yfinance(ticker)` returns invalid/empty.
- Beware: yahooquery emits an HTTP request via `requests-futures` and supports async; for our sequential pipeline, use the synchronous form.

### SEC EDGAR (DATA-03)

- **Pitfall #2 — User-Agent compliance**: SEC requires `User-Agent: <name> <email>` per their fair-access policy. Without it, requests get 403'd. Format: `User-Agent: Markets Personal Research (mohanraval15@gmail.com)`.
- Endpoints used:
  - `https://data.sec.gov/submissions/CIK{cik}.json` — recent filings index for a CIK
  - `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=10-K&dateb=&owner=include&count=10` — HTML fallback if JSON CIK lookup fails
  - `https://www.sec.gov/Archives/edgar/data/{cik}/...` — actual filing documents
- Ticker→CIK lookup: `https://www.sec.gov/files/company_tickers.json` (cache locally; refresh weekly).
- Rate limit: 10 requests/sec hard cap. Use `time.sleep(0.11)` between calls or token-bucket via `ratelimit` lib.
- Store filing metadata only (form type, accession number, filed date, URL, summary text). Don't download full 10-K HTML — too heavy. Personas can fetch on demand.

### RSS feeds (DATA-04)

- **Yahoo Finance per-ticker**: `https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US` — still works as of late 2025 / 2026.
- **Google News per-ticker**: `https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en` — query-based, generous limits, no auth.
- **FinViz**: scrape `https://finviz.com/quote.ashx?t={ticker}` — newsroom block is HTML, not RSS. Use `BeautifulSoup` for the news-table div. Be polite (one req per ticker, sleep 0.5s).
- **Press wires** (PR Newswire / Business Wire / GlobeNewswire) — ticker-specific RSS varies by wire. Easier path: rely on Yahoo Finance + Google News, which already syndicate wire releases. Defer dedicated wire feeds to v1.x unless gap-closure needs them.
- Library: `feedparser` is the standard stdlib-adjacent RSS parser. Pin `feedparser>=6.0,<7`.
- **Dedup strategy**: combine source + entry.id (or entry.link if id missing) as primary key; secondary normalize title (lowercase, strip punctuation, take first 80 chars) and dedup on that as well — same story syndicated across sources.
- **Recency sort**: parse entry.published_parsed → datetime; sort desc.

### Reddit RSS + StockTwits (DATA-05)

- **Reddit RSS** (anonymous, no OAuth):
  - Per-subreddit: `https://www.reddit.com/r/wallstreetbets/.rss`, `https://www.reddit.com/r/stocks/.rss`, `https://www.reddit.com/r/investing/.rss`
  - Per-ticker via search: `https://www.reddit.com/search.rss?q={ticker}+OR+%24{ticker}&restrict_sr=on&sort=new&t=day` — but this only restricts to r/all unless we pass subreddit. Better: fan out across the 3-4 main investing subs and dedup.
  - Reddit blocks bots with default UA. Set: `User-Agent: markets/0.1 (by /u/<reddit-handle-if-any>)`. Also a sleep of 2s between calls to avoid 429.
- **StockTwits trending** (unauthenticated): `https://api.stocktwits.com/api/2/trending/symbols.json` — lists currently-trending symbols. Per-ticker: `https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json` returns the latest 30 messages without auth.
  - Anonymous calls have a soft rate cap (~200/hr). Cache trending list for 15 min; per-ticker for 5 min.

## HTTP Client Choice

- **`requests`** for everything. Synchronous, well-known, no async complexity. yfinance and feedparser already pull it transitively.
- **DO NOT** introduce httpx unless we need async (we don't — sequential ingestion of 50 tickers is fine, ~30s per full refresh).

## Pydantic Schema Design (per analyst/schemas pattern)

Suggested module layout — `analysts/data/`:

```
analysts/
  data/
    __init__.py        # re-exports everything
    prices.py          # PriceSnapshot, OHLCBar
    fundamentals.py    # FundamentalsSnapshot
    filings.py         # FilingMetadata
    news.py            # Headline
    social.py          # SocialSignal, RedditPost, StockTwitsPost
```

Or flatter `analysts/data_models.py` if we want to avoid sub-packages. Recommendation: sub-package — each domain has its own validators and quirks (price > 0, filing form_type in {10-K, 10-Q, 8-K, ...}, etc.).

Each model should include:
- `ticker: str` (re-validate via `normalize_ticker` from `analysts.schemas`)
- `fetched_at: datetime` (UTC)
- `source: Literal["yfinance", "yahooquery", "edgar", "yahoo-rss", "google-news", ...]`
- `data_unavailable: bool = False` for the fallback flag (DATA-07)

## Ingestion Module Layout

Suggested package — `ingestion/` (top-level, sibling to `analysts/`, `cli/`, `watchlist/`):

```
ingestion/
  __init__.py
  http.py              # shared requests.Session with EDGAR-compliant UA, retry, timeouts
  prices.py            # fetch_prices(ticker) -> PriceSnapshot | None
  fundamentals.py      # fetch_fundamentals(ticker) -> FundamentalsSnapshot | None
  filings.py           # fetch_filings(ticker, forms=("10-K","10-Q","8-K")) -> list[FilingMetadata]
  news.py              # fetch_news(ticker) -> list[Headline]
  social.py            # fetch_social(ticker) -> SocialSignal
  refresh.py           # run_refresh(watchlist) -> per-ticker snapshot dict; writes JSON
  errors.py            # IngestionError, NetworkError, SchemaDriftError
```

`ingestion/http.py` is the linchpin — single Session with:
- `User-Agent: Markets Personal Research (mohanraval15@gmail.com)` (from config; allow override via env)
- `requests.adapters.HTTPAdapter` with retries=3, backoff_factor=0.3
- 10s timeout default
- Helper `polite_sleep(source: str, last_call: dict)` for per-source rate limiting

## Snapshot Output Layout

Per-ticker JSON file:
```
snapshots/
  {YYYY-MM-DD}/
    {ticker}.json   # all data for one ticker, one snapshot run
  manifest.json     # which tickers in this snapshot, durations, errors
```

Each per-ticker file:
```json
{
  "ticker": "AAPL",
  "fetched_at": "2026-05-01T...",
  "data_unavailable": false,
  "prices": {...},
  "fundamentals": {...},
  "filings": [...],
  "news": [...],
  "social": {...}
}
```

`json.dumps(..., sort_keys=True, indent=2)` — same deterministic-diff convention as `watchlist/loader.py`.

## Caching Strategy

- **Price**: refresh on every run (cheap, fast).
- **Fundamentals**: refresh daily — they don't change intra-day.
- **Filings**: refresh daily — new ones drop infrequently.
- **News**: refresh on every run.
- **Social**: refresh on every run.
- For the MVP refresh routine, cache per-source via simple file mtime check: if `snapshots/.cache/{source}/{ticker}.json` was written within the cadence window, reuse it.
- Defer Redis / SQLite cache to a later phase if perf becomes an issue.

## Test Strategy (Validation Architecture)

This is the make-or-break section — network code is hard to test reliably.

### Sampling / Nyquist

For each ingestion module, lock these probes:
- **Happy path** (1 cassette/fixture per source): real-shape JSON returns the expected Pydantic object.
- **Empty response** (1 fixture): yfinance returns `{}` → module returns `None` and downstream marks `data_unavailable: true`.
- **Malformed JSON** (1 fixture): broken payload → caught, raises `SchemaDriftError`, ticker marked unavailable.
- **HTTP 403** (1 fixture): EDGAR without UA → caught, raises `NetworkError`, run continues.
- **HTTP 429** (1 fixture): rate-limited → retry-with-backoff path exercised.
- **Network timeout** (1 fixture): `requests.exceptions.Timeout` → caught.
- **yfinance fallback path** (1 fixture pair): yfinance empty + yahooquery returns valid → final snapshot has `source: yahooquery`.

### Library Choice

- **`responses`** — best fit. Mocks `requests`-level HTTP. Inline JSON fixtures, no recording-replay magic, no real network. Already a stable, well-maintained lib.
- VCR.py records real responses, but recording from prod APIs is brittle (they change), and recordings get massive. Skip VCR.
- For yfinance specifically: we can mock at the `Ticker` level via `unittest.mock.patch("yfinance.Ticker")` — easier than mocking yfinance's internal HTTP.

### Test Layout

```
tests/
  ingestion/
    fixtures/
      yfinance_aapl_history.json
      yfinance_empty.json
      edgar_submissions_aapl.json
      edgar_403.txt
      yahoo_rss_aapl.xml
      reddit_search_aapl.xml
      stocktwits_aapl.json
    test_http.py              # shared session, UA, retries
    test_prices.py
    test_fundamentals.py
    test_filings.py
    test_news.py              # also tests dedup logic
    test_social.py
    test_refresh.py           # integration: one ticker through the whole pipeline (mocked)
    test_fallback.py          # yfinance fail → yahooquery success path
```

## Plan Decomposition (proposal for gmd-planner)

Suggested 5-6 plans, organized by data-source independence (max parallelism within waves):

| Plan | Scope | Deps |
|------|-------|------|
| 02-01 | `ingestion/http.py` (shared session, UA, retries, polite_sleep) + `ingestion/errors.py` + Pydantic data schemas | none |
| 02-02 | `ingestion/prices.py` + `fundamentals.py` (yfinance + yahooquery fallback) | 02-01 |
| 02-03 | `ingestion/filings.py` (EDGAR — CIK lookup + submissions + form filter) | 02-01 |
| 02-04 | `ingestion/news.py` (Yahoo RSS + Google News + FinViz scrape + dedup + sort) | 02-01 |
| 02-05 | `ingestion/social.py` (Reddit RSS + StockTwits trending + per-symbol stream) | 02-01 |
| 02-06 | `ingestion/refresh.py` orchestrator + `markets refresh` CLI command + snapshot writer + manifest.json | 02-02, 02-03, 02-04, 02-05 |

Waves:
- Wave 1: 02-01
- Wave 2: 02-02, 02-03, 02-04, 02-05 (all independent — parallel)
- Wave 3: 02-06

That gives 4-way parallelism in wave 2 (the bulk of the phase), which fits the user's `parallelization: true` preference.

## Open Decisions for Planner

1. **CIK cache** — store `company_tickers.json` once at package install OR fetch on first run? Recommend: fetch on first run, cache locally in `snapshots/.cache/cik_lookup.json`, refresh weekly.
2. **Filings depth** — metadata-only or also store extracted text? Recommend metadata-only for v1; persona text-extraction in a later phase.
3. **News dedup window** — 24h? 7d? Recommend 7d so a story syndicated across sources within a week dedups.
4. **Refresh CLI ergonomics** — `markets refresh` (whole watchlist) vs `markets refresh AAPL` (single ticker)? Recommend BOTH (positional optional ticker, default to whole watchlist).
5. **Failure visibility** — if 5/50 tickers fail, exit 0 (and surface in manifest.json) or exit nonzero? Recommend exit 0 with manifest.json having an `errors: []` array; the user notices via the badge in the eventual frontend.

## Validation Architecture

(per Nyquist template requirement)

### Coverage Target

- Each ingestion module: ≥90% line coverage, ≥85% branch coverage, gates checked in CI.
- The phase as a whole: every probe in the Sampling table above is exercised by exactly one named test (probe-ID like 2-W2-01 etc., assigned by planner).

### Probes (one per failure mode × data source)

| Probe ID | Source | Failure mode | What we assert |
|----------|--------|-------------|----------------|
| 2-W1-01 | http session | UA header present | Real request fixture inspects headers |
| 2-W1-02 | http session | Retry on 503 | responses lib returns 503 then 200; final state ok |
| 2-W1-03 | errors | Custom exceptions | inheritance from Exception, subclass tree |
| 2-W2-01 | yfinance prices | Happy path | Ticker.history → PriceSnapshot, sanity passes |
| 2-W2-02 | yfinance prices | Empty path | empty df → None, fallback triggers |
| 2-W2-03 | yahooquery prices | Fallback success | yfinance None → yahooquery returns data → source="yahooquery" |
| 2-W2-04 | yfinance fundamentals | Happy path | info dict → FundamentalsSnapshot |
| 2-W2-05 | yfinance fundamentals | Missing keys | KeyError → data_unavailable: true |
| 2-W2-06 | EDGAR | Happy path | submissions JSON → FilingMetadata list |
| 2-W2-07 | EDGAR | 403 | missing UA → SchemaDriftError? no, NetworkError, continues |
| 2-W2-08 | EDGAR | Rate limit retry | 429 once → backoff → 200 |
| 2-W2-09 | RSS Yahoo | Happy path | XML fixture → list[Headline] |
| 2-W2-10 | RSS Google | Happy path | XML fixture → list[Headline] |
| 2-W2-11 | RSS dedup | Two sources, same story | dedup leaves 1 |
| 2-W2-12 | RSS sort | Out-of-order entries | result is recency-desc |
| 2-W2-13 | FinViz scrape | Happy path | HTML fixture → list[Headline] |
| 2-W2-14 | Reddit RSS | Happy path | XML fixture → posts |
| 2-W2-15 | StockTwits | Trending | JSON fixture → list[ticker] |
| 2-W2-16 | StockTwits | Per-symbol | JSON fixture → list[message] |
| 2-W3-01 | refresh | Whole watchlist | 3-ticker watchlist → 3 snapshot files written |
| 2-W3-02 | refresh | One bad ticker | 1 of 3 fails → manifest.errors has one entry, other two complete |
| 2-W3-03 | manifest | Schema | manifest.json validates against ManifestSchema |
| 2-W3-04 | snapshot serialization | Determinism | running refresh twice with same fixtures produces byte-identical JSON |

### Offline Discipline

- **Zero network calls in the test suite.** Every test mocks at the `responses` layer (or `unittest.mock.patch` for yfinance/yahooquery objects).
- A real-network smoke script may live at `scripts/smoke_ingest.py` but is NOT wired into pytest. It's manually run by the human to confirm prod APIs still work.

## Open Questions / Things Planner Should Resolve

- Should `Snapshot` be a single Pydantic model that aggregates all sub-models, or just a raw dict that each ingestion module writes its key into? Recommendation: aggregate Pydantic model, validated at write time (defense-in-depth same pattern as Watchlist).
- Where does the run_refresh entry point go — `cli/refresh.py` (consistent with add/remove/list/show) or `ingestion/refresh.py` (logic) + `cli/refresh.py` (thin shim)? Recommend the latter — keep CLI thin.
- yfinance is heavy in deps (pandas, numpy). Pin and hope; if a future phase needs to slim this, the IngestionModule abstraction allows swapping yfinance for a slimmer alt.

## Recommended pyproject.toml additions

```toml
dependencies = [
  "pydantic>=2.13",
  "yfinance>=0.2.50,<0.3",
  "yahooquery>=2.3,<3",
  "requests>=2.31,<3",
  "feedparser>=6.0,<7",
  "beautifulsoup4>=4.12,<5",
]

[dependency-groups]
dev = [
  "pytest>=9.0",
  "pytest-cov>=7.0",
  "responses>=0.25",   # mock requests for ingestion tests
  "ruff>=0.15",
]
```

## Done — handing off to planner.

The planner should produce 6 plans across 3 waves matching the decomposition table. Use `responses` library for HTTP mocking. `analysts/data/` package for schemas. `ingestion/` package for fetch logic. `markets refresh` CLI subcommand for orchestration. Snapshots write to `snapshots/{YYYY-MM-DD}/{ticker}.json` with `manifest.json` per run.
