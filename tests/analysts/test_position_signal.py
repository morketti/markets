"""Tests for analysts/position_signal.py — PositionSignal Pydantic schema.

Coverage map (per 04-02-position-signal-PLAN.md):
  * Shape / defaults — minimum-valid signal + extra-field rejection
  * Ticker normalization — delegates to analysts.schemas.normalize_ticker
  * Literal type coverage — 5 PositionState values + 4 ActionHint values
  * Range constraints — consensus_score ∈ [-1, +1], confidence ∈ [0, 100]
  * Evidence caps — count (≤10) + per-string (≤200 chars)
  * Indicators dict — accepts None values + float values
  * data_unavailable invariant — clean path + 5 violation cases
  * JSON round-trip — model_dump_json ↔ model_validate_json
  * PEER-not-subtype contract — `not issubclass(PositionSignal, AgentSignal)`
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from analysts.position_signal import ActionHint, PositionSignal, PositionState
from analysts.signals import AgentSignal


FROZEN = datetime(2026, 5, 1, 13, 30, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Shape / defaults
# ---------------------------------------------------------------------------


def test_minimum_valid_signal() -> None:
    """PositionSignal with only required fields uses canonical no-opinion defaults."""
    sig = PositionSignal(ticker="AAPL", computed_at=FROZEN)
    assert sig.ticker == "AAPL"
    assert sig.state == "fair"
    assert sig.consensus_score == 0.0
    assert sig.confidence == 0
    assert sig.action_hint == "hold_position"
    assert sig.indicators == {}
    assert sig.evidence == []
    assert sig.data_unavailable is False
    assert sig.trend_regime is False


def test_extra_field_forbidden() -> None:
    """ConfigDict(extra='forbid') rejects unknown fields."""
    with pytest.raises(ValidationError) as exc_info:
        PositionSignal(ticker="AAPL", computed_at=FROZEN, metadata={"x": 1})
    assert "metadata" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Ticker normalization
# ---------------------------------------------------------------------------


def test_ticker_normalization() -> None:
    """ticker='brk.b' → normalized to 'BRK-B' via analysts.schemas.normalize_ticker."""
    sig = PositionSignal(ticker="brk.b", computed_at=FROZEN)
    assert sig.ticker == "BRK-B"


def test_ticker_invalid_raises() -> None:
    """Invalid ticker → ValidationError with 'ticker' in error loc."""
    with pytest.raises(ValidationError) as exc_info:
        PositionSignal(ticker="123!@#", computed_at=FROZEN)
    assert "ticker" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Literal coverage
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "state,score",
    [
        ("extreme_oversold", -0.8),
        ("oversold", -0.4),
        ("fair", 0.0),
        ("overbought", 0.4),
        ("extreme_overbought", 0.8),
    ],
)
def test_position_state_5_values_accepted(state: str, score: float) -> None:
    """All 5 PositionState literal values construct cleanly when data_unavailable=False."""
    sig = PositionSignal(
        ticker="AAPL",
        computed_at=FROZEN,
        state=state,
        consensus_score=score,
    )
    assert sig.state == state


def test_position_state_unknown_rejected() -> None:
    """Unknown state value → ValidationError."""
    with pytest.raises(ValidationError):
        PositionSignal(ticker="AAPL", computed_at=FROZEN, state="moonshot")


@pytest.mark.parametrize(
    "hint",
    ["consider_add", "hold_position", "consider_trim", "consider_take_profits"],
)
def test_action_hint_4_values_accepted(hint: str) -> None:
    """All 4 ActionHint literal values construct cleanly."""
    sig = PositionSignal(ticker="AAPL", computed_at=FROZEN, action_hint=hint)
    assert sig.action_hint == hint


def test_action_hint_unknown_rejected() -> None:
    """Unknown action_hint value → ValidationError."""
    with pytest.raises(ValidationError):
        PositionSignal(ticker="AAPL", computed_at=FROZEN, action_hint="buy")


# ---------------------------------------------------------------------------
# Range constraints
# ---------------------------------------------------------------------------


def test_consensus_score_range_accepts_boundaries() -> None:
    """consensus_score=-1.0 and consensus_score=1.0 both construct cleanly."""
    PositionSignal(
        ticker="AAPL",
        computed_at=FROZEN,
        state="extreme_oversold",
        consensus_score=-1.0,
    )
    PositionSignal(
        ticker="AAPL",
        computed_at=FROZEN,
        state="extreme_overbought",
        consensus_score=1.0,
    )


def test_consensus_score_below_minus_one_rejected() -> None:
    with pytest.raises(ValidationError):
        PositionSignal(ticker="AAPL", computed_at=FROZEN, consensus_score=-1.01)


def test_consensus_score_above_plus_one_rejected() -> None:
    with pytest.raises(ValidationError):
        PositionSignal(ticker="AAPL", computed_at=FROZEN, consensus_score=1.01)


def test_confidence_range_accepts_boundaries() -> None:
    """confidence=0 and confidence=100 both construct cleanly."""
    PositionSignal(ticker="AAPL", computed_at=FROZEN, confidence=0)
    PositionSignal(ticker="AAPL", computed_at=FROZEN, confidence=100)


def test_confidence_negative_rejected() -> None:
    with pytest.raises(ValidationError):
        PositionSignal(ticker="AAPL", computed_at=FROZEN, confidence=-1)


def test_confidence_above_100_rejected() -> None:
    with pytest.raises(ValidationError):
        PositionSignal(ticker="AAPL", computed_at=FROZEN, confidence=101)


# ---------------------------------------------------------------------------
# Evidence caps
# ---------------------------------------------------------------------------


def test_evidence_max_items() -> None:
    """Field(max_length=10) rejects 11+ evidence items."""
    with pytest.raises(ValidationError):
        PositionSignal(ticker="AAPL", computed_at=FROZEN, evidence=["a"] * 11)


def test_evidence_string_too_long() -> None:
    """Per-string ≤200 chars enforced via custom @field_validator."""
    with pytest.raises(ValidationError):
        PositionSignal(ticker="AAPL", computed_at=FROZEN, evidence=["x" * 201])


def test_evidence_at_caps_accepted() -> None:
    """10 items, each exactly 200 chars — at the boundary, accepted."""
    sig = PositionSignal(
        ticker="AAPL",
        computed_at=FROZEN,
        evidence=["x" * 200] * 10,
    )
    assert len(sig.evidence) == 10


def test_evidence_empty_list_ok() -> None:
    sig = PositionSignal(ticker="AAPL", computed_at=FROZEN, evidence=[])
    assert sig.evidence == []


# ---------------------------------------------------------------------------
# Indicators dict
# ---------------------------------------------------------------------------


def test_indicators_dict_with_none_values() -> None:
    """All-None indicators dict (warm-up case) constructs cleanly."""
    sig = PositionSignal(
        ticker="AAPL",
        computed_at=FROZEN,
        indicators={
            "rsi_14": None,
            "bb_position": None,
            "zscore_50": None,
            "stoch_k": None,
            "williams_r": None,
            "macd_histogram": None,
            "adx_14": None,
        },
    )
    assert sig.indicators["rsi_14"] is None
    assert len(sig.indicators) == 7


def test_indicators_dict_with_floats() -> None:
    sig = PositionSignal(
        ticker="AAPL",
        computed_at=FROZEN,
        indicators={"rsi_14": 28.4, "stoch_k": 18.5},
    )
    assert sig.indicators["rsi_14"] == 28.4


# ---------------------------------------------------------------------------
# data_unavailable invariant
# ---------------------------------------------------------------------------


def test_data_unavailable_clean_path() -> None:
    """data_unavailable=True with all canonical defaults — VALID."""
    sig = PositionSignal(
        ticker="AAPL",
        computed_at=FROZEN,
        data_unavailable=True,
        evidence=["snapshot data_unavailable=True"],
    )
    assert sig.data_unavailable is True
    assert sig.state == "fair"
    assert sig.consensus_score == 0.0
    assert sig.confidence == 0
    assert sig.action_hint == "hold_position"
    assert sig.trend_regime is False
    assert sig.evidence == ["snapshot data_unavailable=True"]


def test_data_unavailable_invariant_violation_state() -> None:
    with pytest.raises(ValidationError) as exc_info:
        PositionSignal(
            ticker="AAPL",
            computed_at=FROZEN,
            data_unavailable=True,
            state="oversold",
        )
    msg = str(exc_info.value)
    assert "data_unavailable" in msg
    assert "state" in msg


def test_data_unavailable_invariant_violation_consensus_score() -> None:
    with pytest.raises(ValidationError) as exc_info:
        PositionSignal(
            ticker="AAPL",
            computed_at=FROZEN,
            data_unavailable=True,
            consensus_score=-0.5,
        )
    msg = str(exc_info.value)
    assert "data_unavailable" in msg
    assert "consensus_score" in msg


def test_data_unavailable_invariant_violation_confidence() -> None:
    with pytest.raises(ValidationError) as exc_info:
        PositionSignal(
            ticker="AAPL",
            computed_at=FROZEN,
            data_unavailable=True,
            confidence=80,
        )
    msg = str(exc_info.value)
    assert "data_unavailable" in msg
    assert "confidence" in msg


def test_data_unavailable_invariant_violation_action_hint() -> None:
    with pytest.raises(ValidationError) as exc_info:
        PositionSignal(
            ticker="AAPL",
            computed_at=FROZEN,
            data_unavailable=True,
            action_hint="consider_add",
        )
    msg = str(exc_info.value)
    assert "data_unavailable" in msg
    assert "action_hint" in msg


def test_data_unavailable_invariant_violation_trend_regime() -> None:
    with pytest.raises(ValidationError) as exc_info:
        PositionSignal(
            ticker="AAPL",
            computed_at=FROZEN,
            data_unavailable=True,
            trend_regime=True,
        )
    msg = str(exc_info.value)
    assert "data_unavailable" in msg
    assert "trend_regime" in msg


# ---------------------------------------------------------------------------
# JSON round-trip
# ---------------------------------------------------------------------------


def test_json_round_trip() -> None:
    """model_dump_json → model_validate_json yields equal object."""
    sig = PositionSignal(
        ticker="AAPL",
        computed_at=FROZEN,
        state="overbought",
        consensus_score=0.45,
        confidence=67,
        action_hint="consider_trim",
        indicators={"rsi_14": 72.1, "stoch_k": 85.0, "adx_14": 27.5},
        evidence=["RSI(14) 72.1 — overbought", "Stochastic %K 85 — overbought"],
        trend_regime=True,
    )
    serialized = sig.model_dump_json()
    rehydrated = PositionSignal.model_validate_json(serialized)
    assert sig == rehydrated


# ---------------------------------------------------------------------------
# PEER-not-subtype contract
# ---------------------------------------------------------------------------


def test_position_signal_not_subclass_of_agent_signal() -> None:
    """PEER of AgentSignal, NOT subtype (locks 04-RESEARCH.md Pattern #7)."""
    assert not issubclass(PositionSignal, AgentSignal)
    assert not issubclass(AgentSignal, PositionSignal)
