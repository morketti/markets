---
phase: 07-decision-support-view-dissent-surface
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/RecommendationBanner.tsx
  - frontend/src/components/ConvictionDots.tsx
  - frontend/src/components/DriversList.tsx
  - frontend/src/components/DissentPanel.tsx
  - frontend/src/components/__tests__/RecommendationBanner.test.tsx
  - frontend/src/components/__tests__/ConvictionDots.test.tsx
  - frontend/src/components/__tests__/DriversList.test.tsx
  - frontend/src/components/__tests__/DissentPanel.test.tsx
  - frontend/src/routes/DecisionRoute.tsx
  - frontend/src/routes/__tests__/DecisionRoute.test.tsx
  - frontend/src/routes/TickerRoute.tsx
  - frontend/src/routes/Root.tsx
  - frontend/src/App.tsx
  - frontend/tests/fixtures/scan/MSFT-no-dissent.json
  - frontend/tests/e2e/decision.spec.ts
  - frontend/tests/e2e/fixtures-server.ts
autonomous: true
requirements: [VIEW-10]

must_haves:
  truths:
    - "User opens /decision/AAPL/today and sees a recommendation banner with action+conviction visible at first paint"
    - "Banner color is driven by the action (add/buy → bullish; trim/take_profits → amber; hold → fg-muted; avoid → bearish); visual weight (font size + border) is driven by conviction (low/medium/high)"
    - "ConvictionDots renders exactly 3 dots (1/2/3 filled for low/medium/high) — never fewer than 3 total"
    - "Drivers list shows short_term and long_term drivers as two cards (side-by-side on lg, stacked on <lg); empty driver arrays render 'No drivers surfaced' muted text, not collapsed cards"
    - "DissentPanel is ALWAYS rendered — has_dissent: false shows muted 'All personas converged. No dissent surfaced.' panel; has_dissent: true shows persona name + dissent_summary"
    - "When dissenting_persona === 'claude_analyst', DissentPanel uses accent-tinted treatment (border-accent/40 bg-accent/5) — Open Claude is distinct from the 5 canonical personas"
    - "DecisionRoute renders typed-error branches verbatim from TickerRoute (FetchNotFoundError → '<symbol> not in snapshot for <date>'; SchemaMismatchError → 'Schema upgrade required')"
    - "TickerRoute header has '→ Decision view' cross-link; DecisionRoute header has '← Deep dive' cross-link; both preserve :symbol and :date"
    - "Root.tsx useActiveDate also matches /decision/:symbol/:date so DateSelector + StalenessBadge work identically across all three routes"
    - "data_unavailable: true snapshot renders muted 'Data unavailable for some signals — recommendation may be partial' notice ABOVE the banner; banner still shows Hold/low (per Phase 5 schema invariant)"
    - "ticker_decision === null (lite-mode) renders explicit amber 'No recommendation' notice (mirrors TickerRoute null-decision handling)"
    - "Phase 8 hookpoint: data-testid='current-price-placeholder' element with '// PHASE-8-HOOK: current-price-delta' source comment present in DecisionRoute.tsx"
    - "Zero new runtime dependencies; zero new theme tokens; every color from existing Notion-Clean palette tokens (no inline hex)"

  artifacts:
    - path: "frontend/src/components/RecommendationBanner.tsx"
      provides: "Hero banner — 6 actions × 3 convictions = 18 visual states; ConvictionDots embedded"
      exports: ["RecommendationBanner"]
      min_lines: 80
    - path: "frontend/src/components/ConvictionDots.tsx"
      provides: "3-dot conviction indicator (1/2/3 filled for low/medium/high; total always 3)"
      exports: ["ConvictionDots"]
      min_lines: 25
    - path: "frontend/src/components/DriversList.tsx"
      provides: "Two-card pair (short_term + long_term drivers); empty-state 'No drivers surfaced'"
      exports: ["DriversList"]
      min_lines: 60
    - path: "frontend/src/components/DissentPanel.tsx"
      provides: "Always-rendered dissent panel; has_dissent {true,false} branches; claude_analyst accent treatment"
      exports: ["DissentPanel"]
      min_lines: 80
    - path: "frontend/src/routes/DecisionRoute.tsx"
      provides: "/decision/:symbol/:date? composition — banner + drivers + dissent + Phase 8 placeholder"
      exports: ["default DecisionRoute"]
      min_lines: 120
      contains: "PHASE-8-HOOK"
    - path: "frontend/src/components/__tests__/RecommendationBanner.test.tsx"
      provides: "19 tests: 18 matrix (6×3) + 1 a11y (role=status)"
      min_lines: 50
    - path: "frontend/src/components/__tests__/ConvictionDots.test.tsx"
      provides: "3 tests: low/medium/high dot counts (asserts 3 total dots in every case)"
      min_lines: 25
    - path: "frontend/src/components/__tests__/DriversList.test.tsx"
      provides: "4 tests: short populated/empty × long populated/empty"
      min_lines: 50
    - path: "frontend/src/components/__tests__/DissentPanel.test.tsx"
      provides: "6 tests: has_dissent {true,false} × {generic, claude_analyst, missing-summary/unknown-persona}"
      min_lines: 60
    - path: "frontend/src/routes/__tests__/DecisionRoute.test.tsx"
      provides: "5 tests: loading / 404 / schema-mismatch / has_dissent-true / data_unavailable"
      min_lines: 80
    - path: "frontend/tests/fixtures/scan/MSFT-no-dissent.json"
      provides: "MSFT fixture with has_dissent: false (existing MSFT.json has has_dissent: true)"
      contains: '"has_dissent": false'
    - path: "frontend/tests/e2e/decision.spec.ts"
      provides: "1 Playwright spec: /scan → /ticker → /decision → /ticker round-trip; banner + drivers + dissent visible"
      min_lines: 50

  key_links:
    - from: "frontend/src/App.tsx"
      to: "frontend/src/routes/DecisionRoute.tsx"
      via: "third route entry: { path: 'decision/:symbol/:date?', element: <DecisionRoute /> }"
      pattern: "decision/:symbol/:date"
    - from: "frontend/src/routes/DecisionRoute.tsx"
      to: "frontend/src/lib/loadTickerData.ts"
      via: "useTickerData(date, symbol) — same hook + same query key as TickerRoute"
      pattern: "useTickerData"
    - from: "frontend/src/routes/DecisionRoute.tsx"
      to: "frontend/src/components/RecommendationBanner.tsx, DriversList.tsx, DissentPanel.tsx"
      via: "composition; banner first, drivers second, dissent always rendered last"
      pattern: "RecommendationBanner|DriversList|DissentPanel"
    - from: "frontend/src/routes/TickerRoute.tsx"
      to: "frontend/src/routes/DecisionRoute.tsx"
      via: "'→ Decision view' Link in heading row to /decision/:symbol/:date"
      pattern: "decision/\\$\\{symbol\\}"
    - from: "frontend/src/routes/Root.tsx"
      to: "frontend/src/routes/DecisionRoute.tsx"
      via: "useActiveDate — useMatches() iterator already returns :date from /decision/:symbol/:date? params (no regex change required; one-line confirmation/comment update)"
      pattern: "useMatches"
    - from: "frontend/src/components/DissentPanel.tsx"
      to: "frontend/src/components/OpenClaudePin.tsx"
      via: "shared accent-tinted styling (border-accent/40 bg-accent/5) when dissenting_persona === 'claude_analyst'"
      pattern: "border-accent/40"
    - from: "frontend/src/routes/DecisionRoute.tsx"
      to: "Phase 8 (api/refresh.py)"
      via: "data-testid='current-price-placeholder' + '// PHASE-8-HOOK: current-price-delta' source comment — Phase 8's grep finds these"
      pattern: "PHASE-8-HOOK"
---

<objective>
Ship the Decision-Support route at `/decision/:symbol/:date?` — the third pillar of the morning command center. Renders the buy/trim/hold/take-profits/buy/avoid recommendation with conviction band, dual-timeframe drivers, and an always-rendered dissent panel. Closes VIEW-10.

Purpose: VIEW-10 is the final view requirement and the load-bearing decision surface for the user's daily workflow. Pitfall #12 (confirmation-bias guard) requires the dissent panel be ALWAYS rendered — explicit "All personas converged" beats silent absence. Single requirement, single wave, zero new runtime deps — pure additive composition on the locked Phase 6 stack.

Output:
- 5 new components/routes (RecommendationBanner, ConvictionDots, DriversList, DissentPanel, DecisionRoute)
- 5 new test files (~37 vitest tests)
- 1 new Playwright spec + 1 new fixture (MSFT-no-dissent.json)
- 3 small extensions (App.tsx +3 LOC, TickerRoute.tsx +5 LOC, Root.tsx +1 LOC if needed)
- Phase 8 hookpoint marker for current-price-delta deferral
</objective>

<execution_context>
@C:/Users/Mohan/.claude/workflows/execute-plan.md
@C:/Users/Mohan/.claude/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/07-decision-support-view-dissent-surface/07-CONTEXT.md
@.planning/phases/07-decision-support-view-dissent-surface/07-RESEARCH.md
@.planning/phases/07-decision-support-view-dissent-surface/07-VALIDATION.md

# Phase 6 reference assets (read-only — pattern source, do not modify except where this plan explicitly extends)
@frontend/src/routes/TickerRoute.tsx
@frontend/src/routes/Root.tsx
@frontend/src/App.tsx
@frontend/src/schemas/ticker_decision.ts
@frontend/src/components/OpenClaudePin.tsx
@frontend/src/components/TimeframeCard.tsx
@frontend/src/components/PersonaCard.tsx
@frontend/src/components/VerdictBadge.tsx
@frontend/src/components/ActionHintBadge.tsx
@frontend/src/lib/loadTickerData.ts
@frontend/src/lib/fetchSnapshot.ts
@frontend/src/lib/utils.ts
@frontend/tests/fixtures/scan/AAPL.json
@frontend/tests/fixtures/scan/MSFT.json
@frontend/tests/e2e/deep-dive.spec.ts
@frontend/tests/e2e/fixtures-server.ts

<interfaces>
<!-- Schema types are already exported from @/schemas — DO NOT redefine. Import directly. -->

From frontend/src/schemas/ticker_decision.ts (already exported via @/schemas):
```typescript
export type DecisionRecommendation = 'add' | 'trim' | 'hold' | 'take_profits' | 'buy' | 'avoid'
export type ConvictionBand = 'low' | 'medium' | 'high'
export type Timeframe = 'short_term' | 'long_term'
export type ThesisStatus = 'intact' | 'weakening' | 'broken' | 'improving' | 'n/a'

export interface TimeframeBand {
  summary: string         // 1-500 chars
  drivers: string[]       // 0-10 entries, each ≤200 chars  ← THIS IS WHAT DriversList RENDERS
  confidence: number      // int 0-100
  thesis_status: ThesisStatus
}

export interface DissentSection {
  has_dissent: boolean
  dissenting_persona: string | null   // when has_dissent: false this can be null
  dissent_summary: string             // 0-500 chars; may be empty when has_dissent: false
}

export interface TickerDecision {
  ticker: string
  computed_at: string                 // ISO 8601 — used by Phase 8 hookpoint placeholder
  schema_version: 2                   // literal — no version bump in Phase 7
  recommendation: DecisionRecommendation
  conviction: ConvictionBand
  short_term: TimeframeBand
  long_term: TimeframeBand
  open_observation: string
  dissent: DissentSection
  data_unavailable: boolean           // when true ⟹ recommendation='hold' AND conviction='low' (zod refine)
}
```

From frontend/src/lib/loadTickerData.ts (existing — REUSE; do not redefine):
```typescript
export function useTickerData(date: string, symbol: string): {
  data: Snapshot | undefined
  isLoading: boolean
  error: Error | undefined
}
// Snapshot.ticker_decision: TickerDecision | null   ← null in lite-mode runs
```

From frontend/src/lib/fetchSnapshot.ts (existing — REUSE typed errors):
```typescript
export class FetchNotFoundError extends Error { /* ... */ }
export class SchemaMismatchError extends Error { /* ... */ }
```

From frontend/src/lib/utils.ts (existing — REUSE):
```typescript
export function cn(...classes: ClassValue[]): string  // clsx + tailwind-merge
```

From frontend/src/components/PersonaCard.tsx — persona display name lookup pattern (re-derive locally OR factor; see DissentPanel action below):
```typescript
// Canonical persona slate (from Phase 5 LLM_PERSONAS lock):
const PERSONA_LABEL = {
  buffett: 'Warren Buffett',
  munger: 'Charlie Munger',
  wood: 'Cathie Wood',
  burry: 'Michael Burry',
  lynch: 'Peter Lynch',
  claude_analyst: 'Open Claude Analyst',
}
```

Notion-Clean palette tokens (Phase 6 lock, available in Tailwind via @theme):
- bg-bullish, text-bullish, border-bullish (green)
- bg-bearish, text-bearish, border-bearish (red)
- bg-amber, text-amber, border-amber (warning)
- bg-fg-muted, text-fg-muted, border-fg-muted (muted)
- bg-accent, text-accent, border-accent (Open Claude / accent-tinted)
- bg-bg, bg-surface, border-border, text-fg
- Slash modifiers: /5, /10, /15, /30, /40, /50 etc. for opacity
</interfaces>

<color_x_weight_matrix>
<!-- LOCKED from CONTEXT.md — RecommendationBanner MUST follow this exact mapping -->

| recommendation | Color tokens                                      |
|----------------|---------------------------------------------------|
| add            | bg-bullish/10  text-bullish  border-bullish/30    |
| buy            | bg-bullish/15  text-bullish  border-bullish/40    |
| hold           | bg-fg-muted/10 text-fg-muted border-fg-muted/30   |
| trim           | bg-amber/10    text-amber    border-amber/30      |
| take_profits   | bg-amber/15    text-amber    border-amber/40      |
| avoid          | bg-bearish/10  text-bearish  border-bearish/30    |

| conviction | Font / weight modifier                  | Dots filled |
|------------|-----------------------------------------|-------------|
| low        | text-2xl font-medium                    | 1           |
| medium     | text-3xl font-semibold                  | 2           |
| high       | text-4xl font-bold                      | 3           |

Action label map:
add → 'Add' · buy → 'Buy' · hold → 'Hold' · trim → 'Trim' · take_profits → 'Take Profits' · avoid → 'Avoid'
</color_x_weight_matrix>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: RecommendationBanner + ConvictionDots (RED → GREEN)</name>
  <files>
    frontend/src/components/RecommendationBanner.tsx,
    frontend/src/components/ConvictionDots.tsx,
    frontend/src/components/__tests__/RecommendationBanner.test.tsx,
    frontend/src/components/__tests__/ConvictionDots.test.tsx
  </files>
  <behavior>
    ConvictionDots:
    - Renders exactly 3 dot elements (data-testid="conviction-dot") regardless of `filled` prop
    - First N dots styled as filled (data-state="filled"); remaining (3-N) styled as empty (data-state="empty")
    - filled=1 (low) → 1 filled + 2 empty; filled=2 (medium) → 2 filled + 1 empty; filled=3 (high) → 3 filled + 0 empty
    - Container has data-testid="conviction-dots" and data-filled={filled}
    - Pitfall #6 guard: NEVER use Array.from({ length: filled }) — always Array.from({ length: 3 })

    RecommendationBanner:
    - Props: { recommendation: DecisionRecommendation, conviction: ConvictionBand }
    - Renders <div role="status" data-testid="recommendation-banner" data-recommendation={recommendation} data-conviction={conviction} aria-label={...}>
    - Action color tokens applied via cn() per color×weight matrix above (add → bg-bullish/10 text-bullish border-bullish/30, etc. — all 6 actions)
    - Conviction font tokens applied per matrix (low → text-2xl font-medium, medium → text-3xl font-semibold, high → text-4xl font-bold)
    - Action label rendered with font-mono class (matches deep-dive ticker heading typography)
    - ConvictionDots embedded on right side: filled = (conviction === 'low' ? 1 : conviction === 'medium' ? 2 : 3)
    - Conviction word displayed as caption: '{conviction} conviction' in font-mono text-xs uppercase tracking-wider opacity-70
    - aria-label format: 'Recommendation: {Action Label}, conviction {conviction}' (e.g., 'Recommendation: Take Profits, conviction high')

    Test surface (vitest + RTL):
    - ConvictionDots: 3 tests (low/medium/high) — each asserts data-filled, exactly 3 dot children, correct count of data-state="filled"
    - RecommendationBanner: 19 tests
      * 18 matrix tests via nested for-loops over ACTIONS × CONVICTIONS — assert data-recommendation, data-conviction, presence of expected color token in className, presence of expected font token in className
      * 1 a11y test: role="status" present + aria-label contains action label and conviction
  </behavior>
  <action>
    RED step:
    1. Create `frontend/src/components/__tests__/ConvictionDots.test.tsx` with 3 failing tests covering low/medium/high. Run `cd frontend && pnpm test:unit src/components/__tests__/ConvictionDots.test.tsx --run` — MUST fail (component doesn't exist).
    2. Create `frontend/src/components/__tests__/RecommendationBanner.test.tsx` with the 6×3 matrix loop + a11y test (~19 tests). Use ACTIONS = ['add','buy','hold','trim','take_profits','avoid'] and CONVICTIONS = ['low','medium','high']. Run `cd frontend && pnpm test:unit src/components/__tests__/RecommendationBanner.test.tsx --run` — MUST fail.
    3. Commit RED: `test(07-01): add failing tests for RecommendationBanner + ConvictionDots`

    GREEN step:
    4. Create `frontend/src/components/ConvictionDots.tsx` (~30 LOC). Header comment: `// ConvictionDots — 3-dot indicator (1/2/3 filled for low/medium/high). Always renders 3 dots; never fewer. Pitfall #6 guard: Array.from({ length: 3 }), never length: filled.`
       Use Array.from({ length: 3 }, (_, i) => i < filled ? 'filled' : 'empty'). Filled dot: `bg-fg` rounded-full w-2 h-2; empty dot: `border border-fg-muted` rounded-full w-2 h-2. Container: `flex items-center gap-1.5`.
    5. Create `frontend/src/components/RecommendationBanner.tsx` (~100 LOC). Header comment: `// RecommendationBanner — hero element of /decision/:symbol/:date?. Action drives color (Notion-Clean palette tokens); conviction drives visual weight (font + ConvictionDots). 6 actions × 3 convictions = 18 visual states. Independent from ActionHintBadge (Pitfall #4 — different schema field, different enum).`
       Define ACTION_COLOR, CONVICTION_FONT, ACTION_LABEL Records over the locked Literal types (compile-time exhaustiveness via Record<DecisionRecommendation, string>). Layout: `flex items-center justify-between gap-6 rounded-md border px-6 py-5` + ACTION_COLOR[recommendation]. Inner action label uses `font-mono` + CONVICTION_FONT[conviction]. ConvictionDots + caption on the right.
    6. Run `cd frontend && pnpm test:unit src/components/__tests__/ConvictionDots.test.tsx src/components/__tests__/RecommendationBanner.test.tsx --run` — MUST pass (22 tests green).
    7. Run `cd frontend && pnpm typecheck` — MUST pass.
    8. Commit GREEN: `feat(07-01): implement RecommendationBanner + ConvictionDots`

    DO NOT:
    - Import or extend ActionHintBadge (Pitfall #4 — different 4-state enum)
    - Add new theme tokens (Phase 6 palette is locked; reuse bullish/amber/bearish/fg-muted)
    - Use inline hex colors (Notion-Clean discipline — every color from CSS variables via Tailwind)
    - Render fewer than 3 dots when filled<3 (Pitfall #6 — layout shift)
  </action>
  <verify>
    <automated>cd frontend && pnpm test:unit src/components/__tests__/RecommendationBanner.test.tsx src/components/__tests__/ConvictionDots.test.tsx --run</automated>
  </verify>
  <done>
    All 22 tests green (3 ConvictionDots + 19 RecommendationBanner). `pnpm typecheck` clean. Two commits on disk: one RED test commit, one GREEN impl commit. Components exported and importable from `@/components/RecommendationBanner` and `@/components/ConvictionDots`.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: DriversList + DissentPanel (RED → GREEN)</name>
  <files>
    frontend/src/components/DriversList.tsx,
    frontend/src/components/DissentPanel.tsx,
    frontend/src/components/__tests__/DriversList.test.tsx,
    frontend/src/components/__tests__/DissentPanel.test.tsx
  </files>
  <behavior>
    DriversList:
    - Props: { shortTerm: TimeframeBand, longTerm: TimeframeBand }
    - Renders two cards in `<div className="flex flex-col gap-6 lg:flex-row" data-testid="drivers-list">` (mirrors TimeframeCard pair pattern from TickerRoute.tsx line 142)
    - Each card: data-testid="drivers-card" + data-timeframe={"short_term"|"long_term"}; flex-1 border-border bg-surface text-fg shadow-none rounded-md p-6
    - Card header: small font-mono uppercase tracking-wider text-fg-muted label ("Short-term drivers" / "Long-term drivers") + confidence pill (`conf {N}`) on the right + thesis_status badge (reuse the STATUS_COLOR map from TimeframeCard; small inline lookup is acceptable)
    - Card body: `<ul className="ml-4 list-disc space-y-1 text-sm text-fg-muted">` of `<li className="font-mono">{driver}</li>` for each driver
    - EMPTY-STATE LOCK (CONTEXT.md UNIFORM RULE): when drivers.length === 0, render `<p data-testid="drivers-empty" className="text-sm text-fg-muted italic">No drivers surfaced</p>` INSIDE the card (NEVER collapse the card; slot is always present, like OpenClaudePin)

    DissentPanel:
    - Props: { dissent: DissentSection }
    - ALWAYS renders (Pitfall #12) — no early-return null branch
    - Container always has data-testid="dissent-panel" and data-has-dissent={String(has_dissent)}
    - has_dissent: false branch:
      * className: 'rounded-md border border-border/30 bg-surface/50 px-6 py-4 text-fg-muted'
      * Header: <span className="font-mono text-xs uppercase tracking-wider">Dissent</span>
      * Body: <p className="mt-2 text-sm">All personas converged. No dissent surfaced.</p>
    - has_dissent: true branch:
      * Compute isClaude = (dissenting_persona === 'claude_analyst')
      * className when isClaude: 'rounded-md border border-accent/40 bg-accent/5 px-6 py-4 text-fg' (matches OpenClaudePin)
      * className when !isClaude: 'rounded-md border border-amber/30 bg-amber/10 px-6 py-4 text-fg'
      * data-dissenter={dissenting_persona ?? ''}
      * Header row: left = font-mono text-xs uppercase tracking-wider, text = isClaude ? 'Open Claude Dissent' : '{Persona Label} Dissents'; right = font-mono text-xs text-fg-muted persona label (or 'Unknown persona' when dissenting_persona is null)
      * Body: <p className="mt-2 text-sm leading-relaxed">{dissent_summary}</p>
      * If dissent_summary is empty string, render <p data-testid="dissent-summary-missing" className="mt-2 text-sm italic text-fg-muted">No summary provided.</p> instead
    - PERSONA_LABEL lookup is a local const at module top (do NOT factor to a shared file in this plan — single-use is fine; if a future plan needs it, refactor then)

    Test surface:
    - DriversList: 4 tests
      * short populated + long populated → both cards have <li> children, no drivers-empty
      * short empty + long populated → short card has drivers-empty, long card has <li> children
      * short populated + long empty → mirror
      * both empty → both cards have drivers-empty (cards still rendered — NOT collapsed)
    - DissentPanel: 6 tests
      * has_dissent: false → muted text, "All personas converged", data-has-dissent="false"
      * has_dissent: true + dissenting_persona='burry' → amber styling (border-amber/30), "Michael Burry" label, dissent_summary visible, data-dissenter="burry"
      * has_dissent: true + dissenting_persona='claude_analyst' → accent styling (border-accent/40), "Open Claude Dissent" header text, "Open Claude Analyst" label, data-dissenter="claude_analyst" (Pitfall #2 guard)
      * has_dissent: true + dissenting_persona=null → 'Unknown persona' label, amber styling
      * has_dissent: true + dissent_summary='' → renders dissent-summary-missing fallback
      * has_dissent: false → STILL renders panel (queryByTestId NOT toBeNull) — Pitfall #12 explicit guard
  </behavior>
  <action>
    RED step:
    1. Create `frontend/src/components/__tests__/DriversList.test.tsx` with 4 failing tests. Use a `makeBand(drivers: string[], confidence=70, thesis='intact')` factory. Run `cd frontend && pnpm test:unit src/components/__tests__/DriversList.test.tsx --run` — MUST fail.
    2. Create `frontend/src/components/__tests__/DissentPanel.test.tsx` with 6 failing tests. Use a `makeDissent(overrides)` factory. The Pitfall #12 test MUST be phrased as `expect(screen.getByTestId('dissent-panel')).toBeInTheDocument()` — explicitly assert the panel IS rendered when has_dissent=false (NOT toBeNull). Run `cd frontend && pnpm test:unit src/components/__tests__/DissentPanel.test.tsx --run` — MUST fail.
    3. Commit RED: `test(07-01): add failing tests for DriversList + DissentPanel`

    GREEN step:
    4. Create `frontend/src/components/DriversList.tsx` (~80 LOC). Header comment: `// DriversList — short_term + long_term drivers as a two-card pair (lg:flex-row). Empty drivers render 'No drivers surfaced' INSIDE the card; UNIFORM RULE — never silently absent / never collapsed. Pattern adapted from TickerRoute.tsx line 142 TimeframeCard pair layout.`
       Define a small thesis-status STATUS_COLOR map locally (or import the one from TimeframeCard if exported; prefer local — single use, avoids cross-coupling). Render two `<DriverCard>` (inner component or inline) — one per timeframe.
    5. Create `frontend/src/components/DissentPanel.tsx` (~120 LOC). Header comment: `// DissentPanel — ALWAYS rendered (Pitfall #12 confirmation-bias guard). has_dissent: false renders muted "All personas converged" panel; has_dissent: true renders bordered panel with dissenting persona + summary. Special case: dissenting_persona === 'claude_analyst' uses accent-tinted treatment (matches OpenClaudePin) — Open Claude is distinct from the 5 canonical personas (user MEMORY.md lock + Pitfall #2 guard).`
       Local PERSONA_LABEL const. Compute isClaude. Branch on has_dissent.
    6. Run `cd frontend && pnpm test:unit src/components/__tests__/DriversList.test.tsx src/components/__tests__/DissentPanel.test.tsx --run` — MUST pass (10 tests green).
    7. Run `cd frontend && pnpm typecheck` — MUST pass.
    8. Commit GREEN: `feat(07-01): implement DriversList + DissentPanel`

    DO NOT:
    - Reuse TimeframeCard wholesale (CONTEXT.md anti-pattern — TimeframeCard renders summary+status+confidence+drivers; DriversList renders ONLY drivers, since the recommendation IS the summary)
    - Implement DissentPanel as `if (!has_dissent) return null` (Pitfall #12)
    - Treat claude_analyst identically to other personas (Pitfall #2 — must use accent-tinted treatment + 'Open Claude Dissent' header text)
    - Collapse the card when drivers.length === 0 (UNIFORM RULE — slot must be present)
  </action>
  <verify>
    <automated>cd frontend && pnpm test:unit src/components/__tests__/DriversList.test.tsx src/components/__tests__/DissentPanel.test.tsx --run</automated>
  </verify>
  <done>
    All 10 tests green (4 DriversList + 6 DissentPanel). `pnpm typecheck` clean. Two commits on disk (RED + GREEN). DissentPanel always renders regardless of has_dissent (Pitfall #12 explicit guard test passes). claude_analyst path uses border-accent/40 distinct from amber/30 generic dissent.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: DecisionRoute + cross-links + E2E</name>
  <files>
    frontend/src/routes/DecisionRoute.tsx,
    frontend/src/routes/__tests__/DecisionRoute.test.tsx,
    frontend/src/routes/TickerRoute.tsx,
    frontend/src/routes/Root.tsx,
    frontend/src/App.tsx,
    frontend/tests/fixtures/scan/MSFT-no-dissent.json,
    frontend/tests/e2e/decision.spec.ts,
    frontend/tests/e2e/fixtures-server.ts
  </files>
  <behavior>
    DecisionRoute (frontend/src/routes/DecisionRoute.tsx):
    - Mounts at /decision/:symbol/:date? (third route in App.tsx)
    - Pattern: mirror TickerRoute.tsx loading + typed-error branches verbatim (FetchNotFoundError → "{symbol} not in snapshot for {date}"; SchemaMismatchError → "Schema upgrade required"; generic Error → bearish-tinted error block)
    - Composition order:
      1. Heading row: <h1 className="font-mono text-3xl font-semibold tracking-tight" data-testid="decision-heading">{snap.ticker}</h1> + Link "← Deep dive" to /ticker/{symbol}/{date} (text-sm text-fg-muted hover:text-accent, data-testid="back-to-deep-dive-link")
      2. data_unavailable notice (only when dec.data_unavailable === true): muted "⚠ Data unavailable for some signals — recommendation may be partial" — `rounded-md border border-fg-muted/30 bg-surface px-4 py-3 text-sm text-fg-muted` + data-testid="data-unavailable-notice"
      3. <RecommendationBanner recommendation={dec.recommendation} conviction={dec.conviction} />
      4. PHASE-8-HOOK placeholder block (LOAD-BEARING — Phase 8 grep target):
         ```tsx
         {/* PHASE-8-HOOK: current-price-delta — Phase 8 (api/refresh.py) replaces this
             placeholder with <CurrentPriceDelta /> fed by useRefreshData(symbol). The
             data-testid below is the deterministic search target for Phase 8's planner. */}
         <div
           data-testid="current-price-placeholder"
           className="rounded-md border border-dashed border-border bg-surface px-4 py-3 text-sm text-fg-muted"
         >
           Snapshot price as of {new Date(dec.computed_at).toLocaleString()} ET.{' '}
           <span className="italic">Current-price delta arrives via mid-day refresh in Phase 8.</span>
         </div>
         ```
         BOTH the source comment containing "PHASE-8-HOOK: current-price-delta" AND the data-testid="current-price-placeholder" attribute MUST be present. These are the deterministic markers Phase 8's plan-phase will grep for.
      5. <DriversList shortTerm={dec.short_term} longTerm={dec.long_term} />
      6. <Separator />
      7. <DissentPanel dissent={dec.dissent} />
      8. open_observation block (only when dec.open_observation truthy): accent-tinted (border-accent/40 bg-accent/5) — same treatment as DissentPanel claude_analyst case + data-testid="open-observation"
    - Lite-mode handling: when ticker_decision === null, render an amber notice "No recommendation for {symbol} on {date}" with explanation "ticker_decision is null — likely lite-mode run. Re-run today's routine to populate the recommendation." — same shape as TickerRoute null-decision handling
    - Section wrapper: <section className="flex flex-col gap-8 pb-12" data-testid="decision-route">
    - Provenance comment at top of file: `// Pattern adapted from TickerRoute.tsx — same loading/typed-error branches, different content focus (recommendation-first, not analysis-first).`

    TickerRoute extension (frontend/src/routes/TickerRoute.tsx):
    - Add cross-link to existing heading row (line ~121-135), AFTER the existing "← Back to scan" link OR as a sibling group on the right side. Use existing wrap-friendly layout (`<div className="flex flex-wrap items-baseline justify-between gap-4">` already present).
    - New element: `<Link to={`/decision/${symbol}/${date}`} className="text-sm text-fg-muted hover:text-accent" data-testid="to-decision-link">→ Decision view</Link>`
    - Group it with the existing "← Back to scan" Link in a small flex container OR add it as a separate flex child — preserve the wrap/spacing aesthetic.

    Root.tsx audit (frontend/src/routes/Root.tsx):
    - useActiveDate already iterates useMatches() and returns any matched route's :date param — /decision/:symbol/:date? params will be picked up automatically since react-router populates m.params.date for ALL matches. NO regex change needed.
    - Update the comment block (line ~16-24) to mention the third route: "Active date detection: useMatches scans the matched route hierarchy and pulls the :date param from /scan/:date or /ticker/:symbol/:date? or /decision/:symbol/:date?."
    - VERIFY no code change is needed — the implementation is already route-shape-agnostic.

    App.tsx extension (frontend/src/App.tsx):
    - Import: `import DecisionRoute from './routes/DecisionRoute'`
    - Add third child route (after ticker route): `{ path: 'decision/:symbol/:date?', element: <DecisionRoute /> }`
    - Update the header comment to list the third route shape

    fixtures-server.ts extension (frontend/tests/e2e/fixtures-server.ts):
    - Read the existing file. Add MSFT-no-dissent.json to the fixture set if it currently maps tickers to fixture files. If the existing pattern is "intercept by ticker symbol", route MSFT.json hits to MSFT-no-dissent.json conditionally OR add a separate test path. Path of least resistance: add a new exported helper `mountScanFixturesNoDissent(page)` that swaps MSFT.json for MSFT-no-dissent.json. The Playwright spec uses this to test the no-dissent branch.

    MSFT-no-dissent.json (frontend/tests/fixtures/scan/MSFT-no-dissent.json):
    - Identical to MSFT.json EXCEPT the dissent block:
      ```json
      "dissent": {
        "has_dissent": false,
        "dissenting_persona": null,
        "dissent_summary": ""
      }
      ```
    - All other fields preserved verbatim (use MSFT.json as the source).

    DecisionRoute unit tests (frontend/src/routes/__tests__/DecisionRoute.test.tsx) — 5 tests:
    - Use vi.mock('@/lib/loadTickerData', () => ({ useTickerData: vi.fn() })) — the same approach existing route-test patterns expect (mirror the loading/error idioms)
    - Wrap renders in MemoryRouter with initialEntries={['/decision/AAPL/2026-05-04']}; route element is <DecisionRoute />
    - Test 1 — loading: useTickerData returns { data: undefined, isLoading: true, error: undefined } → assert "Loading" text or data-testid="decision-loading"
    - Test 2 — 404: useTickerData returns error: new FetchNotFoundError(...) → assert ticker-error data-testid + "not in snapshot" text
    - Test 3 — schema mismatch: error: new SchemaMismatchError(...) → assert "Schema upgrade required" text
    - Test 4 — happy has_dissent: true: AAPL fixture-shaped data → assert recommendation-banner + drivers-list + dissent-panel (data-has-dissent="true") + current-price-placeholder all present
    - Test 5 — data_unavailable: true (Hold/low + data_unavailable=true) → assert data-unavailable-notice present + recommendation-banner data-recommendation="hold" data-conviction="low"

    decision.spec.ts E2E (frontend/tests/e2e/decision.spec.ts) — 1 test (mirror deep-dive.spec.ts structure):
    - test.beforeEach: mountScanFixtures(page)
    - Test name: "decision view round-trip — /scan → /ticker → /decision → /ticker preserves date and renders banner + drivers + dissent"
    - Steps:
      1. Goto /scan/2026-05-04, click first PositionLens ticker (NVDA)
      2. Assert URL is /ticker/NVDA/2026-05-04
      3. Click [data-testid="to-decision-link"]
      4. Assert URL is /decision/NVDA/2026-05-04
      5. Assert getByTestId('recommendation-banner').toBeVisible() with data-recommendation attr matching expected NVDA value (take_profits)
      6. Assert getByTestId('drivers-list').toBeVisible() and locator('[data-testid="drivers-card"]').toHaveCount(2)
      7. Assert getByTestId('dissent-panel').toBeVisible() with data-has-dissent="true"
      8. Assert getByTestId('current-price-placeholder').toBeVisible()
      9. Click [data-testid="back-to-deep-dive-link"]
      10. Assert URL back to /ticker/NVDA/2026-05-04 (date preserved)
  </behavior>
  <action>
    Step 1 — fixture + harness:
    1. Read frontend/tests/fixtures/scan/MSFT.json. Create frontend/tests/fixtures/scan/MSFT-no-dissent.json — verbatim copy with the dissent block replaced as specified above.
    2. Read frontend/tests/e2e/fixtures-server.ts to understand the existing harness pattern. (No edit required IF the harness already serves all fixtures at fixed paths; otherwise add a small mountScanFixturesNoDissent helper. Document chosen approach in Task SUMMARY.)

    Step 2 — App + Root extensions (small):
    3. Edit frontend/src/App.tsx — import DecisionRoute, add third child route, update the route-shape comment.
    4. Edit frontend/src/routes/Root.tsx — update the useActiveDate comment to mention /decision/. Confirm no code change needed (the useMatches loop is already route-shape-agnostic).
    5. Edit frontend/src/routes/TickerRoute.tsx — add the "→ Decision view" Link in the existing heading row. Wrap the two links in a small flex container if needed for spacing.
    6. Run `cd frontend && pnpm typecheck` — MUST pass before continuing.

    Step 3 — DecisionRoute (RED → GREEN):
    7. Create frontend/src/routes/__tests__/DecisionRoute.test.tsx with all 5 failing tests using vi.mock('@/lib/loadTickerData', ...). Run `cd frontend && pnpm test:unit src/routes/__tests__/DecisionRoute.test.tsx --run` — MUST fail (DecisionRoute doesn't exist).
    8. Commit RED: `test(07-01): add failing tests for DecisionRoute`
    9. Create frontend/src/routes/DecisionRoute.tsx (~150 LOC) following the exact composition order in <behavior>. Include the PHASE-8-HOOK source comment AND the data-testid="current-price-placeholder" element (BOTH required — Phase 8 grep targets).
    10. Run `cd frontend && pnpm test:unit src/routes/__tests__/DecisionRoute.test.tsx --run` — MUST pass (5 tests green).
    11. Run `cd frontend && pnpm typecheck` — MUST pass.

    Step 4 — Full unit suite + E2E:
    12. Run `cd frontend && pnpm test:unit --run` — full vitest suite MUST be green (197 existing + 37 new = 234 expected).
    13. Create frontend/tests/e2e/decision.spec.ts with the 1 happy-path round-trip spec.
    14. Run `cd frontend && pnpm test:e2e --project=chromium-desktop -g 'decision'` — MUST pass.
    15. Commit GREEN: `feat(07-01): implement DecisionRoute + /decision/:symbol/:date? + cross-links + E2E (closes VIEW-10)`

    Step 5 — phase gate:
    16. Run `cd frontend && pnpm test:unit --run && pnpm typecheck && pnpm build` — full gate MUST pass.

    DO NOT:
    - Touch api/, add yfinance, or add any backend dependency (Pitfall #3 — current-price is Phase 8's surface)
    - Replace TickerRoute's "← Back to scan" link (existing flow remains)
    - Skip the PHASE-8-HOOK source comment (load-bearing — Phase 8's plan-phase greps for this exact string)
    - Write a custom error block in DecisionRoute (Pitfall #5 — mirror TickerRoute's typed-error branches verbatim)
    - Reuse TickerRoute's full composition (it's analysis-first; DecisionRoute is recommendation-first — overlap dilutes the banner's authority)
  </action>
  <verify>
    <automated>cd frontend && pnpm test:unit --run && pnpm test:e2e --project=chromium-desktop -g "decision" && pnpm typecheck</automated>
  </verify>
  <done>
    /decision/:symbol/:date? mounts; full vitest suite green (234 tests = 197 existing + 37 new); Playwright decision spec passes on chromium-desktop; typecheck clean. PHASE-8-HOOK source comment AND data-testid="current-price-placeholder" both present in DecisionRoute.tsx (verified by `grep -n "PHASE-8-HOOK" frontend/src/routes/DecisionRoute.tsx` AND `grep -n 'current-price-placeholder' frontend/src/routes/DecisionRoute.tsx`). Cross-links symmetric: TickerRoute → DecisionRoute and DecisionRoute → TickerRoute, :date preserved on round-trip. MSFT-no-dissent.json fixture exists with `"has_dissent": false`. Two commits on disk (RED test commit + GREEN impl + extensions commit).
  </done>
</task>

</tasks>

<verification>
Phase-level checks (run after Task 3 commits):

1. **Frontmatter requirement coverage:** This plan's `requirements: [VIEW-10]` matches the Phase 7 ROADMAP entry. No other plans exist in Phase 7.
2. **Goal-backward truths covered:** Every "must_haves.truths" entry is verified by at least one test or one structural assertion in the three tasks.
3. **Phase 8 hookpoint:** `grep -n "PHASE-8-HOOK: current-price-delta" frontend/src/routes/DecisionRoute.tsx` returns at least one match. `grep -n 'current-price-placeholder' frontend/src/routes/DecisionRoute.tsx` returns at least one match.
4. **Notion-Clean discipline:** `grep -nE "#[0-9a-fA-F]{3,8}" frontend/src/components/RecommendationBanner.tsx frontend/src/components/ConvictionDots.tsx frontend/src/components/DriversList.tsx frontend/src/components/DissentPanel.tsx frontend/src/routes/DecisionRoute.tsx` returns ZERO matches (no inline hex colors).
5. **Always-render dissent (Pitfall #12):** The DissentPanel test file contains an explicit `getByTestId('dissent-panel')` assertion with has_dissent=false (the failing pattern would be `queryByTestId(...)).toBeNull()`).
6. **Open Claude distinct (Pitfall #2):** DissentPanel test for dissenting_persona='claude_analyst' asserts className matches `/border-accent\/40/` AND header text matches `/Open Claude/`.
7. **Schema source-of-truth:** `grep -nE "z\.enum\(\[" frontend/src/components/{RecommendationBanner,ConvictionDots,DriversList,DissentPanel}.tsx frontend/src/routes/DecisionRoute.tsx` returns ZERO matches (no schema redefinition — types imported from `@/schemas`).
8. **Full frontend gate green:** `cd frontend && pnpm test:unit --run && pnpm test:e2e && pnpm typecheck && pnpm build` all green.
9. **Backend regression:** `pytest -q` still green (Phase 7 touches no Python; expect 659 still green).
</verification>

<success_criteria>
- [ ] /decision/:symbol/:date? route registered and reachable from TickerRoute via "→ Decision view" link
- [ ] /decision/:symbol/:date? → "← Deep dive" link returns to /ticker/:symbol/:date with date preserved (round-trip works)
- [ ] RecommendationBanner renders all 6 actions × 3 conviction = 18 visual states correctly (color from action; visual weight from conviction); 19 vitest tests green (18 matrix + 1 a11y)
- [ ] ConvictionDots renders exactly 3 dots in every state (1/2/3 filled for low/medium/high); 3 vitest tests green
- [ ] DriversList renders short_term + long_term cards side-by-side on lg; empty drivers show "No drivers surfaced" inside the card (NEVER collapsed); 4 vitest tests green
- [ ] DissentPanel ALWAYS renders (Pitfall #12); has_dissent: false shows "All personas converged. No dissent surfaced." muted; has_dissent: true shows persona + summary; claude_analyst case uses accent-tinted treatment (border-accent/40 bg-accent/5) matching OpenClaudePin; 6 vitest tests green
- [ ] DecisionRoute mirrors TickerRoute loading + typed-error branches verbatim; 5 vitest tests green covering loading / 404 / schema-mismatch / has_dissent-true / data_unavailable
- [ ] data_unavailable: true renders muted notice ABOVE banner; banner still shows Hold/low (per Phase 5 schema invariant)
- [ ] ticker_decision === null (lite-mode) renders explicit amber "No recommendation" notice
- [ ] Phase 8 hookpoint present: `// PHASE-8-HOOK: current-price-delta` source comment AND data-testid="current-price-placeholder" attribute both in DecisionRoute.tsx (verified by grep — see <verification> step 3)
- [ ] Notion-Clean palette discipline: zero inline hex colors in any new file (verified by grep — see <verification> step 4)
- [ ] Zero new runtime dependencies (no `pnpm add`); zero new theme tokens
- [ ] Playwright decision.spec.ts happy-path round-trip green on chromium-desktop
- [ ] Full frontend gate green: `pnpm test:unit --run && pnpm test:e2e && pnpm typecheck && pnpm build` all pass
- [ ] Six commits on disk (3 RED test commits + 3 GREEN impl commits per TDD task discipline)
- [ ] VIEW-10 marked Complete in REQUIREMENTS.md after closeout (handled by SUMMARY)
</success_criteria>

<output>
After completion, create `.planning/phases/07-decision-support-view-dissent-surface/07-01-SUMMARY.md` with:
- Files created (5 components/routes + 5 test files + 1 fixture + 1 E2E spec)
- Files modified (App.tsx, TickerRoute.tsx, Root.tsx comment update)
- Test counts: vitest +37 (197 → 234); Playwright +1 spec (chromium-desktop)
- Pattern reuse: TickerRoute composition + typed-error branches + OpenClaudePin accent palette
- Phase 8 hookpoint location confirmed (file:line for both PHASE-8-HOOK comment and data-testid)
- Six commit log (3 RED + 3 GREEN)
- VIEW-10 → Complete
</output>
