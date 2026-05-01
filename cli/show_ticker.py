"""`markets show TICKER` — full per-ticker config dump.

Reuses two shared helpers (single sources of truth):
- `analysts.schemas.normalize_ticker` (Plan 02) — case/separator normalization
- `cli._errors.suggest_ticker` (Plan 05) — did-you-mean wrapper around difflib

Mirrors `cli/remove_ticker.py`'s error semantics:
- invalid ticker format → exit 2 (stderr message)
- ticker not in watchlist → exit 1 (stderr message; did-you-mean when close)
- happy path → structured key/value dump on stdout, exit 0

Output is plain text — keep stdlib-only; the rendered shape mirrors a YAML
dump but we don't actually emit YAML (no dep). Empty optional groups print
"-" so users see the full schema surface even when fields are unset.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from analysts.schemas import normalize_ticker
from cli._errors import suggest_ticker
from watchlist.loader import load_watchlist


def build_show_parser(p: argparse.ArgumentParser) -> None:
    """Register `show` subcommand flags."""
    p.add_argument("ticker", help="ticker symbol (case-insensitive; BRK.B → BRK-B)")
    p.add_argument(
        "--watchlist",
        type=Path,
        default=Path("watchlist.json"),
        help="path to watchlist.json (default: ./watchlist.json)",
    )


def show_command(args: argparse.Namespace) -> int:
    """Show a ticker's full config. Returns 0 ok / 1 not-found / 2 invalid input."""
    normalized = normalize_ticker(args.ticker)
    if normalized is None:
        print(f"error: invalid ticker format {args.ticker!r}", file=sys.stderr)
        return 2

    wl = load_watchlist(args.watchlist)
    if normalized not in wl.tickers:
        hint = suggest_ticker(normalized, list(wl.tickers.keys()))
        msg = f"error: ticker {normalized!r} not in watchlist."
        if hint:
            msg += f" did you mean {hint!r}?"
        print(msg, file=sys.stderr)
        return 1

    cfg = wl.tickers[normalized]
    print(f"TICKER: {cfg.ticker}")
    print(f"short_term_focus: {cfg.short_term_focus}")
    print(f"long_term_lens: {cfg.long_term_lens}")
    print(f"thesis_price: {cfg.thesis_price if cfg.thesis_price is not None else '-'}")

    if cfg.technical_levels is not None:
        print("technical_levels:")
        sup = cfg.technical_levels.support
        res = cfg.technical_levels.resistance
        print(f"  support: {sup if sup is not None else '-'}")
        print(f"  resistance: {res if res is not None else '-'}")
    else:
        print("technical_levels: -")

    if cfg.target_multiples is not None:
        print("target_multiples:")
        pe = cfg.target_multiples.pe_target
        ps = cfg.target_multiples.ps_target
        pb = cfg.target_multiples.pb_target
        print(f"  pe_target: {pe if pe is not None else '-'}")
        print(f"  ps_target: {ps if ps is not None else '-'}")
        print(f"  pb_target: {pb if pb is not None else '-'}")
    else:
        print("target_multiples: -")

    print(f"notes: {cfg.notes if cfg.notes else '(none)'}")
    print(f"created_at: {cfg.created_at if cfg.created_at else '-'}")
    print(f"updated_at: {cfg.updated_at if cfg.updated_at else '-'}")
    return 0
