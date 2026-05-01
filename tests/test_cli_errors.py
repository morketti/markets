"""Unit tests for cli/_errors.py — format_validation_error.

Probe coverage:
- 1-W3-09: format_validation_error renders ValidationError as multi-line CLI
  string with field paths and "got: ..." input echoes — never a raw stack trace.
- 1-W3-10: main() ValidationError handler routes to stderr with exit 2 (e2e wiring).
- 1-W3-11: main() FileNotFoundError handler routes to stderr with exit 1 (e2e wiring).

WATCH-05: validation errors must produce actionable Pydantic-derived messages.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from analysts.schemas import TickerConfig
from cli._errors import format_validation_error
from cli.main import main


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


def test_main_validation_error_to_stderr(
    empty_watchlist_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """main() catches ValidationError, emits multi-line message to stderr, exits 2 (1-W3-10)."""
    rc = main(
        ["add", "AAPL", "--thesis", "-1", "--watchlist", str(empty_watchlist_path)]
    )
    captured = capsys.readouterr()
    assert rc == 2
    assert "validation failed" in captured.err
    assert "thesis_price" in captured.err
    assert "Traceback" not in captured.err
    # ValidationError path must not write to stdout.
    assert captured.out == ""


def test_main_file_not_found_to_stderr(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """main() catches FileNotFoundError, emits to stderr, exits 1 (1-W3-11).

    `add` against a watchlist path whose parent dir does not exist forces
    tempfile.NamedTemporaryFile in save_watchlist to raise FileNotFoundError
    (OSError subclass) — exercising the dispatcher's FileNotFoundError branch.
    """
    missing_parent = tmp_path / "missing-dir" / "watchlist.json"
    rc = main(["add", "AAPL", "--watchlist", str(missing_parent)])
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.err.startswith("error:")
    assert "Traceback" not in captured.err
