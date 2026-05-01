"""Tests for ingestion/fundamentals.py — fetch_fundamentals(yfinance .info).

Probes covered here:
- 2-W2-04 → test_fund_happy
- 2-W2-05 → test_fund_missing

Fundamentals come from yfinance.Ticker(t).info — a dict that yfinance
populates from a Yahoo web-scrape. This dict is unstable: it can be `{}`
on a silent breakage day, it can be missing arbitrary keys, and it can
contain non-numeric strings ('Infinity', 'N/A') instead of numbers.
fetch_fundamentals MUST tolerate all of those failure modes without
raising — it returns FundamentalsSnapshot(data_unavailable=True) instead.

All yfinance calls are patched at the import surface
(`ingestion.fundamentals.yfinance.Ticker`). Zero real network in this suite.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from analysts.data.fundamentals import FundamentalsSnapshot
from ingestion.fundamentals import fetch_fundamentals


# Probe 2-W2-04
def test_fund_happy(fixtures_dir: Path) -> None:
    """yfinance.info populated → FundamentalsSnapshot with all metrics filled,
    data_unavailable=False, source='yfinance'."""
    info = json.loads((fixtures_dir / "yfinance_aapl_info.json").read_text())

    mock_ticker = MagicMock()
    mock_ticker.info = info

    with patch("ingestion.fundamentals.yfinance.Ticker", return_value=mock_ticker) as m:
        result = fetch_fundamentals("AAPL")

    assert isinstance(result, FundamentalsSnapshot)
    assert result.ticker == "AAPL"
    assert result.source == "yfinance"
    assert result.data_unavailable is False
    assert result.pe == 28.5
    assert result.ps == 7.2
    assert result.pb == 45.0
    assert result.roe == 1.65
    assert result.debt_to_equity == 1.85
    assert result.profit_margin == 0.25
    assert result.free_cash_flow == 100_000_000_000
    assert result.market_cap == 3_000_000_000_000
    m.assert_called_once_with("AAPL")


# Probe 2-W2-05
def test_fund_missing() -> None:
    """yfinance.info returns {} (silent breakage) → data_unavailable=True,
    all metric fields None, NO KeyError surfaces."""
    mock_ticker = MagicMock()
    mock_ticker.info = {}  # the canonical Pitfall #1 silent-breakage shape

    with patch("ingestion.fundamentals.yfinance.Ticker", return_value=mock_ticker):
        result = fetch_fundamentals("AAPL")

    assert isinstance(result, FundamentalsSnapshot)
    assert result.ticker == "AAPL"
    assert result.data_unavailable is True
    assert result.pe is None
    assert result.ps is None
    assert result.pb is None
    assert result.roe is None
    assert result.debt_to_equity is None
    assert result.profit_margin is None
    assert result.free_cash_flow is None
    assert result.market_cap is None


def test_fund_partial() -> None:
    """yfinance.info returns SOME keys → those are populated, others are None,
    data_unavailable is False (we treat 'some keys present' as available;
    downstream sanity checks decide if the snapshot is useful)."""
    mock_ticker = MagicMock()
    mock_ticker.info = {"trailingPE": 28.5, "marketCap": 3_000_000_000_000}

    with patch("ingestion.fundamentals.yfinance.Ticker", return_value=mock_ticker):
        result = fetch_fundamentals("AAPL")

    assert result.pe == 28.5
    assert result.market_cap == 3_000_000_000_000
    assert result.ps is None
    assert result.roe is None
    assert result.data_unavailable is False


def test_fund_yfinance_raises() -> None:
    """yfinance.Ticker(...) raises an arbitrary Exception → fetch_fundamentals
    catches and returns data_unavailable=True. NEVER propagates the exception."""
    with patch("ingestion.fundamentals.yfinance.Ticker", side_effect=RuntimeError("yf internals broke")):
        result = fetch_fundamentals("AAPL")

    assert isinstance(result, FundamentalsSnapshot)
    assert result.data_unavailable is True
    assert result.pe is None
    assert result.market_cap is None


def test_fund_normalizes_ticker() -> None:
    """fetch_fundamentals('BRK.B') normalizes to 'BRK-B' (yfinance class-share form)
    BEFORE calling yfinance.Ticker."""
    mock_ticker = MagicMock()
    mock_ticker.info = {"trailingPE": 22.0, "marketCap": 900_000_000_000}

    with patch("ingestion.fundamentals.yfinance.Ticker", return_value=mock_ticker) as m:
        result = fetch_fundamentals("BRK.B")

    m.assert_called_once_with("BRK-B")
    assert result.ticker == "BRK-B"
    assert result.source == "yfinance"


def test_fund_invalid_ticker_returns_unavailable() -> None:
    """A ticker that fails normalize_ticker (e.g., empty string) is reported as
    data_unavailable rather than raising."""
    result = fetch_fundamentals("")
    assert isinstance(result, FundamentalsSnapshot)
    assert result.data_unavailable is True


def test_fund_handles_non_numeric_values() -> None:
    """yfinance occasionally returns 'Infinity' or other strings for missing
    metrics. fetch_fundamentals must coerce non-numerics to None (NOT raise)."""
    mock_ticker = MagicMock()
    mock_ticker.info = {
        "trailingPE": "Infinity",         # non-numeric string
        "priceToSalesTrailing12Months": None,
        "priceToBook": float("nan"),       # NaN
        "returnOnEquity": 1.5,             # valid
        "debtToEquity": "N/A",
        "profitMargins": 0.20,             # valid
        "freeCashflow": -50_000_000,       # negative is valid for FCF
        "marketCap": 1_000_000_000_000,
    }

    with patch("ingestion.fundamentals.yfinance.Ticker", return_value=mock_ticker):
        result = fetch_fundamentals("AAPL")

    # Non-numeric / NaN coerced to None
    assert result.pe is None
    assert result.ps is None
    assert result.pb is None
    assert result.debt_to_equity is None
    # Valid values preserved
    assert result.roe == 1.5
    assert result.profit_margin == 0.20
    assert result.free_cash_flow == -50_000_000  # negative FCF allowed
    assert result.market_cap == 1_000_000_000_000
    # data_unavailable=False because trailingPE IS present (just non-numeric);
    # the canonical-marker check considers presence, not value.
    # Actually — we check pe (after coercion) and market_cap; market_cap is set, so available.
    assert result.data_unavailable is False
