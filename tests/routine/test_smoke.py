"""Wave 0 smoke test — confirms the anthropic SDK installed correctly.

After Wave 0 ships pyproject.toml's anthropic>=0.95,<1 dep, this test
verifies the public surface that Wave 2 (routine/llm_client.py) depends on
is importable. If this test fails, Wave 1+ can't proceed.
"""
from __future__ import annotations


def test_anthropic_sdk_imports() -> None:
    """SDK public surface needed by routine/llm_client.py is importable."""
    from anthropic import APIError, APIStatusError, AsyncAnthropic

    assert AsyncAnthropic is not None
    assert APIError is not None
    assert APIStatusError is not None


def test_anthropic_messages_parse_present() -> None:
    """messages.parse() is the canonical 2026 structured-output API.

    Confirms the attribute path exists on a constructed client instance —
    a regression guard against a future SDK rename. We never call .parse()
    here (no auth, no network).
    """
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key="sk-ant-test-not-real")
    assert hasattr(client.messages, "parse"), (
        "anthropic SDK must expose client.messages.parse — required by "
        "05-RESEARCH.md Pattern #2; if this attribute is missing, the "
        "pinned dep version is wrong."
    )
