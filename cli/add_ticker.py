"""`markets add TICKER` — add a ticker to the watchlist file.

Ticker normalization happens inside the schema (TickerConfig.@field_validator).
The CLI does NOT re-implement normalization; passing `BRK.B` here results in
a TickerConfig whose `.ticker` is `"BRK-B"`, and that's the dict key used to
persist it. See 01-CONTEXT.md correction #1.

All flags map 1:1 onto TickerConfig / TechnicalLevels / FundamentalTargets
fields. Optional groups (technical_levels, target_multiples) are only built
when at least one of their flags is provided — this keeps watchlist.json
clean (no `"technical_levels": null` clutter unless the user opts in).
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from analysts.schemas import FundamentalTargets, TechnicalLevels, TickerConfig
from watchlist.loader import load_watchlist, save_watchlist


def _now_iso() -> str:
    """ISO 8601 UTC timestamp with seconds precision (e.g. 2026-04-30T12:34:56+00:00).

    Per 01-RESEARCH.md Pitfall #3: stick with default `+00:00` form (NOT `Z`)
    so Python's `datetime.fromisoformat` round-trips natively without dateutil.
    """
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_add_parser(p: argparse.ArgumentParser) -> None:
    """Register `add` subcommand flags. See 01-RESEARCH.md § Code Examples (CLI add)."""
    p.add_argument("ticker", help="ticker symbol (case-insensitive; BRK.B → BRK-B)")
    p.add_argument(
        "--lens",
        choices=["value", "growth", "contrarian", "mixed"],
        default="mixed",
        help="long-term investment lens",
    )
    p.add_argument(
        "--no-short-term-focus",
        action="store_true",
        help="disable short-term tactical analysis for this ticker",
    )
    p.add_argument("--thesis", type=float, dest="thesis_price", help="long-term price target")
    p.add_argument("--support", type=float, help="technical support level")
    p.add_argument("--resistance", type=float, help="technical resistance level")
    p.add_argument("--pe-target", type=float, help="P/E target multiple")
    p.add_argument("--ps-target", type=float, help="P/S target multiple")
    p.add_argument("--pb-target", type=float, help="P/B target multiple")
    p.add_argument("--notes", default="", help="freeform notes (max 1000 chars)")
    p.add_argument(
        "--watchlist",
        type=Path,
        default=Path("watchlist.json"),
        help="path to watchlist.json",
    )


def add_command(args: argparse.Namespace) -> int:
    """Add a ticker. Returns exit code (0 success, 1 duplicate)."""
    wl = load_watchlist(args.watchlist)

    tech: TechnicalLevels | None = None
    if args.support is not None or args.resistance is not None:
        tech = TechnicalLevels(support=args.support, resistance=args.resistance)

    fund: FundamentalTargets | None = None
    if any(getattr(args, f) is not None for f in ("pe_target", "ps_target", "pb_target")):
        fund = FundamentalTargets(
            pe_target=args.pe_target,
            ps_target=args.ps_target,
            pb_target=args.pb_target,
        )

    now = _now_iso()
    cfg = TickerConfig(
        ticker=args.ticker,  # schema normalizes (BRK.B → BRK-B, aapl → AAPL)
        short_term_focus=not args.no_short_term_focus,
        long_term_lens=args.lens,
        thesis_price=args.thesis_price,
        technical_levels=tech,
        target_multiples=fund,
        notes=args.notes,
        created_at=now,
        updated_at=now,
    )

    if cfg.ticker in wl.tickers:
        print(
            f"error: ticker {cfg.ticker!r} already exists. "
            f"use 'remove' first if you want to replace.",
            file=sys.stderr,
        )
        return 1

    new_tickers = dict(wl.tickers)
    new_tickers[cfg.ticker] = cfg
    new_wl = wl.model_copy(update={"tickers": new_tickers})
    save_watchlist(new_wl, args.watchlist)
    print(f"added {cfg.ticker} ({cfg.long_term_lens})")
    return 0
