# Phase 5: Claude Routine Wiring — Persona Slate + Synthesizer — Context

**Gathered:** 2026-05-03
**Status:** Ready for planning

<domain>
## Phase Boundary

End-to-end Claude Code routine that orchestrates the analytical pipeline and produces daily per-ticker `TickerDecision` JSONs:

1. **Routine entrypoint** (`routine/entrypoint.py`) — single Python entry point invoked by the scheduled Claude Code routine. Loads watchlist → runs ingestion → runs the four analyst score() functions + position_adjustment.score() → invokes 6 persona LLMs → invokes synthesizer LLM → writes per-ticker JSONs and run metadata → commits + pushes via git.
2. **Persona slate** — six markdown prompts at `prompts/personas/`: `buffett.md`, `munger.md`, `wood.md`, `burry.md`, `lynch.md`, `claude_analyst.md`. Each loaded as a string at runtime (NOT hardcoded). Each invocation outputs a Pydantic-validated `AgentSignal` (extending the Phase 3 contract — same shape, different `analyst_id` Literal extension).
3. **Synthesizer** (`prompts/synthesizer.md` + `synthesis/synthesizer.py`) — single LLM call per ticker that consumes the four analytical AgentSignals + the PositionSignal + the six persona AgentSignals + a "dissent" rule, produces one `TickerDecision` (short_term + long_term + recommendation + open_observation).
4. **Storage layer** — daily snapshots at `data/YYYY-MM-DD/{TICKER}.json` (one per ticker) + `_index.json` (run metadata) + `_status.json` (success/partial/failed_tickers/llm_failure_count).
5. **Lite mode** (INFRA-02) — when the routine estimates the token cost would exceed available quota, run analyticals only (skip personas + synthesizer); produce `_status.json` with `partial=true`.

**Out of phase boundary** (do NOT include here):

- Frontend rendering of TickerDecision JSONs — Phase 6.
- Decision-Support recommendation banner UI — Phase 7.
- Memory layer (`memory/historical_signals.jsonl`) — INFRA-06 → Phase 8.
- Mid-day refresh on-demand recompute — Phase 8.
- Endorsement signals — Phase 9.

**Roadmap reconciliation:** ROADMAP.md Phase 5 success criteria say "Memory log + reflection" but the REQUIREMENTS.md traceability puts INFRA-06 in Phase 8. Phase 5 stops at writing the daily snapshot folder + commit + push; the historical-signals memory log lands in Phase 8 alongside the mid-day refresh.

</domain>

<decisions>
## Implementation Decisions

### TickerDecision Schema (LOCKED — to be implemented in plan-1)

```python
# synthesis/decision.py
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from analysts.schemas import normalize_ticker

DecisionRecommendation = Literal[
    "add", "trim", "hold", "take_profits", "buy", "avoid"
]
ConvictionBand = Literal["low", "medium", "high"]
Timeframe = Literal["short_term", "long_term"]


class TimeframeBand(BaseModel):
    """Per-timeframe synthesis content (short_term + long_term)."""
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(min_length=1, max_length=500)
    drivers: list[str] = Field(default_factory=list, max_length=10)
    confidence: int = Field(ge=0, le=100)


class DissentSection(BaseModel):
    """Always-present dissent surfacing — rendered when ≥1 persona disagrees by ≥30 confidence points."""
    model_config = ConfigDict(extra="forbid")
    has_dissent: bool = False
    dissenting_persona: str | None = None
    dissent_summary: str = Field(default="", max_length=500)


class TickerDecision(BaseModel):
    """Final per-ticker synthesizer output. Read by Phase 6 frontend + Phase 7 Decision-Support."""
    model_config = ConfigDict(extra="forbid")

    ticker: str
    computed_at: datetime
    schema_version: int = 1
    recommendation: DecisionRecommendation
    conviction: ConvictionBand
    short_term: TimeframeBand
    long_term: TimeframeBand
    open_observation: str = Field(default="", max_length=500)
    dissent: DissentSection
    data_unavailable: bool = False

    @field_validator("ticker", mode="before")
    @classmethod
    def _normalize_ticker_field(cls, v: object) -> str:
        norm = normalize_ticker(v) if isinstance(v, str) else None
        if norm is None:
            raise ValueError(f"invalid ticker {v!r}")
        return norm
```

- **`schema_version: int = 1`** — Phase 9 + v1.x add fields (endorsements, performance numbers); the version field lets the frontend tolerate forward-compat schema additions.
- **`recommendation: DecisionRecommendation`** — 6-state (add / trim / hold / take_profits / buy / avoid) per Phase 7's eventual UI.
- **`conviction: ConvictionBand`** — 3-state {low, medium, high}. Derived from synthesizer output but locked at the schema layer for Phase 7's banner.
- **`short_term` + `long_term` as `TimeframeBand`** — same shape, different content. Each carries summary + drivers list + per-timeframe confidence.
- **`dissent: DissentSection`** — always present (even when no dissent); `has_dissent: bool` flag drives frontend rendering. Closes LLM-07 contract.
- **`open_observation: str`** — Open Claude Analyst's observation pinned at the top of the per-ticker view (per the user's `claude_analyst.md` persona).

### Persona Slate (LOCKED)

Six markdown prompts at `prompts/personas/`:

| Persona | File | Lens |
|---------|------|------|
| Warren Buffett | `buffett.md` | Long-term value; moat, margin of safety, owner earnings |
| Charlie Munger | `munger.md` | Quality of business, mental-models multidisciplinary check |
| Cathie Wood | `wood.md` | Disruptive innovation, exponential platforms, 5-year horizon |
| Michael Burry | `burry.md` | Macro / contrarian / hidden-risk surfacing |
| Peter Lynch | `lynch.md` | "Invest in what you know"; PEG ratio; 10-bagger framework |
| Open Claude Analyst | `claude_analyst.md` | Claude's inherent reasoning surfaced — NOT a lens, an unfiltered "what does Claude think when given this snapshot" |

Each persona prompt has:
1. **Voice signature anchor** at the top — non-negotiable lens characteristics (LLM-03).
2. **Input section** describing the snapshot + analytical signals it will receive.
3. **Output schema** — must produce a `PersonaSignal` (Pydantic-validated extending AgentSignal).

`PersonaSignal` shape mirrors `AgentSignal` from Phase 3 with:
- `analyst_id: PersonaId` Literal extension: `Literal["buffett", "munger", "wood", "burry", "lynch", "claude_analyst"]`.
- All other fields identical to AgentSignal.

**Decision:** Reuse the AgentSignal schema verbatim by widening the `AnalystId` Literal to include the 6 persona IDs. Persona output IS an AgentSignal — same `verdict + confidence + evidence + data_unavailable` contract as the four analytical AgentSignals. Phase 5 synthesizer sees a list of 11 AgentSignals total: 4 analytical + 6 persona + (PositionSignal as separate peer).

### Synthesizer (LOCKED)

`prompts/synthesizer.md` consumed by `synthesis/synthesizer.py`. Single LLM call per ticker:

**Inputs:**
- `Snapshot` (per-ticker aggregate from Phase 2) — for context only; the synthesizer doesn't re-score.
- 4 analytical AgentSignals (fundamentals, technicals, news_sentiment, valuation).
- 1 PositionSignal (Phase 4 position_adjustment).
- 6 persona AgentSignals (Buffett, Munger, Wood, Burry, Lynch, Open Claude Analyst).
- TickerConfig (user's per-ticker thesis / multiples / focus settings).

**Output:** `TickerDecision` Pydantic-validated.

**Synthesizer prompt logic:**
1. Read short_term_focus + long_term_lens from TickerConfig.
2. Identify the dominant signal direction across the 4+6+1 = 11 inputs.
3. Apply dissent rule: when ≥1 persona disagrees by ≥30 confidence points from the majority, surface that persona's reasoning in `dissent.dissent_summary`.
4. Derive `recommendation` from PositionSignal.action_hint + persona consensus + valuation thesis_price gap (in priority order — POSE drives intraday tactical; persona consensus drives short_term; valuation gap drives long_term thesis updates).
5. Derive `conviction` from agreement count (similar to PositionSignal's confidence formula).
6. Compose `short_term.summary` + `long_term.summary` + `open_observation` from the 11 input signals' evidence strings.

### Routine Entrypoint (LOCKED)

`routine/entrypoint.py` is the single Python entry point invoked by the scheduled Claude Code routine:

```python
def main() -> int:
    """Entry point for the daily Claude Code routine. Returns exit code."""
    try:
        config = load_routine_config()
        run_token_estimate = estimate_run_cost(config)
        lite_mode = run_token_estimate > config.available_quota
        watchlist = load_watchlist()
        results = run_for_watchlist(watchlist, lite_mode=lite_mode)
        write_daily_snapshot(results, date=today_et())
        write_status_json(results, lite_mode=lite_mode)
        commit_and_push(date=today_et())
        return 0
    except Exception:
        write_status_json_failure(error=...)
        return 1
```

Non-trivial sub-modules:
- `routine/run_for_watchlist.py` — main loop. For each ticker: load Snapshot from disk (or fetch fresh) → run 4 analysts → run position_adjustment → if not lite: invoke 6 personas + synthesizer → return per-ticker results.
- `routine/llm_client.py` — thin wrapper over Claude API calls. Loads persona prompt markdown, fills template variables, calls `claude.messages.create(...)`, validates output via Pydantic. On failure: log raw response to `memory/llm_failures.jsonl`, return default `(neutral, 0, "schema_failure")` (LLM-05).
- `routine/persona_runner.py` — loads each persona prompt, builds the input context, dispatches 6 calls (parallel where possible), returns 6 PersonaSignal/AgentSignal objects.
- `routine/synthesizer_runner.py` — single per-ticker synthesizer call, returns TickerDecision.
- `routine/storage.py` — atomic writes (mirrors Phase 1/2 atomic-write pattern); writes `data/YYYY-MM-DD/{TICKER}.json`, `_index.json`, `_status.json`. Stable JSON serialization (sort_keys=True, indent=2).
- `routine/git_publish.py` — `git add data/ && git commit -m "data: snapshot YYYY-MM-DD" && git push`. Auth token from env var `GH_PUBLISH_TOKEN`.

### Storage Format (LOCKED)

**`data/YYYY-MM-DD/{TICKER}.json`** — one per watchlist ticker:
```json
{
  "ticker": "AAPL",
  "computed_at": "2026-05-03T13:30:00+00:00",
  "schema_version": 1,
  "snapshot_summary": {<brief Snapshot fields>},
  "analytical_signals": [<4 AgentSignals>],
  "position_signal": <PositionSignal>,
  "persona_signals": [<6 AgentSignals; empty in lite mode>],
  "ticker_decision": <TickerDecision; null in lite mode>,
  "errors": []
}
```

**`data/YYYY-MM-DD/_index.json`** (run metadata):
```json
{
  "date": "2026-05-03",
  "schema_version": 1,
  "run_started_at": "2026-05-03T11:00:00Z",
  "run_completed_at": "2026-05-03T11:14:32Z",
  "tickers": ["AAPL", "MSFT", ...],
  "lite_mode": false,
  "total_token_count_estimate": 142000
}
```

**`data/YYYY-MM-DD/_status.json`** (closes LLM-08):
```json
{
  "success": true,
  "partial": false,
  "completed_tickers": ["AAPL", "MSFT", ...],
  "failed_tickers": [],
  "skipped_tickers": [],
  "llm_failure_count": 0,
  "lite_mode": false
}
```

### Lite Mode (INFRA-02)

When `estimate_run_cost > available_quota`:
1. Skip persona invocations (6 LLM calls per ticker × N tickers).
2. Skip synthesizer (1 LLM call per ticker × N tickers).
3. Run all 4 analytical analysts + position_adjustment normally (deterministic Python, no LLM cost).
4. Write per-ticker JSON with `persona_signals=[]` and `ticker_decision=null`.
5. Set `_status.json.lite_mode=true` and `partial=true`.

**Trigger:** `estimate_run_cost(config)` reads the watchlist size + persona token budget; compares against an env-var quota ceiling (default: configured at routine setup).

### Empty/Partial Data Handling (UNIFORM RULE)

Same shape as Phase 3+4: every output schema (AgentSignal, PositionSignal, TickerDecision) emits `data_unavailable=True` when its inputs are missing. Specifically:

- **Per-ticker synthesizer failure** → `TickerDecision(data_unavailable=True, recommendation='hold', conviction='low', ...)` with single explanatory note in `open_observation`. Ticker remains in the day's snapshot folder; downstream consumers see the missing data flag.
- **Per-persona LLM failure** → individual AgentSignal with `data_unavailable=True, verdict='neutral', confidence=0, evidence=['schema_failure']`. Other 5 personas + synthesizer continue.
- **Per-ticker ingestion failure** (Snapshot.data_unavailable=True) → all 4 analytical analysts + position_adjustment + 6 personas all emit data_unavailable=True; synthesizer still produces a TickerDecision marked data_unavailable=True for consistency with the contract.

### Provenance

- `routine/persona_runner.py` carries header comment naming `virattt/ai-hedge-fund/src/agents/buffett_agent.py` etc. — adapted from virattt's persona-agent pattern but with markdown-loaded prompts instead of hardcoded Python strings.
- `synthesis/synthesizer.py` carries header naming `TauricResearch/TradingAgents/tradingagents/agents/` synthesis pattern with the same divergence (markdown prompt + Pydantic-validated output).
- `routine/entrypoint.py` is novel-to-this-project — orchestration layer not directly adapted from a reference repo.

### Testing Surface

- `tests/synthesis/test_decision.py` — TickerDecision schema validation (mirrors test_signals.py structure).
- `tests/routine/test_persona_runner.py` — persona prompt loading + Pydantic validation + LLM-failure default-factory path. Mocks the Claude API at the message-create boundary.
- `tests/routine/test_synthesizer_runner.py` — synthesizer prompt + dissent rule (3+ scenarios: no dissent, mild dissent, extreme dissent) + lite-mode skip path.
- `tests/routine/test_entrypoint.py` — main() integration: loaded watchlist → 5-ticker mock-LLM run → emits 5 per-ticker JSONs + _index.json + _status.json. Uses mocked Claude client + frozen clock.
- `tests/routine/test_storage.py` — atomic-write contract; deterministic clock; sort_keys serialization; round-trip equality.
- `tests/routine/test_git_publish.py` — commit + push happy path + push-failure handling. Mocks `subprocess.run` at the git-CLI boundary.

### Dependencies (new)

- **`anthropic` (Python SDK)** — `>= 0.40, < 1` (current Anthropic Python SDK). Used by `routine/llm_client.py` for `claude.messages.create(...)`.
- No other deps. Pydantic v2 already locked from Phase 1.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`analysts.signals.AgentSignal`** — schema reused verbatim for personas. Just widen `AnalystId` Literal to include the 6 persona IDs.
- **`analysts.position_signal.PositionSignal`** — read directly by synthesizer.
- **All 4 Phase 3 analyst score() functions + position_adjustment.score()** — called from `routine/run_for_watchlist.py`.
- **`watchlist/loader.py`** — `load_watchlist(path)` from Phase 1; routine entrypoint calls this first.
- **`ingestion/refresh.py`** — `run_refresh()` from Phase 2; routine can either call this fresh or read pre-fetched snapshots from disk.

### Established Patterns

- **Pydantic v2 + ConfigDict(extra="forbid")** — same discipline; TickerDecision + DissentSection + TimeframeBand all follow.
- **Stable JSON serialization** — `json.dumps(model.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"` (Phase 1/2 pattern).
- **Atomic writes via tempfile + os.replace** — Phase 1/2 pattern; routine/storage.py reuses this for per-ticker JSON writes.
- **Pure-function score() pattern** — Phase 3+4 analysts. Phase 5 personas + synthesizer are NOT pure (they make LLM calls), but the Pydantic-validated output contract is the same.
- **`computed_at` discipline** — `now = computed_at if computed_at is not None else datetime.now(timezone.utc)` read ONCE at top.

### Integration Points

- **Scheduled Claude Code routine** — invoked Mon-Fri 06:00 ET. Implementation depends on current Claude Code routine constraints (researcher will surface specifics).
- **GitHub-as-DB** — `data/YYYY-MM-DD/` snapshot folder committed + pushed. Frontend (Phase 6) reads via `raw.githubusercontent.com`.
- **Vercel mid-day refresh** — Phase 8's serverless function reads `data/YYYY-MM-DD/_index.json` to know which tickers exist.

### Constraints from Existing Architecture

- **Keyless data plane** (PROJECT.md) — no Anthropic API key in repo; uses Claude subscription quota via Claude Code routine. Locked.
- **No long-lived processes** — Claude Code routine fires once per day, runs to completion, exits. No background workers.
- **All LLM I/O is "Claude only"** — no GPT/Gemini fallback in v1. Locked.

</code_context>

<specifics>
## Specific Ideas

### Persona Prompt Structure (locked at LLM-03)

Each persona markdown file follows this exact section structure:

```markdown
# Persona: [Name]

## Voice Signature
[3-5 bullet points capturing the non-negotiable lens. Anchors the persona
across runs — synthesizer can read this section to verify a persona response
hasn't drifted into another persona's voice.]

## Input Context
You will receive:
- Snapshot summary (per-ticker prices, fundamentals, recent news)
- 4 analytical AgentSignals (fundamentals, technicals, news_sentiment, valuation)
- PositionSignal (overbought/oversold consensus)
- TickerConfig (user's thesis_price, target_multiples, lens)

## Task
[Persona-specific task — what to weigh, what to ignore, what to surface.]

## Output Schema
Return ONLY a JSON object matching this schema:

{
  "ticker": "<ticker>",
  "analyst_id": "<persona-id>",
  "verdict": "strong_bullish|bullish|neutral|bearish|strong_bearish",
  "confidence": <int 0-100>,
  "evidence": ["<reason 1>", "<reason 2>", ...],  // ≤10 items, each ≤200 chars
  "data_unavailable": false
}
```

The `routine/llm_client.py` validates the LLM response against AgentSignal directly; on validation failure, returns the default-factory shape per LLM-05.

### Dissent Rule (LLM-07)

Synthesizer checks: for the 6 persona AgentSignals, compute the median verdict's confidence. If any persona's confidence ON THE OPPOSITE DIRECTION is ≥30 points, surface that persona in `dissent.dissenting_persona` + `dissent.dissent_summary`.

Edge cases:
- All 6 personas agree (verdict + ≥30 confidence) → `has_dissent=false`.
- 1 persona dissents by exactly 30 → `has_dissent=true` (boundary inclusive).
- All 6 personas at confidence=0 (data_unavailable) → `has_dissent=false`.

### Lite-Mode Token Estimate (INFRA-02)

`estimate_run_cost(config)`:
- For each watchlist ticker: estimate persona prompt + snapshot context + AgentSignal output ≈ 2000 input tokens + 300 output tokens × 6 personas + 5000 input + 500 output for synthesizer.
- For 30 tickers: 30 × (6 × 2300 + 5500) ≈ 30 × 19400 ≈ 580K tokens.
- Compare against env var `MARKETS_DAILY_QUOTA_TOKENS` (default: configured at routine setup).
- If exceeds: lite mode.

Phase 5 ships a conservative estimator. Phase 8 may refine it with measured tokens-per-call from the first weeks of production data.

### File Sizes Expected

- `routine/entrypoint.py`: ~80-120 lines.
- `routine/run_for_watchlist.py`: ~150 lines.
- `routine/llm_client.py`: ~100 lines.
- `routine/persona_runner.py`: ~80 lines.
- `routine/synthesizer_runner.py`: ~80 lines.
- `routine/storage.py`: ~120 lines.
- `routine/git_publish.py`: ~60 lines.
- `synthesis/decision.py`: ~80 lines.
- `synthesis/synthesizer.py`: ~120 lines (mostly the dissent rule + recommendation derivation).
- 6 persona markdown files: ~80-150 lines each (prompts).
- `prompts/synthesizer.md`: ~150-200 lines.

Total: ~1,000-1,200 lines of production Python + ~700-1,000 lines of markdown prompts + ~600-800 lines of tests.

</specifics>

<deferred>
## Deferred Ideas

- **Memory layer (`memory/historical_signals.jsonl`)** — INFRA-06 → Phase 8.
- **Mid-day refresh** — REFRESH-01..04 → Phase 8.
- **Persona signal trend view** ("Buffett shifted bearish 2 weeks ago") — needs the memory layer; v1.x TREND-01.
- **GPT/Gemini fallback** for personas — single-LLM-vendor lock for v1; v2 territory.
- **User-configurable persona slate** — fixed 6 for v1; v1.x adds custom-persona file drop.
- **Synthesizer reflection loop** (read prior days' decisions to validate consistency) — needs memory; Phase 8 + v1.x.
- **Per-persona token budget** — uniform 2300 input + 300 output for v1; v1.x can tune per-persona based on observed prompt verbosity.
- **Streaming output from Claude API** — Phase 5 uses non-streaming for simplicity. Streaming adds complexity without changing the contract.
- **Routine partial-success retry on transient LLM errors** — v1 logs failures and continues; v1.x adds retry-with-backoff for 429/503.

</deferred>

---

*Phase: 05-claude-routine-wiring*
*Context gathered: 2026-05-03*
