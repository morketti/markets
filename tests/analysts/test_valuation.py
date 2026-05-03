"""Tests for analysts/valuation.py — pure-function 3-tier blended scoring.

Coverage map (per 03-05-valuation-PLAN.md):
  * Each tier alone — thesis_price / target_multiples / yfinance consensus
  * All-three blend (density bonus active)
  * None-set UNIFORM RULE (no thesis, no targets, no consensus)
  * Empty-data UNIFORM RULE (no current price)
  * 02-07 cross-phase dep assertion (FundamentalsSnapshot.analyst_target_mean exists)
  * Determinism + provenance + density-confidence invariant

Cross-phase note: this test file ASSUMES Plan 02-07 has shipped — without
the analyst_target_mean field on FundamentalsSnapshot the consensus-tier
tests would fail at attribute access. The dedicated 02-07 dep test guards
against silent regression.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from analysts.data.fundamentals import FundamentalsSnapshot
from analysts.data.prices import PriceSnapshot
from analysts.schemas import FundamentalTargets, TickerConfig
from analysts.signals import AgentSignal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fund(
    *,
    fetched_at: datetime,
    pe: float | None = None,
    ps: float | None = None,
    pb: float | None = None,
    analyst_target_mean: float | None = None,
    analyst_target_median: float | None = None,
    analyst_recommendation_mean: float | None = None,
    analyst_opinion_count: int | None = None,
    data_unavailable: bool = False,
) -> FundamentalsSnapshot:
    """Minimal FundamentalsSnapshot builder."""
    return FundamentalsSnapshot(
        ticker="AAPL",
        fetched_at=fetched_at,
        source="yfinance",
        data_unavailable=data_unavailable,
        pe=pe,
        ps=ps,
        pb=pb,
        analyst_target_mean=analyst_target_mean,
        analyst_target_median=analyst_target_median,
        analyst_recommendation_mean=analyst_recommendation_mean,
        analyst_opinion_count=analyst_opinion_count,
    )


def _prices(
    *,
    fetched_at: datetime,
    current: float | None = 170.0,
    data_unavailable: bool = False,
) -> PriceSnapshot:
    """Minimal PriceSnapshot — just current_price; empty history is fine for valuation."""
    return PriceSnapshot(
        ticker="AAPL",
        fetched_at=fetched_at,
        source="yfinance",
        data_unavailable=data_unavailable,
        current_price=current,
        history=[],
    )


# ---------------------------------------------------------------------------
# 02-07 cross-phase dependency assertion
# ---------------------------------------------------------------------------


def test_02_07_dependency_present() -> None:
    """02-07 amendment must have shipped — analyst_target_mean field on FundamentalsSnapshot."""
    assert "analyst_target_mean" in FundamentalsSnapshot.model_fields
    assert "analyst_target_median" in FundamentalsSnapshot.model_fields
    assert "analyst_recommendation_mean" in FundamentalsSnapshot.model_fields
    assert "analyst_opinion_count" in FundamentalsSnapshot.model_fields


# ---------------------------------------------------------------------------
# Thesis-price-only path
# ---------------------------------------------------------------------------


def test_thesis_only_undervalued(make_snapshot, make_ticker_config, frozen_now) -> None:
    """thesis_price=200, current=170 → bullish; evidence shows 'thesis_price 200, current 170'."""
    from analysts.valuation import score

    snap = make_snapshot(prices=_prices(fetched_at=frozen_now, current=170.0))
    cfg = make_ticker_config(thesis_price=200.0)

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.analyst_id == "valuation"
    assert sig.data_unavailable is False
    assert sig.verdict in ("bullish", "strong_bullish")
    assert sig.confidence > 0
    evidence_str = " | ".join(sig.evidence)
    assert "thesis_price 200" in evidence_str
    assert "current 170" in evidence_str


def test_thesis_only_overvalued(make_snapshot, make_ticker_config, frozen_now) -> None:
    """thesis_price=200, current=240 → bearish; evidence shows positive gap pct."""
    from analysts.valuation import score

    snap = make_snapshot(prices=_prices(fetched_at=frozen_now, current=240.0))
    cfg = make_ticker_config(thesis_price=200.0)

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.verdict in ("bearish", "strong_bearish")
    evidence_str = " | ".join(sig.evidence)
    assert "+20.0% gap" in evidence_str or "+20%" in evidence_str


def test_thesis_only_at_target(make_snapshot, make_ticker_config, frozen_now) -> None:
    """thesis_price=200, current=200 → neutral; gap=0."""
    from analysts.valuation import score

    snap = make_snapshot(prices=_prices(fetched_at=frozen_now, current=200.0))
    cfg = make_ticker_config(thesis_price=200.0)

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.verdict == "neutral"
    evidence_str = " | ".join(sig.evidence)
    assert "+0.0%" in evidence_str or "0.0%" in evidence_str


def test_thesis_only_strong_undervalued(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """thesis_price=200, current=100 (50% below) → strong_bullish; saturated."""
    from analysts.valuation import score

    snap = make_snapshot(prices=_prices(fetched_at=frozen_now, current=100.0))
    cfg = make_ticker_config(thesis_price=200.0)

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.verdict == "strong_bullish"
    # Confidence reflects density (only 1 tier active) — should be < 100.
    assert 0 < sig.confidence < 100


# ---------------------------------------------------------------------------
# Targets-only path
# ---------------------------------------------------------------------------


def test_targets_only_pe_bullish(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """target_multiples.pe_target=20; fund.pe=15 → bullish; evidence shows P/E 15.0 vs target 20."""
    from analysts.valuation import score

    snap = make_snapshot(
        prices=_prices(fetched_at=frozen_now, current=170.0),
        fundamentals=_fund(fetched_at=frozen_now, pe=15.0),
    )
    cfg = make_ticker_config(
        target_multiples=FundamentalTargets(pe_target=20.0)
    )

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.verdict in ("bullish", "strong_bullish")
    evidence_str = " | ".join(sig.evidence)
    assert "P/E 15" in evidence_str
    assert "target 20" in evidence_str


def test_targets_only_ps_bearish(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """target_multiples.ps_target=3; fund.ps=6 → bearish."""
    from analysts.valuation import score

    snap = make_snapshot(
        prices=_prices(fetched_at=frozen_now, current=170.0),
        fundamentals=_fund(fetched_at=frozen_now, ps=6.0),
    )
    cfg = make_ticker_config(
        target_multiples=FundamentalTargets(ps_target=3.0)
    )

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.verdict in ("bearish", "strong_bearish")
    evidence_str = " | ".join(sig.evidence)
    assert "P/S 6" in evidence_str
    assert "target 3" in evidence_str


def test_targets_pe_and_ps_blend(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """pe_target=20 + ps_target=3; fund.pe=15 (bullish) + fund.ps=2 (bullish). Both contribute.

    Confidence > single-tier bullish path (more weight, density factor higher).
    """
    from analysts.valuation import score

    snap = make_snapshot(
        prices=_prices(fetched_at=frozen_now, current=170.0),
        fundamentals=_fund(fetched_at=frozen_now, pe=15.0, ps=2.0),
    )
    cfg = make_ticker_config(
        target_multiples=FundamentalTargets(pe_target=20.0, ps_target=3.0)
    )

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.verdict in ("bullish", "strong_bullish")
    evidence_str = " | ".join(sig.evidence)
    assert "P/E" in evidence_str and "P/S" in evidence_str


def test_targets_only_pb_bullish(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """pb_target=4; fund.pb=2 → bullish; evidence references pb."""
    from analysts.valuation import score

    snap = make_snapshot(
        prices=_prices(fetched_at=frozen_now, current=170.0),
        fundamentals=_fund(fetched_at=frozen_now, pb=2.0),
    )
    cfg = make_ticker_config(
        target_multiples=FundamentalTargets(pb_target=4.0)
    )

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.verdict in ("bullish", "strong_bullish")
    evidence_str = " | ".join(sig.evidence)
    assert "P/B 2" in evidence_str


# ---------------------------------------------------------------------------
# Consensus-only path (REQUIRES 02-07)
# ---------------------------------------------------------------------------


def test_consensus_only_bullish(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """analyst_target_mean=120, current=100 → bullish; evidence shows consensus 120 (n=42)."""
    from analysts.valuation import score

    snap = make_snapshot(
        prices=_prices(fetched_at=frozen_now, current=100.0),
        fundamentals=_fund(
            fetched_at=frozen_now,
            analyst_target_mean=120.0,
            analyst_opinion_count=42,
        ),
    )
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.verdict in ("bullish", "strong_bullish")
    evidence_str = " | ".join(sig.evidence)
    assert "consensus 120" in evidence_str
    assert "n=42" in evidence_str
    assert "current 100" in evidence_str


def test_consensus_only_bearish(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """analyst_target_mean=80, current=100 → bearish."""
    from analysts.valuation import score

    snap = make_snapshot(
        prices=_prices(fetched_at=frozen_now, current=100.0),
        fundamentals=_fund(
            fetched_at=frozen_now,
            analyst_target_mean=80.0,
            analyst_opinion_count=10,
        ),
    )
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.verdict in ("bearish", "strong_bearish")


def test_consensus_opinion_count_none(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """analyst_target_mean=120, analyst_opinion_count=None → evidence shows n=?."""
    from analysts.valuation import score

    snap = make_snapshot(
        prices=_prices(fetched_at=frozen_now, current=100.0),
        fundamentals=_fund(
            fetched_at=frozen_now,
            analyst_target_mean=120.0,
            analyst_opinion_count=None,
        ),
    )
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    evidence_str = " | ".join(sig.evidence)
    assert "n=?" in evidence_str


# ---------------------------------------------------------------------------
# All-three blend
# ---------------------------------------------------------------------------


def test_all_three_bullish(make_snapshot, make_ticker_config, frozen_now) -> None:
    """All three tiers bullish → bullish/strong_bullish; confidence > any single-tier-only."""
    from analysts.valuation import score

    snap = make_snapshot(
        prices=_prices(fetched_at=frozen_now, current=170.0),
        fundamentals=_fund(
            fetched_at=frozen_now,
            pe=15.0,
            analyst_target_mean=200.0,
            analyst_opinion_count=42,
        ),
    )
    cfg = make_ticker_config(
        thesis_price=200.0,
        target_multiples=FundamentalTargets(pe_target=20.0),
    )

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.verdict in ("bullish", "strong_bullish")
    # Verify all three tiers contributed evidence.
    evidence_str = " | ".join(sig.evidence)
    assert "thesis_price" in evidence_str
    assert "P/E" in evidence_str
    assert "consensus" in evidence_str


# ---------------------------------------------------------------------------
# None-configured / no-tiers UNIFORM RULE
# ---------------------------------------------------------------------------


def test_none_configured_data_unavailable(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """thesis=None + targets=None + consensus=None + current=170 → data_unavailable."""
    from analysts.valuation import score

    snap = make_snapshot(
        prices=_prices(fetched_at=frozen_now, current=170.0),
        fundamentals=_fund(fetched_at=frozen_now),  # no consensus fields
    )
    cfg = make_ticker_config()  # no thesis_price, no target_multiples

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.data_unavailable is True
    assert sig.verdict == "neutral"
    assert sig.confidence == 0
    evidence_str = " | ".join(sig.evidence)
    assert "no thesis_price" in evidence_str
    assert "no target_multiples" in evidence_str
    assert "no consensus" in evidence_str


# ---------------------------------------------------------------------------
# Empty-data UNIFORM RULE (current price gate)
# ---------------------------------------------------------------------------


def test_no_current_price(make_snapshot, make_ticker_config, frozen_now) -> None:
    """snapshot.prices=None → data_unavailable=True."""
    from analysts.valuation import score

    snap = make_snapshot(prices=None)
    cfg = make_ticker_config(thesis_price=200.0)

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.data_unavailable is True
    evidence_str = " | ".join(sig.evidence)
    assert "no current price" in evidence_str


def test_current_price_none(make_snapshot, make_ticker_config, frozen_now) -> None:
    """snapshot.prices.current_price=None → data_unavailable=True."""
    from analysts.valuation import score

    snap = make_snapshot(prices=_prices(fetched_at=frozen_now, current=None))
    cfg = make_ticker_config(thesis_price=200.0)

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.data_unavailable is True


def test_prices_data_unavailable(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """snapshot.prices.data_unavailable=True → data_unavailable=True."""
    from analysts.valuation import score

    snap = make_snapshot(
        prices=_prices(fetched_at=frozen_now, current=None, data_unavailable=True),
    )
    cfg = make_ticker_config(thesis_price=200.0)

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.data_unavailable is True


def test_snapshot_data_unavailable_true(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """snapshot.data_unavailable=True → data_unavailable=True."""
    from analysts.valuation import score

    snap = make_snapshot(data_unavailable=True)
    cfg = make_ticker_config(thesis_price=200.0)

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.data_unavailable is True


# ---------------------------------------------------------------------------
# Density-confidence invariant
# ---------------------------------------------------------------------------


def test_density_bonus_more_tiers_more_confidence(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """Same per-tier signed gap; more active tiers → higher confidence."""
    from analysts.valuation import score

    # Snapshot A: only thesis_price (1 tier).
    snap_a = make_snapshot(prices=_prices(fetched_at=frozen_now, current=170.0))
    cfg_a = make_ticker_config(thesis_price=200.0)
    sig_a = score(snap_a, cfg_a, computed_at=frozen_now)

    # Snapshot B: thesis + targets + consensus (3 tiers, all bullish on similar magnitude).
    snap_b = make_snapshot(
        prices=_prices(fetched_at=frozen_now, current=170.0),
        fundamentals=_fund(
            fetched_at=frozen_now,
            pe=17.0,  # vs target 20 → mild bullish
            analyst_target_mean=200.0,  # vs current 170 → mild bullish
            analyst_opinion_count=42,
        ),
    )
    cfg_b = make_ticker_config(
        thesis_price=200.0,
        target_multiples=FundamentalTargets(pe_target=20.0),
    )
    sig_b = score(snap_b, cfg_b, computed_at=frozen_now)

    assert sig_a.verdict in ("bullish", "strong_bullish")
    assert sig_b.verdict in ("bullish", "strong_bullish")
    # B has more active tiers → higher density → higher confidence.
    assert sig_b.confidence > sig_a.confidence


# ---------------------------------------------------------------------------
# Determinism + provenance + meta
# ---------------------------------------------------------------------------


def test_deterministic(make_snapshot, make_ticker_config, frozen_now) -> None:
    """Two calls with identical inputs → byte-identical model_dump_json."""
    from analysts.valuation import score

    snap = make_snapshot(
        prices=_prices(fetched_at=frozen_now, current=170.0),
        fundamentals=_fund(
            fetched_at=frozen_now,
            pe=15.0,
            analyst_target_mean=200.0,
            analyst_opinion_count=42,
        ),
    )
    cfg = make_ticker_config(
        thesis_price=200.0,
        target_multiples=FundamentalTargets(pe_target=20.0),
    )

    sig1 = score(snap, cfg, computed_at=frozen_now)
    sig2 = score(snap, cfg, computed_at=frozen_now)

    assert sig1.model_dump_json() == sig2.model_dump_json()


def test_computed_at_passes_through(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """Explicit computed_at preserved on returned signal."""
    from analysts.valuation import score

    snap = make_snapshot(prices=_prices(fetched_at=frozen_now, current=170.0))
    cfg = make_ticker_config(thesis_price=200.0)

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.computed_at == frozen_now


def test_provenance_header_present() -> None:
    """Provenance header references virattt source AND documents methods divergence."""
    src = Path("analysts/valuation.py").read_text(encoding="utf-8")
    assert "virattt/ai-hedge-fund/src/agents/valuation.py" in src
    assert "02-07" in src  # cross-phase dep note


def test_returns_agent_signal_type(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """score() always returns AgentSignal."""
    from analysts.valuation import score

    snap = make_snapshot(prices=_prices(fetched_at=frozen_now, current=170.0))
    cfg = make_ticker_config(thesis_price=200.0)

    sig = score(snap, cfg, computed_at=frozen_now)

    assert isinstance(sig, AgentSignal)
    assert sig.analyst_id == "valuation"
