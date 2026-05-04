"""Tests for ingestion/news.py — News aggregation across Yahoo RSS + Google News + FinViz (Plan 02-04).

Probes covered:
- 2-W2-09: Yahoo Finance RSS parse → list[Headline] (test_yahoo_rss)
- 2-W2-10: Google News RSS parse → list[Headline] (test_google_news)
- 2-W2-11: Cross-source dedup leaves a single copy (test_dedup, test_dedup_secondary_normalized_title)
- 2-W2-12: Recency-desc sort with None-published last (test_sort)
- 2-W2-13: FinViz HTML scrape → list[Headline] (test_finviz, +empty/HTTP-500 variants)

Zero real network: feedparser is given a local fixture path (which it parses
without going through requests); FinViz is mocked via the `responses` lib.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
import responses

from analysts.data.news import Headline
from ingestion.news import (
    FINVIZ_URL,
    GOOGLE_NEWS_URL,
    YAHOO_RSS_URL,
    _dedup,
    _fetch_finviz,
    _fetch_google_news,
    _fetch_yahoo_rss,
    _normalize_title,
    _sort_by_recency,
    fetch_news,
)


# ---------- helpers ----------

def _make_headline(
    *,
    title: str,
    source: str = "yahoo-rss",
    published_at=None,
    dedup_key: str | None = None,
    url: str | None = None,
) -> Headline:
    return Headline(
        ticker="AAPL",
        fetched_at=datetime(2026, 4, 30, 14, 30, tzinfo=timezone.utc),
        source=source,  # type: ignore[arg-type]
        title=title,
        url=url or f"https://example.com/{title.replace(' ', '-')}",
        published_at=published_at,
        summary="",
        dedup_key=dedup_key or f"{source}::{title}",
    )


# ---------- 2-W2-09: Yahoo RSS happy path ----------


def test_yahoo_rss(fixtures_dir: Path):
    """Probe 2-W2-09 — Yahoo Finance RSS fixture parses to list[Headline]."""
    fixture_path = fixtures_dir / "yahoo_rss_aapl.xml"

    # feedparser accepts a file path (or URL) — passing a path bypasses requests
    # entirely. We patch feedparser.parse inside ingestion.news so the module's
    # production code path (which thinks it's calling the URL) actually parses
    # the local fixture instead.
    import feedparser

    real_parse = feedparser.parse

    def fake_parse(url, *args, **kwargs):
        return real_parse(str(fixture_path))

    with patch("ingestion.news.feedparser.parse", side_effect=fake_parse):
        result = _fetch_yahoo_rss("AAPL")

    assert isinstance(result, list)
    assert len(result) >= 5
    for h in result:
        assert isinstance(h, Headline)
        assert h.source == "yahoo-rss"
        assert h.ticker == "AAPL"
        assert h.title  # non-empty
        assert h.url.startswith("http")
        assert h.published_at is not None
        assert h.published_at.tzinfo is not None
        assert h.dedup_key.startswith("yahoo-rss::")


# ---------- 2-W2-10: Google News RSS happy path ----------


def test_google_news(fixtures_dir: Path):
    """Probe 2-W2-10 — Google News RSS fixture parses to list[Headline]."""
    fixture_path = fixtures_dir / "google_news_aapl.xml"

    import feedparser

    real_parse = feedparser.parse

    def fake_parse(url, *args, **kwargs):
        return real_parse(str(fixture_path))

    with patch("ingestion.news.feedparser.parse", side_effect=fake_parse):
        result = _fetch_google_news("AAPL")

    assert isinstance(result, list)
    assert len(result) >= 5
    for h in result:
        assert h.source == "google-news"
        assert h.ticker == "AAPL"
        assert h.title
        assert h.url.startswith("http")
        assert h.dedup_key.startswith("google-news::")


# ---------- 2-W2-13: FinViz happy path + variants ----------


@responses.activate
def test_finviz(fixtures_dir: Path):
    """Probe 2-W2-13 — FinViz HTML parses to list[Headline] with dates resolved."""
    html = (fixtures_dir / "finviz_aapl.html").read_text()
    url = FINVIZ_URL.format(ticker="AAPL")
    responses.add(responses.GET, url, body=html, status=200, content_type="text/html")

    result = _fetch_finviz("AAPL")

    assert isinstance(result, list)
    assert len(result) >= 5
    for h in result:
        assert h.source == "finviz"
        assert h.ticker == "AAPL"
        assert h.title
        assert h.url.startswith("http")
        assert h.dedup_key.startswith("finviz::")

    # First row carries an explicit date — should resolve to 2026-04-30 09:15.
    titles = [h.title for h in result]
    assert "Apple beats Q1 estimates" in titles

    # Continuation-form row ("10:30AM" without date prefix) should inherit the
    # most recent full date — i.e. 2026-04-30 10:30.
    bundle = next(h for h in result if "subscription bundle" in h.title)
    assert bundle.published_at is not None
    assert bundle.published_at.year == 2026
    assert bundle.published_at.month == 4
    assert bundle.published_at.day == 30
    assert bundle.published_at.hour == 10
    assert bundle.published_at.minute == 30


@responses.activate
def test_finviz_no_news_block_returns_empty():
    """Probe 2-W2-13 variant — missing news-table div returns [], not an error."""
    url = FINVIZ_URL.format(ticker="AAPL")
    responses.add(
        responses.GET,
        url,
        body="<html><body><p>No news here.</p></body></html>",
        status=200,
        content_type="text/html",
    )
    result = _fetch_finviz("AAPL")
    assert result == []


@responses.activate
def test_finviz_http_500_returns_empty():
    """Probe 2-W2-13 variant — upstream 500 returns [] (graceful degradation)."""
    # Note: shared session retries 5xx 3 times. We register N+1 responses so all
    # attempts see the same 500.
    url = FINVIZ_URL.format(ticker="AAPL")
    for _ in range(4):
        responses.add(responses.GET, url, body="oops", status=500)
    result = _fetch_finviz("AAPL")
    assert result == []


@responses.activate
def test_finviz_http_404_returns_empty():
    """Probe 2-W2-13 variant — non-200 response returns [] gracefully."""
    url = FINVIZ_URL.format(ticker="NOPE")
    responses.add(responses.GET, url, body="Not Found", status=404)
    result = _fetch_finviz("NOPE")
    assert result == []


# ---------- 2-W2-11: Dedup ----------


def test_dedup():
    """Probe 2-W2-11 canonical — duplicate dedup_key collapses to one entry."""
    a = _make_headline(
        title="Apple beats Q1 estimates",
        source="yahoo-rss",
        dedup_key="cross-source::apple-beats-q1",
        published_at=datetime(2026, 4, 30, 13, 15, tzinfo=timezone.utc),
    )
    b = _make_headline(
        title="Apple beats Q1 estimates",
        source="google-news",
        dedup_key="cross-source::apple-beats-q1",  # same primary key
        published_at=datetime(2026, 4, 30, 13, 20, tzinfo=timezone.utc),
    )
    c = _make_headline(
        title="Apple raises dividend",
        source="yahoo-rss",
        dedup_key="cross-source::apple-dividend",
        published_at=datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc),
    )
    d = _make_headline(
        title="Vision Pro 2 rumored",
        source="google-news",
        dedup_key="cross-source::vision-pro-rumor",
        published_at=datetime(2026, 4, 29, 18, 0, tzinfo=timezone.utc),
    )
    result = _dedup([a, b, c, d])
    assert len(result) == 3
    titles = {h.title for h in result}
    assert "Apple beats Q1 estimates" in titles
    assert "Apple raises dividend" in titles
    assert "Vision Pro 2 rumored" in titles


def test_dedup_secondary_normalized_title():
    """Probe 2-W2-11 variant — different dedup_keys but identical normalized titles dedup to 1."""
    a = _make_headline(
        title="Apple Beats Q1 Estimates!",
        source="yahoo-rss",
        dedup_key="yahoo-rss::yahoo-id-1",
        published_at=datetime(2026, 4, 30, 13, 15, tzinfo=timezone.utc),
    )
    b = _make_headline(
        title="apple beats q1 estimates.",
        source="google-news",
        dedup_key="google-news::google-id-2",  # different primary key
        published_at=datetime(2026, 4, 30, 13, 20, tzinfo=timezone.utc),
    )
    result = _dedup([a, b])
    assert len(result) == 1


# ---------- _normalize_title ----------


def test_normalize_title():
    """_normalize_title strips punctuation, lowercases, and collapses whitespace."""
    assert _normalize_title("Apple Beats Q1 Estimates!") == _normalize_title(
        "apple beats q1 estimates"
    )
    assert _normalize_title("Apple   Beats   Q1") == _normalize_title("Apple Beats Q1")


def test_normalize_title_truncates_to_80_chars():
    long = "Apple " * 30  # well over 80
    assert len(_normalize_title(long)) <= 80


# ---------- 2-W2-12: Sort ----------


def test_sort():
    """Probe 2-W2-12 — sort returns recency-desc with None-published items last."""
    h_oldest = _make_headline(
        title="Old story",
        published_at=datetime(2026, 4, 28, 9, 0, tzinfo=timezone.utc),
        dedup_key="k1",
    )
    h_middle = _make_headline(
        title="Middle story",
        published_at=datetime(2026, 4, 29, 9, 0, tzinfo=timezone.utc),
        dedup_key="k2",
    )
    h_newest = _make_headline(
        title="New story",
        published_at=datetime(2026, 4, 30, 9, 0, tzinfo=timezone.utc),
        dedup_key="k3",
    )
    h_none = _make_headline(title="No date", published_at=None, dedup_key="k4")
    h_other = _make_headline(
        title="Another mid",
        published_at=datetime(2026, 4, 29, 18, 0, tzinfo=timezone.utc),
        dedup_key="k5",
    )

    sorted_list = _sort_by_recency([h_none, h_oldest, h_newest, h_middle, h_other])

    assert sorted_list[0] is h_newest
    # h_other is 2026-04-29 18:00 (later than h_middle's 09:00)
    assert sorted_list[1] is h_other
    assert sorted_list[2] is h_middle
    assert sorted_list[3] is h_oldest
    assert sorted_list[4] is h_none  # None goes last


# ---------- fetch_news integration (within-plan) ----------


@responses.activate
def test_fetch_news_aggregates_all_three(fixtures_dir: Path):
    """fetch_news combines Yahoo + Google + FinViz, dedups, and sorts.

    Cross-source dedup expectation: Yahoo and Google both carry an
    "Apple beats Q1 estimates" headline with the same normalized title — the
    aggregation pipeline should leave exactly one copy after dedup.
    """
    yahoo_path = fixtures_dir / "yahoo_rss_aapl.xml"
    google_path = fixtures_dir / "google_news_aapl.xml"
    finviz_html = (fixtures_dir / "finviz_aapl.html").read_text()

    # Mock FinViz HTTP.
    responses.add(
        responses.GET,
        FINVIZ_URL.format(ticker="AAPL"),
        body=finviz_html,
        status=200,
        content_type="text/html",
    )

    import feedparser

    real_parse = feedparser.parse

    def fake_parse(url, *args, **kwargs):
        if "yahoo" in url.lower() or "yahoo" in str(url).lower():
            return real_parse(str(yahoo_path))
        if "google" in url.lower() or "google" in str(url).lower():
            return real_parse(str(google_path))
        return real_parse(url)

    with patch("ingestion.news.feedparser.parse", side_effect=fake_parse):
        result = fetch_news("AAPL")

    assert isinstance(result, list)
    assert len(result) > 0

    sources = {h.source for h in result}
    # All three sources represented (none should be totally swallowed by dedup).
    assert "yahoo-rss" in sources
    assert "google-news" in sources
    assert "finviz" in sources

    # Sorted by published_at desc with None last.
    timestamps = [h.published_at for h in result if h.published_at is not None]
    assert timestamps == sorted(timestamps, reverse=True)

    # Cross-source dedup ran: "apple beats q1 estimates" appears once (by
    # normalized title), not twice.
    normalized = [_normalize_title(h.title) for h in result]
    apple_beats_count = sum(1 for t in normalized if "apple beats q1 estimates" in t)
    assert apple_beats_count == 1, (
        f"expected dedup to leave exactly one 'apple beats q1 estimates' entry; "
        f"got {apple_beats_count}"
    )


def test_fetch_news_invalid_ticker_returns_empty():
    """fetch_news with a bad ticker returns []."""
    result = fetch_news("not a ticker!")
    assert result == []


# ---------- Phase 6 / Plan 06-01: return_raw flag ----------


@responses.activate
def test_fetch_news_with_raw_returns_tuple(fixtures_dir: Path):
    """Plan 06-01: fetch_news(ticker, return_raw=True) returns (list[Headline], list[dict]).

    The list[dict] is the raw `{source, published_at, title, url}` records used
    by Phase 6 storage to persist headlines into per-ticker JSONs (Wave 0
    amendment so the frontend deep-dive's news feed has source structured data
    without re-parsing).
    """
    yahoo_path = fixtures_dir / "yahoo_rss_aapl.xml"
    google_path = fixtures_dir / "google_news_aapl.xml"
    finviz_html = (fixtures_dir / "finviz_aapl.html").read_text()

    responses.add(
        responses.GET,
        FINVIZ_URL.format(ticker="AAPL"),
        body=finviz_html,
        status=200,
        content_type="text/html",
    )

    import feedparser

    real_parse = feedparser.parse

    def fake_parse(url, *args, **kwargs):
        if "yahoo" in str(url).lower():
            return real_parse(str(yahoo_path))
        if "google" in str(url).lower():
            return real_parse(str(google_path))
        return real_parse(url)

    with patch("ingestion.news.feedparser.parse", side_effect=fake_parse):
        result = fetch_news("AAPL", return_raw=True)

    assert isinstance(result, tuple)
    assert len(result) == 2
    headlines, raw = result

    assert isinstance(headlines, list)
    assert all(isinstance(h, Headline) for h in headlines)
    assert isinstance(raw, list)
    assert len(raw) == len(headlines)
    assert all(isinstance(d, dict) for d in raw)
    # Each raw dict carries the 4 keys the frontend deep-dive needs.
    for d in raw:
        assert set(d.keys()) >= {"source", "published_at", "title", "url"}
        assert isinstance(d["source"], str)
        assert isinstance(d["title"], str)
        assert isinstance(d["url"], str)
        # published_at is an ISO 8601 str OR None (RSS feeds sometimes lack pubdate).
        assert d["published_at"] is None or isinstance(d["published_at"], str)


def test_fetch_news_default_signature_unchanged():
    """fetch_news(ticker) (no return_raw flag) preserves the existing list[Headline] return.

    Existing call sites (ingestion/refresh.py:98) MUST remain compatible —
    Plan 06-01 adds an optional flag, NOT a breaking signature change.
    """
    # Bad ticker short-circuits to [] without any RSS fetch — exercises the
    # default-shape path without needing fixture mocking.
    result = fetch_news("not a ticker!")
    assert isinstance(result, list)
    assert result == []


@responses.activate
def test_fetch_news_continues_when_one_source_fails(fixtures_dir: Path):
    """Even if FinViz 500s, fetch_news still returns Yahoo + Google headlines."""
    yahoo_path = fixtures_dir / "yahoo_rss_aapl.xml"
    google_path = fixtures_dir / "google_news_aapl.xml"

    # FinViz 500 (4 responses for retry exhaustion).
    for _ in range(4):
        responses.add(
            responses.GET,
            FINVIZ_URL.format(ticker="AAPL"),
            body="oops",
            status=500,
        )

    import feedparser

    real_parse = feedparser.parse

    def fake_parse(url, *args, **kwargs):
        if "yahoo" in str(url).lower():
            return real_parse(str(yahoo_path))
        if "google" in str(url).lower():
            return real_parse(str(google_path))
        return real_parse(url)

    with patch("ingestion.news.feedparser.parse", side_effect=fake_parse):
        result = fetch_news("AAPL")

    sources = {h.source for h in result}
    assert "yahoo-rss" in sources
    assert "google-news" in sources
    # FinViz failed gracefully — no entries from it, but no exception either.
    assert "finviz" not in sources


# ---------- _parse_pubdate format coverage ----------


def test_parse_pubdate_handles_rfc822():
    from ingestion.news import _parse_pubdate
    dt = _parse_pubdate("Thu, 30 Apr 2026 09:15:00 -0400")
    assert dt is not None
    assert dt.year == 2026
    assert dt.tzinfo is not None


def test_parse_pubdate_handles_finviz_full_form():
    from ingestion.news import _parse_pubdate
    dt = _parse_pubdate("Apr-30-26 09:15AM")
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 4
    assert dt.day == 30
    assert dt.hour == 9
    assert dt.minute == 15


def test_parse_pubdate_returns_none_for_garbage():
    from ingestion.news import _parse_pubdate
    assert _parse_pubdate("not a date at all") is None
    assert _parse_pubdate("") is None
