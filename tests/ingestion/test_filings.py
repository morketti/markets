"""Tests for ingestion/filings.py — SEC EDGAR filings fetch (Plan 02-03).

Probes covered:
- 2-W2-06: happy path — fetch_filings("AAPL") returns recent 10-K/10-Q/8-K
- 2-W2-07: 403 — EDGAR returns 403 when User-Agent is non-compliant; we raise NetworkError
- 2-W2-08: 429 retry — shared session retry adapter retries 429 → 200, fetch_filings succeeds

Zero real network: every HTTP call is mocked via the `responses` library.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import responses

from analysts.data.filings import FilingMetadata
from ingestion import filings as filings_module
from ingestion.errors import NetworkError, SchemaDriftError
from ingestion.filings import (
    EDGAR_SUBMISSIONS_URL,
    EDGAR_TICKERS_URL,
    fetch_filings,
    lookup_cik,
)


@pytest.fixture(autouse=True)
def _clear_cik_cache():
    """Reset the in-process CIK cache between tests so cache-related probes
    don't bleed state. Also resets the polite-sleep last-call dict."""
    filings_module._CIK_CACHE.clear()
    filings_module._LAST_CALL.clear()
    yield
    filings_module._CIK_CACHE.clear()
    filings_module._LAST_CALL.clear()


@pytest.fixture
def edgar_tickers_json(fixtures_dir: Path) -> str:
    return (fixtures_dir / "edgar_company_tickers.json").read_text()


@pytest.fixture
def edgar_submissions_aapl_json(fixtures_dir: Path) -> str:
    return (fixtures_dir / "edgar_submissions_aapl.json").read_text()


@pytest.fixture
def edgar_403_body(fixtures_dir: Path) -> str:
    return (fixtures_dir / "edgar_403.txt").read_text()


# ---------------- lookup_cik ----------------


@responses.activate
def test_lookup_cik_happy(edgar_tickers_json: str):
    """lookup_cik returns 10-digit zero-padded CIK and sends compliant UA header."""
    responses.add(
        responses.GET,
        EDGAR_TICKERS_URL,
        body=edgar_tickers_json,
        status=200,
        content_type="application/json",
    )

    cik = lookup_cik("AAPL")

    assert cik == "0000320193"
    assert len(responses.calls) == 1
    ua = responses.calls[0].request.headers.get("User-Agent", "")
    assert ua.startswith("Markets Personal Research"), f"UA was: {ua!r}"


@responses.activate
def test_lookup_cik_unknown_returns_none(edgar_tickers_json: str):
    """Unknown ticker returns None — not an error (gracefully signal cache miss)."""
    responses.add(
        responses.GET,
        EDGAR_TICKERS_URL,
        body=edgar_tickers_json,
        status=200,
        content_type="application/json",
    )

    assert lookup_cik("XXXY") is None


@responses.activate
def test_lookup_cik_caches_in_process(edgar_tickers_json: str):
    """Second lookup_cik call hits the cache, not the network."""
    responses.add(
        responses.GET,
        EDGAR_TICKERS_URL,
        body=edgar_tickers_json,
        status=200,
        content_type="application/json",
    )

    cik1 = lookup_cik("AAPL")
    cik2 = lookup_cik("NVDA")

    assert cik1 == "0000320193"
    assert cik2 == "0001045810"
    # Only ONE network call — second lookup hit the cache.
    assert len(responses.calls) == 1


@responses.activate
def test_lookup_cik_normalizes_dotted_ticker(edgar_tickers_json: str):
    """BRK.B normalizes to BRK-B before cache lookup (analysts.schemas.normalize_ticker)."""
    responses.add(
        responses.GET,
        EDGAR_TICKERS_URL,
        body=edgar_tickers_json,
        status=200,
        content_type="application/json",
    )

    assert lookup_cik("BRK.B") == "0001067983"


# ---------------- fetch_filings ----------------


@responses.activate
def test_filings_happy(edgar_tickers_json: str, edgar_submissions_aapl_json: str):
    """Probe 2-W2-06: happy path — recent 10-K/10-Q/8-K filings parsed correctly."""
    responses.add(
        responses.GET,
        EDGAR_TICKERS_URL,
        body=edgar_tickers_json,
        status=200,
        content_type="application/json",
    )
    responses.add(
        responses.GET,
        EDGAR_SUBMISSIONS_URL.format(cik="0000320193"),
        body=edgar_submissions_aapl_json,
        status=200,
        content_type="application/json",
    )

    result = fetch_filings("AAPL")

    assert isinstance(result, list)
    assert len(result) > 0
    assert len(result) <= 20
    for f in result:
        assert isinstance(f, FilingMetadata)
        assert f.ticker == "AAPL"
        assert f.source == "edgar"
        assert f.cik == "0000320193"
        assert f.data_unavailable is False
        assert f.form_type in ("10-K", "10-Q", "8-K")
        assert f.accession_number is not None
        assert f.filed_date is not None
        assert f.primary_document is not None

    # Sorted descending by filed_date
    dates = [f.filed_date for f in result]
    assert dates == sorted(dates, reverse=True), "filings must be sorted by filed_date desc"

    # Verify UA header on the data.sec.gov call
    submissions_call = responses.calls[1]
    ua = submissions_call.request.headers.get("User-Agent", "")
    assert ua.startswith("Markets Personal Research"), f"UA on submissions call: {ua!r}"


@responses.activate
def test_filings_filters_forms(edgar_tickers_json: str, edgar_submissions_aapl_json: str):
    """When forms=("10-K",), only 10-K filings should be returned."""
    responses.add(
        responses.GET,
        EDGAR_TICKERS_URL,
        body=edgar_tickers_json,
        status=200,
        content_type="application/json",
    )
    responses.add(
        responses.GET,
        EDGAR_SUBMISSIONS_URL.format(cik="0000320193"),
        body=edgar_submissions_aapl_json,
        status=200,
        content_type="application/json",
    )

    result = fetch_filings("AAPL", forms=("10-K",))

    assert len(result) >= 1, "fixture must include at least one 10-K"
    for f in result:
        assert f.form_type == "10-K"


@responses.activate
def test_filings_respects_limit(edgar_tickers_json: str, edgar_submissions_aapl_json: str):
    """fetch_filings(..., limit=3) returns at most 3 items."""
    responses.add(
        responses.GET,
        EDGAR_TICKERS_URL,
        body=edgar_tickers_json,
        status=200,
        content_type="application/json",
    )
    responses.add(
        responses.GET,
        EDGAR_SUBMISSIONS_URL.format(cik="0000320193"),
        body=edgar_submissions_aapl_json,
        status=200,
        content_type="application/json",
    )

    result = fetch_filings("AAPL", limit=3)
    assert len(result) <= 3


@responses.activate
def test_filings_unknown_ticker(edgar_tickers_json: str):
    """Unknown ticker → empty list, no network call to submissions endpoint."""
    responses.add(
        responses.GET,
        EDGAR_TICKERS_URL,
        body=edgar_tickers_json,
        status=200,
        content_type="application/json",
    )

    result = fetch_filings("XXXY")

    assert result == []
    # Only the company_tickers call; no submissions call.
    assert len(responses.calls) == 1


@responses.activate
def test_filings_403(edgar_tickers_json: str, edgar_403_body: str):
    """Probe 2-W2-07: EDGAR 403 (UA non-compliance) raises NetworkError with diagnostic."""
    responses.add(
        responses.GET,
        EDGAR_TICKERS_URL,
        body=edgar_tickers_json,
        status=200,
        content_type="application/json",
    )
    responses.add(
        responses.GET,
        EDGAR_SUBMISSIONS_URL.format(cik="0000320193"),
        body=edgar_403_body,
        status=403,
        content_type="text/plain",
    )

    with pytest.raises(NetworkError) as exc_info:
        fetch_filings("AAPL")

    msg = str(exc_info.value)
    assert "403" in msg or "User-Agent" in msg, f"expected 403/User-Agent diagnostic, got: {msg!r}"


@responses.activate
def test_filings_429_retry(edgar_tickers_json: str, edgar_submissions_aapl_json: str):
    """Probe 2-W2-08: 429 → 200 retry succeeds via shared session adapter."""
    responses.add(
        responses.GET,
        EDGAR_TICKERS_URL,
        body=edgar_tickers_json,
        status=200,
        content_type="application/json",
    )
    # First submissions call: 429 with short retry-after
    responses.add(
        responses.GET,
        EDGAR_SUBMISSIONS_URL.format(cik="0000320193"),
        body="rate limited",
        status=429,
        headers={"Retry-After": "0"},
        content_type="text/plain",
    )
    # Second submissions call: 200 with the fixture
    responses.add(
        responses.GET,
        EDGAR_SUBMISSIONS_URL.format(cik="0000320193"),
        body=edgar_submissions_aapl_json,
        status=200,
        content_type="application/json",
    )

    result = fetch_filings("AAPL")

    assert isinstance(result, list)
    assert len(result) > 0
    # 1 ticker call + at least 2 submissions calls (retry fired)
    assert len(responses.calls) >= 3, f"expected >=3 calls, got {len(responses.calls)}"


@responses.activate
def test_filings_schema_drift(edgar_tickers_json: str):
    """Probe-adjacent: 200 with malformed shape raises SchemaDriftError."""
    responses.add(
        responses.GET,
        EDGAR_TICKERS_URL,
        body=edgar_tickers_json,
        status=200,
        content_type="application/json",
    )
    responses.add(
        responses.GET,
        EDGAR_SUBMISSIONS_URL.format(cik="0000320193"),
        body="{}",
        status=200,
        content_type="application/json",
    )

    with pytest.raises(SchemaDriftError):
        fetch_filings("AAPL")
