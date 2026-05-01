---
phase: 02-ingestion-keyless-data-plane
plan: 03
type: tdd
wave: 2
depends_on: [02-01]
files_modified:
  - ingestion/filings.py
  - tests/ingestion/test_filings.py
  - tests/ingestion/fixtures/edgar_company_tickers.json
  - tests/ingestion/fixtures/edgar_submissions_aapl.json
  - tests/ingestion/fixtures/edgar_403.txt
autonomous: true
requirements: [DATA-03]
must_haves:
  truths:
    - "fetch_filings(ticker) returns a list[FilingMetadata] of recent 10-K, 10-Q, 8-K filings when EDGAR responds with valid JSON"
    - "fetch_filings sets EDGAR-compliant User-Agent header (verified by responses lib intercepting the actual headers)"
    - "fetch_filings handles 403 (missing/wrong UA) by raising NetworkError — and the orchestrator's try/except catches that and continues, but THIS plan only verifies the raise"
    - "fetch_filings retries on 429 (rate-limit) per the shared session's retry policy and ultimately succeeds when EDGAR returns 200"
    - "Ticker → CIK lookup uses https://www.sec.gov/files/company_tickers.json and zero-pads CIK to 10 digits"
    - "Only forms in {10-K, 10-Q, 8-K} are surfaced by default; other forms filtered out at module boundary"
  artifacts:
    - path: "ingestion/filings.py"
      provides: "fetch_filings(ticker, *, forms=('10-K','10-Q','8-K')) -> list[FilingMetadata]; CIK lookup helper"
      min_lines: 70
    - path: "tests/ingestion/test_filings.py"
      provides: "Probes 2-W2-06 (happy), 2-W2-07 (403), 2-W2-08 (429 retry)"
      min_lines: 60
    - path: "tests/ingestion/fixtures/edgar_company_tickers.json"
      provides: "Real-shape EDGAR ticker→CIK index for AAPL/NVDA/BRK-B"
    - path: "tests/ingestion/fixtures/edgar_submissions_aapl.json"
      provides: "Real-shape EDGAR submissions JSON for CIK0000320193"
  key_links:
    - from: "ingestion/filings.py"
      to: "ingestion.http.get_session()"
      via: "shared session for UA + retries"
      pattern: "from ingestion.http import"
    - from: "ingestion/filings.py"
      to: "ingestion.errors.NetworkError"
      via: "raised on 403 / unrecoverable HTTP failure"
      pattern: "raise NetworkError"
    - from: "ingestion/filings.py"
      to: "analysts.data.FilingMetadata"
      via: "Pydantic validation per filing"
      pattern: "FilingMetadata\\("
---

<objective>
Wave 2 / Source B: SEC EDGAR filings ingestion. Fetches recent 10-K, 10-Q, 8-K filing metadata for a ticker via the SEC EDGAR JSON API with a compliant User-Agent header. Implements DATA-03 in full.

Purpose: EDGAR is the only data source with a hard compliance requirement (User-Agent must include name + email per SEC's fair-access policy — without it, requests get 403'd, per Pitfall #2). Isolating EDGAR into its own plan ensures the UA header story is correct before integration and creates a clear test boundary for the 403-without-UA probe. The CIK lookup logic (ticker → 10-digit zero-padded CIK) is also EDGAR-specific and lives entirely in this module.

Output: ingestion/filings.py with `fetch_filings(ticker, *, forms=('10-K','10-Q','8-K'))` returning `list[FilingMetadata]`. Three probes covered (happy, 403, 429-retry). Three fixture files (CIK index, submissions JSON, 403 body).
</objective>

<execution_context>
@C:/Users/Mohan/.claude/workflows/execute-plan.md
@C:/Users/Mohan/.claude/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/02-ingestion-keyless-data-plane/02-RESEARCH.md
@.planning/phases/02-ingestion-keyless-data-plane/02-VALIDATION.md
@.planning/phases/02-ingestion-keyless-data-plane/02-01-SUMMARY.md

@analysts/schemas.py

<interfaces>
<!-- Wave 1 contracts this plan consumes (landed in 02-01) -->

From ingestion/http.py:
```python
def get_session() -> requests.Session
DEFAULT_TIMEOUT: float = 10.0
USER_AGENT: str = "Markets Personal Research (mohanraval15@gmail.com)"
def polite_sleep(source: str, last_call: dict, min_interval: float) -> None
```

From ingestion/errors.py:
```python
class NetworkError(IngestionError)
class SchemaDriftError(IngestionError)
```

From analysts/data/filings.py:
```python
class FilingMetadata(BaseModel):
    ticker: str
    fetched_at: datetime
    source: Literal["edgar"] = "edgar"
    data_unavailable: bool = False
    cik: Optional[str] = None  # zero-padded 10-digit
    form_type: Literal["10-K","10-Q","8-K","DEF 14A","S-1","20-F","6-K","OTHER"]
    accession_number: Optional[str]
    filed_date: Optional[date]
    primary_document: Optional[str]
    summary: str = ""
```

NEW contracts this plan creates (Plan 02-06 imports):

ingestion/filings.py:
```python
EDGAR_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
EDGAR_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

def lookup_cik(ticker: str) -> Optional[str]:
    """Look up a ticker's 10-digit zero-padded CIK from EDGAR's company_tickers
    index. Returns None when the ticker isn't found. Caches the index in-process
    after first call (no disk cache in this plan; that's a 02-06 enhancement)."""

def fetch_filings(
    ticker: str,
    *,
    forms: tuple[str, ...] = ("10-K", "10-Q", "8-K"),
    limit: int = 20,
) -> list[FilingMetadata]:
    """Fetch recent filings for `ticker` from EDGAR. Filters to `forms`,
    returns at most `limit` most-recent. Raises NetworkError on 403 (UA
    compliance failure) — the orchestrator catches and continues with
    data_unavailable. Raises SchemaDriftError when EDGAR returns 200 but
    the JSON shape we don't recognize. Returns [] (empty list) for an
    unknown ticker (CIK lookup miss)."""
```

EDGAR submissions JSON shape (real example for AAPL CIK 320193):
```json
{
  "cik": "320193",
  "name": "Apple Inc.",
  "tickers": ["AAPL"],
  "filings": {
    "recent": {
      "accessionNumber": ["0000320193-26-000001", ...],
      "filingDate": ["2026-04-30", ...],
      "form": ["8-K", "10-Q", "10-K", ...],
      "primaryDocument": ["aapl-20260331.htm", ...],
      "primaryDocDescription": ["FORM 8-K", ...]
    }
  }
}
```

EDGAR company_tickers.json shape:
```json
{
  "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
  "1": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"},
  ...
}
```
Note: `cik_str` is an int — must zero-pad to 10 digits for the submissions URL.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: TDD ingestion/filings.py — happy path + 403 + 429 retry</name>
  <files>tests/ingestion/test_filings.py, tests/ingestion/fixtures/edgar_company_tickers.json, tests/ingestion/fixtures/edgar_submissions_aapl.json, tests/ingestion/fixtures/edgar_403.txt, ingestion/filings.py</files>
  <behavior>
    Probes 2-W2-06 (happy), 2-W2-07 (403), 2-W2-08 (429 retry → 200).

    test_filings.py:
    - test_lookup_cik_happy (`@responses.activate`): mock GET to EDGAR_TICKERS_URL returning the fixture. Assert: `lookup_cik("AAPL") == "0000320193"` (10-digit zero-padded). Assert: responses.calls[0].request.headers["User-Agent"] starts with "Markets Personal Research".
    - test_lookup_cik_unknown_returns_none: same fixture; `lookup_cik("XXXY") is None`.
    - test_lookup_cik_caches_in_process: call lookup_cik twice; assert `len(responses.calls) == 1` (second call hits cache, not network).
    - test_filings_happy (probe 2-W2-06, `@responses.activate`): mock company_tickers.json AND mock submissions endpoint with the AAPL fixture. Call `fetch_filings("AAPL")`. Assert: returns list[FilingMetadata] of length ≤ 20, each item has form_type ∈ {"10-K","10-Q","8-K"}, sorted by filed_date desc, ticker == "AAPL", source == "edgar", cik == "0000320193", data_unavailable is False. Verify request to data.sec.gov used UA header.
    - test_filings_filters_forms: same fixture but call `fetch_filings("AAPL", forms=("10-K",))`. Assert all returned items have form_type == "10-K"; assert at least one (the fixture must include at least one 10-K).
    - test_filings_unknown_ticker: mock company_tickers.json (with AAPL only); call `fetch_filings("XXXY")`. Assert: returns [] (empty list — CIK miss is not an error, no network call to submissions).
    - test_filings_403 (probe 2-W2-07, `@responses.activate`): mock company_tickers.json happy + mock submissions endpoint to return 403 with `edgar_403.txt` body and Content-Type text/plain. Assert: `pytest.raises(NetworkError)` with a message that mentions "403" or "User-Agent".
    - test_filings_429_retry (probe 2-W2-08, `@responses.activate`): register the submissions URL TWICE — first response 429 (with `Retry-After: 1`), second response 200 with the fixture. Assert: `fetch_filings("AAPL")` returns list of FilingMetadata; assert `len(responses.calls) >= 3` (1 to company_tickers + 2 to submissions = retry fired).
    - test_filings_schema_drift: mock company_tickers.json happy + mock submissions to return 200 with `{}` (empty dict, no "filings" key). Assert: `pytest.raises(SchemaDriftError)`.
  </behavior>
  <action>
    RED phase:
    1. Create `tests/ingestion/fixtures/edgar_company_tickers.json` with at least 5 entries:
       ```json
       {
         "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
         "1": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"},
         "2": {"cik_str": 1067983, "ticker": "BRK-B", "title": "BERKSHIRE HATHAWAY INC"},
         "3": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
         "4": {"cik_str": 1018724, "ticker": "AMZN", "title": "AMAZON COM INC"}
       }
       ```
    2. Create `tests/ingestion/fixtures/edgar_submissions_aapl.json` — real-shape submissions JSON with 25 recent filings spanning 10-K (1), 10-Q (4), 8-K (10), DEF 14A (1), and a few other forms (S-3, 4, etc.) so the form-filter probe has signal. Filing dates from 2025-01-01 → 2026-04-30 in descending order. Required keys: `cik`, `name`, `tickers`, `filings.recent.{accessionNumber, filingDate, form, primaryDocument, primaryDocDescription}` (parallel arrays).
    3. Create `tests/ingestion/fixtures/edgar_403.txt`: plain text body that EDGAR returns: `Your Request Originates from an Undeclared Automated Tool\n\nFor more information please review:\nhttps://www.sec.gov/os/accessing-edgar-data\n` (paraphrase OK; just non-empty so the test sees a body).
    4. Write `tests/ingestion/test_filings.py` with the 9 tests above. Imports: `import pytest, responses, json`, `from pathlib import Path`, `from ingestion.filings import lookup_cik, fetch_filings, EDGAR_TICKERS_URL, EDGAR_SUBMISSIONS_URL, _CIK_CACHE` (last one for cache reset between tests via fixture).
    5. Add a pytest fixture in test_filings.py (or in tests/ingestion/conftest.py) that clears `_CIK_CACHE` before each test — important for cache-related tests not to bleed.
    6. Run `uv run pytest tests/ingestion/test_filings.py -x -q` → all fail (module empty).
    7. Commit: `test(02-03): add failing tests for EDGAR filings (probes 2-W2-06..08)`

    GREEN phase:
    8. Implement `ingestion/filings.py`:
       - Module docstring: cite Pitfall #2 (UA compliance) and DATA-03.
       - Imports: `from datetime import date, datetime, timezone`, `from typing import Optional`, `import json`, `import requests`, `from ingestion.http import get_session, DEFAULT_TIMEOUT, polite_sleep`, `from ingestion.errors import NetworkError, SchemaDriftError`, `from analysts.schemas import normalize_ticker`, `from analysts.data.filings import FilingMetadata`.
       - Constants: `EDGAR_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"`, `EDGAR_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"`, `_CIK_CACHE: dict[str, str] = {}`, `_LAST_CALL: dict[str, float] = {}`, `_MIN_INTERVAL = 0.11` (10 req/sec hard cap → 0.11s spacing).
       - `def lookup_cik(ticker: str) -> Optional[str]`:
         - normalize ticker; if None → return None.
         - if `_CIK_CACHE` is non-empty (already loaded), look up directly. Note: cache is the WHOLE index, not per-ticker — first call populates the entire mapping.
         - else: `polite_sleep("edgar", _LAST_CALL, _MIN_INTERVAL)`; GET EDGAR_TICKERS_URL via shared session, timeout=DEFAULT_TIMEOUT. If response.status_code != 200 → raise NetworkError with status code. Parse JSON; build `_CIK_CACHE[entry["ticker"]] = f"{int(entry['cik_str']):010d}"` for each entry.value. Return `_CIK_CACHE.get(normalized)`.
       - `def fetch_filings(ticker, *, forms=("10-K","10-Q","8-K"), limit=20) -> list[FilingMetadata]`:
         - normalize ticker. cik = lookup_cik(normalized). If cik is None → return [].
         - polite_sleep, then GET EDGAR_SUBMISSIONS_URL.format(cik=cik). On status 403: raise NetworkError(f"EDGAR 403 — User-Agent header may not be compliant. Header sent: {sess.headers.get('User-Agent')}"). On status 429: the retry adapter from get_session() handles up to 3 retries; if we still see 429, raise NetworkError. On status != 200: raise NetworkError with status.
         - Parse JSON. If "filings" not in payload OR "recent" not in payload["filings"] → raise SchemaDriftError("EDGAR submissions JSON missing 'filings.recent' key").
         - Walk parallel arrays: `recent = payload["filings"]["recent"]`; `for i in range(len(recent["accessionNumber"]))`: check if `recent["form"][i] in forms`; build FilingMetadata.
         - form_type validation: if the form value isn't in our schema's Literal, set form_type="OTHER" (DATA-03 says we surface 10-K/10-Q/8-K; the FilingMetadata schema accepts a wider Literal so the type system stays sound, but the function-level filter is what enforces the user-visible contract).
         - filed_date: parse `recent["filingDate"][i]` (YYYY-MM-DD string) → `date.fromisoformat(...)`.
         - Sort the result list by filed_date descending; truncate to `limit`.
         - Wrap each FilingMetadata construction in try/except ValidationError → if any individual filing fails schema, log via `logging.warning` and skip (don't fail the whole fetch).
       - Use `logging.getLogger(__name__)` for the warnings.
    9. Run `uv run pytest tests/ingestion/test_filings.py -v` → all 9 green.
    10. Coverage: `uv run pytest --cov=ingestion.filings --cov-branch tests/ingestion/test_filings.py` → ≥90% line / ≥85% branch.
    11. Run plan-scoped suite: `uv run pytest tests/ingestion/ -v`.
    12. Commit: `feat(02-03): implement EDGAR filings fetch with UA compliance + retry`

    Probe ID test docstring comments:
    - 2-W2-06 → `test_filings_happy`
    - 2-W2-07 → `test_filings_403`
    - 2-W2-08 → `test_filings_429_retry`
  </action>
  <verify>
    <automated>uv run pytest tests/ingestion/test_filings.py -v &amp;&amp; uv run pytest --cov=ingestion.filings --cov-branch tests/ingestion/test_filings.py</automated>
  </verify>
  <done>9 filings tests green. ingestion/filings.py at ≥90% line / ≥85% branch. Three EDGAR fixtures committed. UA header verified at the responses-lib boundary. 403 surfaces as NetworkError with diagnostic message. 429 path uses the shared session's retry adapter. Schema-drift surfaces as SchemaDriftError. Probes 2-W2-06, 2-W2-07, 2-W2-08 satisfied.</done>
</task>

</tasks>

<verification>
- Probes covered: 2-W2-06, 2-W2-07, 2-W2-08.
- Requirement satisfied: DATA-03 (10-K/10-Q/8-K from EDGAR with compliant User-Agent header).
- Coverage gates: ≥90% line / ≥85% branch on ingestion/filings.py.
- Zero real network — all EDGAR HTTP via responses lib.
- `uv run pytest -x -q` (whole repo) — all green.

## Cross-Scope Risks

_vault_status=budget_exhausted; re-run /gmd:plan-phase --replan after vault-maintain_
</verification>

<success_criteria>
1. fetch_filings(ticker) returns list[FilingMetadata] of recent 10-K/10-Q/8-K filings with valid CIK + accession_number + filed_date + primary_document.
2. EDGAR-compliant User-Agent header verified by responses lib intercepting actual headers.
3. 403 raises NetworkError with diagnostic; 429 retries via shared session; schema drift raises SchemaDriftError.
4. CIK lookup caches in-process — second call doesn't hit network.
5. Unknown ticker returns [] (graceful).
6. All three probes mapped to named test functions with probe-id comments.
7. Plan 02-06 can call fetch_filings as the EDGAR public entry point.
</success_criteria>

<output>
After completion, create `.planning/phases/02-ingestion-keyless-data-plane/02-03-SUMMARY.md`.
</output>
