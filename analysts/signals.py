"""AgentSignal — locked output contract for all four Phase 3 analysts.

Pattern adapted from virattt/ai-hedge-fund's signal/confidence/reasoning
Pydantic shape used in src/agents/*.py —
https://github.com/virattt/ai-hedge-fund/tree/main/src/agents

Modifications from the reference implementation:
  * 5-state Verdict ladder (strong_bullish | bullish | neutral | bearish |
    strong_bearish) instead of 3-state (bullish | bearish | neutral); the
    extra magnitude is consumed by the Phase 5 dissent calc and the Phase 6
    rendering.
  * `evidence: list[str]` (≤10 items, ≤200 chars each) replaces the reference
    repo's `reasoning: str` — locked by REQUIREMENTS.md ANLY-01..04.
  * ConfigDict(extra='forbid') — disallows the metadata escape hatch we
    deliberately rejected in 03-CONTEXT.md (preserves schema discipline).
  * Ticker normalized via the project's single-source-of-truth helper
    `analysts.schemas.normalize_ticker` (mirrors PriceSnapshot, Snapshot,
    FundamentalsSnapshot, Headline, etc.).
  * `data_unavailable: bool` flag is explicit (matches the existing convention
    across analysts.data.* sub-schemas).
  * @model_validator(mode='after') enforces the data_unavailable=True ⟹
    verdict='neutral' AND confidence=0 invariant locked in 03-RESEARCH.md
    Pitfall #4 — this is a SCHEMA-level guarantee, not a caller convention.

Public surface (re-imported by every Wave 2 analyst module
03-02/03-03/03-04/03-05 and by tests/analysts/test_invariants.py):
    Verdict     — Literal of the 5 ladder values
    AnalystId   — Literal of the 4 analyst module ids
    AgentSignal — the model
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from analysts.schemas import normalize_ticker

Verdict = Literal["strong_bullish", "bullish", "neutral", "bearish", "strong_bearish"]
AnalystId = Literal[
    # Phase 3 analytical analysts (existing 4) — order preserved:
    "fundamentals",
    "technicals",
    "news_sentiment",
    "valuation",
    # Phase 5 persona slate (new 6) — order matches the iteration order
    # used by routine/persona_runner.py asyncio.gather fan-out (Wave 3):
    "buffett",
    "munger",
    "wood",
    "burry",
    "lynch",
    "claude_analyst",
]


class AgentSignal(BaseModel):
    """One analyst's verdict on one ticker, computed at one point in time.

    Self-identifying — `ticker + analyst_id + computed_at` carry context so a
    serialized AgentSignal stands alone (mirrors how PriceSnapshot etc. carry
    their own ticker + fetched_at). Phase 5 will JSON-serialize four
    AgentSignals per ticker per day into data/YYYY-MM-DD/{ticker}.json
    alongside the Snapshot.

    Defaults — verdict='neutral', confidence=0, evidence=[], data_unavailable=False —
    match the canonical 'neutral signal' shape an analyst emits when its inputs
    are present but truly inconclusive (verdict=neutral with non-zero confidence
    is meaningful: "we looked, evidence is mixed, leaning neither way").
    """

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
        # Same delegation pattern used in every analysts.data.* sub-schema —
        # single source of truth for ticker normalization. Returns canonical
        # hyphen form (BRK-B), or raises ValueError for non-string / regex
        # mismatch input which Pydantic surfaces as a ValidationError with
        # ('ticker',) in the loc path.
        norm = normalize_ticker(v) if isinstance(v, str) else None
        if norm is None:
            raise ValueError(f"invalid ticker {v!r}")
        return norm

    @field_validator("evidence")
    @classmethod
    def _evidence_strings_capped(cls, v: list[str]) -> list[str]:
        # Pydantic's Field(max_length=10) handles the COUNT cap; this validator
        # handles the per-string length cap (≤200 chars, matching LLM-04
        # reasoning cap from REQUIREMENTS.md).
        for s in v:
            if len(s) > 200:
                raise ValueError(
                    f"evidence string exceeds 200 chars (got {len(s)}): {s[:60]!r}..."
                )
        return v

    @model_validator(mode="after")
    def _data_unavailable_implies_neutral_zero(self) -> "AgentSignal":
        """Schema-level invariant: data_unavailable=True ⟹ verdict='neutral' AND confidence=0.

        Closes Pitfall #4 from 03-RESEARCH.md — every analyst that emits
        data_unavailable=True MUST also emit a neutral verdict with zero
        confidence. Catching the violation here means a buggy analyst can
        never write a (data_unavailable=True, verdict='bullish', confidence=80)
        signal to disk; Phase 5/6 consumers can rely on the contract without
        defensive checks.

        Error message names BOTH offending values so a debugging analyst
        author can see exactly what they sent.
        """
        if self.data_unavailable:
            problems: list[str] = []
            if self.verdict != "neutral":
                problems.append(f"verdict={self.verdict!r} (expected 'neutral')")
            if self.confidence != 0:
                problems.append(f"confidence={self.confidence} (expected 0)")
            if problems:
                raise ValueError(
                    f"data_unavailable=True invariant violated: {', '.join(problems)}"
                )
        return self
