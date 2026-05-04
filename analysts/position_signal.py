# novel-to-this-project — Phase 4 schema (PEER of AgentSignal); state ladder + action_hint not present in reference repos.
"""PositionSignal — locked output schema for Phase 4 Position-Adjustment Radar.

Separate from AgentSignal because state ladder + action_hint + per-indicator
dict + trend_regime flag don't fit AgentSignal's verdict-ladder shape.
PEER-level, NOT subtype — see 04-RESEARCH.md Pattern #7.

Field shapes diverge cleanly:
  * AgentSignal carries `verdict: Verdict` (5-state directional ladder).
    PositionSignal carries `state: PositionState` (5-state mean-reversion ladder).
  * PositionSignal additionally carries:
      - `action_hint: ActionHint` — pre-recommendation hint (consider_add /
        hold_position / consider_trim / consider_take_profits).
      - `indicators: dict[str, float | None]` — per-indicator raw readings
        (rsi_14 / bb_position / zscore_50 / stoch_k / williams_r /
        macd_histogram / adx_14) for transparency + Phase 6 deep-dive rendering.
      - `trend_regime: bool` — True when ADX(14) > 25; mean-reversion
        indicators are downweighted in scoring.

Pydantic validators reuse:
  * ConfigDict(extra="forbid") — same discipline as AgentSignal.
  * Ticker normalization via analysts.schemas.normalize_ticker — same
    delegation pattern used in every analysts.data.* sub-schema.
  * Evidence cap (≤10 items via Field(max_length=10), ≤200 chars per item via
    @field_validator) — same as AgentSignal.
  * @model_validator(mode="after") enforces the data_unavailable=True
    invariant (state='fair' AND consensus_score=0.0 AND confidence=0 AND
    action_hint='hold_position' AND trend_regime=False) — closes
    04-RESEARCH.md Pitfall #1. Same shape as Phase 3's AgentSignal invariant
    (analysts/signals.py: _data_unavailable_implies_neutral_zero).

Validator duplication note: ~30 LOC of ticker-normalization + evidence-cap
validator code overlaps with AgentSignal. Accepted per 04-RESEARCH.md
Pattern #7 — a shared base class would force a generic schema (string-typed
state field with type discriminator) that's strictly worse than two clean
peer models. The duplicated validators are simple delegations to
analysts.schemas.normalize_ticker + a stateless string-length check; trivial
to keep in sync; any drift surfaces in tests immediately.

Phase 5 synthesizer reads the four AgentSignals + this PositionSignal as a
list-of-mixed-types; Phase 6 frontend deserializes via Pydantic round-trip;
Phase 7 Decision-Support reads state + action_hint + confidence directly.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from analysts.schemas import normalize_ticker

# ---------------------------------------------------------------------------
# Literal types — module-level so importers can `from analysts.position_signal
# import PositionSignal, PositionState, ActionHint` (mirrors analysts/signals.py
# pattern of co-locating Verdict + AnalystId with AgentSignal).
# ---------------------------------------------------------------------------

PositionState = Literal[
    "extreme_oversold",
    "oversold",
    "fair",
    "overbought",
    "extreme_overbought",
]

ActionHint = Literal[
    "consider_add",
    "hold_position",
    "consider_trim",
    "consider_take_profits",
]


class PositionSignal(BaseModel):
    """Position-Adjustment Radar output — multi-indicator overbought/oversold consensus.

    Self-identifying — `ticker + computed_at` carry context so a serialized
    PositionSignal stands alone (mirrors AgentSignal). Phase 5 will JSON-
    serialize this alongside the four AgentSignals into
    data/YYYY-MM-DD/{ticker}.json.

    Defaults — state='fair', consensus_score=0.0, confidence=0,
    action_hint='hold_position', evidence=[], indicators={},
    data_unavailable=False, trend_regime=False — match the canonical
    'no opinion' shape an analyst emits when its inputs are present but
    truly inconclusive (state='fair' with non-zero confidence is meaningful:
    'we computed 6 indicators, they don't agree, leaning neither way').
    """

    model_config = ConfigDict(extra="forbid")

    ticker: str
    computed_at: datetime
    state: PositionState = "fair"
    consensus_score: float = Field(ge=-1.0, le=1.0, default=0.0)
    confidence: int = Field(ge=0, le=100, default=0)
    action_hint: ActionHint = "hold_position"
    indicators: dict[str, float | None] = Field(default_factory=dict)
    evidence: list[str] = Field(default_factory=list, max_length=10)
    data_unavailable: bool = False
    trend_regime: bool = False

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
                raise ValueError(
                    f"evidence string exceeds 200 chars (got {len(s)}): {s[:60]!r}..."
                )
        return v

    @model_validator(mode="after")
    def _data_unavailable_implies_fair_zero(self) -> "PositionSignal":
        """Schema-level invariant: data_unavailable=True ⟹ canonical no-opinion shape.

        Closes Pitfall #1 from 04-RESEARCH.md. Same pattern as AgentSignal's
        Phase 3 invariant (analysts/signals.py: _data_unavailable_implies_neutral_zero).
        """
        if self.data_unavailable:
            problems: list[str] = []
            if self.state != "fair":
                problems.append(f"state={self.state!r} (expected 'fair')")
            if self.consensus_score != 0.0:
                problems.append(
                    f"consensus_score={self.consensus_score} (expected 0.0)"
                )
            if self.confidence != 0:
                problems.append(f"confidence={self.confidence} (expected 0)")
            if self.action_hint != "hold_position":
                problems.append(
                    f"action_hint={self.action_hint!r} (expected 'hold_position')"
                )
            if self.trend_regime is not False:
                problems.append(
                    f"trend_regime={self.trend_regime!r} (expected False)"
                )
            if problems:
                raise ValueError(
                    "data_unavailable=True invariant violated: "
                    + ", ".join(problems)
                )
        return self
