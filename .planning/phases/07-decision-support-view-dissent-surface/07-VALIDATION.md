---
phase: 7
slug: decision-support-view-dissent-surface
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-04
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

> Filled in by planner. Each task references one of these commands.

### Plan 07-01 — Decision-Support View (Wave 1)

| Task ID | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|-------------|-----------|-------------------|--------|
| 07-01-1 | 1 | VIEW-10 (RecommendationBanner + ConvictionDots) | unit | `cd frontend && pnpm test:unit src/components/__tests__/RecommendationBanner.test.tsx src/components/__tests__/ConvictionDots.test.tsx --run` | ⬜ pending |
| 07-01-2 | 1 | VIEW-10 (DriversList + DissentPanel) | unit | `cd frontend && pnpm test:unit src/components/__tests__/DriversList.test.tsx src/components/__tests__/DissentPanel.test.tsx --run` | ⬜ pending |
| 07-01-3 | 1 | VIEW-10 (DecisionRoute + cross-links + E2E) | unit + e2e | `cd frontend && pnpm test:unit --run && pnpm test:e2e --project=chromium-desktop -g 'decision'` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

No Wave 0 — Phase 7 builds entirely on Phase 6 infrastructure. All test fixtures, components, schemas, and routing patterns already exist. Zero new deps.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual taste-check on `/decision/AAPL/today` | VIEW-10 design lock | Aesthetic judgment against Notion-Clean palette + recommendation visual hierarchy | After Wave 1 closeout: user reviews `/decision/AAPL/today` against the locked banner color × conviction weight matrix; confirms dissent-panel "intentional silence" reads as trustworthy not missing-content |
| Cross-link UX flow (`/ticker/X` ↔ `/decision/X`) | VIEW-10 routing | UX taste — does the round trip feel natural? | After Wave 1: navigate from /ticker/AAPL → click "→ Decision view" → see banner → click "← Deep dive" → back at /ticker/AAPL with same date preserved |

---

## Validation Sign-Off

- [ ] All 3 tasks have `<automated>` verify
- [ ] Sampling continuity: every task has automated verify (3/3)
- [ ] Wave 0 not needed (existing infrastructure covers all phase requirements)
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter (set after planner fills Per-Task Verification Map)

**Approval:** pending
