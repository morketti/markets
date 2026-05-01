---
phase: 01-foundation-watchlist-per-ticker-config
plan: 02
type: tdd
wave: 2
depends_on: [01]
files_modified:
  - analysts/schemas.py
  - tests/test_schemas.py
autonomous: true
requirements: [WATCH-04, WATCH-05]
must_haves:
  truths:
    - "TickerConfig accepts and stores all 9 fields: ticker, short_term_focus, long_term_lens, thesis_price, technical_levels, target_multiples, notes, created_at, updated_at"
    - "TickerConfig.ticker normalizes case-insensitively (aapl → AAPL) and class-share separators to hyphen (BRK.B / BRK/B / BRK_B → BRK-B)"
    - "Invalid tickers (^GSPC, EURUSD=X, 1AAPL, TOOLONGTICKER) raise ValidationError"
    - "long_term_lens enforces Literal['value','growth','contrarian','mixed']; other values raise ValidationError"
    - "thesis_price <= 0 raises ValidationError mentioning 'thesis_price' in loc path"
    - "TechnicalLevels with support >= resistance raises ValidationError mentioning support and resistance"
    - "FundamentalTargets with any *_target <= 0 raises ValidationError"
    - "notes longer than 1000 chars raises ValidationError"
    - "Watchlist with mismatched key vs value.ticker raises ValidationError naming the offending key"
    - "Module-level normalize_ticker(s) helper is exported and reused by CLI plans (no duplication of normalization logic)"
  artifacts:
    - path: "analysts/schemas.py"
      provides: "TechnicalLevels, FundamentalTargets, TickerConfig, Watchlist Pydantic v2 models with all validators; module-level normalize_ticker helper for shared use across CLI"
      exports: ["TechnicalLevels", "FundamentalTargets", "TickerConfig", "Watchlist", "normalize_ticker", "_TICKER_PATTERN"]
      contains: "_TICKER_PATTERN, def normalize_ticker"
      min_lines: 100
    - path: "tests/test_schemas.py"
      provides: "8 unit tests covering WATCH-04 + WATCH-05 schema rules"
      contains: "test_ticker_normalization, test_long_term_lens_enum, test_support_below_resistance, test_target_multiples_positive, test_notes_max_length, test_thesis_price_negative_rejected, test_support_equals_resistance_rejected, test_watchlist_key_mismatch"
  key_links:
    - from: "analysts/schemas.py:_TICKER_PATTERN"
      to: "analysts/schemas.py:normalize_ticker (module-level helper)"
      via: "regex compiled at module level, used in normalize_ticker()"
      pattern: "_TICKER_PATTERN.match"
    - from: "analysts/schemas.py:normalize_ticker (module-level)"
      to: "TickerConfig.normalize_ticker_field @field_validator('ticker', mode='before')"
      via: "field validator delegates to module-level helper for shared logic with CLI"
      pattern: "return normalize_ticker(v)"
    - from: "analysts/schemas.py:TechnicalLevels.support_below_resistance"
      to: "@model_validator(mode='after')"
      via: "CONTEXT.md correction #2 — cross-field rule requires fully-validated model state (not partial state from @field_validator)"
      pattern: "@model_validator"
    - from: "analysts/schemas.py:Watchlist.keys_match_tickers"
      to: "@model_validator(mode='after')"
      via: "CONTEXT.md correction #2 — dict key vs value.ticker is a cross-field rule needing fully-validated model"
      pattern: "@model_validator"
    - from: "tests/test_schemas.py"
      to: "analysts.schemas"
      via: "from analysts.schemas import TickerConfig, TechnicalLevels, FundamentalTargets, Watchlist, normalize_ticker"
      pattern: "from analysts.schemas import"
---

<objective>
Ship the foundation Pydantic v2 schema (TechnicalLevels, FundamentalTargets, TickerConfig, Watchlist) and its full unit-test coverage, plus the module-level `normalize_ticker(s)` helper that CLI plans 04 and 05 reuse for input normalization. After this plan, the schema is the locked source of truth that the loader (Plan 03) and CLI (Plans 04-05) consume — and any future phase that imports from `analysts.schemas` will get exactly the right validation behavior.

Purpose: Per ROADMAP.md, Phase 1 success criterion #4 is "Invalid configs are rejected with actionable Pydantic error messages." This plan delivers that — and locks the schema shape that nine downstream phases depend on. The schema is small (~150 lines) but its decisions are the most expensive to revisit. Get it right once.

Output: `analysts/schemas.py` (all four models, all validators, plus module-level `normalize_ticker` helper) + `tests/test_schemas.py` (8 unit tests covering every validation rule). Both committed; pytest green; coverage on `analysts/schemas.py` ≥ 95%.
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
@.planning/phases/01-foundation-watchlist-per-ticker-config/01-CONTEXT.md
@.planning/phases/01-foundation-watchlist-per-ticker-config/01-RESEARCH.md
@.planning/phases/01-foundation-watchlist-per-ticker-config/01-VALIDATION.md
@.planning/phases/01-foundation-watchlist-per-ticker-config/01-01-scaffold-SUMMARY.md

<interfaces>
<!-- This plan creates the public schema interface that Plans 03, 04, 05 import. -->
<!-- Downstream contract: -->

```python
# analysts/schemas.py — public surface (downstream plans import these names)
from typing import Literal, Optional
from pydantic import BaseModel

# Module-level helper — reused by cli/remove_ticker.py and cli/show_ticker.py.
# Returns canonical hyphen form (or None if input doesn't match the regex).
def normalize_ticker(s: str) -> str | None: ...

class TechnicalLevels(BaseModel):
    support: Optional[float]
    resistance: Optional[float]

class FundamentalTargets(BaseModel):
    pe_target: Optional[float]
    ps_target: Optional[float]
    pb_target: Optional[float]

class TickerConfig(BaseModel):
    ticker: str  # normalized: uppercase, class-share separators → hyphen
    short_term_focus: bool
    long_term_lens: Literal["value", "growth", "contrarian", "mixed"]
    thesis_price: Optional[float]
    technical_levels: Optional[TechnicalLevels]
    target_multiples: Optional[FundamentalTargets]
    notes: str  # max 1000 chars
    created_at: Optional[str]
    updated_at: Optional[str]
    # The field validator delegates to module-level normalize_ticker;
    # raises ValueError on regex mismatch so Pydantic surfaces ValidationError.

class Watchlist(BaseModel):
    version: int  # default 1
    tickers: dict[str, TickerConfig]  # key MUST equal value.ticker
```

The CLI in Plans 04 and 05 will import `from analysts.schemas import normalize_ticker` (module-level helper) and call it directly — NO duplication of normalization logic anywhere in the codebase. This was a deferred decision in the prior revision; resolved now: extract to module level, single source of truth.
</interfaces>

<corrections_callout>
This plan is the primary site of the three CONTEXT.md corrections — the schema is where they manifest:

1. **Hyphen normalization (NOT dot).** `normalize_ticker` MUST produce `BRK-B` from inputs `BRK.B`, `BRK/B`, `BRK_B`. The regex pattern `^[A-Z][A-Z0-9.\-]{0,8}$` allows hyphen and dot in the matcher (so input with a leftover dot doesn't get a misleading "regex" error message before the normalizer runs), but the normalizer always emits hyphen form. Inline comment in the validator: `# yfinance uses hyphenated class-share notation (BRK-B); we normalize to that form for Phase 2 compatibility.`

2. **Cross-field validators use `@model_validator(mode="after")`, NOT `@field_validator`.** Specifically:
   - `TechnicalLevels.support_below_resistance` → `@model_validator(mode="after")`
   - `Watchlist.keys_match_tickers` → `@model_validator(mode="after")`
   Single-field rules (e.g., `thesis_price > 0`, `support > 0`, `pe_target > 0`) MAY remain as `@field_validator` since they only inspect one field.

3. **`json.dumps(... sort_keys=True)` for serialization, NOT `model_dump_json(indent=2)`.** This plan does NOT write serialization code (that's Plan 03), but the test for `Watchlist.keys_match_tickers` may need to construct serialized form for round-trip cases. If so, use `json.dumps(wl.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"` — see conftest.py from Plan 01.

**Module-level `normalize_ticker(s)` helper (resolves prior deferred decision).** The normalization regex + transform is shared across `analysts/schemas.py` (field validator), `cli/remove_ticker.py`, and `cli/show_ticker.py`. To avoid 3-way duplication, extract a module-level function in `analysts/schemas.py`:

```python
def normalize_ticker(s: str) -> str | None:
    """Normalize a ticker string to canonical hyphen form, or return None if invalid.

    Accepts dot, slash, underscore, hyphen as class-share separators; emits hyphen.
    Strips whitespace, uppercases, collapses repeated hyphens.
    Returns None when the result doesn't match _TICKER_PATTERN (caller decides how to error).
    """
    if not isinstance(s, str):
        return None
    norm = s.strip().upper().replace(".", "-").replace("/", "-").replace("_", "-")
    norm = re.sub(r"-+", "-", norm)
    return norm if _TICKER_PATTERN.match(norm) else None
```

The `TickerConfig.ticker` `@field_validator(mode="before")` delegates to this helper:

```python
@field_validator("ticker", mode="before")
@classmethod
def _normalize_ticker_field(cls, v):
    norm = normalize_ticker(v) if isinstance(v, str) else None
    if norm is None:
        raise ValueError(f"invalid ticker {v!r}: must match {_TICKER_PATTERN.pattern}")
    return norm
```

Plans 04 and 05 import `from analysts.schemas import normalize_ticker` and use it directly. No `_normalize_ticker_str` duplication, no inline regex in CLI files.
</corrections_callout>
</context>

<feature>
  <name>Pydantic v2 schema: TickerConfig + Watchlist + supporting nested models + module-level normalize_ticker helper</name>
  <files>analysts/schemas.py, tests/test_schemas.py</files>
  <behavior>
**Module-level helper:**
- `normalize_ticker(s: str) -> str | None` — public function, exported. Accepts dot/slash/underscore/hyphen as separators; emits hyphen. Returns None on invalid input (doesn't raise). Used by `TickerConfig._normalize_ticker_field` (via delegation) and by `cli/remove_ticker.py`, `cli/show_ticker.py` (Plans 04, 05).

**TickerConfig field validation:**
- `ticker` — required string; normalize input via `@field_validator("ticker", mode="before")` that delegates to `normalize_ticker(v)`; raise ValueError if helper returns None (Pydantic wraps in ValidationError).
- `short_term_focus` — bool, default True
- `long_term_lens` — Literal["value", "growth", "contrarian", "mixed"], default "mixed"
- `thesis_price` — Optional[float], default None; if set, must be > 0 (single-field validator)
- `technical_levels` — Optional[TechnicalLevels], default None
- `target_multiples` — Optional[FundamentalTargets], default None
- `notes` — str, default "", max_length=1000 (use `Field(default="", max_length=1000)`)
- `created_at`, `updated_at` — Optional[str], default None (no validation; format set by CLI)

**TechnicalLevels field validation:**
- `support`, `resistance` — Optional[float], default None; each individually must be > 0 if set (single-field validator)
- Cross-field: when BOTH set, support < resistance — `@model_validator(mode="after")`

**FundamentalTargets field validation:**
- `pe_target`, `ps_target`, `pb_target` — Optional[float], default None; each individually must be > 0 if set (single-field validator)

**Watchlist field validation:**
- `version` — int, default 1
- `tickers` — dict[str, TickerConfig], default empty dict via `Field(default_factory=dict)`
- Cross-field: every dict key must equal its value's `.ticker` field after normalization — `@model_validator(mode="after")` raises ValueError naming the offending key (strict mode per Pitfall #4)

**ConfigDict on every model:** `model_config = ConfigDict(validate_assignment=True, extra="forbid")` per 01-RESEARCH.md Pitfall #5 (mutation safety) and Open Question #2 (forbid catches typos in user-edited watchlist.json).

**Test cases (RED → GREEN cycle, all 8 must end green):**
- `test_long_term_lens_enum` — TickerConfig(ticker="AAPL", long_term_lens="invalid_lens") raises ValidationError; valid values "value", "growth", "contrarian", "mixed" all succeed
- `test_support_below_resistance` — TechnicalLevels(support=100, resistance=200) succeeds; TechnicalLevels(support=200, resistance=100) raises ValidationError mentioning "support" and "resistance"
- `test_target_multiples_positive` — FundamentalTargets(pe_target=15) succeeds; FundamentalTargets(pe_target=-1) raises ValidationError; FundamentalTargets(pe_target=0) raises ValidationError; mixed valid+invalid (pe_target=15, ps_target=-1) raises ValidationError naming ps_target
- `test_notes_max_length` — TickerConfig(ticker="AAPL", notes="x"*1000) succeeds; TickerConfig(ticker="AAPL", notes="x"*1001) raises ValidationError mentioning "notes"
- `test_thesis_price_negative_rejected` — TickerConfig(ticker="AAPL", thesis_price=-100) raises ValidationError with "thesis_price" in loc; thesis_price=0 also raises; thesis_price=100 succeeds; thesis_price=None succeeds
- `test_support_equals_resistance_rejected` — TechnicalLevels(support=100, resistance=100) raises ValidationError (uses `>=` not `>`)
- `test_watchlist_key_mismatch` — Watchlist(tickers={"aapl": TickerConfig(ticker="AAPL")}) raises ValidationError naming "aapl" in the message (key normalization is strict — no silent rewrite, per Pitfall #4 recommendation); Watchlist(tickers={"AAPL": TickerConfig(ticker="AAPL")}) succeeds
- `test_ticker_normalization` — covers all forms in one test, exercising BOTH the field validator AND the module-level helper:
  - TickerConfig(ticker="aapl").ticker == "AAPL"
  - TickerConfig(ticker="BRK.B").ticker == "BRK-B"
  - TickerConfig(ticker="BRK/B").ticker == "BRK-B"
  - TickerConfig(ticker="BRK_B").ticker == "BRK-B"
  - TickerConfig(ticker="brk-b").ticker == "BRK-B"
  - TickerConfig(ticker=" AAPL ").ticker == "AAPL"  (whitespace stripped)
  - TickerConfig(ticker="^GSPC") raises ValidationError (starts with non-alpha after norm)
  - TickerConfig(ticker="EURUSD=X") raises ValidationError (= sign)
  - TickerConfig(ticker="1AAPL") raises ValidationError (starts with digit)
  - TickerConfig(ticker="TOOLONGTICKER") raises ValidationError (>9 chars after first letter)
  - TickerConfig(ticker="") raises ValidationError
  - TickerConfig(ticker=123) raises ValidationError (non-string input rejected with type-checked message)
  - normalize_ticker("brk.b") == "BRK-B" (module-level helper called directly)
  - normalize_ticker("^GSPC") is None (returns None on invalid; doesn't raise)
  - normalize_ticker(123) is None (non-string input)
  </behavior>
  <implementation>
**TDD cycle (one commit per phase):**

**RED (commit `test(01-02): add failing schema tests`):**
1. Write `tests/test_schemas.py` with all 8 test functions above. Each calls `TickerConfig(...)`, `TechnicalLevels(...)`, `FundamentalTargets(...)`, or `Watchlist(...)` and uses `pytest.raises(ValidationError)` for negative cases. The `test_ticker_normalization` test also imports and exercises the module-level `normalize_ticker` helper.
2. Run `uv run pytest tests/test_schemas.py -x` — confirm ALL FAIL with `ImportError` or `ModuleNotFoundError` (because `analysts/schemas.py` is empty).

Test imports:
```python
import json
import pytest
from pydantic import ValidationError
from analysts.schemas import TickerConfig, TechnicalLevels, FundamentalTargets, Watchlist, normalize_ticker
```

For tests that need to inspect the error structure (e.g., `test_thesis_price_negative_rejected`), use:
```python
with pytest.raises(ValidationError) as exc_info:
    TickerConfig(ticker="AAPL", thesis_price=-100)
errors = exc_info.value.errors()
assert any("thesis_price" in e["loc"] for e in errors)
```

For the watchlist key-mismatch test, the error message must include the offending key:
```python
with pytest.raises(ValidationError) as exc_info:
    Watchlist(tickers={"aapl": TickerConfig(ticker="AAPL")})
assert "aapl" in str(exc_info.value)
```

For the module-level helper:
```python
def test_ticker_normalization():
    # ... TickerConfig cases ...
    # Module-level helper exercised directly:
    assert normalize_ticker("brk.b") == "BRK-B"
    assert normalize_ticker("AAPL") == "AAPL"
    assert normalize_ticker("^GSPC") is None
    assert normalize_ticker(123) is None
    assert normalize_ticker("") is None
```

**GREEN (commit `feat(01-02): implement TickerConfig + Watchlist schema with shared normalize_ticker helper`):**
3. Write `analysts/schemas.py` from `01-RESEARCH.md` § Code Examples ("Full TickerConfig schema with all locked rules") — verbatim, MODIFIED per this revision to extract the module-level helper:
   - Module docstring explaining the historical `analysts.` namespace per Open Question #3
   - `_TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]{0,8}$")` at module top
   - `from __future__ import annotations` for forward refs
   - **NEW: Module-level `def normalize_ticker(s: str) -> str | None:`** that returns canonical form or None — see corrections_callout for exact body
   - All four models with ConfigDict(validate_assignment=True, extra="forbid")
   - **CHANGED:** `TickerConfig._normalize_ticker_field` is `@field_validator("ticker", mode="before")` + `@classmethod` and DELEGATES to module-level `normalize_ticker(v)`; raises ValueError if helper returns None
   - `TickerConfig.thesis_price_positive` as `@field_validator("thesis_price")`
   - `TechnicalLevels.positive` (covers both support+resistance) as `@field_validator("support", "resistance")`
   - `TechnicalLevels.support_below_resistance` as `@model_validator(mode="after")` — per CONTEXT.md correction #2
   - `FundamentalTargets.positive` as `@field_validator("pe_target", "ps_target", "pb_target")`
   - `Watchlist.keys_match_tickers` as `@model_validator(mode="after")` raising on mismatch (strict mode, no silent rewrite) — per CONTEXT.md correction #2
   - `notes` field as `Field(default="", max_length=1000)`
4. Run `uv run pytest tests/test_schemas.py -x` — confirm ALL 8 PASS.
5. Run coverage: `uv run pytest tests/test_schemas.py --cov=analysts.schemas --cov-report=term-missing` — confirm coverage on `analysts/schemas.py` ≥ 95%. Lines that may be uncovered: import-error branches in `normalize_ticker` (e.g., the `not isinstance(v, str)` check) — covered by `normalize_ticker(123) is None` assertion in `test_ticker_normalization`.

**REFACTOR (skip unless needed):** The schema is small enough that refactoring is unlikely to add value. If a single test takes >50ms, that's a signal something is wrong (Pydantic v2 validation is microseconds). Otherwise, ship the GREEN as-is.

**Per-task verification map (probes from 01-VALIDATION.md):**
- 1-W1-01 → `test_long_term_lens_enum`
- 1-W1-02 → `test_support_below_resistance`
- 1-W1-03 → `test_target_multiples_positive`
- 1-W1-04 → `test_notes_max_length`
- 1-W1-05 → `test_thesis_price_negative_rejected`
- 1-W1-06 → `test_support_equals_resistance_rejected`
- 1-W1-07 → `test_watchlist_key_mismatch`
- 1-W1-08 → `test_ticker_normalization`
  </implementation>
</feature>

<verification>
After GREEN:
1. `uv run pytest tests/test_schemas.py -x` — all 8 tests pass
2. `uv run pytest tests/test_schemas.py --cov=analysts.schemas --cov-fail-under=95` — coverage gate passes
3. `uv run python -c "from analysts.schemas import TickerConfig; t = TickerConfig(ticker='brk.b'); assert t.ticker == 'BRK-B'; print(t.ticker)"` — prints `BRK-B`
4. `uv run python -c "from analysts.schemas import TickerConfig; TickerConfig(ticker='AAPL', thesis_price=-1)"` — raises ValidationError, exit code 1
5. `uv run python -c "from analysts.schemas import normalize_ticker; assert normalize_ticker('brk.b') == 'BRK-B'; assert normalize_ticker('^bad') is None; print('helper OK')"` — prints "helper OK"
6. The `seeded_watchlist_path` fixture from Plan 01's conftest.py now works end-to-end (its lazy import of `analysts.schemas` succeeds): `uv run pytest tests/test_schemas.py --setup-show -k test_ticker_normalization 2>&1 | head -20`
</verification>

<success_criteria>
- [ ] All 8 schema tests pass (`uv run pytest tests/test_schemas.py -x`)
- [ ] Coverage on `analysts/schemas.py` ≥ 95% (`--cov-fail-under=95`)
- [ ] Hyphen normalization verified: `BRK.B`, `BRK/B`, `BRK_B`, `brk-b` all → `BRK-B`
- [ ] All cross-field validators are `@model_validator(mode="after")` (grep `analysts/schemas.py` for `field_validator` and confirm only single-field validators use it)
- [ ] `_TICKER_PATTERN` allows hyphen: pattern includes `\-`
- [ ] Module-level `normalize_ticker(s)` is exported and importable: `from analysts.schemas import normalize_ticker` succeeds; returns None on invalid input (doesn't raise)
- [ ] `extra="forbid"` and `validate_assignment=True` set on all four models (mutation safety + typo catch)
- [ ] `Watchlist.keys_match_tickers` raises on mismatch (strict mode, no silent rewrite — per Pitfall #4)
- [ ] WATCH-04 covered: 5 probes (1-W1-01, 1-W1-02, 1-W1-03, 1-W1-04, 1-W1-08)
- [ ] WATCH-05 covered: 3 probes (1-W1-05, 1-W1-06, 1-W1-07)
</success_criteria>

<output>
After completion, create `.planning/phases/01-foundation-watchlist-per-ticker-config/01-02-schemas-SUMMARY.md` documenting:
- Final line count of `analysts/schemas.py` (expect ~120-160)
- Coverage % on `analysts/schemas.py` (expect ≥95%)
- The exact regex pattern used (verify it's `^[A-Z][A-Z0-9.\-]{0,8}$`)
- Confirmation that `BRK.B` → `BRK-B` (hyphen, per CONTEXT.md correction #1)
- Confirmation that all cross-field validators use `@model_validator(mode="after")` (per CONTEXT.md correction #2)
- Confirmation that module-level `normalize_ticker(s)` helper is exported and used by the field validator (resolves prior deferred decision; CLI plans will import from here)
- Whether `validate_assignment=True` and `extra="forbid"` are set on all four models
- Any deviation from the 01-RESEARCH.md "Full TickerConfig schema" example and why
</output>
