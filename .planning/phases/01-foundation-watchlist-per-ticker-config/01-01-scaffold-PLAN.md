---
phase: 01-foundation-watchlist-per-ticker-config
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - pyproject.toml
  - analysts/__init__.py
  - watchlist/__init__.py
  - cli/__init__.py
  - cli/main.py
  - tests/__init__.py
  - tests/conftest.py
  - .gitignore
autonomous: true
requirements: [WATCH-01, WATCH-02, WATCH-03, WATCH-04, WATCH-05]
must_haves:
  truths:
    - "uv sync installs Pydantic 2.10+, pytest 8+, pytest-cov 5+, ruff 0.6+ with zero errors"
    - "uv run pytest --collect-only succeeds (zero tests collected is fine; framework is wired)"
    - "uv run markets prints a 'not yet implemented' placeholder and exits cleanly"
    - "Empty packages (analysts, watchlist, cli) are importable in Python 3.12"
  artifacts:
    - path: "pyproject.toml"
      provides: "uv-managed project metadata, console script entry point, pytest config, coverage config"
      contains: "[project.scripts]"
    - path: "analysts/__init__.py"
      provides: "analysts package marker"
    - path: "watchlist/__init__.py"
      provides: "watchlist package marker"
    - path: "cli/__init__.py"
      provides: "cli package marker"
    - path: "cli/main.py"
      provides: "argparse dispatcher placeholder; main() entry function"
    - path: "tests/__init__.py"
      provides: "tests package marker for pytest discovery"
    - path: "tests/conftest.py"
      provides: "shared fixtures: empty_watchlist_path, seeded_watchlist_path, large_watchlist_path"
  key_links:
    - from: "pyproject.toml [project.scripts]"
      to: "cli/main.py:main"
      via: "console-script entry point"
      pattern: "markets = \"cli.main:main\""
    - from: "tests/conftest.py"
      to: "analysts.schemas (future)"
      via: "fixtures import schemas — initially placeholder; finalized in Plan 02"
      pattern: "from analysts.schemas import"
---

<objective>
Bootstrap the Python project: pyproject.toml with uv-managed deps, three empty packages (`analysts/`, `watchlist/`, `cli/`), a placeholder CLI dispatcher, and the pytest scaffold (including `tests/conftest.py` with the three watchlist fixtures the rest of the phase depends on). After this plan, every downstream plan in Phase 1 has a working test framework, a console-script target, and importable packages.

Purpose: All four downstream plans (schemas, loader, CLI add/remove, CLI read-only) depend on this scaffold. Without it, `uv run pytest` cannot run, `uv run markets` does not exist, and downstream plans would each duplicate setup work. Per `01-VALIDATION.md` Wave 0 Requirements, this plan creates the test files only as conftest+empty markers — the actual `tests/test_*.py` files are written in their respective downstream plans alongside the code they verify (TDD-style, plan-by-plan).

Output: A green `uv sync` + `uv run pytest --collect-only` + `uv run markets` placeholder. The console-script wiring is verified end-to-end so downstream CLI plans only have to fill in subcommands.
</objective>

<execution_context>
@C:/Users/Mohan/.claude/workflows/execute-plan.md
@C:/Users/Mohan/.claude/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/research/STACK.md
@.planning/research/ARCHITECTURE.md
@.planning/phases/01-foundation-watchlist-per-ticker-config/01-CONTEXT.md
@.planning/phases/01-foundation-watchlist-per-ticker-config/01-RESEARCH.md
@.planning/phases/01-foundation-watchlist-per-ticker-config/01-VALIDATION.md

<interfaces>
<!-- This plan creates new interfaces; no existing code to extract. -->
<!-- Downstream plans 02-05 will import from these packages. The placeholder cli/main.py
     defines the main() function signature that downstream plans wire subcommands into. -->

Console script entry (in pyproject.toml):
```toml
[project.scripts]
markets = "cli.main:main"
```

Placeholder cli/main.py contract (downstream Plan 04 will replace the body):
```python
def main(argv: list[str] | None = None) -> int:
    """Console script entry point. Returns process exit code."""
```

conftest.py fixture contracts (downstream plans use these):
```python
@pytest.fixture
def empty_watchlist_path(tmp_path: Path) -> Path:
    """Returns a path to a non-existent watchlist file in a tmp directory."""

@pytest.fixture
def seeded_watchlist_path(tmp_path: Path) -> Path:
    """Returns a path to a 3-ticker watchlist file in a tmp directory.
       Tickers: AAPL (value, thesis 200), NVDA (growth), BRK-B (value)."""

@pytest.fixture
def large_watchlist_path(tmp_path: Path) -> Path:
    """Returns a path to a 35-ticker synthetic watchlist file (for WATCH-01 30+ probe)."""
```
</interfaces>

<corrections_callout>
The CONTEXT.md document at the top has a CORRECTIONS callout flagging three locked decisions that research overturned. **All five plans in Phase 1 must follow research, not the original CONTEXT.md decision text:**

1. **Ticker normalization → HYPHEN, not dot.** yfinance uses `BRK-B`; the dotted form (`BRK.B`) returns empty data and silently triggers `data_unavailable: true` downstream. Accept `.`, `/`, `_`, `-` as input separators; normalize to hyphen. Regex: `^[A-Z][A-Z0-9.\-]{0,8}$` (allows hyphen and dot in pattern; normalizer always emits hyphen).
2. **Cross-field validators → `@model_validator(mode="after")`, not `@field_validator`.** field_validator runs in declaration order with partial state; cross-field rules need a fully-validated model. Single-field rules (e.g., `thesis_price > 0`) can stay as `@field_validator`.
3. **JSON serialization → `json.dumps(model.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"`, NOT `model_dump_json(indent=2)`.** Pydantic v2 doesn't sort dict keys (issue #7424); without `sort_keys` the watchlist file's git diffs are noisy after every mutation.

This scaffold plan does not write validators or serialization code — but `tests/conftest.py` already uses the corrected serialization in `seeded_watchlist_path` and `large_watchlist_path` fixtures (per the Code Examples section of 01-RESEARCH.md). And `BRK-B` is the form used in seeded fixtures, not `BRK.B`.
</corrections_callout>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Initialize uv project + pyproject.toml + .gitignore</name>
  <files>pyproject.toml, .gitignore</files>
  <action>
Create `pyproject.toml` at repo root with the full configuration from `01-RESEARCH.md` § Code Examples ("pyproject.toml (minimum for this phase)") — verbatim modulo the `dependencies` and `dev` group versions. Specifically:

```toml
[project]
name = "markets"
version = "0.1.0"
description = "Personal stock research dashboard — backend"
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.10",
]

[project.scripts]
markets = "cli.main:main"

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "ruff>=0.6",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["analysts", "watchlist", "cli"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers"

[tool.coverage.run]
source = ["analysts", "watchlist", "cli"]
branch = true
```

Then create `.gitignore` at repo root with:
```
# Python
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.coverage
htmlcov/
.ruff_cache/

# uv
.venv/
uv.lock

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Project
watchlist.json.tmp
watchlist.json.*.tmp
```

Note on `uv.lock`: gitignore it for now — locking will be revisited when CI is set up. The hatchling build-backend is required for `[project.scripts]` to materialize the `markets` console script (per 01-RESEARCH.md "State of the Art" note).

Then run:
```
uv sync --dev
```

This installs Pydantic, pytest, pytest-cov, ruff into a project-local `.venv`. Verify installation with `uv run python -c "import pydantic; print(pydantic.VERSION)"` — should print 2.10.x or higher.

WHY: pyproject.toml is the single configuration spine for all of Phase 1 — deps, console script, pytest, coverage gate, ruff. Doing it once here removes config bikeshedding from every downstream plan.
  </action>
  <verify>
    <automated>uv sync --dev && uv run python -c "import pydantic, pytest; print('pydantic', pydantic.VERSION); print('pytest', pytest.__version__)"</automated>
  </verify>
  <done>`uv sync --dev` exits 0; `uv run python -c "import pydantic, pytest"` prints version strings showing pydantic 2.10+ and pytest 8+; `.venv/` exists; `pyproject.toml` contains the `[project.scripts] markets = "cli.main:main"` line; `.gitignore` excludes `__pycache__`, `.venv`, `*.egg-info`, `.coverage`, `.pytest_cache`, `.ruff_cache`, `watchlist.json.tmp`.</done>
</task>

<task type="auto">
  <name>Task 2: Create three empty packages + placeholder cli/main.py</name>
  <files>analysts/__init__.py, watchlist/__init__.py, cli/__init__.py, cli/main.py</files>
  <action>
Create four files. The three `__init__.py` files are empty (zero bytes).

For `cli/main.py`, write a minimal placeholder that defines the `main()` entry function the console script targets. Plan 04 will replace its body with the full argparse dispatcher; here we ship a working stub so the console-script wiring can be verified end-to-end. Content:

```python
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
```

WHY this stub: it lets us verify the `[project.scripts] markets = "cli.main:main"` wiring in pyproject.toml actually produces a runnable executable (`uv run markets`) before Plan 04 fills in subcommand logic. If the wiring is broken, we catch it here, not in Plan 04 where the failure mode is muddier (could be argparse, could be packaging).

Note on the `from __future__ import annotations` import: Pydantic v2 doesn't require it, but the project standardizes on it for forward-reference flexibility — see 01-RESEARCH.md Pattern 5 example.
  </action>
  <verify>
    <automated>uv sync --dev && uv run python -c "import analysts, watchlist, cli, cli.main; assert callable(cli.main.main); print('packages OK')"</automated>
  </verify>
  <done>Four files exist; all three packages import cleanly under `uv run python -c "import analysts, watchlist, cli"`; `cli.main.main` is a callable; `uv run markets` (after `uv pip install -e .` if needed for editable install) prints "markets: CLI not yet implemented (Phase 1 Plan 04)" to stderr and exits with code 1.</done>
</task>

<task type="auto">
  <name>Task 3: Create tests/__init__.py + tests/conftest.py with all three fixtures</name>
  <files>tests/__init__.py, tests/conftest.py</files>
  <action>
Create `tests/__init__.py` as empty (zero bytes).

Create `tests/conftest.py` with the three fixtures from `01-RESEARCH.md` § Code Examples ("conftest.py / pytest fixtures"). The fixtures depend on `analysts.schemas` (Plan 02 output), so we **import lazily inside each fixture** to avoid collection-time import errors during this plan's own verification (when `analysts.schemas` doesn't yet exist beyond a placeholder).

CRITICAL: This plan creates `analysts/__init__.py` empty in Task 2. So the `from analysts.schemas import ...` lazy import inside the fixtures will only succeed AFTER Plan 02 ships `analysts/schemas.py`. That's fine — pytest collection of `conftest.py` itself does not exercise the fixtures unless a test requests them, and Plan 01's verification only runs `pytest --collect-only` (collection, not execution). Plan 02's verification runs the actual schema tests, which DO exercise these fixtures, and by then `analysts/schemas.py` exists.

Content:

```python
"""Shared pytest fixtures for the markets test suite.

Fixtures here are imported by tests in:
- tests/test_schemas.py     (Plan 02)
- tests/test_loader.py      (Plan 03)
- tests/test_cli_add.py     (Plan 04)
- tests/test_cli_remove.py  (Plan 04)
- tests/test_cli_errors.py  (Plan 04)
- tests/test_cli_readonly.py (Plan 05)

The fixtures import schemas lazily so this conftest collects cleanly even
before Plan 02 lands the schema module.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def empty_watchlist_path(tmp_path: Path) -> Path:
    """Returns a path to a non-existent watchlist file in a tmp directory."""
    return tmp_path / "watchlist.json"


@pytest.fixture
def seeded_watchlist_path(tmp_path: Path) -> Path:
    """Returns a path to a 3-ticker watchlist file (AAPL value, NVDA growth, BRK-B value).

    Note: BRK-B uses HYPHEN (not BRK.B) — yfinance compatibility per 01-RESEARCH.md
    correction. The schema normalizes inputs to hyphen form.
    """
    from analysts.schemas import TickerConfig, Watchlist

    path = tmp_path / "watchlist.json"
    wl = Watchlist(
        tickers={
            "AAPL": TickerConfig(ticker="AAPL", long_term_lens="value", thesis_price=200.0),
            "NVDA": TickerConfig(ticker="NVDA", long_term_lens="growth"),
            "BRK-B": TickerConfig(ticker="BRK-B", long_term_lens="value"),
        }
    )
    # Per 01-RESEARCH.md correction #3: use json.dumps(... sort_keys=True) for deterministic output
    payload = json.dumps(wl.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    path.write_text(payload, encoding="utf-8")
    return path


@pytest.fixture
def large_watchlist_path(tmp_path: Path) -> Path:
    """Returns a path to a 35-ticker synthetic watchlist (for WATCH-01 30+ probe)."""
    from analysts.schemas import TickerConfig, Watchlist

    path = tmp_path / "watchlist.json"
    sample = [
        "AAPL", "MSFT", "NVDA", "GOOG", "AMZN", "META", "TSLA", "BRK-B", "JPM", "V",
        "XOM", "UNH", "JNJ", "PG", "HD", "MA", "CVX", "ABBV", "KO", "PFE",
        "PEP", "WMT", "BAC", "TMO", "COST", "DIS", "CRM", "ORCL", "NKE", "ADBE",
        "AMD", "NFLX", "INTC", "CSCO", "QCOM",
    ]
    wl = Watchlist(tickers={t: TickerConfig(ticker=t) for t in sample})
    payload = json.dumps(wl.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    path.write_text(payload, encoding="utf-8")
    return path
```

WHY lazy import: at this plan's verification (`pytest --collect-only`), `analysts.schemas` does not yet exist — the module is empty. A top-level `from analysts.schemas import ...` would crash collection. Lazy import inside the fixture body defers the import until a test actually requests the fixture, which only happens in Plan 02+ verification.

WHY the ticker list is exactly 35: WATCH-01 mandates "30+ tickers" — 35 gives a comfortable margin and matches the example in 01-RESEARCH.md verbatim so the planner doesn't have to invent new tickers.

WHY include `BRK-B` in the sample: it exercises the hyphen-normalization invariant in the loader's load test (Plan 03) — proves we don't accidentally regress to dot form during round-trip.
  </action>
  <verify>
    <automated>uv run pytest --collect-only -q 2>&1 | tail -5</automated>
  </verify>
  <done>`tests/conftest.py` and `tests/__init__.py` exist; `uv run pytest --collect-only` exits with code 5 ("no tests collected") OR code 0 (zero tests but framework runs) — both are acceptable signal that the framework is wired and `conftest.py` parses without import errors. Stderr does NOT contain "ImportError" or "ModuleNotFoundError" for `analysts.schemas` at collection time (would indicate the lazy-import pattern was bypassed).</done>
</task>

</tasks>

<verification>
After all tasks complete:

1. `uv sync --dev` — installs all deps, exits 0
2. `uv run python -c "import pydantic, pytest, analysts, watchlist, cli; print('all imports OK')"` — exits 0
3. `uv run markets` — prints placeholder message to stderr, exits with code 1
4. `uv run pytest --collect-only -q` — exits with code 0 or 5 (zero tests collected); no ImportError
5. `pyproject.toml` contains `[project.scripts] markets = "cli.main:main"` and `[tool.pytest.ini_options] testpaths = ["tests"]`
6. `.gitignore` excludes `.venv/`, `__pycache__/`, `.pytest_cache/`, `.coverage`, `*.tmp`
</verification>

<success_criteria>
- [ ] `uv sync --dev` clean (Pydantic 2.10+, pytest 8+, pytest-cov 5+, ruff 0.6+ installed)
- [ ] `uv run pytest --collect-only` clean (no ImportError, ready for downstream test files)
- [ ] `uv run markets` runs (placeholder output) — proves console-script wiring works end-to-end
- [ ] All four directories (`analysts/`, `watchlist/`, `cli/`, `tests/`) are importable Python packages
- [ ] `tests/conftest.py` defines `empty_watchlist_path`, `seeded_watchlist_path`, `large_watchlist_path` — all using lazy imports of `analysts.schemas` so this plan's own verification doesn't require Plan 02 to exist
- [ ] `.gitignore` keeps `.venv/`, build artifacts, and `watchlist.json*.tmp` out of version control
</success_criteria>

<output>
After completion, create `.planning/phases/01-foundation-watchlist-per-ticker-config/01-01-scaffold-SUMMARY.md` documenting:
- Exact pydantic / pytest / pytest-cov / ruff versions installed (from `uv pip list`)
- Whether `uv sync --dev` worked first try or required `uv pip install -e .` (Windows + uv editable-install gotcha noted in 01-RESEARCH.md "State of the Art")
- Confirmation that `uv run markets` produces the placeholder output
- Confirmation that `tests/conftest.py` lazy imports work (collect-only succeeds)
- Any deviation from the pyproject.toml template in 01-RESEARCH.md and why
</output>
