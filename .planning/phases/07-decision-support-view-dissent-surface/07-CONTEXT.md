# Phase 7: Decision-Support View + Dissent Surface — Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Source:** Research-derived (research recommendations adopted)

<domain>
## Phase Boundary

A new `/decision/:symbol/:date?` route in the existing Phase 6 frontend, dedicated to the per-ticker buy/trim/hold/take-profits/buy/avoid recommendation with conviction band, drivers (short_term + long_term), dissent surface (always rendered), and snapshot-time price.

**Out of phase boundary** (do NOT include here):

- **Live current-price fetch + delta logic** — DEFERRED to Phase 8. Phase 7 renders snapshot price + timestamp + a `// PHASE-8-HOOK` marker so Phase 8's planner has a deterministic search target. Why: browser-side yfinance is CORS-blocked and Yahoo's anti-scrape blocks proxies; every keyed alternative violates the project's keyless data plane lock. Phase 8 owns `api/refresh.py` (Vercel Python serverless) and is the natural home.
- **Mid-day refresh on-demand recompute** — Phase 8.
- **Endorsement signals** — Phase 9.

</domain>

<decisions>
## Implementation Decisions

### Current-Price Delta (LOCKED — deferred to Phase 8)

Phase 7 renders the snapshot-time price with timestamp. Adjacent placeholder copy: **"Snapshot price as of {timestamp} ET. Current-price delta arrives via mid-day refresh in Phase 8."**

A `data-testid="current-price-placeholder"` attribute and a `// PHASE-8-HOOK: current-price-delta` source comment lock the integration point so Phase 8's plan-phase has a deterministic search target.

### Recommendation Banner (LOCKED)

Visual treatment per the 6 actions × 3 conviction bands matrix:

- **Action drives color (palette tokens from `frontend/src/index.css`):**
  - `add` / `buy` → `bg-bullish` (green `#4ADE80`)
  - `trim` / `take_profits` → `bg-neutral` (amber `#FBBF24`)
  - `hold` → `bg-fg-muted` (muted `#8B8E94`)
  - `avoid` → `bg-bearish` (red `#F87171`)
- **Conviction drives visual weight:**
  - `high` → `font-bold text-2xl` + filled accent border `border-accent/40`
  - `medium` → `font-semibold text-xl` + standard border
  - `low` → `font-normal text-lg` + muted border `border-border/50`
- **Conviction band is also a 3-dot indicator** (`ConvictionDots` component) — 1/2/3 filled circles, low/medium/high. Provides a visual scan-friendly secondary cue.

### Drivers List (LOCKED)

Two stacked cards (or side-by-side on lg breakpoint, mirroring `TimeframeCard` from Phase 6):

- **Short-term drivers card** — header "Short-term drivers"; bulleted list from `ticker_decision.short_term.drivers`; below: short_term confidence + thesis_status pill
- **Long-term drivers card** — header "Long-term drivers"; bulleted list from `ticker_decision.long_term.drivers`; below: long_term confidence + thesis_status pill

If a `drivers` list is empty: render "No drivers surfaced" muted text rather than collapsing the card. UNIFORM RULE — never silently absent.

### Dissent Panel (LOCKED — Pitfall #12 always-render)

`DissentPanel` is ALWAYS rendered — Pitfall #12 confirmation-bias guard. Two states:

- **`has_dissent: false`** — render with muted styling (`border-border/30 bg-surface/50`), text "All personas converged. No dissent surfaced." This is the "intentional silence" signal — no dissent doesn't mean missing-content.
- **`has_dissent: true`** — render with attention-getting styling. Header: "{dissenting_persona} dissents". Body: `dissent_summary`. Special case: when `dissenting_persona === 'claude_analyst'`, apply accent-tinted treatment (`border-accent/40 bg-accent/5` — same palette as `OpenClaudePin` from Phase 6) per the user's "Claude's reasoning surfaced alongside personas, never replaced" lock.

### Routing (LOCKED — third route)

Extend `frontend/src/App.tsx` data-router children array with `/decision/:symbol/:date?`. Cross-link symmetry:

- **TickerRoute (Phase 6)** — adds a "→ Decision view" link in the page header (small button or link, restrained accent color)
- **DecisionRoute (Phase 7)** — adds a "← Deep dive" link in the page header (mirror)

Both routes share the same data fetch (`fetchSnapshot` returns the per-ticker JSON which contains `ticker_decision`). DecisionRoute is the "what should I do" view; TickerRoute is the "what's the data" view.

`useActiveDate` hook in `Root.tsx` extends with one new pattern match for `/decision/:symbol/:date?` so the DateSelector + StalenessBadge work identically across all three routes.

### data_unavailable Handling (UNIFORM RULE)

When `ticker_decision.data_unavailable === true`: render the banner with muted "Data unavailable for some signals — recommendation may be partial" notice, but still show the recommendation (synthesizer always produces one, even with `data_unavailable=true` per Phase 5 lock). The `_data_unavailable_implies_safe_defaults` model validator from `synthesis/decision.py` guarantees `recommendation === 'hold'` and `conviction === 'low'` in this case — frontend can rely on this.

### Notion-Clean Discipline (LOCKED — extend Phase 6, do not deviate)

Every color from `frontend/src/index.css` palette tokens — no inline hex/rgb. Hairline borders, no shadows. Generous spacing (`p-6`, `gap-6`). Inter UI + JetBrains Mono numerics inherited.

### Provenance

`DecisionRoute.tsx` mirrors `TickerRoute.tsx` composition pattern. Reference comment: `// Pattern adapted from TickerRoute.tsx — same loading/error branches, different content focus`.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`frontend/src/schemas/ticker_decision.ts`** — already exports `DecisionRecommendation`, `ConvictionBand`, `Timeframe`, `DissentSection`, `TimeframeBand`, `TickerDecision` zod-parsed types. NO schema work in Phase 7.
- **`frontend/src/lib/fetchSnapshot.ts`** — `fetchAndParse<Snapshot>` is exactly what DecisionRoute needs.
- **`frontend/src/components/ui/`** — shadcn Card, Badge, Separator already vendored.
- **`frontend/src/components/StalenessBadge.tsx` + `DateSelector.tsx` + `ErrorBoundary.tsx`** — Root header components automatically work for `/decision/:symbol/:date?` once the route pattern matches in `useActiveDate`.
- **`frontend/src/components/VerdictBadge.tsx` + `ActionHintBadge.tsx`** — visual reference for the new RecommendationBanner.
- **`frontend/src/components/OpenClaudePin.tsx`** — accent-tinted styling pattern reused for claude_analyst dissent case.
- **`frontend/src/components/TimeframeCard.tsx`** — visual reference for the DriversList card layout.
- **`frontend/tests/fixtures/scan/AAPL.json` + `MSFT.json` + `NVDA.json`** — existing fixtures cover both `has_dissent: true` and `has_dissent: false` cases.

### Established Patterns

- **TanStack Query + `fetchAndParse` + `SchemaMismatchError`** — DecisionRoute uses identical pattern to TickerRoute.
- **Loading + error branches** — copy verbatim from TickerRoute (zod mismatch → SchemaMismatchView, 404 → NotFoundView, generic → ErrorBoundary).
- **URL-synced state via useSearchParams + useParams** — used by ScanRoute and TickerRoute; DecisionRoute inherits.

### Integration Points

- **Reads from**: same per-ticker JSON as TickerRoute (`data/YYYY-MM-DD/{TICKER}.json`).
- **Renders to**: new `/decision/:symbol/:date?` route.
- **Phase 8 hookpoint**: `data-testid="current-price-placeholder"` + `// PHASE-8-HOOK: current-price-delta` comment.

### Constraints from Existing Architecture

- **Notion-Clean palette** (Phase 6 lock) — every color from CSS variables.
- **schema_version: z.literal(2)** — already enforced by zod schema; no Phase 7 changes.
- **Pitfall #12 always-render dissent** — load-bearing for the user's confirmation-bias-guard intent.

</code_context>

<specifics>
## Specific Ideas

### File Layout

```
frontend/src/
├─ components/
│  ├─ RecommendationBanner.tsx     [new]
│  ├─ ConvictionDots.tsx           [new]
│  ├─ DriversList.tsx              [new]
│  └─ DissentPanel.tsx             [new]
├─ routes/
│  ├─ DecisionRoute.tsx            [new]
│  ├─ TickerRoute.tsx              [extend — add "→ Decision view" link]
│  └─ Root.tsx                     [extend — useActiveDate one-line addition]
└─ App.tsx                         [extend — add third route]
```

Plus tests:

```
frontend/src/components/__tests__/
├─ RecommendationBanner.test.tsx   [new — 6 actions × 3 convictions matrix + a11y]
├─ ConvictionDots.test.tsx         [new — 3 states]
├─ DriversList.test.tsx            [new — populated/empty branches]
└─ DissentPanel.test.tsx           [new — has_dissent true/false; claude_analyst accent case]
frontend/src/routes/__tests__/
└─ DecisionRoute.test.tsx          [new — loading/error/data branches; cross-link present]
frontend/tests/e2e/
└─ decision.spec.ts                [new — Playwright happy path: navigate from /ticker/AAPL → /decision/AAPL, see banner + drivers + dissent + cross-link back]
```

### File Sizes Expected

- `RecommendationBanner.tsx`: ~80-120 lines (color × weight matrix + ConvictionDots embed)
- `ConvictionDots.tsx`: ~30 lines (simple SVG or filled-circle component)
- `DriversList.tsx`: ~80-100 lines (two-card layout, empty-state handling)
- `DissentPanel.tsx`: ~80-100 lines (two-state rendering, claude_analyst accent treatment)
- `DecisionRoute.tsx`: ~150-200 lines (full composition, mirrors TickerRoute pattern)
- TickerRoute extension: ~5 lines
- Root extension: ~1 line (useActiveDate pattern match)
- App extension: ~3 lines (new route entry)
- Tests: ~600 lines TypeScript total

Total: ~1,000-1,200 lines TypeScript/TSX (production + tests).

### Testing Surface

- **Unit/component (vitest + RTL):** ~37 tests
  - 19 RecommendationBanner: 6 actions × 3 convictions matrix (18) + 1 a11y test (aria-label, focusable)
  - 4 DriversList: 2 timeframes × {populated, empty} = 4
  - 6 DissentPanel: has_dissent {true, false} × {generic, claude_analyst, missing-summary} = 6
  - 3 ConvictionDots: low/medium/high
  - 5 DecisionRoute: loading / 404 / schema-mismatch / has_dissent-true / has_dissent-false
- **E2E (Playwright):** 1 happy-path spec (chromium-desktop)
- **Coverage gates:** ≥90% line / ≥85% branch on the 5 new files.

### Recommendation Color × Conviction Weight Matrix

| Action | Color token | Low conviction | Medium conviction | High conviction |
|--------|-------------|----------------|-------------------|-----------------|
| add | bullish | font-normal text-lg, border-border/50 | font-semibold text-xl, border-border | font-bold text-2xl, border-accent/40 |
| buy | bullish | (same) | (same) | (same) |
| trim | neutral | (same) | (same) | (same) |
| take_profits | neutral | (same) | (same) | (same) |
| hold | fg-muted | (same) | (same) | (same) |
| avoid | bearish | (same) | (same) | (same) |

</specifics>

<deferred>
## Deferred Ideas

- **Live current-price fetch + delta logic** → Phase 8 (`api/refresh.py` Vercel serverless).
- **Decision-trail / "why this recommendation changed today vs yesterday"** — needs Phase 8 memory log; v1.x.
- **Endorsement-vs-recommendation comparison** ("our system says hold; newsletter X said buy 3 weeks ago at lower price") — Phase 9 + v1.x.
- **Mobile-tap-to-rerun-synthesizer** — needs Phase 8's mid-day refresh; v1.x.
- **Recommendation-history sparkline** ("hold/hold/hold/buy" last 5 days) — needs Phase 8 memory log; v1.x.
- **Conviction-weighted portfolio sizing hint** — out of scope by PROJECT.md (research tool, not trading system).

</deferred>

---

*Phase: 07-decision-support-view-dissent-surface*
*Context gathered: 2026-05-04*
*Single-wave phase (1 PLAN, 5 new files, ~37 tests, 0 new deps)*
