"""Integration tests for `markets remove` subcommand.

Probes covered:
- 1-W3-06 happy path (test_remove_happy_path)
- 1-W3-07 did-you-mean suggestion (test_remove_suggests_close_match)
- 1-W3-08 no-match-no-suggestion (test_remove_no_match_no_suggestion)

Requirement covered: WATCH-03.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from cli.main import main
from watchlist.loader import load_watchlist


def test_remove_happy_path(seeded_watchlist_path: Path) -> None:
    """`markets remove AAPL --yes` removes AAPL, keeps NVDA (1-W3-06)."""
    rc = main(["remove", "AAPL", "--yes", "--watchlist", str(seeded_watchlist_path)])
    assert rc == 0
    wl = load_watchlist(seeded_watchlist_path)
    assert "AAPL" not in wl.tickers
    assert "NVDA" in wl.tickers


def test_remove_suggests_close_match(
    seeded_watchlist_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Typo `AAPK` triggers `did you mean 'AAPL'?` (1-W3-07)."""
    rc = main(["remove", "AAPK", "--yes", "--watchlist", str(seeded_watchlist_path)])
    assert rc != 0
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "did you mean" in output, (
        f"expected 'did you mean' in output; got stdout={captured.out!r} stderr={captured.err!r}"
    )
    assert "AAPL" in output


def test_remove_no_match_no_suggestion(
    seeded_watchlist_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`ZZZZZ` has no close match below cutoff 0.6 — no spurious suggestion (1-W3-08)."""
    rc = main(["remove", "ZZZZZ", "--yes", "--watchlist", str(seeded_watchlist_path)])
    assert rc != 0
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "did you mean" not in output, (
        f"unexpected 'did you mean' in output: {output!r}"
    )
