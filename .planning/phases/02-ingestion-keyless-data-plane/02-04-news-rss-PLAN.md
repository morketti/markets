---
phase: 02-ingestion-keyless-data-plane
plan: 04
type: tdd
wave: 2
depends_on: [02-01]
files_modified:
  - ingestion/news.py
  - tests/ingestion/test_news.py
  - tests/ingestion/fixtures/yahoo_rss_aapl.xml
  - tests/ingestion/fixtures/google_news_aapl.xml
  - tests/ingestion/fixtures/finviz_aapl.html
autonomous: true
requirements: [DATA-04]
must_haves:
  truths:
    - "fetch_news(ticker) returns a list[Headline] aggregated across Yahoo Finance RSS, Google News RSS, and FinViz HTML scrape"
    - "Same story syndicated across two sources (matching dedup_key) appears exactly once in the result"
    - "Result is sorted by published_at descending (most recent first); items with None published_at land at the end"
    - "FinViz news block is parsed with BeautifulSoup; missing news block returns [] for that source (not an error)"
    - "Each Headline carries an exact source Literal — yahoo-rss / google-news / finviz"
  artifacts:
    - path: "ingestion/news.py"
      provides: "fetch_news(ticker) -> list[Headline] aggregating 3 sources + dedup + sort"
      min_lines: 80
    - path: "tests/ingestion/test_news.py"
      provides: "Probes 2-W2-09 (yahoo), 2-W2-10 (google), 2-W2-11 (dedup), 2-W2-12 (sort), 2-W2-13 (finviz)"
      min_lines: 80
    - path: "tests/ingestion/fixtures/yahoo_rss_aapl.xml"
      provides: "Real-shape Yahoo Finance RSS feed for AAPL with 5+ items"
    - path: "tests/ingestion/fixtures/google_news_aapl.xml"
      provides: "Real-shape Google News RSS for AAPL with 5+ items, including one duplicate of a Yahoo headline"
    - path: "tests/ingestion/fixtures/finviz_aapl.html"
      provides: "Real-shape FinViz quote.ashx HTML with news-table div + 5+ rows"
  key_links:
    - from: "ingestion/news.py"
      to: "feedparser.parse"
      via: "RSS XML parsing for Yahoo + Google"
      pattern: "feedparser.parse"
    - from: "ingestion/news.py"
      to: "bs4.BeautifulSoup"
      via: "FinViz HTML scrape (no RSS available)"
      pattern: "BeautifulSoup\\(.*html"
    - from: "ingestion/news.py"
      to: "ingestion.http.get_session()"
      via: "shared session for FinViz fetch"
      pattern: "get_session\\(\\)"
    - from: "ingestion/news.py"
      to: "analysts.data.Headline"
      via: "Pydantic validation per item"
      pattern: "Headline\\("
---

<objective>
Wave 2 / Source C: news headlines aggregation. Fetches per-ticker headlines from three RSS/HTML sources (Yahoo Finance RSS, Google News RSS, FinViz HTML scrape), dedups across sources, sorts by recency. Implements DATA-04 in full.

Purpose: News is the most-syndicated of the data sources — the same wire story shows up on Yahoo, Google News, and FinViz within minutes of each other. Aggregating without dedup would triple the user's headline count and dilute signal. Cross-source dedup is the central design challenge here, and it deserves its own focused plan.

Output: ingestion/news.py with `fetch_news(ticker) -> list[Headline]` and helpers per source. Five probes covered (per-source happy paths × 3, plus dedup, plus sort). Three fixture files (Yahoo RSS, Google News RSS, FinViz HTML).
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

From analysts/data/news.py:
```python
class Headline(BaseModel):
    ticker: str
    fetched_at: datetime
    source: Literal["yahoo-rss", "google-news", "finviz"]
    data_unavailable: bool = False
    title: str = Field(min_length=1, max_length=500)
    url: str
    published_at: Optional[datetime] = None
    summary: str = Field(default="", max_length=2000)
    dedup_key: str
```

NEW contracts this plan creates:

ingestion/news.py:
```python
YAHOO_RSS_URL = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
GOOGLE_NEWS_URL = "https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en"
FINVIZ_URL = "https://finviz.com/quote.ashx?t={ticker}"

def fetch_news(ticker: str, *, dedup_window_days: int = 7) -> list[Headline]:
    """Fetch headlines from Yahoo RSS + Google News RSS + FinViz scrape.
    Dedups within `dedup_window_days` window using primary key
    (source + entry.id) and secondary normalized title. Sorts by
    published_at desc with None-published items at the end."""

# Internal helpers (still useful as test seams):
def _fetch_yahoo_rss(ticker: str) -> list[Headline]
def _fetch_google_news(ticker: str) -> list[Headline]
def _fetch_finviz(ticker: str) -> list[Headline]
def _dedup(headlines: list[Headline]) -> list[Headline]
def _normalize_title(title: str) -> str
```

FinViz HTML scrape target: a `<table id="news-table">` with rows like:
```html
<table id="news-table">
  <tr>
    <td align="right" width="130">Apr-30-26 09:15AM</td>
    <td><a href="https://..." class="tab-link-news">Apple beats Q1 estimates</a><span>(Reuters)</span></td>
  </tr>
  ...
</table>
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: TDD ingestion/news.py — three sources + dedup + sort</name>
  <files>tests/ingestion/test_news.py, tests/ingestion/fixtures/yahoo_rss_aapl.xml, tests/ingestion/fixtures/google_news_aapl.xml, tests/ingestion/fixtures/finviz_aapl.html, ingestion/news.py</files>
  <behavior>
    Probes 2-W2-09 (Yahoo RSS), 2-W2-10 (Google News), 2-W2-11 (dedup), 2-W2-12 (sort), 2-W2-13 (FinViz scrape).

    test_news.py:
    - test_yahoo_rss (probe 2-W2-09): patch `feedparser.parse` to return a parsed result loaded from `yahoo_rss_aapl.xml` (or just call feedparser on the fixture's bytes — feedparser is offline-safe with bytes input). Better: register the URL via `responses` and have feedparser fetch the bytes through requests. Even simpler: bypass network by passing the fixture path directly to `feedparser.parse(str(fixture_path))` — feedparser accepts a file path. Pick the LAST option (path-based) because feedparser internally bypasses requests for file paths. Assert: result is list[Headline] of length ≥ 5; each item has source == "yahoo-rss", title non-empty, url starts with "http", published_at is a datetime (timezone-aware).
    - test_google_news (probe 2-W2-10): same pattern with `google_news_aapl.xml`. Assert: source == "google-news", titles non-empty.
    - test_finviz (probe 2-W2-13): patch `get_session().get(FINVIZ_URL.format(ticker="AAPL"))` via `responses` to return the fixture HTML with status 200. Assert: returns list[Headline] of length ≥ 5; source == "finviz"; published_at parsed from "Apr-30-26 09:15AM" format → datetime; titles match fixture.
    - test_finviz_no_news_block_returns_empty: mock the URL to return HTML without a news-table div. Assert: result is `[]` (NOT an error).
    - test_finviz_http_500_returns_empty: mock the URL to return 500. Assert: result is `[]` and no exception propagates (graceful degradation per data_unavailable semantics).
    - test_dedup (probe 2-W2-11): construct a list of 4 Headline objects manually — two with the same dedup_key (across sources), two unique. Pass through `_dedup()`. Assert: result length == 3, the duplicate appears once. Ordering: when dedup picks a winner, prefer the one with the MOST RECENT published_at (or the first if tied — document the policy).
    - test_dedup_secondary_normalized_title (probe 2-W2-11 variant): two Headlines with DIFFERENT dedup_keys (different sources, different entry.ids) but normalized titles match (e.g., "Apple Beats Q1 Estimates" vs "apple beats q1 estimates."). Assert: dedup leaves 1.
    - test_normalize_title: `_normalize_title("Apple Beats Q1 Estimates!")` == `_normalize_title("apple beats q1 estimates")` (lowercase, strip punctuation, take first 80 chars).
    - test_sort (probe 2-W2-12): construct list of 5 Headlines with various published_at, including one with published_at=None. Pass through `fetch_news` aggregation OR a `_sort_by_recency` helper. Assert: result is sorted by published_at desc with the None one last. Use `key=lambda h: h.published_at or datetime.min.replace(tzinfo=timezone.utc)` (None goes last via sentinel).
    - test_fetch_news_aggregates_all_three (integration within plan, optional but powerful): patch all three sources; assert combined result has items from all three sources (count by source); assert dedup ran (one cross-source dup) and sort ran (ascending check on published_at).
  </behavior>
  <action>
    RED phase:
    1. Create `tests/ingestion/fixtures/yahoo_rss_aapl.xml` — real-shape RSS 2.0 XML with `<channel><item><title>...</title><link>...</link><guid>...</guid><pubDate>Wed, 30 Apr 2026 09:15:00 -0400</pubDate><description>...</description></item>...</channel>`. Include 6 items with realistic AAPL headlines and varied pubDates (mostly 2026-04-30, some 2026-04-29). Include ONE that will be duplicated in the Google News fixture.
    2. Create `tests/ingestion/fixtures/google_news_aapl.xml` — Google News RSS shape (similar but with their wrapper format `<title>Apple beats Q1 estimates - Reuters</title>` etc). 5 items; ONE matches a Yahoo headline by normalized title.
    3. Create `tests/ingestion/fixtures/finviz_aapl.html` — minimal HTML page with `<html><body><table id="news-table"><tr><td>Apr-30-26 09:15AM</td><td><a href="https://reuters.com/..." class="tab-link-news">Apple beats Q1 estimates</a></td></tr>...</table></body></html>`. 5 rows, varied dates. Date format: FinViz uses `MMM-DD-YY HH:MMAM/PM` for the most recent day OR `Today HH:MM` for today's items. Include both formats so the parser handles them.
    4. Write `tests/ingestion/test_news.py` with the ~10 tests above. Imports: `import responses, pytest, feedparser`, `from pathlib import Path`, `from datetime import datetime, timezone`, `from ingestion.news import fetch_news, _fetch_yahoo_rss, _fetch_google_news, _fetch_finviz, _dedup, _normalize_title, YAHOO_RSS_URL, GOOGLE_NEWS_URL, FINVIZ_URL`, `from analysts.data.news import Headline`.
    5. Run `uv run pytest tests/ingestion/test_news.py -x -q` → all fail.
    6. Commit: `test(02-04): add failing tests for news aggregation + dedup + sort (probes 2-W2-09..13)`

    GREEN phase:
    7. Implement `ingestion/news.py`:
       - Module docstring: cite DATA-04 + the dedup strategy from RESEARCH.md (primary: source + entry.id, secondary: normalized title).
       - Imports: `from datetime import datetime, timezone`, `from typing import Optional`, `import re`, `import feedparser`, `from bs4 import BeautifulSoup`, `from ingestion.http import get_session, DEFAULT_TIMEOUT`, `from analysts.schemas import normalize_ticker`, `from analysts.data.news import Headline`, `import logging`.
       - Constants: three URL templates as in interfaces block.
       - `def _normalize_title(title: str) -> str`: lowercase, strip non-alnum-non-space via regex, collapse whitespace, take first 80 chars. Used for secondary dedup key.
       - `def _parse_pubdate(s: str) -> Optional[datetime]`: try multiple formats (RFC 822 via `email.utils.parsedate_to_datetime`, ISO 8601 via `datetime.fromisoformat`, FinViz "Apr-30-26 09:15AM" via `strptime("%b-%d-%y %I:%M%p")` — assume ET timezone for FinViz), return None on failure.
       - `def _fetch_yahoo_rss(ticker: str) -> list[Headline]`: feedparser.parse(YAHOO_RSS_URL.format(ticker=ticker)). For each entry, build Headline(ticker=ticker, fetched_at=now_utc, source="yahoo-rss", title=entry.get("title",""), url=entry.get("link",""), published_at=_parse_pubdate(entry.get("published","")), summary=entry.get("summary",""), dedup_key=f"yahoo-rss::{entry.get('id', entry.get('link',''))}"). Skip entries with empty title or empty url. On any exception, return [].
       - `def _fetch_google_news(ticker: str) -> list[Headline]`: same pattern with source="google-news" and the GOOGLE_NEWS_URL.
       - `def _fetch_finviz(ticker: str) -> list[Headline]`:
         - `resp = get_session().get(FINVIZ_URL.format(ticker=ticker), timeout=DEFAULT_TIMEOUT)`. If resp.status_code != 200, return [].
         - `soup = BeautifulSoup(resp.text, "html.parser")`; `table = soup.find("table", id="news-table")`. If table is None, return [].
         - For each `<tr>`: extract first td (date) and second td (link + source). Parse date — handle "Apr-30-26 09:15AM" full form or "09:15AM" continuation form (carry forward the most recent full date). Extract link via `tr.find("a", class_="tab-link-news")`. Build Headline.
         - dedup_key = f"finviz::{url_or_normalized_title}".
       - `def _dedup(headlines: list[Headline]) -> list[Headline]`:
         - Track seen primary keys (dedup_key) and seen secondary keys (normalized titles).
         - For each headline (in INPUT order): if dedup_key in seen_primary OR normalized_title in seen_secondary, skip. Else add.
         - When deciding which version of a dup wins: since input order is the order we get them, and the assert wants newest-first preference, we should pre-sort by published_at desc BEFORE running dedup. Implementation: sort first, then dedup-by-first-seen.
       - `def fetch_news(ticker: str, *, dedup_window_days: int = 7) -> list[Headline]`:
         - normalize ticker; if None → return [].
         - Aggregate: yahoo + google + finviz lists.
         - Filter to within dedup_window_days: drop headlines older than now - timedelta(days=dedup_window_days), unless published_at is None (keep those — they go to the end).
         - Sort by published_at desc (None last, via sentinel).
         - Dedup (after sort, so newest wins).
         - Return.
    8. Run `uv run pytest tests/ingestion/test_news.py -v` → all green.
    9. Coverage: `uv run pytest --cov=ingestion.news --cov-branch tests/ingestion/test_news.py` → ≥90% line / ≥85% branch.
    10. Run plan-scoped: `uv run pytest tests/ingestion/ -v`.
    11. Commit: `feat(02-04): implement news aggregation across Yahoo/Google/FinViz with dedup + sort`

    Probe ID test docstring comments:
    - 2-W2-09 → `test_yahoo_rss`
    - 2-W2-10 → `test_google_news`
    - 2-W2-11 → `test_dedup` (canonical) + `test_dedup_secondary_normalized_title` (variant)
    - 2-W2-12 → `test_sort`
    - 2-W2-13 → `test_finviz` (canonical) + `test_finviz_no_news_block_returns_empty` + `test_finviz_http_500_returns_empty` (variants)
  </action>
  <verify>
    <automated>uv run pytest tests/ingestion/test_news.py -v &amp;&amp; uv run pytest --cov=ingestion.news --cov-branch tests/ingestion/test_news.py</automated>
  </verify>
  <done>~10 news tests green. ingestion/news.py at ≥90% line / ≥85% branch. Three fixture files committed (Yahoo RSS, Google News RSS, FinViz HTML). Probes 2-W2-09..13 satisfied. fetch_news returns deduplicated, recency-sorted Headlines from three sources.</done>
</task>

</tasks>

<verification>
- Probes covered: 2-W2-09, 2-W2-10, 2-W2-11, 2-W2-12, 2-W2-13.
- Requirement satisfied: DATA-04 (RSS aggregation across Yahoo + Google News + FinViz with dedup + sort).
- Coverage gates: ≥90% line / ≥85% branch on ingestion/news.py.
- Zero real network — feedparser uses fixture file paths, FinViz uses responses lib.

## Cross-Scope Risks

_vault_status=budget_exhausted; re-run /gmd:plan-phase --replan after vault-maintain_
</verification>

<success_criteria>
1. fetch_news(ticker) returns list[Headline] from 3 sources, deduped (primary + secondary keys), sorted by recency (None-published last).
2. Each source-specific helper handles upstream failure gracefully — returns [] (not an exception) when the feed is empty/broken.
3. FinViz HTML parsed correctly with BeautifulSoup; date formats handled (full + continuation); missing news-table block returns [].
4. All 5 probes (2-W2-09..13) mapped to named test functions with probe-id comments.
5. Plan 02-06 can call fetch_news as the single news entry point.
</success_criteria>

<output>
After completion, create `.planning/phases/02-ingestion-keyless-data-plane/02-04-SUMMARY.md`.
</output>
