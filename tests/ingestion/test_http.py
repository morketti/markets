"""Probes 2-W1-01 (UA header) and 2-W1-02 (retry policy) for ingestion.http.

Every test mocks at the `responses` layer (or asserts module-level state) — no
real network. See 02-VALIDATION.md probe table.
"""
from __future__ import annotations

import importlib
import re
import time

import pytest
import requests
import responses

import ingestion.http as ingestion_http
from ingestion.http import DEFAULT_TIMEOUT, USER_AGENT, get_session, polite_sleep


# Probe 2-W1-01 — User-Agent header is present and EDGAR-compliant
def test_session_has_compliant_user_agent() -> None:
    session = get_session()
    ua = session.headers["User-Agent"]
    # Default form: "Markets Personal Research (mohanraval15@gmail.com)" — name
    # then space then "(...email-with-@...)". Allow ANY name + ANY @-bearing
    # parenthetical so env override is also honored by the same regex.
    assert re.match(r"^.+ \(.+@.+\)$", ua), f"non-compliant UA: {ua!r}"


# Probe 2-W1-01 — env override reaches the session
def test_session_user_agent_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    # Reset module-level state then re-import with env set so USER_AGENT
    # picks up the override.
    monkeypatch.setenv("MARKETS_USER_AGENT", "TestAgent test@example.com (override)")
    importlib.reload(ingestion_http)
    try:
        assert ingestion_http.USER_AGENT == "TestAgent test@example.com (override)"
        s = ingestion_http.get_session()
        assert s.headers["User-Agent"] == "TestAgent test@example.com (override)"
    finally:
        # Restore module to default UA for sibling tests.
        monkeypatch.delenv("MARKETS_USER_AGENT", raising=False)
        importlib.reload(ingestion_http)


def test_session_singleton() -> None:
    a = get_session()
    b = get_session()
    assert a is b, "get_session must return the same Session instance"


def test_session_has_default_timeout_constant() -> None:
    # The Session itself does not carry a timeout; callers pass
    # `timeout=DEFAULT_TIMEOUT` per request. We just assert the constant.
    assert DEFAULT_TIMEOUT == 10.0
    assert isinstance(USER_AGENT, str) and len(USER_AGENT) > 0


# Probe 2-W1-02 — retry on 503 then success
@responses.activate
def test_retry_on_503_then_success() -> None:
    url = "https://example.test/x"
    responses.add(responses.GET, url, status=503)
    responses.add(responses.GET, url, status=200, json={"ok": True})

    s = get_session()
    r = s.get(url, timeout=DEFAULT_TIMEOUT)
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    # 1 initial + at least 1 retry == 2 calls.
    assert len(responses.calls) >= 2


# Probe 2-W1-02 — retry on 429 then success (same policy)
@responses.activate
def test_retry_on_429_then_success() -> None:
    url = "https://example.test/y"
    responses.add(responses.GET, url, status=429)
    responses.add(responses.GET, url, status=200, json={"ok": True})

    s = get_session()
    r = s.get(url, timeout=DEFAULT_TIMEOUT)
    assert r.status_code == 200
    assert len(responses.calls) >= 2


# Probe 2-W1-02 — retry policy gives up after exactly 3 retries
@responses.activate
def test_retry_gives_up_after_3() -> None:
    url = "https://example.test/z"
    # 4 = 1 initial + 3 retries; if policy enforced, attempt 5 never fires.
    for _ in range(5):
        responses.add(responses.GET, url, status=503)

    s = get_session()
    try:
        r = s.get(url, timeout=DEFAULT_TIMEOUT)
        # Either we got a final 503 OR urllib3 raised — both prove the retry
        # policy stopped at 3 retries. status_code == 503 covers the first
        # branch.
        assert r.status_code == 503
    except requests.exceptions.RetryError:
        pass
    # 1 initial + 3 retries = 4 attempts; never more.
    assert len(responses.calls) >= 4
    assert len(responses.calls) <= 4


def test_polite_sleep_enforces_min_interval() -> None:
    state: dict[str, float] = {}
    polite_sleep("yahoo", state, 0.1)  # first call: source not in state -> 0 sleep
    t0 = time.monotonic()
    polite_sleep("yahoo", state, 0.1)  # second call: enforces 0.1s gap
    elapsed = time.monotonic() - t0
    # 10ms slack for monotonic clock granularity on Windows.
    assert elapsed >= 0.09, f"polite_sleep didn't enforce interval; elapsed={elapsed:.4f}s"
    # State updated for next call.
    assert "yahoo" in state


def test_polite_sleep_no_sleep_on_first_call() -> None:
    state: dict[str, float] = {}
    t0 = time.monotonic()
    polite_sleep("first", state, 1.0)  # huge interval but source not seen yet
    elapsed = time.monotonic() - t0
    # First call must not sleep (fast path); allow up to 50ms slack.
    assert elapsed < 0.05, f"first call slept {elapsed:.4f}s; should be ~0"
