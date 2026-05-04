# novel-to-this-project — Phase 2 anonymous Reddit + StockTwits aggregator (project-original).
"""Social-signal ingestion — Plan 02-05 / DATA-05.

Anonymous-only protocol: per-ticker posts from Reddit (RSS search across
r/wallstreetbets, r/stocks, r/investing via the global search.rss endpoint)
plus StockTwits' unauthenticated trending list and per-symbol stream. NO
OAuth, NO API keys. Both upstreams expose endpoints that work without auth;
this module deliberately stays inside that envelope.

Pitfall #2 (02-RESEARCH.md — Reddit RSS): Reddit blocks bots that send the
default `python-requests/...` User-Agent. We override the shared session's UA
on every Reddit call by passing `headers={"User-Agent": REDDIT_USER_AGENT}`
to `session.get(...)`. Requests merges per-request headers with the session
defaults, so the EDGAR-compliant UA the shared session carries is replaced
for THIS request only — other ingestion modules are unaffected.

Failure isolation: Reddit and StockTwits have independent rate-limit regimes
(Reddit's bot-blocker vs StockTwits' soft 200/hr cap). When one source fails
(429, 5xx after retries, malformed body), the corresponding collection comes
back empty and the OTHER source is still consulted. `data_unavailable=True`
is set ONLY when ALL three queries (Reddit search, StockTwits trending,
StockTwits per-symbol) come back empty AND the trending list does not
include the ticker.

Public surface:
    fetch_social(ticker) -> SocialSignal

Internal seams (exposed for testing):
    _fetch_reddit_search(ticker) -> list[RedditPost]
    _fetch_stocktwits_trending() -> list[str]   # uppercase symbols
    _fetch_stocktwits_stream(ticker) -> list[StockTwitsPost]

URL templates exposed at module level so tests can mock them via the
`responses` library without duplicating the format string.
"""
from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Optional
from urllib.parse import quote

import feedparser

from analysts.data.social import RedditPost, SocialSignal, StockTwitsPost
from analysts.schemas import normalize_ticker
from ingestion.http import DEFAULT_TIMEOUT, get_session

logger = logging.getLogger(__name__)

# URL templates. Reddit's search.rss accepts a query string; we OR `TICKER`
# with `$TICKER` so the cashtag form is also matched. sort=new + t=day keeps
# the result set focused on the last 24 hours.
REDDIT_SEARCH_URL = "https://www.reddit.com/search.rss?q={query}&sort=new&t=day"

# Reddit's bot-blocker rejects the default python-requests UA. The plan-locked
# value is `markets/0.1 (anonymous research aggregator)` — descriptive,
# non-impersonating, and stable across the Phase-2 codebase. Keep this in sync
# with 02-RESEARCH.md Pitfall #2.
REDDIT_USER_AGENT = "markets/0.1 (anonymous research aggregator)"

STOCKTWITS_TRENDING_URL = "https://api.stocktwits.com/api/2/trending/symbols.json"
STOCKTWITS_STREAM_URL = "https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"

# Subreddit extraction from a Reddit comment URL: capture the segment after /r/
_SUBREDDIT_RE = re.compile(r"/r/([^/]+)/")


def _now_utc() -> datetime:
    """UTC timestamp helper — single seam for tests if ever needed."""
    return datetime.now(UTC)


def _parse_iso8601(value: object) -> Optional[datetime]:
    """Best-effort ISO-8601 → aware datetime.

    Accepts the trailing `Z` form StockTwits emits as well as standard
    `+00:00` offsets. Returns None on anything that fails to parse — Pydantic
    `Optional[datetime]` fields tolerate None, so a single bad timestamp does
    not invalidate the entire post.
    """
    if not isinstance(value, str) or not value:
        return None
    try:
        # datetime.fromisoformat in 3.11+ accepts trailing 'Z' on Python 3.12.
        # Defensive normalize for older variants:
        s = value[:-1] + "+00:00" if value.endswith("Z") else value
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _extract_subreddit(url: str) -> Optional[str]:
    """Pull the subreddit name out of a Reddit comment URL."""
    m = _SUBREDDIT_RE.search(url)
    return m.group(1) if m else None


def _fetch_reddit_search(ticker: str) -> list[RedditPost]:
    """Query Reddit's search.rss for `ticker OR $ticker` and parse to RedditPost.

    Returns [] on any failure (non-200, network exception, malformed body) —
    per-source failure must NOT propagate. The shared session's retry adapter
    already covers transient 429/5xx; only the FINAL response status matters
    here.
    """
    query = quote(f"{ticker} OR ${ticker}")
    url = REDDIT_SEARCH_URL.format(query=query)

    try:
        # Per-request UA override (Pitfall #2). The shared session carries the
        # EDGAR-compliant UA which Reddit reportedly tolerates less than a
        # dedicated descriptive UA. requests merges per-request headers with
        # session defaults, so this replaces UA for THIS call only.
        response = get_session().get(
            url,
            timeout=DEFAULT_TIMEOUT,
            headers={"User-Agent": REDDIT_USER_AGENT},
        )
    except Exception as e:  # noqa: BLE001 — defensive; per-source isolation
        logger.warning("reddit search for %s failed at HTTP layer: %s", ticker, e)
        return []

    if response.status_code != 200:
        logger.info(
            "reddit search for %s returned %d (after retries) — empty result",
            ticker,
            response.status_code,
        )
        return []

    try:
        parsed = feedparser.parse(response.text)
    except Exception as e:  # noqa: BLE001 — feedparser is lenient but defend anyway
        logger.warning("reddit search for %s: feedparser failed: %s", ticker, e)
        return []

    posts: list[RedditPost] = []
    for entry in getattr(parsed, "entries", []) or []:
        title = (getattr(entry, "title", "") or "").strip()
        if not title:
            continue

        # Link: prefer `entry.link`; fall back to first href in entry.links
        link = getattr(entry, "link", None)
        if not link:
            links = getattr(entry, "links", None) or []
            link = links[0].get("href") if links else None
        if not link or not isinstance(link, str) or not link.startswith("http"):
            continue

        sub = _extract_subreddit(link)
        if not sub:
            # Fall back to feedparser's category if present
            tags = getattr(entry, "tags", None) or []
            if tags:
                term = tags[0].get("term") if isinstance(tags[0], dict) else getattr(tags[0], "term", None)
                if term:
                    sub = term
        if not sub:
            continue

        published_at = _parse_iso8601(getattr(entry, "published", None) or getattr(entry, "updated", None))

        try:
            posts.append(
                RedditPost(
                    title=title[:500],
                    url=link,
                    subreddit=sub,
                    published_at=published_at,
                    score=None,  # not in RSS — would require OAuth API
                )
            )
        except Exception as e:  # noqa: BLE001 — Pydantic ValidationError or anything else
            logger.warning("reddit search for %s: skip entry %r — %s", ticker, title[:50], e)
            continue

    return posts


def _fetch_stocktwits_trending() -> list[str]:
    """GET StockTwits trending list, return uppercase ticker symbols in order.

    [] on any failure. The shared session retry adapter handles 429/5xx
    transients; only a still-failing final response or a non-JSON body causes
    [] here.
    """
    try:
        response = get_session().get(STOCKTWITS_TRENDING_URL, timeout=DEFAULT_TIMEOUT)
    except Exception as e:  # noqa: BLE001
        logger.warning("stocktwits trending failed at HTTP layer: %s", e)
        return []

    if response.status_code != 200:
        return []

    try:
        payload = response.json()
    except ValueError as e:
        logger.warning("stocktwits trending: 200 with non-JSON body: %s", e)
        return []

    if not isinstance(payload, dict):
        return []

    symbols_raw = payload.get("symbols") or []
    out: list[str] = []
    for entry in symbols_raw:
        if not isinstance(entry, dict):
            continue
        sym = entry.get("symbol")
        if isinstance(sym, str) and sym:
            out.append(sym.upper())
    return out


def _fetch_stocktwits_stream(ticker: str) -> list[StockTwitsPost]:
    """GET StockTwits per-symbol stream, parse into list[StockTwitsPost].

    sentiment is normalized: `entities.sentiment.basic` ∈ {"Bullish","Bearish"}
    becomes lowercase `"bullish"`/`"bearish"` (the Literal allowed values on
    `StockTwitsPost.sentiment`). Anything else (null, missing, novel value)
    becomes None.
    """
    url = STOCKTWITS_STREAM_URL.format(ticker=ticker)

    try:
        response = get_session().get(url, timeout=DEFAULT_TIMEOUT)
    except Exception as e:  # noqa: BLE001
        logger.warning("stocktwits stream for %s failed at HTTP layer: %s", ticker, e)
        return []

    if response.status_code != 200:
        return []

    try:
        payload = response.json()
    except ValueError as e:
        logger.warning("stocktwits stream for %s: 200 with non-JSON body: %s", ticker, e)
        return []

    if not isinstance(payload, dict):
        return []

    posts: list[StockTwitsPost] = []
    for msg in payload.get("messages") or []:
        if not isinstance(msg, dict):
            continue
        body = msg.get("body")
        if not isinstance(body, str) or not body.strip():
            continue
        body = body[:2000]  # schema cap

        created_at = _parse_iso8601(msg.get("created_at"))

        # entities.sentiment may be: {"basic": "Bullish"}, {"basic": "Bearish"},
        # null, missing, or some novel value. Normalize defensively.
        sentiment_raw = None
        entities = msg.get("entities")
        if isinstance(entities, dict):
            sent_obj = entities.get("sentiment")
            if isinstance(sent_obj, dict):
                basic = sent_obj.get("basic")
                if isinstance(basic, str):
                    candidate = basic.strip().lower()
                    if candidate in ("bullish", "bearish"):
                        sentiment_raw = candidate

        try:
            posts.append(
                StockTwitsPost(
                    body=body,
                    created_at=created_at,
                    sentiment=sentiment_raw,
                )
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "stocktwits stream for %s: skip message %r — %s",
                ticker,
                msg.get("id"),
                e,
            )
            continue

    return posts


def fetch_social(ticker: str) -> SocialSignal:
    """Fetch per-ticker SocialSignal aggregating Reddit RSS + StockTwits.

    Always returns a SocialSignal — never raises for upstream weather. When
    every source comes back empty AND the trending list does not contain the
    ticker, `data_unavailable=True`; otherwise `False`.
    """
    normalized = normalize_ticker(ticker)
    if normalized is None:
        # Ticker can't be persisted on a SocialSignal (the schema validator
        # rejects invalid forms). Use a sentinel that round-trips through
        # Pydantic but signals failure to the caller via data_unavailable.
        return SocialSignal(
            ticker="INVALID",
            fetched_at=_now_utc(),
            source="combined",
            data_unavailable=True,
            reddit_posts=[],
            stocktwits_posts=[],
            trending_rank=None,
        )

    reddit_posts = _fetch_reddit_search(normalized)
    stocktwits_posts = _fetch_stocktwits_stream(normalized)
    trending = _fetch_stocktwits_trending()

    trending_rank: Optional[int] = None
    if normalized in trending:
        trending_rank = trending.index(normalized) + 1  # 1-based

    data_unavailable = (
        len(reddit_posts) == 0
        and len(stocktwits_posts) == 0
        and trending_rank is None
    )

    return SocialSignal(
        ticker=normalized,
        fetched_at=_now_utc(),
        source="combined",
        data_unavailable=data_unavailable,
        reddit_posts=reddit_posts,
        stocktwits_posts=stocktwits_posts,
        trending_rank=trending_rank,
    )
