# Architecture Research

**Domain:** Personal stock research dashboard with keyless data plane and Claude-routine compute
**Researched:** 2026-04-30
**Confidence:** HIGH on patterns (validated against virattt + TradingAgents references), MEDIUM on Claude routine specifics (verify constraints at implementation)

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (static)                             │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  React + Vite, deployed on Vercel                                │ │
│  │  Reads JSON snapshots from raw.githubusercontent.com             │ │
│  │  - Morning scan (3 lenses)                                       │ │
│  │  - Per-ticker deep-dive                                          │ │
│  │  - Decision-support view                                         │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│              │                                  │                     │
│              ▼                                  ▼                     │
├──────────────────────────────────────────────────────────────────────┤
│                       READ PATHS                                      │
│  ┌──────────────────────────┐    ┌──────────────────────────────┐   │
│  │  Static reads             │    │  On-open refresh             │   │
│  │  raw.githubusercontent    │    │  Vercel serverless function  │   │
│  │  /data/YYYY-MM-DD/X.json  │    │  → keyless yfinance + RSS    │   │
│  │  (yesterday's full state) │    │  (current price + new news)  │   │
│  └──────────────────────────┘    └──────────────────────────────┘   │
├──────────────────────────────────────────────────────────────────────┤
│                  COMPUTE — MORNING BATCH                              │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  Scheduled Claude Code routine (6am ET, weekdays)                │ │
│  │                                                                   │ │
│  │  ┌───────────┐    ┌────────────┐    ┌──────────────────────┐    │ │
│  │  │ ingestion │───>│ analytical │───>│ persona LLM agents   │    │ │
│  │  │ (Python)  │    │ agents     │    │ (Claude reads        │    │ │
│  │  │  yfinance │    │ (Python    │    │  prompts/personas/*) │    │ │
│  │  │  EDGAR    │    │  scoring)  │    │                      │    │ │
│  │  │  RSS      │    │  fund/tech │    │  Buffett, Munger,    │    │ │
│  │  │           │    │  /sentim/  │    │  Wood, Burry, Lynch, │    │ │
│  │  │           │    │  position- │    │  Open Claude Analyst │    │ │
│  │  │           │    │  adjust/   │    │                      │    │ │
│  │  │           │    │  valuation │    │                      │    │ │
│  │  └───────────┘    └────────────┘    └──────────────────────┘    │ │
│  │                                                  │                │ │
│  │                                                  ▼                │ │
│  │                                         ┌──────────────┐         │ │
│  │                                         │ synthesizer  │         │ │
│  │                                         │ (Claude)     │         │ │
│  │                                         │ buy/trim/    │         │ │
│  │                                         │ hold + dual- │         │ │
│  │                                         │ timeframe    │         │ │
│  │                                         └──────┬───────┘         │ │
│  │                                                ▼                  │ │
│  │                                        git commit + push          │ │
│  └─────────────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────┤
│                  STORAGE — GitHub repo                                │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  data/                                                         │   │
│  │    YYYY-MM-DD/                                                 │   │
│  │      AAPL.json   ← full TickerDecision per ticker per day      │   │
│  │      MSFT.json                                                 │   │
│  │      _index.json ← {tickers, generated_at, run_metadata}       │   │
│  │  watchlist.json   ← {ticker: TickerConfig}                     │   │
│  │  endorsements.jsonl ← append-only log                          │   │
│  │  memory/                                                       │   │
│  │    historical_signals.jsonl  ← per-ticker per-persona log      │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| **ingestion/** (Python pkg) | Fetch raw data — prices/fundamentals (yfinance), filings (EDGAR), news (RSS), social (Reddit RSS, StockTwits) | One module per source; emits typed Pydantic objects; rate-limited |
| **analysts/** (Python pkg) | Deterministic scoring — fundamentals, technicals, news/sentiment, position-adjustment, valuation | One module per agent; pure functions returning `AgentSignal` |
| **prompts/personas/*.md** | LLM prompt templates for persona analysis | Markdown files; loaded by routine entrypoint at runtime |
| **prompts/synthesizer.md** | Synthesizer prompt for per-ticker buy/trim/hold decision | Single markdown file; takes all analyst signals + per-ticker config |
| **routine/** | Claude Code routine config + entrypoint orchestration script | Routine config (cron schedule, prompt) + `routine_entrypoint.py` that drives the flow |
| **frontend/** | Static React app reading from GitHub raw + on-open refresh | Vite-built static bundle deployed to Vercel |
| **api/refresh.py** | Vercel serverless function for on-open refresh — keyless price + recent news fetch | Python runtime; no LLM; ~20 line handler |
| **data/** (in repo) | Daily JSON snapshots — single source of truth read by frontend | Per-day folder, per-ticker JSON, plus index |
| **memory/** (in repo) | Append-only logs for historical signals + endorsement performance | JSONL files; reflection step amends them |

## Recommended Project Structure

```
markets/
├── .planning/                    # GMD planning docs
│   ├── PROJECT.md
│   ├── REQUIREMENTS.md
│   ├── ROADMAP.md
│   ├── STATE.md
│   ├── config.json
│   └── research/                 # this dir
├── ingestion/                    # Python — keyless data fetchers
│   ├── __init__.py
│   ├── prices.py                 # yfinance prices, OHLC, options chain
│   ├── fundamentals.py           # yfinance fundamentals, ratios
│   ├── filings.py                # SEC EDGAR — 10-K, 10-Q, 8-K, Form 4
│   ├── news_rss.py               # RSS aggregation — Yahoo, Google, FinViz, press wires
│   ├── social.py                 # Reddit RSS, StockTwits trending
│   └── schemas.py                # Pydantic models for raw data
├── analysts/                     # Python — deterministic scoring
│   ├── __init__.py
│   ├── fundamentals.py           # P/E, P/S, ROE, debt/equity scoring
│   ├── technicals.py             # MA, RSI, support/resistance, momentum
│   ├── news_sentiment.py         # RSS dedup + recency + naive sentiment scoring (LLM-aware)
│   ├── position_adjustment.py    # multi-indicator oversold/overbought consensus
│   ├── valuation.py              # current vs thesis, vs analyst consensus
│   └── schemas.py                # AgentSignal, TickerDecision, etc.
├── prompts/                      # Markdown — easily iterated, no code change
│   ├── personas/
│   │   ├── buffett.md
│   │   ├── munger.md
│   │   ├── wood.md
│   │   ├── burry.md
│   │   ├── lynch.md
│   │   └── claude_analyst.md     # the "open" persona — Claude unboxed
│   └── synthesizer.md            # final per-ticker decision prompt
├── routine/
│   ├── routine.json              # Claude Code routine config (schedule, prompt)
│   └── entrypoint.py             # orchestration script invoked by routine prompt
├── frontend/
│   ├── src/
│   │   ├── pages/                # MorningScan, TickerDetail, Decision
│   │   ├── components/           # WatchlistTable, ChartCanvas, SignalCard, etc.
│   │   ├── lib/                  # data fetchers (raw.githubusercontent), date utils, schema validators
│   │   └── styles/
│   ├── index.html
│   ├── vite.config.ts
│   └── package.json
├── api/
│   └── refresh.py                # Vercel serverless function — on-open refresh
├── data/                         # daily snapshots (committed by routine)
│   └── YYYY-MM-DD/
│       ├── _index.json
│       ├── AAPL.json
│       └── ...
├── memory/                       # append-only logs
│   ├── historical_signals.jsonl
│   └── endorsement_performance.jsonl
├── watchlist.json                # source of truth for watchlist + per-ticker config
├── endorsements.jsonl            # user-fed newsletter calls (append-only)
├── pyproject.toml                # uv-managed Python deps
├── vercel.json                   # Vercel deploy config
└── README.md
```

### Structure Rationale

- **`ingestion/` and `analysts/` are separate Python packages** so analysts only depend on `ingestion.schemas`, not on the network — analysts are pure functions, easy to test in isolation.
- **Persona prompts live as markdown, not Python strings** — iterate prompts without touching code; version them in git for free A/B comparison.
- **`routine/entrypoint.py` is short** — its job is to load the persona prompt files, call analysts, ask Claude to apply each persona, then call the synthesizer. The routine config (`routine.json`) just invokes this entrypoint.
- **`data/` is in the same repo for v1** — simpler than a separate `markets-data` repo. Migrate to a separate repo if data volume gets noisy in commit history (likely after 6+ months at 50 tickers/day).
- **`api/refresh.py` at repo root** — Vercel auto-detects this as a Python serverless function. No separate refresh-app to deploy.
- **`memory/` as JSONL not SQLite** — readable in git diffs, no binary blobs, easy to inspect; if perf becomes an issue at v2, migrate to SQLite committed-with-WAL or move to Supabase.

## Architectural Patterns

### Pattern 1: Two-Tier Agent (Adapted from virattt/ai-hedge-fund)

**What:** Separate persona LLM agents (subjective lens, markdown prompt) from analytical agents (objective metrics, deterministic Python scoring). Personas synthesize narrative; analyticals provide ground truth.

**When to use:** Always — this is the core architectural decision adopted from virattt.

**Trade-offs:** Pro — cheaper (LLM only synthesizes interpretation, not arithmetic), more reproducible, easier to test/debug analyticals. Con — two layers to maintain.

**Example flow per ticker:**
```python
# Pattern adapted from virattt/ai-hedge-fund/src/agents/warren_buffett.py
# Modified: data layer is keyless yfinance/EDGAR (no FINANCIAL_DATASETS_API_KEY);
# prompt is loaded from prompts/personas/buffett.md, not inline.

raw_data = ingestion.fetch_all(ticker)            # network
analytical = analysts.fundamentals.score(raw_data) # pure Python — moat, ROE, etc.
analytical_facts = compact(analytical)             # facts for LLM, not numbers
prompt = load_persona("buffett") + analytical_facts
buffett_signal = claude.respond(prompt, schema=AgentSignal)  # signal, confidence, reasoning
```

### Pattern 2: AgentState as Shared Context (Adapted from virattt's TypedDict)

**What:** A single TypedDict flows through every agent, accumulating signals and metadata. Each agent reads what it needs and writes its slice.

**When to use:** Always — keeps function signatures clean and matches the LangGraph mental model without requiring LangGraph.

**Trade-offs:** Pro — uniform shape, easy to serialize for snapshots. Con — risk of mutation bugs (mitigate with Pydantic + clear write-only zones per agent).

**Concrete shape:**
```python
# Pattern adapted from virattt/ai-hedge-fund/src/graph/state.py
# Modified: added watchlist_metadata, historical_signals, endorsements, dual-timeframe TickerDecision

from typing import TypedDict, Literal, Optional
from pydantic import BaseModel

class AgentSignal(BaseModel):
    signal: Literal["bullish", "bearish", "neutral"]
    confidence: int  # 0-100
    reasoning: str   # ≤ 200 chars
    evidence: list[str]  # bullet points for UI rendering

class PositionAdjustment(BaseModel):
    state: Literal["extreme_oversold", "oversold", "fair", "overbought", "extreme_overbought"]
    consensus_score: float  # -1 to +1
    confidence: int
    evidence: list[str]
    action_hint: Literal["consider_add", "hold_position", "consider_trim", "consider_take_profits"]

class ShortTermSignal(BaseModel):
    signal: Literal["bullish", "bearish", "neutral"]
    confidence: int
    timeframe: Literal["1-30d", "30-90d"]
    drivers: list[str]
    position_adjustment: PositionAdjustment

class LongTermSignal(BaseModel):
    signal: Literal["bullish", "bearish", "neutral"]
    confidence: int
    thesis_status: Literal["intact", "weakening", "broken", "validating"]
    drivers: list[str]
    buy_range: Optional["BuyRange"]

class Recommendation(BaseModel):
    short_term_action: Literal["add", "trim", "hold", "take_profits", "watch"]
    long_term_action: Literal["buy", "trim", "hold", "avoid"]
    conviction: Literal["low", "medium", "high"]

class TickerDecision(BaseModel):
    ticker: str
    price: float
    short_term: ShortTermSignal
    long_term: LongTermSignal
    open_observation: Optional[str]   # Open Claude Analyst's off-script take
    recommendation: Recommendation
    persona_signals: dict[str, AgentSignal]  # {persona_id: signal}
    analytical_signals: dict[str, AgentSignal]
    snapshot_date: str  # ISO date
    generated_at: str   # ISO timestamp

class TickerConfig(BaseModel):
    ticker: str
    short_term_focus: bool = True
    long_term_lens: Literal["value", "growth", "contrarian", "mixed"] = "mixed"
    thesis_price: Optional[float] = None
    technical_levels: Optional["TechnicalLevels"] = None
    target_multiples: Optional["FundamentalTargets"] = None
    notes: str = ""

class AgentState(TypedDict):
    """Run-scoped state passed through all agents."""
    tickers: list[str]
    end_date: str
    watchlist_metadata: dict[str, TickerConfig]
    raw: dict[str, dict]                       # per-ticker raw data
    analyst_signals: dict[str, dict[str, AgentSignal]]  # {agent_id: {ticker: signal}}
    endorsements: list["Endorsement"]
    historical_signals: dict[str, list["HistoricalSignal"]]
    decisions: dict[str, TickerDecision]
    metadata: "RunMetadata"
```

### Pattern 3: Synthesizer with Deterministic Pre-Filter (Adapted from virattt's PortfolioManager)

**What:** Before asking the LLM to recommend buy/trim/hold, deterministically compute "is this in the buy range" / "what's the position-adjustment state." Pass facts + constraints to LLM; it picks the recommendation with reasoning.

**When to use:** Always at the synthesis step.

**Trade-offs:** Pro — LLM doesn't have to do arithmetic; output is more reliable. Con — synthesizer prompt must clearly enumerate the deterministic facts.

**Example:**
```python
# Pattern adapted from virattt/ai-hedge-fund/src/agents/portfolio_manager.py
# Modified: outputs buy/trim/hold (no shares), dual-timeframe, conviction band.
# We do NOT compute portfolio math (cash, margin) — research tool, not trade tool.

deterministic_facts = {
    "ticker": "AAPL",
    "price": 185.32,
    "buy_range_status": "above_range",  # from buy_range agent
    "position_adjustment": {"state": "fair", "consensus_score": 0.1, ...},
    "thesis_price_distance": "+8.2% above thesis price",
    "persona_consensus": {"bullish": 2, "bearish": 1, "neutral": 3},
    "analytical_consensus": {...},
    "long_term_lens": "growth",
}
prompt = load("synthesizer.md") + json.dumps(deterministic_facts)
decision = claude.respond(prompt, schema=Recommendation)
```

## Data Flow

### Morning-Batch Flow (Scheduled Claude Routine, 6am ET weekdays)

```
1. Routine fires at 06:00 ET
2. Routine prompt instructs Claude:
   - Run `python -m routine.entrypoint --batch` (deterministic data + analyticals)
       - For each ticker in watchlist.json:
           - ingestion.fetch_all(ticker) → raw data
           - For each analytical agent (fundamentals, technicals, ...): score(raw_data)
           - Write partial state to /tmp/state-{date}.json
   - For each ticker × persona, Claude:
       - Reads prompts/personas/{persona}.md
       - Reads /tmp/state-{date}.json[ticker]
       - Applies persona; outputs structured AgentSignal JSON; writes to state
   - Run `python -m routine.entrypoint --synthesize` (deterministic pre-filter)
   - For each ticker, Claude:
       - Reads prompts/synthesizer.md + ticker's signals + facts
       - Outputs TickerDecision JSON
   - Run `python -m routine.entrypoint --persist`:
       - Writes data/YYYY-MM-DD/{ticker}.json per ticker
       - Writes data/YYYY-MM-DD/_index.json
       - Appends to memory/historical_signals.jsonl
       - git add data/ memory/ && git commit -m "snapshot YYYY-MM-DD" && git push
```

### Deep-Dive Flow (User opens ticker in browser)

```
1. User clicks ticker in watchlist on dashboard
2. Frontend fetches:
   - data/YYYY-MM-DD/AAPL.json (latest snapshot — yesterday morning's full state)
   - api/refresh?ticker=AAPL (current price + headlines since snapshot)
3. Vercel function (api/refresh.py):
   - yfinance.Ticker(AAPL).history(period="1d")  → current price
   - feedparser RSS for AAPL → headlines published since snapshot timestamp
   - Returns merged JSON; no LLM calls
4. Frontend renders:
   - Top: dual-timeframe cards (short_term + long_term), recommendation banner
   - Middle: persona signals, technical chart, news feed
   - Bottom: Open Claude Analyst observation, drivers
   - Staleness badge if api/refresh failed or snapshot older than expected
```

### Decision-Support Flow (User asks "should I buy/trim X today")

```
v1: User opens decision view; reads from latest snapshot's recommendation field.
    No additional compute — synthesizer ran at morning batch.

v1.x (optional later): Manual "re-synthesize" button triggers a focused recompute:
    - Fires routine in on-demand mode for one ticker
    - Re-fetches data, reruns persona+synth for that ticker only
    - Commits a new entry: data/YYYY-MM-DD/_ondemand/{ticker}-HHMM.json
    - Frontend shows ondemand version if newer than morning snapshot
```

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1 user × 30-50 tickers (current target) | Architecture as described — fits within Claude routine quota; GitHub raw reads fine |
| 1 user × 100-200 tickers | Routine may hit time/quota; consider tiered analysis (full synth for top-N most-changed tickers, lite analysis for rest) |
| 1 user × 500+ tickers | GitHub-as-DB starts hurting; migrate snapshots to Supabase or split into separate `markets-data` repo |
| Multi-user (out of scope) | Would require auth, multi-tenant data isolation — fundamental redesign |

### Scaling Priorities

1. **First bottleneck: Claude routine token quota.** If we run out of subscription quota mid-batch, the snapshot is incomplete. Mitigation: prioritize watchlist by recency-of-news + position-adjustment-extremity; skip personas for tickers in `fair` state with no news.
2. **Second bottleneck: yfinance rate limiting.** ~50 tickers serial fetch is fine; if we add concurrency carelessly we get IP-banned. Use `ratelimit` decorator at ≤10 req/sec.
3. **Third bottleneck: GitHub-raw read latency on snapshot fetch.** ~30s after commit before raw URL hits. Mitigation: include `_index.json` with `committed_at` timestamp; frontend retries gracefully.

## Anti-Patterns

### Anti-Pattern 1: Adding LangGraph "Just to Be Safe"

**What people do:** Adopt LangGraph because virattt + TradingAgents both use it.
**Why it's wrong:** LangGraph requires LLM provider keys — incompatible with our keyless-via-Claude-routine choice. Plus it's overkill for our linear pipeline (no debate state, no conditional routing in v1).
**Do this instead:** Claude routine as the orchestrator. The routine prompt walks Claude through the same conceptual graph.

### Anti-Pattern 2: Storing Snapshots in a Database from Day One

**What people do:** Set up Supabase / Postgres for "scalability."
**Why it's wrong:** Adds infra to deploy and maintain; you don't have evidence yet that GitHub-as-DB hurts at this scale; commit history is free version control.
**Do this instead:** GitHub repo. Migrate to Supabase only when you have evidence (commit noise, query patterns that need SQL, multi-day analytics).

### Anti-Pattern 3: Hardcoding Persona Prompts in Python

**What people do:** Put the persona prompt as a Python string literal in the agent file (this is what virattt does).
**Why it's wrong:** Iteration requires code changes; can't version persona-only changes; can't easily A/B test prompts.
**Do this instead:** Markdown files in `prompts/personas/`. Load at runtime. Iterate by editing the .md file.

### Anti-Pattern 4: Letting the LLM Do Arithmetic

**What people do:** Pass raw financials to the LLM and ask "is this overvalued."
**Why it's wrong:** LLMs hallucinate numbers; reproducibility is poor; cost is higher (more tokens for math reasoning).
**Do this instead:** Compute scores deterministically in Python; pass *facts* (not numbers) to the LLM. The LLM synthesizes, doesn't calculate.

### Anti-Pattern 5: Real-Time Streaming for a Research Tool

**What people do:** WebSockets/SSE so prices update live.
**Why it's wrong:** Burns server-running infra; doesn't fit the morning-research workflow; yfinance 15-20min delay is fine for research decisions.
**Do this instead:** On-open refresh function. Stale-by-design with clear staleness badges.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Yahoo Finance (via yfinance) | Library wrap, rate-limited | TOS gray area for commercial use; fine for personal. Cache aggressively. |
| SEC EDGAR | HTTP GET with `User-Agent: <name> <email>` header | **Required** by SEC; emails actually checked when usage is unusual. Hardcode user's email in agent. |
| Reddit | RSS via `https://old.reddit.com/r/X/.rss` and `/search.rss?q=ticker` | No auth needed; old.reddit endpoints; check rate limits |
| Google News per-ticker | RSS via `https://news.google.com/rss/search?q=TICKER+stock` | Free; encoding quirks — use feedparser |
| StockTwits | Unauthenticated trending endpoint | Fragile but free; treat as bonus signal |
| GitHub (storage) | git push from routine; raw.githubusercontent.com reads | Token in routine env for push; CDN caching means ~30s delay before frontend sees new commits |
| Vercel (frontend + refresh fn) | git-driven deploy of frontend, Python runtime for refresh fn | Free tier is fine for personal use |
| Anthropic (LLM) | **Claude Code routine** — runs from user's subscription, NOT API | Verify availability + quota at implementation |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| ingestion ↔ analysts | Direct Python imports; ingestion returns Pydantic objects | Pure data dependency; analysts don't reach out to network |
| analysts ↔ persona prompts | analysts compute scoring, write into AgentState; routine entrypoint passes compact facts to Claude | Personas never see raw numbers, only "fact summaries" |
| routine ↔ data store | Routine commits to data/ via git; frontend reads from raw | One-way; frontend never writes |
| frontend ↔ refresh fn | HTTP fetch from frontend; refresh fn returns JSON | Stateless function; no shared state with batch |

## Sources

- `virattt/ai-hedge-fund` reference repo — agent state pattern, persona/analytical split, synthesizer
- `TauricResearch/TradingAgents` reference repo — memory log + reflection, yfinance use, JSON state persistence
- Anthropic Claude Code documentation — routine constraints (verify at implementation)
- Vercel docs — Python serverless function constraints (10s timeout on free tier)
- SEC EDGAR developer docs — User-Agent compliance

---
*Architecture research for: personal stock research dashboard*
*Researched: 2026-04-30*
