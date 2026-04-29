# Markets — Personal Stock Research Dashboard

## What This Is

A personal, single-user web app — the user's "morning command center" for stock research and position-adjustment decisions. Combines newsbase ingestion, multi-persona AI analysis, technical/fundamental signals, and per-ticker buy-range logic across a watchlist (~30–50 names) plus deep-dive on any ticker. Research and decision-support only — not a trading system.

## Core Value

Every morning, in one screen: which watchlist tickers need attention today and why — across short-term tactical (overbought/oversold, catalysts) and long-term strategic (thesis status, valuation) horizons.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Morning-scan view with three lenses: position-adjustment (oversold/overbought), short-term opportunities, long-term thesis status
- [ ] Per-ticker deep-dive page with dual-timeframe signals side-by-side (short-term + long-term)
- [ ] Decision-support view: per-ticker buy/trim/hold/take-profits with conviction band, drivers, and "off-script" Claude observation
- [ ] Watchlist CRUD with per-ticker config: short-term focus toggle, long-term lens (value/growth/contrarian/mixed), thesis price, technical levels (support/resistance), target multiples
- [ ] Newsbase ingestion: SEC EDGAR filings (10-K/Q, 8-K, Form 4), RSS aggregation (Yahoo, MarketWatch, Google News, FinViz, press wires), Reddit RSS, StockTwits unauthenticated trending
- [ ] Persona-based long-term analysis: Buffett, Munger, Wood, Burry, Lynch + Open Claude Analyst (unboxed)
- [ ] Position Adjustment Analyzer — multi-indicator consensus (RSI, Bollinger Bands, z-score vs 50-day MA, Stochastic, Williams %R, MACD divergence)
- [ ] Endorsement tracking — newsletter/service calls as first-class signal, with source + date + price-at-endorsement vs current price
- [ ] Scheduled morning batch via Claude Code routine (weekday mornings, ~6am ET)
- [ ] Mid-day on-open refresh — lightweight serverless function for prices + recent news only (no LLM)
- [ ] Dark-theme React frontend, mobile-responsive
- [ ] Daily JSON snapshots committed to GitHub repo (per-ticker, per-date) — frontend reads from `raw.githubusercontent.com`

### Out of Scope

- Brokerage integration / position tracking — research tool, not a trading system
- Trade execution — out of scope by definition
- Alerts/notifications (push/email/SMS) — defer to v2
- Real-time intraday tick data — yfinance 15-20min delay sufficient for personal research
- Twitter/X social signal — paid-only since 2023; covered by Reddit + StockTwits proxy
- Premium media full-text (Bloomberg/WSJ/Reuters) — RSS headlines + click-through to existing user subs is sufficient
- Multi-user / auth — single-user, private deploy
- LangGraph framework — keyless constraint forecloses it (requires API keys)
- Paid market-data APIs (Alpha Vantage / Finnhub / Polygon) — keyless v1; revisit only with evidence after 60 days
- Native mobile apps — responsive web only

## Context

**User profile.** Active personal investor managing a ~30–50 name watchlist they "constantly follow," interested in both swing-trade tactical adjustments and long-term thesis tracking. Wants Claude's general financial reasoning surfaced *alongside* canonical-investor personas, not replaced by them.

**Reference projects studied.** Two AI-driven trading-agent systems were analyzed before design lock:
- `virattt/ai-hedge-fund` (cloned to `~/projects/reference/ai-hedge-fund/`) — adopted: AgentState shape, two-tier persona/analytical split, deterministic Python scoring before LLM, Pydantic-typed signal output (`signal/confidence/reasoning`), Portfolio Manager synthesizer pattern with deterministic constraint pre-computation.
- `TauricResearch/TradingAgents` (cloned to `~/projects/reference/TradingAgents/`) — adopted: memory-log + reflection pattern (for endorsement performance tracking and historical persona signal trends), Quick + Deep LLM tier split, yfinance for keyless price/fundamentals, JSON state persistence per run.

Diverged from: hardcoded Python prompts (we use markdown files), trade-decision focus (we surface buy/trim/hold recommendations not orders), API-key data layer (we use keyless), stateless ticker passing (we have persistent watchlist + per-ticker config), LangGraph framework (Claude Code routine is the orchestrator).

**Provenance discipline.** Every file adapted from reference repos carries a header comment naming the source file and what was modified — `# Pattern adapted from virattt/ai-hedge-fund/src/agents/warren_buffett.py — modified for keyless data layer and watchlist-mode operation.`

**Freshness model.** Hybrid (option B from design discussion): overnight batch generates the morning scan; opening a ticker's deep-dive triggers a foreground price+news refresh (cheap endpoints only, no LLM); LLM summaries stay batch unless user clicks "re-summarize."

## Constraints

- **Compute model**: Scheduled Claude Code routine runs the morning batch — no separate Anthropic API key, runs from user's Claude subscription quota. Why: zero ongoing API bill; user already has the subscription.
- **Backend stack**: Python — Why: pandas + yfinance + ta-lib + pydantic for data work; Claude Code orchestration is language-agnostic but Python is the natural fit for finance libraries.
- **Frontend stack**: React, dark theme, mobile-responsive — Why: user spec; static deploy on Vercel reads from GitHub raw URLs.
- **Data plane — fully keyless**: yfinance (prices, fundamentals, options, analyst snapshot), SEC EDGAR (User-Agent only — filings, insider Form 4), RSS feeds (Yahoo, MarketWatch, Google News per-ticker, FinViz, PRNewswire, BusinessWire), Reddit RSS (per-ticker search + r/wallstreetbets), StockTwits unauthenticated trending. Why: zero account/key management; ~85–90% capability of paid stack at $0/month.
- **Storage**: GitHub repo with daily snapshot folders (`data/YYYY-MM-DD/TICKER.json`) — Why: free, versioned, browsable, ~30s read latency acceptable. Supabase upgrade path noted for cross-day analytics if needed.
- **Mid-day refresh**: Single Vercel/Cloudflare serverless function — keyless yfinance + RSS only, no LLM — Why: keep on-open latency low and cost zero.
- **Resilience**: yfinance and scrapers break ~1–2x/year — design for source fallbacks, last-known-good cache, visible staleness badge in UI. Manual force-refresh always available.
- **Architecture**: No LangGraph; Claude Code routine *is* the orchestrator. Persona prompts live in `prompts/personas/*.md` for iteration without code changes. Why: keyless constraint forecloses LangGraph; Claude already executes the work in routines.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Single-user app, no auth in v1 | Personal tool; multi-tenant complexity unnecessary | — Pending |
| Hybrid freshness (B): overnight batch + on-open refresh + on-demand recompute | Maps to the three daily modes (scan / deep-dive / decision-support) without overbuilding intraday streaming | — Pending |
| Keyless data plane | $0/month, no quota cliffs, ~85–90% of paid-stack value; gap (rating-change events, X) deferable | — Pending |
| Claude Code routine as orchestrator (Option A — not LangGraph) | LangGraph requires API keys; Claude routine runs from user's subscription | — Pending |
| Two-tier agent split: persona LLM + analytical Python | Adopted from virattt — deterministic scoring before LLM cuts cost, improves reproducibility, makes debugging easier | — Pending |
| Persona slate v1: Buffett, Munger, Wood, Burry, Lynch, **Open Claude Analyst** | Balanced lenses (value, quality, growth, contrarian, GARP) + unboxed Claude reasoning ensures inherent knowledge isn't lost | — Pending |
| Markdown persona prompts (`prompts/personas/*.md`) | Iterate without touching code; version-controlled | — Pending |
| **Dual-timeframe output** per ticker: short_term + long_term | User explicitly wants both swing tactics and thesis tracking surfaced | — Pending |
| **Position Adjustment Analyzer** as first-class agent | Multi-indicator consensus avoids single-indicator false positives; primary morning-scan view ("oversold today / overbought today") | — Pending |
| Per-ticker config: short_term_focus + long_term_lens + thesis_price + technical_levels + target_multiples | Some tickers need both views, others only one — user controls weighting; replaces simpler buy_mode field | — Pending |
| Storage: GitHub repo daily snapshots | Free, versioned, browsable, simplest v1; Supabase upgrade path noted | — Pending |
| Memory log + reflection (from TradingAgents) for endorsement tracking + historical persona signals | Lets dashboard show "Buffett went bearish 2 weeks ago" and "this newsletter call is +12% since recommendation" | — Pending |
| Provenance comments on every adapted file | Traceable design lineage for future debugging | — Pending |

---
*Last updated: 2026-04-29 after initialization*
