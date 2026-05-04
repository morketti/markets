"""Tests for synthesis/decision.py — Phase 5 / Wave 1 / LLM-06.

Locked schema per .planning/phases/05-claude-routine-wiring/05-CONTEXT.md
TickerDecision section + 05-RESEARCH.md Open Question #3 (the @model_validator
enforcing the data_unavailable=True ⟹ recommendation='hold' AND conviction='low'
invariant).

Test structure mirrors tests/analysts/test_position_signal.py:
  * SHAPE / DEFAULTS — minimum-valid construction + extra-field rejection +
    schema_version forward-compat.
  * TICKER NORMALIZATION — round-trip via analysts.schemas.normalize_ticker.
  * ENUM COVERAGE — parametrized over the 6 DecisionRecommendation + 3
    ConvictionBand + 2 Timeframe Literal values; rejection of unknown values.
  * TIMEFRAMEBAND — length / count / range caps on summary, drivers,
    confidence; extra-field rejection.
  * DISSENT SECTION — defaults + populated + length cap + extra-field
    rejection.
  * OPEN OBSERVATION — length cap + default-empty.
  * DATA_UNAVAILABLE INVARIANT — clean path + 3 violation flavours
    (recommendation, conviction, both at once).
  * JSON ROUND-TRIP — minimal + fully populated.
  * INDEPENDENCE — TickerDecision is NOT a subclass of AgentSignal or
    PositionSignal (PEER-not-subtype contract).

frozen_now fixture comes from tests/conftest.py (root-level).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import get_args

import pytest
from pydantic import ValidationError

from synthesis.decision import (
    ConvictionBand,
    DecisionRecommendation,
    DissentSection,
    TickerDecision,
    Timeframe,
    TimeframeBand,
)


# ---------------------------------------------------------------------------
# Helpers — small builder closures so each test only spells out the field(s)
# it cares about; mirrors the make_ticker_config / make_snapshot pattern from
# tests/analysts/conftest.py without promoting these to pytest fixtures (the
# tests are simple enough that local module-level helpers stay clearer).
# ---------------------------------------------------------------------------


def _band(summary: str = "ok", drivers: list[str] | None = None, confidence: int = 50) -> TimeframeBand:
    return TimeframeBand(
        summary=summary,
        drivers=drivers if drivers is not None else [],
        confidence=confidence,
    )


def _decision(frozen_now: datetime, **overrides) -> TickerDecision:
    """Build a minimal-valid TickerDecision with sensible defaults."""
    kwargs: dict = {
        "ticker": "AAPL",
        "computed_at": frozen_now,
        "recommendation": "hold",
        "conviction": "medium",
        "short_term": _band(summary="short ok"),
        "long_term": _band(summary="long ok"),
        "dissent": DissentSection(),
    }
    kwargs.update(overrides)
    return TickerDecision(**kwargs)


# ---------------------------------------------------------------------------
# SHAPE / DEFAULTS
# ---------------------------------------------------------------------------


def test_minimum_valid_ticker_decision(frozen_now: datetime) -> None:
    """Build a complete valid TickerDecision; verify every default + assigned field.

    Phase 6 / Plan 06-01: schema_version default bumped 1→2.
    """
    d = _decision(
        frozen_now,
        recommendation="hold",
        conviction="medium",
        short_term=_band(summary="short side ok", drivers=["d1"], confidence=55),
        long_term=_band(summary="long side ok", drivers=[], confidence=40),
        dissent=DissentSection(),
    )
    assert d.ticker == "AAPL"
    assert d.computed_at == frozen_now
    assert d.schema_version == 2
    assert d.recommendation == "hold"
    assert d.conviction == "medium"
    assert d.short_term.summary == "short side ok"
    assert d.short_term.drivers == ["d1"]
    assert d.short_term.confidence == 55
    assert d.long_term.summary == "long side ok"
    assert d.long_term.confidence == 40
    assert d.open_observation == ""
    assert d.dissent.has_dissent is False
    assert d.data_unavailable is False


def test_extra_field_forbidden(frozen_now: datetime) -> None:
    with pytest.raises(ValidationError) as excinfo:
        _decision(frozen_now, metadata={"x": 1})
    assert "metadata" in str(excinfo.value)


def test_schema_version_default_bumped_to_2(frozen_now: datetime) -> None:
    """Phase 6 / Plan 06-01: TickerDecision.schema_version default = 2.

    Bumped from 1 → 2 because Wave 0 amendment adds new fields
    (TimeframeBand.thesis_status, plus per-ticker JSON gains
    ohlc_history/indicators/headlines). The frontend zod schemas (Wave 1)
    will assert schema_version == 2; v1 snapshots become invalid by design
    (forces a Phase 5 re-run before frontend renders).
    """
    d = _decision(frozen_now)
    assert d.schema_version == 2


def test_schema_version_forward_compat(frozen_now: datetime) -> None:
    """schema_version=3 is accepted (forward compat hook for Phase 9 + v1.x)."""
    d = _decision(frozen_now, schema_version=3)
    assert d.schema_version == 3


# ---------------------------------------------------------------------------
# TICKER NORMALIZATION
# ---------------------------------------------------------------------------


def test_ticker_normalization(frozen_now: datetime) -> None:
    d = _decision(frozen_now, ticker="brk.b")
    assert d.ticker == "BRK-B"


def test_ticker_invalid_raises(frozen_now: datetime) -> None:
    with pytest.raises(ValidationError) as excinfo:
        _decision(frozen_now, ticker="123!@#")
    assert "ticker" in str(excinfo.value).lower()


# ---------------------------------------------------------------------------
# ENUM COVERAGE
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rec",
    ["add", "trim", "hold", "take_profits", "buy", "avoid"],
)
def test_recommendation_6_values_accepted(frozen_now: datetime, rec: str) -> None:
    """All 6 DecisionRecommendation values construct cleanly with conviction='medium'."""
    d = _decision(frozen_now, recommendation=rec, conviction="medium")
    assert d.recommendation == rec


def test_recommendation_unknown_rejected(frozen_now: datetime) -> None:
    with pytest.raises(ValidationError) as excinfo:
        _decision(frozen_now, recommendation="strong_buy")
    assert "recommendation" in str(excinfo.value).lower()


@pytest.mark.parametrize("conv", ["low", "medium", "high"])
def test_conviction_3_values_accepted(frozen_now: datetime, conv: str) -> None:
    d = _decision(frozen_now, conviction=conv)
    assert d.conviction == conv


def test_conviction_unknown_rejected(frozen_now: datetime) -> None:
    with pytest.raises(ValidationError) as excinfo:
        _decision(frozen_now, conviction="very_high")
    assert "conviction" in str(excinfo.value).lower()


def test_decision_recommendation_literal_arity_and_order() -> None:
    assert get_args(DecisionRecommendation) == (
        "add",
        "trim",
        "hold",
        "take_profits",
        "buy",
        "avoid",
    )


def test_conviction_band_literal_arity_and_order() -> None:
    assert get_args(ConvictionBand) == ("low", "medium", "high")


def test_timeframe_literal_2_values() -> None:
    assert get_args(Timeframe) == ("short_term", "long_term")


# ---------------------------------------------------------------------------
# TIMEFRAMEBAND
# ---------------------------------------------------------------------------


def test_timeframe_band_summary_min_length_1() -> None:
    with pytest.raises(ValidationError) as excinfo:
        TimeframeBand(summary="", drivers=[], confidence=50)
    assert "summary" in str(excinfo.value).lower()


def test_timeframe_band_summary_max_500() -> None:
    with pytest.raises(ValidationError):
        TimeframeBand(summary="x" * 501, drivers=[], confidence=50)


def test_timeframe_band_summary_at_500_accepted() -> None:
    band = TimeframeBand(summary="x" * 500, drivers=[], confidence=50)
    assert len(band.summary) == 500


def test_timeframe_band_drivers_count_cap() -> None:
    with pytest.raises(ValidationError):
        TimeframeBand(summary="ok", drivers=["a"] * 11, confidence=50)


def test_timeframe_band_drivers_per_string_cap() -> None:
    with pytest.raises(ValidationError) as excinfo:
        TimeframeBand(summary="ok", drivers=["x" * 201], confidence=50)
    assert "driver string exceeds 200 chars" in str(excinfo.value)


def test_timeframe_band_drivers_at_caps_accepted() -> None:
    """10 items, each exactly 200 chars — both caps are inclusive at the boundary."""
    band = TimeframeBand(summary="ok", drivers=["x" * 200] * 10, confidence=50)
    assert len(band.drivers) == 10
    assert all(len(d) == 200 for d in band.drivers)


def test_timeframe_band_confidence_negative_rejected() -> None:
    with pytest.raises(ValidationError):
        TimeframeBand(summary="ok", drivers=[], confidence=-1)


def test_timeframe_band_confidence_above_100_rejected() -> None:
    with pytest.raises(ValidationError):
        TimeframeBand(summary="ok", drivers=[], confidence=101)


def test_timeframe_band_confidence_boundaries() -> None:
    low = TimeframeBand(summary="ok", drivers=[], confidence=0)
    high = TimeframeBand(summary="ok", drivers=[], confidence=100)
    assert low.confidence == 0
    assert high.confidence == 100


def test_timeframe_band_extra_field_forbidden() -> None:
    with pytest.raises(ValidationError):
        TimeframeBand(summary="ok", drivers=[], confidence=50, foo="bar")


# ---------------------------------------------------------------------------
# DISSENT SECTION
# ---------------------------------------------------------------------------


def test_dissent_section_defaults() -> None:
    d = DissentSection()
    assert d.has_dissent is False
    assert d.dissenting_persona is None
    assert d.dissent_summary == ""


def test_dissent_section_populated() -> None:
    d = DissentSection(
        has_dissent=True,
        dissenting_persona="burry",
        dissent_summary="burry dissents (bearish, conf=45): hidden risk in margin compression",
    )
    assert d.has_dissent is True
    assert d.dissenting_persona == "burry"
    assert "margin compression" in d.dissent_summary


def test_dissent_section_summary_max_500() -> None:
    with pytest.raises(ValidationError):
        DissentSection(dissent_summary="x" * 501)


def test_dissent_section_extra_field_forbidden() -> None:
    with pytest.raises(ValidationError):
        DissentSection(foo="bar")


# ---------------------------------------------------------------------------
# OPEN OBSERVATION
# ---------------------------------------------------------------------------


def test_open_observation_max_500(frozen_now: datetime) -> None:
    with pytest.raises(ValidationError):
        _decision(frozen_now, open_observation="x" * 501)


def test_open_observation_default_empty(frozen_now: datetime) -> None:
    d = _decision(frozen_now)
    assert d.open_observation == ""


def test_open_observation_at_500_accepted(frozen_now: datetime) -> None:
    d = _decision(frozen_now, open_observation="x" * 500)
    assert len(d.open_observation) == 500


# ---------------------------------------------------------------------------
# DATA_UNAVAILABLE INVARIANT
# ---------------------------------------------------------------------------


def test_data_unavailable_clean_path(frozen_now: datetime) -> None:
    """data_unavailable=True with the canonical safe-defaults shape — VALID."""
    d = TickerDecision(
        ticker="AAPL",
        computed_at=frozen_now,
        data_unavailable=True,
        recommendation="hold",
        conviction="low",
        short_term=TimeframeBand(
            summary="data unavailable: snapshot missing",
            drivers=[],
            confidence=0,
        ),
        long_term=TimeframeBand(
            summary="data unavailable: snapshot missing",
            drivers=[],
            confidence=0,
        ),
        dissent=DissentSection(),
        open_observation="snapshot data_unavailable=True",
    )
    assert d.data_unavailable is True
    assert d.recommendation == "hold"
    assert d.conviction == "low"


def test_data_unavailable_invariant_violation_recommendation(
    frozen_now: datetime,
) -> None:
    with pytest.raises(ValidationError) as excinfo:
        TickerDecision(
            ticker="AAPL",
            computed_at=frozen_now,
            data_unavailable=True,
            recommendation="buy",
            conviction="low",
            short_term=_band(summary="x"),
            long_term=_band(summary="y"),
            dissent=DissentSection(),
        )
    msg = str(excinfo.value)
    assert "data_unavailable=True invariant violated" in msg
    assert "recommendation" in msg


def test_data_unavailable_invariant_violation_conviction(
    frozen_now: datetime,
) -> None:
    with pytest.raises(ValidationError) as excinfo:
        TickerDecision(
            ticker="AAPL",
            computed_at=frozen_now,
            data_unavailable=True,
            recommendation="hold",
            conviction="high",
            short_term=_band(summary="x"),
            long_term=_band(summary="y"),
            dissent=DissentSection(),
        )
    msg = str(excinfo.value)
    assert "data_unavailable=True invariant violated" in msg
    assert "conviction" in msg


def test_data_unavailable_invariant_violation_both(frozen_now: datetime) -> None:
    """Both recommendation AND conviction wrong — single ValueError lists both."""
    with pytest.raises(ValidationError) as excinfo:
        TickerDecision(
            ticker="AAPL",
            computed_at=frozen_now,
            data_unavailable=True,
            recommendation="buy",
            conviction="high",
            short_term=_band(summary="x"),
            long_term=_band(summary="y"),
            dissent=DissentSection(),
        )
    msg = str(excinfo.value)
    assert "data_unavailable=True invariant violated" in msg
    assert "recommendation" in msg
    assert "conviction" in msg


# ---------------------------------------------------------------------------
# JSON ROUND-TRIP
# ---------------------------------------------------------------------------


def test_json_round_trip_minimal(frozen_now: datetime) -> None:
    d = _decision(frozen_now)
    raw = d.model_dump_json()
    parsed = TickerDecision.model_validate_json(raw)
    assert parsed == d
    # The serialized form should be valid JSON with the expected ticker.
    payload = json.loads(raw)
    assert payload["ticker"] == "AAPL"
    # Phase 6 / Plan 06-01: schema_version default bumped 1→2.
    assert payload["schema_version"] == 2


def test_json_round_trip_full(frozen_now: datetime) -> None:
    d = TickerDecision(
        ticker="MSFT",
        computed_at=frozen_now,
        schema_version=2,
        recommendation="add",
        conviction="high",
        short_term=TimeframeBand(
            summary="bullish into earnings",
            drivers=["azure growth", "EPS beats"],
            confidence=78,
        ),
        long_term=TimeframeBand(
            summary="durable moat in cloud + productivity",
            drivers=["AI tailwind", "moat widening"],
            confidence=82,
        ),
        open_observation="cross-checked vs valuation: thesis intact",
        dissent=DissentSection(
            has_dissent=True,
            dissenting_persona="burry",
            dissent_summary="margin compression risk in non-Azure segments",
        ),
        data_unavailable=False,
    )
    raw = d.model_dump_json()
    parsed = TickerDecision.model_validate_json(raw)
    assert parsed == d
    # datetime ISO-8601 is preserved through round-trip:
    assert parsed.computed_at == frozen_now
    assert parsed.computed_at.tzinfo is not None
    # nested sub-models survive cleanly:
    assert parsed.dissent.dissenting_persona == "burry"
    assert parsed.short_term.drivers == ["azure growth", "EPS beats"]


# ---------------------------------------------------------------------------
# INDEPENDENCE — PEER-not-subtype contract
# ---------------------------------------------------------------------------


def test_ticker_decision_not_subclass_of_other_signals() -> None:
    """TickerDecision and its peer models are NOT subtypes of AgentSignal / PositionSignal.

    Locks the PEER contract: synthesis/decision.py is its own schema family.
    Phase 5 synthesizer reads a list of mixed-types (4 analytical AgentSignals +
    PositionSignal + 6 persona AgentSignals) and produces a TickerDecision —
    none of these inherit from the others.
    """
    from analysts.position_signal import PositionSignal
    from analysts.signals import AgentSignal

    assert not issubclass(TickerDecision, AgentSignal)
    assert not issubclass(TickerDecision, PositionSignal)
    assert not issubclass(TimeframeBand, AgentSignal)
    assert not issubclass(TimeframeBand, PositionSignal)
    assert not issubclass(DissentSection, AgentSignal)
    assert not issubclass(DissentSection, PositionSignal)


# ---------------------------------------------------------------------------
# UTC datetime preservation through round-trip — sanity-check that the
# Pydantic v2 default datetime serialization keeps tzinfo (matches the
# Phase 3 + Phase 4 schema discipline).
# ---------------------------------------------------------------------------


def test_computed_at_round_trip_preserves_utc(frozen_now: datetime) -> None:
    d = _decision(frozen_now)
    raw = d.model_dump_json()
    parsed = TickerDecision.model_validate_json(raw)
    assert parsed.computed_at == frozen_now
    assert parsed.computed_at.tzinfo is not None
    assert parsed.computed_at.utcoffset() == timezone.utc.utcoffset(None)


# ---------------------------------------------------------------------------
# Phase 6 / Plan 06-01: ThesisStatus + TimeframeBand.thesis_status
#
# `ThesisStatus = Literal["intact", "weakening", "broken", "improving", "n/a"]`
# is the new field added to TimeframeBand. Default is "n/a" so existing
# snapshots and lite-mode TimeframeBands deserialize without ValidationError.
# The synthesizer (prompts/synthesizer.md) populates this per timeframe so the
# frontend Long-Term Thesis Status lens (VIEW-04) can filter+sort by it.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value", ["intact", "weakening", "broken", "improving", "n/a"]
)
def test_thesis_status_literal_accepts_5_values(value: str) -> None:
    """ThesisStatus accepts exactly 5 enum values."""
    band = TimeframeBand(summary="ok", drivers=[], confidence=50, thesis_status=value)
    assert band.thesis_status == value


def test_thesis_status_rejects_invalid() -> None:
    """ThesisStatus rejects any non-enum value with 'thesis_status' in the validation error."""
    with pytest.raises(ValidationError) as excinfo:
        TimeframeBand(
            summary="ok", drivers=[], confidence=50, thesis_status="garbage"
        )
    assert "thesis_status" in str(excinfo.value).lower()


def test_thesis_status_default_is_na() -> None:
    """TimeframeBand without explicit thesis_status defaults to 'n/a'.

    Default 'n/a' is what makes the field addition non-breaking for every
    existing TickerDecision deserialization (Phase 5 snapshots have no
    thesis_status field; reading them with the new schema must not fail).
    """
    band = TimeframeBand(summary="ok", drivers=[], confidence=50)
    assert band.thesis_status == "n/a"


def test_timeframe_band_thesis_status_field_exists() -> None:
    """TimeframeBand has a 'thesis_status' model field (introspectable for zod codegen)."""
    assert "thesis_status" in TimeframeBand.model_fields


def test_thesis_status_literal_arity_and_order() -> None:
    """ThesisStatus exposes the 5 canonical values in the locked order."""
    from synthesis.decision import ThesisStatus

    assert get_args(ThesisStatus) == (
        "intact",
        "weakening",
        "broken",
        "improving",
        "n/a",
    )
