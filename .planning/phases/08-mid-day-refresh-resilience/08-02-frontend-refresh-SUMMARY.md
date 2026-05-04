---
phase: 08-mid-day-refresh-resilience
plan: 02
subsystem: frontend

tags:
  - tanstack-query
  - zod
  - discriminated-union
  - keep-previous-data
  - playwright
  - resilience
  - notion-clean-palette
  - data-testid-grep-contract
  - dual-route-mount
  - refresh-fallback

requires:
  - phase: 06-frontend-mvp
    provides: fetchAndParse + SchemaMismatchError pattern; TanStack Query setup; Notion-Clean palette tokens; data-testid='ticker-heading' / 'open-claude-pin' Phase 6 grep contracts
  - phase: 07-decision-support-view
    provides: DecisionRoute Phase 7 PHASE-8-HOOK placeholder + data-testid='current-price-placeholder' grep target; recommendation-banner / drivers-list / dissent-panel testids
  - phase: 08-mid-day-refresh-resilience (Wave 0 / Plan 08-01)
    provides: api/refresh.py 3 locked envelope shapes (success / partial / full-failure-without-current_price); SPA-rewrite-narrowing in frontend/vercel.json so /api/* requests don't silently 404 to the SPA HTML shell

provides:
  - frontend/src/schemas/refresh.ts — z.union of Success + Failure variants mirroring api/refresh.py envelopes + isRefreshFailure narrowing
  - frontend/src/lib/useRefreshData.ts — TanStack Query hook with queryKey ['refresh', symbol], staleTime 5min, placeholderData keepPreviousData, retry 1, enabled gate
  - frontend/src/components/CurrentPriceDelta.tsx — 3-branch render component (loading / failure / success+partial); preserves data-testid='current-price-placeholder' in EVERY branch; Notion-Clean palette discipline
  - frontend/src/routes/TickerRoute.tsx — mounts CurrentPriceDelta after OpenClaudePin (section 2b)
  - frontend/src/routes/DecisionRoute.tsx — replaces Phase-7 PHASE-8-HOOK placeholder block with <CurrentPriceDelta /> while preserving the data-testid grep target
  - frontend/tests/e2e/resilience.spec.ts — 3 Playwright specs (500-on-ticker, 500-on-decision, partial-response) closing REFRESH-04
  - 9 vitest cases for CurrentPriceDelta (loading + 4 happy variants + partial + full-failure + isError + isError-no-baseline)
  - 7 vitest cases for useRefreshData (success / error / dedup / staleTime / retry / keepPreviousData / enabled gate)
  - 8 vitest cases for RefreshResponseSchema (3 happy parses + 4 rejection paths + isRefreshFailure narrowing)
  - 1 mount-point test for TickerRoute (new test file) + 1 placeholder-replacement test for DecisionRoute

affects:
  - REFRESH-02, REFRESH-03 closed (frontend deep-dive triggers refresh on open + merges into rendered state)
  - REFRESH-04 fully closed (combined with Wave 0 backend half — frontend now has the resilience.spec.ts lock characterizing the snapshot-stays-canonical-on-refresh-failure UX)
  - frontend/src/routes/__tests__/DecisionRoute.test.tsx — beforeEach added to stub useRefreshData for all existing tests + 6th case asserting Phase-7 placeholder copy GONE
  - Phase 7 decision.spec.ts E2E grep contract — data-testid='current-price-placeholder' preserved (no spec adjustment needed; the testid moved from the placeholder div to CurrentPriceDelta's outer div)

tech-stack:
  added: []  # zero new runtime deps; reuses zod 4 + @tanstack/react-query 5 + @playwright/test (all already in package.json)
  patterns:
    - "z.union over discriminated literals (Success vs Failure variants) — Failure has error: literal(true) + no current_price field; Success may have error absent OR error: false. isRefreshFailure() narrowing helper handles both shapes consistently"
    - "TanStack Query placeholderData: keepPreviousData v5 idiom (NOT keepPreviousData: true — the v4 syntax). Combined with shared queryKey ['refresh', symbol] across TickerRoute + DecisionRoute mount points, gives free dedup + flicker-free symbol swap"
    - "Component-level grep contract preservation: CurrentPriceDelta puts data-testid='current-price-placeholder' on the outer div in EVERY render branch (loading / failure / success). Phase 7 E2E specs that grep the testid stay valid through the placeholder→component swap"
    - "Snapshot-stays-canonical fallback discipline: failure branch (isError OR full-failure envelope) renders snapshotLastPrice baseline + 'Refresh unavailable' muted notice. NEVER throws, NEVER white-screens. The snapshot from the morning routine is the canonical truth; refresh is a 'nice-to-have' overlay"
    - "Chart mock pattern in route tests: vi.mock('@/components/Chart', () => ({ Chart: () => <div data-testid='chart-container' /> })) sidesteps lightweight-charts requiring window.matchMedia + canvas APIs that jsdom doesn't supply. Chart.test.tsx covers the real component"
    - "Permissive headline schema (z.string().min(1) on published_at, NOT z.string().datetime) mirrors snapshot.ts HeadlineSchema discipline — RSS feeds emit RFC-822 alongside ISO-8601; we don't enforce one format and let consumers parse defensively"

key-files:
  created:
    - frontend/src/schemas/refresh.ts — 63 LOC; z.union schema + isRefreshFailure narrowing
    - frontend/src/schemas/__tests__/refresh.test.ts — 120 LOC; 8 schema parse/reject tests
    - frontend/src/lib/useRefreshData.ts — 36 LOC; TanStack Query hook + refreshUrl builder
    - frontend/src/lib/__tests__/useRefreshData.test.ts — 208 LOC; 7 hook behavior tests
    - frontend/src/components/CurrentPriceDelta.tsx — 143 LOC; 3-branch render component
    - frontend/src/components/__tests__/CurrentPriceDelta.test.tsx — 177 LOC; 9 component render tests
    - frontend/src/routes/__tests__/TickerRoute.test.tsx — 107 LOC; new test file (no TickerRoute test existed before — Phase 6 deferred it because lightweight-charts needs jsdom workaround)
    - frontend/tests/e2e/resilience.spec.ts — 106 LOC; 3 Playwright resilience specs
    - .planning/phases/08-mid-day-refresh-resilience/08-02-frontend-refresh-SUMMARY.md (this file)
  modified:
    - frontend/src/routes/TickerRoute.tsx — added CurrentPriceDelta import + section 2b mount (after OpenClaudePin, before TimeframeCards) + layout comment update
    - frontend/src/routes/DecisionRoute.tsx — replaced Phase-7 PHASE-8-HOOK placeholder block (lines 177-190) with <CurrentPriceDelta /> + import; layout comment updated; the grep contract on data-testid='current-price-placeholder' is preserved by the new component
    - frontend/src/routes/__tests__/DecisionRoute.test.tsx — added beforeEach stub for useRefreshData (5 existing tests) + 6th test asserting Phase-7 placeholder copy is GONE while testid stays present

key-decisions:
  - "Used z.union (NOT z.discriminatedUnion) keyed on the `error` flag because the SUCCESS shape may omit `error` entirely OR include it as `error: false`, while FAILURE has `error: literal(true)`. zod's strict discriminator requires the field to be present in EVERY variant — the api/refresh.py builder doesn't write `error: false` on success (it omits the field). z.union tries each variant in order; isRefreshFailure() type guard does the user-facing narrowing."
  - "snapshotLastPrice derives from `snap.ohlc_history[length-1].close` (NOT a hypothetical `snapshot_summary.last_price` field — that field doesn't exist in the v2 SnapshotSchema). The final OHLC bar's close IS the snapshot's canonical baseline price."
  - "Permissive headline `published_at` (z.string().min(1), NOT datetime) — Phase 6's HeadlineSchema in snapshot.ts uses the same permissive shape since RSS feeds emit RFC-822 dates alongside ISO-8601. Strict datetime enforcement here would fail-loud on real-world RSS that the backend already accepts."
  - "Chart component mocked in TickerRoute.test.tsx — lightweight-charts requires window.matchMedia + canvas APIs jsdom doesn't have. The mock returns a div with data-testid='chart-container' so TickerRoute composition is testable; Chart.test.tsx already covers the real chart logic."
  - "Did NOT add the optional 'enabled gate' assertion to vitest's expected count loosely; instead added it as the 7th useRefreshData test ('does_not_fetch_when_symbol_is_empty'). Gives an explicit lock on the `enabled: symbol.length > 0` line so a future refactor that drops it fails the test."

requirements-completed: [REFRESH-02, REFRESH-03, REFRESH-04]

duration: 9min
started: 2026-05-04T18:56:47Z
completed: 2026-05-04T19:05:53Z
---

# Phase 08 Plan 02: Frontend Refresh Integration Summary

**TanStack Query hook (`useRefreshData`) + zod-validated refresh response schema (z.union of Success + Failure variants mirroring api/refresh.py's 3 locked envelopes) + 3-branch CurrentPriceDelta hero component (loading / failure-fallback / success+partial) preserving the Phase-7 `data-testid='current-price-placeholder'` grep contract on the outer div in every render branch — mounted on BOTH TickerRoute (section 2b, after OpenClaudePin) AND DecisionRoute (replacing the Phase-7 PHASE-8-HOOK placeholder), with TanStack Query dedup'ing the fetch via shared `['refresh', symbol]` queryKey + `placeholderData: keepPreviousData` for flicker-free symbol swap + 3 Playwright resilience specs locking the snapshot-stays-canonical-on-refresh-failure UX (closes REFRESH-04 fully).**

## Performance

- **Duration:** ~9 min
- **Started:** 2026-05-04T18:56:47Z
- **Completed:** 2026-05-04T19:05:53Z
- **Tasks:** 3
- **Files created:** 8 production + test files
- **Files modified:** 3 (TickerRoute, DecisionRoute, DecisionRoute.test)

## Accomplishments

- `frontend/src/schemas/refresh.ts` (63 LOC) — z.union of `RefreshSuccessSchema` (current_price + price_timestamp + recent_headlines + errors + partial) and `RefreshFailureSchema` (error: literal(true) + errors + partial: literal(true), no current_price field). `isRefreshFailure(r)` type guard for narrowing. Headline schema permissive on `published_at` (matches Phase 6 snapshot HeadlineSchema discipline).
- `frontend/src/lib/useRefreshData.ts` (36 LOC) — TanStack Query hook with `queryKey: ['refresh', symbol]`, `staleTime: 5*60*1000`, `placeholderData: keepPreviousData` (v5 idiom), `retry: 1`, `enabled: symbol.length > 0`. Calls `fetchAndParse(refreshUrl(symbol), RefreshResponseSchema)` reusing the Phase 6 typed-error pattern.
- `frontend/src/components/CurrentPriceDelta.tsx` (143 LOC) — 3-branch render with `data-testid="current-price-placeholder"` on outer div in EVERY branch:
  - **Loading** (`isPending`): muted "Refreshing {symbol}…" with dashed border (visually distinct from settled states)
  - **Failure** (`isError` OR `isRefreshFailure(data)`): snapshotLastPrice baseline (or `$—` if absent) + muted "Refresh unavailable — showing snapshot price" italic notice
  - **Success/Partial**: hero `$XX.XX` (font-mono, 2xl, semibold) + delta `±X.XX%` (text-bullish / text-bearish / text-fg-muted via the CSS variable tokens — no inline hex anywhere) + "Refreshed Ns ago" footer + "· Headlines unavailable" footnote when `data.partial && errors.includes('rss-unavailable')`
- `frontend/src/routes/TickerRoute.tsx` — mounts `<CurrentPriceDelta />` as section 2b (after OpenClaudePin, before TimeframeCards). `snapshotLastPrice` derives from `snap.ohlc_history[last].close` (the snapshot's canonical baseline price).
- `frontend/src/routes/DecisionRoute.tsx` — replaced the Phase-7 PHASE-8-HOOK placeholder block with `<CurrentPriceDelta />`. The Phase-7 placeholder copy ("Snapshot price as of … ET. Current-price delta arrives via mid-day refresh in Phase 8.") is GONE; the grep contract on `data-testid="current-price-placeholder"` is preserved by the new component.
- TanStack Query queryKey-based dedup verified by test 9 (`dedup_by_query_key`): two `useRefreshData('AAPL')` hooks in the same QueryClient produce ONE network call. This means TickerRoute + DecisionRoute mounted on the same symbol share one fetch (researcher rec #1 lock).
- `frontend/tests/e2e/resilience.spec.ts` 3 Playwright specs cover the snapshot-stays-canonical UX:
  - 500 on TickerRoute → ticker-heading + open-claude-pin still visible; placeholder shows "Refresh unavailable"
  - 500 on DecisionRoute → recommendation-banner + drivers-list + dissent-panel still visible; placeholder shows "Refresh unavailable"
  - Partial response (price OK, RSS unavailable) → "$178.42" + "Headlines unavailable" footnote both visible

## Task Commits

Each task followed RED→GREEN TDD discipline:

1. **Task 1 (refresh.ts schema + useRefreshData hook)**:
   - `bed1c43` — `test(08-02): add failing tests for refresh zod schema + useRefreshData hook` (15 tests)
   - `94d9fdf` — `feat(08-02): refresh zod schema + useRefreshData TanStack hook`
2. **Task 2 (CurrentPriceDelta + dual-route mount)**:
   - `98ef3b4` — `test(08-02): add failing tests for CurrentPriceDelta + dual-route mount` (11 tests: 9 component + 1 TickerRoute + 1 DecisionRoute extension)
   - `0b44525` — `feat(08-02): CurrentPriceDelta component + dual-route mount`
3. **Task 3 (Playwright resilience spec)**:
   - `b1c9241` — `test(08-02): add Playwright resilience E2E spec (refresh failure UX lock)` (3 specs across 3 projects = 9 Playwright cases)

**Plan metadata commit:** (this SUMMARY) — written after STATE.md + ROADMAP.md + REQUIREMENTS.md updates.

## Files Created/Modified

### Created (8)

- `frontend/src/schemas/refresh.ts` — z.union schema + isRefreshFailure narrowing
- `frontend/src/schemas/__tests__/refresh.test.ts` — 8 schema tests
- `frontend/src/lib/useRefreshData.ts` — TanStack Query hook + refreshUrl
- `frontend/src/lib/__tests__/useRefreshData.test.ts` — 7 hook tests
- `frontend/src/components/CurrentPriceDelta.tsx` — 3-branch render component
- `frontend/src/components/__tests__/CurrentPriceDelta.test.tsx` — 9 component tests
- `frontend/src/routes/__tests__/TickerRoute.test.tsx` — new test file with 1 mount-point test (Phase 6 deferred TickerRoute tests because of lightweight-charts jsdom limitations)
- `frontend/tests/e2e/resilience.spec.ts` — 3 Playwright resilience specs
- `.planning/phases/08-mid-day-refresh-resilience/08-02-frontend-refresh-SUMMARY.md` (this file)

### Modified (3)

- `frontend/src/routes/TickerRoute.tsx` — `+CurrentPriceDelta` import + section 2b mount + layout comment update
- `frontend/src/routes/DecisionRoute.tsx` — `+CurrentPriceDelta` import + replaced Phase-7 PHASE-8-HOOK placeholder block; layout comment updated; grep contract preserved
- `frontend/src/routes/__tests__/DecisionRoute.test.tsx` — beforeEach stub for `useRefreshData` (5 existing tests) + 6th case asserting Phase-7 placeholder copy is GONE while testid stays present

## Decisions Made

- **z.union over z.discriminatedUnion.** The `error` flag is NOT a strict discriminator across the 3 locked api/refresh.py envelopes: the SUCCESS shape OMITS `error` entirely (the api builder writes `{partial, errors, current_price, ...}` without an explicit `error` field), while FAILURE writes `error: true`. zod's `discriminatedUnion` requires the discriminator to be present in EVERY variant; `z.union` tries each in order. `isRefreshFailure()` is the user-facing narrowing helper.
- **`snap.ohlc_history[last].close` is the snapshot baseline price.** The plan's `<interfaces>` block referenced a `snapshot.snapshot_summary.last_price` field — that field does NOT exist in the v2 SnapshotSchema. The final OHLC bar's `close` IS the snapshot's canonical baseline price; both TickerRoute + DecisionRoute use this derivation when passing `snapshotLastPrice` to `<CurrentPriceDelta />`.
- **Permissive `published_at` on RefreshHeadline.** Phase 6's `HeadlineSchema` in `snapshot.ts` is intentionally permissive (`z.string()` not `z.string().datetime()`) because RSS feeds emit RFC-822 alongside ISO-8601. Mirrored here. Strict datetime enforcement would have fail-loud-rejected real-world responses the backend accepts.
- **Chart component mocked in TickerRoute.test.tsx.** `lightweight-charts` requires `window.matchMedia` + `devicePixelRatio` observables + canvas/animation-frame APIs that jsdom doesn't supply. Mock returns a `<div data-testid="chart-container" />` so TickerRoute composition is testable. The real Chart logic is exercised by `Chart.test.tsx` (Phase 6).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] TypeScript noUnusedLocals on `now` in TickerRoute.test.tsx**

- **Found during:** Task 2 GREEN — `pnpm typecheck` post-implementation found `'now' is declared but its value is never read` in the new TickerRoute.test.tsx fixture builder.
- **Issue:** Initial fixture builder declared `const now = new Date().toISOString()` but never used it (the `Snapshot` shape doesn't have a top-level `computed_at` field; that lives on per-signal objects).
- **Fix:** Removed the unused declaration.
- **Files modified:** `frontend/src/routes/__tests__/TickerRoute.test.tsx`
- **Verification:** `pnpm typecheck` passes; vitest still green.
- **Committed in:** `0b44525` (Task 2 GREEN commit, included with the route mount changes)

**2. [Rule 3 — Blocking] lightweight-charts canvas/matchMedia error in TickerRoute.test.tsx**

- **Found during:** Task 2 GREEN — first run of TickerRoute.test.tsx threw `TypeError: this._window.matchMedia is not a function` from `fancy-canvas` (a lightweight-charts dep) + `Error: Value is null` from `PriceAxisWidget._internal_optimalWidth`. The test was a brand-new file (no TickerRoute test existed before — Phase 6 deferred it).
- **Issue:** TickerRoute renders the Chart component which boots lightweight-charts; jsdom doesn't supply `window.matchMedia` or canvas/devicePixelRatio observables.
- **Fix:** Added `vi.mock('@/components/Chart', () => ({ Chart: () => <div data-testid="chart-container" /> }))` at the top of TickerRoute.test.tsx — same approach the existing Chart.test.tsx uses for testing the chart component itself in isolation.
- **Files modified:** `frontend/src/routes/__tests__/TickerRoute.test.tsx`
- **Verification:** TickerRoute test now passes; full vitest suite green (260/260).
- **Committed in:** `0b44525` (Task 2 GREEN commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 blocking issues during Task 2's GREEN phase). Both were necessary to make the new TickerRoute.test.tsx file run at all; neither changes the runtime behavior of any production code.

**Impact on plan:** Implementation matches all 7 must-haves locked in the plan frontmatter. Notion-Clean palette discipline holds (every color via CSS-variable tokens). dual-route mount works (verified by useRefreshData dedup test + DecisionRoute mount test + TickerRoute mount test + Playwright resilience specs). REFRESH-04 fully closed (Wave 0 backend half + Wave 1 frontend resilience.spec.ts).

## Issues Encountered

- **No TickerRoute test existed before Wave 1.** Phase 6 (06-04-deep-dive-PLAN.md) deferred the TickerRoute test because lightweight-charts requires jsdom workarounds. Wave 1 needed a TickerRoute test to lock the mount-point assertion (CurrentPriceDelta visible in happy state) — added the file fresh with a Chart mock following the Chart.test.tsx pattern.
- **Phase 7's decision.spec.ts only greps the testid, not the old copy.** Verified up front via `grep -n 'current-price-placeholder|Current-price delta arrives|Snapshot price as of' tests/e2e/`. Result: only one match, the testid grep in decision.spec.ts:53. The new CurrentPriceDelta preserves that testid → no Phase 7 spec adjustment needed.
- **Playwright spec count exceeded the plan's "+2 resilience" estimate.** Plan expected 64 → 66 (+2). Actual: 64 → 72 (+8). Reason: 3 specs × 3 Playwright projects = 9 cases total (chromium-desktop + mobile-safari + mobile-chrome). The plan's per-task verify command targets only `--project=chromium-desktop`, but `playwright.config.ts` runs all 3 projects on `pnpm test:e2e`. All 9 cases pass.

## User Setup Required

None — no external service configuration required. The Vercel function deploys + cold-start timing manual verifications (per 08-VALIDATION.md "Manual-Only Verifications" table) land after the next preview deploy:

1. `curl https://<preview>.vercel.app/api/refresh?ticker=AAPL` returns valid JSON within 10s
2. Open `/ticker/AAPL/today` in real browser; observe snapshot price → swap to current within ~3s
3. Switch to `/ticker/MSFT/today`; verify NO flicker (keepPreviousData)

## Next Phase Readiness

- **Phase 8 fully complete.** Both Wave 0 (backend) and Wave 1 (frontend) plans shipped. REFRESH-01..04 + INFRA-06..07 all closed.
- **Phase 9 (Endorsement Capture) is unblocked** — small, similar to Phase 7 (DecisionRoute extension); the last phase before v1 ships.
- **Test counts at Phase 8 close:**
  - Python pytest: 704 (unchanged from Wave 0; Wave 1 added 0 Python tests, all frontend)
  - vitest: 260 (was 234 before Wave 1, +26)
  - Playwright: 72 (was 64 before Wave 1, +8 net — 9 new cases minus 1 unrelated skip)

## Self-Check: PASSED

- `frontend/src/schemas/refresh.ts` exists ✓
- `frontend/src/lib/useRefreshData.ts` exists ✓
- `frontend/src/components/CurrentPriceDelta.tsx` exists ✓
- `frontend/src/routes/TickerRoute.tsx` mounts CurrentPriceDelta ✓ (verified via grep `<CurrentPriceDelta`)
- `frontend/src/routes/DecisionRoute.tsx` replaces Phase-7 placeholder ✓ (Phase-7 copy gone; testid preserved)
- `frontend/tests/e2e/resilience.spec.ts` exists ✓
- All 5 task commits exist in git log: `bed1c43`, `94d9fdf`, `98ef3b4`, `0b44525`, `b1c9241` ✓
- Per-task verify commands all green:
  - Task 1: `pnpm test:unit src/lib/__tests__/useRefreshData.test.ts src/schemas/__tests__/refresh.test.ts --run` → 15 passed ✓
  - Task 2: `pnpm test:unit src/components/__tests__/CurrentPriceDelta.test.tsx --run && pnpm test:unit --run` → 9 + 260 passed ✓
  - Task 3: `pnpm test:e2e --project=chromium-desktop -g 'resilience'` → 3 passed ✓
- Full vitest suite: 260 passed (234 baseline + 26 new) ✓
- Full Playwright suite: 72 passed across 3 projects (was 64; +8 net) ✓
- Python pytest stays GREEN: 704 passed ✓
- TypeScript typecheck clean (`pnpm typecheck` exits 0) ✓
- Notion-Clean palette discipline: all colors via CSS-variable tokens — verified by inspection of `CurrentPriceDelta.tsx` (text-fg / text-fg-muted / text-bullish / text-bearish / border-border / bg-surface; zero inline hex) ✓

---

*Phase: 08-mid-day-refresh-resilience*
*Plan: 02*
*Completed: 2026-05-04*
