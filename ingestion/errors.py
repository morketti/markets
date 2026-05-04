# novel-to-this-project — Phase 2 exception hierarchy (project-original).
"""Custom exception hierarchy for the ingestion package.

Three levels:
- IngestionError: base — every ingestion failure inherits from this so callers
  (refresh orchestrator in Plan 02-06) can `except IngestionError` once and
  branch on the concrete subclass via isinstance.
- NetworkError: HTTP-layer failure — timeouts, connection errors, 4xx/5xx
  after the retry policy in ingestion/http.py has exhausted its attempts. Also
  covers the EDGAR 403-without-UA case (Pitfall #2 in 02-RESEARCH.md).
- SchemaDriftError: upstream returned 200 but the payload didn't match the
  Pydantic shape we expected. Indicates yfinance / Yahoo / EDGAR changed an
  endpoint silently (Pitfall #1 in 02-RESEARCH.md).

These types let the orchestrator distinguish "the network is broken, retry
later" from "the upstream API changed, page a human" without parsing exception
messages.
"""
from __future__ import annotations


class IngestionError(Exception):
    """Base for all ingestion failures."""


class NetworkError(IngestionError):
    """HTTP-layer failure: timeout, connection error, or 4xx/5xx after retries."""


class SchemaDriftError(IngestionError):
    """Upstream returned 200 but the payload didn't match the expected shape."""
