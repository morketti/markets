# State: Markets

## Project Reference

See: `.planning/PROJECT.md` (last updated 2026-04-30)

**Core value:** Every morning, in one screen — which watchlist tickers need attention today and why, across short-term tactical and long-term strategic horizons.

**Current focus:** Phase 1 in progress — Plan 01 (scaffold) complete; Plan 02 (schemas) is next.

## Current Phase

**Phase:** 01-foundation-watchlist-per-ticker-config
**Status:** In Progress (1 of 5 plans complete)
**Current Plan:** 02 — schemas
**Total Plans in Phase:** 5
**Next:** `/gmd:execute-plan` with `01-02-schemas-PLAN.md`

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

2026-05-01 after Plan 01 (scaffold) execution complete; commits `fb3fad7`, `d3794ce`, `758a2fb`
