---
phase: 01-foundation-watchlist-per-ticker-config
plan: 01
subsystem: infra
tags: [python, uv, pytest, pydantic, ruff, hatchling, pyproject]

# Dependency graph
requires: []
provides:
  - "uv-managed Python project with Pydantic 2.13, pytest 9, pytest-cov 7, ruff 0.15 installed"
  - "Console script wiring: 'markets' executable maps to cli.main:main (verified end-to-end)"
  - "Three importable empty packages: analysts/, watchlist/, cli/"
  - "Placeholder cli/main.py — main(argv) callable returning exit code 1 with stderr message"
  - "tests/ scaffolding with conftest.py exposing empty/seeded/large watchlist fixtures (lazy-imported)"
  - "Pytest framework wired: --collect-only exits 5 (no tests, no ImportError)"
  - "Coverage config (branch=true, sources analysts/watchlist/cli) and ruff config (py312, line=100)"
affects: [01-02-schemas, 01-03-loader, 01-04-cli-core, 01-05-cli-readonly-and-example]

# Tech tracking
tech-stack:
  added:
    - "pydantic 2.13.3 (>=2.10 spec)"
    - "pytest 9.0.3 (>=8.0 spec)"
    - "pytest-cov 7.1.0 (>=5.0 spec)"
    - "ruff 0.15.12 (>=0.6 spec)"
    - "coverage 7.13.5 (transitive via pytest-cov)"
    - "hatchling (build-backend, transitive via uv build)"
  patterns:
    - "Lazy fixture imports — defer 'from analysts.schemas import ...' to fixture body so conftest collects before downstream modules exist"
    - "Deterministic JSON serialization — json.dumps(model.model_dump(mode='json'), indent=2, sort_keys=True) + newline (per 01-RESEARCH.md correction #3)"
    - "Hyphen-form ticker normalization (BRK-B not BRK.B) — yfinance compat per 01-RESEARCH.md correction #1"
    - "from __future__ import annotations — project-wide forward-reference flexibility"

key-files:
  created:
    - "pyproject.toml — uv-managed project, console script, pytest/coverage/ruff config"
    - ".gitignore — Python/uv/IDE/OS/project tmp file exclusions"
    - "analysts/__init__.py — empty package marker"
    - "watchlist/__init__.py — empty package marker"
    - "cli/__init__.py — empty package marker"
    - "cli/main.py — placeholder main() entry; full dispatcher in Plan 04"
    - "tests/__init__.py — pytest discovery marker"
    - "tests/conftest.py — empty/seeded/large watchlist fixtures (lazy schema import)"
  modified: []

key-decisions:
  - "uv installed via 'python -m pip install --user uv' (system had no package manager / no shell PATH entry); binary at C:/Users/Mohan/AppData/Roaming/Python/Python314/Scripts/uv.exe"
  - "Required 'uv sync --reinstall-package markets' after creating package directories — initial wheel built before analysts/watchlist/cli existed on disk; reinstall picked up the now-existing dirs (Windows + hatchling editable-install gotcha confirmed per 01-RESEARCH.md State of the Art)"
  - "Python 3.14.3 used as interpreter (system default; satisfies requires-python >=3.12)"
  - "uv resolved pytest 9.0.3 (one major above the >=8.0 floor); pinning was deliberately not done since plan accepts >=8"

patterns-established:
  - "Lazy fixture imports: conftest.py at scaffold time references modules that don't yet exist; deferring imports to fixture bodies keeps collection green until consumers materialize"
  - "Hatchling explicit packages list: [tool.hatch.build.targets.wheel] packages = [...] is mandatory because the project isn't src-layout — hatchling cannot auto-discover root-level packages"
  - "Console-script verification at scaffold time: ship a working stub for cli.main:main so [project.scripts] wiring failures are caught here, not muddied with subcommand bugs in Plan 04"

requirements-completed: [WATCH-01, WATCH-02, WATCH-03, WATCH-04, WATCH-05]

# Metrics
duration: 2min
completed: 2026-05-01
---

# Phase 1 Plan 1: Scaffold Summary

**uv-managed Python 3.12+ project bootstrap — Pydantic 2.13 / pytest 9 / ruff 0.15 installed, three importable packages (analysts, watchlist, cli), `markets` console script verified end-to-end, pytest+conftest scaffold with lazy-imported watchlist fixtures.**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-01T03:53:36Z
- **Completed:** 2026-05-01T03:55:35Z
- **Tasks:** 3
- **Files created:** 8

## Accomplishments

- `uv sync --dev` resolves 15 packages cleanly into project-local `.venv/`
- `uv run markets` prints "markets: CLI not yet implemented (Phase 1 Plan 04)" to stderr and exits 1 — proves `[project.scripts]` wiring works
- `uv run pytest --collect-only` exits 5 (no tests, no ImportError) — framework wired, ready for downstream test files
- `tests/conftest.py` defines all three fixtures Plans 02-05 depend on (`empty_watchlist_path`, `seeded_watchlist_path`, `large_watchlist_path`) using lazy imports so this plan's verification doesn't require Plan 02
- All four directories (`analysts/`, `watchlist/`, `cli/`, `tests/`) are importable Python packages

## Task Commits

Each task was committed atomically:

1. **Task 1: Initialize uv project + pyproject.toml + .gitignore** — `fb3fad7` (chore)
2. **Task 2: Create three empty packages + placeholder cli/main.py** — `d3794ce` (feat)
3. **Task 3: Create tests/__init__.py + tests/conftest.py with all three fixtures** — `758a2fb` (test)

**Plan metadata:** _pending — final commit captures SUMMARY + STATE + ROADMAP_

## Files Created/Modified

- `pyproject.toml` — uv project metadata, deps, `[project.scripts] markets = "cli.main:main"`, pytest/coverage/ruff config, hatchling build-backend
- `.gitignore` — `__pycache__/`, `.venv/`, `*.egg-info/`, `.pytest_cache/`, `.coverage`, `.ruff_cache/`, `uv.lock`, IDE/OS noise, `watchlist.json*.tmp`
- `analysts/__init__.py` — empty (zero bytes), package marker
- `watchlist/__init__.py` — empty (zero bytes), package marker
- `cli/__init__.py` — empty (zero bytes), package marker
- `cli/main.py` — placeholder `main(argv: list[str] | None = None) -> int` returning 1 with stderr message
- `tests/__init__.py` — empty (zero bytes), pytest discovery marker
- `tests/conftest.py` — three fixtures (empty/seeded/large watchlist paths) with lazy `from analysts.schemas import` inside fixture bodies

## Installed Versions (`uv pip list`)

| Package      | Version  | Spec     |
| ------------ | -------- | -------- |
| pydantic     | 2.13.3   | >=2.10   |
| pydantic-core| 2.46.3   | (transitive) |
| pytest       | 9.0.3    | >=8.0    |
| pytest-cov   | 7.1.0    | >=5.0    |
| ruff         | 0.15.12  | >=0.6    |
| coverage     | 7.13.5   | (transitive) |
| markets      | 0.1.0    | (this project, editable) |

All version floors from pyproject.toml satisfied. Pytest landed at 9.x (one major above the `>=8` floor) — plan's `must_haves.truths` accepts "pytest 8+", so this is in-spec.

## Decisions Made

- **uv installed via `python -m pip install --user uv`** — the system had no `uv` on PATH (Bash, PowerShell, or shims). The pip install puts the binary at `C:/Users/Mohan/AppData/Roaming/Python/Python314/Scripts/uv.exe`. For this plan I prepended that directory to `PATH` per-command. **Persistent fix recommended:** add the directory to the user PATH env var (or use `pipx install uv`).
- **Python 3.14.3 used as the interpreter** rather than 3.12 — Python 3.12 is not installed on the host. Project's `requires-python = ">=3.12"` is satisfied. Ruff `target-version = "py312"` keeps lint targeted at the lower bound.
- **Did not pin `uv.lock`** — gitignored per plan; locking deferred to CI setup phase.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] uv not installed on host system**
- **Found during:** Pre-Task 1 (verifying `uv sync --dev` would run)
- **Issue:** `uv` binary was not present anywhere on system — neither bash PATH, PowerShell PATH, nor common install locations (`~/.cargo/bin`, `~/.local/bin`, scoop shims). Without `uv`, none of the three tasks' automated verifications could run.
- **Fix:** Installed via `python -m pip install --user uv` (uv 0.11.8 → `C:/Users/Mohan/AppData/Roaming/Python/Python314/Scripts/uv.exe`). For each subsequent command, prepended that directory to PATH.
- **Files modified:** None (host environment only — no project-tracked artifacts changed)
- **Verification:** `python -m uv --version` → `uv 0.11.8`; `uv sync --dev` exited 0 with 15 packages resolved.
- **Committed in:** N/A (host-side install, not a tracked change)

**2. [Rule 3 — Blocking] `uv run markets` failed after Task 2 with ModuleNotFoundError: No module named 'cli'**
- **Found during:** Task 2 verification (running `uv run markets` to confirm console-script wiring)
- **Issue:** Initial `uv sync --dev` in Task 1 built the `markets` wheel before the `analysts/`, `watchlist/`, `cli/` directories existed. `[tool.hatch.build.targets.wheel] packages = ["analysts", "watchlist", "cli"]` named directories that hadn't materialized yet, so the wheel shipped without them. Re-running `uv sync` after creating the directories did not rebuild (uv saw the resolution as unchanged).
- **Fix:** Ran `uv sync --dev --reinstall-package markets` to force a rebuild of the editable install. The hatchling wheel then included all three packages.
- **Files modified:** None (only `.venv/` regenerated)
- **Verification:** `uv run markets` → `markets: CLI not yet implemented (Phase 1 Plan 04)` (stderr), exit 1.
- **Committed in:** Captured in Task 2 commit message body (`d3794ce`)
- **Note:** This matches the "Windows + hatchling editable-install gotcha" called out in `01-RESEARCH.md` State of the Art. Recommend adding to PITFALLS.md or downstream plans: when a plan creates new top-level packages listed in `[tool.hatch.build.targets.wheel] packages`, follow with `uv sync --reinstall-package <project>`.

---

**Total deviations:** 2 auto-fixed (both Rule 3 blocking — environment / packaging mechanics)
**Impact on plan:** Both deviations were environmental, not design changes. Plan content (files, contents, contracts, fixtures) shipped exactly as written. No scope creep. The hatchling reinstall observation strengthens the existing 01-RESEARCH.md guidance.

## Issues Encountered

- Initial `uv sync --dev` succeeded but produced a wheel missing the `cli` package because directories were created in Task 2 (after Task 1's sync). Resolved with `--reinstall-package markets` flag — see Deviation #2 above.
- Task 1's `uv sync` already built and installed `markets==0.1.0` because `[project.scripts]` requires hatchling to materialize the script entry — this is expected behavior, just timing-sensitive relative to package-dir creation.

## User Setup Required

None — no external service configuration required. One environmental recommendation:

- **Add `C:/Users/Mohan/AppData/Roaming/Python/Python314/Scripts` to user PATH** so `uv` is available without the prefix workaround. Otherwise downstream plans must repeat the per-command PATH prepend.

## Next Phase Readiness

**Ready for Plan 02 (schemas):**
- `analysts/__init__.py` exists; Plan 02 can drop in `analysts/schemas.py` with `TickerConfig` + `Watchlist` Pydantic models.
- `tests/conftest.py` lazy-imports `from analysts.schemas import TickerConfig, Watchlist` — those imports activate the moment Plan 02's `seeded_watchlist_path` / `large_watchlist_path` fixtures are first requested by `test_schemas.py` / `test_loader.py`.
- Pytest is wired with strict markers and coverage on `analysts/watchlist/cli` — Plan 02's coverage gate evaluation will work out-of-the-box.
- Console-script wiring is verified end-to-end — Plan 04 can replace `cli.main.main()` body without touching pyproject.toml.

**No blockers.** All five Phase-1 requirements (WATCH-01..05) have their scaffold dependencies met.

## Self-Check: PASSED

Verified post-write:

- pyproject.toml: FOUND
- .gitignore: FOUND
- analysts/__init__.py: FOUND
- watchlist/__init__.py: FOUND
- cli/__init__.py: FOUND
- cli/main.py: FOUND
- tests/__init__.py: FOUND
- tests/conftest.py: FOUND
- Commit fb3fad7 (Task 1): FOUND in git log
- Commit d3794ce (Task 2): FOUND in git log
- Commit 758a2fb (Task 3): FOUND in git log

---
*Phase: 01-foundation-watchlist-per-ticker-config*
*Completed: 2026-05-01*
