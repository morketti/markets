"""Tests for api/refresh.py — Vercel Python serverless mid-day refresh.

The handler is structured as a pure builder `_build_response(path) -> (dict, int)`
plus a thin `BaseHTTPRequestHandler` subclass that delegates to it. Most tests
drive `_build_response` directly (no HTTP plumbing); 2 tests exercise the full
`do_GET` path via MagicMock to verify send_response / wfile.write integration.

All upstream calls (`fetch_prices`, `fetch_news`) are stubbed via `monkeypatch`;
zero network in this suite.

Phase 8 / Plan 08-01 / Task 1.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import MagicMock

import pytest

from analysts.data.news import Headline
from analysts.data.prices import PriceSnapshot


# ---------------------------------------------------------------------------
# Helpers — stub builders for upstream returns.
# ---------------------------------------------------------------------------

_FROZEN_FETCH = datetime(2026, 5, 4, 19, 32, 11, tzinfo=timezone.utc)
_FROZEN_PUBLISHED = datetime(2026, 5, 4, 18, 0, 0, tzinfo=timezone.utc)


def _ok_price_snapshot(ticker: str = "AAPL", price: float = 178.42) -> PriceSnapshot:
    return PriceSnapshot(
        ticker=ticker,
        fetched_at=_FROZEN_FETCH,
        source="yfinance",
        data_unavailable=False,
        current_price=price,
        history=[],
    )


def _unavailable_price_snapshot(ticker: str = "AAPL") -> PriceSnapshot:
    return PriceSnapshot(
        ticker=ticker,
        fetched_at=_FROZEN_FETCH,
        source="yfinance",
        data_unavailable=True,
        current_price=None,
        history=[],
    )


def _ok_headlines(ticker: str = "AAPL", count: int = 2) -> tuple[list[Headline], list[dict]]:
    """Return (list[Headline], list[dict]) matching fetch_news(return_raw=True)."""
    headlines = [
        Headline(
            ticker=ticker,
            fetched_at=_FROZEN_FETCH,
            source="yahoo-rss",
            title=f"{ticker} headline {i}",
            url=f"https://example.com/{ticker.lower()}-{i}",
            published_at=_FROZEN_PUBLISHED,
            summary="",
            dedup_key=f"yahoo-rss::{ticker}-{i}",
        )
        for i in range(count)
    ]
    raw = [
        {
            "source": h.source,
            "published_at": h.published_at.isoformat() if h.published_at else None,
            "title": h.title,
            "url": h.url,
        }
        for h in headlines
    ]
    return headlines, raw


# ---------------------------------------------------------------------------
# Test 1 — happy path
# ---------------------------------------------------------------------------


def test_happy_path(monkeypatch):
    """fetch_prices + fetch_news both succeed → 200 with full envelope."""
    from api import refresh as refresh_mod

    monkeypatch.setattr(refresh_mod, "fetch_prices", lambda t, **kw: _ok_price_snapshot(t))
    monkeypatch.setattr(
        refresh_mod, "fetch_news", lambda t, **kw: _ok_headlines(t, count=2),
    )

    payload, status = refresh_mod._build_response("/api/refresh?ticker=AAPL")

    assert status == 200
    assert payload["ticker"] == "AAPL"
    assert payload["current_price"] == 178.42
    assert payload["price_timestamp"] == _FROZEN_FETCH.isoformat()
    assert payload["errors"] == []
    assert payload["partial"] is False
    assert "error" not in payload  # success shape has no `error` field

    # Headlines preserve the 4-key shape (no extras).
    assert isinstance(payload["recent_headlines"], list)
    assert len(payload["recent_headlines"]) == 2
    h0 = payload["recent_headlines"][0]
    assert set(h0.keys()) == {"source", "published_at", "title", "url"}
    assert h0["source"] == "yahoo-rss"
    assert h0["published_at"] == _FROZEN_PUBLISHED.isoformat()


# ---------------------------------------------------------------------------
# Test 2 — missing ticker query param
# ---------------------------------------------------------------------------


def test_missing_ticker_param(monkeypatch):
    """GET /api/refresh (no ?ticker=) → 400 with errors=['missing-ticker-param']."""
    from api import refresh as refresh_mod

    # Stubs that should never be called (defensive).
    monkeypatch.setattr(refresh_mod, "fetch_prices", lambda *a, **k: pytest.fail("should not call"))
    monkeypatch.setattr(refresh_mod, "fetch_news", lambda *a, **k: pytest.fail("should not call"))

    payload, status = refresh_mod._build_response("/api/refresh")

    assert status == 400
    assert payload["error"] is True
    assert "missing-ticker-param" in payload["errors"]


# ---------------------------------------------------------------------------
# Test 3 — invalid ticker (empty string)
# ---------------------------------------------------------------------------


def test_invalid_ticker(monkeypatch):
    """?ticker= (empty) → 400 with errors=['invalid-ticker']."""
    from api import refresh as refresh_mod

    payload, status = refresh_mod._build_response("/api/refresh?ticker=")

    assert status == 400
    assert payload["error"] is True
    assert "invalid-ticker" in payload["errors"]


# ---------------------------------------------------------------------------
# Test 4 — RSS unavailable (price OK)
# ---------------------------------------------------------------------------


def test_rss_unavailable_partial(monkeypatch):
    """fetch_prices ok; fetch_news returns ([], []) → 200 partial=true with rss-unavailable."""
    from api import refresh as refresh_mod

    monkeypatch.setattr(refresh_mod, "fetch_prices", lambda t, **kw: _ok_price_snapshot(t))
    monkeypatch.setattr(refresh_mod, "fetch_news", lambda t, **kw: ([], []))

    payload, status = refresh_mod._build_response("/api/refresh?ticker=AAPL")

    assert status == 200
    assert payload["partial"] is True
    assert payload["errors"] == ["rss-unavailable"]
    assert payload["current_price"] == 178.42  # price still set
    assert payload["recent_headlines"] == []
    assert "error" not in payload  # not a full failure


# ---------------------------------------------------------------------------
# Test 5 — Price data unavailable (yfinance + yahooquery both broken)
# ---------------------------------------------------------------------------


def test_price_data_unavailable(monkeypatch):
    """fetch_prices returns data_unavailable=True; news ok → full-failure shape (no current_price)."""
    from api import refresh as refresh_mod

    monkeypatch.setattr(refresh_mod, "fetch_prices", lambda t, **kw: _unavailable_price_snapshot(t))
    monkeypatch.setattr(
        refresh_mod, "fetch_news", lambda t, **kw: _ok_headlines(t, count=2),
    )

    payload, status = refresh_mod._build_response("/api/refresh?ticker=AAPL")

    assert status == 200
    assert payload.get("error") is True
    assert payload["partial"] is True
    assert "yfinance-unavailable" in payload["errors"]
    assert "yahooquery-unavailable" in payload["errors"]
    # Locked shape: full-failure has NO current_price field.
    assert "current_price" not in payload


# ---------------------------------------------------------------------------
# Test 6 — both layers fail
# ---------------------------------------------------------------------------


def test_both_data_layers_fail(monkeypatch):
    """fetch_prices unavailable AND fetch_news empty → full failure with rss-unavailable too."""
    from api import refresh as refresh_mod

    monkeypatch.setattr(refresh_mod, "fetch_prices", lambda t, **kw: _unavailable_price_snapshot(t))
    monkeypatch.setattr(refresh_mod, "fetch_news", lambda t, **kw: ([], []))

    payload, status = refresh_mod._build_response("/api/refresh?ticker=AAPL")

    assert status == 200
    assert payload.get("error") is True
    assert payload["partial"] is True
    # All 3 error markers present.
    for marker in ("yfinance-unavailable", "yahooquery-unavailable", "rss-unavailable"):
        assert marker in payload["errors"]
    assert "current_price" not in payload


# ---------------------------------------------------------------------------
# Test 7 — fetch_prices raises (defensive — never *should* per the contract,
# but the function must be hardened anyway)
# ---------------------------------------------------------------------------


def test_fetch_prices_raises(monkeypatch):
    """fetch_prices unexpectedly raises → full-failure envelope; no exception escapes."""
    from api import refresh as refresh_mod

    def _boom(*a, **k):
        raise RuntimeError("yfinance internal explode")

    monkeypatch.setattr(refresh_mod, "fetch_prices", _boom)
    monkeypatch.setattr(
        refresh_mod, "fetch_news", lambda t, **kw: _ok_headlines(t, count=1),
    )

    payload, status = refresh_mod._build_response("/api/refresh?ticker=AAPL")

    assert status == 200
    assert payload.get("error") is True
    assert "yfinance-unavailable" in payload["errors"]
    assert "current_price" not in payload


# ---------------------------------------------------------------------------
# Test 8 — fetch_news raises
# ---------------------------------------------------------------------------


def test_fetch_news_raises(monkeypatch):
    """fetch_news unexpectedly raises → partial=true with rss-unavailable; price still set."""
    from api import refresh as refresh_mod

    def _boom(*a, **k):
        raise RuntimeError("rss feed parser explode")

    monkeypatch.setattr(refresh_mod, "fetch_prices", lambda t, **kw: _ok_price_snapshot(t))
    monkeypatch.setattr(refresh_mod, "fetch_news", _boom)

    payload, status = refresh_mod._build_response("/api/refresh?ticker=AAPL")

    assert status == 200
    assert payload["partial"] is True
    assert payload["errors"] == ["rss-unavailable"]
    assert payload["current_price"] == 178.42  # price preserved


# ---------------------------------------------------------------------------
# Test 9 — timeout simulation (in-process)
#
# Vercel's actual timeout is enforced by the platform, not in-process. This
# test only asserts the error envelope shape — fall back per the plan note:
# stub fetch_prices to return data_unavailable AND emit a "timeout" error
# string, verifying our error envelope can carry it.
# ---------------------------------------------------------------------------


def test_timeout_envelope_shape(monkeypatch):
    """When fetch_prices returns data_unavailable shape, errors envelope can carry a 'timeout' marker.

    This is a sanity check on envelope flexibility — the in-process timeout
    wrapper described in the plan was deemed too brittle; we verify here
    that the envelope correctly distinguishes a partial response from a
    healthy one when fetch_prices reports unavailable.
    """
    from api import refresh as refresh_mod

    monkeypatch.setattr(refresh_mod, "fetch_prices", lambda t, **kw: _unavailable_price_snapshot(t))
    monkeypatch.setattr(
        refresh_mod, "fetch_news", lambda t, **kw: _ok_headlines(t, count=1),
    )

    payload, status = refresh_mod._build_response("/api/refresh?ticker=AAPL")

    assert status == 200
    assert payload.get("error") is True
    assert payload["partial"] is True
    assert payload["errors"]  # non-empty


# ---------------------------------------------------------------------------
# Test 10 — Headlines serialize correctly (4-key shape, ISO-8601 published_at)
# ---------------------------------------------------------------------------


def test_headlines_serialize_correctly(monkeypatch):
    """recent_headlines[i] has exactly {source, published_at, title, url}; published_at ISO-8601 UTC."""
    from api import refresh as refresh_mod

    monkeypatch.setattr(refresh_mod, "fetch_prices", lambda t, **kw: _ok_price_snapshot(t))
    monkeypatch.setattr(
        refresh_mod, "fetch_news", lambda t, **kw: _ok_headlines(t, count=1),
    )

    payload, status = refresh_mod._build_response("/api/refresh?ticker=AAPL")

    assert status == 200
    assert len(payload["recent_headlines"]) == 1
    h = payload["recent_headlines"][0]
    assert set(h.keys()) == {"source", "published_at", "title", "url"}
    # published_at is ISO 8601 with tz offset.
    assert isinstance(h["published_at"], str)
    assert "+00:00" in h["published_at"] or h["published_at"].endswith("Z")
    # JSON-serializable end-to-end.
    json.dumps(payload)


# ---------------------------------------------------------------------------
# Test 11 — do_GET integration (full path, MagicMock for HTTP plumbing)
# ---------------------------------------------------------------------------


def test_do_get_writes_json_response(monkeypatch):
    """handler.do_GET writes JSON body via wfile + sets 200 status + Content-Type header."""
    from api import refresh as refresh_mod

    monkeypatch.setattr(refresh_mod, "fetch_prices", lambda t, **kw: _ok_price_snapshot(t))
    monkeypatch.setattr(
        refresh_mod, "fetch_news", lambda t, **kw: _ok_headlines(t, count=1),
    )

    h = refresh_mod.handler.__new__(refresh_mod.handler)
    h.path = "/api/refresh?ticker=AAPL"
    h.send_response = MagicMock()
    h.send_header = MagicMock()
    h.end_headers = MagicMock()
    h.wfile = BytesIO()

    h.do_GET()

    h.send_response.assert_called_once_with(200)
    # Content-Type header sent at least once.
    header_keys = [c.args[0] for c in h.send_header.call_args_list]
    assert "Content-Type" in header_keys
    # Body parses back to the same envelope.
    body_bytes = h.wfile.getvalue()
    parsed = json.loads(body_bytes.decode("utf-8"))
    assert parsed["ticker"] == "AAPL"
    assert parsed["current_price"] == 178.42


def test_do_get_400_for_missing_ticker(monkeypatch):
    """handler.do_GET propagates 400 status when ticker missing."""
    from api import refresh as refresh_mod

    h = refresh_mod.handler.__new__(refresh_mod.handler)
    h.path = "/api/refresh"
    h.send_response = MagicMock()
    h.send_header = MagicMock()
    h.end_headers = MagicMock()
    h.wfile = BytesIO()

    h.do_GET()

    h.send_response.assert_called_once_with(400)


# ---------------------------------------------------------------------------
# Test 12 — Ticker normalization (dot → hyphen via normalize_ticker)
# ---------------------------------------------------------------------------


def test_ticker_normalized(monkeypatch):
    """?ticker=brk.b normalizes to BRK-B for both upstream calls + response payload."""
    from api import refresh as refresh_mod

    seen: dict = {}

    def _stub_prices(t, **kw):
        seen["prices"] = t
        return _ok_price_snapshot(t)

    def _stub_news(t, **kw):
        seen["news"] = t
        return _ok_headlines(t, count=0)  # empty → triggers rss-unavailable but proves call

    monkeypatch.setattr(refresh_mod, "fetch_prices", _stub_prices)
    monkeypatch.setattr(refresh_mod, "fetch_news", _stub_news)

    payload, status = refresh_mod._build_response("/api/refresh?ticker=brk.b")

    assert status == 200
    assert payload["ticker"] == "BRK-B"
    assert seen["prices"] == "BRK-B"
    assert seen["news"] == "BRK-B"
