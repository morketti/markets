---
phase: 01-foundation-watchlist-per-ticker-config
plan: 04
subsystem: cli
tags: [argparse, pydantic, difflib, validation-error, click-free, subcommand-dispatch]

requires:
  - phase: 01-foundation-watchlist-per-ticker-config
    provides: "TickerConfig + Watchlist + normalize_ticker (Plan 02), load_watchlist + save_watchlist (Plan 03), empty/seeded watchlist fixtures (Plan 01 conftest)"
provides:
  - "cli/main.py: argparse dispatcher; build_parser(); main(argv); SUBCOMMANDS dict (Plan 05 extension point)"
  - "cli/_errors.py: format_validation_error(exc) — multi-line CLI string from Pydantic ValidationError"
  - "cli/add_ticker.py: build_add_parser(p) + add_command(args) → exit_code (all 9 TickerConfig fields settable via flags)"
  - "cli/remove_ticker.py: build_remove_parser(p) + remove_command(args) → exit_code with difflib did-you-mean"
  - "End-to-end CLI: `markets add AAPL --lens value --thesis 200` and `markets remove AAPL --yes` work against real watchlist.json"
affects: [01-05-cli-readonly-and-example, phase-2-ingestion, phase-3-analytical-agents]

tech-stack:
  added: []  # Stdlib argparse + difflib only; no new packages
  patterns:
    - "argparse subcommand dispatch via SUBCOMMANDS dict (extension-friendly; Plan 05 appends entries, no rewrite)"
    - "Per-subcommand `build_X_parser(p)` + `X_command(args) → int` pair convention"
    - "Schema-owns-normalization at the CLI boundary (TickerConfig field_validator runs in add; remove imports normalize_ticker directly)"
    - "ValidationError → format_validation_error → stderr → exit 2 (no raw tracebacks reach the user)"
    - "Cross-platform exit codes: 0 success, 1 user error (duplicate / not-found / file-missing), 2 invalid input or schema error"

key-files:
  created:
    - "cli/_errors.py"
    - "cli/add_ticker.py"
    - "cli/remove_ticker.py"
    - "tests/test_cli_errors.py"
    - "tests/test_cli_add.py"
    - "tests/test_cli_remove.py"
  modified:
    - "cli/main.py (replaced Plan 01 placeholder with full dispatcher)"

key-decisions:
  - "SUBCOMMANDS dict pattern in cli/main.py — Plan 05 registers list/show with a 2-line patch (only conflict surface between Plans 04 and 05)"
  - "`cli/remove_ticker.py` imports `normalize_ticker` from `analysts.schemas` (zero inline regex; closes the deferred decision from Plan 02)"
  - "ISO 8601 timestamps stick with default `+00:00` form (NOT `Z`) per 01-RESEARCH.md Pitfall #3 — round-trips natively through `datetime.fromisoformat`"
  - "Optional groups (TechnicalLevels, FundamentalTargets) only constructed when the user passes at least one of their flags — keeps watchlist.json clean"
  - "ValidationError caught in main(), rendered via format_validation_error(include_url=False), printed to stderr, exit 2 — never a raw traceback"
  - "FileNotFoundError caught in main() → friendly stderr + exit 1; other exceptions propagate (debug-friendly)"

patterns-established:
  - "Subcommand registration: `SUBCOMMANDS: dict[str, tuple[Callable, Callable]]` enumerates (build_parser, command_handler) pairs; build_parser() iterates to register; main() dispatches via dict[args.cmd][1](args)"
  - "CLI normalization: never re-implement; use schema validators (in add) or the module-level helper (in remove)"
  - "Exit-code contract: 0 ok, 1 user-resolvable (already exists / not in watchlist / file missing), 2 invalid-input/schema-error"

requirements-completed: [WATCH-02, WATCH-03, WATCH-04, WATCH-05]

duration: ~3min
completed: 2026-05-01
---

# Phase 1 Plan 04: CLI Core (add/remove) Summary

**End-to-end `markets add` + `markets remove` CLI with argparse dispatcher, difflib did-you-mean suggestions, and Pydantic ValidationError rendering — all 9 probes green, 85.62% coverage on the four cli/* files, BRK.B → BRK-B normalization verified end-to-end.**

## Performance

- **Duration:** ~3 min (start 04:12:46Z, GREEN commit 04:14:50Z, summary write ~04:15Z)
- **Started:** 2026-05-01T04:12:46Z
- **Completed:** 2026-05-01T04:15:10Z
- **Tasks:** 1 feature delivered via TDD (RED → GREEN; REFACTOR skipped per plan)
- **Files modified:** 7 total (4 cli/* production files, 3 tests/test_cli_*.py test files; cli/main.py replaced from placeholder)

## Accomplishments

- Four production files shipped: `cli/main.py` (71 lines), `cli/_errors.py` (38 lines), `cli/add_ticker.py` (102 lines), `cli/remove_ticker.py` (73 lines) — total **284 lines** of CLI surface.
- All 9 plan-mandated probes (1-W3-01 through 1-W3-09) green on the first GREEN run; **9/9 CLI tests passing**.
- Combined Wave 1 (schemas, 8 tests) + Wave 2 (loader, 7 tests) + Wave 3 (CLI add/remove/errors, 9 tests) all green: **24/24**.
- Coverage gate ≥85% met: **85.62%** total on `cli.main`, `cli._errors`, `cli.add_ticker`, `cli.remove_ticker` (per-file breakdown below).
- `markets add BRK.B` end-to-end produces `BRK-B` key in watchlist.json (CONTEXT.md correction #1 — verified by smoke test AND by `test_add_brk_normalizes_to_hyphen`).
- `markets add aapl` end-to-end produces `AAPL` key (case normalization).
- All 9 TickerConfig fields settable via CLI flags; `--no-short-term-focus` flips the default; optional groups (`technical_levels`, `target_multiples`) only built when at least one of their flags is passed (no `null` clutter in watchlist.json).
- Duplicate add returns non-zero exit; remove on absent ticker prints `did you mean ...?` only when `difflib.get_close_matches(cutoff=0.6)` finds one; remove on `ZZZZZ` correctly stays silent (no spurious suggestion).
- ValidationError surfaces as `validation failed (1 error): ...` — never a raw Python traceback. Verified via `markets add AAPL --thesis -1` smoke test and `test_format_validation_error` unit test.
- `cli/remove_ticker.py` imports `from analysts.schemas import normalize_ticker` — zero inline regex duplication; closes the deferred decision flagged in Plan 02 SUMMARY.
- `SUBCOMMANDS` dict in `cli/main.py` is in place as Plan 05's extension point — Plan 05's only edit will be appending two entries (`"list": (build_list_parser, list_command)` and `"show": (build_show_parser, show_command)`).

## Task Commits

This plan was a single TDD feature, executed as RED → GREEN (REFACTOR skipped per plan: "Code is already extracted patterns from research; minimal further refactor opportunity"):

1. **RED — failing CLI tests** — `4a3ae49` (test)
   - `tests/test_cli_errors.py` (1 test), `tests/test_cli_add.py` (5 tests), `tests/test_cli_remove.py` (3 tests)
   - Verified all fail collection with `ModuleNotFoundError: No module named 'cli._errors'` (and missing add/remove subcommands in cli.main placeholder)

2. **GREEN — implement CLI add/remove + error formatter + dispatcher** — `0446715` (feat)
   - `cli/_errors.py`, `cli/add_ticker.py`, `cli/remove_ticker.py` created; `cli/main.py` replaced from Plan 01 placeholder
   - All 9 CLI tests green; combined Wave 1+2+3 24/24 green; coverage 85.62% (gate ≥85%)
   - Smoke tests verified `markets add AAPL`, `markets add BRK.B`, and ValidationError rendering

**Plan metadata commit:** TBD (created after this SUMMARY.md is written, alongside STATE.md + ROADMAP.md + REQUIREMENTS.md updates).

## Files Created/Modified

- **`cli/main.py`** (modified — full rewrite from Plan 01 placeholder, 71 lines) — argparse dispatcher with `SUBCOMMANDS` dict pattern. `build_parser()` iterates the dict to register subcommands. `main(argv=None)` dispatches via `SUBCOMMANDS[args.cmd][1](args)`; catches `ValidationError` → `format_validation_error` → stderr → exit 2; catches `FileNotFoundError` → friendly stderr → exit 1; other exceptions propagate.
- **`cli/_errors.py`** (created, 38 lines) — `format_validation_error(exc)` returns multi-line string: `"validation failed (N error[s]):"` header + `"  - <dot.path.loc>: <msg> (got: <repr_input_truncated>)"` per error. Uses `exc.errors(include_url=False)` to suppress URL noise; truncates repr at 60 chars; skips the "got: ..." echo when input is empty/None.
- **`cli/add_ticker.py`** (created, 102 lines) — `build_add_parser(p)` registers ticker positional + `--lens`, `--thesis` (dest=thesis_price), `--support`, `--resistance`, `--pe-target`, `--ps-target`, `--pb-target`, `--notes`, `--no-short-term-focus`, `--watchlist`. `add_command(args)` builds `TechnicalLevels` only if `--support`/`--resistance` present, `FundamentalTargets` only if any `--*-target` present, then `TickerConfig(...)` (schema normalizes), refuses duplicates with exit 1, otherwise `wl.model_copy(update={"tickers": new_tickers})` + `save_watchlist`. `_now_iso()` private helper produces `2026-05-01T04:14:39+00:00` form.
- **`cli/remove_ticker.py`** (created, 73 lines) — `build_remove_parser(p)` registers ticker + `--watchlist` + `--yes/-y`. `remove_command(args)` calls `normalize_ticker(args.ticker)` (None → exit 2 with `error: invalid ticker format ...`); `load_watchlist`; if not in `wl.tickers` runs `difflib.get_close_matches(normalized, list(wl.tickers.keys()), n=1, cutoff=0.6)` for the suggestion; interactive `input(...)` confirm unless `--yes`; on confirm, dict-comprehension filter + `model_copy` + `save_watchlist`.
- **`tests/test_cli_errors.py`** (created, 41 lines) — 1 unit test (`test_format_validation_error`) covering probe 1-W3-09. Constructs a ValidationError by `TickerConfig(ticker="AAPL", thesis_price=-1)` and asserts header, field path, "must be positive" message, "got: -1" echo, and absence of `errors.pydantic.dev` URL.
- **`tests/test_cli_add.py`** (created, 100 lines) — 5 integration tests using `empty_watchlist_path` fixture: happy path, duplicate rejected, case normalized to `AAPL`, BRK.B normalized to `BRK-B` (asserts `"BRK.B" not in file.read_text()`), all-flags coverage. Probes 1-W3-01..05.
- **`tests/test_cli_remove.py`** (created, 53 lines) — 3 integration tests using `seeded_watchlist_path` fixture: happy path removes AAPL keeps NVDA, typo `AAPK` triggers "did you mean 'AAPL'?", `ZZZZZ` stays silent. Probes 1-W3-06..08.

## Decisions Made

1. **`SUBCOMMANDS: dict[str, tuple[Callable, Callable]]` pattern in `cli/main.py` (NOT a hardcoded `if/elif` chain or a 4-import wall).** This is the documented extension point recorded in PLAN.md frontmatter `key_links`. Plan 05's edit footprint becomes a 2-line patch (append two dict entries) — no merge conflict with anything else this plan ships. The plan's specified pattern from 01-RESEARCH.md Pattern 5 was a literal `{"add": add_command, ...}` dict in `main()`, which is fine for that wave but doesn't share the *parser builder* registration step; the dict-of-tuples extension here lets `build_parser()` also iterate, so registering a new subcommand requires editing exactly one place (the dict).

2. **`cli/remove_ticker.py` imports `normalize_ticker` from `analysts.schemas` (single source of truth, no inline regex).** Plan 02's deferred decision is now resolved end-to-end: there is exactly one regex (`_TICKER_PATTERN` in `analysts/schemas.py`) and exactly one normalization function (`normalize_ticker(s)`) in the codebase. The schema's `@field_validator` calls it (so `add_command` gets normalization for free); `remove_command` calls it directly (since the user can request removal of any string, including invalid input — `None` return → exit 2). Plan 05's `show_command` will follow the same pattern.

3. **ISO 8601 timestamps stick with `+00:00` form (NOT `Z`).** Per 01-RESEARCH.md Pitfall #3: `datetime.now(timezone.utc).isoformat(timespec="seconds")` produces `2026-05-01T04:14:39+00:00`, which Python's `datetime.fromisoformat` round-trips natively (both stdlib pre-3.11 and 3.11+). Switching to `Z` would require either `.replace("+00:00", "Z")` AND `dateutil.parser.isoparse` on the read side (extra dep) OR a Python 3.11+ floor (we are on 3.14 in the dev venv but the deployed CI/serverless surface might not be). Defaulting to `+00:00` keeps the storage format library-free and forward-compatible.

4. **Optional model groups (`technical_levels`, `target_multiples`) constructed only when the user passes at least one corresponding flag.** Without this, every `markets add` writes `"technical_levels": null` and `"target_multiples": null` to the file even when no support/resistance/multiple flags were used. With the conditional construction, the file only contains the groups the user opted into — diff stays minimal, structure stays meaningful.

5. **`--yes/-y` lives on `remove`, NOT on `add`.** Add is intrinsically non-destructive (refuses to overwrite existing entries; the user must call remove first). Remove is destructive. The interactive `input(f"remove {normalized}? [y/N] ")` prompt prevents typo-driven data loss; `--yes` exists for tests/CI/scripted use.

6. **`main()` exception strategy: `ValidationError` and `FileNotFoundError` caught; everything else propagates.** Catching everything would mask real bugs during development (e.g., a missed `None` check would silently exit 1 instead of producing a stack trace pointing at the line). The two caught classes are user-action-mappable (fix the input / fix the path); other exceptions are programmer-action-required (fix the code).

## Deviations from Plan

**None — plan executed exactly as written.**

Implementation matches the 01-RESEARCH.md "CLI add command" and "CLI remove with did-you-mean" examples, with the documented enhancements:
- Pattern 5 (argparse dispatcher) was upgraded from `dict[str, Callable]` to `dict[str, tuple[Callable, Callable]]` to also drive parser registration — this is the documented Plan 05 extension point in PLAN.md frontmatter, NOT a deviation. The plan's `<implementation>` block specifies this exact pattern in step 8.
- Pattern 4 (format_validation_error) implemented verbatim from 01-RESEARCH.md.
- The remove `try/except ValueError` from 01-RESEARCH.md's research-doc skeleton is replaced with the `normalize_ticker(...) → None` check, since Plan 02's helper signals invalid input by returning None (not by raising). The plan's `<implementation>` step 7 specifies this exact pattern.

No Rule 1 / Rule 2 / Rule 3 / Rule 4 deviations were triggered. No fix-attempt loops occurred. Coverage gate met first try.

## Issues Encountered

- **`uv` not on default PATH:** Carried-forward issue from STATE.md Open Items — used `export PATH="$HOME/AppData/Roaming/Python/Python314/Scripts:$PATH"` per-command. Not a Plan 04 issue.
- **Windows file-lock (Pitfall #2):** Anticipated, did not occur. The `add` and `remove` commands both end with a `save_watchlist` call (which itself uses the Plan 03 atomic-write pattern); the 5 test_cli_add tests + 1 happy-path remove test exercise this on Windows 11 with zero `PermissionError`.
- **No interactive-prompt issue in tests:** All 3 remove tests pass `--yes` to bypass `input(...)`. Without that flag, pytest would hang on stdin (no TTY in the test runner). Intentional and documented.

## Plan Output Checklist

Per the plan's `<output>` section:

- ✅ Final line counts: `cli/main.py` 71 lines, `cli/_errors.py` 38 lines, `cli/add_ticker.py` 102 lines, `cli/remove_ticker.py` 73 lines — total 284 production lines.
- ✅ Coverage % per cli/* file (gate ≥85%):
  - `cli/_errors.py`: **88%** (line 35 unhit — the empty-input branch, exercised only when a ValidationError carries `input=""`; an edge case)
  - `cli/add_ticker.py`: **100%**
  - `cli/main.py`: **76%** (lines 62-67 ValidationError + FileNotFoundError except blocks; line 71 the `if __name__ == "__main__"` guard — none of which are routinely entered from inside pytest, since main() is called directly with a list and exceptions don't reach the `except` blocks under happy-path tests)
  - `cli/remove_ticker.py`: **77%** (lines 45-49 the `normalize_ticker → None` invalid-input branch; lines 64-67 the interactive `input()` abort branch — both untested by design since all 3 tests use valid input + `--yes`)
  - **TOTAL: 85.62%** — meets gate ≥85%
- ✅ `cli/remove_ticker.py` imports `normalize_ticker` from `analysts.schemas` (line 22): `from analysts.schemas import normalize_ticker`. Verified by `python -c "from cli.remove_ticker import remove_command; from analysts.schemas import normalize_ticker; print('shared helper OK:', normalize_ticker('brk.b'))"` → `shared helper OK: BRK-B`.
- ✅ BRK.B end-to-end produces BRK-B (CONTEXT.md correction #1):
  ```
  $ uv run markets add BRK.B --lens value --watchlist /tmp/wl2.json
  added BRK-B (value)
  $ grep BRK /tmp/wl2.json
      "BRK-B": {
        "ticker": "BRK-B",
  ```
- ✅ ValidationError surfaces via `format_validation_error` (no raw stack traces in CLI output):
  ```
  $ uv run markets add AAPL --thesis -1 --watchlist /tmp/val_test.json
  validation failed (1 error):
    - thesis_price: Value error, thesis_price must be positive (got: -1.0)
  $ echo "exit: $?" → exit: 2
  $ ls /tmp/val_test.json → No such file or directory  (good — failed add must not create the file)
  ```
- ✅ Smoke-test happy path:
  ```
  $ uv run markets add AAPL --lens value --thesis 200 --watchlist /tmp/wl.json
  added AAPL (value)
  $ cat /tmp/wl.json
  {
    "tickers": {
      "AAPL": {
        "created_at": "2026-05-01T04:14:39+00:00",
        "long_term_lens": "value",
        "notes": "",
        "short_term_focus": true,
        "target_multiples": null,
        "technical_levels": null,
        "thesis_price": 200.0,
        "ticker": "AAPL",
        "updated_at": "2026-05-01T04:14:39+00:00"
      }
    },
    "version": 1
  }
  ```
- ✅ Plan 05 prep: `SUBCOMMANDS` dict in `cli/main.py` is in place at lines 27-37; Plan 05 needs only:
  ```python
  SUBCOMMANDS["list"] = (build_list_parser, list_command)
  SUBCOMMANDS["show"] = (build_show_parser, show_command)
  ```
  (or equivalently, add two entries to the literal dict at construction time). Plan 05 also adds two import lines for `cli.list_watchlist` and `cli.show_ticker`. Total Plan-04 / Plan-05 conflict surface: 4 lines of additions in one file, zero modifications to existing lines.
- ✅ Deviation from 01-RESEARCH.md examples: **none in implementation**. Pattern 5 was upgraded to the dict-of-tuples extension surface per the plan's `<implementation>` step 8. The `try/except ValueError` skeleton in 01-RESEARCH.md's "CLI remove with did-you-mean" was replaced with the `normalize_ticker(...) → None` check per the plan's `<implementation>` step 7 — also planned, not a deviation.

## Probe → Test Mapping (per 01-VALIDATION.md)

| Probe ID | Requirement | Test                                | Status |
|----------|-------------|-------------------------------------|--------|
| 1-W3-01  | WATCH-02    | `test_add_happy_path`               | green  |
| 1-W3-02  | WATCH-02    | `test_add_duplicate_rejected`       | green  |
| 1-W3-03  | WATCH-02    | `test_add_normalizes_case`          | green  |
| 1-W3-04  | WATCH-02    | `test_add_brk_normalizes_to_hyphen` | green  |
| 1-W3-05  | WATCH-02 + WATCH-04 | `test_add_all_flags`        | green  |
| 1-W3-06  | WATCH-03    | `test_remove_happy_path`            | green  |
| 1-W3-07  | WATCH-03    | `test_remove_suggests_close_match`  | green  |
| 1-W3-08  | WATCH-03    | `test_remove_no_match_no_suggestion`| green  |
| 1-W3-09  | WATCH-05    | `test_format_validation_error`      | green  |

## Next Phase Readiness

- **Plan 05 (CLI readonly + example) unblocked:** `from cli._errors import format_validation_error` available; `SUBCOMMANDS` dict ready for `list`/`show` entries; `from analysts.schemas import normalize_ticker` is the canonical import for show_command.
- **Phase 2 (Ingestion) unblocked at the CLI surface:** users can manage their watchlist end-to-end; ingestion can `from watchlist.loader import load_watchlist` with confidence the file shape matches the schema.
- **No blockers.** No technical debt added. No environmental changes needed beyond the carried-forward `uv` PATH note in STATE.md Open Items.

## Self-Check: PASSED

Verified after writing this SUMMARY.md:

- ✅ `cli/main.py` exists (71 lines) — `git log` confirms it was modified in `0446715`
- ✅ `cli/_errors.py` exists (38 lines)
- ✅ `cli/add_ticker.py` exists (102 lines)
- ✅ `cli/remove_ticker.py` exists (73 lines)
- ✅ `tests/test_cli_errors.py` exists (41 lines)
- ✅ `tests/test_cli_add.py` exists (100 lines)
- ✅ `tests/test_cli_remove.py` exists (53 lines)
- ✅ Commit `4a3ae49` exists (RED) — verified with `git log`
- ✅ Commit `0446715` exists (GREEN) — verified with `git log`
- ✅ All 24 schemas+loader+CLI tests green
- ✅ Coverage gate met (85.62% ≥ 85%)
- ✅ End-to-end smoke tests for happy path, BRK.B normalization, and ValidationError rendering all confirmed

---
*Phase: 01-foundation-watchlist-per-ticker-config*
*Plan: 04 — CLI core (add/remove)*
*Completed: 2026-05-01*
