"""Tests for analysts/fundamentals.py — pure-function deterministic scoring.

Coverage map (per 03-02-fundamentals-PLAN.md and 03-VALIDATION.md):
  * Per-config target_multiples path (P/E and P/S can be overridden)
  * Fallback band path (when target_multiples is None or per-metric target is None)
  * Per-metric isolation (one missing metric does not poison the other four)
  * Empty-data UNIFORM RULE (snapshot.data_unavailable / fundamentals=None /
    fundamentals.data_unavailable=True)
  * 5-state ladder verdict mapping (strong_bullish .. strong_bearish + neutral)
  * Provenance header presence (INFRA-07)
  * computed_at default + override behavior
  * Ticker normalization round-trip via the Snapshot field validator

Imports follow the pattern set by 03-01: shared fixtures (frozen_now,
make_snapshot, make_ticker_config) come from tests/analysts/conftest.py;
schemas are imported directly from the analysts package.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from analysts.data.fundamentals import FundamentalsSnapshot
from analysts.fundamentals import score
from analysts.schemas import FundamentalTargets, TickerConfig
from analysts.signals import AgentSignal


# ---------------------------------------------------------------------------
# Helpers — local FundamentalsSnapshot builder so each test reads cleanly.
# ---------------------------------------------------------------------------


def _fund(
    *,
    ticker: str = "AAPL",
    fetched_at: datetime | None = None,
    pe: float | None = None,
    ps: float | None = None,
    roe: float | None = None,
    debt_to_equity: float | None = None,
    profit_margin: float | None = None,
    data_unavailable: bool = False,
) -> FundamentalsSnapshot:
    """Construct a FundamentalsSnapshot with minimal kwargs for readability."""
    return FundamentalsSnapshot(
        ticker=ticker,
        fetched_at=fetched_at or datetime(2026, 5, 1, 13, 30, 0, tzinfo=timezone.utc),
        source="yfinance",
        data_unavailable=data_unavailable,
        pe=pe,
        ps=ps,
        roe=roe,
        debt_to_equity=debt_to_equity,
        profit_margin=profit_margin,
    )


# ---------------------------------------------------------------------------
# Per-config (target_multiples) path
# ---------------------------------------------------------------------------


def test_per_config_pe_bullish_undervalued(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """target_multiples.pe_target=20 + actual pe=15 → undervalued (within 80% band)."""
    cfg = make_ticker_config(
        target_multiples=FundamentalTargets(pe_target=20.0),
    )
    snap = make_snapshot(fundamentals=_fund(pe=15.0))  # P/E only — others None

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.analyst_id == "fundamentals"
    assert sig.data_unavailable is False
    # Only P/E scored (others None) → +1/5 normalized = 0.2 → boundary, neutral
    # at strict > 0.2 — but evidence string MUST mention undervalued.
    pe_evidence = [e for e in sig.evidence if "P/E" in e or "p/e" in e.lower()]
    assert len(pe_evidence) == 1
    assert "undervalued" in pe_evidence[0].lower()


def test_per_config_pe_bearish_overvalued(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """target_multiples.pe_target=20 + actual pe=30 → overvalued (>120%)."""
    cfg = make_ticker_config(
        target_multiples=FundamentalTargets(pe_target=20.0),
    )
    snap = make_snapshot(fundamentals=_fund(pe=30.0))

    sig = score(snap, cfg, computed_at=frozen_now)

    pe_evidence = [e for e in sig.evidence if "P/E" in e]
    assert len(pe_evidence) == 1
    assert "overvalued" in pe_evidence[0].lower()


def test_per_config_pe_neutral_within_band(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """target_multiples.pe_target=20 + actual pe=22 (within ±20%) → neutral."""
    cfg = make_ticker_config(
        target_multiples=FundamentalTargets(pe_target=20.0),
    )
    snap = make_snapshot(fundamentals=_fund(pe=22.0))

    sig = score(snap, cfg, computed_at=frozen_now)

    pe_evidence = [e for e in sig.evidence if "P/E" in e]
    assert len(pe_evidence) == 1
    assert "near target" in pe_evidence[0].lower()


def test_per_config_ps_bullish_undervalued(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """target_multiples.ps_target=5 + actual ps=3 → undervalued (within 80% band)."""
    cfg = make_ticker_config(
        target_multiples=FundamentalTargets(ps_target=5.0),
    )
    snap = make_snapshot(fundamentals=_fund(ps=3.0))

    sig = score(snap, cfg, computed_at=frozen_now)

    ps_evidence = [e for e in sig.evidence if "P/S" in e]
    assert len(ps_evidence) == 1
    assert "undervalued" in ps_evidence[0].lower()


def test_per_config_ps_bearish_overvalued(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """target_multiples.ps_target=5 + actual ps=8 → overvalued (>120%)."""
    cfg = make_ticker_config(
        target_multiples=FundamentalTargets(ps_target=5.0),
    )
    snap = make_snapshot(fundamentals=_fund(ps=8.0))

    sig = score(snap, cfg, computed_at=frozen_now)

    ps_evidence = [e for e in sig.evidence if "P/S" in e]
    assert len(ps_evidence) == 1
    assert "overvalued" in ps_evidence[0].lower()


def test_per_config_ps_neutral_within_band(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """target_multiples.ps_target=5 + actual ps=5.5 (within ±20%) → near target."""
    cfg = make_ticker_config(
        target_multiples=FundamentalTargets(ps_target=5.0),
    )
    snap = make_snapshot(fundamentals=_fund(ps=5.5))

    sig = score(snap, cfg, computed_at=frozen_now)

    ps_evidence = [e for e in sig.evidence if "P/S" in e]
    assert len(ps_evidence) == 1
    assert "near target" in ps_evidence[0].lower()


# ---------------------------------------------------------------------------
# Fallback path (no target_multiples set, or target is None for that metric)
# ---------------------------------------------------------------------------


def test_fallback_pe_bullish(make_snapshot, make_ticker_config, frozen_now) -> None:
    """No target_multiples + pe=12 → fallback bullish band (<15)."""
    cfg = make_ticker_config()  # target_multiples=None
    snap = make_snapshot(fundamentals=_fund(pe=12.0))

    sig = score(snap, cfg, computed_at=frozen_now)

    pe_evidence = [e for e in sig.evidence if "P/E" in e]
    assert len(pe_evidence) == 1
    assert "below 15" in pe_evidence[0].lower() or "bullish band" in pe_evidence[0].lower()


def test_fallback_pe_bearish(make_snapshot, make_ticker_config, frozen_now) -> None:
    """No target_multiples + pe=35 → fallback bearish band (>30)."""
    cfg = make_ticker_config()
    snap = make_snapshot(fundamentals=_fund(pe=35.0))

    sig = score(snap, cfg, computed_at=frozen_now)

    pe_evidence = [e for e in sig.evidence if "P/E" in e]
    assert len(pe_evidence) == 1
    assert "above 30" in pe_evidence[0].lower() or "bearish band" in pe_evidence[0].lower()


def test_fallback_pe_neutral(make_snapshot, make_ticker_config, frozen_now) -> None:
    """No target_multiples + pe=22 (15..30) → fallback neutral band."""
    cfg = make_ticker_config()
    snap = make_snapshot(fundamentals=_fund(pe=22.0))

    sig = score(snap, cfg, computed_at=frozen_now)

    pe_evidence = [e for e in sig.evidence if "P/E" in e]
    assert len(pe_evidence) == 1
    assert "neutral band" in pe_evidence[0].lower()


def test_fallback_path_when_only_ps_target_set(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """target_multiples set but pe_target=None → P/E goes through fallback path."""
    cfg = make_ticker_config(
        target_multiples=FundamentalTargets(ps_target=5.0),  # pe_target intentionally None
    )
    snap = make_snapshot(fundamentals=_fund(pe=12.0))  # would be bullish on fallback

    sig = score(snap, cfg, computed_at=frozen_now)

    pe_evidence = [e for e in sig.evidence if "P/E" in e]
    assert len(pe_evidence) == 1
    # Must use the fallback band wording (not "vs target" wording)
    assert "vs target" not in pe_evidence[0].lower()
    assert "below 15" in pe_evidence[0].lower() or "bullish band" in pe_evidence[0].lower()


# ---------------------------------------------------------------------------
# Per-metric isolation
# ---------------------------------------------------------------------------


def test_per_metric_isolation_pe_missing(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """pe=None + 4 other bullish metrics → score still works on the other 4."""
    cfg = make_ticker_config()  # all fallback bands
    snap = make_snapshot(
        fundamentals=_fund(
            pe=None,
            ps=1.5,                # bullish (<2)
            roe=0.20,              # bullish (>0.15)
            debt_to_equity=0.3,    # bullish (<0.5)
            profit_margin=0.18,    # bullish (>0.15)
        )
    )

    sig = score(snap, cfg, computed_at=frozen_now)

    # No "P/E" evidence string should be emitted when pe is None.
    pe_evidence = [e for e in sig.evidence if "P/E" in e]
    assert len(pe_evidence) == 0
    # Other 4 metrics should be present in evidence.
    metric_names = ["P/S", "ROE", "debt/equity", "profit margin"]
    for name in metric_names:
        matches = [e for e in sig.evidence if name.lower() in e.lower()]
        assert len(matches) >= 1, f"expected evidence for {name}, got {sig.evidence!r}"
    # 4/5 bullish → normalized = 0.8 → strong_bullish
    assert sig.verdict == "strong_bullish"
    assert sig.confidence == 80


def test_per_metric_isolation_all_missing(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """All 5 metrics None + data_unavailable=False → defensive data_unavailable signal."""
    cfg = make_ticker_config()
    snap = make_snapshot(
        fundamentals=_fund(
            pe=None, ps=None, roe=None, debt_to_equity=None, profit_margin=None,
            data_unavailable=False,
        )
    )

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.data_unavailable is True
    assert sig.verdict == "neutral"
    assert sig.confidence == 0
    assert len(sig.evidence) == 1
    assert "all 5" in sig.evidence[0].lower() or "all five" in sig.evidence[0].lower()


# ---------------------------------------------------------------------------
# Empty-data UNIFORM RULE — three branches
# ---------------------------------------------------------------------------


def test_empty_data_snapshot_data_unavailable_true(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """snapshot.data_unavailable=True → data_unavailable signal even if fundamentals would otherwise score."""
    cfg = make_ticker_config()
    snap = make_snapshot(
        data_unavailable=True,
        fundamentals=_fund(pe=12.0),  # would be bullish but ignored
    )

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.data_unavailable is True
    assert sig.verdict == "neutral"
    assert sig.confidence == 0
    assert len(sig.evidence) == 1


def test_empty_data_fundamentals_none(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """snapshot.fundamentals=None → data_unavailable signal."""
    cfg = make_ticker_config()
    snap = make_snapshot(fundamentals=None)

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.data_unavailable is True
    assert sig.verdict == "neutral"
    assert sig.confidence == 0
    assert len(sig.evidence) == 1


def test_empty_data_fundamentals_data_unavailable_true(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """snapshot.fundamentals.data_unavailable=True → data_unavailable signal."""
    cfg = make_ticker_config()
    snap = make_snapshot(fundamentals=_fund(data_unavailable=True))

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.data_unavailable is True
    assert sig.verdict == "neutral"
    assert sig.confidence == 0
    assert len(sig.evidence) == 1


# ---------------------------------------------------------------------------
# 5-state ladder mapping
# ---------------------------------------------------------------------------


def test_5_state_ladder_strong_bullish(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """All 5 metrics maxed bullish → strong_bullish, confidence=100."""
    cfg = make_ticker_config()
    snap = make_snapshot(
        fundamentals=_fund(
            pe=10.0, ps=1.0, roe=0.30, debt_to_equity=0.1, profit_margin=0.30,
        )
    )

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.verdict == "strong_bullish"
    assert sig.confidence == 100
    assert len(sig.evidence) == 5


def test_5_state_ladder_strong_bearish(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """All 5 metrics maxed bearish → strong_bearish, confidence=100."""
    cfg = make_ticker_config()
    snap = make_snapshot(
        fundamentals=_fund(
            pe=40.0, ps=10.0, roe=0.02, debt_to_equity=2.0, profit_margin=0.02,
        )
    )

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.verdict == "strong_bearish"
    assert sig.confidence == 100
    assert len(sig.evidence) == 5


def test_5_state_ladder_neutral(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """All 5 metrics in neutral band → neutral, confidence=0."""
    cfg = make_ticker_config()
    snap = make_snapshot(
        fundamentals=_fund(
            pe=22.0, ps=5.0, roe=0.10, debt_to_equity=1.0, profit_margin=0.10,
        )
    )

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.verdict == "neutral"
    assert sig.confidence == 0
    assert len(sig.evidence) == 5  # neutral evidence still emitted


def test_5_state_ladder_bullish_partial(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """3 bullish + 2 neutral → total=3, normalized=0.6 (boundary, NOT strong_bullish)."""
    cfg = make_ticker_config()
    snap = make_snapshot(
        fundamentals=_fund(
            pe=10.0,                # bullish (+1)
            ps=1.0,                 # bullish (+1)
            roe=0.30,               # bullish (+1)
            debt_to_equity=1.0,     # neutral
            profit_margin=0.10,     # neutral
        )
    )

    sig = score(snap, cfg, computed_at=frozen_now)

    # normalized = 3/5 = 0.6 → strict > 0.6 needed for strong_bullish, so bullish.
    assert sig.verdict == "bullish"
    assert sig.confidence == 60


def test_5_state_ladder_bearish_partial(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """2 bearish + 3 neutral → total=-2, normalized=-0.4 → bearish."""
    cfg = make_ticker_config()
    snap = make_snapshot(
        fundamentals=_fund(
            pe=40.0,                # bearish (-1)
            ps=10.0,                # bearish (-1)
            roe=0.10,               # neutral
            debt_to_equity=1.0,     # neutral
            profit_margin=0.10,     # neutral
        )
    )

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.verdict == "bearish"
    assert sig.confidence == 40


# ---------------------------------------------------------------------------
# Provenance + meta-tests
# ---------------------------------------------------------------------------


def test_provenance_header_present() -> None:
    """analysts/fundamentals.py must reference the virattt source per INFRA-07."""
    src = Path("analysts/fundamentals.py").read_text(encoding="utf-8")
    assert "virattt/ai-hedge-fund/src/agents/fundamentals.py" in src


def test_computed_at_passes_through(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """Explicit computed_at is preserved on the returned signal."""
    cfg = make_ticker_config()
    snap = make_snapshot(fundamentals=_fund(pe=22.0))

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.computed_at == frozen_now


def test_computed_at_default_uses_now(
    make_snapshot, make_ticker_config
) -> None:
    """Without explicit computed_at, default is approximately datetime.now(UTC)."""
    cfg = make_ticker_config()
    snap = make_snapshot(fundamentals=_fund(pe=22.0))

    before = datetime.now(timezone.utc)
    sig = score(snap, cfg)
    after = datetime.now(timezone.utc)

    assert before <= sig.computed_at <= after


def test_ticker_normalized_in_signal(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """Snapshot ticker 'brk.b' (lowercase + dot) → signal.ticker == 'BRK-B' via AgentSignal normalizer."""
    cfg = make_ticker_config(ticker="brk.b")
    snap = make_snapshot(
        ticker="brk.b",
        fundamentals=_fund(ticker="brk.b", pe=22.0),
    )

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.ticker == "BRK-B"


def test_returns_agent_signal_type(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """score() always returns an AgentSignal — never None, never raises for missing data."""
    cfg = make_ticker_config()
    snap = make_snapshot(fundamentals=_fund(pe=22.0))

    sig = score(snap, cfg, computed_at=frozen_now)

    assert isinstance(sig, AgentSignal)
    assert sig.analyst_id == "fundamentals"


def test_determinism_two_calls_identical(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """Two calls with identical (snapshot, config, computed_at) → identical AgentSignal."""
    cfg = make_ticker_config()
    snap = make_snapshot(
        fundamentals=_fund(
            pe=12.0, ps=1.5, roe=0.20, debt_to_equity=0.3, profit_margin=0.18,
        )
    )

    sig1 = score(snap, cfg, computed_at=frozen_now)
    sig2 = score(snap, cfg, computed_at=frozen_now)

    assert sig1.model_dump() == sig2.model_dump()
