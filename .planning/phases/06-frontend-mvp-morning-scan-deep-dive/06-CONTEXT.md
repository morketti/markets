# Phase 6: Frontend MVP — Morning Scan + Deep-Dive — Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Source:** User decisions (post-research) on three blocking gaps

<domain>
## Phase Boundary

Static React app deployed to Vercel that reads daily JSON snapshots from `raw.githubusercontent.com/<user>/<repo>/main/data/...` and renders:

1. **Morning Scan view** — three lens tabs (Position Adjustment / Short-Term Opportunities / Long-Term Thesis Status); only one visible at a time.
2. **Per-Ticker Deep-Dive** — dual-timeframe cards + OHLC chart with overlays + persona signal cards + news feed grouped by source + Open Claude Analyst observation pinned at top.
3. **Staleness badge** in header — GREEN/AMBER/RED based on snapshot age + `_status.json.partial` flag.
4. **Mobile-responsive** — passes manual phone test on iOS Safari + Android Chrome.

**Phase 6 also includes a Wave 0 amendment to Phase 5 storage** (per research finding — see Decisions below) so that the frontend has the data shape it needs.

**Out of phase boundary** (do NOT include here):

- Decision-Support route with recommendation banner + dissent surface — Phase 7 (VIEW-10).
- Mid-day refresh function (`api/refresh.py`) — Phase 8.
- Memory log / historical persona signal trend view — Phase 8 / v1.x.
- Endorsement capture or rendering — Phase 9.

</domain>

<decisions>
## Implementation Decisions

### Storage Amendment (LOCKED — user choice "A")

A small Wave 0 inside Phase 6 amends `routine/storage.py` and `synthesis/decision.py` so the per-ticker JSON shape includes everything the frontend needs:

**Add to per-ticker JSON `data/YYYY-MM-DD/{TICKER}.json`:**

- `ohlc_history`: list of last 180 trading days, each with `{date, open, high, low, close, volume}` — sourced from the same yfinance fetch the analysts already do; just persisted instead of discarded.
- `indicators`: dict of pre-computed series aligned to `ohlc_history`:
  - `ma20`, `ma50` — simple moving averages (matches Phase 3 technicals analyst math).
  - `bb_upper`, `bb_lower` — Bollinger Bands (20-period, 2σ; matches Phase 4 position_adjustment math).
  - `rsi14` — RSI(14) (Wilder smoothing; matches `analysts/_indicator_math.py`).
- `headlines`: list of recent news items, each `{source, published_at, title, url}` — captured during ingestion (Phase 2's `ingestion/news.py` already fetches these for sentiment scoring; Wave 0 just persists the raw list before VADER scoring discards them).

**Add to `synthesis/decision.py`:**

- `TimeframeBand.thesis_status: ThesisStatus` — new field, `Literal["intact", "weakening", "broken", "improving", "n/a"]`. Default `"n/a"` (so existing snapshots and lite-mode TickerDecisions don't break).
- The synthesizer prompt must populate this field per timeframe — instruction added to `prompts/synthesizer.md`.

**Add to `data/YYYY-MM-DD/_index.json`:**

- `dates_available`: sorted list of YYYY-MM-DD strings — used by VIEW-14 historical date selector. (One small additional file `data/_dates.json` at repo root, regenerated each run, gives the frontend a single fetch to know what dates exist without enumerating GitHub directory listings.)

**Wave 0 also bumps `schema_version` from 1 → 2** in TickerDecision and the per-ticker JSON. Frontend zod schemas validate against `schema_version: 2`; older v1 snapshots render with a "schema upgrade required — re-run today's routine" banner instead of crashing.

### Staleness Thresholds (LOCKED — user choice "REQUIREMENTS.md")

Per VIEW-11 in REQUIREMENTS.md:

- **GREEN** — snapshot age < 6 hours AND `_status.json.partial == false`
- **AMBER** — snapshot age 6-24 hours, OR `_status.json.partial == true` (any age)
- **RED** — snapshot age > 24 hours

Reason: 2h GREEN window is too tight for a 6am ET routine — would flip AMBER before noon on a regular day. 6h gives a normal trading day's worth of green.

ROADMAP.md text says 2h/12h — that's a documentation bug. **Fix in Phase 6 Wave 0**: update ROADMAP.md Phase 6 success criterion #5 to match REQUIREMENTS.md.

### Visual Direction (LOCKED — user choice "Notion-Clean")

Dark-theme dashboard, information-dense but soft. Reference points:

- **Notion** — inline cards, subtle borders, conversational density.
- **Linear** — sharp typography, restrained color palette (one accent, mostly grayscale).
- **Vercel dashboard** — generous gutters, content-first, no chrome.

Concretely:

- Background: deep neutral gray (e.g., `#0E0F11`), not pure black.
- Surface (cards, panels): one-step-lighter neutral with hairline border (`#1F2024` background, `#2A2C30` border).
- Text: high-contrast off-white for primary (`#E8E9EB`); muted gray for secondary (`#8B8E94`).
- Accent: single color with restraint — recommended `#5B9DFF` blue for actionable elements, plus state colors (green for bullish, red for bearish, amber for neutral/pending).
- Typography: Inter (UI) + JetBrains Mono (numerics, ticker symbols). System fallback both.
- Spacing: 8px base unit; generous (`p-6`, `gap-6` Tailwind). Lots of `pt-12` between sections.
- Borders + shadow: `border` over `shadow` — 1px hairlines, no heavy drop shadows.
- Charts: lightweight-charts with custom dark theme matching surface palette; gridlines barely visible (`#252628`).
- Motion: minimal — opacity fade on lens tab switch, no slide/zoom; respect `prefers-reduced-motion`.

NOT this aesthetic: Bloomberg-Terminal-dense, Robinhood-glossy, neumorphic, glassmorphism, animated backgrounds, gradient hero blocks.

### Stack (LOCKED — research-confirmed 2026 versions)

- **Build**: Vite 6 + TypeScript 5.6
- **Framework**: React 19 (the 2026 stable)
- **Styling**: Tailwind v4 (CSS-first config) + shadcn/ui (vendored Radix primitives — copy into `src/components/ui/`, don't install as a package)
- **State**: TanStack Query v5 for server state; React `useState`/`useReducer` for local — no Redux, no Zustand v1.
- **Routing**: react-router v7 (data-router mode).
- **Validation**: zod v4. One zod schema file per Pydantic file in `src/schemas/`. Hand-authored for v1 (Pydantic→zod codegen evaluated in Phase 8 / v1.x — research recommends `pydantic2zod` but defer until schemas stabilize).
- **Charts**: lightweight-charts 5.2 with a thin React wrapper at `src/components/Chart.tsx` (researcher cited current API in 06-RESEARCH.md).
- **Test**: vitest + React Testing Library for components/hooks; Playwright for the manual-phone-test gate (one happy-path E2E per route, headed-iOS-emulator profile).
- **Package manager**: pnpm (per STACK.md project-wide lock).
- **Deploy**: Vercel static (no serverless functions in Phase 6 — those land in Phase 8).

### Routes (LOCKED — two-route v1)

- `/` → redirect to `/scan/today` (or to `/scan/<latest-available-date>` from `_dates.json`).
- `/scan/:date?lens=position|short|long` — Morning Scan view. URL drives lens selection so links share which lens was open.
- `/ticker/:symbol/:date?` — Per-Ticker Deep-Dive. Date defaults to latest.

A `/decision/:symbol` route is **deferred to Phase 7** (per ROADMAP — Phase 7 is the Decision-Support View). Phase 6's deep-dive renders the recommendation but Phase 7 builds the dedicated banner UI.

### GitHub Repo Configuration (LOCKED)

The frontend reads from `raw.githubusercontent.com/${VITE_GH_USER}/${VITE_GH_REPO}/main/data/...` where both env vars are baked at Vite build time (defined in `.env.production` and `.env.local`). No runtime config.json — that adds an extra fetch and complicates Vercel preview deploys.

### Empty/Partial Data Handling (UNIFORM RULE — same as Phase 1-5)

Every fetched JSON gets zod-validated. Failures render an explicit error state, not a crash:

- Snapshot folder missing for the chosen date → "No snapshot for {date}. Latest available: {latest}." with a link.
- Per-ticker JSON missing (ticker not in today's snapshot) → "{ticker} not in today's run. {reason from _status.json.failed_tickers/skipped_tickers}".
- Per-ticker JSON has `data_unavailable: true` → render whatever is present + "Data unavailable for some signals — last known {N} hours ago" banner.
- zod schema mismatch → "Schema version mismatch — frontend v{X}, snapshot v{Y}. Re-run today's routine or upgrade frontend." (No silent fallback — explicit, with both versions surfaced.)

### Provenance

Frontend code carries provenance comments only where adapted from a reference. shadcn/ui copies retain their original copyright header; Vite/React/Tailwind boilerplate doesn't need attribution. Custom components are novel-to-this-project.

### Testing Surface

- `src/schemas/__tests__/*.test.ts` — zod schemas round-trip tested against fixture JSONs derived from real Phase 5 outputs.
- `src/lib/staleness.test.ts` — GREEN/AMBER/RED threshold logic + `_status.json.partial` flag handling.
- `src/components/__tests__/*.test.tsx` — RTL component tests for Lens tabs, Persona Signal Card, Staleness Badge, Open Claude Analyst Pinned section, OHLC Chart wrapper.
- `tests/e2e/*.spec.ts` — Playwright happy-path: open `/scan/today`, switch lenses, click ticker, see deep-dive, see chart render with overlays, see staleness badge.
- Coverage gates: ≥90% line / ≥85% branch on `src/schemas/` and `src/lib/`. Components are RTL-tested for behavior, not coverage.

### Dependencies (new — Python side, Wave 0 only)

No new Python deps. Wave 0 reuses existing `analysts/_indicator_math.py` for MA/BB/RSI computation; existing `ingestion/news.py` already fetches headlines (just persist them instead of discard).

### Dependencies (new — frontend side)

```json
{
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router": "^7.0.0",
    "@tanstack/react-query": "^5.59.0",
    "zod": "^4.0.0",
    "lightweight-charts": "^5.2.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.5.0"
  },
  "devDependencies": {
    "vite": "^6.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.6.0",
    "tailwindcss": "^4.0.0",
    "vitest": "^2.1.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/dom": "^10.0.0",
    "playwright": "^1.48.0",
    "@playwright/test": "^1.48.0"
  }
}
```

shadcn/ui pulls in additional Radix peers as components are added — those vendor in via the shadcn CLI rather than appearing in `package.json` directly.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- **Phase 5 atomic-write pattern** (`routine/storage.py`) — Wave 0 extends the existing three-phase atomic write to handle the larger payload; no new pattern needed.
- **`analysts/_indicator_math.py`** — `_build_df`, `_adx_14`, `_total_to_verdict` already centralize the indicator math. Wave 0 adds `_ma_series`, `_bb_series`, `_rsi_series` to this same module so frontend overlays use byte-identical math to what the analysts use for verdicts.
- **`ingestion/news.py`** — fetches RSS headlines for sentiment scoring. Wave 0 changes the function signature to return `(headlines_list, sentiment_score)` instead of just `sentiment_score`, so storage can persist the raw headlines.
- **`prompts/synthesizer.md`** — Wave 0 adds an instruction to populate the new `thesis_status` field per timeframe.
- **`synthesis/decision.py`** — Wave 0 adds the `ThesisStatus` Literal + `TimeframeBand.thesis_status` field with sensible default. Schema version bumped 1 → 2.

### Established Patterns from Phase 5

- **Stable JSON serialization** — frontend reads what backend writes, byte-identical.
- **`schema_version` field** — frontend reads + asserts. Mismatch → explicit error.
- **`data_unavailable: true` UNIFORM RULE** — frontend handles this on every signal type.
- **Atomic write contract** — frontend never sees partial JSON files (writes are tmp + os.replace).

### Integration Points

- **Reads from**: `raw.githubusercontent.com/<user>/<repo>/main/data/YYYY-MM-DD/{TICKER}.json` + `_index.json` + `_status.json` + `data/_dates.json`.
- **Writes to**: nothing — frontend is read-only in Phase 6. Phase 8 adds the mid-day refresh function (`api/refresh.py` Vercel serverless) which Phase 6's frontend can opt into by triggering on deep-dive page open.
- **Vercel deploy**: Vite static build → Vercel auto-deploys on push to `main`. Preview deploys on PRs.

### Constraints from Existing Architecture

- **Keyless data plane** (PROJECT.md) — no Anthropic/yfinance/EDGAR keys in the repo. The frontend NEVER fetches market data directly — only the snapshot JSONs.
- **GitHub-as-DB** — frontend latency is `raw.githubusercontent.com` CDN (~30s of edge cache acceptable). No Supabase / no other DB in v1.
- **Single-user, no auth** — no login screen, no user profile, no session management.

</code_context>

<specifics>
## Specific Ideas

### File Layout

```
frontend/
├─ src/
│  ├─ schemas/                    # zod schemas (one per Pydantic file)
│  │  ├─ ticker_decision.ts
│  │  ├─ agent_signal.ts
│  │  ├─ position_signal.ts
│  │  ├─ status.ts
│  │  └─ index.ts                 # re-exports + parsed type aliases
│  ├─ lib/
│  │  ├─ fetchSnapshot.ts         # TanStack Query queryFn — GitHub raw fetch + zod parse
│  │  ├─ staleness.ts             # GREEN/AMBER/RED logic
│  │  └─ format.ts                # number/date formatting
│  ├─ components/
│  │  ├─ ui/                      # shadcn/ui vendored primitives
│  │  ├─ StalenessBadge.tsx       # header badge
│  │  ├─ Chart.tsx                # lightweight-charts React wrapper
│  │  ├─ PersonaCard.tsx          # one persona's AgentSignal rendered
│  │  ├─ OpenClaudePin.tsx        # Open Claude Analyst pinned-at-top component
│  │  ├─ LensTabs.tsx             # three-lens tab UI with URL sync
│  │  ├─ NewsList.tsx             # headlines grouped by source
│  │  ├─ TimeframeCard.tsx        # short_term + long_term card
│  │  └─ ErrorBoundary.tsx        # zod-mismatch catcher
│  ├─ routes/
│  │  ├─ ScanRoute.tsx            # /scan/:date
│  │  ├─ TickerRoute.tsx          # /ticker/:symbol/:date?
│  │  └─ root.tsx                 # outlet + header + staleness
│  ├─ App.tsx                     # router setup
│  ├─ main.tsx                    # entrypoint
│  └─ index.css                   # Tailwind v4 directives + theme tokens
├─ tests/
│  └─ e2e/                        # Playwright specs
├─ public/
├─ index.html
├─ package.json
├─ tsconfig.json
├─ vite.config.ts
├─ tailwind.config.ts
├─ playwright.config.ts
├─ vitest.config.ts
└─ .env.example                   # VITE_GH_USER, VITE_GH_REPO documented
```

(Whether this lives under `frontend/` or at the repo root TBD by planner — `frontend/` keeps Python and React cleanly separated; root makes Vercel deploy slightly simpler. Recommend `frontend/`.)

### File Sizes Expected

Wave 0 (Phase 5 amendment):
- `analysts/_indicator_math.py`: +60 lines (3 series helpers)
- `ingestion/news.py`: small refactor for return shape (~15 lines)
- `routine/storage.py`: +40 lines (assemble new fields into the per-ticker dict)
- `routine/run_for_watchlist.py`: +20 lines (thread headlines + ohlc through)
- `synthesis/decision.py`: +12 lines (`ThesisStatus` + field + default)
- `prompts/synthesizer.md`: +20 lines (thesis_status instruction)
- `data/_dates.json` writer: +30 lines in `routine/storage.py`
- Tests: ~150 lines

Wave 1 (frontend scaffold + schemas + fetch layer):
- `src/schemas/*`: ~200 lines total
- `src/lib/fetchSnapshot.ts`: ~80 lines
- `src/lib/staleness.ts`: ~40 lines
- App scaffold + routing: ~150 lines

Wave 2 (Morning Scan three-lens):
- `LensTabs.tsx`: ~80 lines
- `ScanRoute.tsx`: ~150 lines
- Three lens-specific list/card components: ~250 lines total

Wave 3 (Per-Ticker Deep-Dive):
- `TickerRoute.tsx`: ~200 lines
- `Chart.tsx`: ~150 lines (lightweight-charts wrapper)
- `PersonaCard.tsx` + `OpenClaudePin.tsx` + `NewsList.tsx` + `TimeframeCard.tsx`: ~400 lines

Wave 4 (Polish + responsiveness + Playwright):
- StalenessBadge wiring + ErrorBoundary + responsive breakpoints: ~120 lines
- Playwright E2E: ~150 lines

Total: ~2,000-2,500 lines TypeScript/TSX + ~300 lines Python amendment + ~500 lines tests.

### Schema Codegen Note (deferred)

The 2026-current option is `pydantic2zod` (research cited it). Phase 6 hand-authors zod schemas. Phase 8 (or v1.x) revisits — once Phase 5+6 schemas have stabilized through real use. CI check ("Pydantic and zod schemas drift") lands in Phase 8.

### Vercel Deploy Mechanics

- Vite build → `dist/` static folder → Vercel CDN.
- Build command: `pnpm build`. Output dir: `dist`.
- Env vars: `VITE_GH_USER`, `VITE_GH_REPO` configured in Vercel dashboard.
- Preview deploys: every PR gets a `*.vercel.app` URL — useful for taste-checking design changes against real data.
- Custom domain: deferred (default `.vercel.app` URL is fine for personal use).

</specifics>

<deferred>
## Deferred Ideas

- **`/decision/:symbol` route** — Phase 7 (Decision-Support View + Dissent Surface).
- **Mid-day refresh function** + on-open foreground refetch — Phase 8 (REFRESH-01..04).
- **Memory-log historical signal trend view** — Phase 8 / v1.x.
- **Endorsement capture UI** — Phase 9.
- **Pydantic→zod schema codegen + CI drift check** — Phase 8 / v1.x.
- **Notification / email digest on AMBER→RED staleness** — v2 territory.
- **PWA / offline cache** — v1.x; Phase 6 ships network-required.
- **Multiple watchlist views** — single-watchlist v1; v1.x.
- **Custom alerts on signal thresholds** — v1.x.
- **Dark/light theme toggle** — v1 ships dark-only (per PROJECT.md lock); light theme is v1.x.
- **Multi-day signal comparison view** ("how did Buffett's Nvidia signal evolve last 30 days") — needs Phase 8's memory log; v1.x.

</deferred>

---

*Phase: 06-frontend-mvp-morning-scan-deep-dive*
*Context gathered: 2026-05-04*
*User locks captured post-research (3 high-impact gaps resolved): A / REQUIREMENTS.md / Notion-Clean*
