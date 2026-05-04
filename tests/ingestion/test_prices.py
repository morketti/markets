"""Tests for ingestion/prices.py — fetch_prices(yfinance primary).

Probes covered here:
- 2-W2-01 → test_prices_happy
- 2-W2-02 → test_prices_empty (canonical) + test_prices_yfinance_fast_info_missing_falls_to_info (variant)
  (probe 2-W2-03 — yahooquery fallback success — lives in test_fallback.py)

All yfinance/yahooquery calls are patched at the import surface inside
ingestion.prices (i.e., `ingestion.prices.yfinance.Ticker` /
`ingestion.prices.yahooquery.Ticker`). Zero real network in this suite.

Fixture loading helpers live near the top of the file rather than in a shared
conftest because they are very specific to how yfinance returns data
(DataFrame with DatetimeIndex).
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import requests

from analysts.data.prices import PriceSnapshot
from ingestion.prices import fetch_prices


def _load_history_df(fixtures_dir: Path, name: str) -> pd.DataFrame:
    """Load a yfinance-history JSON fixture and reshape it as the DataFrame
    yfinance.Ticker(...).history() actually returns: DatetimeIndex of dates,
    columns Open/High/Low/Close/Volume (capitalized, as yfinance does)."""
    raw = json.loads((fixtures_dir / name).read_text())
    if not raw:
        return pd.DataFrame()
    df = pd.DataFrame.from_records(raw)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    # yfinance returns capitalized column names — mirror that
    df = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})
    return df


# Probe 2-W2-01
def test_prices_happy(fixtures_dir: Path) -> None:
    """yfinance returns 60-row history + valid fast_info → PriceSnapshot with current_price > 0."""
    df = _load_history_df(fixtures_dir, "yfinance_aapl_history.json")
    assert not df.empty
    assert len(df) == 60

    mock_ticker = MagicMock()
    mock_ticker.history.return_value = df
    mock_ticker.fast_info = {"last_price": 180.5, "lastPrice": 180.5}

    with patch("ingestion.prices.yfinance.Ticker", return_value=mock_ticker) as m:
        result = fetch_prices("AAPL")

    assert isinstance(result, PriceSnapshot)
    assert result.ticker == "AAPL"
    assert result.source == "yfinance"
    assert result.data_unavailable is False
    assert result.current_price == 180.5
    assert len(result.history) == 60
    assert result.history[0].close > 0
    assert result.history[0].volume >= 0
    # yfinance.Ticker called exactly once with the normalized symbol
    m.assert_called_once_with("AAPL")


# Probe 2-W2-02
def test_prices_empty(fixtures_dir: Path) -> None:
    """yfinance empty history + yahooquery also broken → data_unavailable=True."""
    empty_df = pd.DataFrame()  # what yfinance returns when scrape breaks

    mock_yf_ticker = MagicMock()
    mock_yf_ticker.history.return_value = empty_df
    # fast_info absent / raises
    type(mock_yf_ticker).fast_info = property(lambda self: (_ for _ in ()).throw(AttributeError("no fast_info")))
    mock_yf_ticker.info = {}  # info also empty

    # yahooquery fallback also broken — returns "Quote not found" string shape
    mock_yq_ticker = MagicMock()
    mock_yq_ticker.price = {"AAPL": "Quote not found"}

    with patch("ingestion.prices.yfinance.Ticker", return_value=mock_yf_ticker), \
         patch("ingestion.prices.yahooquery.Ticker", return_value=mock_yq_ticker):
        result = fetch_prices("AAPL")

    assert isinstance(result, PriceSnapshot)
    assert result.ticker == "AAPL"
    assert result.data_unavailable is True
    assert result.current_price is None
    assert result.history == []


# Probe 2-W2-02 (variant — fast_info missing but info has the key)
def test_prices_yfinance_fast_info_missing_falls_to_info(fixtures_dir: Path) -> None:
    """When .fast_info.last_price raises AttributeError, fall through to .info['regularMarketPrice']."""
    df = _load_history_df(fixtures_dir, "yfinance_aapl_history.json")

    mock_ticker = MagicMock()
    mock_ticker.history.return_value = df
    # fast_info exists but accessing .last_price raises AttributeError
    type(mock_ticker).fast_info = property(lambda self: (_ for _ in ()).throw(AttributeError("no last_price")))
    mock_ticker.info = {"regularMarketPrice": 175.0}

    with patch("ingestion.prices.yfinance.Ticker", return_value=mock_ticker):
        result = fetch_prices("AAPL")

    assert result.current_price == 175.0
    assert result.source == "yfinance"
    assert result.data_unavailable is False
    assert len(result.history) == 60


def test_prices_normalizes_ticker_for_yfinance_call(fixtures_dir: Path) -> None:
    """fetch_prices('brk.b') normalizes to 'BRK-B' (the form yfinance expects)
    BEFORE calling yfinance.Ticker — required for class-share lookups."""
    df = _load_history_df(fixtures_dir, "yfinance_aapl_history.json")

    mock_ticker = MagicMock()
    mock_ticker.history.return_value = df
    mock_ticker.fast_info = {"last_price": 500.0}

    with patch("ingestion.prices.yfinance.Ticker", return_value=mock_ticker) as m:
        result = fetch_prices("brk.b")

    m.assert_called_once_with("BRK-B")
    assert result.ticker == "BRK-B"
    assert result.source == "yfinance"


def test_prices_invalid_ticker_returns_unavailable() -> None:
    """A ticker that fails normalize_ticker (e.g., empty string) is reported as
    data_unavailable rather than raising — ingestion is forgiving by design."""
    # Even though the input is bad, we never construct a PriceSnapshot with that
    # input as ticker (the schema would reject); fetch_prices uses a placeholder.
    result = fetch_prices("")
    assert isinstance(result, PriceSnapshot)
    assert result.data_unavailable is True
    assert result.current_price is None
    assert result.history == []


def test_prices_yfinance_constructor_raises(fixtures_dir: Path) -> None:
    """If yfinance.Ticker(...) itself raises (e.g., requests timeout deep
    inside), fetch_prices should NOT propagate — falls through to yahooquery."""
    mock_yq_ticker = MagicMock()
    mock_yq_ticker.price = {"AAPL": "Quote not found"}

    with patch("ingestion.prices.yfinance.Ticker", side_effect=requests.exceptions.RequestException("net")), \
         patch("ingestion.prices.yahooquery.Ticker", return_value=mock_yq_ticker):
        result = fetch_prices("AAPL")

    assert isinstance(result, PriceSnapshot)
    assert result.data_unavailable is True


def test_prices_uses_history_close_when_fast_info_and_info_both_missing(fixtures_dir: Path) -> None:
    """Sanity-fallback path: yfinance returns history but neither fast_info
    nor info supply a positive current price. fetch_prices uses the most
    recent close as current_price (better than failing the whole snapshot).
    """
    df = _load_history_df(fixtures_dir, "yfinance_aapl_history.json")

    mock_ticker = MagicMock()
    mock_ticker.history.return_value = df
    # fast_info subscript raises KeyError (not AttributeError on the property)
    fast_info_mock = MagicMock()
    fast_info_mock.__getitem__.side_effect = KeyError("last_price")
    mock_ticker.fast_info = fast_info_mock
    # info also missing regularMarketPrice
    mock_ticker.info = {"longName": "Apple Inc."}

    with patch("ingestion.prices.yfinance.Ticker", return_value=mock_ticker):
        result = fetch_prices("AAPL")

    # Falls back to last bar close — known from fixture: 224.0
    assert result.source == "yfinance"
    assert result.data_unavailable is False
    assert result.current_price == 224.0
    assert len(result.history) == 60


def test_prices_yfinance_info_raises_falls_to_last_close(fixtures_dir: Path) -> None:
    """yfinance returns history but BOTH fast_info AND info raise exceptions
    (e.g., yfinance internal lazy-loader hit a 503). fetch_prices falls back
    to last bar close — exercises the info except-pass branch."""
    df = _load_history_df(fixtures_dir, "yfinance_aapl_history.json")

    mock_yf = MagicMock()
    mock_yf.history.return_value = df
    type(mock_yf).fast_info = property(
        lambda self: (_ for _ in ()).throw(AttributeError())
    )
    type(mock_yf).info = property(
        lambda self: (_ for _ in ()).throw(KeyError("info"))
    )

    with patch("ingestion.prices.yfinance.Ticker", return_value=mock_yf):
        result = fetch_prices("AAPL")

    # Should still succeed — falls back to last bar close (224.0 from fixture)
    assert result.source == "yfinance"
    assert result.data_unavailable is False
    assert result.current_price == 224.0


def test_prices_yfinance_zero_price_falls_through(fixtures_dir: Path) -> None:
    """yfinance returns history + fast_info reports last_price=0 (Pitfall #1
    sanity-check fails). With history non-empty and last close > 0, we fall
    back to last-bar close rather than declaring unavailable."""
    df = _load_history_df(fixtures_dir, "yfinance_aapl_history.json")

    mock_ticker = MagicMock()
    mock_ticker.history.return_value = df
    mock_ticker.fast_info = {"last_price": 0}  # broken price
    mock_ticker.info = {"regularMarketPrice": 0}  # also broken

    with patch("ingestion.prices.yfinance.Ticker", return_value=mock_ticker):
        result = fetch_prices("AAPL")

    # Falls back to last close (224.0) since neither fast_info nor info had a positive price.
    assert result.current_price == 224.0
    assert result.source == "yfinance"


def test_yahooquery_price_returns_non_dict(fixtures_dir: Path) -> None:
    """yahooquery's .price returns a non-dict (e.g., None or a list — has
    happened in older versions). fetch_prices treats this as a failed
    fallback and marks data_unavailable."""
    mock_yq_ticker = MagicMock()
    mock_yq_ticker.price = None  # not a dict

    mock_yf = MagicMock()
    mock_yf.history.return_value = pd.DataFrame()
    type(mock_yf).fast_info = property(lambda self: (_ for _ in ()).throw(AttributeError()))
    mock_yf.info = {}

    with patch("ingestion.prices.yfinance.Ticker", return_value=mock_yf), \
         patch("ingestion.prices.yahooquery.Ticker", return_value=mock_yq_ticker):
        result = fetch_prices("AAPL")

    assert result.data_unavailable is True


def test_yahooquery_price_dict_missing_regular_market_price(fixtures_dir: Path) -> None:
    """yahooquery returns the right shape but missing regularMarketPrice key
    (or it's not a number)."""
    mock_yq_ticker = MagicMock()
    mock_yq_ticker.price = {"AAPL": {"currency": "USD"}}  # dict but no price

    mock_yf = MagicMock()
    mock_yf.history.return_value = pd.DataFrame()
    type(mock_yf).fast_info = property(lambda self: (_ for _ in ()).throw(AttributeError()))
    mock_yf.info = {}

    with patch("ingestion.prices.yfinance.Ticker", return_value=mock_yf), \
         patch("ingestion.prices.yahooquery.Ticker", return_value=mock_yq_ticker):
        result = fetch_prices("AAPL")

    assert result.data_unavailable is True


# ---------------------------------------------------------------------------
# Plan 02-07 amendment: fetch_prices default period bumped 3mo → 1y
# ---------------------------------------------------------------------------


def test_fetch_prices_default_period_is_1y(fixtures_dir: Path) -> None:
    """fetch_prices called with NO period kwarg invokes yfinance's
    history(period=...) with period='1y' — enough trading bars (~252) for
    Phase 3's MA200 / 6m momentum / stable ADX without per-call overrides.
    Plan 02-07 amendment: bumped from '3mo' (~63 bars).
    """
    df = _load_history_df(fixtures_dir, "yfinance_aapl_history.json")

    mock_ticker = MagicMock()
    mock_ticker.history.return_value = df
    mock_ticker.fast_info = {"last_price": 180.5}

    with patch("ingestion.prices.yfinance.Ticker", return_value=mock_ticker):
        fetch_prices("AAPL")  # no period kwarg → must use the new "1y" default

    mock_ticker.history.assert_called_once_with(period="1y")


def test_fetch_prices_explicit_period_still_honored(fixtures_dir: Path) -> None:
    """Caller passing period='6mo' explicitly still gets the override —
    the default change is only visible when the kwarg is omitted, so existing
    callers that pin the period are unaffected."""
    df = _load_history_df(fixtures_dir, "yfinance_aapl_history.json")

    mock_ticker = MagicMock()
    mock_ticker.history.return_value = df
    mock_ticker.fast_info = {"last_price": 180.5}

    with patch("ingestion.prices.yfinance.Ticker", return_value=mock_ticker):
        fetch_prices("AAPL", period="6mo")

    mock_ticker.history.assert_called_once_with(period="6mo")


# ---------------------------------------------------------------------------
# Phase 8 / Plan 08-01 / Task 3 — explicit resilience tests for REFRESH-04.
# ---------------------------------------------------------------------------


def test_yfinance_throws_yahooquery_rescues(fixtures_dir: Path) -> None:
    """yfinance.Ticker raises on .history() call → yahooquery rescues; data_unavailable=False.

    Resilience guarantee: a single broken upstream library does NOT degrade
    the snapshot to data_unavailable when the alternate source is healthy.
    """
    mock_yf = MagicMock()
    mock_yf.history.side_effect = RuntimeError("yfinance scrape broke")

    mock_yq = MagicMock()
    mock_yq.price = {"AAPL": {"regularMarketPrice": 200.5, "currency": "USD"}}

    with patch("ingestion.prices.yfinance.Ticker", return_value=mock_yf), \
         patch("ingestion.prices.yahooquery.Ticker", return_value=mock_yq):
        result = fetch_prices("AAPL")

    assert isinstance(result, PriceSnapshot)
    assert result.data_unavailable is False
    assert result.current_price == 200.5
    assert result.source == "yahooquery"


def test_both_yfinance_and_yahooquery_throw(fixtures_dir: Path) -> None:
    """Both upstream libraries raise → data_unavailable=True; NO exception escapes.

    The "ingestion is forgiving by design" contract: data plane absorbs all
    upstream weather and surfaces a structured failure shape downstream
    (api/refresh.py maps this to the full-failure response envelope).
    """
    with patch(
        "ingestion.prices.yfinance.Ticker",
        side_effect=RuntimeError("yfinance entirely down"),
    ), patch(
        "ingestion.prices.yahooquery.Ticker",
        side_effect=RuntimeError("yahooquery entirely down"),
    ):
        result = fetch_prices("AAPL")

    assert isinstance(result, PriceSnapshot)
    assert result.data_unavailable is True
    assert result.current_price is None
    assert result.history == []
