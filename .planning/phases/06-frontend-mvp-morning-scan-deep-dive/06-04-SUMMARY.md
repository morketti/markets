---
phase: 06-frontend-mvp-morning-scan-deep-dive
plan: 04
subsystem: frontend
tags: [phase-6, wave-3, deep-dive, ticker-route, lightweight-charts-v5, persona-cards, open-claude-pin, news-list, dual-timeframe, search-typeahead, vitest, playwright]

# Dependency graph
requires:
  - phase: 06-frontend-mvp-morning-scan-deep-dive
    provides: Wave 1 schemas (SnapshotSchema/AgentSignal/PositionSignal/TickerDecision incl. ThesisStatus + TimeframeBand) + fetchSnapshot (FetchNotFoundError/SchemaMismatchError/snapshotUrl) + Notion-Clean palette tokens (bg/surface/border/fg/fg-muted/accent/bullish/amber/bearish/grid)
  - phase: 06-frontend-mvp-morning-scan-deep-dive
    provides: Wave 2 visual primitives (TickerCard / VerdictBadge / ActionHintBadge / EvidenceList / StalenessBadge) + shadcn primitives (tabs / card / badge) + AAPL/NVDA/MSFT fixture pattern + mountScanFixtures Playwright helper
provides:
  - "URL `/ticker/:symbol/:date?` renders Per-Ticker Deep-Dive view; `:date` defaults to 'today'"
  - "OpenClaudePin pinned at TOP of deep-dive (per VIEW-09 + user MEMORY.md feedback_claude_knowledge): always rendered with accent border + accent-tinted bg (border-accent/40 bg-accent/5); muted 'data unavailable' state when claude_analyst signal is missing OR data_unavailable=True"
  - "VIEW-09 SEPARATION LOCK: claude_analyst rendered SEPARATELY by OpenClaudePin; PersonaCards grid filters it out → exactly 5 cards (buffett/munger/wood/burry/lynch); never silently absent"
  - "Chart.tsx — lightweight-charts 5.2 v5-API React wrapper rendering OHLC candlesticks + MA20 line + MA50 line + Bollinger upper/lower (dotted) + RSI(14) sub-pane; Notion-Clean dark theme (gridlines #252628, candles #4ADE80/#F87171, MA20 accent #5B9DFF, MA50 muted #8B8E94, RSI amber #FBBF24)"
  - "v5 API used (chart.addSeries(CandlestickSeries, options) + chart.addSeries(LineSeries, options)) — NOT v4 addCandlestickSeries/addLineSeries which were replaced in lightweight-charts 5.0"
  - "pairLines() helper drops null entries from indicator series (warmup periods — MA50 has 50 leading nulls, RSI(14) has 14, etc.) so setData receives only valid points; aligned 1:1 to ohlc_history dates"
  - "PersonaCard renders 1 persona AgentSignal as a card; PERSONA_LABEL maps the 5 canonical investor analyst_ids (buffett→'Warren Buffett' etc.); evidence[0] doubles as reasoning summary + EvidenceList for drivers; muted body when data_unavailable=true"
  - "TimeframeCard (VIEW-05) renders short_term/long_term TimeframeBand with thesis_status pill (intact/improving=bullish, weakening=amber, broken=bearish, n/a=fg-muted), confidence, summary, top-5 drivers"
  - "AnalyticalSignalCard renders 1 of 4 analytical signals (fundamentals/technicals/news_sentiment/valuation) with analyst_id as caption (more compact than PersonaCard)"
  - "NewsList (VIEW-08) groups headlines by source, sorts within group by published_at DESC, renders target='_blank' rel='noopener noreferrer' links; NEW tag on headlines published after snapshot.computed_at"
  - "loadTickerData.useTickerData(date, symbol) TanStack hook — fetches data/{date}/{ticker}.json via fetchAndParse + SnapshotSchema; queryKey ['ticker', date, symbol]"
  - "TickerRoute composes 7 sections top-down: Heading → OpenClaudePin → 2 TimeframeCards (lg:flex-row) → Chart → 5 PersonaCards (md:grid-cols-2 xl:grid-cols-3) → 4 AnalyticalSignalCards (lg:grid-cols-4) → NewsList grouped by source"
  - "Loading + error states in TickerRoute (FetchNotFoundError → '{ticker} not in snapshot' / SchemaMismatchError → 'Schema upgrade required' explicit banner per CONTEXT.md UNIFORM RULE / generic Error → message)"
  - "VIEW-13 ticker search input in Root header — Enter navigates to /ticker/:typed/:date; uppercases input at submit time; uses active :date from useMatches (handles both /scan/:date and /ticker/:symbol/:date?)"
  - "AAPL fixture extended from 3 → 9 headlines across 3 sources (Yahoo Finance / Reuters / Bloomberg RSS, 3 each, varying published_at) for the NewsList grouping E2E assertion"
  - "Separator shadcn primitive vendored (src/components/ui/separator.tsx + @radix-ui/react-separator dep)"
  - "12 new vitest unit tests + 4 new lib tests + 6 new Playwright deep-dive E2E specs (146 → 179 unit; 6 → 12 E2E on chromium-desktop)"
affects: [06-05-polish-responsive]

# Tech tracking
tech-stack:
  added:
    - "@radix-ui/react-separator (vendored via shadcn add separator)"
  patterns:
    - "lightweight-charts 5.2 v5 API: chart.addSeries(SeriesDefinition, options) replaces v4's chart.addCandlestickSeries() / chart.addLineSeries()"
    - "pairLines() invariant: indicator arrays are aligned 1:1 to ohlc_history by index; warmup nulls dropped before setData (filter Number.isFinite(v))"
    - "RSI sub-pane via priceScaleId='rsi' + scaleMargins {top: 0.78, bottom: 0} → bottom ~22% of chart"
    - "ResizeObserver in Chart's useEffect keeps chart width matched to container"
    - "OpenClaudePin signal: AgentSignal | undefined union (NOT just AgentSignal) — the slot ALWAYS renders, signal=undefined branch shows muted state. data-muted='true|false' attribute exposed for E2E"
    - "PersonaCards grid filter: persona_signals.filter(p => p.analyst_id !== 'claude_analyst') — VIEW-09 separation lock at the React layer; deep-dive E2E asserts 5 cards (not 6) and that no card has data-persona='claude_analyst'"
    - "Headline group-by-source: Map<source, Headline[]> + within-group sort by published_at DESC via String#localeCompare (works for ISO-8601; RFC-822 falls back to lexicographic which is acceptable for v1)"
    - "TickerSearch input: inputRef + onKeyDown(Enter) → navigate(/ticker/${value.toUpperCase()}/${date}). Active :date detected via useMatches (works for both /scan/:date and /ticker/:symbol/:date? routes)"

key-files:
  created:
    - "frontend/src/components/Chart.tsx — lightweight-charts 5.2 v5-API wrapper; OHLC candlesticks + MA20/MA50/BB upper/lower + RSI(14) sub-pane; reads from snapshot.indicators (Wave 0 pre-computed series); ResizeObserver + chart.remove cleanup"
    - "frontend/src/components/PersonaCard.tsx — 1 persona AgentSignal as a card; PERSONA_LABEL maps 5 canonical investor analyst_ids to friendly names; muted body when data_unavailable=true"
    - "frontend/src/components/OpenClaudePin.tsx — VIEW-09 lock pinned at TOP; accent border + accent-tinted bg; ALWAYS renders (signal=undefined OR data_unavailable=true → muted state)"
    - "frontend/src/components/TimeframeCard.tsx — VIEW-05 dual-timeframe; thesis_status pill color-mapped (intact/improving=bullish, weakening=amber, broken=bearish, n/a=fg-muted)"
    - "frontend/src/components/AnalyticalSignalCard.tsx — 1 of 4 analytical signals; analyst_id as caption (Fundamentals/Technicals/News & Sentiment/Valuation); compact"
    - "frontend/src/components/NewsList.tsx — VIEW-08 headlines grouped by source, sorted by published_at DESC; NEW tag for headlines newer than snapshotComputedAt; target='_blank' rel='noopener noreferrer' links"
    - "frontend/src/components/ui/separator.tsx — shadcn Separator primitive (Radix-based hairline divider)"
    - "frontend/src/components/__tests__/Chart.test.tsx — 6 mock-based tests; lightweight-charts vi.mock factory records setData/addSeries/priceScale.applyOptions calls"
    - "frontend/src/components/__tests__/PersonaCard.test.tsx — 4 cases (label mapping for 5 personas / verdict + reasoning / data_unavailable muted body / data-persona attr)"
    - "frontend/src/components/__tests__/OpenClaudePin.test.tsx — 5 cases including VIEW-09 always-renders invariant for signal=undefined AND data_unavailable=true; visual lock asserts border-accent/40 bg-accent/5 classes"
    - "frontend/src/components/__tests__/TimeframeCard.test.tsx — 8 cases (label/badge/conf/summary; drivers cap at 5; 5 thesis_status color mappings via it.each)"
    - "frontend/src/components/__tests__/NewsList.test.tsx — 6 cases (empty / group by source / sort published_at DESC / NEW tag for post-snapshot / target=_blank rel=noopener / heading uppercase)"
    - "frontend/src/lib/loadTickerData.ts — useTickerData TanStack hook; __loadTickerForTest test-only export"
    - "frontend/src/lib/__tests__/loadTickerData.test.ts — 4 cases (happy / 404 → FetchNotFoundError / wrong shape → SchemaMismatchError / schema_version=1 → SchemaMismatchError)"
    - "frontend/tests/e2e/deep-dive.spec.ts — 6 Playwright specs on chromium-desktop covering full deep-dive flow + VIEW-13 ticker search"
  modified:
    - "frontend/src/routes/TickerRoute.tsx — Wave 1 stub REPLACED with full Wave 3 deep-dive composition (7 sections top-down)"
    - "frontend/src/routes/Root.tsx — TickerSearch input added in header; Enter → navigate(/ticker/:typed/:date); uppercases input"
    - "frontend/tests/fixtures/scan/AAPL.json — headlines extended from 3 → 9 (3 sources × 3 each) for NewsList grouping E2E"
    - "frontend/package.json + frontend/pnpm-lock.yaml — @radix-ui/react-separator added via shadcn add"

key-decisions:
  - "lightweight-charts v5 API used (chart.addSeries(CandlestickSeries, options) + chart.addSeries(LineSeries, options)) — NOT the v4 addCandlestickSeries/addLineSeries methods shown in the plan's pseudocode. v4 methods were replaced in 5.0; using them produces TypeScript errors. Plan pseudocode was outdated; this is Rule 1 (bug) auto-fix at scaffold time."
  - "OpenClaudePin signal prop typed as AgentSignal | undefined (not just AgentSignal) — the VIEW-09 lock requires the slot ALWAYS render, including when claude_analyst is missing entirely from persona_signals (lite-mode skipped, schema_failure default). The component handles both cases (undefined signal OR data_unavailable=true) via a single muted={!signal || signal.data_unavailable} branch."
  - "PersonaCard reasoning sourcing: evidence[0] = reasoning summary; evidence[1..] = drivers passed to EvidenceList. The persona prompts in prompts/personas/*.md don't have a separate reasoning field — they output a free-form 'reasoning' first-line followed by structured drivers, all packed into evidence[]. v1.x can split this into AgentSignal.reasoning vs evidence cleanly; v1 stays compatible with the existing Phase 5 schema."
  - "RSI sub-pane via priceScaleId='rsi' (not a separate IPaneApi) + scaleMargins {top: 0.78, bottom: 0} — gives RSI the bottom ~22% of the chart in a single chart instance. lightweight-charts v5 supports panes formally via paneIndex parameter, but for v1 the priceScaleId approach is simpler and renders correctly. v1.x can switch to formal panes if RSI rendering needs improvement."
  - "Chart unit tests via vi.mock('lightweight-charts') with a manual factory — jsdom lacks WebGL/canvas. The mock records setData/addSeries/priceScale.applyOptions calls; tests assert call shape (e.g. 11 non-null pairs after dropping 19 leading nulls in a warmup-30 fixture). This is faster + more reliable than headless-canvas mocking."
  - "VIEW-13 ticker search v1 surface: direct text→/ticker/:symbol navigation on Enter, uppercased at submit time. Company-name fuzzy match deferred to v1.x — yfinance ticker symbols ARE the v1 search surface (the routine consumes ticker symbols, the storage uses them as filenames). Building a separate company-name index for v1 is premature; deferred per plan footnote."
  - "Active date detection in TickerSearch via useMatches (not useParams) — useParams only sees the params for the CURRENT route; the search lives in Root which is the parent layout, not a leaf route. useMatches scans the full matched hierarchy and finds :date from /scan/:date or /ticker/:symbol/:date?. Pattern was already established in HeaderStaleness (Wave 2)."
  - "AAPL fixture extended in-place (not regenerated via _generate.mjs) for the news-grouping E2E. _generate.mjs is the source of truth for SnapshotSchema regeneration, but the headlines section is a hand-curated v1.x candidate (real news fetcher will generate this in prod). Extension stayed minimal: 3 sources × 3 headlines each, varying published_at for sort assertion."
  - "Notion-Clean palette tokens duplicated in PALETTE const inside Chart.tsx — lightweight-charts options take raw hex strings (no CSS-variable interpolation at chart-init time). The PALETTE const is kept in sync manually with src/index.css @theme tokens; if the palette ever changes, both files update together. Trade-off: minor DRY violation for the chart's runtime correctness."
  - "Playwright fail-on-stale-build pattern recognized: pnpm test:e2e uses reuseExistingServer=true (locally; CI is false) which serves dist/ as built. After modifying TickerRoute the first E2E run failed because preview was serving the OLD bundle. Rule 3 auto-fix: pnpm build before re-running. v1.x can wire this into a npm script (test:e2e:fresh = pnpm build && pnpm test:e2e) if the foot-gun reoccurs."

requirements-completed: [VIEW-04, VIEW-05, VIEW-06, VIEW-07, VIEW-08, VIEW-09, VIEW-12, VIEW-13]

# Metrics
duration: 13min
completed: 2026-05-04
---

# Phase 6 Plan 04: Per-Ticker Deep-Dive Summary

**`/ticker/:symbol/:date?` ships with 7 stacked sections — OpenClaudePin pinned at TOP (VIEW-09 + user MEMORY.md lock: ALWAYS rendered, never silently absent), 2 TimeframeCards side-by-side (VIEW-05 — short_term + long_term with thesis_status pills), Chart.tsx via lightweight-charts 5.2 v5-API rendering OHLC candlesticks + MA20/MA50/BB upper-lower/RSI(14) sub-pane (VIEW-06), 5 PersonaCards in grid (claude_analyst FILTERED OUT — VIEW-09 separation lock at React layer), 4 AnalyticalSignalCards, NewsList grouped by source with NEW tag for post-snapshot headlines (VIEW-08). Header gets VIEW-13 ticker search input — Enter navigates to /ticker/:typed/:date with uppercase normalization. 179 vitest tests (146 → 179) + 12 Playwright E2E specs on chromium-desktop (6 → 12) all green.**

## Performance

- **Duration:** ~13 min wall-clock
- **Started:** 2026-05-04T14:44:39Z
- **Completed:** 2026-05-04T14:57:28Z
- **Tasks:** 3 (all atomic commits landed)
- **Files created:** 14 (5 components + 4 component tests + 1 hook + 1 hook test + 1 shadcn ui primitive + 1 Playwright spec + 1 SUMMARY)
- **Files modified:** 4 (TickerRoute.tsx + Root.tsx + AAPL fixture + package.json/pnpm-lock.yaml from shadcn add)
- **Tests added:** 12 vitest unit (Chart 6 + PersonaCard 4 + OpenClaudePin 5 + TimeframeCard 8 + NewsList 6) + 4 lib (loadTickerData) + 6 Playwright E2E (deep dive)

## Accomplishments

- **`/ticker/:symbol/:date?` Per-Ticker Deep-Dive ships** — 7 sections stacked top-down per user MEMORY.md "Claude reasoning surfaced alongside personas, never replaced". Wave 1 stub REPLACED with full Wave 3 composition.
- **VIEW-09 + user MEMORY.md LOCK enforced at three layers:**
  1. **OpenClaudePin component** — accent border + accent-tinted background (border-accent/40 bg-accent/5 per CONTEXT.md). Signal prop typed `AgentSignal | undefined` so the slot ALWAYS renders, including when claude_analyst is missing entirely from persona_signals. data-muted attribute exposed for E2E.
  2. **TickerRoute filtering** — `persona_signals.filter(p => p.analyst_id !== 'claude_analyst')` excludes Claude from the grid; `persona_signals.find(p => p.analyst_id === 'claude_analyst')` pulls the signal for OpenClaudePin (returns undefined if absent — handled by the muted state).
  3. **Playwright E2E assertions** — deep-dive spec asserts exactly 5 PersonaCards in grid (not 6), with no card having `data-persona='claude_analyst'`. Second assertion confirms OpenClaudePin always visible on direct navigation.
- **VIEW-06 Chart shipped** — lightweight-charts 5.2 v5-API React wrapper. The plan's pseudocode used the v4 `chart.addCandlestickSeries()` / `chart.addLineSeries()` methods which were REPLACED in lightweight-charts 5.0. Implementation uses the v5 `chart.addSeries(CandlestickSeries, options)` / `chart.addSeries(LineSeries, options)` API. Renders OHLC candlesticks + MA20 (accent solid) + MA50 (muted solid) + BB upper/lower (accent dotted) + RSI(14) sub-pane (amber, priceScaleId='rsi', scaleMargins.top=0.78). pairLines() helper drops null entries from indicator series before passing to setData (warmup periods produce leading nulls — MA50 has 50, RSI(14) has 14, etc.). ResizeObserver keeps chart width matched to container; chart.remove() in cleanup.
- **VIEW-05 dual-timeframe cards** — TimeframeCard renders short_term OR long_term TimeframeBand with: thesis_status pill (color-mapped: intact/improving=bullish, weakening=amber, broken=bearish, n/a=fg-muted), confidence (mono "conf 70"), summary paragraph, top-5 drivers as bullet list. Two cards side-by-side on `lg:flex-row`, stacked on mobile (Wave 4 verifies responsive break).
- **VIEW-07 PersonaCards (5)** — render 1 persona AgentSignal each with PERSONA_LABEL mapping (buffett→"Warren Buffett", munger→"Charlie Munger", wood→"Cathie Wood", burry→"Michael Burry", lynch→"Peter Lynch"). evidence[0] doubles as reasoning summary; evidence[1..] render via EvidenceList (max 3). Muted body when data_unavailable=true.
- **AnalyticalSignalCards (4)** — 4 deterministic analytical signals (fundamentals/technicals/news_sentiment/valuation) with friendly captions (Fundamentals / Technicals / News & Sentiment / Valuation). More compact than PersonaCard — no "voice" framing since these are deterministic Python.
- **VIEW-08 NewsList** — headlines grouped by source via `Map<string, Headline[]>`; within-group sort by published_at DESC via String#localeCompare; target='_blank' rel='noopener noreferrer' on every link. NEW tag rendered when `headlinePublishedMs > snapshotComputedAtMs`. Empty state when headlines=[].
- **VIEW-13 ticker search typeahead** — TickerSearch input in Root header; Enter → navigate(`/ticker/${value.toUpperCase()}/${activeDate}`). Active date detected via useMatches (handles both /scan/:date and /ticker/:symbol/:date? routes). Lowercase input ("aapl") uppercased at submit time. Company-name fuzzy match deferred to v1.x.
- **loadTickerData.useTickerData hook** — TanStack Query with queryKey ['ticker', date, symbol]. fetchAndParse(snapshotUrl, SnapshotSchema). Inherits 5min staleTime from QueryClient defaults. __loadTickerForTest test-only export mirrors loadScanData pattern.
- **Loading + error states in TickerRoute** — typed error branches: FetchNotFoundError → "{ticker} not in snapshot for {date}"; SchemaMismatchError → "Schema upgrade required" explicit banner per CONTEXT.md UNIFORM RULE; generic Error → message surface. All states include "← Back to scan" link.
- **AAPL fixture extended** — headlines from 3 → 9 (Yahoo Finance × 3 + Reuters × 3 + Bloomberg RSS × 3, varying published_at) so the deep-dive E2E can assert the NewsList groups by 3 distinct sources.
- **Notion-Clean palette honored end-to-end** — PALETTE const in Chart.tsx kept in sync with src/index.css @theme tokens (lightweight-charts options take raw hex, not CSS-variable interpolation at chart-init time). All other components use bg-bg/bg-surface/border-border/text-fg/text-fg-muted/text-accent/text-bullish/text-amber/text-bearish/border-accent — zero ad-hoc hex codes.
- **Test counts:** 179 vitest tests across 24 test files (146 Wave 2 baseline + 33 Wave 3 = component + lib + Chart). Playwright: 12 specs on chromium-desktop (1 smoke + 5 morning-scan + 6 deep-dive). All green. typecheck + build clean.

## Task Commits

1. **Task 1: Chart wrapper for lightweight-charts 5.2 with MA/BB/RSI overlays** — `3cd2ea7` (feat)
2. **Task 2: Persona + Open-Claude + Timeframe + Analytical + News components** — `8857fe1` (feat)
3. **Task 3: TickerRoute deep-dive + ticker search typeahead + Playwright E2E** — `fa64df9` (feat)

## Files Created/Modified

See `key-files` block in frontmatter above (14 files created; 4 modified). All committed atomically per task.

## Decisions Made

See `key-decisions` block in frontmatter above (10 decisions captured). Highlights:

- **lightweight-charts v5 API** — Plan pseudocode used v4 `chart.addCandlestickSeries()` / `chart.addLineSeries()` which were REPLACED in 5.0. Implementation uses `chart.addSeries(CandlestickSeries, options)` / `chart.addSeries(LineSeries, options)`. Caught at typecheck-time on Task 1 first compile attempt.
- **OpenClaudePin signal prop = AgentSignal | undefined** (not AgentSignal). The VIEW-09 lock requires the slot ALWAYS render including when claude_analyst is missing entirely. Single `muted` branch handles both undefined-signal AND data_unavailable=true.
- **PersonaCard reasoning sourcing from evidence[0]** — Phase 5 AgentSignal doesn't have a separate reasoning field; persona prompts pack reasoning + drivers into evidence[]. evidence[0] = reasoning summary, evidence[1..] = drivers via EvidenceList. v1.x can split into AgentSignal.reasoning if needed.
- **RSI sub-pane via priceScaleId='rsi' + scaleMargins** — simpler than formal lightweight-charts panes API (paneIndex). Gives RSI the bottom ~22% of the chart in a single chart instance. v1.x can migrate to formal panes if needed.
- **Chart unit tests via vi.mock('lightweight-charts')** — jsdom lacks WebGL/canvas. Mock factory records setData/addSeries calls; tests assert call shape (e.g. 11 non-null pairs after dropping 19 nulls in a warmup-30 fixture).
- **VIEW-13 v1 surface = uppercased text → /ticker/:typed/:date** — no fuzzy match. yfinance ticker symbols ARE the v1 search surface; v1.x adds company-name fuzzy match.
- **Active date detection in Root via useMatches (not useParams)** — Root is the parent layout, not a leaf route. useMatches scans the full hierarchy and finds :date from the active leaf route. Pattern from Wave 2's HeaderStaleness.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] lightweight-charts v4 API in plan pseudocode replaced with v5 API**

- **Found during:** Task 1 (Chart.tsx scaffold)
- **Issue:** Plan's pseudocode showed `chart.addCandlestickSeries({ ... })` and `chart.addLineSeries({ ... })`. Both methods were REMOVED in lightweight-charts 5.0 (the package shipped in this repo is 5.2). The current API is `chart.addSeries(CandlestickSeries, options)` and `chart.addSeries(LineSeries, options)`, where `CandlestickSeries` and `LineSeries` are SeriesDefinition exports from the package. Plan's typecheck would have failed: "Property 'addCandlestickSeries' does not exist on type 'IChartApi'."
- **Fix:** Refactored Chart.tsx to use the v5 `chart.addSeries(SeriesDefinition, options)` pattern. Imports updated: `import { CandlestickSeries, ColorType, LineSeries, LineStyle, createChart, type IChartApi, type Time } from 'lightweight-charts'`. CONTEXT_HANDOFF flagged this would happen ("Chart is the second biggest scope: lightweight-charts 5.2 changed its API in 5.0... Use the v5 API.") — this auto-fix is exactly that.
- **Files modified:** frontend/src/components/Chart.tsx
- **Verification:** `pnpm typecheck` passes; 6 Chart unit tests via vi.mock recording setData calls all green.
- **Committed in:** `3cd2ea7` (Task 1)

**2. [Rule 3 — Blocking] Playwright reuseExistingServer served stale build on first deep-dive E2E run**

- **Found during:** Task 3 first Playwright run after creating TickerRoute + Root.tsx changes
- **Issue:** `playwright.config.ts` has `webServer.reuseExistingServer: !process.env.CI`. On the first Playwright run after creating new TickerRoute composition, Playwright reused an existing preview server that was serving the OLD `dist/` (Wave 1 stub TickerRoute). All 6 deep-dive specs failed with "element(s) not found" for `getByTestId('ticker-heading')` etc.
- **Fix:** Ran `pnpm build` to refresh `dist/`. Re-ran Playwright; all 6 specs passed in 3.7s. (Note: even though there was no existing server LISTEN-ing on 4173, the prebuilt bundle was the v1 stub.)
- **Files modified:** None (build artifact only — dist/ is gitignored)
- **Verification:** All 12 chromium-desktop E2E specs pass: 6 deep-dive + 5 morning-scan (no regression) + 1 smoke.
- **Committed in:** `fa64df9` (Task 3) — captured in commit message "NOTE: Initial Playwright run failed because Playwright's reuseExistingServer served a stale build. Rule 3 auto-fix: rebuilt frontend (pnpm build) before re-running E2E."

### Plan Wording Refinements

**3. PersonaCard reasoning sourcing chose evidence[0] over a non-existent AgentSignal.reasoning field**

The plan's pseudocode showed `<p>{signal.reasoning}</p>` — but `AgentSignal` (per `frontend/src/schemas/agent_signal.ts`) does NOT have a `reasoning` field. It has `verdict`, `confidence`, `evidence: string[]`, `data_unavailable: boolean`. The Phase 5 persona prompts pack reasoning + drivers into the evidence array. Implementation chose `evidence[0]` as the reasoning summary surface and `evidence[1..]` as drivers via EvidenceList — preserves the plan's intent (reasoning paragraph + drivers list) without changing the v1 schema. v1.x candidate: split into AgentSignal.reasoning vs evidence cleanly.

**4. OpenClaudePin signal prop typed as AgentSignal | undefined (not AgentSignal)**

The plan's pseudocode had `interface Props { signal: AgentSignal }`. But the VIEW-09 lock requires the slot ALWAYS render — including when claude_analyst is MISSING entirely from `persona_signals` (lite-mode skipped, schema_failure default returned by upstream). With `signal: AgentSignal` (required), `<OpenClaudePin signal={claudeSig} />` would TypeError at compile time when `claudeSig` is undefined. Fix: typed prop as `AgentSignal | undefined`; muted-state branch handles both undefined-signal AND data_unavailable=true via single `muted = !signal || signal.data_unavailable`. Tighter than plan's "always renders" intent — actually enforced at the React + TypeScript layer.

**5. Chart's Notion-Clean palette duplicated as PALETTE const inside Chart.tsx**

Plan's pseudocode inlined hex codes inside the `createChart` options. Implementation extracted them to a `PALETTE` const at module scope (mirrors src/index.css @theme). Trade-off: minor DRY violation between PALETTE and @theme; if the palette ever changes, both files update. Justified because lightweight-charts options take raw hex strings (not CSS-variable interpolation at chart-init time) and grouping the palette in one const makes the chart's runtime visual identity legible.

### Toolchain Notes

- **Windows line-ending warnings** during `git add` (LF will be replaced by CRLF) — Windows-default; non-issue (git auto-normalizes on checkout).
- **`.planning/config.json` left unstaged** per context_handoff instruction — auto-mode flag toggle, separate concern.
- **shadcn add separator** brought `@radix-ui/react-separator` cleanly (no missing-cva-style hiccup like Wave 2's badge add).

---

**Total deviations:** 2 auto-fixed (1 Rule 1 bug — outdated v4 API in plan pseudocode + 1 Rule 3 blocking — Playwright stale-build) + 3 plan-wording refinements (signal nullability tightened, reasoning sourcing from evidence[0], palette extracted to const). Zero scope creep — all auto-fixes preserve the locked plan scope.

## Issues Encountered

- **lightweight-charts v4 vs v5 API mismatch in plan pseudocode** — Plan was written against v4 API; actual package is v5.2. Caught immediately at Task 1 typecheck. Fix was mechanical (rename `addCandlestickSeries` → `addSeries(CandlestickSeries, ...)`).
- **Playwright stale build** — Ran the new deep-dive E2E without rebuilding first; preview server served the Wave 1 stub bundle. After `pnpm build`, all 6 specs green in 3.7s. v1.x candidate: add `test:e2e:fresh` script that runs `pnpm build` first.

## User Setup Required

None — no external services configured in Wave 3. Wave 4 (06-05) closes out INFRA-05 (Vercel deploy + real GitHub raw URL).

## Next Phase Readiness

**Ready for Plan 06-05 (Polish + Responsive + Playwright — Wave 4):**

- All 7 deep-dive sections rendering on chromium-desktop. Wave 4 polishes mobile-safari + mobile-chrome responsive (VIEW-12) — the lg:flex-row breakpoints on TimeframeCards + the md:grid-cols-2 xl:grid-cols-3 on PersonaCards already in place; Wave 4's mobile-safari Playwright project verifies the responsive breaks.
- Chart container is touch-friendly by default (lightweight-charts respects pinch-zoom on touch devices); Wave 4 mobile-safari run will exercise it.
- ErrorBoundary scaffold (catch zod-mismatch crashes that escape route-level error handling) lands in Wave 4.
- DateSelector loading data/_dates.json (VIEW-14) lands in Wave 4.
- INFRA-05 Vercel deploy lands in Wave 4 final task.
- AAPL fixture extension (3 → 9 headlines from 3 sources) gives Wave 4 mobile-responsive Playwright something visual to assert on for NewsList.

**No blockers for Wave 4.** Plan 06-04 closes complete. Phase 6 progress: 4/5 plans done.

## Self-Check: PASSED

Verified at completion:

| Claim | Verification |
|---|---|
| 3 task commits exist (feat 06-04 ×3) | `git log --oneline -3` → fa64df9 / 8857fe1 / 3cd2ea7 |
| `frontend/src/components/Chart.tsx` created | path exists; 207 lines; uses `chart.addSeries(CandlestickSeries, ...)` v5 API |
| `frontend/src/components/PersonaCard.tsx` created | path exists; PERSONA_LABEL maps 5 canonical personas + claude_analyst |
| `frontend/src/components/OpenClaudePin.tsx` created | path exists; signal prop = AgentSignal \| undefined; data-testid='open-claude-pin' |
| `frontend/src/components/TimeframeCard.tsx` created | path exists; STATUS_COLOR maps 5 thesis_status values |
| `frontend/src/components/AnalyticalSignalCard.tsx` created | path exists; ANALYST_LABEL maps 4 analytical analyst_ids |
| `frontend/src/components/NewsList.tsx` created | path exists; group-by-source + within-group DESC sort + NEW tag |
| `frontend/src/components/ui/separator.tsx` vendored | path exists; @radix-ui/react-separator in package.json |
| `frontend/src/lib/loadTickerData.ts` created | path exists; useTickerData TanStack hook + __loadTickerForTest export |
| `frontend/src/routes/TickerRoute.tsx` populated | Wave 1 stub replaced with full Wave 3 composition |
| `frontend/src/routes/Root.tsx` populated | TickerSearch input added (data-testid='ticker-search-input') |
| `frontend/tests/e2e/deep-dive.spec.ts` created | path exists; 6 specs |
| `frontend/tests/fixtures/scan/AAPL.json` modified | 9 headlines across 3 sources |
| 179 vitest tests pass | `pnpm test:unit --run` → Test Files 24 passed (24) / Tests 179 passed (179) |
| 12 Playwright E2E specs pass on chromium-desktop | `pnpm test:e2e --project=chromium-desktop` → 12 passed (3.5s) |
| typecheck clean | `pnpm typecheck` exits 0 |
| build clean | `pnpm build` produces dist/ with 639.19 kB index.js (gzipped 199.60 kB) |
| OpenClaudePin always renders (VIEW-09 lock) | OpenClaudePin.test.tsx asserts data-muted='true' for signal=undefined; data-muted='false' for happy path |
| PersonaCards grid excludes claude_analyst | TickerRoute filters `persona_signals.filter(p => p.analyst_id !== 'claude_analyst')`; deep-dive E2E asserts 5 cards (not 6) and no data-persona='claude_analyst' |
| Notion-Clean palette honored | every component uses bg-bg/bg-surface/border-border/text-fg/text-fg-muted/text-accent/text-bullish/text-amber/text-bearish/border-accent — zero ad-hoc hex codes (Chart's PALETTE const mirrors @theme) |

---
*Phase: 06-frontend-mvp-morning-scan-deep-dive*
*Completed: 2026-05-04*
