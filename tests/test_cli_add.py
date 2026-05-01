"""Integration tests for `markets add` subcommand.

Probes covered:
- 1-W3-01 happy path (test_add_happy_path)
- 1-W3-02 duplicate rejection (test_add_duplicate_rejected)
- 1-W3-03 case normalization (test_add_normalizes_case)
- 1-W3-04 BRK.B → BRK-B normalization (test_add_brk_normalizes_to_hyphen)
- 1-W3-05 all-flags coverage (test_add_all_flags)

Requirements covered: WATCH-02, WATCH-04.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from cli.main import main
from watchlist.loader import load_watchlist


def test_add_happy_path(empty_watchlist_path: Path) -> None:
    """`markets add AAPL --lens value --thesis 200` writes a valid file (1-W3-01)."""
    rc = main([
        "add", "AAPL",
        "--lens", "value",
        "--thesis", "200",
        "--watchlist", str(empty_watchlist_path),
    ])
    assert rc == 0
    wl = load_watchlist(empty_watchlist_path)
    assert "AAPL" in wl.tickers
    cfg = wl.tickers["AAPL"]
    assert cfg.thesis_price == 200.0
    assert cfg.long_term_lens == "value"
    assert cfg.created_at is not None
    assert cfg.updated_at is not None


def test_add_duplicate_rejected(empty_watchlist_path: Path) -> None:
    """Adding the same ticker twice fails the second time, no silent overwrite (1-W3-02)."""
    rc1 = main(["add", "AAPL", "--watchlist", str(empty_watchlist_path)])
    assert rc1 == 0
    rc2 = main(["add", "AAPL", "--watchlist", str(empty_watchlist_path)])
    assert rc2 != 0
    wl = load_watchlist(empty_watchlist_path)
    assert list(wl.tickers.keys()) == ["AAPL"]


def test_add_normalizes_case(empty_watchlist_path: Path) -> None:
    """Lower-case input becomes the upper-case key in the file (1-W3-03)."""
    rc = main(["add", "aapl", "--watchlist", str(empty_watchlist_path)])
    assert rc == 0
    wl = load_watchlist(empty_watchlist_path)
    assert "AAPL" in wl.tickers
    assert "aapl" not in wl.tickers


def test_add_brk_normalizes_to_hyphen(empty_watchlist_path: Path) -> None:
    """BRK.B input produces BRK-B key — CONTEXT.md correction #1 (1-W3-04)."""
    rc = main(["add", "BRK.B", "--watchlist", str(empty_watchlist_path)])
    assert rc == 0
    wl = load_watchlist(empty_watchlist_path)
    assert "BRK-B" in wl.tickers
    assert "BRK.B" not in wl.tickers
    # Hard guarantee: dot-form must not appear anywhere in the persisted file.
    text = empty_watchlist_path.read_text(encoding="utf-8")
    assert "BRK.B" not in text
    assert "BRK-B" in text


def test_add_all_flags(empty_watchlist_path: Path) -> None:
    """All TickerConfig fields settable via CLI flags (1-W3-05)."""
    rc = main([
        "add", "JPM",
        "--lens", "value",
        "--thesis", "150",
        "--support", "140",
        "--resistance", "180",
        "--pe-target", "12",
        "--ps-target", "4",
        "--pb-target", "1.5",
        "--notes", "test note",
        "--no-short-term-focus",
        "--watchlist", str(empty_watchlist_path),
    ])
    assert rc == 0
    wl = load_watchlist(empty_watchlist_path)
    cfg = wl.tickers["JPM"]
    assert cfg.long_term_lens == "value"
    assert cfg.thesis_price == 150.0
    assert cfg.short_term_focus is False
    assert cfg.notes == "test note"
    assert cfg.technical_levels is not None
    assert cfg.technical_levels.support == 140.0
    assert cfg.technical_levels.resistance == 180.0
    assert cfg.target_multiples is not None
    assert cfg.target_multiples.pe_target == 12.0
    assert cfg.target_multiples.ps_target == 4.0
    assert cfg.target_multiples.pb_target == 1.5
