---
phase: 6
slug: frontend-mvp-morning-scan-deep-dive
status: locked
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-04
updated: 2026-05-04
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

This phase has TWO test stacks because Wave 0 amends Python (Phase 5 storage) while Waves 1-4 build the React frontend:

- **Python side (Wave 0):** existing pytest 9.x suite (~639 tests baseline at end of Phase 5; ~659 after Wave 0).
- **Frontend side (Waves 1-4):** vitest + React Testing Library for unit/component; Playwright for E2E.

---

## Test Infrastructure

### Python (Wave 0 only)

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-asyncio + pytest-cov |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/ingestion/test_news.py tests/routine/test_storage.py tests/synthesis/test_decision.py tests/analysts/test_indicator_math.py tests/routine/test_run_for_watchlist.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | quick ~3s · full ~8s |

### Frontend (Waves 1-4)

| Property | Value |
|----------|-------|
| **Framework** | vitest 2.x + @testing-library/react 16 + Playwright 1.48 |
| **Config file** | `frontend/vitest.config.ts` + `frontend/playwright.config.ts` (created Wave 1) |
| **Quick run command (unit)** | `cd frontend && pnpm test:unit --run` |
| **Quick run command (E2E single project)** | `cd frontend && pnpm test:e2e --project=chromium-desktop` |
| **Full suite command** | `cd frontend && pnpm test:unit --run && pnpm test:e2e` |
| **Estimated runtime** | unit ~5-15s · e2e (single project) ~30s · e2e (3 projects) ~90s |

---

## Sampling Rate

- **After every task commit:** Run the quick command for whichever side the task touched (Python or Frontend).
- **After every plan wave:** Run the full suite for the side that wave touched. After Wave 0: Python full suite must be green. After Wave 4: both Python AND frontend full suites (3 Playwright projects) must be green.
- **Before `/gmd:verify-phase`:** Both full suites green; Playwright happy-path passing on chromium-desktop AND mobile-safari (mobile-chrome optional but recommended).
- **Max feedback latency:** 60 seconds for any single test command (Playwright on a single project; vitest unit + Python pytest both well under). Full 3-project Playwright run is ~90s and is run only at wave/phase close.

---

## Per-Task Verification Map

> Filled in by planner during Step 8. Each plan's tasks reference these test commands.

### Plan 06-01 — Storage Amendment (Wave 0, Python, TDD)

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-1 | 01 | 0 | INFRA-05 (RED phase) | unit | `uv run pytest tests/analysts/test_indicator_math.py tests/synthesis/test_decision.py tests/routine/test_storage.py tests/routine/test_run_for_watchlist.py tests/ingestion/test_news.py -q` | ✅ existing | ⬜ pending |
| 06-01-2 | 01 | 0 | INFRA-05 (GREEN phase) | unit + full | `uv run pytest -q` | ✅ existing | ⬜ pending |
| 06-01-3 | 01 | 0 | INFRA-05 (docs fix) | docs-grep | `grep -nE "(2h\|12h).*stale\|stale.*(2h\|12h)" .planning/ROADMAP.md .planning/PROJECT.md .planning/REQUIREMENTS.md ; echo "EXIT_CODE=$?"` | ✅ existing | ⬜ pending |

### Plan 06-02 — Frontend Scaffold (Wave 1, Frontend)

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-02-1 | 02 | 1 | INFRA-05 (scaffold) | typecheck + build + smoke e2e | `cd frontend && pnpm typecheck && pnpm build && pnpm test:e2e --project=chromium-desktop -g smoke` | ❌ Wave 1 creates | ⬜ pending |
| 06-02-2 | 02 | 1 | INFRA-05 (zod schemas) | unit | `cd frontend && pnpm test:unit src/schemas --run` | ❌ Wave 1 creates | ⬜ pending |
| 06-02-3 | 02 | 1 | INFRA-05 (lib helpers) | unit | `cd frontend && pnpm test:unit --run` | ❌ Wave 1 creates | ⬜ pending |

### Plan 06-03 — Morning Scan (Wave 2, Frontend)

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-03-1 | 03 | 2 | VIEW-11 (StalenessBadge + visual primitives) | unit | `cd frontend && pnpm test:unit src/components --run` | ❌ Wave 1 created scaffolding | ⬜ pending |
| 06-03-2 | 03 | 2 | VIEW-01, VIEW-02, VIEW-03 (lenses + ScanRoute) | unit | `cd frontend && pnpm test:unit --run` | ❌ Wave 2 creates | ⬜ pending |
| 06-03-3 | 03 | 2 | VIEW-01, VIEW-02, VIEW-03 (E2E) | e2e | `cd frontend && pnpm test:e2e --project=chromium-desktop -g 'morning scan'` | ❌ Wave 2 creates | ⬜ pending |

### Plan 06-04 — Deep-Dive (Wave 3, Frontend)

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-04-1 | 04 | 3 | VIEW-06 (Chart) | unit | `cd frontend && pnpm test:unit src/components/__tests__/Chart.test.tsx --run` | ❌ Wave 3 creates | ⬜ pending |
| 06-04-2 | 04 | 3 | VIEW-05, VIEW-07, VIEW-08, VIEW-09 (cards) | unit | `cd frontend && pnpm test:unit src/components --run` | ❌ Wave 3 creates | ⬜ pending |
| 06-04-3 | 04 | 3 | VIEW-04, VIEW-05, VIEW-07, VIEW-08, VIEW-09, VIEW-13 (TickerRoute + E2E) | unit + e2e | `cd frontend && pnpm test:unit --run && pnpm test:e2e --project=chromium-desktop -g 'deep dive'` | ❌ Wave 3 creates | ⬜ pending |

### Plan 06-05 — Polish + Responsive + Playwright (Wave 4, Frontend)

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-05-1 | 05 | 4 | VIEW-14, VIEW-15 (ErrorBoundary + DateSelector + loadDates) | unit | `cd frontend && pnpm test:unit --run` | ❌ Wave 4 creates | ⬜ pending |
| 06-05-2 | 05 | 4 | VIEW-12 (responsive + chart touch) | e2e mobile | `cd frontend && pnpm test:e2e --project=mobile-safari -g responsive` | ❌ Wave 4 creates | ⬜ pending |
| 06-05-3 | 05 | 4 | VIEW-12, VIEW-14, VIEW-15 (full E2E + taste-check) | full e2e (3 projects) | `cd frontend && pnpm test:e2e` | ❌ Wave 4 creates | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Each task in each PLAN.md populates its `<verify><automated>` block with the command from the row above (or a more-specific subset). The planner enforces this during plan-checker Dimension 8 (Nyquist sampling).*

---

## Wave 0 Requirements

Wave 0 (Phase 5 amendment) requires:

- [ ] `tests/ingestion/test_news.py` — extend with persistence-of-headlines test (raw headlines list returned, not just sentiment score)
- [ ] `tests/analysts/test_indicator_math.py` — extend with `_ma_series`, `_bb_series`, `_rsi_series` series-form helpers (must produce values byte-identical to existing single-point versions at iloc[-1])
- [ ] `tests/routine/test_storage.py` — extend with `ohlc_history` + `indicators` + `headlines` persistence + `_dates.json` write
- [ ] `tests/synthesis/test_decision.py` — extend with `ThesisStatus` Literal + `TimeframeBand.thesis_status` field (default `"n/a"`) + `TickerDecision.schema_version` default = 2
- [ ] `tests/routine/test_run_for_watchlist.py` — extend with TickerResult threading ohlc_history + headlines through pipeline
- [ ] Frontend testing infrastructure installed in Wave 1: `pnpm install` (deps from package.json) + `pnpm exec playwright install chromium webkit` (executed via `postinstall` script in package.json)
- [ ] `frontend/vitest.config.ts` + `frontend/playwright.config.ts` created in Wave 1

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| iOS Safari real-device render quality | VIEW-12 / success criterion #6 | Playwright WebKit ≠ real iOS Safari for some font/touch behaviors; user-facing taste check | Open `https://<vercel-preview>.vercel.app/scan/today` on iPhone; verify lens tabs are tap-friendly, chart pans/pinches, no horizontal scroll, staleness badge legible |
| Android Chrome real-device render | VIEW-12 / success criterion #6 | Same — real device > emulator for taste | Same URL on Android Chrome; verify tap-friendly, chart pans, layout doesn't break |
| Vercel deploy succeeds + reads from real GitHub raw URL | INFRA-05 / success criterion #1 | Production CDN behavior + env-var injection only validatable at deploy time | After Wave 4 final commit + push, verify Vercel auto-deploys, env vars resolve, and `/scan/today` loads real data |
| Notion-Clean visual taste-check | CONTEXT design lock | Aesthetic judgment, not regressable | After Wave 4: user reviews `/scan/today` + `/ticker/AAPL/today` against the locked color/spacing/typography spec; reports any drift |

---

## Validation Sign-Off

- [x] All tasks have `<verify><automated>` commands or Wave 0 dependencies named explicitly
- [x] Sampling continuity: every task has automated verify (no 3-consecutive-without gap)
- [x] Wave 0 covers all MISSING references (frontend test infrastructure created in Wave 1 Task 1; Wave 0 Python tests reference existing pytest config)
- [x] No watch-mode flags (vitest uses `--run`; Playwright uses `pnpm test:e2e` without `--ui`)
- [x] Feedback latency < 60s per single command (90s for full 3-project Playwright run; only invoked at wave close + phase verification)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** locked 2026-05-04 — Plans 06-01..06-05 created with per-task automated_verify commands populated.
