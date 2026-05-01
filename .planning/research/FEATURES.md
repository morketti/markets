# Feature Research

**Domain:** Personal stock research dashboard
**Researched:** 2026-04-30
**Confidence:** HIGH (well-defined product class, multiple references analyzed)

## Feature Landscape

### Table Stakes (Users Expect These)

Features without which the product fails as a research tool. Missing any = user goes back to StockAnalysis.com / FinViz / Seeking Alpha.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Watchlist with CRUD (add/remove/rename) | Core workflow — every research tool has this | LOW | Per-ticker config attached (mode, thesis, levels) is the differentiator, not the watchlist itself |
| Price chart per ticker (OHLC, daily candles, ≥1y history) | If you can't see the price, you can't research | LOW | lightweight-charts handles this trivially |
| Latest news per ticker (multi-source feed, dedup, recency-sorted) | Tickers without news context are useless for decision-making | MEDIUM | Aggregating Yahoo + Google News + FinViz + press wires + dedup is the actual work |
| Fundamental snapshot (P/E, P/S, P/B, EPS, revenue, margin, debt/equity) | Every screener shows these — users expect them | LOW | yfinance gives them in one call |
| Search/add ticker (typeahead with company name) | Manual ticker memorization is hostile UX | LOW | Bundle a static ticker→name JSON; fuzzy search client-side |
| Last-updated timestamp + staleness indicator | User must know if they're looking at stale data | LOW | Critical for trust; ours is non-trivial since data spans morning batch + on-open refresh |
| Dark theme | User-specified; standard for finance tools | LOW | Tailwind `dark:` variants |
| Mobile-responsive layout | User-specified; viewing on phone in morning | MEDIUM | Watchlist scan view + ticker detail view need separate mobile layouts |
| Snapshot date selector ("show me yesterday's view") | Comparing across days is a primary research pattern | LOW | Free since we already commit per-day snapshots — UI just needs a date picker |

### Differentiators (Competitive Advantage)

Where we beat StockAnalysis / FinViz / Seeking Alpha for personal research.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Position-Adjustment Radar** (oversold/overbought across watchlist) | "Where do I trim, where do I add — today" — directly actionable, no other free tool surfaces this prominently | MEDIUM | Multi-indicator consensus (RSI + BB + z-score + stochastic + Williams %R + MACD divergence) — already designed |
| **Dual-timeframe per-ticker view** (short-term + long-term side-by-side) | Most tools blend horizons; we explicitly separate them so user knows which they're acting on | MEDIUM | Schema-driven; UI is a side-by-side card layout |
| **Persona slate analysis** (Buffett/Munger/Wood/Burry/Lynch + Open Claude Analyst) with per-persona conviction | "Buffett says bearish 75%, Wood says bullish 60% — here's why each" gives multi-lens decision-support no other tool offers | HIGH | Markdown prompts + Claude routine; biggest engineering item |
| **Open Claude Analyst commentary** ("off-script observation") | Surfaces context the structured agents miss (macro, sector rotation, geopolitics) — pure inherent-knowledge value | LOW | One additional persona prompt + synthesizer field |
| **Endorsement-call performance tracking** | Newsletter/service calls tracked with date + price-at-call vs current → "this advisor is up 12% on this call" | HIGH | Memory log adapted from TradingAgents pattern; non-trivial corp-action math |
| **Per-ticker config** (short_term_focus toggle, long_term_lens, thesis_price, technical_levels, target_multiples) | User declares per-ticker how to analyze — no other tool gives this control | MEDIUM | Lives in watchlist JSON; drives weighting at synthesis |
| **Decision-support "Should I buy/trim/hold X today"** with conviction band, drivers, dissenting views | Most tools surface signals; we explicitly synthesize a recommendation with reasoning | MEDIUM | Synthesizer agent does the work — pattern adapted from virattt's PortfolioManager |
| **Daily git-versioned snapshots** | "What did Buffett's signal look like 2 weeks ago" — free history just by browsing the data repo | LOW | Free side-effect of using GitHub as storage |

### Anti-Features (Commonly Requested, Often Problematic)

Features we deliberately do not build.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Trade execution / brokerage integration | "If I'm researching anyway, why not click to buy" | Different product entirely; security exposure (broker API keys); makes this a fintech app subject to compliance | This is a research tool. Click-out to your broker. |
| Real-time intraday tick data | "I want to see prices live" | Requires WebSockets/SSE infrastructure, paid data subscriptions, server-running compute — kills our keyless cost story | yfinance 15-20min delay is fine for personal research; on-open refresh covers urgency |
| Push notifications / alerts | "Tell me when AAPL crosses $200" | Requires running server (or third-party service), notification permissions, retention logic — substantial scope | Defer to v2; for v1, the morning scan is the alert |
| Multi-user / sharing | "Share this view with friends" | Auth, multi-tenancy, data isolation, share-link security — completely changes architecture | Single-user; deploy is private. If sharing is wanted later, screenshot. |
| Social features (likes, comments, leaderboards) | "Make it engaging" | Distracting from research; introduces moderation; lowers signal quality | None — explicit anti-feature |
| Paper trading / backtesting | "I want to test strategies first" | Different product; requires order simulation, realistic fills, slippage modeling | Not the product; out of scope |
| AI chat with the dashboard ("Ask Claude about NVDA") | Sounds nice, expensive, slow | Burns Claude routine quota; unbounded scope; quality varies | Open Claude Analyst commentary is the disciplined version of this |
| Native mobile app (iOS/Android) | "I want it as an app" | App store overhead, separate codebase, push-notification machinery, code signing | Mobile-responsive web is sufficient for personal use; "Add to Home Screen" gets ~80% of native UX |
| Live order book / Level 2 data | "Show me liquidity" | Paid feeds; not relevant for non-day-trading research | Skip |
| Complex portfolio allocator / rebalancer | "Tell me how to allocate" | Different product; requires position sizes + risk model | Out of scope; we surface signals, user decides allocation |

## Feature Dependencies

```
Watchlist CRUD ──> Per-ticker config ──> All analyst agents
                                         └──> Synthesizer ──> Decisions
                                              ↑
                                              │
News ingestion ────────────────────────────────┤
Fundamentals ingestion ────────────────────────┤
Price/technicals ingestion ────────────────────┤
Endorsement input ─────────────────────────────┤
Persona prompts ───────────────────────────────┘

Daily snapshots ──> Snapshot date selector ──> History views
                └──> Endorsement performance tracking
                └──> Historical persona signal trends

Position-Adjustment Radar ──requires──> Technicals ingestion
                                          └──requires──> Price data

Decision-support ──requires──> All analyst signals + Per-ticker config
```

### Dependency Notes

- **Per-ticker config blocks all analysis weighting.** Without it, every ticker is analyzed identically — defeats the personalization premise. Build this in Phase 1 with the watchlist.
- **Endorsement tracking depends on memory log + corp-action math.** Don't ship endorsement performance until the memory layer is solid; partial = misleading.
- **Decision-support requires all analyst signals.** It's the synthesizer over everything else; ship it after all analyst categories are in place.
- **Snapshot date selector is free if storage is per-day folders.** Don't conflate it with retroactive recomputation (which is out of scope).

## MVP Definition

### Launch With (v1)

The minimum to validate the morning command center concept.

- [ ] Watchlist CRUD with per-ticker config (short_term_focus, long_term_lens, thesis_price, technical_levels, target_multiples) — without this, nothing else is personalized
- [ ] Daily ingestion: yfinance prices/fundamentals + EDGAR filings + RSS news for full watchlist — the data plane
- [ ] Analytical agents: fundamentals, technicals, news/sentiment, position-adjustment, valuation — deterministic Python signals
- [ ] Persona slate: Buffett, Munger, Wood, Burry, Lynch, Open Claude Analyst — markdown prompts + Claude routine
- [ ] Synthesizer: per-ticker buy/trim/hold/take-profits with dual-timeframe outputs and drivers — the decision-support core
- [ ] Storage: GitHub repo with daily JSON snapshots committed by the routine
- [ ] Frontend: morning-scan view (3 lenses: position-adjustment, short-term opportunities, long-term thesis status) + per-ticker deep-dive
- [ ] Mid-day refresh: on-open serverless function fetches current price + recent news (no LLM)

### Add After Validation (v1.x)

Trigger: 60 days of v1 use; surface what's actually missing from morning workflow.

- [ ] Endorsement-call performance tracking with corp-action-aware math — non-trivial, value depends on whether user actually feeds endorsements in regularly
- [ ] Historical persona signal trends ("Buffett shifted bearish 2 weeks ago") — depends on memory log being populated for ≥30 days
- [ ] Sector / peer comparison view — useful but not blocking morning flow
- [ ] PDF/markdown export of decision-support narrative for archiving

### Future Consideration (v2+)

- [ ] Push notifications / alerts — only if user finds themselves missing time-sensitive moves
- [ ] Migration to Supabase for cross-day analytics queries — only if GitHub-as-DB starts hurting
- [ ] Paid data backstop (Polygon/Benzinga rating-change feed) — only with evidence that keyless gaps cost real money
- [ ] LangGraph migration if we add real debate-state / multi-round agent reasoning — current single-pass is sufficient

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Watchlist + per-ticker config | HIGH | LOW | **P1** |
| Daily ingestion (yfinance/EDGAR/RSS) | HIGH | MEDIUM | **P1** |
| Analytical agents (Python) | HIGH | MEDIUM | **P1** |
| Persona slate + Claude routine | HIGH | HIGH | **P1** |
| Synthesizer (decision-support) | HIGH | MEDIUM | **P1** |
| Position-Adjustment Radar (morning-scan view) | HIGH | MEDIUM | **P1** |
| Dual-timeframe per-ticker view | HIGH | LOW (schema-driven) | **P1** |
| Per-ticker deep-dive page | HIGH | MEDIUM | **P1** |
| Mid-day refresh (on-open) | MEDIUM | LOW | **P1** |
| Snapshot date selector | MEDIUM | LOW (free from storage) | **P2** |
| Endorsement performance tracking | MEDIUM | HIGH | **P2** |
| Historical signal trends | MEDIUM | MEDIUM | **P2** |
| Sector/peer comparison | LOW | MEDIUM | **P3** |
| Push alerts | LOW | HIGH | **P3** |

## Competitor Feature Analysis

| Feature | StockAnalysis.com | FinViz Elite | Seeking Alpha | Our Approach |
|---------|-------------------|--------------|---------------|--------------|
| Watchlist with per-ticker notes | Basic notes | Tags only | Tags only | Full per-ticker analytical config (lens, levels, thesis price) |
| Multi-source news feed | Single source per ticker | Aggregated | Aggregated, lots of noise | Aggregated + dedup + recency weighting + LLM-summarized "what changed" |
| Buy/sell signals | None (data only) | Limited | Author-driven, varies | Multi-persona consensus + Open Claude Analyst + dual-timeframe |
| Oversold/overbought screener | Limited (RSI only) | Yes (single-indicator) | No | **Multi-indicator consensus radar** with confidence + extreme tier |
| Newsletter performance tracking | No | No | No | **Endorsement tracking** as first-class signal |
| Personalized analysis lens | No | No | Author following | **Per-ticker lens selection** drives synthesis weighting |
| Free | Mostly | Limited | Paywalled | $0 — keyless data + Claude subscription routine |

## Sources

- StockAnalysis.com, FinViz, Seeking Alpha — competitive feature analysis (general knowledge of these products)
- TradingView watchlists — UX inspiration for per-ticker config patterns
- Reference repos: `virattt/ai-hedge-fund` (persona pattern), `TauricResearch/TradingAgents` (memory log + reflection pattern)
- User's PROJECT.md — locked feature set and anti-feature exclusions

---
*Feature research for: personal stock research dashboard*
*Researched: 2026-04-30*
