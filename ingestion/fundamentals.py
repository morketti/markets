"""Fundamentals ingestion: yfinance.Ticker(t).info → FundamentalsSnapshot.

Implements DATA-02 (P/E, P/S, P/B, ROE, debt/equity, profit margin, FCF,
market cap) and DATA-07 (data_unavailable flag when .info is empty / yfinance
raises / canonical markers missing).

Pitfall #1 (02-RESEARCH.md) — yfinance scrapes Yahoo's web UI; the .info
dict has been deprecated/unstable since 0.2.40+. Yahoo periodically changes
endpoints and returns 200 with an empty `{}` payload, OR populates only
some keys, OR returns non-numeric strings ("Infinity", "N/A") for missing
metrics. fetch_fundamentals tolerates ALL of these failure modes:

- empty {} → data_unavailable=True, all metrics None
- missing key → that metric is None, others populated
- non-numeric string / NaN → coerced to None via _safe_float
- yfinance internal exception → caught, data_unavailable=True

NEVER raises KeyError. NEVER raises NetworkError. The only escapable
exception is a Pydantic ValidationError if our schema rejects the data
we constructed — which would be a programmer bug, not runtime weather.

Public surface:
    fetch_fundamentals(ticker: str) -> FundamentalsSnapshot
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import yfinance

from analysts.data.fundamentals import FundamentalsSnapshot
from analysts.schemas import normalize_ticker


def _now_utc() -> datetime:
    """UTC timestamp helper (single seam for tests if ever needed)."""
    return datetime.now(timezone.utc)


def _safe_float(v: Any) -> Optional[float]:
    """Coerce a yfinance .info value to float — None if it's not a finite number.

    yfinance occasionally returns:
        - None for missing keys
        - the literal string "Infinity" or "N/A"
        - float('nan') / float('inf') around dividend records
        - actual ints/floats (the happy case)
    Any non-finite-number returns None. Bool is rejected explicitly because
    Python treats True/False as ints (`isinstance(True, int) is True`) and we
    don't want a flag accidentally serialized as 1.0.
    """
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        # Reject NaN and infinities — they round-trip badly through JSON
        if v != v or v == float("inf") or v == float("-inf"):  # noqa: PLR0124
            return None
        return float(v)
    return None


def _unavailable(ticker: str) -> FundamentalsSnapshot:
    """Build a data_unavailable FundamentalsSnapshot (all metric fields None)."""
    return FundamentalsSnapshot(
        ticker=ticker,
        fetched_at=_now_utc(),
        source="yfinance",
        data_unavailable=True,
    )


def fetch_fundamentals(ticker: str) -> FundamentalsSnapshot:
    """Fetch fundamentals from yfinance.Ticker(ticker).info.

    Returns a FundamentalsSnapshot with metrics populated from the available
    keys. When yfinance raises, .info is empty, or BOTH canonical-marker keys
    (trailingPE AND marketCap) are missing/non-numeric, the snapshot has
    `data_unavailable=True`.

    Args:
        ticker: ticker symbol (any case / dot notation accepted; normalized).

    Returns:
        FundamentalsSnapshot — never raises for upstream breakage.
    """
    normalized = normalize_ticker(ticker)
    if normalized is None:
        # Bad input — soft-fail with a sentinel valid ticker. "INVALID" matches
        # the regex so Pydantic accepts the construction; data_unavailable=True
        # signals the caller that nothing landed.
        return _unavailable("INVALID")

    try:
        info = yfinance.Ticker(normalized).info
    except Exception:
        # Any yfinance / urllib3 / requests internal failure → data_unavailable
        return _unavailable(normalized)

    if not isinstance(info, dict) or not info:
        return _unavailable(normalized)

    pe = _safe_float(info.get("trailingPE"))
    ps = _safe_float(info.get("priceToSalesTrailing12Months"))
    pb = _safe_float(info.get("priceToBook"))
    roe = _safe_float(info.get("returnOnEquity"))
    debt_to_equity = _safe_float(info.get("debtToEquity"))
    profit_margin = _safe_float(info.get("profitMargins"))
    free_cash_flow = _safe_float(info.get("freeCashflow"))
    market_cap = _safe_float(info.get("marketCap"))

    # Canonical-marker check: if BOTH trailingPE AND marketCap are missing
    # after coercion, treat as silent breakage. A snapshot with one populated
    # metric is still useful — let the caller decide.
    canonical_missing = pe is None and market_cap is None

    return FundamentalsSnapshot(
        ticker=normalized,
        fetched_at=_now_utc(),
        source="yfinance",
        data_unavailable=canonical_missing,
        pe=pe,
        ps=ps,
        pb=pb,
        roe=roe,
        debt_to_equity=debt_to_equity,
        profit_margin=profit_margin,
        free_cash_flow=free_cash_flow,
        market_cap=market_cap,
    )
