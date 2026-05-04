"""News aggregation across Yahoo Finance RSS, Google News RSS, and FinViz HTML scrape (DATA-04).

Public surface:
    fetch_news(ticker, *, dedup_window_days=7) -> list[Headline]
        Fetches headlines from all three sources, dedups across sources, sorts
        by recency desc with None-published items at the end.

    fetch_news(ticker, *, dedup_window_days=7, return_raw=True)
        -> tuple[list[Headline], list[dict]]
        Phase 6 / Plan 06-01 extension. Same headlines as the default form,
        plus a parallel list of `{source, published_at, title, url}` dicts
        used by Phase 6 storage to persist headlines into per-ticker JSONs
        for the deep-dive news feed (VIEW-08).

Dedup strategy (per 02-RESEARCH.md):
    Primary key:   source + entry.id (or entry.link if id missing)
    Secondary key: normalized title (lowercase, strip non-alnum, take first 80
                   chars). Same wire story syndicated across sources collapses
                   to a single Headline.

Sort policy:
    Pre-sort by published_at desc BEFORE running dedup so the freshest copy of
    a duplicated story wins. Items with published_at=None go to the end via a
    sentinel (datetime.min replace tzinfo=UTC).

Date parsing:
    RSS feeds emit RFC 822 (Yahoo) or near-RFC-822 (Google). FinViz emits its
    own "Apr-30-26 09:15AM" format (assumed US/Eastern; we tag as UTC for
    sortability — exact tz precision isn't required for headline ordering).
    Continuation rows in FinViz drop the date prefix ("10:30AM") and inherit
    the most recent full date seen above them.

Failure mode:
    Each source helper returns [] on any failure (network, parse, validation).
    Aggregation never raises; the orchestrator (Plan 02-06) sees an empty list
    and marks data_unavailable downstream if appropriate.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

import feedparser
from bs4 import BeautifulSoup

from analysts.data.news import Headline
from analysts.schemas import normalize_ticker
from ingestion.errors import IngestionError  # re-export shape for callers
from ingestion.http import DEFAULT_TIMEOUT, get_session

__all__ = [
    "fetch_news",
    "YAHOO_RSS_URL",
    "GOOGLE_NEWS_URL",
    "FINVIZ_URL",
]

_LOG = logging.getLogger(__name__)

# Public URL templates — also imported by tests for `responses.add(...)`.
YAHOO_RSS_URL = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
GOOGLE_NEWS_URL = "https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en"
FINVIZ_URL = "https://finviz.com/quote.ashx?t={ticker}"

# Sentinel used to push None-published items to the END of a recency-desc sort.
_NONE_SENTINEL = datetime.min.replace(tzinfo=timezone.utc)

# Regex used by _normalize_title — strip everything that isn't a letter, digit,
# or whitespace.
_NON_ALNUM_SPACE = re.compile(r"[^a-z0-9\s]")
_WHITESPACE = re.compile(r"\s+")

# Google News appends ` - <Publisher>` to every title (e.g. "Apple beats Q1
# estimates - Reuters"). For cross-source dedup against Yahoo's plain title
# we strip that trailing suffix during normalization.
_GOOGLE_NEWS_SUFFIX = re.compile(r"\s+-\s+[^-]+$")

# FinViz date-prefix detector: full form looks like "Apr-30-26", continuation
# is just the time ("09:15AM"). The full form starts with three letters then
# a hyphen.
_FINVIZ_FULL_DATE = re.compile(r"^[A-Z][a-z]{2}-\d{2}-\d{2}\s+\d")


# ---------------- helpers ----------------


def _normalize_title(title: str) -> str:
    """Lowercase, strip punctuation + Google News publisher suffix, collapse whitespace, truncate to 80 chars.

    Used as a secondary dedup key so syndications of the same wire story across
    sources (where source-prefixed dedup_keys naturally differ) still collapse.

    Google News appends a ` - Publisher` tag to every headline ("Apple beats Q1
    estimates - Reuters"). We strip that BEFORE punctuation removal so the
    underlying headline matches the equivalent Yahoo / FinViz title.
    """
    if not isinstance(title, str):
        return ""
    s = title.strip()
    # Strip Google-News-style trailing publisher tag before lowercasing so the
    # `[^-]+$` capture doesn't bleed into a hyphenated title.
    s = _GOOGLE_NEWS_SUFFIX.sub("", s)
    s = s.lower()
    s = _NON_ALNUM_SPACE.sub(" ", s)
    s = _WHITESPACE.sub(" ", s).strip()
    return s[:80]


def _parse_pubdate(s: str) -> Optional[datetime]:
    """Parse a publication-date string into a timezone-aware datetime, or None.

    Tries (in order):
      1. RFC 822 via email.utils.parsedate_to_datetime (Yahoo, Google News).
      2. ISO 8601 via datetime.fromisoformat.
      3. FinViz "Apr-30-26 09:15AM" via strptime("%b-%d-%y %I:%M%p"). Tags as
         UTC since exact ET precision isn't required for ordering.

    Returns None on empty input or parse failure across all formats.
    """
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if not s:
        return None

    # 1. RFC 822
    try:
        dt = parsedate_to_datetime(s)
        if dt is not None:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
    except (TypeError, ValueError):
        pass

    # 2. ISO 8601
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        pass

    # 3. FinViz "Apr-30-26 09:15AM"
    try:
        dt = datetime.strptime(s, "%b-%d-%y %I:%M%p")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    return None


def _now_utc() -> datetime:
    """Indirection so tests can monkeypatch if needed."""
    return datetime.now(timezone.utc)


def _sort_by_recency(headlines: list[Headline]) -> list[Headline]:
    """Sort headlines by published_at desc; None-published items go LAST.

    Implemented via a (has_date, published_at) compound key so None items sort
    after every dated item regardless of their stable order.
    """
    return sorted(
        headlines,
        key=lambda h: (h.published_at is not None, h.published_at or _NONE_SENTINEL),
        reverse=True,
    )


# ---------------- per-source fetchers ----------------


def _fetch_yahoo_rss(ticker: str) -> list[Headline]:
    """Fetch the Yahoo Finance per-ticker RSS feed and parse into Headlines.

    Returns [] on any failure (network, parse, validation) — never raises.
    """
    out: list[Headline] = []
    fetched_at = _now_utc()
    try:
        url = YAHOO_RSS_URL.format(ticker=ticker)
        feed = feedparser.parse(url)
    except Exception:  # noqa: BLE001 — defensive: feedparser shouldn't raise but if it does we degrade
        _LOG.warning("yahoo-rss: feedparser raised for %s", ticker, exc_info=True)
        return out

    for entry in getattr(feed, "entries", []) or []:
        title = (entry.get("title") or "").strip()
        link = (entry.get("link") or "").strip()
        if not title or not link.startswith("http"):
            continue
        published_at = _parse_pubdate(entry.get("published") or entry.get("updated") or "")
        entry_id = entry.get("id") or link
        try:
            out.append(
                Headline(
                    ticker=ticker,
                    fetched_at=fetched_at,
                    source="yahoo-rss",
                    title=title[:500],
                    url=link,
                    published_at=published_at,
                    summary=(entry.get("summary") or "")[:2000],
                    dedup_key=f"yahoo-rss::{entry_id}",
                )
            )
        except Exception:  # noqa: BLE001 — Pydantic ValidationError per-row tolerance
            _LOG.debug("yahoo-rss: skipping invalid entry %r", entry_id)
            continue
    return out


def _fetch_google_news(ticker: str) -> list[Headline]:
    """Fetch the Google News per-ticker RSS feed and parse into Headlines."""
    out: list[Headline] = []
    fetched_at = _now_utc()
    try:
        url = GOOGLE_NEWS_URL.format(ticker=ticker)
        feed = feedparser.parse(url)
    except Exception:  # noqa: BLE001
        _LOG.warning("google-news: feedparser raised for %s", ticker, exc_info=True)
        return out

    for entry in getattr(feed, "entries", []) or []:
        title = (entry.get("title") or "").strip()
        link = (entry.get("link") or "").strip()
        if not title or not link.startswith("http"):
            continue
        published_at = _parse_pubdate(entry.get("published") or entry.get("updated") or "")
        entry_id = entry.get("id") or link
        try:
            out.append(
                Headline(
                    ticker=ticker,
                    fetched_at=fetched_at,
                    source="google-news",
                    title=title[:500],
                    url=link,
                    published_at=published_at,
                    summary=(entry.get("summary") or "")[:2000],
                    dedup_key=f"google-news::{entry_id}",
                )
            )
        except Exception:  # noqa: BLE001
            _LOG.debug("google-news: skipping invalid entry %r", entry_id)
            continue
    return out


def _fetch_finviz(ticker: str) -> list[Headline]:
    """Fetch FinViz quote.ashx page and scrape the news-table div.

    FinViz puts ticker news in a `<table id="news-table">`. Each row is a
    <tr> with two cells: date (or time-only for continuation rows) and the
    headline anchor + source span.

    Returns [] on:
      - non-200 response (404 ticker, 500 server, etc.)
      - missing news-table div (page structure changed or ticker has no news)
      - any parse error
    """
    out: list[Headline] = []
    fetched_at = _now_utc()
    try:
        resp = get_session().get(
            FINVIZ_URL.format(ticker=ticker), timeout=DEFAULT_TIMEOUT
        )
    except Exception:  # noqa: BLE001
        _LOG.warning("finviz: request failed for %s", ticker, exc_info=True)
        return out

    if resp.status_code != 200:
        _LOG.info("finviz: %s returned status %d", ticker, resp.status_code)
        return out

    try:
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception:  # noqa: BLE001
        _LOG.warning("finviz: BeautifulSoup failed for %s", ticker, exc_info=True)
        return out

    table = soup.find("table", id="news-table")
    if table is None:
        return out

    last_full_date: Optional[datetime] = None
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue
        date_text = tds[0].get_text(strip=True)
        link_td = tds[1]
        anchor = link_td.find("a", class_="tab-link-news") or link_td.find("a")
        if anchor is None:
            continue
        title = anchor.get_text(strip=True)
        url = (anchor.get("href") or "").strip()
        if not title or not url.startswith("http"):
            continue

        # Resolve date: full form ("Apr-30-26 09:15AM") OR continuation
        # ("09:15AM") which inherits the last full date.
        published_at: Optional[datetime] = None
        if _FINVIZ_FULL_DATE.match(date_text):
            published_at = _parse_pubdate(date_text)
            if published_at is not None:
                last_full_date = published_at
        elif last_full_date is not None and date_text:
            # Continuation: combine last full date with this time.
            try:
                time_part = datetime.strptime(date_text, "%I:%M%p")
                published_at = last_full_date.replace(
                    hour=time_part.hour,
                    minute=time_part.minute,
                    second=0,
                    microsecond=0,
                )
            except ValueError:
                published_at = last_full_date

        try:
            out.append(
                Headline(
                    ticker=ticker,
                    fetched_at=fetched_at,
                    source="finviz",
                    title=title[:500],
                    url=url,
                    published_at=published_at,
                    summary="",
                    dedup_key=f"finviz::{url}",
                )
            )
        except Exception:  # noqa: BLE001
            _LOG.debug("finviz: skipping invalid row %r", title)
            continue
    return out


# ---------------- dedup ----------------


def _dedup(headlines: list[Headline]) -> list[Headline]:
    """Dedup by (primary: dedup_key) AND (secondary: normalized title).

    Iterates in input order — the FIRST occurrence wins. To bias toward newest,
    callers should `_sort_by_recency` BEFORE passing through dedup so the
    freshest copy of a syndicated story takes the slot.
    """
    seen_primary: set[str] = set()
    seen_secondary: set[str] = set()
    out: list[Headline] = []
    for h in headlines:
        if h.dedup_key in seen_primary:
            continue
        norm = _normalize_title(h.title)
        if norm and norm in seen_secondary:
            continue
        seen_primary.add(h.dedup_key)
        if norm:
            seen_secondary.add(norm)
        out.append(h)
    return out


# ---------------- public entry point ----------------


def fetch_news(
    ticker: str,
    *,
    dedup_window_days: int = 7,
    return_raw: bool = False,
):
    """Fetch headlines for `ticker` from Yahoo RSS + Google News + FinViz, deduped + sorted.

    `dedup_window_days` filters out items older than now - delta (items with
    published_at=None bypass the filter — we keep them but they sort to the end).

    Default return: `list[Headline]` (existing call-site contract; preserved
    by Phase 6 / Plan 06-01).

    When `return_raw=True`, returns `tuple[list[Headline], list[dict]]` where
    the dict list is the raw `{source, published_at, title, url}` records
    used by Phase 6 storage to persist headlines into per-ticker JSONs
    (frontend deep-dive news feed, VIEW-08). The two lists are aligned
    1:1 (same length, same order — both are the post-dedup post-sort
    final output).

    Returns `[]` (or `([], [])` with `return_raw=True`) if `ticker` doesn't
    normalize. Per-source failures are absorbed silently; a single broken
    source never blocks the others.
    """
    norm = normalize_ticker(ticker) if isinstance(ticker, str) else None
    if norm is None:
        return ([], []) if return_raw else []

    yahoo = _fetch_yahoo_rss(norm)
    google = _fetch_google_news(norm)
    finviz = _fetch_finviz(norm)

    all_items = yahoo + google + finviz

    if dedup_window_days > 0:
        cutoff = _now_utc() - timedelta(days=dedup_window_days)
        all_items = [
            h for h in all_items if (h.published_at is None or h.published_at >= cutoff)
        ]

    sorted_items = _sort_by_recency(all_items)
    final = _dedup(sorted_items)
    if not return_raw:
        return final

    # Phase 6 / Plan 06-01: parallel raw-headline list for storage layer.
    # Use mode='json' so datetime → ISO 8601 string and the dict is JSON-safe
    # without further conversion in routine/storage._build_ticker_payload.
    raw: list[dict] = []
    for h in final:
        dumped = h.model_dump(mode="json")
        raw.append(
            {
                "source": dumped["source"],
                "published_at": dumped["published_at"],
                "title": dumped["title"],
                "url": dumped["url"],
            }
        )
    return final, raw


# Mark the unused import as intentional (re-export shape):
_ = IngestionError
