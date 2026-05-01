"""Price ingestion: yfinance primary + yahooquery fallback.

Implements DATA-01 (daily OHLC + current price), DATA-07 (data_unavailable
flag when both sources fail), DATA-08 (yahooquery fallback when yfinance
returns empty).

Pitfall #1 (02-RESEARCH.md) — yfinance scrapes Yahoo's web UI; Yahoo
periodically changes endpoints and returns 200 with empty payloads. Every
result is sanity-checked here (current_price > 0 AND len(history) >= 1) and
treated as "yfinance broke" if those checks fail. The fallback path
(yahooquery) hits a different endpoint family (v7 quote API) so when one is
broken the other often still works.

Public surface:
    fetch_prices(ticker: str, *, period: str = "1y") -> PriceSnapshot

Always returns a PriceSnapshot — sets data_unavailable=True when both sources
fail. NEVER raises for upstream breakage; only Pydantic ValidationError can
escape (which would be a programmer bug, not a runtime condition).

Plan 02-07 amendment — default `period` bumped from "3mo" (~63 trading bars)
to "1y" (~252 trading bars) so Phase 3's technicals analyst (ANLY-02) has
enough warm-up history for MA200 / 6m momentum / stable ADX without
per-call overrides. Existing callers that pin `period=` explicitly are
unaffected. See 03-RESEARCH.md Pitfall #1 for the rationale.

The function is pure-side-effect-free wrt our process: yfinance.Ticker /
yahooquery.Ticker manage their own HTTP under the hood. We don't reuse the
ingestion.http session here because both libraries supply their own client.
"""
from __future__ import annotations

from datetime import UTC, datetime

import yahooquery
import yfinance

from analysts.data.prices import OHLCBar, PriceSnapshot
from analysts.schemas import normalize_ticker


def _now_utc() -> datetime:
    """UTC timestamp helper (single seam for tests if ever needed)."""
    return datetime.now(UTC)


def _bars_from_dataframe(df) -> list[OHLCBar]:
    """Convert a yfinance history DataFrame into a list of OHLCBar.

    yfinance returns a DataFrame indexed by DatetimeIndex with columns
    Open / High / Low / Close / Volume (capitalized). We drop rows containing
    NaN (yfinance occasionally emits them around dividends or splits) and
    coerce volume to int.
    """
    if df is None or df.empty:
        return []

    bars: list[OHLCBar] = []
    df_clean = df.dropna(subset=["Open", "High", "Low", "Close"])
    for idx, row in df_clean.iterrows():
        bar_date = idx.date() if hasattr(idx, "date") else idx
        volume_val = row.get("Volume")
        # NaN compares unequal to itself; treat NaN volume as 0 rather than
        # losing the row entirely (volume occasionally drops out around
        # dividends / splits).
        volume = 0 if (volume_val is None or volume_val != volume_val) else int(volume_val)
        bars.append(
            OHLCBar(
                date=bar_date,
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=volume,
            )
        )
    return bars


def _current_price_from_yfinance(t) -> float | None:
    """Extract current price from a yfinance Ticker.

    Order of preference (per 02-RESEARCH.md — fast_info is the post-0.2.40
    stable path):
        1. fast_info["last_price"] (dict-style — yfinance 0.2.40+)
        2. info["regularMarketPrice"] (older / sometimes still populated)
    Returns None if neither resolves to a positive float.
    """
    # Primary: fast_info (dict-style access — handles both real yfinance
    # FastInfo objects and plain dicts in tests). AttributeError if fast_info
    # property itself raises; TypeError/KeyError if subscript fails.
    try:
        price = t.fast_info["last_price"]
        if isinstance(price, (int, float)) and price > 0:
            return float(price)
    except (AttributeError, TypeError, KeyError):
        pass

    # Fall through to .info
    try:
        info = t.info or {}
        price = info.get("regularMarketPrice")
        if isinstance(price, (int, float)) and price > 0:
            return float(price)
    except (AttributeError, TypeError, KeyError):
        pass

    return None


def _fetch_yfinance(ticker: str, period: str) -> PriceSnapshot | None:
    """Try to build a PriceSnapshot from yfinance.

    Returns None when:
    - yfinance.Ticker(...) raises (network down, lib internals broke)
    - .history() returns an empty DataFrame (Pitfall #1 silent breakage)
    - we cannot resolve a positive current_price after the fast_info / info
      cascade — fail closed, defer to yahooquery.

    Sanity check: current_price > 0 AND len(history) >= 1. If either fails,
    treat as silent breakage and return None.
    """
    try:
        t = yfinance.Ticker(ticker)
        df = t.history(period=period)
    except Exception:
        # Any internal yfinance / urllib3 / requests failure → defer to fallback
        return None

    bars = _bars_from_dataframe(df)
    if not bars:
        return None

    current = _current_price_from_yfinance(t)
    if current is None and bars:
        # Last-resort: use most recent close from history. Better than None.
        current = bars[-1].close

    if current is None or current <= 0:
        return None

    # Pydantic construction can't realistically fail here: ticker is already
    # normalized, current is a positive float, history bars were each built
    # via OHLCBar(...) and therefore already validated. If Pydantic ever does
    # raise, we let it surface — that's a programmer bug, not runtime weather.
    return PriceSnapshot(
        ticker=ticker,
        fetched_at=_now_utc(),
        source="yfinance",
        data_unavailable=False,
        current_price=current,
        history=bars,
    )


def _fetch_yahooquery(ticker: str) -> PriceSnapshot | None:
    """Try to build a PriceSnapshot from yahooquery's .price quote dict.

    yahooquery's .price endpoint does NOT supply OHLC history (only a current
    quote). For the fallback path we accept current_price + empty history;
    that's the documented limitation in 02-RESEARCH.md.

    Returns None when:
    - yahooquery.Ticker(...) or .price raises (network errors, etc.)
    - .price[ticker] is a string (yahooquery's "Quote not found" error shape)
    - .price[ticker] is a dict missing regularMarketPrice
    - the price isn't a positive number
    """
    try:
        t = yahooquery.Ticker(ticker)
        price_dict = t.price
    except Exception:
        return None

    if not isinstance(price_dict, dict):
        return None

    quote = price_dict.get(ticker)
    # yahooquery returns the string "Quote not found" instead of a dict on
    # invalid tickers — we explicitly check for that shape.
    if not isinstance(quote, dict):
        return None

    current = quote.get("regularMarketPrice")
    if not isinstance(current, (int, float)) or current <= 0:
        return None

    # See _fetch_yfinance: Pydantic construction here can't fail for any
    # input we'd actually accept — ticker is normalized, current is a
    # validated positive number.
    return PriceSnapshot(
        ticker=ticker,
        fetched_at=_now_utc(),
        source="yahooquery",
        data_unavailable=False,
        current_price=float(current),
        history=[],  # yahooquery .price doesn't supply OHLC history — documented
    )


def _unavailable(ticker: str, source: str = "yfinance") -> PriceSnapshot:
    """Build a data_unavailable PriceSnapshot — used when both sources fail."""
    return PriceSnapshot(
        ticker=ticker,
        fetched_at=_now_utc(),
        source=source,  # type: ignore[arg-type]
        data_unavailable=True,
        current_price=None,
        history=[],
    )


def fetch_prices(ticker: str, *, period: str = "1y") -> PriceSnapshot:
    """Fetch daily OHLC + current price for `ticker`.

    yfinance is primary (full OHLC history); yahooquery is the fallback for
    current price only when yfinance returns empty. Both can fail — in that
    case the returned PriceSnapshot has `data_unavailable=True`,
    `current_price=None`, `history=[]`.

    NEVER raises for upstream breakage (network, schema drift, yfinance
    internals). The only way an exception escapes is a Pydantic
    ValidationError if our schema rejects the data we constructed — that
    would be a programmer bug.

    Args:
        ticker: ticker symbol (any case / dot notation accepted; normalized).
        period: yfinance history period — default ``"1y"`` (~252 trading days).
            Plan 02-07 bumped this from ``"3mo"`` (~63 bars) so downstream
            Phase 3 analytics (MA200 / 6m momentum / stable ADX) have enough
            warm-up bars without per-call overrides. Callers that pin
            ``period=`` explicitly are unaffected by the default change.

    Returns:
        PriceSnapshot with `source="yfinance"` (happy or both-failed),
        `source="yahooquery"` (yfinance failed but fallback succeeded), or
        `data_unavailable=True` (both failed).
    """
    normalized = normalize_ticker(ticker)
    if normalized is None:
        # Bad input shouldn't reach here (CLI normalizes too) but soft-fail
        # rather than raising. We need a valid ticker to construct the
        # PriceSnapshot — use a sentinel that round-trips through Pydantic.
        # "INVALID" matches the regex but signals to the caller that something
        # was wrong with the input.
        return _unavailable("INVALID")

    primary = _fetch_yfinance(normalized, period)
    if primary is not None:
        return primary

    fallback = _fetch_yahooquery(normalized)
    if fallback is not None:
        return fallback

    return _unavailable(normalized, source="yfinance")
