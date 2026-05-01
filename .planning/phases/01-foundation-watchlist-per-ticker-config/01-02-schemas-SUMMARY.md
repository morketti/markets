---
phase: 01-foundation-watchlist-per-ticker-config
plan: 02
subsystem: schema
tags: [python, pydantic, validation, schema, tdd]

# Dependency graph
requires:
  - "Plan 01: analysts/ package exists, pytest+coverage wired, conftest fixtures lazy-import schemas"
provides:
  - "analysts.schemas.TechnicalLevels — Optional support/resistance with cross-field support<resistance rule"
  - "analysts.schemas.FundamentalTargets — Optional pe/ps/pb_target each > 0"
  - "analysts.schemas.TickerConfig — 9-field per-ticker config (ticker, short_term_focus, long_term_lens, thesis_price, technical_levels, target_multiples, notes, created_at, updated_at)"
  - "analysts.schemas.Watchlist — version + dict[str, TickerConfig], strict key==value.ticker rule"
  - "analysts.schemas.normalize_ticker(s) — module-level helper (single source of truth; CLI Plans 04/05 import directly)"
  - "analysts.schemas._TICKER_PATTERN — exported regex for any future caller that needs the rule directly"
affects: [01-03-loader, 01-04-cli-core, 01-05-cli-readonly-and-example]

# Tech tracking
tech-stack:
  added: []  # All deps already installed in Plan 01
  patterns:
    - "Module-level normalize_ticker(s) helper -> @field_validator delegation — eliminates triple-duplication of normalization logic across schema/cli/cli (resolves Plan-02 deferred decision)"
    - "@model_validator(mode='after') for cross-field rules; @field_validator for single-field rules — Pydantic v2 idiom per 01-CONTEXT.md correction #2"
    - "Hyphen-form ticker normalization: BRK.B / BRK/B / BRK_B / brk-b all -> BRK-B (yfinance compat)"
    - "ConfigDict(validate_assignment=True, extra='forbid') on every model — mutation safety + typo rejection in user-edited watchlist.json"
    - "Strict watchlist key validation (no silent rewrite) — dict key MUST match value.ticker; mismatches raise ValidationError naming the offending key"

key-files:
  created:
    - "analysts/schemas.py — 171 lines; 4 Pydantic v2 models + module-level normalize_ticker helper + _TICKER_PATTERN"
    - "tests/test_schemas.py — 191 lines; 8 unit tests covering all WATCH-04 + WATCH-05 rules"
  modified: []

key-decisions:
  - "normalize_ticker extracted to module level (not just a classmethod). Plans 04/05 will import it as a public function — eliminates the previously deferred 3-way duplication risk (schema/remove_ticker/show_ticker)."
  - "TickerConfig._normalize_ticker_field delegates to module-level helper. The classmethod is now thin (5 lines) and just translates 'helper returned None' into a Pydantic ValueError so the field-loc surfaces correctly."
  - "_TICKER_PATTERN allows BOTH dot and hyphen in the matcher (^[A-Z][A-Z0-9.\\-]{0,8}\$). This means a stray dot in input doesn't get rejected with a misleading 'regex mismatch' before the normalizer runs — the normalizer always emits hyphen form regardless. Same regex covers both pre- and post-normalization shapes."
  - "Watchlist.keys_match_tickers raises rather than rewrites. Silent rewrite would mask user typos and create surprise behavior in 'git diff watchlist.json'. The error message names the offending key for actionable correction."
  - "Added two extra TechnicalLevels test cases (negative support, zero resistance) inside test_support_equals_resistance_rejected to lift coverage from 97% to 99%. Stays within plan scope — same validator, same WATCH-05 requirement."

requirements-completed: [WATCH-04, WATCH-05]

# Metrics
duration: 2m15s
completed: 2026-05-01
---

# Phase 1 Plan 2: Schemas Summary

**Pydantic v2 schema lock-in: `TechnicalLevels`, `FundamentalTargets`, `TickerConfig`, `Watchlist` + module-level `normalize_ticker(s)` helper — 8/8 schema tests green, 99% line coverage on `analysts/schemas.py`, all four cross-field rules in place, BRK.B inputs canonicalize to BRK-B for yfinance compatibility.**

## Performance

- **Duration:** ~2m15s
- **Started:** 2026-05-01T03:59:36Z
- **Completed:** 2026-05-01T04:01:51Z
- **Tasks:** 2 (RED, GREEN — REFACTOR skipped as plan permits)
- **Files created:** 2 (`analysts/schemas.py`, `tests/test_schemas.py`)

## Accomplishments

- `analysts/schemas.py` ships **171 lines** containing all four Pydantic v2 models plus the module-level `normalize_ticker(s)` helper. (Plan target: 100-160; the 11-line overshoot is docstring weight and a clarifying comment about why the regex accepts dot+hyphen.)
- **All 8 schema tests pass** (`uv run pytest tests/test_schemas.py -x` -> `8 passed in 0.21s`):
  - `test_long_term_lens_enum` — covers 1-W1-01 (Literal enum)
  - `test_support_below_resistance` — covers 1-W1-02 (cross-field, model_validator)
  - `test_target_multiples_positive` — covers 1-W1-03 (per-field positive guards)
  - `test_notes_max_length` — covers 1-W1-04 (Field(max_length=1000))
  - `test_thesis_price_negative_rejected` — covers 1-W1-05 (single-field validator)
  - `test_support_equals_resistance_rejected` — covers 1-W1-06 (>= not >, plus extra negative-bound assertions)
  - `test_watchlist_key_mismatch` — covers 1-W1-07 (strict key check, names the offender)
  - `test_ticker_normalization` — covers 1-W1-08 (12 forms via TickerConfig + 6 forms via direct helper call)
- **Coverage on `analysts/schemas.py`: 99%** line, **98.89%** with branch (gate: ≥95%). The single remaining branch-partial is `support is not None and resistance is not None` — both halves are covered, only the `True/False` arm pair on `False/False` isn't materially testable.
- The `seeded_watchlist_path` and `large_watchlist_path` fixtures from Plan 01's `tests/conftest.py` are now live: their `from analysts.schemas import TickerConfig, Watchlist` succeeds, and `Watchlist(tickers={'BRK-B': TickerConfig(ticker='BRK-B', ...)})` round-trips through `model_dump(mode='json')` -> `json.dumps(..., sort_keys=True)` cleanly. Plans 03+ can request them today.

## Schema Shape Confirmation

**Regex pattern (verified):** `^[A-Z][A-Z0-9.\-]{0,8}$` — matches the plan spec exactly.

**Hyphen normalization (verified):**
- `TickerConfig(ticker='brk.b').ticker == 'BRK-B'` ✓
- `TickerConfig(ticker='BRK/B').ticker == 'BRK-B'` ✓
- `TickerConfig(ticker='BRK_B').ticker == 'BRK-B'` ✓
- `TickerConfig(ticker='brk-b').ticker == 'BRK-B'` ✓
- `TickerConfig(ticker='aapl').ticker == 'AAPL'` ✓
- `TickerConfig(ticker=' AAPL ').ticker == 'AAPL'` ✓ (whitespace stripped)

**Cross-field validators (verified — grep `analysts/schemas.py`):**
- `TechnicalLevels.support_below_resistance` — `@model_validator(mode='after')` (line 74) ✓
- `Watchlist.keys_match_tickers` — `@model_validator(mode='after')` (line 162) ✓
- All `@field_validator` uses are single-field: ticker (mode=before normalization), thesis_price positive, support/resistance independent positivity, pe/ps/pb_target independent positivity ✓

**ConfigDict on every model (verified):**
- `TechnicalLevels` ✓
- `FundamentalTargets` ✓
- `TickerConfig` ✓
- `Watchlist` ✓
All four set `validate_assignment=True` (mutation safety per Pitfall #5) and `extra='forbid'` (typo rejection per Open Question #2).

**Module-level `normalize_ticker` helper (verified):**
- `from analysts.schemas import normalize_ticker` succeeds ✓
- `normalize_ticker('brk.b') == 'BRK-B'` ✓
- `normalize_ticker('^GSPC') is None` (returns None, doesn't raise) ✓
- `normalize_ticker(123) is None` (non-string input) ✓
- `TickerConfig._normalize_ticker_field` delegates: `norm = normalize_ticker(v) if isinstance(v, str) else None` then raises ValueError on None ✓

**Strict watchlist key mode (verified):**
- `Watchlist(tickers={'aapl': TickerConfig(ticker='AAPL')})` raises `ValidationError` with `"aapl"` in the message — no silent rewrite ✓
- `Watchlist(tickers={'AAPL': TickerConfig(ticker='AAPL')})` succeeds ✓

## Task Commits

Each TDD phase committed atomically:

1. **RED — `test(01-02): add failing schema tests`** — commit **`66795a2`**
   - Wrote `tests/test_schemas.py` with 8 test functions
   - Confirmed `ModuleNotFoundError: No module named 'analysts.schemas'` on collection
2. **GREEN — `feat(01-02): implement TickerConfig + Watchlist schema with shared normalize_ticker helper`** — commit **`87aaa4e`**
   - Wrote `analysts/schemas.py` with all 4 models + module-level helper
   - Confirmed `8 passed in 0.21s`; coverage 99% (gate 95%)
   - Includes the small +6-line additions to `test_support_equals_resistance_rejected` (per-bound positivity coverage)

REFACTOR was skipped per plan guidance ("schema is small enough that refactoring is unlikely to add value... ship the GREEN as-is"). Schema runs in ~microseconds per validation; no test took > 50ms.

## Files Created/Modified

- **Created** `analysts/schemas.py` (171 lines):
  - Module docstring naming the historical `analysts.` namespace decision
  - `_TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]{0,8}$")`
  - `def normalize_ticker(s) -> Optional[str]` (module-level helper)
  - `class TechnicalLevels` with `positive` field validator + `support_below_resistance` model validator
  - `class FundamentalTargets` with `positive` field validator on all three multiples
  - `class TickerConfig` with `_normalize_ticker_field` (mode=before, delegates to helper) + `thesis_price_positive`
  - `class Watchlist` with `keys_match_tickers` model validator (strict mode, no rewrite)
- **Created** `tests/test_schemas.py` (191 lines):
  - 8 test functions, each tagged with its 1-W1-NN probe
  - Imports `TickerConfig, TechnicalLevels, FundamentalTargets, Watchlist, normalize_ticker`
  - Uses `pytest.raises(ValidationError)` + `exc_info.value.errors()` to assert error loc paths
  - `test_ticker_normalization` exercises both the field validator (12 cases) AND the direct helper (6 cases)

## Decisions Made

- **Module-level `normalize_ticker` extracted (not just classmethod).** Resolves the previously-deferred CLI duplication risk. Plans 04 (`cli/remove_ticker.py`) and 05 (`cli/show_ticker.py`) will `from analysts.schemas import normalize_ticker` and call directly — no `_normalize_ticker_str` duplicate, no inline regex. Single source of truth.
- **Helper returns `Optional[str]` (None on invalid input), does not raise.** This lets the CLI use it for "is this user input parseable?" checks without try/except overhead, while the schema's `_normalize_ticker_field` translates None into a Pydantic ValueError.
- **Helper accepts non-string input gracefully** (returns None for `int`, `bytes`, etc.) so callers can pass `args.ticker` directly without isinstance-guarding everywhere.
- **Strict watchlist key mode** chosen per Pitfall #4: silent rewrite would mask user typos and produce surprise diffs in `git log watchlist.json`. The error message is actionable — names the offending key and tells the user how to fix it.
- **Added two negative-bound assertions to `test_support_equals_resistance_rejected`** to lift coverage of `TechnicalLevels.positive` from 97% to 99%. Stays within plan scope — same WATCH-05 requirement, same validator.

## Deviations from Plan

**None.** Plan executed exactly as written. Schema regex, validator types, ConfigDict settings, normalization rules, error message contents, test structure, and helper signature all match the plan specification verbatim. The 11-line overshoot vs. the 100-160 line target is purely docstring/comment overhead (the validator/model code itself is ~110 lines).

The two extra `TechnicalLevels` assertions in `test_support_equals_resistance_rejected` are not a deviation — they exercise a validator the plan explicitly required (`each individually must be > 0 if set`) and lift the coverage gate further above its threshold. Same probe (1-W1-06), same WATCH-05 requirement.

## Issues Encountered

**None.** Both verification probes ran clean on first try:

- `uv run pytest tests/test_schemas.py -x` -> `8 passed in 0.21s`
- `uv run pytest tests/test_schemas.py --cov=analysts.schemas --cov-fail-under=95` -> coverage gate met at 98.89%

The only diagnostic friction was Windows line-ending warnings (`LF will be replaced by CRLF`) on git add — cosmetic, doesn't affect file content or behavior.

## Verification Probes (from PLAN.md `<verification>`)

1. ✓ `uv run pytest tests/test_schemas.py -x` — `8 passed in 0.21s`
2. ✓ `uv run pytest --cov=analysts.schemas --cov-fail-under=95` — `Required test coverage of 95% reached. Total coverage: 98.89%`
3. ✓ `uv run python -c "...TickerConfig(ticker='brk.b')..."` — prints `BRK-B`
4. ✓ `uv run python -c "...TickerConfig(ticker='AAPL', thesis_price=-1)..."` — raises `ValidationError`, exit 1
5. ✓ `uv run python -c "...normalize_ticker('brk.b')..."` — prints `helper OK`
6. ✓ `seeded_watchlist_path` fixture pattern works end-to-end (`Watchlist(tickers={'AAPL': TickerConfig(...), 'BRK-B': TickerConfig(...)}).model_dump(mode='json')` round-trips through `json.dumps(..., sort_keys=True)`)

## Next Phase Readiness

**Ready for Plan 03 (loader):**
- `analysts.schemas.Watchlist` is the locked input/output type for `watchlist/loader.py`
- `Watchlist().model_validate_json(text)` (Plan 03 entry point) will surface the same actionable error paths the schema tests already verified
- `json.dumps(wl.model_dump(mode='json'), indent=2, sort_keys=True) + "\n"` (the deterministic-serialization recipe) matches what conftest already uses, so loader tests can re-use the seeded fixture pattern verbatim

**Ready for Plans 04-05 (CLI):**
- `from analysts.schemas import normalize_ticker` is the single-source-of-truth helper. CLI code MUST NOT duplicate the regex or normalization rules.
- `TickerConfig` accepts all 9 fields with sane defaults; CLI `add` command can construct via keyword args, set `created_at`/`updated_at` via `datetime.now(timezone.utc).isoformat(timespec='seconds')`.
- Strict watchlist-key mode means CLI must explicitly use the normalized form as the dict key (i.e., key `= cfg.ticker`, never the raw user input).

**No blockers.** All `must_haves.truths` and `key_links` from the PLAN frontmatter satisfied.

## Self-Check: PASSED

Verified post-write:

- `analysts/schemas.py`: FOUND
- `tests/test_schemas.py`: FOUND
- Commit `66795a2` (RED): FOUND in git log
- Commit `87aaa4e` (GREEN): FOUND in git log
- All 8 tests pass: VERIFIED via `uv run pytest tests/test_schemas.py -x`
- Coverage ≥ 95%: VERIFIED at 98.89% via `--cov-fail-under=95`
- Module-level `normalize_ticker` exported: VERIFIED via `python -c "from analysts.schemas import normalize_ticker"`
- All cross-field validators use `@model_validator(mode="after")`: VERIFIED via grep (`support_below_resistance` and `keys_match_tickers` both at `@model_validator(mode="after")`)
- Hyphen normalization: VERIFIED via direct probe (`BRK.B` -> `BRK-B`)

---
*Phase: 01-foundation-watchlist-per-ticker-config*
*Completed: 2026-05-01*
