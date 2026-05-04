---
phase: 07-decision-support-view-dissent-surface
researched: 2026-05-03
domain: React frontend — recommendation banner + dissent panel + drivers list on existing Phase 6 infrastructure
confidence: HIGH
research_tier: normal
vault_status: empty
vault_reads: []
---

# Phase 7: Decision-Support View + Dissent Surface — Research

**Researched:** 2026-05-03
**Domain:** React frontend extension — single new route + 3 new components on Phase 6 stack
**Confidence:** HIGH

## Summary

Phase 7 is small. Single requirement (VIEW-10). Schema is done (Phase 5 produced `TickerDecision.recommendation`, `conviction`, `dissent`, dual `TimeframeBand`). Frontend infrastructure is done (Phase 6 shipped router, zod parse, Notion-Clean palette, ErrorBoundary, DateSelector, fetch boundary, 197 vitest + 60 Playwright). What remains is **routing + 3 components + 1 open question**.

The open question — current-price vs snapshot delta — has a clean answer: **defer to Phase 8**. Browser-side keyless price fetch is foreclosed (yfinance has no CORS; every CORS-enabled free API requires a key, violating the keyless constraint). Phase 8 already ships `api/refresh.py`. Phase 7 ships the snapshot price + a "current price arrives in Phase 8" affordance — momentum over half-baked overlap.

The remaining four areas (banner visual treatment, dissent always-render discipline, conviction band visualization, route integration) follow directly from Phase 6's locked Notion-Clean palette and existing badge components (`VerdictBadge`, `ActionHintBadge`). There's no new stack work and no new dependencies.

**Primary recommendation:** Build `RecommendationBanner` + `DriversList` + `DissentPanel` as three new components in `frontend/src/components/`, mount them at `/decision/:symbol/:date?` in App.tsx (third route), reuse the existing `useTickerData` hook unchanged, defer current-price-delta to Phase 8 with an explicit "current price arrives in Phase 8" placeholder. Total scope: ~600-800 LOC TS/TSX + ~300 LOC tests. One wave; one PR; ~15-20 new tests.

<user_constraints>
## User Constraints (from CONTEXT.md)

**No CONTEXT.md exists for Phase 7 yet.** This research feeds directly into `/gmd:discuss-phase` or `/gmd:plan-phase`. The constraints below are inherited from Phase 6's locks (the user has been clear these extend, not deviate):

### Locked Decisions (inherited from Phase 6)

- **Notion-Clean palette** — must extend, not deviate. Background `#0E0F11`; surface `#1F2024` + hairline border `#2A2C30`; accent `#5B9DFF`; bullish/bearish/amber state colors. No gradients, no glassmorphism, no animated backgrounds. Hairline borders over shadows.
- **Stack** — Vite 6 + React 19 + TS 5.9 + Tailwind v4 (CSS-first @theme tokens) + shadcn/ui (vendored Radix) + zod v4 + react-router v7 + TanStack Query v5. **Zero new runtime dependencies** for Phase 7.
- **Schema is locked** — `TickerDecisionSchema` already validates everything Phase 7 needs. `frontend/src/schemas/ticker_decision.ts` already exports the 6-state `DecisionRecommendation`, 3-state `ConvictionBand`, `DissentSection`, dual `TimeframeBand`. No schema work.
- **schema_version: 2** is the locked literal — no version bump.
- **UNIFORM RULE for empty/partial data** — `data_unavailable: true` invariant forces `recommendation='hold'` + `conviction='low'`; missing snapshots render explicit error states via Phase 6's `ErrorBoundary` + inline route handlers; `SchemaMismatchError` and `FetchNotFoundError` typed errors already plumbed.
- **Single Open Claude Analyst** — `claude_analyst` is rendered separately, never mixed with the 5 personas. This applies to Phase 7's dissent panel: if `dissenting_persona === 'claude_analyst'`, surface that distinctly (accent-tinted border like `OpenClaudePin`).
- **Pitfall #12 confirmation-bias guard** — dissent section is ALWAYS rendered. When `has_dissent: false`, render an explicit "All personas agreed — no dissent surfaced" message. Never silently absent.

### Claude's Discretion

- **Banner visual treatment** — pill vs full-width banner vs left-rail accent stripe. Three options surfaced in Architecture Patterns; recommendation: full-width banner with action color + conviction visual weight modifier.
- **Conviction band visualization** — label + 3-dot indicator vs filled bar vs font-weight modifier. Recommendation: 3-dot indicator (low = 1 filled, medium = 2 filled, high = 3 filled) + conviction word in caption — readable at a glance, Notion-Clean restraint.
- **DriversList layout** — stacked-card vs two-column vs side-by-side responsive. Recommendation: side-by-side on lg, stacked on <lg (matches existing `TimeframeCard` pair pattern in `TickerRoute.tsx`).
- **Routing integration** — separate route at `/decision/:symbol/:date?` with cross-links to/from `/ticker/:symbol/:date?`. Recommendation: separate route per ROADMAP intent; add a Decision link in TickerRoute heading and a "Deep dive" link in DecisionRoute heading (symmetric).
- **Dissent panel "no dissent" treatment** — three patterns surfaced; recommendation: small muted panel with check-mark glyph + "All personas agreed" wording, same border style as the dissent-present panel (so the slot looks intentional, never empty).

### Deferred Ideas (OUT OF SCOPE)

- **Current-price-vs-snapshot delta** — DEFER TO PHASE 8. Browser keyless price fetch is foreclosed (CORS + keyless violation). Phase 8 ships `api/refresh.py` Vercel Python serverless that returns current price + post-snapshot headlines. Phase 7 ships `dec.computed_at` price + "current price arrives via mid-day refresh in Phase 8" placeholder. Phase 8 then adds a `<CurrentPriceDelta />` component that mounts on `useRefreshData(symbol)` (TanStack Query hook fired on route open) and replaces the placeholder in-place.
- **Endorsement display in decision view** — Phase 9 (ENDORSE-03 explicitly says "Decision-Support view shows recent endorsements"; Phase 7 leaves room but doesn't render the section).
- **Persona signal mini-bars** — TickerRoute already has the full PersonaCards grid; Phase 7 doesn't repeat them. Cross-link to /ticker/ instead.
- **Recommendation history / sparkline** — needs the memory log from Phase 8 (INFRA-06); not v1.
- **Conviction calibration explainer** — "why was conviction medium not high" is v1.x.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description (from REQUIREMENTS.md) | Research Support |
|----|------------------------------------|------------------|
| **VIEW-10** | Decision-Support view shows recommendation banner (action + conviction band), drivers list, dissent section, and snapshot vs current-price delta | Banner: § Architecture Pattern 1 (RecommendationBanner). Drivers: § Architecture Pattern 2 (DriversList; reuses TimeframeCard pair layout). Dissent: § Architecture Pattern 3 (DissentPanel always-rendered). Current-price delta: § Open Question #1 — Phase 8 deferral with explicit placeholder. |

ROADMAP success criteria mapped:

| Criterion | Component / Pattern |
|-----------|---------------------|
| 1. Recommendation banner action ∈ {add, trim, hold, take_profits, buy, avoid} + conviction ∈ {low, medium, high} | `RecommendationBanner` — schema-driven, both Literals already exported from `@/schemas` |
| 2. Drivers list rendered separately for short_term and long_term | `DriversList` — two stacked cards mirroring `TimeframeCard` pair (lg:flex-row) |
| 3. Dissent section always present when ≥1 persona disagrees by ≥30 confidence points | `DissentPanel` — branches on `dec.dissent.has_dissent`; renders "All personas agreed" when false (Pitfall #12 guard) |
| 4. Current-price-vs-snapshot delta visible | DEFERRED to Phase 8 — placeholder + cross-reference in Phase 7; full delta lands when `api/refresh.py` ships |
</phase_requirements>

## Standard Stack

### Core (no additions — all from Phase 6 lock)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react | ^19.0.0 | View layer | Phase 6 lock |
| react-router | ^7.0.0 | `/decision/:symbol/:date?` route | Phase 6 lock — same data-router pattern, third route added to `App.tsx` children |
| @tanstack/react-query | ^5.59.0 | `useTickerData(date, symbol)` hook reuse — same query key shape | Phase 6 lock |
| zod | ^4.0.0 | `TickerDecisionSchema.parse` (already plumbed via `fetchAndParse`) | Phase 6 lock |
| tailwindcss | ^4.0.0 | Notion-Clean palette tokens (`bg-bullish/10`, `bg-amber/10`, `bg-bearish/10`, `bg-fg-muted/10`, `border-accent/40`, etc.) | Phase 6 lock |
| shadcn/ui (vendored) | latest | Existing `Card`, `Badge`, `Separator` primitives in `src/components/ui/` | Phase 6 lock |
| clsx + tailwind-merge | ^2.1.0 / ^2.5.0 | `cn()` helper at `@/lib/utils.ts` | Phase 6 lock |

### Supporting (test surface)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| vitest | ^2.1.0 | Component + schema tests | All component tests — `RecommendationBanner.test.tsx`, `DriversList.test.tsx`, `DissentPanel.test.tsx`, `DecisionRoute.test.tsx` |
| @testing-library/react | ^16.0.0 | RTL semantic queries | All component tests — assert by `data-testid`, `getByText`, `getByRole` |
| @playwright/test | ^1.48.0 | Happy-path E2E for new route | One spec at `tests/e2e/decision.spec.ts` — mounts existing AAPL.json fixture, navigates to `/decision/AAPL/2026-05-04`, asserts banner + drivers + dissent visible |

### Alternatives Considered (and rejected)

| Instead of | Could Use | Tradeoff | Why Rejected |
|------------|-----------|----------|-------------|
| Defer current-price delta to Phase 8 | Ship a free CORS proxy (Stooq, finnhub.io free tier) | Could land VIEW-10 SC#4 in Phase 7 | Stooq has no documented CORS allow-list (intermittent 403); finnhub free tier requires API key (violates keyless lock); Phase 8 already owns `api/refresh.py` — overlap is wasteful; momentum > completeness for this small phase |
| Defer current-price to Phase 8 | Ship Vercel `api/price.py` early in Phase 7 | Phase 7 closes VIEW-10 fully | Duplicates Phase 8's REFRESH-01..04 surface; introduces serverless infrastructure mid-stream of a frontend-only phase; complicates Phase 8 plan-phase ("we already have api/price.py — refactor or extend?") |
| New `RecommendationBanner` component | Reuse `ActionHintBadge` + extend it | One less file | `ActionHintBadge` is for `PositionSignal.action_hint` (4-state: consider_add/hold_position/consider_trim/consider_take_profits); `RecommendationBanner` is for `TickerDecision.recommendation` (6-state: add/trim/hold/take_profits/buy/avoid) — different enum, different visual weight (banner is hero element, badge is inline); reuse confuses both contracts |
| Inline upgrade to TickerRoute | Single route handles both | One less route | ROADMAP explicitly defines Phase 7 as a route; user MEMORY.md flags "morning command center" three pillars — Decision-Support is its own pillar |

**No `pnpm add` or `pnpm install` needed.** Phase 7 is purely additive on the locked stack.

## Architecture Patterns

### Recommended Project Structure

```
frontend/src/
├── components/
│   ├── RecommendationBanner.tsx    # NEW — hero banner; action color + conviction weight
│   ├── DriversList.tsx             # NEW — pair of timeframe driver cards (short_term + long_term)
│   ├── DissentPanel.tsx            # NEW — always-rendered; branches on has_dissent
│   ├── ConvictionDots.tsx          # NEW (small) — 3-dot conviction indicator
│   └── __tests__/
│       ├── RecommendationBanner.test.tsx   # 18 tests: 6 actions × 3 convictions = 18
│       ├── DriversList.test.tsx            # 4 tests: empty / short-only / long-only / both
│       ├── DissentPanel.test.tsx           # 6 tests: has_dissent both states + claude_analyst path + persona-name lookup
│       └── ConvictionDots.test.tsx         # 3 tests: low/medium/high
├── routes/
│   └── DecisionRoute.tsx           # NEW — /decision/:symbol/:date? composition
├── App.tsx                         # MODIFIED — add 3rd route to children array
├── routes/Root.tsx                 # MODIFIED — extend useActiveDate to also match /decision/:symbol/:date
└── routes/TickerRoute.tsx          # MODIFIED (small) — add "Decision view" cross-link in heading
tests/e2e/
└── decision.spec.ts                # NEW — happy-path Playwright spec
```

**File size estimates:**

- `RecommendationBanner.tsx`: ~120 LOC (6×3 = 18 visual states matrix + a11y `role="status"` + dataset attrs for E2E)
- `DriversList.tsx`: ~80 LOC (two `Card` children with shared layout)
- `DissentPanel.tsx`: ~140 LOC (two render branches + persona name lookup table reused from PersonaCard.tsx + claude_analyst-distinct treatment)
- `ConvictionDots.tsx`: ~50 LOC (pure render, three dots, accent fill count)
- `DecisionRoute.tsx`: ~180 LOC (composition + loading/error branches mirroring TickerRoute exactly)
- `App.tsx`: +10 LOC (third route entry)
- `Root.tsx`: +5 LOC (extend `useActiveDate` regex / match check)
- `TickerRoute.tsx`: +5 LOC (cross-link)
- Tests: ~400 LOC across 4 vitest files + ~80 LOC Playwright spec

**Total: ~860 LOC TS/TSX + ~480 LOC tests.** One wave is enough; the work is uniform-shape ("add component, render schema field, test").

### Pattern 1: RecommendationBanner — action color × conviction visual weight

**What:** Full-width banner at top of `DecisionRoute` rendering `dec.recommendation` + `dec.conviction`. Action drives color band; conviction drives visual emphasis (font weight + size of the action label).

**When to use:** Hero element of `/decision/:symbol/:date?`. Single instance per route.

**Color mapping (Notion-Clean palette tokens — same vocabulary as `VerdictBadge` / `ActionHintBadge`):**

| `recommendation` | Token combo | Stance |
|------------------|-------------|--------|
| `add` | `bg-bullish/10 text-bullish border-bullish/30` | bullish — buy more of an existing position |
| `buy` | `bg-bullish/15 text-bullish border-bullish/40` | bullish (slightly more saturated than add — initiating new vs sizing up) |
| `hold` | `bg-fg-muted/10 text-fg-muted border-fg-muted/30` | neutral |
| `trim` | `bg-amber/10 text-amber border-amber/30` | cautious — reduce exposure |
| `take_profits` | `bg-amber/15 text-amber border-amber/40` | cautious (slightly more saturated than trim — locked-in wins vs scaling down) |
| `avoid` | `bg-bearish/10 text-bearish border-bearish/30` | bearish |

**Conviction visual weight (font modifiers — Notion-Clean restraint):**

| `conviction` | Font treatment | Layout |
|--------------|---------------|--------|
| `low` | `text-2xl font-medium` | `<ConvictionDots filled=1 />` to right of action label |
| `medium` | `text-3xl font-semibold` | `<ConvictionDots filled=2 />` |
| `high` | `text-4xl font-bold` | `<ConvictionDots filled=3 />` |

**Example:**

```tsx
// frontend/src/components/RecommendationBanner.tsx
import type { DecisionRecommendation, ConvictionBand } from '@/schemas'
import { ConvictionDots } from './ConvictionDots'
import { cn } from '@/lib/utils'

const ACTION_COLOR: Record<DecisionRecommendation, string> = {
  add: 'bg-bullish/10 text-bullish border-bullish/30',
  buy: 'bg-bullish/15 text-bullish border-bullish/40',
  hold: 'bg-fg-muted/10 text-fg-muted border-fg-muted/30',
  trim: 'bg-amber/10 text-amber border-amber/30',
  take_profits: 'bg-amber/15 text-amber border-amber/40',
  avoid: 'bg-bearish/10 text-bearish border-bearish/30',
}

const CONVICTION_FONT: Record<ConvictionBand, string> = {
  low: 'text-2xl font-medium',
  medium: 'text-3xl font-semibold',
  high: 'text-4xl font-bold',
}

const ACTION_LABEL: Record<DecisionRecommendation, string> = {
  add: 'Add',
  buy: 'Buy',
  hold: 'Hold',
  trim: 'Trim',
  take_profits: 'Take Profits',
  avoid: 'Avoid',
}

export function RecommendationBanner({
  recommendation,
  conviction,
}: {
  recommendation: DecisionRecommendation
  conviction: ConvictionBand
}) {
  return (
    <div
      role="status"
      aria-label={`Recommendation: ${ACTION_LABEL[recommendation]}, conviction ${conviction}`}
      data-testid="recommendation-banner"
      data-recommendation={recommendation}
      data-conviction={conviction}
      className={cn(
        'flex items-center justify-between gap-6 rounded-md border px-6 py-5',
        ACTION_COLOR[recommendation],
      )}
    >
      <div className={cn('font-mono', CONVICTION_FONT[conviction])}>
        {ACTION_LABEL[recommendation]}
      </div>
      <div className="flex items-center gap-3">
        <ConvictionDots filled={conviction === 'low' ? 1 : conviction === 'medium' ? 2 : 3} />
        <span className="font-mono text-xs uppercase tracking-wider opacity-70">
          {conviction} conviction
        </span>
      </div>
    </div>
  )
}
```

Note the existing palette tokens (`bg-bullish`, `bg-amber`, `bg-bearish`, `bg-fg-muted`) and existing `cn()` import — zero new theme tokens.

### Pattern 2: DriversList — two-card pair (short_term + long_term)

**What:** Renders `dec.short_term.drivers` and `dec.long_term.drivers` as two stacked cards, side-by-side on lg, stacked on <lg.

**When to use:** Below the banner, above the dissent panel. Single instance.

**Reuse signal:** Phase 6's `TickerRoute.tsx` line 142 already has this exact pair-layout pattern (`<div className="flex flex-col gap-6 lg:flex-row">` wrapping two `<TimeframeCard>` instances). DriversList mirrors that idiom — drivers-only (no thesis_status badge — that lives in `TimeframeCard` already; the decision view is recommendation-focused, not thesis-status-focused). Empty drivers (lite-mode) renders a "no drivers — re-run today's routine" muted message inside the card so the slot stays present.

**Anti-pattern to avoid:** Reusing `TimeframeCard` itself. `TimeframeCard` shows `summary + thesis_status badge + confidence + drivers`; the decision view's drivers list shows just drivers + a small label header (the recommendation IS the summary). Reusing would over-render and dilute the banner's authority.

### Pattern 3: DissentPanel — always-rendered (Pitfall #12 guard)

**What:** Renders `dec.dissent` regardless of `has_dissent`. Two visual branches:

- `has_dissent: true` — bordered panel with `dissenting_persona` name (mapped to display label via existing `PERSONA_LABEL` table from `PersonaCard.tsx`) + `dissent_summary` text. If `dissenting_persona === 'claude_analyst'`, use accent-tinted treatment matching `OpenClaudePin` (`border-accent/40 bg-accent/5`) — the user MEMORY.md lock that Claude's reasoning is distinct from canonical personas extends here too.
- `has_dissent: false` — same panel shape (same border, same padding), muted treatment, "All personas agreed — no dissent surfaced this snapshot" wording, optional check-mark glyph (Unicode `✓` or lucide-react if already vendored — check `src/components/ui/`; likely `✓` keeps zero-deps).

**When to use:** Below the drivers list. Single instance.

**Pitfall #12 guard — why always-rendered matters:** A user opening the decision view who never sees a dissent panel ("oh, looks clean!") is being lulled by a UI that hides disagreement. The always-rendered panel forces the eye to "All personas agreed" — a meaningful, intentional statement that the user can trust as a real consensus signal rather than absence-of-evidence.

**Example:**

```tsx
// frontend/src/components/DissentPanel.tsx (sketch — full impl in plan)
import type { DissentSection } from '@/schemas'

const PERSONA_LABEL: Record<string, string> = {
  buffett: 'Warren Buffett',
  munger: 'Charlie Munger',
  wood: 'Cathie Wood',
  burry: 'Michael Burry',
  lynch: 'Peter Lynch',
  claude_analyst: 'Open Claude Analyst',
}

export function DissentPanel({ dissent }: { dissent: DissentSection }) {
  if (!dissent.has_dissent) {
    return (
      <div
        data-testid="dissent-panel"
        data-has-dissent="false"
        className="rounded-md border border-border bg-surface px-6 py-4 text-fg-muted"
      >
        <span className="font-mono text-xs uppercase tracking-wider">Dissent</span>
        <p className="mt-2 text-sm">
          ✓ All personas agreed — no dissent surfaced this snapshot.
        </p>
      </div>
    )
  }
  const isClaude = dissent.dissenting_persona === 'claude_analyst'
  const label = dissent.dissenting_persona
    ? PERSONA_LABEL[dissent.dissenting_persona] ?? dissent.dissenting_persona
    : 'Unknown persona'
  return (
    <div
      data-testid="dissent-panel"
      data-has-dissent="true"
      data-dissenter={dissent.dissenting_persona ?? ''}
      className={isClaude
        ? 'rounded-md border border-accent/40 bg-accent/5 px-6 py-4 text-fg'
        : 'rounded-md border border-amber/30 bg-amber/10 px-6 py-4 text-fg'
      }
    >
      <div className="flex items-center justify-between">
        <span className="font-mono text-xs uppercase tracking-wider">
          {isClaude ? 'Open Claude Dissent' : 'Dissent'}
        </span>
        <span className="font-mono text-xs text-fg-muted">{label}</span>
      </div>
      <p className="mt-2 text-sm leading-relaxed">{dissent.dissent_summary}</p>
    </div>
  )
}
```

### Pattern 4: ConvictionDots — 3-dot indicator

**What:** Three small circular dots; first N filled with current `text-fg` color, remaining (3-N) outlined with `text-fg-muted`. N=1 for low, N=2 for medium, N=3 for high.

**When to use:** Right side of the `RecommendationBanner`. Trivially small component.

**Why this pattern (vs filled bar / font-weight only):**
- **Filled progress bar:** misleads — conviction isn't a continuous percentage; it's three discrete states. A bar implies "73% conviction" which the schema doesn't carry.
- **Font-weight only:** too subtle on first glance — the user wants visual weight that signals "this is a high-conviction call" at a glance. Combining font-weight (already in banner via `CONVICTION_FONT`) AND dots gives belt-and-suspenders without over-decorating.
- **3 dots:** discrete, restrained, Notion-style (cf. Notion's "filled circle" for status chips), readable on mobile.

### Routing — `/decision/:symbol/:date?` integration

**Add to `App.tsx` children array (third route, after `ticker/:symbol/:date?`):**

```tsx
{
  path: 'decision/:symbol/:date?',
  element: <DecisionRoute />,
},
```

**Cross-link symmetry:**
- `TickerRoute` heading gets a "→ Decision view" link to `/decision/:symbol/:date`
- `DecisionRoute` heading gets a "← Deep dive" link back to `/ticker/:symbol/:date`
- `Root.tsx`'s `useActiveDate` already pulls `:date` from any matched route — extend the for-loop to also catch the new route's params; one-line change since `useMatches()` already iterates all matches.

**No new redirect / loader changes.** The existing `/` → `/scan/today` redirect remains the entry point.

### Anti-Patterns to Avoid

- **Polling for current price client-side:** Phase 6 has no current-price fetch and Phase 7 must NOT introduce one (CORS + keyless violations). Wait for Phase 8.
- **Treating `has_dissent: false` as "skip rendering":** Pitfall #12. Always render the panel.
- **Mixing `claude_analyst` into the persona-name lookup as if it were one of five:** the user MEMORY.md lock applies — Open Claude is distinct. The DissentPanel tests this distinct path.
- **Adding a Decision tab inside TickerRoute instead of a separate route:** ROADMAP defines Phase 7 as a route. Tab-inside-route would couple the two pillars and forfeit URL-shareability.
- **Re-fetching ticker JSON in DecisionRoute when `useTickerData` already cached it under `['ticker', date, symbol]` from a previous TickerRoute visit:** Use the same query key — TanStack Query de-dupes by reference equality. Cache hit is free.
- **Adding new theme tokens for "decision colors":** Phase 6 locked the tokens. Reuse `bullish`/`amber`/`bearish`/`fg-muted` exactly as `VerdictBadge` and `ActionHintBadge` do.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Action / conviction Literal types | New `decision.types.ts` | `DecisionRecommendation`, `ConvictionBand` from `@/schemas` | Already exported; importing keeps zod-source-of-truth |
| Persona display name lookup | Inline ad-hoc map | Same `PERSONA_LABEL` table from `PersonaCard.tsx` (factor to a small `personaLabels.ts` if you want to avoid duplication) | DRY; user MEMORY.md persona slate lock is invariant |
| Loading/error state branching | Custom Suspense boundary | Same pattern as `TickerRoute.tsx` (lines 49-99: `isLoading` → loading section; `error` → typed error branches via `isFetchNotFound` / `isSchemaMismatch` → inline error UI) | Established Phase 6 pattern; Wave 4 ErrorBoundary is the safety net but routes handle their own typed errors inline |
| Schema validation | Hand-rolled type guard | `useTickerData(date, symbol)` — already runs `SnapshotSchema.parse` via `fetchAndParse` | One fetch boundary; no parallel parse paths |
| 404 vs schema-mismatch typing | New error class | Existing `FetchNotFoundError` + `SchemaMismatchError` from `@/lib/fetchSnapshot` | Already plumbed across the app |
| Banner color tokens | New CSS classes | Tailwind `bg-bullish/10`, `border-amber/30`, etc. (Phase 6 `@theme` declarations) | Notion-Clean palette is the lock |
| Date param extraction | Custom hook | Existing `useActiveDate()` in `Root.tsx` (extend for /decision/ matching) | Single source of truth for active date |

**Key insight:** Phase 7 is the smallest possible delta on top of Phase 6. Every problem listed above is already solved in Phase 6 — Phase 7's discipline is to **import, not redefine**.

## Common Pitfalls

### Pitfall 1: Forgetting Pitfall #12 (Confirmation-bias guard)

**What goes wrong:** `DissentPanel` is implemented as `if (!has_dissent) return null`. The user sees the decision view, no dissent panel anywhere, gets a false sense of unanimous consensus.

**Why it happens:** The default React idiom is conditional rendering. "No data → no element" feels clean.

**How to avoid:** The component spec says `has_dissent: false → render explicit "All personas agreed" panel`. Test for both branches. The Playwright spec asserts `data-testid="dissent-panel"` is present on a fixture where `has_dissent: false` (use `MSFT.json` or generate one).

**Warning signs:** A vitest test like `expect(queryByTestId('dissent-panel')).toBeNull()` is the smell — flip it to `expect(getByTestId('dissent-panel')).toHaveAttribute('data-has-dissent', 'false')`.

### Pitfall 2: Mixing claude_analyst into the canonical persona slate

**What goes wrong:** `DissentPanel`'s persona lookup treats `claude_analyst` identically to `buffett`/`munger`/etc. — same border color, same panel treatment.

**Why it happens:** It's just one more entry in a Record<string, string>. Easy to flatten.

**How to avoid:** Branch `isClaude = dissenting_persona === 'claude_analyst'` and use accent-tinted treatment when true. Test the path explicitly with a fixture where `dissenting_persona === 'claude_analyst'`.

**Warning signs:** PR diff that adds `claude_analyst` to a "personas" array without also branching its visual treatment — flag it.

### Pitfall 3: Coupling to current-price-delta in Phase 7

**What goes wrong:** Plan adds an `api/price.py` Vercel function or imports a CORS proxy. Phase 8 then has to refactor or extend.

**Why it happens:** The ROADMAP success criterion #4 reads as "must ship in Phase 7". It does not — VIEW-10 is the requirement (which mentions current-price delta), but Phase 8's REFRESH-01..04 owns the implementation surface.

**How to avoid:** Phase 7 plan explicitly defers SC#4 with a placeholder UI and a Phase 8 reference. Phase 8 plan-phase research cross-references this and confirms `api/refresh.py` returns a payload that Phase 7's placeholder swap-in can consume.

**Warning signs:** Plan-phase 7 PR touches `api/`, adds `yfinance`, adds a CORS proxy URL constant, or adds any non-frontend dependency.

### Pitfall 4: Recommendation banner uses ActionHint colors (4-state) by mistake

**What goes wrong:** Developer reuses `ActionHintBadge`'s 4-state mapping (`consider_add`/`hold_position`/`consider_trim`/`consider_take_profits`) and then has to handle `buy` and `avoid` ad-hoc.

**Why it happens:** `ActionHintBadge` looks reusable. But it's for `PositionSignal.action_hint` (4-state) — different schema field, different enum.

**How to avoid:** `RecommendationBanner` uses `DecisionRecommendation` (6-state). Independent component, independent color map. Test all 6 actions × 3 convictions = 18 combinations.

**Warning signs:** Import of `ActionHint` or `ActionHintBadge` in `RecommendationBanner.tsx` — should not happen.

### Pitfall 5: Schema-version drift surfaces poorly

**What goes wrong:** A v1 snapshot is read; `TickerDecisionSchema.parse` throws; user sees an unhelpful error.

**Why it happens:** Same as Phase 6 — but Phase 7's developer might forget to wire the typed-error branch.

**How to avoid:** Mirror `TickerRoute.tsx` lines 65-99 verbatim — `isFetchNotFound` and `isSchemaMismatch` branches with the locked CONTEXT.md UNIFORM RULE wording. Don't re-invent the error UI.

**Warning signs:** `DecisionRoute.tsx` has a custom error block that doesn't use the typed error classes — flag it.

### Pitfall 6: ConvictionDots with `low` shows a single dot off-center

**What goes wrong:** Visual treatment puts one filled dot followed by no others, looking incomplete or like a render bug.

**Why it happens:** Naive implementation renders just `<div>•</div>` for low.

**How to avoid:** Always render 3 dots; first N styled as filled, rest as outlined. Same width regardless of conviction. Layout is locked.

**Warning signs:** `ConvictionDots` uses an array `Array.from({ length: filled })` instead of `Array.from({ length: 3 })` — flag it.

## Code Examples

### Example 1: Composing DecisionRoute (mirrors TickerRoute structure)

```tsx
// frontend/src/routes/DecisionRoute.tsx — sketch; the plan fills in the loading/error UI verbatim from TickerRoute
import { Link, useParams } from 'react-router'
import { useTickerData } from '@/lib/loadTickerData'
import { RecommendationBanner } from '@/components/RecommendationBanner'
import { DriversList } from '@/components/DriversList'
import { DissentPanel } from '@/components/DissentPanel'
import { Separator } from '@/components/ui/separator'
import { FetchNotFoundError, SchemaMismatchError } from '@/lib/fetchSnapshot'

export default function DecisionRoute() {
  const { symbol = '', date = 'today' } = useParams<{ symbol: string; date?: string }>()
  const { data: snap, isLoading, error } = useTickerData(date, symbol)

  if (isLoading) {
    /* same loading UI as TickerRoute */
  }
  if (error) {
    /* same typed-error branches as TickerRoute (FetchNotFoundError / SchemaMismatchError) */
  }
  if (!snap) return null

  const dec = snap.ticker_decision
  if (!dec) {
    return (
      <section className="space-y-6">
        <div className="rounded-md border border-amber/30 bg-amber/10 px-4 py-3 text-sm text-amber">
          <strong>No recommendation for {symbol} on {date}</strong>
          <div className="mt-1 text-fg-muted">
            ticker_decision is null — likely lite-mode run. Re-run today's routine to populate the recommendation.
          </div>
        </div>
      </section>
    )
  }

  return (
    <section className="flex flex-col gap-8 pb-12" data-testid="decision-route">
      {/* 1. Heading + cross-link */}
      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <h1 className="font-mono text-3xl font-semibold tracking-tight">{snap.ticker}</h1>
        <Link to={`/ticker/${symbol}/${date}`} className="text-sm text-fg-muted hover:text-accent">
          ← Deep dive
        </Link>
      </div>

      {/* 2. Recommendation banner */}
      <RecommendationBanner recommendation={dec.recommendation} conviction={dec.conviction} />

      {/* 3. Current-price delta — Phase 8 placeholder */}
      <div
        data-testid="current-price-placeholder"
        className="rounded-md border border-dashed border-border bg-surface px-4 py-3 text-sm text-fg-muted"
      >
        Snapshot price as of {new Date(dec.computed_at).toLocaleString()}.
        <span className="ml-2 italic">Current-price delta arrives via mid-day refresh in Phase 8.</span>
      </div>

      {/* 4. Drivers — short_term + long_term */}
      <DriversList shortTerm={dec.short_term} longTerm={dec.long_term} />

      <Separator />

      {/* 5. Dissent panel — always rendered */}
      <DissentPanel dissent={dec.dissent} />

      {/* 6. Open observation (claude_analyst voice — already in TickerDecision) */}
      {dec.open_observation && (
        <div className="rounded-md border border-accent/40 bg-accent/5 px-6 py-4 text-fg" data-testid="open-observation">
          <span className="font-mono text-xs uppercase tracking-wider text-accent">Open Claude Observation</span>
          <p className="mt-2 text-sm leading-relaxed">{dec.open_observation}</p>
        </div>
      )}
    </section>
  )
}
```

### Example 2: Mounting in App.tsx

```tsx
// frontend/src/App.tsx — third route added to children
import DecisionRoute from './routes/DecisionRoute'

export const router = createBrowserRouter([
  { path: '/', loader: () => redirect('/scan/today') },
  {
    path: '/',
    element: <Root />,
    children: [
      { path: 'scan/:date', element: <ScanRoute /> },
      { path: 'ticker/:symbol/:date?', element: <TickerRoute /> },
      { path: 'decision/:symbol/:date?', element: <DecisionRoute /> },  // NEW
    ],
  },
])
```

### Example 3: Test for all 18 banner states (vitest + RTL)

```tsx
// frontend/src/components/__tests__/RecommendationBanner.test.tsx
import { render, screen } from '@testing-library/react'
import { RecommendationBanner } from '../RecommendationBanner'
import type { DecisionRecommendation, ConvictionBand } from '@/schemas'

const ACTIONS: DecisionRecommendation[] = ['add', 'buy', 'hold', 'trim', 'take_profits', 'avoid']
const CONVICTIONS: ConvictionBand[] = ['low', 'medium', 'high']

describe('RecommendationBanner', () => {
  for (const action of ACTIONS) {
    for (const conviction of CONVICTIONS) {
      it(`renders ${action} × ${conviction}`, () => {
        render(<RecommendationBanner recommendation={action} conviction={conviction} />)
        const banner = screen.getByTestId('recommendation-banner')
        expect(banner).toHaveAttribute('data-recommendation', action)
        expect(banner).toHaveAttribute('data-conviction', conviction)
      })
    }
  }

  it('exposes role=status for accessibility', () => {
    render(<RecommendationBanner recommendation="add" conviction="high" />)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })
})
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Browser-side yfinance | Server-side proxy / serverless function | Yahoo tightened defenses 2022-2024 (no CORS headers, anti-scrape) | Phase 7's current-price delta CANNOT be a browser fetch — locks deferral to Phase 8 (`api/refresh.py`) |
| Conditional render of "empty" UI sections | Always-render with explicit empty-state copy | Industry shift to "intentional emptiness" (Linear, Notion, Vercel patterns) | DissentPanel always-rendered; reinforces Pitfall #12 guard |
| Pure font-weight conviction signaling | Discrete dot/pill indicators (Linear-style) | Notion-Clean Phase 6 lock | ConvictionDots component pattern |
| Inline tab-style sub-views | Distinct routes per pillar | URL-shareable / bookmarkable as table-stakes | `/decision/:symbol/:date?` is its own route, not a tab in TickerRoute |

**Deprecated / outdated:**

- **Browser-side yfinance scraping for current price:** documented as failing in 2025 due to CORS + Yahoo anti-scrape. Use a backend-mediated source (Phase 8 `api/refresh.py`) or accept snapshot price.
- **Free CORS-enabled APIs without API keys:** none exist that pass keyless lock + reliability. Don't research further; Phase 8 already owns this.

## Open Questions

### Question 1: Current-price source — RESOLVED, deferred to Phase 8

**What we know:**
- yfinance has no CORS headers (verified via 2025-2026 community discussion); browser fetch fails.
- Free CORS-enabled APIs (Alpha Vantage, Finnhub, Polygon) all require API keys, violating the keyless constraint.
- Stooq has occasional CORS support but is unreliable (intermittent 403s, no documented allow-list).
- Phase 8 explicitly owns `api/refresh.py` (REFRESH-01..04) — Vercel Python serverless that fetches current price via yfinance server-side and returns CORS-allowed JSON to the browser.

**What's unclear:** Nothing material. The "ship a stopgap CORS proxy in Phase 7" path is a worse engineering trade than waiting for Phase 8 (~1 phase distance, fully scoped).

**Recommendation:** **Option A (defer to Phase 8).** Phase 7 ships a `data-testid="current-price-placeholder"` element with the snapshot timestamp + an explicit "current-price delta arrives via mid-day refresh in Phase 8" message. Phase 8 swaps the placeholder for a `<CurrentPriceDelta />` component fed by a `useRefreshData(symbol)` TanStack Query hook. Plan-phase 7 should add a `// PHASE-8-HOOK` comment marker so Phase 8's grep finds it.

VALIDATION.md note: ROADMAP success criterion #4 ("Current-price-vs-snapshot delta visible — flags when intraday move materially affected the recommendation logic") is partially satisfied by Phase 7 (snapshot price + timestamp visible) and fully satisfied by Phase 8 (live delta + flagging logic). The phase boundary is acceptable per the project's ship-momentum discipline.

### Question 2: Should "Decision view" be the default, or remain a click-through from TickerRoute?

**What we know:** ROADMAP Phase 7 description says "Decision-Support route shows the per-ticker buy/trim/hold/take-profits recommendation". TickerRoute (Phase 6) already shows the recommendation inside `TimeframeCard.summary`.

**What's unclear:** Should opening a ticker land on `/decision/...` (recommendation-first) or `/ticker/...` (analysis-first)?

**Recommendation:** Keep `/ticker/...` as the click-through default from morning-scan (Phase 6 status quo). Add a "→ Decision view" link in `TickerRoute`'s heading to navigate to `/decision/...`. Reasoning: the morning command center's three pillars are co-equal; analysis-first is the locked Phase 6 behavior; users who want recommendation-first can bookmark `/decision/AAPL/today`. This avoids any Phase 6 regression and keeps Phase 7 purely additive.

### Question 3: Should Phase 7 surface `data_unavailable: true` decisions differently?

**What we know:** Schema invariant: `data_unavailable === true ⟹ recommendation === 'hold' AND conviction === 'low'`. So a `data_unavailable` decision will show "Hold" + "low conviction" in the banner. The summary text in `TimeframeBand.summary` will likely contain "data unavailable: <reason>".

**What's unclear:** Should the banner have a distinct fourth visual state for data_unavailable, or is "Hold + low conviction" + the summary text sufficient?

**Recommendation:** Render a small "⚠ Data unavailable for this snapshot" muted notice ABOVE the banner when `dec.data_unavailable === true`. Don't change the banner's color treatment (the schema invariant already drives `Hold` + `low` which IS the muted neutral treatment). Test path: a fixture with `data_unavailable: true` shows both the notice AND the `Hold/low` banner. ~10 LOC; closes the edge case cleanly.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (frontend) | vitest 2.1 + @testing-library/react 16 + @playwright/test 1.48 |
| Framework (backend) | pytest (unchanged — no Python work in Phase 7) |
| Frontend config | `frontend/vitest.config.ts`, `frontend/playwright.config.ts` (existing) |
| Quick run command | `cd frontend && pnpm test:unit --run` (vitest single-pass) |
| Per-component | `cd frontend && pnpm test:unit --run RecommendationBanner` (filter by file) |
| Full frontend suite | `cd frontend && pnpm test:unit --run && pnpm test:e2e` |
| Phase gate | full suite + `pnpm typecheck` + `pnpm build` green |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| VIEW-10 | Banner renders 6 actions × 3 convictions = 18 visual states with correct color + font weight | unit (vitest + RTL) | `pnpm test:unit --run RecommendationBanner` | ❌ Wave 0 |
| VIEW-10 | Drivers list renders short_term and long_term separately | unit (vitest + RTL) | `pnpm test:unit --run DriversList` | ❌ Wave 0 |
| VIEW-10 | Drivers list handles empty drivers (lite-mode) without breaking layout | unit (vitest + RTL) | `pnpm test:unit --run DriversList` | ❌ Wave 0 |
| VIEW-10 (Pitfall #12) | Dissent panel renders both has_dissent: true and has_dissent: false branches | unit (vitest + RTL) | `pnpm test:unit --run DissentPanel` | ❌ Wave 0 |
| VIEW-10 (MEMORY.md lock) | Dissent panel uses accent-tinted treatment when dissenting_persona === 'claude_analyst' | unit (vitest + RTL) | `pnpm test:unit --run DissentPanel` | ❌ Wave 0 |
| VIEW-10 | ConvictionDots: 1/2/3 dots filled for low/medium/high; total always 3 | unit (vitest + RTL) | `pnpm test:unit --run ConvictionDots` | ❌ Wave 0 |
| VIEW-10 | DecisionRoute mounts at /decision/:symbol/:date and renders banner + drivers + dissent for AAPL fixture | E2E (Playwright) | `pnpm test:e2e -g decision` | ❌ Wave 0 |
| VIEW-10 | DecisionRoute typed-error branches (FetchNotFoundError / SchemaMismatchError) render explicit UI | unit + E2E | `pnpm test:unit --run DecisionRoute` + `pnpm test:e2e -g decision` | ❌ Wave 0 |
| VIEW-10 | Cross-links: /ticker/ → /decision/ → /ticker/ navigation preserves :symbol + :date | E2E (Playwright) | `pnpm test:e2e -g decision` | ❌ Wave 0 |
| VIEW-10 (Phase 8 boundary) | Current-price placeholder is rendered with `data-testid="current-price-placeholder"` and references Phase 8 | unit (vitest + RTL) | `pnpm test:unit --run DecisionRoute` | ❌ Wave 0 |
| VIEW-10 (data_unavailable) | data_unavailable=true snapshot renders muted notice + Hold/low banner | unit (vitest + RTL) | `pnpm test:unit --run DecisionRoute` | ❌ Wave 0 |
| VIEW-10 (UNIFORM RULE) | ticker_decision === null (lite-mode) renders explicit "no recommendation" amber notice | unit (vitest + RTL) | `pnpm test:unit --run DecisionRoute` | ❌ Wave 0 |

**Manual-only verification:** None. Visual taste-check on Notion-Clean adherence is structurally verifiable (grep for forbidden patterns; verify mandatory tokens) per Phase 6 closeout precedent.

### Sampling Rate

- **Per task commit:** `pnpm test:unit --run` (whole vitest pass, ~3-5s) + `pnpm typecheck` (~2s)
- **Per wave merge:** `pnpm test:unit --run && pnpm test:e2e && pnpm typecheck && pnpm build`
- **Phase gate:** Full frontend suite green + `pytest -q` (regression — should be no Python touches; expect 659 still green)

### Wave 0 Gaps

- [ ] `frontend/src/components/RecommendationBanner.tsx` — covers VIEW-10 banner
- [ ] `frontend/src/components/DriversList.tsx` — covers VIEW-10 drivers
- [ ] `frontend/src/components/DissentPanel.tsx` — covers VIEW-10 dissent + Pitfall #12
- [ ] `frontend/src/components/ConvictionDots.tsx` — covers VIEW-10 conviction visual
- [ ] `frontend/src/routes/DecisionRoute.tsx` — covers VIEW-10 composition
- [ ] `frontend/src/components/__tests__/RecommendationBanner.test.tsx` — 18 + a11y = ~19 tests
- [ ] `frontend/src/components/__tests__/DriversList.test.tsx` — 4 tests
- [ ] `frontend/src/components/__tests__/DissentPanel.test.tsx` — 6 tests (true / false / claude / persona-name lookup / unknown-persona / empty-summary)
- [ ] `frontend/src/components/__tests__/ConvictionDots.test.tsx` — 3 tests (low/medium/high dot counts)
- [ ] `frontend/src/routes/__tests__/DecisionRoute.test.tsx` — 5 tests (loading / error / no-decision / data-unavailable / happy-path) — RTL with vi.mock loadTickerData
- [ ] `frontend/tests/e2e/decision.spec.ts` — 1 happy-path Playwright spec mounting AAPL fixture, navigating /scan → /ticker → /decision → /ticker, asserting banner + drivers + dissent + cross-link nav
- [ ] **Optional**: extend `frontend/tests/fixtures/scan/AAPL.json` with a `has_dissent: false` partner fixture (e.g. `MSFT.json` already exists — use it for the no-dissent E2E branch; no new fixture needed)

**Test framework install:** None. vitest + Playwright are already installed and green.

**Estimated test count delta:** +37 vitest tests (~19 banner + 4 drivers + 6 dissent + 3 conviction + 5 route) → 197 + 37 = 234 vitest. +1 Playwright spec → 22 → 23 specs (60 + 3 = 63 invocations across 3 projects, possibly +6 if the new spec adds mobile-only checks).

## Sources

### Primary (HIGH confidence)

- `synthesis/decision.py` (project codebase) — TickerDecision schema lock; 6-state DecisionRecommendation, 3-state ConvictionBand, DissentSection invariant
- `synthesis/dissent.py` (project codebase) — Python-computed dissent rule; LLM-07 contract surface
- `frontend/src/schemas/ticker_decision.ts` (project codebase) — zod mirror; already exports all needed types
- `frontend/src/routes/TickerRoute.tsx` (project codebase) — Phase 6 route composition pattern (loading / typed errors / sections)
- `frontend/src/components/PersonaCard.tsx`, `OpenClaudePin.tsx`, `TimeframeCard.tsx`, `VerdictBadge.tsx`, `ActionHintBadge.tsx` (project codebase) — palette + component patterns to mirror
- `.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-CONTEXT.md` (project) — Notion-Clean palette + Stack lock
- `.planning/phases/06-frontend-mvp-morning-scan-deep-dive/06-05-SUMMARY.md` (project) — Phase 6 final state; ErrorBoundary + DateSelector + responsive groundwork
- `.planning/REQUIREMENTS.md` VIEW-10 (project) — exact requirement text
- `.planning/ROADMAP.md` Phase 7 (project) — 4 success criteria

### Secondary (MEDIUM confidence)

- [Trading Dude — Why yfinance Keeps Getting Blocked, and What to Use Instead (2025)](https://medium.com/@trading.dude/why-yfinance-keeps-getting-blocked-and-what-to-use-instead-92d84bb2cc01) — confirms 2025-2026 yfinance blocking pattern; reinforces Phase 8 deferral logic
- [yahoo-finance2 npm package docs](https://www.npmjs.com/package/yahoo-finance2) — explicitly states "It's not possible to run Yahoo Finance libraries in the browser due to CORS and cookie issues" — locks Open Question #1 resolution

### Tertiary (LOW confidence — none load-bearing)

- General Notion-Clean pattern observations (Linear status pills, Vercel dashboard restraint) — referenced for design language, not for any specific claim. Phase 6 already locked the palette, so these are background context only.

## Metadata

**Confidence breakdown:**
- Stack reuse: HIGH — Phase 6 just shipped; tokens, hooks, error classes, route patterns all in-repo and tested.
- Schema availability: HIGH — `TickerDecisionSchema` already validates everything; verified by reading the schema file directly.
- Component patterns: HIGH — three direct precedents in `VerdictBadge`, `ActionHintBadge`, `OpenClaudePin`.
- Open Question #1 (current price): HIGH — both yfinance-CORS-blocked status AND keyless-constraint conflict are documented; deferral is sound.
- Open Question #2 (route default): HIGH — preserves Phase 6 behavior; user MEMORY.md three-pillars phrasing supports separation.
- Open Question #3 (data_unavailable): MEDIUM — recommendation is straightforward but optional; plan-phase can adopt or defer.

**Research date:** 2026-05-03
**Valid until:** 2026-06-03 (30 days for stable Phase 6 / Phase 7 boundary; longer if no Phase 6 changes)

**Vault status:** empty — no vault tooling configured in this environment; AGENT-04 obligation noted as fail-open per gmd-vault-retrieval contract.
