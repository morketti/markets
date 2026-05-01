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
import pytest
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
