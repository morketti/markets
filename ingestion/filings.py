# novel-to-this-project — Phase 2 EDGAR fetch + atomic JSON parsing (project-original; SEC API is unique to this project's keyless plan).
"""SEC EDGAR filings fetch — Plan 02-03 / DATA-03.

Fetches recent 10-K, 10-Q, 8-K filing metadata for a watchlist ticker via the
SEC EDGAR JSON API. Two-step protocol:

1. Resolve ticker → CIK via the company-tickers index
   (https://www.sec.gov/files/company_tickers.json). The index is fetched
   ONCE per process and cached in `_CIK_CACHE`. CIKs are zero-padded to 10
   digits — the format the submissions endpoint requires.

2. Fetch the company's recent submissions JSON
   (https://data.sec.gov/submissions/CIK{cik}.json) and walk the parallel
   arrays under `filings.recent`, building a `FilingMetadata` per row.

Pitfall #2 (02-RESEARCH.md): SEC EDGAR enforces a fair-access policy via the
User-Agent header. Without `Markets Personal Research (mohanraval15@gmail.com)`
(or equivalent name + contact), EDGAR returns 403 instead of the JSON. The
shared session in `ingestion/http.py` sets that header; THIS module never
overrides it. When EDGAR does respond 403 anyway (header tampering, IP
ban, etc.), we surface a `NetworkError` with diagnostic text — the Plan
02-06 orchestrator catches `IngestionError` and marks `data_unavailable=True`
on the per-ticker output, so the morning scan keeps moving even if EDGAR
goes dark for a session.

Politeness: SEC asks for ≤10 requests per second. We enforce a ~110ms gap
between calls via `polite_sleep("edgar", _LAST_CALL, 0.11)` — caller-owned
state per the Plan 02-01 contract.

Public surface (Plan 02-06 imports):
- `lookup_cik(ticker) -> Optional[str]`: zero-padded 10-digit CIK, or None.
- `fetch_filings(ticker, *, forms=("10-K","10-Q","8-K"), limit=20) -> list[FilingMetadata]`
- `EDGAR_TICKERS_URL`, `EDGAR_SUBMISSIONS_URL` (URL templates, exposed for testing).
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Optional

from pydantic import ValidationError

from analysts.data.filings import FilingMetadata
from analysts.schemas import normalize_ticker
from ingestion.errors import NetworkError, SchemaDriftError
from ingestion.http import DEFAULT_TIMEOUT, get_session, polite_sleep

logger = logging.getLogger(__name__)

EDGAR_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
EDGAR_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

# In-process cache: ticker (canonical hyphen form, uppercase) -> 10-digit CIK.
# Populated wholesale on first lookup_cik() call (the index is small — <30k
# entries, ~1MB JSON). NOT persisted to disk in this plan; Plan 02-06 may add
# a short-TTL on-disk cache when wiring the orchestrator.
_CIK_CACHE: dict[str, str] = {}

# Caller-owned politeness clock per the Plan 02-01 contract. Module-level here
# because filings.py is the sole owner of EDGAR's politeness budget; tests
# clear it via the autouse fixture in test_filings.py.
_LAST_CALL: dict[str, float] = {}

# SEC's fair-access ceiling is 10 req/sec. 0.11s gap = 9.09 req/sec — under
# the limit with a small safety margin.
_MIN_INTERVAL = 0.11

# Forms our schema's Literal accepts. Anything else maps to "OTHER" so an
# unexpected EDGAR form doesn't 500 the fetch.
_KNOWN_FORM_TYPES = {"10-K", "10-Q", "8-K", "DEF 14A", "S-1", "20-F", "6-K"}


def lookup_cik(ticker: str) -> Optional[str]:
    """Look up a ticker's 10-digit zero-padded CIK from EDGAR's company_tickers index.

    Returns None when the ticker isn't found in the index (graceful — caller
    interprets as "no filings to fetch", not as an error).

    On the first call (cache empty), fetches the entire index from EDGAR and
    populates `_CIK_CACHE` with every ticker → CIK mapping. Subsequent calls
    are pure dict lookups with no network round-trip.

    Raises `NetworkError` only when the index fetch itself fails (non-200);
    a successful fetch with the requested ticker absent is None, not an error.
    """
    norm = normalize_ticker(ticker)
    if norm is None:
        return None

    if not _CIK_CACHE:
        _populate_cik_cache()

    return _CIK_CACHE.get(norm)


def _populate_cik_cache() -> None:
    """Fetch the EDGAR company-tickers index and fill `_CIK_CACHE`."""
    polite_sleep("edgar", _LAST_CALL, _MIN_INTERVAL)

    session = get_session()
    response = session.get(EDGAR_TICKERS_URL, timeout=DEFAULT_TIMEOUT)

    if response.status_code != 200:
        raise NetworkError(
            f"EDGAR company_tickers index returned {response.status_code} "
            f"(expected 200). User-Agent sent: {session.headers.get('User-Agent')!r}"
        )

    try:
        payload = response.json()
    except ValueError as e:
        raise SchemaDriftError(
            f"EDGAR company_tickers returned 200 but body is not JSON: {e}"
        ) from e

    # Index shape: {"0": {"cik_str": <int>, "ticker": <str>, "title": <str>}, ...}
    if not isinstance(payload, dict):
        raise SchemaDriftError(
            f"EDGAR company_tickers JSON has unexpected top-level shape: {type(payload).__name__}"
        )

    for entry in payload.values():
        try:
            ticker_raw = entry["ticker"]
            cik_int = int(entry["cik_str"])
        except (KeyError, TypeError, ValueError):
            continue
        norm = normalize_ticker(ticker_raw)
        if norm is None:
            continue
        _CIK_CACHE[norm] = f"{cik_int:010d}"


def fetch_filings(
    ticker: str,
    *,
    forms: tuple[str, ...] = ("10-K", "10-Q", "8-K"),
    limit: int = 20,
) -> list[FilingMetadata]:
    """Fetch recent filings for `ticker` from SEC EDGAR.

    Returns at most `limit` `FilingMetadata` objects (most-recent first by
    filed_date), filtered to `forms`. Returns `[]` for an unknown ticker
    (CIK lookup miss) — that is NOT an error; some watchlist entries may
    legitimately not file with EDGAR (e.g., foreign issuers via 20-F vs 10-K
    cadence, or non-public proxies).

    Raises:
        NetworkError: EDGAR returned 403 (UA non-compliance), unrecoverable
            non-200, or the request errored after the shared session's retry
            policy exhausted.
        SchemaDriftError: EDGAR returned 200 but the JSON shape is missing the
            expected `filings.recent` arrays.
    """
    norm = normalize_ticker(ticker)
    if norm is None:
        return []

    cik = lookup_cik(norm)
    if cik is None:
        return []

    polite_sleep("edgar", _LAST_CALL, _MIN_INTERVAL)

    session = get_session()
    url = EDGAR_SUBMISSIONS_URL.format(cik=cik)
    response = session.get(url, timeout=DEFAULT_TIMEOUT)

    if response.status_code == 403:
        raise NetworkError(
            f"EDGAR 403 for {norm} (CIK {cik}) — User-Agent header may not be "
            f"compliant. Header sent: {session.headers.get('User-Agent')!r}. "
            f"See https://www.sec.gov/os/accessing-edgar-data"
        )
    if response.status_code != 200:
        raise NetworkError(
            f"EDGAR submissions returned {response.status_code} for {norm} "
            f"(CIK {cik}) after retries"
        )

    try:
        payload = response.json()
    except ValueError as e:
        raise SchemaDriftError(
            f"EDGAR submissions for {norm} returned 200 but body is not JSON: {e}"
        ) from e

    if not isinstance(payload, dict) or "filings" not in payload:
        raise SchemaDriftError(
            f"EDGAR submissions for {norm} (CIK {cik}) missing 'filings' key — "
            f"top-level keys: {list(payload.keys()) if isinstance(payload, dict) else type(payload).__name__}"
        )

    filings_section = payload["filings"]
    if not isinstance(filings_section, dict) or "recent" not in filings_section:
        raise SchemaDriftError(
            f"EDGAR submissions for {norm} (CIK {cik}) missing 'filings.recent' key"
        )

    recent = filings_section["recent"]
    accession_numbers = recent.get("accessionNumber", [])
    filing_dates = recent.get("filingDate", [])
    forms_arr = recent.get("form", [])
    primary_documents = recent.get("primaryDocument", [])

    forms_set = set(forms)
    fetched_at = datetime.now(timezone.utc)

    items: list[FilingMetadata] = []
    n = min(len(accession_numbers), len(filing_dates), len(forms_arr), len(primary_documents))

    for i in range(n):
        form_value = forms_arr[i]
        if form_value not in forms_set:
            continue

        # Map to schema-acceptable form_type Literal. Unknown forms → "OTHER".
        form_type = form_value if form_value in _KNOWN_FORM_TYPES else "OTHER"

        try:
            filed = date.fromisoformat(filing_dates[i])
        except (ValueError, TypeError):
            logger.warning(
                "filings(%s): skipping filing %s with invalid filingDate %r",
                norm, accession_numbers[i], filing_dates[i],
            )
            continue

        try:
            item = FilingMetadata(
                ticker=norm,
                fetched_at=fetched_at,
                source="edgar",
                data_unavailable=False,
                cik=cik,
                form_type=form_type,
                accession_number=accession_numbers[i],
                filed_date=filed,
                primary_document=primary_documents[i],
                summary="",
            )
        except ValidationError as e:
            logger.warning(
                "filings(%s): skipping filing %s — schema validation failed: %s",
                norm, accession_numbers[i], e,
            )
            continue

        items.append(item)

    # Sort descending by filed_date (most recent first), then truncate.
    items.sort(key=lambda f: f.filed_date or date.min, reverse=True)
    return items[:limit]
