# Pattern adapted from cli/add_ticker.py — flag-only argparse + Pydantic validation.
"""`markets add_endorsement` — append a newsletter/service endorsement to JSONL.

All flags are required except --notes (default '') and --path (default
endorsements.jsonl at repo root). Date validated via date.fromisoformat;
ValueError on malformed input prints actionable stderr message + returns 2
(matches dispatcher contract). Pydantic ValidationError raised inside
Endorsement(...) propagates to cli/main.py:68-70 which prints + returns 2 —
atomic-on-success holds (append never reached on validation failure).

captured_at is auto-populated from datetime.now(timezone.utc) — the user does
NOT pass it via flag; --date is the call date (when the endorsement was
issued), captured_at is when the entry was added. Pitfall #2 from
09-RESEARCH.md: 90-day filter on the frontend uses `date`, NOT `captured_at`.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from analysts.endorsement_schema import Endorsement
from endorsements.log import append_endorsement


def _now_utc() -> datetime:
    """UTC-aware datetime at second precision."""
    return datetime.now(timezone.utc).replace(microsecond=0)


def build_add_endorsement_parser(p: argparse.ArgumentParser) -> None:
    """Register `add_endorsement` subcommand flags."""
    p.add_argument("--ticker", required=True, help="ticker symbol (BRK.B → BRK-B)")
    p.add_argument(
        "--source",
        required=True,
        help="newsletter/service name (e.g. 'Motley Fool')",
    )
    p.add_argument(
        "--date",
        required=True,
        dest="call_date",
        help="ISO date the call was made (YYYY-MM-DD)",
    )
    p.add_argument(
        "--price",
        type=float,
        required=True,
        dest="price_at_call",
        help="price when endorsement issued",
    )
    p.add_argument(
        "--notes",
        default="",
        help="freeform notes (max 2000 chars)",
    )
    p.add_argument(
        "--path",
        type=Path,
        default=Path("endorsements.jsonl"),
        help="path to endorsements.jsonl",
    )


def add_endorsement_command(args: argparse.Namespace) -> int:
    """Append an Endorsement. Returns exit code (0 success, 2 validation failure)."""
    try:
        call_date = date.fromisoformat(args.call_date)
    except ValueError as exc:
        print(
            f"error: invalid --date {args.call_date!r}: {exc}",
            file=sys.stderr,
        )
        return 2

    # Pydantic ValidationError propagates → cli/main.py dispatcher → exit 2.
    # Atomic-on-success: append_endorsement is NOT called when validation
    # fails (control-flow never reaches the next line).
    e = Endorsement(
        ticker=args.ticker,
        source=args.source,
        date=call_date,
        price_at_call=args.price_at_call,
        notes=args.notes,
        captured_at=_now_utc(),
    )
    append_endorsement(e, path=args.path)
    print(
        f"recorded endorsement: {e.ticker} from {e.source} "
        f"({e.date.isoformat()})"
    )
    return 0
