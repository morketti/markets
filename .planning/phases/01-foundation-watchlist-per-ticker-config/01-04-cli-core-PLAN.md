---
phase: 01-foundation-watchlist-per-ticker-config
plan: 04
type: tdd
wave: 4
depends_on: [01, 02, 03]
files_modified:
  - cli/main.py
  - cli/_errors.py
  - cli/add_ticker.py
  - cli/remove_ticker.py
  - tests/test_cli_add.py
  - tests/test_cli_remove.py
  - tests/test_cli_errors.py
autonomous: true
requirements: [WATCH-02, WATCH-03, WATCH-04, WATCH-05]
must_haves:
  truths:
    - "`markets add AAPL --lens value --thesis 200` writes a valid watchlist.json with AAPL present"
    - "Adding a duplicate ticker (`markets add AAPL` after AAPL exists) is rejected with non-zero exit and clear error"
    - "Lower-case input (`markets add aapl`) normalizes to AAPL key in the file"
    - "Class-share input (`markets add BRK.B`) normalizes to BRK-B (hyphen) per yfinance compat"
    - "All TickerConfig fields settable via CLI flags (--lens, --thesis, --support, --resistance, --pe-target, --ps-target, --pb-target, --notes, --no-short-term-focus)"
    - "`markets remove AAPL` removes the ticker from the file"
    - "`markets remove ABT` (typo for ABC) suggests 'did you mean ABC?' via difflib.get_close_matches with cutoff 0.6"
    - "`markets remove ZZZZZ` (no close match) errors cleanly with no spurious suggestion"
    - "Pydantic ValidationError is rendered as multi-line CLI output via format_validation_error — never raw stack trace"
  artifacts:
    - path: "cli/main.py"
      provides: "argparse dispatcher; build_parser(); main(argv); SUBCOMMANDS dict (extension point for Plan 05)"
      exports: ["main", "build_parser", "SUBCOMMANDS"]
      replaces: "Plan 01 placeholder"
    - path: "cli/_errors.py"
      provides: "format_validation_error(exc) → multi-line CLI string"
      exports: ["format_validation_error"]
    - path: "cli/add_ticker.py"
      provides: "build_add_parser(p); add_command(args) → exit_code"
      exports: ["build_add_parser", "add_command"]
    - path: "cli/remove_ticker.py"
      provides: "build_remove_parser(p); remove_command(args) → exit_code"
      exports: ["build_remove_parser", "remove_command"]
    - path: "tests/test_cli_add.py"
      provides: "5 integration tests covering WATCH-02 + WATCH-04 happy path, duplicate, normalization, all-flags"
      contains: "test_add_happy_path, test_add_duplicate_rejected, test_add_normalizes_case, test_add_brk_normalizes_to_hyphen, test_add_all_flags"
    - path: "tests/test_cli_remove.py"
      provides: "3 integration tests covering WATCH-03 happy path + suggestion + no-match"
      contains: "test_remove_happy_path, test_remove_suggests_close_match, test_remove_no_match_no_suggestion"
    - path: "tests/test_cli_errors.py"
      provides: "1 unit test covering format_validation_error formatting"
      contains: "test_format_validation_error"
  key_links:
    - from: "cli/main.py:main"
      to: "cli/add_ticker.py:add_command, cli/remove_ticker.py:remove_command"
      via: "dict dispatch on args.cmd via SUBCOMMANDS"
      pattern: "args.cmd"
    - from: "cli/main.py:SUBCOMMANDS"
      to: "cli/list_watchlist.py, cli/show_ticker.py (Plan 05)"
      via: "dict extension point — Plan 05 appends 'list' and 'show' entries to this dict; designed as the only conflict surface between Plans 04 and 05"
      pattern: "# Plan 05 will append"
    - from: "cli/main.py:main"
      to: "cli/_errors.py:format_validation_error"
      via: "except ValidationError block — print formatted, return exit code 2"
      pattern: "except ValidationError"
    - from: "cli/remove_ticker.py:remove_command"
      to: "analysts.schemas.normalize_ticker (module-level helper from Plan 02)"
      via: "import-and-call: normalized = normalize_ticker(args.ticker); shared logic, no duplication"
      pattern: "from analysts.schemas import normalize_ticker"
    - from: "cli/remove_ticker.py:remove_command"
      to: "difflib.get_close_matches"
      via: "import difflib; get_close_matches(unknown, known, n=1, cutoff=0.6)"
      pattern: "difflib.get_close_matches"
    - from: "cli/add_ticker.py:add_command, cli/remove_ticker.py:remove_command"
      to: "watchlist.loader.load_watchlist + save_watchlist"
      via: "import-and-call pattern"
      pattern: "from watchlist.loader import"
---

<objective>
Ship the four-subcommand CLI core: `markets add`, `markets remove`, plus the dispatcher (`cli/main.py`) and the shared error formatter (`cli/_errors.py`). After this plan, the user can run `uv run markets add AAPL --lens value --thesis 200` end-to-end and the data persists. The `list` and `show` read-only commands ship in Plan 05 (parallel — no shared file conflicts).

Purpose: ROADMAP.md Phase 1 success criterion #2 ("CLI utilities `cli/add_ticker.py` and `cli/remove_ticker.py` work end-to-end") and #4 ("Invalid configs are rejected with actionable Pydantic error messages"). This plan delivers the user-facing surface of Phase 1.

Output: 4 production files, 3 test files, 9 integration+unit tests covering 9 of the 21 phase probes (1-W3-01 through 1-W3-09 except 03/04 readonly). All tests green; coverage on the four cli/* files ≥ 85% (CLI integration-test coverage is harder than schema unit coverage; lower target reflects that).
</objective>

<execution_context>
@C:/Users/Mohan/.claude/workflows/execute-plan.md
@C:/Users/Mohan/.claude/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/01-foundation-watchlist-per-ticker-config/01-CONTEXT.md
@.planning/phases/01-foundation-watchlist-per-ticker-config/01-RESEARCH.md
@.planning/phases/01-foundation-watchlist-per-ticker-config/01-VALIDATION.md
@.planning/phases/01-foundation-watchlist-per-ticker-config/01-01-scaffold-SUMMARY.md
@.planning/phases/01-foundation-watchlist-per-ticker-config/01-02-schemas-SUMMARY.md
@.planning/phases/01-foundation-watchlist-per-ticker-config/01-03-loader-SUMMARY.md
@analysts/schemas.py
@watchlist/loader.py

<interfaces>
<!-- This plan replaces Plan 01's placeholder cli/main.py with the full dispatcher. -->
<!-- Plan 05 will register additional `list` and `show` subcommands by following the same pattern. -->

```python
# cli/main.py — public surface
def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with add/remove subcommands.
    
    Plan 05 may register additional subcommands (list, show) by importing
    from cli.list_watchlist and cli.show_ticker — those subcommand builders
    follow the same `build_<name>_parser(p)` pattern as `build_add_parser`.
    """

def main(argv: list[str] | None = None) -> int:
    """Console-script entry. Dispatches to the chosen subcommand handler.
    Catches ValidationError → format_validation_error → return 2.
    Catches FileNotFoundError → simple stderr message → return 1.
    """

# cli/_errors.py — shared formatter (used by main.py and any subcommand that
# needs to surface a ValidationError). Plan 05 may also use this.
def format_validation_error(exc: ValidationError) -> str: ...

# cli/add_ticker.py
def build_add_parser(p: argparse.ArgumentParser) -> None: ...
def add_command(args: argparse.Namespace) -> int: ...  # returns exit code

# cli/remove_ticker.py
def build_remove_parser(p: argparse.ArgumentParser) -> None: ...
def remove_command(args: argparse.Namespace) -> int: ...
```

Plan 05 will import `format_validation_error` from `cli._errors` and add `build_list_parser`, `list_command`, `build_show_parser`, `show_command` to `cli/main.py`'s dispatcher dict — but not in this plan (Plan 05 is parallel; it modifies `cli/main.py` to register its subcommands too). To avoid a merge conflict, this plan ships a `cli/main.py` that uses a **registration list pattern** that Plan 05 can extend without rewriting:

```python
# In cli/main.py:
SUBCOMMANDS: dict[str, tuple[Callable, Callable]] = {
    "add": (build_add_parser, add_command),
    "remove": (build_remove_parser, remove_command),
    # Plan 05 will append: "list": (build_list_parser, list_command), "show": (build_show_parser, show_command)
}
```

Plan 05 will edit this dict to add two entries — a 2-line change on a single file. Acceptable conflict surface. This dict is the documented extension point — see frontmatter `key_links`.

**Shared normalization helper from Plan 02:** `cli/remove_ticker.py` imports `from analysts.schemas import normalize_ticker` (module-level helper resolved during prior revision). Single source of truth — no inline regex duplication. Same module is used by Plan 05's `cli/show_ticker.py`.
</interfaces>

<corrections_callout>
This plan touches CONTEXT.md correction #1 (hyphen normalization) directly:

- **`markets add BRK.B` MUST produce a watchlist.json with the key `BRK-B` (hyphen).** The test `test_add_brk_normalizes_to_hyphen` enforces this end-to-end. Normalization happens automatically inside the schema (Plan 02) — `add_command` builds a `TickerConfig(ticker=args.ticker)`, the `@field_validator(mode="before")` kicks in (which delegates to module-level `normalize_ticker`) and produces hyphenated form. The CLI does NOT re-implement normalization in `add_command`.
- **`markets remove BRK.B` MUST normalize the input to `BRK-B` BEFORE looking up in `wl.tickers` and BEFORE running `difflib.get_close_matches`.** The remove command imports `normalize_ticker` from `analysts.schemas` (module-level helper from Plan 02) and calls it directly. Returns `None` on invalid input → CLI prints clean error and returns exit 2. Test `test_remove_happy_path` includes a case with mixed-case input.

Corrections #2 (`@model_validator(mode="after")`) and #3 (`json.dumps(... sort_keys=True)`) are inherited from Plans 02 and 03 — the CLI builds models and calls save_watchlist; the schemas and loader handle correctness. No additional CLI work needed for those.

**Edge case from Pitfall #5 (`validate_assignment`):** if a future change has the CLI directly mutate fields on a loaded `TickerConfig` (e.g., `cfg.thesis_price = -1`), `validate_assignment=True` from the schema (Plan 02) will catch it. We don't rely on this — the CLI rebuilds models via `model_copy(update=...)` per 01-RESEARCH.md examples.

**Resolved deferred decision (prior revision):** `normalize_ticker` is now a module-level helper in `analysts/schemas.py` (Plan 02 owns the extraction). Plan 04's `remove_command` imports and uses it directly. Plan 05's `show_command` does the same. No duplication; no inline regex anywhere in the CLI layer.
</corrections_callout>
</context>

<feature>
  <name>cli/main.py dispatcher + cli/_errors.py + cli/add_ticker.py + cli/remove_ticker.py with full integration tests</name>
  <files>cli/main.py, cli/_errors.py, cli/add_ticker.py, cli/remove_ticker.py, tests/test_cli_add.py, tests/test_cli_remove.py, tests/test_cli_errors.py</files>
  <behavior>
**`cli/_errors.py:format_validation_error(exc)` behavior:**
- Returns a multi-line string starting with `"validation failed (N error[s]):"`
- One indented bullet per error: `"  - {dot.path.loc}: {msg} (got: {repr_input_truncated})"`
- Uses `exc.errors(include_url=False)` to suppress noise URLs
- Truncates input repr at 60 chars with `...` suffix when longer
- Empty/None inputs are not echoed (no useless "got: ''")

**`cli/main.py:main(argv)` behavior:**
- Builds the argparse parser with subcommands `add`, `remove` (Plan 05 will add `list`, `show` to the SUBCOMMANDS dict)
- `argv` defaults to `None` (argparse uses `sys.argv[1:]`); explicit-None enables test injection
- Dispatches via `SUBCOMMANDS[args.cmd][1](args)` returning exit code
- Catches `pydantic.ValidationError` → prints `format_validation_error(e)` to stderr → returns 2
- Catches `FileNotFoundError` → prints `f"error: {e}"` to stderr → returns 1
- Other exceptions propagate (debug-friendly)

**`cli/add_ticker.py` behavior:**
- `build_add_parser` registers flags from 01-RESEARCH.md § Code Examples ("CLI add command"): `ticker` (positional), `--lens`, `--no-short-term-focus`, `--thesis` (dest=thesis_price), `--support`, `--resistance`, `--pe-target`, `--ps-target`, `--pb-target`, `--notes`, `--watchlist` (default Path("watchlist.json"))
- `add_command(args)` flow:
  1. `wl = load_watchlist(args.watchlist)`
  2. Build `TechnicalLevels(...)` only if `--support` or `--resistance` present
  3. Build `FundamentalTargets(...)` only if any `--*-target` present
  4. Build `TickerConfig(ticker=args.ticker, ...)` — schema normalizes the ticker
  5. Refuse if `cfg.ticker in wl.tickers` (exit 1, message "ticker {X!r} already exists. use 'remove' first if you want to replace.")
  6. Build `new_tickers = dict(wl.tickers); new_tickers[cfg.ticker] = cfg`
  7. `new_wl = wl.model_copy(update={"tickers": new_tickers})`
  8. `save_watchlist(new_wl, args.watchlist)`
  9. Print confirmation; return 0
- Sets `created_at` and `updated_at` to `datetime.now(timezone.utc).isoformat(timespec="seconds")` per Open Question #1 recommendation (default `+00:00` form)

**`cli/remove_ticker.py` behavior:**
- `build_remove_parser` registers `ticker` (positional), `--watchlist`, `--yes`/`-y`
- `remove_command(args)` flow:
  1. `wl = load_watchlist(args.watchlist)`
  2. Normalize input via shared helper: `normalized = normalize_ticker(args.ticker)` (imported from `analysts.schemas`). If `normalized is None`: print `f"error: invalid ticker format {args.ticker!r}"` to stderr, return 2.
  3. If `normalized not in wl.tickers`:
     - `suggestion = difflib.get_close_matches(normalized, list(wl.tickers.keys()), n=1, cutoff=0.6)`
     - print `"error: ticker {normalized!r} not in watchlist."` plus `" did you mean {suggestion[0]!r}?"` if suggestion
     - return 1
  4. If not `--yes`: `input(f"remove {normalized}? [y/N] ")`; abort if not y/yes
  5. Build `new_tickers = {k: v for k, v in wl.tickers.items() if k != normalized}`
  6. `save_watchlist(...)`, print confirmation, return 0

**Test cases (RED → GREEN):**

`tests/test_cli_errors.py:`
- `test_format_validation_error` — construct a ValidationError by trying `TickerConfig(ticker="AAPL", thesis_price=-1)`, capture the exception, call format_validation_error, assert: starts with "validation failed", contains "thesis_price", contains "must be positive" (or whatever Pydantic outputs), contains "got: -1.0" or "got: -1" (probe 1-W3-09)

`tests/test_cli_add.py:` (use the `empty_watchlist_path` fixture from conftest)
- `test_add_happy_path` — call `main(["add", "AAPL", "--lens", "value", "--thesis", "200", "--watchlist", str(empty_watchlist_path)])`; assert exit code 0; load file via `load_watchlist`, assert "AAPL" in tickers, assert tickers["AAPL"].thesis_price == 200, lens == "value", created_at and updated_at not None (probe 1-W3-01)
- `test_add_duplicate_rejected` — first add succeeds; second add of same ticker returns non-zero exit; file still has only one entry (probe 1-W3-02)
- `test_add_normalizes_case` — call `main(["add", "aapl", "--watchlist", str(empty_watchlist_path)])`; load file; assert "AAPL" in tickers (key, NOT "aapl") (probe 1-W3-03)
- `test_add_brk_normalizes_to_hyphen` — call `main(["add", "BRK.B", "--watchlist", str(empty_watchlist_path)])`; load file; assert "BRK-B" in tickers, assert "BRK.B" NOT in tickers; file content (read_text) does not contain "BRK.B" anywhere (probe 1-W3-04)
- `test_add_all_flags` — call `main(["add", "JPM", "--lens", "value", "--thesis", "150", "--support", "140", "--resistance", "180", "--pe-target", "12", "--ps-target", "4", "--pb-target", "1.5", "--notes", "test note", "--no-short-term-focus", "--watchlist", str(empty_watchlist_path)])`; load and assert all fields set as expected; assert short_term_focus is False (probe 1-W3-05)

`tests/test_cli_remove.py:` (use `seeded_watchlist_path` for happy paths; `empty_watchlist_path` for "no match")
- `test_remove_happy_path` — call `main(["remove", "AAPL", "--yes", "--watchlist", str(seeded_watchlist_path)])`; assert exit 0; load and assert "AAPL" NOT in tickers; assert "NVDA" still in tickers (probe 1-W3-06)
- `test_remove_suggests_close_match` — call `main(["remove", "AAPK", "--yes", "--watchlist", str(seeded_watchlist_path)])` (typo for AAPL); capture stderr (or stdout depending on impl); assert exit 1 AND output contains "did you mean" AND "AAPL" (probe 1-W3-07)
- `test_remove_no_match_no_suggestion` — call `main(["remove", "ZZZZZ", "--yes", "--watchlist", str(seeded_watchlist_path)])`; assert exit 1 AND output does NOT contain "did you mean" (no close match below cutoff 0.6) (probe 1-W3-08)

For tests that need to capture stdout/stderr, use pytest's `capsys` fixture.

For the `--yes` flag: ALL test invocations of `remove` use `--yes` to bypass the interactive `input()` prompt — important since CI/test runners can't answer prompts.
  </behavior>
  <implementation>
**TDD cycle (one combined RED/GREEN per command for context efficiency; commit per file group):**

**RED Phase — commit `test(01-04): add failing CLI tests`:**
1. Write `tests/test_cli_errors.py` with `test_format_validation_error`. Imports:
   ```python
   import pytest
   from pydantic import ValidationError
   from analysts.schemas import TickerConfig
   from cli._errors import format_validation_error
   ```
2. Write `tests/test_cli_add.py` with all 5 tests. Imports include `from cli.main import main`.
3. Write `tests/test_cli_remove.py` with all 3 tests. Same imports.
4. Run `uv run pytest tests/test_cli_*.py -x` — confirm ALL FAIL with ImportError on `cli._errors`, `cli.main`'s SUBCOMMANDS dict (since Plan 01 placeholder doesn't have it), or argparse-related errors.

**GREEN Phase — commit `feat(01-04): implement CLI add/remove + error formatter + dispatcher`:**

5. Write `cli/_errors.py`. Content from 01-RESEARCH.md § Pattern 4:
   ```python
   """Pydantic ValidationError → CLI multi-line string formatter.
   
   Used by cli/main.py's exception handler; can be reused by individual
   subcommand handlers if they want to render a ValidationError inline.
   """
   from __future__ import annotations
   from pydantic import ValidationError


   def format_validation_error(exc: ValidationError) -> str:
       count = exc.error_count()
       plural = "s" if count != 1 else ""
       lines = [f"validation failed ({count} error{plural}):"]
       for err in exc.errors(include_url=False):
           loc = ".".join(str(p) for p in err["loc"]) or "<root>"
           msg = err["msg"]
           inp = err.get("input")
           inp_str = ""
           if inp is not None and inp != "":
               s = repr(inp)
               if len(s) > 60:
                   s = s[:57] + "..."
               inp_str = f" (got: {s})"
           lines.append(f"  - {loc}: {msg}{inp_str}")
       return "\n".join(lines)
   ```

6. Write `cli/add_ticker.py` from 01-RESEARCH.md § Code Examples ("CLI add command"). Add module docstring; ensure `_now_iso()` helper is module-private.

7. Write `cli/remove_ticker.py` using the **shared `normalize_ticker` helper from Plan 02**. No inline regex; no duplication. Skeleton:
   ```python
   """`markets remove TICKER` — remove a ticker from the watchlist with did-you-mean suggestion."""
   from __future__ import annotations
   import argparse
   import difflib
   import sys
   from pathlib import Path

   from analysts.schemas import normalize_ticker
   from watchlist.loader import load_watchlist, save_watchlist


   def build_remove_parser(p: argparse.ArgumentParser) -> None:
       p.add_argument("ticker")
       p.add_argument("--watchlist", type=Path, default=Path("watchlist.json"))
       p.add_argument("--yes", "-y", action="store_true")


   def remove_command(args: argparse.Namespace) -> int:
       normalized = normalize_ticker(args.ticker)
       if normalized is None:
           print(f"error: invalid ticker format {args.ticker!r}", file=sys.stderr)
           return 2
       wl = load_watchlist(args.watchlist)
       if normalized not in wl.tickers:
           matches = difflib.get_close_matches(normalized, list(wl.tickers.keys()), n=1, cutoff=0.6)
           msg = f"error: ticker {normalized!r} not in watchlist."
           if matches:
               msg += f" did you mean {matches[0]!r}?"
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
   ```
   No fallback inline regex needed — Plan 02 owns and exports the helper.

8. Write `cli/main.py` from 01-RESEARCH.md § Pattern 5, modified with the SUBCOMMANDS dict pattern for Plan 05 extensibility:
   ```python
   """CLI dispatcher entry point — `markets` console script.

   Subcommands register via the SUBCOMMANDS dict. Plan 05 extends this with
   list and show by adding entries; the rest of the dispatcher stays unchanged.
   """
   from __future__ import annotations
   import argparse
   import sys
   from typing import Callable
   from pydantic import ValidationError

   from cli._errors import format_validation_error
   from cli.add_ticker import add_command, build_add_parser
   from cli.remove_ticker import remove_command, build_remove_parser

   # Plan 05 will append two more entries (list, show) to this dict.
   SUBCOMMANDS: dict[str, tuple[Callable[[argparse.ArgumentParser], None], Callable[[argparse.Namespace], int]]] = {
       "add": (build_add_parser, add_command),
       "remove": (build_remove_parser, remove_command),
   }


   def build_parser() -> argparse.ArgumentParser:
       parser = argparse.ArgumentParser(prog="markets", description="watchlist management")
       sub = parser.add_subparsers(dest="cmd", required=True)
       for name, (build, _handler) in SUBCOMMANDS.items():
           build(sub.add_parser(name, help=f"{name} subcommand"))
       return parser


   def main(argv: list[str] | None = None) -> int:
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
   ```

9. Run `uv run pytest tests/test_cli_*.py -x` — confirm 9 tests pass.
10. Run full Wave 1+2+3 (partial) suite: `uv run pytest tests/test_schemas.py tests/test_loader.py tests/test_cli_*.py -x` — confirm all green.
11. Coverage: `uv run pytest tests/test_cli_*.py --cov=cli.main --cov=cli._errors --cov=cli.add_ticker --cov=cli.remove_ticker --cov-fail-under=85`.

**REFACTOR (skip):** Code is already extracted patterns from research; minimal further refactor opportunity.

**Per-task verification map (probes from 01-VALIDATION.md):**
- 1-W3-01 → `test_add_happy_path`
- 1-W3-02 → `test_add_duplicate_rejected`
- 1-W3-03 → `test_add_normalizes_case`
- 1-W3-04 → `test_add_brk_normalizes_to_hyphen`
- 1-W3-05 → `test_add_all_flags`
- 1-W3-06 → `test_remove_happy_path`
- 1-W3-07 → `test_remove_suggests_close_match`
- 1-W3-08 → `test_remove_no_match_no_suggestion`
- 1-W3-09 → `test_format_validation_error`
  </implementation>
</feature>

<verification>
After GREEN:
1. `uv run pytest tests/test_cli_add.py tests/test_cli_remove.py tests/test_cli_errors.py -x` — all 9 tests pass
2. Combined Wave 1+2+3 (excluding readonly): `uv run pytest tests/test_schemas.py tests/test_loader.py tests/test_cli_add.py tests/test_cli_remove.py tests/test_cli_errors.py -x` — all green
3. Coverage on `cli.main`, `cli._errors`, `cli.add_ticker`, `cli.remove_ticker` ≥ 85%
4. Manual smoke test (in tmp dir to avoid polluting repo root):
   ```
   cd /tmp && uv run --project /c/Users/Mohan/markets markets add AAPL --lens value --thesis 200 --watchlist /tmp/wl.json
   ```
   exits 0; `/tmp/wl.json` exists with valid content
5. `uv run markets add BRK.B --lens value --watchlist /tmp/wl2.json` exits 0; `/tmp/wl2.json` contains `"BRK-B"`, NOT `"BRK.B"`
6. **End-to-end ValidationError surfacing (NOT raw traceback):** `uv run markets add AAPL --thesis -1 --watchlist /tmp/val_test.json 2>&1 | grep "validation failed"` — exits 0 (grep finds the marker line); proves `format_validation_error` is wired into `main()`'s except-block path, NOT a raw Python traceback bubbling up. Cleanup: `rm -f /tmp/val_test.json` (file should not have been created since the add failed).
7. **Shared helper integration:** `uv run python -c "from cli.remove_ticker import remove_command; from analysts.schemas import normalize_ticker; print('shared helper OK')"` — confirms `cli/remove_ticker.py` imports from `analysts.schemas` (no duplication).
</verification>

<success_criteria>
- [ ] All 9 CLI tests pass (`uv run pytest tests/test_cli_*.py -x`)
- [ ] All Wave 1+2+3-add/remove tests pass combined
- [ ] Coverage on `cli/main.py`, `cli/_errors.py`, `cli/add_ticker.py`, `cli/remove_ticker.py` ≥ 85%
- [ ] `markets add BRK.B` end-to-end produces `BRK-B` key in watchlist.json (CONTEXT.md correction #1)
- [ ] `markets add aapl` end-to-end produces `AAPL` key (case normalization)
- [ ] All 9 TickerConfig fields settable via CLI flags (test_add_all_flags green)
- [ ] Duplicate add rejected with non-zero exit (no silent overwrite)
- [ ] Remove suggests close match via `difflib.get_close_matches(cutoff=0.6)` (test_remove_suggests_close_match green)
- [ ] Remove with no match prints clean error (no spurious "did you mean")
- [ ] `cli/remove_ticker.py` imports `normalize_ticker` from `analysts.schemas` — no inline regex duplication (resolved deferred decision)
- [ ] ValidationError surfaces as multi-line `format_validation_error` output (NOT raw stack trace) — verified end-to-end via Check 6 in `<verification>`
- [ ] SUBCOMMANDS dict pattern in `cli/main.py` is extensible — Plan 05 can register `list` and `show` with a 2-line patch
- [ ] WATCH-02 covered: 5 probes (1-W3-01..05)
- [ ] WATCH-03 covered: 3 probes (1-W3-06..08)
- [ ] WATCH-04 covered: 1 probe (1-W3-05 all-flags)
- [ ] WATCH-05 covered: 1 probe (1-W3-09 format_validation_error)
</success_criteria>

<output>
After completion, create `.planning/phases/01-foundation-watchlist-per-ticker-config/01-04-cli-core-SUMMARY.md` documenting:
- Final line counts for `cli/main.py`, `cli/_errors.py`, `cli/add_ticker.py`, `cli/remove_ticker.py`
- Coverage % on each cli/* file
- Confirmation that `cli/remove_ticker.py` imports `normalize_ticker` from `analysts.schemas` (no duplication; resolved deferred decision from prior revision)
- Confirmation that `BRK.B` end-to-end produces `BRK-B` (CONTEXT.md correction #1)
- Confirmation that ValidationError in any subcommand surfaces via `format_validation_error` (no raw stack traces in CLI output) — paste output from `markets add AAPL --thesis -1` smoke test (`<verification>` Check 6)
- Smoke-test output of `uv run markets add AAPL --lens value --thesis 200 --watchlist /tmp/wl.json` (paste actual output)
- Plan 05 prep: confirm `SUBCOMMANDS` dict in `cli/main.py` is in place and Plan 05 just needs to append `"list"` and `"show"` entries
- Any deviation from 01-RESEARCH.md examples and why
</output>
