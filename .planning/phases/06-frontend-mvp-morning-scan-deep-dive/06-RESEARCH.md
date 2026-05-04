---
phase: 6
title: Frontend MVP — Morning Scan + Deep-Dive
researched: 2026-05-03
domain: Static React SPA (Vite + TypeScript + zod) consuming GitHub-raw daily JSON snapshots
confidence: HIGH (frontend stack is mature; one HIGH-IMPACT open question on OHLC data source)
research_tier: normal
vault_reads: []
vault_status: not_configured
---

# Phase 6: Frontend MVP — Morning Scan + Deep-Dive — Research

## Summary

Phase 6 ships a static Vite + React + TypeScript SPA on Vercel that reads `data/YYYY-MM-DD/*.json` from `raw.githubusercontent.com`, validates each payload through zod, and renders the morning-scan three-lens view + per-ticker deep-dive. The stack is locked by PROJECT.md (React, dark theme, mobile-responsive, Vercel, lightweight-charts, zod) — research confirms 2026-current versions and surfaces which gaps in the locked spec still need decision.

The single highest-leverage finding: **`data/YYYY-MM-DD/{TICKER}.json` does NOT contain historical OHLC bars today** — Phase 5 persists the four `analytical_signals`, `position_signal`, six `persona_signals`, and `ticker_decision` only. The Snapshot object (which holds `prices.ohlc` history) is consumed by analysts and discarded. This makes ROADMAP success criterion #4 ("OHLC chart with MA/BB/RSI overlays") un-shippable in Phase 6 without one of three remediations (see Open Question #1). The two viable paths: (a) extend the Phase 5 storage shape to embed last-N-days OHLC bars in the per-ticker JSON, or (b) defer the OHLC chart to Phase 8 when the mid-day refresh function exists and can serve OHLC server-side.

The second-highest-leverage finding: **yfinance/Yahoo Finance is not callable from the browser** (CORS-blocked + IP-banned). Confirmed across 2024-2026 reports. So "frontend fetches OHLC directly from Yahoo" is not an option — OHLC data must come from a server-side source (the GitHub-raw JSON, OR Phase 8's serverless function). This forecloses one tempting workaround.

The third-highest-leverage finding: **`raw.githubusercontent.com` works for simple GET requests of public JSON files in modern browsers** (sets `access-control-allow-origin: *` for simple requests), but is fragile for credentialed/preflight requests. The Phase 6 fetch path is exactly the supported case (cross-origin GET, no credentials, no custom headers). CDN cache is ~30s after commit per Phase 5's existing assumption — the frontend must tolerate occasional 404s for "today's snapshot not pushed yet" and degrade gracefully.

**Primary recommendation:** Lock the v1 stack to Vite 6 + React 19 + TS 5.6 + Tailwind v4 + shadcn/ui + zod 4 + lightweight-charts 5.2 + react-router 7 (declarative SPA mode) + react-query (TanStack Query v5) + vitest + Playwright (smoke only). Resolve Open Question #1 (OHLC data source) before plan-check by extending Phase 5 storage to embed last-180-days OHLC OR defer the chart to Phase 8 — DO NOT plan around fetching OHLC from the browser.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VIEW-01 | Morning-Scan view shows three lens tabs (Position Adjustment, Short-Term Opportunities, Long-Term Thesis Status); one lens visible at a time | Tab discipline section + Pitfall #8 prevention; URL-state pattern (`?lens=position`); aria-tablist + radio-group semantics |
| VIEW-02 | Position Adjustment lens lists tickers sorted by `\|consensus_score\|` desc; shows state, evidence, action_hint | Sort key sourced from `position_signal.consensus_score` (already in JSON); state/evidence/action_hint fields are top-level on PositionSignal |
| VIEW-03 | Short-Term Opportunities lens lists tickers with bullish short_term sorted by confidence | Source: `ticker_decision.short_term.confidence` + `ticker_decision.short_term.summary` (TimeframeBand schema confirmed) |
| VIEW-04 | Long-Term Thesis Status lens lists tickers with thesis_status ∈ {weakening, broken} sorted by severity | **GAP:** TickerDecision schema has no `thesis_status` field today (synthesis/decision.py confirmed) — see Open Question #5 |
| VIEW-05 | Per-Ticker Deep-Dive shows dual-timeframe cards (short_term + long_term) side-by-side at top | TimeframeBand × 2 lives on TickerDecision; layout pattern documented |
| VIEW-06 | Deep-dive shows OHLC chart (lightweight-charts) with MA20/MA50, Bollinger Bands, RSI overlay | **HIGH-IMPACT GAP:** OHLC bars not in JSON today — Open Question #1; lightweight-charts 5.2 multi-pane API documented |
| VIEW-07 | Deep-dive shows persona signals as individual cards (verdict, confidence, reasoning, evidence) | `persona_signals: [AgentSignal × 6]` in JSON; AgentSignal has all rendered fields |
| VIEW-08 | Deep-dive shows news feed grouped by source with timestamps; "since snapshot" delta surfaced | **GAP:** Headlines not persisted to per-ticker JSON today (Snapshot is discarded) — Open Question #2 |
| VIEW-09 | Deep-dive shows Open Claude Analyst observation pinned at top | `claude_analyst` is one of 6 entries in `persona_signals[]`; pin-at-top is rendering policy |
| VIEW-11 | Header shows snapshot date + staleness badge GREEN/AMBER/RED (success criterion thresholds: <2h/2-12h/>12h or partial) | Source: `_status.json.partial` + `_index.json.run_completed_at`; thresholds documented (note REQUIREMENTS.md says 6h/24h — see Open Question #6) |
| VIEW-12 | All views are mobile-responsive; phone-optimized layouts | Tailwind responsive utilities + shadcn/ui mobile patterns; manual phone test gate |
| VIEW-13 | Search/add ticker via typeahead with company-name fuzzy match | **GAP:** No ticker→name mapping ships today; bundle a static `tickers.json` (e.g., from SEC company tickers list) at build time |
| VIEW-14 | Snapshot date selector lets user load historical snapshots | List dates from `_index.json` lookup pattern (multiple `_index.json` per day); needs date enumeration approach (Open Question #7) |
| VIEW-15 | All JSON reads from `raw.githubusercontent.com` are zod-validated; mismatches render error state | zod 4 schema discriminated unions; per-fetch error boundary pattern |
| INFRA-05 | Frontend deployed to Vercel; builds on `main` push; reads from `raw.githubusercontent.com` | Vite-on-Vercel autodetect; `VITE_GITHUB_USER` + `VITE_GITHUB_REPO` env vars at build time |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **Vite** | 6.x (current) | Build + dev server | Fastest cold start; first-class TS; static `dist/` deploys trivially; PROJECT.md lock |
| **React** | 19.x | UI runtime | PROJECT.md lock; concurrent rendering helps chart-heavy pages |
| **TypeScript** | 5.6+ | Static types | Catches Python↔TS schema drift at compile time |
| **Tailwind CSS** | 4.x | Styling system | Dark-theme trivial via OKLCH tokens; mobile-responsive utilities; STACK.md lock |
| **shadcn/ui** | (vendored, latest) | Component primitives on Radix UI | Vendored not installed (you own the source); composes with Tailwind v4; dark-mode-first; finance-dashboard fit |
| **Radix UI primitives** | (transitively via shadcn) | Accessible headless components | Tabs, Dialog, Select, Toast — accessibility free; covers VIEW-01 tab discipline cleanly |
| **lightweight-charts** | 5.2.0 (current) | OHLC + indicator overlays | Best-in-class for finance candlesticks; ~35KB; multi-pane support added in v5 (RSI sub-pane); STACK.md lock |
| **zod** | 4.x | Runtime schema validation | Required by VIEW-15; 14× faster string parsing + 7× faster array parsing vs v3; 2.3× smaller bundle; **discriminated unions** are first-class for `analyst_id`-tagged signals |
| **react-router** | 7.x (declarative SPA mode) | Client-side routing | v7 is non-breaking upgrade from v6; declarative mode is the small-SPA default; tree-shakes well |
| **TanStack Query (react-query)** | v5 | Async data fetching + cache | Stale-while-revalidate; 5min cache aligns with snapshot freshness; per-route prefetch; 12M weekly downloads (the de-facto standard); fine-grained re-render via field tracking |
| **date-fns** | 3.x | Date math | Tree-shakeable; staleness threshold computation; market-day formatting |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **clsx** + **tailwind-merge** | latest | Class composition | shadcn/ui `cn()` helper standard pattern |
| **lucide-react** | latest | Icon set | shadcn/ui default; tree-shakeable; ~3KB per icon |
| **fuse.js** | 7.x | Fuzzy search for ticker typeahead | VIEW-13; ~12KB; well-suited for company-name search |
| **vitest** | latest | Unit + component testing | Native Vite integration; 5-10× faster than Jest cold start |
| **@testing-library/react** | latest | Component test queries | Standard pairing with vitest |
| **@testing-library/jest-dom** | latest | DOM matchers | Standard |
| **@playwright/test** | latest | Smoke E2E (mobile-viewport iOS Safari + Android Chrome emulation) | Success criterion #6 mandate; emulation only for v1 — manual phone test still required |
| **biome** | latest | Lint + format | STACK.md lock; replaces ESLint + Prettier; single binary |

### Alternatives Considered

| Instead of | Could Use | Tradeoff | Recommendation |
|------------|-----------|----------|----------------|
| react-router v7 | wouter (1.5KB) | Wouter wins on bundle (~15KB savings); v7 wins on ecosystem familiarity, future Remix-loader path | **react-router** — bundle size is moot for a personal-tool dashboard; ecosystem familiarity is the win |
| react-router v7 | TanStack Router | Type-safe routes; but heavier mind-share cost for two routes | **react-router** — 2 routes don't justify the type-safety machinery |
| TanStack Query v5 | SWR (5.3KB) | SWR is 3× smaller and simpler; TQ v5 has fine-grained re-render + better devtools | **TanStack Query** — devtools value > 11KB bundle delta; we'll use the cache invalidation features for staleness tracking |
| TanStack Query v5 | plain fetch + useState | Lighter, no dep | **TanStack Query** — staleness detection + retry + cache TTL match `_status.json` polling pattern; rolling our own is Pitfall #10 |
| shadcn/ui (vendored) | radix-ui directly | Less code, more control | **shadcn/ui** — radix-ui is the right primitive layer; shadcn just gives you opinionated styling on top, fully editable. Skipping it = rolling-your-own. |
| shadcn/ui | headlessui or react-aria | Both are good; shadcn ecosystem is bigger in 2026 | **shadcn/ui** — wider component library (Tabs, Dialog, Toast, DatePicker), less work for v1 |
| Tailwind v4 | CSS Modules + plain CSS | More explicit; no utility-class soup | **Tailwind v4** — PROJECT.md lock; iteration speed in v1 dominates |
| zod 4 | valibot, arktype | Smaller, sometimes faster; zod has the largest ecosystem and Pydantic-codegen story | **zod 4** — ecosystem + pydantic2zod tooling matter |
| pnpm | npm or bun | pnpm is content-addressable + fast; bun is fastest but less mature on Windows | **pnpm** — STACK.md lock; works clean on Windows |
| Vercel | Cloudflare Pages, Netlify | All comparable for static + serverless | **Vercel** — PROJECT.md lock; existing Phase 8 plan assumes Vercel Python runtime |

**Installation (planner reference):**

```bash
pnpm create vite frontend --template react-ts
cd frontend
pnpm add react-router@^7 @tanstack/react-query@^5 zod@^4 \
        lightweight-charts@^5 date-fns@^3 fuse.js@^7 \
        clsx tailwind-merge lucide-react
pnpm add -D tailwindcss@next @tailwindcss/vite \
            vitest @testing-library/react @testing-library/jest-dom \
            @testing-library/user-event jsdom \
            @playwright/test \
            @biomejs/biome \
            @types/react @types/react-dom

# shadcn/ui (vendor — does not install, copies code into src/components/ui)
pnpm dlx shadcn@latest init
pnpm dlx shadcn@latest add tabs card badge button input dialog select toast
```

## Architecture Patterns

### Recommended Project Structure

```
frontend/
├── src/
│   ├── main.tsx                # React entry; sets up QueryClient, BrowserRouter
│   ├── App.tsx                 # Route table (2 routes for v1)
│   ├── routes/
│   │   ├── MorningScan.tsx     # /scan — three-lens view (default route)
│   │   └── TickerDeepDive.tsx  # /ticker/:symbol — deep-dive
│   ├── components/
│   │   ├── ui/                 # shadcn vendored primitives (tabs, card, etc.)
│   │   ├── lenses/
│   │   │   ├── PositionLens.tsx
│   │   │   ├── ShortTermLens.tsx
│   │   │   └── LongTermLens.tsx
│   │   ├── deep-dive/
│   │   │   ├── DualTimeframeCards.tsx
│   │   │   ├── OhlcChart.tsx              # lightweight-charts wrapper
│   │   │   ├── PersonaSignalCard.tsx
│   │   │   ├── ClaudeAnalystPin.tsx       # pinned-at-top per VIEW-09
│   │   │   └── NewsFeed.tsx               # blocked by Open Q #2
│   │   ├── header/
│   │   │   ├── StalenessBadge.tsx         # GREEN/AMBER/RED logic
│   │   │   └── SnapshotDatePicker.tsx     # VIEW-14
│   │   └── shared/
│   │       ├── ErrorState.tsx             # VIEW-15 zod-mismatch surface
│   │       ├── LoadingSkeleton.tsx
│   │       └── TickerSearch.tsx           # VIEW-13 typeahead
│   ├── lib/
│   │   ├── github-fetch.ts     # raw.githubusercontent.com client + retry
│   │   ├── schemas.ts          # zod schemas (mirror Pydantic)
│   │   ├── staleness.ts        # GREEN/AMBER/RED computation from _status.json
│   │   ├── ticker-data.ts      # bundled SEC tickers JSON (VIEW-13)
│   │   └── format.ts           # number/date/percentage formatters
│   ├── hooks/
│   │   ├── useSnapshot.ts      # useQuery wrapper for per-ticker JSON
│   │   ├── useDayIndex.ts      # useQuery wrapper for _index.json
│   │   └── useStatus.ts        # useQuery wrapper for _status.json
│   ├── styles/
│   │   └── globals.css         # Tailwind v4 entry + OKLCH theme tokens
│   └── config.ts               # GITHUB_USER, GITHUB_REPO from VITE_* env
├── public/
│   ├── favicon.svg
│   └── tickers.json            # bundled SEC company-tickers map (VIEW-13)
├── tests/
│   ├── unit/                   # vitest + RTL component tests
│   └── e2e/                    # playwright smoke (1 test/route × mobile emulation)
├── index.html
├── vite.config.ts              # tailwind plugin + path aliases
├── tailwind.config.ts          # OR @import "tailwindcss"; in v4 (config-less)
├── tsconfig.json
├── biome.json
├── package.json
└── README.md
```

### Pattern 1: Locked-Then-Generated zod Schemas

**What:** Mirror every Pydantic model in `synthesis/decision.py`, `analysts/signals.py`, `analysts/position_signal.py`, and `routine/storage.py` payloads as zod schemas. Generate via `pydantic2zod` OR hand-author with the Pydantic file as the source of truth.

**When to use:** All cross-network reads from raw.githubusercontent.com.

**Tradeoff:** Hand-authoring is 1 hour of typing + ~150 LOC; risks drift on schema changes. Codegen is one-time setup + a CI check; risks tool bugs but eliminates drift. **Recommendation: hand-author for v1, add codegen check in Phase 8.** Rationale: schema is locked (`schema_version: 1` in TickerDecision, AgentSignal, PositionSignal); only ~5 models matter; Pydantic v2 → zod 4 mappings are direct.

**Schema co-location:** Put all zod schemas in ONE file (`src/lib/schemas.ts`) with each schema sized 5-30 lines. Export both the schema and the inferred TS type:

```typescript
// src/lib/schemas.ts
import { z } from "zod";

// Mirror analysts/signals.py: AnalystId Literal[10]
export const AnalystIdSchema = z.enum([
  "fundamentals", "technicals", "news_sentiment", "valuation",
  "buffett", "munger", "wood", "burry", "lynch", "claude_analyst",
]);
export type AnalystId = z.infer<typeof AnalystIdSchema>;

// Mirror analysts/signals.py: Verdict Literal[5]
export const VerdictSchema = z.enum([
  "strong_bullish", "bullish", "neutral", "bearish", "strong_bearish",
]);

// Mirror analysts/signals.py: AgentSignal
export const AgentSignalSchema = z.object({
  ticker: z.string(),
  analyst_id: AnalystIdSchema,
  computed_at: z.iso.datetime(),     // zod 4 top-level
  verdict: VerdictSchema,
  confidence: z.number().int().min(0).max(100),
  evidence: z.array(z.string().max(200)).max(10),
  data_unavailable: z.boolean(),
}).strict();    // mirrors ConfigDict(extra="forbid")
export type AgentSignal = z.infer<typeof AgentSignalSchema>;

// Mirror analysts/position_signal.py: PositionSignal
export const PositionStateSchema = z.enum([
  "extreme_oversold", "oversold", "fair", "overbought", "extreme_overbought",
]);
export const ActionHintSchema = z.enum([
  "consider_add", "hold_position", "consider_trim", "consider_take_profits",
]);
export const PositionSignalSchema = z.object({
  ticker: z.string(),
  computed_at: z.iso.datetime(),
  state: PositionStateSchema,
  consensus_score: z.number().min(-1).max(1),
  confidence: z.number().int().min(0).max(100),
  action_hint: ActionHintSchema,
  indicators: z.record(z.string(), z.number().nullable()),
  evidence: z.array(z.string().max(200)).max(10),
  data_unavailable: z.boolean(),
  trend_regime: z.boolean(),
}).strict();

// Mirror synthesis/decision.py: TickerDecision
export const TimeframeBandSchema = z.object({
  summary: z.string().min(1).max(500),
  drivers: z.array(z.string().max(200)).max(10),
  confidence: z.number().int().min(0).max(100),
}).strict();

export const DissentSectionSchema = z.object({
  has_dissent: z.boolean(),
  dissenting_persona: z.string().nullable(),
  dissent_summary: z.string().max(500),
}).strict();

export const TickerDecisionSchema = z.object({
  ticker: z.string(),
  computed_at: z.iso.datetime(),
  schema_version: z.literal(1),
  recommendation: z.enum(["add", "trim", "hold", "take_profits", "buy", "avoid"]),
  conviction: z.enum(["low", "medium", "high"]),
  short_term: TimeframeBandSchema,
  long_term: TimeframeBandSchema,
  open_observation: z.string().max(500),
  dissent: DissentSectionSchema,
  data_unavailable: z.boolean(),
}).strict();

// Top-level per-ticker payload (routine/storage.py shape)
export const TickerPayloadSchema = z.object({
  ticker: z.string(),
  schema_version: z.literal(1),
  analytical_signals: z.array(AgentSignalSchema),
  position_signal: PositionSignalSchema.nullable(),
  persona_signals: z.array(AgentSignalSchema),
  ticker_decision: TickerDecisionSchema.nullable(),
  errors: z.array(z.string()),
}).strict();
export type TickerPayload = z.infer<typeof TickerPayloadSchema>;

// _status.json (routine/storage.py write_daily_snapshot Phase C)
export const StatusJsonSchema = z.object({
  success: z.boolean(),
  partial: z.boolean(),
  completed_tickers: z.array(z.string()),
  failed_tickers: z.array(z.string()),
  skipped_tickers: z.array(z.string()),
  llm_failure_count: z.number().int().min(0),
  lite_mode: z.boolean(),
}).strict();

// _index.json
export const IndexJsonSchema = z.object({
  date: z.string(),
  schema_version: z.literal(1),
  run_started_at: z.iso.datetime(),
  run_completed_at: z.iso.datetime(),
  tickers: z.array(z.string()),
  lite_mode: z.boolean(),
  total_token_count_estimate: z.number().int(),
}).strict();
```

### Pattern 2: zod-Validated Fetch with Error Boundary (VIEW-15)

**What:** Every cross-network fetch goes through a single typed wrapper that runs `schema.safeParse()` and converts validation failures into a typed Error, never a thrown exception leaking to React.

**When to use:** ALL reads from `raw.githubusercontent.com`.

**Example:**

```typescript
// src/lib/github-fetch.ts
import type { ZodSchema } from "zod";

const BASE = `https://raw.githubusercontent.com/${import.meta.env.VITE_GITHUB_USER}/${import.meta.env.VITE_GITHUB_REPO}/main`;

export class SchemaMismatchError extends Error {
  constructor(public path: string, public issues: unknown) {
    super(`schema mismatch at ${path}`);
    this.name = "SchemaMismatchError";
  }
}

export async function fetchValidated<T>(path: string, schema: ZodSchema<T>): Promise<T> {
  const url = `${BASE}/${path}`;
  const res = await fetch(url, { method: "GET", credentials: "omit" });
  if (res.status === 404) throw new Error(`not_found:${path}`);
  if (!res.ok) throw new Error(`http_${res.status}:${path}`);
  const json = await res.json();
  const parsed = schema.safeParse(json);
  if (!parsed.success) throw new SchemaMismatchError(path, parsed.error.issues);
  return parsed.data;
}
```

Pair with React Query's `useQuery({ queryKey, queryFn, retry: 2, staleTime: 5*60*1000 })` and a top-level `<ErrorBoundary>` that renders `<ErrorState />` when `error instanceof SchemaMismatchError`.

### Pattern 3: One-Lens-At-A-Time Tab Discipline (VIEW-01, Pitfall #8)

**What:** Use `Tabs` from shadcn/ui (Radix UI tabs primitive) with the lens stored in URL search params (`?lens=position`), NOT React state. Bookmarkable; back-button-friendly; single source of truth.

**Why URL state:** the user can paste a link to "the Long-Term Thesis Status view" into their notes. Hash routing works too but query param composes better with `/scan`.

**When to use:** Morning Scan view (`/scan`) — three lenses as tabs. Default lens = `position` (the headline view per POSE-05).

**Sketch:**

```tsx
// src/routes/MorningScan.tsx
import { useSearchParams } from "react-router";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

const LENSES = ["position", "short", "long"] as const;
type Lens = typeof LENSES[number];

export function MorningScan() {
  const [params, setParams] = useSearchParams();
  const active = (params.get("lens") ?? "position") as Lens;
  return (
    <Tabs value={active} onValueChange={(v) => setParams({ lens: v })}>
      <TabsList>
        <TabsTrigger value="position">Position Adjustment</TabsTrigger>
        <TabsTrigger value="short">Short-Term Opportunities</TabsTrigger>
        <TabsTrigger value="long">Long-Term Thesis Status</TabsTrigger>
      </TabsList>
      <TabsContent value="position"><PositionLens /></TabsContent>
      <TabsContent value="short"><ShortTermLens /></TabsContent>
      <TabsContent value="long"><LongTermLens /></TabsContent>
    </Tabs>
  );
}
```

Radix Tabs gives keyboard nav (arrow keys, Home/End), aria-tablist roles, and focus management for free. **Do NOT** roll your own tabs.

### Pattern 4: Staleness Badge GREEN/AMBER/RED (VIEW-11, Pitfall #9)

**What:** A single computed function on `_status.json` + `_index.json.run_completed_at` returns the badge color + tooltip text. Recompute on every render via React Query's `staleTime` + `refetchInterval`.

**Threshold reconciliation needed (Open Question #6):** ROADMAP says GREEN <2h, AMBER 2-12h, RED >12h-or-partial. REQUIREMENTS.md VIEW-11 says GREEN <6h, AMBER 6-24h, RED >24h-or-partial. I recommend the **REQUIREMENTS.md thresholds** because they match the morning-batch cadence (run at 6am ET, "fresh" until ~noon ET on weekday is reasonable; "stale but usable" through next morning).

```typescript
// src/lib/staleness.ts
import type { StatusJson, IndexJson } from "./schemas";

export type Staleness = "green" | "amber" | "red";

export function computeStaleness(
  status: StatusJson | null,
  index: IndexJson | null,
  now: Date = new Date(),
): { badge: Staleness; tooltip: string } {
  if (!status || !index) return { badge: "red", tooltip: "Snapshot missing" };
  if (status.partial || !status.success) return { badge: "amber", tooltip: "Partial snapshot — some tickers failed or lite-mode" };
  if (status.lite_mode) return { badge: "amber", tooltip: "Lite mode: analyticals only, no LLM personas/synthesis" };
  const ageHours = (now.getTime() - new Date(index.run_completed_at).getTime()) / 3_600_000;
  if (ageHours > 24) return { badge: "red", tooltip: `Snapshot is ${ageHours.toFixed(0)}h old` };
  if (ageHours > 6) return { badge: "amber", tooltip: `Snapshot is ${ageHours.toFixed(0)}h old` };
  return { badge: "green", tooltip: `Fresh: ${ageHours.toFixed(1)}h old` };
}
```

Critical: render the badge in the header of EVERY page (not just the scan view) so the user can never look at deep-dive data without seeing freshness.

### Pattern 5: lightweight-charts React Wrapper (VIEW-06)

**What:** Lightweight-charts is imperative (Canvas-based); the React-correct pattern is a `useEffect`-based wrapper that creates the chart on mount, updates the data series via refs on prop change, and disposes on unmount. Do NOT use `lightweight-charts-react-components` for v1 — it's a community wrapper, the official tutorial uses the imperative pattern, and v5's API is clean enough.

**Multi-pane in v5:** RSI as a separate pane below the price pane is now first-class (was a hack in v4). Pattern:

```typescript
// src/components/deep-dive/OhlcChart.tsx
import { createChart, ColorType, CandlestickSeries, LineSeries } from "lightweight-charts";
import { useEffect, useRef } from "react";

interface Props {
  bars: { time: string; open: number; high: number; low: number; close: number }[];
  ma20: { time: string; value: number }[];
  ma50: { time: string; value: number }[];
  bbUpper: { time: string; value: number }[];
  bbLower: { time: string; value: number }[];
  rsi: { time: string; value: number }[];
}

export function OhlcChart({ bars, ma20, ma50, bbUpper, bbLower, rsi }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: "#cbd5e1" },
      grid: { vertLines: { color: "#1e293b" }, horzLines: { color: "#1e293b" } },
      autoSize: true,
    });
    const candles = chart.addSeries(CandlestickSeries);
    candles.setData(bars);
    chart.addSeries(LineSeries, { color: "#fbbf24" }).setData(ma20);
    chart.addSeries(LineSeries, { color: "#a78bfa" }).setData(ma50);
    chart.addSeries(LineSeries, { color: "#64748b", lineStyle: 2 }).setData(bbUpper);
    chart.addSeries(LineSeries, { color: "#64748b", lineStyle: 2 }).setData(bbLower);
    // RSI in a separate pane (v5 multi-pane API):
    const rsiPane = chart.addPane();
    rsiPane.addSeries(LineSeries, { color: "#f472b6" }).setData(rsi);
    return () => chart.remove();
  }, [bars, ma20, ma50, bbUpper, bbLower, rsi]);
  return <div ref={containerRef} className="h-96 w-full" />;
}
```

**BLOCKED on:** OHLC bars not in JSON today. See Open Question #1 — this code can't run until that's resolved.

### Pattern 6: Mobile-Responsive Watchlist (VIEW-12)

**Pattern:** Table-on-desktop, card-stack-on-mobile. Tailwind utility:

```tsx
{/* Desktop: table */}
<table className="hidden md:table w-full">
  <thead><tr><th>Ticker</th><th>State</th><th>Score</th></tr></thead>
  <tbody>{rows.map(...)}</tbody>
</table>

{/* Mobile: stacked cards */}
<div className="md:hidden space-y-2">
  {rows.map(r => (
    <Card key={r.ticker} className="p-4">
      <div className="flex justify-between"><span className="font-bold">{r.ticker}</span><Badge>{r.state}</Badge></div>
      <div className="text-sm text-slate-400">score: {r.consensus_score.toFixed(2)}</div>
    </Card>
  ))}
</div>
```

Tap-target sizing: minimum 44×44px (iOS HIG); shadcn Button defaults to `h-10` (40px) — bump deep-dive nav buttons to `h-11` for thumb-friendliness.

Viewport meta in `index.html`:
```html
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
```

`viewport-fit=cover` is needed for iOS Safari notch handling.

### Anti-Patterns to Avoid

- **Roll-your-own tabs.** Use `@radix-ui/react-tabs` (via shadcn). Accessibility compliance is non-trivial.
- **Roll-your-own date picker.** Use shadcn DatePicker (cmdk + react-day-picker).
- **Fetch raw OHLC from yfinance in browser.** CORS-blocked AND IP-banned. Verified across 2024-2026 reports.
- **Naked `fetch` without zod validation.** Violates VIEW-15.
- **Storing the full watchlist in component state.** Use React Query cache; one fetch per ticker per day; `staleTime: 5*60*1000` (5min).
- **localStorage for the lens selection.** Use URL state — bookmarkable, shareable, back-button-friendly.
- **Mock data hardcoded in components.** Use MSW (Mock Service Worker) for tests; never inline.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tab UI with keyboard nav + aria | Custom button group + state | Radix UI Tabs (via shadcn) | aria-tablist semantics + arrow keys + Home/End + focus management — easy to get wrong |
| Date picker for snapshot selector (VIEW-14) | `<input type="date">` styling hack | shadcn DatePicker (react-day-picker + cmdk) | Cross-browser dark-theme alignment; mobile-first |
| Async fetch state machine | useState + useEffect + try/catch | TanStack Query v5 | Loading/error/refetch states + cache invalidation + retry — re-implementing this is Pitfall #10 |
| Schema validation | hand-rolled type guards | zod 4 | Discriminated unions + safeParse + inferred TS types in one |
| OHLC + indicator overlays | recharts or self-rolled canvas | lightweight-charts 5.2 | Optimized for finance; 35KB; multi-pane; touch-pan-zoom on mobile out of box |
| Fuzzy search for tickers (VIEW-13) | substring match | fuse.js | Company-name fuzziness ("appl" → AAPL) without an embedding model |
| Toast/notification for error states | custom div + setTimeout | shadcn Toaster | Stacking, dismissal, accessible live region |
| Theme management (dark default) | CSS-in-JS theme provider | Tailwind dark variant + OKLCH tokens | Single source of truth in CSS custom properties |
| Routing | hash + window event listener | react-router v7 | URL params + nested routes — table stakes |
| Accessibility primitives | aria-* attribute soup | Radix UI | Each Radix primitive has WCAG-tested behavior |

**Key insight:** Phase 6 has zero novel UI work. Every UI primitive needed (Tabs, Card, Badge, Tooltip, DatePicker, Dialog, Toast, Select) ships in shadcn/ui. The ONLY custom components are domain-specific compositions: lens views, dual-timeframe cards, OHLC chart, persona signal card, staleness badge.

## Common Pitfalls

### Pitfall A: zod Schema Drift Without CI Enforcement
**What goes wrong:** Phase 5 ships a schema change (e.g., adds `endorsement_refs` field in Phase 9 per `schema_version: int = 1` forward-compat hook), Phase 6 zod schemas are stale, frontend renders `<ErrorState />` for every ticker.
**Why it happens:** Pydantic and zod are in different repos / different files; no automated check.
**How to avoid:** Run `model_json_schema()` on each Pydantic model in CI (a tiny pytest); compare against a snapshot file. When the snapshot changes, force the developer to regenerate zod schemas (or hand-update them) in the same PR. **Phase 6 ships the snapshot baseline; Phase 8 adds the CI check.**
**Warning signs:** Frontend error state appears immediately after a Phase 5 routine deploy; `_status.json` looks healthy but per-ticker JSON fails zod parse.

### Pitfall B: lightweight-charts Memory Leak on Route Change
**What goes wrong:** User navigates between deep-dive routes; chart instances accumulate in browser memory; tab grows to 500MB.
**Why it happens:** `chart.remove()` not called in `useEffect` cleanup function.
**How to avoid:** ALWAYS return a cleanup from the chart-creating `useEffect` that calls `chart.remove()`. Verified pattern in code example above.
**Warning signs:** Browser tab memory grows linearly with route navigation; canvas elements pile up in DOM.

### Pitfall C: Vite Build-Time Env Vars Don't Update Without Rebuild
**What goes wrong:** User changes `VITE_GITHUB_USER` in Vercel dashboard; existing deployment still reads the old user.
**Why it happens:** `import.meta.env.VITE_*` is replaced at BUILD time, not runtime.
**How to avoid:** Document this in README. For runtime config, you'd need `/runtime-config.json` fetched on app start — overkill for personal-tool v1. Stick with build-time; redeploy when user/repo changes.
**Warning signs:** "I changed the env var but the frontend still hits the old repo" — answer: redeploy.

### Pitfall D: raw.githubusercontent.com 30s CDN Lag
**What goes wrong:** Routine pushes at 6:00:00; user opens dashboard at 6:00:15; raw URL still serves yesterday's snapshot.
**Why it happens:** GitHub raw CDN cache TTL is ~30s.
**How to avoid:** TanStack Query `retry: 3, retryDelay: (n) => 10_000 * n` for 404s on today's snapshot; show "snapshot pending" loading state with a manual retry button. Surfacing it as the staleness badge "AMBER: snapshot pending" is clean.
**Warning signs:** Right after a routine run, user sees yesterday's data for the first ~30s.

### Pitfall E: Mobile Viewport Without `viewport-fit=cover` Loses Real Estate on iPhone Notch
**What goes wrong:** Header gets pushed below the notch; users see white-bar gap or content under the notch.
**How to avoid:** `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">` + `padding: env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left)` in body or app root.
**Warning signs:** iPhone Safari shows misaligned content top/bottom.

### Pitfall F: Tailwind v4 Config Migration Surprise
**What goes wrong:** Following Tailwind v3 docs, dev creates `tailwind.config.ts` — Tailwind v4 uses CSS-first config (`@theme { ... }` in globals.css).
**How to avoid:** Follow shadcn/ui's Tailwind v4 docs explicitly. Use `@tailwindcss/vite` plugin. Theme tokens live in CSS, not TS.

### Pitfall G: Discriminated Union Confusion with `analyst_id`
**What goes wrong:** Tempting to model `analytical_signals` and `persona_signals` as a discriminated union on `analyst_id`. But the JSON shape is identical for all 10 — only the enum differs. So a flat `z.array(AgentSignalSchema)` is correct; a discriminated union adds complexity for no validation benefit.
**How to avoid:** Use plain enum on `analyst_id` field. Save discriminated unions for cases where the SHAPE differs by tag (e.g., if some signal types had extra fields).

### Pitfall H: Sorting NaN consensus_score
**What goes wrong:** When `position_signal` is null (data_unavailable ticker) or `consensus_score` is 0.0, sort order in Position Lens gets jumbled.
**How to avoid:** Filter out `null position_signal` first; tie-break by ticker alphabetical. Pre-compute `Math.abs(consensus_score)` and sort descending; never sort on a derived float in-place repeatedly.

### Pitfall I: SSR Misunderstanding (Vite ≠ Next.js)
**What goes wrong:** Dev expects `getStaticProps`/`getServerSideProps`; tries to fetch JSON at build time.
**How to avoid:** This is a static SPA. ALL data fetching is client-side. README and PR template should call this out — ARCHITECTURE.md is already explicit ("read JSON directly from raw.githubusercontent.com").

### Pitfall J (re-emphasis of project Pitfall #8): Information Density Creep
**Already documented in PITFALLS.md.** Specific Phase 6 enforcement: max 5 visible signals per ticker on scan-view rows. Persona detail goes on deep-dive only. Position lens shows: ticker | state badge | |consensus_score| number | action_hint badge | top-2 evidence. Five elements, no more.

### Pitfall K (re-emphasis of project Pitfall #9): Stale-Data UX
**Already documented.** Specific Phase 6 enforcement: `<StalenessBadge />` in `<Header />` is mandatory on every route. Each ticker card on the scan view ALSO shows `_index.json.run_completed_at` formatted as relative time ("4h ago").

## Code Examples

### Example: Position Lens Sort + Render

```tsx
// src/components/lenses/PositionLens.tsx
import { useQuery } from "@tanstack/react-query";
import { fetchValidated } from "@/lib/github-fetch";
import { TickerPayloadSchema, IndexJsonSchema } from "@/lib/schemas";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Link } from "react-router";

const STATE_COLORS = {
  extreme_oversold: "bg-emerald-500",
  oversold: "bg-emerald-700",
  fair: "bg-slate-600",
  overbought: "bg-rose-700",
  extreme_overbought: "bg-rose-500",
} as const;

export function PositionLens({ date }: { date: string }) {
  const indexQ = useQuery({
    queryKey: ["index", date],
    queryFn: () => fetchValidated(`data/${date}/_index.json`, IndexJsonSchema),
    staleTime: 5 * 60 * 1000,
  });
  const tickerQs = (indexQ.data?.tickers ?? []).map((t) =>
    useQuery({
      queryKey: ["ticker", date, t],
      queryFn: () => fetchValidated(`data/${date}/${t}.json`, TickerPayloadSchema),
      staleTime: 5 * 60 * 1000,
      enabled: !!indexQ.data,
    })
  );
  if (indexQ.isLoading) return <LoadingSkeleton />;
  if (indexQ.isError) return <ErrorState error={indexQ.error} />;

  const rows = tickerQs
    .map((q) => q.data)
    .filter((p): p is NonNullable<typeof p> => p !== undefined && p.position_signal !== null)
    .map((p) => ({ ticker: p.ticker, ps: p.position_signal! }))
    .sort((a, b) => Math.abs(b.ps.consensus_score) - Math.abs(a.ps.consensus_score));

  return (
    <div className="space-y-2">
      {rows.map(({ ticker, ps }) => (
        <Link key={ticker} to={`/ticker/${ticker}`}>
          <Card className="p-4 hover:bg-slate-800 transition-colors">
            <div className="flex items-center justify-between gap-4">
              <span className="font-bold text-lg">{ticker}</span>
              <Badge className={STATE_COLORS[ps.state]}>{ps.state.replace("_", " ")}</Badge>
              <span className="font-mono">{ps.consensus_score.toFixed(2)}</span>
              <Badge variant="outline">{ps.action_hint.replace("_", " ")}</Badge>
              <span className="text-sm text-slate-400 truncate max-w-md">
                {ps.evidence[0]}
              </span>
            </div>
          </Card>
        </Link>
      ))}
    </div>
  );
}
```

### Example: vitest + RTL Component Test

```typescript
// tests/unit/StalenessBadge.test.tsx
import { describe, it, expect } from "vitest";
import { computeStaleness } from "@/lib/staleness";

describe("computeStaleness", () => {
  const mkIndex = (h: number) => ({
    date: "2026-05-03", schema_version: 1 as const,
    run_started_at: new Date(Date.now() - h*3600*1000 - 60_000).toISOString(),
    run_completed_at: new Date(Date.now() - h*3600*1000).toISOString(),
    tickers: ["AAPL"], lite_mode: false, total_token_count_estimate: 10000,
  });
  const okStatus = {
    success: true, partial: false, completed_tickers: ["AAPL"],
    failed_tickers: [], skipped_tickers: [], llm_failure_count: 0, lite_mode: false,
  };
  it("green when fresh and successful", () => {
    expect(computeStaleness(okStatus, mkIndex(2)).badge).toBe("green");
  });
  it("amber when 6-24h old", () => {
    expect(computeStaleness(okStatus, mkIndex(10)).badge).toBe("amber");
  });
  it("red when >24h old", () => {
    expect(computeStaleness(okStatus, mkIndex(30)).badge).toBe("red");
  });
  it("amber when partial", () => {
    expect(computeStaleness({...okStatus, partial: true}, mkIndex(1)).badge).toBe("amber");
  });
  it("red when status missing", () => {
    expect(computeStaleness(null, null).badge).toBe("red");
  });
});
```

## State of the Art

| Old Approach | Current Approach (2026) | When Changed | Impact |
|--------------|--------------------------|--------------|--------|
| Tailwind v3 with `tailwind.config.ts` | Tailwind v4 with `@theme` in CSS | early 2025 | Config-less; OKLCH tokens; CSS-first |
| zod v3 `z.string().email()` | zod v4 `z.email()` (top-level format fns) | mid 2025 | 14× faster string parse; new top-level API |
| react-router v6 `<Routes>` | react-router v7 declarative mode | late 2024 | Non-breaking upgrade; same API; future loader path |
| lightweight-charts v4 (RSI as panes hack) | lightweight-charts v5 multi-pane native API | late 2024 | First-class multi-pane; `addPane()` |
| Jest + Enzyme + Cypress | Vitest + RTL + Playwright | 2024-2025 | 5-10× faster cold start; first-class TS |
| ESLint + Prettier (separate) | Biome (single binary) | 2024-2025 | One tool, one config |
| HSL tokens in shadcn/ui | OKLCH tokens (`oklch(0.xx 0.xx hue)`) | early 2025 | Better color perception; future P3 wide-gamut |

**Deprecated/avoid:**
- moment.js — use date-fns
- enzyme — use @testing-library/react
- Cypress — use Playwright
- ESLint+Prettier separate configs — use Biome
- `lightweight-charts-react-components` (community wrapper) — use the imperative pattern directly; v5 API is clean
- `passthrough()`/`strict()`/`strip()` zod methods — deprecated in v4; default behavior is strip; we use `.strict()` (deprecated but still works) OR set `extra="forbid"`-equivalent inline

## Open Questions

### Open Question #1 — OHLC Data Source (HIGH IMPACT)

**The gap:** `data/YYYY-MM-DD/{TICKER}.json` does NOT contain historical OHLC bars. Phase 5's `routine/storage.py` persists `analytical_signals`, `position_signal`, `persona_signals`, `ticker_decision`, `errors` — but the `Snapshot.prices.ohlc` history is consumed by analysts and discarded.

**ROADMAP success criterion #4 demands:** "OHLC chart (lightweight-charts) with MA/BB/RSI overlays."

**Why "fetch from browser" doesn't work:** yfinance/Yahoo Finance is CORS-blocked AND IP-banned for browser-origin requests. Confirmed across 2024-2026 reports.

**Three remediations:**

1. **(RECOMMENDED) Extend Phase 5 storage to embed last-180-days OHLC in per-ticker JSON.**
   - Per-ticker JSON gets a new top-level `ohlc_bars: [{time, open, high, low, close, volume}]` field, sized to 180 trading days (~37KB JSON per ticker, ~1.85MB total for 50 tickers).
   - Pre-compute `ma20`, `ma50`, `bb_upper`, `bb_lower`, `rsi_14` series alongside in the same payload — avoids client-side recompute.
   - Schema bump: `schema_version: 2` for forward-compat.
   - Cost: 1-2 day Phase 6 amendment to Phase 5 (or a Phase-5 closeout PR before Phase 6 starts).
   - Why recommended: keeps the frontend pure-static-read; no serverless function dependency for the chart; the OHLC bars are already fetched by Phase 2 ingestion — just persist them.

2. **Defer the OHLC chart entirely to Phase 8 (mid-day refresh).**
   - Phase 6 ships everything EXCEPT VIEW-06 (the chart). User sees dual-timeframe cards + persona signals + news but no chart.
   - Phase 8's serverless function adds an `/api/ohlc?ticker=X` endpoint that fetches yfinance server-side and returns bars+overlays.
   - Cost: zero in Phase 6; pushes one success-criterion item to Phase 8.
   - Why secondary: ROADMAP explicitly lists OHLC chart as a Phase 6 success criterion; deferring weakens the morning-research utility.

3. **Render the chart from `snapshot_summary.recent_prices` if/when that field is added.**
   - The orchestrator prompt mentions `snapshot_summary` as an existing field; it's NOT in storage today (verified). Could be added.
   - Smaller in scope than option 1 (just current-state, not 180 bars).
   - Insufficient for MA50/BB/RSI overlays (need history).

**Recommendation:** **Option 1.** Plan a "Phase 5.5" amendment OR fold this into Phase 6's first plan as a prerequisite. This keeps Phase 6 scope honest; defers nothing; matches success criterion #4.

### Open Question #2 — News Feed Data Source (MEDIUM IMPACT)

**The gap:** VIEW-08 demands "news feed grouped by source with timestamps." The per-ticker JSON does NOT contain headlines today (Snapshot.news is discarded after analysts.news_sentiment scoring).

**Three remediations:**

1. **(RECOMMENDED) Extend Phase 5 storage to embed last-7-days headlines.** ~50 headlines × ~150 bytes = 7.5KB per ticker = 375KB for 50-ticker watchlist. Modest. Schema bump.
2. **Defer news feed to Phase 8 (mid-day refresh).** Phase 8's `api/refresh.py` already returns headlines; Phase 6 deep-dive shows news only if Phase 8 is wired. Loses VIEW-08 in Phase 6.
3. **Capture only headline references (URL + title + source + timestamp) in the news_sentiment AgentSignal evidence.** Already structured — just elevate to top-level `news` array. ~3-5 headlines per ticker; smaller than option 1.

**Recommendation:** **Option 1** (paired with Open Question #1 amendment), OR Option 3 if option 1 is too heavy.

### Open Question #3 — Package Manager Choice

**The choice:** pnpm (STACK.md lock) vs npm vs bun.

**Recommendation: pnpm.** STACK.md lock; works clean on Windows; content-addressable store saves disk; ecosystem support is universal. Bun is faster but less mature on Windows (per 2026 reports).

### Open Question #4 — Component Library

**Locked here:** shadcn/ui (vendored on Radix UI primitives + Tailwind v4 styling).

**Why not alternatives:**
- **Build custom:** Pitfall #10 (premature abstraction); 2-3 weeks of UI-primitive work for zero domain value.
- **Material UI / Chakra:** opinionated visual style that conflicts with finance-dashboard density; harder to customize for dark theme + OKLCH tokens.
- **headlessui:** Tailwind Labs primitives — viable but smaller component surface than Radix.
- **react-aria-components:** excellent accessibility but smaller community in 2026.

shadcn/ui's vendored model gives us full ownership of the source AND a maintained baseline.

### Open Question #5 — `thesis_status` Field Missing from TickerDecision

**The gap:** REQUIREMENTS.md VIEW-04 says "Long-Term Thesis Status lens lists tickers with thesis_status ∈ {weakening, broken} sorted by severity." But `TickerDecision.long_term: TimeframeBand` has NO `thesis_status` field — only `summary`, `drivers`, `confidence`.

**Two remediations:**

1. **Add `thesis_status: Literal["intact", "weakening", "broken", "validating"]` to TimeframeBand** — a new field on `synthesis/decision.py`. Synthesizer prompt updated to populate it. Schema bump.
2. **Derive from synthesis output heuristically** — e.g., `recommendation in {avoid, trim} AND long_term.confidence > 60 ⇒ "weakening"`. Brittle.

**Recommendation:** **Option 1.** Same Phase 5 amendment as Open Q #1/#2 — bundle the schema bumps. A clean field is cheaper than perpetual heuristic disputes.

### Open Question #6 — Staleness Threshold Reconciliation

**ROADMAP says:** GREEN <2h, AMBER 2-12h, RED >12h-or-partial.
**REQUIREMENTS.md VIEW-11 says:** GREEN <6h, AMBER 6-24h, RED >24h-or-partial.

**Recommendation:** Use REQUIREMENTS.md (6h/24h). Rationale: morning batch fires at 6am ET; user opens dashboard at 7-9am (GREEN <6h is comfortably "this morning"); afternoon use through 6pm ET is the same trading day (AMBER 6-24h is "this morning's snapshot, still actionable"); next morning before refresh is also AMBER. RED only when batch failed (>24h). The 2h threshold from ROADMAP would push the badge to AMBER by 8am ET on a normal day — too noisy.

**Action:** Update ROADMAP to match REQUIREMENTS.md, OR accept the looser thresholds. Defer to Wave 0 of Phase 6 plan.

### Open Question #7 — Snapshot Date Selector Date Enumeration (VIEW-14)

**The challenge:** How does the frontend know which dates have snapshots?

**Three options:**

1. **(RECOMMENDED) Add `data/_dates.json` written by Phase 5's `git_publish.py`** as a side-effect of every routine run — `{available_dates: ["2026-04-29", "2026-04-30", "2026-05-03"]}`. One additional atomic write per day. Schema bump.
2. **Use GitHub API to list `data/` subdirectories.** Authenticated rate limits + auth headers + CORS for the GitHub REST API. Adds complexity.
3. **Hardcode a date range and probe `_index.json` 404s.** Wasteful; ugly UX; unreliable.

**Recommendation:** **Option 1.** Tiny Phase 5 amendment. Done.

### Open Question #8 — Number of Top-Level Routes in v1

**The choice:** v1 routes — just `/scan` + `/ticker/:symbol`, OR also `/decision/:symbol`?

**Recommendation:** **Two routes only.** `/scan` (default) and `/ticker/:symbol`. The `/decision/:symbol` route is Phase 7's territory (VIEW-10 is mapped to Phase 7 in REQUIREMENTS.md / ROADMAP). Phase 6 should NOT pre-build that route. Premature scaffolding is Pitfall #10.

The deep-dive page shows the recommendation banner inline (one of the dual-timeframe cards), so users see the decision without a separate route. Phase 7 adds the dedicated decision view.

### Open Question #9 — Visual Design Direction (DEFER TO USER)

Three concrete aesthetic directions, each with concrete tradeoffs:

| Direction | What It Looks Like | Tradeoff | Best Fit If |
|-----------|---------------------|----------|-------------|
| **A. Bloomberg-Terminal Modern** | Dense data, monospace numbers, subtle accent colors (amber/cyan), minimal whitespace, table-heavy. Matrix-feel without being parody. | Pro: information-density parallels how the user reads. Con: can feel hostile / overwhelming on mobile; harder to add personas-as-cards. | User prioritizes morning scannability and reads dense quote tables at speed. |
| **B. Stripe-Dashboard Editorial** | Generous whitespace, clean sans-serif, OKLCH muted greens/reds for verdicts, large card-based layout, soft borders. Information-as-storytelling. | Pro: persona signals shine as cards; mobile-first by nature; pleasant to use daily. Con: less data-per-screen; can feel "consumer" for a research tool. | User wants a calm morning-coffee experience; reads through verdicts thoughtfully rather than scanning for outliers. |
| **C. Notion-Clean Information-Dense** | Hybrid — sans-serif body, monospace numbers, minimal chrome, sidebar navigation, OKLCH accent colors used sparingly. Information-density of A with whitespace discipline of B. | Pro: balanced; familiar to power-users; flexes between scan and deep-dive contexts. Con: requires more design decisions (more knobs to turn). | User wants both — fast scan in morning, careful read in deep-dive. |

**Recommendation:** Default to **Direction C** (Notion-clean). Best balance for the dual-use case (morning scan + deep-dive). The dark theme + OKLCH tokens in Tailwind v4 + shadcn/ui defaults all align here.

**Action:** Surface this question in plan-check; let user adjust before locking the design tokens.

### Open Question #10 — Type Generation From Pydantic to zod

**Three paths:**

1. **(RECOMMENDED for v1) Hand-author zod schemas in `src/lib/schemas.ts`.** ~150 LOC; one-time cost; Pydantic file is the source of truth in code review. v1 has 5 models — manageable.
2. **`pydantic2zod` codegen in CI.** Generates from Pydantic AST; has v2 support; some edge-case handling needed for Literal types.
3. **`datamodel-code-generator` reverse direction (Pydantic → JSON Schema → zod via tooling).** Two-hop pipeline; more brittle.

**Recommendation:** **Option 1 for Phase 6**, schedule **Option 2 as a Phase 8 quality-of-life improvement** (CI check that hand-authored zod matches Pydantic-generated JSON Schema).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest (unit/component) + Playwright (smoke) |
| Config files | `vite.config.ts` (vitest config inline) + `playwright.config.ts` |
| Quick run command | `pnpm vitest run` (~5-30s for unit tests) |
| Full suite command | `pnpm vitest run && pnpm playwright test` |
| Coverage target | 95% line / 90% branch on `src/lib/` (matches Phase 1-5 discipline); component tests are descriptive rather than coverage-driven |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VIEW-01 | One lens visible at a time; tab switch updates URL `?lens=` | component | `pnpm vitest run tests/unit/MorningScan.test.tsx` | ❌ Wave 0 |
| VIEW-02 | Position lens sorts by `\|consensus_score\|` desc; renders state, evidence, action_hint | component | `pnpm vitest run tests/unit/PositionLens.test.tsx` | ❌ Wave 0 |
| VIEW-03 | Short-term lens filters bullish + sorts by confidence | component | `pnpm vitest run tests/unit/ShortTermLens.test.tsx` | ❌ Wave 0 |
| VIEW-04 | Long-term lens filters thesis_status ∈ {weakening, broken} | component | `pnpm vitest run tests/unit/LongTermLens.test.tsx` | ❌ Wave 0 (BLOCKED on Open Q #5) |
| VIEW-05 | Deep-dive renders both timeframe cards | component | `pnpm vitest run tests/unit/DualTimeframeCards.test.tsx` | ❌ Wave 0 |
| VIEW-06 | OHLC chart renders with overlays | component (mock data) | `pnpm vitest run tests/unit/OhlcChart.test.tsx` | ❌ Wave 0 (BLOCKED on Open Q #1) |
| VIEW-07 | Persona signal cards render verdict, confidence, reasoning, evidence | component | `pnpm vitest run tests/unit/PersonaSignalCard.test.tsx` | ❌ Wave 0 |
| VIEW-08 | News feed grouped by source | component | `pnpm vitest run tests/unit/NewsFeed.test.tsx` | ❌ Wave 0 (BLOCKED on Open Q #2) |
| VIEW-09 | Open Claude Analyst pinned at top of deep-dive | component | `pnpm vitest run tests/unit/ClaudeAnalystPin.test.tsx` | ❌ Wave 0 |
| VIEW-11 | Staleness badge GREEN/AMBER/RED transitions | unit | `pnpm vitest run tests/unit/staleness.test.ts` | ❌ Wave 0 |
| VIEW-12 | Mobile viewport: stacked cards on <md breakpoint | E2E (mobile emulation) | `pnpm playwright test --project=mobile` | ❌ Wave 0 |
| VIEW-13 | Ticker typeahead with fuzzy match | component | `pnpm vitest run tests/unit/TickerSearch.test.tsx` | ❌ Wave 0 |
| VIEW-14 | Snapshot date selector loads historical date | E2E | `pnpm playwright test tests/e2e/date-selector.spec.ts` | ❌ Wave 0 |
| VIEW-15 | zod mismatch renders `<ErrorState />` not crash | component | `pnpm vitest run tests/unit/github-fetch.test.ts` | ❌ Wave 0 |
| INFRA-05 | Vercel deploys on `main` push, reads from raw URL | manual + smoke E2E | `pnpm playwright test tests/e2e/smoke.spec.ts` (post-deploy) | ❌ Wave 0 |

**Note:** Three tests are BLOCKED until Open Questions #1, #2, #5 are resolved (extending Phase 5 storage). These belong in Wave 0 of Phase 6 plan as prerequisite work.

### Sampling Rate
- **Per task commit:** `pnpm vitest run` (unit tests; ~5-30s)
- **Per wave merge:** `pnpm vitest run && pnpm tsc --noEmit && pnpm biome check src` (~1-2min)
- **Phase gate:** Full suite green + `pnpm playwright test --project=mobile` + 1 manual phone test on real iOS Safari + Android Chrome before `/gmd:verify-work`

### Wave 0 Gaps
- [ ] **Frontend scaffold:** `pnpm create vite frontend --template react-ts` + base dir structure under `frontend/`
- [ ] **Resolve Open Q #1:** Extend `routine/storage.py` to persist OHLC bars + indicator pre-computes (or defer VIEW-06 to Phase 8)
- [ ] **Resolve Open Q #2:** Persist headlines in per-ticker JSON (or defer VIEW-08 to Phase 8)
- [ ] **Resolve Open Q #5:** Add `thesis_status` field to `TimeframeBand` in `synthesis/decision.py` + update synthesizer prompt
- [ ] **Resolve Open Q #6:** Pick staleness thresholds (recommend REQUIREMENTS.md 6h/24h)
- [ ] **Resolve Open Q #7:** Add `data/_dates.json` writer in `routine/git_publish.py`
- [ ] **`tests/unit/` directory:** vitest setup + RTL config + `setup.ts` for `@testing-library/jest-dom` matchers
- [ ] **`tests/e2e/` directory:** Playwright config with mobile emulation projects (iPhone 14 Pro, Pixel 7)
- [ ] **`src/lib/schemas.ts`:** zod schemas mirroring Pydantic — baseline reference for downstream tasks
- [ ] **MSW (Mock Service Worker):** mock `raw.githubusercontent.com` for vitest tests
- [ ] **Bundled `public/tickers.json`:** SEC company-tickers map for VIEW-13 fuzzy search
- [ ] **`vercel.json`:** explicit static-build config + rewrite rules for SPA routing
- [ ] **Vercel env var setup:** `VITE_GITHUB_USER` + `VITE_GITHUB_REPO` configured in dashboard

## Sources

### Primary (HIGH confidence)
- Phase 5 source code: `synthesis/decision.py`, `analysts/signals.py`, `analysts/position_signal.py`, `routine/storage.py`, `routine/run_for_watchlist.py` — read directly; confirms exact JSON shape persisted on disk
- `prompts/personas/claude_analyst.md` — confirms Open Claude Analyst voice + per VIEW-09 pinning intent
- `.planning/PROJECT.md` — frontend stack lock (React, dark theme, mobile-responsive, Vercel, lightweight-charts, zod)
- `.planning/REQUIREMENTS.md` — VIEW-01..15 + INFRA-05 exact requirement text
- `.planning/ROADMAP.md` — Phase 6 success criteria (7 specific items)
- `.planning/research/STACK.md` + `.planning/research/FEATURES.md` + `.planning/research/PITFALLS.md` + `.planning/research/ARCHITECTURE.md` — project-wide research baseline
- [Lightweight Charts v5 release notes](https://tradingview.github.io/lightweight-charts/docs/release-notes) — confirms multi-pane API + 35KB bundle
- [Lightweight Charts React tutorial](https://tradingview.github.io/lightweight-charts/tutorials/react/simple) — confirms imperative-pattern recommendation
- [Vite on Vercel docs](https://vercel.com/docs/frameworks/frontend/vite) — confirms autodetect + build-time env var behavior
- [shadcn/ui Tailwind v4 docs](https://ui.shadcn.com/docs/tailwind-v4) — confirms CSS-first config + OKLCH tokens
- [Zod v4 release notes](https://zod.dev/v4) — confirms top-level format functions + 14× perf
- [TanStack Query v5 docs](https://tanstack.com/query/v5/docs/framework/react/comparison) — confirms staleTime + refetch semantics
- [GitHub Community discussion #69281: CORS and raw.githubusercontent.com](https://github.com/orgs/community/discussions/69281) — confirms CORS issues for preflight; simple GETs of public files work

### Secondary (MEDIUM confidence)
- [SWR vs TanStack Query 2026 comparison](https://dev.to/jake_kim_bd3065a6816799db/swr-vs-tanstack-query-2026-which-react-data-fetching-library-should-you-choose-342c) — bundle size + feature comparison
- [React Router v7 vs Wouter 2026](https://blog.logrocket.com/react-router-v7-guide/) — declarative-mode + bundle delta
- [Pockit Zod v4 migration guide](https://pockit.tools/blog/zod-v4-migration-guide-breaking-changes-new-features/) — breaking changes details
- [Why yfinance keeps getting blocked (2026)](https://medium.com/@trading.dude/why-yfinance-keeps-getting-blocked-and-what-to-use-instead-92d84bb2cc01) — confirms yfinance browser inviability
- [pydantic2zod GitHub](https://github.com/argyle-engineering/pydantic2zod) — codegen tool for Open Question #10
- [Vitest + RTL + Playwright 2026 setup guide](https://dev.to/juan_deto/configure-vitest-msw-and-playwright-in-a-react-project-with-vite-and-ts-1d92) — testing stack reference
- [Best shadcn dashboard templates 2026](https://thefrontkit.com/blogs/best-shadcn-dashboard-templates-2026) — visual-design direction precedent (finance dashboards)

### Tertiary (LOW confidence — flagged for validation)
- 2h vs 6h staleness threshold reconciliation — documented in Open Question #6; needs user confirmation
- Tailwind v4 OKLCH token migration on real iPhone wide-gamut displays — works in theory; verify on hardware before claiming done
- pnpm vs bun on Windows in mid-2026 — pnpm is safe; bun reports vary

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — every library version cross-checked against npm and official docs as of May 2026
- Architecture: **HIGH** — patterns are mature (TanStack Query + zod + shadcn/ui is the 2026 default)
- Pitfalls: **HIGH** — most surface from official docs; B (chart memory leak) and D (CDN lag) verified from code reasoning + GitHub discussions
- Open questions: **HIGH** confidence in identification; user/planner must DECIDE — research can't unblock without input

**Research date:** 2026-05-03
**Valid until:** 2026-06-15 (frontend ecosystem moves fast — Tailwind v4 + zod v4 + react-router v7 are recent and may iterate; shadcn/ui Tailwind-v4 docs received mid-2025 update)

**Critical follow-up before plan-check:**
1. Resolve Open Question #1 (OHLC data source) — blocks VIEW-06
2. Resolve Open Question #2 (news feed source) — blocks VIEW-08
3. Resolve Open Question #5 (`thesis_status` field) — blocks VIEW-04
4. Resolve Open Question #6 (staleness thresholds) — picks 6h/24h or 2h/12h
5. Resolve Open Question #7 (`_dates.json` for VIEW-14) — Phase 5 amendment
6. Resolve Open Question #9 (visual design direction A/B/C) — locks design tokens

These six items belong in Phase 6 CONTEXT.md (`/gmd:discuss-phase 6`) before plans are drafted.
