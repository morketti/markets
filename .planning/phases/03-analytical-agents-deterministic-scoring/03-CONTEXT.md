# Phase 3: Analytical Agents — Deterministic Scoring — Context

**Gathered:** 2026-05-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Four pure-function Python analyst modules — Fundamentals, Technicals, News/Sentiment, Valuation — that consume the per-ticker `Snapshot` produced by Plan 02-06 and emit one `AgentSignal` each. Plus the shared `AgentSignal` schema. No LLM, no I/O, no persistence. Pure deterministic scoring callable from any context (Phase 5 routine, Phase 8 mid-day refresh, unit tests).

**Out of phase boundary** (do NOT include here):

- Position-Adjustment Radar — Phase 4 (POSE-01..05). The Phase 3 *technicals* analyst is MA + momentum + ADX only; support/resistance/oscillator-consensus scoring lives in Phase 4.
- LLM persona slate, Synthesizer, `TickerDecision`, `_status.json`, scheduling — Phase 5.
- Frontend rendering of signals — Phase 6.
- Mid-day refresh wiring — Phase 8.
- Endorsement signals — Phase 9.

**Roadmap reconciliation:** ROADMAP.md Phase 3 goal says "Five Python analyst modules" but REQUIREMENTS.md ANLY-01..04 enumerates four. The 5th analyst-style module is Position-Adjustment, which lives in Phase 4. Phase 3 ships **four** analysts. The roadmap goal wording should be tightened to "Four" during the planner's roadmap-touch step.

</domain>

<decisions>
## Implementation Decisions

### AgentSignal Schema (LOCKED)

```python
# analysts/signals.py
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from analysts.schemas import normalize_ticker

Verdict = Literal["strong_bullish", "bullish", "neutral", "bearish", "strong_bearish"]
AnalystId = Literal["fundamentals", "technicals", "news_sentiment", "valuation"]


class AgentSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str
    analyst_id: AnalystId
    computed_at: datetime
    verdict: Verdict = "neutral"
    confidence: int = Field(ge=0, le=100, default=0)
    evidence: list[str] = Field(default_factory=list, max_length=10)
    data_unavailable: bool = False

    @field_validator("ticker", mode="before")
    @classmethod
    def _normalize_ticker_field(cls, v: object) -> str:
        norm = normalize_ticker(v) if isinstance(v, str) else None
        if norm is None:
            raise ValueError(f"invalid ticker {v!r}")
        return norm

    @field_validator("evidence")
    @classmethod
    def _evidence_strings_capped(cls, v: list[str]) -> list[str]:
        for s in v:
            if len(s) > 200:
                raise ValueError("evidence string exceeds 200 chars")
        return v
```

- **5-state verdict.** Broader than REQUIREMENTS.md ANLY-01..04 wording ("bullish/bearish/neutral"). Deliberate widening — `strong_*` collapse to direction for 3-state consumers, but the extra magnitude is useful for Phase 5 dissent calc and Phase 6 rendering. **Planner must update REQUIREMENTS.md ANLY-01..04 wording during this phase to keep requirement text and schema aligned.**
- **0–100 integer confidence.** Locked by REQUIREMENTS.md LLM-07 dissent rule ("≥30 confidence delta") — interoperates with persona signals in Phase 5 without translation.
- **`evidence: list[str]`**, each string ≤200 chars (matches LLM-04 reasoning cap), list ≤10 items. Free-form like virattt convention; `metadata: dict[str, Any]` escape hatch deliberately omitted (`extra="forbid"` discipline).
- **Self-identifying.** `ticker` + `analyst_id` + `computed_at` carry context so a serialized signal stands alone (mirrors how `PriceSnapshot` etc. carry `ticker` + `fetched_at`).
- **`data_unavailable: bool`** — separate explicit flag, matches the existing pattern across `PriceSnapshot`, `FundamentalsSnapshot`, `Headline`, `FilingMetadata`, `SocialSignal`. When True, verdict defaults to `"neutral"`, confidence to `0`, evidence carries a single explanatory string.

### Module Layout

- `analysts/signals.py` — `AgentSignal`, `Verdict`, `AnalystId` types.
- `analysts/fundamentals.py` — `score(snapshot: Snapshot, config: TickerConfig) -> AgentSignal`. Module-level threshold constants at the top.
- `analysts/technicals.py` — same shape. MA20/50/200 alignment + momentum (1m/3m/6m) + ADX(14) trend gating only. Support/resistance is Phase 4.
- `analysts/news_sentiment.py` — same shape. Named `news_sentiment` (not `news`) to avoid confusion with `analysts/data/news.py` (the `Headline` schema).
- `analysts/valuation.py` — same shape.
- All four are **pure functions**: no I/O, no module-level mutable state, no clock reads (caller passes `computed_at` if reproducibility matters; otherwise function reads `datetime.now(UTC)` exactly once).

### Scoring Philosophy

| Analyst | Method |
|---------|--------|
| Fundamentals | Per-`TickerConfig.target_multiples` when set, else hard-coded fallback bands (`PE_BULLISH_BELOW`, `PE_BEARISH_ABOVE`, etc.) at top of `analysts/fundamentals.py`. Five inputs scored: P/E, P/S, ROE, debt/equity, profit margin. Each contributes one or more evidence strings; verdict is the weighted aggregate. |
| Technicals | Hard-coded thresholds. MA alignment (MA20 > MA50 > MA200 = bullish stack), momentum (sign + magnitude over 1m/3m/6m), ADX(14) > 25 = trend regime / < 20 = range regime. **Support/resistance NOT scored here** — that's Phase 4 POSE. |
| News/Sentiment | VADER (`vaderSentiment`, MIT, ~100KB, no API) for per-headline polarity. Aggregate to one `AgentSignal` with **recency weighting** (decay over 7 days) + **source-credibility weight** (Yahoo/Google primary, FinViz secondary, press wires lowest weight). |
| Valuation | All-three blend with explicit precedence — when set: thesis_price (primary) → target_multiples (secondary) → yfinance analyst consensus (tertiary). Each contributes evidence; verdict = sign of weighted aggregate. When NONE configured/available: `data_unavailable=True`. |

### Empty / Partial Data Handling (UNIFORM RULE)

Single rule for all four analysts: **if the analyst cannot form an opinion from the inputs available, emit `AgentSignal(verdict="neutral", confidence=0, data_unavailable=True, evidence=[<reason>])`.** Specifically:

- `snapshot.data_unavailable=True` (every source dark) → all four analysts emit `data_unavailable=True` signals.
- Per-source missing — fundamentals analyst checks `snapshot.fundamentals`; if `None` or `data_unavailable=True`, emit `data_unavailable=True`. Each analyst is self-contained, no cross-coordination.
- Valuation with no thesis_price + no target_multiples + no consensus → `data_unavailable=True` with evidence `['no thesis_price, no target_multiples, no consensus']`.
- **Invariant:** every ticker always gets exactly four signals — never fewer, never more. Phase 5 synthesizer and Phase 6 frontend can rely on this.

### Threshold Configuration

Module-level constants in each analyst module (e.g., `PE_BULLISH_BELOW = 15` at top of `analysts/fundamentals.py`). No central `analysts/thresholds.py`, no TOML config file (YAGNI for v1 single-user). Thresholds tuned by editing the analyst file and re-running tests.

### Provenance

- `analysts/fundamentals.py`, `technicals.py`, `news_sentiment.py`, `valuation.py` all carry header comment naming source: `virattt/ai-hedge-fund/src/agents/{name}.py` where applicable. Reference repo cloned at `~/projects/reference/ai-hedge-fund/`.
- `analysts/signals.py` adapts virattt's `signal/confidence/reasoning` Pydantic pattern; carry header comment naming the source.

### Testing Surface

- `tests/analysts/test_signals.py` — `AgentSignal` schema validation, ticker normalization, evidence cap, verdict literal, confidence range, `extra="forbid"`.
- `tests/analysts/test_fundamentals.py` — happy path with target_multiples, fallback path without, missing-data path, each metric individually exercised.
- `tests/analysts/test_technicals.py` — MA stack patterns (bullish/bearish/mixed), momentum sign tests, ADX trend-gating regression.
- `tests/analysts/test_news_sentiment.py` — VADER call mocked; recency weighting and source weighting verified deterministically; empty-headlines case.
- `tests/analysts/test_valuation.py` — thesis-price-only, targets-only, consensus-only, all-three-blend, none-set (data_unavailable) cases.
- All tests pure-function: build a `Snapshot` + `TickerConfig` fixture, call `score(...)`, assert on returned `AgentSignal`. No filesystem, no network.

### Dependencies (new)

- Add `vaderSentiment >= 3.3, < 4` to `pyproject.toml` `[project.dependencies]`. MIT licensed, no transitive deps beyond stdlib.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`analysts.schemas.normalize_ticker`** — single source of truth for ticker normalization; `AgentSignal.ticker` uses the same `field_validator(mode="before")` pattern locked in Plan 01-02 and reused throughout `analysts/data/*.py`.
- **`analysts.schemas.TickerConfig`** — read by every analyst that uses per-ticker overrides (target_multiples, technical_levels, thesis_price). No re-import work needed.
- **`analysts.data.snapshot.Snapshot`** — locked input contract. Contains `prices`, `fundamentals`, `filings`, `news`, `social`, plus `data_unavailable` and `errors`. Plan 02-06 atomic-write semantics mean analysts can trust the shape on read.
- **`analysts.data.{prices, fundamentals, news, social, filings}`** — sub-schemas pre-validated by ingestion. Analysts read fields directly; no re-validation needed.

### Established Patterns

- **Pydantic v2 + `ConfigDict(extra="forbid")`** — every schema in the codebase uses this. `AgentSignal` follows suit.
- **Cross-field rules use `@model_validator(mode="after")`** — locked correction from Plan 01-02 research. Single-field rules use `@field_validator`. Phase 3 mostly needs single-field validators on `AgentSignal` (verdict literal, confidence range, evidence cap).
- **Atomic writes / determinism / sort_keys** — patterns from Plan 02-06 don't apply here (analysts are pure functions, no file writes), but Plan 02-06 establishes the guarantee that analysts always see a consistent `Snapshot` to score against.
- **Provenance header comments** on adapted files — locked PROJECT.md decision; mandatory.
- **`pytest` + `responses` + ≥90% coverage on schema/loader equivalents** — test harness pattern from Phase 1+2 carries over.

### Integration Points

- **Caller will be Phase 5 routine** (`routine/entrypoint.py` per ROADMAP, not yet built). Each analyst's `score(snapshot, config)` call is the contract.
- **`pyproject.toml` `[tool.coverage.run] source` already includes `analysts`** — coverage will pick up the new modules automatically.
- **CLI `markets` console script** stays untouched — analysts are not user-invokable in this phase. Phase 5 routine drives them.

### Constraints from Existing Architecture

- **Keyless** — no `vaderSentiment` upgrade path requires API keys (it's a local lexicon). Compatible with PROJECT.md keyless-data-plane lock.
- **No LangGraph / no LLM** in this phase — REQUIREMENTS.md INFRA-02 lite-mode says "analyticals only — no persona LLM, no synthesizer LLM" must be reachable; Phase 3's deterministic analysts are the building blocks of lite mode.

</code_context>

<specifics>
## Specific Ideas

### `AgentSignal.evidence` — Format Convention (not enforced by schema)

Each evidence string should embed the metric, observed value, and threshold or comparison. Examples:

```
"P/E 28.4 vs target 22 — overvalued by 29%"
"ROE 18.2% (above 15% bullish band)"
"MA20 (180.5) > MA50 (172.3) > MA200 (165.0) — bullish stack"
"ADX 31 — trend regime; mean-reversion indicators downweighted"
"News volume 14 headlines (7-day weighted), avg VADER compound +0.34 — bullish"
"thesis_price 200, current 175 — 12.5% below thesis"
"no thesis_price, no target_multiples, no consensus"
```

Frontend in Phase 6 renders these as bullets. The format is convention — the schema only enforces ≤200 chars and ≤10 items.

### Threshold Defaults (starting values, may be tuned)

- **Fundamentals fallback bands** (when no `target_multiples` set): P/E < 15 bullish / > 30 bearish; P/S < 2 bullish / > 8 bearish; ROE > 15% bullish / < 5% bearish; debt/equity < 0.5 bullish / > 1.5 bearish; profit margin > 15% bullish / < 5% bearish.
- **Technicals momentum**: 1m > +5% bullish / < -5% bearish; 3m > +10% / < -10%; 6m > +15% / < -15%. Weighted toward shorter horizons.
- **Technicals ADX**: > 25 = trend regime, < 20 = range regime, between = ambiguous (no gating).
- **News recency decay**: half-life of 3 days (anything older than 7 days contributes < 20% weight).
- **News source weights**: Yahoo RSS = 1.0, Google News = 1.0, FinViz = 0.7, press wires (PRNewswire/BusinessWire) = 0.5.

### Determinism

Each `score(...)` call is deterministic given identical inputs (`Snapshot`, `TickerConfig`). The only non-deterministic source is `computed_at`; tests pin it via fixture or pass an explicit value to keep snapshot tests stable.

### File Sizes Expected

- `signals.py`: ~50 lines (schema + literal types).
- Each analyst module: ~100-150 lines (constants + `score()` + small helpers). News sentiment slightly heavier due to VADER + aggregation.

</specifics>

<deferred>
## Deferred Ideas

- **5th analyst module.** ROADMAP wording mentions "Five" — that's Position-Adjustment Radar, which is Phase 4 (POSE-01..05) and explicitly out of scope here. Planner should tighten roadmap text to "Four" during the roadmap-touch step.
- **Z-score scoring vs ticker's own historical fundamentals/technicals.** Most defensible methodology long-term but requires historical snapshot accumulation we don't yet have. Revisit after Phase 5 has been writing daily snapshots for ≥30 days.
- **Loughran-McDonald financial sentiment dictionary.** Finance-specific, more accurate than VADER for filings/headlines but heavier to ship (word lists, not pip-installable). VADER is the v1 pick; revisit if news sentiment quality is the limiting factor downstream.
- **Per-sector / peer-relative scoring** ("AAPL P/E 28 vs sector median 22"). v1.x SEC-01 territory; deferred per requirements.
- **`AgentSignal.metadata: dict[str, Any]`** structured-numbers escape hatch. Considered + rejected to preserve `extra="forbid"` discipline. Revisit only with concrete need.
- **TOML/YAML threshold config file** for user-tunable bands. YAGNI — single user, edit the analyst module and re-run.
- **Real-time / on-demand recompute** of analysts. v1.x OND-01 territory; out of scope for Phase 3.
- **Persona signal trend view** ("Buffett shifted bearish 2 weeks ago"). v1.x TREND-01; needs the memory layer (Phase 8 INFRA-06).

</deferred>

---

*Phase: 03-analytical-agents-deterministic-scoring*
*Context gathered: 2026-05-01*
