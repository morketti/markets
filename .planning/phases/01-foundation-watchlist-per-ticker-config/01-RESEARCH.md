---
phase: 1
phase_name: Foundation — Watchlist + Per-Ticker Config
researched: 2026-04-29
domain: Python schema design + atomic file I/O + tiny CLI
confidence: HIGH
research_tier: normal
vault_status: not_attempted
vault_reads: []
---

# Phase 1: Foundation — Watchlist + Per-Ticker Config — Research

**Researched:** 2026-04-29
**Domain:** Pydantic v2 schema design, atomic JSON persistence, argparse CLI, Python 3.12 packaging
**Confidence:** HIGH (Pydantic + stdlib are well-trodden; only one ecosystem question — yfinance ticker format — has direct downstream impact and is verified)

## Summary

Phase 1 is a small surface area (~500 LOC of Python + tests) but its decisions ossify the schema for nine downstream phases. The good news: every technical question has a clear, well-documented answer in stdlib + Pydantic v2 — no exotic libraries needed. The bad news: there is one decision in CONTEXT.md that will cause downstream breakage if shipped as-written, and it must be reversed in the plan before anyone writes code.

**Critical correction (CONTEXT.md decision needs reversal):** CONTEXT.md says "normalize `BRK-B` → `BRK.B`" for downstream consistency with yfinance. This is **wrong**. yfinance accepts the hyphen form (`BRK-B`), not the dot form, for Berkshire Hathaway Class B. Yahoo Finance URLs and the yfinance library both use `BRK-B`. Shipping the dotted normalization will cause every Phase 2 yfinance call for `BRK.B` to silently return empty data, then trigger the `data_unavailable: true` path for that ticker — a confusing failure mode. Reverse the normalization: accept `BRK.B`, `BRK/B`, `BRK_B` and normalize to **`BRK-B`** (hyphen).

**Primary recommendation:** Pydantic v2 with `model_validator(mode="after")` for cross-field rules; argparse stdlib for CLI (no Click/Typer dependency); `tempfile.NamedTemporaryFile(dir=...) + os.replace()` atomic write; `difflib.get_close_matches` for "did you mean"; `pyproject.toml` with `[project.scripts]` entry point `markets = "cli.main:main"` and a single dispatching `main` that handles `add` / `remove` / `list` / `show` subcommands. Build in three serial waves: schemas → loader → CLI.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Source of truth:** `watchlist.json` at repo root (NOT in `data/`)
- **Format:** JSON (not YAML, not TOML) — for clean git diffs and zod compatibility in Phase 6
- **Schema home:** Pydantic v2 models in `analysts/schemas.py` (importable from any later phase without circular deps)
- **TickerConfig fields:** `ticker`, `short_term_focus: bool = True`, `long_term_lens: Literal["value", "growth", "contrarian", "mixed"] = "mixed"`, `thesis_price: Optional[float] = None`, `technical_levels: Optional[TechnicalLevels] = None`, `target_multiples: Optional[FundamentalTargets] = None`, `notes: str = ""`, `created_at: Optional[str] = None`, `updated_at: Optional[str] = None`
- **TechnicalLevels:** `support: Optional[float]`, `resistance: Optional[float]` — when both set, support < resistance
- **FundamentalTargets:** `pe_target`, `ps_target`, `pb_target` — when set, value > 0
- **Watchlist:** `version: int = 1`, `tickers: dict[str, TickerConfig]` — each `value.ticker == key` after normalization
- **CLI:** `cli/add_ticker.py`, `cli/remove_ticker.py` — argparse-based; atomic write via tmp + `os.replace`; full Watchlist re-validation after mutation
- **Validation behavior:** schema-level (not CLI-level); `Watchlist.model_validate_json` on load; surface full Pydantic error path on failure
- **Ticker normalization:** uppercase + class-share separator normalization + regex `^[A-Z][A-Z0-9.]{0,8}$`
- **Cross-field rules:** support < resistance, thesis_price > 0, target_multiples > 0, watchlist key == value.ticker, notes ≤ 1000 chars
- **No header comments needed** in this phase's files (no direct adaptation from reference repos)

### Claude's Discretion

- Specific Python package layout within `markets/` — recommendation: `watchlist/` package with `models.py` re-exporting from `analysts.schemas`, `loader.py`, `cli/` for utilities
- Whether to ship `watchlist.example.json` with 3-5 example tickers (recommended: yes)
- Exact error message wording
- Argparse subcommand structure (`markets watchlist add` vs separate scripts) — keep simple
- Whether to include `cli/list_watchlist.py` or `cli/show_ticker.py` for read-only inspection (recommended: yes, low cost, high QoL)
- Whether `created_at` / `updated_at` use UTC ISO 8601 with `Z` suffix (recommended) or local timezone

### Deferred Ideas (OUT OF SCOPE)

- Frontend watchlist CRUD UI — v1.x (WATCH-06, WATCH-07)
- Bulk import from CSV — v1.x
- Watchlist groups / categories — v2
- Per-config audit log (use `git log watchlist.json` instead)
- Real-time validation in CLI (does ticker exist on Yahoo) — defer to Phase 2
- Watchlist file location override — YAGNI for single-user
- Web-based config editing — out of scope
- Schema migration tooling — premature; bump `version` field manually if needed

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WATCH-01 | User can maintain a watchlist of 30+ tickers in `watchlist.json` | Validated by `Watchlist` Pydantic model with `tickers: dict[str, TickerConfig]`; performance check on 50-entry validation is HIGH-confidence safe (Pydantic v2 core is C-extension, microseconds per model) |
| WATCH-02 | User can add a ticker via CLI utility | argparse-based `cli/add_ticker.py` (or `markets watchlist add` subcommand); atomic write; sets `created_at` and `updated_at` |
| WATCH-03 | User can remove a ticker via CLI utility | argparse-based; refuses with `difflib.get_close_matches` suggestion when ticker not present |
| WATCH-04 | User can set per-ticker config | All fields covered by TickerConfig schema; CLI flags map 1:1 to fields |
| WATCH-05 | Per-ticker config is validated via Pydantic schema; invalid entries rejected with clear error | `Watchlist.model_validate_json()` on load + `Watchlist.model_validate()` after every mutation; `ValidationError.errors()` formatted with dot-path locations for CLI display |

## Critical Correction Needed (Before Implementation)

| Topic | CONTEXT.md says | Research finds | Recommendation |
|-------|-----------------|----------------|----------------|
| Class-share separator | Normalize to `BRK.B` (dot) "for downstream consistency with yfinance" | yfinance uses `BRK-B` (hyphen). Yahoo Finance URLs use `BRK-B`. The dot form returns empty data. | **Reverse the normalization direction.** Accept `BRK.B`, `BRK/B`, `BRK_B` as input and normalize to `BRK-B` (hyphen). Update the regex to allow hyphen: `^[A-Z][A-Z0-9.\-]{0,8}$`. Document the choice inline in the validator: `# yfinance uses hyphenated class-share notation (BRK-B); we normalize to that form for Phase 2 compatibility.` |

**Confidence:** HIGH — verified against yfinance README example and Yahoo Finance canonical URL `finance.yahoo.com/quote/BRK-B/`. The dot form (`BRK.B`) is what Google Finance / TradingView / IEX use; yfinance is in the hyphen camp.

The planner MUST surface this correction in the plan; if the user objects, the schema can preserve the dotted form but CONTEXT.md's stated rationale ("for downstream consistency with yfinance") is factually incorrect and should not be cited.

## Standard Stack

### Core (all already locked in `.planning/research/STACK.md`)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python | 3.12.x | Runtime | Locked; supports `X | None` syntax, `delete_on_close` on `NamedTemporaryFile`, modern type-hint UX |
| pydantic | ≥ 2.10 | Schema validation | Locked; v2 core is Rust-backed, ~50× faster than v1; `model_validator(mode="after")` is the canonical cross-field tool |
| pytest | ≥ 8.0 | Test runner | Locked; `tmp_path` fixture is the right primitive for file-system tests |
| pytest-cov | ≥ 5.0 | Coverage | Standard pairing |
| ruff | ≥ 0.6 | Lint + format | Locked; replaces black + isort + flake8 |

### Stdlib (no install needed)
| Module | Purpose | Note |
|--------|---------|------|
| `argparse` | CLI parsing | Sufficient for this CLI's complexity; avoid adding click/typer |
| `tempfile.NamedTemporaryFile` | Tmp file creation in same dir as target | `delete=False` pattern; close before rename |
| `os.replace` | Atomic rename (POSIX + Windows) | Atomic on both platforms via `MoveFileEx`; replaces target if exists |
| `pathlib.Path` | Path manipulation | Standard for new Python code |
| `difflib.get_close_matches` | "Did you mean" suggestions | Default cutoff 0.6 is right; ratchet to 0.7 for short strings like tickers |
| `json` | Pretty-print round-trip if needed | Use `json.dumps(model.model_dump(), indent=2, sort_keys=True)` for deterministic output (see Pitfalls) |
| `datetime` (with `timezone.utc`) | ISO 8601 timestamps | `datetime.now(timezone.utc).isoformat(timespec="seconds")` produces clean UTC `Z`-suffixed strings |
| `re` | Ticker regex | Single pattern, compiled once at module level |

### Alternatives Considered

| Instead of | Could Use | Tradeoff | Recommendation |
|------------|-----------|----------|----------------|
| argparse | typer | typer is sleeker (type-hint-driven, less boilerplate) but adds a dependency for ~100 LOC of CLI surface | **Stick with argparse.** Zero deps; YAGNI for this size. |
| argparse | click | click is the most popular Python CLI lib but heavier than typer (decorators, contexts) | **Stick with argparse.** |
| `os.replace` | `python-atomicwrites` library | Library wraps the same pattern + handles edge cases (durable fsync, lock files) | **Stdlib `os.replace`.** YAGNI; single-user CLI doesn't need fsync durability for a watchlist file. |
| `difflib` | `python-Levenshtein` (or `rapidfuzz`) | Faster, more accurate edit distance | **Stick with difflib.** Stdlib; ticker count is ≤ 50; speed is irrelevant. |
| `json.dumps(sort_keys=True)` | `model.model_dump_json(indent=2)` | model_dump_json doesn't yet support `sort_keys` natively (Pydantic issue #7424 still open as of 2026); for a top-level `dict[str, TickerConfig]`, key order matters for git diffs | **Use `json.dumps(model.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"`** for the persisted file. See Pitfalls #1. |
| `hypothesis` (property-based) | manual unit tests | Hypothesis would auto-generate edge cases but adds a dep + cognitive load for ~5 cross-field rules | **Skip Hypothesis for Phase 1.** Schema is simple enough that hand-rolled fixture cases cover it. Reconsider for Phase 4 (position-adjustment math has a real combinatorial surface). |

**Installation:**
```bash
uv add 'pydantic>=2.10'
uv add --dev 'pytest>=8.0' 'pytest-cov>=5.0' 'ruff>=0.6'
```

## Architecture Patterns

### Recommended Project Structure (this phase only)

```
markets/
├── analysts/
│   ├── __init__.py
│   └── schemas.py            # ALL Pydantic models live here per CONTEXT.md
├── watchlist/
│   ├── __init__.py
│   └── loader.py             # load_watchlist() / save_watchlist() — atomic I/O
├── cli/
│   ├── __init__.py
│   ├── main.py               # argparse dispatcher — entry point for `markets`
│   ├── add_ticker.py         # add subcommand handler
│   ├── remove_ticker.py      # remove subcommand handler
│   ├── list_watchlist.py     # list subcommand handler (read-only)
│   ├── show_ticker.py        # show subcommand handler (read-only)
│   └── _errors.py            # format_validation_error() for pretty CLI output
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # shared fixtures (tmp watchlist factory)
│   ├── test_schemas.py
│   ├── test_loader.py
│   ├── test_cli_add.py
│   ├── test_cli_remove.py
│   └── test_cli_readonly.py
├── watchlist.example.json    # 5 representative tickers; copy-and-edit pattern
├── pyproject.toml
└── README.md                 # documents copy-and-edit pattern + schema reference
```

**Why `analysts/schemas.py` rather than a top-level `schemas/` package:**
CONTEXT.md locks this. The rationale: downstream phases (`analysts/fundamentals.py`, etc.) will import `from analysts.schemas import AgentSignal`; co-locating watchlist schemas there avoids `from schemas.watchlist import TickerConfig` + `from schemas.signals import AgentSignal` duplication. The cost is mild conceptual confusion (why does the analyst package own watchlist schemas?). Worth it.

**Why `watchlist/` as a separate package, not co-located in `cli/`:**
The loader will be imported by Phase 2 ingestion code (`from watchlist.loader import load_watchlist`). Keeping it out of `cli/` avoids a circular import path through CLI argparse code.

### Pattern 1: Cross-Field Validation with `model_validator(mode="after")`

**What:** When two or more fields must satisfy a relational constraint, use `@model_validator(mode="after")`, not `@field_validator`. The "after" mode runs once all fields are validated and populated.

**When to use:**
- `TechnicalLevels`: `support < resistance` when both set
- `Watchlist`: `tickers[k].ticker == k` for every key

**Why not `@field_validator`:** Field validators run in field-declaration order. Accessing other fields via `ValidationInfo.data` is allowed but fragile — earlier-declared fields haven't been validated yet, later-declared fields aren't in `data` at all. `model_validator(mode="after")` sees the fully-validated model.

**Example:**
```python
# Source: https://docs.pydantic.dev/latest/concepts/validators/ (verified 2026-04-29)
from typing import Optional
from pydantic import BaseModel, model_validator

class TechnicalLevels(BaseModel):
    support: Optional[float] = None
    resistance: Optional[float] = None

    @model_validator(mode="after")
    def support_below_resistance(self) -> "TechnicalLevels":
        if self.support is not None and self.resistance is not None:
            if self.support >= self.resistance:
                raise ValueError(
                    f"support ({self.support}) must be less than resistance ({self.resistance})"
                )
        return self
```

For positivity-only checks on a single field (e.g., `thesis_price > 0`), use `@field_validator` — it's simpler:
```python
from pydantic import field_validator

@field_validator("thesis_price")
@classmethod
def positive_when_set(cls, v: Optional[float]) -> Optional[float]:
    if v is not None and v <= 0:
        raise ValueError("thesis_price must be positive")
    return v
```

### Pattern 2: Ticker Normalization in `@field_validator(mode="before")`

**What:** Run normalization (uppercase, separator swap) before type validation so the regex check sees canonical form.

**When to use:** Any field where user input is messy but downstream code wants canonical form.

**Example:**
```python
import re
from pydantic import BaseModel, field_validator

# yfinance uses hyphenated class-share notation (BRK-B); we normalize to that form.
_TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]{0,8}$")

class TickerConfig(BaseModel):
    ticker: str
    # ... other fields ...

    @field_validator("ticker", mode="before")
    @classmethod
    def normalize_ticker(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError(f"ticker must be a string, got {type(v).__name__}")
        # Strip whitespace, uppercase, swap class-share separators to hyphen
        normalized = v.strip().upper().replace(".", "-").replace("/", "-").replace("_", "-")
        # Collapse double-hyphens (paranoia)
        normalized = re.sub(r"-+", "-", normalized)
        if not _TICKER_PATTERN.match(normalized):
            raise ValueError(
                f"invalid ticker format: {v!r} (normalized to {normalized!r}); "
                f"expected pattern {_TICKER_PATTERN.pattern}"
            )
        return normalized
```

**Note on the pattern:** the existing CONTEXT.md regex `^[A-Z][A-Z0-9.]{0,8}$` excludes `-`. Update to `^[A-Z][A-Z0-9.\-]{0,8}$` to allow the hyphen. Or — since we normalize TO hyphen — only allow `^[A-Z][A-Z0-9\-]{0,8}$` post-normalization. Recommend: **allow hyphen and dot in the pattern** (simpler regex; only matters that the normalizer always produces hyphen).

### Pattern 3: Atomic File Write (Stdlib)

**What:** Write to a tmp file in the same directory as the target, then `os.replace` to swap. Atomic on POSIX (rename(2)) and Windows (MoveFileEx with REPLACE_EXISTING).

**When to use:** Every write to `watchlist.json`. Always.

**Why "same directory":** `os.replace` is only atomic when source and destination are on the same filesystem. A tmp file in `/tmp` (Linux) or `%TEMP%` (Windows) may be on a different volume — falls back to copy+delete (non-atomic).

**Why `delete=False` + manual close + replace:** Windows holds an exclusive lock on `NamedTemporaryFile` while it's open; `os.replace` over a locked file fails. Close the handle first, then replace.

**Example:**
```python
# Source: https://docs.python.org/3/library/tempfile.html + os.replace docs (verified 2026-04-29)
import json
import os
import tempfile
from pathlib import Path
from analysts.schemas import Watchlist

DEFAULT_PATH = Path("watchlist.json")

def save_watchlist(watchlist: Watchlist, path: Path = DEFAULT_PATH) -> None:
    """Atomic write — tmp file in same dir, then os.replace."""
    path = Path(path)
    parent = path.parent if path.parent != Path("") else Path(".")
    # Validate before persisting (defense-in-depth: catches caller passing a constructed but unvalidated model)
    Watchlist.model_validate(watchlist.model_dump())
    # mode="json" coerces datetime/Decimal to JSON-friendly types; sort_keys=True for deterministic output
    payload = json.dumps(watchlist.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    # delete=False so we can close the handle and rename; dir=parent so we're on the same filesystem
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
        dir=parent,
        prefix=path.name + ".",
        suffix=".tmp",
    ) as tmp:
        tmp.write(payload)
        tmp_path = Path(tmp.name)
    # Handle is closed; safe to rename on Windows
    try:
        os.replace(tmp_path, path)
    except OSError:
        tmp_path.unlink(missing_ok=True)
        raise
```

**Failure modes considered:**
- **Power loss during write:** Tmp file is partial; target is untouched. Recovery: orphan `.tmp` file remains; user/cleanup script can `rm`. No corruption of `watchlist.json`.
- **Ctrl-C during write:** Same as power loss; tmp file orphaned, target intact.
- **Concurrent CLI invocations:** Two `add` runs racing — last writer wins. Acceptable for single-user, near-zero collision probability. If this ever matters, add a `filelock` later.
- **Disk full:** `tmp.write()` raises `OSError`; we never call `os.replace`; target intact.
- **Permission error on rename:** Caught, tmp file cleaned up, error re-raised.

### Pattern 4: Pydantic ValidationError → CLI Display

**What:** `ValidationError.errors()` returns a list of dicts with `loc` (field path tuple), `msg`, `type`, `input`. Format the loc as a dot-separated path for human reading.

**Example:**
```python
# Source: https://docs.pydantic.dev/latest/errors/errors/ (verified 2026-04-29)
from pydantic import ValidationError

def format_validation_error(exc: ValidationError) -> str:
    """Render a ValidationError as multi-line CLI output."""
    lines = [f"validation failed ({exc.error_count()} error{'s' if exc.error_count() != 1 else ''}):"]
    for err in exc.errors(include_url=False):
        loc = ".".join(str(p) for p in err["loc"]) or "<root>"
        msg = err["msg"]
        # Optionally include the bad input value, but truncate long strings
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

`include_url=False` suppresses the "for further information visit https://errors.pydantic.dev/..." links — those are noise in CLI output for a single-user tool.

### Pattern 5: argparse Single Entry Point with Subcommands

**What:** One `markets` console script with subcommands `add`, `remove`, `list`, `show`. Cleaner than four standalone scripts; `pyproject.toml` declares one entry point.

**Why not separate scripts (`add_ticker.py`, `remove_ticker.py`):** CONTEXT.md mentions both styles. Separate scripts are simpler but four entry points in `pyproject.toml` clutter. A dispatcher is barely more code and gives uniform `--help`.

**Example:**
```python
# cli/main.py
# Source: https://docs.python.org/3/library/argparse.html#sub-commands (verified 2026-04-29)
import argparse
import sys
from pathlib import Path
from pydantic import ValidationError

from cli.add_ticker import add_command, build_add_parser
from cli.remove_ticker import remove_command, build_remove_parser
from cli.list_watchlist import list_command
from cli.show_ticker import show_command, build_show_parser
from cli._errors import format_validation_error

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="markets", description="watchlist management")
    sub = parser.add_subparsers(dest="cmd", required=True)
    build_add_parser(sub.add_parser("add", help="add a ticker"))
    build_remove_parser(sub.add_parser("remove", help="remove a ticker"))
    sub.add_parser("list", help="list all tickers")
    build_show_parser(sub.add_parser("show", help="show one ticker's full config"))
    return parser

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return {
            "add": add_command,
            "remove": remove_command,
            "list": list_command,
            "show": show_command,
        }[args.cmd](args)
    except ValidationError as e:
        print(format_validation_error(e), file=sys.stderr)
        return 2
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

`pyproject.toml`:
```toml
[project.scripts]
markets = "cli.main:main"
```

Invocation: `markets add AAPL --lens value --thesis 200 --support 175 --resistance 220`

**Sub-parser builder pattern** (per command):
```python
# cli/add_ticker.py
import argparse
from datetime import datetime, timezone
from pathlib import Path
from analysts.schemas import TickerConfig, TechnicalLevels, FundamentalTargets
from watchlist.loader import load_watchlist, save_watchlist

def build_add_parser(p: argparse.ArgumentParser) -> None:
    p.add_argument("ticker", help="ticker symbol (case-insensitive)")
    p.add_argument("--lens", choices=["value", "growth", "contrarian", "mixed"], default="mixed")
    p.add_argument("--no-short-term-focus", action="store_true")
    p.add_argument("--thesis", type=float, dest="thesis_price")
    p.add_argument("--support", type=float)
    p.add_argument("--resistance", type=float)
    p.add_argument("--pe-target", type=float)
    p.add_argument("--ps-target", type=float)
    p.add_argument("--pb-target", type=float)
    p.add_argument("--notes", default="")
    p.add_argument("--watchlist", type=Path, default=Path("watchlist.json"))
    p.add_argument("--yes", "-y", action="store_true", help="skip confirmation prompt")

def add_command(args: argparse.Namespace) -> int:
    # ... builds TickerConfig, loads existing watchlist, mutates dict, validates, saves ...
    pass
```

### Pattern 6: "Did You Mean" with `difflib.get_close_matches`

**What:** When a remove command can't find the ticker, suggest the closest existing ticker.

**Example:**
```python
# Source: https://docs.python.org/3/library/difflib.html (verified 2026-04-29)
import difflib

def suggest_ticker(unknown: str, known: list[str]) -> str | None:
    """Return the single closest match if any, else None."""
    matches = difflib.get_close_matches(unknown, known, n=1, cutoff=0.6)
    return matches[0] if matches else None

# Usage:
# unknown = "ABC"; known = list(watchlist.tickers.keys())
# match = suggest_ticker(unknown, known)
# if match:
#     print(f"error: ticker {unknown!r} not found. did you mean {match!r}?", file=sys.stderr)
```

**Cutoff selection:** stdlib default is 0.6. For 3-5 character tickers, 0.6 is generous (e.g., `ABC` vs `ABT` → 0.67). Recommend 0.6 for maximum helpfulness.

### Anti-Patterns to Avoid

- **`@field_validator` for cross-field rules.** Order-dependent; brittle. Use `@model_validator(mode="after")`.
- **Bare `path.write_text(...)`.** Not atomic; partial writes possible on Ctrl-C. Always tmp + replace.
- **Adding click/typer for a 4-subcommand CLI.** Extra dep for zero benefit at this size.
- **`model.model_dump_json(indent=2)` for the persisted file.** Doesn't sort keys (Pydantic v2 doesn't expose sort_keys yet — issue #7424). Git diffs become noisy when a `dict[str, TickerConfig]` is reordered. Use `json.dumps(..., sort_keys=True, indent=2)`.
- **Reading `watchlist.json` with `json.load` then constructing models.** Bypasses some Pydantic v2 fast-path. Use `Watchlist.model_validate_json(path.read_text())` directly.
- **Hardcoding the watchlist path in functions.** Pass it as a parameter (default `Path("watchlist.json")`); makes tmp_path-based testing trivial.
- **Letting argparse error to default stderr without exit code.** argparse already exits 2 on parse error. Match that for validation errors.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-field validation | Custom `__init__` checks | `@model_validator(mode="after")` | Pydantic accumulates errors, surfaces them via `ValidationError.errors()` with structured `loc` paths |
| JSON parsing with type coercion | `json.load` + manual type casts | `Watchlist.model_validate_json(text)` | Faster (Rust core path); error messages include field paths |
| Atomic file write | tmp file + `os.rename` (bare) | `tempfile.NamedTemporaryFile(dir=...) + os.replace` | `os.rename` won't overwrite existing files on Windows pre-3.3; `os.replace` is the cross-platform answer |
| Fuzzy ticker match | edit distance from scratch | `difflib.get_close_matches` | Stdlib; correct; default cutoff 0.6 is well-calibrated |
| ISO 8601 timestamp | string formatting | `datetime.now(timezone.utc).isoformat(timespec="seconds")` | Produces `2026-04-29T12:34:56+00:00`; if `Z` suffix preferred, replace `+00:00` → `Z` |
| Error path formatting | parse string repr of ValidationError | `exc.errors()` then `".".join(str(p) for p in err["loc"])` | Structured access; future-proof against Pydantic format changes |
| CLI subcommand dispatch | `if args.cmd == "add": ...` chain | `argparse.add_subparsers(dest="cmd")` + dict dispatch | Standard pattern; trivial to extend |

**Key insight:** Phase 1 is almost entirely "use stdlib + Pydantic correctly." There are no domain libraries to chase down. The only ecosystem question with downstream impact is the BRK-B vs BRK.B decision, and it's resolved.

## Common Pitfalls

### Pitfall 1: `model_dump_json(indent=2)` produces non-deterministic key order
**What goes wrong:** `Watchlist.tickers` is a `dict[str, TickerConfig]`. `model_dump_json` preserves insertion order. After several `add` operations, the dict order in the JSON file reflects insertion sequence, not lexicographic order. Git diffs are noisier than necessary; round-tripping `load → save` is not byte-identical if the user manually re-ordered keys in their editor.
**Why it happens:** Pydantic v2 doesn't yet expose `sort_keys` on `model_dump_json` (issue #7424 still open).
**How to avoid:** Use `json.dumps(model.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"`. The trailing newline is POSIX-friendly; sort_keys=True gives deterministic, alphabetic order at every level.
**Warning sign:** A no-op CLI run (`markets list` then nothing) followed by adding a ticker should produce a clean diff containing only the new entry — not a giant reorder.

### Pitfall 2: `os.replace` over a Windows-locked tmp file
**What goes wrong:** On Windows, `NamedTemporaryFile(delete=False)` may still hold an exclusive handle even after the `with` block exits if the file was opened with default mode. `os.replace` then fails with `PermissionError`.
**Why it happens:** Windows file-locking semantics differ from POSIX. The handle must be fully closed before any other process (including the same process) can rename over it.
**How to avoid:** Use `with tempfile.NamedTemporaryFile(...) as tmp:` to auto-close; capture `tmp.name` inside the block; call `os.replace` outside the `with` block.
**Warning sign:** Tests pass on macOS/Linux but `PermissionError` on Windows. Always test on Windows for this phase (it's locked as the dev OS for this user).

### Pitfall 3: ISO 8601 round-trip with `Z` suffix
**What goes wrong:** Python's `datetime.fromisoformat()` couldn't parse the `Z` suffix until Python 3.11. The user is on 3.12 so this is fine, but if a CONTEXT.md decision specifies "Z suffix" and someone uses `datetime.now(timezone.utc).isoformat()` (which produces `+00:00`, not `Z`), strings differ across CLI invocations and round-trip breaks.
**How to avoid:** Standardize on `+00:00` (default `isoformat()` output) OR explicitly `.replace("+00:00", "Z")` and decode with `dateutil.parser.isoparse` or Python 3.11+ `fromisoformat`. Recommend default `+00:00` form for simplicity — Python parses it natively, JSON consumers don't care.
**Warning sign:** A test that loads-then-saves and asserts byte-identical content fails on the timestamp field.

### Pitfall 4: `dict[str, TickerConfig]` validation expects str keys, not casefold-normalized
**What goes wrong:** User edits `watchlist.json` to add `"aapl": {"ticker": "AAPL", ...}`. The TickerConfig validates fine (`ticker` field is normalized). But the dict key remains `"aapl"`, and our `model_validator` rule "key == value.ticker" fails — or worse, succeeds if we forgot to normalize keys too.
**How to avoid:** In `Watchlist.@model_validator(mode="after")`, rebuild the dict with normalized keys:
```python
@model_validator(mode="after")
def keys_match_tickers(self) -> "Watchlist":
    fixed: dict[str, TickerConfig] = {}
    for k, v in self.tickers.items():
        if k != v.ticker:
            # key was raw user input; canonicalize
            fixed[v.ticker] = v
        else:
            fixed[k] = v
    self.tickers = fixed
    return self
```
Or strict-mode: raise on mismatch and force the user to fix manually.
**Recommendation:** **Strict mode** — raise on mismatch with a clear message ("watchlist key 'aapl' does not match ticker 'AAPL'; please fix manually or use the CLI"). The CLI never produces mismatches (it normalizes before insertion); only manual edits do, and silent rewrite hides typos.
**Warning sign:** A round-trip test where a user-edited file with `"aapl"` keys persists with `"AAPL"` keys without warning.

### Pitfall 5: Pydantic validation does not run on direct attribute assignment by default
**What goes wrong:** After `wl = load_watchlist()`, code does `wl.tickers["AAPL"].thesis_price = -100`. No validation. The negative price is now in memory and gets persisted.
**Why it happens:** Pydantic v2 model instances are mutable by default; mutation skips validators unless `model_config = ConfigDict(validate_assignment=True)`.
**How to avoid:** Two-pronged defense: (1) `model_config = ConfigDict(validate_assignment=True)` on TickerConfig, TechnicalLevels, FundamentalTargets, Watchlist — small perf cost, big safety. (2) The CLI rebuilds the model from a dict via `model_validate` rather than mutating. Even with validate_assignment off, this catches bad data before persist.
**Warning sign:** A bug where a CLI accepts `--thesis -100` because the field type is `Optional[float]` but the validator only fires at construction; mutation slips through.

### Pitfall 6: Phase 2 will be sad if BRK-B / BRK.B is wrong
**What goes wrong:** See "Critical Correction Needed" above. yfinance returns empty data for `BRK.B`; correct ticker is `BRK-B`.
**How to avoid:** Normalize to hyphen, document why in the validator inline comment.
**Warning sign:** Phase 2 implementation flags "Berkshire returning empty data" — too late, the schema is set.

### Pitfall 7: pytest `tmp_path` and the `cwd`-relative default `Path("watchlist.json")`
**What goes wrong:** Code defaults to `Path("watchlist.json")` (cwd-relative). Tests using `tmp_path` create the watchlist there but the code under test reads cwd-relative — mismatch.
**How to avoid:** Always pass the path explicitly into loader functions; never read cwd inside the loader. The default path is only resolved at the CLI argparse layer.
**Warning sign:** Tests pollute the repo root with `watchlist.json` files.

## Code Examples

Verified patterns ready for the planner to adapt.

### Full TickerConfig schema with all locked rules

```python
# analysts/schemas.py
# Source: synthesized from CONTEXT.md decisions + https://docs.pydantic.dev/latest/concepts/validators/
from typing import Literal, Optional
import re
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# yfinance uses hyphenated class-share notation (BRK-B, RDS-A). We normalize to that form
# for downstream Phase 2 yfinance compatibility.
_TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]{0,8}$")

class TechnicalLevels(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="forbid")
    support: Optional[float] = None
    resistance: Optional[float] = None

    @field_validator("support", "resistance")
    @classmethod
    def positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("must be positive")
        return v

    @model_validator(mode="after")
    def support_below_resistance(self) -> "TechnicalLevels":
        if self.support is not None and self.resistance is not None:
            if self.support >= self.resistance:
                raise ValueError(
                    f"support ({self.support}) must be less than resistance ({self.resistance})"
                )
        return self


class FundamentalTargets(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="forbid")
    pe_target: Optional[float] = None
    ps_target: Optional[float] = None
    pb_target: Optional[float] = None

    @field_validator("pe_target", "ps_target", "pb_target")
    @classmethod
    def positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("must be positive")
        return v


class TickerConfig(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="forbid")
    ticker: str
    short_term_focus: bool = True
    long_term_lens: Literal["value", "growth", "contrarian", "mixed"] = "mixed"
    thesis_price: Optional[float] = None
    technical_levels: Optional[TechnicalLevels] = None
    target_multiples: Optional[FundamentalTargets] = None
    notes: str = Field(default="", max_length=1000)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @field_validator("ticker", mode="before")
    @classmethod
    def normalize_ticker(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError(f"ticker must be a string, got {type(v).__name__}")
        normalized = (
            v.strip().upper()
            .replace(".", "-").replace("/", "-").replace("_", "-")
        )
        normalized = re.sub(r"-+", "-", normalized)
        if not _TICKER_PATTERN.match(normalized):
            raise ValueError(
                f"invalid ticker format {v!r}; expected pattern {_TICKER_PATTERN.pattern}"
            )
        return normalized

    @field_validator("thesis_price")
    @classmethod
    def thesis_price_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("thesis_price must be positive")
        return v


class Watchlist(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="forbid")
    version: int = 1
    tickers: dict[str, TickerConfig] = Field(default_factory=dict)

    @model_validator(mode="after")
    def keys_match_tickers(self) -> "Watchlist":
        for k, v in self.tickers.items():
            if k != v.ticker:
                raise ValueError(
                    f"watchlist key {k!r} does not match its ticker field {v.ticker!r} "
                    f"(after normalization). Use the CLI or fix manually."
                )
        return self
```

### Loader / atomic save

```python
# watchlist/loader.py
import json
import os
import tempfile
from pathlib import Path
from analysts.schemas import Watchlist

DEFAULT_PATH = Path("watchlist.json")

def load_watchlist(path: Path = DEFAULT_PATH) -> Watchlist:
    """Load and validate. Returns empty Watchlist if file does not exist."""
    path = Path(path)
    if not path.exists():
        return Watchlist()
    return Watchlist.model_validate_json(path.read_text(encoding="utf-8"))

def save_watchlist(watchlist: Watchlist, path: Path = DEFAULT_PATH) -> None:
    """Atomic write to path. Re-validates before persisting."""
    path = Path(path)
    parent = path.parent if str(path.parent) else Path(".")
    Watchlist.model_validate(watchlist.model_dump())  # defense-in-depth
    payload = json.dumps(watchlist.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
        dir=parent,
        prefix=path.name + ".",
        suffix=".tmp",
    ) as tmp:
        tmp.write(payload)
        tmp_path = Path(tmp.name)
    try:
        os.replace(tmp_path, path)
    except OSError:
        tmp_path.unlink(missing_ok=True)
        raise
```

### CLI add command (illustrative skeleton)

```python
# cli/add_ticker.py
import argparse
from datetime import datetime, timezone
from pathlib import Path
from analysts.schemas import TickerConfig, TechnicalLevels, FundamentalTargets
from watchlist.loader import load_watchlist, save_watchlist

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def build_add_parser(p: argparse.ArgumentParser) -> None:
    p.add_argument("ticker")
    p.add_argument("--lens", choices=["value", "growth", "contrarian", "mixed"], default="mixed")
    p.add_argument("--no-short-term-focus", action="store_true")
    p.add_argument("--thesis", type=float, dest="thesis_price")
    p.add_argument("--support", type=float)
    p.add_argument("--resistance", type=float)
    p.add_argument("--pe-target", type=float)
    p.add_argument("--ps-target", type=float)
    p.add_argument("--pb-target", type=float)
    p.add_argument("--notes", default="")
    p.add_argument("--watchlist", type=Path, default=Path("watchlist.json"))

def add_command(args: argparse.Namespace) -> int:
    wl = load_watchlist(args.watchlist)
    tech = None
    if args.support is not None or args.resistance is not None:
        tech = TechnicalLevels(support=args.support, resistance=args.resistance)
    fund = None
    if any(getattr(args, f) is not None for f in ("pe_target", "ps_target", "pb_target")):
        fund = FundamentalTargets(
            pe_target=args.pe_target,
            ps_target=args.ps_target,
            pb_target=args.pb_target,
        )
    now = _now_iso()
    cfg = TickerConfig(
        ticker=args.ticker,
        short_term_focus=not args.no_short_term_focus,
        long_term_lens=args.lens,
        thesis_price=args.thesis_price,
        technical_levels=tech,
        target_multiples=fund,
        notes=args.notes,
        created_at=now,
        updated_at=now,
    )
    if cfg.ticker in wl.tickers:
        print(f"error: ticker {cfg.ticker!r} already exists. use 'remove' first if you want to replace.")
        return 1
    new_tickers = dict(wl.tickers)
    new_tickers[cfg.ticker] = cfg
    new_wl = wl.model_copy(update={"tickers": new_tickers})
    save_watchlist(new_wl, args.watchlist)
    print(f"added {cfg.ticker} ({cfg.long_term_lens})")
    return 0
```

### CLI remove with "did you mean"

```python
# cli/remove_ticker.py
import argparse
import difflib
from pathlib import Path
from datetime import datetime, timezone
from watchlist.loader import load_watchlist, save_watchlist

def build_remove_parser(p: argparse.ArgumentParser) -> None:
    p.add_argument("ticker")
    p.add_argument("--watchlist", type=Path, default=Path("watchlist.json"))
    p.add_argument("--yes", "-y", action="store_true")

def remove_command(args: argparse.Namespace) -> int:
    wl = load_watchlist(args.watchlist)
    # Normalize the input through the same path the schema uses
    from analysts.schemas import TickerConfig
    try:
        normalized = TickerConfig.normalize_ticker(args.ticker)  # type: ignore[arg-type]
    except ValueError as e:
        print(f"error: {e}")
        return 2
    if normalized not in wl.tickers:
        suggestion = difflib.get_close_matches(normalized, list(wl.tickers.keys()), n=1, cutoff=0.6)
        msg = f"error: ticker {normalized!r} not in watchlist."
        if suggestion:
            msg += f" did you mean {suggestion[0]!r}?"
        print(msg)
        return 1
    if not args.yes:
        ans = input(f"remove {normalized}? [y/N] ").strip().lower()
        if ans not in ("y", "yes"):
            print("aborted")
            return 0
    new_tickers = {k: v for k, v in wl.tickers.items() if k != normalized}
    new_wl = wl.model_copy(update={"tickers": new_tickers})
    save_watchlist(new_wl, args.watchlist)
    print(f"removed {normalized}")
    return 0
```

### pyproject.toml (minimum for this phase)

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

**Note on the `[build-system]`:** required for `[project.scripts]` to actually create the `markets` console executable. `hatchling` is the most-vanilla PEP 517 backend and is what `uv init` defaults to in 2026.

### conftest.py / pytest fixtures

```python
# tests/conftest.py
import json
from pathlib import Path
import pytest
from analysts.schemas import Watchlist, TickerConfig, TechnicalLevels, FundamentalTargets

@pytest.fixture
def empty_watchlist_path(tmp_path: Path) -> Path:
    """Returns a path to a non-existent watchlist file in a tmp directory."""
    return tmp_path / "watchlist.json"

@pytest.fixture
def seeded_watchlist_path(tmp_path: Path) -> Path:
    """Returns a path to a 3-ticker watchlist file in a tmp directory."""
    path = tmp_path / "watchlist.json"
    wl = Watchlist(
        tickers={
            "AAPL": TickerConfig(ticker="AAPL", long_term_lens="value", thesis_price=200.0),
            "NVDA": TickerConfig(ticker="NVDA", long_term_lens="growth"),
            "BRK-B": TickerConfig(ticker="BRK-B", long_term_lens="value"),
        }
    )
    path.write_text(json.dumps(wl.model_dump(mode="json"), indent=2, sort_keys=True) + "\n")
    return path

@pytest.fixture
def large_watchlist_path(tmp_path: Path) -> Path:
    """30+ tickers for WATCH-01 verification."""
    path = tmp_path / "watchlist.json"
    sample = ["AAPL","MSFT","NVDA","GOOG","AMZN","META","TSLA","BRK-B","JPM","V",
              "XOM","UNH","JNJ","PG","HD","MA","CVX","ABBV","KO","PFE",
              "PEP","WMT","BAC","TMO","COST","DIS","CRM","ORCL","NKE","ADBE",
              "AMD","NFLX","INTC","CSCO","QCOM"]
    wl = Watchlist(tickers={t: TickerConfig(ticker=t) for t in sample})
    path.write_text(json.dumps(wl.model_dump(mode="json"), indent=2, sort_keys=True) + "\n")
    return path
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic v1 `@validator` (single-field) + `@root_validator` (whole-model) | Pydantic v2 `@field_validator` + `@model_validator(mode="before"|"after")` | Pydantic 2.0 (Jun 2023) | All examples in this doc use v2; v1 idioms will not work |
| `tempfile.NamedTemporaryFile` workarounds for Windows file locking | `delete=False` is canonical; `delete_on_close=False` (Py 3.12+) for cleaner ergonomics | Python 3.12 (Oct 2023) | We're on 3.12 — can use either pattern; `delete=False` + manual close is clearest |
| `requirements.txt` + `pip-tools` | `pyproject.toml` + `uv` (or `poetry`) | uv 1.0 GA (early 2025) | Locked in `.planning/research/STACK.md`; this phase uses uv exclusively |
| `pip install -e .` for local editable | `uv pip install -e .` or `uv sync --dev` (auto-installs editable in newer uv) | uv evolved through 2025 | If `markets` console script doesn't appear after `uv sync`, run `uv pip install -e .` once |
| `python -m mymodule` | `[project.scripts]` console script | PEP 621 (Nov 2020) widely adopted | Both work; we standardize on `markets` console script for one consistent invocation surface |

**Deprecated/outdated:**
- Pydantic v1 — do not reach for `BaseModel.dict()` (use `model_dump()`), `parse_obj` (use `model_validate`), or `Config` inner class (use `model_config = ConfigDict(...)`)
- `os.rename` for cross-platform atomic — `os.replace` is the right call (3.3+)

## Open Questions

1. **Should `created_at`/`updated_at` use `Z` suffix or `+00:00`?**
   - What we know: Both are valid ISO 8601. `+00:00` is what `datetime.isoformat()` produces by default. `Z` is more compact and JS-friendly.
   - What's unclear: User preference; CONTEXT.md says "recommended `Z`" but lists it as Claude's discretion.
   - Recommendation: **Default `+00:00`** (no string surgery, parsable by stdlib `fromisoformat` on 3.11+). Document the choice in a `# format note` at the top of `cli/_time.py`. Cost of switching later is trivial.

2. **Should `extra="forbid"` be set on schemas?**
   - What we know: `extra="forbid"` rejects unknown fields at validation time — catches typos in the watchlist file (`"long_term_lens"` vs `"long_term_lense"`).
   - What's unclear: It also makes future-version migrations harder (a v2 watchlist with new fields would fail to load in v1 code).
   - Recommendation: **Set `extra="forbid"`** for v1. Schema migrations are explicitly deferred per CONTEXT.md ("bump `version` field manually if we ever break schema") — `forbid` is the right strict default. If we ever break the schema, the `version` field gives us a branch point.

3. **Is `analysts/` the right home for `schemas.py`?**
   - What we know: CONTEXT.md locks this. `analysts.schemas` will eventually hold AgentSignal, TickerDecision, etc.
   - What's unclear: Some readers will be confused why `Watchlist` lives in an "analysts" package.
   - Recommendation: **Honor CONTEXT.md.** Add a docstring at the top of `analysts/schemas.py` explaining: "this module holds project-wide Pydantic schemas; the `analysts` namespace is historic — it's the first package that needed shared schemas. Future schemas (signals, decisions) join this module."

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-cov 5.x |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (no separate pytest.ini) |
| Quick run command | `uv run pytest tests/test_schemas.py -x` |
| Full suite command | `uv run pytest --cov=analysts --cov=watchlist --cov=cli --cov-fail-under=90` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WATCH-01 | A `watchlist.json` with 30+ tickers loads and validates | unit | `uv run pytest tests/test_loader.py::test_load_30_ticker_watchlist -x` | ❌ Wave 0 (`tests/test_loader.py`) |
| WATCH-01 | Validation completes in < 100ms for 50 tickers (perf sanity) | unit | `uv run pytest tests/test_loader.py::test_load_50_tickers_under_100ms -x` | ❌ Wave 0 |
| WATCH-02 | `markets add AAPL --lens value` produces a valid file with AAPL | integration | `uv run pytest tests/test_cli_add.py::test_add_happy_path -x` | ❌ Wave 0 (`tests/test_cli_add.py`) |
| WATCH-02 | `markets add AAPL` then `markets add AAPL` rejects with non-zero exit | integration | `uv run pytest tests/test_cli_add.py::test_add_duplicate_rejected -x` | ❌ Wave 0 |
| WATCH-02 | `markets add aapl` (lowercase) normalizes to AAPL key | integration | `uv run pytest tests/test_cli_add.py::test_add_normalizes_case -x` | ❌ Wave 0 |
| WATCH-02 | `markets add BRK.B` normalizes to `BRK-B` (yfinance compat) | integration | `uv run pytest tests/test_cli_add.py::test_add_brk_normalizes_to_hyphen -x` | ❌ Wave 0 |
| WATCH-02 | Atomic write — Ctrl-C simulation leaves either old or new state, never partial | unit | `uv run pytest tests/test_loader.py::test_atomic_save_no_partial -x` | ❌ Wave 0 |
| WATCH-03 | `markets remove AAPL` removes ticker from file | integration | `uv run pytest tests/test_cli_remove.py::test_remove_happy_path -x` | ❌ Wave 0 (`tests/test_cli_remove.py`) |
| WATCH-03 | `markets remove ABT` (typo for ABC present) suggests ABC | integration | `uv run pytest tests/test_cli_remove.py::test_remove_suggests_close_match -x` | ❌ Wave 0 |
| WATCH-03 | `markets remove XYZ` (no close match) errors cleanly without suggestion | integration | `uv run pytest tests/test_cli_remove.py::test_remove_no_match_no_suggestion -x` | ❌ Wave 0 |
| WATCH-04 | All TickerConfig fields settable via CLI flags | integration | `uv run pytest tests/test_cli_add.py::test_add_all_flags -x` | ❌ Wave 0 |
| WATCH-04 | `long_term_lens` enforces Literal choices | unit | `uv run pytest tests/test_schemas.py::test_long_term_lens_enum -x` | ❌ Wave 0 (`tests/test_schemas.py`) |
| WATCH-04 | `technical_levels.support < resistance` enforced | unit | `uv run pytest tests/test_schemas.py::test_support_below_resistance -x` | ❌ Wave 0 |
| WATCH-04 | `target_multiples.*_target > 0` enforced | unit | `uv run pytest tests/test_schemas.py::test_target_multiples_positive -x` | ❌ Wave 0 |
| WATCH-04 | `notes` length capped at 1000 chars | unit | `uv run pytest tests/test_schemas.py::test_notes_max_length -x` | ❌ Wave 0 |
| WATCH-05 | Invalid JSON (malformed syntax) → clear error path | unit | `uv run pytest tests/test_loader.py::test_malformed_json_raises -x` | ❌ Wave 0 |
| WATCH-05 | `thesis_price = -1` → ValidationError with `thesis_price` in `loc` | unit | `uv run pytest tests/test_schemas.py::test_thesis_price_negative_rejected -x` | ❌ Wave 0 |
| WATCH-05 | `support = resistance` → ValidationError mentioning support and resistance | unit | `uv run pytest tests/test_schemas.py::test_support_equals_resistance_rejected -x` | ❌ Wave 0 |
| WATCH-05 | watchlist key mismatch → ValidationError naming the offending key | unit | `uv run pytest tests/test_schemas.py::test_watchlist_key_mismatch -x` | ❌ Wave 0 |
| WATCH-05 | `format_validation_error` produces multi-line string with field paths | unit | `uv run pytest tests/test_cli_errors.py::test_format_validation_error -x` | ❌ Wave 0 (`tests/test_cli_errors.py`) |
| WATCH-05 | Round-trip: load → save → load is byte-identical for unchanged data | unit | `uv run pytest tests/test_loader.py::test_round_trip_byte_identical -x` | ❌ Wave 0 |

**Note on the 30+ ticker test (WATCH-01):** The test creates a synthetic 35-ticker fixture (see `tests/conftest.py::large_watchlist_path` above) and verifies load + validation. No user-provided fixture needed; this is a property of the schema, not of any specific ticker list.

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_schemas.py tests/test_loader.py -x` (Wave 1 + Wave 2 fast tests, ≤ 2 seconds)
- **Per wave merge:** `uv run pytest -x` (all tests including CLI integration; ≤ 10 seconds)
- **Phase gate:** `uv run pytest --cov=analysts --cov=watchlist --cov=cli --cov-fail-under=90` (full suite + coverage gate; required green before `/gmd:verify-work`)

### Wave 0 Gaps

All test files are gaps (project is bare); install + scaffold list:

- [ ] `pyproject.toml` — including `[project.scripts]`, `[build-system]`, `[tool.pytest.ini_options]`, `[tool.coverage.run]` (see Code Examples)
- [ ] `tests/__init__.py` — empty
- [ ] `tests/conftest.py` — shared fixtures (`empty_watchlist_path`, `seeded_watchlist_path`, `large_watchlist_path`)
- [ ] `tests/test_schemas.py` — covers WATCH-04, WATCH-05 (schema-level rules)
- [ ] `tests/test_loader.py` — covers WATCH-01, WATCH-05 (file I/O + round-trip)
- [ ] `tests/test_cli_add.py` — covers WATCH-02
- [ ] `tests/test_cli_remove.py` — covers WATCH-03
- [ ] `tests/test_cli_readonly.py` — covers `list`, `show` subcommands (Claude's discretion; covers QoL behavior)
- [ ] `tests/test_cli_errors.py` — covers `format_validation_error` formatting
- [ ] Framework install: `uv add 'pydantic>=2.10'` and `uv add --dev 'pytest>=8.0' 'pytest-cov>=5.0' 'ruff>=0.6'`

## Recommended Wave Structure

The planner should structure Phase 1 as **three serial waves with parallelism inside each wave**.

### Wave 0 — Project scaffold (1 task)
- Initialize `pyproject.toml`, install deps, create empty package skeletons (`analysts/`, `watchlist/`, `cli/`, `tests/`) with `__init__.py` files
- Add `[project.scripts] markets = "cli.main:main"` and a placeholder `cli/main.py` that prints "not yet implemented"
- Verify `uv sync` + `uv run pytest --collect-only` runs cleanly with zero tests

### Wave 1 — Schemas (parallel) — 2-3 tasks
All tasks here touch only `analysts/schemas.py` and `tests/test_schemas.py` — they can land in any order or in parallel. Recommendation: keep as ONE task because all schemas are in one file (~150 lines) and conflicts are guaranteed if split.
- Task 1.1: `analysts/schemas.py` with all four models (TechnicalLevels, FundamentalTargets, TickerConfig, Watchlist), all validators (field + model), inline yfinance-compat comment
- Task 1.2: `tests/test_schemas.py` — every cross-field rule has a positive + negative test; ticker normalization has fixture cases for `AAPL`, `aapl`, `BRK.B`, `BRK-B`, `BRK/B`, `^GSPC` (rejected), `EURUSD=X` (rejected), `TOOLONGTICKER` (rejected), `1AAPL` (rejected: starts with digit)
- Task 1.3 (optional, parallel): `tests/conftest.py` shared fixtures

**Wave 1 gate:** `uv run pytest tests/test_schemas.py -x` green; coverage on `analysts/schemas.py` ≥ 95%

### Wave 2 — Loader + atomic I/O (1-2 tasks)
- Task 2.1: `watchlist/loader.py` (`load_watchlist`, `save_watchlist`)
- Task 2.2: `tests/test_loader.py` — round-trip, malformed JSON, atomic-save sanity (write then verify file contents), 30+ ticker load
- Both tasks depend on Wave 1; can be parallel within Wave 2 (different files, no overlap)

**Wave 2 gate:** `uv run pytest tests/test_schemas.py tests/test_loader.py -x` green; round-trip byte-identical test passes

### Wave 3 — CLI + error formatting (parallel) — 4-5 tasks
- Task 3.1: `cli/main.py` (dispatcher) + `cli/_errors.py` (`format_validation_error`)
- Task 3.2: `cli/add_ticker.py` + `tests/test_cli_add.py`
- Task 3.3: `cli/remove_ticker.py` + `tests/test_cli_remove.py`
- Task 3.4: `cli/list_watchlist.py` + `cli/show_ticker.py` + `tests/test_cli_readonly.py` (Claude's discretion deliverables)
- Task 3.5: `watchlist.example.json` + minimal README section documenting copy-and-edit pattern

These can all execute in parallel — they touch disjoint files. Task 3.1 has no dependencies in this wave; tasks 3.2-3.4 depend logically on 3.1 (the dispatcher) but each provides its own subparser builder, so no merge conflict.

**Wave 3 gate:** Full suite `uv run pytest --cov=... --cov-fail-under=90` green; manual smoke test: `uv run markets add AAPL --lens value --thesis 200`, `uv run markets list`, `uv run markets show AAPL`, `uv run markets remove AAPL`.

### Why this structure
- **Schemas first:** Every other task depends on the schema being correct. Ship and stabilize before building consumers.
- **Loader second:** CLI commands need a working loader; loader doesn't need a CLI.
- **CLI parallel:** Four subcommands are independent surface area. Maximizes parallelism with zero merge risk.
- **Three serial waves match the natural data flow** (data → I/O → UX) and keep verification gates tight (each wave has a fast pytest gate).

## Sources

### Primary (HIGH confidence)
- [Pydantic v2 — Validators](https://docs.pydantic.dev/latest/concepts/validators/) — `field_validator` vs `model_validator` semantics, mode options
- [Pydantic v2 — Errors](https://docs.pydantic.dev/latest/errors/errors/) — `ValidationError.errors()` shape, `include_url` flag
- [Pydantic v2 — Fields](https://docs.pydantic.dev/latest/concepts/fields/) — Optional default semantics in v2 (no implicit None)
- [Pydantic v2 — Performance](https://docs.pydantic.dev/latest/concepts/performance/) — TypeAdapter, dict validation guidance
- [Python docs — tempfile](https://docs.python.org/3/library/tempfile.html) — `NamedTemporaryFile` `delete=False`, `delete_on_close` (3.12+), Windows considerations
- [Python docs — os.replace](https://docs.python.org/3/library/os.html#os.replace) — atomic on POSIX + Windows MoveFileEx
- [Python docs — difflib](https://docs.python.org/3/library/difflib.html) — `get_close_matches`, default cutoff 0.6
- [Python docs — argparse subcommands](https://docs.python.org/3/library/argparse.html#sub-commands)
- [uv — Configuring projects](https://docs.astral.sh/uv/concepts/projects/config/) — `[project.scripts]` requires PEP 517 `[build-system]`
- [Yahoo Finance — BRK-B canonical URL](https://finance.yahoo.com/quote/BRK-B/) — confirms hyphenated form
- [yfinance README on PyPI](https://pypi.org/project/yfinance/) — examples use hyphenated tickers

### Secondary (MEDIUM confidence)
- [GitHub issue 7424 — Pydantic v2 model_dump_json sort_keys](https://github.com/pydantic/pydantic/issues/7424) — confirms feature still pending
- [Issue 14243 / GitHub 58451 — Windows NamedTemporaryFile usefulness](https://github.com/python/cpython/issues/58451) — explains why `delete=False` pattern is canonical on Windows
- [pytest tmp_path docs](https://docs.pytest.org/en/stable/how-to/tmp_path.html) — fixture semantics, `tmp_path_factory` for session scope
- [GitHub issue 1764 OpenBB — ticker symbol differences IEX vs yfinance](https://github.com/OpenBB-finance/OpenBB/issues/1764) — corroborates yfinance hyphen / IEX dot split

### Tertiary (LOW confidence — flagged but verified at higher tier)
- (none — every claim traces to primary or multiple secondary sources)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Pydantic v2 + stdlib are well-documented and battle-tested; no library-version risk
- Architecture: HIGH — patterns are stdlib-canonical; only judgment calls are layout (already largely fixed by CONTEXT.md)
- Pitfalls: HIGH — six of seven pitfalls have direct documentation/issue trail; #6 (yfinance ticker format) is verified across multiple primary sources
- Validation Architecture: HIGH — pytest tmp_path + small synthetic fixtures cover everything; no manual-only probes for this phase

**Research date:** 2026-04-29
**Valid until:** 2026-07-29 (~90 days; Pydantic v2 minor releases unlikely to break documented APIs; Python 3.12 stable)

---
*Phase: 01-foundation-watchlist-per-ticker-config*
*Research file: 01-RESEARCH.md*
