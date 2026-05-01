"""Tests for ingestion/fundamentals.py — fetch_fundamentals(yfinance .info).

Probes covered here:
- 2-W2-04 → test_fund_happy
- 2-W2-05 → test_fund_missing

Plan 02-07 amendment tests (analyst-consensus fields) appended at the end:
- test_fundamentals_snapshot_accepts_analyst_fields_when_provided
- test_fundamentals_snapshot_accepts_analyst_fields_when_omitted
- test_fundamentals_snapshot_opinion_count_float_coercion
- test_fundamentals_snapshot_extra_forbid_still_active
- test_fetch_fundamentals_populates_analyst_fields
- test_fetch_fundamentals_handles_missing_analyst_fields
- test_fetch_fundamentals_handles_partial_analyst_fields
- test_fetch_fundamentals_handles_non_numeric_analyst_fields
- test_safe_int_helper

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
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

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


# ---------------------------------------------------------------------------
# Plan 02-07 amendment: analyst-consensus schema additions
# ---------------------------------------------------------------------------


def test_fundamentals_snapshot_accepts_analyst_fields_when_provided() -> None:
    """FundamentalsSnapshot accepts the 4 new Optional analyst-consensus fields
    (analyst_target_mean / analyst_target_median / analyst_recommendation_mean /
    analyst_opinion_count) when constructed explicitly. Round-trips through
    model_dump(mode='json') without losing any of them.
    """
    snap = FundamentalsSnapshot(
        ticker="AAPL",
        fetched_at=datetime(2026, 5, 1, 14, 0, 0, tzinfo=timezone.utc),
        source="yfinance",
        analyst_target_mean=180.5,
        analyst_target_median=185.0,
        analyst_recommendation_mean=2.1,
        analyst_opinion_count=42,
    )
    assert snap.analyst_target_mean == 180.5
    assert snap.analyst_target_median == 185.0
    assert snap.analyst_recommendation_mean == 2.1
    assert snap.analyst_opinion_count == 42

    dumped = snap.model_dump(mode="json")
    assert dumped["analyst_target_mean"] == 180.5
    assert dumped["analyst_target_median"] == 185.0
    assert dumped["analyst_recommendation_mean"] == 2.1
    assert dumped["analyst_opinion_count"] == 42


def test_fundamentals_snapshot_accepts_analyst_fields_when_omitted() -> None:
    """FundamentalsSnapshot constructed without any of the 4 new analyst fields
    defaults each to None; existing fields (pe, ps, data_unavailable) keep
    working. Verifies the additive change is fully backward-compatible.
    """
    snap = FundamentalsSnapshot(
        ticker="AAPL",
        fetched_at=datetime(2026, 5, 1, 14, 0, 0, tzinfo=timezone.utc),
        source="yfinance",
        pe=28.5,
        ps=7.2,
    )
    assert snap.analyst_target_mean is None
    assert snap.analyst_target_median is None
    assert snap.analyst_recommendation_mean is None
    assert snap.analyst_opinion_count is None
    # Existing fields still work
    assert snap.pe == 28.5
    assert snap.ps == 7.2
    assert snap.data_unavailable is False


def test_fundamentals_snapshot_opinion_count_float_coercion() -> None:
    """analyst_opinion_count is typed Optional[int]. Pydantic v2's default
    coercion mode floors floats with no fractional part (e.g., 42.0 → 42)
    but rejects floats with fractional parts to preserve int semantics. We
    lock the documented behavior here.

    Whatever the project chose, this test pins the contract so a future
    Pydantic upgrade can't silently flip it.
    """
    # 42.0 should coerce cleanly (no fractional loss)
    snap = FundamentalsSnapshot(
        ticker="AAPL",
        fetched_at=datetime(2026, 5, 1, 14, 0, 0, tzinfo=timezone.utc),
        source="yfinance",
        analyst_opinion_count=42.0,  # pyright: ignore[reportArgumentType]
    )
    assert snap.analyst_opinion_count == 42

    # 42.5 has a fractional part — Pydantic v2 default rejects it via
    # int_from_float to avoid silent truncation. Lock the rejection.
    with pytest.raises(ValidationError):
        FundamentalsSnapshot(
            ticker="AAPL",
            fetched_at=datetime(2026, 5, 1, 14, 0, 0, tzinfo=timezone.utc),
            source="yfinance",
            analyst_opinion_count=42.5,  # pyright: ignore[reportArgumentType]
        )


def test_fundamentals_snapshot_extra_forbid_still_active() -> None:
    """ConfigDict(extra='forbid') discipline preserved after the additive
    field set — unknown kwargs still raise ValidationError, so a typo like
    'analyst_target_means' (note the trailing s) fails loudly rather than
    silently being absorbed.
    """
    with pytest.raises(ValidationError):
        FundamentalsSnapshot(
            ticker="AAPL",
            fetched_at=datetime(2026, 5, 1, 14, 0, 0, tzinfo=timezone.utc),
            source="yfinance",
            extra_unknown_field=1,  # pyright: ignore[reportCallIssue]
        )


def test_fetch_fundamentals_populates_analyst_fields() -> None:
    """yfinance .info has all 4 analyst-consensus keys populated →
    fetch_fundamentals reads them via _safe_float / _safe_int and passes
    them through to the constructed FundamentalsSnapshot.
    """
    mock_ticker = MagicMock()
    mock_ticker.info = {
        "trailingPE": 28.5,
        "marketCap": 3_000_000_000_000,
        "targetMeanPrice": 180.5,
        "targetMedianPrice": 185.0,
        "recommendationMean": 2.1,
        "numberOfAnalystOpinions": 42,
    }

    with patch("ingestion.fundamentals.yfinance.Ticker", return_value=mock_ticker):
        result = fetch_fundamentals("AAPL")

    assert result.analyst_target_mean == 180.5
    assert result.analyst_target_median == 185.0
    assert result.analyst_recommendation_mean == 2.1
    assert result.analyst_opinion_count == 42
    # Existing canonical fields still populated; data_unavailable still False
    assert result.pe == 28.5
    assert result.market_cap == 3_000_000_000_000
    assert result.data_unavailable is False


def test_fetch_fundamentals_handles_missing_analyst_fields() -> None:
    """yfinance .info has canonical fields BUT no analyst-consensus keys →
    the 4 new fields are None; data_unavailable stays False (canonical pe /
    market_cap present), confirming analyst-consensus fields are not part
    of the data_unavailable predicate.
    """
    mock_ticker = MagicMock()
    mock_ticker.info = {
        "trailingPE": 28.5,
        "marketCap": 3_000_000_000_000,
        # No targetMeanPrice / targetMedianPrice / recommendationMean / numberOfAnalystOpinions
    }

    with patch("ingestion.fundamentals.yfinance.Ticker", return_value=mock_ticker):
        result = fetch_fundamentals("AAPL")

    assert result.analyst_target_mean is None
    assert result.analyst_target_median is None
    assert result.analyst_recommendation_mean is None
    assert result.analyst_opinion_count is None
    assert result.data_unavailable is False  # canonical fields present


def test_fetch_fundamentals_handles_partial_analyst_fields() -> None:
    """Only one of the 4 analyst keys present → that one populates, the other
    three stay None. Verifies per-field independence (no all-or-nothing
    coupling)."""
    mock_ticker = MagicMock()
    mock_ticker.info = {
        "trailingPE": 28.5,
        "marketCap": 3_000_000_000_000,
        "targetMeanPrice": 180.5,
        # targetMedianPrice / recommendationMean / numberOfAnalystOpinions absent
    }

    with patch("ingestion.fundamentals.yfinance.Ticker", return_value=mock_ticker):
        result = fetch_fundamentals("AAPL")

    assert result.analyst_target_mean == 180.5
    assert result.analyst_target_median is None
    assert result.analyst_recommendation_mean is None
    assert result.analyst_opinion_count is None


def test_fetch_fundamentals_handles_non_numeric_analyst_fields() -> None:
    """yfinance occasionally returns non-numeric values for analyst keys:
    string 'N/A' for targetMeanPrice, NaN for recommendationMean, bool for
    numberOfAnalystOpinions (since `isinstance(True, int) is True` Python
    treats bools as int subclass; we explicitly reject them via _safe_int).
    All four must coerce to None without raising.
    """
    mock_ticker = MagicMock()
    mock_ticker.info = {
        "trailingPE": 28.5,
        "marketCap": 3_000_000_000_000,
        "targetMeanPrice": "N/A",                  # string → None
        "targetMedianPrice": float("inf"),         # inf → None
        "recommendationMean": float("nan"),        # NaN → None
        "numberOfAnalystOpinions": True,           # bool → None
    }

    with patch("ingestion.fundamentals.yfinance.Ticker", return_value=mock_ticker):
        result = fetch_fundamentals("AAPL")

    assert result.analyst_target_mean is None
    assert result.analyst_target_median is None
    assert result.analyst_recommendation_mean is None
    assert result.analyst_opinion_count is None
    # data_unavailable still False — canonical fields present
    assert result.data_unavailable is False


def test_safe_int_helper() -> None:
    """Unit-test the _safe_int helper directly: locks the contract on bool
    rejection, NaN/inf rejection, float-floor for whole-number floats, and
    string-to-None (no string-numeric coercion to keep parity with
    _safe_float's defensive posture).
    """
    from ingestion.fundamentals import _safe_int

    # None / bool — rejected
    assert _safe_int(None) is None
    assert _safe_int(True) is None
    assert _safe_int(False) is None
    # Plain ints — pass through
    assert _safe_int(42) == 42
    assert _safe_int(-3) == 0 - 3
    assert _safe_int(0) == 0
    # Floats — floored / truncated toward zero
    assert _safe_int(42.7) == 42
    assert _safe_int(42.0) == 42
    # Strings — rejected (we don't try to parse, just like _safe_float)
    assert _safe_int("5") is None
    assert _safe_int("N/A") is None
    # NaN / inf — rejected
    assert _safe_int(float("nan")) is None
    assert _safe_int(float("inf")) is None
    assert _safe_int(float("-inf")) is None
