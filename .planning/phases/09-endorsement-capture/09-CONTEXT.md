# Phase 9: Endorsement Capture — Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Source:** Research-derived (researcher recommendations adopted)

<domain>
## Phase Boundary

Three additive surfaces to ship endorsement capture as a first-class signal — performance math deferred to v1.x via schema versioning:

1. **Python schema + log writer** — `analysts/endorsement_schema.py` Pydantic model + `endorsements/log.py` JSONL append helper.
2. **CLI command** — `cli/add_endorsement.py` registered in `cli/main.py:36` SUBCOMMANDS dict; flag-only invocation (`markets add_endorsement --ticker AAPL --source "Motley Fool" --date 2026-04-15 --price 178.42 --notes "10-bagger thesis"`).
3. **Frontend rendering** — `frontend/src/schemas/endorsement.ts` zod schema + `frontend/src/lib/loadEndorsements.ts` TanStack fetcher + `frontend/src/components/EndorsementsList.tsx` mounted in `DecisionRoute.tsx` between DissentPanel and CurrentPriceDelta.

**Out of phase boundary** (per ROADMAP "v1.x successors"):
- Performance number computation (ENDORSE-04 corp-action-aware perf, ENDORSE-05 vs S&P alpha, ENDORSE-06 perf rendering, ENDORSE-07 corp-action notice) — all v1.x.
- Routine integration (auto-capture from RSS feeds) — v1.x.
- Edit/delete UI — v1.x; v1 is append-only.

</domain>

<decisions>
## Implementation Decisions

### Endorsement Schema (LOCKED — Pydantic v2)

```python
# analysts/endorsement_schema.py
# novel-to-this-project — endorsement signal capture for newsletter/service calls.
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from analysts.schemas import normalize_ticker


class Endorsement(BaseModel):
    """Single endorsement record. Append-only; performance math deferred to v1.x."""
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1   # LOAD-BEARING — v1.x bumps to Literal[2] non-breakingly
    ticker: str
    source: str = Field(min_length=1, max_length=200)
    date: date                       # when the call was made (drives 90-day filter)
    price_at_call: float = Field(gt=0)
    notes: str = Field(default="", max_length=2000)
    captured_at: datetime            # when user added the entry — metadata

    @field_validator("ticker", mode="before")
    @classmethod
    def _normalize_ticker_field(cls, v: object) -> str:
        norm = normalize_ticker(v) if isinstance(v, str) else None
        if norm is None:
            raise ValueError(f"invalid ticker {v!r}")
        return norm
```

**`schema_version: Literal[1] = 1` is load-bearing** — forces v1.x to bump to `Literal[2]` rather than silently extend. Prevents v1.x readers from misinterpreting v1 records as having implicit "0% performance" when the perf field arrives. (Pitfall #1 from research.)

### Storage (LOCKED — committed at repo root)

`endorsements.jsonl` lives at repo root, **committed** (NOT gitignored). Diverges from `memory/historical_signals.jsonl` (Phase 8) which IS gitignored. Reason: PROJECT.md frames endorsements as "first-class signal" — visible on GitHub, readable by frontend via `raw.githubusercontent.com`.

Append-only via `endorsements/log.py` mirroring `routine/memory_log.py` pattern (atomic append + retry on tmp collision). One JSON object per line, `sort_keys=True`, no trailing newline ambiguity.

### CLI (LOCKED — flag-only, append-on-success)

```
markets add_endorsement \
  --ticker AAPL \
  --source "Motley Fool" \
  --date 2026-04-15 \
  --price 178.42 \
  --notes "10-bagger thesis around Vision Pro adoption"
```

- `--ticker`, `--source`, `--date`, `--price` required.
- `--notes` optional (default empty string).
- `captured_at` auto-populated `datetime.now(timezone.utc)`.
- On Pydantic ValidationError → print actionable error, exit 1, NO append.
- On success → print "Captured endorsement: {ticker} from {source} on {date} at ${price}" + exit 0.
- Duplicate detection deferred to v1.x — append-only purity in v1.

### Frontend Schema (LOCKED — zod mirrors Pydantic)

```ts
// frontend/src/schemas/endorsement.ts
import { z } from 'zod'

export const endorsementSchema = z.object({
  schema_version: z.literal(1),  // strict — rejects v0 / v1.x v2 records explicitly
  ticker: z.string(),
  source: z.string().min(1).max(200),
  date: z.string(),               // ISO date YYYY-MM-DD
  price_at_call: z.number().positive(),
  notes: z.string().max(2000),
  captured_at: z.string(),        // ISO 8601 datetime
})

export type Endorsement = z.infer<typeof endorsementSchema>
```

### Frontend Fetcher (LOCKED — JSONL stream parse)

`frontend/src/lib/loadEndorsements.ts` — TanStack Query queryFn fetches `https://raw.githubusercontent.com/${VITE_GH_USER}/${VITE_GH_REPO}/main/endorsements.jsonl`, splits on newlines, zod-parses each line, filters by `ticker` + `date >= today - 90 days`, sorts by `date` descending.

Failures handled per Phase 6 pattern (SchemaMismatchError + FetchNotFoundError). 404 (file doesn't exist yet) returns empty list — endorsements.jsonl is OPTIONAL (user might never add one); empty state must render cleanly.

### Frontend Component Layout (LOCKED — DecisionRoute panel)

`<EndorsementsList ticker={symbol} />` mounts in `DecisionRoute.tsx:199` between `<DissentPanel />` and `<CurrentPriceDelta />`. Renders:

- Empty state: muted "No endorsements captured for {ticker} in the last 90 days. Use `markets add_endorsement` to capture one."
- Populated state: list of cards (most recent first) showing `source` (header), `date` + `price_at_call` (sub-header), `notes` (body), captured_at relative timestamp ("captured 3 days ago") muted footer.
- NO performance number rendered. Period.

### Notion-Clean Discipline

All colors from CSS variable tokens. Hairline borders. Generous spacing (`gap-4`, `p-4` on individual endorsement cards; `gap-6` between panel and adjacent panels).

### Provenance

- `analysts/endorsement_schema.py` → `# novel-to-this-project` (no reference adaptation)
- `endorsements/log.py` → `# Pattern adapted from routine/memory_log.py — JSONL atomic append`
- `cli/add_endorsement.py` → `# Pattern adapted from cli/add_ticker.py — flag-only argparse + Pydantic validation`
- All frontend files → `// novel-to-this-project` header comment
- `scripts/check_provenance.py` (Phase 8) will assert these markers on next CI run.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`routine/memory_log.py`** (Phase 8) — JSONL append pattern. `endorsements/log.py` mirrors verbatim with different schema.
- **`cli/add_ticker.py` + `cli/main.py:36` SUBCOMMANDS dict** — CLI registration pattern. `add_endorsement` plugs into the same dispatcher.
- **`analysts/schemas.py`** — Pydantic v2 + `normalize_ticker()` reused.
- **`frontend/src/schemas/refresh.ts`** (Phase 8) — zod parity pattern.
- **`frontend/src/lib/useRefreshData.ts`** (Phase 8) — TanStack hook pattern.
- **`frontend/src/routes/DecisionRoute.tsx:199`** — mount site (between DissentPanel and CurrentPriceDelta).

### Established Patterns

- **JSONL atomic append** — same as memory_log + llm_failures.
- **Pydantic + zod parity** — schema_version: Literal[1] both sides.
- **TanStack Query + zod-parse** — same as fetchSnapshot.
- **CLI subcommand via SUBCOMMANDS dict** — same as add_ticker / refresh.

### Integration Points

- **Reads from**: `endorsements.jsonl` at repo root (frontend) + same file (CLI append target)
- **Writes to**: `endorsements.jsonl` (CLI only)
- **Reads in DecisionRoute.tsx**: zod-parsed endorsements filtered by ticker + 90-day window

### Constraints from Existing Architecture

- **GitHub-as-DB** — endorsements.jsonl committed alongside snapshots.
- **Notion-Clean palette** — CSS vars only.
- **No backend serverless changes** — Phase 8 owns api/refresh.py; Phase 9 doesn't touch it.

</code_context>

<specifics>
## Specific Ideas

### File Layout

```
analysts/endorsement_schema.py        [new ~50 lines]
endorsements/__init__.py              [new — empty]
endorsements/log.py                   [new ~60 lines — JSONL append]
cli/add_endorsement.py                [new ~80 lines]
cli/main.py                           [extend +3 lines — SUBCOMMANDS entry]
endorsements.jsonl                    [new — empty file at repo root, committed]

tests/analysts/test_endorsement_schema.py  [new ~80 lines, ~10 tests]
tests/endorsements/__init__.py             [new — empty]
tests/endorsements/test_log.py             [new ~80 lines, ~6 tests]
tests/cli/test_add_endorsement.py          [new ~100 lines, ~9 tests]

frontend/src/schemas/endorsement.ts        [new ~30 lines]
frontend/src/schemas/__tests__/endorsement.test.ts [new ~60 lines, ~6 tests]
frontend/src/lib/loadEndorsements.ts       [new ~70 lines — fetcher + 90-day filter + sort]
frontend/src/lib/__tests__/loadEndorsements.test.ts [new ~80 lines, ~9 tests]
frontend/src/components/EndorsementsList.tsx [new ~100 lines]
frontend/src/components/__tests__/EndorsementsList.test.tsx [new ~80 lines, ~6 tests]
frontend/src/routes/DecisionRoute.tsx      [extend +5 lines — mount EndorsementsList]
frontend/tests/e2e/endorsements.spec.ts    [new ~80 lines, ~3 specs]
```

### File Sizes Expected

Production: ~470 lines (Python ~190, TypeScript ~205, config ~75).
Tests: ~480 lines (Python ~260, TypeScript ~220).
Total: ~950 lines.

### Test Surface

- Python: ~25 new tests (schema + log + CLI)
- vitest: ~21 new tests (schema + fetcher + component)
- Playwright: 3 new specs (empty state + populated + 90-day filter cutoff) on chromium-desktop

Total: ~49 new tests. Repo total at Phase 9 close: ~729 Python + ~281 vitest + ~75 Playwright.

### Wave Structure (LOCKED — single wave, three tasks)

**Plan 09-01 — Endorsement Capture** (Wave 1, autonomous=true):
- Task 1: Python — schema + log + CLI + 3 test files (~25 tests)
- Task 2: Frontend — schema + fetcher + 2 test files (~15 tests)
- Task 3: Frontend — component + DecisionRoute mount + Playwright (~9 tests)

Hits requirements: ENDORSE-01, ENDORSE-02, ENDORSE-03.

</specifics>

<deferred>
## Deferred Ideas (v1.x successors)

- **Performance computation** — corp-action-aware (ENDORSE-04), vs S&P alpha (ENDORSE-05), perf rendering (ENDORSE-06), corp-action notice (ENDORSE-07).
- **Routine integration** — auto-capture from RSS feeds.
- **Edit/delete UI** — v1 is append-only purity.
- **CLI list / search subcommand** — `markets list_endorsements --ticker AAPL`. Frontend EndorsementsList covers v1.
- **Endorsement source taxonomy** — free-form string in v1; v1.x adds enum/normalization.
- **Duplicate detection** — append-only in v1; v1.x adds `--force` if user feedback demands.

</deferred>

---

*Phase: 09-endorsement-capture*
*Context gathered: 2026-05-04*
*Single-wave phase (1 PLAN, 3 tasks, ~49 tests, 0 new deps) — FINAL phase before v1 complete*
