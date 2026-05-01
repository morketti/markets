---
phase: 02-ingestion-keyless-data-plane
plan: 05
type: tdd
wave: 2
depends_on: [02-01]
files_modified:
  - ingestion/social.py
  - tests/ingestion/test_social.py
  - tests/ingestion/fixtures/reddit_search_aapl.xml
  - tests/ingestion/fixtures/stocktwits_trending.json
  - tests/ingestion/fixtures/stocktwits_aapl.json
autonomous: true
requirements: [DATA-05]
must_haves:
  truths:
    - "fetch_social(ticker) returns a SocialSignal aggregating Reddit RSS posts and StockTwits per-symbol stream"
    - "Reddit RSS calls send a non-default User-Agent (per Pitfall #2 / RESEARCH.md — Reddit blocks default UA)"
    - "StockTwits trending list is fetched separately and the ticker's trending_rank is set when present in the trending response"
    - "All access is anonymous — no OAuth tokens, no API keys"
    - "Per-source failure (Reddit 429, StockTwits empty) marks that source's collection as empty but does NOT fail the whole call"
  artifacts:
    - path: "ingestion/social.py"
      provides: "fetch_social(ticker) -> SocialSignal aggregating Reddit + StockTwits"
      min_lines: 70
    - path: "tests/ingestion/test_social.py"
      provides: "Probes 2-W2-14 (reddit), 2-W2-15 (stocktwits trending), 2-W2-16 (stocktwits per-symbol)"
      min_lines: 60
    - path: "tests/ingestion/fixtures/reddit_search_aapl.xml"
      provides: "Real-shape Reddit search RSS for AAPL with 5+ posts across r/wallstreetbets and r/stocks"
    - path: "tests/ingestion/fixtures/stocktwits_trending.json"
      provides: "Real-shape /api/2/trending/symbols.json response"
    - path: "tests/ingestion/fixtures/stocktwits_aapl.json"
      provides: "Real-shape /api/2/streams/symbol/AAPL.json response with 30 messages"
  key_links:
    - from: "ingestion/social.py"
      to: "ingestion.http.get_session()"
      via: "shared session for both Reddit + StockTwits"
      pattern: "get_session\\(\\)"
    - from: "ingestion/social.py"
      to: "feedparser.parse"
      via: "Reddit RSS XML parsing"
      pattern: "feedparser.parse"
    - from: "ingestion/social.py"
      to: "analysts.data.SocialSignal"
      via: "Pydantic validation"
      pattern: "SocialSignal\\("
---

<objective>
Wave 2 / Source D: anonymous social-signal ingestion. Fetches per-ticker posts from Reddit (RSS search across r/wallstreetbets, r/stocks, r/investing) and StockTwits (trending + per-symbol stream — no OAuth). Implements DATA-05 in full.

Purpose: Social is the only source family with two genuinely different upstream protocols (RSS vs JSON API) and two different rate-limit regimes (Reddit's bot-blocker vs StockTwits' soft 200/hr cap). Bundling them keeps the "no auth tokens, anonymous endpoints only" discipline in one mental model and one test file.

Output: ingestion/social.py with `fetch_social(ticker) -> SocialSignal`. Three probes covered (Reddit RSS happy, StockTwits trending, StockTwits per-symbol stream). Three fixture files.
</objective>

<execution_context>
@C:/Users/Mohan/.claude/workflows/execute-plan.md
@C:/Users/Mohan/.claude/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/02-ingestion-keyless-data-plane/02-RESEARCH.md
@.planning/phases/02-ingestion-keyless-data-plane/02-VALIDATION.md
@.planning/phases/02-ingestion-keyless-data-plane/02-01-SUMMARY.md

@analysts/schemas.py

<interfaces>
<!-- Wave 1 contracts this plan consumes -->

From ingestion/http.py:
```python
def get_session() -> requests.Session
DEFAULT_TIMEOUT: float = 10.0
def polite_sleep(source: str, last_call: dict, min_interval: float) -> None
```

From analysts/data/social.py:
```python
class RedditPost(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    url: str
    subreddit: str
    published_at: Optional[datetime] = None
    score: Optional[int] = None

class StockTwitsPost(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    created_at: Optional[datetime] = None
    sentiment: Optional[Literal["bullish", "bearish"]] = None

class SocialSignal(BaseModel):
    ticker: str
    fetched_at: datetime
    source: Literal["reddit-rss", "stocktwits", "combined"] = "combined"
    data_unavailable: bool = False
    reddit_posts: list[RedditPost] = []
    stocktwits_posts: list[StockTwitsPost] = []
    trending_rank: Optional[int] = None
```

NEW contracts this plan creates:

ingestion/social.py:
```python
REDDIT_SEARCH_URL = "https://www.reddit.com/search.rss?q={query}&sort=new&t=day"
REDDIT_USER_AGENT = "markets/0.1 (anonymous research aggregator)"
STOCKTWITS_TRENDING_URL = "https://api.stocktwits.com/api/2/trending/symbols.json"
STOCKTWITS_STREAM_URL = "https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"

def fetch_social(ticker: str) -> SocialSignal:
    """Fetch per-ticker social signal from Reddit RSS + StockTwits.
    Returns combined SocialSignal. Per-source failure marks that source's
    collection empty but does NOT fail the whole call. Sets data_unavailable
    only when ALL sources fail."""

# Internal seams (test-friendly):
def _fetch_reddit_search(ticker: str) -> list[RedditPost]
def _fetch_stocktwits_trending() -> list[str]  # ticker symbols, lowercased
def _fetch_stocktwits_stream(ticker: str) -> list[StockTwitsPost]
```

StockTwits per-symbol JSON shape:
```json
{
  "response": {"status": 200},
  "symbol": {"symbol": "AAPL", "title": "Apple Inc"},
  "cursor": {...},
  "messages": [
    {
      "id": 99999,
      "body": "AAPL looks strong heading into earnings",
      "created_at": "2026-04-30T13:15:00Z",
      "user": {...},
      "entities": {"sentiment": {"basic": "Bullish"}}
    },
    ...
  ]
}
```

StockTwits trending JSON shape:
```json
{
  "response": {"status": 200},
  "symbols": [
    {"symbol": "TSLA", "title": "Tesla", "id": 8849, "watchlist_count": 1500000},
    {"symbol": "AAPL", "title": "Apple Inc", ...},
    ...
  ]
}
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: TDD ingestion/social.py — Reddit RSS + StockTwits trending + StockTwits per-symbol</name>
  <files>tests/ingestion/test_social.py, tests/ingestion/fixtures/reddit_search_aapl.xml, tests/ingestion/fixtures/stocktwits_trending.json, tests/ingestion/fixtures/stocktwits_aapl.json, ingestion/social.py</files>
  <behavior>
    Probes 2-W2-14 (Reddit RSS), 2-W2-15 (StockTwits trending), 2-W2-16 (StockTwits per-symbol).

    test_social.py:
    - test_reddit (probe 2-W2-14): patch via responses lib OR pass fixture path to feedparser. Use `responses.add(responses.GET, REDDIT_SEARCH_URL.format(query="AAPL+OR+%24AAPL"), body=fixture_path.read_text(), status=200, content_type="application/atom+xml")`. Assert: `_fetch_reddit_search("AAPL")` returns list[RedditPost] of length ≥ 5; each post has title non-empty, url starts with "https://", subreddit non-empty (parsed from the entry's source or from the URL path).
    - test_reddit_user_agent_is_non_default (probe 2-W2-14 variant): make a request with responses; capture `responses.calls[0].request.headers["User-Agent"]`; assert it is `REDDIT_USER_AGENT` exactly (NOT the EDGAR UA — Reddit gets its own). Note: this requires the implementation to OVERRIDE the session UA per-request, since the shared session has the EDGAR UA. Implementation will pass `headers={"User-Agent": REDDIT_USER_AGENT}` to the .get() call.
    - test_reddit_429_returns_empty: responses returns 429 (after retries are exhausted). Assert: `_fetch_reddit_search("AAPL")` returns []. (Note: shared session has retry on 429, so we register 4 consecutive 429s.)
    - test_trending (probe 2-W2-15): mock STOCKTWITS_TRENDING_URL with `stocktwits_trending.json`. Assert: `_fetch_stocktwits_trending()` returns list[str] like ["TSLA", "AAPL", ...] (uppercase symbols), length matches fixture.
    - test_trending_failure_returns_empty: mock 500 response. Assert: returns [].
    - test_per_symbol (probe 2-W2-16): mock STOCKTWITS_STREAM_URL.format(ticker="AAPL") with `stocktwits_aapl.json`. Assert: `_fetch_stocktwits_stream("AAPL")` returns list[StockTwitsPost] of length 30; each has body non-empty; sentiment populated for posts with `entities.sentiment.basic == "Bullish"` → "bullish" (lowercase normalized).
    - test_per_symbol_no_messages: mock to return `{"response": {"status": 200}, "messages": []}`. Assert: returns [].
    - test_fetch_social_aggregates: mock all three endpoints (reddit + trending + stream). Assert: result.reddit_posts is non-empty, result.stocktwits_posts is non-empty, result.trending_rank is the index+1 of "AAPL" in the trending fixture (1-based). result.data_unavailable is False.
    - test_fetch_social_all_sources_fail: mock all endpoints to 500. Assert: result.data_unavailable is True; reddit_posts == []; stocktwits_posts == []; trending_rank is None.
    - test_fetch_social_partial_failure: mock reddit 500, stocktwits 200. Assert: result.data_unavailable is False (because at least stocktwits worked); reddit_posts == []; stocktwits_posts non-empty.
  </behavior>
  <action>
    RED phase:
    1. Create `tests/ingestion/fixtures/reddit_search_aapl.xml` — Reddit's search.rss output. Atom-flavored:
       ```xml
       <?xml version="1.0" encoding="UTF-8"?>
       <feed xmlns="http://www.w3.org/2005/Atom">
         <title>search results for AAPL</title>
         <entry>
           <title>AAPL earnings preview - thoughts?</title>
           <link href="https://www.reddit.com/r/wallstreetbets/comments/abc123/aapl_earnings_preview/"/>
           <id>t3_abc123</id>
           <updated>2026-04-30T15:00:00+00:00</updated>
           <author><name>/u/someuser</name></author>
           <content type="html">...</content>
         </entry>
         ... 6 entries total across r/wallstreetbets, r/stocks, r/investing
       </feed>
       ```
       Subreddit is parseable from the `<link>` URL path: `r/<subreddit>/comments/...`.
    2. Create `tests/ingestion/fixtures/stocktwits_trending.json`:
       ```json
       {"response": {"status": 200}, "symbols": [
         {"symbol": "TSLA", "title": "Tesla", "id": 8849, "watchlist_count": 1500000},
         {"symbol": "AAPL", "title": "Apple Inc", "id": 686, "watchlist_count": 2000000},
         {"symbol": "NVDA", "title": "NVIDIA", "id": 3735, "watchlist_count": 1200000},
         {"symbol": "GME", "title": "GameStop", "id": 33179, "watchlist_count": 500000},
         {"symbol": "AMC", "title": "AMC Entertainment", "id": 26430, "watchlist_count": 400000}
       ]}
       ```
    3. Create `tests/ingestion/fixtures/stocktwits_aapl.json` — 30 messages, half with sentiment, half without; mix of bullish/bearish:
       ```json
       {
         "response": {"status": 200},
         "symbol": {"symbol": "AAPL", "title": "Apple Inc"},
         "messages": [
           {"id": 1, "body": "AAPL looks strong heading into earnings", "created_at": "2026-04-30T13:15:00Z", "entities": {"sentiment": {"basic": "Bullish"}}},
           {"id": 2, "body": "Selling my AAPL position", "created_at": "2026-04-30T13:00:00Z", "entities": {"sentiment": {"basic": "Bearish"}}},
           {"id": 3, "body": "AAPL chart looking interesting", "created_at": "2026-04-30T12:30:00Z", "entities": {"sentiment": null}},
           ... (continue to 30)
         ]
       }
       ```
    4. Write `tests/ingestion/test_social.py` with the ~10 tests above. Imports: `import responses, pytest, json`, `from pathlib import Path`, `from datetime import datetime, timezone`, `from ingestion.social import fetch_social, _fetch_reddit_search, _fetch_stocktwits_trending, _fetch_stocktwits_stream, REDDIT_SEARCH_URL, REDDIT_USER_AGENT, STOCKTWITS_TRENDING_URL, STOCKTWITS_STREAM_URL`, `from analysts.data.social import SocialSignal, RedditPost, StockTwitsPost`.
    5. Run `uv run pytest tests/ingestion/test_social.py -x -q` → fails.
    6. Commit: `test(02-05): add failing tests for social signal aggregation (probes 2-W2-14..16)`

    GREEN phase:
    7. Implement `ingestion/social.py`:
       - Module docstring: cite DATA-05 + the anonymous-only constraint + Reddit's bot-blocker UA quirk.
       - Imports: `from datetime import datetime, timezone`, `from typing import Optional`, `import re`, `import logging`, `import feedparser`, `from urllib.parse import quote`, `from ingestion.http import get_session, DEFAULT_TIMEOUT`, `from analysts.schemas import normalize_ticker`, `from analysts.data.social import RedditPost, StockTwitsPost, SocialSignal`.
       - Constants per interfaces block.
       - `def _fetch_reddit_search(ticker: str) -> list[RedditPost]`:
         - Build URL: query = quote(f"{ticker} OR ${ticker}"); url = REDDIT_SEARCH_URL.format(query=query).
         - `resp = get_session().get(url, timeout=DEFAULT_TIMEOUT, headers={"User-Agent": REDDIT_USER_AGENT})`. The headers kwarg overrides the session UA for this single call.
         - If status != 200, return [].
         - Parse with `feedparser.parse(resp.text)`. (We get bytes via requests, then hand to feedparser as a string — avoids feedparser doing its own HTTP.)
         - For each entry, extract: title, link (entry.link or entry.links[0].href), subreddit (parsed from URL via regex `r"/r/([^/]+)/"`), published_at via _parse_pubdate (similar to news.py's helper — copy or factor out later). Build RedditPost. Skip empty titles.
         - On any exception, log warning and return [].
       - `def _fetch_stocktwits_trending() -> list[str]`:
         - GET STOCKTWITS_TRENDING_URL via shared session (no UA override needed; StockTwits accepts default).
         - On non-200, return [].
         - Parse JSON; extract `[s["symbol"].upper() for s in payload.get("symbols", [])]`.
         - On any exception, return [].
       - `def _fetch_stocktwits_stream(ticker: str) -> list[StockTwitsPost]`:
         - GET STOCKTWITS_STREAM_URL.format(ticker=ticker) via shared session.
         - On non-200, return [].
         - Parse JSON. For each message in payload.get("messages", []):
           - body = msg.get("body", "")
           - created_at = parse_iso8601(msg.get("created_at"))
           - sentiment = msg.get("entities", {}).get("sentiment")
           - sentiment_normalized = sentiment.get("basic", "").lower() if sentiment else None
           - sentiment_normalized only kept if it's "bullish" or "bearish"
         - Build StockTwitsPost. Skip empty bodies.
       - `def fetch_social(ticker: str) -> SocialSignal`:
         - normalize ticker; if None → return SocialSignal(ticker=ticker_or_placeholder, fetched_at=now_utc, data_unavailable=True).
         - reddit_posts = _fetch_reddit_search(normalized).
         - stocktwits_posts = _fetch_stocktwits_stream(normalized).
         - trending = _fetch_stocktwits_trending().
         - trending_rank = (trending.index(normalized) + 1) if normalized in trending else None.
         - data_unavailable = (len(reddit_posts) == 0 AND len(stocktwits_posts) == 0 AND trending_rank is None).
         - Return SocialSignal(ticker=normalized, fetched_at=now_utc, source="combined", data_unavailable=data_unavailable, reddit_posts=reddit_posts, stocktwits_posts=stocktwits_posts, trending_rank=trending_rank).
    8. Run `uv run pytest tests/ingestion/test_social.py -v` → all green.
    9. Coverage: `uv run pytest --cov=ingestion.social --cov-branch tests/ingestion/test_social.py` → ≥90% line / ≥85% branch.
    10. Run plan-scoped suite: `uv run pytest tests/ingestion/ -v`.
    11. Commit: `feat(02-05): implement anonymous social signal fetch (Reddit RSS + StockTwits)`

    Probe ID test docstring comments:
    - 2-W2-14 → `test_reddit` (canonical) + `test_reddit_user_agent_is_non_default`
    - 2-W2-15 → `test_trending`
    - 2-W2-16 → `test_per_symbol`
  </action>
  <verify>
    <automated>uv run pytest tests/ingestion/test_social.py -v &amp;&amp; uv run pytest --cov=ingestion.social --cov-branch tests/ingestion/test_social.py</automated>
  </verify>
  <done>~10 social tests green. ingestion/social.py at ≥90% line / ≥85% branch. Three fixture files. Reddit UA override verified. StockTwits trending + per-symbol both wired and degradation-safe. Probes 2-W2-14, 2-W2-15, 2-W2-16 satisfied. Partial-failure path tested (one source down ≠ whole call fails).</done>
</task>

</tasks>

<verification>
- Probes covered: 2-W2-14, 2-W2-15, 2-W2-16.
- Requirement satisfied: DATA-05 (anonymous Reddit RSS + StockTwits trending + StockTwits per-symbol stream).
- Coverage gates: ≥90% line / ≥85% branch on ingestion/social.py.
- Anonymous discipline: no API keys, no OAuth, Reddit UA override sent per request.
- Partial failure path: any single source down → that collection empty, others unaffected.

## Cross-Scope Risks

_vault_status=budget_exhausted; re-run /gmd:plan-phase --replan after vault-maintain_
</verification>

<success_criteria>
1. fetch_social(ticker) returns SocialSignal with reddit_posts, stocktwits_posts, trending_rank populated when sources respond.
2. Reddit calls use REDDIT_USER_AGENT (verified via responses lib header inspection).
3. Per-source failure isolated — does not fail the whole SocialSignal.
4. data_unavailable=True only when ALL three sources fail.
5. All three probes (2-W2-14..16) mapped to named test functions with probe-id comments.
6. Plan 02-06 can call fetch_social as the single social entry point.
</success_criteria>

<output>
After completion, create `.planning/phases/02-ingestion-keyless-data-plane/02-05-SUMMARY.md`.
</output>
