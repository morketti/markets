# Stack Research

**Domain:** Personal stock research dashboard (single-user, keyless data plane, Claude routine compute)
**Researched:** 2026-04-30
**Confidence:** HIGH for backend libraries, MEDIUM for Claude routine specifics (verify limits at implementation)

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Python** | 3.12.x | Backend ingestion + analytical agents | Pandas/yfinance/pydantic ecosystem; Windows-friendly via official installer |
| **yfinance** | 0.2.x latest | Prices, fundamentals, options, analyst snapshot | No API key, scrapes Yahoo, ~95% reliability for US large-caps. The most-used keyless source. |
| **pandas-ta** | 0.3.14b+ | Technical indicators (RSI, BB, stochastic, Williams %R, MACD, ADX) | **Pure-Python — no C dependency.** Avoids ta-lib's brutal Windows install. Slightly slower than ta-lib on huge datasets but irrelevant for 50-ticker watchlist. |
| **feedparser** | 6.0.x | RSS aggregation (Yahoo, Google News, FinViz, press wires) | The de-facto Python RSS lib; handles Atom + RSS variants; rock-solid since 2003 |
| **requests** | 2.32+ | EDGAR + Reddit RSS fetching | Standard. Use `urllib3.Retry` for resilience. EDGAR requires `User-Agent: <name> <email>` header (legal requirement, enforced) |
| **pydantic** | 2.10+ | Schema validation for AgentState + JSON outputs | v2 is significantly faster than v1; required for typed LLM output validation |
| **Claude Code routines** | (Anthropic feature) | Scheduled compute orchestrator | Runs from user's Claude subscription — no Anthropic API key needed. Confirm availability + quota on user's plan at implementation. |
| **React** | 19.x | Frontend UI | User-specified. Concurrent rendering helps with chart-heavy dashboards. |
| **Vite** | 6.x | Frontend build tool | Lightning-fast dev server; static build trivially deployable to Vercel; better than Next.js for our use (no SSR needed — we read static JSON from GitHub raw) |
| **TypeScript** | 5.6+ | Frontend types | Catches API-shape drift between Python output and React consumption — critical for our typed signal payloads |
| **TailwindCSS** | 4.x | Styling | Fast iteration, dark theme trivial via `dark:` variants, mobile-responsive utilities built-in |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **lightweight-charts** | 5.x (TradingView) | OHLC + volume + indicator overlays | Best-in-class for finance charts, free, ~50KB gzipped, much better than recharts for candlesticks |
| **recharts** | 2.x | Simple charts (signal trend lines, conviction bars, persona consensus over time) | Use alongside lightweight-charts for non-OHLC charts where it shines |
| **date-fns** | 3.x | Date math (market days, snapshot timestamps) | Tree-shakeable, avoid moment.js (legacy, large) |
| **zod** | 3.x | TypeScript runtime schema validation on the frontend | Validate JSON read from `raw.githubusercontent.com` matches expected shape — catches Python-side schema drift |
| **python-dateutil** | 2.9+ | Backend date parsing | EDGAR + RSS feed dates are inconsistent; this normalizes them |
| **httpx** | 0.27+ | Optional async fetcher for parallel data ingestion | Drop-in for `requests` if/when we want parallel ticker fetches |
| **ratelimit** | 2.2+ | Decorator-based rate limiting for yfinance/EDGAR calls | Prevents accidental quota burn or IP bans |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **uv** | Python package manager | 10-100x faster than pip; replaces `requirements.txt` with `pyproject.toml` + lockfile. Strongly recommend over pip/poetry. |
| **ruff** | Lint + format Python | Replaces flake8 + black + isort. Single config, blazing fast. |
| **pnpm** | Frontend package manager | Faster than npm, smaller node_modules via content-addressable store |
| **biome** | TypeScript lint + format | Replaces ESLint + Prettier; single binary, fast |
| **pytest** | Backend testing | Standard; use with `pytest-asyncio` if we add async fetchers |
| **vitest** | Frontend testing | Native Vite integration; pairs with React Testing Library |

## Installation

```bash
# Backend (Python)
uv init
uv add yfinance pandas-ta feedparser requests pydantic python-dateutil ratelimit
uv add --dev ruff pytest

# Frontend (React)
pnpm create vite frontend --template react-ts
cd frontend
pnpm add lightweight-charts recharts date-fns zod tailwindcss@next
pnpm add -D biome vitest @testing-library/react

# Mid-day refresh function (Vercel)
# Defined inline in api/refresh.py at repo root — Vercel auto-detects Python runtime
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| **yfinance** | yahooquery | If yfinance breaks and yahooquery's separate scraping path still works — keep as fallback dependency |
| **yfinance** | openbb-platform | If/when you want a unified financial data SDK with paid sources later — overkill for v1 keyless scope |
| **pandas-ta** | ta-lib | If you need maximum performance on multi-thousand ticker scans and have build-tools installed (Linux/macOS preferred) |
| **pandas-ta** | talipp | If you need streaming incremental indicators (one tick at a time) — irrelevant for batch processing |
| **Vite** | Next.js | If you ever need server-side rendering or API routes co-located — currently no need |
| **lightweight-charts** | apexcharts | If you want fancier interactivity (annotations, drag-to-zoom across panes) at the cost of bundle size |
| **Claude Code routines** | GitHub Actions cron + Anthropic API key | If routines aren't available on your plan or quota is too tight — fallback path |
| **uv** | poetry | Existing poetry users; uv is meaningfully faster but newer |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **ta-lib (C bindings)** | Brutal Windows install, build-tools required, frequent ABI breaks | pandas-ta (pure Python) |
| **LangChain / LangGraph** | Requires LLM provider keys; we explicitly run keyless via Claude routines | Claude routine as the orchestrator + plain Python for analytical agents |
| **alpaca-trade-api** | Trading-focused; pulls in dependencies we don't need; we don't trade | yfinance for data, no trade execution at all |
| **moment.js (frontend)** | Legacy, ~70KB, mutable API, deprecated | date-fns |
| **PRAW for Reddit** | Requires Reddit OAuth credentials | Anonymous old.reddit.com RSS endpoints (e.g. `https://old.reddit.com/r/wallstreetbets/.rss`) |
| **Next.js SSR for this project** | Adds runtime server we don't need; complicates Vercel deploy with static GitHub raw reads | Vite static build — read JSON directly from `raw.githubusercontent.com` |
| **MongoDB / Postgres for v1** | Extra infra to deploy and maintain | GitHub repo as the database (each snapshot is a JSON file). Migrate to Supabase only if cross-day analytics become a v2 need. |
| **Anthropic SDK / API key** | We explicitly chose keyless via Claude routines | Claude routines run from user's subscription quota |
| **tweepy / X API** | Paid since 2023, ~$100/month minimum | Reddit RSS + StockTwits unauthenticated trending as social proxy |
| **websockets / SSE for v1** | Premature for hybrid-batch architecture; on-open refresh suffices | Plain HTTP fetch on dashboard open |

## Stack Patterns by Variant

**If yfinance breaks for a ticker (transient):**
- Detect: `yf.Ticker("X").history(period="1d")` returns empty
- Fallback: try yahooquery (`Ticker("X").history(period="1d")`)
- Persistent: cache last successful fetch, surface staleness badge in UI, mark ticker as `data_unavailable: true` in snapshot

**If a ticker is foreign / illiquid (yfinance fundamentals patchy):**
- Skip Buffett/Munger personas (their analysis depends on clean fundamentals — they'll return `neutral, confidence=20, "Insufficient data"`)
- Surface a UI badge: "Limited fundamental data — short-term signals only"

**If Claude routine quota tightens:**
- Reduce persona slate per ticker (run fewer agents)
- Skip the Open Claude Analyst step (lowest-priority persona)
- Fall back to deterministic-only signals (no LLM synthesis)

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| yfinance 0.2.x | pandas 2.x | Required since 0.2.40 — yfinance dropped pandas 1.x support |
| pandas-ta 0.3.14b+ | pandas 2.x, numpy 2.x | numpy 2.x compatibility added late — pin floor at 0.3.14b |
| pydantic 2.x | Python ≥ 3.9 | We're on 3.12; no concern |
| React 19 | TypeScript ≥ 5.4 | New JSX transform requires recent TS |
| lightweight-charts 5.x | React 18+ via official react wrapper | Or use directly with refs (more flexible) |

## Sources

- yfinance: GitHub `ranaroussi/yfinance` — active issues, breakage history (verify "broken" issues at implementation)
- SEC EDGAR: official developer docs at `sec.gov/os/accessing-edgar-data` — User-Agent rules
- pandas-ta: GitHub `twopirllc/pandas-ta` — confirm latest beta is stable
- Claude Code routines: Anthropic docs (verify availability on user's plan + quota at implementation time)
- Reference repo `virattt/ai-hedge-fund/requirements.txt`: confirms LangChain/Anthropic dependency we explicitly drop
- Reference repo `TauricResearch/TradingAgents`: confirms yfinance use for keyless data

---
*Stack research for: personal stock research dashboard*
*Researched: 2026-04-30*
