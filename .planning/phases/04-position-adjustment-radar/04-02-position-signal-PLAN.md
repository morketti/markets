---
phase: 04-position-adjustment-radar
plan: 02
type: tdd
wave: 2
depends_on: [04-01]
files_modified:
  - analysts/position_signal.py
  - tests/analysts/test_position_signal.py
autonomous: true
requirements: [POSE-02, POSE-04]
provides:
  - "analysts/position_signal.py — `PositionSignal` Pydantic v2 model + `PositionState` Literal (5-state mean-reversion ladder) + `ActionHint` Literal (4-state pre-recommendation hint)"
  - "PositionSignal field surface: ticker (normalized via analysts.schemas.normalize_ticker), computed_at, state (default 'fair'), consensus_score ∈ [-1, +1] (default 0.0), confidence ∈ [0, 100] (default 0), action_hint (default 'hold_position'), indicators dict[str, float | None], evidence list[str] (≤10 items, ≤200 chars each), data_unavailable bool (default False), trend_regime bool (default False)"
  - "@model_validator(mode='after') enforcing the data_unavailable=True invariant: data_unavailable=True ⟹ state='fair' AND consensus_score==0.0 AND confidence==0 AND action_hint='hold_position' AND trend_regime==False (closes 04-RESEARCH.md Pitfall #1)"
  - "ConfigDict(extra='forbid'), @field_validator('ticker', mode='before') delegating to normalize_ticker, @field_validator('evidence') enforcing per-string ≤200 char cap (the Field(max_length=10) handles count separately)"
  - "PEER-level peer to AgentSignal — separate Pydantic model, NOT subclass; ~30 LOC of validator duplication (ticker normalization + evidence cap) accepted per 04-RESEARCH.md Pattern #7 to keep both schemas standalone-readable"
tags: [phase-4, schema, position-signal, tdd, wave-1, foundation, pose-02, pose-04]

must_haves:
  truths:
    - "PositionSignal validates: ticker normalized via analysts.schemas.normalize_ticker; computed_at is datetime; state is PositionState Literal (5-state); consensus_score ∈ [-1, +1] (Pydantic Field ge/le); confidence ∈ [0, 100] (Pydantic Field ge/le, int); action_hint is ActionHint Literal (4-state); indicators is dict[str, float | None]; evidence ≤10 items each ≤200 chars; data_unavailable bool; trend_regime bool; ConfigDict(extra='forbid')"
    - "Default values match the canonical no-opinion shape: state='fair', consensus_score=0.0, confidence=0, action_hint='hold_position', indicators={}, evidence=[], data_unavailable=False, trend_regime=False"
    - "PositionState Literal accepts EXACTLY 5 values: extreme_oversold | oversold | fair | overbought | extreme_overbought (parametrized test verifies each constructs cleanly when data_unavailable=False)"
    - "ActionHint Literal accepts EXACTLY 4 values: consider_add | hold_position | consider_trim | consider_take_profits"
    - "Ticker normalization: PositionSignal(ticker='brk.b', ...) → .ticker == 'BRK-B' (delegates to analysts.schemas.normalize_ticker — same pattern as AgentSignal and Snapshot)"
    - "Invalid ticker: PositionSignal(ticker='123!@#', ...) → ValidationError with 'ticker' in loc"
    - "Extra field rejection: PositionSignal(..., metadata={'x': 1}) → ValidationError ('metadata' not allowed; ConfigDict extra='forbid')"
    - "Evidence cap (count): PositionSignal(..., evidence=['a'] * 11) → ValidationError (Field max_length=10)"
    - "Evidence cap (per-string): PositionSignal(..., evidence=['x' * 201]) → ValidationError (custom @field_validator)"
    - "consensus_score range: PositionSignal(..., consensus_score=1.01) → ValidationError; PositionSignal(..., consensus_score=-1.01) → ValidationError; -1.0 and +1.0 boundaries accepted cleanly"
    - "confidence range: PositionSignal(..., confidence=-1) → ValidationError; PositionSignal(..., confidence=101) → ValidationError; 0 and 100 boundaries accepted cleanly"
    - "data_unavailable invariant — state violation: PositionSignal(..., data_unavailable=True, state='oversold') → ValidationError mentioning 'data_unavailable' AND 'state'"
    - "data_unavailable invariant — consensus_score violation: PositionSignal(..., data_unavailable=True, consensus_score=-0.5) → ValidationError mentioning 'data_unavailable' AND 'consensus_score'"
    - "data_unavailable invariant — confidence violation: PositionSignal(..., data_unavailable=True, confidence=80) → ValidationError mentioning 'data_unavailable' AND 'confidence'"
    - "data_unavailable invariant — action_hint violation: PositionSignal(..., data_unavailable=True, action_hint='consider_add') → ValidationError mentioning 'data_unavailable' AND 'action_hint'"
    - "data_unavailable invariant — trend_regime violation: PositionSignal(..., data_unavailable=True, trend_regime=True) → ValidationError mentioning 'data_unavailable' AND 'trend_regime'"
    - "data_unavailable clean path: PositionSignal(ticker='AAPL', computed_at=frozen_now, data_unavailable=True, evidence=['snapshot data_unavailable=True'], indicators={'rsi_14': None, ...}) — VALID (all defaults match invariant)"
    - "JSON round-trip: model_dump_json → model_validate_json yields equal object (datetime ISO-8601 serialization works; ConfigDict extra='forbid' doesn't reject its own JSON output)"
    - "Independence from AgentSignal: PositionSignal is NOT a subclass of AgentSignal; importing AgentSignal does NOT create a name collision; Phase 5 can import both side by side"
    - "Coverage ≥90% line / ≥85% branch on analysts/position_signal.py"
  artifacts:
    - path: "analysts/position_signal.py"
      provides: "PositionSignal + PositionState Literal + ActionHint Literal + provenance docstring + @model_validator(mode='after') data_unavailable invariant; ~80-100 LOC total"
      min_lines: 80
    - path: "tests/analysts/test_position_signal.py"
      provides: "≥12 tests covering schema validation, default values, ticker normalization, range constraints, extra-field rejection, evidence caps, all 5 PositionState literals, all 4 ActionHint literals, every data_unavailable invariant violation case, JSON round-trip, independence from AgentSignal"
      min_lines: 150
  key_links:
    - from: "analysts/position_signal.py"
      to: "analysts.schemas.normalize_ticker"
      via: "@field_validator('ticker', mode='before') reuses single-source-of-truth normalizer (same delegation pattern as AgentSignal in analysts/signals.py and PriceSnapshot in analysts/data/prices.py)"
      pattern: "from analysts\\.schemas import normalize_ticker"
    - from: "analysts/position_signal.py"
      to: "Pydantic v2 @model_validator(mode='after')"
      via: "data_unavailable=True ⟹ state='fair' AND consensus_score=0.0 AND confidence=0 AND action_hint='hold_position' AND trend_regime=False invariant"
      pattern: "@model_validator\\(mode=\"after\"\\)"
    - from: "tests/analysts/test_position_signal.py"
      to: "analysts.position_signal (the unit under test)"
      via: "imports PositionSignal, PositionState, ActionHint; uses frozen_now fixture from conftest.py"
      pattern: "from analysts\\.position_signal import PositionSignal, PositionState, ActionHint"
    - from: "analysts/position_signal.py"
      to: "Phase 5 routine + Phase 6 frontend + Phase 7 Decision-Support (downstream consumers)"
      via: "PositionSignal is the locked output type the Phase 4 score() function emits; Phase 5 serializes it alongside the 4 AgentSignals; Phase 6 deserializes via Pydantic round-trip; Phase 7 reads state + action_hint + confidence"
      pattern: "PositionSignal"
---

<objective>
Wave 1 / POSE-02 + POSE-04 schema scaffold: ship the `PositionSignal` Pydantic v2 model + `PositionState` Literal (5-state mean-reversion ladder) + `ActionHint` Literal (4-state pre-recommendation hint) at `analysts/position_signal.py`. Includes the `@model_validator(mode='after')` enforcing the `data_unavailable=True` invariant — closes 04-RESEARCH.md Pitfall #1 at zero schema-shape cost (mirrors Phase 3's AgentSignal `_data_unavailable_implies_neutral_zero` validator pattern).

Purpose: PositionSignal is the locked output contract for Phase 4. Wave 2's `analysts/position_adjustment.py` (Plan 04-03) imports `PositionSignal` + `PositionState` + `ActionHint` — without this Wave 1 plan shipped first, Wave 2 can't be written. Phase 5 (LLM routine wiring), Phase 6 (frontend morning-scan), and Phase 7 (Decision-Support) all import this same schema as a peer-level type alongside the four `AgentSignal`s. Per 04-RESEARCH.md Pattern #7, PositionSignal is a PEER of AgentSignal, NOT a subclass — field shapes diverge (state ladder vs verdict ladder; action_hint + indicators dict + trend_regime flag are PositionSignal-only). The ~30 LOC of validator duplication (ticker normalization + evidence per-string cap) is accepted as the cost of keeping both schemas standalone-readable.

The `@model_validator(mode='after')` is the new lock vs. CONTEXT.md's bare schema. Without it, an analyst returning `PositionSignal(data_unavailable=True, state='extreme_oversold', consensus_score=-0.8, confidence=80, action_hint='consider_add', ...)` would be schema-accepted — 04-RESEARCH.md Pitfall #1 calls this out as a class of bugs we close at the schema layer (same shape as AgentSignal's invariant in `analysts/signals.py`).

The schema lives in its OWN module (`analysts/position_signal.py`) — separate from Wave 2's `analysts/position_adjustment.py` — for the same reason `analysts/signals.py` lives separately from the four Phase 3 analyst modules. Phase 5/6/7 importers shouldn't pay the indicator-math import cost just to deserialize a stored signal.

Output: analysts/position_signal.py (~80-100 LOC: provenance docstring + 2 Literal types + PositionSignal class with 10 fields + 3 validators); tests/analysts/test_position_signal.py (~180-200 LOC, ≥12 tests covering every invariant, all GREEN).
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
@.planning/phases/04-position-adjustment-radar/04-CONTEXT.md
@.planning/phases/04-position-adjustment-radar/04-RESEARCH.md
@.planning/phases/04-position-adjustment-radar/04-01-foundation-PLAN.md

# Existing patterns to mirror
@analysts/signals.py
@analysts/schemas.py
@analysts/data/prices.py
@analysts/data/snapshot.py
@tests/analysts/conftest.py
@tests/analysts/test_signals.py

<interfaces>
<!-- Existing AgentSignal pattern to mirror — analysts/signals.py: -->

```python
# AgentSignal — peer-level Pydantic model. PositionSignal mirrors its discipline:
#   * ConfigDict(extra="forbid")
#   * @field_validator("ticker", mode="before") delegating to normalize_ticker
#   * @field_validator("evidence") for the per-string ≤200 char cap (Field(max_length=10) handles count)
#   * @model_validator(mode="after") for the data_unavailable invariant

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
                raise ValueError(...)
        return v

    @model_validator(mode="after")
    def _data_unavailable_implies_neutral_zero(self) -> "AgentSignal":
        if self.data_unavailable:
            problems: list[str] = []
            if self.verdict != "neutral":
                problems.append(...)
            if self.confidence != 0:
                problems.append(...)
            if problems:
                raise ValueError(f"data_unavailable=True invariant violated: {', '.join(problems)}")
        return self
```

<!-- analysts.schemas.normalize_ticker — single source of truth for ticker validation: -->

```python
# Returns the canonical normalized ticker (e.g. "brk.b" -> "BRK-B") or None if invalid.
def normalize_ticker(ticker: str) -> Optional[str]: ...
```

<!-- The frozen_now fixture from tests/analysts/conftest.py:138-141 (already shipped): -->

```python
@pytest.fixture
def frozen_now() -> datetime:
    """Pinned UTC datetime — pass as `computed_at=` to score() functions for byte-stable assertions."""
    return FROZEN_DT  # = datetime(2026, 5, 1, 13, 30, 0, tzinfo=timezone.utc)
```

<!-- NEW contract this plan creates — analysts/position_signal.py: -->

```python
PositionState = Literal[
    "extreme_oversold", "oversold", "fair", "overbought", "extreme_overbought"
]
ActionHint = Literal[
    "consider_add", "hold_position", "consider_trim", "consider_take_profits"
]


class PositionSignal(BaseModel):
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
    def _normalize_ticker_field(cls, v: object) -> str: ...

    @field_validator("evidence")
    @classmethod
    def _evidence_strings_capped(cls, v: list[str]) -> list[str]: ...

    @model_validator(mode="after")
    def _data_unavailable_implies_fair_zero(self) -> "PositionSignal":
        # data_unavailable=True ⟹ state='fair' AND consensus_score=0.0 AND
        # confidence=0 AND action_hint='hold_position' AND trend_regime=False
        ...
```
</interfaces>

<implementation_sketch>
<!-- The full file content. Module docstring carries the PEER-not-subtype rationale. -->

```python
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
Pattern #7: a shared base class would force a generic schema (string-typed
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
```

<!-- The test file structure mirrors tests/analysts/test_signals.py one-to-one:
     parametrize over Literal values, ValidationError-asserting tests for every
     boundary, JSON round-trip, default-value snapshot. Use the existing
     `frozen_now` fixture (already in conftest.py from Phase 3 / 03-01). -->
</implementation_sketch>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: PositionSignal schema (RED → GREEN, ≥12 tests)</name>
  <files>tests/analysts/test_position_signal.py, analysts/position_signal.py</files>
  <behavior>
    Locked schema per 04-CONTEXT.md + 04-RESEARCH.md (the latter adds the @model_validator). Same TDD shape as Phase 3's 03-01 Task 3 (AgentSignal schema): write the test file first, watch it fail with ImportError, implement the module, watch tests turn green, regression-check the rest of the suite.

    Tests in `tests/analysts/test_position_signal.py` (≥12):

    SHAPE / DEFAULTS:
    - test_minimum_valid_signal: PositionSignal(ticker="AAPL", computed_at=frozen_now). Asserts: .state=='fair', .consensus_score==0.0, .confidence==0, .action_hint=='hold_position', .indicators=={}, .evidence==[], .data_unavailable is False, .trend_regime is False. All 8 defaults.
    - test_extra_field_forbidden: PositionSignal(ticker="AAPL", computed_at=frozen_now, metadata={"x": 1}) → ValidationError ("metadata" not allowed; ConfigDict extra='forbid').

    TICKER NORMALIZATION:
    - test_ticker_normalization: PositionSignal(ticker="brk.b", computed_at=frozen_now) → .ticker == "BRK-B" (delegates to analysts.schemas.normalize_ticker).
    - test_ticker_invalid_raises: PositionSignal(ticker="123!@#", computed_at=frozen_now) → ValidationError with "ticker" in error loc.

    LITERAL TYPE COVERAGE:
    - test_position_state_5_values_accepted: parametrize over ["extreme_oversold", "oversold", "fair", "overbought", "extreme_overbought"]; each constructs cleanly when data_unavailable=False (the @model_validator only fires when data_unavailable=True, so non-default state is fine here). Use `consensus_score` matching the state to avoid range conflicts (e.g., for extreme_oversold use consensus_score=-0.8).
    - test_position_state_unknown_rejected: PositionSignal(..., state="moonshot") → ValidationError.
    - test_action_hint_4_values_accepted: parametrize over ["consider_add", "hold_position", "consider_trim", "consider_take_profits"].
    - test_action_hint_unknown_rejected: PositionSignal(..., action_hint="buy") → ValidationError.

    RANGE CONSTRAINTS:
    - test_consensus_score_range_accepts_boundaries: PositionSignal(..., consensus_score=-1.0) and PositionSignal(..., consensus_score=1.0) both construct cleanly.
    - test_consensus_score_below_minus_one_rejected: PositionSignal(..., consensus_score=-1.01) → ValidationError.
    - test_consensus_score_above_plus_one_rejected: PositionSignal(..., consensus_score=1.01) → ValidationError.
    - test_confidence_range_accepts_boundaries: PositionSignal(..., confidence=0) and PositionSignal(..., confidence=100) both construct cleanly.
    - test_confidence_negative_rejected: PositionSignal(..., confidence=-1) → ValidationError.
    - test_confidence_above_100_rejected: PositionSignal(..., confidence=101) → ValidationError.

    EVIDENCE CAPS:
    - test_evidence_max_items: PositionSignal(..., evidence=["a"] * 11) → ValidationError (Field(max_length=10)).
    - test_evidence_string_too_long: PositionSignal(..., evidence=["x" * 201]) → ValidationError (custom @field_validator).
    - test_evidence_at_caps_accepted: PositionSignal(..., evidence=["x" * 200] * 10) constructs cleanly (10 items, each 200 chars).
    - test_evidence_empty_list_ok: PositionSignal(..., evidence=[]) constructs cleanly.

    INDICATORS DICT:
    - test_indicators_dict_with_none_values: PositionSignal(..., indicators={"rsi_14": None, "bb_position": None, "zscore_50": None, "stoch_k": None, "williams_r": None, "macd_histogram": None, "adx_14": None}) constructs cleanly. (None is the empty-data warm-up case — every indicator maps to either a float or None.)
    - test_indicators_dict_with_floats: PositionSignal(..., indicators={"rsi_14": 28.4, "stoch_k": 18.5}) constructs cleanly.

    DATA_UNAVAILABLE INVARIANT:
    - test_data_unavailable_clean_path: PositionSignal(ticker="AAPL", computed_at=frozen_now, data_unavailable=True, evidence=["snapshot data_unavailable=True"]) — VALID (all defaults match invariant). Verify the evidence is preserved.
    - test_data_unavailable_invariant_violation_state: PositionSignal(..., data_unavailable=True, state="oversold") → ValidationError mentioning 'data_unavailable' AND 'state'.
    - test_data_unavailable_invariant_violation_consensus_score: PositionSignal(..., data_unavailable=True, consensus_score=-0.5) → ValidationError mentioning 'data_unavailable' AND 'consensus_score'.
    - test_data_unavailable_invariant_violation_confidence: PositionSignal(..., data_unavailable=True, confidence=80) → ValidationError mentioning 'data_unavailable' AND 'confidence'.
    - test_data_unavailable_invariant_violation_action_hint: PositionSignal(..., data_unavailable=True, action_hint="consider_add") → ValidationError mentioning 'data_unavailable' AND 'action_hint'.
    - test_data_unavailable_invariant_violation_trend_regime: PositionSignal(..., data_unavailable=True, trend_regime=True) → ValidationError mentioning 'data_unavailable' AND 'trend_regime'.

    JSON ROUND-TRIP:
    - test_json_round_trip: build a non-trivial PositionSignal (state="overbought", consensus_score=0.45, confidence=67, action_hint="consider_trim", indicators={"rsi_14": 72.1, "stoch_k": 85.0, "adx_14": 27.5}, evidence=["RSI(14) 72.1 — overbought", "Stochastic %K 85 — overbought"], trend_regime=True). Round-trip via PositionSignal.model_validate_json(s.model_dump_json()) → equal object.

    INDEPENDENCE FROM AGENTSIGNAL:
    - test_position_signal_not_subclass_of_agent_signal:
        ```python
        from analysts.signals import AgentSignal
        from analysts.position_signal import PositionSignal
        assert not issubclass(PositionSignal, AgentSignal)
        ```
      Locks the PEER-not-subtype contract from 04-RESEARCH.md Pattern #7.

    Total: ~22-25 tests ≥ the ≥12 minimum.

    Implementation per implementation_sketch above — NO deviations. The model_validator must produce error messages including BOTH the field name and its actual value (for debuggability), with the literal substring "data_unavailable=True invariant violated" so the violation tests can grep on it.
  </behavior>
  <action>
    RED:
    1. Write `tests/analysts/test_position_signal.py` with the ≥12 tests above. Imports:
       ```python
       import json
       import pytest
       from datetime import datetime, timezone
       from pydantic import ValidationError
       from analysts.position_signal import PositionSignal, PositionState, ActionHint
       ```
       Use the `frozen_now` fixture from `tests/analysts/conftest.py` (already shipped Phase 3 / 03-01).
    2. Run `poetry run pytest tests/analysts/test_position_signal.py -x -q` → ImportError on `analysts.position_signal` (module does not exist).
    3. Commit (RED): `test(04-02): add failing tests for PositionSignal schema (5-state ladder, action_hint, data_unavailable invariant, JSON round-trip)`

    GREEN:
    4. Implement `analysts/position_signal.py` per the implementation_sketch verbatim:
       - Module docstring (~25 lines) explaining PEER-not-subtype and the validator-duplication acceptance.
       - Imports as specified.
       - `PositionState` Literal type at module level.
       - `ActionHint` Literal type at module level.
       - `PositionSignal(BaseModel)` class with `model_config = ConfigDict(extra="forbid")` and 10 fields.
       - `@field_validator("ticker", mode="before")` delegating to `normalize_ticker` (mirror analysts/signals.py exactly — same control flow).
       - `@field_validator("evidence")` walking the list, raising ValueError on any string > 200 chars (Pydantic Field(max_length=10) handles count separately).
       - `@model_validator(mode="after")` enforcing the 5-field invariant. Error message includes ALL violated fields' actual values for debuggability AND the literal substring "data_unavailable=True invariant violated" for grep-ability.
    5. Run `poetry run pytest tests/analysts/test_position_signal.py -v` → all ≥12 tests green.
    6. Coverage check: `poetry run pytest --cov=analysts.position_signal --cov-branch tests/analysts/test_position_signal.py` → ≥90% line / ≥85% branch on `analysts/position_signal.py`.
    7. Phase 3 + Phase 4-Wave-0 regression: `poetry run pytest tests/analysts/ -v` → all existing tests still GREEN (the new module is additive only — doesn't import from or modify any Phase 3 file).
    8. Full repo regression: `poetry run pytest -x -q` → all green (Phase 1 + Phase 2 + Phase 3 + Wave 0 + new schema tests).
    9. Sanity import check: `poetry run python -c "from analysts.position_signal import PositionSignal, PositionState, ActionHint; from analysts.signals import AgentSignal; assert not issubclass(PositionSignal, AgentSignal); s = PositionSignal(ticker='aapl', computed_at=__import__('datetime').datetime(2026,5,1,tzinfo=__import__('datetime').timezone.utc)); assert s.ticker == 'AAPL'; assert s.state == 'fair'; assert s.action_hint == 'hold_position'; print('OK')"`.
    10. Commit (GREEN): `feat(04-02): PositionSignal Pydantic schema with 5-state state ladder + 4-state action_hint + data_unavailable invariant`
  </action>
  <verify>
    <automated>poetry run pytest tests/analysts/test_position_signal.py -v && poetry run pytest --cov=analysts.position_signal --cov-branch tests/analysts/test_position_signal.py && poetry run pytest tests/analysts/ -v && poetry run pytest -x -q && poetry run python -c "from analysts.position_signal import PositionSignal, PositionState, ActionHint; from analysts.signals import AgentSignal; assert not issubclass(PositionSignal, AgentSignal); print('peer-not-subtype OK')"</automated>
  </verify>
  <done>analysts/position_signal.py shipped (~80-100 LOC) with PositionSignal + PositionState + ActionHint + 3 validators (ticker normalization, evidence per-string cap, data_unavailable invariant); ≥12 tests in tests/analysts/test_position_signal.py all GREEN; coverage ≥90% line / ≥85% branch on the new module; PEER-not-subtype contract verified; full repo regression GREEN; both commits (RED + GREEN) landed.</done>
</task>

</tasks>

<verification>
- 1 task, 2 commits (RED + GREEN). TDD discipline preserved.
- Coverage gate: ≥90% line / ≥85% branch on `analysts/position_signal.py`.
- Full repo regression after each commit: existing test count + ≥12 new schema tests = all green.
- PositionSignal schema enforces every invariant locked in 04-CONTEXT.md, including the @model_validator from 04-RESEARCH.md Pitfall #1 (data_unavailable=True ⟹ all 5 fields at canonical no-opinion values).
- PositionState Literal exactly 5 values; ActionHint Literal exactly 4 values; both verified by parametrized tests.
- Ticker normalization delegates to `analysts.schemas.normalize_ticker` — same single-source-of-truth pattern as AgentSignal and PriceSnapshot.
- Evidence cap: Field(max_length=10) for count + custom @field_validator for per-string ≤200 chars.
- consensus_score: Field(ge=-1.0, le=1.0); confidence: Field(ge=0, le=100, int).
- ConfigDict(extra="forbid"); JSON round-trip works (datetime ISO-8601 default Pydantic v2 serialization).
- PEER-not-subtype: `not issubclass(PositionSignal, AgentSignal)` — locked by test.
- Wave 2 (04-03) unblocked: imports `PositionSignal`, `PositionState`, `ActionHint` from this plan's `analysts/position_signal.py`.

## Cross-Scope Risks

_vault_status=budget_exhausted; re-run /gmd:plan-phase --replan after vault-maintain_
</verification>

<success_criteria>
1. `analysts/position_signal.py` exports `PositionSignal`, `PositionState`, `ActionHint`.
2. PositionSignal has all 10 fields per the locked CONTEXT.md schema (ticker, computed_at, state, consensus_score, confidence, action_hint, indicators, evidence, data_unavailable, trend_regime).
3. All defaults match the canonical no-opinion shape (state='fair', consensus_score=0.0, confidence=0, action_hint='hold_position', indicators={}, evidence=[], data_unavailable=False, trend_regime=False).
4. ConfigDict(extra='forbid') discipline; @field_validator('ticker', mode='before') delegates to normalize_ticker; @field_validator('evidence') enforces ≤200-char per-string cap; @model_validator(mode='after') enforces the 5-field data_unavailable invariant.
5. ≥12 tests in `tests/analysts/test_position_signal.py`, all GREEN; coverage ≥90% line / ≥85% branch on `analysts/position_signal.py`.
6. PEER-not-subtype contract verified via `not issubclass(PositionSignal, AgentSignal)` test.
7. JSON round-trip works (model_dump_json → model_validate_json yields equal object).
8. Full repo regression green (Phase 1 + Phase 2 + Phase 3 + 04-01 Wave 0 + this plan).
9. Wave 2 (Plan 04-03 Position-Adjustment Radar analyst) unblocked — can now import `PositionSignal`, `PositionState`, `ActionHint` from `analysts.position_signal`.
</success_criteria>

<output>
After completion, create `.planning/phases/04-position-adjustment-radar/04-02-SUMMARY.md` summarizing the 2 commits, naming the PositionSignal contract (10 fields + 3 validators + the data_unavailable invariant), and forward-flagging Wave 2 (04-03) as the consumer.

Update `.planning/STATE.md` Recent Decisions with a 04-02 entry naming: PositionSignal schema locked at `analysts/position_signal.py` (PEER of AgentSignal, NOT subtype); data_unavailable invariant enforced at the schema layer via @model_validator (closes 04-RESEARCH.md Pitfall #1); 5-state PositionState ladder + 4-state ActionHint Literal types exported; Wave 2 (04-03 Position-Adjustment analyst) unblocked.
</output>
