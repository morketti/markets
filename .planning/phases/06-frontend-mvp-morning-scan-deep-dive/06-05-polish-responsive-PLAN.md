---
phase: 06-frontend-mvp-morning-scan-deep-dive
plan: 05
type: execute
wave: 4
depends_on: [06-01, 06-02, 06-03, 06-04]
files_modified:
  - frontend/src/components/ErrorBoundary.tsx
  - frontend/src/components/DateSelector.tsx
  - frontend/src/lib/loadDates.ts
  - frontend/src/routes/Root.tsx
  - frontend/src/routes/ScanRoute.tsx
  - frontend/src/routes/TickerRoute.tsx
  - frontend/src/components/Chart.tsx
  - frontend/src/components/__tests__/ErrorBoundary.test.tsx
  - frontend/src/components/__tests__/DateSelector.test.tsx
  - frontend/src/lib/__tests__/loadDates.test.ts
  - frontend/tests/e2e/responsive.spec.ts
  - frontend/tests/e2e/error-boundary.spec.ts
  - frontend/tests/e2e/full-flow.spec.ts
  - frontend/tests/fixtures/scan/AAPL-bad-version.json
  - frontend/src/index.css
autonomous: true
requirements: [VIEW-12, VIEW-14, VIEW-15]
gap_closure: false
tags: [phase-6, wave-4, polish, responsive, error-boundary, date-selector, playwright-mobile, visual-taste-check]

must_haves:
  truths:
    - "VIEW-12 mobile-responsive: morning scan AND deep-dive pass Playwright mobile-safari project (devices iPhone 14) AND mobile-chrome project (devices Pixel 7) — no horizontal scroll, lens tabs are tap-friendly (≥44px hit area), chart pans/pinches, table-rows-to-card-stack on narrow screens"
    - "VIEW-14 date selector: header DateSelector.tsx reads data/_dates.json (Wave 0 file) via loadDates hook; renders a dropdown listing all available dates; selecting one navigates the URL (/scan/{date} or /ticker/:symbol/{date}); preserves whatever lens or symbol the user had active"
    - "VIEW-15 zod-mismatch error boundary: ErrorBoundary.tsx catches SchemaMismatchError + FetchNotFoundError and renders explicit error states per CONTEXT.md UNIFORM RULE (NOT a crash):"
    - "  - SchemaMismatchError: 'Schema version mismatch — frontend v{frontend_v}, snapshot v{snapshot_v}. Re-run today's routine or upgrade frontend.' surfacing both versions"
    - "  - FetchNotFoundError on snapshot: 'No snapshot for {date}. Latest available: {latest from _dates.json}.' with link to latest"
    - "  - FetchNotFoundError on per-ticker: '{ticker} not in {date} run. {reason from _status.json.failed_tickers/skipped_tickers if present}'"
    - "Mobile responsive breakpoints: deep-dive 2 TimeframeCards stack on <lg (1024px); persona-card grid is 1-col on <md (768px), 2-col on md, 3-col on xl (1280px); ticker-card rows in scan lenses collapse mono-ticker into card header on <sm (640px)"
    - "Chart.tsx mobile: respects viewport width; touch-friendly pinch-zoom on chart (lightweight-charts 5.2 supports this natively — verify by setting handleScroll/handleScale options to true; test on mobile-safari Playwright project)"
    - "Visual taste-check pass: assistant runs through `/scan/today` + `/ticker/AAPL/today` on chromium-desktop AND mobile-safari; cross-references against CONTEXT.md Notion-Clean spec (palette + spacing + typography); records any drift in the SUMMARY (does NOT auto-fix unless trivial — leaves user-facing taste decisions for human verification)"
    - "Playwright full-flow E2E (frontend/tests/e2e/full-flow.spec.ts): single test that runs the entire happy path top-to-bottom on chromium-desktop AND mobile-safari: open /scan/today → see staleness badge → switch lenses (3 of them) → click ticker → see deep-dive (chart + persona cards + news) → use date selector → return to scan; both projects pass"
    - "Coverage gates honored: ≥90% line / ≥85% branch on src/schemas/ + src/lib/; components measured but not gated (CONTEXT.md says 'components are RTL-tested for behavior, not coverage')"
    - "Wave 4 verification command passes: `cd frontend && pnpm test:unit --run && pnpm test:e2e && pnpm build` — all green; Playwright runs all 3 projects (chromium-desktop + mobile-safari + mobile-chrome) by default per playwright.config.ts"
    - "Final test suite at end of Phase 6: ~80+ vitest unit/component tests + ~10+ Playwright E2E across 3 projects; full suite (`pnpm test:unit --run && pnpm test:e2e`) completes in <90s total"
  artifacts:
    - path: "frontend/src/components/ErrorBoundary.tsx"
      provides: "React 19 error boundary catching SchemaMismatchError + FetchNotFoundError; renders UNIFORM RULE error states per CONTEXT.md; falls back to generic 'Something went wrong' for unknown errors"
      min_lines: 90
    - path: "frontend/src/components/DateSelector.tsx"
      provides: "header dropdown reading data/_dates.json; selecting a date navigates with active lens/symbol preserved"
      min_lines: 60
    - path: "frontend/src/lib/loadDates.ts"
      provides: "useDates() hook fetching DatesIndexSchema from data/_dates.json; cached 5min via TanStack default"
      min_lines: 25
    - path: "frontend/src/routes/Root.tsx"
      provides: "wraps RouterProvider Outlet in ErrorBoundary; adds DateSelector to header next to StalenessBadge + ticker-search input"
      min_lines: 60
    - path: "frontend/src/routes/ScanRoute.tsx"
      provides: "responsive grid breakpoints applied to lens content; mobile-friendly tab layout (full-width on <sm)"
      min_lines: 90
    - path: "frontend/src/routes/TickerRoute.tsx"
      provides: "responsive breakpoints on TimeframeCard pair + persona-card grid + analytical grid; chart container scales to viewport"
      min_lines: 160
    - path: "frontend/src/components/Chart.tsx"
      provides: "Wave 4 polish — handleScroll: true, handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true }; verify mobile touch behavior with Playwright"
      min_lines: 160
    - path: "frontend/tests/e2e/responsive.spec.ts"
      provides: "mobile-safari + mobile-chrome project tests: assert lens tabs full-width on iPhone, no horizontal scroll, deep-dive timeframe cards stack vertically"
      min_lines: 60
    - path: "frontend/tests/e2e/error-boundary.spec.ts"
      provides: "tests for: schema mismatch (mock per-ticker JSON with schema_version=1) → user-friendly error renders both versions; ticker 404 → 'not in today's run' message"
      min_lines: 50
    - path: "frontend/tests/e2e/full-flow.spec.ts"
      provides: "top-to-bottom happy-path E2E: scan → switch lens → click ticker → deep-dive → date selector; runs on all 3 Playwright projects"
      min_lines: 60
    - path: "frontend/tests/fixtures/scan/AAPL-bad-version.json"
      provides: "fixture with schema_version=1 to test ErrorBoundary's schema-mismatch path"
      min_lines: 10
    - path: "frontend/src/components/__tests__/ErrorBoundary.test.tsx"
      provides: "vitest tests: renders schema-mismatch UI, renders 404 UI, falls back to generic on unknown error"
      min_lines: 60
    - path: "frontend/src/components/__tests__/DateSelector.test.tsx"
      provides: "renders dates list, selecting date navigates with preserved lens/symbol param"
      min_lines: 50
    - path: "frontend/src/lib/__tests__/loadDates.test.ts"
      provides: "happy path + 404 (data/_dates.json missing) → empty list fallback"
      min_lines: 30
  key_links:
    - from: "frontend/src/components/ErrorBoundary.tsx"
      to: "SchemaMismatchError + FetchNotFoundError from fetchSnapshot.ts"
      via: "instanceof checks in componentDidCatch"
      pattern: "SchemaMismatchError|FetchNotFoundError"
    - from: "frontend/src/components/DateSelector.tsx"
      to: "data/_dates.json (Wave 0 file)"
      via: "useDates() → DatesIndexSchema"
      pattern: "useDates|DatesIndexSchema|_dates\\.json"
    - from: "frontend/src/routes/Root.tsx"
      to: "frontend/src/components/ErrorBoundary.tsx"
      via: "Wraps Outlet in <ErrorBoundary>"
      pattern: "<ErrorBoundary>"
---

<objective>
Wave 4 polishes the Phase 6 frontend to release-ready: mobile-responsive breakpoints across all routes, ErrorBoundary catching SchemaMismatchError + FetchNotFoundError per CONTEXT.md UNIFORM RULE, DateSelector reading data/_dates.json (Wave 0 file) for VIEW-14, full-flow Playwright E2E running on 3 projects (chromium-desktop + mobile-safari + mobile-chrome), and a final visual taste-check pass against the locked Notion-Clean spec.

Purpose: Close the 3 remaining VIEW requirements (VIEW-12 mobile-responsive, VIEW-14 date selector, VIEW-15 zod error boundary). Lock the testing surface so Phase 7 (Decision-Support View) and Phase 8 (Mid-Day Refresh) can build on a stable, regression-protected frontend.

Output: A release-ready frontend that passes all 3 Playwright projects, has explicit error states for every documented failure mode (CONTEXT.md UNIFORM RULE), and has a final visual taste-check report stored in the SUMMARY for the user to manually verify on real devices (manual-only verifications are documented in VALIDATION.md).
</objective>

<execution_context>
@C:/Users/Mohan/.claude/workflows/execute-plan.md
@C:/Users/Mohan/.claude/templates/summary.md
</execution_context>

<context>
@.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-CONTEXT.md
@.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-VALIDATION.md
@.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-01-SUMMARY.md
@.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-02-SUMMARY.md
@.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-03-SUMMARY.md
@.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-04-SUMMARY.md

# Wave 1-3 outputs Wave 4 imports/extends
@frontend/src/lib/fetchSnapshot.ts
@frontend/src/schemas/dates_index.ts
@frontend/src/routes/Root.tsx
@frontend/src/routes/ScanRoute.tsx
@frontend/src/routes/TickerRoute.tsx
@frontend/src/components/Chart.tsx

# Skills relevant to Wave 4 visual + responsive polish
@C:/Users/Mohan/.claude/skills/design-taste-frontend/SKILL.md
@C:/Users/Mohan/.claude/skills/minimalist-ui/SKILL.md
@C:/Users/Mohan/.claude/skills/high-end-visual-design/SKILL.md
@C:/Users/Mohan/.claude/skills/impeccable/SKILL.md

<interfaces>
<!-- React 19 Error Boundary pattern (still class component in v19) -->
```tsx
import { Component, type ReactNode, type ErrorInfo } from 'react'
import { SchemaMismatchError, FetchNotFoundError } from '@/lib/fetchSnapshot'

interface Props { children: ReactNode }
interface State { error: Error | null }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }
  static getDerivedStateFromError(error: Error): State { return { error } }
  componentDidCatch(error: Error, info: ErrorInfo) { console.error('ErrorBoundary caught:', error, info) }
  render() {
    if (this.state.error) {
      const e = this.state.error
      if (e instanceof SchemaMismatchError) return <SchemaMismatchView error={e} />
      if (e instanceof FetchNotFoundError) return <NotFoundView error={e} />
      return <GenericErrorView error={e} />
    }
    return this.props.children
  }
}
```

<!-- Wave 0 file the DateSelector reads -->
data/_dates.json: { schema_version: 1, dates_available: ['2026-04-30', '2026-05-01', ...], updated_at: ISO }
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: ErrorBoundary + DateSelector + loadDates hook</name>
  <files>frontend/src/components/ErrorBoundary.tsx, frontend/src/components/DateSelector.tsx, frontend/src/lib/loadDates.ts, frontend/src/components/__tests__/ErrorBoundary.test.tsx, frontend/src/components/__tests__/DateSelector.test.tsx, frontend/src/lib/__tests__/loadDates.test.ts, frontend/tests/fixtures/scan/AAPL-bad-version.json, frontend/src/routes/Root.tsx</files>
  <action>
    1. **src/components/ErrorBoundary.tsx** — React 19 class-component error boundary. Catches errors thrown during render. The TanStack Query useQuery throws asynchronously into render via the `throw new Error(...)` pattern when the query's error state is consumed — but for cleaner UX, use the `useQuery({ throwOnError: true })` option in Wave 4 to make errors propagate to the boundary (instead of returning the error to consumers). Update useScanData + useTickerData + useDates to use `throwOnError: (error) => error instanceof SchemaMismatchError || error instanceof FetchNotFoundError`.

       Render branches:
       - **SchemaMismatchView** (e instanceof SchemaMismatchError): "Schema version mismatch — frontend expects v2, snapshot is older. Re-run today's routine or upgrade frontend." Include link to repo's README. Surface both versions if extractable from the zodError (the `expected` value of the schema_version field on the literal mismatch).
       - **NotFoundView** (e instanceof FetchNotFoundError): match URL pattern to determine context — if it's a per-ticker URL, "{ticker} not in run for {date}." with Link to /scan/{date}. If it's a snapshot URL (just /_index.json or /_status.json), "No snapshot for {date}. Latest available: {latest from useDates}." with Link to /scan/{latest}.
       - **GenericErrorView**: muted "Something went wrong: {error.message}. <Link to /scan/today>Reload</Link>"

       Provide a "Reset" button on each branch that calls `this.setState({ error: null })` and triggers a query refetch (via QueryClient.resetQueries from useQueryClient — pass through context).

    2. **src/lib/loadDates.ts**:
       ```ts
       import { useQuery } from '@tanstack/react-query'
       import { fetchAndParse, datesUrl } from './fetchSnapshot'
       import { DatesIndexSchema, type DatesIndex } from '@/schemas/dates_index'

       export function useDates() {
         return useQuery<DatesIndex>({
           queryKey: ['dates'],
           queryFn: () => fetchAndParse(datesUrl(), DatesIndexSchema),
           staleTime: 60 * 1000,  // 1min — dates list is small + cheap to refetch
           // Don't throw on 404 — empty list fallback for first-deploy scenario
         })
       }
       ```

    3. **src/components/DateSelector.tsx**:
       ```tsx
       import { useDates } from '@/lib/loadDates'
       import { useNavigate, useParams, useLocation } from 'react-router'

       export function DateSelector() {
         const { data, isLoading } = useDates()
         const navigate = useNavigate()
         const params = useParams()
         const location = useLocation()
         if (isLoading || !data) return null

         const currentDate = params.date ?? 'today'
         const onChange = (newDate: string) => {
           // Preserve route shape (scan vs ticker) and lens query param
           if (location.pathname.startsWith('/ticker/')) {
             const symbol = params.symbol
             navigate(`/ticker/${symbol}/${newDate}${location.search}`)
           } else {
             navigate(`/scan/${newDate}${location.search}`)
           }
         }

         return (
           <select
             value={currentDate}
             onChange={(e) => onChange(e.target.value)}
             className="bg-bg border border-border rounded px-3 py-1.5 text-sm font-mono focus:border-accent outline-none"
             data-testid="date-selector"
           >
             <option value="today">today</option>
             {[...data.dates_available].reverse().map(d => <option key={d} value={d}>{d}</option>)}
           </select>
         )
       }
       ```
       (For v1, native `<select>` is fine — Notion-Clean style; user can upgrade to shadcn/ui Select in v1.x if desired. The native control is mobile-friendly out of the box and doesn't add layout shifts.)

    4. **src/routes/Root.tsx** — extend Wave 2/3 Root to wrap Outlet in ErrorBoundary AND add DateSelector to the header (next to ticker-search input + StalenessBadge):
       ```tsx
       <header className="border-b border-border px-6 py-4 flex items-center justify-between gap-4">
         <Link to="/scan/today" className="text-sm font-mono uppercase tracking-wider">MARKETS</Link>
         <div className="flex items-center gap-4">
           <DateSelector />
           <input ... ticker search input ... />
           <StalenessBadge ... />
         </div>
       </header>
       <main className="px-6 py-8 mx-auto max-w-7xl">
         <ErrorBoundary>
           <Outlet />
         </ErrorBoundary>
       </main>
       ```

    5. **frontend/tests/fixtures/scan/AAPL-bad-version.json** — fixture for ErrorBoundary E2E test: same shape as AAPL.json but with `"schema_version": 1` (Wave 0 bumped to 2; this fixture intentionally fails the SnapshotSchema literal).

    6. Tests:
       - **ErrorBoundary.test.tsx**: render an in-test child that throws SchemaMismatchError → boundary renders schema-mismatch UI; child throws FetchNotFoundError with snapshot URL → renders 'No snapshot' UI; child throws generic Error → renders generic UI.
       - **DateSelector.test.tsx**: with mock useDates returning ['2026-04-30','2026-05-01','2026-05-02'], render in MemoryRouter at /scan/2026-05-01; assert select shows 4 options (today + 3 dates); change to '2026-04-30' → useNavigate called with '/scan/2026-04-30'; render at /ticker/AAPL/2026-05-01 → change preserves /ticker/AAPL/...
       - **loadDates.test.ts**: mock fetch with happy + 404 paths.

    7. Run: `cd frontend && pnpm test:unit --run` — confirm all new tests + existing tests green.
    8. Commit with: `feat(06-05): ErrorBoundary + DateSelector + loadDates per VIEW-14 + VIEW-15`
  </action>
  <verify>
    <automated>cd frontend && pnpm test:unit --run 2>&1 | tail -15</automated>
  </verify>
  <done>ErrorBoundary catches SchemaMismatchError + FetchNotFoundError + generic; DateSelector reads data/_dates.json + navigates with preserved route shape; Root wraps Outlet in ErrorBoundary + adds DateSelector to header; ~6+ new tests green; commit landed.</done>
</task>

<task type="auto">
  <name>Task 2: Mobile-responsive polish + Chart touch-friendliness + Playwright responsive specs</name>
  <files>frontend/src/routes/ScanRoute.tsx, frontend/src/routes/TickerRoute.tsx, frontend/src/components/Chart.tsx, frontend/src/components/lenses/PositionLens.tsx, frontend/src/components/lenses/ShortTermLens.tsx, frontend/src/components/lenses/LongTermLens.tsx, frontend/src/index.css, frontend/tests/e2e/responsive.spec.ts</files>
  <action>
    1. **Tailwind responsive breakpoints applied across the app** — review every Wave 2-3 component and add breakpoint utility classes:
       - **TickerRoute.tsx**: 2 TimeframeCards: `flex flex-col lg:flex-row gap-6` (stacked on <lg, side-by-side on lg+); persona grid `grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4`; analytical grid `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4`; main heading + back-link row uses `flex flex-wrap items-baseline justify-between gap-2`.
       - **ScanRoute.tsx**: lens tabs use shadcn Tabs default (already responsive); add `overflow-x-auto` to TabsList wrapper for very narrow screens (<360px) to prevent layout break.
       - **Lens components** (Position/ShortTerm/LongTerm): TickerCard rows already stack content via `flex-col gap-4` — add `sm:flex-row sm:items-center` to inner content where appropriate so on >sm it's a row, on <sm it's a column. Verify mono-ticker label stays aligned (`w-20 shrink-0` on >sm; `w-full` on <sm).
       - **Root.tsx header**: `flex flex-col sm:flex-row sm:items-center justify-between gap-2 sm:gap-4` so on narrow phones the header stacks (logo on top, controls below).

    2. **Chart.tsx touch-friendliness** — extend createChart options:
       ```ts
       const chart = createChart(containerRef.current, {
         ...,
         handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: false },
         handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true },
       })
       ```
       Set chart height responsive: 400 on lg+, 300 on md, 240 on sm. Pass via Tailwind container queries OR a useMedia hook OR a ResizeObserver-driven prop. Simplest: use a CSS aspect-ratio container and let lightweight-charts fill its parent (already wired via ResizeObserver from Wave 3 — verify it still resizes on the iPhone viewport).

    3. **src/index.css** — verify Inter + JetBrains Mono are loaded (or fall back to system fonts). Add `@font-face` declarations OR use a CDN link in index.html. For v1 simplicity:
       ```html
       <!-- index.html <head> -->
       <link rel="preconnect" href="https://fonts.googleapis.com">
       <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
       <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
       ```
       (Or self-host via Fontsource — `pnpm add @fontsource/inter @fontsource/jetbrains-mono` — Notion-Clean spec doesn't lock the source, just the family. Self-host is preferred for deterministic builds + offline dev; CDN is simpler.)

    4. **frontend/tests/e2e/responsive.spec.ts**:
       ```ts
       import { test, expect } from '@playwright/test'
       import { mountScanFixtures } from './fixtures-server'

       test.describe('responsive', () => {
         test.beforeEach(async ({ page }) => mountScanFixtures(page))

         test('mobile: scan tabs full-width and tap-friendly', async ({ page, isMobile }) => {
           test.skip(!isMobile, 'mobile-only')
           await page.goto('/scan/2026-05-04')
           const tabsList = page.getByRole('tablist')
           await expect(tabsList).toBeVisible()
           // Each tab should be ≥44px tall (Apple HIG)
           const tab = page.getByRole('tab', { name: 'Position Adjustment' })
           const box = await tab.boundingBox()
           expect(box!.height).toBeGreaterThanOrEqual(40)
         })

         test('mobile: deep-dive timeframe cards stack vertically', async ({ page, isMobile }) => {
           test.skip(!isMobile, 'mobile-only')
           await page.goto('/ticker/NVDA/2026-05-04')
           const cards = page.locator('[data-testid="timeframe-card"]')  // requires adding data-testid in Wave 3 OR target via heading
           // Or: target by heading "Short-Term" + "Long-Term" and assert their y-coordinates differ (stacked = different y)
           const shortHeading = page.getByText(/Short-Term/i).first()
           const longHeading = page.getByText(/Long-Term/i).first()
           const shortBox = await shortHeading.boundingBox()
           const longBox = await longHeading.boundingBox()
           expect(longBox!.y).toBeGreaterThan(shortBox!.y + 50)  // stacked, not side-by-side
         })

         test('mobile: no horizontal scroll on scan or deep-dive', async ({ page, isMobile }) => {
           test.skip(!isMobile, 'mobile-only')
           for (const path of ['/scan/2026-05-04', '/ticker/NVDA/2026-05-04']) {
             await page.goto(path)
             const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth)
             const clientWidth = await page.evaluate(() => document.documentElement.clientWidth)
             expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 1)  // +1 for sub-pixel rounding tolerance
           }
         })
       })
       ```

    5. Run: `cd frontend && pnpm test:e2e --project=mobile-safari --project=mobile-chrome -g responsive` — confirm all responsive specs pass on both mobile projects.
    6. Commit with: `feat(06-05): mobile-responsive breakpoints + chart touch-friendliness + Playwright responsive specs`
  </action>
  <verify>
    <automated>cd frontend && pnpm test:e2e --project=mobile-safari -g responsive 2>&1 | tail -15</automated>
  </verify>
  <done>Tailwind breakpoints applied across all routes; Chart pans/pinches on mobile; Inter + JetBrains Mono fonts loaded; mobile-safari + mobile-chrome Playwright projects pass responsive specs; commit landed.</done>
</task>

<task type="auto">
  <name>Task 3: Error-boundary E2E + full-flow E2E + visual taste-check pass</name>
  <files>frontend/tests/e2e/error-boundary.spec.ts, frontend/tests/e2e/full-flow.spec.ts</files>
  <action>
    1. **frontend/tests/e2e/error-boundary.spec.ts**:
       ```ts
       import { test, expect } from '@playwright/test'
       import { mountScanFixtures } from './fixtures-server'
       import fs from 'node:fs'
       import path from 'node:path'

       test.describe('error boundary', () => {
         test('schema_version mismatch renders user-friendly error', async ({ page }) => {
           // Mount happy fixtures EXCEPT route AAPL.json to the bad-version fixture
           await mountScanFixtures(page)
           await page.route(/\/AAPL\.json/, route => {
             const fixDir = path.resolve(__dirname, 'fixtures/scan')
             route.fulfill({ body: fs.readFileSync(path.join(fixDir, 'AAPL-bad-version.json')) })
           })
           await page.goto('/ticker/AAPL/2026-05-04')
           await expect(page.getByText(/Schema version mismatch/i)).toBeVisible()
           await expect(page.getByText(/v2/i)).toBeVisible()  // expected version surfaced
         })

         test('404 on per-ticker JSON renders not-found message', async ({ page }) => {
           await mountScanFixtures(page)
           await page.route(/\/ZZZZ\.json/, route => route.fulfill({ status: 404, body: 'Not found' }))
           await page.goto('/ticker/ZZZZ/2026-05-04')
           await expect(page.getByText(/not in/i)).toBeVisible()
           await expect(page.locator('a[href*="/scan/"]')).toBeVisible()  // back-to-scan link
         })

         test('404 on _index.json renders no-snapshot message', async ({ page }) => {
           await page.route(/\/2099-12-31\/(_index|_status)\.json/, route => route.fulfill({ status: 404, body: 'Not found' }))
           await page.route(/\/_dates\.json/, route => route.fulfill({ body: JSON.stringify({ schema_version: 1, dates_available: ['2026-05-04'], updated_at: new Date().toISOString() })}))
           await page.goto('/scan/2099-12-31')
           await expect(page.getByText(/No snapshot/i)).toBeVisible()
         })
       })
       ```

    2. **frontend/tests/e2e/full-flow.spec.ts** — single comprehensive happy-path test:
       ```ts
       import { test, expect } from '@playwright/test'
       import { mountScanFixtures } from './fixtures-server'

       test.describe('full flow', () => {
         test.beforeEach(async ({ page }) => mountScanFixtures(page))

         test('scan → switch lenses → click ticker → deep-dive → date selector', async ({ page }) => {
           // Mount _dates.json fixture too
           await page.route(/\/_dates\.json/, route => route.fulfill({ body: JSON.stringify({
             schema_version: 1, dates_available: ['2026-05-03','2026-05-04'], updated_at: new Date().toISOString(),
           })}))

           // 1. Open scan
           await page.goto('/scan/2026-05-04')
           await expect(page.getByRole('tab', { name: 'Position Adjustment' })).toBeVisible()
           await expect(page.getByText(/GREEN|AMBER|RED/)).toBeVisible()  // staleness badge

           // 2. Switch to Short-Term lens
           await page.getByRole('tab', { name: 'Short-Term Opportunities' }).click()
           await expect(page).toHaveURL(/lens=short/)

           // 3. Switch to Long-Term lens
           await page.getByRole('tab', { name: 'Long-Term Thesis Status' }).click()
           await expect(page).toHaveURL(/lens=long/)

           // 4. Click NVDA (should appear — thesis_status='broken' fixture)
           await page.locator('a[href*="/ticker/NVDA/"]').first().click()
           await expect(page).toHaveURL(/\/ticker\/NVDA\//)

           // 5. Deep-dive sections all present
           await expect(page.getByTestId('open-claude-pin')).toBeVisible()
           await expect(page.getByTestId('chart-container')).toBeVisible()
           await expect(page.getByRole('heading', { name: /Persona Signals/i })).toBeVisible()
           await expect(page.getByRole('heading', { name: /News Feed/i })).toBeVisible()

           // 6. Date selector navigates with preserved symbol
           await page.getByTestId('date-selector').selectOption('2026-05-03')
           await expect(page).toHaveURL(/\/ticker\/NVDA\/2026-05-03/)
         })
       })
       ```
       This test runs by default on all 3 Playwright projects (chromium-desktop + mobile-safari + mobile-chrome) — that's the multi-device E2E discipline locked in playwright.config.ts.

    3. **Visual taste-check pass**: After tests pass, run a final scripted self-review:
       - Open `pnpm preview` locally (Vite preview server on port 4173).
       - Use Playwright in headed mode OR a local browser to visit /scan/today, /scan/today?lens=short, /scan/today?lens=long, /ticker/AAPL/today (all served via fixture-server pattern OR real data if Wave 0 data has been published).
       - Record findings in the SUMMARY: palette adherence (background #0E0F11; surfaces #1F2024; borders #2A2C30; text #E8E9EB primary / #8B8E94 secondary; accent #5B9DFF; bullish #4ADE80; bearish #F87171; amber #FBBF24); spacing (8px base, generous gutters); typography (Inter for UI, JetBrains Mono for ticker symbols + numerics); motion (fade only, no slide/zoom; respects prefers-reduced-motion); border-vs-shadow (1px hairlines preferred; minimal drop shadow).
       - Note any visual drift WITHOUT auto-fixing — visual-taste decisions are user-facing per VALIDATION.md "Manual-Only Verifications".
       - Capture 2-4 screenshots of /scan + /ticker desktop + mobile (Playwright `page.screenshot({ path: '...' })` from inside any spec; save to a Wave 4 closeout directory like `frontend/.taste-check/` or attach via SUMMARY).

    4. Run full suite: `cd frontend && pnpm test:unit --run && pnpm test:e2e && pnpm build` — confirm all 3 Playwright projects pass + vitest green + build succeeds.
    5. Commit with: `test(06-05): error-boundary + full-flow E2E + visual taste-check pass`
  </action>
  <verify>
    <automated>cd frontend && pnpm test:e2e 2>&1 | tail -20</automated>
  </verify>
  <done>error-boundary.spec.ts (3 specs) + full-flow.spec.ts (1 spec × 3 projects = 3 invocations) all green; visual taste-check findings recorded in SUMMARY; commit landed.</done>
</task>

</tasks>

<verification>
- All 3 tasks complete; commits landed
- Vitest: ~80+ unit tests passing (Wave 1+2+3+4 cumulative)
- Playwright: all 3 projects (chromium-desktop + mobile-safari + mobile-chrome) green on smoke + scan + deep-dive + responsive + error-boundary + full-flow specs
- typecheck + build succeed
- VIEW-12: mobile-responsive — Playwright mobile-safari + mobile-chrome project specs pass
- VIEW-14: DateSelector reads data/_dates.json; navigates with preserved route shape (scan or ticker) and lens query param
- VIEW-15: ErrorBoundary catches SchemaMismatchError + FetchNotFoundError; renders explicit error states per CONTEXT.md UNIFORM RULE; never silently crashes
- All 14 frontend VIEW requirements (VIEW-01..09 + VIEW-11..15) closed across Waves 2-4
- INFRA-05 closed across Waves 0-1 (Wave 0: schema_version=2 + _dates.json; Wave 1: Vercel deploy config)
- Visual taste-check findings stored in SUMMARY for user manual verification
</verification>

<success_criteria>
- [ ] ErrorBoundary catches SchemaMismatchError → renders schema-mismatch error with both versions surfaced
- [ ] ErrorBoundary catches FetchNotFoundError → renders not-found error with appropriate context (snapshot vs ticker)
- [ ] ErrorBoundary catches generic errors → renders fallback with reload link
- [ ] DateSelector reads data/_dates.json; selecting a date navigates with active lens/symbol preserved
- [ ] All routes responsive: tested on mobile-safari (iPhone 14) + mobile-chrome (Pixel 7) Playwright projects
- [ ] Chart pans/pinches on mobile; height scales to viewport
- [ ] No horizontal scroll on any route at 375px width (iPhone)
- [ ] Lens tabs ≥40px tall on mobile (tap-friendly)
- [ ] TimeframeCards stack vertically on <lg breakpoint
- [ ] Inter + JetBrains Mono fonts loaded (CDN or self-hosted)
- [ ] Vitest unit tests: ~6+ new tests pass; total ≥ 80 tests green
- [ ] Playwright: all 3 projects green (smoke + scan + deep-dive + responsive + error-boundary + full-flow)
- [ ] Build succeeds with no type errors
- [ ] Visual taste-check findings recorded in SUMMARY (manual verification deferred to user per VALIDATION.md)
- [ ] 3 commits landed: `feat(06-05): ErrorBoundary + DateSelector + loadDates` → `feat(06-05): mobile-responsive + chart touch + Playwright specs` → `test(06-05): error-boundary + full-flow E2E + visual taste-check`
</success_criteria>

<output>
After completion, create `.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-05-SUMMARY.md` matching Phase 1-5 SUMMARY template — sections: Plan Identity / Wave / Outcome / Files Created / VIEW-12+14+15 Coverage Map / Test Suite Summary (vitest + Playwright counts across all 3 projects) / Visual Taste-Check Findings (palette adherence + screenshots referenced) / Phase 6 Closeout Notes (all 14 VIEW + INFRA-05 closed; Phase 7 Decision-Support View unblocked; Phase 8 Mid-Day Refresh unblocked — frontend infrastructure stable for /api/refresh integration).
</output>
