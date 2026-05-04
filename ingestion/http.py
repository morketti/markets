# novel-to-this-project — Phase 2 shared requests.Session (Pitfall #2 EDGAR User-Agent — project-original).
"""Shared HTTP client for the ingestion package.

Single process-wide requests.Session with:
- EDGAR-compliant User-Agent header (Pitfall #2 in 02-RESEARCH.md). The default
  is `"Markets Personal Research (mohanraval15@gmail.com)"`; override per
  process via the `MARKETS_USER_AGENT` environment variable. Without a
  compliant UA, SEC EDGAR returns 403 instead of the requested submissions
  JSON, so this header is the difference between "filings work" and "filings
  break silently".
- urllib3 Retry policy (Pitfall #1 — yfinance/Yahoo silent breakage and
  upstream 429 rate-limits): 3 retries with backoff_factor=0.3 on status
  429 / 500 / 502 / 503 / 504. Allowed methods restricted to GET/HEAD so we
  never silently retry a POST that may have already partially succeeded.

DEFAULT_TIMEOUT (10s) is exposed as a module-level constant; callers pass it
per request via `session.get(url, timeout=DEFAULT_TIMEOUT)`. The Session
itself does not carry a timeout attribute (requests doesn't expose one).

`polite_sleep` is a per-source min-interval helper for code paths that hit
domains with self-imposed politeness (Reddit RSS, EDGAR, FinViz scrape). The
caller owns the `last_call: dict[str, float]` state so each refresh run gets
its own clock — no module-level singletons that bleed between tests.
"""
from __future__ import annotations

import os
import time
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT: str = os.environ.get(
    "MARKETS_USER_AGENT",
    "Markets Personal Research (mohanraval15@gmail.com)",
)

DEFAULT_TIMEOUT: float = 10.0

# Process-wide singleton; lazy-init on first get_session() call. Reset by
# importlib.reload(ingestion.http) (used in env-override tests).
_SESSION: Optional[requests.Session] = None


def get_session() -> requests.Session:
    """Return the process-shared requests.Session, constructing on first call.

    Idempotent: every subsequent call returns the same instance so connection
    pooling and the retry policy persist across the run.
    """
    global _SESSION
    if _SESSION is not None:
        return _SESSION

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    retry = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET", "HEAD"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    _SESSION = session
    return _SESSION


def polite_sleep(source: str, last_call: dict[str, float], min_interval: float) -> None:
    """Sleep just long enough that consecutive calls to `source` are >=`min_interval`s apart.

    Stateful via the caller-owned `last_call` dict (mapping source -> monotonic
    timestamp of the last call). First call for a given source is a no-op
    fast-path — there is nothing to gate against. Updates `last_call[source]`
    to the post-sleep timestamp so the NEXT call sees an accurate clock.

    Used by ingestion modules whose upstream has self-imposed rate limits:
    EDGAR (10 req/s -> ~0.11s), Reddit RSS (2s between calls), FinViz scrape
    (~0.5s).
    """
    last = last_call.get(source)
    if last is not None:
        elapsed = time.monotonic() - last
        gap = min_interval - elapsed
        if gap > 0:
            time.sleep(gap)
    last_call[source] = time.monotonic()
