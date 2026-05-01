---
phase: 1
slug: foundation-watchlist-per-ticker-config
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-30
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from `01-RESEARCH.md` § Validation Architecture.

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

All 21 probes are automated unit/integration tests — zero manual-only. Test files are Wave 0 gaps; see "Wave 0 Requirements" below.

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

All test files are gaps; the project is bare except for `.planning/` and `.git`. The Wave 0 (scaffold) plan must create:

- [ ] `pyproject.toml` — including `[project.scripts] markets = "cli.main:main"`, `[build-system]`, `[tool.pytest.ini_options]`, `[tool.coverage.run]`
- [ ] `tests/__init__.py` — empty (pytest discovery)
- [ ] `tests/conftest.py` — shared fixtures: `empty_watchlist_path`, `seeded_watchlist_path`, `large_watchlist_path` (35 synthetic tickers for WATCH-01 30+ ticker probe)
- [ ] `tests/test_schemas.py` — covers WATCH-04, WATCH-05 (schema-level rules)
- [ ] `tests/test_loader.py` — covers WATCH-01, WATCH-02, WATCH-05 (file I/O + round-trip + atomic save)
- [ ] `tests/test_cli_add.py` — covers WATCH-02, WATCH-04 (add CLI happy paths + cross-field flag exercise)
- [ ] `tests/test_cli_remove.py` — covers WATCH-03 (remove CLI happy paths + suggestion logic)
- [ ] `tests/test_cli_readonly.py` — covers `list`, `show` subcommands (Claude's discretion, low-cost QoL)
- [ ] `tests/test_cli_errors.py` — covers `format_validation_error`
- [ ] Framework install: `uv add 'pydantic>=2.10'`, `uv add --dev 'pytest>=8.0' 'pytest-cov>=5.0' 'ruff>=0.6'`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|

*All phase behaviors have automated verification.*

The Wave 3 smoke test (`uv run markets add AAPL --lens value && uv run markets list && uv run markets show AAPL && uv run markets remove AAPL`) is convenience-only confirmation — not required for sign-off.

---

## Validation Sign-Off

- [ ] All tasks have automated `<verify>` commands or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (8 test files + pyproject.toml)
- [ ] No watch-mode flags (CI-friendly: `-x` for fail-fast, no interactive)
- [ ] Feedback latency < 10s for full suite
- [ ] `nyquist_compliant: true` set in frontmatter once Wave 0 is verified scaffold-complete

**Approval:** pending
