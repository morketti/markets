"""CLI dispatcher entry point for the `markets` console script.

This is a placeholder. The full argparse subcommand dispatcher lands in
Plan 04 (CLI Core). See ../analysts/schemas.py and ../watchlist/loader.py
for the underlying data layer (Plans 02 and 03).
"""
from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    """Console-script entry point. Returns a process exit code.

    Replaced in Plan 04 with the full argparse dispatcher (add/remove/list/show).
    """
    print("markets: CLI not yet implemented (Phase 1 Plan 04)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
