"""Tests for synthesis.dissent.compute_dissent + module constants.

Locks LLM-07 + Pattern #7 (05-RESEARCH.md):
  * Signed-weighted-vote majority direction (NOT mode-based majority verdict)
  * Opposite-direction-≥30-confidence trigger (boundary inclusive)
  * Tie-break: highest confidence first; alphabetical analyst_id second

Test coverage map (≥12 tests; ~16 with parametrization):
  * 2 module-constant locks (DISSENT_THRESHOLD == 30; VERDICT_TO_DIRECTION
    exact 5-key map with strong_bullish/bullish=+1, neutral=0,
    bearish/strong_bearish=-1).
  * Scenario 1 — no dissent: 6 all-bullish AgentSignals → (None, '').
  * Scenario 2 — clear dissent: 5 bullish + 1 burry-bearish-conf-80 →
    ('burry', summary mentioning 'bearish' + 'conf=80' + evidence).
  * Scenario 3 — boundary inclusive at 30: 5 bullish + 1 bearish-conf-30 →
    triggers; boundary exclusive at 29 → no dissent.
  * Edge — <2 valid persona signals: 1 valid + 5 data_unavailable → (None, '').
  * Edge — all data_unavailable: 6 personas → (None, '').
  * Edge — zero-sum direction_score: 3 bullish-conf-50 + 3 bearish-conf-50 →
    direction_score=0 → (None, '').
  * Edge — neutral doesn't count: 5 bullish + 1 neutral-conf-80 →
    direction=0 for neutral, not opposite to majority → no dissent.
  * Tie-break — confidence: 4 bullish + 2 bearish (conf 40 vs 70) →
    conf=70 wins.
  * Tie-break — alphabetical at confidence-tie: burry vs munger at
    same conf=70 → 'burry' alphabetical first.
  * Return shape contract: tuple of (Optional[str], str).
  * Summary truncation at 500 chars.

frozen_now fixture comes from tests/conftest.py (root-level).
"""
from __future__ import annotations

from datetime import datetime

import pytest

from analysts.signals import AgentSignal
from synthesis.dissent import (
    DISSENT_THRESHOLD,
    VERDICT_TO_DIRECTION,
    compute_dissent,
)


# ---------------------------------------------------------------------------
# Helpers — local module-level builder (mirrors test_decision.py _band /
# _decision pattern). Not promoted to pytest fixture because each test only
# overrides 1-2 fields and the call-site flat list is clearer than a builder
# fixture closure.
# ---------------------------------------------------------------------------


def _persona(
    analyst_id: str,
    verdict: str,
    confidence: int,
    evidence: list[str] | None = None,
    *,
    data_unavailable: bool = False,
    computed_at: datetime,
) -> AgentSignal:
    return AgentSignal(
        ticker="AAPL",
        analyst_id=analyst_id,
        computed_at=computed_at,
        verdict=verdict,
        confidence=confidence,
        evidence=evidence if evidence is not None else [f"{analyst_id} reasoning"],
        data_unavailable=data_unavailable,
    )


# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------


def test_dissent_threshold_is_30() -> None:
    """LLM-07 boundary: confidence == 30 on opposite direction triggers dissent."""
    assert DISSENT_THRESHOLD == 30


def test_verdict_to_direction_mapping() -> None:
    """5-key map: strong_bullish/bullish=+1; neutral=0; bearish/strong_bearish=-1."""
    assert VERDICT_TO_DIRECTION == {
        "strong_bearish": -1,
        "bearish": -1,
        "neutral": 0,
        "bullish": 1,
        "strong_bullish": 1,
    }


# ---------------------------------------------------------------------------
# Scenario 1 — no dissent
# ---------------------------------------------------------------------------


def test_no_dissent_all_bullish(frozen_now: datetime) -> None:
    signals = [
        _persona("buffett", "bullish", 70, computed_at=frozen_now),
        _persona("munger", "bullish", 80, computed_at=frozen_now),
        _persona("wood", "strong_bullish", 60, computed_at=frozen_now),
        _persona("burry", "bullish", 50, computed_at=frozen_now),
        _persona("lynch", "bullish", 65, computed_at=frozen_now),
        _persona("claude_analyst", "bullish", 55, computed_at=frozen_now),
    ]
    pid, summary = compute_dissent(signals)
    assert pid is None
    assert summary == ""


# ---------------------------------------------------------------------------
# Scenario 2 — clear dissent (5 bullish + 1 burry-bearish-conf-80)
# ---------------------------------------------------------------------------


def test_clear_dissent_burry_bearish(frozen_now: datetime) -> None:
    signals = [
        _persona("buffett", "bullish", 70, computed_at=frozen_now),
        _persona("munger", "bullish", 70, computed_at=frozen_now),
        _persona("wood", "bullish", 70, computed_at=frozen_now),
        _persona(
            "burry",
            "bearish",
            80,
            evidence=["hidden risk in margin compression"],
            computed_at=frozen_now,
        ),
        _persona("lynch", "bullish", 70, computed_at=frozen_now),
        _persona("claude_analyst", "bullish", 70, computed_at=frozen_now),
    ]
    pid, summary = compute_dissent(signals)
    assert pid == "burry"
    assert "burry dissents" in summary
    assert "bearish" in summary
    assert "conf=80" in summary
    assert "hidden risk in margin compression" in summary


# ---------------------------------------------------------------------------
# Scenario 3 — boundary inclusive at 30 / exclusive below 30
# ---------------------------------------------------------------------------


def test_dissent_boundary_inclusive_at_30(frozen_now: datetime) -> None:
    """confidence==DISSENT_THRESHOLD on opposite direction MUST trigger."""
    signals = [
        _persona("buffett", "bullish", 50, computed_at=frozen_now),
        _persona("munger", "bullish", 50, computed_at=frozen_now),
        _persona("wood", "bullish", 50, computed_at=frozen_now),
        _persona("burry", "bearish", 30, computed_at=frozen_now),
        _persona("lynch", "bullish", 50, computed_at=frozen_now),
        _persona("claude_analyst", "bullish", 50, computed_at=frozen_now),
    ]
    pid, summary = compute_dissent(signals)
    assert pid == "burry"
    assert "conf=30" in summary


def test_dissent_boundary_exclusive_below_30(frozen_now: datetime) -> None:
    signals = [
        _persona("buffett", "bullish", 50, computed_at=frozen_now),
        _persona("munger", "bullish", 50, computed_at=frozen_now),
        _persona("wood", "bullish", 50, computed_at=frozen_now),
        _persona("burry", "bearish", 29, computed_at=frozen_now),
        _persona("lynch", "bullish", 50, computed_at=frozen_now),
        _persona("claude_analyst", "bullish", 50, computed_at=frozen_now),
    ]
    pid, summary = compute_dissent(signals)
    assert pid is None
    assert summary == ""


# ---------------------------------------------------------------------------
# Edge: <2 valid persona signals
# ---------------------------------------------------------------------------


def test_dissent_lt_2_valid_signals(frozen_now: datetime) -> None:
    """1 valid + 5 data_unavailable → can't define majority from <2 → no dissent."""
    signals = [
        _persona("buffett", "bullish", 70, computed_at=frozen_now),
    ] + [
        _persona(
            pid, "neutral", 0, data_unavailable=True, computed_at=frozen_now,
        )
        for pid in ("munger", "wood", "burry", "lynch", "claude_analyst")
    ]
    pid, summary = compute_dissent(signals)
    assert pid is None
    assert summary == ""


def test_dissent_all_data_unavailable(frozen_now: datetime) -> None:
    signals = [
        _persona(
            pid, "neutral", 0, data_unavailable=True, computed_at=frozen_now,
        )
        for pid in ("buffett", "munger", "wood", "burry", "lynch", "claude_analyst")
    ]
    pid, summary = compute_dissent(signals)
    assert pid is None
    assert summary == ""


# ---------------------------------------------------------------------------
# Edge: zero-sum direction_score
# ---------------------------------------------------------------------------


def test_dissent_zero_sum_direction(frozen_now: datetime) -> None:
    """3 bullish (+150) + 3 bearish (-150) = 0 → no clear majority direction."""
    signals = [
        _persona("buffett", "bullish", 50, computed_at=frozen_now),
        _persona("munger", "bullish", 50, computed_at=frozen_now),
        _persona("wood", "bullish", 50, computed_at=frozen_now),
        _persona("burry", "bearish", 50, computed_at=frozen_now),
        _persona("lynch", "bearish", 50, computed_at=frozen_now),
        _persona("claude_analyst", "bearish", 50, computed_at=frozen_now),
    ]
    pid, summary = compute_dissent(signals)
    assert pid is None
    assert summary == ""


# ---------------------------------------------------------------------------
# Edge: neutral personas don't count as dissent
# ---------------------------------------------------------------------------


def test_dissent_neutral_doesnt_count(frozen_now: datetime) -> None:
    """5 bullish + 1 neutral-conf-80 → neutral has direction=0, not opposite."""
    signals = [
        _persona("buffett", "bullish", 70, computed_at=frozen_now),
        _persona("munger", "bullish", 70, computed_at=frozen_now),
        _persona("wood", "bullish", 70, computed_at=frozen_now),
        _persona("burry", "neutral", 80, computed_at=frozen_now),
        _persona("lynch", "bullish", 70, computed_at=frozen_now),
        _persona("claude_analyst", "bullish", 70, computed_at=frozen_now),
    ]
    pid, summary = compute_dissent(signals)
    assert pid is None
    assert summary == ""


# ---------------------------------------------------------------------------
# Tie-break 1: highest confidence wins
# ---------------------------------------------------------------------------


def test_dissent_tie_break_by_confidence(frozen_now: datetime) -> None:
    """2 bearish dissenters at conf 40 vs 70 → conf=70 wins."""
    signals = [
        _persona("buffett", "bullish", 50, computed_at=frozen_now),
        _persona("munger", "bullish", 50, computed_at=frozen_now),
        _persona("wood", "bullish", 50, computed_at=frozen_now),
        _persona("burry", "bearish", 40, computed_at=frozen_now),
        _persona("lynch", "bullish", 50, computed_at=frozen_now),
        _persona("claude_analyst", "bearish", 70, computed_at=frozen_now),
    ]
    pid, summary = compute_dissent(signals)
    assert pid == "claude_analyst"
    assert "conf=70" in summary


# ---------------------------------------------------------------------------
# Tie-break 2: alphabetical when confidence ties
# ---------------------------------------------------------------------------


def test_dissent_tie_break_alphabetical_when_conf_ties(
    frozen_now: datetime,
) -> None:
    """2 bearish dissenters at SAME conf=70: burry < munger alphabetically."""
    signals = [
        _persona("buffett", "bullish", 80, computed_at=frozen_now),
        _persona("munger", "bearish", 70, computed_at=frozen_now),
        _persona("wood", "bullish", 80, computed_at=frozen_now),
        _persona("burry", "bearish", 70, computed_at=frozen_now),
        _persona("lynch", "bullish", 80, computed_at=frozen_now),
        _persona("claude_analyst", "bullish", 80, computed_at=frozen_now),
    ]
    pid, summary = compute_dissent(signals)
    assert pid == "burry"  # burry < munger alphabetically


# ---------------------------------------------------------------------------
# Return shape contracts
# ---------------------------------------------------------------------------


def test_dissent_return_shape_no_dissent_is_tuple(frozen_now: datetime) -> None:
    signals = [
        _persona(pid, "bullish", 70, computed_at=frozen_now)
        for pid in (
            "buffett", "munger", "wood", "burry", "lynch", "claude_analyst",
        )
    ]
    result = compute_dissent(signals)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert result[0] is None
    assert isinstance(result[1], str)


def test_dissent_summary_truncated_at_500(frozen_now: datetime) -> None:
    """Long evidence joined with '; ' could exceed 500 chars; truncate defensively."""
    long_evidence = ["x" * 200, "y" * 200, "z" * 200]  # ≈600 chars when joined
    signals = [
        _persona("buffett", "bullish", 70, computed_at=frozen_now),
        _persona("munger", "bullish", 70, computed_at=frozen_now),
        _persona("wood", "bullish", 70, computed_at=frozen_now),
        _persona(
            "burry",
            "bearish",
            80,
            evidence=long_evidence,
            computed_at=frozen_now,
        ),
        _persona("lynch", "bullish", 70, computed_at=frozen_now),
        _persona("claude_analyst", "bullish", 70, computed_at=frozen_now),
    ]
    pid, summary = compute_dissent(signals)
    assert pid == "burry"
    assert len(summary) <= 500


# ---------------------------------------------------------------------------
# Coverage: empty list + summary content sanity
# ---------------------------------------------------------------------------


def test_dissent_empty_list() -> None:
    """compute_dissent([]) is the degenerate <2 case → (None, '')."""
    pid, summary = compute_dissent([])
    assert pid is None
    assert summary == ""


def test_dissent_strong_verdicts_treated_as_directional(
    frozen_now: datetime,
) -> None:
    """strong_bullish maps to +1 and strong_bearish to -1 in VERDICT_TO_DIRECTION."""
    signals = [
        _persona("buffett", "strong_bullish", 80, computed_at=frozen_now),
        _persona("munger", "strong_bullish", 80, computed_at=frozen_now),
        _persona("wood", "strong_bullish", 80, computed_at=frozen_now),
        _persona(
            "burry",
            "strong_bearish",
            70,
            evidence=["macro warning"],
            computed_at=frozen_now,
        ),
        _persona("lynch", "strong_bullish", 80, computed_at=frozen_now),
        _persona("claude_analyst", "strong_bullish", 80, computed_at=frozen_now),
    ]
    pid, summary = compute_dissent(signals)
    assert pid == "burry"
    assert "strong_bearish" in summary
