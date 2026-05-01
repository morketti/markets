"""Shared HTTP client for the ingestion package — STUB.

This module's contract is declared here for downstream plans, but the real
implementation lands in Task 2 of Plan 02-01 (TDD: tests fail until then).

Public surface:
    USER_AGENT     module-level string, EDGAR-compliant per Pitfall #2
    DEFAULT_TIMEOUT  module-level float, seconds — callers pass per request
    get_session()  returns a process-shared requests.Session with retry policy
    polite_sleep() per-source min-interval helper, no real network
"""
from __future__ import annotations

import os

USER_AGENT: str = os.environ.get(
    "MARKETS_USER_AGENT",
    "Markets Personal Research (mohanraval15@gmail.com)",
)

DEFAULT_TIMEOUT: float = 10.0


def get_session():  # type: ignore[no-untyped-def]
    """Return a process-shared requests.Session — implemented in Task 2."""
    raise NotImplementedError("populated in Task 2")


def polite_sleep(source: str, last_call: dict, min_interval: float) -> None:
    """Sleep so consecutive calls to `source` are min_interval seconds apart — Task 2."""
    raise NotImplementedError("populated in Task 2")
