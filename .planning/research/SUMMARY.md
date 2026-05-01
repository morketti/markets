# Project Research Summary

**Project:** Markets — Personal Stock Research Dashboard
**Domain:** Personal stock research / decision-support dashboard with keyless data plane and Claude-routine compute
**Researched:** 2026-04-30
**Confidence:** HIGH

## Executive Summary

Markets is a single-user, dual-timeframe stock research dashboard with a "morning command center" framing. Three primary modes: (1) morning scan across a 30–50 ticker watchlist, (2) per-ticker deep-dive, (3) decision-support buy/trim/hold/take-profits recommendation. The architecture is intentionally unconventional: **no API keys** (keyless data via yfinance + SEC EDGAR + RSS; no Anthropic API key — LLM compute runs from the user's Claude subscription via scheduled Claude Code routines), **no LangGraph framework** (Claude routine itself is the orchestrator), and **GitHub-as-database** (daily JSON snapshots committed by the routine; static React frontend reads from `raw.githubusercontent.com`). This eliminates ~$200/month of typical paid-stack cost while preserving ~85–90% of capability.

The recommended approach combines two patterns from analyzed reference repos: (1) **virattt/ai-hedge-fund's two-tier persona/analytical agent split** with deterministic Python scoring before LLM synthesis — adopted for cost, reproducibility, and debuggability; (2) **TauricResearch/TradingAgents' memory-log + reflection pattern** — adopted for endorsement-call performance tracking and historical persona signal trends. We diverge from both reference repos on three things: persona prompts live as markdown files (not Python strings) for iteration, all LLM calls go through Pydantic-validated schemas, and the dual-timeframe (short-term + long-term) per-ticker output schema is a first-class architectural feature absent from both references.

The most material risks are (1) **Claude routine quota burnout mid-batch** — mitigated by token-aware orchestration, persona slate trimming, and lite-mode fallback; (2) **yfinance silent breakage** — mitigated by Pydantic sanity checks and a yahooquery fallback path; (3) **persona prompt drift** — mitigated by markdown versioning, voice-signature anchors, and a regression test set. None of these are blocking; all are addressable with disciplined Phase 4-5 implementation.

## Key Findings

### Recommended Stack

Backend Python 3.12 with `yfinance` + `pandas-ta` (pure-Python — avoids ta-lib's Windows install pain) + `feedparser` + `pydantic v2`. Frontend Vite + React 19 + TypeScript + TailwindCSS, with `lightweight-charts` for OHLC and `recharts` for non-OHLC visuals. Storage is the GitHub repo itself (daily JSON snapshots committed by the routine). Mid-day refresh is a single Vercel Python serverless function. LLM compute is scheduled Claude Code routines (verify availability + quota at implementation; fallback path is GitHub Actions + Anthropic API key if routines aren't on user's plan).

**Core technologies:**
- **Python 3.12 + uv (package manager)** — backend ingestion + analytical agents
- **yfinance + pandas-ta + feedparser** — keyless data plane
- **Pydantic v2** — schema validation across the entire pipeline (raw data, agent signals, LLM responses, frontend reads)
- **Claude Code routines** — scheduled compute orchestrator, no API key
- **Vite + React 19 + TypeScript + Tailwind v4** — static frontend deployable to Vercel
- **lightweight-charts (TradingView)** — best-in-class free finance charts
- **GitHub repo** — versioned database for daily snapshots; readable via `raw.githubusercontent.com`

**Key "what NOT to use":** ta-lib (C dep), LangChain/LangGraph (key-required), Next.js SSR (overkill), Reddit OAuth (use anonymous RSS), MongoDB/Postgres (premature for v1), tweepy/X API (paid).

See `STACK.md` for full version matrix and alternatives analysis.

### Expected Features

**Must have (table stakes — without these the product fails as a research tool):**
- Watchlist with per-ticker config (mode/lens, thesis price, technical levels, target multiples)
- Daily price chart per ticker (OHLC, ≥1y history)
- Multi-source news feed per ticker (Yahoo + Google News + FinViz + press wires + Reddit/StockTwits)
- Fundamental snapshot (P/E, P/S, P/B, ROE, debt/equity, margins)
- Last-updated timestamp + staleness badge
- Dark theme + mobile-responsive layout
- Search/add ticker

**Should have (differentiators — our edge over StockAnalysis/FinViz/Seeking Alpha):**
- **Position-Adjustment Radar** — multi-indicator oversold/overbought consensus across watchlist (the headline morning-scan view)
- **Dual-timeframe per-ticker view** — short-term tactical + long-term strategic side-by-side
- **Persona slate analysis** — Buffett, Munger, Wood, Burry, Lynch + Open Claude Analyst (unlensed)
- **Endorsement-call performance tracking** — newsletters/services as first-class signal with corp-action-aware math
- **Decision-support synthesis** — buy/trim/hold/take-profits per ticker with conviction band, drivers, dissenting persona view
- **Per-ticker config-driven analysis weighting** — user controls lens, no other tool gives this granularity

**Defer (v2+):**
- Push notifications / alerts
- Endorsement performance — defer corp-action-correct math to v1.x
- Sector / peer comparison views
- Migration to Supabase (only when GitHub-as-DB hurts)

**Hard anti-features (do NOT build):** Trade execution, brokerage integration, real-time tick data, paper trading, social/leaderboards, multi-user, native mobile apps, AI chat. See FEATURES.md for full rationale.

### Architecture Approach

A scheduled Claude Code routine fires at 6am ET on weekdays, runs a Python ingestion script (deterministic data fetching + analytical scoring), then walks Claude through each persona's markdown prompt for each ticker, then through a synthesizer prompt that produces the per-ticker `TickerDecision` (dual-timeframe + recommendation). Output JSONs are committed to the GitHub repo. The static React frontend reads from `raw.githubusercontent.com`; opening a ticker triggers an on-open Vercel serverless function refresh for current price + recent headlines (no LLM, ~50 lines).

**Major components:**
1. **`ingestion/` (Python)** — keyless data fetchers: yfinance (prices/fundamentals), SEC EDGAR (filings), RSS (news), Reddit RSS / StockTwits (social)
2. **`analysts/` (Python)** — deterministic scoring agents: fundamentals, technicals, news/sentiment, position-adjustment, valuation
3. **`prompts/personas/*.md`** — markdown persona prompts (Buffett, Munger, Wood, Burry, Lynch, Open Claude Analyst) loaded at runtime
4. **`prompts/synthesizer.md`** — final decision prompt
5. **`routine/`** — Claude Code routine config + entrypoint orchestration script
6. **`frontend/`** — static React + Vite app on Vercel, reads JSON from GitHub raw
7. **`api/refresh.py`** — Vercel Python serverless function for on-open refresh (keyless yfinance + RSS, no LLM)
8. **`data/` + `memory/`** — daily snapshots and append-only logs for historical signals + endorsements

The `AgentState` TypedDict carries run-scoped state through every agent (adapted from virattt's pattern, expanded with `watchlist_metadata`, `historical_signals`, `endorsements`, dual-timeframe `TickerDecision`). See ARCHITECTURE.md for the concrete schema and three data-flow narratives (morning batch / deep-dive / decision support).

### Critical Pitfalls

The 5 most material risks (full list of 13 in PITFALLS.md):

1. **Claude routine quota burnout mid-batch** — Snapshot becomes partial when subscription quota hits. **Avoid by:** prioritized watchlist ordering (most-likely-to-need-fresh first), trimming personas for fair-state no-news tickers, lite-mode fallback (analyticals only), per-ticker token-cost estimation up-front, `_status.json` emission so frontend surfaces partial-snapshot state.

2. **yfinance silent breakage** — Yahoo changes a layout; yfinance returns empty/wrong data; snapshot looks valid but is wrong. **Avoid by:** pinned versions, Pydantic sanity checks on every fetch, `data_unavailable: true` flag when checks fail, yahooquery fallback path for prices.

3. **LLM output schema drift on model upgrades** — Claude is upgraded; persona JSON shapes shift; synthesizer chokes. **Avoid by:** Pydantic-validate every LLM response with `default_factory` fallback to `(neutral, 0, "schema_failure")`; pin model version where possible; log raw failures to `memory/llm_failures.jsonl`.

4. **Persona prompt drift** — Iteration toward "clarity" pushes prompts toward generic; persona slate's value collapses. **Avoid by:** version persona prompts in git, voice-signature anchor at prompt top, periodic regression test (fixed AAPL data → all 6 personas → diff outputs).

5. **Position-adjustment indicator false positives in trending markets** — RSI says "oversold" in an uptrend; user trims; trend resumes. **Avoid by:** multi-indicator consensus (already designed), trend-regime gating via ADX, `extreme_oversold/extreme_overbought` tier for strongest UI affordance, recommendation language as "consider" not "do."

## Implications for Roadmap

Based on research, suggested phase structure for **Fine granularity** (8-12 phases × 5-10 plans each, per user config). The product naturally splits into 9 phases for v1, ordered by dependency:

### Phase 1: Foundation — Watchlist + Per-Ticker Config

**Rationale:** Per-ticker config blocks all downstream personalization. Without it, every ticker is analyzed identically.
**Delivers:** `watchlist.json` schema; CRUD utility script; per-ticker config validation (Pydantic models for `TickerConfig`, `BuyRange`, `TechnicalLevels`, `FundamentalTargets`).
**Addresses:** Watchlist requirement; per-ticker analytical control.
**Avoids:** Pitfall #10 (premature abstraction — keep watchlist simple, no plugin system).

### Phase 2: Ingestion — Keyless Data Plane

**Rationale:** All analyticals depend on raw data; ingestion is the foundation.
**Delivers:** `ingestion/prices.py`, `fundamentals.py`, `filings.py` (EDGAR with proper User-Agent), `news_rss.py`, `social.py`. Pydantic schemas. Sanity-check assertions on every fetch.
**Uses:** yfinance, requests + EDGAR User-Agent compliance, feedparser, anonymous Reddit RSS.
**Avoids:** Pitfall #1 (yfinance breakage), Pitfall #2 (EDGAR User-Agent block).

### Phase 3: Analytical Agents — Deterministic Scoring

**Rationale:** All persona LLM agents pass *facts*, not numbers — analyticals must produce facts first.
**Delivers:** `analysts/fundamentals.py`, `technicals.py`, `news_sentiment.py`, `position_adjustment.py`, `valuation.py`. AgentSignal Pydantic schema.
**Implements:** Two-tier agent pattern (deterministic Python scoring layer).
**Avoids:** Pitfall #6 (false positives — multi-indicator consensus + trend-regime gating designed in).

### Phase 4: Position-Adjustment Radar — First Differentiator

**Rationale:** This is the headline morning-scan view; ship it as a standalone deliverable to validate value early.
**Delivers:** `analysts/position_adjustment.py` finalized with extreme tiers; CLI script that runs across watchlist and outputs JSON.
**Addresses:** "Where do I trim, where do I add today" core question.
**Note:** Could merge into Phase 3 if granularity feels too fine; user picked Fine so keep separate.

### Phase 5: Claude Routine Wiring — Persona Slate + Synthesizer

**Rationale:** This is the biggest engineering item; depends on all prior phases.
**Delivers:** `prompts/personas/*.md` (6 files), `prompts/synthesizer.md`, `routine/routine.json`, `routine/entrypoint.py`. Pydantic validation on all LLM responses with `default_factory`. Token-cost logging. Lite-mode fallback.
**Implements:** Two-tier agent pattern (LLM persona layer); synthesizer pattern adapted from virattt's PortfolioManager.
**Avoids:** Pitfall #3 (quota burnout), Pitfall #4 (schema drift), Pitfall #7 (persona drift via voice signatures).

### Phase 6: Frontend MVP — Morning Scan + Deep-Dive

**Rationale:** First user-visible value; deliberately minimal to avoid UI overload.
**Delivers:** Vite + React app; routes for MorningScan (3-lens toggle), TickerDetail (deep-dive). Reads from `raw.githubusercontent.com`. Staleness badge from `_status.json`.
**Uses:** lightweight-charts, Tailwind v4, zod for schema validation.
**Avoids:** Pitfall #8 (UI overload — one lens at a time), Pitfall #9 (stale-data UX — badge as foundational pattern).

### Phase 7: Decision-Support View + Dissent Surface

**Rationale:** Synthesizes everything into the "should I buy X today" view; depends on full persona slate.
**Delivers:** Decision view route; dissent-surfacing UI; conviction band rendering; recommendation language conventions.
**Avoids:** Pitfall #12 (self-confirmation bias — dissent always rendered).

### Phase 8: Mid-Day Refresh + Resilience

**Rationale:** Hybrid freshness (option B from design discussion) requires the on-open layer.
**Delivers:** `api/refresh.py` Vercel function (keyless yfinance + RSS, no LLM). Per-ticker refresh integrated into TickerDetail. Routine quota-aware orchestration finalized. yahooquery fallback path. `_status.json` emission tested under failure modes.
**Avoids:** Pitfall #1 (fallback for yfinance), Pitfall #3 (quota awareness), Pitfall #9 (staleness fully covered).

### Phase 9: Endorsement Layer + Memory Reflection

**Rationale:** Endorsement performance tracking is a v1 differentiator but depends on memory log being populated for ≥30 days. Ship the *capture* in v1, the *performance math* in v1.x.
**Delivers (v1 portion):** `endorsements.jsonl` capture mechanism in routine; manual entry tool (CLI script + frontend form). `memory/historical_signals.jsonl` write path. Decision view shows recent endorsements per ticker (no performance number yet).
**Defers (v1.x):** Corp-action-aware performance math; UI for "this newsletter is up 12%."
**Avoids:** Pitfall #5 (corp-action math complexity — defer the math, not the capture).

### Phase Ordering Rationale

- **Foundation → Data → Logic → LLM → UI** maps the natural dependency graph
- **Position-adjustment ships standalone (Phase 4)** so user gets a tangible "morning radar" deliverable before the full routine is wired
- **Decision-support split from frontend MVP (Phases 6 + 7)** because dissent surfacing requires the full persona slate to be running first
- **Resilience phase (8) lands after full pipeline is working** — premature resilience work is wasted effort
- **Endorsement layer last (9)** because it's the most complex and only differentiates if user feeds endorsements regularly

### Research Flags

Phases likely needing deeper per-phase research during planning:

- **Phase 5 (Claude Routine Wiring):** Verify current Claude Code routine constraints — quota allocation, output format expectations, retry behavior, observability. May need to adjust orchestration based on actual routine API.
- **Phase 8 (Resilience):** Vercel Python serverless function cold-start timing under real load; yfinance fallback strategy may need adjustment based on yahooquery's current state (also-scrapes-Yahoo means same upstream breakage hits both).
- **Phase 9 (Endorsement Math, in v1.x):** Specific corp-action handling for the user's actual endorsements — research only when user has 30+ days of endorsement entries to test against.

Phases with standard patterns (skip per-phase research, plan directly):

- **Phase 1 (Watchlist):** Trivial JSON CRUD; no domain research needed.
- **Phase 2 (Ingestion):** Patterns well-documented from reference repos and library docs.
- **Phase 3 + 4 (Analyticals):** Standard technical-analysis indicator patterns; pandas-ta has examples for all of them.
- **Phase 6 (Frontend MVP):** Standard React + Vite patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All libraries are widely-used; uncertainty only on Claude routine specifics — verify at Phase 5 implementation |
| Features | HIGH | Validated against three competitor products; differentiators clearly map to PROJECT.md decisions |
| Architecture | MEDIUM-HIGH | Core patterns adopted from working reference repos; the keyless + Claude-routine variant is novel and unproven at scale (but at user's scale, low risk) |
| Pitfalls | HIGH | Most pitfalls grounded in known reference-repo bugs, library-history breakage, or finance-domain experience |

**Overall confidence:** HIGH for the v1 path; MEDIUM specifically on Claude routine quota behavior under our load (only resolvable empirically once Phase 5 ships).

### Gaps to Address

- **Claude Code routine API surface** — Need current docs at Phase 5 implementation: cron syntax, prompt-vs-script invocation, environment variable injection (for git push token), output streaming, error/retry behavior, quota visibility.
- **yfinance current breakage state** — Pin a specific version after testing against current Yahoo layout at Phase 2 implementation.
- **Vercel Python serverless cold-start timing** — Test against real ticker fetch + RSS parse path to confirm < 10s timeout headroom, especially for the first request after cold start.
- **User's actual endorsement sources** — The endorsement layer's value depends entirely on which newsletters/services the user actually subscribes to. Research that specifically when Phase 9 starts.

## Sources

### Primary (HIGH confidence)
- Reference repo `virattt/ai-hedge-fund` (cloned to `~/projects/reference/ai-hedge-fund/`) — agent state, two-tier split, persona pattern, synthesizer pattern; provenance noted in adopted code
- Reference repo `TauricResearch/TradingAgents` (cloned to `~/projects/reference/TradingAgents/`) — memory-log + reflection pattern, yfinance use, JSON state persistence
- yfinance, pandas-ta, feedparser, Pydantic — official documentation and PyPI version histories
- SEC EDGAR developer documentation — User-Agent rules, rate limits

### Secondary (MEDIUM confidence)
- Anthropic Claude Code routines — feature availability/quota verified at implementation time
- Vercel Python serverless documentation — runtime constraints
- Competitor products (StockAnalysis.com, FinViz, Seeking Alpha) — feature analysis from general product knowledge

### Tertiary (LOW confidence)
- 2026 library version specifics — verify at implementation against current PyPI/npm
- Claude routine quota allocation under our load — purely empirical; unverifiable without running

---
*Research completed: 2026-04-30*
*Ready for roadmap: yes*
