---
phase: 06-frontend-mvp-morning-scan-deep-dive
plan: 02
type: execute
wave: 1
depends_on: [06-01]
files_modified:
  - frontend/package.json
  - frontend/pnpm-lock.yaml
  - frontend/tsconfig.json
  - frontend/tsconfig.node.json
  - frontend/vite.config.ts
  - frontend/vitest.config.ts
  - frontend/playwright.config.ts
  - frontend/index.html
  - frontend/.env.example
  - frontend/.env.local
  - frontend/.gitignore
  - frontend/vercel.json
  - frontend/postcss.config.js
  - frontend/tailwind.config.ts
  - frontend/src/index.css
  - frontend/src/main.tsx
  - frontend/src/App.tsx
  - frontend/src/lib/utils.ts
  - frontend/src/lib/fetchSnapshot.ts
  - frontend/src/lib/staleness.ts
  - frontend/src/lib/format.ts
  - frontend/src/schemas/index.ts
  - frontend/src/schemas/agent_signal.ts
  - frontend/src/schemas/position_signal.ts
  - frontend/src/schemas/ticker_decision.ts
  - frontend/src/schemas/snapshot.ts
  - frontend/src/schemas/status.ts
  - frontend/src/schemas/dates_index.ts
  - frontend/src/schemas/__tests__/agent_signal.test.ts
  - frontend/src/schemas/__tests__/position_signal.test.ts
  - frontend/src/schemas/__tests__/ticker_decision.test.ts
  - frontend/src/schemas/__tests__/snapshot.test.ts
  - frontend/src/schemas/__tests__/status.test.ts
  - frontend/src/schemas/__tests__/dates_index.test.ts
  - frontend/src/lib/__tests__/staleness.test.ts
  - frontend/src/lib/__tests__/fetchSnapshot.test.ts
  - frontend/src/routes/ScanRoute.tsx
  - frontend/src/routes/TickerRoute.tsx
  - frontend/src/routes/Root.tsx
  - frontend/src/components/ui/.gitkeep
  - frontend/tests/e2e/smoke.spec.ts
  - .gitignore
autonomous: true
requirements: [INFRA-05]
gap_closure: false
tags: [phase-6, wave-1, scaffold, frontend, vite, react, typescript, tailwind, zod, tanstack-query, react-router, vercel]

must_haves:
  truths:
    - "frontend/ directory exists with Vite 6 + React 19 + TypeScript 5.6 + Tailwind v4 + shadcn/ui CLI configured project"
    - "package.json declares exact deps from CONTEXT.md: react ^19, react-dom ^19, react-router ^7, @tanstack/react-query ^5.59, zod ^4, lightweight-charts ^5.2, clsx ^2.1, tailwind-merge ^2.5"
    - "package.json devDeps: vite ^6, @vitejs/plugin-react ^4.3, typescript ^5.6, tailwindcss ^4, vitest ^2.1, @testing-library/react ^16, @testing-library/dom ^10, playwright ^1.48, @playwright/test ^1.48, @types/react ^19, @types/react-dom ^19, @types/node"
    - "package.json scripts: `dev` (vite), `build` (tsc -b && vite build), `preview` (vite preview), `test:unit` (vitest), `test:e2e` (playwright test), `lint` (tsc --noEmit + eslint OR tsc --noEmit alone if eslint deferred), `typecheck` (tsc --noEmit)"
    - "pnpm install completes without error; pnpm-lock.yaml committed"
    - "frontend/vite.config.ts configures @vitejs/plugin-react + path alias `@` → `./src` + Tailwind v4 plugin"
    - "frontend/tailwind.config.ts (or @import 'tailwindcss' in CSS — Tailwind v4 CSS-first config preferred) defines Notion-Clean palette tokens: --bg #0E0F11, --surface #1F2024, --border #2A2C30, --text-primary #E8E9EB, --text-secondary #8B8E94, --accent #5B9DFF, plus state colors green/red/amber"
    - "frontend/src/index.css imports Tailwind v4 + sets dark theme via :root selectors with the palette tokens above; sets base font-family Inter (with system fallback) + JetBrains Mono for .font-mono"
    - "frontend/src/schemas/ contains 6 zod schema files (one per relevant Pydantic file): agent_signal.ts, position_signal.ts, ticker_decision.ts, snapshot.ts (per-ticker JSON wrapper that combines all the above), status.ts, dates_index.ts"
    - "Each zod schema validates the schema_version=2 contract from Wave 0 (TickerDecision schema_version: z.literal(2))"
    - "ticker_decision schema includes ThesisStatus z.enum(['intact','weakening','broken','improving','n/a']) and TimeframeBand carries thesis_status field"
    - "snapshot.ts (the per-ticker JSON shape) validates the new ohlc_history + indicators + headlines fields from Wave 0"
    - "Each zod schema has a corresponding __tests__ file with at least one happy-path round-trip test using a fixture JSON OR an inline JSON literal that mirrors a real Phase 5 output shape; tests must include at least one schema_version mismatch test (rejects schema_version=1) per CONTEXT.md error-handling rule"
    - "frontend/src/lib/staleness.ts exports `computeStaleness(snapshotIso: string, partial: boolean, now?: Date): 'GREEN' | 'AMBER' | 'RED'` implementing VIEW-11 thresholds: GREEN if age<6h && !partial; RED if age>24h; AMBER otherwise (covers 6-24h regardless of partial AND <6h+partial)"
    - "staleness.test.ts has parametrized tests covering: <6h non-partial → GREEN; <6h partial → AMBER; 6h-24h non-partial → AMBER; 6h-24h partial → AMBER; >24h non-partial → RED; >24h partial → RED; boundary cases at exactly 6h and exactly 24h"
    - "frontend/src/lib/fetchSnapshot.ts exports a TanStack Query queryFn factory that takes a URL + zod schema and returns the parsed object; throws an error of kind `SchemaMismatchError` on zod parse failure (frontend renders error state per CONTEXT.md UNIFORM RULE)"
    - "fetchSnapshot.test.ts uses fetch mock (vi.fn or msw) to test happy path + 404 path + zod-mismatch path"
    - "frontend/src/App.tsx wires react-router v7 data-router mode with routes: `/` redirect to `/scan/today`; `/scan/:date` → ScanRoute (stub); `/ticker/:symbol/:date?` → TickerRoute (stub); Root layout has the staleness badge slot in header (placeholder div in Wave 1 — populated in Wave 2/4)"
    - "TanStack Query QueryClient + QueryClientProvider wraps the router in main.tsx with sane defaults: staleTime: 5*60*1000 (5min), refetchOnWindowFocus: false (matches GitHub-as-DB read-mostly model)"
    - "frontend/.env.example documents VITE_GH_USER + VITE_GH_REPO (build-time env vars); frontend/.env.local committed with placeholder values for local dev (NOT real user/repo — use 'example-user'/'example-repo')"
    - "frontend/vercel.json configures static build: `framework: vite`, `buildCommand: pnpm build`, `outputDirectory: dist`, `installCommand: pnpm install` (Vercel auto-detects but explicit is safer for preview deploys)"
    - "frontend/playwright.config.ts configures: testDir: './tests/e2e', projects: [{name: 'chromium-desktop'}, {name: 'mobile-safari', use: {...devices['iPhone 14']}}, {name: 'mobile-chrome', use: {...devices['Pixel 7']}}], baseURL: 'http://localhost:4173' (vite preview port)"
    - "tests/e2e/smoke.spec.ts has 1 trivial test that opens / and asserts the page redirects to /scan/today and renders SOMETHING (a placeholder text in the stub Wave 1 ScanRoute is fine — Wave 2 builds the real content)"
    - "repo-root .gitignore extended with frontend-specific lines: frontend/node_modules, frontend/dist, frontend/.vite, frontend/playwright-report, frontend/test-results, frontend/coverage"
    - "shadcn/ui base setup: frontend/src/components/ui/.gitkeep exists (dir reserved for vendored primitives in Wave 2-3); shadcn CLI config (`components.json` at frontend root) declares Notion-Clean style tokens for shadcn copy operations"
    - "Wave 1 verification command passes: `cd frontend && pnpm install && pnpm typecheck && pnpm test:unit --run && pnpm build && pnpm test:e2e --project=chromium-desktop -g smoke`"
  artifacts:
    - path: "frontend/package.json"
      provides: "Vite 6 + React 19 + Tailwind v4 + zod + TanStack Query + react-router v7 + lightweight-charts + vitest + Playwright deps; 7 npm scripts"
      min_lines: 40
    - path: "frontend/pnpm-lock.yaml"
      provides: "deterministic lockfile committed"
      min_lines: 1
    - path: "frontend/tsconfig.json"
      provides: "strict TypeScript config with paths alias @ → ./src"
      min_lines: 25
    - path: "frontend/vite.config.ts"
      provides: "@vitejs/plugin-react + tailwindcss/vite + path resolve alias"
      min_lines: 15
    - path: "frontend/vitest.config.ts"
      provides: "vitest config with jsdom environment + RTL setup"
      min_lines: 15
    - path: "frontend/playwright.config.ts"
      provides: "3 projects: chromium-desktop + mobile-safari + mobile-chrome"
      min_lines: 30
    - path: "frontend/tailwind.config.ts"
      provides: "Tailwind v4 config OR @import 'tailwindcss' CSS-first; Notion-Clean palette tokens"
      min_lines: 1
    - path: "frontend/src/index.css"
      provides: "Tailwind v4 directives + dark theme color tokens + base typography"
      min_lines: 30
    - path: "frontend/src/main.tsx"
      provides: "React 19 createRoot + QueryClientProvider + RouterProvider"
      min_lines: 20
    - path: "frontend/src/App.tsx"
      provides: "createBrowserRouter with /, /scan/:date, /ticker/:symbol/:date? routes"
      min_lines: 30
    - path: "frontend/src/lib/utils.ts"
      provides: "cn() helper (clsx + tailwind-merge composition) — shadcn/ui standard"
      min_lines: 6
    - path: "frontend/src/lib/fetchSnapshot.ts"
      provides: "TanStack Query queryFn factory + SchemaMismatchError class + GitHub raw URL builder"
      min_lines: 60
    - path: "frontend/src/lib/staleness.ts"
      provides: "computeStaleness with VIEW-11 thresholds (6h/24h)"
      min_lines: 35
    - path: "frontend/src/lib/format.ts"
      provides: "formatNumber, formatDate, formatTicker — JetBrains Mono numeric formatting helpers"
      min_lines: 25
    - path: "frontend/src/schemas/agent_signal.ts"
      provides: "zod schema mirroring analysts/signals.py AgentSignal shape (5-state Verdict + analyst_id Literal of 10 IDs + 0-100 confidence + evidence list + data_unavailable)"
      min_lines: 30
    - path: "frontend/src/schemas/position_signal.ts"
      provides: "zod schema mirroring analysts/position_signal.py PositionSignal (5-state PositionState + 4-state ActionHint + consensus_score [-1,1] + confidence + evidence + trend_regime)"
      min_lines: 35
    - path: "frontend/src/schemas/ticker_decision.ts"
      provides: "zod schema mirroring synthesis/decision.py: TickerDecision + TimeframeBand (with thesis_status from Wave 0) + DissentSection + DecisionRecommendation enum + ConvictionBand enum + ThesisStatus enum + schema_version z.literal(2)"
      min_lines: 60
    - path: "frontend/src/schemas/snapshot.ts"
      provides: "per-ticker JSON shape (data/{date}/{TICKER}.json): combines all schemas above + ohlc_history (Wave 0 field) + indicators (Wave 0 field with 5 series) + headlines (Wave 0 field) + errors list + schema_version z.literal(2)"
      min_lines: 50
    - path: "frontend/src/schemas/status.ts"
      provides: "zod schema for _status.json (success, partial, completed_tickers, failed_tickers, skipped_tickers, llm_failure_count, lite_mode)"
      min_lines: 20
    - path: "frontend/src/schemas/dates_index.ts"
      provides: "zod schema for data/_dates.json (Wave 0 file): schema_version z.literal(1) + dates_available list + updated_at"
      min_lines: 15
    - path: "frontend/src/schemas/index.ts"
      provides: "barrel re-exports of all 6 schemas + their inferred TypeScript types via z.infer"
      min_lines: 15
    - path: "frontend/src/schemas/__tests__/agent_signal.test.ts"
      provides: "happy path + invalid analyst_id + data_unavailable invariant + schema_version mismatch tests"
      min_lines: 40
    - path: "frontend/src/schemas/__tests__/position_signal.test.ts"
      provides: "happy path + state out-of-enum + consensus_score out-of-range + data_unavailable invariant"
      min_lines: 40
    - path: "frontend/src/schemas/__tests__/ticker_decision.test.ts"
      provides: "happy path + recommendation enum + thesis_status enum + schema_version=2 enforcement (rejects schema_version=1)"
      min_lines: 50
    - path: "frontend/src/schemas/__tests__/snapshot.test.ts"
      provides: "happy path + schema_version=2 enforcement + ohlc_history shape + indicators 5-series shape + headlines shape"
      min_lines: 50
    - path: "frontend/src/schemas/__tests__/status.test.ts"
      provides: "happy path + missing required field rejection"
      min_lines: 25
    - path: "frontend/src/schemas/__tests__/dates_index.test.ts"
      provides: "happy path + sorted dates assertion + invalid date format rejection"
      min_lines: 25
    - path: "frontend/src/lib/__tests__/staleness.test.ts"
      provides: "8+ parametrized tests covering VIEW-11 thresholds + boundary cases"
      min_lines: 40
    - path: "frontend/src/lib/__tests__/fetchSnapshot.test.ts"
      provides: "happy path + 404 + zod mismatch path with mocked fetch"
      min_lines: 50
    - path: "frontend/src/routes/ScanRoute.tsx"
      provides: "Wave 1 stub: reads :date param; renders <h1>Morning Scan — {date}</h1> placeholder; Wave 2 fills in real content"
      min_lines: 15
    - path: "frontend/src/routes/TickerRoute.tsx"
      provides: "Wave 1 stub: reads :symbol + :date params; renders <h1>{symbol} — {date}</h1> placeholder; Wave 3 fills in real content"
      min_lines: 15
    - path: "frontend/src/routes/Root.tsx"
      provides: "layout with header (staleness badge slot — placeholder div) + main outlet"
      min_lines: 25
    - path: "frontend/components.json"
      provides: "shadcn/ui CLI config with Notion-Clean style + path aliases"
      min_lines: 15
    - path: "frontend/vercel.json"
      provides: "Vercel static deploy config"
      min_lines: 8
    - path: "frontend/.env.example"
      provides: "VITE_GH_USER + VITE_GH_REPO documentation"
      min_lines: 8
    - path: "frontend/tests/e2e/smoke.spec.ts"
      provides: "1 smoke test — page loads + redirects to /scan/today"
      min_lines: 20
  key_links:
    - from: "frontend/src/lib/fetchSnapshot.ts"
      to: "raw.githubusercontent.com/<VITE_GH_USER>/<VITE_GH_REPO>/main/data/..."
      via: "fetch + zod schema parse"
      pattern: "raw\\.githubusercontent\\.com|VITE_GH_USER"
    - from: "frontend/src/schemas/snapshot.ts"
      to: "Wave 0 storage.py per-ticker JSON"
      via: "schema_version z.literal(2)"
      pattern: "schema_version.*z\\.literal\\(2\\)"
    - from: "frontend/src/lib/staleness.ts"
      to: "VIEW-11 thresholds"
      via: "6h/24h hardcoded constants matching REQUIREMENTS.md"
      pattern: "6 \\* 60 \\* 60 \\* 1000|24 \\* 60 \\* 60 \\* 1000"
    - from: "frontend/src/App.tsx"
      to: "react-router v7 data-router routes"
      via: "createBrowserRouter"
      pattern: "createBrowserRouter|RouterProvider"
---

<objective>
Initialize the frontend/ Vite + React 19 + TypeScript + Tailwind v4 + shadcn/ui project. Author all 6 zod schemas (one per relevant Pydantic file from Phases 3/4/5 + Wave 0). Build the GitHub raw fetch + zod parse layer. Build the staleness logic with VIEW-11 thresholds. Configure Vite, vitest, Playwright (3 projects: chromium-desktop + mobile-safari + mobile-chrome), Vercel deploy. Wire react-router v7 with stub route components — Waves 2 and 3 populate them.

Purpose: Lock the frontend infrastructure so Waves 2-4 add behavior, not boilerplate. Every JSON read goes through zod (per VIEW-15); schema mismatches surface as explicit error states (per CONTEXT.md UNIFORM RULE); staleness logic is pure-function and unit-tested before any visual component depends on it.

Output: A pnpm-installable frontend/ project with green vitest unit tests + a green Playwright smoke test on chromium-desktop. Vercel preview deploy works (or fails for VITE_* env-var reasons, which is documented for the user). Wave 2 imports the schemas + fetchSnapshot + staleness + Tailwind palette without modification.
</objective>

<execution_context>
@C:/Users/Mohan/.claude/workflows/execute-plan.md
@C:/Users/Mohan/.claude/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-CONTEXT.md
@.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-RESEARCH.md
@.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-VALIDATION.md
@.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-01-SUMMARY.md

# Pydantic source-of-truth for zod schema mirrors
@analysts/signals.py
@analysts/position_signal.py
@synthesis/decision.py

# Wave 0 storage shape source-of-truth
@routine/storage.py

<interfaces>
<!-- Pydantic shapes (Phase 3/4/5 + Wave 0) the zod schemas must mirror exactly -->

From analysts/signals.py:
```python
AnalystId = Literal["fundamentals", "technicals", "news_sentiment", "valuation",
                    "buffett", "munger", "wood", "burry", "lynch", "claude_analyst"]
Verdict = Literal["strong_bullish", "bullish", "neutral", "bearish", "strong_bearish"]

class AgentSignal(BaseModel):
    analyst_id: AnalystId
    ticker: str
    computed_at: datetime
    verdict: Verdict
    confidence: int  # 0-100
    reasoning: str   # ≤200 chars
    evidence: list[str]  # ≤10 items, each ≤200 chars
    data_unavailable: bool = False
    # Invariant: data_unavailable=True ⟹ verdict='neutral' AND confidence=0
```

From analysts/position_signal.py:
```python
PositionState = Literal["extreme_oversold", "oversold", "fair", "overbought", "extreme_overbought"]
ActionHint = Literal["consider_add", "hold_position", "consider_trim", "consider_take_profits"]

class PositionSignal(BaseModel):
    ticker: str
    computed_at: datetime
    state: PositionState
    consensus_score: float  # [-1, 1]
    confidence: int  # 0-100
    action_hint: ActionHint
    evidence: list[str]
    trend_regime: bool
    data_unavailable: bool = False
```

From synthesis/decision.py (POST Wave 0):
```python
DecisionRecommendation = Literal["add", "trim", "hold", "take_profits", "buy", "avoid"]
ConvictionBand = Literal["low", "medium", "high"]
Timeframe = Literal["short_term", "long_term"]
ThesisStatus = Literal["intact", "weakening", "broken", "improving", "n/a"]  # NEW Wave 0

class TimeframeBand(BaseModel):
    summary: str  # 1-500 chars
    drivers: list[str]  # ≤10, each ≤200 chars
    confidence: int  # 0-100
    thesis_status: ThesisStatus = "n/a"  # NEW Wave 0

class DissentSection(BaseModel):
    has_dissent: bool
    dissenting_persona: str | None  # one of 6 persona IDs
    dissent_summary: str  # ≤500 chars

class TickerDecision(BaseModel):
    ticker: str
    computed_at: datetime
    schema_version: int = 2  # Wave 0 BUMPED 1→2
    recommendation: DecisionRecommendation
    conviction: ConvictionBand
    short_term: TimeframeBand
    long_term: TimeframeBand
    open_observation: str  # ≤500 chars
    dissent: DissentSection
    data_unavailable: bool = False
```

From routine/storage.py per-ticker payload (POST Wave 0):
```python
{
    "ticker": str,
    "schema_version": 2,  # Wave 0 BUMPED
    "analytical_signals": list[AgentSignal_dict],  # 4 entries
    "position_signal": PositionSignal_dict | None,
    "persona_signals": list[AgentSignal_dict],  # 6 entries
    "ticker_decision": TickerDecision_dict | None,
    "ohlc_history": list[{"date": "YYYY-MM-DD", "open": float, "high": float,
                          "low": float, "close": float, "volume": int}],  # NEW Wave 0
    "indicators": {                                                         # NEW Wave 0
        "ma20": list[float | None],     # aligned to ohlc_history
        "ma50": list[float | None],
        "bb_upper": list[float | None],
        "bb_lower": list[float | None],
        "rsi14": list[float | None],
    },
    "headlines": list[{"source": str, "published_at": str_iso8601,         # NEW Wave 0
                       "title": str, "url": str}],
    "errors": list[str],
}
```

From routine/storage.py _status.json:
```python
{
    "success": bool,
    "partial": bool,
    "completed_tickers": list[str],
    "failed_tickers": list[str],
    "skipped_tickers": list[str],
    "llm_failure_count": int,
    "lite_mode": bool,
}
```

From routine/storage.py data/_dates.json (NEW Wave 0):
```python
{
    "schema_version": 1,
    "dates_available": list[str],  # sorted YYYY-MM-DD
    "updated_at": str_iso8601,
}
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Vite + React + Tailwind + tooling scaffold</name>
  <files>frontend/package.json, frontend/pnpm-lock.yaml, frontend/tsconfig.json, frontend/tsconfig.node.json, frontend/vite.config.ts, frontend/vitest.config.ts, frontend/playwright.config.ts, frontend/index.html, frontend/src/main.tsx, frontend/src/App.tsx, frontend/src/index.css, frontend/tailwind.config.ts, frontend/postcss.config.js, frontend/components.json, frontend/.env.example, frontend/.env.local, frontend/.gitignore, frontend/vercel.json, frontend/src/lib/utils.ts, frontend/src/components/ui/.gitkeep, frontend/src/routes/ScanRoute.tsx, frontend/src/routes/TickerRoute.tsx, frontend/src/routes/Root.tsx, frontend/tests/e2e/smoke.spec.ts, .gitignore</files>
  <action>
    1. Create `frontend/` directory at repo root.
    2. Initialize via `cd frontend && pnpm init` then edit package.json directly (do NOT use `pnpm create vite` — manual is more controllable):
       - "type": "module"
       - dependencies (exact versions): react ^19.0.0, react-dom ^19.0.0, react-router ^7.0.0, @tanstack/react-query ^5.59.0, zod ^4.0.0, lightweight-charts ^5.2.0, clsx ^2.1.0, tailwind-merge ^2.5.0
       - devDependencies: vite ^6.0.0, @vitejs/plugin-react ^4.3.0, typescript ^5.6.0, tailwindcss ^4.0.0, @tailwindcss/vite ^4.0.0, vitest ^2.1.0, jsdom ^25, @testing-library/react ^16.0.0, @testing-library/dom ^10.0.0, @testing-library/jest-dom ^6, playwright ^1.48.0, @playwright/test ^1.48.0, @types/react ^19, @types/react-dom ^19, @types/node, @types/testing-library__jest-dom
       - scripts: `"dev": "vite"`, `"build": "tsc -b && vite build"`, `"preview": "vite preview"`, `"test:unit": "vitest"`, `"test:e2e": "playwright test"`, `"typecheck": "tsc --noEmit"`, `"postinstall": "playwright install chromium webkit"`
    3. Run `pnpm install` (this generates pnpm-lock.yaml + installs Playwright browsers via postinstall).
    4. Create `tsconfig.json` (strict, target ES2022, jsx react-jsx, paths "@/*": ["./src/*"], references to tsconfig.node.json) and `tsconfig.node.json` (for vite.config.ts).
    5. Create `vite.config.ts`:
       ```ts
       import { defineConfig } from 'vite'
       import react from '@vitejs/plugin-react'
       import tailwindcss from '@tailwindcss/vite'
       import path from 'node:path'
       export default defineConfig({
         plugins: [react(), tailwindcss()],
         resolve: { alias: { '@': path.resolve(__dirname, './src') } },
       })
       ```
    6. Create `vitest.config.ts` (extends vite config; environment 'jsdom'; setupFiles ['./src/setupTests.ts']; coverage v8 with thresholds 90/85 on src/schemas + src/lib).
    7. Create `playwright.config.ts` per VALIDATION.md sampling: testDir './tests/e2e', baseURL 'http://localhost:4173', webServer { command: 'pnpm preview', port: 4173, reuseExistingServer: !process.env.CI }, projects: chromium-desktop / mobile-safari (devices['iPhone 14']) / mobile-chrome (devices['Pixel 7']).
    8. Create `index.html` (minimal Vite shell, references /src/main.tsx, lang='en', title 'Markets').
    9. Create `src/index.css`:
       ```css
       @import 'tailwindcss';
       @theme {
         --color-bg: #0E0F11;
         --color-surface: #1F2024;
         --color-border: #2A2C30;
         --color-text-primary: #E8E9EB;
         --color-text-secondary: #8B8E94;
         --color-accent: #5B9DFF;
         --color-bullish: #4ADE80;
         --color-bearish: #F87171;
         --color-amber: #FBBF24;
         --color-grid: #252628;
         --font-sans: 'Inter', system-ui, sans-serif;
         --font-mono: 'JetBrains Mono', ui-monospace, monospace;
         --spacing: 8px;
       }
       :root { color-scheme: dark; }
       body { background: var(--color-bg); color: var(--color-text-primary); font-family: var(--font-sans); }
       ```
    10. Create `tailwind.config.ts` as a minimal stub (Tailwind v4 is CSS-first; the config file is mostly for IDE integration). Optional — can be omitted in v4. Include if @tailwindcss/vite needs it for content scanning.
    11. Create `src/main.tsx`:
        ```tsx
        import { StrictMode } from 'react'
        import { createRoot } from 'react-dom/client'
        import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
        import { RouterProvider } from 'react-router/dom'
        import { router } from './App'
        import './index.css'
        const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 5*60*1000, refetchOnWindowFocus: false }}})
        createRoot(document.getElementById('root')!).render(
          <StrictMode>
            <QueryClientProvider client={queryClient}>
              <RouterProvider router={router} />
            </QueryClientProvider>
          </StrictMode>
        )
        ```
    12. Create `src/App.tsx` with createBrowserRouter from 'react-router' (v7 API):
        ```tsx
        import { createBrowserRouter, redirect } from 'react-router'
        import Root from './routes/Root'
        import ScanRoute from './routes/ScanRoute'
        import TickerRoute from './routes/TickerRoute'
        export const router = createBrowserRouter([
          { path: '/', loader: () => redirect('/scan/today'), element: null },
          { path: '/', element: <Root />, children: [
            { path: 'scan/:date', element: <ScanRoute /> },
            { path: 'ticker/:symbol/:date?', element: <TickerRoute /> },
          ]},
        ])
        ```
    13. Create stub route components:
        - `src/routes/Root.tsx`: header with staleness badge slot (`<header className="border-b border-border px-6 py-4"><div data-testid="staleness-slot">SCAN</div></header>`) + `<main className="px-6 py-8"><Outlet /></main>`
        - `src/routes/ScanRoute.tsx`: reads useParams to get :date; renders `<h1 className="text-2xl font-semibold">Morning Scan — {date}</h1>` placeholder
        - `src/routes/TickerRoute.tsx`: useParams symbol + date; renders `<h1>{symbol} — {date ?? 'today'}</h1>` placeholder
    14. Create `src/lib/utils.ts`:
        ```ts
        import { clsx, type ClassValue } from 'clsx'
        import { twMerge } from 'tailwind-merge'
        export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)) }
        ```
    15. Create `src/components/ui/.gitkeep` so the dir exists for shadcn vendoring in Wave 2-3.
    16. Create `components.json` (shadcn/ui CLI config):
        ```json
        {
          "$schema": "https://ui.shadcn.com/schema.json",
          "style": "default",
          "rsc": false,
          "tsx": true,
          "tailwind": { "config": "", "css": "src/index.css", "baseColor": "neutral", "cssVariables": true, "prefix": "" },
          "aliases": { "components": "@/components", "utils": "@/lib/utils", "ui": "@/components/ui", "lib": "@/lib", "hooks": "@/hooks" }
        }
        ```
    17. Create `.env.example` documenting:
        ```
        # Required: which GitHub repo holds the data/ folder the frontend reads.
        VITE_GH_USER=your-github-username
        VITE_GH_REPO=markets
        ```
        Create `.env.local` with placeholder values (`VITE_GH_USER=example-user`, `VITE_GH_REPO=example-repo`) so dev mode boots; .env.local is .gitignored (next step).
    18. Create `frontend/.gitignore`:
        ```
        node_modules
        dist
        .vite
        playwright-report
        test-results
        coverage
        .env.local
        ```
    19. Extend repo-root `.gitignore` with frontend-specific lines (mirroring frontend/.gitignore, scoped to `frontend/`).
    20. Create `vercel.json`:
        ```json
        {
          "framework": "vite",
          "installCommand": "pnpm install",
          "buildCommand": "pnpm build",
          "outputDirectory": "dist",
          "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
        }
        ```
        (rewrites entry is critical — react-router v7 client-side routing on Vercel needs SPA fallback to index.html).
    21. Create `tests/e2e/smoke.spec.ts`:
        ```ts
        import { test, expect } from '@playwright/test'
        test('redirects / to /scan/today', async ({ page }) => {
          await page.goto('/')
          await expect(page).toHaveURL(/\/scan\/today/)
          await expect(page.getByRole('heading', { name: /Morning Scan — today/i })).toBeVisible()
        })
        ```
    22. Create `src/setupTests.ts` (vitest setup): `import '@testing-library/jest-dom'`.
    23. Run: `cd frontend && pnpm typecheck && pnpm build && pnpm test:e2e --project=chromium-desktop -g smoke` — confirm all three pass.
    24. Commit with: `feat(06-02): scaffold frontend Vite+React+TS+Tailwind+router+Playwright`
  </action>
  <verify>
    <automated>cd frontend && pnpm typecheck && pnpm build && pnpm test:e2e --project=chromium-desktop -g smoke 2>&1 | tail -10</automated>
  </verify>
  <done>frontend/ scaffolded; pnpm install + typecheck + build + smoke e2e all pass; commit landed.</done>
</task>

<task type="auto">
  <name>Task 2: zod schemas (one per Pydantic file) + schema unit tests</name>
  <files>frontend/src/schemas/agent_signal.ts, frontend/src/schemas/position_signal.ts, frontend/src/schemas/ticker_decision.ts, frontend/src/schemas/snapshot.ts, frontend/src/schemas/status.ts, frontend/src/schemas/dates_index.ts, frontend/src/schemas/index.ts, frontend/src/schemas/__tests__/agent_signal.test.ts, frontend/src/schemas/__tests__/position_signal.test.ts, frontend/src/schemas/__tests__/ticker_decision.test.ts, frontend/src/schemas/__tests__/snapshot.test.ts, frontend/src/schemas/__tests__/status.test.ts, frontend/src/schemas/__tests__/dates_index.test.ts</files>
  <action>
    1. **agent_signal.ts** — author zod schema mirroring AgentSignal exactly (see <interfaces>). Use z.enum for Literals. Key code:
       ```ts
       export const AnalystIdSchema = z.enum(['fundamentals','technicals','news_sentiment','valuation','buffett','munger','wood','burry','lynch','claude_analyst'])
       export const VerdictSchema = z.enum(['strong_bullish','bullish','neutral','bearish','strong_bearish'])
       export const AgentSignalSchema = z.object({
         analyst_id: AnalystIdSchema,
         ticker: z.string(),
         computed_at: z.string().datetime(),
         verdict: VerdictSchema,
         confidence: z.number().int().min(0).max(100),
         reasoning: z.string().max(200),
         evidence: z.array(z.string().max(200)).max(10),
         data_unavailable: z.boolean().default(false),
       }).refine(d => !d.data_unavailable || (d.verdict === 'neutral' && d.confidence === 0), {
         message: 'data_unavailable=true requires verdict=neutral AND confidence=0',
       })
       export type AgentSignal = z.infer<typeof AgentSignalSchema>
       ```
    2. **position_signal.ts** — same pattern; PositionStateSchema (5 enum), ActionHintSchema (4 enum), PositionSignalSchema with consensus_score in [-1,1] via z.number().min(-1).max(1), trend_regime: z.boolean(). Add the data_unavailable invariant refinement.
    3. **ticker_decision.ts** — DecisionRecommendationSchema (6 enum), ConvictionBandSchema (3 enum), TimeframeSchema (2 enum), ThesisStatusSchema (5 enum), TimeframeBandSchema (with thesis_status default 'n/a'), DissentSectionSchema, TickerDecisionSchema with `schema_version: z.literal(2)` (NOT z.number — strict literal so v1 snapshots are rejected — frontend renders schema-mismatch error per CONTEXT.md UNIFORM RULE).
    4. **snapshot.ts** — the per-ticker JSON shape (data/{date}/{TICKER}.json):
       ```ts
       export const OHLCBarSchema = z.object({
         date: z.string(), open: z.number(), high: z.number(),
         low: z.number(), close: z.number(), volume: z.number().int(),
       })
       export const IndicatorsSchema = z.object({
         ma20: z.array(z.number().nullable()),
         ma50: z.array(z.number().nullable()),
         bb_upper: z.array(z.number().nullable()),
         bb_lower: z.array(z.number().nullable()),
         rsi14: z.array(z.number().nullable()),
       })
       export const HeadlineSchema = z.object({
         source: z.string(), published_at: z.string().datetime(),
         title: z.string(), url: z.string().url(),
       })
       export const SnapshotSchema = z.object({
         ticker: z.string(),
         schema_version: z.literal(2),
         analytical_signals: z.array(AgentSignalSchema),
         position_signal: PositionSignalSchema.nullable(),
         persona_signals: z.array(AgentSignalSchema),
         ticker_decision: TickerDecisionSchema.nullable(),
         ohlc_history: z.array(OHLCBarSchema),
         indicators: IndicatorsSchema,
         headlines: z.array(HeadlineSchema),
         errors: z.array(z.string()),
       })
       ```
    5. **status.ts** — _status.json shape:
       ```ts
       export const StatusSchema = z.object({
         success: z.boolean(), partial: z.boolean(),
         completed_tickers: z.array(z.string()),
         failed_tickers: z.array(z.string()),
         skipped_tickers: z.array(z.string()),
         llm_failure_count: z.number().int().min(0),
         lite_mode: z.boolean(),
       })
       ```
    6. **dates_index.ts** — data/_dates.json shape:
       ```ts
       export const DatesIndexSchema = z.object({
         schema_version: z.literal(1),
         dates_available: z.array(z.string().regex(/^\d{4}-\d{2}-\d{2}$/)),
         updated_at: z.string().datetime(),
       })
       ```
    7. **index.ts** barrel: re-export all 6 schemas + their inferred types via z.infer.
    8. For each schema, create __tests__/<schema>.test.ts with vitest. Each test file MUST cover:
       - happy path (valid input parses; type narrows correctly)
       - at least 1 invalid-shape rejection (wrong enum value, missing required field, wrong type)
       - schema-version-mismatch tests for snapshot.ts + ticker_decision.ts (rejects schema_version=1 — frontend renders error)
       - data_unavailable invariant for agent_signal + position_signal
       - dates_index rejects unsorted dates? — actually no, the schema does NOT enforce sortedness (storage.py writes them sorted); just verify parses + the regex catches invalid date strings
    9. Sample test fixture for snapshot.test.ts: hand-author a JSON literal that matches a real Phase 5 output shape (use the persona_signals: 6 entries with analyst_ids buffett/munger/wood/burry/lynch/claude_analyst — this catches a Phase 5 closeout bug if the schema ever diverges).
    10. Run: `cd frontend && pnpm test:unit src/schemas --run` — confirm all schema tests pass.
    11. Commit with: `feat(06-02): add zod schemas + schema unit tests for snapshot v2 contract`
  </action>
  <verify>
    <automated>cd frontend && pnpm test:unit src/schemas --run 2>&1 | tail -15</automated>
  </verify>
  <done>6 zod schemas authored; ~30+ schema tests pass; schema_version=1 rejection tests confirm frontend will surface schema-mismatch error per CONTEXT.md UNIFORM RULE.</done>
</task>

<task type="auto">
  <name>Task 3: fetchSnapshot + staleness + format helpers + lib unit tests</name>
  <files>frontend/src/lib/fetchSnapshot.ts, frontend/src/lib/staleness.ts, frontend/src/lib/format.ts, frontend/src/lib/__tests__/staleness.test.ts, frontend/src/lib/__tests__/fetchSnapshot.test.ts</files>
  <action>
    1. **src/lib/staleness.ts**:
       ```ts
       export type StalenessLevel = 'GREEN' | 'AMBER' | 'RED'
       const SIX_HOURS_MS = 6 * 60 * 60 * 1000
       const TWENTY_FOUR_HOURS_MS = 24 * 60 * 60 * 1000
       export function computeStaleness(snapshotIso: string, partial: boolean, now: Date = new Date()): StalenessLevel {
         const snapshotDate = new Date(snapshotIso)
         const ageMs = now.getTime() - snapshotDate.getTime()
         if (ageMs > TWENTY_FOUR_HOURS_MS) return 'RED'
         if (ageMs >= SIX_HOURS_MS) return 'AMBER'
         // age < 6h
         return partial ? 'AMBER' : 'GREEN'
       }
       ```
    2. **src/lib/fetchSnapshot.ts**:
       ```ts
       import { ZodSchema, z } from 'zod'
       export class SchemaMismatchError extends Error {
         constructor(public url: string, public zodError: z.ZodError) {
           super(`Schema mismatch at ${url}: ${zodError.message}`)
           this.name = 'SchemaMismatchError'
         }
       }
       export class FetchNotFoundError extends Error {
         constructor(public url: string) { super(`Not found: ${url}`); this.name = 'FetchNotFoundError' }
       }
       const GH_USER = import.meta.env.VITE_GH_USER ?? 'example-user'
       const GH_REPO = import.meta.env.VITE_GH_REPO ?? 'example-repo'
       export const RAW_BASE = `https://raw.githubusercontent.com/${GH_USER}/${GH_REPO}/main`
       export async function fetchAndParse<T>(url: string, schema: ZodSchema<T>): Promise<T> {
         const res = await fetch(url, { headers: { 'Accept': 'application/json' } })
         if (res.status === 404) throw new FetchNotFoundError(url)
         if (!res.ok) throw new Error(`Fetch ${url} failed: ${res.status}`)
         const json = await res.json()
         const result = schema.safeParse(json)
         if (!result.success) throw new SchemaMismatchError(url, result.error)
         return result.data
       }
       export const snapshotUrl = (date: string, ticker: string) => `${RAW_BASE}/data/${date}/${ticker}.json`
       export const indexUrl    = (date: string)                => `${RAW_BASE}/data/${date}/_index.json`
       export const statusUrl   = (date: string)                => `${RAW_BASE}/data/${date}/_status.json`
       export const datesUrl    = ()                             => `${RAW_BASE}/data/_dates.json`
       ```
    3. **src/lib/format.ts**: small helpers — formatNumber (Intl.NumberFormat), formatDate (YYYY-MM-DD or relative), formatTicker (uppercase + hyphen normalization to match analysts/schemas.normalize_ticker conceptually).
    4. **src/lib/__tests__/staleness.test.ts**: 8+ parametrized vitest tests covering: <6h non-partial → GREEN; <6h partial → AMBER; exactly 6h non-partial → AMBER; exactly 6h partial → AMBER; 12h non-partial → AMBER; 12h partial → AMBER; exactly 24h non-partial → AMBER; >24h non-partial → RED; >24h partial → RED. Use a frozen `now` arg (Date) for determinism.
    5. **src/lib/__tests__/fetchSnapshot.test.ts**: mock `global.fetch` (vi.stubGlobal('fetch', vi.fn())); test 3 paths:
       - happy: returns 200 + valid JSON; resolves to parsed type-narrowed object
       - 404: throws FetchNotFoundError
       - zod mismatch: returns 200 + bad JSON; throws SchemaMismatchError carrying the zodError
       Use a tiny inline schema (e.g. z.object({ foo: z.string() })) — DO NOT pull in the real snapshot schemas (keeps test focused on fetch behavior).
    6. Run: `cd frontend && pnpm test:unit src/lib --run` — confirm all lib tests pass.
    7. Commit with: `feat(06-02): add fetchSnapshot + staleness + format with VIEW-11 thresholds + zod-mismatch error class`
  </action>
  <verify>
    <automated>cd frontend && pnpm test:unit --run 2>&1 | tail -15</automated>
  </verify>
  <done>fetchSnapshot + staleness + format authored; 12+ lib tests pass; full vitest run (schemas + lib) green; smoke e2e still passes; commit landed.</done>
</task>

</tasks>

<verification>
- All 3 tasks complete; commits landed
- `cd frontend && pnpm install && pnpm typecheck && pnpm test:unit --run && pnpm build && pnpm test:e2e --project=chromium-desktop -g smoke` all green
- 6 zod schemas exist + 6 schema test files passing (~30+ tests)
- staleness.ts + fetchSnapshot.ts + format.ts exist + tested (~12+ tests)
- Stub routes render (Wave 2 + 3 fill in real content)
- Vercel config + .env.example documented
- `frontend/.gitignore` + repo-root `.gitignore` updated
- shadcn/ui CLI configured (`components.json`) — Wave 2-3 vendor primitives
</verification>

<success_criteria>
- [ ] frontend/ project boots locally (`pnpm dev`) and serves /scan/today with placeholder content
- [ ] All 6 zod schemas validate Phase 5/Wave 0 fixture JSONs round-trip
- [ ] schema_version=1 rejected by snapshot + ticker_decision schemas (CONTEXT.md UNIFORM RULE)
- [ ] computeStaleness returns correct GREEN/AMBER/RED for all 9 boundary cases (VIEW-11 thresholds)
- [ ] fetchSnapshot throws SchemaMismatchError on zod parse failure (no silent fallback)
- [ ] vitest unit tests: 30+ schema + 12+ lib + 0 component (Wave 2-3 add component tests) → all green
- [ ] Playwright chromium-desktop smoke test green: `/` redirects to `/scan/today` and renders placeholder heading
- [ ] `pnpm build` produces dist/ with no TypeScript errors
- [ ] `vercel.json` configures SPA fallback (rewrite to /index.html) — react-router v7 client routing works on Vercel
- [ ] frontend/ files added to .gitignore correctly (no node_modules / dist / .env.local committed)
- [ ] 3 commits landed: `feat(06-02): scaffold` → `feat(06-02): zod schemas` → `feat(06-02): fetchSnapshot + staleness`
</success_criteria>

<output>
After completion, create `.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-02-SUMMARY.md` matching Phase 1-5 SUMMARY template — sections: Plan Identity / Wave / Outcome / Files Created / Tests Added / Coverage / Stack Versions Locked / Notes for Wave 2-3 (which schemas + lib helpers to import).
</output>
