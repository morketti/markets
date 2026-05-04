---
phase: 06-frontend-mvp-morning-scan-deep-dive
plan: 03
subsystem: frontend
tags: [phase-6, wave-2, morning-scan, lens-tabs, position-adjustment, short-term, long-term-thesis, staleness-badge, vitest, playwright, shadcn, radix-tabs, react-router-v7, tanstack-query]

# Dependency graph
requires:
  - phase: 06-frontend-mvp-morning-scan-deep-dive
    provides: Wave 1 frontend scaffold — schemas (SnapshotSchema/StatusSchema/PositionSignalSchema/TickerDecisionSchema with schema_version=2 strict literal); fetchAndParse + URL builders + SchemaMismatchError + FetchNotFoundError; computeStaleness with VIEW-11 6h/24h thresholds; Notion-Clean palette tokens (bg/surface/border/fg/fg-muted/accent/bullish/amber/bearish/grid) as first-class Tailwind utilities; react-router v7 data-router with stub routes; TanStack Query 5 wired
provides:
  - "Morning Scan view at /scan/:date with three lens tabs (Position Adjustment / Short-Term Opportunities / Long-Term Thesis Status), URL-synced via ?lens=position|short|long"
  - "Pitfall #8 / VIEW-01 LOCK: only ONE lens content area in DOM at any time — Radix Tabs.Content default unmounts inactive tabs (no forceMount)"
  - "PositionLens (VIEW-02): filter !data_unavailable, sort by |consensus_score| DESC + alphabetical tiebreak; renders state + score + confidence + ActionHintBadge + EvidenceList top-3"
  - "ShortTermLens (VIEW-03): filter to bullish-direction recommendation (add/buy), sort by short_term.confidence DESC; renders recommendation badge + conviction band + summary + drivers top-5"
  - "LongTermLens (VIEW-04 list portion): filter to thesis_status ∈ {weakening, broken}, sort by severity (broken first) then confidence ASC; renders thesis pill + summary + drivers top-3 — deep-dive content lands in Wave 3"
  - "StalenessBadge.tsx in Root header: GREEN/AMBER/RED via computeStaleness with Notion-Clean palette (bullish/amber/bearish color tokens); injectable now arg for tests; data-level + data-testid attrs for E2E"
  - "loadScanData.useScanData(date) TanStack hook: fans out _status.json + _index.json + per-ticker JSONs via Promise.allSettled; partitions failed (404 / schema-mismatch) tickers into failedTickers array (CONTEXT.md UNIFORM RULE — partial degrade, not crash)"
  - "loadScanData.useHeaderScanMeta(date) hook: lightweight _status + _index pair fetched independently for the staleness badge (decoupled from per-ticker fan-out so badge renders even while snapshots are still in flight)"
  - "ScanRoute.tsx populated: loading skeleton → error UI (FetchNotFoundError → 'No snapshot for date' / SchemaMismatchError → 'Schema upgrade required' explicit banner per CONTEXT.md UNIFORM RULE / generic Error → message) → success state with partial-data banner above LensTabs"
  - "Root.tsx populated: HeaderStaleness component reads :date param via useMatches, fetches via useHeaderScanMeta, renders StalenessBadge (replaces Wave 1 placeholder)"
  - "TickerCard shared row primitive: clickable Link to /ticker/:symbol/:date for all 3 lens rows; Notion-Clean bg-surface + border-border styling; mono-font ticker symbol w-20 shrink-0"
  - "VerdictBadge + ActionHintBadge + EvidenceList visual primitives — composable across Wave 3 deep-dive when persona signal cards land"
  - "shadcn/ui primitives vendored under src/components/ui/ (tabs.tsx + card.tsx + badge.tsx) via pnpm dlx shadcn add — class-variance-authority dep added separately (shadcn add missed it)"
  - "3 fixture JSONs (AAPL/NVDA/MSFT) with full Phase-5 v2 shape: 4 analytical_signals + 6 persona_signals + position_signal + ticker_decision + 30 ohlc_history bars + indicators 5-series + 3 headlines each — round-trip test confirms SnapshotSchema parses cleanly"
  - "Playwright fixtures-server.ts: route() interceptors fulfill raw.githubusercontent.com URLs with local fixture content; run_completed_at patched dynamically so staleness stays GREEN"
  - "5 Playwright E2E specs on chromium-desktop covering: 3 lens tabs visible, default sort (NVDA→AAPL→MSFT by |score|), tab click → URL update + content swap, ?lens=long thesis filter (broken→weakening, intact excluded), staleness badge GREEN, deep-dive link href"
  - "47 new vitest unit tests + 5 fixture round-trip tests + 5 Playwright E2E specs (94→146 unit, 1→6 E2E)"
affects: [06-04-deep-dive, 06-05-polish-responsive]

# Tech tracking
tech-stack:
  added:
    - "@radix-ui/react-tabs ^1.1.13 + @radix-ui/react-slot ^1.2.4 (vendored via shadcn add)"
    - "class-variance-authority ^0.7.1 (required by shadcn badge.tsx — missed by shadcn CLI add)"
    - "@testing-library/user-event ^14.6.1 (required for Radix Tabs pointer-event simulation in jsdom — fireEvent.click alone doesn't trigger Radix's internal state machine)"
    - "msw ^2.14.2 + ~340 transitive deps brought in by shadcn add (msw is unused — vestigial dep added by shadcn registry; can be pruned in Wave 4)"
  patterns:
    - "URL-synced UI state via useSearchParams: ?lens drives Tabs value; setSearchParams with { replace: true } prevents history pollution on tab clicks"
    - "Radix Tabs.Content unmounts inactive tabs by default — DO NOT pass forceMount=true; this is the test-locked invariant for Pitfall #8 / VIEW-01"
    - "Promise.allSettled fan-out for per-ticker fetches → partition into snapshots map + failedTickers array; ScanRoute renders partial-data banner above lens content when failedTickers.length > 0 OR status.partial=true"
    - "Two-query split for the same date: useScanData (heavyweight per-ticker fan-out) + useHeaderScanMeta (lightweight _status + _index) — TanStack cache de-dupes the metadata fetches across hooks"
    - "Notion-Clean palette overrides on shadcn primitives via className prop: shadcn ships with bg-card/bg-muted/bg-primary tokens we don't have; consumers pass explicit bg-surface + border-border + text-fg-muted via className to map onto our @theme tokens"
    - "Test-only export pattern: __loadScanForTest = loadScan exposed from loadScanData.ts — `__` prefix signals internal-for-testing, not part of the public hook surface"
    - "_loadScanFixtures.ts builders (makeStatus / makeIndex / makeSnapshot / makePositionRich) — shared fixture authoring used by both loadScanData unit tests AND lens component tests; one fixture-builder module = byte-identical fixture shape across the test suite"
    - "Fixture-server pattern: page.route() with regex URL match + readFileSync over fixture files at request time + run_completed_at patched dynamically to keep staleness GREEN — no separate HTTP server, no MSW needed"

key-files:
  created:
    - "frontend/src/components/ui/tabs.tsx — vendored shadcn/Radix Tabs primitive (Root/List/Trigger/Content)"
    - "frontend/src/components/ui/card.tsx — vendored shadcn Card primitive (Card/Header/Title/Description/Content/Footer)"
    - "frontend/src/components/ui/badge.tsx — vendored shadcn Badge primitive with cva variants"
    - "frontend/src/components/StalenessBadge.tsx — VIEW-11 header badge: GREEN/AMBER/RED via computeStaleness; data-level + data-testid + title tooltip with snapshot age + partial detail; injectable now arg for deterministic tests"
    - "frontend/src/components/VerdictBadge.tsx — 5-state Verdict color mapping (bullish/strong_bullish→bullish; neutral→fg-muted; bearish/strong_bearish→bearish)"
    - "frontend/src/components/ActionHintBadge.tsx — 4-state ActionHint color mapping (consider_add→bullish; hold_position→fg-muted; consider_trim→amber; consider_take_profits→bearish)"
    - "frontend/src/components/EvidenceList.tsx — top-N truncation with +N more disclosure; mono-font bullets; respects items=[] empty"
    - "frontend/src/components/TickerCard.tsx — shared row primitive: clickable Link to /ticker/:symbol/:date; Notion-Clean bg-surface + border-border; w-20 shrink-0 mono ticker label + flex-1 children slot"
    - "frontend/src/components/LensTabs.tsx — URL-synced 3-tab UI; Radix Tabs.Content default-unmount discipline locked"
    - "frontend/src/components/lenses/PositionLens.tsx — VIEW-02 lens (sort by |consensus_score| DESC + alphabetical tiebreak; render state + action_hint + evidence)"
    - "frontend/src/components/lenses/ShortTermLens.tsx — VIEW-03 lens (filter bullish add/buy; sort by short_term.confidence DESC)"
    - "frontend/src/components/lenses/LongTermLens.tsx — VIEW-04 list portion (filter weakening/broken; sort severity then confidence ASC)"
    - "frontend/src/lib/loadScanData.ts — useScanData + useHeaderScanMeta TanStack hooks; IndexSchema (per-day _index.json shape, distinct from data/_dates.json's DatesIndexSchema); ScanData/ScanIndex/HeaderScanMeta types; __loadScanForTest test-only export"
    - "frontend/src/components/__tests__/StalenessBadge.test.tsx — 6 boundary cases (GREEN <6h, AMBER 12h, RED >24h, AMBER if partial=true, title tooltip surface)"
    - "frontend/src/components/__tests__/TickerCard.test.tsx — 4 cases (mono font on ticker, children slot, href shape, Notion-Clean palette classes)"
    - "frontend/src/components/__tests__/Badges.test.tsx — 7 cases across VerdictBadge + ActionHintBadge color mappings"
    - "frontend/src/components/__tests__/EvidenceList.test.tsx — 5 cases (empty / top-N / +N disclosure / expand-on-click / no-disclosure-when-le-max)"
    - "frontend/src/components/__tests__/LensTabs.test.tsx — 6 cases including the Pitfall #8 / VIEW-01 lock (switching tabs unmounts the previous content)"
    - "frontend/src/components/__tests__/PositionLens.test.tsx — 5 cases (empty / |score| sort / data_unavailable filter / state+action_hint+evidence render / row link href)"
    - "frontend/src/components/__tests__/ShortTermLens.test.tsx — 5 cases (empty / bullish-only filter / confidence DESC sort / recommendation badge + summary / row link)"
    - "frontend/src/components/__tests__/LongTermLens.test.tsx — 5 cases (empty / weakening|broken filter / severity-then-confidence sort / thesis pill + summary / row link)"
    - "frontend/src/lib/__tests__/loadScanData.test.ts — 4 cases (happy fan-out / 404 + schema-mismatch partition / _status.json fetch fails / _index.json schema mismatches)"
    - "frontend/src/lib/__tests__/_loadScanFixtures.ts — shared fixture builders + loadScanModule test-helper"
    - "frontend/src/__tests__/fixtures.test.ts — 5 round-trip tests confirming _status.json + _index.json + AAPL/NVDA/MSFT.json all parse through their respective zod schemas"
    - "frontend/tests/fixtures/scan/_index.json — 3-ticker fixture day 2026-05-04, schema_version=2"
    - "frontend/tests/fixtures/scan/_status.json — happy-path success=true, partial=false, all 3 completed"
    - "frontend/tests/fixtures/scan/AAPL.json — oversold |0.65| consider_add, short_term=add 70, long_term=intact"
    - "frontend/tests/fixtures/scan/NVDA.json — overbought |0.78| consider_take_profits, short_term=take_profits, long_term=broken"
    - "frontend/tests/fixtures/scan/MSFT.json — fair |0.05| hold, short_term=buy 85, long_term=weakening"
    - "frontend/tests/fixtures/scan/_generate.mjs — deterministic fixture generator script (committed alongside JSONs for future schema-bump regeneration)"
    - "frontend/tests/e2e/fixtures-server.ts — Playwright route() interceptors fulfill raw.githubusercontent.com URLs with local fixture content; run_completed_at patched dynamically"
    - "frontend/tests/e2e/scan.spec.ts — 5 Playwright specs on chromium-desktop"
  modified:
    - "frontend/src/routes/Root.tsx — Wave 1 staleness slot placeholder REPLACED with HeaderStaleness component (useMatches → :date → useHeaderScanMeta → StalenessBadge)"
    - "frontend/src/routes/ScanRoute.tsx — Wave 1 stub REPLACED with full Wave 2 implementation: loading/error/partial-banner/LensTabs(3 lens components)"
    - "frontend/package.json — added @radix-ui/react-tabs + @radix-ui/react-slot + class-variance-authority + @testing-library/user-event"
    - "frontend/pnpm-lock.yaml — regenerated"

key-decisions:
  - "Radix Tabs.Content default unmount discipline (no forceMount) = the Pitfall #8 / VIEW-01 lock at the framework layer. Test asserts position-marker NOT in DOM after switching to Short-Term tab — if a future refactor passes forceMount=true, this test breaks immediately"
  - "Two-query split (useScanData for the heavyweight per-ticker fan-out + useHeaderScanMeta for the lightweight metadata pair) — both share TanStack cache for _status.json + _index.json on the same date; staleness badge renders even while per-ticker snapshots are in flight"
  - "shadcn primitives vendored as-is, palette overrides via className. The shadcn defaults (bg-card/bg-muted/bg-primary) DO NOT exist in our Notion-Clean @theme — consumers pass explicit Notion-Clean tokens via className. Trade-off chosen over forking shadcn primitives because: (a) lower drift cost on shadcn updates, (b) consumer components own their visual identity per the Notion-Clean spec"
  - "userEvent dep added for Radix Tabs simulation in jsdom — fireEvent.click does NOT trigger Radix's pointerdown handler; userEvent.click does. The LensTabs 'switching tabs unmounts previous content' test couldn't pass with fireEvent. Future component tests that interact with Radix should default to userEvent"
  - "PositionLens sort tie-break = alphabetical by ticker. Without a tie-break, JS Array.sort is non-stable on equal-|score| rows; alphabetical gives deterministic ordering across reloads"
  - "Filter rule for ShortTermLens = bullish-direction (add/buy) only. The plan's wording ('bullish short_term verdict') resolves to: directionSign(recommendation) > 0. Hold/trim/take_profits/avoid all drop out. The synthesizer's recommendation enum is the source of truth here, not the per-persona verdicts"
  - "LongTermLens severity ordering: broken → weakening → improving → intact → n/a (rank 0..4). Confidence ASC tie-break inside same severity: less confidence on a broken thesis is MORE concerning (the synthesizer is uncertain even though the thesis is breaking — that uncertainty is itself a flag)"
  - "Fixture run_completed_at computed at request time (not stored in fixture file) — keeps staleness badge GREEN regardless of when the fixture file was last regenerated. Otherwise the staleness assertion would flap as the fixture aged on disk"
  - "Test-only export pattern (__loadScanForTest = loadScan): exposes the orchestrator function for unit tests without forcing a TanStack QueryClient setup in jsdom. The `__` prefix signals 'internal' to readers"
  - "EvidenceList max=3 default for PositionLens; max=5 for ShortTermLens drivers; max=3 for LongTermLens drivers — tuned to lens information density (PositionLens has more density via state+score+conf+action_hint, so evidence is tighter)"

requirements-completed: [VIEW-01, VIEW-02, VIEW-03, VIEW-11]

# Metrics
duration: 14min
completed: 2026-05-04
---

# Phase 6 Plan 03: Morning Scan three-lens view Summary

**`/scan/:date` ships with three URL-synced lens tabs (Position Adjustment / Short-Term Opportunities / Long-Term Thesis Status) — Radix Tabs default-unmount enforces Pitfall #8 / VIEW-01 one-lens-at-a-time discipline at the framework layer; PositionLens sorts by |consensus_score| DESC, ShortTermLens filters bullish-direction recommendations and sorts by short_term.confidence DESC, LongTermLens filters thesis_status ∈ {weakening, broken} with broken-first severity sort. StalenessBadge in Root header transitions GREEN/AMBER/RED via computeStaleness on the active :date's _index.json + _status.json. 146 vitest tests + 6 Playwright E2E specs all green on chromium-desktop.**

## Performance

- **Duration:** ~14 min wall-clock (most spent on shadcn `pnpm dlx` + dep resolution + first Playwright failure on the fixture path)
- **Started:** 2026-05-04T14:21:56Z
- **Completed:** 2026-05-04T14:36:02Z
- **Tasks:** 3 (all atomic commits landed)
- **Files created:** 23 (9 components + 8 component tests + 1 hook + 1 hook test + 1 fixture builder + 1 fixture round-trip test + 5 fixture JSONs + 1 fixture generator + 1 Playwright spec + 1 fixture-server helper)
- **Files modified:** 4 (Root.tsx + ScanRoute.tsx + package.json + pnpm-lock.yaml)
- **Tests added:** 47 vitest unit + 5 fixture round-trip + 5 Playwright E2E (all green)

## Accomplishments

- **3-lens Morning Scan view** at `/scan/:date` — three lens tabs URL-synced via `?lens=position|short|long`. ONE lens content area in DOM at any time (Radix Tabs.Content default unmounts inactive tabs — no forceMount). VIEW-01 + Pitfall #8 lock asserted at the test layer (LensTabs test verifies `position-marker` is NOT in DOM after switching to Short-Term tab).
- **PositionLens (VIEW-02 lock)** — filters out tickers with `data_unavailable=true` position_signal; sorts by `Math.abs(consensus_score)` DESCENDING with alphabetical tie-break. Renders per row: state pill + score + confidence + ActionHintBadge + EvidenceList (top 3). Each row is a click-through `<Link>` to `/ticker/:symbol/:date`. Empty state: `"No position-adjustment data for this date."`
- **ShortTermLens (VIEW-03 lock)** — filters to bullish-direction recommendation (`add` or `buy`); sorts by `short_term.confidence` DESC with alphabetical tie-break. Renders recommendation badge (color-coded by direction) + conviction band + summary + drivers (top 5). Excludes hold/trim/take_profits/avoid by design.
- **LongTermLens (VIEW-04 list-view portion)** — filters to `thesis_status ∈ {weakening, broken}`; sorts by severity rank (broken=0 < weakening=1) then `long_term.confidence` ASC. Renders thesis_status pill + summary + drivers (top 3). Wave 3's deep-dive will hang off the click-through link.
- **StalenessBadge in Root header** — replaces Wave 1's placeholder div. Reads `:date` param via `useMatches` (handles both `/scan/:date` and `/ticker/:symbol/:date?` routes), fetches `_index.json` + `_status.json` via `useHeaderScanMeta` (lightweight pair, decoupled from per-ticker fan-out), pipes `index.run_completed_at` + `status.partial` into the existing `computeStaleness` from Wave 1. Color tokens: bullish (GREEN), amber (AMBER), bearish (RED). Hover tooltip surfaces snapshot age + partial detail.
- **`loadScanData.useScanData(date)` TanStack hook** — orchestrates the fan-out: `Promise.all([statusUrl, indexUrl])` for metadata, then `Promise.allSettled(per-ticker fetches)`. Failed tickers (404 or schema-mismatch) partition into `failedTickers` array — never crashes the whole view. Returns `ScanData = { status, index, snapshots, failedTickers }`.
- **`ScanRoute.tsx` Wave 2 implementation** — replaces Wave 1 stub. Loading state shows `"Loading scan…"`. Error states are typed: `FetchNotFoundError` → `"No snapshot for {date}"`; `SchemaMismatchError` → `"Schema upgrade required"` explicit banner per CONTEXT.md UNIFORM RULE; generic `Error` → message surface. Success state: heading + ticker count + lite-mode badge + partial-data banner (when `status.partial || failedTickers.length > 0`) + `<LensTabs>` with the 3 lens components.
- **Notion-Clean palette honored everywhere**: every component uses tokens from `src/index.css @theme` (`bg-bg`, `bg-surface`, `border-border`, `text-fg`, `text-fg-muted`, `text-accent`, `text-bullish`, `text-amber`, `text-bearish`). Zero ad-hoc hex codes. shadcn primitive defaults (`bg-card`, `bg-muted`, `bg-primary`) overridden via className at every consumption site.
- **shadcn/ui primitives vendored** under `src/components/ui/` — `tabs.tsx` (Radix Tabs Root/List/Trigger/Content), `card.tsx` (Card/Header/Title/Description/Content/Footer), `badge.tsx` (with cva variants). Brought in via `pnpm dlx shadcn@latest add tabs card badge --yes --overwrite`.
- **3 fixture JSONs** (AAPL, NVDA, MSFT) at `frontend/tests/fixtures/scan/` — full Phase-5 v2 shape: 4 analytical_signals + 6 persona_signals (incl claude_analyst — required by AnalystId Literal Phase 5 widening) + position_signal + ticker_decision + 30 ohlc_history bars + indicators 5-series + 3 headlines each. Designed for lens-specific assertions: NVDA wins PositionLens (|0.78| > AAPL |0.65| > MSFT |0.05|); MSFT wins ShortTermLens (buy 85 > AAPL add 70; NVDA take_profits excluded); NVDA broken first in LongTermLens then MSFT weakening (AAPL intact excluded).
- **`_generate.mjs` fixture-generator script** committed alongside the JSONs — deterministic regeneration if SnapshotSchema ever bumps shape. Single source of truth.
- **5 vitest fixture round-trip tests** at `src/__tests__/fixtures.test.ts` — guarantee every fixture parses through `SnapshotSchema` / `StatusSchema` / `IndexSchema`. If a future schema bump breaks fixtures, this test fails immediately rather than the Playwright E2E flaking later.
- **`tests/e2e/fixtures-server.ts` Playwright helper** — `mountScanFixtures(page)` registers `page.route()` interceptors that fulfill `raw.githubusercontent.com` URL patterns with local fixture content; `run_completed_at` patched dynamically at request time so staleness stays GREEN regardless of fixture file age. No separate HTTP server needed; no MSW needed.
- **5 Playwright E2E specs** on chromium-desktop covering: 3 lens tabs visible + default sort (NVDA→AAPL→MSFT); tab click → URL update + content swap (one-lens-at-a-time); `?lens=long` thesis filter (NVDA broken→MSFT weakening, AAPL intact excluded); StalenessBadge GREEN; row click-through to `/ticker/:symbol/:date`. All green in 5.1s combined.
- **146 total vitest tests** across 18 test files (94 Wave 1 baseline + 47 Wave 2 component/hook + 5 Wave 2 fixture round-trip). Total Playwright: 6 specs (1 smoke + 5 morning-scan), all green on chromium-desktop. typecheck + build clean.

## Task Commits

1. **Task 1: Vendor shadcn primitives + StalenessBadge + TickerCard + supporting badges** — `385fb23` (feat)
2. **Task 2: Morning Scan route with 3 URL-synced lenses + staleness badge wiring** — `03e4dd9` (feat)
3. **Task 3: Scan fixtures + Playwright E2E for 3-lens UI** — `5bf032f` (test)

## Files Created/Modified

See `key-files` block in frontmatter above (23 files created; 4 modified). All committed atomically per task.

## Decisions Made

See `key-decisions` block in frontmatter above (10 decisions captured). Highlights:

- **Radix Tabs default-unmount = the Pitfall #8 lock at the framework layer.** We deliberately do NOT pass `forceMount` to TabsContent — Radix unmounts inactive tabs by default. The LensTabs test asserts the previous lens marker is NOT in DOM after switching tabs; if any future refactor breaks this invariant (e.g. someone adds `forceMount` for animation), the test breaks loudly.
- **Two-query split** (`useScanData` heavyweight + `useHeaderScanMeta` lightweight) — both share TanStack cache for `_status.json` + `_index.json` on the same date. Staleness badge renders even while per-ticker snapshots are in flight; no hard coupling between the badge and the lens fan-out.
- **shadcn palette overrides via className** — shadcn defaults (`bg-card`, `bg-muted`, `bg-primary`) don't exist in our Notion-Clean `@theme`. Rather than fork the primitives, every consumer passes Notion-Clean tokens (`bg-surface`, `border-border`, `text-fg-muted`, etc.) via className. Trade-off: lower drift cost on shadcn updates vs. the cost of remembering to pass overrides at each consumption site (mitigated by the visual primitives — TickerCard, the badges — encapsulating this once).
- **userEvent for Radix Tabs simulation in jsdom** — `fireEvent.click` doesn't trigger Radix's pointerdown handler; `userEvent.click` does. Future component tests touching Radix should default to userEvent.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] `class-variance-authority` dep missing after `shadcn add`**

- **Found during:** Task 1 first build attempt
- **Issue:** `pnpm dlx shadcn@latest add tabs card badge --yes --overwrite` vendored the primitive files and added `@radix-ui/react-tabs` + `@radix-ui/react-slot` to `package.json`, but the `badge.tsx` it generated imports `class-variance-authority` (`cva`) and that dep wasn't added. Build would fail at runtime with `Cannot find module 'class-variance-authority'`.
- **Fix:** `pnpm add class-variance-authority` — added v0.7.1.
- **Files modified:** `frontend/package.json` + `frontend/pnpm-lock.yaml`
- **Verification:** `pnpm build` produces clean dist/; `pnpm typecheck` passes; component tests touching Badge pass.
- **Committed in:** `385fb23` (Task 1)

**2. [Rule 3 — Blocking] `@testing-library/user-event` dep missing for Radix Tabs simulation**

- **Found during:** Task 2 first run of LensTabs test "switching tabs unmounts the previous content"
- **Issue:** `fireEvent.click` on a Radix Tabs.Trigger does NOT dispatch the `pointerdown` event that Radix's internal state machine watches for. The test fired the click but Radix didn't propagate the value change → `onValueChange` didn't fire → `setSearchParams` didn't trigger a re-render → the previous lens content stayed in DOM. The test reported "element(s) not found" for the new lens content.
- **Fix:** `pnpm add -D @testing-library/user-event` (v14.6.1). Replaced `fireEvent.click(...)` with `await user.click(...)` where `user = userEvent.setup()`. userEvent dispatches the full pointerdown + click + focus sequence Radix needs.
- **Files modified:** `frontend/package.json` + `frontend/pnpm-lock.yaml` + `frontend/src/components/__tests__/LensTabs.test.tsx`
- **Verification:** All 6 LensTabs tests pass after the fix.
- **Committed in:** `03e4dd9` (Task 2)

**3. [Rule 3 — Blocking] Playwright fixture-server `FIX_DIR` path resolved incorrectly**

- **Found during:** Task 3 first Playwright run
- **Issue:** `fixtures-server.ts` lives at `frontend/tests/e2e/`. Fixtures live at `frontend/tests/fixtures/scan/`. Initial code: `const FIX_DIR = resolve(__dirname, 'fixtures/scan')` → resolved to `frontend/tests/e2e/fixtures/scan` (non-existent). All 5 E2E specs failed with `ENOENT: no such file or directory`.
- **Fix:** Changed to `resolve(__dirname, '..', 'fixtures', 'scan')` to step up one level from `e2e/` to `tests/`.
- **Files modified:** `frontend/tests/e2e/fixtures-server.ts`
- **Verification:** All 5 morning-scan E2E specs pass after the fix.
- **Committed in:** `5bf032f` (Task 3)

### Plan Wording Refinements (Honored CONTEXT.md Locks Over Plan Implementation Sketch)

**4. ScanRoute partial banner appears WHEN status.partial OR failedTickers.length > 0**

The plan's pseudocode showed `partial = data.status.partial || data.failedTickers.length > 0` — implemented exactly as spec'd. However the plan also said "Wave 1 stubs (ScanRoute placeholder) replaced with real content" — the heading "Morning Scan — {date}" stays in the loading + error + success states (so the Wave 1 smoke E2E that asserts the heading still passes — no regression).

**5. Tabs primitive uses bg-bg for the active tab background, not a fully-saturated surface**

The plan said "Notion-Clean accent color (#5B9DFF underline)" — this implementation uses `data-[state=active]:text-accent` for the text and `data-[state=active]:bg-bg` for the active tab background (sets it back to the page background, which makes it look like a "lifted" tab against the bg-surface tab strip). Visually this is a Notion/Linear-style flat tab treatment; the underline accent comes from text-accent.

### Toolchain Notes

- **shadcn add brought in ~340 transitive deps** via the registry — including `msw@2.14.2` which we don't currently use. msw's postinstall script is gated behind `pnpm.onlyBuiltDependencies` (currently `["esbuild"]`), so it's "ignored builds" — non-issue for now. Wave 4 may prune msw if we don't end up needing it.
- **Windows line-ending warnings** during `git add` (LF will be replaced by CRLF) — Windows-default behavior; non-issue (git auto-normalizes on checkout).
- **`.planning/config.json` left unstaged** per context_handoff instruction — auto-mode flag toggle, separate concern.

---

**Total deviations:** 3 auto-fixed (3 Rule 3 blocking — 2 missing deps + 1 path resolution) + 2 plan-wording refinements. Zero scope creep — all fixes tighten the locked plan scope.

## Issues Encountered

None — plan executed end-to-end without architectural decisions, auth gates, or unresolvable failures. All 3 deviations were auto-fixable toolchain quirks (shadcn skipping cva, jsdom + Radix needing userEvent, fixture path off-by-one) caught during the first verify-command run on each task.

## User Setup Required

None — no external services configured in Wave 2. Wave 4 will close out INFRA-05 (Vercel deploy + real GitHub raw URL).

## Next Phase Readiness

**Ready for Plan 06-04 (Per-Ticker Deep-Dive — Wave 3):**

- All 3 lens row click-throughs already deep-link to `/ticker/:symbol/:date` — Wave 3 just populates `TickerRoute.tsx` (still a Wave 1 stub) with the full deep-dive view.
- Fixture shape (`AAPL.json` / `NVDA.json` / `MSFT.json` with full v2 envelope including OHLC + indicators + headlines + persona_signals + ticker_decision) is exactly what Wave 3's deep-dive consumes — Wave 3's tests can re-use the same fixtures via the same `mountScanFixtures` pattern.
- TickerCard + ActionHintBadge + VerdictBadge + EvidenceList primitives are reusable across Wave 3's PersonaCard + TimeframeCard.
- shadcn `card.tsx` + `badge.tsx` already vendored; Wave 3 will pull `tooltip` + `dialog` (or `sheet`) for the Open Claude Analyst pinned section + chart overlay popovers.
- `useScanData` hook returns `ScanData.snapshots[ticker]` — Wave 3 reads `snapshots[symbol]` for the deep-dive, so no new fetch layer needed.
- StalenessBadge already in Root header — picks up `:date` from `/ticker/:symbol/:date?` route too (useMatches scans full hierarchy).

**No blockers for Wave 3.** Plan 06-03 closes complete.

## Self-Check: PASSED

Verified at completion:

| Claim | Verification |
|---|---|
| 3 task commits exist (feat 06-03 / feat 06-03 / test 06-03) | `git log --oneline -3` → 5bf032f / 03e4dd9 / 385fb23 |
| `frontend/src/components/StalenessBadge.tsx` created | path exists; data-level + data-testid wired; computeStaleness imported |
| `frontend/src/components/LensTabs.tsx` created | path exists; useSearchParams + Tabs primitive composed; no forceMount |
| 3 lens components created | `frontend/src/components/lenses/{PositionLens,ShortTermLens,LongTermLens}.tsx` — all exist |
| `frontend/src/lib/loadScanData.ts` created | exports useScanData + useHeaderScanMeta + IndexSchema + ScanData/ScanIndex types + __loadScanForTest |
| `frontend/src/routes/ScanRoute.tsx` populated | Wave 1 stub replaced with full Wave 2 implementation |
| `frontend/src/routes/Root.tsx` populated | HeaderStaleness component added; calls useHeaderScanMeta |
| 3 fixture JSONs round-trip through SnapshotSchema | `pnpm test:unit src/__tests__/fixtures.test.ts --run` → 5 passed |
| Playwright E2E green on chromium-desktop | `pnpm test:e2e --project=chromium-desktop -g 'morning scan'` → 5 passed (5.1s) |
| Smoke E2E still green (no regression) | `pnpm test:e2e --project=chromium-desktop` → 6 passed (1 smoke + 5 morning scan) |
| 146 vitest tests pass | `pnpm test:unit --run` → Test Files 18 passed (18) / Tests 146 passed (146) |
| typecheck clean | `pnpm typecheck` exits 0 |
| build clean | `pnpm build` produces dist/index.html + dist/assets/index-*.css (17.72 kB) + dist/assets/index-*.js (452.39 kB) |
| Notion-Clean palette honored | every component uses bg-bg/bg-surface/border-border/text-fg/text-fg-muted/text-accent/text-bullish/text-amber/text-bearish — zero ad-hoc hex codes |

---
*Phase: 06-frontend-mvp-morning-scan-deep-dive*
*Completed: 2026-05-04*
