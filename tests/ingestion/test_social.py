"""Tests for ingestion/social.py — Reddit RSS + StockTwits anonymous fetch (Plan 02-05).

Probes covered:
- 2-W2-14: Reddit RSS happy path — fixture XML → list[RedditPost], non-default UA verified
- 2-W2-15: StockTwits trending — fixture JSON → list[ticker symbols, uppercase]
- 2-W2-16: StockTwits per-symbol stream — fixture JSON → list[StockTwitsPost] of 30 messages

Zero real network: every HTTP call is mocked via the `responses` library.
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import pytest
import responses

from analysts.data.social import RedditPost, SocialSignal, StockTwitsPost
from ingestion.social import (
    REDDIT_SEARCH_URL,
    REDDIT_USER_AGENT,
    STOCKTWITS_STREAM_URL,
    STOCKTWITS_TRENDING_URL,
    _fetch_reddit_search,
    _fetch_stocktwits_stream,
    _fetch_stocktwits_trending,
    fetch_social,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def reddit_aapl_xml(fixtures_dir: Path) -> str:
    return (fixtures_dir / "reddit_search_aapl.xml").read_text(encoding="utf-8")


@pytest.fixture
def stocktwits_trending_json(fixtures_dir: Path) -> str:
    return (fixtures_dir / "stocktwits_trending.json").read_text(encoding="utf-8")


@pytest.fixture
def stocktwits_aapl_json(fixtures_dir: Path) -> str:
    return (fixtures_dir / "stocktwits_aapl.json").read_text(encoding="utf-8")


def _reddit_url_for(ticker: str) -> str:
    """Recreate the URL the implementation will hit so responses can match exactly."""
    query = quote(f"{ticker} OR ${ticker}")
    return REDDIT_SEARCH_URL.format(query=query)


def _stream_url_for(ticker: str) -> str:
    return STOCKTWITS_STREAM_URL.format(ticker=ticker)


# ---------------------------------------------------------------------------
# Reddit RSS — Probe 2-W2-14
# ---------------------------------------------------------------------------


@responses.activate
def test_reddit(reddit_aapl_xml: str):
    """Probe 2-W2-14: Reddit RSS happy path — fixture XML parses into ≥5 RedditPosts."""
    responses.add(
        responses.GET,
        _reddit_url_for("AAPL"),
        body=reddit_aapl_xml,
        status=200,
        content_type="application/atom+xml",
    )

    posts = _fetch_reddit_search("AAPL")

    assert isinstance(posts, list)
    assert len(posts) >= 5
    for p in posts:
        assert isinstance(p, RedditPost)
        assert p.title  # non-empty
        assert p.url.startswith("https://")
        assert p.subreddit  # non-empty
    # The fixture covers three subreddits
    subs = {p.subreddit.lower() for p in posts}
    assert {"wallstreetbets", "stocks", "investing"}.issubset(subs)


@responses.activate
def test_reddit_user_agent_is_non_default(reddit_aapl_xml: str):
    """Probe 2-W2-14 variant: Reddit calls MUST send REDDIT_USER_AGENT, NOT the EDGAR UA."""
    responses.add(
        responses.GET,
        _reddit_url_for("AAPL"),
        body=reddit_aapl_xml,
        status=200,
        content_type="application/atom+xml",
    )

    _fetch_reddit_search("AAPL")

    assert len(responses.calls) == 1
    sent_ua = responses.calls[0].request.headers["User-Agent"]
    assert sent_ua == REDDIT_USER_AGENT
    # Verify it is NOT the EDGAR-compliant default the shared session carries
    assert "Markets Personal Research" not in sent_ua


@responses.activate
def test_reddit_429_returns_empty():
    """Reddit 429 after retries → empty list (per-source failure isolated)."""
    # Shared session retry adapter retries 429 up to 3 times. Register 4 consecutive
    # 429 responses so the adapter exhausts retries and the final response is 429.
    url = _reddit_url_for("AAPL")
    for _ in range(4):
        responses.add(responses.GET, url, body="rate limited", status=429)

    posts = _fetch_reddit_search("AAPL")

    assert posts == []


@responses.activate
def test_reddit_malformed_xml_returns_empty():
    """If the body cannot be parsed, _fetch_reddit_search returns [] (does not raise)."""
    responses.add(
        responses.GET,
        _reddit_url_for("AAPL"),
        body="<not><valid></xml",
        status=200,
        content_type="application/atom+xml",
    )

    # feedparser is lenient; even garbage usually yields an empty entry list.
    # Either way, the function must not raise.
    posts = _fetch_reddit_search("AAPL")
    assert posts == []


# ---------------------------------------------------------------------------
# StockTwits trending — Probe 2-W2-15
# ---------------------------------------------------------------------------


@responses.activate
def test_trending(stocktwits_trending_json: str):
    """Probe 2-W2-15: trending fixture → list of uppercase symbols in fixture order."""
    responses.add(
        responses.GET,
        STOCKTWITS_TRENDING_URL,
        body=stocktwits_trending_json,
        status=200,
        content_type="application/json",
    )

    trending = _fetch_stocktwits_trending()

    assert isinstance(trending, list)
    assert all(isinstance(s, str) for s in trending)
    assert all(s == s.upper() for s in trending)
    assert trending == ["TSLA", "AAPL", "NVDA", "GME", "AMC"]


@responses.activate
def test_trending_failure_returns_empty():
    """5xx after retries → empty list (per-source failure isolated)."""
    for _ in range(4):
        responses.add(responses.GET, STOCKTWITS_TRENDING_URL, body="server error", status=500)
    assert _fetch_stocktwits_trending() == []


@responses.activate
def test_trending_malformed_json_returns_empty():
    """200 with non-JSON body → empty list, no exception escapes."""
    responses.add(
        responses.GET,
        STOCKTWITS_TRENDING_URL,
        body="not json",
        status=200,
        content_type="application/json",
    )
    assert _fetch_stocktwits_trending() == []


# ---------------------------------------------------------------------------
# StockTwits per-symbol — Probe 2-W2-16
# ---------------------------------------------------------------------------


@responses.activate
def test_per_symbol(stocktwits_aapl_json: str):
    """Probe 2-W2-16: per-symbol fixture → list[StockTwitsPost] length 30, sentiment lowercased."""
    responses.add(
        responses.GET,
        _stream_url_for("AAPL"),
        body=stocktwits_aapl_json,
        status=200,
        content_type="application/json",
    )

    posts = _fetch_stocktwits_stream("AAPL")

    assert isinstance(posts, list)
    assert len(posts) == 30
    for p in posts:
        assert isinstance(p, StockTwitsPost)
        assert p.body  # non-empty
    # Sentiment is normalized to lowercase Literal
    bullish = [p for p in posts if p.sentiment == "bullish"]
    bearish = [p for p in posts if p.sentiment == "bearish"]
    untagged = [p for p in posts if p.sentiment is None]
    assert len(bullish) > 0
    assert len(bearish) > 0
    assert len(untagged) > 0
    # Sentiment must only ever be exactly "bullish" / "bearish" / None — schema-enforced
    assert {p.sentiment for p in posts} <= {"bullish", "bearish", None}


@responses.activate
def test_per_symbol_no_messages():
    """Empty messages array → empty list (not data_unavailable; that's caller's call)."""
    responses.add(
        responses.GET,
        _stream_url_for("AAPL"),
        body='{"response": {"status": 200}, "messages": []}',
        status=200,
        content_type="application/json",
    )
    assert _fetch_stocktwits_stream("AAPL") == []


@responses.activate
def test_per_symbol_failure_returns_empty():
    for _ in range(4):
        responses.add(responses.GET, _stream_url_for("AAPL"), body="oops", status=500)
    assert _fetch_stocktwits_stream("AAPL") == []


# ---------------------------------------------------------------------------
# Aggregator — fetch_social
# ---------------------------------------------------------------------------


@responses.activate
def test_fetch_social_aggregates(
    reddit_aapl_xml: str, stocktwits_trending_json: str, stocktwits_aapl_json: str
):
    """All three sources respond → SocialSignal aggregates posts, trending_rank set."""
    responses.add(
        responses.GET,
        _reddit_url_for("AAPL"),
        body=reddit_aapl_xml,
        status=200,
        content_type="application/atom+xml",
    )
    responses.add(
        responses.GET,
        STOCKTWITS_TRENDING_URL,
        body=stocktwits_trending_json,
        status=200,
        content_type="application/json",
    )
    responses.add(
        responses.GET,
        _stream_url_for("AAPL"),
        body=stocktwits_aapl_json,
        status=200,
        content_type="application/json",
    )

    sig = fetch_social("AAPL")

    assert isinstance(sig, SocialSignal)
    assert sig.ticker == "AAPL"
    assert sig.source == "combined"
    assert sig.data_unavailable is False
    assert len(sig.reddit_posts) >= 5
    assert len(sig.stocktwits_posts) == 30
    # AAPL is the 2nd entry in the trending fixture → rank=2 (1-based)
    assert sig.trending_rank == 2


@responses.activate
def test_fetch_social_all_sources_fail():
    """All three endpoints 500 → SocialSignal.data_unavailable=True, all collections empty."""
    for _ in range(4):
        responses.add(responses.GET, _reddit_url_for("AAPL"), body="x", status=500)
        responses.add(responses.GET, STOCKTWITS_TRENDING_URL, body="x", status=500)
        responses.add(responses.GET, _stream_url_for("AAPL"), body="x", status=500)

    sig = fetch_social("AAPL")

    assert sig.data_unavailable is True
    assert sig.reddit_posts == []
    assert sig.stocktwits_posts == []
    assert sig.trending_rank is None


@responses.activate
def test_fetch_social_partial_failure(stocktwits_aapl_json: str, stocktwits_trending_json: str):
    """Reddit dies, StockTwits works → data_unavailable False; reddit_posts=[]; stocktwits non-empty."""
    for _ in range(4):
        responses.add(responses.GET, _reddit_url_for("AAPL"), body="x", status=500)
    responses.add(
        responses.GET,
        STOCKTWITS_TRENDING_URL,
        body=stocktwits_trending_json,
        status=200,
        content_type="application/json",
    )
    responses.add(
        responses.GET,
        _stream_url_for("AAPL"),
        body=stocktwits_aapl_json,
        status=200,
        content_type="application/json",
    )

    sig = fetch_social("AAPL")

    assert sig.data_unavailable is False
    assert sig.reddit_posts == []
    assert len(sig.stocktwits_posts) == 30
    assert sig.trending_rank == 2


@responses.activate
def test_fetch_social_unknown_ticker_off_trending(
    reddit_aapl_xml: str, stocktwits_trending_json: str, stocktwits_aapl_json: str
):
    """A ticker not in the trending list → trending_rank=None even if other sources succeed."""
    responses.add(
        responses.GET,
        _reddit_url_for("ZZZZ"),
        body=reddit_aapl_xml,  # body content doesn't matter for this assertion
        status=200,
        content_type="application/atom+xml",
    )
    responses.add(
        responses.GET,
        STOCKTWITS_TRENDING_URL,
        body=stocktwits_trending_json,
        status=200,
        content_type="application/json",
    )
    responses.add(
        responses.GET,
        _stream_url_for("ZZZZ"),
        body=stocktwits_aapl_json,
        status=200,
        content_type="application/json",
    )

    sig = fetch_social("ZZZZ")

    assert sig.ticker == "ZZZZ"
    assert sig.trending_rank is None
    # Other sources still aggregated
    assert sig.data_unavailable is False


def test_fetch_social_invalid_ticker():
    """Invalid input → data_unavailable=True without any HTTP calls."""
    # Garbage that won't normalize. With responses NOT activated, any HTTP call
    # would raise — confirming we short-circuit before touching the network.
    sig = fetch_social("not a ticker!!")
    assert sig.data_unavailable is True
    assert sig.reddit_posts == []
    assert sig.stocktwits_posts == []
    assert sig.trending_rank is None


# ---------------------------------------------------------------------------
# Coverage-completing tests — defensive paths
# ---------------------------------------------------------------------------


@responses.activate
def test_reddit_http_layer_exception(monkeypatch):
    """A requests-layer exception (connection error) → empty list."""
    from ingestion import social as social_module

    class _BoomSession:
        headers = {"User-Agent": "test"}

        def get(self, *args, **kwargs):
            raise ConnectionError("DNS exploded")

    monkeypatch.setattr(social_module, "get_session", lambda: _BoomSession())
    assert _fetch_reddit_search("AAPL") == []


def test_stocktwits_trending_http_layer_exception(monkeypatch):
    """A requests-layer exception on trending → empty list."""
    from ingestion import social as social_module

    class _BoomSession:
        def get(self, *args, **kwargs):
            raise ConnectionError("network down")

    monkeypatch.setattr(social_module, "get_session", lambda: _BoomSession())
    assert _fetch_stocktwits_trending() == []


def test_stocktwits_stream_http_layer_exception(monkeypatch):
    """A requests-layer exception on stream → empty list."""
    from ingestion import social as social_module

    class _BoomSession:
        def get(self, *args, **kwargs):
            raise ConnectionError("network down")

    monkeypatch.setattr(social_module, "get_session", lambda: _BoomSession())
    assert _fetch_stocktwits_stream("AAPL") == []


@responses.activate
def test_stocktwits_stream_malformed_json():
    """200 with non-JSON body on stream → empty list."""
    responses.add(
        responses.GET,
        _stream_url_for("AAPL"),
        body="not json at all",
        status=200,
        content_type="application/json",
    )
    assert _fetch_stocktwits_stream("AAPL") == []


@responses.activate
def test_stocktwits_trending_top_level_not_dict():
    """200 with JSON array (not dict) on trending → empty list."""
    responses.add(
        responses.GET,
        STOCKTWITS_TRENDING_URL,
        body='["TSLA", "AAPL"]',
        status=200,
        content_type="application/json",
    )
    assert _fetch_stocktwits_trending() == []


@responses.activate
def test_stocktwits_trending_drops_malformed_entries():
    """Entries that are not dicts or lack 'symbol' key are filtered out."""
    body = (
        '{"response": {"status": 200}, "symbols": ['
        '"not_a_dict",'
        '{"no_symbol": "TSLA"},'
        '{"symbol": null},'
        '{"symbol": ""},'
        '{"symbol": "valid"}'
        ']}'
    )
    responses.add(
        responses.GET,
        STOCKTWITS_TRENDING_URL,
        body=body,
        status=200,
        content_type="application/json",
    )
    assert _fetch_stocktwits_trending() == ["VALID"]


@responses.activate
def test_stocktwits_stream_top_level_not_dict():
    """200 with JSON array (not dict) on stream → empty list."""
    responses.add(
        responses.GET,
        _stream_url_for("AAPL"),
        body='["whatever"]',
        status=200,
        content_type="application/json",
    )
    assert _fetch_stocktwits_stream("AAPL") == []


@responses.activate
def test_stocktwits_stream_drops_malformed_messages():
    """Messages missing body / non-dict / empty body are skipped; valid ones survive."""
    body = (
        '{"response": {"status": 200}, "messages": ['
        '"not_a_dict",'
        '{"id": 1},'
        '{"id": 2, "body": ""},'
        '{"id": 3, "body": "   "},'
        '{"id": 4, "body": "good post", "created_at": "not-an-iso", "entities": null},'
        '{"id": 5, "body": "novel sentiment", "entities": {"sentiment": {"basic": "Neutral"}}},'
        '{"id": 6, "body": "non-dict sentiment", "entities": {"sentiment": "weird"}},'
        '{"id": 7, "body": "non-string basic", "entities": {"sentiment": {"basic": 42}}}'
        ']}'
    )
    responses.add(
        responses.GET,
        _stream_url_for("AAPL"),
        body=body,
        status=200,
        content_type="application/json",
    )
    posts = _fetch_stocktwits_stream("AAPL")
    # All 4 well-formed bodies (ids 4,5,6,7) survive; sentiment normalizes to None for non-bull/bear
    assert len(posts) == 4
    assert all(p.sentiment is None for p in posts)
    # The bad created_at on id=4 falls back to None
    assert posts[0].created_at is None


@responses.activate
def test_reddit_drops_entries_without_subreddit_or_link():
    """Entries with empty title, missing link, non-http link, or no subreddit get skipped."""
    bad_xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>broken results</title>
  <entry>
    <title></title>
    <link href="https://www.reddit.com/r/wallstreetbets/comments/x/y/"/>
    <id>t3_empty_title</id>
  </entry>
  <entry>
    <title>Valid title but no link</title>
    <id>t3_no_link</id>
  </entry>
  <entry>
    <title>Title with non-http link</title>
    <link href="ftp://reddit.com/foo"/>
    <id>t3_bad_scheme</id>
  </entry>
  <entry>
    <title>Title with link but no subreddit</title>
    <link href="https://www.reddit.com/some/other/path/"/>
    <id>t3_no_subreddit</id>
  </entry>
  <entry>
    <title>Falls back to category tag</title>
    <link href="https://www.reddit.com/some/other/path/"/>
    <category term="stocks" label="r/stocks"/>
    <id>t3_category_fallback</id>
    <updated>2026-04-30T15:00:00+00:00</updated>
    <published>2026-04-30T15:00:00+00:00</published>
  </entry>
  <entry>
    <title>Valid normal entry</title>
    <link href="https://www.reddit.com/r/investing/comments/abc/def/"/>
    <id>t3_normal</id>
  </entry>
</feed>
"""
    responses.add(
        responses.GET,
        _reddit_url_for("AAPL"),
        body=bad_xml,
        status=200,
        content_type="application/atom+xml",
    )
    posts = _fetch_reddit_search("AAPL")
    # 2 should survive: the category-fallback one and the normal one
    titles = [p.title for p in posts]
    subs = [p.subreddit for p in posts]
    assert "Falls back to category tag" in titles
    assert "Valid normal entry" in titles
    assert "stocks" in subs
    assert "investing" in subs
    # The 4 broken entries are filtered out
    assert len(posts) == 2


@responses.activate
def test_reddit_long_title_truncated_not_rejected():
    """A title over 500 chars is sliced to 500 (max_length) — not dropped."""
    long_title = "AAPL " * 200  # 1000 chars
    long_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>long-title test</title>
  <entry>
    <title>{long_title}</title>
    <link href="https://www.reddit.com/r/wallstreetbets/comments/abc/def/"/>
    <id>t3_long</id>
  </entry>
</feed>
"""
    responses.add(
        responses.GET,
        _reddit_url_for("AAPL"),
        body=long_xml,
        status=200,
        content_type="application/atom+xml",
    )
    posts = _fetch_reddit_search("AAPL")
    assert len(posts) == 1
    assert len(posts[0].title) == 500
    assert posts[0].subreddit == "wallstreetbets"


def test_parse_iso8601_handles_bad_input():
    """Internal helper: None / empty / non-string / unparseable returns None."""
    from ingestion.social import _parse_iso8601

    assert _parse_iso8601(None) is None
    assert _parse_iso8601("") is None
    assert _parse_iso8601(12345) is None  # non-string
    assert _parse_iso8601("totally not a date") is None
    # Valid Z-form parses
    dt = _parse_iso8601("2026-04-30T13:15:00Z")
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 4
    assert dt.tzinfo is not None
