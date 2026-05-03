"""Tests for the new synthetic-history builders added in Plan 04-01.

Covers `synthetic_oversold_history`, `synthetic_overbought_history`, and
`synthetic_mean_reverting_history` — three builders that produce explicit
overbought / oversold / range-regime price-history shapes for Phase 4
regression testing. Determinism contract verified for each.
"""
from __future__ import annotations

from tests.analysts.conftest import (
    synthetic_mean_reverting_history,
    synthetic_overbought_history,
    synthetic_oversold_history,
)


def test_synthetic_oversold_history_qualitative() -> None:
    """252-bar oversold history: sustained downtrend + final-shock-drop."""
    bars = synthetic_oversold_history(252)
    assert len(bars) == 252
    # Sustained -0.5% daily for 247 bars + final -5% drops for 5 bars.
    # Theoretical: 200 * 0.995^247 * 0.95^5 ≈ 200 * 0.290 * 0.774 ≈ 45 (~22.5% of start).
    assert bars[-1].close < bars[0].close * 0.5
    for b in bars:
        assert b.high > b.close > b.low > 0
        assert b.volume > 0


def test_synthetic_overbought_history_qualitative() -> None:
    """252-bar overbought history: sustained uptrend + final-shock-pop."""
    bars = synthetic_overbought_history(252)
    assert len(bars) == 252
    # Theoretical: 100 * 1.005^247 * 1.05^5 ≈ 100 * 3.44 * 1.276 ≈ 439 (~4.4x start).
    assert bars[-1].close > bars[0].close * 2.0
    for b in bars:
        assert b.high > b.close > b.low > 0


def test_synthetic_mean_reverting_history_oscillates() -> None:
    """252-bar mean-reverting history: sinusoidal oscillation around start."""
    bars = synthetic_mean_reverting_history(252, period_bars=50, amplitude=0.10)
    closes = [b.close for b in bars]
    assert len(closes) == 252
    # Default start=150.0; sinusoidal around start.
    mean_close = sum(closes) / len(closes)
    assert abs(mean_close - 150.0) < 5.0
    # Amplitude=0.10 → peaks/troughs at start ± 10% with deterministic noise on top.
    assert max(closes) > 150.0 * 1.05
    assert min(closes) < 150.0 * 0.95


def test_synthetic_fixtures_deterministic() -> None:
    """Two calls with identical args produce byte-identical OHLCBar lists."""
    for builder in (
        synthetic_oversold_history,
        synthetic_overbought_history,
        synthetic_mean_reverting_history,
    ):
        bars1 = builder(60)
        bars2 = builder(60)
        assert bars1 == bars2, f"{builder.__name__} is not deterministic"
