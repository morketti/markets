---
phase: 05-claude-routine-wiring
plan: 02
type: tdd
wave: 1
depends_on: [05-01]
files_modified:
  - synthesis/decision.py
  - tests/synthesis/test_decision.py
autonomous: true
requirements: [LLM-06]
provides:
  - "synthesis/decision.py — TickerDecision Pydantic v2 model + DecisionRecommendation Literal (6-state) + ConvictionBand Literal (3-state) + Timeframe Literal (2-state) + TimeframeBand model + DissentSection model"
  - "TickerDecision field surface: ticker (normalized via analysts.schemas.normalize_ticker), computed_at, schema_version (int=1, forward-compat), recommendation (DecisionRecommendation), conviction (ConvictionBand), short_term (TimeframeBand), long_term (TimeframeBand), open_observation (str≤500), dissent (DissentSection), data_unavailable (bool=False)"
  - "TimeframeBand: summary (str, 1-500 chars), drivers (list[str], ≤10 items, ≤200 chars each via custom @field_validator), confidence (int 0-100); ConfigDict(extra='forbid')"
  - "DissentSection: has_dissent (bool=False), dissenting_persona (str|None=None), dissent_summary (str, default='', ≤500 chars); ConfigDict(extra='forbid')"
  - "@model_validator(mode='after') on TickerDecision enforcing data_unavailable=True ⟹ recommendation='hold' AND conviction='low' (matches Phase 3 AgentSignal + Phase 4 PositionSignal pattern; Open Question #3 from 05-RESEARCH.md recommends include — closes Pitfall #4-class drift)"
  - "@field_validator('ticker', mode='before') on TickerDecision delegating to analysts.schemas.normalize_ticker — same single-source-of-truth pattern as AgentSignal + PositionSignal + every analysts.data.* schema"
  - "tests/synthesis/test_decision.py — ≥18 tests covering schema validation, all 6 recommendation enum values, all 3 conviction enum values, ticker normalization, length caps, data_unavailable invariant violations + clean path, JSON round-trip, default values, schema_version forward-compat hook, drivers per-string cap, TimeframeBand min_length=1 enforcement"
tags: [phase-5, schema, decision, ticker-decision, dissent, timeframe-band, tdd, wave-1, llm-06]

must_haves:
  truths:
    - "TickerDecision validates a complete instance with ticker='AAPL', computed_at=frozen_now, recommendation='hold', conviction='medium', short_term=TimeframeBand(summary='x', drivers=[], confidence=50), long_term=TimeframeBand(summary='y', drivers=[], confidence=40), dissent=DissentSection() — VALID; no validation errors raised"
    - "DecisionRecommendation Literal accepts EXACTLY these 6 values: add | trim | hold | take_profits | buy | avoid (parametrized test verifies each constructs cleanly)"
    - "ConvictionBand Literal accepts EXACTLY these 3 values: low | medium | high"
    - "Timeframe Literal accepts EXACTLY these 2 values: short_term | long_term"
    - "DecisionRecommendation rejects 'strong_buy' (Phase 3-style verdict word, not in 6-state enum) → ValidationError with 'recommendation' in loc"
    - "ConvictionBand rejects 'very_high' → ValidationError with 'conviction' in loc"
    - "TickerDecision schema_version defaults to 1 when omitted; explicit schema_version=2 also accepted (forward compat for Phase 9 + v1.x; the field is just `int = 1`, no validator clamps it)"
    - "TickerDecision ticker normalization: TickerDecision(ticker='brk.b', ...) → .ticker == 'BRK-B' (delegates to analysts.schemas.normalize_ticker — same single-source-of-truth as AgentSignal + PositionSignal)"
    - "TickerDecision invalid ticker: TickerDecision(ticker='123!@#', ...) → ValidationError with 'ticker' in loc"
    - "TickerDecision extra field rejection: TickerDecision(..., metadata={'x': 1}) → ValidationError ('metadata' not allowed; ConfigDict extra='forbid')"
    - "TimeframeBand summary min_length=1: TimeframeBand(summary='', drivers=[], confidence=50) → ValidationError mentioning 'summary'"
    - "TimeframeBand summary max_length=500: TimeframeBand(summary='x'*501, drivers=[], confidence=50) → ValidationError"
    - "TimeframeBand drivers count cap: TimeframeBand(summary='ok', drivers=['a']*11, confidence=50) → ValidationError (Field(max_length=10))"
    - "TimeframeBand drivers per-string cap: TimeframeBand(summary='ok', drivers=['x'*201], confidence=50) → ValidationError (custom @field_validator)"
    - "TimeframeBand confidence range: TimeframeBand(summary='ok', drivers=[], confidence=-1) → ValidationError; confidence=101 → ValidationError; 0 and 100 boundaries accepted"
    - "DissentSection defaults: DissentSection() yields .has_dissent==False, .dissenting_persona is None, .dissent_summary == ''"
    - "DissentSection populated: DissentSection(has_dissent=True, dissenting_persona='burry', dissent_summary='burry dissents (bearish, conf=45): hidden risk in margin compression') — VALID"
    - "DissentSection dissent_summary max_length=500: DissentSection(dissent_summary='x'*501) → ValidationError"
    - "TickerDecision open_observation max_length=500: open_observation='x'*501 → ValidationError"
    - "data_unavailable invariant — recommendation violation: TickerDecision(..., data_unavailable=True, recommendation='buy', conviction='low', short_term=..., long_term=..., dissent=DissentSection()) → ValidationError mentioning 'data_unavailable' AND 'recommendation'"
    - "data_unavailable invariant — conviction violation: TickerDecision(..., data_unavailable=True, recommendation='hold', conviction='high', ...) → ValidationError mentioning 'data_unavailable' AND 'conviction'"
    - "data_unavailable invariant — clean path: TickerDecision(ticker='AAPL', computed_at=frozen_now, data_unavailable=True, recommendation='hold', conviction='low', short_term=TimeframeBand(summary='data unavailable', drivers=[], confidence=0), long_term=TimeframeBand(summary='data unavailable', drivers=[], confidence=0), dissent=DissentSection(), open_observation='snapshot data_unavailable=True') — VALID"
    - "JSON round-trip: model_dump_json → model_validate_json yields equal TickerDecision; datetime ISO-8601 serialization preserved; nested TimeframeBand + DissentSection round-trip cleanly"
    - "Independence from AgentSignal + PositionSignal: TickerDecision is NOT a subclass of either; coexists in the same module-import path without name collision"
    - "Coverage ≥90% line / ≥85% branch on synthesis/decision.py"
  artifacts:
    - path: "synthesis/decision.py"
      provides: "TickerDecision + DissentSection + TimeframeBand + 3 Literal types + 3 validators (ticker normalization, drivers per-string cap, data_unavailable invariant) + provenance docstring referencing TauricResearch/TradingAgents portfolio_manager.py per INFRA-07. ~80-110 LOC."
      min_lines: 80
    - path: "tests/synthesis/test_decision.py"
      provides: "≥18 tests covering: (a) shape — minimum valid TickerDecision; (b) enum coverage — all 6 DecisionRecommendation + all 3 ConvictionBand + all 2 Timeframe; (c) ticker normalization + invalid-ticker rejection; (d) extra-field rejection; (e) length caps on summary / drivers / dissent_summary / open_observation; (f) confidence range; (g) data_unavailable invariant — 2 violations + 1 clean path; (h) DissentSection defaults + populated; (i) JSON round-trip; (j) schema_version forward-compat; (k) independence from AgentSignal/PositionSignal."
      min_lines: 250
  key_links:
    - from: "synthesis/decision.py"
      to: "analysts.schemas.normalize_ticker"
      via: "@field_validator('ticker', mode='before') reuses single-source-of-truth normalizer (same delegation pattern as AgentSignal + PositionSignal + PriceSnapshot + Snapshot)"
      pattern: "from analysts\\.schemas import normalize_ticker"
    - from: "synthesis/decision.py"
      to: "Pydantic v2 @model_validator(mode='after')"
      via: "data_unavailable=True ⟹ recommendation='hold' AND conviction='low' invariant — matches Phase 3 + Phase 4 precedent"
      pattern: "@model_validator\\(mode=\"after\"\\)"
    - from: "synthesis/decision.py"
      to: "Phase 5 routine + Phase 6 frontend + Phase 7 Decision-Support (downstream consumers)"
      via: "TickerDecision is the locked output type the Phase 5 synthesizer produces; Phase 6 deserializes via Pydantic round-trip; Phase 7 reads recommendation + conviction + dissent for the banner"
      pattern: "TickerDecision"
    - from: "tests/synthesis/test_decision.py"
      to: "synthesis.decision (the unit under test)"
      via: "imports TickerDecision, DissentSection, TimeframeBand, DecisionRecommendation, ConvictionBand, Timeframe; uses frozen_now fixture from tests/analysts/conftest.py"
      pattern: "from synthesis\\.decision import"
    - from: "synthesis/decision.py docstring"
      to: "TauricResearch/TradingAgents portfolio_manager.py PortfolioDecision shape (INFRA-07 provenance)"
      via: "module docstring carries the lineage + 6-state-vs-5-state recommendation divergence note"
      pattern: "TauricResearch/TradingAgents"
---

<objective>
Wave 1 / LLM-06 schema scaffold: ship the `TickerDecision` Pydantic v2 model + `DissentSection` + `TimeframeBand` peer models + 3 Literal types (`DecisionRecommendation` 6-state, `ConvictionBand` 3-state, `Timeframe` 2-state) at `synthesis/decision.py`. Includes the `@model_validator(mode='after')` enforcing the `data_unavailable=True ⟹ recommendation='hold' AND conviction='low'` invariant — closes Pitfall #4-class drift at zero schema-shape cost (matches Phase 3 AgentSignal + Phase 4 PositionSignal precedent; Open Question #3 from 05-RESEARCH.md explicitly recommends include).

Purpose: TickerDecision is the locked output contract for Phase 5's synthesizer call (LLM-06). Wave 4's `synthesis/synthesizer.py` (Plan 05-05) imports `TickerDecision` + `DissentSection` + `TimeframeBand` + the 3 Literal types — without this Wave 1 plan shipped first, Wave 4 can't be written. Wave 5's `routine/storage.py` serializes TickerDecision into per-ticker JSONs. Phase 6 (frontend) deserializes via `raw.githubusercontent.com` reads. Phase 7 (Decision-Support View) reads `recommendation` + `conviction` + `dissent` for the banner.

The `schema_version: int = 1` field is the forward-compat hook: Phase 9 (Endorsements) + v1.x add fields (endorsement_refs, performance numbers); the version field lets the frontend tolerate forward-compat additions. ConfigDict(extra='forbid') still applies — backward-incompatible field additions require a deliberate schema_version bump (Phase 6's zod validation will key off this).

The provenance per INFRA-07: header references `TauricResearch/TradingAgents/tradingagents/agents/managers/portfolio_manager.py` for the structured-output PortfolioDecision shape. Modifications: 6-state recommendation enum (vs TradingAgents' 5-state buy/overweight/hold/underweight/sell); explicit DissentSection (novel-to-this-project; LLM-07 — TradingAgents has no analog); dual-timeframe TimeframeBand (short_term + long_term — TradingAgents' PortfolioDecision is single-timeframe).

The schema lives in its own module (`synthesis/decision.py`) — separate from Wave 4's `synthesis/synthesizer.py` orchestrator — for the same reason `analysts/signals.py` lives separately from the four Phase 3 analyst modules and `analysts/position_signal.py` lives separately from `analysts/position_adjustment.py`. Phase 6 frontend importers shouldn't pay the synthesizer's import cost just to deserialize a stored TickerDecision.

Output: synthesis/decision.py (~80-110 LOC: provenance docstring + 3 Literal types + DissentSection class + TimeframeBand class + TickerDecision class + 3 validators); tests/synthesis/test_decision.py (~250-300 LOC, ≥18 tests covering every invariant, all GREEN).
</objective>

<execution_context>
@C:/Users/Mohan/.claude/workflows/execute-plan.md
@C:/Users/Mohan/.claude/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/05-claude-routine-wiring/05-CONTEXT.md
@.planning/phases/05-claude-routine-wiring/05-RESEARCH.md
@.planning/phases/05-claude-routine-wiring/05-01-foundation-PLAN.md

# Existing patterns to mirror
@analysts/signals.py
@analysts/position_signal.py
@analysts/schemas.py
@tests/analysts/test_signals.py
@tests/analysts/test_position_signal.py
@tests/analysts/conftest.py

<interfaces>
<!-- Existing AgentSignal + PositionSignal patterns to mirror — both have:
       * ConfigDict(extra="forbid")
       * @field_validator("ticker", mode="before") delegating to normalize_ticker
       * @field_validator on bounded list fields for per-string char caps
       * @model_validator(mode="after") for the data_unavailable invariant
-->

```python
# AgentSignal precedent — analysts/signals.py:
class AgentSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # ... 7 fields ...
    @field_validator("ticker", mode="before")
    @classmethod
    def _normalize_ticker_field(cls, v): ...
    @field_validator("evidence")
    @classmethod
    def _evidence_strings_capped(cls, v): ...
    @model_validator(mode="after")
    def _data_unavailable_implies_neutral_zero(self): ...

# PositionSignal precedent — analysts/position_signal.py:
class PositionSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # ... 10 fields ...
    @model_validator(mode="after")
    def _data_unavailable_implies_fair_zero(self): ...
```

<!-- New types this plan creates — synthesis/decision.py: -->

```python
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

    @field_validator("drivers")
    @classmethod
    def _drivers_strings_capped(cls, v: list[str]) -> list[str]: ...


class DissentSection(BaseModel):
    """Always-present dissent surface."""
    model_config = ConfigDict(extra="forbid")
    has_dissent: bool = False
    dissenting_persona: str | None = None
    dissent_summary: str = Field(default="", max_length=500)


class TickerDecision(BaseModel):
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
    def _normalize_ticker_field(cls, v): ...

    @model_validator(mode="after")
    def _data_unavailable_implies_safe_defaults(self) -> "TickerDecision": ...
```

<!-- frozen_now fixture from tests/analysts/conftest.py (already shipped Phase 3): -->

```python
@pytest.fixture
def frozen_now() -> datetime:
    return datetime(2026, 5, 1, 13, 30, 0, tzinfo=timezone.utc)
```
</interfaces>

<implementation_sketch>
<!-- The full file content. Provenance docstring references TauricResearch/TradingAgents
     per INFRA-07; module is structured top-down: imports → Literal types →
     TimeframeBand → DissentSection → TickerDecision (the deepest type last so
     the 2 nested types are defined before TickerDecision references them). -->

```python
"""TickerDecision — Phase 5 synthesizer output schema.

Pattern adapted from TauricResearch/TradingAgents
tradingagents/agents/managers/portfolio_manager.py PortfolioDecision shape —
adapted for our 6-state recommendation enum (vs their 5-state buy/overweight/
hold/underweight/sell), our explicit DissentSection (novel-to-this-project;
LLM-07 — TradingAgents has no analog dissent surface), and our dual-timeframe
TimeframeBand (short_term + long_term cards).

Read by Phase 6 frontend (Per-Ticker Deep-Dive view, VIEW-05..VIEW-09) and
Phase 7 Decision-Support View (VIEW-10) for the recommendation banner.

The `schema_version: int = 1` field is the forward-compat hook: Phase 9 +
v1.x add fields (endorsement_refs, performance numbers); the version field
lets the frontend tolerate forward-compat schema additions. ConfigDict
(extra='forbid') still applies — backward-incompatible field additions
require a deliberate schema_version bump.

Modifications from the reference implementation:
  * 6-state DecisionRecommendation Literal (add | trim | hold | take_profits |
    buy | avoid) — diverges from TradingAgents' 5-state rating scale.
  * Explicit DissentSection model — TradingAgents' PortfolioDecision has no
    dissent surface; LLM-07 makes ours mandatory.
  * Dual-timeframe TimeframeBand — TradingAgents is single-timeframe;
    short_term + long_term are user-locked.
  * Pydantic v2 ConfigDict(extra='forbid') — same project-wide schema
    discipline as Phase 3 AgentSignal + Phase 4 PositionSignal.
  * Ticker normalized via the project's single-source-of-truth helper
    `analysts.schemas.normalize_ticker` — mirrors AgentSignal, PositionSignal,
    PriceSnapshot, FundamentalsSnapshot, Headline, Snapshot, etc.
  * @model_validator(mode='after') enforces the data_unavailable=True ⟹
    recommendation='hold' AND conviction='low' invariant — matches Phase 3
    AgentSignal + Phase 4 PositionSignal precedent (closes Pitfall #4-class
    drift; Open Question #3 from 05-RESEARCH.md recommends include).

Public surface (re-imported by synthesis/synthesizer.py at Wave 4 and by
routine/storage.py at Wave 5):
    DecisionRecommendation — Literal of 6 enum values
    ConvictionBand        — Literal of 3 enum values
    Timeframe             — Literal of 2 enum values (used by Phase 6 frontend)
    TimeframeBand         — per-timeframe synthesis content
    DissentSection        — always-present dissent surface
    TickerDecision        — final per-ticker synthesizer output
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from analysts.schemas import normalize_ticker

# ---------------------------------------------------------------------------
# Literal types — module-level so importers can `from synthesis.decision import
# DecisionRecommendation, ConvictionBand, Timeframe`. Mirrors analysts/signals.py
# pattern of co-locating Literal types with their consumer model classes.
# ---------------------------------------------------------------------------
DecisionRecommendation = Literal[
    "add",
    "trim",
    "hold",
    "take_profits",
    "buy",
    "avoid",
]

ConvictionBand = Literal["low", "medium", "high"]

Timeframe = Literal["short_term", "long_term"]


class TimeframeBand(BaseModel):
    """Per-timeframe synthesis content (short_term + long_term).

    The synthesizer produces TWO of these per TickerDecision — one for the
    1-week-to-1-month tactical horizon, one for the 1-year-to-5-year strategic
    horizon. Same shape; different content.

    Defaults: drivers=[], no confidence default (caller MUST set; the field is
    Field(ge=0, le=100) without a default to avoid silent zero-confidence). The
    summary field has min_length=1 — empty summaries are a synthesizer bug.
    """
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=500)
    drivers: list[str] = Field(default_factory=list, max_length=10)
    confidence: int = Field(ge=0, le=100)

    @field_validator("drivers")
    @classmethod
    def _drivers_strings_capped(cls, v: list[str]) -> list[str]:
        # Pydantic's Field(max_length=10) handles the COUNT cap; this validator
        # handles the per-string length cap (≤200 chars; same shape as
        # AgentSignal.evidence + PositionSignal.evidence).
        for s in v:
            if len(s) > 200:
                raise ValueError(
                    f"driver string exceeds 200 chars (got {len(s)}): {s[:60]!r}..."
                )
        return v


class DissentSection(BaseModel):
    """Always-present dissent surface — closes LLM-07 contract.

    `has_dissent: bool` flag drives Phase 6 frontend rendering — the section
    is ALWAYS present in the JSON (even when no dissent), but the frontend
    renders the dissenting-persona summary only when has_dissent=True. This
    avoids null-vs-missing field divergence between routine output and frontend
    consumption.

    The Python dissent computation (synthesis/synthesizer.py / Wave 4 /
    compute_dissent) populates `dissenting_persona` with one of the 6 persona
    IDs ('buffett', 'munger', 'wood', 'burry', 'lynch', 'claude_analyst') or
    None. The synthesizer LLM is INSTRUCTED to render the pre-computed
    dissent_summary string verbatim into this field. See 05-RESEARCH.md
    Pattern #7 for the dissent-in-Python rationale.
    """
    model_config = ConfigDict(extra="forbid")

    has_dissent: bool = False
    dissenting_persona: str | None = None
    dissent_summary: str = Field(default="", max_length=500)


class TickerDecision(BaseModel):
    """Final per-ticker synthesizer output. Read by Phase 6 + Phase 7 frontend.

    Self-identifying — `ticker + computed_at` carry context so a serialized
    TickerDecision stands alone (mirrors AgentSignal + PositionSignal). Phase 5
    routine/storage.py JSON-serializes this into data/YYYY-MM-DD/{ticker}.json
    alongside the 4 analytical AgentSignals + PositionSignal + 6 persona
    AgentSignals.

    The `schema_version: int = 1` lock is the forward-compat hook for Phase 9
    + v1.x. Frontend reads schema_version first; if it sees a version > 1, it
    can choose to render with v1 fields only (graceful degradation) or surface
    a "schema upgrade required" notice.

    Defaults: schema_version=1, open_observation='', data_unavailable=False.
    No defaults on the 5 required fields (recommendation, conviction,
    short_term, long_term, dissent) — synthesizer MUST populate all of them
    explicitly. data_unavailable=True path uses _data_unavailable_decision
    helper in synthesis/synthesizer.py (Wave 4) to fill the required fields
    with safe defaults that satisfy the @model_validator invariant.
    """
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
        # Same delegation pattern as AgentSignal + PositionSignal + every
        # analysts.data.* sub-schema — single source of truth for ticker
        # normalization. Returns canonical hyphen form (BRK-B), or raises
        # ValueError for non-string / regex mismatch input which Pydantic
        # surfaces as a ValidationError with ('ticker',) in the loc path.
        norm = normalize_ticker(v) if isinstance(v, str) else None
        if norm is None:
            raise ValueError(f"invalid ticker {v!r}")
        return norm

    @model_validator(mode="after")
    def _data_unavailable_implies_safe_defaults(self) -> "TickerDecision":
        """Schema-level invariant: data_unavailable=True ⟹ recommendation='hold' AND conviction='low'.

        Closes Pitfall #4-class drift. Same pattern as Phase 3 AgentSignal's
        _data_unavailable_implies_neutral_zero (analysts/signals.py) and
        Phase 4 PositionSignal's _data_unavailable_implies_fair_zero
        (analysts/position_signal.py).

        Note: short_term/long_term/dissent/open_observation are NOT enforced
        here — the synthesizer's _data_unavailable_decision helper (Wave 4)
        fills them with safe content ('data unavailable: <reason>' summaries,
        empty drivers, confidence=0, dissent=DissentSection() default), but
        we don't lock that at the schema layer because the helpful-content
        choice is implementation-side, not schema-side.

        Error message names BOTH offending values for debuggability AND the
        literal substring "data_unavailable=True invariant violated" so the
        violation tests can grep on it.
        """
        if self.data_unavailable:
            problems: list[str] = []
            if self.recommendation != "hold":
                problems.append(
                    f"recommendation={self.recommendation!r} (expected 'hold')"
                )
            if self.conviction != "low":
                problems.append(
                    f"conviction={self.conviction!r} (expected 'low')"
                )
            if problems:
                raise ValueError(
                    "data_unavailable=True invariant violated: "
                    + ", ".join(problems)
                )
        return self
```

<!-- The test file structure mirrors tests/analysts/test_position_signal.py + test_signals.py:
     parametrize over Literal values, ValidationError-asserting tests for every
     boundary, JSON round-trip, default-value snapshot. Use the existing
     `frozen_now` fixture (already in tests/analysts/conftest.py).

     IMPORTANT: tests/synthesis/test_decision.py needs to import the frozen_now
     fixture. Two options:
       (a) Re-define frozen_now in tests/synthesis/conftest.py (duplicates
           the constant; minor maintenance cost).
       (b) Use rootdir-level conftest discovery — pytest auto-discovers
           conftest.py up the directory tree. tests/analysts/conftest.py is
           NOT visible from tests/synthesis/.
       (c) Move frozen_now to tests/conftest.py (the rootdir of the test tree)
           so all sub-packages inherit it.

     LOCK: option (c) — move frozen_now to a NEW tests/conftest.py at the test
     tree root. Keep the existing tests/analysts/conftest.py for the
     analyst-specific synthetic-history builders. NO existing test imports
     change — frozen_now is auto-discovered.

     NOTE: if tests/conftest.py already exists from a prior phase, EXTEND it.
     If absent, create with frozen_now + necessary imports. Verify by running
     all existing tests — none must break. -->

<!-- Test outline (≥18 tests; structure mirrors tests/analysts/test_position_signal.py):

  SHAPE / DEFAULTS:
  1. test_minimum_valid_ticker_decision — TickerDecision with all 8 required fields populated, defaults observed.
  2. test_extra_field_forbidden — TickerDecision(..., metadata={'x': 1}) → ValidationError.
  3. test_schema_version_default_is_1 — TickerDecision(...) without schema_version → .schema_version == 1.
  4. test_schema_version_2_accepted — TickerDecision(..., schema_version=2) — VALID (forward compat hook).

  TICKER NORMALIZATION:
  5. test_ticker_normalization — TickerDecision(ticker='brk.b', ...) → .ticker == 'BRK-B'.
  6. test_ticker_invalid_raises — TickerDecision(ticker='123!@#', ...) → ValidationError with 'ticker' in loc.

  ENUM COVERAGE:
  7. test_recommendation_6_values_accepted — parametrize over the 6 DecisionRecommendation values; each constructs cleanly (with conviction='medium' to satisfy invariant).
  8. test_recommendation_invalid_rejected — TickerDecision(..., recommendation='strong_buy') → ValidationError.
  9. test_conviction_3_values_accepted — parametrize over ['low','medium','high']; each constructs cleanly.
  10. test_conviction_invalid_rejected — TickerDecision(..., conviction='very_high') → ValidationError.

  TIMEFRAMEBAND:
  11. test_timeframe_band_summary_min_length_1 — TimeframeBand(summary='', ...) → ValidationError mentioning 'summary'.
  12. test_timeframe_band_summary_max_500 — TimeframeBand(summary='x'*501, ...) → ValidationError.
  13. test_timeframe_band_drivers_count_cap — drivers=['a']*11 → ValidationError.
  14. test_timeframe_band_drivers_per_string_cap — drivers=['x'*201] → ValidationError.
  15. test_timeframe_band_drivers_at_caps_accepted — drivers=['x'*200]*10 — VALID.
  16. test_timeframe_band_confidence_range — confidence=-1 → ValidationError; confidence=101 → ValidationError; 0 and 100 boundaries accepted.

  DISSENT SECTION:
  17. test_dissent_section_defaults — DissentSection() → .has_dissent==False, .dissenting_persona is None, .dissent_summary == ''.
  18. test_dissent_section_populated — DissentSection(has_dissent=True, dissenting_persona='burry', dissent_summary='x'*100) — VALID.
  19. test_dissent_section_summary_max_500 — DissentSection(dissent_summary='x'*501) → ValidationError.

  OPEN OBSERVATION:
  20. test_open_observation_max_500 — open_observation='x'*501 → ValidationError.
  21. test_open_observation_default_empty — TickerDecision(...) without open_observation → .open_observation == ''.

  DATA_UNAVAILABLE INVARIANT:
  22. test_data_unavailable_clean_path — data_unavailable=True with recommendation='hold' + conviction='low' + safe TimeframeBands + DissentSection() — VALID.
  23. test_data_unavailable_invariant_violation_recommendation — data_unavailable=True + recommendation='buy' → ValidationError mentioning 'data_unavailable' AND 'recommendation'.
  24. test_data_unavailable_invariant_violation_conviction — data_unavailable=True + recommendation='hold' + conviction='high' → ValidationError mentioning 'data_unavailable' AND 'conviction'.

  JSON ROUND-TRIP:
  25. test_json_round_trip_minimal — TickerDecision with minimal valid fields → model_dump_json → model_validate_json → equal.
  26. test_json_round_trip_full — TickerDecision with all fields populated, dissent active, drivers populated → round-trip equal.

  INDEPENDENCE:
  27. test_ticker_decision_not_subclass_of_signal_or_position — assert not issubclass(TickerDecision, AgentSignal); assert not issubclass(TickerDecision, PositionSignal); assert not issubclass(TimeframeBand, AgentSignal); etc.

  Total: ≥18 tests minimum, ~25 with parametrized expansions. -->
</implementation_sketch>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: TickerDecision + DissentSection + TimeframeBand schema (RED → GREEN, ≥18 tests)</name>
  <files>tests/synthesis/test_decision.py, synthesis/decision.py, tests/conftest.py</files>
  <behavior>
    Locked schema per 05-CONTEXT.md TickerDecision section + 05-RESEARCH.md Open Question #3 (the @model_validator). Same TDD shape as Phase 4's 04-02 (PositionSignal schema): write the test file first, watch it fail with ImportError on `synthesis.decision`, implement the module, watch tests turn green, regression-check the rest of the suite.

    BEFORE TESTING: ensure the `frozen_now` fixture is visible from `tests/synthesis/`. Two options — verify which is in place:
    (a) `tests/conftest.py` already exists with `frozen_now` defined → no action needed; pytest auto-discovers from rootdir.
    (b) `tests/conftest.py` does NOT exist → create it with `frozen_now` (lift from tests/analysts/conftest.py); leave tests/analysts/conftest.py unchanged (its synthetic_*_history builders are analyst-specific and stay there).
    (c) frozen_now lives only in tests/analysts/conftest.py → create tests/conftest.py with the same fixture; tests/analysts/conftest.py keeps the duplicate (defensive — Phase 3 tests still see it via local discovery; new tests/synthesis/ tests see it via root discovery).

    Implementation per implementation_sketch above — NO deviations. The model_validator must produce error messages including BOTH the field name and its actual value (for debuggability), with the literal substring "data_unavailable=True invariant violated" so the violation tests can grep on it.

    Tests in `tests/synthesis/test_decision.py` (≥18, ideally ~25-27 with parametrized expansions):

    SHAPE / DEFAULTS:
    - test_minimum_valid_ticker_decision: build a complete valid TickerDecision; assert .schema_version==1, .open_observation=='', .data_unavailable is False, .recommendation/conviction/short_term/long_term/dissent populated as supplied.
    - test_extra_field_forbidden: TickerDecision(..., metadata={'x': 1}) → ValidationError.
    - test_schema_version_default_is_1: TickerDecision(...) without schema_version → .schema_version == 1.
    - test_schema_version_forward_compat: TickerDecision(..., schema_version=2) — VALID (forward compat hook for Phase 9 + v1.x).

    TICKER NORMALIZATION:
    - test_ticker_normalization: TickerDecision(ticker='brk.b', ...) → .ticker == 'BRK-B'.
    - test_ticker_invalid_raises: TickerDecision(ticker='123!@#', ...) → ValidationError with 'ticker' in loc.

    ENUM COVERAGE:
    - test_recommendation_6_values_accepted: parametrize over ['add', 'trim', 'hold', 'take_profits', 'buy', 'avoid']; each constructs cleanly. Use conviction='medium' (data_unavailable=False so invariant doesn't fire).
    - test_recommendation_unknown_rejected: TickerDecision(..., recommendation='strong_buy') → ValidationError with 'recommendation' in loc.
    - test_conviction_3_values_accepted: parametrize over ['low', 'medium', 'high']; each constructs cleanly.
    - test_conviction_unknown_rejected: TickerDecision(..., conviction='very_high') → ValidationError with 'conviction' in loc.
    - test_timeframe_literal_2_values: from synthesis.decision import Timeframe; assert get_args(Timeframe) == ('short_term', 'long_term').

    TIMEFRAMEBAND:
    - test_timeframe_band_summary_min_length_1: TimeframeBand(summary='', drivers=[], confidence=50) → ValidationError mentioning 'summary'.
    - test_timeframe_band_summary_max_500: TimeframeBand(summary='x'*501, ...) → ValidationError.
    - test_timeframe_band_summary_at_500_accepted: TimeframeBand(summary='x'*500, drivers=[], confidence=50) — VALID.
    - test_timeframe_band_drivers_count_cap: TimeframeBand(summary='ok', drivers=['a']*11, confidence=50) → ValidationError.
    - test_timeframe_band_drivers_per_string_cap: TimeframeBand(summary='ok', drivers=['x'*201], confidence=50) → ValidationError mentioning 'driver string exceeds 200 chars'.
    - test_timeframe_band_drivers_at_caps_accepted: TimeframeBand(summary='ok', drivers=['x'*200]*10, confidence=50) — VALID (10 items, each 200 chars).
    - test_timeframe_band_confidence_negative_rejected: TimeframeBand(summary='ok', drivers=[], confidence=-1) → ValidationError.
    - test_timeframe_band_confidence_above_100_rejected: confidence=101 → ValidationError.
    - test_timeframe_band_confidence_boundaries: confidence=0 and confidence=100 both accepted.
    - test_timeframe_band_extra_field_forbidden: TimeframeBand(summary='ok', drivers=[], confidence=50, foo='bar') → ValidationError.

    DISSENT SECTION:
    - test_dissent_section_defaults: DissentSection() → .has_dissent is False, .dissenting_persona is None, .dissent_summary == ''.
    - test_dissent_section_populated: DissentSection(has_dissent=True, dissenting_persona='burry', dissent_summary='burry dissents (bearish, conf=45): hidden risk in margin compression') — VALID.
    - test_dissent_section_summary_max_500: DissentSection(dissent_summary='x'*501) → ValidationError.
    - test_dissent_section_extra_field_forbidden: DissentSection(foo='bar') → ValidationError.

    OPEN OBSERVATION:
    - test_open_observation_max_500: TickerDecision(..., open_observation='x'*501) → ValidationError.
    - test_open_observation_default_empty: TickerDecision(...) without open_observation → .open_observation == ''.
    - test_open_observation_at_500_accepted: open_observation='x'*500 — VALID.

    DATA_UNAVAILABLE INVARIANT:
    - test_data_unavailable_clean_path: TickerDecision(ticker='AAPL', computed_at=frozen_now, data_unavailable=True, recommendation='hold', conviction='low', short_term=TimeframeBand(summary='data unavailable: snapshot missing', drivers=[], confidence=0), long_term=TimeframeBand(summary='data unavailable: snapshot missing', drivers=[], confidence=0), dissent=DissentSection(), open_observation='snapshot data_unavailable=True') — VALID.
    - test_data_unavailable_invariant_violation_recommendation: data_unavailable=True + recommendation='buy' → ValidationError mentioning 'data_unavailable=True invariant violated' AND 'recommendation' in error message.
    - test_data_unavailable_invariant_violation_conviction: data_unavailable=True + recommendation='hold' + conviction='high' → ValidationError mentioning 'data_unavailable=True invariant violated' AND 'conviction'.
    - test_data_unavailable_invariant_violation_both: data_unavailable=True + recommendation='buy' + conviction='high' → ValidationError mentioning BOTH 'recommendation' AND 'conviction' in error message (single ValueError captures both problems).

    JSON ROUND-TRIP:
    - test_json_round_trip_minimal: build a TickerDecision with minimal valid fields → s.model_dump_json() → TickerDecision.model_validate_json(s_json) yields equal object.
    - test_json_round_trip_full: build a TickerDecision with all fields populated, dissent active, drivers populated, schema_version=2 → round-trip yields equal object. Confirms datetime ISO-8601 + nested model serialization work.

    INDEPENDENCE:
    - test_ticker_decision_not_subclass_of_other_signals: from analysts.signals import AgentSignal; from analysts.position_signal import PositionSignal; from synthesis.decision import TickerDecision, TimeframeBand, DissentSection; assert not issubclass(TickerDecision, AgentSignal); assert not issubclass(TickerDecision, PositionSignal); assert not issubclass(TimeframeBand, AgentSignal); assert not issubclass(DissentSection, AgentSignal). Locks the PEER-not-subtype contract.

    Total: ~28 tests ≥ ≥18 minimum.
  </behavior>
  <action>
    PRE-WORK (verify frozen_now visibility):
    0. Check whether `tests/conftest.py` exists at repo root:
       ```bash
       ls tests/conftest.py 2>/dev/null
       ```
       If absent: create `tests/conftest.py` with the `frozen_now` fixture lifted verbatim from `tests/analysts/conftest.py`:
       ```python
       """Repo-root conftest — fixtures inherited by every test sub-package.

       The `frozen_now` fixture is lifted here so tests/synthesis/ + tests/routine/
       (Phase 5) inherit it without re-declaring. tests/analysts/conftest.py
       continues to host its analyst-specific synthetic_*_history builders.
       """
       from datetime import datetime, timezone

       import pytest

       FROZEN_DT = datetime(2026, 5, 1, 13, 30, 0, tzinfo=timezone.utc)


       @pytest.fixture
       def frozen_now() -> datetime:
           """Pinned UTC datetime — pass as `computed_at=` for byte-stable assertions."""
           return FROZEN_DT
       ```
       NOTE: tests/analysts/conftest.py keeps its own `frozen_now` definition for
       defensive backwards compat (Phase 3 + Phase 4 tests still reference it
       via local discovery; the duplicate is harmless — Pytest fixture resolution
       picks the closest one).

    RED:
    1. Write `tests/synthesis/test_decision.py` with the ≥18 tests above. Imports:
       ```python
       import json
       import pytest
       from datetime import datetime, timezone
       from typing import get_args

       from pydantic import ValidationError

       from synthesis.decision import (
           ConvictionBand,
           DecisionRecommendation,
           DissentSection,
           TickerDecision,
           Timeframe,
           TimeframeBand,
       )
       ```
    2. Run `poetry run pytest tests/synthesis/test_decision.py -x -q` → ImportError on `synthesis.decision` (module does not exist; only `synthesis/__init__.py` exists from Wave 0).
    3. Commit (RED): `test(05-02): add failing tests for TickerDecision + TimeframeBand + DissentSection schemas (LLM-06; ≥18 tests covering enum coverage, length caps, data_unavailable invariant, JSON round-trip)`.

    GREEN:
    4. Implement `synthesis/decision.py` per the implementation_sketch verbatim:
       - Provenance docstring (~30 lines) referencing TauricResearch/TradingAgents portfolio_manager.py per INFRA-07; lists the 6 modifications (6-state recommendation, dissent section, dual-timeframe, ConfigDict extra='forbid', ticker normalize delegation, data_unavailable @model_validator).
       - Imports: `from __future__ import annotations`; `datetime`; `Literal`; `BaseModel, ConfigDict, Field, field_validator, model_validator`; `from analysts.schemas import normalize_ticker`.
       - 3 Literal types at module level: `DecisionRecommendation` (6 values), `ConvictionBand` (3 values), `Timeframe` (2 values).
       - `TimeframeBand(BaseModel)` class: ConfigDict(extra='forbid'); summary/drivers/confidence fields; `_drivers_strings_capped` field validator.
       - `DissentSection(BaseModel)` class: ConfigDict(extra='forbid'); 3 fields with locked defaults.
       - `TickerDecision(BaseModel)` class: ConfigDict(extra='forbid'); 10 fields; `_normalize_ticker_field` field validator delegating to normalize_ticker; `_data_unavailable_implies_safe_defaults` model validator producing the locked error message format.
    5. Run `poetry run pytest tests/synthesis/test_decision.py -v` → all ≥18 tests green.
    6. Coverage check: `poetry run pytest --cov=synthesis.decision --cov-branch tests/synthesis/test_decision.py` → ≥90% line / ≥85% branch on `synthesis/decision.py`.
    7. Phase 1-4 + Wave 0 regression: `poetry run pytest -x -q` → all existing tests still GREEN. The new module is additive only — doesn't import from or modify any Phase 1-4 file.
    8. Sanity import check: `poetry run python -c "from synthesis.decision import TickerDecision, DissentSection, TimeframeBand, DecisionRecommendation, ConvictionBand, Timeframe; from analysts.signals import AgentSignal; from analysts.position_signal import PositionSignal; assert not issubclass(TickerDecision, AgentSignal); assert not issubclass(TickerDecision, PositionSignal); assert not issubclass(TimeframeBand, AgentSignal); print('peer-not-subtype OK')"`.
    9. Sanity grep for provenance: `grep -n 'TauricResearch/TradingAgents' synthesis/decision.py` returns at least 1 match (the provenance docstring lineage).
    10. Commit (GREEN): `feat(05-02): TickerDecision + DissentSection + TimeframeBand Pydantic schemas with data_unavailable invariant + 6/3/2-state Literal enums (LLM-06)`.
  </action>
  <verify>
    <automated>poetry run pytest tests/synthesis/test_decision.py -v && poetry run pytest --cov=synthesis.decision --cov-branch tests/synthesis/test_decision.py && poetry run pytest -x -q && poetry run python -c "from synthesis.decision import TickerDecision, DissentSection, TimeframeBand, DecisionRecommendation, ConvictionBand, Timeframe; from typing import get_args; assert get_args(DecisionRecommendation) == ('add', 'trim', 'hold', 'take_profits', 'buy', 'avoid'); assert get_args(ConvictionBand) == ('low', 'medium', 'high'); assert get_args(Timeframe) == ('short_term', 'long_term'); from analysts.signals import AgentSignal; from analysts.position_signal import PositionSignal; assert not issubclass(TickerDecision, AgentSignal); assert not issubclass(TickerDecision, PositionSignal); print('OK')" && grep -n 'TauricResearch/TradingAgents' synthesis/decision.py</automated>
  </verify>
  <done>synthesis/decision.py shipped (~80-110 LOC) with 3 Literal types + TimeframeBand + DissentSection + TickerDecision classes + 3 validators (ticker normalization, drivers per-string cap, data_unavailable invariant); provenance docstring references TauricResearch/TradingAgents portfolio_manager.py per INFRA-07; ≥18 tests in tests/synthesis/test_decision.py all GREEN (parametrized over 6+3+2 enum values + length caps + ticker normalization + extra-field rejection + invariant violations + JSON round-trip + PEER-not-subtype); coverage ≥90% line / ≥85% branch on the new module; Phase 1-4 + Wave 0 regression GREEN; tests/conftest.py created or extended with frozen_now if not already present; both commits (RED + GREEN) landed.</done>
</task>

</tasks>

<verification>
- 1 task, 2 commits (RED + GREEN). TDD discipline preserved.
- Coverage gate: ≥90% line / ≥85% branch on `synthesis/decision.py`.
- Phase 1-4 + Wave 0 regression invariant: existing 433+ tests stay GREEN. The new module is additive only.
- TickerDecision schema enforces every invariant locked in 05-CONTEXT.md + 05-RESEARCH.md Open Question #3, including the @model_validator (data_unavailable=True ⟹ recommendation='hold' AND conviction='low').
- DecisionRecommendation Literal exactly 6 values; ConvictionBand exactly 3; Timeframe exactly 2 — verified by parametrized + arity tests.
- Ticker normalization delegates to `analysts.schemas.normalize_ticker` — same single-source-of-truth pattern as AgentSignal + PositionSignal + every analysts.data.* schema.
- Drivers cap: Field(max_length=10) for count + custom @field_validator for per-string ≤200 chars (mirrors AgentSignal.evidence + PositionSignal.evidence).
- TimeframeBand summary: Field(min_length=1, max_length=500); confidence: Field(ge=0, le=100, int).
- ConfigDict(extra='forbid') on all 3 models; JSON round-trip works (datetime ISO-8601 default Pydantic v2 serialization).
- PEER-not-subtype: TickerDecision is NOT a subclass of AgentSignal or PositionSignal — locked by test.
- Provenance per INFRA-07: docstring references TauricResearch/TradingAgents/tradingagents/agents/managers/portfolio_manager.py + names 6 modifications.
- schema_version=1 default + schema_version=2 acceptance — forward compat hook for Phase 9 + v1.x.
- Wave 4 (05-05 synthesizer) unblocked: imports `TickerDecision`, `DissentSection`, `TimeframeBand`, `DecisionRecommendation`, `ConvictionBand` from this plan's `synthesis/decision.py`.

## Cross-Scope Risks

_vault_status=budget_exhausted; re-run /gmd:plan-phase --replan after vault-maintain_
</verification>

<success_criteria>
1. `synthesis/decision.py` exports `TickerDecision`, `DissentSection`, `TimeframeBand`, `DecisionRecommendation`, `ConvictionBand`, `Timeframe`.
2. TickerDecision has all 10 fields per the locked CONTEXT.md schema (ticker, computed_at, schema_version, recommendation, conviction, short_term, long_term, open_observation, dissent, data_unavailable).
3. DecisionRecommendation Literal accepts EXACTLY: add, trim, hold, take_profits, buy, avoid (in that order).
4. ConvictionBand Literal accepts EXACTLY: low, medium, high (in that order).
5. Timeframe Literal accepts EXACTLY: short_term, long_term.
6. ConfigDict(extra='forbid') discipline on all 3 models; @field_validator('ticker') delegates to normalize_ticker; @field_validator('drivers') enforces ≤200-char per-string cap; @model_validator(mode='after') enforces the data_unavailable invariant.
7. ≥18 tests in `tests/synthesis/test_decision.py`, all GREEN; coverage ≥90% line / ≥85% branch on `synthesis/decision.py`.
8. PEER-not-subtype contract verified via `not issubclass(TickerDecision, AgentSignal)` + `not issubclass(TickerDecision, PositionSignal)` test.
9. JSON round-trip works (model_dump_json → model_validate_json yields equal object) for both minimal and fully-populated TickerDecision instances.
10. tests/conftest.py exists at repo root with `frozen_now` fixture (created or extended if absent); tests/analysts/conftest.py unchanged (its synthetic_*_history builders preserved).
11. Provenance per INFRA-07: synthesis/decision.py docstring contains literal substring `TauricResearch/TradingAgents`.
12. Full repo regression GREEN (Phase 1 + Phase 2 + Phase 3 + Phase 4 + Wave 0 + this plan).
13. Wave 4 (Plan 05-05 synthesizer + dissent rule) unblocked — can now import all needed types from `synthesis.decision`.
</success_criteria>

<output>
After completion, create `.planning/phases/05-claude-routine-wiring/05-02-SUMMARY.md` summarizing the 2 commits, naming the TickerDecision contract (10 fields + 3 nested types + 3 Literal enums + 3 validators including the data_unavailable invariant), and forward-flagging Wave 4 (05-05 synthesizer) as the consumer.

Update `.planning/STATE.md` Recent Decisions with a 05-02 entry naming: TickerDecision + DissentSection + TimeframeBand schemas locked at `synthesis/decision.py` (PEER of AgentSignal AND PositionSignal); data_unavailable invariant enforced at the schema layer via @model_validator (closes Pitfall #4-class drift; matches Phase 3 + Phase 4 precedent); 6-state DecisionRecommendation + 3-state ConvictionBand + 2-state Timeframe Literal types exported; schema_version=1 forward-compat hook landed; Wave 2 (05-03 LLM client) and Wave 4 (05-05 synthesizer) unblocked.
</output>
</content>
</invoke>