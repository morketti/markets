"""`markets list` — read-only deterministic dump of the watchlist.

Output columns: TICKER, LENS, THESIS, NOTES (truncated). Tickers are sorted
alphabetically by key so `git diff` over `markets list > scratch.txt` is
trivially reviewable. Empty watchlist prints a copy-the-add-command hint and
exits 0 (not an error — first-run UX per Plan 03 loader contract).

Pure stdlib output (no colors / tables / wrapping libraries). Argparse-style
plain text is the precedent already set by `markets --help`.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from watchlist.loader import load_watchlist

_NOTES_MAX = 40  # truncate notes column at this many chars (then add "...")


def build_list_parser(p: argparse.ArgumentParser) -> None:
    """Register `list` subcommand flags. Only --watchlist."""
    p.add_argument(
        "--watchlist",
        type=Path,
        default=Path("watchlist.json"),
        help="path to watchlist.json (default: ./watchlist.json)",
    )


def list_command(args: argparse.Namespace) -> int:
    """Print watchlist rows alphabetically. Returns 0 even when empty."""
    wl = load_watchlist(args.watchlist)
    if not wl.tickers:
        print("(empty watchlist — try: markets add AAPL --lens value --thesis 200)")
        return 0
    print(f"{'TICKER':<8}{'LENS':<13}{'THESIS':<10}NOTES")
    for ticker in sorted(wl.tickers.keys()):
        cfg = wl.tickers[ticker]
        thesis_str = f"{cfg.thesis_price:.2f}" if cfg.thesis_price is not None else "-"
        notes = cfg.notes if cfg.notes else "-"
        if len(notes) > _NOTES_MAX:
            notes = notes[: _NOTES_MAX - 3] + "..."
        print(f"{ticker:<8}{cfg.long_term_lens:<13}{thesis_str:<10}{notes}")
    return 0
