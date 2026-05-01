---
gmd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_plan: 4
status: executing
last_updated: "2026-05-01T04:09:21.678Z"
progress:
  total_phases: 9
  completed_phases: 0
  total_plans: 5
  completed_plans: 3
---

# State: Markets

## Project Reference

See: `.planning/PROJECT.md` (last updated 2026-04-30)

**Core value:** Every morning, in one screen — which watchlist tickers need attention today and why, across short-term tactical and long-term strategic horizons.

**Current focus:** Phase 1 in progress — Plans 01 (scaffold), 02 (schemas), and 03 (loader) complete; Plan 04 (CLI core) is next.

## Current Phase

**Phase:** 01-foundation-watchlist-per-ticker-config
**Status:** In Progress (3 of 5 plans complete)
**Current Plan:** 04 — CLI core (add/remove)
**Total Plans in Phase:** 5
**Next:** `/gmd:execute-plan` with `01-04-cli-core-PLAN.md`

## Phase Status

| # | Phase | Status |
|---|-------|--------|
| 1 | Foundation — Watchlist + Per-Ticker Config | In Progress |
| 2 | Ingestion — Keyless Data Plane | Pending |
| 3 | Analytical Agents — Deterministic Scoring | Pending |
| 4 | Position-Adjustment Radar | Pending |
| 5 | Claude Routine Wiring — Persona Slate + Synthesizer | Pending |
| 6 | Frontend MVP — Morning Scan + Deep-Dive | Pending |
| 7 | Decision-Support View + Dissent Surface | Pending |
| 8 | Mid-Day Refresh + Resilience | Pending |
| 9 | Endorsement Capture | Pending |

## Recent Decisions

- **2026-04-29 / 2026-04-30**: Project initialized via `/gmd:new-project`. Architecture locked through brainstorming flow (PROJECT.md captures all locked decisions).
- **2026-04-30**: Reference projects studied — `virattt/ai-hedge-fund` (cloned to `~/projects/reference/ai-hedge-fund/`) and `TauricResearch/TradingAgents` (cloned to `~/projects/reference/TradingAgents/`). Patterns adopted: agent state TypedDict, two-tier persona/analytical split, deterministic scoring before LLM, synthesizer with deterministic pre-filter, memory log + reflection. Patterns rejected: hardcoded Python prompts (we use markdown), trade-execution focus (we surface recommendations only), API-key data plane (we use keyless), LangGraph framework (incompatible with keyless).
- **2026-04-30**: Configuration locked — YOLO mode, Fine granularity, parallel execution, Quality model profile (Opus for research/roadmap, Sonnet for synthesis), all workflow agents enabled (Research / Plan-Check / Verifier).
- **2026-04-30**: Research completed inline (parallel research-agent spawns hit Opus quota; agents resumable at 3:50pm Chicago via SendMessage to agent IDs `ad9c4b82904461fce`, `a78c5f332fe5fa097`, `a14f95a61bb93489b` if cross-check desired). Five research docs produced: STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md, SUMMARY.md.
- **2026-05-01 (Phase 1 / Plan 01 — scaffold)**: uv-managed Python project bootstrapped. Pydantic 2.13.3, pytest 9.0.3, pytest-cov 7.1.0, ruff 0.15.12 installed. Three importable packages (analysts/, watchlist/, cli/) created. `markets` console script wired end-to-end (verified). `tests/conftest.py` exposes empty/seeded/large watchlist fixtures with lazy schema imports. Pytest framework wired (collect-only exits 5, no ImportError). Plan-level commits: `fb3fad7`, `d3794ce`, `758a2fb`. Five WATCH-0* requirements marked complete in REQUIREMENTS.md.
- **2026-05-01 (deviations during Plan 01)**: (1) `uv` not installed on host — installed via `python -m pip install --user uv` to `C:/Users/Mohan/AppData/Roaming/Python/Python314/Scripts/`. (2) `uv run markets` failed after Task 2 with `ModuleNotFoundError: No module named 'cli'` — initial wheel was built before package directories existed; fixed with `uv sync --reinstall-package markets`. Both Rule 3 (blocking environmental) auto-fixes — no design changes.
- **2026-05-01 (Phase 1 / Plan 02 — schemas)**: Pydantic v2 schemas locked. `analysts/schemas.py` (171 lines) ships `TechnicalLevels`, `FundamentalTargets`, `TickerConfig`, `Watchlist` + module-level `normalize_ticker(s)` helper. 8/8 schema tests green; coverage 99% line / 98.89% branch (gate ≥95%). Hyphen-form normalization verified (BRK.B/BRK_B/BRK/B/brk-b → BRK-B). All cross-field rules use `@model_validator(mode='after')`. **Decision:** `normalize_ticker` extracted to module level (single source of truth) — Plans 04/05 will `from analysts.schemas import normalize_ticker` and reuse directly, no duplication. **Decision:** Strict watchlist key mode — dict-key/value.ticker mismatch raises `ValidationError` naming the offender, never silently rewrites. WATCH-04 + WATCH-05 covered (already marked `[x]` in REQUIREMENTS.md from Plan 01 over-attribution; behavior now actually delivered). Plan-level commits: `66795a2` (RED test), `87aaa4e` (GREEN impl). Zero deviations from plan.
- **2026-05-01 (Phase 1 / Plan 03 — loader)**: Stdlib atomic-write loader landed. `watchlist/loader.py` (69 lines) ships `load_watchlist(path)` + `save_watchlist(wl, path)` + `DEFAULT_PATH`. **Decision:** stdlib `json.dumps(model_dump(mode="json"), indent=2, sort_keys=True) + "\n"` for serialization (NOT `model_dump_json`) per CONTEXT.md correction #3 / Pydantic v2 issue #7424 — guarantees byte-identical round-trip and stable git diffs. **Decision:** `tempfile.NamedTemporaryFile(delete=False, dir=parent) ... with-block-exit ... os.replace(tmp_path, path)` per Pitfall #2 (Windows file-lock release); on OSError, `tmp_path.unlink(missing_ok=True)` then re-raise. **Decision:** `load_watchlist` on missing path returns empty `Watchlist()` (not an error) — drives first-run CLI UX. **Decision:** save_watchlist re-validates the model before persistence (defense-in-depth). 7/7 loader tests green (15/15 combined with schemas); coverage 100% line+branch (gate ≥90%); 50-ticker load measured 6.18ms (<<100ms gate); round-trip byte-identical confirmed; no orphan tmp files in any test path. **Deviation (Rule 2):** Added 7th test `test_save_cleanup_on_replace_failure` (monkeypatched `os.replace` raises OSError → asserts cleanup + re-raise) to lock the failure-cleanup contract and close the coverage gap on lines 67-69 (originally-specified 6 tests came in at 88.89% coverage). No implementation deviation from `01-RESEARCH.md` "Loader / atomic save" example. Plan-level commits: `7c1bf15` (RED), `e40f0eb` (GREEN). WATCH-01, WATCH-02, WATCH-05 confirmed covered.

## Context Notes

- **All ingestion is keyless**: yfinance + SEC EDGAR (User-Agent only) + RSS feeds + Reddit RSS + StockTwits unauthenticated trending
- **LLM compute**: runs from user's Claude subscription via scheduled Claude Code routines — no Anthropic API key
- **Storage**: GitHub repo itself — daily JSON snapshots at `data/YYYY-MM-DD/TICKER.json` plus `_index.json` and `_status.json`
- **Frontend reads**: directly from `raw.githubusercontent.com` (no backend server)
- **Mid-day refresh**: single Vercel Python serverless function (keyless, no LLM)
- **Provenance discipline**: every reference-adapted file carries a header comment naming source file and modifications
- **Outputs**: dual-timeframe per ticker (short_term + long_term) with per-persona signals, position-adjustment state, and synthesizer-produced recommendation
- **Persona slate**: Buffett, Munger, Wood, Burry, Lynch, Open Claude Analyst (all markdown prompts in `prompts/personas/`)

## Open Items / Research Flags

- **Phase 5 implementation:** Verify current Claude Code routine constraints (cron syntax, output format, quota visibility, env-var injection for git push token, retry behavior)
- **Phase 2 implementation:** Verify yfinance current breakage state; pin known-good version
- **Phase 8 implementation:** Verify Vercel Python serverless cold-start timing under realistic ticker fetch + RSS parse path
- **v1.x (Phase 9 successor):** Endorsement performance math depends on user's actual newsletter sources — research at v1.x kickoff

## Open Items — Environmental

- **`uv` PATH:** `uv.exe` is at `C:/Users/Mohan/AppData/Roaming/Python/Python314/Scripts/`. This is currently NOT on the user PATH (bash or PowerShell). Each subsequent plan that runs `uv` commands must either prepend that directory to PATH per-command, or the user can permanently add it to PATH (recommended). Alternative: `pipx install uv`.
- **Hatchling editable-install gotcha confirmed:** When a plan creates a new top-level package listed in `[tool.hatch.build.targets.wheel] packages`, follow with `uv sync --reinstall-package markets` so the editable wheel is rebuilt to include it. (Plan 01 Task 2 hit this.)

## Last Touched

2026-05-01 after Plan 03 (loader) execution complete; commits `7c1bf15` (RED), `e40f0eb` (GREEN). Next: Plan 04 (CLI core — add/remove).
