---
phase: 7
slug: decision-support-view-dissent-surface
status: ready
nyquist_compliant: true
wave_0_complete: n/a
created: 2026-05-04
planner_filled: 2026-05-04
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

Frontend-only phase. Single wave. Reuses the Phase 6 vitest + Playwright stack.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest 2.1 + @testing-library/react 16 + Playwright 1.59 |
| **Config file** | `frontend/vitest.config.ts` + `frontend/playwright.config.ts` (already created in Phase 6 Wave 1) |
| **Quick run command (unit)** | `cd frontend && pnpm test:unit src/components/__tests__/RecommendationBanner.test.tsx src/components/__tests__/DissentPanel.test.tsx --run` |
| **Full unit suite** | `cd frontend && pnpm test:unit --run` |
| **E2E single project** | `cd frontend && pnpm test:e2e --project=chromium-desktop -g 'decision'` |
| **Full E2E** | `cd frontend && pnpm test:e2e` |
| **Estimated runtime** | quick ~3s · full unit ~10s · single E2E ~10s · full 3-project E2E ~90s |

---

## Sampling Rate

- **After every task commit:** Run quick unit command for the touched component(s).
- **At plan close:** Run full unit suite + Playwright `-g decision` happy path.
- **Before `/gmd:verify-phase`:** Full unit suite green; Playwright decision spec passing on chromium-desktop AND mobile-safari.
- **Max feedback latency:** 60 seconds (single-project Playwright).

---

## Per-Task Verification Map

> Filled in by planner 2026-05-04. Each task in `07-01-decision-support-PLAN.md` references one of these commands.

### Plan 07-01 — Decision-Support View (Wave 1)

| Task ID | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|-------------|-----------|-------------------|--------|
| 07-01-1 | 1 | VIEW-10 (RecommendationBanner 6×3 matrix + ConvictionDots 3-state) | unit (vitest + RTL, TDD RED→GREEN — 1 RED commit + 1 GREEN commit) | `cd frontend && pnpm test:unit src/components/__tests__/RecommendationBanner.test.tsx src/components/__tests__/ConvictionDots.test.tsx --run` | ⬜ planned |
| 07-01-2 | 1 | VIEW-10 (DriversList short+long pair, empty-state UNIFORM RULE; DissentPanel always-render Pitfall #12 + claude_analyst accent Pitfall #2) | unit (vitest + RTL, TDD RED→GREEN — 1 RED commit + 1 GREEN commit) | `cd frontend && pnpm test:unit src/components/__tests__/DriversList.test.tsx src/components/__tests__/DissentPanel.test.tsx --run` | ⬜ planned |
| 07-01-3 | 1 | VIEW-10 (DecisionRoute composition + App.tsx route + TickerRoute cross-link + Phase 8 hookpoint markers + E2E round-trip /scan→/ticker→/decision→/ticker) | unit + e2e (vitest RTL + Playwright chromium-desktop; TDD RED→GREEN on DecisionRoute) | `cd frontend && pnpm test:unit --run && pnpm test:e2e --project=chromium-desktop -g "decision" && pnpm typecheck` | ⬜ planned |

*Status: ⬜ planned · ⬜ pending (in execution) · ✅ green · ❌ red · ⚠️ flaky*

**Test count totals (planner estimate):**
- Task 1: 22 vitest tests (3 ConvictionDots + 19 RecommendationBanner)
- Task 2: 10 vitest tests (4 DriversList + 6 DissentPanel)
- Task 3: 5 vitest tests (DecisionRoute) + 1 Playwright spec
- **Phase total: 37 new vitest + 1 new Playwright spec → suite goes 197→234 vitest, +1 spec on chromium-desktop**

---

## Wave 0 Requirements

No Wave 0 — Phase 7 builds entirely on Phase 6 infrastructure. All test fixtures, components, schemas, and routing patterns already exist. Zero new deps. The only "fixture work" is creating `frontend/tests/fixtures/scan/MSFT-no-dissent.json` (verbatim copy of MSFT.json with the dissent block flipped to `has_dissent: false` / `dissenting_persona: null` / `dissent_summary: ""`) — this is a Task 3 sub-step, not a Wave 0 task.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual taste-check on `/decision/AAPL/today` | VIEW-10 design lock | Aesthetic judgment against Notion-Clean palette + recommendation visual hierarchy | After Wave 1 closeout: user reviews `/decision/AAPL/today` against the locked banner color × conviction weight matrix; confirms dissent-panel "intentional silence" reads as trustworthy not missing-content |
| Cross-link UX flow (`/ticker/X` ↔ `/decision/X`) | VIEW-10 routing | UX taste — does the round trip feel natural? | After Wave 1: navigate from /ticker/AAPL → click "→ Decision view" → see banner → click "← Deep dive" → back at /ticker/AAPL with same date preserved |

---

## Validation Sign-Off

- [x] All 3 tasks have `<automated>` verify (RED+GREEN per TDD task)
- [x] Sampling continuity: every task has automated verify (3/3)
- [x] Wave 0 not needed (existing infrastructure covers all phase requirements)
- [x] No watch-mode flags (all commands use `--run`)
- [x] Feedback latency < 60s (Task 1 ~3s · Task 2 ~3s · Task 3 ~70s including E2E — within sampling SLO when split)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planner-approved 2026-05-04 — plan 07-01 references all 3 task IDs with automated `<automated>` verify commands; Per-Task Verification Map filled in; nyquist_compliant flipped to true.
