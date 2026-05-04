"""Phase 5 routine test fixtures — mock Claude client + isolated failure log.

The mock client is a pure-Python fixture-replay implementation: tests register
canned responses (or canned exceptions) before invoking call_with_retry; the
mock yields them in queue order on each .messages.parse() call.

This avoids the brittleness of MagicMock-spy chains and gives tests a
specification feel: "given the LLM returns this AgentSignal, then
call_with_retry returns that AgentSignal".

Wave 3 + Wave 4 + Wave 5 reuse this same fixture; the mock object's `.calls`
list captures every kwargs dict for downstream assertion (e.g., "synthesizer
test asserts model='claude-opus-4-7' was passed").
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pydantic import BaseModel


class MockMessages:
    """Mock Anthropic SDK messages object with queueable responses/exceptions."""

    def __init__(self) -> None:
        self._queue: list[tuple[str, object]] = []
        self.calls: list[dict] = []

    def queue_response(self, parsed_output: "BaseModel") -> None:
        """Append a successful response to the queue."""
        self._queue.append(("response", parsed_output))

    def queue_exception(self, exc: BaseException) -> None:
        """Append an exception (raised on next .parse() call)."""
        self._queue.append(("exception", exc))

    async def parse(self, **kwargs) -> object:
        """Mock parse — record kwargs, pop next queued item, return or raise."""
        self.calls.append(dict(kwargs))
        if not self._queue:
            raise RuntimeError(
                f"MockMessages: queue empty on call {len(self.calls)} "
                f"(test setup error — queued fewer responses than test "
                f"expected). kwargs.keys={list(kwargs.keys())}"
            )
        kind, payload = self._queue.pop(0)
        if kind == "exception":
            raise payload  # type: ignore[misc]

        class _Response:
            parsed_output = payload

        return _Response()


class MockAnthropicClient:
    """Mock AsyncAnthropic — exposes a .messages property that's the MockMessages."""

    def __init__(self) -> None:
        self.messages = MockMessages()


@pytest.fixture
def mock_anthropic_client() -> MockAnthropicClient:
    """Per-test fresh MockAnthropicClient. Tests register queued items inline."""
    return MockAnthropicClient()


@pytest.fixture(autouse=True)
def isolated_failure_log(tmp_path, monkeypatch) -> Path:
    """Redirect memory/llm_failures.jsonl to a temp dir for test isolation.

    Auto-applied to every test in tests/routine/ so tests don't pollute the
    real memory/ folder. Yields the temp Path so tests can read records.
    """
    log_path = tmp_path / "memory" / "llm_failures.jsonl"
    # Lazy import — routine.llm_client may not exist yet during RED phase.
    try:
        import routine.llm_client as llm_client_mod
    except ImportError:
        return log_path

    monkeypatch.setattr(llm_client_mod, "LLM_FAILURE_LOG", log_path)
    return log_path
