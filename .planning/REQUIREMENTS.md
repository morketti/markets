# Requirements: Markets — Personal Stock Research Dashboard

**Defined:** 2026-04-30
**Core Value:** Every morning, in one screen — which watchlist tickers need attention today and why, across short-term tactical and long-term strategic horizons.

## v1 Requirements

Requirements for initial release. Each maps to a roadmap phase.

### Watchlist (WATCH)

- [x] **WATCH-01**: User can maintain a watchlist of 30+ tickers in `watchlist.json`
- [x] **WATCH-02**: User can add a ticker via CLI utility (frontend CRUD deferred to v1.x)
- [x] **WATCH-03**: User can remove a ticker via CLI utility
- [x] **WATCH-04**: User can set per-ticker config: `short_term_focus` (bool), `long_term_lens` (value/growth/contrarian/mixed), `thesis_price`, `technical_levels` (support/resistance), `target_multiples` (P/E, P/S targets), `notes`
- [x] **WATCH-05**: Per-ticker config is validated via Pydantic schema; invalid entries rejected with clear error

### Data Ingestion (DATA)

- [x] **DATA-01**: System fetches daily OHLC + current price for each watchlist ticker via yfinance
- [x] **DATA-02**: System fetches latest fundamentals (P/E, P/S, ROE, debt/equity, margins, FCF) per ticker via yfinance
- [x] **DATA-03**: System fetches latest 10-K, 10-Q, 8-K filings from SEC EDGAR with compliant `User-Agent: <name> <email>` header
- [x] **DATA-04**: System fetches news headlines per ticker from RSS (Yahoo Finance, Google News per-ticker, FinViz, press wires)
- [x] **DATA-05**: System fetches social signal per ticker via anonymous Reddit RSS endpoints + StockTwits unauthenticated trending
- [x] **DATA-06**: All ingestion modules emit Pydantic-validated objects; sanity checks (price > 0, expected fields present) fail loudly
- [x] **DATA-07**: When yfinance returns empty/invalid data for a ticker, the ticker is flagged `data_unavailable: true`; downstream agents skip; frontend renders limited-data badge
- [x] **DATA-08**: yahooquery is available as a fallback price source; ingestion attempts it when yfinance fails

### Analytical Agents (ANLY)

- [x] **ANLY-01**: Fundamentals analyst produces an `AgentSignal` per ticker scoring P/E, P/S, ROE, debt/equity, margins with **5-state ladder verdict (strong_bullish | bullish | neutral | bearish | strong_bearish)** + confidence (0-100 int) + evidence list (≤10 items, each ≤200 chars)
- [x] **ANLY-02**: Technicals analyst produces an `AgentSignal` per ticker covering MA crossovers, momentum (1m/3m/6m), ADX-based trend strength; **5-state ladder verdict (strong_bullish | bullish | neutral | bearish | strong_bearish)** + confidence (0-100 int) + evidence list
- [x] **ANLY-03**: News/sentiment analyst produces an `AgentSignal` per ticker based on aggregated news with recency weighting (3-day half-life) and per-headline sentiment via VADER; **5-state ladder verdict (strong_bullish | bullish | neutral | bearish | strong_bearish)** + confidence (0-100 int) + evidence list
- [x] **ANLY-04**: Valuation analyst produces an `AgentSignal` per ticker based on current price vs `thesis_price` and `target_multiples` (when configured); deterministic compare to analyst consensus from yfinance (when available); **5-state ladder verdict (strong_bullish | bullish | neutral | bearish | strong_bearish)** + confidence (0-100 int) + evidence list

### Position-Adjustment Radar (POSE)

- [ ] **POSE-01**: Position-Adjustment Analyzer computes multi-indicator consensus from RSI(14), Bollinger Bands position, z-score vs 50-day MA, Stochastic %K, Williams %R, MACD divergence
- [ ] **POSE-02**: Output `state` ∈ {extreme_oversold, oversold, fair, overbought, extreme_overbought}; `consensus_score` ∈ [-1, +1]; `confidence` reflects indicator agreement count
- [ ] **POSE-03**: ADX(14) > 25 triggers trend-regime gating: mean-reversion indicators are downweighted in scoring
- [ ] **POSE-04**: `action_hint` derived from state ∈ {consider_add, hold_position, consider_trim, consider_take_profits}
- [ ] **POSE-05**: Position-Adjustment output is the headline data structure powering the Morning Scan's primary lens

### LLM Persona + Synthesizer (LLM)

- [ ] **LLM-01**: Persona prompts live as markdown files in `prompts/personas/`: `buffett.md`, `munger.md`, `wood.md`, `burry.md`, `lynch.md`, `claude_analyst.md`
- [ ] **LLM-02**: Each persona prompt is loaded at runtime by `routine/entrypoint.py`; never hardcoded as Python string
- [ ] **LLM-03**: Each persona prompt has a "voice signature" anchor section at the top defining non-negotiable lens characteristics
- [ ] **LLM-04**: Each persona invocation outputs Pydantic-validated `AgentSignal` (signal, confidence, reasoning ≤ 200 chars, evidence list)
- [ ] **LLM-05**: When persona LLM response fails Pydantic validation, `default_factory` returns `(neutral, 0, "schema_failure")` and the raw response is logged to `memory/llm_failures.jsonl`
- [ ] **LLM-06**: Synthesizer prompt (`prompts/synthesizer.md`) produces a per-ticker `TickerDecision` with `short_term`, `long_term`, `recommendation`, `open_observation`
- [ ] **LLM-07**: Synthesizer always renders a "Dissent" section identifying the most-bearish persona reasoning when ≥1 persona disagrees by ≥30 confidence points
- [ ] **LLM-08**: Routine emits `data/YYYY-MM-DD/_status.json` at end of run with `{success: bool, partial: bool, completed_tickers: [], failed_tickers: [], skipped_tickers: [], llm_failure_count: int}`

### Frontend Views (VIEW)

- [ ] **VIEW-01**: Morning-Scan view shows three lens tabs: **Position Adjustment**, **Short-Term Opportunities**, **Long-Term Thesis Status**; one lens visible at a time (no all-at-once dump)
- [ ] **VIEW-02**: Position Adjustment lens lists watchlist tickers sorted by extremity (`|consensus_score|` descending); shows state, evidence list, action_hint
- [ ] **VIEW-03**: Short-Term Opportunities lens lists tickers with bullish short_term signal sorted by confidence; shows drivers
- [ ] **VIEW-04**: Long-Term Thesis Status lens lists tickers with thesis_status ∈ {weakening, broken} sorted by severity
- [ ] **VIEW-05**: Per-Ticker Deep-Dive page shows dual-timeframe cards (short_term + long_term) side-by-side at top
- [ ] **VIEW-06**: Deep-dive shows OHLC chart (lightweight-charts) with MA20/MA50, Bollinger Bands, RSI overlay
- [ ] **VIEW-07**: Deep-dive shows persona signals as individual cards (each persona: verdict, confidence, reasoning, evidence)
- [ ] **VIEW-08**: Deep-dive shows news feed grouped by source with timestamps; "since snapshot" delta surfaced
- [ ] **VIEW-09**: Deep-dive shows Open Claude Analyst observation pinned at top
- [ ] **VIEW-10**: Decision-Support view shows recommendation banner (action + conviction band), drivers list, dissent section, and snapshot vs current-price delta
- [ ] **VIEW-11**: Header shows snapshot date + staleness badge (GREEN < 6h, AMBER 6-24h, RED > 24h or partial)
- [ ] **VIEW-12**: All views are mobile-responsive; morning-scan and deep-dive have phone-optimized layouts (collapsed cards, swipeable tabs)
- [ ] **VIEW-13**: Search/add ticker via typeahead with company name fuzzy match
- [ ] **VIEW-14**: Snapshot date selector lets user load historical snapshots from `data/YYYY-MM-DD/`
- [ ] **VIEW-15**: All JSON reads from `raw.githubusercontent.com` are zod-validated; schema mismatches render error state, not crash

### Mid-Day Refresh (REFRESH)

- [ ] **REFRESH-01**: Mid-day refresh runs as Vercel Python serverless function at `api/refresh.py`
- [ ] **REFRESH-02**: Refresh accepts `?ticker=X` query, fetches current price (yfinance) + headlines published since the snapshot timestamp (RSS) — no LLM calls
- [ ] **REFRESH-03**: Frontend Deep-Dive page triggers refresh on open and merges results into rendered state
- [ ] **REFRESH-04**: Refresh function completes within 10s Vercel timeout; on yfinance/RSS failure returns partial response with explicit `error: true` flag and frontend continues to show snapshot data

### Endorsements (ENDORSE — capture only in v1)

- [ ] **ENDORSE-01**: System captures endorsement entries via append-only `endorsements.jsonl`: `{ticker, source, date, price_at_call, notes, captured_at}`
- [ ] **ENDORSE-02**: User can add endorsements via CLI utility (frontend form deferred to v1.x)
- [ ] **ENDORSE-03**: Decision-Support view shows recent endorsements (last 90 days) for the active ticker; performance math (% vs S&P, corp-action-aware) deferred to v1.x

### Infrastructure (INFRA)

- [ ] **INFRA-01**: Scheduled Claude Code routine fires Mon-Fri at 06:00 ET; runs from user's Claude subscription quota (no Anthropic API key)
- [ ] **INFRA-02**: Routine entrypoint logs estimated token cost up front; if estimate exceeds available quota, runs in lite mode (analyticals only, no persona LLM, no synthesizer LLM)
- [ ] **INFRA-03**: Daily snapshots committed to `data/YYYY-MM-DD/` with one JSON per ticker (`AAPL.json`, etc.) plus `_index.json` listing tickers + run metadata
- [ ] **INFRA-04**: Routine commits and pushes via git from within the routine; auth token stored as routine env var (not in repo)
- [ ] **INFRA-05**: Frontend deployed to Vercel; builds triggered on `main` branch push; reads from `raw.githubusercontent.com` via public repo URL
- [ ] **INFRA-06**: Memory layer writes append-only `memory/historical_signals.jsonl` per run with `{date, ticker, persona_id, signal, confidence}` records (used in v1.x for trend surfacing)
- [ ] **INFRA-07**: Provenance: every code file adapted from reference repos (`virattt/ai-hedge-fund` or `TauricResearch/TradingAgents`) carries a header comment naming the source file and modifications

## v1.x Requirements

Deferred to follow-up release. Tracked but not in current roadmap.

### Endorsements (Performance Math)

- **ENDORSE-04**: System computes endorsement performance using corp-action-adjusted historical prices (yfinance `auto_adjust=True`)
- **ENDORSE-05**: System computes performance vs S&P 500 (alpha) for each endorsement
- **ENDORSE-06**: Decision-Support view shows endorsement performance number per recent endorsement
- **ENDORSE-07**: System detects corp-action events affecting recent endorsements and surfaces a notice

### Watchlist UI

- **WATCH-06**: Frontend watchlist CRUD UI (add/edit/remove) replacing CLI utility
- **WATCH-07**: Per-ticker config edit form in frontend

### Historical Trends

- **TREND-01**: Persona signal trend view per ticker ("Buffett shifted bearish 2 weeks ago")
- **TREND-02**: Position-Adjustment historical chart per ticker

### On-Demand Recompute

- **OND-01**: User can trigger on-demand re-synthesis of a single ticker; results commit to `data/YYYY-MM-DD/_ondemand/{ticker}-HHMM.json`; UI shows ondemand version when newer than morning snapshot
- **OND-02**: On-demand recompute respects token quota with explicit "may use your daily quota" warning

### Sector / Peer Comparison

- **SEC-01**: Per-ticker page shows peer tickers (sector-based) with comparable metrics

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Trade execution / brokerage integration | Research tool, not a trading system; security exposure; compliance scope |
| Real-time intraday tick data | Requires WebSocket infrastructure + paid feeds; kills keyless cost story; yfinance 15-20min delay sufficient |
| Push notifications / SMS / email alerts | Requires running server or third-party service; defer evaluation to v2 with usage evidence |
| Multi-user / sharing / public profiles | Single-user app; auth + isolation = different product |
| Social features (likes, comments, leaderboards) | Lowers signal quality; introduces moderation; explicit anti-feature |
| Paper trading / strategy backtesting | Different product; requires order simulation + slippage |
| AI chat with dashboard | Burns Claude routine quota; unbounded scope; Open Claude Analyst is the disciplined version |
| Native iOS/Android apps | Mobile-responsive web sufficient; "Add to Home Screen" gets ~80% of native UX |
| Live order book / Level 2 data | Paid feeds; not relevant for non-day-trading research |
| Portfolio allocation / rebalancing recommender | Out of scope — we surface per-ticker signals, user decides allocation |
| Twitter/X social signal | Paid API since 2023; covered by Reddit + StockTwits proxy |
| Premium media full-text (Bloomberg/WSJ/Reuters) | Paywalled; RSS headlines + click-through to user's existing subs is sufficient |
| Paid market-data APIs (Alpha Vantage / Finnhub / Polygon) | Keyless v1; revisit only with 60-day evidence of capability gap |
| LangGraph / LangChain framework | Requires LLM provider keys; incompatible with keyless-via-Claude-routine choice |
| Database (Supabase / Postgres / MongoDB) | GitHub-as-DB sufficient for v1; migrate only with evidence |
| Anthropic API (with key) | Compute runs from Claude Code routine subscription; no separate key |
| Real-time WebSocket / SSE updates | Premature; on-open refresh covers urgency; would require running server |

## Traceability

Phase mapping per requirement. Updated by ROADMAP.md.

| Requirement | Phase | Status |
|-------------|-------|--------|
| WATCH-01 | Phase 1 | Complete |
| WATCH-02 | Phase 1 | Complete |
| WATCH-03 | Phase 1 | Complete |
| WATCH-04 | Phase 1 | Complete |
| WATCH-05 | Phase 1 | Complete |
| DATA-01 | Phase 2 | Complete |
| DATA-02 | Phase 2 | Complete |
| DATA-03 | Phase 2 | Complete |
| DATA-04 | Phase 2 | Complete |
| DATA-05 | Phase 2 | Complete |
| DATA-06 | Phase 2 | Complete |
| DATA-07 | Phase 2 | Complete |
| DATA-08 | Phase 2 | Complete |
| ANLY-01 | Phase 3 | Complete |
| ANLY-02 | Phase 3 | Complete |
| ANLY-03 | Phase 3 | Complete |
| ANLY-04 | Phase 3 | Complete |
| POSE-01 | Phase 4 | Pending |
| POSE-02 | Phase 4 | Pending |
| POSE-03 | Phase 4 | Pending |
| POSE-04 | Phase 4 | Pending |
| POSE-05 | Phase 4 | Pending |
| LLM-01 | Phase 5 | Pending |
| LLM-02 | Phase 5 | Pending |
| LLM-03 | Phase 5 | Pending |
| LLM-04 | Phase 5 | Pending |
| LLM-05 | Phase 5 | Pending |
| LLM-06 | Phase 5 | Pending |
| LLM-07 | Phase 5 | Pending |
| LLM-08 | Phase 5 | Pending |
| VIEW-01 | Phase 6 | Pending |
| VIEW-02 | Phase 6 | Pending |
| VIEW-03 | Phase 6 | Pending |
| VIEW-04 | Phase 6 | Pending |
| VIEW-05 | Phase 6 | Pending |
| VIEW-06 | Phase 6 | Pending |
| VIEW-07 | Phase 6 | Pending |
| VIEW-08 | Phase 6 | Pending |
| VIEW-09 | Phase 6 | Pending |
| VIEW-10 | Phase 7 | Pending |
| VIEW-11 | Phase 6 | Pending |
| VIEW-12 | Phase 6 | Pending |
| VIEW-13 | Phase 6 | Pending |
| VIEW-14 | Phase 6 | Pending |
| VIEW-15 | Phase 6 | Pending |
| REFRESH-01 | Phase 8 | Pending |
| REFRESH-02 | Phase 8 | Pending |
| REFRESH-03 | Phase 8 | Pending |
| REFRESH-04 | Phase 8 | Pending |
| ENDORSE-01 | Phase 9 | Pending |
| ENDORSE-02 | Phase 9 | Pending |
| ENDORSE-03 | Phase 9 | Pending |
| INFRA-01 | Phase 5 | Pending |
| INFRA-02 | Phase 5 | Pending |
| INFRA-03 | Phase 5 | Pending |
| INFRA-04 | Phase 5 | Pending |
| INFRA-05 | Phase 6 | Pending |
| INFRA-06 | Phase 8 | Pending |
| INFRA-07 | Phase 8 | Pending |

**Coverage:**
- v1 requirements: 59 total
- Mapped to phases: 59
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-30*
*Last updated: 2026-05-03 — Phase 3 / Plan 02 complete: ANLY-01 (fundamentals analyst) marked complete after `analysts/fundamentals.py` shipped with 5-state verdict + per-config + fallback band scoring*
