---
phase: 9
slug: endorsement-capture
status: draft
nyquist_compliant: false
wave_0_complete: n/a
created: 2026-05-04
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

Final phase of v1. Single wave, three tasks. Reuses Phase 5/6/7/8 test infrastructure verbatim.

---

## Test Infrastructure

### Python (Tasks 1)

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Quick run** | `python -m pytest tests/analysts/test_endorsement_schema.py tests/endorsements/test_log.py tests/cli/test_add_endorsement.py -q` |
| **Full suite** | `python -m pytest -q` |
| **Estimated runtime** | quick ~3s · full ~10s |

### Frontend (Tasks 2-3)

| Property | Value |
|----------|-------|
| **Framework** | vitest 2.1 + @testing-library/react 16 + Playwright 1.59 |
| **Quick run (unit)** | `cd frontend && pnpm test:unit src/schemas/__tests__/endorsement.test.ts src/lib/__tests__/loadEndorsements.test.ts src/components/__tests__/EndorsementsList.test.tsx --run` |
| **Full unit** | `cd frontend && pnpm test:unit --run` |
| **E2E single** | `cd frontend && pnpm test:e2e --project=chromium-desktop -g 'endorsements'` |

---

## Per-Task Verification Map

### Plan 09-01 — Endorsement Capture (Wave 1)

| Task ID | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|-------------|-----------|-------------------|--------|
| 09-01-1 | 1 | ENDORSE-01, ENDORSE-03 (Python schema + log + CLI) | unit | `python -m pytest tests/analysts/test_endorsement_schema.py tests/endorsements/test_log.py tests/cli/test_add_endorsement.py -q` | ⬜ pending |
| 09-01-2 | 1 | ENDORSE-02, ENDORSE-03 (frontend schema + fetcher) | unit | `cd frontend && pnpm test:unit src/schemas/__tests__/endorsement.test.ts src/lib/__tests__/loadEndorsements.test.ts --run` | ⬜ pending |
| 09-01-3 | 1 | ENDORSE-02 (component + mount + E2E) | unit + e2e | `cd frontend && pnpm test:unit --run && pnpm test:e2e --project=chromium-desktop -g 'endorsements'` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end CLI append + frontend render | ENDORSE-01 + ENDORSE-02 | Real GitHub raw fetch round-trip | After Phase 9 deploy: `markets add_endorsement --ticker AAPL --source "Motley Fool" --date 2026-04-15 --price 178.42 --notes "test"`; commit + push; open `/decision/AAPL/today` on Vercel preview; verify endorsement card appears |
| Notion-Clean visual taste-check on EndorsementsList | ENDORSE-02 | Aesthetic judgment | After Wave 1: review `/decision/AAPL/today` rendering; confirm card spacing, restraint, hairline borders, no inline color drift |

---

## Validation Sign-Off

- [ ] All 3 tasks have `<automated>` verify
- [ ] Sampling continuity: every task has automated verify
- [ ] Wave 0 not needed (single-wave phase, all infrastructure inherited)
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter (post-planner)

**Approval:** pending
