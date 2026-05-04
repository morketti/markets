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

# Phase 6 / Plan 06-01 (Wave 0 amendment): per-timeframe thesis status.
#
# Drives the frontend Long-Term Thesis Status lens (VIEW-04) — sorts by
# severity ('broken' first, then 'weakening'). Default 'n/a' so existing
# Phase 5 v1 snapshots and lite-mode TimeframeBands deserialize without
# ValidationError. The synthesizer (prompts/synthesizer.md) is instructed
# to populate this per timeframe.
ThesisStatus = Literal[
    "intact",
    "weakening",
    "broken",
    "improving",
    "n/a",
]


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
    # Phase 6 / Plan 06-01 — per-timeframe thesis state for Long-Term Thesis
    # Status lens. Default 'n/a' makes the field addition non-breaking for
    # every existing TickerDecision deserialization (v1 snapshots have no
    # thesis_status field; reading them with the v2 schema must not fail).
    thesis_status: ThesisStatus = "n/a"

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

    The `schema_version: int = 2` lock is the forward-compat hook for Phase 9
    + v1.x. Frontend reads schema_version first; if it sees a version > 2, it
    can choose to render with v2 fields only (graceful degradation) or surface
    a "schema upgrade required" notice. Phase 6 / Plan 06-01 bumped the
    default 1 → 2 alongside the per-ticker JSON shape extension
    (ohlc_history + indicators + headlines + TimeframeBand.thesis_status).

    Defaults: schema_version=2, open_observation='', data_unavailable=False.
    No defaults on the 5 required fields (recommendation, conviction,
    short_term, long_term, dissent) — synthesizer MUST populate all of them
    explicitly. data_unavailable=True path uses _data_unavailable_decision
    helper in synthesis/synthesizer.py (Wave 4) to fill the required fields
    with safe defaults that satisfy the @model_validator invariant.
    """

    model_config = ConfigDict(extra="forbid")

    ticker: str
    computed_at: datetime
    schema_version: int = 2
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
