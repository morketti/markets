# Roadmap: Markets — Personal Stock Research Dashboard

**Created:** 2026-04-30
**Phases:** 9
**Granularity:** Fine
**Requirements:** 59 v1 (100% mapped)

## Phase Summary

| # | Phase | Goal | Requirements | Success Criteria | Dependencies |
|---|-------|------|--------------|------------------|--------------|
| 1 | Foundation — Watchlist + Per-Ticker Config (5/5 plans, Complete) | Complete    | 2026-05-01 | 4 | — |
| 2 | Ingestion — Keyless Data Plane (7/7 plans, Complete) | Complete    | 2026-05-02 | 5 | Phase 1 |
| 3 | Analytical Agents — Deterministic Scoring | Four Python analyst modules emit structured signals per ticker (5th is Phase 4 POSE) | ANLY-01..04 | 5 | Phase 2 |
| 4 | Position-Adjustment Radar | Multi-indicator overbought/oversold consensus with trend-regime gating | POSE-01..05 | 5 | Phases 2, 3 |
| 5 | Claude Routine Wiring — Persona Slate + Synthesizer | Scheduled routine produces full TickerDecisions and commits snapshots | LLM-01..08, INFRA-01..04 | 6 | Phases 3, 4 |
| 6 | Frontend MVP — Morning Scan + Deep-Dive | Static React app reads snapshots, renders three lenses + ticker detail | VIEW-01..09, VIEW-11..15, INFRA-05 | 7 | Phase 5 |
| 7 | Decision-Support View + Dissent Surface | User reads buy/trim/hold recommendation with drivers + dissent | VIEW-10 | 4 | Phases 5, 6 |
| 8 | Mid-Day Refresh + Resilience | On-open refresh layer + lite-mode fallback + memory writes verified | REFRESH-01..04, INFRA-06..07 | 5 | Phase 6 |
| 9 | Endorsement Capture | Endorsements as first-class signal (capture only — performance math deferred) | ENDORSE-01..03 | 3 | Phase 7 |

## Phase Detail

### Phase 1: Foundation — Watchlist + Per-Ticker Config

**Goal:** User can declare a watchlist with rich per-ticker configuration that drives all downstream analysis.

**Requirements:** WATCH-01, WATCH-02, WATCH-03, WATCH-04, WATCH-05

**Success Criteria:**
1. `watchlist.json` schema with 30+ tickers loads and validates via Pydantic v2
2. CLI utilities `cli/add_ticker.py` and `cli/remove_ticker.py` work end-to-end against `watchlist.json`
3. Per-ticker config supports `short_term_focus`, `long_term_lens`, `thesis_price`, `technical_levels`, `target_multiples`, `notes`
4. Invalid configs are rejected with actionable Pydantic error messages

**Why first:** Per-ticker config blocks all downstream personalization. Without it, every ticker gets the same analysis — defeats the product premise.

**Dependencies:** None

**Pitfalls addressed:** #10 (premature abstraction — keep watchlist simple, no plugin system)

**Plans:** 5/5 plans complete

Plans:
- [x] 01-01-scaffold-PLAN.md — pyproject.toml, packages, conftest fixtures, placeholder CLI dispatcher
- [x] 01-02-schemas-PLAN.md — analysts/schemas.py: TickerConfig + Watchlist + nested models, all validators
- [x] 01-03-loader-PLAN.md — watchlist/loader.py: load_watchlist + atomic save_watchlist with sort_keys serialization
- [x] 01-04-cli-core-PLAN.md — cli/main.py dispatcher + add/remove subcommands + format_validation_error
- [x] 01-05-cli-readonly-and-example-PLAN.md — list/show subcommands + watchlist.example.json + README

---

### Phase 2: Ingestion — Keyless Data Plane

**Goal:** System fetches all needed data for any ticker without API keys, with sanity checks and fallbacks.

**Requirements:** DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DATA-07, DATA-08

**Success Criteria:**
1. yfinance prices and fundamentals fetched for full watchlist; Pydantic sanity checks (price > 0, fundamentals dict has expected keys) pass or `data_unavailable: true` is set
2. EDGAR filings (10-K, 10-Q, 8-K) fetched with compliant `User-Agent: <name> <email>` header — zero 403s logged
3. RSS aggregation produces de-duplicated, recency-sorted headlines per ticker from Yahoo Finance + Google News + FinViz + press wires
4. Reddit RSS + StockTwits trending fetched anonymously (no OAuth)
5. yfinance failure on a ticker triggers yahooquery fallback path; ultimate failure marks ticker `data_unavailable`

**Dependencies:** Phase 1 (needs watchlist to know which tickers to fetch)

**Pitfalls addressed:** #1 (yfinance silent breakage — sanity checks + fallback), #2 (EDGAR User-Agent compliance)

**Plans:** 7/7 plans complete

Plans:
- [x] 02-01-foundation-PLAN.md — ingestion/http.py + errors + analysts/data/ schemas + Wave-0 fixtures + responses dep
- [x] 02-02-prices-fundamentals-PLAN.md — ingestion/prices.py + fundamentals.py (yfinance + yahooquery fallback)
- [x] 02-03-edgar-filings-PLAN.md — ingestion/filings.py (EDGAR with compliant User-Agent + retry)
- [x] 02-04-news-rss-PLAN.md — ingestion/news.py (Yahoo RSS + Google News + FinViz scrape + dedup + sort)
- [x] 02-05-social-PLAN.md — ingestion/social.py (Reddit RSS + StockTwits trending + per-symbol)
- [x] 02-06-refresh-orchestrator-PLAN.md — ingestion/refresh.py + manifest + Snapshot + cli/refresh.py + SUBCOMMANDS extension
- [x] 02-07-fundamentals-analyst-fields-PLAN.md — Phase 2 amendment for Phase 3 valuation prerequisite (4 analyst-consensus fields on FundamentalsSnapshot + fetch_prices default period 3mo→1y)

---

### Phase 3: Analytical Agents — Deterministic Scoring

**Goal:** Four Python analyst modules produce structured signals per ticker, all pure-function and unit-testable. (5th analyst — Position-Adjustment — lives in Phase 4 / POSE-01..05.)

**Requirements:** ANLY-01, ANLY-02, ANLY-03, ANLY-04

**Success Criteria:**
1. Fundamentals analyst emits `AgentSignal` (P/E, P/S, ROE, debt/equity, margins) with bullish/bearish/neutral verdict + confidence + evidence list
2. Technicals analyst emits `AgentSignal` covering MA20/50/200 alignment, momentum (1m/3m/6m), ADX trend strength
3. News/sentiment analyst aggregates RSS, applies recency weighting, classifies headline-level sentiment, emits `AgentSignal`
4. Valuation analyst compares price vs `thesis_price` and `target_multiples`; compares to yfinance analyst consensus snapshot; emits `AgentSignal`
5. All signals serialize/deserialize cleanly through Pydantic and have unit tests against representative fixture inputs

**Dependencies:** Phase 2 (needs raw data to score)

**Pitfalls addressed:** #4 (LLM schema drift — these Python scores are stable inputs to LLM personas)

**Plans:** 5 plans

Plans:
- [ ] 03-01-signals-PLAN.md — AgentSignal schema + tests/analysts/ scaffold + vaderSentiment dep + REQUIREMENTS/ROADMAP touch-ups
- [ ] 03-02-fundamentals-PLAN.md — fundamentals analyst (5-metric per-config + fallback bands + 5-state ladder)
- [ ] 03-03-technicals-PLAN.md — technicals analyst (MA20/50/200 + momentum 1m/3m/6m + ADX(14) + warm-up guards; hand-rolled pandas math)
- [ ] 03-04-news-sentiment-PLAN.md — news/sentiment analyst (VADER per-headline + 3-day-half-life recency + source weighting)
- [ ] 03-05-valuation-PLAN.md — valuation analyst (thesis_price > target_multiples > yfinance consensus blend; depends on 02-07)

---

### Phase 4: Position-Adjustment Radar

**Goal:** Multi-indicator overbought/oversold consensus drives the headline morning-scan view.

**Requirements:** POSE-01, POSE-02, POSE-03, POSE-04, POSE-05

**Success Criteria:**
1. Six indicators computed correctly: RSI(14), Bollinger Bands position, z-score vs 50-day MA, Stochastic %K, Williams %R, MACD divergence
2. Output `state` ∈ {extreme_oversold, oversold, fair, overbought, extreme_overbought}; `consensus_score` ∈ [-1, +1]; `confidence` reflects agreement count
3. ADX(14) > 25 triggers trend-regime gating — mean-reversion indicators downweighted in scoring
4. `action_hint` correctly derived from state mapping
5. Output passes regression test against synthetic trending and mean-reverting price series fixtures

**Dependencies:** Phase 2 (price data), Phase 3 (shared signal schema)

**Pitfalls addressed:** #6 (false positives in trending markets — multi-indicator consensus + ADX gating)

---

### Phase 5: Claude Routine Wiring — Persona Slate + Synthesizer

**Goal:** Scheduled Claude Code routine produces full per-ticker `TickerDecision` JSONs and commits the daily snapshot folder.

**Requirements:** LLM-01, LLM-02, LLM-03, LLM-04, LLM-05, LLM-06, LLM-07, LLM-08, INFRA-01, INFRA-02, INFRA-03, INFRA-04

**Success Criteria:**
1. Six markdown personas in `prompts/personas/` (`buffett.md`, `munger.md`, `wood.md`, `burry.md`, `lynch.md`, `claude_analyst.md`) load at runtime; each has voice-signature anchor section
2. Pydantic validation + `default_factory` active on every LLM call; failures log raw output to `memory/llm_failures.jsonl`
3. Synthesizer prompt produces dual-timeframe `TickerDecision` with dissent surface when ≥1 persona disagrees by ≥30 confidence delta
4. Routine fires Mon-Fri 06:00 ET; runs entrypoint script; commits `data/YYYY-MM-DD/` snapshot folder; pushes via env-var token
5. `_status.json` emitted with `{success, partial, completed_tickers, failed_tickers, llm_failure_count}`
6. Lite-mode fallback verified on simulated quota exhaustion (analyticals only — no persona LLM, no synthesizer LLM)

**Dependencies:** Phase 3 (analytical signals), Phase 4 (position-adjustment as first-class input)

**Pitfalls addressed:** #3 (quota burnout — lite mode + prioritization), #4 (schema drift — Pydantic + default_factory), #7 (persona drift — voice signatures + regression test set)

**Research flag:** Verify current Claude Code routine constraints during plan-phase research (cron syntax, output format, quota visibility, env-var injection for git push token).

---

### Phase 6: Frontend MVP — Morning Scan + Deep-Dive

**Goal:** Static React app reads daily snapshots from GitHub raw and renders the morning-scan three-lens view + per-ticker deep-dive.

**Requirements:** VIEW-01, VIEW-02, VIEW-03, VIEW-04, VIEW-05, VIEW-06, VIEW-07, VIEW-08, VIEW-09, VIEW-11, VIEW-12, VIEW-13, VIEW-14, VIEW-15, INFRA-05

**Success Criteria:**
1. Vite + React + TypeScript app deployed to Vercel; reads from `raw.githubusercontent.com/<user>/<repo>/main/data/...`
2. Morning Scan view renders three lens tabs (Position Adjustment / Short-Term Opportunities / Long-Term Thesis Status); only one visible at a time (no all-at-once dump)
3. Position Adjustment lens sorts watchlist by `|consensus_score|` descending; renders state, evidence, action_hint
4. Per-Ticker Deep-Dive shows dual-timeframe cards + OHLC chart (lightweight-charts) with MA/BB/RSI overlays + persona signal cards + news feed grouped by source + Open Claude Analyst observation pinned at top
5. Staleness badge in header transitions GREEN/AMBER/RED based on snapshot age and `_status.json` partial-success state
6. Mobile-responsive layout passes manual phone test on iOS Safari + Android Chrome
7. zod validates every JSON read from raw URL — schema mismatches render error state (not crash)

**Dependencies:** Phase 5 (snapshots must exist for the frontend to read)

**Pitfalls addressed:** #8 (UI overload — one lens at a time), #9 (stale-data UX — staleness badge as foundational pattern)

---

### Phase 7: Decision-Support View + Dissent Surface

**Goal:** Decision-Support route shows the per-ticker buy/trim/hold/take-profits recommendation with drivers, dissent, and current-price delta.

**Requirements:** VIEW-10

**Success Criteria:**
1. Decision view renders recommendation banner: action ∈ {add, trim, hold, take_profits, buy, avoid} + conviction band ∈ {low, medium, high}
2. Drivers list rendered separately for short_term and long_term timeframes
3. Dissent section always present when ≥1 persona disagrees with majority by ≥30 confidence points
4. Current-price-vs-snapshot delta visible — flags when intraday move materially affected the recommendation logic

**Dependencies:** Phase 5 (synthesizer output), Phase 6 (frontend infrastructure)

**Pitfalls addressed:** #12 (self-confirmation bias — dissent always rendered)

---

### Phase 8: Mid-Day Refresh + Resilience

**Goal:** On-open refresh function, end-to-end resilience verification, memory-layer wiring.

**Requirements:** REFRESH-01, REFRESH-02, REFRESH-03, REFRESH-04, INFRA-06, INFRA-07

**Success Criteria:**
1. `api/refresh.py` Vercel Python serverless function returns within 10s timeout for any ticker (cold start + warm)
2. Frontend Deep-Dive triggers refresh on open and merges current price + post-snapshot headlines without flicker
3. Failure modes verified: yfinance down (yahooquery fallback), RSS unavailable (return partial with `error: true`), function timeout (frontend continues with snapshot)
4. `memory/historical_signals.jsonl` written on every routine run with `{date, ticker, persona_id, signal, confidence}` records
5. Provenance comments verified on all reference-adapted code (script-checked at CI / pre-commit)

**Dependencies:** Phase 6 (deep-dive integration point)

**Pitfalls addressed:** #1 (yfinance fallback verified), #3 (quota awareness in routine), #9 (staleness fully covered), #11 (early monitoring of GitHub-as-DB scaling)

**Research flag:** Verify Vercel Python serverless cold-start timing under realistic ticker fetch + RSS parse path before declaring done.

---

### Phase 9: Endorsement Capture

**Goal:** Endorsement entries captured as first-class signal — performance math deferred to v1.x with clean schema versioning so the addition is non-breaking.

**Requirements:** ENDORSE-01, ENDORSE-02, ENDORSE-03

**Success Criteria:**
1. CLI utility `cli/add_endorsement.py` appends to `endorsements.jsonl` with required fields: `ticker, source, date, price_at_call, notes, captured_at`
2. Decision-Support view shows last 90 days of endorsements per ticker (most recent first); no performance number rendered yet
3. Schema versioned (`endorsement_schema_v1`) so v1.x performance-math addition is a non-breaking column addition, not a schema migration

**Dependencies:** Phase 7 (decision view exists to render endorsements)

**Pitfalls addressed:** #5 (corp-action complexity — defer the math, ship the capture)

**v1.x successors:** ENDORSE-04..07 (corp-action-aware performance, vs S&P alpha, performance number rendering, corp-action notice surface)

---

## Phase Ordering Rationale

- **Foundation → Data → Logic → LLM → UI** is the natural dependency graph; each phase depends on the previous
- **Position-Adjustment Radar (Phase 4)** ships standalone before the full routine (Phase 5) so the user gets a tangible "morning radar" deliverable early, even before personas are wired
- **Decision-Support split from Frontend MVP (Phases 6 + 7)** because dissent surfacing requires the full persona slate to be running and producing the dissent payload
- **Resilience phase (8) lands after the full pipeline is working** — premature resilience work without real failure data is wasted effort
- **Endorsement Capture last (9)** because it has the lowest blocking value and the highest complexity surface (corp-action math) that defers cleanly to v1.x

## Coverage Validation

| Category | Count | Phase Coverage |
|----------|-------|----------------|
| WATCH | 5 | Phase 1 (5/5) |
| DATA | 8 | Phase 2 (8/8) |
| ANLY | 4 | Phase 3 (4/4) |
| POSE | 5 | Phase 4 (5/5) |
| LLM | 8 | Phase 5 (8/8) |
| VIEW | 15 | Phase 6 (14/15) + Phase 7 (1/15) |
| REFRESH | 4 | Phase 8 (4/4) |
| ENDORSE | 3 | Phase 9 (3/3) |
| INFRA | 7 | Phase 5 (4/7) + Phase 6 (1/7) + Phase 8 (2/7) |

**Total v1 requirements:** 59
**Mapped to phases:** 59
**Unmapped:** 0 ✓

---
*Roadmap created: 2026-04-30*
*Granularity: fine*
*Ready for `/gmd:plan-phase 1`*
