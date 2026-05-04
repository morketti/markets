---
phase: 06-frontend-mvp-morning-scan-deep-dive
plan: 02
subsystem: frontend
tags: [phase-6, wave-1, scaffold, frontend, vite, react, typescript, tailwind, zod, tanstack-query, react-router, vercel, schemas, fetch-layer, staleness]

# Dependency graph
requires:
  - phase: 06-frontend-mvp-morning-scan-deep-dive
    provides: per-ticker JSON shape v2 (schema_version=2, ohlc_history, indicators 5 series, headlines, TimeframeBand.thesis_status); data/_dates.json repo-root index; ThesisStatus 5-state Literal in synthesis/decision.py
provides:
  - frontend/ Vite 6 + React 19 + TypeScript 5.6 + Tailwind v4 + react-router v7 + TanStack Query v5 + zod 4 + lightweight-charts 5.2 project at repo root
  - Notion-Clean palette tokens in src/index.css @theme directive (CONTEXT.md lock — bg #0E0F11, surface #1F2024, border #2A2C30, fg #E8E9EB, fg-muted #8B8E94, accent #5B9DFF, bullish/bearish/amber state colors, grid #252628)
  - Inter UI + JetBrains Mono numerics typography via Google Fonts <link>
  - 6 zod schema files mirroring Pydantic source-of-truth (agent_signal/position_signal/ticker_decision/snapshot/status/dates_index) + barrel index re-exporting parsed types
  - schema_version: z.literal(2) on TickerDecision + Snapshot — strict v1 rejection per CONTEXT.md UNIFORM RULE
  - fetchAndParse<T> single GitHub-raw read boundary with SchemaMismatchError + FetchNotFoundError typed errors
  - URL builders: snapshotUrl / indexUrl / statusUrl / datesUrl
  - computeStaleness(iso, partial, now?) implementing VIEW-11 6h/24h thresholds with SIX_HOURS_MS + TWENTY_FOUR_HOURS_MS module constants
  - format helpers (formatNumber / formatPercent / formatCompact / formatDate / formatTicker)
  - react-router v7 data-router (/ → redirect /scan/today; /scan/:date stub; /ticker/:symbol/:date? stub; Root layout with staleness slot placeholder)
  - shadcn/ui CLI configured (components.json) + ui/.gitkeep dir reserved for Wave 2-3 vendoring
  - vitest config with mergeConfig(viteConfig, ...) workaround for vitest 2.x peer-dep type clash with vite 6
  - Playwright config with 3 projects (chromium-desktop / mobile-safari iPhone 14 / mobile-chrome Pixel 7) + webServer pnpm preview at port 4173
  - Vercel static deploy config (rewrites /(.*) → /index.html for SPA fallback)
  - .env.example documents VITE_GH_USER + VITE_GH_REPO; .env.local placeholder so dev mode boots
  - pnpm 10 onlyBuiltDependencies allowlist for esbuild postinstall scripts
affects: [06-03-morning-scan, 06-04-deep-dive, 06-05-polish-responsive]

# Tech tracking
tech-stack:
  added:
    - "vite ^6.4 + @vitejs/plugin-react ^4.7 + @tailwindcss/vite ^4.2 (Tailwind v4 CSS-first plugin)"
    - "react ^19.2 + react-dom ^19.2 + react-router ^7.14"
    - "@tanstack/react-query ^5.100 + zod ^4.4 + lightweight-charts ^5.2 + clsx ^2.1 + tailwind-merge ^2.6"
    - "typescript ^5.9 (resolved from ^5.6 floor)"
    - "tailwindcss ^4.2 (CSS-first via @theme directive — no plugin chain)"
    - "vitest ^2.1 + @testing-library/react ^16 + @testing-library/dom ^10 + @testing-library/jest-dom ^6 + jsdom ^25"
    - "@playwright/test ^1.59 + playwright ^1.59 (chromium binary downloaded)"
  patterns:
    - "Tailwind v4 CSS-first @theme directive — palette tokens become first-class utilities (bg-bg, text-fg, border-border, font-mono) without separate config"
    - "schema_version: z.literal(N) for STRICT version pinning at zod parse time — rejects non-matching versions instead of silent coercion (CONTEXT.md UNIFORM RULE)"
    - "Pydantic invariant → zod refine() one-to-one mapping — data_unavailable contracts hold byte-identically server-side (Pydantic) and client-side (zod)"
    - "fetchAndParse<T>(url, schema) single read boundary — typed error classes (SchemaMismatchError / FetchNotFoundError) let Wave 4 ErrorBoundary render distinct UI per failure mode"
    - "URL builders co-located with the fetch helper — single source of truth for snapshot path layout; consumers import builders, not template strings"
    - "vitest 2.x + vite 6 peer-dep mismatch resolved via mergeConfig(viteConfig, ...) instead of dual defineConfig imports (vitest 3.x will collapse this)"
    - "pnpm 10 onlyBuiltDependencies allowlist — esbuild postinstall must be explicitly approved or pnpm refuses to run it (security posture; we approve only esbuild)"
    - "Build-time env vars via import.meta.env.VITE_* — no runtime config.json fetch (CONTEXT.md GitHub Repo Configuration lock)"
    - "react-router v7 data-router with loader-based redirect from / → /scan/today (no flash of placeholder content)"

key-files:
  created:
    - "frontend/package.json — full dependency manifest with pinned floors (vite ^6, react ^19, etc.) + 7 pnpm scripts + pnpm.onlyBuiltDependencies allowlist"
    - "frontend/pnpm-lock.yaml — deterministic lockfile (~5K lines)"
    - "frontend/tsconfig.json — strict TS config, paths alias @ → ./src, references tsconfig.node.json"
    - "frontend/tsconfig.node.json — composite project for vite/vitest/playwright config files"
    - "frontend/vite.config.ts — @vitejs/plugin-react + tailwindcss/vite + path resolve alias"
    - "frontend/vitest.config.ts — mergeConfig(viteConfig, ...) overlaying jsdom + setupFiles + coverage thresholds 90/85"
    - "frontend/playwright.config.ts — 3 projects (chromium-desktop/mobile-safari/mobile-chrome) + webServer pnpm preview port 4173"
    - "frontend/index.html — minimal Vite shell + Google Fonts (Inter + JetBrains Mono)"
    - "frontend/src/index.css — Tailwind v4 @theme directive with Notion-Clean palette tokens + Inter/JetBrains Mono font stacks + prefers-reduced-motion respect"
    - "frontend/tailwind.config.ts — minimal stub for IDE integration (v4 is CSS-first)"
    - "frontend/postcss.config.js — empty (Tailwind v4 owns the pipeline via Vite plugin)"
    - "frontend/components.json — shadcn/ui CLI config, neutral baseColor, @ aliases"
    - "frontend/.env.example — documents VITE_GH_USER + VITE_GH_REPO; frontend/.env.local — placeholder for dev mode"
    - "frontend/.gitignore — node_modules / dist / .vite / playwright-report / test-results / coverage / .env.local / *.tsbuildinfo"
    - "frontend/vercel.json — framework: vite, rewrites /(.*) → /index.html for SPA fallback"
    - "frontend/src/main.tsx — React 19 createRoot + StrictMode + QueryClientProvider (staleTime 5min, refetchOnWindowFocus false) + RouterProvider"
    - "frontend/src/App.tsx — createBrowserRouter v7 with / redirect loader + Root layout + ScanRoute + TickerRoute"
    - "frontend/src/routes/Root.tsx — header (brand link + staleness slot placeholder) + Outlet"
    - "frontend/src/routes/ScanRoute.tsx — Wave 1 stub: 'Morning Scan — {date}' heading; Wave 2 fills in"
    - "frontend/src/routes/TickerRoute.tsx — Wave 1 stub: '{symbol} — {date}' heading; Wave 3 fills in"
    - "frontend/src/lib/utils.ts — cn() helper (clsx + tailwind-merge composition; shadcn/ui standard)"
    - "frontend/src/lib/fetchSnapshot.ts — fetchAndParse<T> + SchemaMismatchError + FetchNotFoundError + RAW_BASE + 4 URL builders"
    - "frontend/src/lib/staleness.ts — computeStaleness + SIX_HOURS_MS + TWENTY_FOUR_HOURS_MS (VIEW-11 thresholds)"
    - "frontend/src/lib/format.ts — formatNumber / formatPercent / formatCompact / formatDate / formatTicker"
    - "frontend/src/schemas/agent_signal.ts — VerdictSchema + AnalystIdSchema (10 ids) + AgentSignalSchema with data_unavailable refine"
    - "frontend/src/schemas/position_signal.ts — PositionStateSchema + ActionHintSchema + PositionSignalSchema with canonical no-opinion refine"
    - "frontend/src/schemas/ticker_decision.ts — DecisionRecommendationSchema + ConvictionBandSchema + TimeframeSchema + ThesisStatusSchema + TimeframeBandSchema + DissentSectionSchema + TickerDecisionSchema with schema_version: z.literal(2) + data_unavailable refine"
    - "frontend/src/schemas/snapshot.ts — OHLCBarSchema + IndicatorsSchema (5 series) + HeadlineSchema + SnapshotSchema with schema_version: z.literal(2)"
    - "frontend/src/schemas/status.ts — StatusSchema for _status.json"
    - "frontend/src/schemas/dates_index.ts — DatesIndexSchema with schema_version: z.literal(1) for data/_dates.json"
    - "frontend/src/schemas/index.ts — barrel re-export of all 6 schemas + their inferred types"
    - "frontend/src/schemas/__tests__/agent_signal.test.ts — 12 tests (happy paths, all 10 analyst_ids, 5 verdicts, invariant rejections, evidence cap)"
    - "frontend/src/schemas/__tests__/position_signal.test.ts — 12 tests (state ladder, action hints, consensus_score range, indicator nulls, canonical no-opinion invariant)"
    - "frontend/src/schemas/__tests__/ticker_decision.test.ts — 14 tests (happy path, schema_version=1 + 3 rejection, recommendation/conviction/thesis_status enums, dissent populated, data_unavailable invariant)"
    - "frontend/src/schemas/__tests__/snapshot.test.ts — 12 tests (full Phase 5 / Wave 0 fixture, schema_version=1 rejection, null position_signal/ticker_decision lite mode paths, indicators 5-series shape, malformed date/url rejection)"
    - "frontend/src/schemas/__tests__/status.test.ts — 7 tests (happy / partial / lite mode / missing-required-field rejections / negative llm_failure_count rejection)"
    - "frontend/src/schemas/__tests__/dates_index.test.ts — 7 tests (happy, empty, schema_version=2 rejection, malformed date, partial date, sortedness-not-enforced)"
    - "frontend/src/lib/__tests__/staleness.test.ts — 16 tests (all 13 boundary cases: <6h ± partial, exactly 6h, 12h, exactly 24h, >24h ± partial, defensive unparseable ISO, Date.now() default arg path) + 2 module-constant tests"
    - "frontend/src/lib/__tests__/fetchSnapshot.test.ts — 14 tests (happy path / 404 → FetchNotFoundError / 500 → generic Error / zod-mismatch → SchemaMismatchError with url+zodError attached / Accept header verification / 4 URL builder shape tests / 2 error-class construction tests)"
    - "frontend/src/components/ui/.gitkeep — Wave 2-3 vendor shadcn primitives here"
    - "frontend/src/setupTests.ts — vitest setup imports @testing-library/jest-dom matchers"
    - "frontend/src/vite-env.d.ts — vite/client types + ImportMetaEnv typings for VITE_GH_USER + VITE_GH_REPO"
    - "frontend/tests/e2e/smoke.spec.ts — 1 Playwright spec asserting / → /scan/today redirect + 'Morning Scan — today' heading visible"
  modified:
    - ".gitignore — extended with frontend/node_modules + frontend/dist + frontend/.vite + frontend/playwright-report + frontend/test-results + frontend/coverage + frontend/.env.local + frontend/*.tsbuildinfo"

key-decisions:
  - "Frontend lives at repo root under frontend/ (NOT at repo root flat) — keeps Python (analysts/, synthesis/, routine/, ingestion/, watchlist/, prompts/) and React cleanly separated; matches CONTEXT.md recommendation"
  - "schema_version: z.literal(2) on TickerDecision + Snapshot rejects v1 snapshots at parse time — explicit Wave 4 banner rather than silent coercion (CONTEXT.md UNIFORM RULE)"
  - "Pydantic invariants (data_unavailable=true canonical-shape contracts on AgentSignal / PositionSignal / TickerDecision) mirrored 1:1 as zod refine() — same contract holds server-side AND client-side; a buggy backend can't sneak a bad shape past the frontend"
  - "Tailwind v4 CSS-first config via @theme directive in src/index.css — palette tokens become first-class utilities (bg-bg, text-fg, border-border) without a tailwind.config.ts plugin chain"
  - "vitest 2.x + vite 6 peer-dep mismatch resolved via mergeConfig(viteConfig, ...) — vitest 2.1 ships its own Vite 5 peer; importing defineConfig from 'vite' directly causes a Plugin<any> overload clash on react(). mergeConfig is the supported pattern; vitest 3.x will collapse this"
  - "tsconfig.node.json with composite + emitDeclarationOnly + outDir → ./node_modules/.tmp — composite projects can't have noEmit:true (TS6310). The project still type-checks but emits .d.ts to a hidden tmp dir which is gitignored"
  - "pnpm 10 onlyBuiltDependencies: ['esbuild'] in package.json — pnpm 10's strict policy ignores postinstall scripts by default; we explicitly allow esbuild's binary-extraction postinstall"
  - "Playwright browser binaries (chromium ~111MB) installed via `pnpm exec playwright install chromium` — NOT bundled into postinstall script (would slow every fresh install). webkit + mobile devices install in Wave 4 when mobile-safari + mobile-chrome projects start running"
  - "vercel.json declares rewrites /(.*) → /index.html — load-bearing for react-router v7 client-side routing on Vercel; without it, /scan/today direct hit returns 404"
  - "frontend/.env.local committed with placeholder values (example-user / example-repo) — production env vars set in Vercel dashboard; .env.local is .gitignored to prevent accidental real-credential commits BUT the .env.example sibling file documents the required vars"
  - "computeStaleness boundary semantics: exactly 6h → AMBER (>= comparison); exactly 24h → AMBER (> strict on RED); 24h + 1ms → RED. Locked by 4 dedicated boundary tests so Wave 4 StalenessBadge math agrees byte-identically with the (server-side) staleness intuition users expect"
  - "fetchAndParse<T> generic + ZodType<T> bound — single read helper services every JSON shape; Wave 2-4 components compose it via useQuery(['snapshot', date, ticker], () => fetchAndParse(snapshotUrl(date, ticker), SnapshotSchema))"
  - "tailwind.config.ts is a minimal stub — Tailwind v4's CSS-first config in src/index.css is the source of truth. The .ts file exists for IDE Tailwind LSP integration only"
  - "Stub route components (ScanRoute / TickerRoute / Root) — Wave 2 populates ScanRoute with three lens tabs; Wave 3 populates TickerRoute with the full deep-dive; Wave 4 wires StalenessBadge into Root's staleness slot"
  - "src/lib/format.ts is small but worth its own file — Wave 2-4 components will sprinkle formatNumber / formatDate calls everywhere; centralizing means consistent locale + locale-options across the app"

requirements-completed: []
# INFRA-05 stays Pending in REQUIREMENTS.md — the Wave 1 scaffolding portion
# is satisfied, but INFRA-05 also requires "Vercel deploy succeeds + reads
# from real GitHub raw URL" which is a Wave 4 closeout gate (the user has to
# add VITE_GH_USER + VITE_GH_REPO in Vercel + verify the production preview
# loads real data). Per CONTEXT.md handoff: "INFRA-05 stays Pending in
# REQUIREMENTS.md" until Wave 4 ships.

# Metrics
duration: 10min
completed: 2026-05-04
---

# Phase 6 Plan 02: Frontend Scaffold Summary

**Vite 6 + React 19 + TypeScript 5.9 + Tailwind v4 + react-router v7 + TanStack Query v5 + zod 4 frontend scaffolded at `frontend/`; 6 zod schemas mirror the Wave-0 v2 Pydantic shapes with `schema_version: z.literal(2)` strict-rejection of v1 snapshots; fetchAndParse + SchemaMismatchError + FetchNotFoundError ship the read layer; computeStaleness encodes VIEW-11 6h/24h thresholds; 94 vitest tests + 1 Playwright smoke E2E all green.**

## Performance

- **Duration:** ~10 min wall-clock (most spent on `pnpm install` resolve + Playwright chromium download)
- **Started:** 2026-05-04T14:03:11Z
- **Completed:** 2026-05-04T14:12:50Z
- **Tasks:** 3 (all atomic commits landed)
- **Files created:** 43 frontend/ files (committed) + 1 modified (.gitignore)
- **Tests added:** 94 vitest unit + 1 Playwright smoke E2E (all green)

## Accomplishments

- **Frontend scaffold at `frontend/`** with the full locked stack from CONTEXT.md: Vite 6.4 + React 19.2 + TypeScript 5.9 + Tailwind v4.2 (CSS-first `@theme` directive) + react-router 7.14 + TanStack Query 5.100 + zod 4.4 + lightweight-charts 5.2 + clsx + tailwind-merge in dependencies; vitest 2.1 + jsdom + RTL + Playwright 1.59 + @types/* in dev deps. `pnpm install` clean; `pnpm-lock.yaml` committed.
- **Notion-Clean palette tokens** in `src/index.css` `@theme` directive — verbatim hex from CONTEXT.md (`#0E0F11` bg / `#1F2024` surface / `#2A2C30` border / `#E8E9EB` fg / `#8B8E94` fg-muted / `#5B9DFF` accent / `#4ADE80` bullish / `#F87171` bearish / `#FBBF24` amber / `#252628` grid). Inter UI + JetBrains Mono numerics loaded via Google Fonts `<link>` in `index.html`.
- **6 zod schemas** (one per Pydantic file): `agent_signal.ts` (10-id `AnalystId` Literal + 5-state `Verdict` ladder + `data_unavailable` invariant via `refine()`); `position_signal.ts` (5-state `PositionState` + 4-state `ActionHint` + `consensus_score` [-1,1] range + canonical no-opinion invariant); `ticker_decision.ts` (`schema_version: z.literal(2)` strict + `ThesisStatus` 5-enum + `TimeframeBand` with `thesis_status` field + `DissentSection` + invariant); `snapshot.ts` (per-ticker JSON v2 envelope + `OHLCBar` + `Indicators` 5 series + `Headline` with URL validation); `status.ts` (`_status.json` shape); `dates_index.ts` (`data/_dates.json` with `schema_version: z.literal(1)`); barrel `index.ts` re-exporting parsed types.
- **fetchAndParse<T>** in `src/lib/fetchSnapshot.ts` — single GitHub-raw read boundary; throws `SchemaMismatchError` (carries `url` + `zodError`) on zod parse failure; throws `FetchNotFoundError` (carries `url`) on 404; throws generic `Error` on other non-2xx. Plus `RAW_BASE` (built from `VITE_GH_USER` + `VITE_GH_REPO`) + 4 URL builders (`snapshotUrl`, `indexUrl`, `statusUrl`, `datesUrl`).
- **computeStaleness** in `src/lib/staleness.ts` — VIEW-11 thresholds locked to REQUIREMENTS.md: `<6h && !partial → GREEN`; `<6h && partial → AMBER`; `6-24h → AMBER` (both partial states); `>24h → RED`. Boundary semantics locked: exactly 6h → AMBER (`>=` comparison); exactly 24h → AMBER (`>` strict on RED transition); 24h+1ms → RED. `SIX_HOURS_MS` + `TWENTY_FOUR_HOURS_MS` exported as named constants.
- **format helpers** in `src/lib/format.ts` — `formatNumber` / `formatPercent` / `formatCompact` (Intl.NumberFormat-based), `formatDate` (UTC YYYY-MM-DD), `formatTicker` (uppercase + dot→hyphen — mirrors `analysts.schemas.normalize_ticker` conceptually).
- **react-router v7 data-router** in `src/App.tsx` — `/` → loader-based redirect to `/scan/today` (no flash of placeholder); `/scan/:date` → `ScanRoute` stub; `/ticker/:symbol/:date?` → `TickerRoute` stub; `Root` layout has staleness slot placeholder in header.
- **TanStack Query** wired in `src/main.tsx` — `staleTime: 5min`, `refetchOnWindowFocus: false`, `retry: 1` (sane defaults for the GitHub-as-DB read-mostly model).
- **shadcn/ui CLI** configured (`components.json` declares Notion-Clean style + `@` aliases + `tailwind.cssVariables: true`); `src/components/ui/.gitkeep` reserves the dir for Wave 2-3 vendoring.
- **Vercel deploy config** (`vercel.json`) declares `framework: vite`, `pnpm install`, `pnpm build`, `dist`, AND the load-bearing rewrites entry `(.*) → /index.html` (without it, react-router v7 client-side routing returns 404 on direct deep links).
- **`.env.example`** documents `VITE_GH_USER` + `VITE_GH_REPO`; **`.env.local`** committed with placeholder values (`example-user` / `example-repo`) so dev mode boots; `.env.local` IS gitignored to prevent accidental real-credential commits BUT we DO commit the placeholder version specifically because Wave 1 needs `pnpm dev` to boot without manual setup.
- **Playwright** with 3 projects (chromium-desktop / mobile-safari iPhone 14 / mobile-chrome Pixel 7); `webServer: pnpm preview` at port 4173 (production-build E2E, not dev-server). chromium binary downloaded; webkit + mobile-chrome binaries install on first Wave 4 mobile-safari/mobile-chrome run.
- **Repo-root `.gitignore`** extended with frontend-specific lines (`frontend/node_modules` / `frontend/dist` / `frontend/.vite` / `frontend/playwright-report` / `frontend/test-results` / `frontend/coverage` / `frontend/.env.local` / `frontend/*.tsbuildinfo`).
- **94 vitest unit tests** across 8 test files — 64 schema tests (12 + 12 + 14 + 12 + 7 + 7 across the 6 schemas) + 16 staleness tests (covering all 9+ boundary cases from CONTEXT.md handoff plus the unparseable-ISO defensive path AND the `Date.now()` default-arg path) + 14 fetchSnapshot tests (happy / 404 / 500 / zod-mismatch / Accept header / 4 URL builder shape tests / 2 error-class construction tests). All green.
- **1 Playwright smoke E2E** (`tests/e2e/smoke.spec.ts`) on chromium-desktop — proves the scaffold boots end-to-end: `/` redirects to `/scan/today` (react-router loader works) AND the `Morning Scan — today` heading is visible (React + bundle + Tailwind v4 + router compose correctly).

## Task Commits

1. **Task 1: Vite + React + Tailwind + tooling scaffold** — `f755908` (feat)
2. **Task 2: zod schemas (one per Pydantic file) + 64 schema unit tests** — `1ee1959` (feat)
3. **Task 3: fetchSnapshot + staleness + format helpers + 30 lib unit tests** — `7b2e9ff` (feat)

## Files Created/Modified

See `key-files` block in frontmatter above (43 frontend/ files created; .gitignore modified). All committed atomically per task.

## Decisions Made

See `key-decisions` block in frontmatter above (15 decisions captured). Highlights:

- **schema_version: z.literal(2)** chosen over `z.number()` so v1 snapshots are REJECTED at parse time. Wave 4 ErrorBoundary gets a clean error shape (`SchemaMismatchError` with `url` + `zodError`) to render the explicit "schema upgrade required — re-run today's routine" banner per CONTEXT.md UNIFORM RULE. No silent coercion of v1 → v2.
- **Pydantic invariants → zod `refine()`** one-to-one. The Python `data_unavailable=True ⟹ canonical-shape` invariants in `analysts/signals.py:_data_unavailable_implies_neutral_zero`, `analysts/position_signal.py:_data_unavailable_implies_fair_zero`, and `synthesis/decision.py:_data_unavailable_implies_safe_defaults` are mirrored 1:1 in the corresponding zod schemas. Buggy backend output that sneaks past Pydantic (impossible by design) would still be caught client-side; correct-by-construction defense-in-depth.
- **Tailwind v4 CSS-first** via `@theme` directive in `src/index.css` — palette tokens become first-class Tailwind utilities (`bg-bg`, `text-fg`, `border-border`, `font-mono`) without a `tailwind.config.ts` plugin chain. The `.ts` config file exists ONLY for IDE Tailwind LSP integration.
- **vitest 2.x + vite 6 peer-dep clash** resolved via `mergeConfig(viteConfig, ...)` in `vitest.config.ts` instead of dual `defineConfig` imports from `vite` AND `vitest/config` (which collide on the `react()` plugin's `Plugin<any>` overload). vitest 3.x ships with vite 6 peer; this workaround disappears at the next vitest upgrade.
- **Stub routes** (`ScanRoute`, `TickerRoute`, `Root`) — Wave 1's job is the SCAFFOLD; Waves 2-3 fill in real content. The placeholder headings (`Morning Scan — {date}`, `{symbol} — {date}`) are exactly what `tests/e2e/smoke.spec.ts` asserts, so the smoke test stays meaningful through the iteration cycle.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Composite tsconfig.node.json had `noEmit: true` (TS6310)**

- **Found during:** Task 1 first `pnpm typecheck` run
- **Issue:** TypeScript composite project references (used so the main `tsconfig.json` can include `tsconfig.node.json` for vite/vitest/playwright config files) are forbidden from setting `noEmit: true` (error TS6310: "Referenced project may not disable emit"). Plan didn't specify the composite-project edge case.
- **Fix:** Removed `noEmit: true` from `tsconfig.node.json`; added `outDir: ./node_modules/.tmp/tsbuildinfo` + `tsBuildInfoFile: ./node_modules/.tmp/tsconfig.node.tsbuildinfo` + `emitDeclarationOnly: true` + `declaration: true`. The .d.ts emit goes to a hidden tmp dir under `node_modules` (already gitignored); zero source-tree impact.
- **Files modified:** `frontend/tsconfig.node.json`
- **Verification:** `pnpm typecheck` passes clean; `pnpm build` produces correct `dist/` with no leaked .d.ts files.
- **Committed in:** `f755908` (Task 1 scaffold commit)

**2. [Rule 1 — Bug] vitest 2.x + vite 6 peer-dep type clash on `react()` plugin**

- **Found during:** Task 1 first `pnpm build` run (which runs `tsc -b` before vite build)
- **Issue:** vitest 2.1.9 ships its own Vite 5.4.21 peer dependency; importing `defineConfig` from `vite` directly in `vitest.config.ts` causes TypeScript to see TWO different `Plugin<any>` overload definitions (one from vite 6.4.2, one from vite 5.4.21) and refuse to unify them. Build fails with a 50-line cascade of "Type 'Plugin<any>' is not assignable to type 'PluginOption'".
- **Fix:** Switched `vitest.config.ts` to use `mergeConfig(viteConfig, defineConfig({...test...}))` from `vitest/config`, importing the host vite config (Vite 6) and overlaying the test-only fields. This is the documented vitest pattern for vite-version-mismatch scenarios. Will collapse back to a single `defineConfig` once vitest 3.x lands with a Vite 6 peer.
- **Files modified:** `frontend/vitest.config.ts`
- **Verification:** `pnpm typecheck` AND `pnpm build` both clean; `pnpm test:unit --run` runs 94 tests successfully.
- **Committed in:** `f755908` (Task 1 scaffold commit)

**3. [Rule 1 — Bug] `tsconfig.tsbuildinfo` accidentally committed; gitignore extended**

- **Found during:** Task 1 `git status` after first staging
- **Issue:** `tsc -b` (the build's first step) emits a `tsconfig.tsbuildinfo` incremental-compilation cache file at `frontend/tsconfig.tsbuildinfo`. The frontend/.gitignore (and repo-root .gitignore frontend/* additions) didn't include `*.tsbuildinfo`, so it got staged.
- **Fix:** Added `*.tsbuildinfo` to `frontend/.gitignore` AND `frontend/*.tsbuildinfo` to repo-root `.gitignore`. Ran `git rm --cached frontend/tsconfig.tsbuildinfo` to unstage. Re-ran the full Task 1 verify (`pnpm typecheck && pnpm build && pnpm test:e2e -g smoke`) — all green; tsbuildinfo is regenerated by the next build but stays out of git.
- **Files modified:** `.gitignore`, `frontend/.gitignore`
- **Verification:** `git ls-tree -r HEAD frontend/ | grep tsbuildinfo` → zero matches (clean); `pnpm build` still produces the file locally for incremental-compile speed.
- **Committed in:** `f755908` (Task 1 scaffold commit — both .gitignore files included in same commit)

**4. [Rule 1 — Bug] `import.meta.env.VITE_*` typed access required `vite/client` types**

- **Found during:** Task 3 final `pnpm typecheck` after authoring `src/lib/fetchSnapshot.ts`
- **Issue:** `tsc --noEmit` (which is the `pnpm typecheck` script body) flagged `Property 'env' does not exist on type 'ImportMeta'` at the two `import.meta.env.VITE_GH_USER` / `VITE_GH_REPO` accesses in `fetchSnapshot.ts`. Vite injects these at build time via its own type plumbing, but `tsc --noEmit` doesn't auto-pull `vite/client` types unless the project explicitly references them.
- **Fix:** Created `frontend/src/vite-env.d.ts` with `/// <reference types="vite/client" />` triple-slash AND explicit `ImportMetaEnv` interface declaring `VITE_GH_USER` + `VITE_GH_REPO` as optional readonly strings. This is the canonical Vite recipe for typed env vars.
- **Files modified:** Added `frontend/src/vite-env.d.ts`
- **Verification:** `pnpm typecheck` passes clean; `import.meta.env.VITE_GH_USER` is typed as `string | undefined` in IDE hover.
- **Committed in:** `7b2e9ff` (Task 3 fetchSnapshot commit)

**5. [Rule 3 — Blocking] pnpm 10 `onlyBuiltDependencies` required for esbuild postinstall**

- **Found during:** Task 1 first `pnpm install` run
- **Issue:** pnpm 10 ships with a strict default policy that ignores `postinstall` build scripts unless explicitly approved. esbuild (transitive dep of vite) needs its postinstall to run so it can extract the platform-specific binary. pnpm's warning: "Ignored build scripts: esbuild@0.21.5, esbuild@0.25.12. Run `pnpm approve-builds` to pick which dependencies should be allowed to run scripts." Vite would then fail at runtime trying to find the missing binary.
- **Fix:** Added `pnpm.onlyBuiltDependencies: ["esbuild"]` to `frontend/package.json`. Re-ran `pnpm install`; the two esbuild postinstalls (one for vite's transitive dep, one for vitest's transitive dep) ran cleanly.
- **Files modified:** `frontend/package.json` (added `pnpm.onlyBuiltDependencies` block)
- **Verification:** `pnpm install` runs the postinstalls; `pnpm build` produces `dist/`; `pnpm test:e2e` boots the preview server (which uses esbuild internally).
- **Committed in:** `f755908` (Task 1 scaffold commit)

### Plan Wording Deviations (Honored CONTEXT.md Locks Over Plan Implementation Sketch)

**6. shadcn/ui base primitives (Button, Card, Tabs, Badge) NOT vendored in Wave 1**

The plan's `must_haves.truths` list includes "shadcn/ui base setup: frontend/src/components/ui/.gitkeep exists (dir reserved for vendored primitives in Wave 2-3)". This is the AUTHORITATIVE language — the success criteria explicitly defer primitive vendoring to Wave 2-3. The phase-level success criteria block in the prompt mentions "Button, Card, Tabs, Badge minimum — others added in later waves as needed", but per the plan + CONTEXT.md, the dir is RESERVED in Wave 1 and primitives are added on-demand in Wave 2-3 when the first component that needs them is built. Wave 1 ships `components.json` (shadcn CLI config) + the empty `ui/` dir; Wave 2 will run `pnpm dlx shadcn@latest add button card tabs badge` when needed.

This is a deliberate scoping choice — vendoring primitives now would mean writing tests for primitives that no Wave 1 component imports, padding the wave artificially. Wave 2 vendors what it actually uses.

### Toolchain Notes

- **Node 24.14.1** (machine default) used; pnpm 10.33.2.
- **Playwright chromium binary ~111MB** downloaded once. webkit + mobile-chrome binaries NOT downloaded yet (Wave 4 fires `pnpm exec playwright install webkit` when mobile-safari + mobile-chrome project tests start running).
- **Windows line-ending warnings** during `git add` (LF will be replaced by CRLF) — Windows-default behavior; non-issue (git auto-normalizes on checkout).

---

**Total deviations:** 5 auto-fixed (4 Rule 1 bugs in toolchain config + 1 Rule 3 blocking pnpm policy) + 1 plan-wording clarification. Zero scope creep — all fixes tighten the locked plan scope.

## Issues Encountered

None — plan executed end-to-end without architectural decisions or auth gates. All 5 deviations were auto-fixable toolchain quirks (TypeScript composite-project rule, vitest peer-dep mismatch, gitignore omission, vite/client typings, pnpm 10 strict policy) caught during the first verify-command run on each task.

## User Setup Required

**For local development:**
- The committed `.env.local` has placeholder values (`example-user` / `example-repo`); fetches will hit `https://raw.githubusercontent.com/example-user/example-repo/main/data/...` and 404. To dev against real data, edit `.env.local` to point at the actual user/repo (DO NOT commit real values — `.env.local` is gitignored). Wave 4 ErrorBoundary will render explicit 404 messages rather than crash.

**For Vercel deploy (Wave 4 closeout, NOT Wave 1):**
- Set `VITE_GH_USER` + `VITE_GH_REPO` as Production + Preview environment variables in Vercel Project Settings → Environment Variables.
- First deploy: connect the repo to Vercel; Vercel auto-detects Vite + uses `vercel.json`'s `pnpm install` + `pnpm build` + `dist` settings.
- Verify the production URL loads `/scan/today` and shows the placeholder heading (Wave 1 baseline) → confirms env vars + build pipeline work.

## Next Phase Readiness

**Ready for Plan 06-03 (Morning Scan — Wave 2):**

- All 6 zod schemas + their parsed types available via `import { SnapshotSchema, type Snapshot } from '@/schemas'`.
- `fetchAndParse` + URL builders ready: Wave 2 components will write `useQuery({ queryKey: ['snapshot', date, ticker], queryFn: () => fetchAndParse(snapshotUrl(date, ticker), SnapshotSchema) })` without any plumbing setup.
- `computeStaleness` ready: Wave 2's `StalenessBadge` component imports it directly + binds to `_status.json.partial` + `_index.json.run_completed_at`.
- Notion-Clean palette tokens are first-class Tailwind utilities: `<div className="bg-surface border border-border text-fg">` works today.
- `components/ui/.gitkeep` reserves the shadcn vendoring dir; Wave 2 runs `pnpm dlx shadcn@latest add button card tabs badge` when the first lens tab needs them.
- Stub routes (`ScanRoute` / `TickerRoute`) are pure-function placeholders Wave 2/3 fully replace; no API contract to honor between waves.
- Smoke E2E (`tests/e2e/smoke.spec.ts`) is the canary — Wave 2/3 add additional E2E specs (`morning-scan.spec.ts`, `deep-dive.spec.ts`) alongside it; the smoke spec keeps proving the bundle boots.

**No blockers for Wave 2.** Plan 06-02 closes complete.

## Self-Check: PASSED

Verified at completion:

| Claim | Verification |
|---|---|
| frontend/ scaffold exists with all 24 task-1 files | `git ls-tree -r HEAD frontend/ \| wc -l` → 43 (24 task-1 + 13 task-2 schemas/tests + 5 task-3 lib/tests + vite-env.d.ts) |
| package.json declares vite ^6, react ^19, react-router ^7, zod ^4, lightweight-charts ^5.2 | `grep -E '"vite":\|"react":\|"react-router":\|"zod":\|"lightweight-charts":' frontend/package.json` → all 5 present at ^6/^19/^7/^4/^5.2 floors |
| 6 zod schema files exist | `ls frontend/src/schemas/*.ts` → agent_signal/position_signal/ticker_decision/snapshot/status/dates_index/index = 7 files (6 schemas + 1 barrel) |
| schema_version: z.literal(2) on TickerDecision + Snapshot | `grep -n "schema_version: z.literal(2)" frontend/src/schemas/{ticker_decision,snapshot}.ts` → 2 matches |
| computeStaleness + 6h/24h constants | `grep -nE "6 \* 60 \* 60 \* 1000\|24 \* 60 \* 60 \* 1000" frontend/src/lib/staleness.ts` → 2 matches |
| SchemaMismatchError class | `grep -n "class SchemaMismatchError" frontend/src/lib/fetchSnapshot.ts` → match |
| Notion-Clean palette in src/index.css | `grep -nE "color-bg.*0e0f11\|color-surface.*1f2024\|color-accent.*5b9dff" frontend/src/index.css` → 3 matches |
| Vercel rewrite for SPA fallback | `grep -n '"rewrites"' frontend/vercel.json` → match |
| 3 commits exist | `git log --oneline -3` → 7b2e9ff (Task 3) / 1ee1959 (Task 2) / f755908 (Task 1) |
| 94 vitest tests pass | `pnpm test:unit --run` final line: `Test Files 8 passed (8) / Tests 94 passed (94)` |
| Smoke E2E green on chromium-desktop | `pnpm test:e2e --project=chromium-desktop -g smoke` final line: `1 passed (1.8s)` |
| pnpm typecheck clean | `pnpm typecheck` exits 0 with no output |
| pnpm build green | `pnpm build` produces `dist/index.html` + `dist/assets/index-*.css` (6.54kB) + `dist/assets/index-*.js` (315.60kB) |
| frontend/.gitignore + repo-root .gitignore extended | `grep -E "frontend/\|node_modules\|dist" .gitignore frontend/.gitignore` → matches in both |

---
*Phase: 06-frontend-mvp-morning-scan-deep-dive*
*Completed: 2026-05-04*
