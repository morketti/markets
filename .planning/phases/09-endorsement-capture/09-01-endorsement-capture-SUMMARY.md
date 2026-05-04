---
phase: 09-endorsement-capture
plan: 01
subsystem: api
tags: [pydantic, zod, jsonl, cli, react, tanstack-query, playwright]

# Dependency graph
requires:
  - phase: 07-decision-support-view
    provides: DecisionRoute mount site (after DissentPanel) + RecommendationBanner / DriversList / DissentPanel composition order
  - phase: 08-mid-day-refresh-resilience
    provides: api/refresh.py + CurrentPriceDelta lock (preserves data-testid grep contract); routine/memory_log.py JSONL append pattern (mirrored verbatim in endorsements/log.py); scripts/check_provenance.py walker (now scans 49 files including the 4 new production files)
  - phase: 01-foundation
    provides: analysts/schemas.py normalize_ticker (single source of truth — reused via field_validator); cli/main.py SUBCOMMANDS dispatcher convention
provides:
  - Pydantic v2 Endorsement record with schema_version Literal[1] = 1 (forward-compat lock for v1.x)
  - endorsements/log.py append_endorsement + load_endorsements (atomic JSONL append; mirrors routine/memory_log.py)
  - cli/add_endorsement.py flag-only subcommand (atomic-on-success — Pydantic ValidationError → exit 2 + NO append)
  - frontend/src/schemas/endorsement.ts zod parity (z.literal(1) + .strict() mirroring extra='forbid')
  - frontend/src/lib/loadEndorsements.ts JSONL fetcher + 90-day filter on `date` (NOT captured_at) + date-desc sort + useEndorsements TanStack hook
  - frontend/src/components/EndorsementsList.tsx 4-state render (loading/error/empty/populated) — Notion-Clean palette only; NO performance number anywhere (regex-guarded)
  - DecisionRoute mount: EndorsementsList immediately AFTER DissentPanel
  - endorsements.jsonl committed at repo root (NOT gitignored — first-class signal, diverges from memory_log.jsonl)
affects: [v1.x ENDORSE-04, v1.x ENDORSE-05, v1.x ENDORSE-06, v1.x ENDORSE-07]

# Tech tracking
tech-stack:
  added: []  # zero new dependencies — entirely codebase-pattern reuse
  patterns:
    - "schema_version: Literal[1] = 1 lock — forces v1.x to bump non-breakingly via Literal[2] discriminator"
    - "Pydantic + zod parity at the schema boundary (extra='forbid' ↔ .strict())"
    - "Append-only JSONL discipline (mkdir parents=True; mode='a'; sort_keys=True; one record per line)"
    - "Pure-helper filter (filterRecent90) tested in isolation; useQuery select callback applies it client-side"
    - "Date-vs-captured-at semantic split: 90-day filter operates on the call date, NOT the entry date"

key-files:
  created:
    - "analysts/endorsement_schema.py"
    - "endorsements/__init__.py"
    - "endorsements/log.py"
    - "cli/add_endorsement.py"
    - "endorsements.jsonl"
    - "tests/analysts/test_endorsement_schema.py"
    - "tests/endorsements/__init__.py"
    - "tests/endorsements/test_log.py"
    - "tests/cli/__init__.py"
    - "tests/cli/test_add_endorsement.py"
    - "frontend/src/schemas/endorsement.ts"
    - "frontend/src/schemas/__tests__/endorsement.test.ts"
    - "frontend/src/lib/loadEndorsements.ts"
    - "frontend/src/lib/__tests__/loadEndorsements.test.ts"
    - "frontend/src/components/EndorsementsList.tsx"
    - "frontend/src/components/__tests__/EndorsementsList.test.tsx"
    - "frontend/tests/e2e/endorsements.spec.ts"
  modified:
    - "cli/main.py"  # SUBCOMMANDS dict + 1 import line
    - "frontend/src/routes/DecisionRoute.tsx"  # mount EndorsementsList after DissentPanel
    - "frontend/src/routes/__tests__/DecisionRoute.test.tsx"  # mount-order assertion + useEndorsements mock
    - ".planning/REQUIREMENTS.md"  # ENDORSE-01..03 flipped to Complete

key-decisions:
  - "schema_version: Literal[1] = 1 is LOAD-BEARING — v1.x ENDORSE-04..07 will bump to Literal[2] (or Union[V1, V2]) so v1 readers cannot silently misread future records as '0% performance'"
  - "endorsements.jsonl COMMITTED at repo root (NOT gitignored) — diverges from memory/historical_signals.jsonl (gitignored, transient). PROJECT.md frames endorsements as 'first-class signal' visible on GitHub + readable by frontend via raw.githubusercontent.com"
  - "90-day filter operates on `date` (the call date), NOT `captured_at` (the entry date). User can capture an old endorsement they remember from January — it correctly EXCLUDES from the 90-day window even though captured_at is recent"
  - "NO performance number rendered ANYWHERE — period. Component has no % math, no S&P alpha, no gain/loss. Test guards via regex scan of rendered HTML"
  - "Mount order: RecommendationBanner → CurrentPriceDelta → DriversList → Separator → DissentPanel → EndorsementsList → open_observation. CurrentPriceDelta stays as Phase 8 hero immediately under banner; EndorsementsList sits AFTER DissentPanel"
  - "Append-only purity in v1: no edit/delete UI, no duplicate detection, no auto-capture. CLI just appends; frontend just reads. v1.x can add affordances"
  - "Notion-Clean palette discipline: every color in EndorsementsList.tsx is a CSS variable token (text-fg / text-fg-muted / border-border / bg-surface / bg-bg). Zero inline hex"

patterns-established:
  - "schema_version Literal lock at the parse boundary (Pydantic + zod both enforce strictly) — forward compatibility through explicit version bumping, not optional-field accumulation"
  - "JSONL line-loader for read-only frontend consumption (text fetch + line split + per-line zod parse) — sibling to single-object fetchAndParse boundary"
  - "Pure-helper-plus-hook split: filterRecent90 unit-tested in isolation; useEndorsements composes it via select callback. Test surface stays small, hook stays thin"
  - "Test fixture discipline: source names in regex-guarded tests must avoid trip words ('Seeking Alpha' in fixtures triggers /alpha/i guard — fixture changed to 'Stock Picks Weekly' to keep guard clean)"

requirements-completed: [ENDORSE-01, ENDORSE-02, ENDORSE-03]

# Metrics
duration: 10min
completed: 2026-05-04
---

# Phase 9 Plan 01: Endorsement Capture Summary

**Append-only endorsements.jsonl (committed at repo root) + Pydantic v2 schema with `schema_version: Literal[1] = 1` lock + flag-only CLI + zod-validated React panel mounted after DissentPanel — NO performance number rendered anywhere.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-05-04T19:26:39Z
- **Completed:** 2026-05-04T19:36:55Z
- **Tasks:** 3 (TDD: RED + GREEN per task)
- **Files created:** 17
- **Files modified:** 4

## Accomplishments

- **ENDORSE-01 closed**: `endorsements.jsonl` at repo root accepts append via `Endorsement` Pydantic record `{ticker, source, date, price_at_call, notes, captured_at, schema_version: 1}`; atomic-on-success only.
- **ENDORSE-02 closed**: `markets add_endorsement --ticker --source --date --price [--notes] [--path]` CLI subcommand registered in `cli/main.py` SUBCOMMANDS; flag-only; ValidationError → exit 2 + actionable message + NO append.
- **ENDORSE-03 closed**: DecisionRoute mounts `<EndorsementsList symbol={symbol} />` immediately AFTER DissentPanel; renders last 90 days for active ticker (date-desc); 4-state render (loading / error / empty / populated); NO performance number anywhere.
- **`schema_version: Literal[1] = 1` lock holds on Pydantic AND zod sides** — forces v1.x bump non-breakingly.
- **Append-only purity preserved**: zero edit/delete UI, zero duplicate detection, zero auto-capture (all v1.x deferred).
- **v1 COMPLETE**: all 9 phases shipped; all 59 v1 requirements closed.

## Test Counts (before → after)

| Suite | Baseline | After Phase 9 | Delta |
|---|---|---|---|
| Python pytest | 704 | **738** | +34 (16 schema + 7 log + 11 CLI) |
| Frontend vitest | 260 | **291** | +31 (12 schema + 11 loader + 7 component + 1 mount-order) |
| Playwright | 72 | **81** | +9 (3 specs × 3 projects) |

(Plan target was ~25 / ~21 / +3-spec — actual is +34 / +31 / +9 because TDD discipline yields slightly higher per-feature test density and Playwright auto-runs on all 3 projects.)

## Provenance

| File | Marker form |
|---|---|
| `analysts/endorsement_schema.py` | `# novel-to-this-project — endorsement signal capture for newsletter/service calls.` |
| `endorsements/log.py` | `# Pattern adapted from routine/memory_log.py — JSONL atomic append discipline` |
| `cli/add_endorsement.py` | `# Pattern adapted from cli/add_ticker.py — flag-only argparse + Pydantic validation.` |
| `frontend/src/schemas/endorsement.ts` | `// novel-to-this-project — Phase 9 endorsement record schema mirroring analysts/endorsement_schema.py` |
| `frontend/src/lib/loadEndorsements.ts` | `// novel-to-this-project — Phase 9 JSONL loader + 90-day filter + ticker filter + date-desc sort` |
| `frontend/src/components/EndorsementsList.tsx` | `// novel-to-this-project — Phase 9 Decision-Route panel rendering last-90-days endorsements per ticker.` |

`python scripts/check_provenance.py` → green (49 files scanned).

## Schema Version Lock — Why It Is Load-Bearing

`schema_version: Literal[1] = 1` (Pydantic) + `z.literal(1)` (zod) both REJECT `schema_version: 2` and `schema_version: 0` at parse time. This forces v1.x ENDORSE-04..07 to:

- Either bump the literal to `Literal[2]` (breaking the type — readers fail loud)
- Or introduce a discriminated union: `Union[V1Endorsement, V2Endorsement]` with explicit branching

Without the lock, v1.x could silently add optional `perf_pct_vs_snapshot: float | None` fields. v1 records lacking those fields would deserialize as `None` — and a naive renderer would treat `None` as "0% performance," producing damning false signals on v1 endorsements that were captured before performance math existed.

The lock is the FIRST guarantee that v1.x performance math additions are visible at the type boundary, not silent at runtime.

## File-Ownership Note

`endorsements.jsonl` is **COMMITTED at repo root** (NOT gitignored). Verify via:

```bash
git check-ignore endorsements.jsonl  # exits 1 (NOT ignored)
git ls-files endorsements.jsonl      # output: endorsements.jsonl (tracked)
```

This **diverges** from `memory/historical_signals.jsonl` (gitignored, transient — Phase 8) because PROJECT.md frames endorsements as "first-class signal":
- Visible on GitHub (peer review, audit trail)
- Readable by frontend via `raw.githubusercontent.com/.../endorsements.jsonl`
- Append-only history that v1.x performance math will reach back through

`memory/historical_signals.jsonl` (Phase 8) is local-only routine telemetry; revisited for cross-device persistence in v1.x.

## Task Commits

Each task TDD-committed atomically (RED → GREEN). Final two commits handle metadata.

1. **Task 1 RED** — `d2a745d` — *test(09-01): add failing tests for endorsement schema + log + CLI*
2. **Task 1 GREEN** — `3c2abef` — *feat(09-01): implement endorsement schema + JSONL log + add_endorsement CLI*
3. **Task 2 RED** — `15491b7` — *test(09-01): add failing frontend tests for endorsement schema + loader*
4. **Task 2 GREEN** — `9701cec` — *feat(09-01): implement frontend endorsement zod schema + loader*
5. **Task 3 RED** — `dcea8c1` — *test(09-01): add failing component + DecisionRoute mount-order + Playwright tests*
6. **Task 3 GREEN** — `a6154f7` — *feat(09-01): mount EndorsementsList in DecisionRoute + Playwright E2E*
7. **REQUIREMENTS flip** — `d6c9402` — *docs(09-01): flip ENDORSE-01..03 to complete in REQUIREMENTS.md (Phase 9 done — v1 complete)*

## Files Created/Modified

### Created (17)

**Python (production):**
- `analysts/endorsement_schema.py` — Pydantic v2 Endorsement model with schema_version Literal[1] lock
- `endorsements/__init__.py` — package marker
- `endorsements/log.py` — append_endorsement + load_endorsements (mirrors routine/memory_log.py)
- `cli/add_endorsement.py` — flag-only CLI subcommand
- `endorsements.jsonl` — empty committed file at repo root

**Python (tests):**
- `tests/analysts/test_endorsement_schema.py` — 16 schema tests (literal lock + ticker normalize + extra=forbid + roundtrip)
- `tests/endorsements/__init__.py` — package marker
- `tests/endorsements/test_log.py` — 7 log tests (atomic append + sort_keys + load skip-blank + Pydantic round-trip)
- `tests/cli/__init__.py` — package marker
- `tests/cli/test_add_endorsement.py` — 11 CLI tests (happy / normalize / atomic-on-failure / captured_at recency / SUBCOMMANDS registration)

**Frontend (production):**
- `frontend/src/schemas/endorsement.ts` — zod EndorsementSchema with z.literal(1) + .strict()
- `frontend/src/lib/loadEndorsements.ts` — fetchEndorsementsJsonl + filterRecent90 + useEndorsements
- `frontend/src/components/EndorsementsList.tsx` — 4-state render + Notion-Clean palette + NO perf number

**Frontend (tests):**
- `frontend/src/schemas/__tests__/endorsement.test.ts` — 12 schema parity tests
- `frontend/src/lib/__tests__/loadEndorsements.test.ts` — 11 loader tests (4 fetch + 4 filter + 3 boundary)
- `frontend/src/components/__tests__/EndorsementsList.test.tsx` — 7 component render tests
- `frontend/tests/e2e/endorsements.spec.ts` — 3 Playwright specs (empty / populated / 90-day cutoff)

### Modified (4)

- `cli/main.py` — added 1 import line + 1 SUBCOMMANDS entry (`add_endorsement`)
- `frontend/src/routes/DecisionRoute.tsx` — added 1 import + 4-line mount block after DissentPanel
- `frontend/src/routes/__tests__/DecisionRoute.test.tsx` — added vi.mock('@/lib/loadEndorsements') + default empty stub + 1 mount-order test using compareDocumentPosition
- `.planning/REQUIREMENTS.md` — flipped ENDORSE-01..03 from Pending to Complete; updated footer date stamp; coverage table count unchanged (still 59 v1, all mapped)

## Decisions Made

All key decisions captured in frontmatter `key-decisions`. Notable elaborations:

1. **`captured_at` strips microseconds at second-precision** to match the ISO 8601 second-precision convention used elsewhere (cli/add_ticker._now_iso). Test originally asserted `before <= captured_at <= after` strict bracket; adjusted to "within last 60s" since `datetime.now()` includes microseconds and the recorded value does not.
2. **Strict zod (`.strict()` mode)** mirrors Pydantic `extra='forbid'` — unknown keys at the JSONL line level fail the parse. v1.x cannot silently ride extra fields through; explicit schema bump required.
3. **`filterRecent90` is exported separately** from `useEndorsements` so unit tests can pass a fixed `now: Date` for deterministic 90-day boundary checks (tested 91d-out vs 89d-in around `2026-05-04T12:00:00Z`).
4. **Test fixture trap caught + fixed:** the e2e populated-state spec originally used "Seeking Alpha" as a source name. The component is correctly free of performance text, but the fixture's literal substring tripped the `/alpha/i` regex guard. Renamed to "Stock Picks Weekly" — the guard now catches what it was designed to catch (component regressions), not fixture word choice.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Strict before/after datetime bracket assertion was unreliable**
- **Found during:** Task 1 GREEN (full pytest run)
- **Issue:** `test_captured_at_auto_populated` asserted `before <= captured_at <= after` where `before` came from `datetime.now()` (with microseconds) and `captured_at` was stripped to second precision by `_now_utc()`. Microsecond > 0 caused `before` to exceed the second-truncated `captured_at`, failing the assertion ~50% of runs.
- **Fix:** Replaced strict bracket with "within last 60s" recency check using `datetime.now() - captured_at` delta. Preserves intent (captured_at is auto-populated to current time) without flaking on sub-second clock skew.
- **Files modified:** `tests/cli/test_add_endorsement.py`
- **Verification:** Test passes deterministically; all 34 Python tests green.
- **Committed in:** `3c2abef` (Task 1 GREEN)

**2. [Rule 1 - Bug] Playwright spec fixture tripped own regex guard**
- **Found during:** Task 3 GREEN (Playwright run)
- **Issue:** Populated-state spec used `source: 'Seeking Alpha'` as a fixture record. The same spec asserts `expect(listText).not.toMatch(/alpha/i)` to guard against future performance-vocabulary regressions. The fixture's literal substring "Alpha" tripped the guard — false positive.
- **Fix:** Renamed fixture source to `'Stock Picks Weekly'`. The COMPONENT is correct (no perf vocabulary in EndorsementsList.tsx); the guard remains a regression sentinel for future component changes; the fixture no longer self-trips.
- **Files modified:** `frontend/tests/e2e/endorsements.spec.ts`
- **Verification:** Playwright spec passes; component-side regex guard intact.
- **Committed in:** `a6154f7` (Task 3 GREEN)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs in test code, not in plan-locked production behavior).
**Impact on plan:** Both auto-fixes preserve scope and lock-bearing assertions. Production behavior matches CONTEXT.md exactly: schema_version Literal[1] held; date-vs-captured-at split held; NO performance number anywhere; mount AFTER DissentPanel; append-only purity. Zero scope creep.

## Issues Encountered

None during planned work — both deviations above were test-only adjustments. No architectural decisions deferred; no Rule 4 STOP fires.

## v1.x Successors (Deferred — NOT in this phase)

Per CONTEXT.md `<deferred>` and ROADMAP.md Phase 9 v1.x successors:

- **ENDORSE-04**: corp-action-aware historical price lookup (yfinance `auto_adjust=True`)
- **ENDORSE-05**: vs-S&P alpha computation
- **ENDORSE-06**: performance number rendered in UI (% gain, alpha)
- **ENDORSE-07**: corp-action notice surface
- **WATCH-06/07-style frontend form** for endorsement entry (CLI-only in v1)
- **Endorsement edit/delete** UI (append-only by design; v1.x adds tombstone records if demanded)
- **CLI `list_endorsements`** subcommand (debug-only — frontend EndorsementsList covers the v1 surface)
- **Routine integration** to auto-read endorsements + emit performance signals into routine snapshots

The `schema_version: Literal[1] = 1` lock means v1.x ENDORSE-04..07 will introduce `Literal[2]` (or a discriminated union) — v1 records will be readable but explicitly versioned, never silently misinterpreted.

## v1 Completion Marker

**Phase 9 closes the v1 ROADMAP.** All 9 phases complete. All 59 v1 requirements mapped + closed:

- Phase 1 — Foundation (5/5) ✓
- Phase 2 — Ingestion (7/7) ✓
- Phase 3 — Analytical Agents (5/5) ✓
- Phase 4 — Position-Adjustment Radar (3/3) ✓
- Phase 5 — Claude Routine Wiring (6/6) ✓
- Phase 6 — Frontend MVP (5/5) ✓
- Phase 7 — Decision-Support View (1/1) ✓
- Phase 8 — Mid-Day Refresh (2/2) ✓
- Phase 9 — Endorsement Capture (1/1) ✓ ← THIS PLAN

User can now run `/gmd:complete-milestone` to archive v1 and start v1.x.

## Next Phase Readiness

**v1 is shippable.** No blockers. Manual verifications deferred per VALIDATION.md Manual-Only Verifications table:

1. End-to-end CLI append + frontend render: `markets add_endorsement --ticker AAPL --source "Motley Fool" --date 2026-04-15 --price 178.42 --notes "test"` → commit + push → verify card appears at `/decision/AAPL/today` on Vercel preview.
2. Notion-Clean visual taste-check at `/decision/AAPL/today` with populated `endorsements.jsonl` — confirm card spacing, restraint, hairline borders, no inline color drift.

These are user-facing concerns the assistant cannot regress and they do NOT block v1 ship.

## Self-Check: PASSED

- [x] All 17 created files exist on disk and were committed
- [x] All 7 commits exist in git history (`git log --oneline -10`)
- [x] Backend pytest 738 green (704 + 34)
- [x] Frontend vitest 291 green (260 + 31)
- [x] Playwright 81 green (72 + 9 = 3 specs × 3 projects)
- [x] TypeScript typecheck clean
- [x] `git check-ignore endorsements.jsonl` returns exit 1 (NOT ignored)
- [x] `git ls-files endorsements.jsonl` shows file is tracked
- [x] `python scripts/check_provenance.py` returns exit 0 (49 files scanned)
- [x] REQUIREMENTS.md ENDORSE-01..03 marked `[x]`; Traceability table shows Complete; footer dated

---
*Phase: 09-endorsement-capture*
*Completed: 2026-05-04*
