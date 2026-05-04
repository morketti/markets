---
phase: 09-endorsement-capture
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - analysts/endorsement_schema.py
  - endorsements/__init__.py
  - endorsements/log.py
  - cli/add_endorsement.py
  - cli/main.py
  - endorsements.jsonl
  - tests/analysts/test_endorsement_schema.py
  - tests/endorsements/__init__.py
  - tests/endorsements/test_log.py
  - tests/cli/test_add_endorsement.py
  - frontend/src/schemas/endorsement.ts
  - frontend/src/schemas/__tests__/endorsement.test.ts
  - frontend/src/lib/loadEndorsements.ts
  - frontend/src/lib/__tests__/loadEndorsements.test.ts
  - frontend/src/components/EndorsementsList.tsx
  - frontend/src/components/__tests__/EndorsementsList.test.tsx
  - frontend/src/routes/DecisionRoute.tsx
  - frontend/tests/e2e/endorsements.spec.ts
autonomous: true
requirements:
  - ENDORSE-01
  - ENDORSE-02
  - ENDORSE-03
must_haves:
  truths:
    - "User runs `markets add_endorsement --ticker AAPL --source 'Motley Fool' --date 2026-04-15 --price 178.42 --notes '...'` and a single JSON line is appended to endorsements.jsonl at repo root"
    - "User runs `markets add_endorsement` with invalid input (negative price, malformed date, blank source); CLI exits non-zero with an actionable Pydantic message and endorsements.jsonl is UNCHANGED (atomic-on-success only)"
    - "Pydantic Endorsement model rejects schema_version != 1 (forces v1.x to bump non-breakingly)"
    - "Frontend zod EndorsementSchema rejects schema_version != 1 with SchemaMismatchError (silently rejects v0 / future v2)"
    - "loadEndorsements(symbol) returns last-90-days endorsements for that ticker, sorted by date descending"
    - "loadEndorsements gracefully returns [] when endorsements.jsonl is 404 (file does not exist yet)"
    - "EndorsementsList empty state renders 'No endorsements captured for {ticker} in the last 90 days. Use markets add_endorsement to capture one.' in muted text"
    - "EndorsementsList populated state renders one card per endorsement (most recent first) showing source / date+price / notes / captured_at relative timestamp — NO performance number anywhere"
    - "DecisionRoute mounts EndorsementsList immediately after DissentPanel (between DissentPanel and the open_observation block, preserving CurrentPriceDelta as the hero above)"
    - "Notion-Clean palette discipline holds: every color in EndorsementsList is a CSS variable token (text-fg, text-fg-muted, border-border, bg-surface) — zero inline hex"
  artifacts:
    - path: "analysts/endorsement_schema.py"
      provides: "Pydantic Endorsement model with schema_version: Literal[1] = 1"
      contains: "class Endorsement"
    - path: "endorsements/__init__.py"
      provides: "endorsements package marker"
    - path: "endorsements/log.py"
      provides: "append_endorsement() + load_endorsements() — JSONL atomic append + read"
      contains: "def append_endorsement"
    - path: "cli/add_endorsement.py"
      provides: "build_add_endorsement_parser + add_endorsement_command (flag-only argparse)"
      contains: "def add_endorsement_command"
    - path: "cli/main.py"
      provides: "SUBCOMMANDS dict extended with add_endorsement entry"
      contains: "add_endorsement"
    - path: "endorsements.jsonl"
      provides: "Empty committed file at repo root (NOT gitignored)"
    - path: "frontend/src/schemas/endorsement.ts"
      provides: "zod EndorsementSchema mirroring Pydantic — z.literal(1) on schema_version"
      contains: "EndorsementSchema"
    - path: "frontend/src/lib/loadEndorsements.ts"
      provides: "useEndorsements(symbol) TanStack hook + 90-day filter + ticker filter + date-desc sort"
      contains: "useEndorsements"
    - path: "frontend/src/components/EndorsementsList.tsx"
      provides: "Decision-Route panel rendering empty + populated states"
      contains: "EndorsementsList"
    - path: "frontend/src/routes/DecisionRoute.tsx"
      provides: "EndorsementsList mounted after DissentPanel"
      contains: "EndorsementsList"
  key_links:
    - from: "cli/main.py"
      to: "cli/add_endorsement.add_endorsement_command"
      via: "SUBCOMMANDS dict registration"
      pattern: "\"add_endorsement\":\\s*\\(build_add_endorsement_parser, add_endorsement_command\\)"
    - from: "cli/add_endorsement.py"
      to: "endorsements/log.append_endorsement"
      via: "import + call after Pydantic validation"
      pattern: "append_endorsement\\("
    - from: "endorsements/log.py"
      to: "analysts/endorsement_schema.Endorsement"
      via: "import + model_dump(mode='json')"
      pattern: "from analysts.endorsement_schema import Endorsement"
    - from: "frontend/src/lib/loadEndorsements.ts"
      to: "raw.githubusercontent.com/.../endorsements.jsonl"
      via: "fetch (text) + line-split + zod parse per line"
      pattern: "endorsements\\.jsonl"
    - from: "frontend/src/components/EndorsementsList.tsx"
      to: "frontend/src/lib/loadEndorsements.useEndorsements"
      via: "hook call with symbol prop"
      pattern: "useEndorsements\\("
    - from: "frontend/src/routes/DecisionRoute.tsx"
      to: "frontend/src/components/EndorsementsList"
      via: "JSX mount immediately after DissentPanel"
      pattern: "<EndorsementsList\\s+symbol="
---

<objective>
Capture endorsements as a first-class signal — append-only JSONL + Pydantic v2 schema with `schema_version: Literal[1] = 1` lock + flag-only CLI + zod-validated frontend panel mounted in DecisionRoute. **Performance math is deferred to v1.x successors (ENDORSE-04..07) — this plan ships capture only.**

Purpose: Close the final 3 v1 requirements (ENDORSE-01, ENDORSE-02, ENDORSE-03) so v1 is shippable. The `Literal[1]` lock guarantees that v1.x performance-math fields can be added non-breakingly via a `Literal[2]` discriminator — v1 readers will not silently misinterpret future records as "0% performance."

Output: 14 new files (~470 production LOC + ~480 test LOC) + 1 modified file (cli/main.py SUBCOMMANDS extension) + 1 modified route (DecisionRoute.tsx mount). ~49 new tests (~25 Python, ~21 vitest, 3 Playwright). Zero new dependencies.
</objective>

<execution_context>
@C:/Users/Mohan/.claude/workflows/execute-plan.md
@C:/Users/Mohan/.claude/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/09-endorsement-capture/09-CONTEXT.md
@.planning/phases/09-endorsement-capture/09-RESEARCH.md
@.planning/phases/09-endorsement-capture/09-VALIDATION.md

# Reference patterns (verbatim mirrors — no exploration needed)
@analysts/schemas.py
@routine/memory_log.py
@cli/add_ticker.py
@cli/main.py
@frontend/src/schemas/refresh.ts
@frontend/src/lib/useRefreshData.ts
@frontend/src/lib/fetchSnapshot.ts
@frontend/src/routes/DecisionRoute.tsx

<interfaces>
<!-- Key contracts the executor needs. Extracted from existing codebase. -->
<!-- Use these directly — no codebase exploration required. -->

From analysts/schemas.py:
```python
def normalize_ticker(s: str) -> Optional[str]
# Returns canonical uppercase + hyphen form (BRK.B → BRK-B, aapl → AAPL).
# Returns None on invalid input. Reuse via field_validator (NOT regex in CLI).
```

From routine/memory_log.py (Pattern to mirror in endorsements/log.py):
```python
# Atomic append discipline:
path.parent.mkdir(parents=True, exist_ok=True)
record = {...}  # plain dict
line = json.dumps(record, sort_keys=True) + "\n"
with path.open("a", encoding="utf-8") as f:
    f.write(line)
```

From cli/main.py:30-42 (SUBCOMMANDS dict — single registration point):
```python
SUBCOMMANDS: dict[str, tuple[
    Callable[[argparse.ArgumentParser], None],
    Callable[[argparse.Namespace], int],
]] = {
    "add": (build_add_parser, add_command),
    "remove": (build_remove_parser, remove_command),
    "list": (build_list_parser, list_command),
    "show": (build_show_parser, show_command),
    "refresh": (build_refresh_parser, refresh_command),
    # Phase 9 adds: "add_endorsement": (build_add_endorsement_parser, add_endorsement_command)
}
# Dispatcher catches ValidationError → format_validation_error → exit 2 (NOT exit 1).
# FileNotFoundError → exit 1. Other exceptions propagate.
```

From cli/add_ticker.py (Pattern to mirror in cli/add_endorsement.py):
```python
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def build_X_parser(p: argparse.ArgumentParser) -> None:
    p.add_argument("--flag", ...)

def X_command(args: argparse.Namespace) -> int:
    # Build Pydantic model (raises ValidationError → caught by dispatcher → exit 2)
    # Append via log helper (raises ValueError on bad input)
    # Print success message; return 0
```

From frontend/src/lib/fetchSnapshot.ts (Reuse for endorsements):
```typescript
export const RAW_BASE: string  // 'https://raw.githubusercontent.com/${GH_USER}/${GH_REPO}/main'
export class FetchNotFoundError extends Error  // 404 path — return [] for endorsements
export class SchemaMismatchError extends Error  // zod parse failure — bubble up
export async function fetchAndParse<T>(url: string, schema: ZodSchema<T>): Promise<T>
// fetchAndParse parses ONE JSON object. For JSONL (line-delimited) we fetch as
// text + split + parse each line manually (loadEndorsements pattern).
```

From frontend/src/lib/useRefreshData.ts (TanStack hook pattern):
```typescript
import { keepPreviousData, useQuery } from '@tanstack/react-query'
useQuery({
  queryKey: ['refresh', symbol],
  queryFn: () => fetchAndParse(...),
  staleTime: 5 * 60 * 1000,
  placeholderData: keepPreviousData,
  retry: 1,
  enabled: symbol.length > 0,
})
```

From frontend/src/routes/DecisionRoute.tsx (mount sequence — current order after Phase 8):
```tsx
<RecommendationBanner ... />        // line 173
<CurrentPriceDelta ... />            // line 183 — Phase 8 hero (UNCHANGED)
<DriversList ... />                  // line 194
<Separator />
<DissentPanel dissent={dec.dissent} />   // line 199 — INSERT EndorsementsList AFTER THIS
{/* PHASE 9 INSERT: <EndorsementsList symbol={symbol} /> here */}
{dec.open_observation && ( ... )}    // open_observation block
```
**Mount lock:** EndorsementsList renders immediately AFTER `<DissentPanel />`, BEFORE the
open_observation conditional. CONTEXT phrasing "between DissentPanel and CurrentPriceDelta"
refers to the conceptual ordering pair — RESEARCH Pattern 6 makes the placement explicit.
CurrentPriceDelta stays as the Phase 8 hero immediately under the RecommendationBanner.

From frontend/src/schemas/refresh.ts (zod parity convention):
```typescript
import { z } from 'zod'
export const Schema = z.object({
  schema_version: z.literal(1),  // strict — rejects v0 / v2+
  ticker: z.string().min(1),
  // ...
})
export type T = z.infer<typeof Schema>
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Python — Endorsement schema + JSONL log + flag-only CLI + 25 tests</name>
  <files>
    analysts/endorsement_schema.py,
    endorsements/__init__.py,
    endorsements/log.py,
    cli/add_endorsement.py,
    cli/main.py,
    endorsements.jsonl,
    tests/analysts/test_endorsement_schema.py,
    tests/endorsements/__init__.py,
    tests/endorsements/test_log.py,
    tests/cli/test_add_endorsement.py
  </files>
  <behavior>
    **tests/analysts/test_endorsement_schema.py (~10 tests):**
    - test_happy_minimal — required fields only (ticker, source, date, price_at_call, captured_at) → valid; notes defaults to ""
    - test_happy_full — all fields including notes → valid
    - test_schema_version_default_is_1 — omitting schema_version → instance has schema_version == 1
    - test_schema_version_locked_rejects_2 — `Endorsement(schema_version=2, ...)` → ValidationError (Literal mismatch)
    - test_schema_version_locked_rejects_0 — schema_version=0 → ValidationError
    - test_ticker_normalized_brk_b — `ticker="brk.b"` → instance.ticker == "BRK-B"
    - test_ticker_normalized_aapl_lower — `ticker="aapl"` → "AAPL"
    - test_ticker_invalid_raises — `ticker="!!!"` → ValidationError naming `ticker`
    - test_price_must_be_positive — `price_at_call=0` and `=-1` both → ValidationError (gt=0)
    - test_source_min_length — `source=""` → ValidationError; `source="x"` → ok
    - test_notes_max_length — `notes="a" * 2001` → ValidationError; `"a" * 2000` → ok
    - test_extra_field_forbidden — `Endorsement(..., bogus="x")` → ValidationError (extra="forbid")
    - test_date_field_is_python_date — `date=date(2026, 4, 15)` → instance.date is a `datetime.date` (not str)
    - test_model_dump_json_roundtrip — `Endorsement.model_validate_json(e.model_dump_json())` round-trips equal

    **tests/endorsements/test_log.py (~6 tests):**
    - test_append_creates_file — empty path → first append creates the file with one JSON line + trailing newline
    - test_append_appends_to_existing — second append leaves first line intact + adds second
    - test_append_writes_sort_keys — line is `json.dumps(..., sort_keys=True)` so keys are alphabetical (assert raw line bytes match expected)
    - test_load_returns_empty_when_file_missing — `load_endorsements(missing_path)` → []
    - test_load_skips_blank_lines — file with `{...}\n\n{...}\n` parses to 2 records
    - test_load_validates_each_line — file with one malformed JSON line → ValidationError or json.JSONDecodeError raised on load
    - test_round_trip_via_pydantic — append e1, e2; load → [e1, e2] preserving field equality (date type, price float, etc.)

    **tests/cli/test_add_endorsement.py (~9 tests) — invokes via cli.main.main(argv=[...]):**
    - test_happy_path — all flags → exit 0; endorsements.jsonl has 1 line; line parses back to the expected Endorsement
    - test_ticker_normalized — `--ticker brk.b` → file contains `"ticker": "BRK-B"`
    - test_default_notes_empty — omit `--notes` → file contains `"notes": ""`
    - test_invalid_ticker_exits_2 — `--ticker "!!!"` → exit 2; file UNCHANGED (or absent)
    - test_invalid_price_exits_2 — `--price -42` → exit 2 (Pydantic ValidationError caught by dispatcher); file UNCHANGED
    - test_invalid_date_exits_nonzero — `--date "not-a-date"` → exit 2 or 1 (date.fromisoformat raises ValueError; choose dispatcher path: catch in command and re-raise as ValidationError-equivalent OR let argparse-level fail; document chosen contract in test); file UNCHANGED
    - test_blank_source_exits_2 — `--source ""` → exit 2; file UNCHANGED
    - test_captured_at_auto_populated — happy path → record's `captured_at` is parseable as ISO 8601 UTC datetime within last 60 seconds
    - test_atomic_on_failure — invalid input on a SECOND call (after a successful first call) → file still has exactly 1 line (the first record); the failed second call did NOT append
    - test_subcommand_registered — `cli.main.SUBCOMMANDS["add_endorsement"]` exists and points to (build_add_endorsement_parser, add_endorsement_command) tuple

    All Python tests use a `tmp_endorsements_path` fixture (pytest tmp_path / "endorsements.jsonl") passed via `--path`. Production code in cli/add_endorsement.py uses `Path("endorsements.jsonl")` default.
  </behavior>
  <action>
    **RED phase — write failing tests FIRST, then commit, then GREEN.**

    **Step 1 (RED): Create test files only. Run: `python -m pytest tests/analysts/test_endorsement_schema.py tests/endorsements/test_log.py tests/cli/test_add_endorsement.py -q` — expect ImportError / collection failure (modules don't exist yet). Commit RED:**
    ```
    test(09-01): add failing tests for endorsement schema + log + CLI (ENDORSE-01..03)
    ```

    **Step 2 (GREEN): Implement production code in this exact order:**

    **(a) `analysts/endorsement_schema.py` (~50 LOC):**
    ```python
    # novel-to-this-project — endorsement signal capture for newsletter/service calls.
    """Pydantic v2 Endorsement record. Append-only; performance math deferred to v1.x.

    schema_version: Literal[1] = 1 is LOAD-BEARING — v1.x ENDORSE-04..07 will bump
    to Literal[2] (or introduce Union[V1Endorsement, V2Endorsement]) so v1 records
    cannot be silently misread as "0% performance" once perf fields exist.
    """
    from __future__ import annotations
    from datetime import date as date_type, datetime
    from typing import Literal
    from pydantic import BaseModel, ConfigDict, Field, field_validator
    from analysts.schemas import normalize_ticker

    class Endorsement(BaseModel):
        model_config = ConfigDict(extra="forbid")
        schema_version: Literal[1] = 1
        ticker: str
        source: str = Field(min_length=1, max_length=200)
        date: date_type
        price_at_call: float = Field(gt=0)
        notes: str = Field(default="", max_length=2000)
        captured_at: datetime

        @field_validator("ticker", mode="before")
        @classmethod
        def _normalize_ticker_field(cls, v: object) -> str:
            norm = normalize_ticker(v) if isinstance(v, str) else None
            if norm is None:
                raise ValueError(f"invalid ticker {v!r}")
            return norm
    ```
    NOTE: Match CONTEXT lock — `source` max_length=200 (CONTEXT) NOT 100 (RESEARCH); CONTEXT supersedes when they diverge.

    **(b) `endorsements/__init__.py`:** empty file (package marker).

    **(c) `endorsements/log.py` (~60 LOC):** mirror `routine/memory_log.py` discipline. Header: `# Pattern adapted from routine/memory_log.py — JSONL atomic append`.
    ```python
    """endorsements.log — append-only JSONL writer for Endorsement records.
    Pattern adapted from routine/memory_log.py: mkdir parents=True, mode='a',
    sort_keys=True, one record per line.
    """
    from __future__ import annotations
    import json
    from pathlib import Path
    from typing import Final
    from analysts.endorsement_schema import Endorsement

    DEFAULT_PATH: Final[Path] = Path("endorsements.jsonl")

    def append_endorsement(e: Endorsement, *, path: Path | None = None) -> None:
        target = path if path is not None else DEFAULT_PATH
        target.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(e.model_dump(mode="json"), sort_keys=True) + "\n"
        with target.open("a", encoding="utf-8") as f:
            f.write(line)

    def load_endorsements(path: Path | None = None) -> list[Endorsement]:
        target = path if path is not None else DEFAULT_PATH
        if not target.exists():
            return []
        out: list[Endorsement] = []
        for line in target.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(Endorsement.model_validate_json(line))
        return out
    ```

    **(d) `cli/add_endorsement.py` (~80 LOC):** mirror `cli/add_ticker.py`. Header: `# Pattern adapted from cli/add_ticker.py — flag-only argparse + Pydantic validation`.
    Required flags: `--ticker`, `--source`, `--date`, `--price`. Optional: `--notes` (default ""), `--path` (default `Path("endorsements.jsonl")`).
    ```python
    def _now_iso_utc() -> datetime:
        return datetime.now(timezone.utc)

    def build_add_endorsement_parser(p: argparse.ArgumentParser) -> None:
        p.add_argument("--ticker", required=True, help="ticker (BRK.B → BRK-B)")
        p.add_argument("--source", required=True, help="newsletter/service name")
        p.add_argument("--date", required=True, help="ISO date YYYY-MM-DD")
        p.add_argument("--price", type=float, required=True, dest="price_at_call",
                       help="price when endorsement issued")
        p.add_argument("--notes", default="", help="freeform notes (≤2000 chars)")
        p.add_argument("--path", type=Path, default=Path("endorsements.jsonl"))

    def add_endorsement_command(args: argparse.Namespace) -> int:
        # date.fromisoformat raises ValueError on malformed input; let it propagate
        # to the dispatcher (cli/main.py catches ValidationError as exit 2; for
        # ValueError from non-Pydantic source, wrap into a ValidationError-style
        # message via raise — simpler: call Endorsement(...) which validates date
        # transitively if we pass a string and rely on pydantic's date coercion).
        # SIMPLEST: parse date here; on ValueError, print stderr + return 2.
        try:
            call_date = date.fromisoformat(args.date)
        except ValueError as exc:
            print(f"error: invalid --date {args.date!r}: {exc}", file=sys.stderr)
            return 2
        e = Endorsement(
            ticker=args.ticker,
            source=args.source,
            date=call_date,
            price_at_call=args.price_at_call,
            notes=args.notes,
            captured_at=_now_iso_utc(),
        )
        append_endorsement(e, path=args.path)
        print(f"recorded endorsement: {e.ticker} from {e.source} ({e.date.isoformat()})")
        return 0
    ```
    Pydantic ValidationError raised inside `Endorsement(...)` propagates to `cli/main.py:68-70` which prints + returns exit 2 — atomic-on-success holds (append never reached).

    **(e) `cli/main.py` extension:** add ONE entry to SUBCOMMANDS dict + ONE import line. Do NOT touch other dispatcher code.
    ```python
    from cli.add_endorsement import add_endorsement_command, build_add_endorsement_parser
    # ... in SUBCOMMANDS dict:
    "add_endorsement": (build_add_endorsement_parser, add_endorsement_command),
    ```

    **(f) `endorsements.jsonl`:** create empty file at repo root. Verify `.gitignore` does NOT include this path (memory/*.jsonl IS gitignored — endorsements.jsonl IS NOT — see CONTEXT line 64). If `.gitignore` matches it, surface the conflict in the SUMMARY (do not silently fix without user confirmation).

    **Step 3 (GREEN): Run tests until green.**
    ```
    python -m pytest tests/analysts/test_endorsement_schema.py tests/endorsements/test_log.py tests/cli/test_add_endorsement.py -q
    ```
    All 25 tests pass. Then run FULL backend suite to confirm zero regression:
    ```
    python -m pytest -q
    ```
    Expected: 704 (Phase 8 baseline) + 25 (Phase 9) = ~729 passing. Commit GREEN:
    ```
    feat(09-01): implement endorsement schema + JSONL log + add_endorsement CLI (ENDORSE-01, ENDORSE-02)
    ```

    **Provenance markers (verify before commit):**
    - `analysts/endorsement_schema.py` line 1: `# novel-to-this-project — endorsement signal capture for newsletter/service calls.`
    - `endorsements/log.py` line 1: `# Pattern adapted from routine/memory_log.py — JSONL atomic append`
    - `cli/add_endorsement.py` line 1: `# Pattern adapted from cli/add_ticker.py — flag-only argparse + Pydantic validation`
    - `endorsements/__init__.py`: empty (no marker needed — package marker)
    - Test files: no marker required (tests are not subject to scripts/check_provenance.py per Phase 8 audit).

    **Anti-patterns to avoid:**
    - DO NOT add interactive prompt mode (flag-only — CONTEXT lock).
    - DO NOT add duplicate detection (append-only purity in v1; deferred to v1.x).
    - DO NOT compute or render any performance number anywhere (CONTEXT lock).
    - DO NOT extend SUBCOMMANDS naming convention — use `add_endorsement` (underscore matches add_ticker / refresh symmetry).
    - DO NOT add `--force` flag (deferred — v1.x ENDORSE-07 polish).
    - DO NOT touch existing CLI commands or dispatcher exception handling.
  </action>
  <verify>
    <automated>python -m pytest tests/analysts/test_endorsement_schema.py tests/endorsements/test_log.py tests/cli/test_add_endorsement.py -q</automated>
    Manual sanity: `python -m markets add_endorsement --ticker AAPL --source "Test" --date 2026-04-15 --price 178.42 --notes "smoke" --path /tmp/e.jsonl && cat /tmp/e.jsonl` — one JSON line with sorted keys.
    Provenance: `python scripts/check_provenance.py` (Phase 8 walker) — passes for all 3 new production files.
    Full suite: `python -m pytest -q` — green at ~729 tests (704 baseline + 25 new).
  </verify>
  <done>
    - 25 Python tests passing (10 schema + 6 log + 9 CLI; counts ±2 acceptable)
    - `analysts/endorsement_schema.py` exports `Endorsement` with `schema_version: Literal[1] = 1`
    - `endorsements/log.py` exports `append_endorsement` + `load_endorsements`; mirrors memory_log discipline
    - `cli/add_endorsement.py` exports `build_add_endorsement_parser` + `add_endorsement_command`; flag-only; atomic-on-success (no append on ValidationError)
    - `cli/main.py` SUBCOMMANDS extended with `"add_endorsement"` entry
    - `endorsements.jsonl` exists at repo root, empty, NOT in .gitignore
    - Provenance markers present on all 3 new production files; check_provenance.py passes
    - Full backend suite green at ~729 tests; zero regression
    - Two commits landed: RED (test scaffold) + GREEN (implementation)
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Frontend — zod schema + TanStack fetcher (90-day filter + sort) + 15 tests</name>
  <files>
    frontend/src/schemas/endorsement.ts,
    frontend/src/schemas/__tests__/endorsement.test.ts,
    frontend/src/lib/loadEndorsements.ts,
    frontend/src/lib/__tests__/loadEndorsements.test.ts
  </files>
  <behavior>
    **frontend/src/schemas/__tests__/endorsement.test.ts (~6 tests):**
    - parses_valid_endorsement — happy-path object → safeParse success; .data fields equal input
    - rejects_schema_version_2 — `{schema_version: 2, ...}` → safeParse failure on schema_version
    - rejects_schema_version_0 — `{schema_version: 0, ...}` → safeParse failure
    - rejects_negative_price — `price_at_call: -10` → failure on price_at_call
    - rejects_blank_source — `source: ""` → failure (min(1))
    - rejects_notes_too_long — `notes: "x".repeat(2001)` → failure (max 2000)
    - rejects_invalid_date_format — `date: "April 15 2026"` → failure (regex /^\d{4}-\d{2}-\d{2}$/)
    - accepts_iso_date_string — `date: "2026-04-15"` → success
    - accepts_empty_notes — `notes: ""` → success
    - rejects_extra_unknown_field — handled by zod default (passthrough vs strict): use `.strict()` so unknown keys fail. Test confirms.

    **frontend/src/lib/__tests__/loadEndorsements.test.ts (~9 tests):**
    Mock `fetch` via vi.spyOn(globalThis, 'fetch') / vi.fn().
    - fetchEndorsementsJsonl_returns_empty_on_404 — fetch resolves with `{ok: false, status: 404}` → returns []
    - fetchEndorsementsJsonl_throws_on_other_5xx — `{ok: false, status: 500}` → throws Error
    - fetchEndorsementsJsonl_parses_multiple_lines — text with 3 valid JSONL lines → returns 3 Endorsement objects
    - fetchEndorsementsJsonl_skips_blank_lines — text `"{json}\n\n{json}\n"` → returns 2 records
    - fetchEndorsementsJsonl_throws_SchemaMismatchError_on_invalid_line — one line with schema_version: 99 → throws SchemaMismatchError
    - fetchEndorsementsJsonl_handles_trailing_newline — text ending in `\n` → no JSON.parse('') crash
    - filter_by_ticker_active — array of 4 records (2x AAPL, 1x MSFT, 1x GOOGL); filter('AAPL') → 2 records
    - filter_excludes_records_older_than_90_days — record with date = today-91d → excluded; date = today-89d → included
    - sort_descending_by_date — 3 records out of order → result array `dates[i] >= dates[i+1]`
    - filter_uses_call_date_not_captured_at — record with date=today-100d, captured_at=today → EXCLUDED (filter on `date`, NOT `captured_at`); covers Pitfall #2 from RESEARCH

    Note: the 90-day filter + ticker filter + sort live in a `select` callback (or pure helper `filterRecent90`); tests can call the helper directly OR use the hook with a QueryClient wrapper. Prefer pure-helper testing for unit-level + queryFn testing for fetch integration — split into the two test files above (schema test for schema; loadEndorsements test for fetch + filter + sort).
  </behavior>
  <action>
    **RED phase — write failing tests FIRST, commit, then GREEN.**

    **Step 1 (RED):** Create test files only. Run: `cd frontend && pnpm test:unit src/schemas/__tests__/endorsement.test.ts src/lib/__tests__/loadEndorsements.test.ts --run` — expect import-resolution failure. Commit:
    ```
    test(09-01): add failing frontend tests for endorsement schema + loader (ENDORSE-03)
    ```

    **Step 2 (GREEN): Implement production code.**

    **(a) `frontend/src/schemas/endorsement.ts` (~30 LOC):** mirror `frontend/src/schemas/refresh.ts`. Header: `// novel-to-this-project — endorsement record schema mirroring analysts/endorsement_schema.py`.
    ```typescript
    import { z } from 'zod'

    export const EndorsementSchema = z.object({
      schema_version: z.literal(1),  // strict — rejects v0 and v2+
      ticker: z.string().min(1),
      source: z.string().min(1).max(200),
      date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
      price_at_call: z.number().positive(),
      notes: z.string().max(2000),
      captured_at: z.string().min(1),  // ISO 8601 — permissive parse (matches refresh.ts convention)
    }).strict()  // reject extra keys (parity with Pydantic extra='forbid')
    export type Endorsement = z.infer<typeof EndorsementSchema>
    ```
    NOTE: `source` max 200 chars (CONTEXT lock; supersedes RESEARCH 100). `.strict()` to mirror Pydantic `extra='forbid'`.

    **(b) `frontend/src/lib/loadEndorsements.ts` (~70 LOC):** Header: `// novel-to-this-project — JSONL loader + 90-day filter + ticker filter + date-desc sort for endorsements`.
    ```typescript
    import { useQuery } from '@tanstack/react-query'
    import { RAW_BASE, SchemaMismatchError } from '@/lib/fetchSnapshot'
    import { EndorsementSchema, type Endorsement } from '@/schemas/endorsement'

    export const endorsementsUrl = (): string => `${RAW_BASE}/endorsements.jsonl`

    export async function fetchEndorsementsJsonl(): Promise<Endorsement[]> {
      const url = endorsementsUrl()
      const res = await fetch(url, { headers: { Accept: 'text/plain' } })
      if (res.status === 404) return []  // file optional — never crash
      if (!res.ok) throw new Error(`Fetch ${url} failed: ${res.status}`)
      const text = await res.text()
      const out: Endorsement[] = []
      for (const line of text.split('\n')) {
        if (!line.trim()) continue  // skip blank + trailing newline
        const json: unknown = JSON.parse(line)
        const result = EndorsementSchema.safeParse(json)
        if (!result.success) throw new SchemaMismatchError(url, result.error)
        out.push(result.data)
      }
      return out
    }

    export function filterRecent90(all: Endorsement[], symbol: string, now: Date = new Date()): Endorsement[] {
      const cutoff = now.getTime() - 90 * 24 * 60 * 60 * 1000
      const sym = symbol.toUpperCase()
      return all
        .filter((e) => e.ticker === sym)
        .filter((e) => new Date(e.date + 'T00:00:00Z').getTime() >= cutoff)
        .sort((a, b) => b.date.localeCompare(a.date))
    }

    export function useEndorsements(symbol: string) {
      return useQuery<Endorsement[]>({
        queryKey: ['endorsements'],  // global key; full file is small; client filters
        queryFn: fetchEndorsementsJsonl,
        staleTime: 10 * 60 * 1000,
        enabled: symbol.length > 0,
        select: (all) => filterRecent90(all, symbol),
      })
    }
    ```
    Pattern source: `useRefreshData.ts` (TanStack idiom) + `fetchSnapshot.ts` (RAW_BASE + SchemaMismatchError reuse). NO new dependencies. NO new error classes — reuse `SchemaMismatchError`.

    **Step 3 (GREEN):** Run unit tests:
    ```
    cd frontend && pnpm test:unit src/schemas/__tests__/endorsement.test.ts src/lib/__tests__/loadEndorsements.test.ts --run
    ```
    All 15 tests pass. Run typecheck: `cd frontend && pnpm typecheck` — clean. Commit:
    ```
    feat(09-01): implement frontend endorsement zod schema + loader (90-day filter + sort) (ENDORSE-03)
    ```

    **Provenance markers (verify):**
    - `frontend/src/schemas/endorsement.ts` line 1: `// novel-to-this-project — ...`
    - `frontend/src/lib/loadEndorsements.ts` line 1: `// novel-to-this-project — ...`

    **Anti-patterns to avoid:**
    - DO NOT introduce a new error class (reuse `SchemaMismatchError` + plain `Error` for non-404 non-OK responses).
    - DO NOT use `discriminatedUnion` on schema_version (only one variant in v1; CONTEXT defers v1.x v2 discriminator).
    - DO NOT filter by `captured_at` (Pitfall #2 — filter is on `date`, the call date).
    - DO NOT cache-bust the URL (consistency with snapshot fetch — Pitfall #3).
    - DO NOT split per-ticker files (single JSONL — CONTEXT lock).
  </action>
  <verify>
    <automated>cd frontend && pnpm test:unit src/schemas/__tests__/endorsement.test.ts src/lib/__tests__/loadEndorsements.test.ts --run</automated>
    Typecheck: `cd frontend && pnpm typecheck` — clean.
    Full unit suite: `cd frontend && pnpm test:unit --run` — green at ~275 tests (260 baseline + 15 new); zero regression.
  </verify>
  <done>
    - 15 vitest tests passing (~6 schema + ~9 loader; counts ±2 acceptable)
    - `frontend/src/schemas/endorsement.ts` exports `EndorsementSchema` (z.literal(1) on schema_version) + `Endorsement` type
    - `frontend/src/lib/loadEndorsements.ts` exports `endorsementsUrl`, `fetchEndorsementsJsonl`, `filterRecent90`, `useEndorsements`
    - 404 returns []; non-404 non-OK throws Error; invalid line throws SchemaMismatchError
    - 90-day filter uses `date` field (NOT captured_at); sort is date-descending
    - Typecheck clean; full vitest suite green at ~275 tests
    - Two commits landed: RED + GREEN
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Frontend — EndorsementsList component + DecisionRoute mount + Playwright E2E (~9 tests)</name>
  <files>
    frontend/src/components/EndorsementsList.tsx,
    frontend/src/components/__tests__/EndorsementsList.test.tsx,
    frontend/src/routes/DecisionRoute.tsx,
    frontend/tests/e2e/endorsements.spec.ts
  </files>
  <behavior>
    **frontend/src/components/__tests__/EndorsementsList.test.tsx (~6 tests):**
    Use existing test harness with `QueryClientProvider` wrapper + `vi.mock('@/lib/loadEndorsements')` to inject controlled hook returns.
    - renders_loading_state — useEndorsements returns `{isLoading: true}` → renders a skeleton/placeholder element with data-testid='endorsements-loading'
    - renders_empty_state_with_cta — hook returns `{data: []}` → renders muted text "No endorsements captured for AAPL in the last 90 days. Use `markets add_endorsement` to capture one."
    - renders_populated_state_card_per_endorsement — hook returns 3 records → DOM has 3 cards with data-testid='endorsement-card' (or similar selector)
    - renders_card_fields — populated card shows source, formatted date, formatted price, notes, captured_at relative timestamp ("captured 3 days ago" / use `Intl.RelativeTimeFormat` or simple helper)
    - renders_no_performance_number — populated card MUST NOT contain any text matching `/%|alpha|gain|loss|return|perf/i` (assert via `expect(container.textContent).not.toMatch(...)`)
    - renders_in_descending_date_order — 3 records with dates 2026-04-01, 2026-04-15, 2026-04-10 → DOM order is 2026-04-15, 2026-04-10, 2026-04-01
    - renders_error_state_quietly — hook returns `{isError: true}` → renders muted "Endorsements unavailable" notice (preserves layout; does not crash; matches Phase 8 CurrentPriceDelta failure-fallback discipline)

    **DecisionRoute test extension (in `frontend/src/routes/__tests__/DecisionRoute.test.tsx`):**
    - mounts_endorsements_list_after_dissent_panel — render DecisionRoute; assert `<EndorsementsList symbol={...} />` is present in the DOM AFTER the DissentPanel (use queryAllByTestId order check OR document.querySelectorAll positional assertion)
    - existing DecisionRoute tests continue to pass (CurrentPriceDelta still hero, DissentPanel still rendered).

    **frontend/tests/e2e/endorsements.spec.ts (~3 specs on chromium-desktop):**
    Use Playwright `page.route()` to mock the JSONL fetch (mirror `resilience.spec.ts` pattern).
    - empty_state — route mocks 404 on endorsements.jsonl → navigate to /decision/AAPL/today → assert empty-state copy visible + DissentPanel still renders + CurrentPriceDelta still renders
    - populated_state — route mocks 200 with 3 JSONL lines (2x AAPL within 90d, 1x MSFT outside scope) → navigate to /decision/AAPL/today → assert exactly 2 cards rendered (MSFT filtered) in date-desc order; assert NO `%` symbol or "performance" text anywhere within the EndorsementsList region
    - 90_day_cutoff — route mocks 200 with 3 AAPL records (date today-30d, today-89d, today-95d) → navigate; assert 2 cards visible (today-95d filtered); assert most-recent-first order

    Run on `chromium-desktop` project only (Playwright spec count: 72 baseline + 3 = 75; matches VALIDATION expected baseline).
  </behavior>
  <action>
    **RED phase — write failing tests FIRST, commit, then GREEN.**

    **Step 1 (RED):** Create the component test file + Playwright spec + extend DecisionRoute test (the new mount-order assertion will fail until production code lands). Run:
    ```
    cd frontend && pnpm test:unit src/components/__tests__/EndorsementsList.test.tsx src/routes/__tests__/DecisionRoute.test.tsx --run
    cd frontend && pnpm test:e2e --project=chromium-desktop -g 'endorsements'
    ```
    Both red. Commit:
    ```
    test(09-01): add failing component + DecisionRoute mount + Playwright tests (ENDORSE-03)
    ```

    **Step 2 (GREEN): Implement production code.**

    **(a) `frontend/src/components/EndorsementsList.tsx` (~100 LOC):** Header: `// novel-to-this-project — Decision-Route panel rendering last-90-days endorsements per ticker. NO performance number per ENDORSE-03 (deferred to v1.x ENDORSE-06).`
    ```tsx
    import { useEndorsements } from '@/lib/loadEndorsements'
    import type { Endorsement } from '@/schemas/endorsement'

    interface Props {
      symbol: string
    }

    export function EndorsementsList({ symbol }: Props) {
      const { data, isLoading, isError } = useEndorsements(symbol)

      if (isLoading) {
        return (
          <section
            className="rounded-md border border-border bg-surface px-6 py-4"
            data-testid="endorsements-loading"
          >
            <span className="font-mono text-xs uppercase tracking-wider text-fg-muted">
              Endorsements
            </span>
            <p className="mt-2 text-sm text-fg-muted">Loading…</p>
          </section>
        )
      }

      if (isError) {
        return (
          <section
            className="rounded-md border border-border bg-surface px-6 py-4"
            data-testid="endorsements-error"
          >
            <span className="font-mono text-xs uppercase tracking-wider text-fg-muted">
              Endorsements
            </span>
            <p className="mt-2 text-sm text-fg-muted">Endorsements unavailable</p>
          </section>
        )
      }

      const items = data ?? []

      return (
        <section
          className="rounded-md border border-border bg-surface px-6 py-4"
          data-testid="endorsements-list"
        >
          <span className="font-mono text-xs uppercase tracking-wider text-fg-muted">
            Endorsements (last 90 days)
          </span>
          {items.length === 0 ? (
            <p className="mt-3 text-sm text-fg-muted leading-relaxed">
              No endorsements captured for {symbol.toUpperCase()} in the last 90 days.
              Use <code className="font-mono text-xs">markets add_endorsement</code> to capture one.
            </p>
          ) : (
            <ul className="mt-3 flex flex-col gap-4">
              {items.map((e) => (
                <EndorsementCard key={`${e.source}-${e.date}-${e.captured_at}`} e={e} />
              ))}
            </ul>
          )}
        </section>
      )
    }

    function EndorsementCard({ e }: { e: Endorsement }) {
      return (
        <li
          className="rounded-md border border-border bg-bg p-4"
          data-testid="endorsement-card"
        >
          <header className="text-sm font-medium text-fg">{e.source}</header>
          <p className="mt-1 text-xs text-fg-muted">
            {e.date} · ${e.price_at_call.toFixed(2)}
          </p>
          {e.notes && (
            <p className="mt-2 text-sm text-fg leading-relaxed">{e.notes}</p>
          )}
          <p className="mt-2 text-xs text-fg-muted">
            captured {formatRelative(e.captured_at)}
          </p>
        </li>
      )
    }

    function formatRelative(iso: string): string {
      const then = new Date(iso).getTime()
      const days = Math.floor((Date.now() - then) / (24 * 60 * 60 * 1000))
      if (days < 1) return 'today'
      if (days === 1) return '1 day ago'
      return `${days} days ago`
    }
    ```
    **Notion-Clean palette discipline:** every color is a CSS variable token (`text-fg`, `text-fg-muted`, `border-border`, `bg-surface`, `bg-bg`). ZERO inline hex. ZERO performance number. Verify by `grep -E "(#[0-9a-fA-F]{3,6}|%|alpha|gain|return|perf)" frontend/src/components/EndorsementsList.tsx` returning no production-code hits (only matches in code comments referencing "performance" are acceptable IF clearly marked as exclusion notes).

    **(b) `frontend/src/routes/DecisionRoute.tsx` extension (~5 lines):** Insert `<EndorsementsList symbol={symbol} />` immediately AFTER `<DissentPanel dissent={dec.dissent} />` (line 199), BEFORE the `{dec.open_observation && ( ... )}` conditional. Do NOT touch other mount sequence. Add the import at the top alongside existing `import { DissentPanel } from '@/components/DissentPanel'` line.
    ```tsx
    // After line 199 — between DissentPanel and open_observation block:
    <EndorsementsList symbol={symbol} />
    ```
    **Mount lock confirmed:** RecommendationBanner → CurrentPriceDelta → DriversList → Separator → DissentPanel → **EndorsementsList (NEW)** → open_observation block. CurrentPriceDelta stays as the Phase 8 hero (CONTEXT phrasing "between DissentPanel and CurrentPriceDelta" refers to the conceptual pair; RESEARCH Pattern 6 makes it explicit — AFTER DissentPanel).

    **Step 3 (GREEN):** Run all tests:
    ```
    cd frontend && pnpm test:unit --run
    cd frontend && pnpm test:e2e --project=chromium-desktop -g 'endorsements'
    cd frontend && pnpm typecheck
    ```
    All green. Then run REQUIREMENTS.md flip in this same task (saves a commit):

    **(c) Update `.planning/REQUIREMENTS.md`:** flip ENDORSE-01, ENDORSE-02, ENDORSE-03 from `- [ ]` to `- [x]` (lines 82-84) AND update the Traceability table at lines 205-207 from `Pending` to `Complete`. Update the closing footer date stamp.

    Commit:
    ```
    feat(09-01): mount EndorsementsList in DecisionRoute + Playwright E2E (ENDORSE-03)
    ```

    Then a docs commit:
    ```
    docs(09-01): flip ENDORSE-01..03 to complete in REQUIREMENTS.md (Phase 9 done — v1 complete)
    ```

    **Provenance markers (verify):**
    - `frontend/src/components/EndorsementsList.tsx` line 1: `// novel-to-this-project — ...`
    - `frontend/src/routes/DecisionRoute.tsx` line for new import + JSX block carries inline comment `{/* Phase 9 — ENDORSE-03 */}` for grep continuity.

    **Anti-patterns to avoid:**
    - DO NOT render `%` or any performance text. (Test guards this.)
    - DO NOT render edit/delete affordances (append-only purity).
    - DO NOT alter DissentPanel or CurrentPriceDelta render or position.
    - DO NOT introduce a new color/spacing variable — reuse the Notion-Clean palette already in use.
    - DO NOT mock fetch in production code — Playwright + vi.mock at test layer only.
    - DO NOT add a "no captured_at yet" defensive branch — the schema requires captured_at.
  </action>
  <verify>
    <automated>cd frontend && pnpm test:unit --run && pnpm test:e2e --project=chromium-desktop -g 'endorsements' && pnpm typecheck</automated>
    Visual check (manual, after Wave 1 ship): `cd frontend && pnpm dev` → open `/decision/AAPL/today` with `endorsements.jsonl` populated locally → confirm card spacing, hairline borders, no inline color drift, no performance number.
    Provenance: `python scripts/check_provenance.py` (Phase 8 walker) — passes.
    Full integration: `python -m pytest -q && cd frontend && pnpm test:unit --run && pnpm test:e2e` — green across the board.
  </verify>
  <done>
    - ~9 frontend tests passing (~6 component + ~1 DecisionRoute mount-order extension + 3 Playwright)
    - `frontend/src/components/EndorsementsList.tsx` renders 4 states: loading / error / empty (with CTA copy) / populated (cards in date-desc order)
    - Notion-Clean palette discipline holds: `grep -E "#[0-9a-fA-F]{3,6}" frontend/src/components/EndorsementsList.tsx` returns nothing in production code
    - NO performance number anywhere: regex assertion in tests + grep in production code
    - DecisionRoute mounts EndorsementsList immediately after DissentPanel (existing tests still pass; new mount-order test passes)
    - Playwright spec count: 72 → 75 (3 new specs on chromium-desktop only)
    - vitest count: ~275 → ~281 (Phase 9 task 2 + task 3 cumulative; ±2 acceptable)
    - REQUIREMENTS.md flipped: ENDORSE-01..03 marked complete; Traceability table updated; footer date-stamped
    - Provenance markers present on EndorsementsList.tsx; check_provenance.py passes
    - Three commits landed in this task: RED + GREEN (component+mount+E2E) + docs (REQUIREMENTS flip)
  </done>
</task>

</tasks>

<verification>

## Phase 9 Closeout Verification

After all 3 tasks complete, run the comprehensive verification:

1. **Backend full suite:** `python -m pytest -q` — green at ~729 tests (704 baseline + 25 new)
2. **Frontend unit suite:** `cd frontend && pnpm test:unit --run` — green at ~281 tests (260 baseline + 21 new)
3. **Playwright suite:** `cd frontend && pnpm test:e2e` — green at ~75 specs (72 baseline + 3 new on chromium-desktop)
4. **Typecheck:** `cd frontend && pnpm typecheck` — clean
5. **Provenance walker:** `python scripts/check_provenance.py` — passes (4 new production files: endorsement_schema.py, log.py, add_endorsement.py, endorsement.ts/loadEndorsements.ts/EndorsementsList.tsx all carry markers)
6. **CLI smoke test:** `python -m markets add_endorsement --ticker AAPL --source "Smoke Test" --date 2026-04-15 --price 178.42 --path /tmp/smoke.jsonl && cat /tmp/smoke.jsonl` — emits one sorted-keys JSON line + trailing newline; ticker upcased
7. **JSONL committed (not gitignored):** `git check-ignore endorsements.jsonl` — exits non-zero (file is NOT ignored). `git ls-files endorsements.jsonl` — file is tracked.
8. **REQUIREMENTS.md updated:** ENDORSE-01..03 are `[x]`; Traceability table shows `Complete` for all three.

## Manual Verification (post-deploy, optional pre-merge)

Two manual gates from VALIDATION.md (deferred to post-merge taste-check, not blocking plan close):
1. End-to-end CLI append + frontend render: after Vercel preview deploys with a populated `endorsements.jsonl`, open `/decision/AAPL/today` → endorsement card appears.
2. Notion-Clean visual taste-check: review `/decision/AAPL/today` rendering for card spacing, restraint, hairline borders, no inline color drift.

</verification>

<success_criteria>

Phase 9 plan execution is complete when:
- [x] **ENDORSE-01** closed: `endorsements.jsonl` at repo root (committed) accepts append via `Endorsement` Pydantic record `{ticker, source, date, price_at_call, notes, captured_at, schema_version: 1}`; atomic-on-success only.
- [x] **ENDORSE-02** closed: `markets add_endorsement --ticker --source --date --price [--notes]` CLI subcommand registered in cli/main.py SUBCOMMANDS; flag-only; ValidationError → exit 2 + actionable message + NO append.
- [x] **ENDORSE-03** closed: DecisionRoute mounts `<EndorsementsList symbol={symbol} />` immediately after DissentPanel; renders last 90 days for active ticker (date-desc); empty + populated + loading + error states; NO performance number anywhere.
- [x] schema_version Literal[1] = 1 lock holds on Pydantic AND zod sides (forces v1.x bump non-breakingly).
- [x] Append-only purity: zero edit/delete UI, zero duplicate detection, zero auto-capture (all v1.x deferred per CONTEXT).
- [x] Provenance markers present + check_provenance.py walker passes.
- [x] Notion-Clean palette discipline: zero inline hex in production frontend code.
- [x] Test counts: backend ~729, vitest ~281, Playwright ~75 (all green).
- [x] REQUIREMENTS.md flipped + Traceability table updated.
- [x] Phase 9 SUMMARY.md written; Phase 9 closes; **v1 complete**.

</success_criteria>

<output>
After completion, create `.planning/phases/09-endorsement-capture/09-01-endorsement-capture-SUMMARY.md` per `@C:/Users/Mohan/.claude/templates/summary.md` template.

Include in summary:
- Test counts (before → after for backend, vitest, Playwright)
- Provenance: 4 production files + their marker forms
- Schema version lock decision rationale (load-bearing for v1.x)
- File-ownership note: endorsements.jsonl COMMITTED at repo root (diverges from memory_log.jsonl gitignored)
- v1.x successor list (ENDORSE-04..07) clearly deferred — NOT in this phase
- v1 completion marker — Phase 9 closes the v1 ROADMAP (final phase)
</output>
