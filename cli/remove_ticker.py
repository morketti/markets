"""`markets remove TICKER` — remove a ticker with did-you-mean suggestion.

Imports the shared `normalize_ticker` helper from `analysts.schemas` (single
source of truth — see Plan 02 SUMMARY). No inline regex duplication. The same
helper is used by `cli.show_ticker` (Plan 05).

Imports the shared `suggest_ticker` helper from `cli._errors` (single source
of truth for did-you-mean — see Plan 05 SUMMARY). The same helper is used by
`cli.show_ticker`. No inline difflib calls outside `cli/_errors.py`.

Flow:
  1. Normalize input via shared helper. None → exit 2 (invalid format).
  2. Load watchlist. If normalized not present → suggest closest match via
     shared `suggest_ticker` (cutoff=0.6) → exit 1.
  3. Confirm interactively unless --yes/-y → exit 0 silently if user aborts.
  4. Remove key, save atomically, print confirmation.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from analysts.schemas import normalize_ticker
from cli._errors import suggest_ticker
from watchlist.loader import load_watchlist, save_watchlist


def build_remove_parser(p: argparse.ArgumentParser) -> None:
    """Register `remove` subcommand flags."""
    p.add_argument("ticker", help="ticker symbol (case-insensitive; BRK.B → BRK-B)")
    p.add_argument(
        "--watchlist",
        type=Path,
        default=Path("watchlist.json"),
        help="path to watchlist.json",
    )
    p.add_argument(
        "--yes", "-y",
        action="store_true",
        help="skip the interactive confirmation prompt",
    )


def remove_command(args: argparse.Namespace) -> int:
    """Remove a ticker. Returns exit code (0 success, 1 not-found, 2 invalid input)."""
    normalized = normalize_ticker(args.ticker)
    if normalized is None:
        print(
            f"error: invalid ticker format {args.ticker!r}",
            file=sys.stderr,
        )
        return 2

    wl = load_watchlist(args.watchlist)

    if normalized not in wl.tickers:
        hint = suggest_ticker(normalized, list(wl.tickers.keys()))
        msg = f"error: ticker {normalized!r} not in watchlist."
        if hint:
            msg += f" did you mean {hint!r}?"
        print(msg, file=sys.stderr)
        return 1

    if not args.yes:
        ans = input(f"remove {normalized}? [y/N] ")
        if ans.strip().lower() not in ("y", "yes"):
            print("aborted")
            return 0

    new_tickers = {k: v for k, v in wl.tickers.items() if k != normalized}
    new_wl = wl.model_copy(update={"tickers": new_tickers})
    save_watchlist(new_wl, args.watchlist)
    print(f"removed {normalized}")
    return 0
