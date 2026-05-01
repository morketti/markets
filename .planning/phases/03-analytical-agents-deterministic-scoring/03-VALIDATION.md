---
phase: 3
slug: analytical-agents-deterministic-scoring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-01
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Detail authority: see `## Validation Architecture` in `03-RESEARCH.md` for the full per-test specification (req-ID coverage, fixture corpus, regression tests). This file mirrors that spec into the Nyquist-required shape and adds sampling cadence.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + pytest-cov 7.x (already pinned in `[dependency-groups].dev`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]`, `addopts = "-ra --strict-markers"` |
| **Quick run command** | `uv run pytest tests/analysts -x` |
| **Full suite command** | `uv run pytest --cov` |
| **Estimated runtime** | ~10 seconds (full suite, includes Phases 1+2) |

---

## Sampling Rate

- **After every task commit:** `uv run pytest tests/analysts -x` (quick run; only the analyst tests touched in this phase)
- **After every plan wave:** `uv run pytest --cov` (full suite — catches regressions in Phase 1+2 caused by schema or dep changes)
- **Before `/gmd:verify-work`:** Full suite must be green AND coverage ≥90% line / ≥85% branch on `analysts/{signals,fundamentals,technicals,news_sentiment,valuation}.py`
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

> Source: `03-RESEARCH.md` § "Phase Requirements → Test Map". The planner refines this map by mapping concrete `task_id`s once PLAN.md files exist. Initial mapping below covers requirement → test-file granularity; task-level refinement happens in plan-checker iteration.

| Req | Behavior under test | Test Type | Automated Command | File After Wave | Status |
|-----|---------------------|-----------|-------------------|-----------------|--------|
| AgentSignal schema | shape, validators, serialize/deserialize round-trip | unit | `pytest tests/analysts/test_signals.py -x` | Wave 1 | ⬜ pending |
| ANLY-01 | Fundamentals analyst: per-config + fallback + 5-state ladder + per-metric isolation + empty-data | unit | `pytest tests/analysts/test_fundamentals.py -x` | Wave 1 | ⬜ pending |
| ANLY-02 | Technicals analyst: MA stack patterns + momentum + ADX trend gating + warm-up guards (<200, <27, <20 bars) + known-regime regressions | unit | `pytest tests/analysts/test_technicals.py -x` | Wave 2 | ⬜ pending |
| ANLY-03 | News/sentiment: VADER bullish/bearish/neutral + recency decay (3-day half-life) + source weighting + empty list + undated drop | unit | `pytest tests/analysts/test_news_sentiment.py -x` | Wave 2 | ⬜ pending |
| ANLY-04 | Valuation: thesis_price-only + targets-only + consensus-only + all-three blend + none-set (data_unavailable) | unit | `pytest tests/analysts/test_valuation.py -x` | Wave 2 | ⬜ pending |
| Cross-cutting (Snapshot data_unavailable) | All four analysts emit data_unavailable=True when snapshot.data_unavailable=True | unit | `pytest tests/analysts/test_invariants.py::test_dark_snapshot_emits_four_unavailable -x` | Wave 2 | ⬜ pending |
| Cross-cutting (always 4 signals) | For any (snapshot, config) combination, exactly 4 AgentSignals are produced | unit | `pytest tests/analysts/test_invariants.py::test_always_four_signals -x` | Wave 2 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/analysts/__init__.py` — package marker (currently does not exist; `tests/` has only `tests/ingestion/` and top-level test files)
- [ ] `tests/analysts/conftest.py` — shared analyst fixtures: `make_snapshot(...)`, `make_ticker_config(...)`, deterministic `frozen_now`, regime-specific price-history builders (synthetic uptrend / downtrend / sideways)
- [ ] `vaderSentiment >= 3.3, < 4` added to `pyproject.toml` `[project.dependencies]` and locked into `poetry.lock` (Wave 0 dep install task)
- [ ] **External pre-Phase-3 dependency** — `02-07-fundamentals-analyst-fields-PLAN.md` (or equivalent) must add `analyst_target_mean`, `analyst_target_median`, `analyst_recommendation_mean`, `analyst_opinion_count` to `FundamentalsSnapshot`. ANLY-04 (valuation analyst) cannot ship without these. Planner must decide whether this is a separate Phase 2 patch plan or a Wave 0 task in Phase 3 — see CORRECTIONS block in 03-RESEARCH.md.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| (none) | — | All Phase 3 deliverables are pure-function Python with deterministic inputs/outputs — fully covered by automated unit tests. | — |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (vaderSentiment dep, tests/analysts/ package + conftest, Phase 2 schema amendment ordering)
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter (post-planner verification)

**Approval:** pending
