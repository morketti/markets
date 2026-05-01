---
phase: 01-foundation-watchlist-per-ticker-config
plan: 03
subsystem: persistence
tags: [pydantic, json, atomic-write, tempfile, file-io, determinism]

requires:
  - phase: 01-foundation-watchlist-per-ticker-config
    provides: "TickerConfig + Watchlist Pydantic v2 schemas (Plan 02), tmp_path fixtures (Plan 01 conftest)"
provides:
  - "watchlist/loader.py: load_watchlist(path) + save_watchlist(wl, path) + DEFAULT_PATH"
  - "Atomic-save contract: tmp file in same dir, close handle, os.replace; cleanup on failure"
  - "Deterministic serialization: json.dumps(model_dump(mode='json'), indent=2, sort_keys=True) + trailing newline"
  - "Defense-in-depth re-validation before persistence"
  - "Round-trip byte-identical guarantee (test-locked)"
affects: [01-04-cli-core, 01-05-cli-readonly-and-example, phase-2-ingestion]

tech-stack:
  added: []
  patterns:
    - "Atomic write via NamedTemporaryFile + os.replace (Pitfall #2 Windows-safe)"
    - "Stdlib-only file I/O (no third-party serializers; json + tempfile + os.replace)"
    - "Path-explicit module API (no cwd-relative reads inside loader; Pitfall #7)"
    - "Defense-in-depth schema re-validation at the persistence boundary"

key-files:
  created:
    - "watchlist/loader.py"
    - "tests/test_loader.py"
  modified: []

key-decisions:
  - "Stdlib json.dumps(... sort_keys=True) for serialization, NOT model_dump_json (CONTEXT.md correction #3 / Pydantic v2 issue #7424)"
  - "tempfile.NamedTemporaryFile context exits BEFORE os.replace (Pitfall #2: Windows file-lock release)"
  - "load_watchlist on a missing path returns Watchlist() rather than raising (CLI add-first-ticker UX)"
  - "save_watchlist re-validates the model defensively (catches caller-side mutation that bypassed validate_assignment)"
  - "Added test_save_cleanup_on_replace_failure to lock the failure-cleanup contract (also closes coverage gap on lines 67-69)"

patterns-established:
  - "Atomic write pattern: with NamedTemporaryFile(...delete=False, dir=parent...) as tmp: tmp.write(payload); tmp_path=Path(tmp.name); then os.replace(tmp_path, path) OUTSIDE the with-block; OSError -> tmp.unlink(missing_ok=True) + raise"
  - "Deterministic JSON: json.dumps(model.model_dump(mode='json'), indent=2, sort_keys=True) + '\\n' for git-friendly stable output"
  - "Single-source-of-truth import: from analysts.schemas import Watchlist (no schema duplication in persistence layer)"

requirements-completed: [WATCH-01, WATCH-02, WATCH-05]

duration: 2min
completed: 2026-05-01
---

# Phase 1 Plan 03: Loader Summary

**Stdlib atomic-write loader: load_watchlist + save_watchlist with sort_keys=True deterministic JSON, NamedTemporaryFile + os.replace atomicity, and defense-in-depth re-validation — 100% line+branch coverage, 6.18ms 50-ticker load.**

## Performance

- **Duration:** ~2 min (start 04:05:48Z, end 04:07:40Z)
- **Started:** 2026-05-01T04:05:48Z
- **Completed:** 2026-05-01T04:07:40Z
- **Tasks:** 1 feature delivered via TDD (RED → GREEN; REFACTOR skipped per plan)
- **Files modified:** 2 created (`watchlist/loader.py` 69 lines, `tests/test_loader.py` 147 lines)

## Accomplishments

- `watchlist/loader.py` ships `load_watchlist`, `save_watchlist`, `DEFAULT_PATH` — total 69 lines, zero third-party deps beyond Pydantic (already in tree).
- All 5 plan-mandated probes (1-W2-01 through 1-W2-05) green; bonus missing-file branch test green; bonus failure-cleanup test green — **7/7 passing**.
- Combined Wave 1 (schemas, 8 tests) + Wave 2 (loader, 7 tests) all green: **15/15**.
- Coverage on `watchlist/loader.py`: **100% line, 100% branch** (gate ≥90%, 25 stmts / 2 branches / 0 missing).
- 50-ticker load measured at **6.18ms** — 16x under the 100ms perf gate.
- Round-trip byte-identical confirmed: `seeded_watchlist_path` → load → save → bytes unchanged. Locks the determinism contract end-to-end.
- Sorted-key output verified manually: top-level alpha (`tickers` then `version`); per-ticker alpha (`created_at`, `long_term_lens`, `notes`, ...). Git diffs from CLI add/remove will be minimal and predictable.
- Failure-cleanup contract locked: monkeypatched `os.replace` to raise OSError; assertion confirms tmp file is removed AND the original target is untouched.

## Task Commits

This plan was a single TDD feature, executed as RED → GREEN (REFACTOR skipped per plan: "The loader is too small to refactor"):

1. **RED — failing loader tests** — `7c1bf15` (test)
   - 6 test functions added (5 mandated probes + 1 bonus missing-file branch)
   - Verified all fail with `ModuleNotFoundError: No module named 'watchlist.loader'`

2. **GREEN — implement loader + add coverage test** — `e40f0eb` (feat)
   - `watchlist/loader.py` per 01-RESEARCH.md "Loader / atomic save" example, verbatim
   - Added 7th test (`test_save_cleanup_on_replace_failure`) to close coverage gap on lines 67-69 (os.replace failure path) — Rule 2 deviation
   - All 7 loader tests green; combined schemas+loader 15/15 green; coverage 100% (gate ≥90%)

**Plan metadata commit:** TBD (to be created after this SUMMARY.md is written)

## Files Created/Modified

- **`watchlist/loader.py`** (created, 69 lines) — `load_watchlist(path)` reads + validates, `save_watchlist(wl, path)` re-validates + atomically writes with deterministic key ordering. Stdlib only (`json`, `os`, `tempfile`, `pathlib`) plus the `Watchlist` import from `analysts.schemas`. `DEFAULT_PATH = Path("watchlist.json")` is cwd-relative on purpose — only the CLI argparse layer ever resolves it (Pitfall #7).
- **`tests/test_loader.py`** (created, 147 lines) — 7 tests, all green. Reuses the three watchlist fixtures from `tests/conftest.py` (`empty_watchlist_path`, `seeded_watchlist_path`, `large_watchlist_path`); never writes to repo root.

## Decisions Made

1. **Serialization: stdlib `json.dumps(..., sort_keys=True)` not `model_dump_json`.** CONTEXT.md correction #3 + Pydantic v2 issue #7424 — `model_dump_json` does not sort dict keys, so per-ticker insertion order would leak into `watchlist.json`. With sort_keys=True, every CLI add/remove produces a predictable git diff and round-trip is byte-identical even after the user manually re-orders the file in their editor. The `test_round_trip_byte_identical` probe enforces this end-to-end.

2. **Pitfall #2: `with NamedTemporaryFile(...) as tmp:` exits before `os.replace`.** On Windows, the open handle holds an exclusive lock; calling `os.replace` while the handle is open raises `PermissionError`. The implementation captures `tmp_path = Path(tmp.name)` inside the `with` block, then performs `os.replace(tmp_path, path)` outside — only after the context manager closes the handle. This was developed and tested directly on Windows 11 (the user's host); zero `PermissionError` encountered during the run. The 7 tests' tmp-file lifecycle (creation, write, close, replace, no-orphans assertion) all passed cleanly on this OS.

3. **`load_watchlist` on missing path returns empty `Watchlist()` (no error).** Drives the CLI UX: `markets add AAPL` on a fresh checkout with no `watchlist.json` MUST work — the loader returns `Watchlist(version=1, tickers={})`, the CLI mutates, then save creates the file. If load raised on missing path, every CLI command would need a special-case "first run" branch.

4. **Defense-in-depth re-validation in `save_watchlist`.** `Watchlist.model_validate(watchlist.model_dump())` runs before serialization. The `Watchlist` and `TickerConfig` configs already set `validate_assignment=True`, so a properly-mutated model stays validated — but if a caller bypasses that (e.g., constructs an empty model and stuffs `.tickers` via `__dict__` manipulation, or mutates a child in a subtle way), this catches it before bad data hits disk.

5. **Added 7th test (`test_save_cleanup_on_replace_failure`) — Rule 2 auto-fix for missing critical coverage.** Plan listed 6 tests but ran the coverage gate at 89% (lines 67-69 — the OSError cleanup path — uncovered). Without this test, a regression that removed `tmp_path.unlink(missing_ok=True)` would silently litter the user's directory with orphan `*.tmp` files after any failed save (visible in `git status`, confusing). The test monkeypatches `watchlist.loader.os.replace` to raise OSError, asserts the OSError propagates, AND asserts no tmp file remains. Coverage now 100%.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Missing Critical] Added test for save failure-cleanup contract**
- **Found during:** GREEN-phase coverage check
- **Issue:** Plan specified 6 tests; coverage on `watchlist/loader.py` came in at **88.89%** (gate ≥90%). Missing lines 67-69 — the `except OSError: tmp_path.unlink(missing_ok=True); raise` cleanup path. The plan's `<verification>` step 4 ("Verify no orphan tmp files: `find /tmp -name '*.tmp' -path '*watchlist*'` returns empty") asserts the *happy-path* case but not the failure-mode contract. A regression that silently dropped the cleanup would not be caught.
- **Fix:** Added `test_save_cleanup_on_replace_failure` — uses pytest `monkeypatch` to swap `watchlist.loader.os.replace` for a raiser, calls `save_watchlist`, asserts OSError propagates (`pytest.raises(OSError)`), and asserts the parent dir contains no `*.tmp` files. Locks the contract under regression.
- **Files modified:** `tests/test_loader.py` (one new test function, ~25 lines)
- **Verification:** Coverage rose from 88.89% → 100% line/branch on `watchlist/loader.py`. Combined Wave 1+2 tests all green.
- **Committed in:** `e40f0eb` (rolled into the GREEN feat commit, since the test exercises the same module being introduced)

---

**Total deviations:** 1 auto-fixed (Rule 2 — missing critical coverage of failure-cleanup contract)
**Impact on plan:** No scope creep. The new test exists purely to lock the cleanup behavior the plan's implementation already specified; the implementation code is unchanged from the 01-RESEARCH.md "Loader / atomic save" example. The 90% coverage gate would have failed on the originally-specified 6 tests; the deviation closes that gap and additionally hardens against silent regression of orphan-tmp-file cleanup.

## Issues Encountered

- **`uv` not on default PATH:** Resolved per the existing Open-Items note in STATE.md — used `export PATH="$HOME/AppData/Roaming/Python/Python314/Scripts:$PATH"` per-command. Not a Plan 03 issue; carried forward from Plan 01.
- **Windows file-lock (Pitfall #2):** Anticipated, did not occur. The `with`-block-exit-then-os.replace pattern worked first try on Windows 11 across all 7 tests including the 50-ticker stress and the failure-cleanup monkeypatch test. The decision to capture `tmp.name` inside the `with` and call `os.replace` outside it (rather than passing `tmp` itself or relying on `delete=True`) is what kept this clean.

## Plan Output Checklist

Per the plan's `<output>` section:

- ✅ Final line count of `watchlist/loader.py`: **69 lines** (plan expected 50-70)
- ✅ Coverage on `watchlist/loader.py`: **100%** (gate ≥90%)
- ✅ Byte-identical round-trip: `test_round_trip_byte_identical` green
- ✅ Confirmation `json.dumps(... sort_keys=True)` is used (not `model_dump_json`): line 51 of loader.py
- ✅ Atomic-save: confirmed no orphan `*.tmp` files after success (asserted in `test_atomic_save_no_partial`)
- ✅ Windows file-lock issue: anticipated via `with`-block-exit + outside-block `os.replace`; **not encountered** during this run on Windows 11
- ✅ 50-ticker load timing: **6.18ms** (gate <100ms)
- ✅ Deviation from 01-RESEARCH.md "Loader / atomic save" example: **none in implementation**; only deviation is the additional 7th test (Rule 2, documented above)

## Probe → Test Mapping (per 01-VALIDATION.md)

| Probe ID | Requirement | Test | Status |
|----------|-------------|------|--------|
| 1-W2-01 | WATCH-01 | `test_load_30_ticker_watchlist` | green |
| 1-W2-02 | WATCH-01 | `test_load_50_tickers_under_100ms` (6.18ms) | green |
| 1-W2-03 | WATCH-02 | `test_atomic_save_no_partial` | green |
| 1-W2-04 | WATCH-05 | `test_malformed_json_raises` | green |
| 1-W2-05 | WATCH-05 | `test_round_trip_byte_identical` | green |
| (bonus) | (branch lock) | `test_load_nonexistent_returns_empty` | green |
| (bonus) | (branch lock) | `test_save_cleanup_on_replace_failure` | green |

## Next Phase Readiness

- **Plan 04 (CLI core — add/remove)** unblocked: can now `from watchlist.loader import load_watchlist, save_watchlist, DEFAULT_PATH` without re-implementing file I/O.
- **Plan 05 (CLI readonly + example)** unblocked: same import, plus `examples/watchlist.json` will use the same byte-identical serialization that `save_watchlist` produces (so committing the example to git is stable).
- **Phase 2 (Ingestion)** unblocked at the loader contract: ingestion will `wl = load_watchlist(...)` to enumerate which tickers to fetch.
- **No blockers.** No technical debt added. No environmental changes needed.

## Self-Check: PASSED

Verified after writing this SUMMARY.md:

- ✅ `watchlist/loader.py` exists (69 lines)
- ✅ `tests/test_loader.py` exists (147 lines)
- ✅ Commit `7c1bf15` exists (RED) — verified with `git log`
- ✅ Commit `e40f0eb` exists (GREEN) — verified with `git log`
- ✅ All 15 schemas+loader tests green
- ✅ Coverage gate met (100% ≥ 90%)

---
*Phase: 01-foundation-watchlist-per-ticker-config*
*Plan: 03 — loader*
*Completed: 2026-05-01*
