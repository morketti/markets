"""Valuation analyst — pure-function deterministic 3-tier blended scoring.

Adapted from virattt/ai-hedge-fund/src/agents/valuation.py
(https://github.com/virattt/ai-hedge-fund/blob/main/src/agents/valuation.py).

Modifications from the reference implementation:

  * Multi-method weighted aggregation pattern adopted (when a method's value
    is missing or ≤ 0, exclude it from weights and recompute total_weight
    from the remaining methods). This shape carries over verbatim.
  * Methods diverge — virattt uses DCF + Owner Earnings + EV/EBITDA +
    Residual Income (all derived from financials). We use:
      Tier 1 — config.thesis_price (weight W_THESIS = 1.0): user's locked
      thesis price; the highest-trust anchor because it encodes
      domain-specific work the user did themselves.
      Tier 2 — config.target_multiples.{pe_target, ps_target, pb_target}
      (weight W_TARGETS = 0.7 per multiple): user's per-ticker P/E / P/S /
      P/B targets compared against the snapshot's matching FundamentalsSnapshot
      field. Each multiple set + matching-fundamental-present yields one
      sub-signal.
      Tier 3 — snapshot.fundamentals.analyst_target_mean (weight
      W_CONSENSUS = 0.5): yfinance sell-side mean target. Lower trust
      because consensus drift is a known anchoring artifact, but useful
      tertiary blend per 03-CONTEXT.md scoring philosophy.
  * Pure function `score(snapshot, config, *, computed_at=None) -> AgentSignal`
    replaces the reference's graph-node ainvoke. No I/O, no global state,
    no LangGraph dep.
  * Empty-data UNIFORM RULE: snapshot.data_unavailable=True OR
    snapshot.prices is None OR snapshot.prices.data_unavailable=True OR
    snapshot.prices.current_price is None or ≤ 0 → AgentSignal(
    data_unavailable=True, evidence=["no current price"]).
  * None-configured UNIFORM RULE: when ALL three tiers are absent
    (thesis_price=None, target_multiples=None or empty, no consensus
    target) → AgentSignal(data_unavailable=True, evidence=
    ["no thesis_price, no target_multiples, no consensus"]).
  * Density-weighted confidence: more active tiers → higher confidence.
    `density = min(1.0, total_w / 2.2)`. Saturates at 1.0 when 2+ tiers
    are active with multiple multiples; ~0.45 when only thesis_price set.

CROSS-PHASE DEPENDENCY — Plan 02-07 is a hard prerequisite. This module
reads `snapshot.fundamentals.analyst_target_mean` directly (not via
getattr-defensive); without 02-07 having shipped the four
analyst-consensus fields on FundamentalsSnapshot
(analyst_target_mean / analyst_target_median /
analyst_recommendation_mean / analyst_opinion_count), this module
fails at attribute access. This is intentional — fail loudly if a
future change reverts 02-07 rather than silently degrading the Tier 3
contribution to None.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from analysts._indicator_math import _total_to_verdict
from analysts.data.snapshot import Snapshot
from analysts.schemas import TickerConfig
from analysts.signals import AgentSignal, Verdict

# ---------------------------------------------------------------------------
# Tier weights — see 03-CONTEXT.md scoring philosophy.
# ---------------------------------------------------------------------------

W_THESIS: float = 1.0
W_TARGETS: float = 0.7
W_CONSENSUS: float = 0.5

# Gap saturation: a 50% premium clips the sub-signal at -1.0; a 50% discount
# clips at +1.0. Linear in between. Tunable; tests pin the formula.
GAP_SATURATION: float = 0.5

# Density factor saturation point. With all three tiers maxed (thesis +
# 3 multiples + consensus), max total_w = 1.0 + 0.7*3 + 0.5 = 3.6.
# Dividing by 2.2 saturates near 1.0 when 2+ tiers active with multiple
# multiples; ~0.45 when only thesis_price set.
DENSITY_SATURATION: float = 2.2


# ---------------------------------------------------------------------------
# Per-tier helpers
# ---------------------------------------------------------------------------


def _signed_gap(anchor: float, current: float) -> float:
    """Signed gap in [-1, +1]: positive = current below anchor (bullish).

    `anchor=200, current=170` → delta = -0.15 (15% below) → signal = +0.30.
    Clipped to ±1 at GAP_SATURATION (50% premium / 50% discount).
    """
    delta = (current - anchor) / anchor
    s = -delta / GAP_SATURATION
    return max(-1.0, min(1.0, s))


# ---------------------------------------------------------------------------
# Public scoring function
# ---------------------------------------------------------------------------


def score(
    snapshot: Snapshot,
    config: TickerConfig,
    *,
    computed_at: Optional[datetime] = None,
) -> AgentSignal:
    """Score valuation deterministically. Three-tier blend with explicit precedence.

    Tier 1 (weight 1.0): config.thesis_price vs snapshot.prices.current_price.
    Tier 2 (weight 0.7 each): config.target_multiples.{pe,ps,pb}_target vs
        snapshot.fundamentals.{pe,ps,pb}.
    Tier 3 (weight 0.5): snapshot.fundamentals.analyst_target_mean vs
        snapshot.prices.current_price (REQUIRES 02-07).

    Empty-data UNIFORM RULE: no current price OR no tier configured/available
    → AgentSignal(data_unavailable=True, ...). Otherwise → 5-state verdict
    from weighted aggregate, density-weighted confidence, evidence list.

    Pure function; never raises for missing data.
    """
    now = computed_at if computed_at is not None else datetime.now(timezone.utc)

    # Empty-data UNIFORM RULE — current price is the universal anchor.
    if (
        snapshot.data_unavailable
        or snapshot.prices is None
        or snapshot.prices.data_unavailable
        or snapshot.prices.current_price is None
        or snapshot.prices.current_price <= 0
    ):
        return AgentSignal(
            ticker=snapshot.ticker,
            analyst_id="valuation",
            computed_at=now,
            data_unavailable=True,
            evidence=["no current price"],
        )

    current = snapshot.prices.current_price
    fund = snapshot.fundamentals  # may be None or data_unavailable=True

    # Each sub-signal: (signal in [-1, +1], weight, evidence_str). Collected
    # then aggregated.
    sub: list[tuple[float, float, str]] = []

    # Tier 1 — thesis_price (weight W_THESIS = 1.0).
    if config.thesis_price is not None and config.thesis_price > 0:
        s = _signed_gap(config.thesis_price, current)
        gap_pct = (current - config.thesis_price) / config.thesis_price * 100
        sub.append(
            (
                s,
                W_THESIS,
                f"thesis_price {config.thesis_price:.0f}, "
                f"current {current:.0f} — {gap_pct:+.1f}% gap",
            )
        )

    # Tier 2 — target_multiples.{pe,ps,pb}_target vs snapshot.fundamentals
    # (weight W_TARGETS = 0.7 per multiple).
    targets = config.target_multiples
    if targets is not None and fund is not None and not fund.data_unavailable:
        if (
            targets.pe_target is not None
            and fund.pe is not None
            and targets.pe_target > 0
        ):
            s = _signed_gap(targets.pe_target, fund.pe)
            sub.append(
                (
                    s,
                    W_TARGETS,
                    f"P/E {fund.pe:.1f} vs target {targets.pe_target:.0f}",
                )
            )
        if (
            targets.ps_target is not None
            and fund.ps is not None
            and targets.ps_target > 0
        ):
            s = _signed_gap(targets.ps_target, fund.ps)
            sub.append(
                (
                    s,
                    W_TARGETS,
                    f"P/S {fund.ps:.1f} vs target {targets.ps_target:.0f}",
                )
            )
        if (
            targets.pb_target is not None
            and fund.pb is not None
            and targets.pb_target > 0
        ):
            s = _signed_gap(targets.pb_target, fund.pb)
            sub.append(
                (
                    s,
                    W_TARGETS,
                    f"P/B {fund.pb:.1f} vs target {targets.pb_target:.0f}",
                )
            )

    # Tier 3 — yfinance analyst consensus (weight W_CONSENSUS = 0.5).
    # REQUIRES 02-07: reads fund.analyst_target_mean and fund.analyst_opinion_count.
    if (
        fund is not None
        and not fund.data_unavailable
        and fund.analyst_target_mean is not None
        and fund.analyst_target_mean > 0
    ):
        s = _signed_gap(fund.analyst_target_mean, current)
        gap_pct = (current - fund.analyst_target_mean) / fund.analyst_target_mean * 100
        n = fund.analyst_opinion_count
        n_str = f"n={n}" if n else "n=?"
        sub.append(
            (
                s,
                W_CONSENSUS,
                f"analyst consensus {fund.analyst_target_mean:.0f} ({n_str}), "
                f"current {current:.0f} — {gap_pct:+.1f}% gap",
            )
        )

    # None-configured UNIFORM RULE.
    if not sub:
        return AgentSignal(
            ticker=snapshot.ticker,
            analyst_id="valuation",
            computed_at=now,
            data_unavailable=True,
            evidence=["no thesis_price, no target_multiples, no consensus"],
        )

    # Aggregate. total_w is the sum of active weights; aggregate is the
    # weight-weighted average of the per-tier signals in [-1, +1].
    total_w = sum(w for _, w, _ in sub)
    aggregate = sum(s * w for s, w, _ in sub) / total_w

    verdict = _total_to_verdict(aggregate)
    # Density factor — more active tiers → higher confidence. Saturates
    # near 1.0 when 2+ tiers active with multiple multiples.
    density = min(1.0, total_w / DENSITY_SATURATION)
    confidence = min(100, int(round(abs(aggregate) * 100 * density)))

    evidence = [e for _, _, e in sub][:10]

    return AgentSignal(
        ticker=snapshot.ticker,
        analyst_id="valuation",
        computed_at=now,
        verdict=verdict,
        confidence=confidence,
        evidence=evidence,
    )
