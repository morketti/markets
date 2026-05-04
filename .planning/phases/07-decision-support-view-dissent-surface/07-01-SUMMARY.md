---
phase: 07-decision-support-view-dissent-surface
plan: 01
subsystem: ui

tags: [react, react-router, vitest, playwright, decision-support, dissent, recommendation, notion-clean, phase-8-hookpoint]

# Dependency graph
requires:
  - phase: 05-claude-routine-wiring-persona-slate-synthesizer
    provides: TickerDecision schema + DissentSection + dual TimeframeBands + 6-state DecisionRecommendation Literal + 3-state ConvictionBand Literal
  - phase: 06-frontend-mvp-morning-scan-deep-dive
    provides: react-router data-router scaffold + zod-mirrored schemas + Notion-Clean palette tokens (bullish/amber/bearish/fg-muted/accent + opacity slash modifiers) + fetchSnapshot typed-error branches (FetchNotFoundError + SchemaMismatchError) + useTickerData TanStack Query hook + Playwright 3-project config + fixtures-server harness pattern + OpenClaudePin accent-tinted treatment
provides:
  - "Decision-Support View at /decision/:symbol/:date? — third pillar route alongside /scan/:date and /ticker/:symbol/:date?"
  - "RecommendationBanner — 6 actions × 3 conviction bands = 18-state hero element; action drives color, conviction drives visual weight"
  - "ConvictionDots — 3-dot indicator (always 3 total, never collapses) for low/medium/high conviction signal"
  - "DriversList — short_term + long_term card pair with empty-state UNIFORM RULE (slot always present, never collapsed)"
  - "DissentPanel — Pitfall #12 always-render guard; Pitfall #2 claude_analyst accent treatment distinct from 5 canonical personas"
  - "Cross-link symmetry: TickerRoute → DecisionRoute (→ Decision view) and DecisionRoute → TickerRoute (← Deep dive); date preserved on round-trip"
  - "Phase 8 hookpoint markers (PHASE-8-HOOK source comment + data-testid='current-price-placeholder') as deterministic grep targets for current-price-delta integration"
  - "MSFT-no-dissent.json fixture for has_dissent: false branch coverage"
affects: [phase-08-mid-day-refresh, phase-09-endorsement-capture]

# Tech tracking
tech-stack:
  added: []  # Zero new runtime dependencies; zero new theme tokens (PLAN frontmatter must_have honored)
  patterns:
    - "Color × weight matrix via Record<DecisionRecommendation, ...> + Record<ConvictionBand, ...> — compile-time exhaustiveness for visual states"
    - "Pitfall #12 always-render component pattern: shell with data-testid renders in BOTH branches (no `if (!flag) return null`); explicit muted state for the negative branch beats silent absence"
    - "Pitfall #2 special-case styling: dissenting_persona === 'claude_analyst' triggers accent-tinted treatment (border-accent/40 bg-accent/5) — visually distinct from canonical investor personas"
    - "Phase deferral hookpoint discipline: source comment + data-testid attribute as paired grep targets for downstream integration without coupling"
    - "TDD per-task atomic commits: RED (test only) commit + GREEN (impl) commit per Task — 6 production commits across 3 tasks"

key-files:
  created:
    - "frontend/src/components/RecommendationBanner.tsx (~100 LOC)"
    - "frontend/src/components/ConvictionDots.tsx (~45 LOC)"
    - "frontend/src/components/DriversList.tsx (~105 LOC)"
    - "frontend/src/components/DissentPanel.tsx (~115 LOC)"
    - "frontend/src/routes/DecisionRoute.tsx (~195 LOC)"
    - "frontend/src/components/__tests__/RecommendationBanner.test.tsx (19 tests)"
    - "frontend/src/components/__tests__/ConvictionDots.test.tsx (3 tests)"
    - "frontend/src/components/__tests__/DriversList.test.tsx (4 tests)"
    - "frontend/src/components/__tests__/DissentPanel.test.tsx (6 tests)"
    - "frontend/src/routes/__tests__/DecisionRoute.test.tsx (5 tests)"
    - "frontend/tests/e2e/decision.spec.ts (1 round-trip spec)"
    - "frontend/tests/fixtures/scan/MSFT-no-dissent.json (has_dissent: false fixture)"
  modified:
    - "frontend/src/App.tsx (+10 LOC — third route entry + 3-pillar comment update)"
    - "frontend/src/routes/TickerRoute.tsx (+11 LOC — '→ Decision view' Link in heading row, wrapped both links in flex container)"
    - "frontend/src/routes/Root.tsx (comment-only update — useActiveDate already route-shape-agnostic)"
    - "frontend/tests/e2e/fixtures-server.ts (+12 LOC — msftNoDissent option swap-in)"

key-decisions:
  - "Banner color × weight matrix locked: action drives color (bullish/amber/fg-muted/bearish + opacity modifier per matrix); conviction drives font weight + size (text-2xl/3xl/4xl + medium/semibold/bold). 18 visual states total; no overlap of axes."
  - "Pitfall #12 explicit positive-assertion test: `expect(getByTestId('dissent-panel')).toBeInTheDocument()` for has_dissent: false case — would fail if a future refactor added `if (!has_dissent) return null` regression."
  - "Pitfall #2 claude_analyst accent path uses border-accent/40 bg-accent/5 (verbatim OpenClaudePin palette) — a visual lock the Open Claude analyst is distinct from the 5 investor personas. Header text reads 'Open Claude Dissent' (not '{Persona} Dissents') so the distinction is reinforced verbally."
  - "Local PERSONA_LABEL const in DissentPanel — single-use; deferred any extraction to a shared lookup file until a future plan needs it elsewhere (avoids premature factor-out)."
  - "Phase 8 hookpoint discipline: BOTH the source comment (PHASE-8-HOOK: current-price-delta) AND the data-testid (current-price-placeholder) are present in DecisionRoute.tsx. Phase 8's plan-phase has two grep targets — one for source-level location, one for runtime DOM."
  - "Cross-link wrapping in TickerRoute: both Links ('→ Decision view' + '← Back to scan') grouped in a small flex container preserving Phase 6's wrap-friendly heading aesthetic — no separate row, no aesthetic regression on narrow viewports."
  - "Lite-mode (ticker_decision === null) branch: explicit amber 'No recommendation' notice mirrors TickerRoute null-decision posture — intentional 'we didn't synthesize' state, not blank page."
  - "Decoupled DriversList from TimeframeCard: TimeframeCard renders summary+status+confidence+drivers (deep-dive analysis-first); DriversList renders ONLY drivers (decision-support — the recommendation IS the summary). Visual overlap dilutes banner authority."

patterns-established:
  - "Always-render component shell: data-testid on container appears in EVERY branch; muted/empty state copy appears INSIDE the shell rather than collapsing it"
  - "Special-case persona styling: PERSONA_LABEL[id] lookup + boolean flag (e.g. isClaude) + cn() conditional class — repeatable for any future per-persona visual differentiation"
  - "Phase deferral hookpoint pair (source comment + data-testid) for any future-phase integration point that the current phase intentionally does not implement"
  - "TDD task discipline: RED test commit + GREEN impl commit per Task; small extensions (App.tsx route entry + cross-link Link) bundled into the GREEN commit of the route they enable"

requirements-completed: [VIEW-10]

# Metrics
duration: 9min
completed: 2026-05-04
---

# Phase 7 Plan 01: Decision-Support View + Dissent Surface Summary

**Decision-Support route /decision/:symbol/:date? ships with 6×3 RecommendationBanner matrix + always-rendered DissentPanel (Pitfall #12) + claude_analyst accent treatment (Pitfall #2) + Phase 8 current-price-delta hookpoint markers — closes VIEW-10 with zero new runtime deps.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-05-04T17:49:20Z
- **Completed:** 2026-05-04T17:58:34Z
- **Tasks:** 3 (each TDD RED → GREEN)
- **Production commits:** 6 (3 RED + 3 GREEN)
- **Files created:** 12 (5 components/routes + 5 test files + 1 fixture + 1 E2E spec)
- **Files modified:** 4 (App.tsx, TickerRoute.tsx, Root.tsx comment, fixtures-server.ts)

## Accomplishments

- **/decision/:symbol/:date?** mounted as third pillar route alongside /scan/:date and /ticker/:symbol/:date?; cross-link symmetry both ways with date preservation on round-trip
- **RecommendationBanner** — 6 actions × 3 conviction bands = 18 visual states; action drives color tokens (bullish/amber/fg-muted/bearish + /10 vs /15 opacity for the within-color-pair distinction); conviction drives visual weight (text-2xl/3xl/4xl + font-medium/semibold/bold); compile-time exhaustiveness via Record<DecisionRecommendation, ...> + Record<ConvictionBand, ...>
- **ConvictionDots** — 3-dot indicator with Pitfall #6 layout-shift guard (Array.from({ length: 3 }), never length: filled); 1/2/3 filled for low/medium/high
- **DriversList** — short_term + long_term card pair with UNIFORM RULE empty-state (cards stay rendered, "No drivers surfaced" copy lives inside)
- **DissentPanel** — Pitfall #12 always-render lock (no early-return null branch; explicit positive-assertion test) + Pitfall #2 claude_analyst accent treatment (border-accent/40 bg-accent/5 verbatim OpenClaudePin palette + "Open Claude Dissent" header text distinct from "{Persona} Dissents"); 5 PERSONA_LABEL canonical investor personas + null persona fallback + empty summary fallback
- **Phase 8 hookpoint markers** — both PHASE-8-HOOK: current-price-delta source comment AND data-testid="current-price-placeholder" attribute present in DecisionRoute.tsx; deterministic grep targets for downstream Phase 8 plan-phase
- **MSFT-no-dissent.json** — verbatim copy of MSFT.json with dissent block flipped (has_dissent: false / dissenting_persona: null / dissent_summary: ""); fixtures-server.ts msftNoDissent option swap-in
- **Test count delta:** vitest 197 → 234 (+37: 19 RecommendationBanner + 3 ConvictionDots + 4 DriversList + 6 DissentPanel + 5 DecisionRoute); Playwright +1 spec running across all 3 projects (chromium-desktop + mobile-safari + mobile-chrome) → 60 → 63 passed
- **Plan-gate greps all pass:** PHASE-8-HOOK comment present (lines 22 + 177); current-price-placeholder data-testid present (line 183); ZERO inline hex across the 5 new component/route files; ZERO z.enum schema redefinition (types imported from @/schemas)

## Task Commits

Each task was committed atomically per TDD discipline:

1. **Task 1 RED:** `be734bd` test(07-01): add failing tests for RecommendationBanner + ConvictionDots
2. **Task 1 GREEN:** `9c972a0` feat(07-01): implement RecommendationBanner + ConvictionDots
3. **Task 2 RED:** `6460ad6` test(07-01): add failing tests for DriversList + DissentPanel
4. **Task 2 GREEN:** `d65f424` feat(07-01): implement DriversList + DissentPanel
5. **Task 3 RED:** `913eddd` test(07-01): add failing tests for DecisionRoute
6. **Task 3 GREEN:** `c1a1c8e` feat(07-01): implement DecisionRoute + /decision/:symbol/:date? + cross-links + E2E (closes VIEW-10)

**Plan metadata commit:** (this SUMMARY.md + STATE.md + ROADMAP.md + REQUIREMENTS.md update — see final docs commit)

## Files Created/Modified

### Created

- `frontend/src/components/RecommendationBanner.tsx` — 6×3 matrix hero banner; ACTION_COLOR + ACTION_LABEL + CONVICTION_FONT + CONVICTION_DOTS Record maps for compile-time exhaustiveness; role="status" + aria-label combining action label + conviction word
- `frontend/src/components/ConvictionDots.tsx` — 3-dot conviction indicator; Array.from({ length: 3 }) Pitfall #6 layout-shift guard; filled dot bg-fg + empty dot border border-fg-muted/50
- `frontend/src/components/DriversList.tsx` — two-card pair (lg:flex-row, flex-col on mobile); STATUS_COLOR map for thesis_status pill; empty-state "No drivers surfaced" inside card (UNIFORM RULE — never collapsed)
- `frontend/src/components/DissentPanel.tsx` — Pitfall #12 always-render shell; PERSONA_LABEL local const for 5 canonical investors + claude_analyst; isClaude boolean drives accent vs amber styling + "Open Claude Dissent" vs "{Persona} Dissents" header text
- `frontend/src/routes/DecisionRoute.tsx` — third pillar route at /decision/:symbol/:date?; mirrors TickerRoute typed-error branches (FetchNotFoundError → "{symbol} not in snapshot for {date}"; SchemaMismatchError → "Schema upgrade required"); composition order: heading + ← Deep dive cross-link → data_unavailable notice (when true) → RecommendationBanner → PHASE-8-HOOK current-price-placeholder → DriversList → Separator → DissentPanel → open_observation accent block; lite-mode (ticker_decision === null) branch with explicit amber "No recommendation" notice
- `frontend/src/components/__tests__/RecommendationBanner.test.tsx` — 18 matrix tests via nested for-loops over ACTIONS × CONVICTIONS + 1 a11y test (role=status + aria-label)
- `frontend/src/components/__tests__/ConvictionDots.test.tsx` — 3 tests covering low/medium/high; each asserts EXACTLY 3 dots total + correct filled count
- `frontend/src/components/__tests__/DriversList.test.tsx` — 4 tests covering (short populated/empty) × (long populated/empty); empty-both case asserts both cards STILL rendered
- `frontend/src/components/__tests__/DissentPanel.test.tsx` — 6 tests including explicit Pitfall #12 positive assertion (`getByTestId(...)).toBeInTheDocument()` for has_dissent: false) + Pitfall #2 accent styling assertion
- `frontend/src/routes/__tests__/DecisionRoute.test.tsx` — 5 tests covering loading / FetchNotFoundError / SchemaMismatchError / happy has_dissent: true / data_unavailable: true; vi.mock('@/lib/loadTickerData') boundary mock pattern
- `frontend/tests/e2e/decision.spec.ts` — Playwright round-trip spec (/scan → /ticker → /decision → /ticker); date preservation; banner data-recommendation attr verification against NVDA fixture (take_profits); 2 driver cards; dissent has_dissent='true'; current-price-placeholder visible
- `frontend/tests/fixtures/scan/MSFT-no-dissent.json` — verbatim MSFT.json copy with dissent block flipped to has_dissent: false / dissenting_persona: null / dissent_summary: ""

### Modified

- `frontend/src/App.tsx` — third route entry { path: 'decision/:symbol/:date?', element: <DecisionRoute /> }; comment block updated to enumerate the 3 pillar routes
- `frontend/src/routes/TickerRoute.tsx` — heading row extended with "→ Decision view" Link wrapped alongside existing "← Back to scan" in a small flex container (gap-4); preserves Phase 6 wrap-friendly aesthetic; data-testid="to-decision-link"
- `frontend/src/routes/Root.tsx` — comment-only update to useActiveDate doc block to mention /decision/:symbol/:date?; useMatches loop is route-shape-agnostic so zero code change
- `frontend/tests/e2e/fixtures-server.ts` — MountOptions interface gained msftNoDissent boolean; per-ticker route handler swaps MSFT.json → MSFT-no-dissent.json when option set

## Decisions Made

- **Banner color × weight matrix locked verbatim from PLAN frontmatter / CONTEXT.md** — action axis (bullish/amber/fg-muted/bearish + /10 vs /15 opacity differentiator within color pairs) × conviction axis (text-2xl/3xl/4xl + font-medium/semibold/bold). All 18 visual states tested via nested for-loop matrix
- **Pitfall #12 explicit positive-assertion test** — `expect(getByTestId('dissent-panel')).toBeInTheDocument()` for has_dissent: false case; would fail if any future refactor added an early-return-null regression
- **Pitfall #2 accent palette verbatim from OpenClaudePin** — border-accent/40 bg-accent/5 (NOT a new variant); ensures Open Claude visual signature is consistent across deep-dive (OpenClaudePin) and decision-support (DissentPanel claude_analyst case)
- **PERSONA_LABEL local in DissentPanel** — single-use; deferred extraction to shared file until 2nd consumer materializes (premature factor-out is anti-pattern per CONTEXT.md guidance)
- **Phase 8 hookpoint pair (source comment + data-testid)** — Phase 8 grep gets both source-level location AND runtime DOM target; reduces planner ambiguity for the integration point
- **Cross-link wrapped both Links in TickerRoute heading** — group container preserves Phase 6 flex-wrap aesthetic on narrow viewports; gap-4 between the two Links maintains visual rhythm
- **DriversList decoupled from TimeframeCard** — recommendation IS the summary in decision-support context; rendering both summary + drivers in DriversList would dilute banner authority. DriversList shows ONLY drivers + the small thesis-status / confidence header row
- **Lite-mode (ticker_decision === null) handled with explicit amber notice** — mirrors TickerRoute null-decision posture; intentional state, not blank page

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Plan step ordering: App.tsx import of DecisionRoute can't typecheck before DecisionRoute exists**

- **Found during:** Task 3 (between Step 2 "App + Root extensions" and Step 3 "DecisionRoute RED → GREEN")
- **Issue:** Plan's Step 2.6 says `pnpm typecheck MUST pass before continuing` AFTER editing App.tsx to import DecisionRoute, BEFORE Step 3 creates DecisionRoute.tsx. App.tsx import would fail typecheck because the imported module doesn't yet exist.
- **Fix:** Reordered work within Task 3 to defer App.tsx + TickerRoute.tsx + Root.tsx code edits until DecisionRoute.tsx existed (i.e. bundled all extensions into the GREEN commit of Task 3 alongside the implementation). Created MSFT-no-dissent.json + fixtures-server.ts msftNoDissent option in Step 1 (no DecisionRoute dependency); wrote DecisionRoute.test.tsx in RED step 3a (DecisionRoute import fails — expected RED behavior); implemented DecisionRoute.tsx + extensions together in GREEN step 3b.
- **Files modified:** workflow ordering only; no source-level fix
- **Verification:** Typecheck clean before commit; full unit suite + E2E green
- **Committed in:** `c1a1c8e` (Task 3 GREEN — extensions bundled with DecisionRoute impl)

**2. [Rule 3 — Blocking] Playwright served stale build on first decision E2E run**

- **Found during:** Task 3 Step 4 (first run of `pnpm test:e2e --project=chromium-desktop -g "decision"`)
- **Issue:** Playwright's webServer is `pnpm preview` which serves the previously-built dist/. The new TickerRoute "→ Decision view" link existed only in source, not in the served bundle, so the spec timed out at `getByTestId('to-decision-link')`.
- **Fix:** Ran `pnpm build` to regenerate dist/ with the new link, then re-ran the E2E spec.
- **Files modified:** none (build artifact regeneration only; dist/ is gitignored)
- **Verification:** Decision spec passed in 540ms post-rebuild; full E2E suite (63 passed + 6 mobile-only-skipped) green across all 3 Playwright projects
- **Committed in:** N/A — build artifact, not source. Same foot-gun documented in Phase 6 Wave 3 SUMMARY (loadTickerData rename); recurring pattern, future plans should pre-build before Playwright runs.
- **Note:** This deviation matches the recurring pattern documented in Phase 6 Wave 3 + Wave 4 deviations — `pnpm preview`-backed Playwright config requires explicit `pnpm build` after source edits. Worth surfacing as a gap candidate for v1.x to switch to `pnpm dev`-backed webServer for tests, OR auto-build in playwright.config.ts.

---

**Total deviations:** 2 auto-fixed (both Rule 3 — blocking)
**Impact on plan:** Both deviations were workflow/ordering fixes with no scope change. The architectural and visual specs were executed verbatim — color × weight matrix, Pitfall #12 always-render, Pitfall #2 accent treatment, PHASE-8-HOOK markers, cross-link symmetry — all locked per plan with no compromises.

## Issues Encountered

None — all tasks executed in single RED → GREEN cycle each. No fix-attempt-limit triggered. No architectural Rule-4 stops. No authentication gates.

## User Setup Required

None — frontend-only plan; zero new runtime dependencies; zero new theme tokens; zero new env vars; zero new vendored shadcn components. Existing Vercel deploy continues to work unchanged.

## Next Phase Readiness

**Phase 7 closeout — VIEW-10 complete; all 15 VIEW requirements (VIEW-01 through VIEW-15) now closed across Phases 6 + 7.**

Phase 8 (Mid-Day Refresh + Resilience — REFRESH-01..04, INFRA-06..07) unblocked:

- The PHASE-8-HOOK source comment (DecisionRoute.tsx line 177) + data-testid="current-price-placeholder" (line 183) are the deterministic grep targets Phase 8's plan-phase will use to find where to wire `<CurrentPriceDelta />` (fed by `useRefreshData(symbol)`) into the DecisionRoute composition.
- Phase 8's `api/refresh.py` Vercel Python serverless function will return current price + post-snapshot headlines; frontend's `useRefreshData(symbol)` TanStack Query hook (Phase 8 will create) populates the delta. The placeholder block already shows the snapshot computed_at timestamp + the explanatory copy ("Current-price delta arrives via mid-day refresh in Phase 8") so the user sees an intentional "snapshot price now, live delta soon" state until Phase 8 lands.
- Phase 9 (Endorsement Capture — ENDORSE-01..03) also depends on Phase 7's DecisionRoute as the rendering surface for endorsement badges. Phase 9's plan-phase will likely add an EndorsementsList component composed below the DissentPanel.

Verifier (`/gmd:verify-phase 7`) and Nyquist coverage (`/gmd:validate-phase 7`) will auto-fire from the orchestrator if quota allows. Both manual-only verifications from VALIDATION.md (visual taste-check at /decision/AAPL/today; cross-link UX flow) are user-facing and deferred to user — those do not block Phase 8.

## Self-Check: PASSED

All 13 created files verified on disk; all 6 production commits present in git log.

---
*Phase: 07-decision-support-view-dissent-surface*
*Completed: 2026-05-04*
