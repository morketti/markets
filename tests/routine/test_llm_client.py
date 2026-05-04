"""Tests for routine.llm_client.call_with_retry + _log_failure (LLM-04 + LLM-05).

Mocks the AsyncAnthropic boundary via tests/routine/conftest.py's
mock_anthropic_client fixture (fixture-replay pattern). Tests register canned
responses or exceptions; call_with_retry's behavior is asserted via the mock's
.calls list and the isolated_failure_log file (autouse — per-test tmp_path).

Coverage targets per 05-03-llm-client-PLAN.md:
  * Happy path
  * ValidationError → retry → success
  * ValidationError exhaustion → default_factory()
  * APIStatusError → default_factory()
  * APIError → default_factory()
  * Unknown exception → default_factory()
  * Failure log append-only across invocations
  * Failure log record shape (5 keys, UTC timestamp, sort_keys serialization)
  * Failure log message + raw truncation
  * No temperature/top_p/top_k in call site (AST grep)
  * Provenance docstring references virattt source file (INFRA-07)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from analysts.signals import AgentSignal
from routine.llm_client import (
    DEFAULT_MAX_RETRIES,
    call_with_retry,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------
def _make_signal(
    ticker: str = "AAPL",
    analyst_id: str = "buffett",
    verdict: str = "bullish",
    confidence: int = 70,
) -> AgentSignal:
    """Build a valid AgentSignal for queueing as a mock response payload."""
    return AgentSignal(
        ticker=ticker,
        analyst_id=analyst_id,
        computed_at=datetime(2026, 5, 1, 13, 30, 0, tzinfo=timezone.utc),
        verdict=verdict,
        confidence=confidence,
        evidence=["test evidence string"],
        data_unavailable=False,
    )


def _default_factory_signal(ticker: str = "AAPL") -> AgentSignal:
    """Default-factory return for retry-exhaustion path: neutral / data_unavailable=True."""
    return AgentSignal(
        ticker=ticker,
        analyst_id="buffett",
        computed_at=datetime(2026, 5, 1, 13, 30, 0, tzinfo=timezone.utc),
        verdict="neutral",
        confidence=0,
        evidence=["schema_failure"],
        data_unavailable=True,
    )


def _forge_validation_error() -> ValidationError:
    """Construct a real Pydantic ValidationError by attempting an invalid AgentSignal.

    Reused across multiple tests; ensures `isinstance(err, ValidationError)` is True
    and exc.errors() returns a list with at least one error dict.
    """
    try:
        AgentSignal(
            ticker="!!!",
            analyst_id="buffett",
            computed_at=datetime.now(timezone.utc),
        )
    except ValidationError as exc:
        return exc
    raise AssertionError("AgentSignal('!!!') unexpectedly accepted")


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------
async def test_happy_path_returns_parsed_output(mock_anthropic_client) -> None:
    """Single successful call returns the parsed AgentSignal exactly once."""
    expected = _make_signal()
    mock_anthropic_client.messages.queue_response(expected)

    result = await call_with_retry(
        mock_anthropic_client,
        model="claude-sonnet-4-6",
        system="You are Warren Buffett.",
        user="Analyze AAPL.",
        output_format=AgentSignal,
        default_factory=lambda: _default_factory_signal(),
        max_tokens=2000,
        context_label="buffett:AAPL",
    )

    assert result is expected
    assert len(mock_anthropic_client.messages.calls) == 1
    call_kwargs = mock_anthropic_client.messages.calls[0]
    assert call_kwargs["model"] == "claude-sonnet-4-6"
    assert call_kwargs["max_tokens"] == 2000
    assert call_kwargs["output_format"] is AgentSignal
    # Critical: no temp / top_p / top_k forwarded (Pattern #2 lock):
    assert "temperature" not in call_kwargs
    assert "top_p" not in call_kwargs
    assert "top_k" not in call_kwargs


# ---------------------------------------------------------------------------
# ValidationError paths
# ---------------------------------------------------------------------------
async def test_validation_error_then_success(
    mock_anthropic_client, isolated_failure_log
) -> None:
    """First call raises ValidationError → second call succeeds → returns second signal."""
    ve = _forge_validation_error()
    success = _make_signal(verdict="strong_bullish")

    mock_anthropic_client.messages.queue_exception(ve)
    mock_anthropic_client.messages.queue_response(success)

    result = await call_with_retry(
        mock_anthropic_client,
        model="claude-sonnet-4-6",
        system="...",
        user="...",
        output_format=AgentSignal,
        default_factory=lambda: _default_factory_signal(),
        max_tokens=2000,
        context_label="buffett:AAPL",
    )

    assert result is success
    assert len(mock_anthropic_client.messages.calls) == 2

    records = [
        json.loads(line)
        for line in isolated_failure_log.read_text(encoding="utf-8").splitlines()
    ]
    assert len(records) == 1
    assert records[0]["kind"] == "validation_error"
    assert records[0]["label"] == "buffett:AAPL"


async def test_validation_error_exhaustion_returns_default_factory(
    mock_anthropic_client, isolated_failure_log
) -> None:
    """Both attempts raise ValidationError → default_factory() returned, 2 records logged."""
    ve = _forge_validation_error()

    mock_anthropic_client.messages.queue_exception(ve)
    mock_anthropic_client.messages.queue_exception(ve)

    factory_calls = {"n": 0}

    def factory() -> AgentSignal:
        factory_calls["n"] += 1
        return _default_factory_signal()

    result = await call_with_retry(
        mock_anthropic_client,
        model="claude-sonnet-4-6",
        system="...",
        user="...",
        output_format=AgentSignal,
        default_factory=factory,
        max_tokens=2000,
        context_label="buffett:AAPL",
    )

    assert result.verdict == "neutral"
    assert result.data_unavailable is True
    assert result.evidence == ["schema_failure"]
    assert factory_calls["n"] == 1  # default_factory invoked exactly ONCE
    assert len(mock_anthropic_client.messages.calls) == DEFAULT_MAX_RETRIES

    records = [
        json.loads(line)
        for line in isolated_failure_log.read_text(encoding="utf-8").splitlines()
    ]
    assert len(records) == DEFAULT_MAX_RETRIES
    assert all(r["kind"] == "validation_error" for r in records)


# ---------------------------------------------------------------------------
# APIStatusError + APIError paths
# ---------------------------------------------------------------------------
async def test_api_status_error_returns_default_factory(
    mock_anthropic_client, isolated_failure_log
) -> None:
    """APIStatusError(429-class) on both attempts → default_factory; kind='api_error'."""
    from anthropic import APIStatusError

    class _FakeStatus(APIStatusError):
        # Bypass the SDK's __init__ which requires real httpx.Response objects.
        def __init__(self) -> None:  # noqa: D401
            pass

        def __str__(self) -> str:
            return "rate limit (mocked)"

    err = _FakeStatus()
    mock_anthropic_client.messages.queue_exception(err)
    mock_anthropic_client.messages.queue_exception(err)

    result = await call_with_retry(
        mock_anthropic_client,
        model="claude-sonnet-4-6",
        system="...",
        user="...",
        output_format=AgentSignal,
        default_factory=lambda: _default_factory_signal(),
        max_tokens=2000,
        context_label="buffett:AAPL",
    )
    assert result.data_unavailable is True
    records = [
        json.loads(line)
        for line in isolated_failure_log.read_text(encoding="utf-8").splitlines()
    ]
    assert len(records) == 2
    assert all(r["kind"] == "api_error" for r in records)
    # message field is preserved (truncated at 1000 chars; 'rate limit' fits):
    assert "rate limit" in records[0]["message"]


async def test_api_error_returns_default_factory(
    mock_anthropic_client, isolated_failure_log
) -> None:
    """APIError (network class) on both attempts → default_factory; kind='api_error'."""
    from anthropic import APIError

    class _FakeApiError(APIError):
        def __init__(self) -> None:  # noqa: D401
            pass

        def __str__(self) -> str:
            return "network down (mocked)"

    err = _FakeApiError()
    mock_anthropic_client.messages.queue_exception(err)
    mock_anthropic_client.messages.queue_exception(err)

    result = await call_with_retry(
        mock_anthropic_client,
        model="claude-sonnet-4-6",
        system="...",
        user="...",
        output_format=AgentSignal,
        default_factory=lambda: _default_factory_signal(),
        max_tokens=2000,
        context_label="buffett:AAPL",
    )
    assert result.data_unavailable is True
    records = [
        json.loads(line)
        for line in isolated_failure_log.read_text(encoding="utf-8").splitlines()
    ]
    assert all(r["kind"] == "api_error" for r in records)


# ---------------------------------------------------------------------------
# Unknown exception path (defensive cascade prevention)
# ---------------------------------------------------------------------------
async def test_unknown_exception_logged_and_default_factory_returned(
    mock_anthropic_client, isolated_failure_log
) -> None:
    """Any non-API/non-Validation Exception is caught, logged with kind='unknown_error'."""
    mock_anthropic_client.messages.queue_exception(ValueError("weird non-API error"))
    mock_anthropic_client.messages.queue_exception(ValueError("weird non-API error"))

    result = await call_with_retry(
        mock_anthropic_client,
        model="claude-sonnet-4-6",
        system="...",
        user="...",
        output_format=AgentSignal,
        default_factory=lambda: _default_factory_signal(),
        max_tokens=2000,
        context_label="buffett:AAPL",
    )
    assert result.data_unavailable is True
    records = [
        json.loads(line)
        for line in isolated_failure_log.read_text(encoding="utf-8").splitlines()
    ]
    assert len(records) == 2
    assert all(r["kind"] == "unknown_error" for r in records)


# ---------------------------------------------------------------------------
# Failure log discipline
# ---------------------------------------------------------------------------
async def test_failure_log_append_only_across_invocations(
    mock_anthropic_client, isolated_failure_log
) -> None:
    """3 sequential failing invocations → 6 records (2 per invocation); no truncation."""
    ve = _forge_validation_error()

    for _ in range(3):
        mock_anthropic_client.messages.queue_exception(ve)
        mock_anthropic_client.messages.queue_exception(ve)
        await call_with_retry(
            mock_anthropic_client,
            model="claude-sonnet-4-6",
            system="...",
            user="...",
            output_format=AgentSignal,
            default_factory=lambda: _default_factory_signal(),
            max_tokens=2000,
            context_label="buffett:AAPL",
        )

    records = [
        json.loads(line)
        for line in isolated_failure_log.read_text(encoding="utf-8").splitlines()
    ]
    assert len(records) == 3 * DEFAULT_MAX_RETRIES  # 6 records total


async def test_failure_log_record_shape(
    mock_anthropic_client, isolated_failure_log
) -> None:
    """Each record has EXACTLY {timestamp, label, kind, message, raw}; UTC; sort_keys."""
    ve = _forge_validation_error()
    mock_anthropic_client.messages.queue_exception(ve)
    mock_anthropic_client.messages.queue_exception(ve)

    await call_with_retry(
        mock_anthropic_client,
        model="claude-sonnet-4-6",
        system="...",
        user="...",
        output_format=AgentSignal,
        default_factory=lambda: _default_factory_signal(),
        max_tokens=2000,
        context_label="buffett:AAPL",
    )

    lines = isolated_failure_log.read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[0])
    assert set(record.keys()) == {"timestamp", "label", "kind", "message", "raw"}
    # UTC timestamp — ends with '+00:00' (isoformat) OR 'Z' (alternate UTC form):
    assert record["timestamp"].endswith("+00:00") or record["timestamp"].endswith("Z")
    # sort_keys: re-serialize with sort_keys=True and compare to the on-disk line:
    reserialized = json.dumps(record, sort_keys=True)
    assert reserialized == lines[0]


async def test_failure_log_directory_creation(
    mock_anthropic_client, tmp_path, monkeypatch
) -> None:
    """When memory/ does not exist, _log_failure creates parent dirs (mkdir parents=True)."""
    # Override autouse fixture's path with one whose parents we KNOW don't exist:
    fresh_log = tmp_path / "deep" / "nested" / "memory" / "llm_failures.jsonl"
    assert not fresh_log.parent.exists()

    import routine.llm_client as llm_client_mod
    monkeypatch.setattr(llm_client_mod, "LLM_FAILURE_LOG", fresh_log)

    ve = _forge_validation_error()
    mock_anthropic_client.messages.queue_exception(ve)
    mock_anthropic_client.messages.queue_exception(ve)

    await call_with_retry(
        mock_anthropic_client,
        model="claude-sonnet-4-6",
        system="...",
        user="...",
        output_format=AgentSignal,
        default_factory=lambda: _default_factory_signal(),
        max_tokens=2000,
        context_label="buffett:AAPL",
    )

    assert fresh_log.exists()
    assert fresh_log.parent.is_dir()
    assert len(fresh_log.read_text(encoding="utf-8").splitlines()) == 2


async def test_failure_log_message_truncation(
    mock_anthropic_client, isolated_failure_log
) -> None:
    """A 5000-char ValidationError message is truncated to ≤1000 chars; raw to ≤5000."""

    # We need a ValidationError-like object whose .errors() returns a list with
    # an 'input' key whose value is >5000 chars, AND whose str() is >5000 chars.
    # Constructing a real Pydantic v2 ValidationError that meets both conditions
    # is awkward, so we subclass and stub the two attributes call_with_retry uses.
    class _LargeValidation(ValidationError):  # type: ignore[misc]
        def __init__(self) -> None:  # noqa: D401
            pass

        def __str__(self) -> str:
            return "X" * 5000

        def errors(self, *args, **kwargs):  # type: ignore[override]
            return [
                {
                    "input": "Y" * 6000,
                    "msg": "x",
                    "type": "x",
                    "loc": ("x",),
                }
            ]

    err = _LargeValidation()
    mock_anthropic_client.messages.queue_exception(err)
    mock_anthropic_client.messages.queue_exception(err)

    await call_with_retry(
        mock_anthropic_client,
        model="claude-sonnet-4-6",
        system="...",
        user="...",
        output_format=AgentSignal,
        default_factory=lambda: _default_factory_signal(),
        max_tokens=2000,
        context_label="buffett:AAPL",
    )
    records = [
        json.loads(line)
        for line in isolated_failure_log.read_text(encoding="utf-8").splitlines()
    ]
    assert len(records[0]["message"]) <= 1000
    assert records[0]["raw"] is not None
    assert len(records[0]["raw"]) <= 5000


async def test_failure_log_raw_is_null_when_unavailable(
    mock_anthropic_client, isolated_failure_log
) -> None:
    """For non-ValidationError paths (api_error, unknown_error), raw is null."""
    from anthropic import APIError

    class _FakeApiError(APIError):
        def __init__(self) -> None:  # noqa: D401
            pass

    err = _FakeApiError()
    mock_anthropic_client.messages.queue_exception(err)
    mock_anthropic_client.messages.queue_exception(err)

    await call_with_retry(
        mock_anthropic_client,
        model="claude-sonnet-4-6",
        system="...",
        user="...",
        output_format=AgentSignal,
        default_factory=lambda: _default_factory_signal(),
        max_tokens=2000,
        context_label="buffett:AAPL",
    )
    records = [
        json.loads(line)
        for line in isolated_failure_log.read_text(encoding="utf-8").splitlines()
    ]
    assert records[0]["raw"] is None


# ---------------------------------------------------------------------------
# AST / source-level invariants on routine/llm_client.py
# ---------------------------------------------------------------------------
def test_no_temperature_top_p_top_k_in_call_site() -> None:
    """routine/llm_client.py never passes temperature/top_p/top_k to messages.parse.

    Opus 4.7 returns 400 on these parameters (05-RESEARCH.md Pattern #2 lock).
    Greppable guard so a future contributor adding temperature= here gets caught.
    """
    source = Path("routine/llm_client.py").read_text(encoding="utf-8")
    assert "temperature=" not in source, "Opus 4.7 rejects temperature= per Pattern #2"
    assert "top_p=" not in source, "Opus 4.7 rejects top_p= per Pattern #2"
    assert "top_k=" not in source, "Opus 4.7 rejects top_k= per Pattern #2"


def test_provenance_header_references_virattt() -> None:
    """INFRA-07: routine/llm_client.py docstring names the virattt source file."""
    source = Path("routine/llm_client.py").read_text(encoding="utf-8")
    assert "virattt/ai-hedge-fund/src/utils/llm.py" in source


def test_module_constants_exposed() -> None:
    """LLM_FAILURE_LOG (Path) + DEFAULT_MAX_RETRIES (int=2) are public module attrs."""
    from routine.llm_client import DEFAULT_MAX_RETRIES, LLM_FAILURE_LOG

    assert isinstance(LLM_FAILURE_LOG, Path)
    assert str(LLM_FAILURE_LOG).replace("\\", "/").endswith("memory/llm_failures.jsonl")
    assert DEFAULT_MAX_RETRIES == 2
