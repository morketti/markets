# Pitfalls Research

**Domain:** Personal stock research dashboard with keyless data, Claude routine compute, dual-timeframe outputs
**Researched:** 2026-04-30
**Confidence:** HIGH (pitfalls grounded in reference-repo bugs, known scraper history, and finance-domain experience)

## Critical Pitfalls

### Pitfall 1: yfinance Silently Returns Empty / Wrong Data

**What goes wrong:**
yfinance scrapes Yahoo's HTML/JSON endpoints. When Yahoo changes a layout or a field, yfinance returns empty DataFrames, `None` values, or worse — partially correct data with one column shifted. The morning batch produces a "successful" snapshot that is actually wrong.

**Why it happens:**
yfinance has no SLA and no schema validation between calls. Issues are typically fixed in the library within 1-7 days, but during that window your snapshot looks normal but isn't.

**How to avoid:**
- Pin a known-good yfinance version; treat upgrades as code changes (test before merging)
- After every fetch, run a sanity-check assertion: price > 0, market_cap > 0 if present, fundamentals dict has expected keys
- If sanity check fails, mark ticker as `data_unavailable: true` in snapshot — frontend renders "Limited data — refresh later" rather than wrong analysis
- Keep `yahooquery` as a parallel fallback path for prices specifically; if yfinance returns empty, try yahooquery before giving up
- Subscribe to yfinance GitHub issues/releases via RSS; periodic check for "Yahoo broke X" reports

**Warning signs:**
- Sudden empty `info` dicts on previously-working tickers
- All historical prices returning as zero or NaN
- Fundamentals dict missing keys you used yesterday
- Unusual error logs in routine output

**Phase to address:**
Phase 2 (data plane) — sanity-check assertions baked into ingestion from day one. Phase 4+ — fallback path to yahooquery for prices.

---

### Pitfall 2: SEC EDGAR User-Agent Compliance Violation → IP Block

**What goes wrong:**
SEC requires every EDGAR request to include a `User-Agent: <name> <email>` header. Without it, requests fail; with a generic one, your IP can be rate-limited or blocked. Block can persist hours.

**Why it happens:**
Many scrape tutorials don't mention the rule; default `requests` User-Agent gets flagged.

**How to avoid:**
- Hardcode a `User-Agent: Markets Research mohanraval15@gmail.com` header in the EDGAR fetcher
- Respect the documented rate limit: ≤10 req/sec across all your processes
- Use exponential backoff on 429 / 403 responses
- Log first request of every batch run to confirm header is present (catch regressions)

**Warning signs:**
- 403 responses from EDGAR
- "Your access has been temporarily blocked" page returned as HTML body of a 200 response (yes, they do this)
- Requests slowing dramatically without obvious reason

**Phase to address:**
Phase 2 — implement compliantly from day one; never as an afterthought.

---

### Pitfall 3: Claude Routine Quota Burnout Mid-Batch

**What goes wrong:**
Routine fires at 6am, runs through 30 tickers, then hits user's subscription token cap on ticker 31. Snapshot is partial; frontend shows "missing analysis" for the last 19 tickers. Next day same thing happens for the same tickers.

**Why it happens:**
Per-ticker token cost is non-trivial: 6 personas × ~2K tokens out + 1 synth × ~3K tokens = ~15K tokens per ticker. 50 tickers × 15K = 750K tokens. User's plan limit may be lower than this, or the day's prior usage already ate the budget.

**How to avoid:**
- **Prioritize the watchlist** — process tickers most likely to need fresh analysis first (sorted by: recency of news, position-adjustment extremity yesterday, days-since-analyzed). If quota dies, the boring tickers are the ones missing.
- **Skip personas for fair-state, no-news tickers** — emit a "no change" decision deterministically; saves ~12K tokens per ticker
- **Trim persona slate dynamically** — if quota tight, drop the Open Claude Analyst step (it's the lowest-priority — analyticals + 5 personas still produce a decision)
- **Estimate before committing** — log estimated token cost at start of run; if it exceeds available quota, run in lite mode (analyticals only, no LLM personas)
- **Emit `quota_exhausted: true` in `_index.json`** — frontend surfaces "partial snapshot — N of M tickers analyzed today"

**Warning signs:**
- Routine logs show ratelimit/quota errors after partial completion
- Some tickers in today's `data/YYYY-MM-DD/` folder, others missing
- LLM responses cut off mid-JSON (parse failures)

**Phase to address:**
Phase 5 (routine wiring) — quota-aware orchestration designed in. Phase 8 (resilience) — graceful degradation modes.

**Non-obvious:** Easy to discover only in production with full watchlist on a low-quota day.

---

### Pitfall 4: LLM Output Schema Drift on Model Upgrades

**What goes wrong:**
Claude is upgraded silently (Sonnet 4.6 → 4.7, etc.). Persona prompts that worked yesterday now produce slightly different JSON shapes — extra wrapper keys, different field names, prose instead of JSON, or markdown code fences around JSON. Synthesizer chokes; snapshot fails.

**Why it happens:**
Model behavior shifts between versions; prompts that relied on undocumented model behavior break.

**How to avoid:**
- **Pydantic-validate every LLM response** before storing or passing downstream
- **Wrap each LLM call with a `default_factory`** (adopted from virattt's `call_llm`) — on schema validation failure, return a known-good default (`signal=neutral, confidence=0, reasoning="schema_failure"`)
- **Log the raw LLM response to `memory/llm_failures.jsonl`** when validation fails — diagnose without re-running
- **Use Pydantic v2 `model_validate_json()` rather than parse-then-validate** — better error messages
- **Pin model version in routine config** when possible; do a manual test run after any forced model upgrade

**Warning signs:**
- New entries in `memory/llm_failures.jsonl` after a previously-stable run
- Snapshots show many `"reasoning": "schema_failure"` entries
- Frontend renders "Insufficient data" badges on tickers that worked yesterday

**Phase to address:**
Phase 5 (routine + persona wiring) — Pydantic validation + default_factory pattern is mandatory in the persona invocation utility.

---

### Pitfall 5: Endorsement Performance Math Breaks on Corp Actions

**What goes wrong:**
User enters: "X newsletter recommended AAPL on 2024-01-15 at $185." Two months later: AAPL splits 4:1. Now the price-at-call vs current-price math says AAPL "dropped 75%" overnight. User loses trust.

**Why it happens:**
Naive `(current - price_at_call) / price_at_call` doesn't account for splits, spin-offs, special dividends, or currency for foreign listings.

**How to avoid:**
- Use yfinance's `auto_adjust=True` and `.history(actions=True)` — Yahoo provides split/dividend-adjusted historical prices that are comparable
- Store endorsements as `(ticker, date, price_at_call_unadjusted, source)` — recompute "performance vs S&P" on-demand from adjusted history each run
- For foreign listings, also store currency; convert to USD with daily FX rate
- Surface alerts in UI when an endorsement's underlying ticker has had a corp action since the call ("AAPL split 4:1 on 2024-08-30 — adjusted comparison applies")

**Warning signs:**
- Endorsement showing dramatic single-day swing in performance
- User reports "this performance number looks wrong"
- Performance math returning negative numbers consistently

**Phase to address:**
Phase 7+ (endorsement layer) — this layer is non-trivial; should not ship in MVP. Defer to v1.x.

---

### Pitfall 6: Position-Adjustment Indicator False Positives in Trending Markets

**What goes wrong:**
RSI says "oversold" for a stock in a powerful uptrend pulling back; user buys; trend resumes downward; user blames the dashboard. Or RSI says "overbought" for a stock in a powerful uptrend; user trims; stock keeps rising 30% over the next month.

**Why it happens:**
Single-indicator over-reliance. Mean-reversion indicators (RSI, Bollinger Bands, z-score) systematically misfire in trending markets. They work in range-bound markets.

**How to avoid:**
- **Multi-indicator consensus already designed** — require ≥3 of 6 indicators to agree before marking oversold/overbought
- **Weight by trend regime** — if ADX > 25 (strong trend), DOWN-weight mean-reversion indicators; UP-weight momentum
- **Surface confidence prominently** — a `consensus_score: 0.4` should look weak in UI, not "oversold"
- **Add an "extreme" tier** — only `extreme_oversold` / `extreme_overbought` triggers the strongest UI affordance; `oversold` is a hint not a recommendation
- **In synthesizer**, frame as "consider X" never "do X" — language matters

**Warning signs:**
- Backlog of "I trimmed because the radar said overbought, then it ran 20%" feedback
- Position-adjustment radar firing on the same trending names every day for weeks

**Phase to address:**
Phase 4 (analytical agents — position-adjustment) — multi-indicator consensus + trend-regime weighting designed in.

---

### Pitfall 7: Persona Prompt Drift Over Iteration

**What goes wrong:**
You tweak Buffett's prompt to be more concise. Three iterations later, "Buffett's" reasoning is generic markdown bullet points indistinguishable from any other persona. The persona slate's value collapses; user no longer trusts that the persona analysis is meaningfully different per persona.

**Why it happens:**
- Iteration toward "clarity" pushes prompts toward generic
- Prompt edits aren't tested against a fixed input baseline
- No A/B comparison against prior versions

**How to avoid:**
- **Version persona prompts in git** — every edit is a commit; `git diff prompts/personas/buffett.md` shows what changed
- **Maintain a "persona regression" test** — fixed AAPL data from a known date, run all 6 personas, compare outputs. If Buffett's output starts looking like Wood's, the prompt has drifted.
- **Each persona's prompt has a "voice signature" section** at the top — non-negotiable lines that anchor the persona ("Buffett: prioritize moat and margin of safety; conservative on growth assumptions; reject speculation")
- **Periodic "diff the personas" review** — read all 6 outputs side-by-side for the same ticker; if they sound the same, prompts need tightening

**Warning signs:**
- Outputs across personas converging in tone and verdict
- Confidence scores clustering at similar values across personas
- User says "all the personas are saying the same thing"

**Phase to address:**
Phase 5 (persona wiring) — voice signature + regression test set up from day one.

---

### Pitfall 8: UI Overload Killing the Morning-Scan

**What goes wrong:**
Dashboard shows 47 widgets. User opens it at 7am, sees a wall of info, closes browser. The product fails the "morning command center" job because it isn't scannable.

**Why it happens:**
Every signal feels valuable; designer adds it; nobody removes anything; 6 months in there are 47 things on the page.

**How to avoid:**
- **Morning scan defaults to ONE lens at a time** (position-adjustment / short-term opportunities / long-term thesis status) — toggle, not all-at-once
- **Three-row info hierarchy**: row 1 = ticker + price + recommendation badge (must-read); row 2 = drivers + confidence (skim); row 3 = persona detail (click-through)
- **No more than 5 signals visible per ticker on scan view** — everything else is in the deep-dive
- **Add features by removing first** — every new widget must replace something or earn its place via a "would I miss this if it was gone" test

**Warning signs:**
- User opens dashboard, scrolls less than 2 seconds, leaves
- "I check StockAnalysis instead in the morning"
- Each session involves "I have to find X" instead of "X is right there"

**Phase to address:**
Phase 6 (frontend MVP) — initial UI is intentionally minimal. Phase 9+ — every UI addition justified.

---

### Pitfall 9: Stale-Data UX Failure — Showing Yesterday's Data Without Saying So

**What goes wrong:**
The 6am routine fails (Yahoo breakage, quota exhausted, network issue). User opens dashboard at 8am; it cheerfully shows yesterday morning's snapshot as if it were fresh. User makes decisions on stale data.

**Why it happens:**
Default-renders the latest available snapshot without distinguishing "today" from "yesterday."

**How to avoid:**
- **Every visible card shows snapshot date** ("As of 2026-04-29 06:12 ET")
- **Staleness badge** in header: GREEN (today, < 6h old), AMBER (yesterday, partial), RED (>1 day old or batch failed)
- **Per-ticker on-open refresh** runs whenever a deep-dive opens — fetches current price + headlines, surfaces any divergence from snapshot
- **Routine emits a `_status.json`** at end of run: `{success: bool, partial: bool, missing_tickers: [...]}`. Frontend reads this for the staleness banner.

**Warning signs:**
- User reports decisions made on data that turned out to be stale
- Routine has been silently failing for days; no one noticed because frontend kept showing data

**Phase to address:**
Phase 6 (frontend) — staleness UX as a foundational design pattern, not retrofit.

---

### Pitfall 10: Premature Abstraction — Building the v3 We Imagine

**What goes wrong:**
"This might break later" leads to multi-layer plugin systems for ingestion sources, abstract base classes for personas, configuration-driven analyst weights. Months pass; v1 isn't shipped; abstractions don't fit the real shape of the problem when it finally emerges.

**Why it happens:**
Reference repos (virattt, TradingAgents) have abstractions appropriate for their multi-LLM-provider, multi-user-eventual-product. Cargo-culting those abstractions into our single-user keyless tool is overkill.

**How to avoid:**
- **YAGNI hard** — don't build a generic LLM-provider abstraction. Claude is the LLM. Done.
- **Don't build a generic data-source plugin system** — ingestion has 4 sources (yfinance/EDGAR/RSS/Reddit); just write 4 modules
- **Don't build a config-driven analyst-weight system** — analyst weights are simple constants in synthesizer.md; iterate by editing the prompt
- **Don't build a debate-state machine for personas** — they're independent single-pass; aggregate at synthesis. Add complexity only when concrete need emerges.
- **Three similar lines is better than premature abstraction** — wait for the fourth or fifth before extracting

**Warning signs:**
- More time on `BaseAgent` interfaces than on actual agents
- Configuration files growing faster than data files
- Functions with `**kwargs` everywhere

**Phase to address:**
All phases — this is ongoing discipline, not a single-phase concern.

---

### Pitfall 11: GitHub-as-DB Eventually Hurts

**What goes wrong:**
Daily snapshots × 50 tickers × 365 days = 18,250 JSON files in one repo after a year. `git log` slows; `data/` directory listing in IDE chokes; `git clone` takes minutes.

**Why it happens:**
GitHub-as-DB is great until the cumulative volume crosses a threshold.

**How to avoid:**
- **Migrate snapshots to a separate `markets-data` repo** when current repo's data folder reaches ~5K files
- **Or: roll up old snapshots** — after 90 days, compress per-month into `data/2026-01.tar.gz` and remove individual files
- **Or: migrate to Supabase** for snapshots + keep watchlist/config/prompts in main repo

**Warning signs:**
- `git status` slow
- Vercel build times growing
- IDE lag opening the repo

**Phase to address:**
Phase 8+ (resilience/scaling) — initially do nothing; revisit at 90-day mark.

---

### Pitfall 12: Self-Confirmation Bias via Lens Selection

**What goes wrong:**
User sets `long_term_lens: growth` for NVDA because they believe in NVDA's growth story. Wood persona always weighted heavy. Wood is reliably bullish on growth names. User reads "Wood says bullish" every morning, takes it as confirmation, never sees Burry's bearish dissent prominently.

**Why it happens:**
The per-ticker lens system, while powerful, can hide dissenting views.

**How to avoid:**
- **Synthesizer always surfaces the most-bearish persona's reasoning** as a "Dissent" section in the decision view, even when the lens is bullish-tilted
- **"Dissent strength" badge** — when ≥1 persona disagrees with the recommendation by ≥30 confidence points, the badge shows prominently
- **Open Claude Analyst is lens-agnostic** — its observation is generated without persona weighting, providing a neutral counter
- **Periodic "rotate the lens" review** — UI suggests trying a different lens for a ticker once a month, just to surface what changes

**Warning signs:**
- User has held conviction on losing position much longer than warranted
- All decision-views show "high conviction buy" for the user's favorites
- User reports "the dashboard tells me what I want to hear"

**Phase to address:**
Phase 7 (synthesizer + decision view) — dissent surfacing designed in, not bolted on later.

**Non-obvious:** Easy to discover only after months of use when an outcome reveals the bias.

---

### Pitfall 13: Unexpected Claude Subscription Reset Mid-Day

**What goes wrong:**
The 6am batch runs fine. User clicks "re-synthesize NVDA" at 2pm. Quota was already tight from the morning batch + a long Claude Code session for unrelated work; the on-demand recompute fails partway through.

**Why it happens:**
Subscription quota is shared across all Claude usage; a heavy non-finance day can leave nothing for routine on-demand calls.

**How to avoid:**
- **Don't promise on-demand recompute in v1** — only in v1.x with explicit "this may use your daily quota" warning
- **Surface a routine `_status.json` quota field** if Anthropic exposes it: "morning batch used X% of daily quota"
- **Cache the latest morning synth aggressively** — most decisions can be made on this; on-demand is only for "something material happened today"

**Warning signs:**
- Quota errors on on-demand calls
- User opens dashboard, gets "decision unavailable" for a ticker that worked this morning

**Phase to address:**
Phase 5 (routine) — design for graceful degradation. v1.x — only ship on-demand with explicit caveats.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip Pydantic validation on LLM responses | Faster initial dev | Schema drift breakages months later, hard to debug | **Never** — too cheap to skip |
| Hardcode watchlist in Python instead of `watchlist.json` | One less file | Every config change is a code change | Only in earliest prototype (Phase 1, ≤1 week) |
| Use `print()` instead of structured logging | Move faster | Routine failures impossible to diagnose | Acceptable in MVP if `_status.json` captures the key facts |
| Skip frontend type-validation on API responses | Faster shipping | Backend changes silently break frontend | **Never** for production — use zod |
| Single-source RSS (Yahoo only, no aggregation) | Less code | Misses press-wire and Google News stories | Acceptable in MVP if you commit to Phase 2.5 expansion |
| No `memory/historical_signals.jsonl` initially | Skip the memory layer | Can't show "Buffett went bearish 2 weeks ago" — major feature gap | Acceptable until Phase 7; ship empty schema in Phase 5 so future writes work |
| Use latest Claude model implicitly | Always best | Schema drift on upgrades | Pin model where possible; don't make this a "deal with it later" |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| yfinance | Treating `info` dict as schema-stable | Wrap in Pydantic; gracefully degrade missing fields |
| SEC EDGAR | Generic `User-Agent` or none | Always `<name> <email>` format; rate-limit ≤10 req/sec |
| Reddit RSS | Using `praw` for read-only data (requires OAuth) | Use anonymous `old.reddit.com/.rss` endpoints |
| Google News RSS | Assuming all entries are recent | Filter by `published_parsed` against snapshot timestamp |
| GitHub raw reads | Assuming sub-second latency after commit | ~30s CDN delay; design loading states for it |
| Vercel Python functions | Importing heavy libraries (pandas) — cold start kills 10s timeout | Refresh function uses minimal deps (requests, feedparser only); keep cold start < 1s |
| Claude routine | Assuming token cost is predictable | Log per-ticker estimated cost; have a "lite mode" fallback |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Serial yfinance fetches with no concurrency | 50-ticker batch takes 10+ minutes | Add `httpx` async with rate limiter at ≤10 concurrent | Already at MVP scale (~50 tickers) |
| Loading all snapshots into frontend memory | Browser tab grows to 500MB+ | Lazy-load by route; only fetch the snapshots actively viewed | At ~30 days of history |
| Recomputing analytical indicators on every render | UI sluggish on chart pages | Compute once in batch, store in snapshot; frontend reads scores | Already at MVP |
| Re-fetching from raw.githubusercontent on every refresh | Hits CDN repeatedly; slow on flaky network | Use HTTP cache headers; service worker for offline-first feel | At mobile use on flaky connection |
| GitHub repo with 10K+ files in one folder | `git status` slow, IDE chokes | Per-month sub-folders or migrate snapshots to separate repo | At ~9 months |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Committing API keys (Anthropic, anything else) | Public repo exposure | Use `.env` files, gitignore them; routine env vars stored in routine config not repo |
| Public repo with personal financial decisions exposed | Privacy / pattern-of-life leakage | Make data + main repo private; only frontend code (no data) might be public |
| Vercel function exposing user identity in logs | Logs visible to platform | Don't log query params; redact tickers if dashboard URL becomes shared |
| Storing brokerage credentials | Doesn't apply — we don't integrate brokers | Out of scope deliberately |
| EDGAR User-Agent leaks user email | The User-Agent header is publicly logged at SEC | Acceptable — that's how SEC requires identification; understand it's not private |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Showing all 6 personas' verdicts as equally weighted | User confused which to trust | Highlight the lens-relevant personas; collapse others |
| "AI says X" with no reasoning | User doesn't trust it | Always show drivers + evidence list per signal |
| Confidence as a percentage with two decimals | Spurious precision | Round to 5s ("75%") or use bands ("high/medium/low") |
| Asking user to set thesis_price for every ticker | Onboarding friction kills adoption | Optional with sensible default; only required when user wants thesis-driven analysis |
| No empty state on watchlist page | First-run feels broken | "Add your first ticker" CTA |
| Persona disagreement shown as average ("3 bullish 2 bearish, average bullish") | Loses the signal of disagreement | Show distribution; highlight strongest dissenter |

## "Looks Done But Isn't" Checklist

- [ ] **Watchlist persistence:** Often missing — write-on-edit, debounced; verify a hard refresh preserves the latest watchlist state
- [ ] **Stale-data badge:** Often missing — verify the staleness indicator changes color when forcibly clocking forward 24h
- [ ] **Multi-indicator consensus:** Often defaults to single-indicator under the hood — verify by mocking divergent indicator values; ensure radar requires consensus
- [ ] **Pydantic validation on LLM:** Often skipped under deadline pressure — verify by feeding malformed JSON; ensure default_factory triggers
- [ ] **Mobile layout:** Often shows desktop-cropped — verify each page on actual phone, not just devtools
- [ ] **Error-state UI:** Often missing — verify what happens when refresh fn returns 500, when ticker not found, when EDGAR is down
- [ ] **Routine status emission:** Often only writes data, not status — verify `_status.json` exists and is read by frontend
- [ ] **Endorsement corp-action handling:** Easy to ship without — verify with a synthetic test (split, dividend) before claiming done

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| yfinance breakage | LOW (1-3 days) | Pin known-good version; revert; wait for upstream fix; ship with fallback to yahooquery |
| EDGAR IP block | MEDIUM (hours-days) | Confirm correct User-Agent; pause for 24h; contact SEC if persistent |
| Claude routine partial failure | LOW (overnight) | Diagnose `_status.json`; rerun in lite mode for missing tickers; commit |
| LLM schema drift on model upgrade | MEDIUM (test + fix prompts) | Pin model version; or update prompt + Pydantic schema |
| Endorsement math wrong (corp action) | MEDIUM (manual recompute + UI patch) | Use yfinance adjusted history; recompute affected entries |
| Position-adjustment false positive | LOW (incremental) | Tune indicator weights; add trend-regime gating |
| Persona drift | LOW (prompt edit) | Run regression test; revert offending commit; tighten voice signature |
| UI overload | MEDIUM (UX redesign) | Remove widgets ruthlessly; lens-toggle pattern |
| Stale data shown as fresh | LOW (badge fix) | Add `_status.json` reading + staleness badge to header |
| Premature abstraction | HIGH (rewrite) | Recognize early; delete the abstraction; inline the code |
| GitHub-as-DB scaling | MEDIUM (migration) | Move snapshots to separate repo or Supabase; update frontend reads |
| Self-confirmation bias | LOW (UI surface) | Surface dissenting persona reasoning prominently |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| yfinance silent breakage | Phase 2 (ingestion) | Sanity-check assertions on every fetch; logged failures stored |
| EDGAR User-Agent | Phase 2 (ingestion) | First test fetches; header confirmed in logs |
| Routine quota burnout | Phase 5 (routine) + Phase 8 (resilience) | Token budget logging; lite-mode fallback tested |
| LLM schema drift | Phase 5 (routine + persona wiring) | Pydantic + default_factory mandatory; failure log writes |
| Endorsement math | Phase 7 (endorsement layer) | Synthetic split test before declaring done |
| Position-adjustment false positive | Phase 4 (analyticals) | Multi-indicator consensus; trend-regime weighting |
| Persona drift | Phase 5 (persona wiring) + ongoing | Voice signatures; regression test suite |
| UI overload | Phase 6 (frontend MVP) + ongoing discipline | One-lens-at-a-time scan view; "remove first" rule |
| Stale-data UX | Phase 6 (frontend) | Staleness badge; per-card snapshot date; `_status.json` reading |
| Premature abstraction | Ongoing discipline (all phases) | Code review against YAGNI checklist |
| GitHub-as-DB scaling | Phase 8+ (resilience) | File count threshold trigger |
| Self-confirmation bias | Phase 7 (synthesizer + decision view) | Dissent section always rendered |
| Subscription quota mid-day | Phase 5 + v1.x decision | Don't ship on-demand in v1 without quota awareness |

## Sources

- yfinance GitHub issue history — known breakage patterns
- SEC EDGAR developer documentation — User-Agent rules
- Reference repos (virattt, TradingAgents) — patterns adopted with provenance, abstractions deliberately not adopted
- Anthropic Claude Code routine documentation — quota and reliability constraints
- General finance-domain experience — corp-action math, RSI false-positive patterns, signal-bias dynamics

---
*Pitfalls research for: personal stock research dashboard*
*Researched: 2026-04-30*
