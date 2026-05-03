"""Fundamentals analyst — pure-function deterministic scoring.

Adapted from virattt/ai-hedge-fund/src/agents/fundamentals.py
(https://github.com/virattt/ai-hedge-fund/blob/main/src/agents/fundamentals.py).

Modifications from the reference implementation:
  * Five-metric scoring (P/E, P/S, ROE, debt/equity, profit_margin) instead
    of the reference's 13-metric grid — matches the fields we actually carry
    in analysts.data.fundamentals.FundamentalsSnapshot.
  * Per-`TickerConfig.target_multiples` overrides on P/E and P/S (when set)
    take precedence over the hard-coded fallback bands. ROE / debt-to-equity
    / profit-margin always use module-level constants because the
    FundamentalTargets schema does not carry roe_target / de_target /
    pm_target — adding those is a v1.x scope decision.
  * Module-level threshold constants at the top of the file (PE_BULLISH_BELOW
    etc.) are tunable by editing this file; no central thresholds module,
    no TOML config — explicit YAGNI for v1 single-user (per 03-CONTEXT.md
    "Threshold Configuration").
  * 5-state Verdict (strong_bullish | bullish | neutral | bearish |
    strong_bearish) instead of the reference's 3-state — matches the
    AgentSignal contract locked in 03-01.
  * Pure function `score(snapshot, config, *, computed_at=None) -> AgentSignal`
    replaces the reference's graph-node `ainvoke` — no I/O, no global state,
    no LangGraph dependency. Two calls with identical inputs produce
    identical signals (modulo computed_at when defaulted).
  * Empty-data UNIFORM RULE guard at the top: if any of
    `snapshot.data_unavailable`, `snapshot.fundamentals is None`, or
    `snapshot.fundamentals.data_unavailable` is true, return the canonical
    `data_unavailable=True` signal (verdict='neutral', confidence=0)
    immediately — closes 03-CONTEXT.md "Empty / Partial Data Handling".
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from analysts._indicator_math import _total_to_verdict
from analysts.data.snapshot import Snapshot
from analysts.schemas import TickerConfig
from analysts.signals import AgentSignal, Verdict

# ---------------------------------------------------------------------------
# Threshold constants — tunable by editing this file. Defaults from
# 03-CONTEXT.md "Threshold Defaults". ROE / profit_margin are decimals
# (0.15 == 15%), matching how yfinance reports them in
# FundamentalsSnapshot.
# ---------------------------------------------------------------------------

PE_BULLISH_BELOW: float = 15.0
PE_BEARISH_ABOVE: float = 30.0

PS_BULLISH_BELOW: float = 2.0
PS_BEARISH_ABOVE: float = 8.0

ROE_BULLISH_ABOVE: float = 0.15
ROE_BEARISH_BELOW: float = 0.05

DE_BULLISH_BELOW: float = 0.5
DE_BEARISH_ABOVE: float = 1.5

PM_BULLISH_ABOVE: float = 0.15
PM_BEARISH_BELOW: float = 0.05

# Per-config band: when target_multiples.pe_target (or ps_target) is set, an
# observed value within ±20% of the target is "near target" (score 0); below
# 80% of target is "undervalued" (+1); above 120% of target is "overvalued"
# (-1). Symmetric around the user's stated target.
PER_CONFIG_BAND: float = 0.20

# Aggregation: max possible total score is len(metrics) (5 here), one +1 per
# bullish metric. Normalize total to [-1, +1] by dividing by this constant.
_MAX_POSSIBLE_SCORE: int = 5


# ---------------------------------------------------------------------------
# Per-metric helpers — each returns (score, evidence) where:
#   score in {-1, 0, +1}  — the metric's contribution to the aggregate
#   evidence in (str | None) — the line for the AgentSignal.evidence list,
#       or None when the input was None (metric not readable).
# When evidence is None, the metric is treated as missing for n_scored
# accounting; when evidence is a string, the metric was readable (and
# scored 0 if neutral, +/-1 if directional).
# ---------------------------------------------------------------------------


def _score_pe(pe: Optional[float], target: Optional[float]) -> tuple[int, Optional[str]]:
    if pe is None:
        return 0, None
    if target is not None:
        lower = target * (1 - PER_CONFIG_BAND)
        upper = target * (1 + PER_CONFIG_BAND)
        if pe < lower:
            pct = (1 - pe / target) * 100
            return +1, f"P/E {pe:.1f} vs target {target:.0f} — undervalued by {pct:.0f}%"
        if pe > upper:
            pct = (pe / target - 1) * 100
            return -1, f"P/E {pe:.1f} vs target {target:.0f} — overvalued by {pct:.0f}%"
        return 0, f"P/E {pe:.1f} near target {target:.0f}"
    # Fallback bands (target was None — either target_multiples=None or
    # pe_target=None inside FundamentalTargets).
    if pe < PE_BULLISH_BELOW:
        return +1, f"P/E {pe:.1f} (below {PE_BULLISH_BELOW:.0f} bullish band)"
    if pe > PE_BEARISH_ABOVE:
        return -1, f"P/E {pe:.1f} (above {PE_BEARISH_ABOVE:.0f} bearish band)"
    return 0, f"P/E {pe:.1f} (neutral band)"


def _score_ps(ps: Optional[float], target: Optional[float]) -> tuple[int, Optional[str]]:
    if ps is None:
        return 0, None
    if target is not None:
        lower = target * (1 - PER_CONFIG_BAND)
        upper = target * (1 + PER_CONFIG_BAND)
        if ps < lower:
            pct = (1 - ps / target) * 100
            return +1, f"P/S {ps:.1f} vs target {target:.0f} — undervalued by {pct:.0f}%"
        if ps > upper:
            pct = (ps / target - 1) * 100
            return -1, f"P/S {ps:.1f} vs target {target:.0f} — overvalued by {pct:.0f}%"
        return 0, f"P/S {ps:.1f} near target {target:.0f}"
    if ps < PS_BULLISH_BELOW:
        return +1, f"P/S {ps:.1f} (below {PS_BULLISH_BELOW:.0f} bullish band)"
    if ps > PS_BEARISH_ABOVE:
        return -1, f"P/S {ps:.1f} (above {PS_BEARISH_ABOVE:.0f} bearish band)"
    return 0, f"P/S {ps:.1f} (neutral band)"


def _score_roe(roe: Optional[float]) -> tuple[int, Optional[str]]:
    if roe is None:
        return 0, None
    if roe > ROE_BULLISH_ABOVE:
        return +1, (
            f"ROE {roe * 100:.1f}% (above {ROE_BULLISH_ABOVE * 100:.0f}% bullish band)"
        )
    if roe < ROE_BEARISH_BELOW:
        return -1, (
            f"ROE {roe * 100:.1f}% (below {ROE_BEARISH_BELOW * 100:.0f}% bearish band)"
        )
    return 0, f"ROE {roe * 100:.1f}% (neutral band)"


def _score_de(de: Optional[float]) -> tuple[int, Optional[str]]:
    if de is None:
        return 0, None
    if de < DE_BULLISH_BELOW:
        return +1, (
            f"debt/equity {de:.2f} (below {DE_BULLISH_BELOW:.1f} bullish band)"
        )
    if de > DE_BEARISH_ABOVE:
        return -1, (
            f"debt/equity {de:.2f} (above {DE_BEARISH_ABOVE:.1f} bearish band)"
        )
    return 0, f"debt/equity {de:.2f} (neutral band)"


def _score_pm(pm: Optional[float]) -> tuple[int, Optional[str]]:
    if pm is None:
        return 0, None
    if pm > PM_BULLISH_ABOVE:
        return +1, (
            f"profit margin {pm * 100:.1f}% "
            f"(above {PM_BULLISH_ABOVE * 100:.0f}% bullish band)"
        )
    if pm < PM_BEARISH_BELOW:
        return -1, (
            f"profit margin {pm * 100:.1f}% "
            f"(below {PM_BEARISH_BELOW * 100:.0f}% bearish band)"
        )
    return 0, f"profit margin {pm * 100:.1f}% (neutral band)"


# ---------------------------------------------------------------------------
# Public scoring function
# ---------------------------------------------------------------------------


def score(
    snapshot: Snapshot,
    config: TickerConfig,
    *,
    computed_at: Optional[datetime] = None,
) -> AgentSignal:
    """Score fundamentals deterministically; pure function; never raises for missing data.

    Parameters
    ----------
    snapshot : Snapshot
        Per-ticker aggregate snapshot from the ingestion phase. The fundamentals
        sub-field (snapshot.fundamentals) is read for the five scored metrics.
    config : TickerConfig
        Per-ticker configuration. config.target_multiples (when set) provides
        per-config overrides for P/E and P/S; ROE / debt-to-equity / profit
        margin always score against the module-level fallback constants.
    computed_at : datetime, optional
        UTC timestamp to stamp on the returned signal. Defaults to
        datetime.now(timezone.utc) — pin explicitly in tests for reproducible
        output.

    Returns
    -------
    AgentSignal
        Always non-None; analyst_id='fundamentals'. Never raises for missing
        data — empty / partial inputs produce the canonical
        data_unavailable=True signal per the UNIFORM RULE.
    """
    now = computed_at if computed_at is not None else datetime.now(timezone.utc)

    # UNIFORM RULE empty-data guard — three branches, all collapse to the
    # canonical data_unavailable signal. Order of branches doesn't matter
    # since they short-circuit independently; we check snapshot-level first
    # because it's the most common "this ticker is dark today" signal from
    # the orchestrator.
    if snapshot.data_unavailable:
        return AgentSignal(
            ticker=snapshot.ticker,
            analyst_id="fundamentals",
            computed_at=now,
            data_unavailable=True,
            evidence=["snapshot data_unavailable=True"],
        )
    if snapshot.fundamentals is None:
        return AgentSignal(
            ticker=snapshot.ticker,
            analyst_id="fundamentals",
            computed_at=now,
            data_unavailable=True,
            evidence=["fundamentals snapshot missing"],
        )
    if snapshot.fundamentals.data_unavailable:
        return AgentSignal(
            ticker=snapshot.ticker,
            analyst_id="fundamentals",
            computed_at=now,
            data_unavailable=True,
            evidence=["fundamentals.data_unavailable=True"],
        )

    fund = snapshot.fundamentals
    targets = config.target_multiples  # Optional[FundamentalTargets]
    pe_target = targets.pe_target if targets is not None else None
    ps_target = targets.ps_target if targets is not None else None

    # Score each metric individually. Per-metric isolation: a None input on
    # any metric contributes 0 to the aggregate AND emits no evidence
    # string, but does not affect the other four metrics.
    sub: list[tuple[int, Optional[str]]] = [
        _score_pe(fund.pe, pe_target),
        _score_ps(fund.ps, ps_target),
        _score_roe(fund.roe),
        _score_de(fund.debt_to_equity),
        _score_pm(fund.profit_margin),
    ]

    # n_scored counts metrics where the input was non-None (evidence is set).
    # When all five metrics are None despite snapshot.fundamentals being
    # data_unavailable=False, the upstream is in a defensive bad state —
    # collapse to the data_unavailable signal with an explicit reason.
    n_scored = sum(1 for _s, e in sub if e is not None)
    if n_scored == 0:
        return AgentSignal(
            ticker=snapshot.ticker,
            analyst_id="fundamentals",
            computed_at=now,
            data_unavailable=True,
            evidence=["all 5 fundamentals metrics missing"],
        )

    total = sum(s for s, _e in sub)
    # Normalize against the MAX POSSIBLE score across all 5 metrics (not
    # against n_scored). This means a single bullish metric out of 5 (with
    # 4 missing) does not get amplified into a strong verdict — partial-data
    # signals are deliberately damped, matching the per-metric isolation
    # contract.
    normalized = total / _MAX_POSSIBLE_SCORE
    verdict = _total_to_verdict(normalized)
    confidence = min(100, int(round(abs(normalized) * 100)))
    evidence = [e for _s, e in sub if e is not None]

    return AgentSignal(
        ticker=snapshot.ticker,
        analyst_id="fundamentals",
        computed_at=now,
        verdict=verdict,
        confidence=confidence,
        evidence=evidence,
    )
