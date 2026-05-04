---
phase: 06-frontend-mvp-morning-scan-deep-dive
plan: 03
type: execute
wave: 2
depends_on: [06-01, 06-02]
files_modified:
  - frontend/src/components/LensTabs.tsx
  - frontend/src/components/StalenessBadge.tsx
  - frontend/src/components/lenses/PositionLens.tsx
  - frontend/src/components/lenses/ShortTermLens.tsx
  - frontend/src/components/lenses/LongTermLens.tsx
  - frontend/src/components/TickerCard.tsx
  - frontend/src/components/EvidenceList.tsx
  - frontend/src/components/ActionHintBadge.tsx
  - frontend/src/components/VerdictBadge.tsx
  - frontend/src/lib/loadScanData.ts
  - frontend/src/routes/ScanRoute.tsx
  - frontend/src/routes/Root.tsx
  - frontend/src/components/__tests__/LensTabs.test.tsx
  - frontend/src/components/__tests__/StalenessBadge.test.tsx
  - frontend/src/components/__tests__/PositionLens.test.tsx
  - frontend/src/components/__tests__/ShortTermLens.test.tsx
  - frontend/src/components/__tests__/LongTermLens.test.tsx
  - frontend/src/components/__tests__/TickerCard.test.tsx
  - frontend/src/lib/__tests__/loadScanData.test.ts
  - frontend/tests/e2e/scan.spec.ts
  - frontend/tests/fixtures/scan/_index.json
  - frontend/tests/fixtures/scan/_status.json
  - frontend/tests/fixtures/scan/AAPL.json
  - frontend/tests/fixtures/scan/NVDA.json
  - frontend/tests/fixtures/scan/MSFT.json
  - frontend/src/components/ui/tabs.tsx
  - frontend/src/components/ui/card.tsx
  - frontend/src/components/ui/badge.tsx
autonomous: true
requirements: [VIEW-01, VIEW-02, VIEW-03, VIEW-11]
gap_closure: false
tags: [phase-6, wave-2, morning-scan, lens-tabs, position-adjustment, short-term, long-term-thesis, staleness-badge, vitest, playwright]

must_haves:
  truths:
    - "URL `/scan/:date` renders the Morning Scan view with three lens tabs (Position Adjustment / Short-Term Opportunities / Long-Term Thesis Status)"
    - "Lens tab selection is URL-synced via `?lens=position|short|long` (deep-link sharable + survives refresh)"
    - "Only ONE lens is visible at a time (no all-at-once dump — VIEW-01 requires this; Pitfall #8 explicitly addressed)"
    - "Position Adjustment lens lists watchlist tickers sorted by `|consensus_score|` descending (VIEW-02); each row shows: ticker symbol (mono font) + state pill (extreme_oversold/oversold/fair/overbought/extreme_overbought) + action_hint badge (consider_add/hold_position/consider_trim/consider_take_profits) + top 3 evidence strings + confidence number"
    - "Short-Term Opportunities lens lists tickers with bullish short_term verdict (TickerDecision.short_term implied bullish from drivers OR ≥4 of 6 personas bullish — but the simpler v1 implementation: just sort by short_term.confidence DESC * direction-sign-derived-from-recommendation enum) — sorted by confidence × verdict-direction sign descending; shows drivers (top 5) + recommendation badge + conviction band (VIEW-03)"
    - "Long-Term Thesis Status lens FILTERS the watchlist to only tickers where TickerDecision.long_term.thesis_status ∈ {weakening, broken} (per VIEW-04 in REQUIREMENTS — though VIEW-04 is technically Wave 3's deep-dive concern, the FILTER also applies to this scan-lens). Sort: broken first, then weakening, then by long_term.confidence ASC (less confident is more concerning when thesis is breaking). NOTE: VIEW-04 is in Wave 3, but the lens here renders the SUMMARY rows — it's a list view that links to /ticker/:symbol/today for the deep-dive (Wave 3). Wave 2 ships the list-view; Wave 3 ships the deep-dive."
    - "StalenessBadge.tsx renders in Root.tsx header; reads _status.json + _index.json computed_at; computes via lib/staleness.computeStaleness; applies GREEN/AMBER/RED color via Notion-Clean palette tokens"
    - "LensTabs.tsx uses shadcn/ui tabs primitive (vendored under src/components/ui/tabs.tsx); tab active state styled with Notion-Clean accent color (#5B9DFF underline); transition is opacity fade (no slide) per CONTEXT.md motion lock + respects prefers-reduced-motion"
    - "lib/loadScanData.ts exports a TanStack useQuery hook `useScanData(date: string)` that fetches: _status.json + _index.json + per-ticker JSONs for every ticker in _index.tickers. Returns { status, index, snapshots: Record<ticker, Snapshot>, isLoading, error }. Uses Promise.allSettled internally so one ticker's zod failure doesn't crash the whole view (failed tickers surface in the snapshots map as the SchemaMismatchError sentinel — view skips them with a small banner)."
    - "ScanRoute.tsx wires useScanData(date param) + reads ?lens query param + renders LensTabs + the 3 lens components based on active lens; loading skeleton uses placeholder shadcn cards"
    - "TickerCard.tsx is the shared row primitive used by all 3 lenses; renders ticker (mono) + a slot for lens-specific content via children prop OR composition pattern; Notion-Clean card styling (1F2024 bg, 1px hairline border 2A2C30)"
    - "Each lens row is a clickable Link to `/ticker/:symbol/:date` — clicking deep-links to the Wave 3 deep-dive (Wave 2 ships only the link; Wave 3 wires the deep-dive content)"
    - "Empty / partial data UNIFORM RULE applied: if _status.json says partial=true, show 'Partial data — N/M tickers loaded' banner above the lens; if a ticker JSON 404s or schema-mismatches, exclude from the lens but show count of excluded in the partial banner"
    - "Vitest component tests: LensTabs (URL sync + only-one-visible discipline), StalenessBadge (renders correct color per state), each Lens (correct sort + filter), TickerCard (shape rendering); ≥85% line coverage on src/components/lenses + src/components"
    - "Playwright E2E test: open /scan/today (test fixtures served via vite dev server fixture or msw); switch lenses; assert URL changes; assert only one lens content is in DOM at a time"
    - "Wave 2 verification command passes: `cd frontend && pnpm test:unit --run && pnpm test:e2e -g 'morning scan'` and `pnpm build` succeeds with no type errors"
    - "Wave 1 stubs (ScanRoute placeholder) replaced with real content; Wave 1 unit tests stay green (no regression)"
  artifacts:
    - path: "frontend/src/components/LensTabs.tsx"
      provides: "URL-synced 3-tab UI; only one tab content rendered at a time; opacity fade transition; respects prefers-reduced-motion"
      min_lines: 80
    - path: "frontend/src/components/StalenessBadge.tsx"
      provides: "header badge; GREEN/AMBER/RED via lib/staleness; tooltip with 'snapshot age' + 'partial' detail"
      min_lines: 40
    - path: "frontend/src/components/lenses/PositionLens.tsx"
      provides: "VIEW-02 lens — sort by |consensus_score| DESC; render TickerCard per row with state + action_hint + evidence + confidence"
      min_lines: 80
    - path: "frontend/src/components/lenses/ShortTermLens.tsx"
      provides: "VIEW-03 lens — sort by short_term confidence × direction; render drivers + recommendation + conviction"
      min_lines: 80
    - path: "frontend/src/components/lenses/LongTermLens.tsx"
      provides: "filter long_term.thesis_status ∈ {weakening, broken}; sort by status severity then confidence ASC"
      min_lines: 80
    - path: "frontend/src/components/TickerCard.tsx"
      provides: "shared row primitive; ticker mono + lens-specific children slot; clickable Link to /ticker/:symbol/:date"
      min_lines: 50
    - path: "frontend/src/components/EvidenceList.tsx"
      provides: "renders evidence strings as bullet list; truncates to top N with 'show more'"
      min_lines: 30
    - path: "frontend/src/components/ActionHintBadge.tsx"
      provides: "color-coded badge for 4 ActionHint values (consider_add green / hold_position muted / consider_trim amber / consider_take_profits red)"
      min_lines: 25
    - path: "frontend/src/components/VerdictBadge.tsx"
      provides: "color-coded badge for 5 Verdict values (strong_bullish/bullish green; neutral muted; bearish/strong_bearish red)"
      min_lines: 25
    - path: "frontend/src/lib/loadScanData.ts"
      provides: "useScanData(date) TanStack hook fanning out to N per-ticker fetches via Promise.allSettled; returns status + index + snapshots map + error map"
      min_lines: 60
    - path: "frontend/src/routes/ScanRoute.tsx"
      provides: "wires useScanData + ?lens URL param + LensTabs + 3 lens components; loading skeleton; partial-data banner"
      min_lines: 80
    - path: "frontend/src/routes/Root.tsx"
      provides: "header now renders StalenessBadge (replaces Wave 1 placeholder div); preserves Outlet"
      min_lines: 35
    - path: "frontend/src/components/ui/tabs.tsx"
      provides: "shadcn/ui Tabs vendored from `pnpm dlx shadcn@latest add tabs` (or copy-paste from shadcn docs); Notion-Clean styling applied via index.css color tokens"
      min_lines: 50
    - path: "frontend/src/components/ui/card.tsx"
      provides: "shadcn/ui Card vendored"
      min_lines: 60
    - path: "frontend/src/components/ui/badge.tsx"
      provides: "shadcn/ui Badge vendored"
      min_lines: 30
    - path: "frontend/tests/fixtures/scan/_index.json"
      provides: "fixture for 3 tickers (AAPL, NVDA, MSFT) at fictitious date; mirrors real Phase 5 schema_version=2 shape"
      min_lines: 12
    - path: "frontend/tests/fixtures/scan/_status.json"
      provides: "happy-path status fixture (success=true, partial=false, all 3 tickers completed)"
      min_lines: 10
    - path: "frontend/tests/fixtures/scan/AAPL.json"
      provides: "full per-ticker fixture with 4 analytical_signals + position_signal + 6 persona_signals + ticker_decision + ohlc_history (180 entries) + indicators + headlines"
      min_lines: 200
    - path: "frontend/tests/fixtures/scan/NVDA.json"
      provides: "full per-ticker fixture; thesis_status='broken' on long_term so LongTermLens picks it up"
      min_lines: 200
    - path: "frontend/tests/fixtures/scan/MSFT.json"
      provides: "full per-ticker fixture; bullish short_term so ShortTermLens picks it up"
      min_lines: 200
    - path: "frontend/tests/e2e/scan.spec.ts"
      provides: "Playwright happy-path: open /scan/today, see 3 lens tabs, click each, assert URL changes, assert only one content area visible"
      min_lines: 60
  key_links:
    - from: "frontend/src/routes/ScanRoute.tsx"
      to: "frontend/src/lib/loadScanData.ts"
      via: "useScanData(date) hook"
      pattern: "useScanData|loadScanData"
    - from: "frontend/src/lib/loadScanData.ts"
      to: "raw.githubusercontent.com per-ticker JSON"
      via: "fetchAndParse + SnapshotSchema"
      pattern: "fetchAndParse.*SnapshotSchema"
    - from: "frontend/src/components/LensTabs.tsx"
      to: "URL ?lens query param"
      via: "useSearchParams from react-router"
      pattern: "useSearchParams|setSearchParams"
    - from: "frontend/src/components/StalenessBadge.tsx"
      to: "frontend/src/lib/staleness.ts"
      via: "computeStaleness(_index.run_completed_at, _status.partial)"
      pattern: "computeStaleness"
---

<objective>
Build the Morning Scan three-lens view at `/scan/:date` — the headline view of the entire app. Three tabs (Position Adjustment / Short-Term Opportunities / Long-Term Thesis Status), one visible at a time, URL-synced via `?lens=`. Header staleness badge transitions GREEN/AMBER/RED per VIEW-11. Empty/partial data handled per CONTEXT.md UNIFORM RULE.

Purpose: Closes VIEW-01, VIEW-02, VIEW-03, VIEW-11. Position Adjustment is the headline lens — sorted by `|consensus_score|` DESC so the most-extreme tickers surface first (POSE-05 promise: "the headline data structure powering the Morning Scan's primary lens"). The lens tab discipline (one at a time) addresses Pitfall #8 — UI overload kills the morning-scan use case.

Output: A working `/scan/today` page with 3 lenses, URL-synced lens selection, staleness badge, and Playwright E2E coverage. Clicking any ticker row deep-links to `/ticker/:symbol/today` (Wave 3 wires the deep-dive content).
</objective>

<execution_context>
@C:/Users/Mohan/.claude/workflows/execute-plan.md
@C:/Users/Mohan/.claude/templates/summary.md
</execution_context>

<context>
@.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-CONTEXT.md
@.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-01-SUMMARY.md
@.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-02-SUMMARY.md

# Wave 1 outputs the Wave 2 imports
@frontend/src/schemas/index.ts
@frontend/src/lib/fetchSnapshot.ts
@frontend/src/lib/staleness.ts
@frontend/src/lib/utils.ts
@frontend/src/routes/Root.tsx
@frontend/src/routes/ScanRoute.tsx

# Skills relevant to Wave 2 visual work
@C:/Users/Mohan/.claude/skills/design-taste-frontend/SKILL.md
@C:/Users/Mohan/.claude/skills/minimalist-ui/SKILL.md
@C:/Users/Mohan/.claude/skills/frontend-design/SKILL.md

<interfaces>
<!-- Already authored in Wave 1 — Wave 2 imports these directly. -->

From frontend/src/schemas/index.ts:
- SnapshotSchema, type Snapshot — per-ticker JSON shape (data/{date}/{TICKER}.json)
- StatusSchema, type Status — _status.json
- AgentSignalSchema, type AgentSignal
- PositionSignalSchema, type PositionSignal
- TickerDecisionSchema, type TickerDecision
- ThesisStatusSchema, type ThesisStatus

From frontend/src/lib/fetchSnapshot.ts:
- fetchAndParse<T>(url, schema): Promise<T>
- snapshotUrl(date, ticker), indexUrl(date), statusUrl(date), datesUrl()
- SchemaMismatchError, FetchNotFoundError

From frontend/src/lib/staleness.ts:
- computeStaleness(snapshotIso, partial, now?) -> 'GREEN' | 'AMBER' | 'RED'

From frontend/src/lib/utils.ts:
- cn(...inputs) — Tailwind class merge
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Vendor shadcn/ui primitives + build shared visual components</name>
  <files>frontend/src/components/ui/tabs.tsx, frontend/src/components/ui/card.tsx, frontend/src/components/ui/badge.tsx, frontend/src/components/StalenessBadge.tsx, frontend/src/components/VerdictBadge.tsx, frontend/src/components/ActionHintBadge.tsx, frontend/src/components/EvidenceList.tsx, frontend/src/components/TickerCard.tsx, frontend/src/components/__tests__/StalenessBadge.test.tsx, frontend/src/components/__tests__/TickerCard.test.tsx</files>
  <action>
    1. Vendor shadcn/ui primitives via:
       ```bash
       cd frontend
       pnpm dlx shadcn@latest add tabs card badge --yes --overwrite
       ```
       This generates `src/components/ui/tabs.tsx`, `card.tsx`, `badge.tsx`. If shadcn CLI fails (non-interactive issues, react 19 compat), copy-paste the relevant primitives from https://ui.shadcn.com/docs/components/{tabs,card,badge} and adjust import paths to `@/lib/utils`. Both options yield equivalent code.
    2. Author `src/components/StalenessBadge.tsx`:
       ```tsx
       import { computeStaleness, type StalenessLevel } from '@/lib/staleness'
       import { Badge } from './ui/badge'
       interface Props { snapshotIso: string; partial: boolean }
       const COLOR: Record<StalenessLevel, string> = {
         GREEN: 'bg-bullish/10 text-bullish border-bullish/30',
         AMBER: 'bg-amber/10 text-amber border-amber/30',
         RED: 'bg-bearish/10 text-bearish border-bearish/30',
       }
       export function StalenessBadge({ snapshotIso, partial }: Props) {
         const level = computeStaleness(snapshotIso, partial)
         const ageHrs = ((Date.now() - new Date(snapshotIso).getTime()) / 3_600_000).toFixed(1)
         return <Badge variant="outline" className={COLOR[level]} title={`Snapshot age ${ageHrs}h${partial ? ' · partial' : ''}`}>{level}</Badge>
       }
       ```
    3. Author `src/components/VerdictBadge.tsx` — 5 colors mapped to Verdict values; mono font for verdict text.
    4. Author `src/components/ActionHintBadge.tsx` — 4 colors mapped to ActionHint values.
    5. Author `src/components/EvidenceList.tsx` — `interface Props { items: string[]; max?: number }` — renders top N (default 3) as muted bullet list with mono font; if items.length > max, render `+{N} more` collapsed disclosure (use shadcn collapsible OR plain <details> for v1 — plain is fine).
    6. Author `src/components/TickerCard.tsx`:
       ```tsx
       import { Link } from 'react-router'
       import { Card, CardContent } from './ui/card'
       import { cn } from '@/lib/utils'
       interface Props { ticker: string; date: string; children: React.ReactNode; className?: string }
       export function TickerCard({ ticker, date, children, className }: Props) {
         return (
           <Link to={`/ticker/${ticker}/${date}`} className="block hover:bg-surface/60 transition-colors">
             <Card className={cn("border-border bg-surface", className)}>
               <CardContent className="flex items-start gap-4 p-6">
                 <div className="font-mono text-lg font-semibold w-20 shrink-0">{ticker}</div>
                 <div className="flex-1 min-w-0">{children}</div>
               </CardContent>
             </Card>
           </Link>
         )
       }
       ```
    7. Author tests:
       - `__tests__/StalenessBadge.test.tsx`: render with 1h-old + partial=false → 'GREEN' text + green color class; 12h + false → 'AMBER'; 30h + false → 'RED'; 1h + partial=true → 'AMBER'.
       - `__tests__/TickerCard.test.tsx`: renders ticker text in mono font (querySelector for class containing 'font-mono'); renders children inside; href is `/ticker/AAPL/2026-05-04`.
    8. Run: `cd frontend && pnpm test:unit src/components --run` — confirm tests pass.
    9. Commit with: `feat(06-03): vendor shadcn primitives + build StalenessBadge + TickerCard + supporting badges`
  </action>
  <verify>
    <automated>cd frontend && pnpm test:unit src/components --run 2>&1 | tail -10</automated>
  </verify>
  <done>shadcn/ui primitives vendored; 5 visual components built + 2 component test files green; commit landed.</done>
</task>

<task type="auto">
  <name>Task 2: loadScanData hook + 3 lens components + LensTabs + ScanRoute wiring</name>
  <files>frontend/src/lib/loadScanData.ts, frontend/src/lib/__tests__/loadScanData.test.ts, frontend/src/components/LensTabs.tsx, frontend/src/components/__tests__/LensTabs.test.tsx, frontend/src/components/lenses/PositionLens.tsx, frontend/src/components/lenses/ShortTermLens.tsx, frontend/src/components/lenses/LongTermLens.tsx, frontend/src/components/__tests__/PositionLens.test.tsx, frontend/src/components/__tests__/ShortTermLens.test.tsx, frontend/src/components/__tests__/LongTermLens.test.tsx, frontend/src/routes/ScanRoute.tsx, frontend/src/routes/Root.tsx</files>
  <action>
    1. **src/lib/loadScanData.ts**:
       ```ts
       import { useQuery } from '@tanstack/react-query'
       import { fetchAndParse, indexUrl, statusUrl, snapshotUrl } from './fetchSnapshot'
       import { SnapshotSchema, StatusSchema, type Snapshot, type Status } from '@/schemas'
       import { z } from 'zod'

       const IndexSchema = z.object({
         date: z.string(), schema_version: z.literal(2),
         run_started_at: z.string().datetime(),
         run_completed_at: z.string().datetime(),
         tickers: z.array(z.string()),
         lite_mode: z.boolean(),
         total_token_count_estimate: z.number(),
       })
       export type ScanIndex = z.infer<typeof IndexSchema>

       export interface ScanData {
         status: Status; index: ScanIndex;
         snapshots: Record<string, Snapshot>;
         failedTickers: string[];  // tickers whose JSON 404'd or zod-mismatched
       }

       async function loadScan(date: string): Promise<ScanData> {
         const [status, index] = await Promise.all([
           fetchAndParse(statusUrl(date), StatusSchema),
           fetchAndParse(indexUrl(date), IndexSchema),
         ])
         const settled = await Promise.allSettled(
           index.tickers.map(t => fetchAndParse(snapshotUrl(date, t), SnapshotSchema).then(s => [t, s] as const))
         )
         const snapshots: Record<string, Snapshot> = {}
         const failedTickers: string[] = []
         for (let i = 0; i < settled.length; i++) {
           const r = settled[i]
           if (r.status === 'fulfilled') snapshots[r.value[0]] = r.value[1]
           else failedTickers.push(index.tickers[i])
         }
         return { status, index, snapshots, failedTickers }
       }

       export function useScanData(date: string) {
         return useQuery({ queryKey: ['scan', date], queryFn: () => loadScan(date) })
       }

       // Note: Wave 0 schema_version=2 is enforced by SnapshotSchema. v1 snapshots
       // will surface as failedTickers — Wave 4 ErrorBoundary will render the
       // schema-mismatch banner per CONTEXT.md UNIFORM RULE.
       ```
    2. **src/lib/__tests__/loadScanData.test.ts** — mock fetch with 3 tickers (one happy-path snapshot, one 404, one schema-mismatch); assert returned ScanData has 1 entry in snapshots, 2 in failedTickers.
    3. **src/components/LensTabs.tsx**:
       ```tsx
       import { useSearchParams } from 'react-router'
       import { Tabs, TabsList, TabsTrigger, TabsContent } from './ui/tabs'
       export type LensId = 'position' | 'short' | 'long'
       const VALID: Set<LensId> = new Set(['position', 'short', 'long'])
       interface Props { positionContent: React.ReactNode; shortContent: React.ReactNode; longContent: React.ReactNode }
       export function LensTabs({ positionContent, shortContent, longContent }: Props) {
         const [params, setParams] = useSearchParams()
         const lensParam = params.get('lens')
         const lens: LensId = (lensParam && VALID.has(lensParam as LensId)) ? (lensParam as LensId) : 'position'
         function setLens(next: LensId) {
           setParams(prev => { const np = new URLSearchParams(prev); np.set('lens', next); return np }, { replace: true })
         }
         return (
           <Tabs value={lens} onValueChange={(v) => setLens(v as LensId)}>
             <TabsList>
               <TabsTrigger value="position">Position Adjustment</TabsTrigger>
               <TabsTrigger value="short">Short-Term Opportunities</TabsTrigger>
               <TabsTrigger value="long">Long-Term Thesis Status</TabsTrigger>
             </TabsList>
             <TabsContent value="position">{positionContent}</TabsContent>
             <TabsContent value="short">{shortContent}</TabsContent>
             <TabsContent value="long">{longContent}</TabsContent>
           </Tabs>
         )
       }
       ```
       Critical: shadcn TabsContent only renders the active tab's children — that satisfies the "only one visible at a time" VIEW-01 + Pitfall #8 lock. Confirm by reading the vendored tabs.tsx — Radix Tabs.Content is mounted unmount-on-inactive by default with `forceMount={false}` (the default). DO NOT pass forceMount.
    4. **src/components/__tests__/LensTabs.test.tsx** — render inside MemoryRouter (initialEntries=['/scan/2026-05-04']); assert default lens='position' (no ?lens param); click 'Short-Term' tab; assert URL ?lens=short and short content visible + position content NOT in document (the discipline test); switch to long; same.
    5. **src/components/lenses/PositionLens.tsx**:
       ```tsx
       import type { Snapshot } from '@/schemas'
       import { TickerCard } from '../TickerCard'
       import { ActionHintBadge } from '../ActionHintBadge'
       import { EvidenceList } from '../EvidenceList'
       interface Props { date: string; snapshots: Record<string, Snapshot> }
       export function PositionLens({ date, snapshots }: Props) {
         const rows = Object.values(snapshots)
           .filter(s => s.position_signal && !s.position_signal.data_unavailable)
           .sort((a, b) => Math.abs(b.position_signal!.consensus_score) - Math.abs(a.position_signal!.consensus_score))
         if (rows.length === 0) return <div className="text-text-secondary p-6">No position-adjustment data for this date.</div>
         return (
           <div className="flex flex-col gap-4 pt-6">
             {rows.map(s => {
               const ps = s.position_signal!
               return (
                 <TickerCard key={s.ticker} ticker={s.ticker} date={date}>
                   <div className="flex items-start gap-6">
                     <div className="flex flex-col gap-2 min-w-0">
                       <div className="flex items-center gap-3">
                         <span className="text-sm font-mono text-text-secondary">state={ps.state}</span>
                         <span className="text-sm font-mono text-text-secondary">score={ps.consensus_score.toFixed(2)}</span>
                         <span className="text-sm font-mono text-text-secondary">conf={ps.confidence}</span>
                         <ActionHintBadge hint={ps.action_hint} />
                       </div>
                       <EvidenceList items={ps.evidence} max={3} />
                     </div>
                   </div>
                 </TickerCard>
               )
             })}
           </div>
         )
       }
       ```
    6. **src/components/lenses/ShortTermLens.tsx** — sort by `(short_term.confidence) * directionSign(recommendation)` DESC where directionSign maps add/buy → +1; trim/take_profits/avoid → -1; hold → 0. Filter to positive direction (only show bullish opportunities per VIEW-03 wording). Render drivers (top 5) + recommendation badge + conviction band.
    7. **src/components/lenses/LongTermLens.tsx** — filter to long_term.thesis_status ∈ {weakening, broken}; sort severity (broken first) then long_term.confidence ASC. Render thesis_status pill + summary + drivers (top 3).
    8. Tests for each lens with fixture snapshots (use scan/AAPL.json + NVDA.json + MSFT.json fixtures from Task 3) — assert sort order + filter behavior + click-through link href.
    9. **src/routes/ScanRoute.tsx** — replace Wave 1 stub with:
       ```tsx
       import { useParams } from 'react-router'
       import { useScanData } from '@/lib/loadScanData'
       import { LensTabs } from '@/components/LensTabs'
       import { PositionLens } from '@/components/lenses/PositionLens'
       import { ShortTermLens } from '@/components/lenses/ShortTermLens'
       import { LongTermLens } from '@/components/lenses/LongTermLens'
       export default function ScanRoute() {
         const { date = 'today' } = useParams()
         const { data, isLoading, error } = useScanData(date)
         if (isLoading) return <div className="text-text-secondary p-12">Loading scan…</div>
         if (error) return <div className="text-bearish p-12">Failed to load: {(error as Error).message}</div>
         if (!data) return null
         const partial = data.status.partial || data.failedTickers.length > 0
         return (
           <div>
             {partial && (
               <div className="mb-6 rounded-md border border-amber/30 bg-amber/10 px-4 py-3 text-sm text-amber">
                 Partial data — {Object.keys(data.snapshots).length}/{data.index.tickers.length} tickers loaded
                 {data.failedTickers.length > 0 && ` (${data.failedTickers.length} failed: ${data.failedTickers.slice(0,5).join(', ')}${data.failedTickers.length > 5 ? '…' : ''})`}
               </div>
             )}
             <LensTabs
               positionContent={<PositionLens date={date} snapshots={data.snapshots} />}
               shortContent={<ShortTermLens date={date} snapshots={data.snapshots} />}
               longContent={<LongTermLens date={date} snapshots={data.snapshots} />}
             />
           </div>
         )
       }
       ```
    10. **src/routes/Root.tsx** — replace Wave 1 placeholder div with:
        ```tsx
        // Header reads the LATEST date's _status.json + _index.json to compute staleness.
        // For Wave 2 keep it simple: read the date from the current URL (useParams from child)
        // OR fetch data/_dates.json + most-recent date's _status. Wave 4 wires the date selector.
        // Simplest Wave 2 implementation: lift staleness data via a context provider populated
        // by ScanRoute, OR just refetch _status.json + _index.json in Root.tsx using the URL
        // param. Pick the latter — useMatches from react-router gives us the :date param.
        ```
        Implement Root.tsx to use useMatches to read the active :date param if present (defaults to 'today'); inside Root, useQuery on _status.json + _index.json for that date; pass to <StalenessBadge snapshotIso={index.run_completed_at} partial={status.partial} />. If still loading, render a muted "—" placeholder.
    11. Run: `cd frontend && pnpm test:unit --run && pnpm typecheck && pnpm build` — confirm green.
    12. Commit with: `feat(06-03): morning scan route with 3 URL-synced lenses + staleness badge`
  </action>
  <verify>
    <automated>cd frontend && pnpm test:unit --run 2>&1 | tail -10</automated>
  </verify>
  <done>loadScanData + LensTabs + 3 lenses + ScanRoute + Root all built; ~15+ component/hook tests green; only-one-lens-visible discipline locked at the test layer.</done>
</task>

<task type="auto">
  <name>Task 3: Test fixtures + Playwright E2E for morning scan</name>
  <files>frontend/tests/fixtures/scan/_index.json, frontend/tests/fixtures/scan/_status.json, frontend/tests/fixtures/scan/AAPL.json, frontend/tests/fixtures/scan/NVDA.json, frontend/tests/fixtures/scan/MSFT.json, frontend/tests/e2e/scan.spec.ts, frontend/tests/e2e/fixtures-server.ts</files>
  <action>
    1. Hand-author 3 per-ticker fixture JSONs that round-trip through SnapshotSchema. Use realistic-looking but synthetic data:
       - AAPL: position_signal.state='oversold', consensus_score=-0.65 (high |score|), action_hint='consider_add'; ticker_decision.short_term.confidence=70 + recommendation='add' (bullish); ticker_decision.long_term.thesis_status='intact'
       - NVDA: position_signal.state='overbought', consensus_score=+0.78 (highest |score|, sorts first in PositionLens); action_hint='consider_take_profits'; long_term.thesis_status='broken' (LongTermLens picks up); short_term recommendation='take_profits' (bearish — ShortTermLens does NOT show it)
       - MSFT: position_signal.state='fair', consensus_score=+0.05 (low |score|, sorts last); short_term.confidence=85 + recommendation='buy' (highest in ShortTermLens); long_term.thesis_status='weakening' (LongTermLens picks up after NVDA-broken)
       Each ticker needs 4 analytical_signals + 6 persona_signals (use claude_analyst as 6th — required by analyst_id Literal); ohlc_history can be a small array (≥27 bars to satisfy any indicator warmup; 30 is safe); indicators arrays aligned to ohlc_history length; headlines list (3-5 entries each).
    2. Create `_index.json` listing AAPL, NVDA, MSFT with run_completed_at = current time minus 2h (so staleness = GREEN); schema_version=2; lite_mode=false.
    3. Create `_status.json`: success=true, partial=false, all 3 in completed_tickers, lite_mode=false, llm_failure_count=0.
    4. **tests/e2e/fixtures-server.ts** — small helper that, when called from a Playwright spec, intercepts requests to raw.githubusercontent.com and serves the fixture files via Playwright's route() API:
       ```ts
       import type { Page } from '@playwright/test'
       import fs from 'node:fs'
       import path from 'node:path'
       export async function mountScanFixtures(page: Page, date = 'today') {
         const fixDir = path.resolve(__dirname, 'fixtures/scan')
         await page.route(/raw\.githubusercontent\.com\/.+\/_status\.json/, route => route.fulfill({ body: fs.readFileSync(path.join(fixDir, '_status.json')) }))
         await page.route(/raw\.githubusercontent\.com\/.+\/_index\.json/, route => route.fulfill({ body: fs.readFileSync(path.join(fixDir, '_index.json')) }))
         await page.route(/raw\.githubusercontent\.com\/.+\/(AAPL|NVDA|MSFT)\.json/, route => {
           const m = route.request().url().match(/(AAPL|NVDA|MSFT)\.json$/)!
           route.fulfill({ body: fs.readFileSync(path.join(fixDir, `${m[1]}.json`)) })
         })
       }
       ```
    5. **tests/e2e/scan.spec.ts**:
       ```ts
       import { test, expect } from '@playwright/test'
       import { mountScanFixtures } from './fixtures-server'

       test.describe('morning scan', () => {
         test.beforeEach(async ({ page }) => mountScanFixtures(page))

         test('renders 3 lens tabs and only one content visible', async ({ page }) => {
           await page.goto('/scan/2026-05-04')
           await expect(page.getByRole('tab', { name: 'Position Adjustment' })).toBeVisible()
           await expect(page.getByRole('tab', { name: 'Short-Term Opportunities' })).toBeVisible()
           await expect(page.getByRole('tab', { name: 'Long-Term Thesis Status' })).toBeVisible()
           // Default lens=position — NVDA appears (highest |consensus_score|=0.78)
           await expect(page.locator('a[href*="/ticker/NVDA/"]')).toBeVisible()
           // Switch to short — MSFT appears, NVDA NOT visible
           await page.getByRole('tab', { name: 'Short-Term Opportunities' }).click()
           await expect(page).toHaveURL(/\?lens=short/)
           await expect(page.locator('a[href*="/ticker/MSFT/"]')).toBeVisible()
         })

         test('long-term lens filters to weakening or broken', async ({ page }) => {
           await page.goto('/scan/2026-05-04?lens=long')
           // NVDA (broken) and MSFT (weakening) appear; AAPL (intact) does not
           await expect(page.locator('a[href*="/ticker/NVDA/"]')).toBeVisible()
           await expect(page.locator('a[href*="/ticker/MSFT/"]')).toBeVisible()
           await expect(page.locator('a[href*="/ticker/AAPL/"]')).not.toBeVisible()
         })

         test('staleness badge shows GREEN with 2h-old fixture', async ({ page }) => {
           // Mock Date.now() if needed — but the fixture uses `new Date() - 2h` so live should still be GREEN
           await page.goto('/scan/2026-05-04')
           await expect(page.getByText('GREEN')).toBeVisible()
         })
       })
       ```
       NOTE on staleness badge time: the fixture writes run_completed_at as a hard-coded ISO string (e.g., 2 hours before the test was authored). Either (a) compute it dynamically in the fixture-server route handler at request time, OR (b) accept that the badge may show RED when the fixture ages and skip the staleness assertion (or use page.clock.install() in Playwright to freeze time). Pick (a) — compute run_completed_at dynamically:
       ```ts
       await page.route(/_index\.json/, route => {
         const idx = JSON.parse(fs.readFileSync(...).toString())
         idx.run_completed_at = new Date(Date.now() - 2*60*60*1000).toISOString()
         idx.run_started_at = new Date(Date.now() - 2.5*60*60*1000).toISOString()
         route.fulfill({ body: JSON.stringify(idx) })
       })
       ```
    6. Run: `cd frontend && pnpm test:e2e -g 'morning scan'` — expect all 3 specs pass on chromium-desktop.
    7. Commit with: `test(06-03): add scan fixtures + Playwright E2E for 3-lens UI`
  </action>
  <verify>
    <automated>cd frontend && pnpm test:e2e --project=chromium-desktop -g 'morning scan' 2>&1 | tail -15</automated>
  </verify>
  <done>3 fixture JSONs round-trip through SnapshotSchema; Playwright fixture-server helper works; 3 E2E specs green on chromium-desktop; commit landed.</done>
</task>

</tasks>

<verification>
- All 3 tasks complete; commits landed
- Vitest: ~50+ unit tests passing across schemas + lib + components (Wave 1's 42 + Wave 2's ~15 new)
- Playwright: chromium-desktop morning-scan E2E green; smoke E2E (Wave 1) still green
- typecheck + build succeed
- VIEW-01: 3 lens tabs visible; only one content area at a time (Radix Tabs default unmounting verified by E2E)
- VIEW-02: Position lens sorted by |consensus_score| DESC (NVDA 0.78 > AAPL 0.65 > MSFT 0.05)
- VIEW-03: Short-Term lens shows MSFT (bullish recommendation=buy), excludes NVDA (take_profits)
- VIEW-11: StalenessBadge in header renders GREEN/AMBER/RED based on Wave 1 staleness logic
- LongTermLens filter: only weakening + broken tickers (Wave 4 might tweak the sort but the filter is locked here)
</verification>

<success_criteria>
- [ ] /scan/:date page renders 3 lens tabs; ?lens query param syncs URL ↔ active tab
- [ ] Only ONE lens's content is in the DOM at any moment (Pitfall #8 / VIEW-01 lock)
- [ ] PositionLens sorts by |consensus_score| DESC; renders state + action_hint + evidence + confidence
- [ ] ShortTermLens shows bullish-direction tickers sorted by confidence DESC
- [ ] LongTermLens filters to thesis_status ∈ {weakening, broken}; sorts severity then confidence ASC
- [ ] StalenessBadge in Root header transitions GREEN/AMBER/RED per VIEW-11
- [ ] Empty/partial banner shows when status.partial=true OR any per-ticker fetch fails
- [ ] Click-through from any lens row → /ticker/:symbol/:date (Wave 3 wires deep-dive)
- [ ] Vitest unit tests: ~15 new tests pass; total Wave 1+2 vitest count ≥ 60 tests green
- [ ] Playwright morning-scan E2E green on chromium-desktop
- [ ] Notion-Clean palette honored: 1F2024 cards, 2A2C30 hairline borders, 5B9DFF accent for active tab
- [ ] 3 commits landed: `feat(06-03): vendor primitives` → `feat(06-03): morning scan route` → `test(06-03): scan fixtures + E2E`
</success_criteria>

<output>
After completion, create `.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-03-SUMMARY.md` matching Phase 1-5 SUMMARY template — sections: Plan Identity / Wave / Outcome / Files Created / Components Built / Lenses (3 — sort/filter rules locked) / Tests Added (vitest + Playwright) / Notion-Clean Palette Applied / Notes for Wave 3 (TickerRoute deep-dive consumes the same fixture shape).
</output>
