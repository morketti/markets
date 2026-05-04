---
phase: 8
slug: mid-day-refresh-resilience
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-04
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

Two-wave phase. Wave 0 = Python backend (refresh function + memory log + provenance + resilience tests). Wave 1 = frontend integration (TanStack hook + CurrentPriceDelta + cross-mount).

---

## Test Infrastructure

### Python (Wave 0)

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-asyncio + pytest-cov |
| **Quick run** | `uv run pytest tests/api/ tests/routine/test_memory_log.py tests/scripts/test_check_provenance.py tests/ingestion/test_prices.py tests/ingestion/test_news.py -q` |
| **Full suite** | `uv run pytest -q` |
| **Estimated runtime** | quick ~4s · full ~10s |

### Frontend (Wave 1)

| Property | Value |
|----------|-------|
| **Framework** | vitest 2.1 + @testing-library/react 16 + Playwright 1.59 |
| **Quick run (unit)** | `cd frontend && pnpm test:unit src/lib/__tests__/useRefreshData.test.ts src/components/__tests__/CurrentPriceDelta.test.tsx src/schemas/__tests__/refresh.test.ts --run` |
| **Full unit** | `cd frontend && pnpm test:unit --run` |
| **E2E resilience** | `cd frontend && pnpm test:e2e --project=chromium-desktop -g 'resilience'` |
| **Full E2E** | `cd frontend && pnpm test:e2e` |
| **Estimated runtime** | quick ~3s · full unit ~12s · single E2E ~15s |

---

## Sampling Rate

- **After every task commit:** Run quick unit command for the touched side.
- **At plan close:** Full suite for the touched side + targeted E2E if frontend.
- **Before `/gmd:verify-phase`:** Both Python full suite + frontend full unit + Playwright resilience spec all green.
- **Max feedback latency:** 60s.

---

## Per-Task Verification Map

> Filled in by planner. Each task in each PLAN.md references one of these commands.

### Plan 08-01 — Backend Refresh + Memory Log + Provenance (Wave 0, Python)

| Task ID | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|-------------|-----------|-------------------|--------|
| 08-01-1 | 0 | REFRESH-01, REFRESH-04 (backend) | unit | `uv run pytest tests/api/ -q` | ⬜ pending |
| 08-01-2 | 0 | INFRA-06 (memory log) | unit | `uv run pytest tests/routine/test_memory_log.py tests/routine/test_run_for_watchlist.py -q` | ⬜ pending |
| 08-01-3 | 0 | INFRA-07 (provenance) + REFRESH-04 (resilience) | unit | `uv run pytest tests/scripts/test_check_provenance.py tests/ingestion/test_prices.py tests/ingestion/test_news.py -q && python scripts/check_provenance.py` | ⬜ pending |

### Plan 08-02 — Frontend Refresh Integration (Wave 1, Frontend)

| Task ID | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|-------------|-----------|-------------------|--------|
| 08-02-1 | 1 | REFRESH-02 (hook + schema) | unit | `cd frontend && pnpm test:unit src/lib/__tests__/useRefreshData.test.ts src/schemas/__tests__/refresh.test.ts --run` | ⬜ pending |
| 08-02-2 | 1 | REFRESH-02, REFRESH-03 (component + cross-mount) | unit | `cd frontend && pnpm test:unit src/components/__tests__/CurrentPriceDelta.test.tsx --run && pnpm test:unit --run` | ⬜ pending |
| 08-02-3 | 1 | REFRESH-04 (resilience E2E) | e2e | `cd frontend && pnpm test:e2e --project=chromium-desktop -g 'resilience'` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 produces:
- `tests/api/test_refresh.py` (new) — refresh function happy + failure modes + timeout simulation
- `tests/routine/test_memory_log.py` (new) — JSONL append contract + atomic write + record schema
- `tests/scripts/test_check_provenance.py` (new) — accept/reject regex test cases for the provenance walker
- Extensions to `tests/ingestion/test_prices.py` + `tests/ingestion/test_news.py` — resilience cases
- `.pre-commit-config.yaml` — provenance hook entry (skipped on hooks=false config; CI runs always)

Wave 1 produces:
- `frontend/src/schemas/__tests__/refresh.test.ts` (new) — zod parse correctness for refresh response shapes
- `frontend/src/lib/__tests__/useRefreshData.test.ts` (new) — TanStack hook behavior incl. error branch
- `frontend/src/components/__tests__/CurrentPriceDelta.test.tsx` (new) — render states + isError fallback
- `frontend/tests/e2e/resilience.spec.ts` (new) — Playwright: refresh fetch fails (mocked) → snapshot stays canonical

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Vercel function deploys + reachable from preview URL | REFRESH-01 | Real Vercel deployment + cold-start timing only verifiable post-deploy | After Wave 1 commit + push to a preview branch: `curl https://<preview>.vercel.app/api/refresh?ticker=AAPL` returns valid JSON within 10s |
| Cold-start timing under realistic load | REFRESH-01 + ROADMAP research_flag | yfinance import + first RSS fetch on cold function — measure actual budget vs 30s maxDuration | First 3 requests after preview deploy: log timings; should be 3-8s realistic, well under 30s cap |
| Refresh + snapshot integration UX in real browser | REFRESH-02, REFRESH-03 | UX taste — does the merge feel natural, no flicker on symbol change? | Open `/ticker/AAPL/today` → see snapshot price → see refresh swap to current within ~3s → switch to `/ticker/MSFT/today` → no flicker, refresh kicks for new symbol |
| `vercel.json` SPA-rewrite narrowing actually works | REFRESH-01 (load-bearing fix) | Routing-layer behavior | Preview URL `/api/refresh?ticker=AAPL` returns JSON (not HTML SPA shell) — this is the canary for the rewrite-narrowing fix |

---

## Validation Sign-Off

- [ ] All 6 tasks have `<automated>` verify
- [ ] Sampling continuity: every task has automated verify
- [ ] Wave 0 covers all MISSING references (api/, scripts/, memory log infrastructure)
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter (post-planner)

**Approval:** pending
