"""Pydantic ValidationError → CLI multi-line string formatter.

Used by cli/main.py's exception handler so any ValidationError raised inside
add/remove (or any future subcommand) surfaces as a friendly multi-line
message instead of a raw Python traceback. May be reused by individual
subcommand handlers if they want to render a ValidationError inline before
returning a non-zero exit code.

Format:
    validation failed (N error[s]):
      - <dot.path.loc>: <msg> (got: <repr_input_truncated>)

`include_url=False` suppresses Pydantic's "for further information visit ..."
URLs — those are noise in CLI output for a single-user tool.
"""
from __future__ import annotations

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
