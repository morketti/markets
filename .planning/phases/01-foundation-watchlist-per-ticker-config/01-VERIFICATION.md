---
phase: 01-foundation-watchlist-per-ticker-config
verified: 2026-04-30T00:00:00Z
status: passed
score: 4/4 success criteria verified
vault_status: skipped
re_verification: false
---

# Phase 1: Foundation Watchlist Per-Ticker Config — Verification Report

**Phase Goal:** User can declare a watchlist with rich per-ticker configuration that drives all downstream analysis.
**Verified:** 2026-04-30
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from Phase Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | watchlist.json schema with 30+ tickers loads and validates via Pydantic v2 | VERIFIED | `test_load_30_ticker_watchlist` passes; 35-ticker fixture roundtrips cleanly; `Watchlist.model_validate_json` used in loader |
| 2 | CLI utilities `cli/add_ticker.py` and `cli/remove_ticker.py` work end-to-end against watchlist.json | VERIFIED | 5 add tests + 3 remove tests all green; integration path: `main()` → `add/remove_command()` → `save_watchlist()` → file |
| 3 | Per-ticker config supports short_term_focus, long_term_lens, thesis_price, technical_levels, target_multiples, notes | VERIFIED | All 9 fields present in `TickerConfig`; `test_add_all_flags` exercises every field via CLI; `watchlist.example.json` serializes them |
| 4 | Invalid configs are rejected with actionable Pydantic error messages | VERIFIED | `format_validation_error` wired in `main()` except-block; `test_format_validation_error` confirms multi-line "validation failed (N errors):" output with field paths and "got: ..." input echo |

**Score:** 4/4 success criteria verified

### Locked Architectural Decisions

| Decision | Status | Evidence |
|----------|--------|----------|
| Ticker normalization uses HYPHEN form (BRK-B) | VERIFIED | `normalize_ticker()` in `analysts/schemas.py:50` calls `.replace(".", "-")`, `.replace("/", "-")`, `.replace("_", "-")`; `test_ticker_normalization` asserts all separator forms → `BRK-B`; `watchlist.example.json` contains `"BRK-B"` on disk |
| Cross-field validators use `@model_validator(mode="after")` | VERIFIED | `schemas.py:74` (`TechnicalLevels.support_below_resistance`) and `schemas.py:162` (`Watchlist.keys_match_tickers`) both use `@model_validator(mode="after")`; single-field rules correctly use `@field_validator` |
| JSON serialization uses `json.dumps(..., sort_keys=True)` | VERIFIED | `loader.py:51`: `payload = json.dumps(watchlist.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"`; `test_round_trip_byte_identical` enforces this end-to-end |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `analysts/schemas.py` | TechnicalLevels, FundamentalTargets, TickerConfig, Watchlist, normalize_ticker | VERIFIED | 171 lines; all 5 exports present; `_TICKER_PATTERN`, `normalize_ticker`, all 4 models with `ConfigDict(validate_assignment=True, extra="forbid")` |
| `watchlist/loader.py` | load_watchlist, save_watchlist, DEFAULT_PATH | VERIFIED | 69 lines; atomic write via NamedTemporaryFile + os.replace; sort_keys=True; defense-in-depth re-validation |
| `cli/main.py` | argparse dispatcher, build_parser(), main(argv), SUBCOMMANDS dict | VERIFIED | 75 lines; SUBCOMMANDS has all 4 entries: add, remove, list, show |
| `cli/_errors.py` | format_validation_error(exc), suggest_ticker(unknown, known) | VERIFIED | 61 lines; both functions present and exported |
| `cli/add_ticker.py` | build_add_parser(p), add_command(args) | VERIFIED | 102 lines; all 9 TickerConfig fields settable via CLI flags |
| `cli/remove_ticker.py` | build_remove_parser(p), remove_command(args) | VERIFIED | 75 lines; imports `normalize_ticker` from `analysts.schemas`, `suggest_ticker` from `cli._errors` |
| `cli/list_watchlist.py` | build_list_parser(p), list_command(args) | VERIFIED | 45 lines; alphabetical sort; notes truncation at 40 chars |
| `cli/show_ticker.py` | build_show_parser(p), show_command(args) | VERIFIED | 83 lines; structured dump; imports shared helpers |
| `tests/conftest.py` | empty_watchlist_path, seeded_watchlist_path, large_watchlist_path | VERIFIED | 66 lines; lazy imports inside fixture bodies; `BRK-B` in seeded fixture; 35 tickers in large fixture |
| `tests/test_schemas.py` | 8 schema unit tests | VERIFIED | 191 lines; all 8 test functions present and passing |
| `tests/test_loader.py` | 5+ loader tests | VERIFIED | 147 lines; 7 tests including bonus cleanup-on-failure test |
| `tests/test_cli_add.py` | 5 CLI add tests | VERIFIED | 100 lines; all 5 tests present |
| `tests/test_cli_remove.py` | 3 CLI remove tests | VERIFIED | 53 lines; all 3 tests present |
| `tests/test_cli_errors.py` | 1 error formatter test | VERIFIED | 41 lines |
| `tests/test_cli_readonly.py` | 5+ readonly tests | VERIFIED | 199 lines; 8 tests (more than the 5 required) |
| `watchlist.example.json` | 5 tickers spanning all 4 lenses | VERIFIED | AAPL (value), NVDA (growth), BRK-B (value), GME (contrarian), V (mixed); `"BRK-B"` on disk, not `"BRK.B"` |
| `README.md` | Quick-start with copy-and-edit pattern, ≥40 lines | VERIFIED | 88 lines; contains `cp watchlist.example.json watchlist.json`, all 4 CLI commands documented |
| `pyproject.toml` | uv project with console-script, pytest/coverage/ruff config | VERIFIED | Contains `markets = "cli.main:main"`, hatchling build-backend, all 3 package paths |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `pyproject.toml [project.scripts]` | `cli/main.py:main` | `markets = "cli.main:main"` | VERIFIED | Pattern present in pyproject.toml:11 |
| `analysts/schemas.py:_TICKER_PATTERN` | `normalize_ticker()` | `_TICKER_PATTERN.match(norm)` | VERIFIED | `schemas.py:52`: `return norm if _TICKER_PATTERN.match(norm) else None` |
| `normalize_ticker()` (module-level) | `TickerConfig._normalize_ticker_field` | `return normalize_ticker(v)` | VERIFIED | `schemas.py:133`: delegates to module-level helper |
| `TechnicalLevels.support_below_resistance` | `@model_validator(mode="after")` | cross-field rule | VERIFIED | `schemas.py:74` |
| `Watchlist.keys_match_tickers` | `@model_validator(mode="after")` | cross-field rule | VERIFIED | `schemas.py:162` |
| `watchlist/loader.py:save_watchlist` | `json.dumps(..., sort_keys=True)` | deterministic serialization | VERIFIED | `loader.py:51` |
| `watchlist/loader.py:save_watchlist` | `tempfile.NamedTemporaryFile + os.replace` | atomic write | VERIFIED | `loader.py:54-68` |
| `cli/main.py:SUBCOMMANDS` | add, remove, list, show handlers | dict dispatch | VERIFIED | All 4 entries present in SUBCOMMANDS dict |
| `cli/main.py:main` | `cli._errors.format_validation_error` | `except ValidationError` block | VERIFIED | `main.py:66-68` |
| `cli/remove_ticker.py:remove_command` | `analysts.schemas.normalize_ticker` | shared import, no duplication | VERIFIED | `remove_ticker.py:24`: `from analysts.schemas import normalize_ticker` |
| `cli/show_ticker.py:show_command` | `analysts.schemas.normalize_ticker` | shared import | VERIFIED | `show_ticker.py:22`: `from analysts.schemas import normalize_ticker` |
| `cli/remove_ticker.py + show_ticker.py` | `cli._errors.suggest_ticker` | shared did-you-mean | VERIFIED | Both files import `from cli._errors import suggest_ticker` |
| `watchlist.example.json` | `watchlist/loader.py:load_watchlist` | `test_example_file_loads_cleanly` | VERIFIED | Test passes; file is a valid watchlist |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| WATCH-01 | 01-01, 01-03, 01-05 | User can maintain a watchlist of 30+ tickers | SATISFIED | `test_load_30_ticker_watchlist` (35-ticker fixture); `test_list_30_plus_tickers` (35 rows printed) |
| WATCH-02 | 01-04 | User can add a ticker via CLI utility | SATISFIED | `test_add_happy_path`, `test_add_duplicate_rejected`, `test_add_normalizes_case`, `test_add_brk_normalizes_to_hyphen`, `test_add_all_flags` — all 5 green |
| WATCH-03 | 01-04, 01-05 | User can remove a ticker via CLI utility | SATISFIED | `test_remove_happy_path` green; `test_remove_suggests_close_match` (did-you-mean AAPL from AAPK); `test_show_unknown_ticker` (ergonomics extended to show) |
| WATCH-04 | 01-02, 01-04 | Per-ticker config supports 9 fields | SATISFIED | All 9 fields in `TickerConfig`; `test_add_all_flags` exercises all via CLI |
| WATCH-05 | 01-02, 01-04 | Per-ticker config validated via Pydantic; invalid rejected with clear error | SATISFIED | 8 schema validation tests; `test_format_validation_error` confirms actionable multi-line error output |

**All 5 requirements SATISFIED. No orphaned requirements.**

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `cli/add_ticker.py` | 91-94 | Duplicate-ticker error printed to stdout (not stderr) | ℹ️ Info | Inconsistent with other error paths that use `file=sys.stderr`; does not affect tests since `test_add_duplicate_rejected` only checks exit code |

No blockers or warnings found. The stdout vs stderr inconsistency in `add_ticker.py` for the duplicate error is the only notable item — all other error paths (`remove_ticker.py`, `show_ticker.py`, `main.py`) correctly route errors to stderr.

### Test Suite Results

- **Total tests:** 33
- **Result:** 33 passed, 0 failed
- **Coverage:** 94% total (analysts: 99%, watchlist: 100%, cli: varies 77-100%)
- **Coverage detail:** The 77% lines in `cli/main.py` and `cli/remove_ticker.py` are the exception-handler branches (ValidationError, FileNotFoundError in main; invalid-format and interactive-prompt paths in remove). These are branch-coverage gaps, not implementation gaps. The phase plan set 85% as the CLI target; overall 94% exceeds the 90% gate set by Plan 05.

### Human Verification Required

None. All functional behaviors are automated-test-verified. The only candidate for human verification would be the interactive confirmation prompt (`remove TICKER? [y/N]`) in `remove_ticker.py:66`, which the test suite intentionally bypasses via `--yes`. This is correct behavior for a CLI test.

### Gaps Summary

No gaps. All 4 success criteria verified, all 5 requirements satisfied, all key architectural decisions confirmed in code, all artifacts substantive and wired.

---

## Code Quality Review (Stage 2)

**Diff range:** `fb3fad7077c3c871187522e03d03d016503197d4~1..428fb4b8f0c414a30f7869fa6bbb2870c1db5c02`
**Files reviewed:** 31 (production: 11, tests: 7, planning docs: 6, config: 3, other: 4)
**Production LOC added:** ~681 (schemas 171, loader 69, cli files 441)

### Strengths

- **Single source of truth enforced without drift.** `normalize_ticker` lives only in `analysts/schemas.py` and is imported (not reimplemented) by `remove_ticker.py` and `show_ticker.py`. `suggest_ticker` lives only in `cli/_errors.py` and is imported by both consumer files. The diff has zero instances of inline regex or inline `difflib.get_close_matches` outside those canonical files.
- **Architectural decision comments are load-bearing.** `loader.py` docstring explicitly names Pydantic issue #7424 as the reason for `json.dumps(sort_keys=True)`. `schemas.py` explains the `analysts/` vs `watchlist/` placement to prevent future circular dependency. These are not decoration — they document decisions a future phase author would otherwise relitigate.
- **TDD discipline is verifiable in git history.** The commit sequence for each plan is: `test(01-0N): add failing ...` → `feat(01-0N): implement ...` → `docs(01-0N): complete ...`. The red-green-commit pattern is faithfully executed, not retroactively described.
- **Defense-in-depth without noise.** `save_watchlist` re-validates the model before writing (`Watchlist.model_validate(watchlist.model_dump())`). `ConfigDict(validate_assignment=True, extra="forbid")` on all four Pydantic models catches mutation bugs and typos in user-edited JSON. Both patterns are low-friction (no performance cost at human-scale) and high-value for a file that users hand-edit.
- **Test quality is high.** Tests are integration-style where it matters (CLI tests call `main()` with real arg lists and assert on the written file) and unit-style where it matters (schema tests call constructors directly). No mock-heavy patterns that test the wrong thing. The byte-identical round-trip test (`test_round_trip_byte_identical`) is a particularly clean determinism probe.
- **Atomic write correctly handles Windows file-locking.** `tmp.name` captured inside `with` block; `os.replace` called outside. The `test_save_cleanup_on_replace_failure` test with `monkeypatch` locks in the cleanup contract — this is a real production concern on the dev OS (Windows 11) that was anticipated and tested.

### Critical

None.

### Important

- **`cli/add_ticker.py:91-94` — duplicate-ticker error prints to stdout, not stderr.** Every other error path in the CLI routes to `file=sys.stderr` (remove, show, main exception handlers). The duplicate-add error breaks this convention by printing to stdout. This is visible to scripts that pipe `uv run markets add` output: `2>/dev/null` suppresses real errors but would show the duplicate message as if it were normal output. Suggested fix: add `file=sys.stderr` to the `print(...)` call at line 91.

- **`cli/main.py:66-71` — ValidationError and FileNotFoundError handlers are not covered by the test suite.** The `format_validation_error` output is tested by `test_format_validation_error` (calling the function directly), but the `main()`-level except-block that wires it is not exercised via an end-to-end path through `main()`. If a future refactor breaks the wiring (`format_validation_error` removed from the import, or the `except ValidationError` block deleted), no test would catch it. Suggested addition: one test in `test_cli_errors.py` that calls `main(["add", "AAPL", "--thesis", "-1", "--watchlist", str(path)])` and asserts stderr contains "validation failed".

### Minor

- **`normalize_ticker` return type declared as `Optional[str]` (from `typing`) but the plan specified `str | None`.** Both are identical at runtime in Python 3.10+. In Python 3.12 (the project target), the `str | None` union syntax is the idiomatic form per PEP 604. The other functions in the codebase (e.g., `suggest_ticker`) use `str | None`. Inconsistency is cosmetic but worth aligning in a future pass.

- **`cli/remove_ticker.py:65-69` — interactive confirmation prompt is untested.** The `--yes` flag bypasses it in all tests, meaning the `input()` call and the "aborted" / "y/yes" logic at lines 65-69 have no test coverage. Not a blocker (interactive prompts are hard to test and the `--yes` path is the operationally important one), but the 77% branch coverage on this file is primarily from these lines.

- **`cli/_errors.py:42-43` — the `> 60 char` truncation branch for long error inputs is not exercised.** Coverage shows branch `40->45` (the `inp is not None and inp != ""` check) and line 43 (`s = s[:57] + "..."`) are uncovered. A test constructing a ValidationError with a long input value (e.g., a 100-char ticker string) would cover it.

- **`watchlist.example.json` uses `null` for fields like `technical_levels` and `target_multiples` rather than omitting them.** The schema allows both (`Optional[TechnicalLevels] = None`) and the loader round-trips correctly. However, the file is used as a user-facing reference document — showing `"technical_levels": null` for all tickers may confuse users who expect to see the structure. This is a UX consideration, not a correctness issue.

### Assessment

The phase is ready to merge. The implementation is architecturally sound, all success criteria are met, the test suite is green at 94% coverage, and the locked decisions (hyphen normalization, model_validator(after), sort_keys) are correctly applied and tested. The one Important finding (stdout vs stderr for the duplicate-add error) is a minor convention inconsistency that does not break any tests or real-world behavior, but should be addressed before Phase 2 adds more CLI commands that would inherit the pattern. The second Important finding (ValidationError handler not covered end-to-end in main()) is a genuine coverage gap but not a correctness risk given the direct unit test for `format_validation_error`.

---

_Verified: 2026-04-30T00:00:00Z_
_Verifier: Claude (gmd-verifier)_
