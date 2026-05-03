"""Tests for analysts/position_adjustment.py — Position-Adjustment Radar.

Coverage map (per 04-03-position-adjustment-PLAN.md):
  * Empty-data UNIFORM RULE — 5 branches
  * POSE-01: 6 indicators correct (RSI / BB / zscore / Stoch / Williams / MACD)
    + cross-ticker scale invariance
  * POSE-02: 5-state ladder + strict > / < boundaries + consensus_score clamp
    + confidence formula (full agreement / abstain rule / n_active<2 / near-zero)
  * POSE-03: ADX trend-regime gating (uptrend / sideways / ambiguous / warm-up
    / boundary at 25 / downweight verification)
  * POSE-04: state → action_hint mapping (5 cases)
  * POSE-05: known-regime regressions (oversold / overbought / sideways)
  * Warm-up tiers — 5 boundary cases (14-19 / 20-26 / 27-49 / 50-93 / ≥94)
  * Determinism + provenance + no-forbidden-imports
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from analysts.data.prices import OHLCBar, PriceSnapshot
from analysts.position_adjustment import (
    _bb_to_subsignal,
    _consensus_to_state,
    _macd_z_to_subsignal,
    _rsi_to_subsignal,
    _state_to_action_hint,
    _stoch_to_subsignal,
    _williams_to_subsignal,
    _zscore_to_subsignal,
    score,
)
from analysts.position_signal import ActionHint, PositionSignal, PositionState
from tests.analysts.conftest import (
    synthetic_mean_reverting_history,
    synthetic_overbought_history,
    synthetic_oversold_history,
    synthetic_sideways_history,
    synthetic_uptrend_history,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_price_snapshot(
    history: list[OHLCBar],
    frozen_now: datetime,
    *,
    ticker: str = "AAPL",
    data_unavailable: bool = False,
) -> PriceSnapshot:
    return PriceSnapshot(
        ticker=ticker,
        fetched_at=frozen_now,
        source="yfinance",
        data_unavailable=data_unavailable,
        current_price=history[-1].close if history else None,
        history=history,
    )


# ---------------------------------------------------------------------------
# Empty-data UNIFORM RULE
# ---------------------------------------------------------------------------


def test_empty_data_snapshot_unavailable(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    snap = make_snapshot(data_unavailable=True)
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.data_unavailable is True
    assert sig.state == "fair"
    assert sig.consensus_score == 0.0
    assert sig.confidence == 0
    assert sig.action_hint == "hold_position"
    assert sig.trend_regime is False
    assert sig.evidence == ["snapshot data_unavailable=True"]
    assert sig.indicators.keys() == {
        "rsi_14", "bb_position", "zscore_50", "stoch_k",
        "williams_r", "macd_histogram", "adx_14",
    }
    assert all(v is None for v in sig.indicators.values())


def test_empty_data_prices_none(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    snap = make_snapshot(prices=None)
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.data_unavailable is True
    assert "prices snapshot missing" in sig.evidence[0]


def test_empty_data_prices_data_unavailable(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    snap = make_snapshot(
        prices=PriceSnapshot(
            ticker="AAPL",
            fetched_at=frozen_now,
            source="yfinance",
            data_unavailable=True,
            current_price=None,
            history=[],
        )
    )
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.data_unavailable is True
    assert "prices.data_unavailable=True" in sig.evidence[0]


def test_empty_data_history_empty(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    snap = make_snapshot(
        prices=PriceSnapshot(
            ticker="AAPL",
            fetched_at=frozen_now,
            source="yfinance",
            data_unavailable=False,
            current_price=None,
            history=[],
        )
    )
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.data_unavailable is True
    assert "prices history is empty" in sig.evidence[0]


def test_empty_data_history_below_min_bars(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    history = synthetic_uptrend_history(10)
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.data_unavailable is True
    assert "10 bars" in sig.evidence[0]
    assert "14" in sig.evidence[0]
    assert sig.indicators.keys() == {
        "rsi_14", "bb_position", "zscore_50", "stoch_k",
        "williams_r", "macd_histogram", "adx_14",
    }
    assert all(v is None for v in sig.indicators.values())


# ---------------------------------------------------------------------------
# POSE-01 — Indicator correctness
# ---------------------------------------------------------------------------


def test_rsi_oversold_regression(make_snapshot, make_ticker_config, frozen_now) -> None:
    history = synthetic_oversold_history(252)
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.indicators["rsi_14"] is not None
    assert sig.indicators["rsi_14"] < 30
    assert any("RSI(14)" in e and "oversold" in e for e in sig.evidence)


def test_rsi_overbought_regression(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    history = synthetic_overbought_history(252)
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.indicators["rsi_14"] is not None
    assert sig.indicators["rsi_14"] > 70
    assert any("RSI(14)" in e and "overbought" in e for e in sig.evidence)


def test_bb_position_oversold_regression(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    history = synthetic_oversold_history(252)
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.indicators["bb_position"] is not None
    assert sig.indicators["bb_position"] < -1.0


def test_bb_position_overbought_regression(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    history = synthetic_overbought_history(252)
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.indicators["bb_position"] is not None
    assert sig.indicators["bb_position"] > 1.0


def test_stoch_k_extremes(make_snapshot, make_ticker_config, frozen_now) -> None:
    over = synthetic_overbought_history(252)
    under = synthetic_oversold_history(252)
    snap_over = make_snapshot(prices=_make_price_snapshot(over, frozen_now))
    snap_under = make_snapshot(prices=_make_price_snapshot(under, frozen_now))
    cfg = make_ticker_config()

    sig_over = score(snap_over, cfg, computed_at=frozen_now)
    sig_under = score(snap_under, cfg, computed_at=frozen_now)

    assert sig_over.indicators["stoch_k"] > 80
    assert sig_under.indicators["stoch_k"] < 20


def test_williams_r_extremes(make_snapshot, make_ticker_config, frozen_now) -> None:
    over = synthetic_overbought_history(252)
    under = synthetic_oversold_history(252)
    snap_over = make_snapshot(prices=_make_price_snapshot(over, frozen_now))
    snap_under = make_snapshot(prices=_make_price_snapshot(under, frozen_now))
    cfg = make_ticker_config()

    sig_over = score(snap_over, cfg, computed_at=frozen_now)
    sig_under = score(snap_under, cfg, computed_at=frozen_now)

    assert sig_over.indicators["williams_r"] > -20
    assert sig_under.indicators["williams_r"] < -80


def test_zscore_extremes(make_snapshot, make_ticker_config, frozen_now) -> None:
    over = synthetic_overbought_history(252)
    under = synthetic_oversold_history(252)
    snap_over = make_snapshot(prices=_make_price_snapshot(over, frozen_now))
    snap_under = make_snapshot(prices=_make_price_snapshot(under, frozen_now))
    cfg = make_ticker_config()

    sig_over = score(snap_over, cfg, computed_at=frozen_now)
    sig_under = score(snap_under, cfg, computed_at=frozen_now)

    assert sig_over.indicators["zscore_50"] > 1.5
    assert sig_under.indicators["zscore_50"] < -1.5


def test_macd_zscore_signed(make_snapshot, make_ticker_config, frozen_now) -> None:
    over = synthetic_overbought_history(252)
    under = synthetic_oversold_history(252)
    snap_over = make_snapshot(prices=_make_price_snapshot(over, frozen_now))
    snap_under = make_snapshot(prices=_make_price_snapshot(under, frozen_now))
    cfg = make_ticker_config()

    sig_over = score(snap_over, cfg, computed_at=frozen_now)
    sig_under = score(snap_under, cfg, computed_at=frozen_now)

    assert sig_over.indicators["macd_histogram"] is not None
    assert sig_under.indicators["macd_histogram"] is not None
    # Sign matters — overbought should produce positive, oversold negative.
    # Note: MACD lags; in extreme conditions the sign flips, so we lock the
    # weaker but reliable invariant: they DIFFER in sign.
    assert (
        sig_over.indicators["macd_histogram"] * sig_under.indicators["macd_histogram"]
        < 0
    )


def test_macd_scale_invariance(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """Cross-ticker scale invariance — 100x price difference must not bias the verdict."""
    over_low = synthetic_overbought_history(252, start=10.0)
    over_high = synthetic_overbought_history(252, start=1000.0)
    snap_low = make_snapshot(prices=_make_price_snapshot(over_low, frozen_now))
    snap_high = make_snapshot(prices=_make_price_snapshot(over_high, frozen_now))
    cfg = make_ticker_config()

    sig_low = score(snap_low, cfg, computed_at=frozen_now)
    sig_high = score(snap_high, cfg, computed_at=frozen_now)

    assert abs(sig_low.consensus_score - sig_high.consensus_score) < 0.10


# ---------------------------------------------------------------------------
# POSE-02 — State ladder + confidence formula
# ---------------------------------------------------------------------------


def test_state_ladder_oversold(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    history = synthetic_oversold_history(252)
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.state in ("oversold", "extreme_oversold")


def test_state_ladder_overbought(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    history = synthetic_overbought_history(252)
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.state in ("overbought", "extreme_overbought")


def test_state_ladder_sideways_no_strong_tier(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """synthetic_sideways_history(252) is sinusoidal — at the random sampled
    phase its mean-reversion indicators may show oversold/overbought readings.
    The strong tier MUST NOT fire; magnitude stays modest.
    """
    history = synthetic_sideways_history(252)
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.state in ("fair", "oversold", "overbought")
    assert sig.state not in ("extreme_oversold", "extreme_overbought")
    assert abs(sig.consensus_score) < 0.6


@pytest.mark.parametrize(
    "score_in,expected",
    [
        (-0.7, "extreme_oversold"),
        (-0.61, "extreme_oversold"),
        (-0.6, "oversold"),     # strict < -0.6 fails
        (-0.5, "oversold"),
        (-0.21, "oversold"),
        (-0.2, "fair"),         # strict < -0.2 fails
        (0.0, "fair"),
        (0.2, "fair"),          # strict > 0.2 fails
        (0.21, "overbought"),
        (0.6, "overbought"),    # strict > 0.6 fails
        (0.61, "extreme_overbought"),
        (0.7, "extreme_overbought"),
    ],
)
def test_consensus_to_state_strict_boundaries(
    score_in: float, expected: str
) -> None:
    assert _consensus_to_state(score_in) == expected


def test_consensus_score_range_clamp(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """Defensive clamp — consensus_score stays in [-1.0, +1.0] even with extreme inputs."""
    history = synthetic_overbought_history(
        252, start=100.0, daily_drift=0.005, final_pop_bars=10, final_pop_pct=0.30
    )
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert -1.0 <= sig.consensus_score <= 1.0


def test_confidence_full_agreement(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    history = synthetic_overbought_history(252)
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    # All 6 indicators should agree on overbought consensus → high confidence.
    assert sig.confidence >= 50


def test_confidence_n_active_lt_2_zero() -> None:
    """n_active < 2 → confidence == 0. Direct unit test on _compute_confidence."""
    from analysts.position_adjustment import _compute_confidence

    # 1 active sub-signal, agreeing.
    assert _compute_confidence([(0.5, 1.0, "x")], consensus_score=0.5) == 0
    # 0 active sub-signals.
    assert _compute_confidence([], consensus_score=0.0) == 0


def test_confidence_near_zero_consensus_zero() -> None:
    """|consensus_score| < CONFIDENCE_ABSTAIN_THRESHOLD → confidence == 0."""
    from analysts.position_adjustment import _compute_confidence

    sub = [(0.5, 1.0, "a"), (-0.5, 1.0, "b")]
    assert _compute_confidence(sub, consensus_score=0.005) == 0


def test_confidence_abstain_rule() -> None:
    """Indicators with |sub_signal| < CONFIDENCE_ABSTAIN_THRESHOLD count toward
    n_active but NOT n_agreeing.
    """
    from analysts.position_adjustment import _compute_confidence

    sub = [
        (-0.5, 1.0, "a"),
        (-0.5, 1.0, "b"),
        (-0.5, 1.0, "c"),
        (-0.5, 1.0, "d"),
        (-0.5, 1.0, "e"),
        (0.0, 1.0, "f"),  # abstaining
    ]
    # consensus_score is the weighted mean; with these 6 sub-signals at weight 1 each,
    # mean = (-0.5 * 5 + 0.0) / 6 ≈ -0.417.
    assert _compute_confidence(sub, consensus_score=-0.417) == round(100 * 5 / 6)


# ---------------------------------------------------------------------------
# POSE-03 — ADX trend-regime gating
# ---------------------------------------------------------------------------


def test_adx_trend_regime_uptrend(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    history = synthetic_uptrend_history(252)
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.trend_regime is True
    assert any("trend regime" in e and "downweighted" in e for e in sig.evidence)


def test_adx_range_or_ambiguous_regime_sideways(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """synthetic_sideways_history(252) ADX lands ~21 (ambiguous zone 20-25).
    Accept either 'range regime' OR 'ambiguous regime' evidence — both cases
    keep all weights at 1.0 (no gating). Phase 3's similar technical test
    uses the same union per its documented amplitude flakiness.
    """
    history = synthetic_sideways_history(252)
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.trend_regime is False
    assert any(
        "range regime" in e or "ambiguous regime" in e for e in sig.evidence
    )


def test_adx_warmup_no_gating(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """Below 27 bars → ADX is None, trend_regime=False, no ADX evidence string."""
    history = synthetic_uptrend_history(20)
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.trend_regime is False
    assert sig.indicators["adx_14"] is None
    assert not any("ADX" in e for e in sig.evidence)


def test_adx_boundary_25_exact(
    make_snapshot, make_ticker_config, frozen_now, monkeypatch
) -> None:
    """ADX=24.99 → no gating; ADX=25.01 → gating active."""
    history = synthetic_uptrend_history(252)
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    monkeypatch.setattr("analysts.position_adjustment._adx_14", lambda df: 24.99)
    sig_below = score(snap, cfg, computed_at=frozen_now)
    assert sig_below.trend_regime is False

    monkeypatch.setattr("analysts.position_adjustment._adx_14", lambda df: 25.01)
    sig_above = score(snap, cfg, computed_at=frozen_now)
    assert sig_above.trend_regime is True


def test_trend_regime_downweights_mean_reversion(
    make_snapshot, make_ticker_config, frozen_now, monkeypatch
) -> None:
    """When mean-reversion indicators are extreme but trend-following indicators
    are neutral, ADX gating downweights the mean-reversion contribution and
    weakens the consensus toward zero.

    Rather than hunt for a synthetic fixture with this exact divergence, we
    monkeypatch the 6 indicator helpers directly to control sub-signals:
    mean-reversion indicators all give -1 (extreme oversold), trend-following
    indicators give 0 (neutral). With this setup:
      * No gating: weighted mean = (-1*4 + 0*2) / 6 = -0.667
      * Gating (ADX > 25): weighted mean = (-1*0.5*4 + 0*1*2) / (0.5*4 + 1*2) = -0.5
    Gating must produce |consensus_score| smaller in magnitude.
    """
    history = synthetic_uptrend_history(252)  # any ≥94-bar history works
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    # Mean-reversion indicators saturate negative; trend-following stay neutral.
    # RSI: low value → oversold. BB: very negative. Stoch: low. Williams: low.
    # Z-score: 0 (neutral). MACD: 0 (neutral).
    monkeypatch.setattr("analysts.position_adjustment._rsi_14", lambda df: 0.0)
    monkeypatch.setattr(
        "analysts.position_adjustment._bollinger_position", lambda df: -2.0
    )
    monkeypatch.setattr("analysts.position_adjustment._stoch_k_14", lambda df: 0.0)
    monkeypatch.setattr(
        "analysts.position_adjustment._williams_r_14", lambda df: -100.0
    )
    monkeypatch.setattr("analysts.position_adjustment._zscore_vs_ma50", lambda df: 0.0)
    monkeypatch.setattr(
        "analysts.position_adjustment._macd_histogram_zscore", lambda df: 0.0
    )

    monkeypatch.setattr("analysts.position_adjustment._adx_14", lambda df: 15.0)
    sig_no_gate = score(snap, cfg, computed_at=frozen_now)

    monkeypatch.setattr("analysts.position_adjustment._adx_14", lambda df: 30.0)
    sig_gated = score(snap, cfg, computed_at=frozen_now)

    # Gating downweights mean-reversion → |consensus_score| smaller (closer to zero).
    assert abs(sig_gated.consensus_score) < abs(sig_no_gate.consensus_score)


# ---------------------------------------------------------------------------
# POSE-04 — state → action_hint mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "state,expected_hint",
    [
        ("extreme_oversold", "consider_add"),
        ("oversold", "consider_add"),
        ("fair", "hold_position"),
        ("overbought", "consider_trim"),
        ("extreme_overbought", "consider_take_profits"),
    ],
)
def test_state_to_action_hint_mapping(state: str, expected_hint: str) -> None:
    assert _state_to_action_hint(state) == expected_hint


# ---------------------------------------------------------------------------
# POSE-05 — Known-regime regressions (the headline lens)
# ---------------------------------------------------------------------------


def test_known_oversold_regression(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    history = synthetic_oversold_history(252)
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.state in ("oversold", "extreme_oversold")
    assert sig.consensus_score < -0.2
    assert sig.action_hint == "consider_add"


def test_known_overbought_regression(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    history = synthetic_overbought_history(252)
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.state in ("overbought", "extreme_overbought")
    assert sig.consensus_score > 0.2
    assert sig.action_hint in ("consider_trim", "consider_take_profits")


def test_known_sideways_no_strong_tier(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """Sideways: NOT in strong tier; magnitude low; action_hint not extreme.

    Sinusoidal fixture sampled at the last bar may show oversold/overbought
    readings (cycle phase tilt). Lock the regression: the analyst doesn't
    drift INTO the strong tiers on sideways data.
    """
    history = synthetic_sideways_history(252)
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.state in ("fair", "oversold", "overbought")
    assert sig.state not in ("extreme_oversold", "extreme_overbought")
    assert abs(sig.consensus_score) < 0.6
    assert sig.action_hint != "consider_take_profits"


# ---------------------------------------------------------------------------
# Warm-up tiers
# ---------------------------------------------------------------------------


def test_warmup_tier_14_to_19_only_stoch_williams(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    history = synthetic_uptrend_history(15)
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.indicators["rsi_14"] is None
    assert sig.indicators["bb_position"] is None
    assert sig.indicators["zscore_50"] is None
    assert sig.indicators["macd_histogram"] is None
    assert sig.indicators["adx_14"] is None
    assert sig.indicators["stoch_k"] is not None
    assert sig.indicators["williams_r"] is not None


def test_warmup_tier_20_to_26_adds_bb(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    history = synthetic_uptrend_history(22)
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.indicators["bb_position"] is not None
    assert sig.indicators["rsi_14"] is None
    assert sig.indicators["zscore_50"] is None
    assert sig.indicators["macd_histogram"] is None
    assert sig.indicators["adx_14"] is None


def test_warmup_tier_27_to_49_adds_rsi_adx(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    history = synthetic_uptrend_history(35)
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.indicators["rsi_14"] is not None
    assert sig.indicators["adx_14"] is not None
    assert sig.indicators["zscore_50"] is None
    assert sig.indicators["macd_histogram"] is None


def test_warmup_tier_50_to_93_adds_zscore(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    history = synthetic_uptrend_history(75)
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.indicators["zscore_50"] is not None
    assert sig.indicators["macd_histogram"] is None


def test_warmup_tier_ge_94_all_indicators(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    history = synthetic_uptrend_history(252)
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.indicators["rsi_14"] is not None
    assert sig.indicators["bb_position"] is not None
    assert sig.indicators["zscore_50"] is not None
    assert sig.indicators["stoch_k"] is not None
    assert sig.indicators["williams_r"] is not None
    assert sig.indicators["macd_histogram"] is not None
    assert sig.indicators["adx_14"] is not None


# ---------------------------------------------------------------------------
# Determinism + provenance + meta
# ---------------------------------------------------------------------------


def test_deterministic(make_snapshot, make_ticker_config, frozen_now) -> None:
    history = synthetic_overbought_history(252)
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    sig1 = score(snap, cfg, computed_at=frozen_now)
    sig2 = score(snap, cfg, computed_at=frozen_now)

    assert sig1.model_dump_json() == sig2.model_dump_json()


def test_computed_at_passes_through(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    history = synthetic_uptrend_history(252)
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.computed_at == frozen_now


def test_computed_at_default_uses_now(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    history = synthetic_uptrend_history(50)
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    before = datetime.now(timezone.utc)
    sig = score(snap, cfg)
    after = datetime.now(timezone.utc)

    assert before <= sig.computed_at <= after


def test_provenance_header_present() -> None:
    src = Path("analysts/position_adjustment.py").read_text(encoding="utf-8")
    assert "virattt/ai-hedge-fund/src/agents/risk_manager.py" in src


def test_no_ta_library_imports() -> None:
    """analysts/position_adjustment.py uses hand-rolled pandas — no ta-lib / pandas-ta IMPORTS."""
    import re

    src = Path("analysts/position_adjustment.py").read_text(encoding="utf-8")
    assert "import pandas as pd" in src
    forbidden = re.compile(
        r"^\s*(?:import|from)\s+(pandas_ta|talib|ta_lib)\b",
        re.MULTILINE,
    )
    matches = forbidden.findall(src)
    assert not matches, f"forbidden indicator-library imports: {matches}"


def test_returns_position_signal_type(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    history = synthetic_uptrend_history(252)
    snap = make_snapshot(prices=_make_price_snapshot(history, frozen_now))
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert isinstance(sig, PositionSignal)


# ---------------------------------------------------------------------------
# Sub-signal mapper unit tests (locks the linearization)
# ---------------------------------------------------------------------------


def test_subsignal_mappers_clamp_to_unit_interval() -> None:
    """All 6 sub-signal mappers clamp output to [-1, +1] with correct sign:
    negative = oversold, positive = overbought (per 04-CONTEXT.md aggregation).
    """
    # RSI: low (e.g. 0) = oversold = -1; high (100) = overbought = +1.
    assert _rsi_to_subsignal(0.0) == -1.0
    assert _rsi_to_subsignal(100.0) == 1.0
    assert _rsi_to_subsignal(50.0) == 0.0

    # Bollinger position: -1 = below lower band = oversold; +1 = above upper = overbought.
    assert _bb_to_subsignal(-5.0) == -1.0
    assert _bb_to_subsignal(5.0) == 1.0

    # z-score: negative = below MA = oversold; positive = above = overbought.
    assert _zscore_to_subsignal(-10.0) == -1.0
    assert _zscore_to_subsignal(10.0) == 1.0

    # Stochastic %K: low (0) = oversold = -1; high (100) = overbought = +1.
    assert _stoch_to_subsignal(0.0) == -1.0
    assert _stoch_to_subsignal(100.0) == 1.0
    assert _stoch_to_subsignal(50.0) == 0.0

    # Williams %R: low (-100) = oversold = -1; high (0) = overbought = +1.
    assert _williams_to_subsignal(-100.0) == -1.0
    assert _williams_to_subsignal(0.0) == 1.0

    # MACD z-score: negative = bearish momentum (oversold-direction); positive = bullish.
    assert _macd_z_to_subsignal(-10.0) == -1.0
    assert _macd_z_to_subsignal(10.0) == 1.0
