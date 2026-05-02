"""Shared fixtures + factory builders for the Phase 3 analyst test suite.

Pattern reference: 03-RESEARCH.md Pattern 2 — factory fixtures (closures over
keyword overrides) beat fixture classes for unit-test readability when the
same model needs to be built with one or two field overrides per test.

Public surface (consumed by all four Wave 2 analyst test files
03-02/03-03/03-04/03-05 plus tests/analysts/test_signals.py and
tests/analysts/test_invariants.py in this plan):

    Pytest fixtures:
        frozen_now           — pinned UTC datetime for reproducible computed_at stamps
        make_ticker_config   — builder closure over TickerConfig with sensible defaults
        make_snapshot        — builder closure over Snapshot with sensible defaults

    Module-level builders (NOT fixtures — importable directly so tests can pin n):
        synthetic_uptrend_history(n, start, daily_drift)  -> list[OHLCBar]
        synthetic_downtrend_history(n, start, daily_drift) -> list[OHLCBar]
        synthetic_sideways_history(n, start, amplitude)    -> list[OHLCBar]

Determinism contract: builders use NO random sources. Two calls with identical
arguments produce byte-identical OHLCBar lists. Tests that depend on this
property pin `n` explicitly. The deterministic-noise pattern uses
`(i % 5) - 2` for HLC variance and `i * 100` for volume drift — small enough
not to swamp the directional signal, large enough to keep H > C > L
strictly true on every bar.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone

import pytest

from analysts.data.prices import OHLCBar
from analysts.data.snapshot import Snapshot
from analysts.schemas import TickerConfig

# Pinned UTC datetime used as `computed_at` / `fetched_at` in every test that
# needs reproducible timestamps. Same value as 02-06 test fixtures use so
# fixtures cross-pollinate cleanly between Phase 2 and Phase 3 test files.
FROZEN_DT = datetime(2026, 5, 1, 13, 30, 0, tzinfo=timezone.utc)


def _build_ohlc_bars(
    n: int,
    start: float,
    *,
    close_fn,
) -> list[OHLCBar]:
    """Internal helper: construct n daily OHLCBars ending at FROZEN_DT.date().

    `close_fn(i, prev_close, start)` returns the close price for bar i (0-indexed).
    open = close * 0.998, high = close * 1.01, low = close * 0.99 (constants
    chosen so high > close > low > 0 for any positive close); volume drifts
    deterministically via 1_000_000 + i * 100.
    """
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n!r}")
    if start <= 0:
        raise ValueError(f"start must be > 0, got {start!r}")

    end_date: date = FROZEN_DT.date()
    bars: list[OHLCBar] = []
    prev_close = start
    for i in range(n):
        d = end_date - timedelta(days=n - 1 - i)
        c = close_fn(i, prev_close, start)
        # Defensive: clamp tiny non-positive computations (e.g. extreme downtrend
        # over very long n) so OHLCBar's gt=0 constraint never fires from a
        # legitimate fixture. Real fixtures pick drifts that never bottom out.
        if c <= 0:
            c = 0.01
        o = c * 0.998
        h = c * 1.01
        low_ = c * 0.99
        v = 1_000_000 + i * 100
        bars.append(OHLCBar(date=d, open=o, high=h, low=low_, close=c, volume=v))
        prev_close = c
    return bars


def synthetic_uptrend_history(
    n: int = 252,
    start: float = 100.0,
    daily_drift: float = 0.005,
) -> list[OHLCBar]:
    """n daily bars with positive geometric drift + tiny deterministic noise.

    Default 252 bars (~1 trading year) with daily_drift=0.005 → ~1.005**252 ≈ 3.5x
    return over the full window — clearly bullish at every horizon (1m, 3m, 6m).
    Used by the technicals analyst (03-03) to assert MA20 > MA50 > MA200 (bullish
    stack) and momentum > 0 across all three windows.
    """
    def _close(i: int, prev: float, _start: float) -> float:
        # Geometric drift + small bounded noise. Noise term is `0.001 * ((i%5)-2)`
        # which oscillates over {-0.002, -0.001, 0, 0.001, 0.002} — large enough
        # to vary daily ranges, small enough not to affect 20+ day MAs.
        return prev * (1.0 + daily_drift) + 0.001 * ((i % 5) - 2)

    return _build_ohlc_bars(n, start, close_fn=_close)


def synthetic_downtrend_history(
    n: int = 252,
    start: float = 200.0,
    daily_drift: float = -0.005,
) -> list[OHLCBar]:
    """n daily bars with negative geometric drift + tiny deterministic noise.

    Mirror of synthetic_uptrend_history. Default 252 bars with daily_drift=-0.005
    → ~0.995**252 ≈ 0.28x — clearly bearish at every horizon.
    """
    def _close(i: int, prev: float, _start: float) -> float:
        return prev * (1.0 + daily_drift) + 0.001 * ((i % 5) - 2)

    return _build_ohlc_bars(n, start, close_fn=_close)


def synthetic_sideways_history(
    n: int = 252,
    start: float = 150.0,
    amplitude: float = 0.02,
) -> list[OHLCBar]:
    """n daily bars in a range-bound sinusoidal pattern around `start`.

    close[i] = start * (1 + amplitude * sin(2π i / 20)) — period of 20 bars.
    No drift → MA20 ≈ MA50 ≈ MA200 ≈ start, ADX < 20 (range regime). Used by
    the technicals analyst (03-03) to verify trend-regime gating fires when ADX
    indicates mean-reversion conditions.
    """
    def _close(i: int, _prev: float, s: float) -> float:
        return s * (1.0 + amplitude * math.sin(2.0 * math.pi * i / 20.0))

    return _build_ohlc_bars(n, start, close_fn=_close)


@pytest.fixture
def frozen_now() -> datetime:
    """Pinned UTC datetime — pass as `computed_at=` to score() functions for byte-stable assertions."""
    return FROZEN_DT


@pytest.fixture
def make_ticker_config():
    """Returns a builder closure for TickerConfig with sensible defaults.

    Usage:
        cfg = make_ticker_config(ticker="NVDA", thesis_price=900.0)
    """
    def _build(**overrides) -> TickerConfig:
        kwargs: dict = {"ticker": "AAPL"}
        kwargs.update(overrides)
        return TickerConfig(**kwargs)

    return _build


@pytest.fixture
def make_snapshot(frozen_now: datetime):
    """Returns a builder closure for Snapshot with sensible defaults.

    Defaults to ticker=AAPL, fetched_at=frozen_now, all sub-fields None/empty
    (matching the post-fetch shape Plan 02-06 produces when no source returned
    useful data). Override any field by passing it as a kwarg:

        snap = make_snapshot(prices=PriceSnapshot(...), fundamentals=...)
    """
    def _build(**overrides) -> Snapshot:
        kwargs: dict = {"ticker": "AAPL", "fetched_at": frozen_now}
        kwargs.update(overrides)
        return Snapshot(**kwargs)

    return _build
