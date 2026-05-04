---
phase: 6
slug: frontend-mvp-morning-scan-deep-dive
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-04
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

This phase has TWO test stacks because Wave 0 amends Python (Phase 5 storage) while Waves 1-4 build the React frontend:

- **Python side (Wave 0):** existing pytest 9.x suite (~639 tests baseline at end of Phase 5).
- **Frontend side (Waves 1-4):** vitest + React Testing Library for unit/component; Playwright for E2E.

---

## Test Infrastructure

### Python (Wave 0 only)

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-asyncio + pytest-cov |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/ingestion/test_news.py tests/routine/test_storage.py tests/synthesis/test_decision.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | quick ~3s · full ~8s |

### Frontend (Waves 1-4)

| Property | Value |
|----------|-------|
| **Framework** | vitest 2.x + @testing-library/react 16 + Playwright 1.48 |
| **Config file** | `frontend/vitest.config.ts` + `frontend/playwright.config.ts` (created Wave 1) |
| **Quick run command** | `cd frontend && pnpm test:unit --run` |
| **Full suite command** | `cd frontend && pnpm test:unit --run && pnpm test:e2e` |
| **Estimated runtime** | unit ~5-15s · e2e ~30-60s |

---

## Sampling Rate

- **After every task commit:** Run the quick command for whichever side the task touched (Python or Frontend).
- **After every plan wave:** Run the full suite for the side that wave touched. After Wave 0: Python full suite must be green. After Wave 4: both Python AND frontend full suites must be green.
- **Before `/gmd:verify-phase`:** Both full suites green; Playwright E2E happy-path passing on at least Chromium-headless.
- **Max feedback latency:** 60 seconds (Playwright is the slowest; vitest unit + Python pytest both well under).

---

## Per-Task Verification Map

> Filled in by planner during Step 8. Each plan's tasks reference these test commands.

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-XX | 01 | 0 | INFRA-05 / Wave 0 amendment | unit | `uv run pytest tests/routine/test_storage.py -q` | ❌ W0 | ⬜ pending |
| 06-02-XX | 02 | 1 | INFRA-05 / scaffold + zod | unit | `cd frontend && pnpm test:unit src/schemas --run` | ❌ W0 | ⬜ pending |
| 06-03-XX | 03 | 2 | VIEW-01..03 / Morning Scan | unit + e2e | `cd frontend && pnpm test:unit --run && pnpm test:e2e -g "morning scan"` | ❌ W0 | ⬜ pending |
| 06-04-XX | 04 | 3 | VIEW-04..09 / Deep-Dive | unit + e2e | `cd frontend && pnpm test:unit --run && pnpm test:e2e -g "deep dive"` | ❌ W0 | ⬜ pending |
| 06-05-XX | 05 | 4 | VIEW-11..15 / Polish + responsive | unit + e2e | `cd frontend && pnpm test:e2e --project=mobile-safari` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Each task in each PLAN.md must populate its `automated_verify` field with one of the commands above (or a more-specific subset). The planner enforces this during plan-checker Dimension 8.*

---

## Wave 0 Requirements

Wave 0 (Phase 5 amendment) requires:

- [ ] `tests/ingestion/test_news.py` — extend with persistence-of-headlines test (raw headlines list returned, not just sentiment score)
- [ ] `tests/analysts/test_indicator_math.py` — extend with `_ma_series`, `_bb_series`, `_rsi_series` series-form helpers (must produce values byte-identical to existing single-point versions)
- [ ] `tests/routine/test_storage.py` — extend with `ohlc_history` + `indicators` + `headlines` persistence + `_dates.json` write
- [ ] `tests/synthesis/test_decision.py` — extend with `ThesisStatus` Literal + `TimeframeBand.thesis_status` field (default `"n/a"`)
- [ ] Frontend testing infrastructure installed in Wave 1: `pnpm install vitest @testing-library/react @testing-library/dom @vitejs/plugin-react @types/node` + `pnpm install -D playwright @playwright/test`. `pnpm exec playwright install chromium webkit` for the manual-phone-test browsers.
- [ ] `frontend/vitest.config.ts` + `frontend/playwright.config.ts` created in Wave 1.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| iOS Safari real-device render quality | VIEW-15 / success criterion #6 | Playwright WebKit ≠ real iOS Safari for some font/touch behaviors; user-facing taste check | Open `https://<vercel-preview>.vercel.app/scan/today` on iPhone; verify lens tabs are tap-friendly, chart pans/pinches, no horizontal scroll, staleness badge legible |
| Android Chrome real-device render | VIEW-15 / success criterion #6 | Same — real device > emulator for taste | Same URL on Android Chrome; verify tap-friendly, chart pans, layout doesn't break |
| Vercel deploy succeeds + reads from real GitHub raw URL | INFRA-05 / success criterion #1 | Production CDN behavior + env-var injection only validatable at deploy time | After Wave 4 final commit + push, verify Vercel auto-deploys, env vars resolve, and `/scan/today` loads real data |
| Notion-Clean visual taste-check | CONTEXT design lock | Aesthetic judgment, not regressable | After Wave 4: user reviews `/scan/today` + `/ticker/AAPL/today` against the locked color/spacing/typography spec; reports any drift |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (frontend test infrastructure)
- [ ] No watch-mode flags (use `--run` for vitest, no `--watch`; use `pnpm test:e2e`, no `--ui`)
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter (set after planner fills Per-Task Verification Map)

**Approval:** pending
