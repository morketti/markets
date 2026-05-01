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
  artifacts:
    - path: "analysts/schemas.py"
      provides: "TechnicalLevels, FundamentalTargets, TickerConfig, Watchlist Pydantic v2 models with all validators"
      exports: ["TechnicalLevels", "FundamentalTargets", "TickerConfig", "Watchlist"]
      contains: "_TICKER_PATTERN"
      min_lines: 100
    - path: "tests/test_schemas.py"
      provides: "8 unit tests covering WATCH-04 + WATCH-05 schema rules"
      contains: "test_ticker_normalization, test_long_term_lens_enum, test_support_below_resistance, test_target_multiples_positive, test_notes_max_length, test_thesis_price_negative_rejected, test_support_equals_resistance_rejected, test_watchlist_key_mismatch"
  key_links:
    - from: "analysts/schemas.py:_TICKER_PATTERN"
      to: "TickerConfig.normalize_ticker @field_validator(mode='before')"
      via: "regex compiled at module level, used in normalize_ticker"
      pattern: "_TICKER_PATTERN.match"
    - from: "tests/test_schemas.py"
      to: "analysts.schemas"
      via: "from analysts.schemas import TickerConfig, TechnicalLevels, FundamentalTargets, Watchlist"
      pattern: "from analysts.schemas import"
---

<objective>
Ship the foundation Pydantic v2 schema (TechnicalLevels, FundamentalTargets, TickerConfig, Watchlist) and its full unit-test coverage. After this plan, the schema is the locked source of truth that the loader (Plan 03) and CLI (Plans 04-05) consume — and any future phase that imports from `analysts.schemas` will get exactly the right validation behavior.

Purpose: Per ROADMAP.md, Phase 1 success criterion #4 is "Invalid configs are rejected with actionable Pydantic error messages." This plan delivers that — and locks the schema shape that nine downstream phases depend on. The schema is small (~150 lines) but its decisions are the most expensive to revisit. Get it right once.

Output: `analysts/schemas.py` (all four models, all validators) + `tests/test_schemas.py` (8 unit tests covering every validation rule). Both committed; pytest green; coverage on `analysts/schemas.py` ≥ 95%.
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

    @classmethod
    def normalize_ticker(cls, v: str) -> str: ...  # accessible as classmethod for CLI direct call

class Watchlist(BaseModel):
    version: int  # default 1
    tickers: dict[str, TickerConfig]  # key MUST equal value.ticker
```

The CLI in Plan 04 will call `TickerConfig.normalize_ticker` directly (as a classmethod) to normalize `args.ticker` for "did you mean" suggestion lookups.
</interfaces>

<corrections_callout>
This plan is the primary site of the three CONTEXT.md corrections — the schema is where they manifest:

1. **Hyphen normalization (NOT dot).** `normalize_ticker` MUST produce `BRK-B` from inputs `BRK.B`, `BRK/B`, `BRK_B`. The regex pattern `^[A-Z][A-Z0-9.\-]{0,8}$` allows hyphen and dot in the matcher (so input with a leftover dot doesn't get a misleading "regex" error message before the normalizer runs), but the normalizer always emits hyphen form. Inline comment in the validator: `# yfinance uses hyphenated class-share notation (BRK-B); we normalize to that form for Phase 2 compatibility.`

2. **Cross-field validators use `@model_validator(mode="after")`, NOT `@field_validator`.** Specifically:
   - `TechnicalLevels.support_below_resistance` → `@model_validator(mode="after")`
   - `Watchlist.keys_match_tickers` → `@model_validator(mode="after")`
   Single-field rules (e.g., `thesis_price > 0`, `support > 0`, `pe_target > 0`) MAY remain as `@field_validator` since they only inspect one field.

3. **`json.dumps(... sort_keys=True)` for serialization, NOT `model_dump_json(indent=2)`.** This plan does NOT write serialization code (that's Plan 03), but the test for `Watchlist.keys_match_tickers` may need to construct serialized form for round-trip cases. If so, use `json.dumps(wl.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"` — see conftest.py from Plan 01.
</corrections_callout>
</context>

<feature>
  <name>Pydantic v2 schema: TickerConfig + Watchlist + supporting nested models</name>
  <files>analysts/schemas.py, tests/test_schemas.py</files>
  <behavior>
**TickerConfig field validation:**
- `ticker` — required string; normalize input to uppercase + hyphen form via `@field_validator(mode="before")`; reject if doesn't match `^[A-Z][A-Z0-9.\-]{0,8}$` after normalization.
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
- `test_ticker_normalization` — covers all forms in one test:
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
  </behavior>
  <implementation>
**TDD cycle (one commit per phase):**

**RED (commit `test(01-02): add failing schema tests`):**
1. Write `tests/test_schemas.py` with all 8 test functions above. Each calls `TickerConfig(...)`, `TechnicalLevels(...)`, `FundamentalTargets(...)`, or `Watchlist(...)` and uses `pytest.raises(ValidationError)` for negative cases.
2. Run `uv run pytest tests/test_schemas.py -x` — confirm ALL FAIL with `ImportError` or `ModuleNotFoundError` (because `analysts/schemas.py` is empty).

Test imports:
```python
import json
import pytest
from pydantic import ValidationError
from analysts.schemas import TickerConfig, TechnicalLevels, FundamentalTargets, Watchlist
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

**GREEN (commit `feat(01-02): implement TickerConfig + Watchlist schema`):**
3. Write `analysts/schemas.py` from `01-RESEARCH.md` § Code Examples ("Full TickerConfig schema with all locked rules") — verbatim, including:
   - Module docstring explaining the historical `analysts.` namespace per Open Question #3
   - `_TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]{0,8}$")` at module top
   - `from __future__ import annotations` for forward refs
   - All four models with ConfigDict(validate_assignment=True, extra="forbid")
   - `TickerConfig.normalize_ticker` as `@field_validator("ticker", mode="before")` + `@classmethod`
   - `TickerConfig.thesis_price_positive` as `@field_validator("thesis_price")`
   - `TechnicalLevels.positive` (covers both support+resistance) as `@field_validator("support", "resistance")`
   - `TechnicalLevels.support_below_resistance` as `@model_validator(mode="after")`
   - `FundamentalTargets.positive` as `@field_validator("pe_target", "ps_target", "pb_target")`
   - `Watchlist.keys_match_tickers` as `@model_validator(mode="after")` raising on mismatch (strict mode, no silent rewrite)
   - `notes` field as `Field(default="", max_length=1000)`
4. Run `uv run pytest tests/test_schemas.py -x` — confirm ALL 8 PASS.
5. Run coverage: `uv run pytest tests/test_schemas.py --cov=analysts.schemas --cov-report=term-missing` — confirm coverage on `analysts/schemas.py` ≥ 95%. Lines that may be uncovered: import-error branches in `normalize_ticker` (e.g., the `not isinstance(v, str)` check) — if so, add a test case `TickerConfig(ticker=123)`.

**REFACTOR (skip unless needed):** The schema is small enough that refactoring is unlikely to add value. If a single test takes >50ms, that's a signal something is wrong (Pydantic v2 validation is microseconds). If `normalize_ticker` has more than ~15 lines, look for consolidation. Otherwise, ship the GREEN as-is.

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
5. The `seeded_watchlist_path` fixture from Plan 01's conftest.py now works end-to-end (its lazy import of `analysts.schemas` succeeds): `uv run pytest tests/test_schemas.py --setup-show -k test_ticker_normalization 2>&1 | head -20`
</verification>

<success_criteria>
- [ ] All 8 schema tests pass (`uv run pytest tests/test_schemas.py -x`)
- [ ] Coverage on `analysts/schemas.py` ≥ 95% (`--cov-fail-under=95`)
- [ ] Hyphen normalization verified: `BRK.B`, `BRK/B`, `BRK_B`, `brk-b` all → `BRK-B`
- [ ] All cross-field validators are `@model_validator(mode="after")` (grep `analysts/schemas.py` for `field_validator` and confirm only single-field validators use it)
- [ ] `_TICKER_PATTERN` allows hyphen: pattern includes `\-`
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
- Whether `validate_assignment=True` and `extra="forbid"` are set on all four models
- Any deviation from the 01-RESEARCH.md "Full TickerConfig schema" example and why
</output>
