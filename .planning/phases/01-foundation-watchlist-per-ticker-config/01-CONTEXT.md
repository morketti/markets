# Phase 1: Foundation — Watchlist + Per-Ticker Config — Context

**Gathered:** 2026-04-30
**Status:** Ready for planning
**Source:** Synthesized from prior `/gmd:new-project` conversation + `.planning/PROJECT.md` Key Decisions + `.planning/research/ARCHITECTURE.md` AgentState section. No separate `/gmd:discuss-phase` run — design context for this phase was locked through the new-project flow and is durable across the project artifacts.

> **CORRECTIONS FROM RESEARCH (2026-04-30 — see `01-RESEARCH.md`):**
> Phase research surfaced three factual corrections to locked decisions below. The planner MUST follow research where it conflicts with this document:
> 1. **Ticker normalization → HYPHEN, not dot.** yfinance uses `BRK-B`; the dotted form returns empty data and silently triggers `data_unavailable` in Phase 2. Accept `.`, `/`, `_`, `-` as input separators; normalize to hyphen. Regex: `^[A-Z][A-Z0-9-]{0,8}$`.
> 2. **Cross-field validators → use `@model_validator(mode="after")`, not `@field_validator`.** `field_validator` runs in declaration order with partial state (`ValidationInfo.data`); cross-field rules need a fully-validated model. Single-field rules (e.g., `thesis_price > 0`) can stay as `@field_validator`.
> 3. **JSON serialization → `json.dumps(model.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"`, NOT `model_dump_json(indent=2)`.** Pydantic v2 doesn't sort dict keys (issue #7424); without `sort_keys` the watchlist file's git diffs are noisy after every mutation.

<domain>
## Phase Boundary

This phase delivers ONE thing: a `watchlist.json` source-of-truth file with rich per-ticker configuration, plus CLI utilities to maintain it. Nothing else.

**Out of phase boundary** (these come later):
- Any data ingestion — Phase 2
- Any analytical scoring — Phase 3
- Position-Adjustment Radar — Phase 4
- Claude routine wiring / persona prompts — Phase 5
- Any frontend rendering — Phase 6

The deliverable is a self-contained Python package + CLI that the user can run to add/remove tickers and validate config. After this phase, `watchlist.json` is authoritative and consumable by downstream phases without further coordination.

</domain>

<decisions>
## Implementation Decisions

### Source of Truth

- Watchlist lives at repo root: `watchlist.json` (NOT in `data/`, which is for daily snapshots)
- **JSON format** (not YAML, not TOML) — git diffs are clean, the frontend will zod-validate the same shape in Phase 6
- Pydantic v2 is the schema-of-record. Pydantic models for shared types (`TickerConfig`, `TechnicalLevels`, `FundamentalTargets`, `Watchlist`) live in `analysts/schemas.py` so they're importable from any later-phase package without circular dependencies

### TickerConfig Schema (LOCKED)

```python
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

class TechnicalLevels(BaseModel):
    support: Optional[float] = None
    resistance: Optional[float] = None
    # field_validator: when both set, support < resistance

class FundamentalTargets(BaseModel):
    pe_target: Optional[float] = None
    ps_target: Optional[float] = None
    pb_target: Optional[float] = None
    # field_validators: when set, value > 0

class TickerConfig(BaseModel):
    ticker: str
    short_term_focus: bool = True
    long_term_lens: Literal["value", "growth", "contrarian", "mixed"] = "mixed"
    thesis_price: Optional[float] = None
    technical_levels: Optional[TechnicalLevels] = None
    target_multiples: Optional[FundamentalTargets] = None
    notes: str = ""
    created_at: Optional[str] = None  # ISO 8601 — set by add CLI
    updated_at: Optional[str] = None  # ISO 8601 — touched on any change

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, v: str) -> str:
        # uppercase, normalize BRK-B / BRK/B → BRK.B
        # validate ^[A-Z][A-Z0-9.]{0,8}$ (allows class shares, ETFs, indexes)
        ...

class Watchlist(BaseModel):
    version: int = 1
    tickers: dict[str, TickerConfig]  # keyed by symbol for O(1) lookup
    # field_validator: each value.ticker == its key (case-corrected)
```

### CLI Utilities

- `cli/add_ticker.py` — argparse-based; positional `ticker`, optional flags for each TickerConfig field
- `cli/remove_ticker.py` — argparse-based; positional `ticker`; refuses if ticker not present (with Levenshtein-suggestion if close match exists)
- Both write **atomically**: write to `watchlist.json.tmp` then `os.replace()` — no partial corruption on Ctrl-C / crash
- Both validate the full Watchlist after mutation before persisting; reject with actionable Pydantic errors if invalid
- Both `touch` the `updated_at` of changed entries (and set `created_at` on new entries)

### Validation Behavior

- Loading `watchlist.json`: `Watchlist.model_validate_json(text)`. On failure, surface the full error path so the user can fix it manually
- Cross-field rules enforced at schema level (Pydantic `field_validator` + `model_validator`), not in the CLI — schema is single source of truth
- The CLI is a thin wrapper around schema validation + persistence

### Provenance

- This phase has **no direct adaptation** from `virattt/ai-hedge-fund` or `TauricResearch/TradingAgents` (neither has a persistent watchlist abstraction — both pass tickers as CLI args per run)
- No header comments needed in this phase's files
- Inline note acceptable where relevant: `# (virattt passes tickers per-run; we persist a richer per-ticker config)`

### Claude's Discretion

- Specific Python package layout within `markets/` — recommendation: `watchlist/` package with `models.py` re-exporting from `analysts.schemas`, `loader.py`, `cli/` for the utilities
- Whether to ship a `watchlist.example.json` with 3-5 example tickers for new-user onboarding (recommended: yes)
- Exact wording of error messages
- Specific argparse subcommand structure (`markets watchlist add` vs separate scripts) — keep simple
- Whether to include a `cli/list_watchlist.py` or `cli/show_ticker.py` for read-only inspection (recommended: yes, low cost, high QoL)
- Whether `created_at` / `updated_at` use UTC ISO 8601 with `Z` suffix (recommended) or local timezone

</decisions>

<specifics>
## Specific Ideas

### Ticker Symbol Normalization

- Convert to uppercase on entry
- Tolerate `BRK.B`, `BRK-B`, `BRK/B` — normalize to dotted form (`BRK.B`) for downstream consistency with yfinance
- Reject anything not matching `^[A-Z][A-Z0-9.]{0,8}$` (allows class shares, ETFs, common indexes)

### Cross-Field Validators

- `TechnicalLevels`: when both `support` and `resistance` set, `support < resistance`
- `TickerConfig`: when `thesis_price` set, must be > 0
- `FundamentalTargets`: when any target set, must be > 0
- `Watchlist`: each `tickers[k].ticker == k` (after normalization) — keys must match values
- `notes` length ≤ 1000 chars (sanity cap)

### CLI Ergonomics — Examples

```bash
markets watchlist add AAPL --lens value --thesis 200 --support 175 --resistance 220
markets watchlist add NVDA --lens growth --notes "AI infra play, reload zone $850"
markets watchlist add JPM --lens value --pe-target 12 --ps-target 4
markets watchlist remove ABC          # errors with suggestion if "ABT" or similar close match exists
markets watchlist list                  # ticker, lens, thesis, notes
markets watchlist show AAPL             # full config dump
```

Sensible defaults: missing flags use TickerConfig defaults; only `ticker` is required.

### Seed File

`watchlist.example.json` with 5 representative tickers spanning lenses:
- `AAPL` — value
- `NVDA` — growth
- `BRK.B` — value (also tests dot normalization)
- `GME` — contrarian (also tests volatility edge cases)
- `V` — mixed

README documents copy-and-edit pattern + the schema reference.

### Atomic Write Pattern

```python
def save_watchlist(watchlist: Watchlist, path: Path = Path("watchlist.json")) -> None:
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(watchlist.model_dump_json(indent=2))
    os.replace(tmp, path)  # atomic on POSIX and Win32
```

### Testing Surface

- `tests/test_schemas.py` — schema validation: valid, invalid (each cross-field rule), normalization
- `tests/test_loader.py` — round-trip load/save, malformed JSON handling
- `tests/test_cli_add.py` — happy path, duplicate ticker, invalid ticker, all-flags, file-not-exists
- `tests/test_cli_remove.py` — happy path, missing ticker, suggestion logic
- pytest + pytest-cov; aim for ≥90% coverage on schema + loader (these are the foundation everything depends on)

</specifics>

<deferred>
## Deferred Ideas

- **Frontend watchlist CRUD UI** — deferred to v1.x (REQUIREMENTS.md WATCH-06, WATCH-07). Phase 1 is CLI-only.
- **Bulk import from CSV** — v1.x; not blocking morning-scan workflow
- **Watchlist groups / categories** ("core holdings" vs "watch only") — v2; YAGNI for v1, single watchlist sufficient
- **Per-config audit log** — overengineering; `git log watchlist.json` is sufficient version history
- **Real-time validation in CLI** ("does this ticker exist on Yahoo?") — defer to Phase 2 (ingestion has the means; validating at edit creates a Phase 1 → Phase 2 dependency we don't want)
- **Watchlist file location override** (env var or `--watchlist <path>` flag) — YAGNI for personal single-user use; root-level is fine
- **Web-based config editing** — out of scope; addressed by frontend CRUD in v1.x
- **Schema migration tooling** — premature; bump `version` field manually if we ever break schema (won't happen in v1)

</deferred>

---

*Phase: 01-foundation-watchlist-per-ticker-config*
*Context synthesized: 2026-04-30 from project-level locked decisions in `.planning/PROJECT.md` and `.planning/research/ARCHITECTURE.md`*
