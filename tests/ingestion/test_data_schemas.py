"""Probe 2-W1-03 (data schemas slice) — Pydantic shape validation across all
five ingested-data domains.

Each schema:
- Includes ticker (normalized via analysts.schemas.normalize_ticker),
  fetched_at: datetime, source: Literal[...], data_unavailable: bool=False.
- Round-trips byte-stable via model_dump_json + model_validate_json on the
  happy path.
- Rejects obvious garbage (negative prices, empty titles, unknown form types,
  bad source values).

Names mirror the canonical happy-path-and-bad-data pattern from
analysts/schemas tests in Phase 1.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from analysts.data.filings import FilingMetadata
from analysts.data.fundamentals import FundamentalsSnapshot
from analysts.data.news import Headline
from analysts.data.prices import OHLCBar, PriceSnapshot
from analysts.data.social import RedditPost, SocialSignal, StockTwitsPost

UTC = timezone.utc
NOW = datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC)


# ----- PriceSnapshot / OHLCBar -----


def test_price_snapshot_happy() -> None:
    snap = PriceSnapshot(
        ticker="AAPL",
        fetched_at=NOW,
        source="yfinance",
        current_price=180.5,
    )
    j = snap.model_dump_json()
    snap2 = PriceSnapshot.model_validate_json(j)
    assert snap2 == snap
    assert snap2.ticker == "AAPL"
    assert snap2.source == "yfinance"
    assert snap2.data_unavailable is False
    assert snap2.history == []


def test_price_snapshot_normalizes_ticker() -> None:
    snap = PriceSnapshot(ticker="brk.b", fetched_at=NOW, source="yfinance")
    assert snap.ticker == "BRK-B"


def test_price_snapshot_rejects_negative_price() -> None:
    with pytest.raises(ValidationError):
        PriceSnapshot(ticker="AAPL", fetched_at=NOW, source="yfinance", current_price=-1.0)


def test_price_snapshot_rejects_bad_source() -> None:
    with pytest.raises(ValidationError):
        PriceSnapshot(ticker="AAPL", fetched_at=NOW, source="finnhub")  # type: ignore[arg-type]


def test_ohlc_bar_validates() -> None:
    bar = OHLCBar(
        date=date(2026, 5, 1), open=180, high=185, low=179, close=183, volume=1_000_000
    )
    assert bar.volume == 1_000_000
    with pytest.raises(ValidationError):
        OHLCBar(date=date(2026, 5, 1), open=180, high=185, low=179, close=183, volume=-1)


def test_price_snapshot_with_history_round_trip() -> None:
    snap = PriceSnapshot(
        ticker="AAPL",
        fetched_at=NOW,
        source="yfinance",
        current_price=180.5,
        history=[
            OHLCBar(date=date(2026, 4, 30), open=178, high=181, low=177, close=180, volume=5_000_000)
        ],
    )
    j = snap.model_dump_json()
    snap2 = PriceSnapshot.model_validate_json(j)
    assert snap2.history[0].close == 180.0


# ----- FundamentalsSnapshot -----


def test_fundamentals_snapshot_happy() -> None:
    snap = FundamentalsSnapshot(ticker="NVDA", fetched_at=NOW, source="yfinance")
    assert snap.pe is None
    assert snap.data_unavailable is False
    j = snap.model_dump_json()
    assert FundamentalsSnapshot.model_validate_json(j) == snap


def test_fundamentals_snapshot_data_unavailable() -> None:
    snap = FundamentalsSnapshot(
        ticker="NVDA", fetched_at=NOW, source="yfinance", data_unavailable=True
    )
    assert snap.data_unavailable is True


def test_fundamentals_rejects_bad_ticker() -> None:
    with pytest.raises(ValidationError):
        FundamentalsSnapshot(ticker="123!@#", fetched_at=NOW, source="yfinance")


def test_fundamentals_allows_negative_fcf() -> None:
    # Free cash flow can legitimately be negative (cash-burning growth co.).
    snap = FundamentalsSnapshot(
        ticker="GME", fetched_at=NOW, source="yfinance", free_cash_flow=-1_000_000.0
    )
    assert snap.free_cash_flow == -1_000_000.0


# ----- FilingMetadata -----


def test_filing_metadata_happy() -> None:
    f = FilingMetadata(
        ticker="AAPL",
        fetched_at=NOW,
        form_type="10-K",
        filed_date=date(2026, 4, 1),
        accession_number="0000320193-26-000001",
        cik="0000320193",
    )
    assert f.source == "edgar"
    assert f.summary == ""
    j = f.model_dump_json()
    assert FilingMetadata.model_validate_json(j) == f


def test_filing_metadata_rejects_unknown_form() -> None:
    with pytest.raises(ValidationError):
        FilingMetadata(ticker="AAPL", fetched_at=NOW, form_type="13F")  # type: ignore[arg-type]


def test_filing_metadata_other_form_allowed() -> None:
    f = FilingMetadata(ticker="AAPL", fetched_at=NOW, form_type="OTHER")
    assert f.form_type == "OTHER"


def test_filing_metadata_rejects_bad_cik() -> None:
    with pytest.raises(ValidationError):
        FilingMetadata(ticker="AAPL", fetched_at=NOW, form_type="10-K", cik="320193")  # not 10-digit


# ----- Headline -----


def test_headline_happy() -> None:
    h = Headline(
        ticker="AAPL",
        fetched_at=NOW,
        source="yahoo-rss",
        title="Apple beats expectations",
        url="https://news.example.test/aapl",
        dedup_key="yahoo-rss::abc123",
    )
    j = h.model_dump_json()
    assert Headline.model_validate_json(j) == h
    assert h.summary == ""


def test_headline_rejects_empty_title() -> None:
    with pytest.raises(ValidationError):
        Headline(
            ticker="AAPL",
            fetched_at=NOW,
            source="yahoo-rss",
            title="",
            url="https://x.test",
            dedup_key="x::1",
        )


def test_headline_rejects_overlong_title() -> None:
    with pytest.raises(ValidationError):
        Headline(
            ticker="AAPL",
            fetched_at=NOW,
            source="yahoo-rss",
            title="x" * 501,
            url="https://x.test",
            dedup_key="x::1",
        )


# ----- SocialSignal / RedditPost / StockTwitsPost -----


def test_social_signal_happy() -> None:
    sig = SocialSignal(
        ticker="GME",
        fetched_at=NOW,
        reddit_posts=[
            RedditPost(title="GME to the moon", url="https://reddit.com/r/wsb/x", subreddit="wsb")
        ],
        stocktwits_posts=[
            StockTwitsPost(body="bullish on GME", sentiment="bullish")
        ],
    )
    j = sig.model_dump_json()
    sig2 = SocialSignal.model_validate_json(j)
    assert sig2 == sig
    assert sig.source == "combined"


def test_social_signal_empty_collections_ok() -> None:
    sig = SocialSignal(ticker="GME", fetched_at=NOW, data_unavailable=True)
    assert sig.reddit_posts == []
    assert sig.stocktwits_posts == []
    assert sig.data_unavailable is True


def test_stocktwits_post_rejects_bad_sentiment() -> None:
    with pytest.raises(ValidationError):
        StockTwitsPost(body="meh", sentiment="neutral")  # type: ignore[arg-type]


def test_reddit_post_rejects_empty_title() -> None:
    with pytest.raises(ValidationError):
        RedditPost(title="", url="https://reddit.com/x", subreddit="wsb")


def test_schemas_reject_non_string_ticker() -> None:
    """Cover the isinstance-False branch in every _normalize_ticker_field validator."""
    bad: object = 123  # int instead of str — covers `isinstance(v, str)` False path
    with pytest.raises(ValidationError):
        PriceSnapshot(ticker=bad, fetched_at=NOW, source="yfinance")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        FundamentalsSnapshot(ticker=bad, fetched_at=NOW, source="yfinance")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        FilingMetadata(ticker=bad, fetched_at=NOW, form_type="10-K")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        Headline(
            ticker=bad,  # type: ignore[arg-type]
            fetched_at=NOW,
            source="yahoo-rss",
            title="x",
            url="https://x.test",
            dedup_key="x::1",
        )
    with pytest.raises(ValidationError):
        SocialSignal(ticker=bad, fetched_at=NOW)  # type: ignore[arg-type]


def test_data_re_exports() -> None:
    """analysts.data top-level re-exports everything."""
    from analysts.data import (
        FilingMetadata as FM,
        FundamentalsSnapshot as FS,
        Headline as H,
        OHLCBar as OB,
        PriceSnapshot as PS,
        RedditPost as RP,
        SocialSignal as SS,
        StockTwitsPost as ST,
    )

    assert FM is FilingMetadata
    assert FS is FundamentalsSnapshot
    assert H is Headline
    assert OB is OHLCBar
    assert PS is PriceSnapshot
    assert RP is RedditPost
    assert SS is SocialSignal
    assert ST is StockTwitsPost
