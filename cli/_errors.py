"""Shared CLI error helpers.

Two utilities live here:

1. `format_validation_error(exc)` — Pydantic ValidationError → CLI multi-line string.
   Used by cli/main.py's exception handler so any ValidationError raised inside
   add/remove (or any future subcommand) surfaces as a friendly multi-line
   message instead of a raw Python traceback.

   Format:
       validation failed (N error[s]):
         - <dot.path.loc>: <msg> (got: <repr_input_truncated>)

   `include_url=False` suppresses Pydantic's "for further information visit ..."
   URLs — those are noise in CLI output for a single-user tool.

2. `suggest_ticker(unknown, known)` — did-you-mean wrapper around
   `difflib.get_close_matches(n=1, cutoff=0.6)`. Single source of truth for the
   typo-suggestion logic shared by `cli/remove_ticker.py` and `cli/show_ticker.py`
   (closes the deferred decision flagged in Plan 04 SUMMARY).
"""
from __future__ import annotations

import difflib

from pydantic import ValidationError


def format_validation_error(exc: ValidationError) -> str:
    """Render a ValidationError as multi-line CLI output."""
    count = exc.error_count()
    plural = "s" if count != 1 else ""
    lines = [f"validation failed ({count} error{plural}):"]
    for err in exc.errors(include_url=False):
        loc = ".".join(str(p) for p in err["loc"]) or "<root>"
        msg = err["msg"]
        inp = err.get("input")
        inp_str = ""
        # Echo the offending input value, but skip empty/None to avoid useless "got: ''".
        if inp is not None and inp != "":
            s = repr(inp)
            if len(s) > 60:
                s = s[:57] + "..."
            inp_str = f" (got: {s})"
        lines.append(f"  - {loc}: {msg}{inp_str}")
    return "\n".join(lines)


def suggest_ticker(unknown: str, known: list[str]) -> str | None:
    """Did-you-mean helper for ticker symbols.

    Wraps `difflib.get_close_matches` with project defaults (n=1, cutoff=0.6)
    so callers don't drift on the cutoff value. Used by `cli/remove_ticker.py`
    and `cli/show_ticker.py` — single source of truth.

    Returns the closest match (string) or None when no candidate clears the
    cutoff. Cutoff 0.6 is the difflib default; chosen so `AAPK` → `AAPL` lands
    but `ZZZZZ` against [AAPL, NVDA, BRK-B] does NOT.
    """
    matches = difflib.get_close_matches(unknown, known, n=1, cutoff=0.6)
    return matches[0] if matches else None
