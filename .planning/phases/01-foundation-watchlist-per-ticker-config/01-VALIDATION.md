---
phase: 1
slug: foundation-watchlist-per-ticker-config
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-30
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from `01-RESEARCH.md` § Validation Architecture.

---

## Wave 0 Model (TDD-Equivalent)

**This phase uses TDD Red commits as the Wave 0 equivalent.** Every test file is created by its owning plan's TDD Red phase BEFORE any implementation lands in the same plan:

- Plan 02 (Schemas, type=tdd) — RED commit creates `tests/test_schemas.py`
- Plan 03 (Loader, type=tdd) — RED commit creates `tests/test_loader.py`
- Plan 04 (CLI core, type=tdd) — RED commit creates `tests/test_cli_add.py`, `tests/test_cli_remove.py`, `tests/test_cli_errors.py`
- Plan 05 (CLI readonly, type=tdd) — RED commit creates `tests/test_cli_readonly.py`

Plan 01 (Scaffold) creates `tests/__init__.py` and `tests/conftest.py` (the shared fixture surface) so pytest collection works before any test files exist.

**Probe markers `❌ W0` in the table below mean "test file does not yet exist on disk" — they are satisfied by the corresponding plan's TDD Red phase commit.** The `<verify>` commands in each plan's tasks are the satisfying refs: every probe ID maps to a specific `pytest tests/test_*.py::test_<name> -x` invocation that runs in the owning plan's GREEN phase.

This is functionally equivalent to a separate Wave 0 stub-test plan but avoids duplicating the test names in two places (a Wave 0 stub plan + the TDD plan that fills them in).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-cov 5.x |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options]` (no separate pytest.ini) |
| **Quick run command** | `uv run pytest tests/test_schemas.py tests/test_loader.py -x` |
| **Full suite command** | `uv run pytest --cov=analysts --cov=watchlist --cov=cli --cov-fail-under=90` |
| **Estimated runtime** | ~5 seconds (full suite incl. CLI integration); ~2 seconds (quick run) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_schemas.py tests/test_loader.py -x` (Wave 1+2 fast tests)
- **After every plan wave:** Run `uv run pytest -x` (full suite incl. CLI integration)
- **Before `/gmd:verify-work`:** Full suite + coverage gate must be green: `uv run pytest --cov=analysts --cov=watchlist --cov=cli --cov-fail-under=90`
- **Max feedback latency:** 10 seconds (full suite cap)

---

## Per-Task Verification Map

All 21 probes are automated unit/integration tests — zero manual-only. The `❌ W0` markers in the "File Exists" column indicate the test file is created by the owning plan's TDD Red phase (see "Wave 0 Model" above) — not a separate Wave 0 stub plan.

| Probe ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|----------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-W1-01 | Schemas | 1 | WATCH-04 | unit | `uv run pytest tests/test_schemas.py::test_long_term_lens_enum -x` | ❌ W0 | ⬜ pending |
| 1-W1-02 | Schemas | 1 | WATCH-04 | unit | `uv run pytest tests/test_schemas.py::test_support_below_resistance -x` | ❌ W0 | ⬜ pending |
| 1-W1-03 | Schemas | 1 | WATCH-04 | unit | `uv run pytest tests/test_schemas.py::test_target_multiples_positive -x` | ❌ W0 | ⬜ pending |
| 1-W1-04 | Schemas | 1 | WATCH-04 | unit | `uv run pytest tests/test_schemas.py::test_notes_max_length -x` | ❌ W0 | ⬜ pending |
| 1-W1-05 | Schemas | 1 | WATCH-05 | unit | `uv run pytest tests/test_schemas.py::test_thesis_price_negative_rejected -x` | ❌ W0 | ⬜ pending |
| 1-W1-06 | Schemas | 1 | WATCH-05 | unit | `uv run pytest tests/test_schemas.py::test_support_equals_resistance_rejected -x` | ❌ W0 | ⬜ pending |
| 1-W1-07 | Schemas | 1 | WATCH-05 | unit | `uv run pytest tests/test_schemas.py::test_watchlist_key_mismatch -x` | ❌ W0 | ⬜ pending |
| 1-W1-08 | Schemas | 1 | WATCH-04 | unit | `uv run pytest tests/test_schemas.py::test_ticker_normalization -x` | ❌ W0 | ⬜ pending |
| 1-W2-01 | Loader | 2 | WATCH-01 | unit | `uv run pytest tests/test_loader.py::test_load_30_ticker_watchlist -x` | ❌ W0 | ⬜ pending |
| 1-W2-02 | Loader | 2 | WATCH-01 | unit | `uv run pytest tests/test_loader.py::test_load_50_tickers_under_100ms -x` | ❌ W0 | ⬜ pending |
| 1-W2-03 | Loader | 2 | WATCH-02 | unit | `uv run pytest tests/test_loader.py::test_atomic_save_no_partial -x` | ❌ W0 | ⬜ pending |
| 1-W2-04 | Loader | 2 | WATCH-05 | unit | `uv run pytest tests/test_loader.py::test_malformed_json_raises -x` | ❌ W0 | ⬜ pending |
| 1-W2-05 | Loader | 2 | WATCH-05 | unit | `uv run pytest tests/test_loader.py::test_round_trip_byte_identical -x` | ❌ W0 | ⬜ pending |
| 1-W3-01 | CLI Add | 3 | WATCH-02 | integration | `uv run pytest tests/test_cli_add.py::test_add_happy_path -x` | ❌ W0 | ⬜ pending |
| 1-W3-02 | CLI Add | 3 | WATCH-02 | integration | `uv run pytest tests/test_cli_add.py::test_add_duplicate_rejected -x` | ❌ W0 | ⬜ pending |
| 1-W3-03 | CLI Add | 3 | WATCH-02 | integration | `uv run pytest tests/test_cli_add.py::test_add_normalizes_case -x` | ❌ W0 | ⬜ pending |
| 1-W3-04 | CLI Add | 3 | WATCH-02 | integration | `uv run pytest tests/test_cli_add.py::test_add_brk_normalizes_to_hyphen -x` | ❌ W0 | ⬜ pending |
| 1-W3-05 | CLI Add | 3 | WATCH-04 | integration | `uv run pytest tests/test_cli_add.py::test_add_all_flags -x` | ❌ W0 | ⬜ pending |
| 1-W3-06 | CLI Remove | 3 | WATCH-03 | integration | `uv run pytest tests/test_cli_remove.py::test_remove_happy_path -x` | ❌ W0 | ⬜ pending |
| 1-W3-07 | CLI Remove | 3 | WATCH-03 | integration | `uv run pytest tests/test_cli_remove.py::test_remove_suggests_close_match -x` | ❌ W0 | ⬜ pending |
| 1-W3-08 | CLI Remove | 3 | WATCH-03 | integration | `uv run pytest tests/test_cli_remove.py::test_remove_no_match_no_suggestion -x` | ❌ W0 | ⬜ pending |
| 1-W3-09 | CLI Errors | 3 | WATCH-05 | unit | `uv run pytest tests/test_cli_errors.py::test_format_validation_error -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Coverage check:** Every requirement (WATCH-01..05) has ≥1 automated probe.
- WATCH-01 (load watchlist 30+ tickers): 2 probes
- WATCH-02 (add ticker via CLI): 6 probes
- WATCH-03 (remove ticker via CLI): 3 probes
- WATCH-04 (per-ticker config fields): 5 probes
- WATCH-05 (Pydantic validation rejection): 7 probes

---

## Wave 0 Requirements

Per the "Wave 0 Model" note above, this phase satisfies Wave 0 via TDD Red commits inside each owning plan. The list below describes WHICH plan creates WHICH file — it is NOT a separate scaffold plan list.

- [x] Plan 01 — `pyproject.toml` (incl. `[project.scripts] markets = "cli.main:main"`, `[build-system]`, `[tool.pytest.ini_options]`, `[tool.coverage.run]`)
- [x] Plan 01 — `tests/__init__.py` (empty, pytest discovery)
- [x] Plan 01 — `tests/conftest.py` (shared fixtures: `empty_watchlist_path`, `seeded_watchlist_path`, `large_watchlist_path` with 35 synthetic tickers for WATCH-01)
- [x] Plan 02 RED — `tests/test_schemas.py` (covers WATCH-04, WATCH-05)
- [x] Plan 03 RED — `tests/test_loader.py` (covers WATCH-01, WATCH-02, WATCH-05)
- [x] Plan 04 RED — `tests/test_cli_add.py` (covers WATCH-02, WATCH-04)
- [x] Plan 04 RED — `tests/test_cli_remove.py` (covers WATCH-03)
- [x] Plan 04 RED — `tests/test_cli_errors.py` (covers `format_validation_error`)
- [x] Plan 05 RED — `tests/test_cli_readonly.py` (covers `list`, `show`)
- [x] Plan 01 — Framework install: `uv add 'pydantic>=2.10'`, `uv add --dev 'pytest>=8.0' 'pytest-cov>=5.0' 'ruff>=0.6'`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|

*All phase behaviors have automated verification.*

The Wave 3 smoke test (`uv run markets add AAPL --lens value && uv run markets list && uv run markets show AAPL && uv run markets remove AAPL`) is convenience-only confirmation — not required for sign-off.

---

## Validation Sign-Off

- [x] All tasks have automated `<verify>` commands or Wave 0 (TDD Red) dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (every test file owned by a plan's TDD Red phase)
- [x] No watch-mode flags (CI-friendly: `-x` for fail-fast, no interactive)
- [x] Feedback latency < 10s for full suite
- [x] `nyquist_compliant: true` set in frontmatter (Wave 0 model: TDD Red commits)

**Approval:** approved (revision 1)
