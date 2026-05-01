"""CLI dispatcher entry point — `markets` console script.

Subcommands register via the SUBCOMMANDS dict. Plan 05 extended this with
`list` and `show` by appending two entries; the rest of the dispatcher
remains untouched. This is the documented extension point — see PLAN.md
frontmatter key_links.

Exception strategy:
- pydantic.ValidationError → format_validation_error → stderr → exit 2
- FileNotFoundError → simple stderr message → exit 1
- Other exceptions propagate (debug-friendly during development)
"""
from __future__ import annotations

import argparse
import sys
from typing import Callable

from pydantic import ValidationError

from cli._errors import format_validation_error
from cli.add_ticker import add_command, build_add_parser
from cli.list_watchlist import build_list_parser, list_command
from cli.remove_ticker import build_remove_parser, remove_command
from cli.show_ticker import build_show_parser, show_command

# Each value is (parser_builder, command_handler). New subcommands extend
# this dict — no other dispatcher code needs to change.
SUBCOMMANDS: dict[
    str,
    tuple[
        Callable[[argparse.ArgumentParser], None],
        Callable[[argparse.Namespace], int],
    ],
] = {
    "add": (build_add_parser, add_command),
    "remove": (build_remove_parser, remove_command),
    "list": (build_list_parser, list_command),
    "show": (build_show_parser, show_command),
}


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with all registered subcommands."""
    parser = argparse.ArgumentParser(
        prog="markets",
        description="watchlist management — add/remove tickers and per-ticker config",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, (build, _handler) in SUBCOMMANDS.items():
        build(sub.add_parser(name, help=f"{name} subcommand"))
    return parser


def main(argv: list[str] | None = None) -> int:
    """Console-script entry. Returns process exit code.

    `argv=None` lets argparse use `sys.argv[1:]`; explicit-None enables
    test injection (pass a list of args directly).
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        _build, handler = SUBCOMMANDS[args.cmd]
        return handler(args)
    except ValidationError as e:
        print(format_validation_error(e), file=sys.stderr)
        return 2
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
