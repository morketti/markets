"""`markets refresh` — orchestrator CLI shim.

Thin wrapper around `ingestion.refresh.run_refresh`:
    1. Normalize the optional positional ticker (un-normalizable → exit 1).
    2. Call run_refresh with watchlist_path + snapshots_root + only_ticker.
    3. Print a one-line summary (total / succeeded / failed + snapshot dir).
    4. Echo any run-level manifest.errors to stderr.
    5. Always return exit code 0 — failure detail lives in manifest.json
       (per-ticker outcomes carry their own success flag).

Mirrors `cli/list_watchlist.py`'s shape: tiny build_*_parser, tiny
*_command, exit codes consistent with the rest of the CLI surface (0
success / data-only error like missing tickers, 1 input error, 2 reserved
for ValidationError via the dispatcher).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from analysts.schemas import normalize_ticker
from ingestion.refresh import run_refresh


def build_refresh_parser(parser: argparse.ArgumentParser) -> None:
    """Register `refresh` subcommand args."""
    parser.add_argument(
        "ticker",
        nargs="?",
        default=None,
        help="optional single ticker; default: refresh whole watchlist",
    )
    parser.add_argument(
        "--watchlist",
        type=Path,
        default=Path("watchlist.json"),
        help="path to watchlist.json (default: ./watchlist.json)",
    )
    parser.add_argument(
        "--snapshots-root",
        type=Path,
        default=Path("snapshots"),
        help="root dir for snapshot output (default: ./snapshots)",
    )


def refresh_command(args: argparse.Namespace) -> int:
    """Run the orchestrator and print a summary. Always returns 0."""
    only_ticker: str | None
    if args.ticker is not None:
        normalized = normalize_ticker(args.ticker)
        if normalized is None:
            print(f"error: invalid ticker {args.ticker!r}", file=sys.stderr)
            return 1
        only_ticker = normalized
    else:
        only_ticker = None

    manifest = run_refresh(
        watchlist_path=args.watchlist,
        snapshots_root=args.snapshots_root,
        only_ticker=only_ticker,
    )

    n_total = len(manifest.tickers)
    n_success = sum(1 for t in manifest.tickers if t.success)
    n_fail = n_total - n_success
    suffix = "s" if n_total != 1 else ""
    print(
        f"refreshed {n_total} ticker{suffix}: {n_success} succeeded, {n_fail} failed"
    )
    print(f"snapshot: {args.snapshots_root}/{manifest.snapshot_date.isoformat()}/")

    if manifest.errors:
        print("run errors:", file=sys.stderr)
        for err in manifest.errors:
            print(f"  - {err}", file=sys.stderr)

    return 0
