---
phase: 8
title: Mid-Day Refresh + Resilience
researched: 2026-05-04
domain: Vercel Python serverless (api/refresh.py) + frontend on-open refresh + memory-log discipline + provenance CI gate + end-to-end resilience verification
confidence: HIGH (Vercel + TanStack patterns verified at official docs; memory-log + provenance grounded in Phase 1-7 internal precedent); MEDIUM (cold-start timing for yfinance/feedparser combo — derived from public benchmarks, not project-measured)
research_tier: normal
vault_reads: []
vault_status: not_configured
---

# Phase 8: Mid-Day Refresh + Resilience — Research

## Summary

Phase 8 ships **four deliverables** against six requirements:

1. **`api/refresh.py`** — a Vercel Python serverless function that wraps existing `ingestion.prices.fetch_prices()` + `ingestion.news.fetch_news(return_raw=True)` and returns a JSON envelope `{ticker, current_price, price_timestamp, recent_headlines, errors[], partial}`. **No LLM**. Reuses keyless data plane (yfinance + yahooquery fallback + RSS).
2. **Frontend on-open refresh** — TanStack Query hook `useRefreshData(symbol)` fired on TickerRoute + DecisionRoute mount; merges fresh price into the snapshot view via `placeholderData: keepPreviousData` to prevent flicker; populates the existing `data-testid="current-price-placeholder"` lock-in DOM target on DecisionRoute (Phase 7 hookpoint).
3. **Memory log writes** — `routine/run_for_watchlist.py` extended (or `routine/storage.py` extended) to append per-persona records to `memory/historical_signals.jsonl` after every routine run. Reuses the EXISTING JSONL append pattern from `routine/llm_client.py` (`_log_failure`).
4. **Provenance check** — `scripts/check_provenance.py` pre-commit hook + CI gate that greps reference-adapted Python files for the established `# Adapted from <reference-path>` header pattern (already present in 9 files: 5 analysts + synthesis/decision.py + synthesis/synthesizer.py + routine/llm_client.py + routine/persona_runner.py + 5 persona prompts).

**Single most important finding (HIGH confidence, pivotal):** **The orchestrator prompt's "10s Vercel Hobby plan default timeout" is OUTDATED.** As of 2026 with **Fluid Compute enabled by default for new Vercel projects (since 2025-04-23)**, the Hobby plan default AND maximum is **300s (5 minutes)**. Phase 8 is dramatically less constrained than the brief implied. This changes the design space — yfinance import + price fetch + RSS fetch (~3-12s total even on cold start) fits comfortably with massive headroom, no exotic optimization needed.

**Second most important finding (HIGH confidence):** **Same-origin CORS is functionally a non-issue when the Vite static frontend AND `api/refresh.py` are deployed to the SAME Vercel project.** The frontend at `xxx.vercel.app` calling `/api/refresh?ticker=AAPL` is same-origin — the browser never preflights, never blocks. CORS only becomes a concern if the frontend is hosted elsewhere. The current `frontend/vercel.json` rewrites `/(.*)` → `/index.html` for SPA routing — that wildcard MUST be narrowed to NOT swallow `/api/*` paths (Vercel auto-handles `/api/*` before the rewrite, but explicit narrowing eliminates ambiguity).

**Third most important finding (HIGH confidence):** The frontend-side merge pattern is **two parallel `useQuery` hooks**, not one composite query. `useTickerData(date, symbol)` (existing, snapshot from `raw.githubusercontent.com`) and `useRefreshData(symbol)` (new, refresh from `/api/refresh`). The snapshot is the source of truth; refresh is decorative freshness. When refresh is loading or failed, the UI shows snapshot price; when refresh succeeds, the UI shows fresh price + delta. This is the TanStack v5 idiom (separate query keys, `placeholderData: keepPreviousData` for the refresh hook on symbol change) — confirmed at the official 2026 v5 docs.

**Primary recommendation:** Lock `api/refresh.py` as a `BaseHTTPRequestHandler`-based handler at the **repo root `/api/refresh.py`** (NOT under `frontend/`) so Vercel auto-detects the Python runtime alongside the Vite static frontend. Set `vercel.json.functions["api/refresh.py"].maxDuration = 30` (defensive — 10× the typical execution time but well under the 300s cap; avoids billing surprises). Reuse `ingestion/prices.py` and `ingestion/news.py` verbatim — the function is a 30-50 line adapter, not new fetch code. Memory log appends via the same atomic-line `json.dumps(record, sort_keys=True) + "\n"` pattern already in `routine/llm_client._log_failure` (no new framework).

## User Constraints (from CONTEXT.md)

**No CONTEXT.md exists for Phase 8 yet** — this is research-first / discuss-after for Phase 8. The orchestrator prompt's `<additional_context>` block carries the constraints in lieu of CONTEXT.md:

### Locked Decisions (from orchestrator prompt + ROADMAP success criteria)

- **Function location**: `api/refresh.py` Vercel Python serverless function (REFRESH-01).
- **Function inputs/outputs**: GET `?ticker=AAPL` → JSON envelope including `{ticker, current_price, price_timestamp, recent_headlines, errors[], partial}` (REFRESH-02).
- **No LLM in refresh**: prices + RSS only — keyless data plane lock from PROJECT.md.
- **Frontend integration point**: DecisionRoute.tsx already has `data-testid="current-price-placeholder"` + `// PHASE-8-HOOK: current-price-delta` markers from Phase 7 (REFRESH-03).
- **Failure-mode coverage**: yfinance fail → yahooquery fallback; RSS fail → partial response with `error: true`; function timeout → frontend continues with snapshot (REFRESH-04).
- **Memory log**: `memory/historical_signals.jsonl` append-only with `{date, ticker, persona_id, signal, confidence}` (INFRA-06).
- **Provenance gate**: CI / pre-commit script verifies provenance headers on reference-adapted code (INFRA-07).

### Claude's Discretion

- **Maximum function duration in `vercel.json`**: research recommends 30s (defensive cap; well under 300s ceiling).
- **Frontend hook architecture**: research recommends two parallel `useQuery` hooks (`useTickerData` existing + `useRefreshData` new) with `placeholderData: keepPreviousData` on the refresh hook.
- **Memory log write location**: research recommends a new `routine/memory_log.py` module (single responsibility) called from `routine/storage.py` after `_index.json` write — keeps storage atomic-write discipline pure and adds memory-log writes as a 4th phase.
- **Should `useRefreshData` mount on TickerRoute (deep-dive) too, or only DecisionRoute?**: research **recommends both** — both views show price-sensitive data; deep-dive is "what's the data" view, decision is "what should I do" view; both benefit from current-price freshness.
- **Memory log write frequency**: research recommends **append every routine run** (not "only when signals change") — simpler, cheaper, future trend view in v1.x reads chronologically anyway.
- **Provenance hook implementation**: research recommends a Python script + pre-commit hook entry; pure-Python (no external deps), runs in <100ms.

### Deferred Ideas (OUT OF SCOPE — do NOT include in plan)

- Frontend trend visualization reading `historical_signals.jsonl` — v1.x (TREND-01, TREND-02 in REQUIREMENTS.md).
- On-demand re-synthesize button (mid-day re-LLM) — v1.x (OND-01, OND-02).
- Pydantic→zod schema codegen + drift CI check — Phase 8 / v1.x; defer to v1.x per Phase 6 lock.
- Switch Playwright webServer from `pnpm preview` to `pnpm dev` — recurring foot-gun documented in Phases 6+7 SUMMARYs; v1.x QoL.
- GitHub-as-DB scaling (separate `markets-data` repo, monthly compaction) — Pitfall #11 mitigation; only triggered after >5K files in `data/`.
- Refresh function caching layer (Vercel Edge Cache, KV) — premature; per-ticker per-call is fine at 30-50 ticker scale.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REFRESH-01 | Mid-day refresh runs as Vercel Python serverless function at `api/refresh.py` | Vercel Python runtime locked at 3.12 default with `BaseHTTPRequestHandler` handler pattern; deployed at repo-root `/api/refresh.py` (Vercel auto-detects); see "Standard Stack" + "Vercel Deployment Mechanics" |
| REFRESH-02 | Refresh accepts `?ticker=X`, fetches current price (yfinance) + headlines published since snapshot timestamp (RSS) — no LLM calls | Reuses `ingestion.prices.fetch_prices(ticker, period="1d")` + `ingestion.news.fetch_news(ticker, return_raw=True)` verbatim; "since snapshot" timestamp filtering happens client-side OR by passing `?since=ISO-8601` param (recommend client-side filter — keeps function stateless) |
| REFRESH-03 | Frontend Deep-Dive page triggers refresh on open and merges results into rendered state | TanStack Query v5 `useQuery({ queryKey: ['refresh', symbol], placeholderData: keepPreviousData })` mounted in TickerRoute + DecisionRoute; merge happens at render time (snapshot is source of truth, refresh decorates current_price + post-snapshot headlines) |
| REFRESH-04 | Refresh completes within 10s Vercel timeout; on yfinance/RSS failure returns partial response with explicit `error: true` flag and frontend continues to show snapshot data | **CONSTRAINT UPDATE**: Vercel Hobby 2026 default = 300s (Fluid Compute enabled by default since 2025-04-23). The "10s" in the requirement is conservative budget, not a Vercel limit. Set `vercel.json.functions["api/refresh.py"].maxDuration = 30` defensively. yfinance fallback is INTERNAL to `fetch_prices()` (Phase 2 already implements yahooquery fallback); RSS fail handled at `fetch_news()` per-source-isolated try/except (Phase 2 already does this); function-level timeout handled by frontend's TanStack `error` branch — render snapshot price + "refresh failed" badge |
| INFRA-06 | Memory layer writes append-only `memory/historical_signals.jsonl` per run with `{date, ticker, persona_id, signal, confidence}` records | New module `routine/memory_log.py` with `append_persona_signals(date, ticker_results) -> None`; called from `routine/storage.write_daily_snapshot` as Phase D step (after `_dates.json` write); reuses the line-append + `json.dumps(sort_keys=True)` + `"\n"` pattern from `routine/llm_client._log_failure` |
| INFRA-07 | Provenance: every reference-adapted code file carries header comment naming source file + modifications | New `scripts/check_provenance.py` + `.pre-commit-config.yaml` entry; pure-Python regex walker over `analysts/`, `synthesis/`, `routine/`, `prompts/personas/`; allow-list of files known to NOT need provenance (e.g. `__init__.py`, novel-to-this-project files); fails CI / blocks commit when an adapted-looking file lacks `Adapted from <path>` or `Pattern adapted from <path>` |

## Standard Stack

### Core (Phase 8 — what's NEW)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **Vercel Python runtime** | Python 3.12 (default in 2026; 3.13 + 3.14 also available) | Serverless function host | Vercel auto-detects `api/*.py` files with `handler` class inheriting `BaseHTTPRequestHandler` OR `app` ASGI/WSGI variable. We use `BaseHTTPRequestHandler` — minimal, matches the simple GET surface. |
| **yfinance** | already pinned `>=0.2.50,<0.3` (project-wide) | Price fetch path inside refresh function | Reuses existing `ingestion.prices.fetch_prices` — zero new deps |
| **yahooquery** | already pinned `>=2.3,<3` (project-wide) | yfinance fallback inside refresh function | Reuses existing fallback path — zero new deps |
| **feedparser** | already pinned `>=6.0,<7` (project-wide) | RSS fetch inside refresh function | Reuses existing `ingestion.news.fetch_news` — zero new deps |
| **TanStack Query v5** | already pinned `^5.59.0` (frontend) | On-open refresh merge | Reuses existing `useQuery` pattern; `placeholderData: keepPreviousData` import is from `@tanstack/react-query` (no new dep) |
| **pre-commit framework** | latest (NEW dev dep — optional, can run as plain script) | Provenance check at commit time | Industry standard; minimal config; runs the `scripts/check_provenance.py` Python script |

### Supporting (existing project infra reused)

| Library | Purpose | When to Use |
|---------|---------|-------------|
| `BaseHTTPRequestHandler` (stdlib) | Vercel Python serverless handler base class | Default for simple GET endpoints — DO NOT pull in FastAPI / Flask for one endpoint |
| `urllib.parse` (stdlib) | Parse query string `?ticker=AAPL` from `self.path` | Standard pattern in Vercel Python examples |
| `json` (stdlib) | Serialize response body | Already used throughout project |
| `pydantic` (existing pin) | Optional: validate refresh response shape before serialization | RECOMMEND — single source of truth for refresh response schema; the same Pydantic model can be re-exported as a TS type via shared schema discipline |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `BaseHTTPRequestHandler` (stdlib) | FastAPI ASGI app | FastAPI auto-validates Pydantic in/out — but adds ~5MB cold-start dep; overkill for a single GET endpoint; matches project's "don't pull in framework when 30 lines of stdlib work" discipline (Pitfall #10 — premature abstraction) |
| `BaseHTTPRequestHandler` (stdlib) | Flask WSGI app | Mature but same "extra dep for one endpoint" objection; less popular in 2026 vs FastAPI |
| TanStack Query v5 `placeholderData: keepPreviousData` | Single composite query that returns merged shape | Composite query couples snapshot fetch + refresh fetch in lockstep — losing the "snapshot is source of truth even if refresh fails" property; harder to reason about loading states; pattern recommended against in TanStack v5 docs |
| `routine/memory_log.py` (new module) | Inline append in `routine/storage.py` | Inline is shorter but mixes concerns — storage is "snapshot per ticker"; memory-log is "persona signals across all tickers"; separating the modules makes the call-site explicit and the test surface clean |
| Pre-commit hook (Python script) | GitHub Actions workflow only | CI-only catches violations after commit — slower feedback loop; pre-commit is local + faster; can enable BOTH (pre-commit for fast local + GH Actions as backstop) |
| Provenance grep script | LLM-based provenance review | LLM is overkill — provenance is a regex problem (header comment present? cite a `<reference>/<path>` pattern? exit 0 or 1) |

**Installation (planner reference):**

```bash
# No new Python runtime deps — yfinance/yahooquery/feedparser already pinned
# No new frontend deps — TanStack Query v5 already pinned

# Optional pre-commit dev dep (can also run script directly without framework):
uv add --dev pre-commit

# Provenance check script — pure stdlib (re, pathlib, sys); no install step
```

## Architecture Patterns

### Recommended Project Structure (Phase 8 additions only)

```
markets/
├── api/                              # NEW — Vercel auto-detects
│   └── refresh.py                    # ~80 LOC; wraps fetch_prices + fetch_news
├── frontend/                         # existing
│   ├── src/
│   │   ├── lib/
│   │   │   ├── fetchRefresh.ts       # NEW — fetch + zod-parse helper
│   │   │   └── useRefreshData.ts     # NEW — TanStack Query hook
│   │   ├── schemas/
│   │   │   └── refresh.ts            # NEW — zod schema for refresh envelope
│   │   ├── components/
│   │   │   └── CurrentPriceDelta.tsx # NEW — replaces Phase 7 placeholder
│   │   └── routes/
│   │       ├── DecisionRoute.tsx     # MODIFY — replace placeholder with <CurrentPriceDelta />
│   │       └── TickerRoute.tsx       # MODIFY — add <CurrentPriceDelta /> alongside snapshot price
├── routine/
│   ├── memory_log.py                 # NEW — append_persona_signals
│   ├── storage.py                    # MODIFY — call memory_log after Phase D
│   └── run_for_watchlist.py          # NO CHANGE (already produces TickerResults that memory_log consumes)
├── scripts/                          # NEW directory
│   └── check_provenance.py           # ~120 LOC; pure-Python regex walker
├── tests/
│   ├── api/                          # NEW
│   │   └── test_refresh.py           # ~150 LOC; mock yfinance/feedparser; cover 5 failure modes
│   ├── routine/
│   │   └── test_memory_log.py        # NEW; ~80 LOC; covers append + serialization
│   └── scripts/                      # NEW
│       └── test_check_provenance.py  # NEW; ~80 LOC; covers detect-success + detect-violation paths
├── frontend/src/lib/__tests__/
│   └── useRefreshData.test.ts        # NEW; ~80 LOC; happy + error + stale-fallback branches
├── frontend/src/components/__tests__/
│   └── CurrentPriceDelta.test.tsx    # NEW; ~80 LOC; matrix of (refresh ok/loading/error) × (price up/down/flat)
├── frontend/tests/e2e/
│   └── refresh.spec.ts               # NEW; ~80 LOC; Playwright happy path + RSS-down failure mode
├── memory/                           # already exists (llm_failures.jsonl present)
│   └── historical_signals.jsonl      # NEW (or grows with new appends)
├── vercel.json                       # NEW at repo root (frontend/vercel.json moves up OR add a new one)
└── .pre-commit-config.yaml           # NEW; pre-commit framework entry for check_provenance
```

### Pattern 1: Vercel Python Serverless Function (BaseHTTPRequestHandler)

**What:** Subclass `BaseHTTPRequestHandler`; implement `do_GET`; parse query string from `self.path`; call existing `fetch_prices` + `fetch_news`; serialize response as JSON; write to `self.wfile`. The handler class MUST be named `handler` (lowercase) — Vercel's autodetect convention.

**When to use:** Simple GET endpoints with no auth, no streaming, no framework needs. PERFECT fit for Phase 8 — zero framework, zero magic, fits in 80 LOC.

**Example:**
```python
# Source: https://vercel.com/docs/functions/runtimes/python (verified 2026-05-04)
# Pattern adapted from Vercel Python runtime documentation — modified to wrap
# the project's existing keyless ingestion stack (ingestion.prices.fetch_prices
# + ingestion.news.fetch_news) for the on-open refresh contract.
"""api/refresh.py — Vercel Python serverless mid-day refresh.

Public surface:
    GET /api/refresh?ticker=AAPL
        → 200 JSON {ticker, current_price, price_timestamp,
                    recent_headlines, errors, partial}

Behaviour:
    - data_unavailable=True from fetch_prices → current_price=null + errors+=["price-unavailable"] + partial=true
    - empty headlines from fetch_news → recent_headlines=[] + errors+=["rss-unavailable"] + partial=true (ONLY if both also fail)
    - any caught exception → 200 with errors=[repr(exc)] + partial=true (NEVER 5xx; frontend distinguishes
      by inspecting the envelope, not the status code)

Why no LLM here: PROJECT.md keyless data plane lock + REFRESH-02 explicit "no LLM calls".
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from ingestion.news import fetch_news
from ingestion.prices import fetch_prices


def _build_envelope(ticker: str) -> dict:
    """Return the canonical refresh envelope; never raises."""
    errors: list[str] = []
    partial = False

    # Price path — fetch_prices NEVER raises (Phase 2 lock); always returns
    # PriceSnapshot with data_unavailable=True if both yfinance + yahooquery fail.
    price_snap = fetch_prices(ticker, period="1d")
    if price_snap.data_unavailable:
        current_price = None
        price_timestamp = None
        errors.append("price-unavailable")
        partial = True
    else:
        current_price = price_snap.current_price
        price_timestamp = price_snap.fetched_at.isoformat()

    # News path — fetch_news NEVER raises; absorbs per-source failures silently.
    # We treat empty headlines as "RSS unavailable" only if it's persistent;
    # for v1 we surface the empty list with errors+=["rss-empty"] for diagnostics.
    headlines, raw = fetch_news(ticker, return_raw=True)
    recent_headlines = raw[:20]  # cap response size — frontend filters by since-snapshot client-side
    if not raw:
        errors.append("rss-empty")
        partial = True

    return {
        "ticker": ticker,
        "current_price": current_price,
        "price_timestamp": price_timestamp,
        "recent_headlines": recent_headlines,
        "errors": errors,
        "partial": partial,
    }


class handler(BaseHTTPRequestHandler):  # noqa: N801 — Vercel autodetect convention
    def do_GET(self) -> None:  # noqa: N802 — BaseHTTPRequestHandler convention
        try:
            qs = parse_qs(urlparse(self.path).query)
            ticker_raw = (qs.get("ticker") or [""])[0]
            ticker = ticker_raw.strip().upper()
            if not ticker:
                self._respond(400, {"errors": ["missing-ticker"], "partial": True})
                return

            envelope = _build_envelope(ticker)
            self._respond(200, envelope)
        except Exception as exc:  # noqa: BLE001 — never surface 5xx; frontend reads errors
            self._respond(
                200,
                {
                    "ticker": "",
                    "current_price": None,
                    "price_timestamp": None,
                    "recent_headlines": [],
                    "errors": [f"handler-failure: {exc!r}"],
                    "partial": True,
                },
            )

    def _respond(self, status: int, body: dict) -> None:
        payload = json.dumps(body, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)
```

**Key locks in this pattern:**
- Class name MUST be `handler` (lowercase) — Vercel autodetect.
- The handler module MUST live at `<repo-root>/api/refresh.py` — Vercel checks `api/` at the project root.
- Imports of `ingestion.prices` + `ingestion.news` work because Vercel includes ALL files reachable at build time (per Python runtime docs, no automatic tree-shaking) — the existing `pyproject.toml` declares the packages so they're bundled.
- `Cache-Control: no-store` — refresh is by definition fresh data; do not let edge cache linger.

### Pattern 2: Frontend Two-Hook Merge (TanStack Query v5)

**What:** Two parallel `useQuery` hooks. Snapshot is source of truth (cached, stale-while-revalidate from `raw.githubusercontent.com`). Refresh is decorative freshness (TanStack-managed, with `placeholderData: keepPreviousData` to prevent flicker on symbol change).

**When to use:** Whenever a view needs both stable historical data AND a real-time-ish overlay. Phase 8 fits this exactly.

**Example:**
```typescript
// Source: https://tanstack.com/query/v5/docs/framework/react/guides/placeholder-query-data
// Pattern adapted from TanStack Query v5 placeholder docs — modified to layer
// a refresh fetch on top of an existing snapshot fetch where the snapshot is
// the source of truth even when refresh fails (Phase 2 keyless data plane
// resilience model).
import { useQuery, keepPreviousData } from '@tanstack/react-query'
import { z } from 'zod'

import { fetchAndParse } from './fetchSnapshot'

export const RefreshEnvelopeSchema = z.object({
  ticker: z.string(),
  current_price: z.number().nullable(),
  price_timestamp: z.string().nullable(),
  recent_headlines: z.array(z.object({
    source: z.string(),
    published_at: z.string().nullable(),
    title: z.string(),
    url: z.string(),
  })),
  errors: z.array(z.string()),
  partial: z.boolean(),
})
export type RefreshEnvelope = z.infer<typeof RefreshEnvelopeSchema>

const refreshUrl = (symbol: string) =>
  `/api/refresh?ticker=${encodeURIComponent(symbol)}`

export function useRefreshData(symbol: string) {
  return useQuery<RefreshEnvelope, Error>({
    queryKey: ['refresh', symbol],
    queryFn: () => fetchAndParse(refreshUrl(symbol), RefreshEnvelopeSchema),
    placeholderData: keepPreviousData,  // Prevent flicker on symbol change
    staleTime: 60_000,                   // 1 min — refresh is "fresh enough" for 60s
    gcTime: 5 * 60_000,                  // 5 min retention in cache
    retry: 1,                            // One retry on transient network blip; don't hammer
  })
}
```

**Then in DecisionRoute / TickerRoute:**
```typescript
// Replace the Phase 7 PHASE-8-HOOK placeholder block with:
import { CurrentPriceDelta } from '@/components/CurrentPriceDelta'
// ... in the JSX where the placeholder lived:
<CurrentPriceDelta
  symbol={symbol}
  snapshotPrice={dec.snapshot_price /* or wherever it lives */}
  snapshotComputedAt={dec.computed_at}
/>
```

**`<CurrentPriceDelta />` internals (high-level):**
- Calls `useRefreshData(symbol)` itself.
- `if (refresh.isLoading || refresh.isError)` → render snapshot price only + tiny muted "refresh pending / failed" badge.
- `if (refresh.data && !refresh.data.partial && refresh.data.current_price)` → render snapshot price + delta arrow + percent + colored bullish/bearish based on sign.
- Pitfall #2 lock: never silently absent. Always render the placeholder shell so the data-testid persists for E2E.

### Pattern 3: Memory Log Append (reused JSONL pattern from llm_client._log_failure)

**What:** Append-only `memory/historical_signals.jsonl` written by routine after every successful run. One line per (ticker × persona × date). At ~30 tickers × 6 personas = 180 lines/day; ~65K lines/year — well under any practical limit.

**When to use:** v1 INFRA-06 closeout. Reads happen in v1.x (TREND-01, TREND-02 — out of scope here).

**Example:**
```python
# Source: routine/llm_client._log_failure (existing pattern; line 167 onward)
# Pattern adapted from internal-precedent (project's own llm_failures.jsonl
# discipline) — single-source-of-truth for "append-only JSONL line discipline"
# in this project.
"""routine/memory_log.py — append-only persona signal log per INFRA-06.

Schema per line (sort_keys=True):
    {date: ISO YYYY-MM-DD, ticker: STRING, persona_id: STRING,
     signal: STRING, confidence: INT}

Why JSONL not SQLite: matches project-wide GitHub-as-DB lock; readable in git
diffs; no binary blobs; v1.x readers are trivial. Migration to SQLite/Supabase
is a Pitfall #11 trigger (>5K records / day or >100K total) — both well above
v1 scale.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, TYPE_CHECKING

if TYPE_CHECKING:
    from routine.run_for_watchlist import TickerResult

logger = logging.getLogger(__name__)

HISTORICAL_SIGNALS_LOG: Path = Path("memory/historical_signals.jsonl")


def append_persona_signals(
    *,
    snapshot_date: str,
    ticker_results: Iterable["TickerResult"],
    log_path: Path = HISTORICAL_SIGNALS_LOG,
) -> int:
    """Append one line per (ticker × persona) for a single routine run.

    Returns the number of lines appended (== sum of persona_signals across
    ticker_results). Skips ticker_results with errors set (pipeline failed)
    and ticker_results with empty persona_signals (lite-mode skip).

    Atomic write per line: open in append mode + single write() of the
    full line + closing brace + newline. JSONL semantics: each line is
    independently parseable; partial-write at file end never corrupts
    earlier records.
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    appended = 0
    with log_path.open("a", encoding="utf-8") as f:
        for result in ticker_results:
            if result.errors:
                continue  # pipeline failure — skip
            if not result.persona_signals:
                continue  # lite-mode skip
            for sig in result.persona_signals:
                record = {
                    "date": snapshot_date,
                    "ticker": result.ticker,
                    "persona_id": sig.analyst_id,
                    "signal": sig.signal,
                    "confidence": sig.confidence,
                }
                line = json.dumps(record, sort_keys=True) + "\n"
                f.write(line)
                appended += 1
    return appended
```

**Integration point:** `routine/storage.write_daily_snapshot()` calls `append_persona_signals(snapshot_date=date, ticker_results=results)` after Phase D (`_dates.json` write) — making memory log Phase E in the locked write order.

### Pattern 4: Provenance CI Gate

**What:** Pure-Python script walks designated directories; for each `.py` file (or `.md` for persona prompts), check the first 30 lines contain a regex like `^Adapted from <reference-path>` OR `^Pattern adapted from <reference-path>`. The reference-path must contain `/` (a path-shape) and one of `virattt/ai-hedge-fund` or `TauricResearch/TradingAgents` OR an explicit "novel-to-this-project" allow-list marker.

**When to use:** INFRA-07 closeout. Runs at pre-commit AND in CI as a safety net.

**Example:**
```python
# Source: novel-to-this-project — implements the project's own provenance
# discipline lock from PROJECT.md. No external pattern adapted.
"""scripts/check_provenance.py — INFRA-07 enforcement.

Walks designated paths; for each Python module / Markdown prompt file,
verifies a provenance header is present in the first ~30 lines. The header
matches one of:

    Adapted from <reference-path>
    Pattern adapted from <reference-path>
    novel-to-this-project — <free-form rationale>

Files in the explicit ALLOW_LIST (e.g. __init__.py, package boilerplate,
test files) are skipped. Files in PROVENANCE_PATHS that match neither
pattern fail the script with exit code 1 and a list of violators.

Usage:
    python scripts/check_provenance.py            # walk default paths
    python scripts/check_provenance.py path1 ...  # walk explicit paths

Exit codes:
    0 — every file under PROVENANCE_PATHS passes the check
    1 — at least one violator (path printed to stderr)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROVENANCE_PATHS: tuple[Path, ...] = (
    Path("analysts"),
    Path("synthesis"),
    Path("routine"),
    Path("ingestion"),
    Path("prompts/personas"),
)

# Files that are package-boilerplate or known-novel-to-this-project — skip.
ALLOW_LIST: frozenset[Path] = frozenset({
    Path("analysts/__init__.py"),
    Path("synthesis/__init__.py"),
    Path("routine/__init__.py"),
    Path("ingestion/__init__.py"),
    # ... add more as encountered
})

# Provenance pattern: header line within first 30 lines starting with
# "Adapted from", "Pattern adapted from", or "novel-to-this-project".
PATTERN = re.compile(
    r"(Adapted from|Pattern adapted from|novel-to-this-project)",
    re.IGNORECASE,
)

EXTENSIONS: frozenset[str] = frozenset({".py", ".md"})

HEADER_LINE_LIMIT = 30


def is_violator(path: Path) -> bool:
    """Return True if `path` lacks a provenance marker in its first 30 lines."""
    try:
        with path.open("r", encoding="utf-8") as f:
            head = "".join(line for _, line in zip(range(HEADER_LINE_LIMIT), f))
    except OSError:
        return True  # unreadable file — block commit
    return not PATTERN.search(head)


def main(argv: list[str]) -> int:
    paths = [Path(p) for p in argv[1:]] if len(argv) > 1 else list(PROVENANCE_PATHS)
    violators: list[Path] = []
    for root in paths:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in EXTENSIONS:
                continue
            if path in ALLOW_LIST:
                continue
            if is_violator(path):
                violators.append(path)
    if violators:
        print("Provenance check FAILED — missing 'Adapted from' / 'Pattern adapted from' / 'novel-to-this-project' header in:", file=sys.stderr)
        for v in violators:
            print(f"  - {v}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

**Pre-commit hook entry:**
```yaml
# Source: pre-commit framework docs (https://pre-commit.com/)
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: check-provenance
        name: Check provenance headers (INFRA-07)
        entry: python scripts/check_provenance.py
        language: system
        pass_filenames: false
        always_run: true
```

### Anti-Patterns to Avoid

- **Pulling in FastAPI/Flask for one endpoint:** Pitfall #10 (premature abstraction); 30 lines of stdlib `BaseHTTPRequestHandler` is enough.
- **Letting refresh return non-200 status codes:** Frontend cannot distinguish "function unavailable" (network 502) from "function ran but data unavailable" (200 with `partial=true`) easily; collapse all error states into 200-with-error-envelope. Only return 4xx for malformed requests (missing `?ticker=`).
- **Making refresh stateful (cache, sessions):** Pitfall #10; functions are stateless by design; per-call latency is fine at single-user scale.
- **Composite query merging snapshot + refresh into one fetch:** Couples sources of truth; loses "snapshot is canonical even if refresh fails" semantics.
- **Writing memory log MID-routine (per-ticker as it completes):** Defeats the atomic write discipline; if routine fails halfway, memory log shows partial. Write all-or-nothing AFTER `_index.json` + `_status.json` confirm a successful run.
- **Provenance check that lints comments inside file body:** False positives explode (any comment mentioning "adapted from" anywhere in code passes); restrict to first 30 lines of file (header zone only).
- **Exposing query params in Vercel function logs:** Pitfall (Security Mistakes table in PITFALLS.md): `self.path` → log surface includes `?ticker=AAPL` → user's research watchlist leaks into platform logs. Either redact at log-time OR use `Vercel-Project-Settings > Logs > Redact` features.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP request parsing in Vercel function | Custom regex over `self.path` | `urllib.parse.parse_qs` (stdlib) | Edge-cases: URL encoding, multiple values, missing params, malformed input |
| TanStack Query merge logic for stale + fresh | Custom React state + useEffect orchestration | `placeholderData: keepPreviousData` from `@tanstack/react-query` | Already handles cache lifecycle, garbage collection, refetch-on-mount, retries |
| JSONL append discipline | Manual file open + write + close | Reuse `routine/llm_client._log_failure` PATTERN (not the function — copy the discipline into `routine/memory_log.py`) | Already proven through Phase 5; consistency = future debuggability |
| Pydantic ↔ zod schema for refresh envelope | Hand-author both sides separately | (Phase 8 / v1.x deferred — hand-author both for v1 honestly per Phase 6 lock; CI-check drift in v1.x) | Pydantic→zod codegen tooling not stable enough yet (per Phase 6 research Open Q #10) |
| Provenance regex walker | Bash `find ... -exec grep ...` | Pure-Python script | Cross-platform (Windows users can't rely on POSIX find/grep); easier test surface |
| Vercel cold-start optimization | Lazy imports / package compression / Lambda Layers | Trust 2026 Fluid Compute defaults; measure first | Pitfall #10 — premature optimization; 300s budget vs ~3-12s actual is 25-100× headroom |

**Key insight:** Phase 8 is a *thin* phase. The heavy lifting (yfinance/yahooquery/RSS fetch, Pydantic schemas, atomic-write JSONL discipline, TanStack Query setup) all exists from Phases 2-7. Phase 8 is wiring + boundary code.

## Common Pitfalls

### Pitfall 1: yfinance Cold-Start Penalty Burns the Function Budget

**What goes wrong:** The first invocation after a deploy or after idle period takes 5-10s longer than warm invocations because yfinance + pandas + numpy import cost is non-trivial (per `marcov/lambda-yfinance` benchmark: 8-12s on AWS Lambda for full execution; pandas alone is ~0.5-1.5s import).

**Why it happens:** Vercel Python serverless containers are cold by default; the Python interpreter has to import every transitive dep (`yfinance` → `pandas` → `numpy` → ...). Fluid Compute (enabled by default in 2026) reduces but does not eliminate cold starts.

**How to avoid:**
- Set `vercel.json.functions["api/refresh.py"].maxDuration = 30` (defensive — well under 300s but generous over typical 3-6s warm execution).
- DO NOT do exotic optimization (Lambda Layers, lazy imports, package compression) until measured cold-start exceeds 20s. **YAGNI.**
- Frontend-side mitigation: TanStack Query `retry: 1` with default `retryDelay` of ~1s, so a transient cold-start timeout isn't user-visible.

**Warning signs:**
- Vercel function logs show duration > 15s on first invocation.
- Frontend `<CurrentPriceDelta />` shows "refresh failed" badge immediately after every deploy.
- Vercel cold-start dashboard metric trending upward.

### Pitfall 2: Same-Origin CORS False Alarm (vercel.json rewrite swallowing /api/*)

**What goes wrong:** The current `frontend/vercel.json` rewrite `{"source": "/(.*)", "destination": "/index.html"}` is a SPA-fallback for client-side routing. If left unchanged when `api/refresh.py` is added, the wildcard *might* match `/api/refresh` BEFORE Vercel's auto-routing for the function. Frontend gets the SPA HTML instead of the JSON envelope.

**Why it happens:** Vercel's documented routing precedence: filesystem (static + functions) → rewrites → 404. Functions in `/api/*` are part of "filesystem" so they take precedence over the wildcard rewrite — but ONLY if the function file resolves correctly AND the function module imports succeed at build time. If the import path is wrong (e.g. `from ingestion.prices` fails because `pyproject.toml` is at root + `vercel.json` is in `frontend/`), the function never registers and the wildcard catches the URL, producing the silent SPA-HTML failure mode.

**How to avoid:**
- **Move `vercel.json` to repo root** (not `frontend/vercel.json`). Add the Vite `buildCommand` + `outputDirectory` settings explicitly so Vercel still treats `frontend/` as the static build source.
- Narrow the rewrite to NOT match `/api/*`:
  ```json
  {
    "rewrites": [
      { "source": "/((?!api/).*)", "destination": "/index.html" }
    ]
  }
  ```
- Verify with `vercel dev` (local Vercel emulator) before deploying — confirm `GET /api/refresh?ticker=AAPL` returns JSON, not HTML.

**Warning signs:**
- Frontend `useRefreshData` query throws `SchemaMismatchError` (because zod parses HTML as JSON).
- Browser network tab shows `Content-Type: text/html` for `/api/refresh?ticker=AAPL` requests.

### Pitfall 3: Memory Log Writes Not Atomic-Per-Run (corrupted line on routine crash)

**What goes wrong:** Routine fan-out writes per-ticker as each completes. If routine crashes after writing 15 of 30 tickers' persona signals, the next morning's run appends another 30 — now memory log has 45 records for that date. Trend view in v1.x shows duplicate signals.

**Why it happens:** Streaming append in a parallel-completion loop creates per-ticker partial state.

**How to avoid:**
- **Write memory log AFTER `_index.json` + `_status.json` are fully written** — Phase E in the storage.py write order. If routine crashes before Phase B (`_index.json`), no memory log entries written; if crash between B and E, status file IS written but memory log isn't — next run can detect "status exists for date but no memory log entries" and either (a) skip, (b) backfill from snapshot files. Recommend (a) — simpler.
- Alternative: write memory log entries to a SET (deduped by `(date, ticker, persona_id)`) before append. Slightly safer but requires reading the file first (slow if it grows large).

**Warning signs:**
- Trend query in v1.x shows N>6 personas for a single ticker on a single day.
- Memory log file size grows faster than expected (180 lines/day expected).

### Pitfall 4: Provenance Check False-Positive on Novel Code

**What goes wrong:** `scripts/check_provenance.py` flags `routine/run_for_watchlist.py` as missing provenance — but this file IS novel-to-this-project (per its docstring). The script doesn't know that.

**Why it happens:** The script is a pure regex match on "Adapted from" / "Pattern adapted from"; it doesn't know which files are novel.

**How to avoid:**
- Define the pattern to ALSO accept `novel-to-this-project` as a valid header marker. Files that are genuinely novel get a header like:
  ```python
  """routine/run_for_watchlist.py — novel-to-this-project orchestration glue.

  Provenance: novel-to-this-project. The per-ticker shape ... (rationale here).
  """
  ```
- Maintain an explicit `ALLOW_LIST` for files that genuinely should not have provenance (`__init__.py`, etc.).
- Run the script BEFORE adding the pre-commit hook to surface existing violators; fix headers OR add to allow-list; only THEN enable enforcement.

**Warning signs:**
- New developer commit blocked because of an `__init__.py` change.
- Hook fires on `tests/*.py` (which definitely don't need provenance — add `tests/` to the path filter or allow-list).

### Pitfall 5: Frontend Refresh Hook Fires on EVERY Render (not just symbol change)

**What goes wrong:** `useRefreshData` hook is mounted in TickerRoute; if the queryKey is computed in a way that changes on every render (e.g. includes a `Date.now()` timestamp), the query refetches constantly, hammering `/api/refresh` and the user's Vercel quota.

**Why it happens:** TanStack Query keys are equality-checked; an unstable key triggers refetch every render.

**How to avoid:**
- Keep `queryKey` minimal: `['refresh', symbol]` — symbol is the ONLY invalidator.
- DO NOT include the snapshot date in the refresh queryKey — refresh is "current price now," doesn't depend on which snapshot date the user is viewing.
- Set `staleTime: 60_000` so the query is "fresh" for 60s after each successful fetch — prevents refetch on remount within the same minute.

**Warning signs:**
- Vercel function invocation count for `api/refresh.py` >> 1 per page navigation.
- React DevTools "Profiler" shows TickerRoute re-rendering every few hundred ms.

### Pitfall 6: Resilience Test Suite Hits Real yfinance / Yahoo Servers

**What goes wrong:** Test that "verifies yfinance fallback works" actually calls yfinance — flaky, slow, can rate-limit the user's IP, and breaks reproducibility (Yahoo returning different prices in CI than local).

**Why it happens:** Easy to forget to mock at the resilience layer because the existing Phase 2 tests already mock yfinance per-source.

**How to avoid:**
- Reuse the existing `responses` (Python) library setup from `tests/ingestion/conftest.py` — mock `yfinance.Ticker` and `yahooquery.Ticker` at the boundary. Resilience tests inject specific failure modes (raise exception, return empty DataFrame, return partial data).
- For the Vercel function tests: mock at the `ingestion.prices.fetch_prices` level; treat `fetch_prices` as the boundary.
- For frontend tests: MSW (Mock Service Worker) intercepting `/api/refresh?ticker=*`; test the (200 ok / 200 partial / network error) matrix of frontend behavior.

**Warning signs:**
- CI flakes on weekend / market-closed days.
- Tests pass locally, fail in GitHub Actions (Yahoo rate-limited GH IP range).

## Code Examples

### Example 1: vercel.json at repo root (combined Vite static + Python serverless)

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "framework": "vite",
  "installCommand": "pnpm --dir frontend install",
  "buildCommand": "pnpm --dir frontend build",
  "outputDirectory": "frontend/dist",
  "functions": {
    "api/refresh.py": {
      "maxDuration": 30
    }
  },
  "rewrites": [
    { "source": "/((?!api/).*)", "destination": "/index.html" }
  ]
}
```

**Notes:**
- `maxDuration: 30` is defensive — well under 300s ceiling. Caps billable duration in case of a stuck function.
- `(?!api/)` negative lookahead in rewrite source ensures `/api/*` is NOT swallowed by the SPA fallback.
- `installCommand` / `buildCommand` use `--dir frontend` so the same `vercel.json` deploys frontend + function from one config.

### Example 2: Frontend integration in DecisionRoute.tsx (replaces Phase 7 placeholder)

```typescript
// Source: novel-to-this-project — implements REFRESH-03 frontend hookpoint.
// Replaces the Phase 7 PHASE-8-HOOK: current-price-delta placeholder block.
import { Link, useParams } from 'react-router'
import { useTickerData } from '@/lib/loadTickerData'
import { useRefreshData } from '@/lib/useRefreshData'
import { CurrentPriceDelta } from '@/components/CurrentPriceDelta'
// ... other imports

export default function DecisionRoute() {
  const { symbol = '', date = 'today' } = useParams<{ symbol: string; date?: string }>()
  const { data: snap, isLoading, error } = useTickerData(date, symbol)
  // ... existing loading + error branches preserved

  // ... existing happy-path rendering up to the placeholder block
  return (
    <section /* ... */>
      {/* ... existing heading + RecommendationBanner ... */}

      {/* PHASE-8-WIRE: replaces the Phase 7 placeholder.
          The data-testid="current-price-placeholder" lock-in DOM target is
          PRESERVED inside <CurrentPriceDelta /> so existing E2E specs
          continue to pass. */}
      <CurrentPriceDelta
        symbol={symbol}
        snapshotPrice={snap.price}  // or wherever the snapshot price lives
        snapshotComputedAt={dec.computed_at}
      />

      {/* ... rest of route preserved ... */}
    </section>
  )
}
```

### Example 3: CurrentPriceDelta component

```typescript
// Source: novel-to-this-project — REFRESH-03 + Pitfall #2 always-render lock.
import { useRefreshData } from '@/lib/useRefreshData'
import { cn } from '@/lib/utils'

interface Props {
  symbol: string
  snapshotPrice: number
  snapshotComputedAt: string  // ISO 8601
}

export function CurrentPriceDelta({ symbol, snapshotPrice, snapshotComputedAt }: Props) {
  const { data: refresh, isLoading, isError } = useRefreshData(symbol)

  // Always-render shell — Pitfall #2 + #12 lock from Phases 6-7.
  // The data-testid="current-price-placeholder" is preserved here so the
  // Phase 7 lock-in target survives the Phase 8 swap.
  return (
    <div
      data-testid="current-price-placeholder"
      className="rounded-md border border-border bg-surface px-4 py-3 text-sm"
    >
      <div className="font-mono text-fg">${snapshotPrice.toFixed(2)}</div>
      <div className="mt-1 text-xs text-fg-muted">
        Snapshot price as of {new Date(snapshotComputedAt).toLocaleString()} ET
      </div>
      {/* Refresh state: loading → muted "refreshing"; error → muted "refresh unavailable";
          partial → muted "partial refresh"; ok → green/red delta arrow */}
      {isLoading && (
        <div className="mt-2 text-xs text-fg-muted italic" data-testid="refresh-loading">
          Refreshing current price…
        </div>
      )}
      {isError && (
        <div className="mt-2 text-xs text-fg-muted italic" data-testid="refresh-error">
          Refresh unavailable — showing snapshot price.
        </div>
      )}
      {refresh?.current_price != null && (
        <CurrentPriceDeltaInner
          snapshotPrice={snapshotPrice}
          currentPrice={refresh.current_price}
          partial={refresh.partial}
        />
      )}
    </div>
  )
}

function CurrentPriceDeltaInner({
  snapshotPrice, currentPrice, partial,
}: { snapshotPrice: number; currentPrice: number; partial: boolean }) {
  const delta = currentPrice - snapshotPrice
  const deltaPct = (delta / snapshotPrice) * 100
  const sign = delta > 0 ? '+' : delta < 0 ? '' : '±'
  return (
    <div
      className={cn(
        'mt-2 flex items-baseline gap-2 font-mono text-sm',
        delta > 0 && 'text-bullish',
        delta < 0 && 'text-bearish',
        delta === 0 && 'text-fg-muted',
      )}
      data-testid="refresh-delta"
    >
      <span>${currentPrice.toFixed(2)}</span>
      <span className="text-xs">
        ({sign}${Math.abs(delta).toFixed(2)} / {sign}{deltaPct.toFixed(2)}%)
      </span>
      {partial && <span className="text-xs italic text-fg-muted">partial data</span>}
    </div>
  )
}
```

## State of the Art

| Old Approach | Current Approach (2026) | When Changed | Impact |
|--------------|--------------------------|--------------|--------|
| Vercel Hobby plan: 10s default, 60s max function duration | Vercel Hobby plan: 300s default, 300s max (Fluid Compute enabled by default) | 2025-04-23 (Fluid Compute default-on) | Phase 8 has 30× more budget than the orchestrator brief assumed; eliminates "shave milliseconds off cold start" pressure |
| Vercel Python: pre-3.10 only | Vercel Python: 3.12 default, 3.13 + 3.14 available | 2025+ | Project's `requires-python = ">=3.12"` works directly |
| TanStack Query v4: `keepPreviousData: true` boolean prop | TanStack Query v5: `placeholderData: keepPreviousData` (function import) | late 2024 | One-line idiom change; same behavior; non-breaking with our v5 pin |
| TanStack v3/v4: composite query for merged shapes | TanStack v5: two parallel queries with `placeholderData` for stale-while-revalidate | 2024-2025 | Cleaner separation of concerns; better matches the "snapshot is canon, refresh is decoration" semantics |

**Deprecated/avoid:**
- Heavy Python frameworks (FastAPI, Flask) for single-endpoint Vercel functions — `BaseHTTPRequestHandler` is enough.
- `keepPreviousData: true` — replaced by the function import in v5.
- Composite "fetch both at once" queries — split into two queries, use `placeholderData` for the volatile one.
- Lambda Layers / package compression / lazy imports — premature optimization at 30s budget for 3-12s typical execution.

## Open Questions

### Open Question #1 — Should `useRefreshData` mount on TickerRoute (deep-dive) too, or only DecisionRoute?

**The choice:** The Phase 7 hookpoint marker (`PHASE-8-HOOK: current-price-delta` + `data-testid="current-price-placeholder"`) lives ONLY in `DecisionRoute.tsx`. But TickerRoute (the deep-dive view) also surfaces price-sensitive data and would benefit from a current-price overlay.

**Recommendation:** **Mount on BOTH.** Justification:
- TickerRoute is "what's the data" — current-price freshness directly improves the data view's actionability.
- DecisionRoute is "what should I do" — current-price freshness directly affects the recommendation's relevance (per Phase 7's deferred-to-Phase-8 logic).
- Two parallel routes calling the same `/api/refresh?ticker=AAPL` is fine — TanStack Query dedupes the request via the same `queryKey: ['refresh', symbol]` cache key.
- User memory.md ("active investor, ~30-50 tickers, dual-timeframe") explicitly values both views as primary surfaces.

**If user disagrees during discuss-phase**, the fallback is "DecisionRoute only" — Phase 7's hookpoint is the locked target; mounting in TickerRoute can be a v1.x addition.

### Open Question #2 — Should memory log write every routine run, or only when persona signals CHANGE vs prior day?

**The choice:** `historical_signals.jsonl` could be append-everything (180 records/day, 65K/year) OR delta-only (write only when a persona's signal/confidence changes from yesterday — far smaller log).

**Recommendation:** **Append every run.** Justification:
- Simpler — no "look up yesterday's record" step before append.
- v1.x reads (TREND-01, TREND-02 — "Buffett went bearish 2 weeks ago") want the full timeline; gaps in the log force the reader to interpolate.
- 65K records/year is trivially small (raw JSONL ~6MB; gzipped ~1.5MB) — well under any practical limit.
- Pitfall #11 (GitHub-as-DB scaling) trigger is at >5K files OR >100K records; well above v1 scale.

### Open Question #3 — Should the refresh function accept a `?since=ISO-8601` parameter for headline filtering, or filter client-side?

**The choice:** Frontend wants only headlines published since the snapshot was generated. Two implementations:
- (A) Pass `?since={snapshot.computed_at}` to refresh; function filters server-side; response is small.
- (B) Refresh always returns last-N headlines (e.g. 20); frontend filters client-side using snapshot.computed_at.

**Recommendation:** **Option B (client-side filter).** Justification:
- Function stays stateless — no `since` interpretation, no edge cases for clock skew between routine and serverless function.
- Response is at most 20 headlines × ~150 bytes = 3KB; well under 4.5MB Vercel response limit.
- Frontend already has the snapshot's `computed_at`; trivial to filter (`headlines.filter(h => h.published_at > snapshotComputedAt)`).
- v1.x can layer caching + smarter filtering on top without breaking the v1 contract.

### Open Question #4 — Refresh response schema: snake_case (Python convention) or camelCase (TS convention)?

**The choice:** The function emits JSON; frontend parses via zod. We can adopt either convention OR mirror the existing per-ticker JSON convention (which uses snake_case throughout — `current_price`, `recent_headlines`).

**Recommendation:** **snake_case.** Justification:
- Mirrors `data/YYYY-MM-DD/{TICKER}.json` (Phase 5+6 output) — consistency.
- zod schemas in `frontend/src/schemas/` already accept snake_case keys (TS happily handles either).
- No conversion layer needed.

### Open Question #5 — Provenance allow-list discipline: explicit file list vs path-pattern globs?

**The choice:** Files like `routine/run_for_watchlist.py` are novel-to-this-project; need to be either listed in ALLOW_LIST or carry a `novel-to-this-project` header.

**Recommendation:** **Header marker over allow-list.** Justification:
- Self-documenting — the file declares its own provenance status; no hidden allow-list to maintain.
- Failure mode (missing header) is the SAME for both novel and adapted files — easier to fix consistently.
- Allow-list reserved for genuine package boilerplate (`__init__.py`).

### Open Question #6 — `vercel.json` location: repo root vs `frontend/`?

**The choice:** Currently `frontend/vercel.json` exists for the static deploy. With Phase 8 adding `api/refresh.py` at repo root, we need ONE config that covers both.

**Recommendation:** **Move to repo root.** Justification:
- `api/` lives at repo root (Vercel autodetect convention) — config near it is intuitive.
- One source of truth for build + functions + rewrites.
- Vite static build still works via `outputDirectory: "frontend/dist"` + `installCommand`/`buildCommand` pointing at `frontend/`.

**If user disagrees:** can keep `frontend/vercel.json` for static settings + add `vercel.json` at root for `api/*` settings; Vercel merges them. Slightly less clean but works.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (Python) | pytest 8.x + pytest-asyncio + responses (already in `[dependency-groups].dev`) |
| Framework (Frontend) | vitest 2.x + @testing-library/react + Playwright 1.x (already pinned) |
| Config files | `pyproject.toml` `[tool.pytest.ini_options]` + `frontend/vitest.config.ts` + `frontend/playwright.config.ts` |
| Quick run command (Python) | `uv run pytest tests/api/ tests/routine/test_memory_log.py tests/scripts/ -x` |
| Quick run command (Frontend) | `pnpm --dir frontend test:unit -- src/lib/__tests__/useRefreshData.test.ts src/components/__tests__/CurrentPriceDelta.test.tsx` |
| Full suite command | `uv run pytest && pnpm --dir frontend test:unit && pnpm --dir frontend test:e2e` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REFRESH-01 | `api/refresh.py` is a valid Vercel Python serverless function with `handler` class subclassing `BaseHTTPRequestHandler`; Python module imports cleanly | unit | `uv run pytest tests/api/test_refresh.py::test_handler_class_exists -x` | ❌ Wave 0 |
| REFRESH-02 | Refresh accepts `?ticker=AAPL`, returns JSON envelope with `current_price` from `fetch_prices` + `recent_headlines` from `fetch_news`; NO LLM module imported | unit | `uv run pytest tests/api/test_refresh.py::test_happy_path -x` AND `uv run pytest tests/api/test_refresh.py::test_no_llm_imports -x` | ❌ Wave 0 |
| REFRESH-03 | `useRefreshData` hook fires on TickerRoute + DecisionRoute mount; renders snapshot price + delta when refresh succeeds; renders snapshot price + "refresh unavailable" when refresh fails | component | `pnpm --dir frontend test:unit -- src/components/__tests__/CurrentPriceDelta.test.tsx` | ❌ Wave 0 |
| REFRESH-04 | Failure-mode matrix: yfinance down (yahooquery fallback works); both down (`partial: true`); RSS empty (`partial: true`); function timeout (frontend continues with snapshot) | unit + e2e | `uv run pytest tests/api/test_refresh.py -k "failure" -x` AND `pnpm --dir frontend test:e2e -- refresh.spec.ts` | ❌ Wave 0 |
| INFRA-06 | `routine.memory_log.append_persona_signals` writes one line per (ticker × persona) to `memory/historical_signals.jsonl`; line is sort_keys-stable JSON; appends are atomic | unit | `uv run pytest tests/routine/test_memory_log.py -x` | ❌ Wave 0 |
| INFRA-07 | `scripts/check_provenance.py` exits 0 when all files have headers; exits 1 when a violator exists; exits 0 for explicit ALLOW_LIST entries | unit | `uv run pytest tests/scripts/test_check_provenance.py -x` | ❌ Wave 0 |

**Manual-only verifications** (not blocking gate; deferred to user):
- Real Vercel preview deploy: `vercel deploy --preview` + manual `curl /api/refresh?ticker=AAPL` against the preview URL — confirms the actual Vercel Python runtime works, not just the local mock.
- Real-data resilience drill: temporarily unplug network during `useRefreshData`; confirm `<CurrentPriceDelta />` shows snapshot price + "refresh unavailable" badge; reconnect; confirm refresh succeeds on next mount.

### Sampling Rate

- **Per task commit:** `uv run pytest tests/api/ tests/routine/test_memory_log.py tests/scripts/ -x` (~2-5s); + `pnpm --dir frontend test:unit src/lib/__tests__/useRefreshData.test.ts src/components/__tests__/CurrentPriceDelta.test.tsx` (~3-10s).
- **Per wave merge:** Full Python suite (`uv run pytest`) + full frontend unit suite + relevant Playwright spec (~1-3 min).
- **Phase gate:** Full Python + frontend unit + Playwright (all projects: chromium-desktop + mobile-safari + mobile-chrome) green; provenance script exits 0; manual Vercel preview deploy + `curl` smoke test before `/gmd:verify-work`.

### Wave 0 Gaps

- [ ] `tests/api/` directory + `tests/api/__init__.py` + `tests/api/test_refresh.py`
- [ ] `tests/api/conftest.py` shared fixtures (mock yfinance.Ticker / yahooquery.Ticker / feedparser.parse via `responses` lib)
- [ ] `tests/routine/test_memory_log.py`
- [ ] `tests/scripts/__init__.py` + `tests/scripts/test_check_provenance.py`
- [ ] `frontend/src/lib/__tests__/useRefreshData.test.ts` — TanStack Query hook test (vi.mock `fetchAndParse`)
- [ ] `frontend/src/components/__tests__/CurrentPriceDelta.test.tsx` — RTL test matrix
- [ ] `frontend/tests/e2e/refresh.spec.ts` — Playwright happy path + RSS-down failure + function-timeout (mocked) failure
- [ ] `frontend/tests/e2e/fixtures-server.ts` — extend with `mountRefreshFixture` option (mock `/api/refresh` responses for E2E)
- [ ] MSW (Mock Service Worker) setup OR Playwright route interceptors for `/api/refresh` mocking
- [ ] `pyproject.toml` — extend `[tool.hatch.build.targets.wheel].packages` to include `api` if treating as a package (or rely on Vercel auto-include — confirm during scaffold)
- [ ] `pyproject.toml` — `[tool.coverage.run].source` extends to include `api` and `routine` and `scripts`
- [ ] Initial run of `scripts/check_provenance.py` against the existing repo to surface ALL existing violators BEFORE enforcement; fix or allow-list before enabling pre-commit hook

## Sources

### Primary (HIGH confidence)

- [Vercel Functions: Python Runtime](https://vercel.com/docs/functions/runtimes/python) — handler class pattern (BaseHTTPRequestHandler), Python 3.12 default + 3.13 + 3.14 available, 500MB Python bundle limit, `pyproject.toml` / `requirements.txt` / `Pipfile` dependency declaration. Last updated 2026-03-17.
- [Vercel Functions Limits](https://vercel.com/docs/functions/limitations) — Hobby plan max duration 300s; Pro 800s; 4.5MB request/response payload; 250MB Node.js bundle / 500MB Python bundle. Last updated 2026-02-24.
- [Vercel Configuring Maximum Duration](https://vercel.com/docs/functions/configuring-functions/duration) — `vercel.json.functions["api/*.py"].maxDuration` syntax + Hobby/Pro/Enterprise limits with Fluid Compute. Last updated 2026-02-27.
- [Vercel Fluid Compute](https://vercel.com/docs/fluid-compute) — Fluid Compute enabled by default for new projects since 2025-04-23; supports Python runtime; 300s/300s default/max for Hobby. Last updated 2026-01-29.
- [TanStack Query v5: keepPreviousData](https://github.com/TanStack/query/discussions/6460) — official `placeholderData: keepPreviousData` migration pattern in v5.
- [TanStack Query v5: Migration Guide](https://tanstack.com/query/v5/docs/framework/react/guides/migrating-to-v5) — confirmed `keepPreviousData` deprecated in favor of function import from `@tanstack/react-query`.
- Existing project files (HIGH confidence — verified by direct read):
  - `routine/llm_client.py:_log_failure` (line 167) — append-only JSONL pattern for memory log reuse.
  - `ingestion/prices.py:fetch_prices` — keyless yfinance + yahooquery fallback.
  - `ingestion/news.py:fetch_news` — RSS aggregation with `return_raw=True` form for headline persistence.
  - `frontend/src/routes/DecisionRoute.tsx:177-189` — Phase 7 hookpoint (PHASE-8-HOOK + current-price-placeholder).
  - `frontend/src/lib/fetchSnapshot.ts` — fetchAndParse + zod-typed-error pattern reusable for refresh fetch.
  - 9 files carry "Adapted from"/"Pattern adapted from" provenance headers (verified).

### Secondary (MEDIUM confidence)

- [marcov/lambda-yfinance](https://github.com/marcov/lambda-yfinance) — yfinance on AWS Lambda benchmark: ~8-12s for full multi-ticker history download; useful upper-bound for cold-start budgeting.
- [Vercel CORS Knowledge Base](https://vercel.com/kb/guide/how-to-enable-cors) — same-origin scenarios; states CORS headers not auto-added but does not contradict the same-origin "no preflight" browser behavior.

### Tertiary (LOW confidence — flagged for measurement)

- yfinance import time exact value — public benchmarks scarce; estimated 1-2s based on pandas + numpy import overhead. **VALIDATE BY MEASUREMENT** during Phase 8 implementation: deploy to Vercel preview + capture cold-start `Date.now()` deltas in function logs.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — Vercel Python + TanStack v5 + existing project pinned deps all verified at official 2026 docs.
- Architecture (function pattern + frontend hook + memory log + provenance script): HIGH — patterns mirror existing internal precedent (`_log_failure`, `useTickerData`, `fetchAndParse`) verified by direct code read.
- Vercel timeout / Fluid Compute defaults: HIGH — fetched directly from Vercel's `/docs/fluid-compute` page (last updated 2026-01-29) which explicitly states 300s default for Hobby; corrects the orchestrator brief's "10s Vercel Hobby plan default" assumption.
- Cold-start timing for yfinance + feedparser combo: MEDIUM — extrapolated from Lambda benchmark (8-12s typical full execution); should be measured in preview deploy before declaring Phase 8 done (per ROADMAP success criterion #1).
- CORS same-origin: MEDIUM — Vercel docs are silent on the exact same-origin flow but browser semantics + Phase 6 same-origin static + raw GitHub fetches working confirm same-origin GETs don't preflight.
- Pitfalls + open questions: HIGH — derived from PITFALLS.md + Phase 6/7 patterns + project's locked discipline.

**Research date:** 2026-05-04

**Valid until:** 2026-06-04 (30 days — Vercel platform docs change occasionally; TanStack Query v5 is stable; project codebase is the dominant source of truth and is current).
