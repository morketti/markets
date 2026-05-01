---
gmd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_plan: 02-02-prices-fundamentals
status: in_progress
last_updated: "2026-05-01T08:13:00Z"
progress:
  total_phases: 9
  completed_phases: 1
  total_plans: 11
  completed_plans: 6
---

# State: Markets

## Project Reference

See: `.planning/PROJECT.md` (last updated 2026-04-30)

**Core value:** Every morning, in one screen — which watchlist tickers need attention today and why, across short-term tactical and long-term strategic horizons.

**Current focus:** Phase 2 Wave 1 complete. Plan 02-01 (foundation) shipped — shared HTTP session + ingestion exception hierarchy + 5 Pydantic data schemas. Ready to start Wave 2 (Plans 02-02..02-05 can run in parallel).

## Current Phase

**Phase:** 02-ingestion-keyless-data-plane
**Status:** In progress (1/6 plans complete)
**Current Plan:** 02-02-prices-fundamentals (next)
**Total Plans in Phase:** 6
**Next:** Run Plan 02-02 (yfinance + yahooquery prices/fundamentals). Plans 02-02..02-05 are independent and can run in parallel; Plan 02-06 (refresh orchestrator) gates on all four.

## Phase Status

| # | Phase | Status |
|---|-------|--------|
| 1 | Foundation — Watchlist + Per-Ticker Config | Complete (5/5 plans) — pending verify |
| 2 | Ingestion — Keyless Data Plane | In progress (1/6 plans — Wave 1 done) |
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
- **2026-05-01 (Phase 1 / Plan 04 — CLI core)**: argparse dispatcher + add/remove + format_validation_error shipped. `cli/main.py` (71 lines), `cli/_errors.py` (38), `cli/add_ticker.py` (102), `cli/remove_ticker.py` (73) — 284 production lines total. **Decision:** SUBCOMMANDS dict-of-tuples pattern in `cli/main.py` is Plan 05's documented extension surface (4-line patch: 2 imports + 2 dict entries; zero modifications to existing lines). **Decision:** `cli/remove_ticker.py` imports `normalize_ticker` from `analysts.schemas` (zero inline regex; closes Plan 02's deferred decision). **Decision:** ISO 8601 timestamps stick with `+00:00` form (NOT `Z`) per Pitfall #3 — round-trips natively through `datetime.fromisoformat`. **Decision:** Optional groups (TechnicalLevels, FundamentalTargets) constructed only when at least one of their flags is passed (no `null` clutter in watchlist.json). **Decision:** ValidationError caught in main() → format_validation_error → stderr → exit 2 (no raw tracebacks); FileNotFoundError → stderr → exit 1; other exceptions propagate (debug-friendly). 9/9 CLI tests green (probes 1-W3-01..09); combined Wave 1+2+3 24/24 green; coverage 85.62% on the four cli/* files (gate ≥85%). BRK.B → BRK-B verified end-to-end via `test_add_brk_normalizes_to_hyphen` AND smoke test. ValidationError surfaces cleanly via smoke test (`markets add AAPL --thesis -1` → `validation failed (1 error): - thesis_price: ... (got: -1.0)` exit 2, no file created). Plan-level commits: `4a3ae49` (RED), `0446715` (GREEN). WATCH-02, WATCH-03, WATCH-04, WATCH-05 confirmed covered. **Zero deviations** from plan.
- **2026-05-01 (Phase 1 / Plan 05 — CLI readonly + example)**: Read-only CLI surface shipped. `cli/list_watchlist.py` (45 lines) + `cli/show_ticker.py` (83 lines) + `watchlist.example.json` (5 tickers, 4 lenses, BRK-B hyphenated) + `README.md` (88 lines, quick-start + schema table + provenance). **Decision (locked):** `cli/_errors.py:suggest_ticker(unknown, known)` is the single source of truth for did-you-mean across show + remove — closes Plan 04's deferred decision. Plan 04's remove tests stay green with no test changes (refactor is internal). **Decision (locked):** `cli/show_ticker.py` imports `normalize_ticker` from `analysts.schemas` — same pattern as Plan 04 remove. **Decision:** `markets list` empty watchlist exits 0 (mirrors loader contract); show error codes mirror remove (0/1/2). **Decision:** Notes column truncated at 40 chars in list output. **Decision:** `watchlist.example.json` generated via dogfooded `markets add` (not hand-crafted) — exercises full add → schema → loader → save pipeline. WATCH-01 user-facing demo proven (`test_list_30_plus_tickers` over 35-ticker fixture); WATCH-03 ergonomics extended to show (`markets show AAPK` → did-you-mean AAPL). 33/33 Phase 1 tests pass; coverage 94% global, 100% list_watchlist.py, 98% show_ticker.py — well above the ≥90% gate. Plan-level commits: `6f555d3` (RED), `ba679ce` (GREEN). **Zero deviations** from plan (3 extra coverage tests added to clear the gate are documented in SUMMARY).
- **2026-05-01 (Phase 2 / Plan 01 — foundation)**: Wave 1 ingestion foundation shipped. `ingestion/http.py` (76 lines) provides `get_session()` returning a process-shared `requests.Session` with EDGAR-compliant `User-Agent` (env-overridable via `MARKETS_USER_AGENT`), `HTTPAdapter` mounted with `Retry(total=3, backoff_factor=0.3, status_forcelist=[429,500,502,503,504], allowed_methods={GET,HEAD}, raise_on_status=False)`, `DEFAULT_TIMEOUT=10.0` constant, and `polite_sleep(source, last_call, min_interval)` helper. `ingestion/errors.py` ships the 3-class hierarchy (`IngestionError` → `NetworkError`, `SchemaDriftError`). `analysts/data/` sub-package ships eight Pydantic schemas (`PriceSnapshot`, `OHLCBar`, `FundamentalsSnapshot`, `FilingMetadata`, `Headline`, `RedditPost`, `StockTwitsPost`, `SocialSignal`) — every one delegates ticker normalization to `analysts.schemas.normalize_ticker` (no regex duplication) and uses `ConfigDict(extra="forbid")`. `pyproject.toml` extended with 5 runtime deps (yfinance/yahooquery/requests/feedparser/beautifulsoup4) + 1 dev dep (responses); `ingestion` registered in hatch packages and coverage source. **Decision:** `raise_on_status=False` on Retry — callers see the final response (status + body) when retries exhaust on 5xx so the Plan 02-06 orchestrator can branch on response type rather than catching `MaxRetryError`. **Decision:** `polite_sleep` is caller-owned-state (no module singletons that would bleed between tests). **Decision:** Fundamentals carry NO positivity constraint at the schema layer — FCF/ROE can be negative legitimately; downstream sanity checks enforce ranges. **Decision:** `Headline.url` is plain `str` (not HttpUrl) — Yahoo redirect URLs sometimes fail strict checks. **Decision:** `FilingMetadata.form_type` Literal includes `"OTHER"` escape-hatch for unknown EDGAR forms. 34/34 Phase 2 W1 tests green (9 http + 2 errors + 23 schemas; full suite 69/69). Coverage: errors.py 100%/100%, http.py 97%/91%, analysts/data/* 100%/100%. Plan-level commits: `0ffcabf` (chore scaffold), `b370d9c` (RED tests), `b58f932` (GREEN http impl), `b206206` (RED schemas), `777ff28` (GREEN schemas). **Deviations:** 4 auto-fixed (1 Rule 1 bug — `raise_on_status=False`; 2 Rule 2 missing-critical — added `test_schemas_reject_non_string_ticker` for branch coverage + 4 extra schema tests beyond the planned ~16; 1 Rule 3 blocking — observed `uv.lock` is gitignored and skipped from staging). All tightening, no scope creep. DATA-06 marked complete in REQUIREMENTS.md.

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

2026-05-01 after Phase 2 / Plan 01 (foundation) execution complete; commits `0ffcabf` (scaffold), `b370d9c` (RED http+errors), `b58f932` (GREEN http), `b206206` (RED schemas), `777ff28` (GREEN schemas). Phase 2 progress: 1/6 plans complete (Wave 1 done). Next: Wave 2 — Plans 02-02..02-05 can run in parallel (prices/fundamentals, EDGAR filings, news/RSS, social). Plan 02-06 (refresh orchestrator) gates on all four.
