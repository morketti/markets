"""Tests for the AgentSignal schema (Plan 03-01).

Locked schema per 03-CONTEXT.md (5-state Verdict, 0..100 confidence,
evidence list ≤10 items each ≤200 chars, ConfigDict(extra='forbid'),
ticker normalization via analysts.schemas.normalize_ticker, plus the
@model_validator invariant from 03-RESEARCH.md Pitfall #4 enforcing
data_unavailable=True ⟹ verdict='neutral' AND confidence=0).

Test count: 17 (one over the planned ≥16). Coverage gate: ≥90% line /
≥85% branch on analysts/signals.py.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from analysts.signals import AgentSignal, AnalystId, Verdict


@pytest.fixture
def base_kwargs(frozen_now: datetime) -> dict:
    """Minimum-valid kwargs for AgentSignal construction. Override in each test."""
    return {
        "ticker": "AAPL",
        "analyst_id": "fundamentals",
        "computed_at": frozen_now,
    }


def test_signal_minimum_valid(base_kwargs: dict) -> None:
    """Constructing with only the three required fields applies all four defaults."""
    sig = AgentSignal(**base_kwargs)
    assert sig.ticker == "AAPL"
    assert sig.analyst_id == "fundamentals"
    assert sig.verdict == "neutral"
    assert sig.confidence == 0
    assert sig.evidence == []
    assert sig.data_unavailable is False


def test_ticker_normalization(base_kwargs: dict) -> None:
    """Lowercase + dot-form ticker should normalize to canonical hyphen form."""
    base_kwargs["ticker"] = "brk.b"
    sig = AgentSignal(**base_kwargs)
    assert sig.ticker == "BRK-B"


def test_ticker_invalid_raises(base_kwargs: dict) -> None:
    """Garbage ticker → ValidationError with 'ticker' in the loc path."""
    base_kwargs["ticker"] = "123!@#"
    with pytest.raises(ValidationError) as exc_info:
        AgentSignal(**base_kwargs)
    locs = [err["loc"] for err in exc_info.value.errors()]
    assert ("ticker",) in locs, f"expected ('ticker',) in errors, got {locs}"


def test_verdict_literal_rejects_unknown(base_kwargs: dict) -> None:
    """Verdict must be one of the 5 literal values; anything else rejected."""
    with pytest.raises(ValidationError):
        AgentSignal(**base_kwargs, verdict="moonshot")


@pytest.mark.parametrize(
    "verdict",
    ["strong_bullish", "bullish", "neutral", "bearish", "strong_bearish"],
)
def test_verdict_5_state_accepts_all(base_kwargs: dict, verdict: str) -> None:
    """All 5 ladder values must construct cleanly when data_unavailable=False."""
    sig = AgentSignal(**base_kwargs, verdict=verdict)
    assert sig.verdict == verdict


def test_confidence_range_lo(base_kwargs: dict) -> None:
    """confidence < 0 → ValidationError."""
    with pytest.raises(ValidationError):
        AgentSignal(**base_kwargs, confidence=-1)


def test_confidence_range_hi(base_kwargs: dict) -> None:
    """confidence > 100 → ValidationError."""
    with pytest.raises(ValidationError):
        AgentSignal(**base_kwargs, confidence=101)


def test_confidence_accepts_0_and_100(base_kwargs: dict) -> None:
    """Both endpoints (0 and 100) are inclusive."""
    sig0 = AgentSignal(**base_kwargs, confidence=0)
    assert sig0.confidence == 0
    sig100 = AgentSignal(**base_kwargs, confidence=100, verdict="strong_bullish")
    assert sig100.confidence == 100


def test_evidence_max_items(base_kwargs: dict) -> None:
    """evidence list with > 10 items → ValidationError."""
    with pytest.raises(ValidationError):
        AgentSignal(**base_kwargs, evidence=["x"] * 11)


def test_evidence_string_too_long(base_kwargs: dict) -> None:
    """A single evidence string > 200 chars → ValidationError."""
    with pytest.raises(ValidationError):
        AgentSignal(**base_kwargs, evidence=["x" * 201])


def test_evidence_empty_list_ok(base_kwargs: dict) -> None:
    """Empty evidence list is valid (it is the default)."""
    sig = AgentSignal(**base_kwargs, evidence=[])
    assert sig.evidence == []


def test_evidence_string_at_cap_ok(base_kwargs: dict) -> None:
    """Exactly 200-char string at the boundary is valid (≤, not <)."""
    sig = AgentSignal(**base_kwargs, evidence=["x" * 200])
    assert sig.evidence == ["x" * 200]


def test_extra_field_forbidden(base_kwargs: dict) -> None:
    """ConfigDict(extra='forbid') rejects unknown fields like 'metadata'."""
    with pytest.raises(ValidationError) as exc_info:
        AgentSignal(**base_kwargs, metadata={"x": 1})
    locs = [err["loc"] for err in exc_info.value.errors()]
    assert ("metadata",) in locs, f"expected ('metadata',) in errors, got {locs}"


def test_data_unavailable_invariant_violation_verdict(base_kwargs: dict) -> None:
    """data_unavailable=True with verdict='bullish' → ValidationError mentioning the invariant."""
    with pytest.raises(ValidationError) as exc_info:
        AgentSignal(**base_kwargs, data_unavailable=True, verdict="bullish")
    msg = str(exc_info.value).lower()
    assert "data_unavailable" in msg
    assert "verdict" in msg


def test_data_unavailable_invariant_violation_confidence(base_kwargs: dict) -> None:
    """data_unavailable=True with confidence=80 → ValidationError mentioning the invariant."""
    with pytest.raises(ValidationError) as exc_info:
        AgentSignal(**base_kwargs, data_unavailable=True, confidence=80)
    msg = str(exc_info.value).lower()
    assert "data_unavailable" in msg
    assert "confidence" in msg


def test_data_unavailable_clean_path(base_kwargs: dict) -> None:
    """data_unavailable=True with default verdict='neutral' + confidence=0 + an
    explanatory evidence string is the canonical 'dark snapshot' shape."""
    sig = AgentSignal(
        **base_kwargs,
        data_unavailable=True,
        evidence=["snapshot.fundamentals is None"],
    )
    assert sig.data_unavailable is True
    assert sig.verdict == "neutral"
    assert sig.confidence == 0
    assert sig.evidence == ["snapshot.fundamentals is None"]


def test_json_round_trip(base_kwargs: dict) -> None:
    """model_dump_json -> model_validate_json round-trip preserves equality.

    Verifies datetime ISO-8601 round-trip + extra='forbid' doesn't choke on
    its own JSON output (a common Pydantic v2 trap).
    """
    sig = AgentSignal(
        **base_kwargs,
        verdict="bullish",
        confidence=72,
        evidence=["P/E 18 vs target 22 — undervalued by 18%", "ROE 22% (well above 15% bullish band)"],
    )
    payload = sig.model_dump_json()
    sig2 = AgentSignal.model_validate_json(payload)
    assert sig == sig2


def test_byte_stable_serialization(base_kwargs: dict) -> None:
    """json.dumps(model_dump(mode='json'), sort_keys=True, indent=2) + '\\n' is
    byte-identical across two calls — the same pattern Plan 01-03's
    watchlist/loader.save_watchlist uses for stable git diffs.

    This is forward-compat scaffolding for Phase 5 snapshot writes that will
    embed AgentSignal alongside the per-ticker Snapshot.
    """
    sig = AgentSignal(
        **base_kwargs,
        verdict="bearish",
        confidence=45,
        evidence=["debt/equity 1.8 (above 1.5 bearish band)"],
    )
    payload_a = json.dumps(sig.model_dump(mode="json"), sort_keys=True, indent=2) + "\n"
    payload_b = json.dumps(sig.model_dump(mode="json"), sort_keys=True, indent=2) + "\n"
    assert payload_a == payload_b


def test_analyst_id_literal_rejects_unknown(base_kwargs: dict) -> None:
    """analyst_id must be one of the 4 literal values; everything else rejected.

    Tightening test added beyond the plan's ≥16 list — locks the AnalystId
    Literal at the schema layer (matches Verdict's coverage). Closes the
    branch where a typo'd id like 'fundamental' (singular) might otherwise
    silently land.
    """
    base_kwargs["analyst_id"] = "fundamental"  # typo'd — singular instead of plural
    with pytest.raises(ValidationError):
        AgentSignal(**base_kwargs)


def test_verdict_and_analyst_id_types_exposed() -> None:
    """The Verdict and AnalystId Literal types are part of the public surface
    of analysts.signals — every Wave 2 analyst module imports them."""
    # Smoke-import — confirms the names exist and survive future refactors.
    assert Verdict is not None
    assert AnalystId is not None
