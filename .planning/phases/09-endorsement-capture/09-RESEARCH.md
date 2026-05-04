---
phase: 9
phase_name: Endorsement Capture
researched: 2026-05-03
domain: append-only JSONL capture + Pydantic v2 schema versioning + CLI add subcommand + React decision-route panel
confidence: HIGH
tier: normal
vault_status: not-configured
vault_reads: []
---

# Phase 9: Endorsement Capture — Research

**Researched:** 2026-05-03
**Domain:** Append-only JSONL capture + Pydantic v2 schema versioning + CLI add subcommand + React decision-route rendering
**Confidence:** HIGH (entirely codebase-pattern-derived; no new external libraries)

## Summary

Phase 9 is the smallest phase in v1 — three requirements (ENDORSE-01..03), the final phase before v1 ship. The work is **capture only**: a `cli/add_endorsement.py` subcommand appends records to `endorsements.jsonl`, the existing `DecisionRoute.tsx` gets an `EndorsementsList` panel that shows the last 90 days, and a `endorsement_schema_v1: 1` integer locks forward compatibility for v1.x performance math (ENDORSE-04..07).

The research is HIGH confidence because **every pattern is already established in this codebase**: append-only JSONL writes mirror `routine/memory_log.py` (08-shipped), CLI subcommand registration mirrors `cli/main.py` SUBCOMMANDS dict, Pydantic schema discipline mirrors `analysts/schemas.py` (Phase 1), zod read-layer mirrors `frontend/src/schemas/refresh.ts` (08-shipped), and route-mounted TanStack Query hooks mirror `useRefreshData` (08-shipped). **Zero new dependencies. Zero new external integrations.**

**Primary recommendation:** Single wave, single PLAN, three tasks (Python schema+CLI / Frontend schema+hook / Frontend component+E2E). Mirror `memory_log.py` for the writer, mirror `add_ticker.py` for the CLI, mirror `useRefreshData.ts` for the read hook, mirror `DissentPanel.tsx` for the render component. Defer ALL performance math to v1.x.

## User Constraints

(No CONTEXT.md exists for Phase 9 yet — research feeds the planner directly. The orchestrator-supplied additional_context provides the constraint surface in lieu of CONTEXT.md.)

### Locked Decisions (from orchestrator brief + ROADMAP)
- **Capture only — performance math deferred to v1.x.** Zero `% gain`, zero S&P alpha, zero corp-action handling in v1.
- **`endorsement_schema_v1: int = 1` field is required** on every record so v1.x adds columns non-breakingly.
- **JSONL committed (not gitignored).** PROJECT.md frames endorsements as "first-class signal" — committed makes them browsable on GitHub like the daily snapshots; user can override post-merge. Diverges from `memory_log.py` (which is gitignored as transient run-state).
- **CLI flag-only UX in v1.** Interactive prompt mode is v1.x polish; flags-only matches `cli/add_ticker.py` precedent.
- **Decision-Support panel placement: below `DissentPanel`, above `CurrentPriceDelta`** in `DecisionRoute.tsx`. Endorsements are evidence, not the recommendation hero.
- **Frontend reads endorsements via `raw.githubusercontent.com`** — same GitHub-as-DB pattern as snapshots. Single source of truth for "what does the deployed frontend see."

### Claude's Discretion
- Endorsement record file location: **`endorsements.jsonl` at repo root** (recommend) vs `data/endorsements.jsonl`. Repo root mirrors `watchlist.json` (single global file, not per-date). `data/` is reserved for per-date snapshot folders. Recommend repo root.
- Ticker filtering in render: client-side filter by `ticker === active` from the full JSONL (the file is small — 90 days × low call rate ≈ <1 KB) vs split-by-ticker. Recommend client-side filter — simpler, file stays single source.
- 90-day window enforcement: client-side date filter on render, NOT a server-side trim. The full JSONL is append-only history; v1.x performance math will need older entries. Recommend client filter.

### Deferred Ideas (OUT OF SCOPE — v1.x successors)
- ENDORSE-04: corp-action-aware historical price lookup (yfinance `auto_adjust=True`)
- ENDORSE-05: vs-S&P alpha computation
- ENDORSE-06: performance number rendered in UI (% gain, alpha)
- ENDORSE-07: corp-action notice surface
- WATCH-06/07-style frontend form for endorsement entry (CLI-only in v1)
- Endorsement edit / delete (append-only by design; "delete" is v1.x append a tombstone record)

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ENDORSE-01 | Append-only `endorsements.jsonl` capture: `{ticker, source, date, price_at_call, notes, captured_at}` | `routine/memory_log.append_memory_record` is the proven JSONL append pattern — mkdir parents=True, mode="a", `json.dumps(..., sort_keys=True) + "\n"`, one record per line. Pydantic-validate inputs synchronously (raise on first offence). |
| ENDORSE-02 | CLI utility for adding endorsements | `cli/add_ticker.py` is the proven CLI subcommand pattern — `build_*_parser(p)` registers flags, `*_command(args)` returns exit code, `SUBCOMMANDS` dict in `cli/main.py` line 36-42 is the single registration point. |
| ENDORSE-03 | Decision-Support view shows last 90 days of endorsements per ticker; performance number deferred | `DecisionRoute.tsx` already mounts `DissentPanel`, `CurrentPriceDelta` etc. via TanStack Query hooks. New `EndorsementsList` component + `useEndorsements()` hook + zod-validated read of `raw.githubusercontent.com/.../endorsements.jsonl` follows the established read-layer pattern. |

## Standard Stack

### Core (no new deps)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | v2 (already pinned) | Endorsement record schema + JSONL line validation | Project-wide schema discipline (analysts/schemas.py, AgentSignal, TickerDecision). |
| argparse | stdlib | CLI flag parsing | `cli/main.py` dispatcher convention; zero new deps. |
| json (stdlib) | stdlib | JSONL serialization | `routine/memory_log.py` pattern — `json.dumps(record, sort_keys=True) + "\n"`. |
| zod | v3 (already pinned in frontend) | Frontend endorsement record validation | Mirrors `frontend/src/schemas/refresh.ts` discipline. |
| @tanstack/react-query | v5 (already pinned) | Endorsement fetch + cache | Mirrors `useRefreshData` hook (08-shipped). |
| react-router | v7 (already pinned) | DecisionRoute is the mount point | No new routes; existing `/decision/:symbol/:date?` route gets one new section. |

### Supporting (no new deps)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest + responses | already pinned | CLI + writer + schema tests | Same fixtures as Phase 1-8. |
| vitest + Playwright | already pinned | Frontend component + E2E tests | Same harness as Phases 6-8. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `endorsements.jsonl` (append) | `endorsements.json` (object map keyed by id) | JSONL: O(1) append, no read-modify-write race, mirrors memory_log. Object: easier random delete (we don't need delete in v1). **Choose JSONL.** |
| Repo root `endorsements.jsonl` | `data/endorsements.jsonl` | Root: mirrors `watchlist.json` (global single-file). `data/`: reserved for per-date snapshots. **Choose root.** |
| Pydantic schema | dataclass + manual validation | Pydantic: matches every other schema in project; auto-generates JSON. Dataclass: lighter. **Choose Pydantic — consistency wins.** |
| `httpx`-fetched endorsements URL | Direct `fetch()` via `fetchAndParse` | We already have `fetchAndParse` — reuse. **Choose fetchAndParse.** |

**Installation:** None. All deps already installed.

## Architecture Patterns

### Recommended Structure (additions only — existing code untouched)

```
endorsements.jsonl                  # NEW — repo root, committed
analysts/
  endorsement_schema.py             # NEW — Pydantic Endorsement model
endorsements/                       # NEW package
  __init__.py
  log.py                            # NEW — append_endorsement(), load_endorsements()
cli/
  add_endorsement.py                # NEW — build_add_endorsement_parser + add_endorsement_command
  main.py                           # MOD — register "add_endorsement" in SUBCOMMANDS
frontend/src/
  schemas/
    endorsement.ts                  # NEW — zod schema mirroring Pydantic
  lib/
    loadEndorsements.ts             # NEW — useEndorsements(symbol) TanStack hook + JSONL parser
  components/
    EndorsementsList.tsx            # NEW — last-90-days panel
  routes/
    DecisionRoute.tsx               # MOD — mount EndorsementsList between DissentPanel and CurrentPriceDelta
tests/
  endorsements/test_schema.py       # NEW
  endorsements/test_log.py          # NEW
  cli/test_add_endorsement.py       # NEW
frontend/tests/
  unit/EndorsementsList.test.tsx    # NEW
  unit/loadEndorsements.test.ts     # NEW
  unit/endorsement_schema.test.ts   # NEW
  e2e/endorsements.spec.ts          # NEW — 1 spec
```

### Pattern 1: Pydantic Endorsement record + schema-version field

**Source:** `analysts/schemas.py` (TickerConfig pattern) + `frontend/src/schemas/refresh.ts` (zod parity)

```python
# analysts/endorsement_schema.py — Pydantic v2
from datetime import date as date_type
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from analysts.schemas import normalize_ticker  # reuse — single source of truth

ENDORSEMENT_SCHEMA_VERSION: int = 1

class Endorsement(BaseModel):
    """One newsletter / service / analyst call. Append-only.

    schema_version locks forward-compatibility — v1.x ENDORSE-04..07 add
    optional fields (perf_pct_vs_snapshot, alpha_vs_sp500, corp_action_event)
    which default to None on v1 records when v1.x routine reads them.
    """
    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    schema_version: Literal[1] = 1  # locks v1 shape; v1.x will use Literal[2] etc.
    ticker: str                     # normalized via field_validator
    source: str = Field(min_length=1, max_length=100)  # e.g. "Motley Fool"
    date: date_type                 # date the call was made (ISO YYYY-MM-DD)
    price_at_call: float = Field(gt=0)
    notes: str = Field(max_length=2000, default="")
    captured_at: str                # ISO 8601 UTC (mirrors created_at convention)

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, v: str) -> str:
        norm = normalize_ticker(v)
        if norm is None:
            raise ValueError(f"invalid ticker: {v!r}")
        return norm
```

### Pattern 2: Append-only JSONL writer

**Source:** `routine/memory_log.py` lines 88-103 (verbatim discipline; only the schema differs)

```python
# endorsements/log.py
from pathlib import Path
import json
from analysts.endorsement_schema import Endorsement

DEFAULT_PATH: Path = Path("endorsements.jsonl")

def append_endorsement(e: Endorsement, *, path: Path | None = None) -> None:
    """Append one Endorsement to endorsements.jsonl. Pydantic-validates first.

    Atomic-append discipline: mode='a' is single-writer-safe on POSIX +
    Windows for sub-PIPE_BUF lines (record << 4 KB). mkdir parents=True
    matches memory_log convention.
    """
    target = path if path is not None else DEFAULT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(e.model_dump(mode="json"), sort_keys=True) + "\n"
    with target.open("a", encoding="utf-8") as f:
        f.write(line)


def load_endorsements(path: Path | None = None) -> list[Endorsement]:
    """Read all endorsements. Skips blank lines. Pydantic-validates each.

    Used by CLI 'list_endorsements' (deferred to v1.x) and tests. Frontend
    does NOT use this — it reads the JSONL directly via fetch.
    """
    target = path if path is not None else DEFAULT_PATH
    if not target.exists():
        return []
    out: list[Endorsement] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(Endorsement.model_validate_json(line))
    return out
```

### Pattern 3: CLI subcommand registration

**Source:** `cli/add_ticker.py` (verbatim pattern) + `cli/main.py:36` SUBCOMMANDS dict

```python
# cli/add_endorsement.py
import argparse
from datetime import date, datetime, timezone
from pathlib import Path
from analysts.endorsement_schema import Endorsement
from endorsements.log import append_endorsement

def build_add_endorsement_parser(p: argparse.ArgumentParser) -> None:
    p.add_argument("--ticker", required=True, help="ticker symbol (BRK.B → BRK-B)")
    p.add_argument("--source", required=True, help="newsletter/service name (e.g. 'Motley Fool')")
    p.add_argument("--date", required=True, help="ISO date the call was made (YYYY-MM-DD)")
    p.add_argument("--price", type=float, required=True, dest="price_at_call",
                   help="price when endorsement issued")
    p.add_argument("--notes", default="", help="freeform notes (max 2000 chars)")
    p.add_argument("--path", type=Path, default=Path("endorsements.jsonl"),
                   help="path to endorsements.jsonl")

def add_endorsement_command(args: argparse.Namespace) -> int:
    e = Endorsement(
        ticker=args.ticker,
        source=args.source,
        date=date.fromisoformat(args.date),
        price_at_call=args.price_at_call,
        notes=args.notes,
        captured_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    append_endorsement(e, path=args.path)
    print(f"recorded endorsement: {e.ticker} from {e.source} ({e.date})")
    return 0
```

```python
# cli/main.py — line 36 extension (1-line change)
SUBCOMMANDS = {
    ...,
    "add_endorsement": (build_add_endorsement_parser, add_endorsement_command),
}
```

### Pattern 4: Frontend zod schema (parity with Pydantic)

**Source:** `frontend/src/schemas/refresh.ts` (zod discipline + naming convention)

```typescript
// frontend/src/schemas/endorsement.ts
import { z } from 'zod'

export const EndorsementSchema = z.object({
  schema_version: z.literal(1),  // strict — rejects v0 and future v2+
  ticker: z.string().min(1),
  source: z.string().min(1).max(100),
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),  // ISO date
  price_at_call: z.number().positive(),
  notes: z.string().max(2000),
  captured_at: z.string().min(1),
})
export type Endorsement = z.infer<typeof EndorsementSchema>
```

### Pattern 5: TanStack Query hook reading JSONL via raw.githubusercontent.com

**Source:** `frontend/src/lib/useRefreshData.ts` + `frontend/src/lib/fetchSnapshot.ts`

```typescript
// frontend/src/lib/loadEndorsements.ts
import { useQuery } from '@tanstack/react-query'
import { RAW_BASE, FetchNotFoundError, SchemaMismatchError } from './fetchSnapshot'
import { EndorsementSchema, type Endorsement } from '@/schemas/endorsement'

export const endorsementsUrl = (): string => `${RAW_BASE}/endorsements.jsonl`

// JSONL is line-delimited — fetch as text, split, parse each line.
// Skips blank lines. Throws SchemaMismatchError on first invalid line.
export async function fetchEndorsementsJsonl(): Promise<Endorsement[]> {
  const url = endorsementsUrl()
  const res = await fetch(url, { headers: { Accept: 'text/plain' } })
  if (res.status === 404) return []  // empty before any endorsement is added
  if (!res.ok) throw new Error(`Fetch ${url} failed: ${res.status}`)
  const text = await res.text()
  const out: Endorsement[] = []
  for (const line of text.split('\n')) {
    if (!line.trim()) continue
    const json = JSON.parse(line) as unknown
    const result = EndorsementSchema.safeParse(json)
    if (!result.success) throw new SchemaMismatchError(url, result.error)
    out.push(result.data)
  }
  return out
}

export function useEndorsements(symbol: string) {
  return useQuery<Endorsement[]>({
    queryKey: ['endorsements'],  // global — full file is small
    queryFn: fetchEndorsementsJsonl,
    staleTime: 10 * 60 * 1000,   // 10 min (mirrors snapshot cache philosophy)
    enabled: symbol.length > 0,
    select: (all) => filterRecent90(all, symbol),  // client-side filter
  })
}

function filterRecent90(all: Endorsement[], symbol: string): Endorsement[] {
  const cutoff = Date.now() - 90 * 24 * 60 * 60 * 1000
  return all
    .filter((e) => e.ticker === symbol.toUpperCase())
    .filter((e) => new Date(e.date).getTime() >= cutoff)
    .sort((a, b) => b.date.localeCompare(a.date))  // most recent first
}
```

### Pattern 6: Decision-Route panel mount

**Source:** `frontend/src/routes/DecisionRoute.tsx:174-200` (existing mount discipline)

```tsx
// In DecisionRoute.tsx, between DissentPanel and CurrentPriceDelta:
<DriversList ... />
<Separator />
<DissentPanel dissent={dec.dissent} />
<EndorsementsList symbol={symbol} />   {/* NEW — Phase 9 */}
<CurrentPriceDelta ... />
```

### Anti-Patterns to Avoid
- **Reading-then-writing the JSONL.** Append-only means `mode='a'`, never load-modify-save (race window + lost data on crash).
- **Computing performance %.** ENDORSE-06 is v1.x. The component renders metadata only.
- **Per-date subdirectory.** `data/YYYY-MM-DD/` is for routine snapshots. Endorsements are time-of-call, not time-of-snapshot.
- **Discriminated union on schema_version.** v1 has only one variant — `z.literal(1)`. v1.x adds variants then.
- **CLI prompts in v1.** Flag-only matches `add_ticker.py`; interactive UX is polish.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSONL atomic append | custom file lock | `mode='a'` + sub-PIPE_BUF lines | Already proven in `memory_log.py`; sub-4KB lines are atomic on POSIX + Windows. |
| Ticker normalization | regex in CLI | `analysts.schemas.normalize_ticker` | Single source of truth; locks `BRK.B → BRK-B`. |
| ISO date validation | manual regex | Pydantic `date` type + `date.fromisoformat` | Zero new code; standard error messages. |
| ISO timestamp formatting | hand-rolled `strftime` | `datetime.now(timezone.utc).isoformat(timespec="seconds")` | Verbatim from `cli/add_ticker.py:_now_iso`. |
| GitHub raw read + parse | new fetch helper | reuse `fetchAndParse` boundary OR build a `fetchTextAndParseJsonl` peer | Consistent error class hierarchy (FetchNotFoundError / SchemaMismatchError). |
| Date-window filter | server-side trim | client-side `filter` on `select` callback | File is tiny; v1.x performance math will need full history anyway. |

**Key insight:** Phase 9 is 90% pattern reuse. The only genuinely new code is the schema definition (~30 LOC) and the EndorsementsList component (~80 LOC). Everything else is direct re-application of patterns already proven in Phases 1, 5, 6, 7, 8.

## Common Pitfalls

### Pitfall 1: Schema-version drift — v1.x performance fields silently dropped
**What goes wrong:** v1.x adds `perf_pct_vs_snapshot: float | None`. v1 records have no such field. If v1.x reads a v1 record without checking `schema_version`, the field reads as `None` and the UI shows "0% performance" — false signal.
**Why it happens:** Optional fields with default `None` look harmless until the renderer treats `None` as "no gain yet."
**How to avoid:** v1.x MUST branch on `schema_version` for ALL added behaviors. The `Literal[1]` lock in v1 forces v1.x to introduce a `Literal[2]` discriminator (or `Union[V1Endorsement, V2Endorsement]`) — cannot be silently extended.
**Warning signs:** Any v1.x reader that doesn't pattern-match on `schema_version`.

### Pitfall 2: Date type confusion — `date` (the call) vs `captured_at` (the timestamp of entry)
**What goes wrong:** User adds an old endorsement they remember from January. They type `--date 2026-01-15` but `captured_at` is set to "now" (2026-05-03). The 90-day window filter uses `date` (call date), not `captured_at` (entry date) — so the January endorsement is correctly EXCLUDED from the recent panel.
**Why it happens:** Two date fields with overlapping semantics — easy to filter on the wrong one.
**How to avoid:** Lock the field naming in the schema with explicit comments. UI filters on `date` (the call), not `captured_at`. Tests assert this explicitly.
**Warning signs:** Tests that use the same date for both fields can't catch the bug.

### Pitfall 3: GitHub raw caching — newly-added endorsement invisible for ~5 minutes
**What goes wrong:** User runs `markets add_endorsement --ticker AAPL ...`, commits + pushes, refreshes the frontend — endorsement doesn't appear. Cause: `raw.githubusercontent.com` CDN cache, ~5 min TTL.
**Why it happens:** Same caching that makes daily snapshots cheap to serve.
**How to avoid:** Documented expectation, not a bug. The user lives with it for daily snapshots already. If acute, add a `?t=<unix>` cache-buster — but Phase 8 didn't, so don't introduce inconsistency here.
**Warning signs:** "endorsement showed up later" support questions — non-actionable.

### Pitfall 4: JSONL parsing — trailing newline, blank lines, partial line on crash
**What goes wrong:** Frontend `text.split('\n')` produces a trailing empty string when the file ends with `\n`; `JSON.parse('')` throws. Or: routine crashes mid-write, JSONL has a half-written line — JSON.parse throws on next read.
**Why it happens:** JSONL by-spec ends with `\n`; partial writes can happen.
**How to avoid:** Always `if (!line.trim()) continue` skip-blank guard. For partial-line corruption, accept that one bad line throws SchemaMismatchError (matches project convention — render error banner, don't silent-coerce).
**Warning signs:** Tests that don't include trailing-newline + blank-line fixtures.

### Pitfall 5: CLI accepts negative price (catches at Pydantic, but exit-code matters)
**What goes wrong:** `--price -42` passes argparse (it's a float) and fails at Pydantic with `ValueError: must be > 0`. The dispatcher in `cli/main.py:68-70` catches `ValidationError` and exits 2 — correct. But test fixtures sometimes assume exit 1.
**Why it happens:** Argparse type=float is permissive; Pydantic enforces gt=0.
**How to avoid:** Test for exit code 2 explicitly; mirror the `cli/add_ticker.py` test conventions.
**Warning signs:** Tests using `subprocess.run` and not checking returncode.

## Code Examples

(All examples in Architecture Patterns above are copy-paste-ready and sourced from existing project files. No external Context7 lookups required — Phase 9 introduces no new libraries.)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single JSON object map | Append-only JSONL | Phase 5 (memory_log) | O(1) append, no race, easy to grep. |
| Untyped CLI flags | argparse → Pydantic schema validation | Phase 1 (add_ticker) | Validation errors localized to schema, not CLI. |
| Fetch + JSON.parse inline | `fetchAndParse(url, schema)` | Phase 6 | Single error-class hierarchy across all reads. |
| TanStack Query inline | `useXxxData(symbol)` hook per concern | Phase 6/8 | Cache key discipline; route-mount-friendly. |

**Deprecated/outdated:** N/A — Phase 9 follows current project patterns exactly.

## Open Questions

1. **Should `cli/list_endorsements.py` ship in v1?**
   - What we know: ROADMAP success criteria don't require it. `cli/list_watchlist.py` exists, so symmetry argues yes.
   - What's unclear: Is `markets list_endorsements --ticker AAPL` worth the test surface for v1 ship?
   - **Recommendation:** Skip in v1. The frontend EndorsementsList is the primary UI; CLI list is debug-only and trivial to add in v1.x. Closing on 3 success criteria is the win.

2. **Should the routine ever read `endorsements.jsonl`?**
   - What we know: ENDORSE-04 (v1.x) needs the routine to compute performance. v1 has zero routine integration.
   - What's unclear: Should v1 emit a "endorsement count per ticker" field in `_status.json` for visibility?
   - **Recommendation:** No. Keep v1 routine untouched. v1.x ENDORSE-04 does the integration cleanly.

3. **What about an existing entry being a duplicate (same ticker + source + date)?**
   - What we know: Append-only design means duplicates are technically allowed.
   - What's unclear: Should the CLI detect and refuse?
   - **Recommendation:** Allow duplicates in v1 (append-only purity). v1.x can add a `--force` flag and detection if user feedback demands it. Document the choice.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Backend framework | pytest (already pinned) |
| Backend config | pyproject.toml (existing) |
| Frontend framework | vitest + Playwright (already pinned) |
| Frontend config | frontend/vite.config.ts + frontend/playwright.config.ts (existing) |
| Quick run command (backend) | `pytest tests/endorsements/ tests/cli/test_add_endorsement.py -x` |
| Quick run command (frontend) | `cd frontend && npm run test:unit -- endorsement` |
| Full suite (backend) | `pytest` |
| Full suite (frontend) | `cd frontend && npm run test && npm run test:e2e` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| ENDORSE-01 | JSONL append schema validation | unit | `pytest tests/endorsements/test_schema.py -x` | ❌ Wave 0 |
| ENDORSE-01 | Append round-trip + sort_keys + trailing newline | unit | `pytest tests/endorsements/test_log.py -x` | ❌ Wave 0 |
| ENDORSE-01 | schema_version=1 lock; v0 / v2 rejected | unit | `pytest tests/endorsements/test_schema.py::test_schema_version_locked -x` | ❌ Wave 0 |
| ENDORSE-02 | CLI happy path (all flags) | unit | `pytest tests/cli/test_add_endorsement.py::test_happy -x` | ❌ Wave 0 |
| ENDORSE-02 | CLI ticker normalization (BRK.B → BRK-B) | unit | `pytest tests/cli/test_add_endorsement.py::test_ticker_normalized -x` | ❌ Wave 0 |
| ENDORSE-02 | CLI invalid price exits 2 (Pydantic ValidationError) | unit | `pytest tests/cli/test_add_endorsement.py::test_invalid_price -x` | ❌ Wave 0 |
| ENDORSE-03 | zod schema parity with Pydantic | unit | `cd frontend && npm run test:unit -- endorsement_schema` | ❌ Wave 0 |
| ENDORSE-03 | useEndorsements 90-day filter + ticker filter + sort | unit | `cd frontend && npm run test:unit -- loadEndorsements` | ❌ Wave 0 |
| ENDORSE-03 | EndorsementsList renders source/date/price; NO performance number | unit | `cd frontend && npm run test:unit -- EndorsementsList` | ❌ Wave 0 |
| ENDORSE-03 | DecisionRoute mounts EndorsementsList between Dissent and CurrentPriceDelta | unit | `cd frontend && npm run test:unit -- DecisionRoute` (extend existing) | partial — DecisionRoute test exists |
| ENDORSE-03 | Playwright: open /decision/AAPL → Endorsements panel renders | e2e | `cd frontend && npx playwright test endorsements.spec.ts` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/endorsements/ tests/cli/test_add_endorsement.py -x` + `cd frontend && npm run test:unit -- endorsement` (~30s combined)
- **Per wave merge:** Full backend `pytest` + frontend `npm run test`
- **Phase gate:** Full suite GREEN (backend pytest + frontend vitest + Playwright) before `/gmd:verify-work`. Existing baselines: backend ~704 tests; frontend vitest 260; Playwright 72. Phase 9 adds ~25 backend + ~20 frontend unit + 1 Playwright spec → expected baselines after merge: ~729 / ~280 / 73-75.

### Wave 0 Gaps
- [ ] `tests/endorsements/__init__.py` + `tests/endorsements/test_schema.py` + `tests/endorsements/test_log.py`
- [ ] `tests/cli/test_add_endorsement.py`
- [ ] `tests/endorsements/conftest.py` — shared `tmp_endorsements_path` fixture
- [ ] `frontend/tests/unit/endorsement_schema.test.ts`
- [ ] `frontend/tests/unit/loadEndorsements.test.ts`
- [ ] `frontend/tests/unit/EndorsementsList.test.tsx`
- [ ] `frontend/tests/e2e/endorsements.spec.ts` (1 spec; mock the JSONL fetch via Playwright route handler — same pattern as resilience.spec.ts)
- [ ] No new framework installs needed.

## Sources

### Primary (HIGH confidence — codebase-derived)
- `routine/memory_log.py` — JSONL append discipline (mkdir, sort_keys, mode='a')
- `cli/add_ticker.py` + `cli/main.py` — CLI subcommand registration pattern
- `analysts/schemas.py` — Pydantic v2 ConfigDict + field_validator patterns + normalize_ticker helper
- `frontend/src/schemas/refresh.ts` — zod parity pattern + isXxxFailure narrowing convention
- `frontend/src/lib/fetchSnapshot.ts` — RAW_BASE + FetchNotFoundError + SchemaMismatchError + fetchAndParse
- `frontend/src/lib/useRefreshData.ts` — TanStack Query hook + queryKey + staleTime + enabled gate
- `frontend/src/routes/DecisionRoute.tsx` — current mount order; line 199 DissentPanel insertion site
- `frontend/tests/e2e/resilience.spec.ts` — Playwright route-mock pattern for JSONL stub
- `.planning/REQUIREMENTS.md` lines 82-84 — exact ENDORSE-01..03 wording
- `.planning/ROADMAP.md` lines 259-274 — Phase 9 success criteria + v1.x successors
- `.gitignore` — establishes `memory/*.jsonl` is gitignored (Phase 9 diverges: `endorsements.jsonl` is committed)

### Secondary (MEDIUM confidence)
- N/A — no external sources required for this phase.

### Tertiary (LOW confidence)
- N/A.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every library is already pinned and used in adjacent phases
- Architecture: HIGH — every pattern is verbatim from existing project files
- Pitfalls: HIGH — the 5 listed pitfalls are derived from the schema_version + dual-date + JSONL format constraints, all observable in the code

**Research date:** 2026-05-03
**Valid until:** Phase 9 ship (no external deps means no decay risk)

**Vault status:** not-configured — no `.claude/skills/` or `.agents/skills/` present in repo; no vault citations available. Research stands on codebase-derived primary sources.

---
*Research complete. Ready for `/gmd:plan-phase 9` (single PLAN, single wave, three tasks recommended).*
