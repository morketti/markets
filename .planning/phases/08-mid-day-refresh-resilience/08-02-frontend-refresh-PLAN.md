---
phase: 08-mid-day-refresh-resilience
plan: 02
type: execute
wave: 1
depends_on: ['08-01']
files_modified:
  - frontend/src/schemas/refresh.ts
  - frontend/src/schemas/__tests__/refresh.test.ts
  - frontend/src/lib/useRefreshData.ts
  - frontend/src/lib/__tests__/useRefreshData.test.ts
  - frontend/src/components/CurrentPriceDelta.tsx
  - frontend/src/components/__tests__/CurrentPriceDelta.test.tsx
  - frontend/src/routes/TickerRoute.tsx
  - frontend/src/routes/DecisionRoute.tsx
  - frontend/tests/e2e/resilience.spec.ts
autonomous: true
requirements: [REFRESH-02, REFRESH-03, REFRESH-04]

must_haves:
  truths:
    - "Opening /ticker/AAPL/today triggers GET /api/refresh?ticker=AAPL via useRefreshData(symbol); current_price + delta vs snapshot.last_price renders next to the ticker hero"
    - "Opening /decision/AAPL/today replaces the Phase-7 PHASE-8-HOOK placeholder with <CurrentPriceDelta /> driven by useRefreshData('AAPL') — the data-testid='current-price-placeholder' attribute is preserved"
    - "Switching from /ticker/AAPL/today to /ticker/MSFT/today does NOT flicker the previous-symbol price (TanStack keepPreviousData)"
    - "TanStack Query dedupes the refresh fetch by queryKey: ['refresh', symbol] — TickerRoute + DecisionRoute mounted on the same symbol share one fetch"
    - "Refresh fetch fails (HTTP 5xx OR network error) -> frontend continues rendering snapshot price; muted 'Refresh unavailable — showing snapshot price' notice appears; NO crash, NO white-screen, snapshot stays canonical"
    - "Refresh response with partial=true (RSS unavailable) -> current_price + delta still render; recent_headlines section gracefully shows empty (no error UI for the headline absence)"
    - "Notion-Clean palette discipline holds — every color in <CurrentPriceDelta /> via CSS variable tokens (no inline hex)"
  artifacts:
    - path: frontend/src/schemas/refresh.ts
      provides: "zod discriminated-union schema for refresh response (success / partial / full-failure shapes)"
      contains: "z.discriminatedUnion"
    - path: frontend/src/lib/useRefreshData.ts
      provides: "TanStack Query hook with keepPreviousData + 5-min staleTime + retry: 1"
      contains: "useQuery"
    - path: frontend/src/components/CurrentPriceDelta.tsx
      provides: "Component rendering current_price + delta % + refreshed-N-ago + isError fallback; preserves data-testid='current-price-placeholder'"
      contains: "data-testid=\"current-price-placeholder\""
    - path: frontend/src/routes/TickerRoute.tsx
      provides: "Mounts <CurrentPriceDelta /> in the deep-dive layout (above or alongside TimeframeCards)"
    - path: frontend/src/routes/DecisionRoute.tsx
      provides: "Replaces the Phase-7 placeholder with <CurrentPriceDelta /> while preserving the data-testid"
    - path: frontend/tests/e2e/resilience.spec.ts
      provides: "Playwright spec mocking refresh failure → asserts snapshot stays canonical + 'refresh unavailable' badge visible"
      min_lines: 70
  key_links:
    - from: frontend/src/lib/useRefreshData.ts
      to: frontend/src/schemas/refresh.ts
      via: "fetchAndParse(refreshUrl(symbol), RefreshResponseSchema) — reuses Phase 6 fetchAndParse pattern"
      pattern: "RefreshResponseSchema"
    - from: frontend/src/components/CurrentPriceDelta.tsx
      to: frontend/src/lib/useRefreshData.ts
      via: "Calls useRefreshData(symbol) and reads {data, isError, isPending, dataUpdatedAt}"
      pattern: "useRefreshData"
    - from: frontend/src/routes/TickerRoute.tsx
      to: frontend/src/components/CurrentPriceDelta.tsx
      via: "Renders <CurrentPriceDelta symbol={symbol} snapshotLastPrice={snap.snapshot_summary?.last_price} snapshotComputedAt={snap.computed_at} />"
      pattern: "<CurrentPriceDelta"
    - from: frontend/src/routes/DecisionRoute.tsx
      to: frontend/src/components/CurrentPriceDelta.tsx
      via: "Replaces the PHASE-8-HOOK placeholder div with <CurrentPriceDelta /> while preserving data-testid"
      pattern: "<CurrentPriceDelta"
---

<objective>
Wave 1 — Frontend on-open refresh integration. Mounts the TanStack hook on BOTH TickerRoute and DecisionRoute so deep-dive AND decision-support views see the same fresh current_price + delta. Replaces Phase 7's PHASE-8-HOOK placeholder. Resilience E2E spec verifies the lock: refresh failure NEVER crashes the page; snapshot stays canonical.

Purpose: Close the user-facing half of Phase 8. Wave 0 stood up the Vercel function + memory log + provenance enforcement; this wave wires the function into the frontend and verifies the failure-mode UX with a real Playwright spec.

Output: refresh zod schema + useRefreshData TanStack hook + CurrentPriceDelta component + dual-route mount + ~20 vitest cases + 1 Playwright resilience spec. Closes REFRESH-02, REFRESH-03, and the frontend half of REFRESH-04.
</objective>

<execution_context>
@C:/Users/Mohan/.claude/workflows/execute-plan.md
@C:/Users/Mohan/.claude/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/08-mid-day-refresh-resilience/08-CONTEXT.md
@.planning/phases/08-mid-day-refresh-resilience/08-RESEARCH.md
@.planning/phases/08-mid-day-refresh-resilience/08-VALIDATION.md
@.planning/phases/08-mid-day-refresh-resilience/08-01-backend-refresh-PLAN.md

# Reusable assets — Phase 6 + 7 patterns to clone:
@frontend/src/lib/fetchSnapshot.ts
@frontend/src/routes/TickerRoute.tsx
@frontend/src/routes/DecisionRoute.tsx

<interfaces>
<!-- Contracts the executor consumes directly. -->

From `frontend/src/lib/fetchSnapshot.ts` (Phase 6 — reuse the typed-error pattern):
```ts
export class SchemaMismatchError extends Error {
  readonly url: string
  readonly zodError: ZodError
}
export class FetchNotFoundError extends Error {
  readonly url: string
}
// Generic fetch + zod parse — REUSE for the new fetchRefresh helper.
export async function fetchAndParse<T>(url: string, schema: ZodType<T>): Promise<T>
```

Refresh response shapes (LOCKED in 08-CONTEXT.md, snake_case mirrors backend):
```ts
// SUCCESS: {ticker, current_price, price_timestamp, recent_headlines[], errors:[], partial: false}
// PARTIAL (RSS unavailable): {ticker, current_price, price_timestamp, recent_headlines: [], errors: ['rss-unavailable'], partial: true}
// FULL FAILURE: {ticker, error: true, errors: [...], partial: true}  // current_price absent or null
```

From `frontend/src/routes/DecisionRoute.tsx` lines 177-190 — the Phase-7 hookpoint to replace:
```tsx
{/* 4. PHASE-8-HOOK: current-price-delta — Phase 8 (api/refresh.py)
    replaces this placeholder with <CurrentPriceDelta /> fed by
    useRefreshData(symbol). The data-testid below is the deterministic
    search target for Phase 8's planner; keep BOTH the source comment
    (this string) AND the data-testid attribute for the grep contract. */}
<div
  data-testid="current-price-placeholder"
  className="rounded-md border border-dashed border-border bg-surface px-4 py-3 text-sm text-fg-muted"
>
  Snapshot price as of {new Date(dec.computed_at).toLocaleString()} ET.{' '}
  <span className="italic">
    Current-price delta arrives via mid-day refresh in Phase 8.
  </span>
</div>
```

The replacement MUST preserve `data-testid="current-price-placeholder"` (the existing grep target stays valid for any future tooling).

Existing TanStack Query setup: project already uses `useQuery` from `@tanstack/react-query` in `frontend/src/lib/loadTickerData.ts` (Phase 6). `keepPreviousData` is the v5 idiom: `placeholderData: keepPreviousData` (NOT `keepPreviousData: true`).

Notion-Clean palette tokens (Phase 6 lock — DO NOT use inline hex):
- `text-fg`, `text-fg-muted` — primary / secondary text
- `bg-surface`, `bg-bg` — surfaces
- `border-border`, `border-border/50` — borders
- `text-bullish` (green), `text-bearish` (red), `text-accent` (blue) — semantic colors
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: refresh zod schema + useRefreshData TanStack hook + tests</name>
  <files>frontend/src/schemas/refresh.ts, frontend/src/schemas/__tests__/refresh.test.ts, frontend/src/lib/useRefreshData.ts, frontend/src/lib/__tests__/useRefreshData.test.ts</files>
  <behavior>
    Test surface in `frontend/src/schemas/__tests__/refresh.test.ts` (~6 tests, ~50 LOC):

    1. **parses_success_shape** — Input `{ticker:"AAPL", current_price:178.42, price_timestamp:"2026-05-04T19:32:11+00:00", recent_headlines:[{source:"Reuters", published_at:"...", title:"...", url:"..."}], errors:[], partial:false}`. Parse succeeds; output is correctly typed.
    2. **parses_partial_shape_rss_unavailable** — Input has `partial:true, errors:["rss-unavailable"], recent_headlines:[]`. Parses successfully via the discriminated union.
    3. **parses_full_failure_shape** — Input `{ticker:"AAPL", error:true, errors:["yfinance-unavailable","yahooquery-unavailable"], partial:true}` (no current_price). Parses via the failure variant.
    4. **rejects_invalid_current_price** — current_price=-1 OR current_price="178" (string instead of number) → safeParse fails.
    5. **rejects_missing_ticker** — Input lacks ticker. safeParse fails.
    6. **rejects_invalid_iso_timestamp** — price_timestamp="not a date". safeParse fails.

    Test surface in `frontend/src/lib/__tests__/useRefreshData.test.ts` (~6-8 tests, ~120 LOC):

    7. **returns_data_on_success** — Use MSW (existing project setup) OR `vi.fn()` mocking `fetchAndParse` to return a happy-path RefreshResponse. Render `useRefreshData('AAPL')` via `renderHook` + `QueryClientProvider`. Wait for `result.current.isSuccess`; assert `result.current.data.current_price === 178.42`.
    8. **error_state_on_500** — Mock fetch returning 500. Eventually `result.current.isError === true`. data is undefined.
    9. **dedup_by_query_key** — Render `useRefreshData('AAPL')` twice in the same QueryClient wrapper; assert `fetchAndParse` (the mocked fetcher) was called only once.
    10. **stale_time_5_minutes** — After successful fetch, data is fresh; immediate re-render does NOT trigger another fetch within the 5-min staleTime window. Verify via `vi.useFakeTimers()` / mock timer skipping.
    11. **retry_count_one** — Mock fetch failing twice then succeeding. With `retry: 1`, hook tries 2 total (1 initial + 1 retry); on failure of both, isError=true.
    12. **keep_previous_data_on_symbol_swap** — Render with symbol='AAPL', resolve. Re-render with symbol='MSFT'. While the MSFT fetch is in-flight, `result.current.data` STILL points to the AAPL result (placeholderData: keepPreviousData behavior).
  </behavior>
  <action>
    Create `frontend/src/schemas/refresh.ts` (~50 LOC).

    ```ts
    // novel-to-this-project — refresh response schema mirroring api/refresh.py
    // (snake_case discipline locked in 08-CONTEXT.md). zod discriminated union
    // over the `error` flag distinguishes success/partial from full-failure
    // shapes, so the rest of the frontend pattern-matches via narrowing.

    import { z } from 'zod'

    export const RefreshHeadlineSchema = z.object({
      source: z.string(),
      published_at: z.string().datetime({ offset: true }),  // ISO-8601 with offset
      title: z.string(),
      url: z.string().url(),
    })
    export type RefreshHeadline = z.infer<typeof RefreshHeadlineSchema>

    // SUCCESS / PARTIAL — current_price present
    const RefreshSuccessSchema = z.object({
      ticker: z.string().min(1),
      current_price: z.number().positive(),
      price_timestamp: z.string().datetime({ offset: true }),
      recent_headlines: z.array(RefreshHeadlineSchema),
      errors: z.array(z.string()),
      partial: z.boolean(),
      error: z.literal(false).optional(),  // explicit false OR absent
    })

    // FULL FAILURE — error: true, no current_price
    const RefreshFailureSchema = z.object({
      ticker: z.string().min(1),
      error: z.literal(true),
      errors: z.array(z.string()).min(1),
      partial: z.literal(true),
    })

    // Discriminated union — narrows on `error` flag.
    export const RefreshResponseSchema = z.union([RefreshSuccessSchema, RefreshFailureSchema])
    export type RefreshResponse = z.infer<typeof RefreshResponseSchema>

    // Helper for narrowing in render code.
    export const isRefreshFailure = (r: RefreshResponse): r is z.infer<typeof RefreshFailureSchema> =>
      'error' in r && r.error === true
    ```

    Create `frontend/src/lib/useRefreshData.ts` (~50 LOC).

    ```ts
    // novel-to-this-project — TanStack Query hook for the on-open refresh.
    // Mounted on TickerRoute AND DecisionRoute; queryKey ['refresh', symbol]
    // dedupes across the two routes (researcher rec #1 lock).

    import { keepPreviousData, useQuery } from '@tanstack/react-query'
    import { fetchAndParse } from '@/lib/fetchSnapshot'
    import { RefreshResponseSchema, type RefreshResponse } from '@/schemas/refresh'

    // Same-origin path. In dev (Vite) the function is unavailable; tests mock
    // fetchAndParse directly. In Vercel preview/prod the SPA-rewrite narrowing
    // (frontend/vercel.json /((?!api/).*)) ensures /api/refresh is NOT
    // rewritten to /index.html.
    export const refreshUrl = (symbol: string): string =>
      `/api/refresh?ticker=${encodeURIComponent(symbol)}`

    export function useRefreshData(symbol: string) {
      return useQuery<RefreshResponse>({
        queryKey: ['refresh', symbol],
        queryFn: () => fetchAndParse(refreshUrl(symbol), RefreshResponseSchema),
        staleTime: 5 * 60 * 1000,           // 5 min — refresh once per ticker view
        placeholderData: keepPreviousData,   // no flicker on symbol swap
        retry: 1,
        enabled: symbol.length > 0,
      })
    }
    ```

    Create `frontend/src/schemas/__tests__/refresh.test.ts` implementing tests 1-6. Use `RefreshResponseSchema.safeParse(input)` and assert `.success` true/false.

    Create `frontend/src/lib/__tests__/useRefreshData.test.ts` implementing tests 7-12. Use `@testing-library/react`'s `renderHook` + `QueryClientProvider` wrapper. Mock `fetchAndParse` via `vi.mock('@/lib/fetchSnapshot', ...)`. Reuse the QueryClient setup pattern from existing `frontend/src/lib/__tests__/loadTickerData.test.ts` (Phase 6) if present — clone the pattern verbatim for consistency.
  </action>
  <verify>
    <automated>cd frontend && pnpm test:unit src/lib/__tests__/useRefreshData.test.ts src/schemas/__tests__/refresh.test.ts --run</automated>
  </verify>
  <done>
    All ~12 tests pass. RefreshResponseSchema parses 3 documented shapes (success / partial / full-failure) and rejects 3 invalid shapes. useRefreshData hook returns typed data, keeps previous data on symbol swap, dedupes by queryKey, retries once, respects 5-min staleTime.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: CurrentPriceDelta component + dual-route mount + tests</name>
  <files>frontend/src/components/CurrentPriceDelta.tsx, frontend/src/components/__tests__/CurrentPriceDelta.test.tsx, frontend/src/routes/TickerRoute.tsx, frontend/src/routes/DecisionRoute.tsx</files>
  <behavior>
    Test surface in `frontend/src/components/__tests__/CurrentPriceDelta.test.tsx` (~8 tests, ~150 LOC):

    1. **renders_loading_state** — useRefreshData mocked to isPending=true. Component shows muted "Refreshing…" placeholder; preserves `data-testid="current-price-placeholder"`.
    2. **renders_success_with_positive_delta** — data={current_price: 180.00}, snapshotLastPrice=178.00. Renders "$180.00" + "+1.12%" with bullish color class (`text-bullish`). Refreshed timestamp shows.
    3. **renders_success_with_negative_delta** — current_price=176, snapshotLastPrice=178. Renders "−1.12%" with bearish color class.
    4. **renders_zero_delta_neutral** — Identical prices. Delta shows "0.00%" with neutral color (no bullish/bearish class).
    5. **renders_no_snapshot_price_baseline** — snapshotLastPrice=undefined. Renders current_price WITHOUT a delta percentage; no crash.
    6. **renders_partial_response** — data has partial=true, errors=['rss-unavailable']. current_price + delta still render normally; subtle muted note "Headlines unavailable" appears (or omitted — pick one and lock).
    7. **renders_full_failure_envelope** — data={error: true, errors: ['yfinance-unavailable','yahooquery-unavailable'], partial: true}. Component renders "Refresh unavailable — showing snapshot price" muted notice; `data-testid="current-price-placeholder"` preserved; NO crash.
    8. **renders_isError_fallback** — useRefreshData mocked with isError=true (network failure / fetchAndParse threw). Shows the same "Refresh unavailable — showing snapshot price" muted notice; preserves data-testid; the snapshotLastPrice is rendered as fallback display.

    All tests use `vi.mock('@/lib/useRefreshData', ...)` to inject hook return values and avoid TanStack Query setup overhead.

    **Mount-point assertions** — extend an existing or new test (whichever is cheaper) verifying:

    9. **TickerRoute_mounts_CurrentPriceDelta** — Render TickerRoute via the existing test harness; assert `screen.getByTestId('current-price-placeholder')` is present.
    10. **DecisionRoute_mounts_CurrentPriceDelta** — Render DecisionRoute; assert the same testid is present AND the Phase-7 placeholder copy ("Current-price delta arrives via mid-day refresh in Phase 8.") is GONE (replaced).

    Tests 9-10 may live in the existing `frontend/src/routes/__tests__/TickerRoute.test.tsx` and `DecisionRoute.test.tsx` (Phase 6/7) — APPEND, do not replace.
  </behavior>
  <action>
    Create `frontend/src/components/CurrentPriceDelta.tsx` (~110 LOC).

    **File header:**
    ```tsx
    // novel-to-this-project — Phase 8 frontend hero element. Replaces the
    // Phase-7 PHASE-8-HOOK placeholder in DecisionRoute. Mounted ALSO on
    // TickerRoute (researcher rec #1 — dual-timeframe focus). Preserves
    // data-testid='current-price-placeholder' for grep-target continuity.
    //
    // Notion-Clean palette discipline: every color via CSS variable tokens
    // (text-fg, text-fg-muted, text-bullish, text-bearish, border-border).
    // No inline hex. No tw-arbitrary values.
    ```

    **Component shape (sketch — fill in):**
    ```tsx
    import { useRefreshData } from '@/lib/useRefreshData'
    import { isRefreshFailure } from '@/schemas/refresh'

    interface CurrentPriceDeltaProps {
      symbol: string
      snapshotLastPrice?: number | null
      snapshotComputedAt?: string  // ISO-8601 string
    }

    export function CurrentPriceDelta({
      symbol, snapshotLastPrice, snapshotComputedAt,
    }: CurrentPriceDeltaProps) {
      const { data, isPending, isError, dataUpdatedAt } = useRefreshData(symbol)

      // Fallback shape: error / failure envelope / undefined data
      const showFallback = isError || (data !== undefined && isRefreshFailure(data))

      if (isPending) {
        return (
          <div data-testid="current-price-placeholder" className="...">
            Refreshing {symbol}…
          </div>
        )
      }

      if (showFallback) {
        return (
          <div data-testid="current-price-placeholder" className="rounded-md border border-dashed border-border bg-surface px-4 py-3 text-sm text-fg-muted">
            <span>{snapshotLastPrice != null ? `$${snapshotLastPrice.toFixed(2)}` : '—'}</span>{' '}
            <span className="italic">Refresh unavailable — showing snapshot price.</span>
          </div>
        )
      }

      // SUCCESS / PARTIAL path — `data` is RefreshSuccessSchema-shaped.
      const success = data as Extract<typeof data, { current_price: number }>
      const current = success.current_price
      const hasBaseline = typeof snapshotLastPrice === 'number' && snapshotLastPrice > 0
      const deltaPct = hasBaseline
        ? ((current - snapshotLastPrice!) / snapshotLastPrice!) * 100
        : null

      const deltaClass =
        deltaPct == null ? 'text-fg-muted'
        : deltaPct > 0 ? 'text-bullish'
        : deltaPct < 0 ? 'text-bearish'
        : 'text-fg-muted'

      const refreshedSecondsAgo = Math.max(
        0, Math.round((Date.now() - dataUpdatedAt) / 1000),
      )

      return (
        <div data-testid="current-price-placeholder" className="rounded-md border border-border bg-surface px-4 py-3">
          <div className="flex items-baseline gap-3">
            <span className="font-mono text-2xl font-semibold text-fg">
              ${current.toFixed(2)}
            </span>
            {deltaPct != null && (
              <span className={`font-mono text-lg font-medium ${deltaClass}`}>
                {deltaPct > 0 ? '+' : ''}{deltaPct.toFixed(2)}%
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-fg-muted">
            Refreshed {refreshedSecondsAgo}s ago
            {success.partial && success.errors.includes('rss-unavailable') && (
              <span className="ml-2 italic">· Headlines unavailable</span>
            )}
          </p>
        </div>
      )
    }
    ```

    Modify `frontend/src/routes/TickerRoute.tsx` — add `<CurrentPriceDelta />` to the layout. Insert it ABOVE the TimeframeCards section (Section 3 in the existing layout numbering), AFTER the OpenClaudePin (Section 2). Pass `symbol={symbol}`, `snapshotLastPrice={snap.snapshot_summary?.last_price}` (or whichever field Phase 6 storage exposes — verify against the existing snapshot schema during implementation), `snapshotComputedAt={snap.computed_at}`.

    Modify `frontend/src/routes/DecisionRoute.tsx` — REPLACE the existing PHASE-8-HOOK placeholder block (lines 177-190 in the current file). Replacement code:
    ```tsx
    {/* 4. CurrentPriceDelta — Phase 8 close. Replaces the Phase-7 placeholder.
        data-testid='current-price-placeholder' is preserved on the new element
        for grep-target continuity. */}
    <CurrentPriceDelta
      symbol={symbol}
      snapshotLastPrice={dec.snapshot_summary?.last_price}
      snapshotComputedAt={dec.computed_at}
    />
    ```

    Also remove the "Snapshot price as of {...} ET. Current-price delta arrives via mid-day refresh in Phase 8." copy — replaced. The `dec.computed_at` reference may move into CurrentPriceDelta for the "as of" tooltip if useful; otherwise drop.

    Create `frontend/src/components/__tests__/CurrentPriceDelta.test.tsx` implementing tests 1-8. Use `vi.mock('@/lib/useRefreshData', ...)` to inject `{ data, isPending, isError, dataUpdatedAt }` directly per test.

    Append tests 9-10 to existing `TickerRoute.test.tsx` + `DecisionRoute.test.tsx` (verify these files exist; if not, create the minimal harness needed). Mock `useRefreshData` in those tests to keep them deterministic.

    **Final full-unit-suite gate:** Run `pnpm test:unit --run` once at the end of the task to confirm no Phase 6/7 vitest tests regressed (the DecisionRoute placeholder change must NOT break Phase 7's tests — those tests probably grep for the data-testid, which the new component preserves).
  </action>
  <verify>
    <automated>cd frontend && pnpm test:unit src/components/__tests__/CurrentPriceDelta.test.tsx --run && pnpm test:unit --run</automated>
  </verify>
  <done>
    CurrentPriceDelta covers 8 render states (loading + 4 happy variants + partial + full-failure + isError); preserves data-testid in every state. TickerRoute mounts the component; DecisionRoute REPLACES the Phase-7 placeholder. Full vitest suite green (zero Phase 6/7 regressions).
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Playwright resilience E2E spec — refresh failure UX lock</name>
  <files>frontend/tests/e2e/resilience.spec.ts</files>
  <behavior>
    Test surface in `frontend/tests/e2e/resilience.spec.ts` (~3 specs, ~100 LOC):

    1. **refresh_500_does_not_crash_ticker_route** — Use Playwright's `page.route('**/api/refresh*', ...)` to intercept and return HTTP 500 with empty body. Navigate to `/ticker/AAPL/today` (using a fixture date / fixture snapshot — reuse the Phase 6 fixture pattern from existing E2E specs). Assertions:
       - Page does NOT show a global error / white-screen (`page.locator('body')` content includes the AAPL ticker text).
       - The `[data-testid="current-price-placeholder"]` element IS present.
       - Its inner text contains the substring "Refresh unavailable" OR "showing snapshot price".
       - The snapshot-side content (TimeframeCards, OpenClaudePin, PersonaCards, NewsList) all render normally — assert at least 2 of these are visible.

    2. **refresh_500_does_not_crash_decision_route** — Same intercept setup; navigate to `/decision/AAPL/today`. Assertions:
       - RecommendationBanner renders.
       - DriversList renders (DOM check for the existing testid OR content match).
       - DissentPanel renders (existing testid).
       - `[data-testid="current-price-placeholder"]` is present with the "Refresh unavailable" text.
       - NO global error boundary fired.

    3. **refresh_partial_response_renders_price_only** — Intercept returns the locked partial-response shape (HTTP 200, `{ticker: "AAPL", current_price: 178.42, price_timestamp: "2026-05-04T19:32:11+00:00", recent_headlines: [], errors: ["rss-unavailable"], partial: true}`). Navigate to `/ticker/AAPL/today`. Assertions:
       - `[data-testid="current-price-placeholder"]` shows "$178.42" (price renders).
       - Subtle "Headlines unavailable" copy is visible (or omitted per the locked render — match the lock).
       - No banner / error UI fired.

    Use the existing Playwright config at `frontend/playwright.config.ts` (chromium-desktop project for Phase 8 — the mobile-safari + mobile-chrome projects from Phase 6 add value but aren't required for Phase 8 close per VALIDATION.md).
  </behavior>
  <action>
    Create `frontend/tests/e2e/resilience.spec.ts`.

    **File header:**
    ```ts
    // novel-to-this-project — Phase 8 resilience E2E spec. Locks the
    // user-facing failure-mode contract: a refresh fetch failing (5xx /
    // network / partial) MUST NOT crash the page. Snapshot stays canonical;
    // CurrentPriceDelta degrades gracefully.
    ```

    **Spec body (sketch):**
    ```ts
    import { test, expect } from '@playwright/test'

    // Fixture date matches the Phase 6 / Phase 7 E2E pattern. Update the
    // route prefix if existing specs use a different placeholder date.
    const FIXTURE_DATE = 'today'  // or a fixed date if existing specs do
    const FIXTURE_TICKER = 'AAPL'

    test.describe('refresh resilience', () => {
      test('refresh 500 does not crash TickerRoute', async ({ page }) => {
        await page.route('**/api/refresh*', (route) =>
          route.fulfill({ status: 500, body: '' }),
        )
        await page.goto(`/ticker/${FIXTURE_TICKER}/${FIXTURE_DATE}`)

        // Snapshot side renders normally — check at least the ticker hero.
        await expect(page.locator(`text=${FIXTURE_TICKER}`).first()).toBeVisible()

        const placeholder = page.locator('[data-testid="current-price-placeholder"]')
        await expect(placeholder).toBeVisible()
        await expect(placeholder).toContainText(/Refresh unavailable|showing snapshot price/i)

        // No global error UI.
        await expect(page.locator('text=/something went wrong|error boundary/i')).toHaveCount(0)
      })

      test('refresh 500 does not crash DecisionRoute', async ({ page }) => {
        await page.route('**/api/refresh*', (route) =>
          route.fulfill({ status: 500, body: '' }),
        )
        await page.goto(`/decision/${FIXTURE_TICKER}/${FIXTURE_DATE}`)

        // Decision-route core elements still render (Phase 7 contract).
        const placeholder = page.locator('[data-testid="current-price-placeholder"]')
        await expect(placeholder).toBeVisible()
        await expect(placeholder).toContainText(/Refresh unavailable|showing snapshot price/i)

        // RecommendationBanner + DissentPanel still rendered.
        // (Adjust the locators to match the existing testids in Phase 7 specs.)
        await expect(page.getByRole('status')).toBeVisible()  // RecommendationBanner aria
      })

      test('refresh partial response renders price only', async ({ page }) => {
        await page.route('**/api/refresh*', (route) =>
          route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              ticker: FIXTURE_TICKER,
              current_price: 178.42,
              price_timestamp: '2026-05-04T19:32:11+00:00',
              recent_headlines: [],
              errors: ['rss-unavailable'],
              partial: true,
            }),
          }),
        )
        await page.goto(`/ticker/${FIXTURE_TICKER}/${FIXTURE_DATE}`)

        const placeholder = page.locator('[data-testid="current-price-placeholder"]')
        await expect(placeholder).toBeVisible()
        await expect(placeholder).toContainText('$178.42')
      })
    })
    ```

    **Important fixture note:** The existing Phase 6/7 E2E suite uses fixture snapshot data served via either MSW or static `data/{date}/AAPL.json` files. Inspect `frontend/tests/e2e/` for existing specs (e.g. `decision-route.spec.ts`) and clone whichever fixture-loading approach is in use. The new resilience spec does NOT need to set up fresh fixtures — it leverages whatever snapshot path the existing specs already work against; the only NEW interception is the `/api/refresh*` route.

    **Note on placeholder vs replaced UX:** Task 2's CurrentPriceDelta preserves `data-testid="current-price-placeholder"` on the REPLACED element. The Phase 7 spec(s) that grep for that testid + the OLD copy ("Current-price delta arrives via mid-day refresh in Phase 8.") will need to be updated — search Phase 7's E2E specs for that exact string and replace the assertion with one that matches the new component's rendered text. If found, update those assertions in this task.
  </action>
  <verify>
    <automated>cd frontend && pnpm test:e2e --project=chromium-desktop -g 'resilience'</automated>
  </verify>
  <done>
    All 3 resilience specs pass. The 500-intercept tests verify no crash + "Refresh unavailable" copy + snapshot side renders. The partial-response test verifies the happy-degraded path (price renders even when headlines fail). Any Phase 7 E2E spec(s) that asserted the OLD placeholder copy are updated to match the new component's rendered text — full E2E suite green.
  </done>
</task>

</tasks>

<verification>
**Automated (full Wave 1 close):**

```bash
cd frontend
pnpm test:unit --run                                            # full vitest suite
pnpm test:e2e --project=chromium-desktop -g 'resilience'        # Phase 8 resilience
pnpm test:e2e --project=chromium-desktop                        # full chromium E2E (regression)
```

All three must pass. The full E2E run catches any Phase 6/7 spec that needs the placeholder-text assertion updated.

**Frontmatter validation:**

```bash
node "C:/Users/Mohan/.claude/bin/gmd-tools.cjs" frontmatter validate .planning/phases/08-mid-day-refresh-resilience/08-02-frontend-refresh-PLAN.md --schema plan
node "C:/Users/Mohan/.claude/bin/gmd-tools.cjs" verify plan-structure .planning/phases/08-mid-day-refresh-resilience/08-02-frontend-refresh-PLAN.md
```

**Manual (post-deploy — see 08-VALIDATION.md):**
1. Deploy preview, `curl https://<preview>.vercel.app/api/refresh?ticker=AAPL` returns valid JSON within 10s
2. Open `/ticker/AAPL/today` in real browser; observe snapshot price → swap to current within ~3s
3. Switch to `/ticker/MSFT/today`; verify NO flicker (keepPreviousData)
4. Confirm `/api/refresh?ticker=AAPL` returns JSON not HTML (canary for the SPA-rewrite-narrowing fix from Plan 08-01)
</verification>

<success_criteria>
- All 3 tasks pass their automated verify commands
- `frontend/src/schemas/refresh.ts` parses 3 documented response shapes via discriminated union
- `frontend/src/lib/useRefreshData.ts` returns typed data, dedupes by queryKey, retries once, 5-min staleTime, keepPreviousData behavior
- `frontend/src/components/CurrentPriceDelta.tsx` covers loading + 4 happy variants + partial + full-failure + isError; preserves `data-testid="current-price-placeholder"` in every state; uses CSS-variable color tokens only
- `frontend/src/routes/TickerRoute.tsx` mounts the component
- `frontend/src/routes/DecisionRoute.tsx` REPLACES the Phase-7 PHASE-8-HOOK placeholder; the data-testid grep target is preserved
- `frontend/tests/e2e/resilience.spec.ts` 3 specs pass against chromium-desktop
- Full vitest + full chromium E2E both green (zero Phase 6/7 regressions)
- All 3 requirements (REFRESH-02, REFRESH-03, REFRESH-04 frontend) closed; REFRESH-04 fully closed when combined with Plan 08-01's backend half
</success_criteria>

<output>
After completion, create `.planning/phases/08-mid-day-refresh-resilience/08-02-frontend-refresh-SUMMARY.md` documenting:
- 3 tasks executed
- Test counts (~12 vitest + ~8 component + ~2 mount-point + 3 Playwright = ~25 new tests)
- Final line counts (refresh.ts + useRefreshData.ts + CurrentPriceDelta.tsx + resilience.spec.ts production LOC)
- Phase 7 spec adjustments made (which file(s), which assertion(s))
- REFRESH-02, REFRESH-03 marked Complete
- REFRESH-04 marked Complete (combined with 08-01 backend half)
- Confirmation that Plan 08-01's `data-testid="current-price-placeholder"` grep contract was preserved
- Phase 8 closeout note: ROADMAP Phase 8 status flipped to Complete after this plan + Plan 08-01 are both green
</output>
