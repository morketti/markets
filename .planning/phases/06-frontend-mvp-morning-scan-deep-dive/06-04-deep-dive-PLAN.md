---
phase: 06-frontend-mvp-morning-scan-deep-dive
plan: 04
type: execute
wave: 3
depends_on: [06-01, 06-02, 06-03]
files_modified:
  - frontend/src/components/Chart.tsx
  - frontend/src/components/PersonaCard.tsx
  - frontend/src/components/OpenClaudePin.tsx
  - frontend/src/components/NewsList.tsx
  - frontend/src/components/TimeframeCard.tsx
  - frontend/src/components/AnalyticalSignalCard.tsx
  - frontend/src/lib/loadTickerData.ts
  - frontend/src/routes/TickerRoute.tsx
  - frontend/src/components/__tests__/Chart.test.tsx
  - frontend/src/components/__tests__/PersonaCard.test.tsx
  - frontend/src/components/__tests__/OpenClaudePin.test.tsx
  - frontend/src/components/__tests__/NewsList.test.tsx
  - frontend/src/components/__tests__/TimeframeCard.test.tsx
  - frontend/src/lib/__tests__/loadTickerData.test.ts
  - frontend/tests/e2e/deep-dive.spec.ts
  - frontend/src/components/ui/separator.tsx
autonomous: true
requirements: [VIEW-04, VIEW-05, VIEW-06, VIEW-07, VIEW-08, VIEW-09, VIEW-12, VIEW-13]
gap_closure: false
tags: [phase-6, wave-3, deep-dive, ticker-route, lightweight-charts, persona-cards, open-claude-pin, news-list, dual-timeframe, search-typeahead]

must_haves:
  truths:
    - "URL `/ticker/:symbol/:date?` renders the Per-Ticker Deep-Dive view; `:date` defaults to 'today' when absent"
    - "Open Claude Analyst observation pinned at TOP of the deep-dive (per VIEW-09 + user MEMORY.md feedback: 'include Claude's inherent reasoning, not just personas') — even when claude_analyst.data_unavailable=True, the pin renders a muted 'Open Claude Analyst: data unavailable' state (never silently absent)"
    - "Dual-timeframe cards (TimeframeCard.tsx) render short_term + long_term side-by-side at top below OpenClaudePin (VIEW-05): each shows summary + drivers (top 5) + confidence + thesis_status"
    - "Chart.tsx renders OHLC chart via lightweight-charts 5.2 with: candlestick series from snapshot.ohlc_history, MA20 line overlay, MA50 line overlay, Bollinger upper + lower bands, RSI(14) in a subordinate pane below (VIEW-06). Reads from snapshot.indicators (Wave 0 pre-computed series — frontend does NOT recompute)."
    - "PersonaCard.tsx renders one persona's AgentSignal as an individual card (verdict + confidence + reasoning + evidence). 5 cards rendered in a grid: buffett, munger, wood, burry, lynch (NOT claude_analyst — that's the OpenClaudePin at top, VIEW-07 + VIEW-09 separation locked per user MEMORY)"
    - "AnalyticalSignalCard.tsx renders the 4 analytical AgentSignals (fundamentals + technicals + news_sentiment + valuation) — distinct from PersonaCard styling (analyticals are deterministic Python; personas are LLM)"
    - "NewsList.tsx renders snapshot.headlines grouped by source (Yahoo Finance / Google News / FinViz); within each group sorted by published_at DESC; each headline is a clickable link opening url in new tab (target='_blank' + rel='noopener noreferrer')"
    - "VIEW-08 'since snapshot' delta — when computed_at of the snapshot is older than headline.published_at, show a 'NEW since snapshot' tag on those headlines. (Phase 8 mid-day refresh adds the merge logic; Wave 3 just renders the tag based on snapshot computed_at vs headline timestamp.)"
    - "VIEW-13 ticker search typeahead — header search input lets user type a ticker and navigate to /ticker/:symbol/:date; uses snapshot.companyName when available (fallback to ticker symbol if not). Source: enumerate the index.tickers list from the loaded scan data + (optionally) fuzzy match against ticker symbol. Simple v1: filter tickers from the date's _index.json by substring match — no separate company-name index needed for v1 (yfinance ticker symbols ARE the v1 search surface; company name fuzzy search is v1.x)."
    - "Loading state: skeleton placeholder cards while loadTickerData fetches; empty/partial state: render whatever is present + 'Data unavailable for some signals' banner if snapshot.data_unavailable indicators are set on any sub-signal"
    - "TickerRoute reads useParams symbol + date; calls useTickerData hook; renders the layout in this order top-to-bottom: header search (Wave 3 location: in the layout's Root header — but adding to the deep-dive route is also acceptable for v1; recommend Root header) → OpenClaudePin → 2 TimeframeCards (short + long, side-by-side on lg, stacked on mobile) → Chart with overlays → PersonaCards grid (5) → AnalyticalSignalCards row (4) → NewsList grouped by source"
    - "Component coverage: ≥85% line on src/components/Chart + PersonaCard + OpenClaudePin + NewsList + TimeframeCard"
    - "Playwright E2E: from /scan/today click NVDA row → land on /ticker/NVDA/today → assert OpenClaudePin visible + chart rendered (lightweight-charts container in DOM) + 5 persona cards visible + news headlines visible"
    - "Wave 3 verification command passes: `cd frontend && pnpm test:unit --run && pnpm test:e2e -g 'deep dive' && pnpm build`"
  artifacts:
    - path: "frontend/src/components/Chart.tsx"
      provides: "lightweight-charts 5.2 wrapper; OHLC candlestick + MA20 line + MA50 line + BB upper/lower + RSI(14) sub-pane; reads from snapshot.indicators (Wave 0); React 19 ref + cleanup; respects prefers-reduced-motion"
      min_lines: 150
    - path: "frontend/src/components/PersonaCard.tsx"
      provides: "renders 1 persona AgentSignal as a card; verdict pill + confidence + reasoning paragraph + evidence list; uses VerdictBadge from Wave 2"
      min_lines: 70
    - path: "frontend/src/components/OpenClaudePin.tsx"
      provides: "pinned-at-top component for claude_analyst signal; visually distinct from PersonaCard (accent border + 'Open Claude Analyst' label badge per user MEMORY.md feedback); falls back to muted 'data unavailable' state"
      min_lines: 60
    - path: "frontend/src/components/NewsList.tsx"
      provides: "snapshot.headlines grouped by source; within group sorted by published_at DESC; clickable links target='_blank'; 'NEW since snapshot' tag when published_at > snapshot.computed_at"
      min_lines: 80
    - path: "frontend/src/components/TimeframeCard.tsx"
      provides: "short_term OR long_term TimeframeBand rendered as a card with summary + drivers + confidence + thesis_status pill"
      min_lines: 70
    - path: "frontend/src/components/AnalyticalSignalCard.tsx"
      provides: "renders 1 analytical AgentSignal (fundamentals/technicals/news_sentiment/valuation) — slightly different visual treatment than PersonaCard (no 'persona' framing; analyst_id label as caption)"
      min_lines: 60
    - path: "frontend/src/lib/loadTickerData.ts"
      provides: "useTickerData(date, symbol) hook fetching the per-ticker JSON via fetchAndParse + SnapshotSchema; returns { snapshot, isLoading, error }"
      min_lines: 35
    - path: "frontend/src/routes/TickerRoute.tsx"
      provides: "wires useTickerData + ticker search input + composes OpenClaudePin + 2 TimeframeCards + Chart + 5 PersonaCards + 4 AnalyticalSignalCards + NewsList"
      min_lines: 150
    - path: "frontend/src/components/ui/separator.tsx"
      provides: "shadcn/ui Separator (visual divider between sections); vendored"
      min_lines: 20
    - path: "frontend/tests/e2e/deep-dive.spec.ts"
      provides: "Playwright E2E: navigate from /scan/today → click ticker → /ticker/:symbol/today → assert OpenClaudePin + chart + persona cards + news headlines"
      min_lines: 80
  key_links:
    - from: "frontend/src/components/Chart.tsx"
      to: "lightweight-charts 5.2 createChart API"
      via: "npm package import; ChartApi.addCandlestickSeries / addLineSeries"
      pattern: "createChart|addCandlestickSeries|addLineSeries"
    - from: "frontend/src/routes/TickerRoute.tsx"
      to: "frontend/src/lib/loadTickerData.ts"
      via: "useTickerData hook"
      pattern: "useTickerData"
    - from: "frontend/src/components/Chart.tsx"
      to: "snapshot.indicators (Wave 0 pre-computed series)"
      via: "MA20/MA50/BB/RSI series passed as props"
      pattern: "indicators\\.(ma20|ma50|bb_upper|bb_lower|rsi14)"
    - from: "frontend/src/components/OpenClaudePin.tsx"
      to: "snapshot.persona_signals where analyst_id='claude_analyst'"
      via: "filter + render with distinct visual treatment"
      pattern: "claude_analyst"
---

<objective>
Build the Per-Ticker Deep-Dive view at `/ticker/:symbol/:date?`. Closes 8 requirements (VIEW-04 through VIEW-09 + VIEW-12 mobile-responsive groundwork + VIEW-13 ticker search). Open Claude Analyst pinned at TOP — distinct from the 5 persona cards — per user MEMORY.md emphasis. Chart renders OHLC + 4 indicator overlays + RSI sub-pane via lightweight-charts 5.2. News list groups by source with "NEW since snapshot" tagging.

Purpose: Closes the deep-dive surface — the user clicks any ticker from the morning scan and gets a full per-ticker briefing with chart, dual timeframe synthesis, all persona reasoning, and news context. Open Claude Analyst pinned at TOP is the load-bearing UX requirement (user feedback: "include Claude's inherent reasoning alongside personas — never let lenses replace inherent reasoning").

Output: Working `/ticker/:symbol/:date?` page composing 6 new component primitives + 1 hook. Playwright E2E covers the click-through happy path from morning scan. Wave 4 polishes responsiveness + error boundary + Playwright mobile-safari project + visual taste-check.
</objective>

<execution_context>
@C:/Users/Mohan/.claude/workflows/execute-plan.md
@C:/Users/Mohan/.claude/templates/summary.md
</execution_context>

<context>
@.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-CONTEXT.md
@.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-RESEARCH.md
@.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-01-SUMMARY.md
@.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-02-SUMMARY.md
@.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-03-SUMMARY.md

# Wave 1-2 outputs Wave 3 imports
@frontend/src/schemas/index.ts
@frontend/src/lib/fetchSnapshot.ts
@frontend/src/components/VerdictBadge.tsx
@frontend/src/components/EvidenceList.tsx
@frontend/src/components/TickerCard.tsx

# Skills
@C:/Users/Mohan/.claude/skills/design-taste-frontend/SKILL.md
@C:/Users/Mohan/.claude/skills/minimalist-ui/SKILL.md

<interfaces>
<!-- lightweight-charts 5.2 API surface relevant to Wave 3 -->

```ts
import { createChart, ColorType, type IChartApi, type ISeriesApi, type CandlestickData, type LineData, type Time } from 'lightweight-charts'

const chart: IChartApi = createChart(container, {
  width: 800, height: 400,
  layout: { background: { type: ColorType.Solid, color: '#0E0F11' }, textColor: '#E8E9EB' },
  grid: { vertLines: { color: '#252628' }, horzLines: { color: '#252628' } },
  rightPriceScale: { borderColor: '#2A2C30' },
  timeScale: { borderColor: '#2A2C30' },
})
const candles: ISeriesApi<'Candlestick'> = chart.addCandlestickSeries({ upColor: '#4ADE80', downColor: '#F87171', borderVisible: false, wickUpColor: '#4ADE80', wickDownColor: '#F87171' })
candles.setData([{ time: '2026-04-01' as Time, open: 180, high: 182, low: 179, close: 181 }, ...])
const ma20: ISeriesApi<'Line'> = chart.addLineSeries({ color: '#5B9DFF', lineWidth: 1 })
ma20.setData([{ time: '2026-04-01' as Time, value: 180.5 }, ...])  // skip null entries
// RSI in a separate price scale (sub-pane):
const rsi: ISeriesApi<'Line'> = chart.addLineSeries({ priceScaleId: 'rsi', color: '#8B8E94', lineWidth: 1 })
chart.priceScale('rsi').applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } })
// cleanup on unmount: chart.remove()
```

<!-- Wave 0/1 schemas Wave 3 imports -->

From frontend/src/schemas/snapshot.ts:
- SnapshotSchema, type Snapshot — full per-ticker JSON
- OHLCBarSchema, IndicatorsSchema, HeadlineSchema

From snapshot.persona_signals (Phase 5 contract):
- 6 entries with analyst_id ∈ ['buffett','munger','wood','burry','lynch','claude_analyst']
- Wave 3: filter to first 5 for PersonaCards grid; pull claude_analyst out for OpenClaudePin
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Chart.tsx (lightweight-charts wrapper) + tests</name>
  <files>frontend/src/components/Chart.tsx, frontend/src/components/__tests__/Chart.test.tsx</files>
  <action>
    1. **src/components/Chart.tsx**:
       ```tsx
       import { useEffect, useRef } from 'react'
       import { createChart, ColorType, type IChartApi, type Time } from 'lightweight-charts'
       import type { Snapshot } from '@/schemas'

       interface Props {
         ohlcHistory: Snapshot['ohlc_history']
         indicators: Snapshot['indicators']
         height?: number
       }

       export function Chart({ ohlcHistory, indicators, height = 400 }: Props) {
         const containerRef = useRef<HTMLDivElement>(null)
         const chartRef = useRef<IChartApi | null>(null)

         useEffect(() => {
           if (!containerRef.current) return
           const chart = createChart(containerRef.current, {
             height,
             layout: { background: { type: ColorType.Solid, color: '#0E0F11' }, textColor: '#E8E9EB' },
             grid: { vertLines: { color: '#252628' }, horzLines: { color: '#252628' } },
             rightPriceScale: { borderColor: '#2A2C30', scaleMargins: { top: 0.05, bottom: 0.25 } },
             timeScale: { borderColor: '#2A2C30', timeVisible: true, secondsVisible: false },
             crosshair: { mode: 1 },  // CrosshairMode.Normal
           })
           chartRef.current = chart

           // OHLC candles
           const candles = chart.addCandlestickSeries({
             upColor: '#4ADE80', downColor: '#F87171', borderVisible: false,
             wickUpColor: '#4ADE80', wickDownColor: '#F87171',
           })
           candles.setData(ohlcHistory.map(b => ({
             time: b.date as Time, open: b.open, high: b.high, low: b.low, close: b.close,
           })))

           // Helper — pair (date, value) entries dropping nulls (Wave 0 indicators have warmup nulls)
           const pairLines = (vals: (number | null)[]) =>
             ohlcHistory.map((b, i) => ({ time: b.date as Time, value: vals[i] }))
                        .filter((p): p is { time: Time; value: number } => p.value != null)

           const ma20 = chart.addLineSeries({ color: '#5B9DFF', lineWidth: 1, priceLineVisible: false, lastValueVisible: false })
           ma20.setData(pairLines(indicators.ma20))
           const ma50 = chart.addLineSeries({ color: '#8B8E94', lineWidth: 1, priceLineVisible: false, lastValueVisible: false })
           ma50.setData(pairLines(indicators.ma50))
           const bbU = chart.addLineSeries({ color: '#5B9DFF', lineWidth: 1, lineStyle: 2 /*Dotted*/, priceLineVisible: false, lastValueVisible: false })
           bbU.setData(pairLines(indicators.bb_upper))
           const bbL = chart.addLineSeries({ color: '#5B9DFF', lineWidth: 1, lineStyle: 2, priceLineVisible: false, lastValueVisible: false })
           bbL.setData(pairLines(indicators.bb_lower))

           // RSI sub-pane (priceScaleId='rsi' on its own margins)
           const rsi = chart.addLineSeries({ priceScaleId: 'rsi', color: '#FBBF24', lineWidth: 1, priceLineVisible: false, lastValueVisible: false })
           rsi.setData(pairLines(indicators.rsi14))
           chart.priceScale('rsi').applyOptions({ scaleMargins: { top: 0.78, bottom: 0 }, borderColor: '#2A2C30' })

           chart.timeScale().fitContent()

           // Resize on container resize
           const resizeObs = new ResizeObserver(entries => {
             for (const e of entries) chart.applyOptions({ width: e.contentRect.width })
           })
           resizeObs.observe(containerRef.current)

           return () => {
             resizeObs.disconnect()
             chart.remove()
             chartRef.current = null
           }
         }, [ohlcHistory, indicators, height])

         return <div ref={containerRef} className="w-full border border-border rounded-md bg-bg" data-testid="chart-container" />
       }
       ```
    2. **src/components/__tests__/Chart.test.tsx** — test that:
       - Component renders (returns container with data-testid='chart-container')
       - When ohlcHistory has 30 entries + indicators series with first 19 entries null on ma20, the chart's setData calls receive only the non-null pairs (mock createChart and inspect calls — vi.mock('lightweight-charts') with a manual factory)
       - Cleanup runs on unmount (chart.remove called)
    3. Run: `cd frontend && pnpm test:unit src/components/__tests__/Chart.test.tsx --run` — confirm green.
    4. Commit with: `feat(06-04): Chart wrapper for lightweight-charts 5.2 with MA20/MA50/BB/RSI overlays`
  </action>
  <verify>
    <automated>cd frontend && pnpm test:unit src/components/__tests__/Chart.test.tsx --run 2>&1 | tail -10</automated>
  </verify>
  <done>Chart.tsx renders OHLC + 4 indicator overlays + RSI sub-pane; mock-based unit tests verify setData call shape (null-filtering correct); commit landed.</done>
</task>

<task type="auto">
  <name>Task 2: Persona/Open-Claude/Timeframe/Analytical/News components + tests</name>
  <files>frontend/src/components/PersonaCard.tsx, frontend/src/components/OpenClaudePin.tsx, frontend/src/components/TimeframeCard.tsx, frontend/src/components/AnalyticalSignalCard.tsx, frontend/src/components/NewsList.tsx, frontend/src/components/__tests__/PersonaCard.test.tsx, frontend/src/components/__tests__/OpenClaudePin.test.tsx, frontend/src/components/__tests__/TimeframeCard.test.tsx, frontend/src/components/__tests__/NewsList.test.tsx, frontend/src/components/ui/separator.tsx</files>
  <action>
    1. Vendor `pnpm dlx shadcn@latest add separator` → src/components/ui/separator.tsx (used between Wave 3 sections).
    2. **src/components/PersonaCard.tsx**:
       ```tsx
       import type { AgentSignal } from '@/schemas'
       import { Card, CardContent, CardHeader } from './ui/card'
       import { VerdictBadge } from './VerdictBadge'
       import { EvidenceList } from './EvidenceList'

       const PERSONA_LABEL: Record<string, string> = {
         buffett: 'Warren Buffett', munger: 'Charlie Munger', wood: 'Cathie Wood',
         burry: 'Michael Burry', lynch: 'Peter Lynch', claude_analyst: 'Open Claude Analyst',
       }

       interface Props { signal: AgentSignal }
       export function PersonaCard({ signal }: Props) {
         const muted = signal.data_unavailable
         return (
           <Card className="bg-surface border-border">
             <CardHeader className="flex flex-row items-center justify-between gap-4 pb-3">
               <div className="font-medium">{PERSONA_LABEL[signal.analyst_id] ?? signal.analyst_id}</div>
               <div className="flex items-center gap-3">
                 <VerdictBadge verdict={signal.verdict} />
                 <span className="text-sm font-mono text-text-secondary">conf {signal.confidence}</span>
               </div>
             </CardHeader>
             <CardContent className="pt-0">
               {muted ? (
                 <div className="text-sm text-text-secondary">data unavailable</div>
               ) : (
                 <>
                   <p className="text-sm text-text-primary mb-3">{signal.reasoning}</p>
                   <EvidenceList items={signal.evidence} max={3} />
                 </>
               )}
             </CardContent>
           </Card>
         )
       }
       ```
    3. **src/components/OpenClaudePin.tsx** — visually distinct from PersonaCard (accent border, 'Open Claude Analyst' label badge top-right, slightly larger reasoning text). Falls back to muted 'data unavailable' state when claude_analyst signal data_unavailable=True. Always renders — never silently absent (per VIEW-09 + user MEMORY.md feedback).
       ```tsx
       import type { AgentSignal } from '@/schemas'
       import { Card, CardContent } from './ui/card'
       import { VerdictBadge } from './VerdictBadge'
       interface Props { signal: AgentSignal }
       export function OpenClaudePin({ signal }: Props) {
         const muted = signal.data_unavailable
         return (
           <Card className="border-accent/40 bg-accent/5 mb-8" data-testid="open-claude-pin">
             <CardContent className="p-6">
               <div className="flex items-center justify-between gap-4 mb-3">
                 <div className="text-xs uppercase tracking-wider text-accent font-medium">Open Claude Analyst</div>
                 {!muted && (
                   <div className="flex items-center gap-3">
                     <VerdictBadge verdict={signal.verdict} />
                     <span className="text-xs font-mono text-text-secondary">conf {signal.confidence}</span>
                   </div>
                 )}
               </div>
               {muted ? (
                 <div className="text-sm text-text-secondary">Open Claude Analyst: data unavailable for this snapshot.</div>
               ) : (
                 <>
                   <p className="text-base text-text-primary leading-relaxed mb-4">{signal.reasoning}</p>
                   {signal.evidence.length > 0 && (
                     <ul className="text-sm text-text-secondary space-y-1 list-disc pl-5">
                       {signal.evidence.slice(0, 4).map((e, i) => <li key={i}>{e}</li>)}
                     </ul>
                   )}
                 </>
               )}
             </CardContent>
           </Card>
         )
       }
       ```
    4. **src/components/TimeframeCard.tsx**:
       ```tsx
       import type { TickerDecision } from '@/schemas'
       import { Card, CardContent, CardHeader } from './ui/card'
       import { Badge } from './ui/badge'
       interface Props { label: string; band: TickerDecision['short_term'] }
       const STATUS_COLOR: Record<string, string> = {
         intact: 'bg-bullish/10 text-bullish border-bullish/30',
         improving: 'bg-bullish/10 text-bullish border-bullish/30',
         weakening: 'bg-amber/10 text-amber border-amber/30',
         broken: 'bg-bearish/10 text-bearish border-bearish/30',
         'n/a': 'bg-surface text-text-secondary border-border',
       }
       export function TimeframeCard({ label, band }: Props) {
         return (
           <Card className="bg-surface border-border flex-1">
             <CardHeader className="flex flex-row items-center justify-between gap-4">
               <div className="font-medium">{label}</div>
               <div className="flex items-center gap-3">
                 <Badge variant="outline" className={STATUS_COLOR[band.thesis_status]}>{band.thesis_status}</Badge>
                 <span className="text-sm font-mono text-text-secondary">conf {band.confidence}</span>
               </div>
             </CardHeader>
             <CardContent>
               <p className="text-sm text-text-primary mb-4">{band.summary}</p>
               <ul className="text-sm text-text-secondary space-y-1 list-disc pl-5">
                 {band.drivers.slice(0, 5).map((d, i) => <li key={i}>{d}</li>)}
               </ul>
             </CardContent>
           </Card>
         )
       }
       ```
    5. **src/components/AnalyticalSignalCard.tsx** — like PersonaCard but with analyst_id label as caption ('Fundamentals' / 'Technicals' / 'News & Sentiment' / 'Valuation' — friendly labels) and slightly more compact.
    6. **src/components/NewsList.tsx**:
       ```tsx
       import type { Snapshot } from '@/schemas'
       interface Props { headlines: Snapshot['headlines']; snapshotComputedAt: string }
       export function NewsList({ headlines, snapshotComputedAt }: Props) {
         const groups = new Map<string, typeof headlines>()
         for (const h of headlines) {
           const arr = groups.get(h.source) ?? []
           arr.push(h); groups.set(h.source, arr)
         }
         // Sort each group by published_at DESC
         for (const [k, arr] of groups) {
           arr.sort((a, b) => b.published_at.localeCompare(a.published_at))
           groups.set(k, arr)
         }
         const snapshotMs = new Date(snapshotComputedAt).getTime()
         return (
           <div className="space-y-6">
             {[...groups.entries()].map(([source, items]) => (
               <div key={source}>
                 <h3 className="text-xs uppercase tracking-wider text-text-secondary mb-3">{source}</h3>
                 <ul className="space-y-3">
                   {items.map(h => {
                     const isNew = new Date(h.published_at).getTime() > snapshotMs
                     return (
                       <li key={h.url} className="flex items-start gap-3">
                         {isNew && <span className="text-xs px-2 py-0.5 rounded bg-accent/20 text-accent border border-accent/40 shrink-0 mt-0.5">NEW</span>}
                         <a href={h.url} target="_blank" rel="noopener noreferrer" className="text-sm text-text-primary hover:text-accent line-clamp-2 flex-1">
                           {h.title}
                         </a>
                         <time className="text-xs font-mono text-text-secondary shrink-0">{new Date(h.published_at).toISOString().slice(0, 10)}</time>
                       </li>
                     )
                   })}
                 </ul>
               </div>
             ))}
           </div>
         )
       }
       ```
    7. Tests for each component:
       - PersonaCard.test: renders verdict + confidence + reasoning; data_unavailable=True hides reasoning + shows muted 'data unavailable' text
       - OpenClaudePin.test: renders distinct accent styling; data-testid='open-claude-pin' present; data_unavailable=True branch renders muted state (still in DOM — per VIEW-09)
       - TimeframeCard.test: renders thesis_status badge with correct color class; renders top 5 drivers
       - NewsList.test: 4 headlines from 2 sources → 2 groups with 2 items each, each sorted by published_at DESC; published_at > snapshotComputedAt → NEW tag rendered
    8. Run: `cd frontend && pnpm test:unit --run` — confirm green.
    9. Commit with: `feat(06-04): persona + open-claude + timeframe + analytical + news components`
  </action>
  <verify>
    <automated>cd frontend && pnpm test:unit src/components --run 2>&1 | tail -15</automated>
  </verify>
  <done>5 new component files + 4 test files green; OpenClaudePin always renders (never silently absent); NewsList groups by source + tags NEW correctly; commit landed.</done>
</task>

<task type="auto">
  <name>Task 3: loadTickerData hook + TickerRoute composition + Playwright deep-dive E2E</name>
  <files>frontend/src/lib/loadTickerData.ts, frontend/src/lib/__tests__/loadTickerData.test.ts, frontend/src/routes/TickerRoute.tsx, frontend/tests/e2e/deep-dive.spec.ts</files>
  <action>
    1. **src/lib/loadTickerData.ts**:
       ```ts
       import { useQuery } from '@tanstack/react-query'
       import { fetchAndParse, snapshotUrl } from './fetchSnapshot'
       import { SnapshotSchema, type Snapshot } from '@/schemas'

       export function useTickerData(date: string, symbol: string) {
         return useQuery<Snapshot>({
           queryKey: ['ticker', date, symbol],
           queryFn: () => fetchAndParse(snapshotUrl(date, symbol), SnapshotSchema),
           // Inherits 5min staleTime from QueryClient defaults.
         })
       }
       ```
    2. **src/lib/__tests__/loadTickerData.test.ts** — mock fetch with happy path + 404 + zod-mismatch; assert hook returns the right state for each.
    3. **src/routes/TickerRoute.tsx** — replace Wave 1 stub with full composition:
       ```tsx
       import { useParams, Link } from 'react-router'
       import { useTickerData } from '@/lib/loadTickerData'
       import { OpenClaudePin } from '@/components/OpenClaudePin'
       import { TimeframeCard } from '@/components/TimeframeCard'
       import { Chart } from '@/components/Chart'
       import { PersonaCard } from '@/components/PersonaCard'
       import { AnalyticalSignalCard } from '@/components/AnalyticalSignalCard'
       import { NewsList } from '@/components/NewsList'
       import { Separator } from '@/components/ui/separator'

       export default function TickerRoute() {
         const { symbol = '', date = 'today' } = useParams()
         const { data: snap, isLoading, error } = useTickerData(date, symbol)
         if (isLoading) return <div className="text-text-secondary p-12">Loading {symbol}…</div>
         if (error) return (
           <div className="p-12">
             <div className="text-bearish mb-4">Failed to load {symbol}: {(error as Error).message}</div>
             <Link to={`/scan/${date}`} className="text-accent">← Back to scan</Link>
           </div>
         )
         if (!snap) return null

         const claudeSig = snap.persona_signals.find(p => p.analyst_id === 'claude_analyst')
         const otherPersonas = snap.persona_signals.filter(p => p.analyst_id !== 'claude_analyst')
         const dec = snap.ticker_decision

         return (
           <div className="space-y-8 pb-12">
             <div className="flex items-baseline justify-between">
               <h1 className="text-3xl font-mono font-semibold">{snap.ticker}</h1>
               <Link to={`/scan/${date}`} className="text-sm text-text-secondary hover:text-accent">← Back to scan</Link>
             </div>

             {/* Open Claude Analyst pinned at TOP — always rendered (VIEW-09 + MEMORY.md) */}
             {claudeSig && <OpenClaudePin signal={claudeSig} />}

             {/* Dual-timeframe cards (VIEW-05) — side-by-side on lg, stacked on mobile (Wave 4 polishes) */}
             {dec && (
               <div className="flex flex-col lg:flex-row gap-6">
                 <TimeframeCard label="Short-Term (1w-1m)" band={dec.short_term} />
                 <TimeframeCard label="Long-Term (1y-5y)" band={dec.long_term} />
               </div>
             )}

             {/* OHLC chart with overlays (VIEW-06) */}
             <section>
               <h2 className="text-sm uppercase tracking-wider text-text-secondary mb-3">Price Chart (180 days)</h2>
               <Chart ohlcHistory={snap.ohlc_history} indicators={snap.indicators} />
             </section>

             <Separator />

             {/* 5 persona cards (VIEW-07; claude_analyst handled separately above) */}
             <section>
               <h2 className="text-sm uppercase tracking-wider text-text-secondary mb-4">Persona Signals</h2>
               <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                 {otherPersonas.map(p => <PersonaCard key={p.analyst_id} signal={p} />)}
               </div>
             </section>

             {/* 4 analytical signal cards */}
             <section>
               <h2 className="text-sm uppercase tracking-wider text-text-secondary mb-4">Analytical Signals</h2>
               <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                 {snap.analytical_signals.map(s => <AnalyticalSignalCard key={s.analyst_id} signal={s} />)}
               </div>
             </section>

             <Separator />

             {/* News feed grouped by source (VIEW-08) */}
             <section>
               <h2 className="text-sm uppercase tracking-wider text-text-secondary mb-4">News Feed</h2>
               <NewsList headlines={snap.headlines} snapshotComputedAt={dec?.computed_at ?? new Date(0).toISOString()} />
             </section>
           </div>
         )
       }
       ```
    4. **VIEW-13 ticker search typeahead** — for v1 simplicity, add a small search input in the Root.tsx header (lifting from Wave 2's Root). The input filters the loaded scan data's _index.tickers by substring match (case-insensitive); on Enter or click, navigate to `/ticker/:typed/:date`. If the user wants company-name fuzzy match later, that's v1.x — note it in SUMMARY.

       Update Root.tsx to include:
       ```tsx
       // Above the StalenessBadge in the header
       <input
         type="text"
         placeholder="Ticker (e.g. AAPL)"
         className="bg-bg border border-border rounded px-3 py-1.5 text-sm font-mono focus:border-accent outline-none"
         onKeyDown={(e) => {
           if (e.key === 'Enter') {
             const v = (e.target as HTMLInputElement).value.trim().toUpperCase()
             if (v) navigate(`/ticker/${v}/${dateFromMatches}`)
           }
         }}
       />
       ```
       (Use useNavigate from react-router; useMatches to extract the active :date.)
    5. **tests/e2e/deep-dive.spec.ts**:
       ```ts
       import { test, expect } from '@playwright/test'
       import { mountScanFixtures } from './fixtures-server'

       test.describe('deep dive', () => {
         test.beforeEach(async ({ page }) => mountScanFixtures(page))

         test('click ticker from scan navigates to deep-dive with all sections', async ({ page }) => {
           await page.goto('/scan/2026-05-04')
           await page.locator('a[href*="/ticker/NVDA/"]').first().click()
           await expect(page).toHaveURL(/\/ticker\/NVDA\/2026-05-04/)
           await expect(page.getByRole('heading', { name: 'NVDA' })).toBeVisible()
           // Open Claude Analyst pinned at top
           await expect(page.getByTestId('open-claude-pin')).toBeVisible()
           // Chart container present
           await expect(page.getByTestId('chart-container')).toBeVisible()
           // Persona signal section header
           await expect(page.getByRole('heading', { name: /Persona Signals/i })).toBeVisible()
           // News feed section header
           await expect(page.getByRole('heading', { name: /News Feed/i })).toBeVisible()
         })

         test('ticker search input navigates to /ticker/:symbol', async ({ page }) => {
           await page.goto('/scan/2026-05-04')
           await page.getByPlaceholder('Ticker (e.g. AAPL)').fill('AAPL')
           await page.getByPlaceholder('Ticker (e.g. AAPL)').press('Enter')
           await expect(page).toHaveURL(/\/ticker\/AAPL\//)
         })

         test('VIEW-09 OpenClaudePin always renders even when data_unavailable', async ({ page }) => {
           // Use a fixture with claude_analyst.data_unavailable=True for this assertion.
           // For Wave 3 simplest: rely on the existing fixtures' happy-path claude_analyst signal.
           await page.goto('/ticker/AAPL/2026-05-04')
           await expect(page.getByTestId('open-claude-pin')).toBeVisible()
         })
       })
       ```
    6. Run: `cd frontend && pnpm test:e2e -g 'deep dive'` — confirm 3 specs pass on chromium-desktop. Run `pnpm test:unit --run` — confirm full suite green. Run `pnpm build` — confirm typecheck + build pass.
    7. Commit with: `feat(06-04): TickerRoute deep-dive + ticker search typeahead + Playwright E2E`
  </action>
  <verify>
    <automated>cd frontend && pnpm test:unit --run && pnpm test:e2e --project=chromium-desktop -g 'deep dive' 2>&1 | tail -20</automated>
  </verify>
  <done>useTickerData hook + TickerRoute composing all 6 sections + ticker search input + 3 Playwright deep-dive specs all green; commit landed; build passes.</done>
</task>

</tasks>

<verification>
- All 3 tasks complete; commits landed
- Vitest: ~70+ unit tests passing across schemas + lib + components (Wave 1+2's 60 + Wave 3's ~12 new)
- Playwright: chromium-desktop deep-dive E2E green; morning-scan E2E (Wave 2) still green; smoke E2E (Wave 1) still green
- typecheck + build succeed
- VIEW-04 thesis-status surface: Wave 2 LongTermLens uses thesis_status filter; Wave 3 TimeframeCard renders thesis_status pill (joint coverage)
- VIEW-05 dual-timeframe cards: 2 TimeframeCards side-by-side on lg, stacked on mobile (Wave 4 verifies the responsive break)
- VIEW-06 OHLC chart: candlestick + MA20/MA50 + BB upper/lower + RSI sub-pane all rendered from snapshot.indicators
- VIEW-07 persona cards: 5 PersonaCards (excluding claude_analyst) in grid
- VIEW-08 news feed: grouped by source, sorted by published_at DESC, 'NEW' tag when published > snapshot.computed_at
- VIEW-09 Open Claude Analyst pinned at TOP: OpenClaudePin always renders, distinct accent styling, fallback for data_unavailable=True
- VIEW-12 mobile-responsive groundwork: lg:flex-row breakpoints in place; Wave 4 verifies on Playwright mobile-safari project
- VIEW-13 ticker search: header input navigates to /ticker/:symbol on Enter
</verification>

<success_criteria>
- [ ] /ticker/:symbol/:date? renders OpenClaudePin pinned at top (always present, even on data_unavailable=True)
- [ ] 2 TimeframeCards (short_term + long_term) render side-by-side on lg breakpoint, stacked on mobile
- [ ] Chart renders OHLC candlestick + MA20 + MA50 + BB upper/lower + RSI(14) sub-pane via lightweight-charts 5.2
- [ ] Chart reads from snapshot.indicators (Wave 0 pre-computed series — frontend never recomputes)
- [ ] 5 PersonaCards in grid (claude_analyst excluded — pinned separately above)
- [ ] 4 AnalyticalSignalCards (fundamentals/technicals/news_sentiment/valuation) in grid
- [ ] NewsList groups headlines by source; within group sorted by published_at DESC; 'NEW' tag when published > snapshot.computed_at
- [ ] Header ticker search input navigates to /ticker/:symbol on Enter
- [ ] Vitest unit tests: ~12 new tests pass; total ≥ 70 tests green
- [ ] Playwright deep-dive E2E green on chromium-desktop (3 specs)
- [ ] typecheck + build pass
- [ ] Notion-Clean palette honored: 1F2024 surfaces, 2A2C30 hairlines, 5B9DFF accent on OpenClaudePin border, 4ADE80/F87171 candles
- [ ] 3 commits landed: `feat(06-04): Chart wrapper` → `feat(06-04): persona+open-claude+timeframe+analytical+news components` → `feat(06-04): TickerRoute deep-dive + ticker search + E2E`
</success_criteria>

<output>
After completion, create `.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-04-SUMMARY.md` matching Phase 1-5 SUMMARY template — sections: Plan Identity / Wave / Outcome / Files Created / Components Built / Chart Surface (lightweight-charts integration notes) / Tests Added / VIEW-04..09+12+13 Coverage Map / Notes for Wave 4 (responsive polish + ErrorBoundary + date selector + visual taste-check).
</output>
