"""Tests for the yahooquery fallback path in ingestion/prices.py.

Probe 2-W2-03 — yfinance empty → yahooquery success path.

The yahooquery .price endpoint does NOT supply OHLC history (only a current
quote dict). For the fallback we accept current_price + empty history; that's
documented in 02-RESEARCH.md ("yahooquery fallback") as a deliberate limitation.

All calls are patched. Zero real network.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import requests

from analysts.data.prices import PriceSnapshot
from ingestion.prices import fetch_prices


def _empty_yfinance_mock() -> MagicMock:
    """Return a MagicMock that simulates yfinance returning an empty
    DataFrame from .history() and a missing fast_info — the canonical
    'silent-breakage' shape from Pitfall #1."""
    m = MagicMock()
    m.history.return_value = pd.DataFrame()
    type(m).fast_info = property(lambda self: (_ for _ in ()).throw(AttributeError("no fast_info")))
    m.info = {}
    return m


# Probe 2-W2-03
def test_yfinance_empty_yahooquery_succeeds(fixtures_dir: Path) -> None:
    """yfinance returns empty AND yahooquery has data → PriceSnapshot with source='yahooquery'.

    Asserts the full handoff from primary to fallback happens cleanly. The
    snapshot's history is empty (yahooquery .price doesn't supply bars), but
    current_price is set and source is 'yahooquery'.
    """
    yq_data = json.loads((fixtures_dir / "yahooquery_aapl_price.json").read_text())

    mock_yq_ticker = MagicMock()
    mock_yq_ticker.price = yq_data

    with patch("ingestion.prices.yfinance.Ticker", return_value=_empty_yfinance_mock()), \
         patch("ingestion.prices.yahooquery.Ticker", return_value=mock_yq_ticker) as yq_m:
        result = fetch_prices("AAPL")

    assert isinstance(result, PriceSnapshot)
    assert result.source == "yahooquery"
    assert result.data_unavailable is False
    assert result.current_price == 178.0
    assert result.history == []
    # yahooquery.Ticker called with normalized form
    yq_m.assert_called_once_with("AAPL")


def test_yahooquery_quote_not_found(fixtures_dir: Path) -> None:
    """yahooquery's actual error shape: .price[ticker] is a string ('Quote not
    found') instead of a dict. fetch_prices must handle this WITHOUT a
    TypeError — both sources failed → data_unavailable=True. The `source`
    field in this all-failed branch is whichever was the last attempted; the
    caller should look at data_unavailable, not source ID, when nothing worked.
    """
    mock_yq_ticker = MagicMock()
    mock_yq_ticker.price = {"AAPL": "Quote not found"}

    with patch("ingestion.prices.yfinance.Ticker", return_value=_empty_yfinance_mock()), \
         patch("ingestion.prices.yahooquery.Ticker", return_value=mock_yq_ticker):
        result = fetch_prices("AAPL")

    assert isinstance(result, PriceSnapshot)
    assert result.data_unavailable is True
    assert result.current_price is None
    assert result.source in ("yfinance", "yahooquery")  # caller cares about data_unavailable


def test_yahooquery_network_error(fixtures_dir: Path) -> None:
    """yahooquery raises requests.exceptions.RequestException → fetch_prices
    catches and marks data_unavailable, never propagates."""
    mock_yq_ticker = MagicMock()
    type(mock_yq_ticker).price = property(
        lambda self: (_ for _ in ()).throw(requests.exceptions.RequestException("net dead"))
    )

    with patch("ingestion.prices.yfinance.Ticker", return_value=_empty_yfinance_mock()), \
         patch("ingestion.prices.yahooquery.Ticker", return_value=mock_yq_ticker):
        result = fetch_prices("AAPL")

    assert isinstance(result, PriceSnapshot)
    assert result.data_unavailable is True
