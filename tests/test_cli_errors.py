"""Unit tests for cli/_errors.py — format_validation_error.

Probe coverage:
- 1-W3-09: format_validation_error renders ValidationError as multi-line CLI
  string with field paths and "got: ..." input echoes — never a raw stack trace.

WATCH-05: validation errors must produce actionable Pydantic-derived messages.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from analysts.schemas import TickerConfig
from cli._errors import format_validation_error


def test_format_validation_error() -> None:
    """ValidationError on TickerConfig(thesis_price=-1) renders cleanly (1-W3-09)."""
    with pytest.raises(ValidationError) as exc_info:
        TickerConfig(ticker="AAPL", thesis_price=-1)
    rendered = format_validation_error(exc_info.value)
    # Header: "validation failed (N error[s]):"
    assert rendered.startswith("validation failed ("), (
        f"missing 'validation failed' header; got: {rendered!r}"
    )
    assert "error" in rendered.splitlines()[0]
    # Field path surfaced
    assert "thesis_price" in rendered, (
        f"missing 'thesis_price' field path; got: {rendered!r}"
    )
    # Pydantic's own message bubbles through (we use ValueError("thesis_price must be positive"))
    assert "must be positive" in rendered, (
        f"missing 'must be positive' message; got: {rendered!r}"
    )
    # Input echoed in "got: -1" or "got: -1.0" form
    assert "got: -1" in rendered, (
        f"missing 'got: -1' input echo; got: {rendered!r}"
    )
    # No URL noise (we pass include_url=False)
    assert "errors.pydantic.dev" not in rendered
