# Phase 8: Mid-Day Refresh + Resilience — Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Source:** Research-derived (researcher recommendations adopted across 6 open questions)

<domain>
## Phase Boundary

Three additive surfaces:

1. **`api/refresh.py`** — Vercel Python serverless function. Thin adapter wrapping existing `ingestion.prices.fetch_prices()` + `ingestion.news.fetch_news(return_raw=True)`. NO LLM. Returns `{ticker, current_price, price_timestamp, recent_headlines, errors[]}`.
2. **Frontend on-open refresh** — TanStack Query hook `useRefreshData(symbol)` mounted on BOTH `TickerRoute` (deep-dive) AND `DecisionRoute` (decision view). Replaces Phase 7's `PHASE-8-HOOK` placeholder with live current-price delta.
3. **Memory log + provenance + resilience tests** — `routine/memory_log.py` writes per-persona JSONL records every routine run; `scripts/check_provenance.py` + pre-commit hook verifies provenance headers; failure-mode tests across the data pipeline.

**Out of phase boundary:**
- Frontend rendering of memory log (persona signal trends) — v1.x.
- Endorsement signals — Phase 9.
- LLM-driven re-summarize on demand — v1.x.

</domain>

<decisions>
## Implementation Decisions

### `api/refresh.py` Vercel Python Serverless (LOCKED)

**Location:** repo root `api/refresh.py` (Vercel auto-detects).

**Pattern:** `BaseHTTPRequestHandler` subclass named `handler` (Vercel's Python runtime convention).

**Endpoint:** GET `/api/refresh?ticker=AAPL`.

**Response shape (success):**
```json
{
  "ticker": "AAPL",
  "current_price": 178.42,
  "price_timestamp": "2026-05-04T19:32:11+00:00",
  "recent_headlines": [
    {"source": "Reuters", "published_at": "...", "title": "...", "url": "..."}
  ],
  "errors": [],
  "partial": false
}
```

**Response shape (partial failure — yfinance throws but yahooquery rescues, or RSS unavailable):**
```json
{
  "ticker": "AAPL",
  "current_price": 178.42,
  "price_timestamp": "...",
  "recent_headlines": [],
  "errors": ["rss-unavailable"],
  "partial": true
}
```

**Response shape (full failure — both yfinance + yahooquery throw):**
```json
{
  "ticker": "AAPL",
  "error": true,
  "errors": ["yfinance-unavailable", "yahooquery-unavailable"],
  "partial": true
}
```

**Vercel config (LOCKED):** `vercel.json` at repo root (NOT inside `frontend/`):
```json
{
  "functions": {
    "api/refresh.py": {"maxDuration": 30}
  }
}
```
30s default is 10× typical execution (yfinance ~1-2s + RSS ~0.5-2s = ~3-6s realistic), 10× under the 300s Hobby cap. Researcher confirmed 300s is current Hobby default with Fluid Compute.

**LOAD-BEARING FIX:** `frontend/vercel.json` SPA rewrite **must be narrowed** from current `/(.*)` → `/index.html` to `/((?!api/).*)` → `/index.html`. Without this fix, requests to `/api/refresh?ticker=AAPL` silently return HTML (the SPA index) instead of JSON, breaking the function with no error from Vercel's routing layer. Test this in the resilience suite.

**Path-resolution caveat:** Vercel Python serverless can't `import` from sibling top-level packages by default. The function file should sit at `api/refresh.py` and prepend the repo root to `sys.path` before importing `ingestion.prices` / `ingestion.news`. Alternative: copy `ingestion/prices.py` + `ingestion/news.py` into `api/` (worse — drift risk). Recommend the sys.path approach with a brief header comment.

### Frontend Integration (LOCKED — researcher recommendation #1 adopted)

`frontend/src/lib/useRefreshData.ts` — new TanStack Query hook:
```ts
export function useRefreshData(symbol: string) {
  return useQuery({
    queryKey: ['refresh', symbol],
    queryFn: () => fetchRefresh(symbol),
    staleTime: 5 * 60 * 1000,        // 5 min — refresh once per ticker view
    placeholderData: keepPreviousData, // no flicker on symbol change
    retry: 1,
  })
}
```

Mounted on **BOTH** `TickerRoute` AND `DecisionRoute` per researcher rec #1 (user is a "dual-timeframe focus" investor, both views are price-sensitive). TanStack Query dedupes by `queryKey: ['refresh', symbol]` — two route mounts share one fetch.

`<CurrentPriceDelta />` component renders next to the snapshot price, showing:
- `current_price` (large, bold, accent if positive delta, bearish if negative)
- delta % vs `snapshot.snapshot_summary.last_price` (if present in snapshot)
- "Refreshed {N}s ago" muted timestamp
- On `useRefreshData.isError`: "Refresh unavailable — showing snapshot price" muted notice. Snapshot stays canonical.

**MUST PRESERVE** `data-testid="current-price-placeholder"` on the new component (Phase 7's grep target stays valid for any future tooling). Replace the placeholder content but keep the test ID.

### Memory Log (LOCKED — INFRA-06)

**Location:** `memory/historical_signals.jsonl` (repo root, gitignored — local-only by default).

**Writer:** new `routine/memory_log.py` reusing the JSONL append pattern from `routine/llm_client._log_failure` (line 167) verbatim — same atomic-append + retry-on-tmp-collision discipline.

**Schema:**
```json
{"date": "2026-05-04", "ticker": "AAPL", "persona_id": "buffett", "verdict": "bullish", "confidence": 72, "evidence_count": 3}
```

One record per (ticker, persona) per routine run. ~30 tickers × 6 personas = 180 records/day. Append every run (researcher rec #2) — change-detection adds complexity without trivial-storage payoff (65K records/year ≈ ~10 MB JSONL).

Called from `routine/run_for_watchlist.py` after the per-ticker pipeline produces the 6 persona signals — Phase E in the existing per-ticker flow (Phases A-D are: load → analysts → personas → synthesizer; Phase E is the new memory log write).

**Frontend reads:** None in v1. Phase 8 just writes. The persona-trend frontend view ("Buffett shifted bearish 2 weeks ago") is v1.x.

### Provenance Check (LOCKED — INFRA-07)

**Location:** `scripts/check_provenance.py` (repo root) + pre-commit hook in `.pre-commit-config.yaml`.

**Pattern:** for every Python file in `analysts/`, `routine/`, `synthesis/`, `ingestion/`, `prompts/personas/*.md`, `prompts/synthesizer.md`: assert presence of one of three header markers in the first 30 lines:
- `Pattern adapted from <ref-repo>/<path>` (canonical reference adaptation)
- `Adapted from <ref-repo>/<path>` (shorter form, also valid)
- `# novel-to-this-project` (explicit marker for files NOT adapted from references — required for transparency)

Files without any of the three markers fail the check. Output: list of offenders + suggested marker.

Pre-commit hook runs on `pre-commit` stage; CI runs on `push`. Either fails the build / commit.

### Resilience Test Surface (LOCKED — REFRESH-04)

5 failure-mode tests added across the codebase:

1. **`tests/ingestion/test_prices.py`**: yfinance throws → yahooquery fallback returns successfully → snapshot saves with no error
2. **`tests/ingestion/test_prices.py`**: Both yfinance + yahooquery throw → snapshot saves with `data_unavailable: true` + clear error
3. **`tests/ingestion/test_news.py`**: RSS fetcher throws → `(headlines: [], sentiment_score: 0.0)` returned + error logged
4. **`tests/api/test_refresh.py`** (new): refresh function timeout simulation → returns 504 or partial response with `errors: ["timeout"]`
5. **`frontend/tests/e2e/resilience.spec.ts`**: refresh fetch fails (mock 500 from MSW or test fixture) → frontend continues rendering snapshot with "refresh unavailable" badge — NO crash, NO white-screen, snapshot stays canonical

### CORS (LOCKED — non-issue per research)

Frontend at `xxx.vercel.app/scan/today` → `xxx.vercel.app/api/refresh?ticker=AAPL` is same-origin. NO CORS headers needed in `api/refresh.py`. Confirmed via Vercel KB.

The vercel.json SPA-rewrite narrowing IS the load-bearing change to make routing work; CORS itself is not a concern.

### Schema Convention (LOCKED — researcher rec #4)

snake_case for refresh response fields (mirrors existing `data/{date}/{TICKER}.json` shape). Frontend zod schema at `frontend/src/schemas/refresh.ts` mirrors verbatim.

### `?since=` Filter (LOCKED — researcher rec #3)

Server is stateless. No `?since=` query parameter. Frontend filters "post-snapshot" headlines client-side (compares `recent_headlines[i].published_at` to `snapshot.computed_at`). Smaller blast radius — refresh function just returns recent headlines, frontend decides which are "new".

### Provenance Header Marker (LOCKED — researcher rec #5)

Use the header-marker pattern (allow `Adapted from` / `Pattern adapted from` / `# novel-to-this-project`) over an explicit allow-list. Self-documenting; survives file moves; explicit per-file ownership statement.

### vercel.json Location (LOCKED — researcher rec #6)

Repo root `vercel.json` (one source of truth covering both static frontend AND `api/` functions). The existing `frontend/vercel.json` gets the SPA-rewrite narrowing (`/((?!api/).*)`) but stops being the deploy-config root.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`ingestion/prices.py`**: `fetch_prices(ticker, period="1d")` already has yfinance + yahooquery fallback. `api/refresh.py` calls it directly.
- **`ingestion/news.py`** (Wave 0 amended in Phase 6): `fetch_news(ticker, return_raw=True)` returns `(headlines_list, sentiment_score)`. `api/refresh.py` uses this for headlines.
- **`routine/llm_client._log_failure`** (line 167): JSONL append pattern. `routine/memory_log.py` mirrors verbatim.
- **`frontend/src/lib/fetchSnapshot.ts`**: `fetchAndParse<T>` + typed-error class pattern. New `fetchRefresh` reuses.
- **`frontend/src/routes/DecisionRoute.tsx`** (lines 177-189): Phase 7 hookpoint with `data-testid="current-price-placeholder"` + `// PHASE-8-HOOK: current-price-delta` comment.

### Established Patterns

- **JSONL atomic append** — `_log_failure` pattern; same for memory log.
- **TanStack Query + zod-typed-error** — Phase 6 pattern; reused for refresh.
- **react-router data-router** — refresh hook mounts on existing routes; no routing changes.
- **shadcn UI primitives** — `<CurrentPriceDelta />` uses Card + Badge from existing inventory.

### Integration Points

- **Reads from**: `/api/refresh` (new) + existing `data/YYYY-MM-DD/{TICKER}.json` snapshot.
- **Writes to**: `memory/historical_signals.jsonl` (new, gitignored).
- **CI/pre-commit**: `scripts/check_provenance.py` invoked.
- **Vercel deploy**: `vercel.json` at repo root configures both static + functions.

### Constraints from Existing Architecture

- **Keyless data plane**: refresh function uses yfinance/yahooquery/feedparser only. NO API keys.
- **Notion-Clean palette** (Phase 6 lock): `<CurrentPriceDelta />` uses CSS variable tokens — no inline hex.
- **GitHub-as-DB**: snapshots stay in `data/YYYY-MM-DD/`. Memory log is local-only (gitignored) for v1; v1.x can revisit GitHub-write.

</code_context>

<specifics>
## Specific Ideas

### File Layout

```
api/
├─ refresh.py                       [new ~80 lines]

routine/
├─ memory_log.py                    [new ~60 lines — JSONL append + record assembly]
├─ run_for_watchlist.py             [extend +15 lines — Phase E memory log write]

scripts/
├─ check_provenance.py              [new ~120 lines — regex walker]

.pre-commit-config.yaml             [new or extend — provenance hook]

frontend/src/
├─ lib/useRefreshData.ts            [new ~40 lines — TanStack hook]
├─ schemas/refresh.ts               [new ~40 lines — zod schema]
├─ components/CurrentPriceDelta.tsx [new ~80 lines]
├─ routes/TickerRoute.tsx           [extend +15 lines — mount useRefreshData + render <CurrentPriceDelta />]
├─ routes/DecisionRoute.tsx         [extend +10 lines — replace placeholder with <CurrentPriceDelta />]

vercel.json                         [new at repo root — function config + SPA rewrite]
frontend/vercel.json                [extend — SPA rewrite narrowed to /((?!api/).*)]

tests/api/test_refresh.py           [new ~150 lines — 8-10 tests covering happy + 4 failure modes + timeout sim]
tests/ingestion/test_prices.py      [extend — 2 new resilience tests]
tests/ingestion/test_news.py        [extend — 1 new resilience test]
tests/routine/test_memory_log.py    [new ~80 lines — JSONL contract + atomic append]
tests/scripts/test_check_provenance.py [new ~80 lines — accept/reject test cases]

frontend/src/components/__tests__/CurrentPriceDelta.test.tsx [new ~100 lines]
frontend/src/lib/__tests__/useRefreshData.test.ts            [new ~80 lines]
frontend/src/schemas/__tests__/refresh.test.ts               [new ~40 lines]
frontend/tests/e2e/resilience.spec.ts                        [new ~80 lines]
```

### File Sizes Expected

Production: ~445 lines Python + ~250 lines TypeScript/TSX + ~30 lines config = ~725 lines net new.
Tests: ~310 lines Python + ~300 lines TypeScript = ~610 lines net new.

Total: ~1,335 lines.

### Wave Structure (suggested — planner finalizes)

**Wave 0 — Backend resilience + memory log + provenance** (single PLAN, autonomous=true):
- `api/refresh.py` + `tests/api/test_refresh.py`
- `routine/memory_log.py` + tests + `routine/run_for_watchlist.py` Phase E extension
- `scripts/check_provenance.py` + tests + `.pre-commit-config.yaml`
- Resilience-test extensions to `test_prices.py` + `test_news.py`
- `vercel.json` at repo root + frontend/vercel.json narrowing
- Hits requirements: REFRESH-01, REFRESH-04 (partial — backend portion), INFRA-06, INFRA-07

**Wave 1 — Frontend refresh integration** (single PLAN, autonomous=true):
- `frontend/src/schemas/refresh.ts`
- `frontend/src/lib/useRefreshData.ts`
- `frontend/src/components/CurrentPriceDelta.tsx`
- `TickerRoute.tsx` + `DecisionRoute.tsx` extensions
- Component tests + E2E resilience.spec.ts
- Hits requirements: REFRESH-02, REFRESH-03, REFRESH-04 (full)

Two-wave structure: backend can be tested + deployed independently; frontend integration tests against a deployed function (or mocked for unit tests).

### Test Surface

- Python: ~25 new tests (refresh function happy + failure modes + memory log + provenance + resilience extensions)
- Vitest: ~20 new tests (refresh schema + useRefreshData hook + CurrentPriceDelta component)
- Playwright: 1 new E2E (resilience.spec.ts — refresh fail handling)

Total: ~46 new tests. Repo total at Phase 8 close: ~684 Python + ~254 vitest + ~64 Playwright.

### Provenance Header Examples

```python
# Pattern adapted from virattt/ai-hedge-fund/src/agents/warren_buffett.py
# — modified for keyless data layer and watchlist-mode operation.
```

```python
# novel-to-this-project — orchestration layer not directly adapted from any reference.
```

```markdown
<!-- Pattern adapted from TauricResearch/TradingAgents/tradingagents/agents/managers/portfolio_manager.py -->
```

</specifics>

<deferred>
## Deferred Ideas

- **Memory log frontend view** (persona-signal trend "Buffett shifted bearish 2 weeks ago") — needs Phase 8's writes to accumulate; v1.x.
- **GitHub-write of memory log** — currently local-only (gitignored). v1.x revisits if user wants cross-device persistence.
- **Server-side `?since=` filter** for headlines — stateless function design lock; client filters.
- **Refresh on staleness threshold breach** — auto-refresh when StalenessBadge goes RED; v1.x UX polish.
- **Refresh-on-demand button** in StalenessBadge — manual trigger; v1.x UX polish.
- **Prometheus / observability** for refresh function — Vercel function logs cover v1; v2 territory.
- **Endpoint-key auth** on `/api/refresh` — single-user no-auth lock; v1 no auth at all (function URL is by-default not enumerated, low risk).
- **Streaming response** from refresh function — fixed payload; HTTP 200 + JSON body works.

</deferred>

---

*Phase: 08-mid-day-refresh-resilience*
*Context gathered: 2026-05-04*
*Two-wave phase (Wave 0 backend, Wave 1 frontend); ~46 new tests; researcher confirmed Vercel Hobby 300s timeout (NOT 10s)*
