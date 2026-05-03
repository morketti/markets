"""News/sentiment analyst — pure-function deterministic VADER scoring.

Adapted from virattt/ai-hedge-fund/src/agents/news_sentiment.py
(https://github.com/virattt/ai-hedge-fund/blob/main/src/agents/news_sentiment.py).

Modifications from the reference implementation (almost a complete divergence —
provenance comment is "structural pattern adapted from … with full
sentiment-classifier substitution"):

  * virattt classifies sentiment via call_llm() (non-deterministic, paid,
    incompatible with our keyless / lite-mode constraint per INFRA-02).
    We use VADER (vaderSentiment >= 3.3) — deterministic, free, no LLM.
  * virattt has NO recency weighting; we add an exponential decay with a
    3-day half-life (`DECAY_K = math.log(2.0) / 3.0 ≈ 0.231`) per
    03-CONTEXT.md scoring philosophy. A 10-day-old headline contributes
    only ~10% of a fresh one's weight; past 14 days the weight is < 4%
    and we drop the headline entirely (noise floor).
  * virattt has NO source-credibility weighting; we weight yahoo-rss /
    google-news at 1.0 and finviz at 0.7 (finviz scrapes are noisier and
    sometimes pick up press-release flak). press-wires=0.5 is included
    in SOURCE_WEIGHTS as forward-compat dead code — Headline.source
    Literal does not currently include "press-wires" (see 03-RESEARCH.md
    Pitfall #6); this entry will activate when ingestion/news.py adds
    press-wires support in a future plan, with no analyst-side change.
  * Pure function `score(snapshot, config, *, computed_at=None) -> AgentSignal`
    replaces the reference's graph-node `ainvoke`. No I/O, no global
    state mutation outside the lazy VADER singleton, no LangGraph dep.
  * Empty-data UNIFORM RULE guard: snapshot.data_unavailable=True OR
    snapshot.news=[] OR all-headlines-filtered → canonical
    AgentSignal(data_unavailable=True, ...) with distinct evidence
    reason per branch.
  * Lazy VADER init via module-level `_VADER = None` + `_vader()`
    accessor (lazy import + lazy construction) — keeps schema-only test
    runs (e.g. tests/analysts/test_signals.py) from paying VADER's
    import cost.
  * Determinism: `now` is read ONCE at the top of `score()`. Helpers
    (`_score_one`, `_aggregate`) accept `now` as a parameter and never
    call `datetime.now()` themselves (per 03-RESEARCH.md Pitfall #7).

VADER-on-financial-text caveat: VADER's published accuracy on financial
headlines is ~55-68% vs FinBERT's ~85% (03-RESEARCH.md Pitfall #2).
VADER is locked for v1 by 03-CONTEXT.md per the keyless / lite-mode
constraint. FinVADER and Loughran-McDonald are tracked in 03-CONTEXT.md
deferred ideas for v1.x — a future maintainer reading this should not
think we forgot to swap classifiers.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional

from analysts.data.news import Headline
from analysts.data.snapshot import Snapshot
from analysts.schemas import TickerConfig
from analysts.signals import AgentSignal, Verdict

# ---------------------------------------------------------------------------
# Lazy VADER singleton — first call constructs the analyzer; subsequent calls
# reuse. The lazy import keeps schema-only test runs (e.g. test_signals.py)
# from paying VADER's import cost.
# ---------------------------------------------------------------------------

_VADER = None


def _vader():
    """Return the module-level SentimentIntensityAnalyzer, constructing on first call."""
    global _VADER
    if _VADER is None:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        _VADER = SentimentIntensityAnalyzer()
    return _VADER


# ---------------------------------------------------------------------------
# Module-level constants — tunable by editing this file. Values from
# 03-CONTEXT.md "Threshold Defaults" + 03-RESEARCH.md Pattern 5.
# ---------------------------------------------------------------------------

# Recency decay: 3-day half-life — a 3-day-old headline contributes 50%, a
# 6-day-old one contributes 25%, a 14-day-old one < 4% (below the noise
# floor and dropped entirely).
NEWS_HALFLIFE_DAYS: float = 3.0
DECAY_K: float = math.log(2.0) / NEWS_HALFLIFE_DAYS  # ≈ 0.231

# Source-credibility weights. yahoo-rss + google-news are first-tier
# (publisher-curated); finviz scrapes are noisier and sometimes pick up
# press-release flak. press-wires=0.5 is forward-compat dead code per
# Pitfall #6 — Headline.source Literal does not currently include it,
# so this entry never fires in v1; it activates when ingestion/news.py
# adds press-wires support in a future plan.
SOURCE_WEIGHTS: dict[str, float] = {
    "yahoo-rss": 1.0,
    "google-news": 1.0,
    "finviz": 0.7,
    "press-wires": 0.5,  # forward-compat dead code — see 03-RESEARCH.md Pitfall #6
}

# VADER compound classification thresholds (canonical VADER-paper values).
COMPOUND_BULLISH: float = 0.05
COMPOUND_BEARISH: float = -0.05

# Verdict-tier boundaries for the strong tiers. Raw input is in [-1, +1]
# but VADER compounds for typical financial headlines cluster in [-0.5, +0.5]
# — matching the natural data distribution rather than the 5-state ladder
# strict-> 0.6/0.2 used by fundamentals/technicals.
COMPOUND_STRONG_BULLISH: float = 0.4
COMPOUND_STRONG_BEARISH: float = -0.4

# Filter thresholds. Titles shorter than MIN_TITLE_LEN are below VADER's
# noise floor (one-word punditry like "Apple up"). Headlines older than
# MAX_AGE_DAYS have decay weights < 4% and are silently dropped.
MIN_TITLE_LEN: int = 20
MAX_AGE_DAYS: float = 14.0


# ---------------------------------------------------------------------------
# Per-headline + aggregation helpers. All take `now` as a parameter; no
# helper calls datetime.now() directly (Pitfall #7).
# ---------------------------------------------------------------------------


def _score_one(h: Headline, now: datetime) -> tuple[Optional[float], Optional[float]]:
    """Score one headline. Returns (compound_score, weight) or (None, None) if filtered.

    Filters (in order):
      * h.published_at is None — undated, exclude.
      * len(h.title) < MIN_TITLE_LEN — below VADER noise floor.
      * (now - h.published_at) > MAX_AGE_DAYS — stale; decay weight < 4%.

    Weight = recency_w * source_w. Unknown sources (defensive) default to 0.5.
    """
    if h.published_at is None:
        return None, None
    if len(h.title) < MIN_TITLE_LEN:
        return None, None
    age_days = max(0.0, (now - h.published_at).total_seconds() / 86400.0)
    if age_days > MAX_AGE_DAYS:
        return None, None
    recency_w = math.exp(-DECAY_K * age_days)
    source_w = SOURCE_WEIGHTS.get(h.source, 0.5)
    compound = _vader().polarity_scores(h.title)["compound"]
    return compound, recency_w * source_w


def _aggregate(
    headlines: list[Headline], now: datetime
) -> tuple[float, int, int, int, int]:
    """Aggregate a list of headlines.

    Returns (weighted_avg_compound, n_used, n_undated, n_short, n_stale).
    """
    weighted_sum = 0.0
    total_weight = 0.0
    n_used = n_undated = n_short = n_stale = 0
    for h in headlines:
        if h.published_at is None:
            n_undated += 1
            continue
        if len(h.title) < MIN_TITLE_LEN:
            n_short += 1
            continue
        age_days = max(0.0, (now - h.published_at).total_seconds() / 86400.0)
        if age_days > MAX_AGE_DAYS:
            n_stale += 1
            continue
        compound, w = _score_one(h, now)
        if compound is None or w is None:
            # Defensive — should be unreachable given the early filters above.
            continue
        weighted_sum += compound * w
        total_weight += w
        n_used += 1
    if total_weight == 0.0:
        return 0.0, 0, n_undated, n_short, n_stale
    return weighted_sum / total_weight, n_used, n_undated, n_short, n_stale


def _total_to_verdict(weighted_compound: float) -> Verdict:
    """Map weighted-average VADER compound to the 5-state verdict ladder.

    Strict > boundaries at 0.4 / 0.05 (and mirror for bearish). Tighter than
    the fundamentals/technicals 0.6/0.2 because VADER compounds for financial
    headlines cluster in [-0.5, +0.5] — adjusting the boundaries to the
    natural data distribution keeps the strong tiers from never firing.
    """
    if weighted_compound > COMPOUND_STRONG_BULLISH:
        return "strong_bullish"
    if weighted_compound > COMPOUND_BULLISH:
        return "bullish"
    if weighted_compound < COMPOUND_STRONG_BEARISH:
        return "strong_bearish"
    if weighted_compound < COMPOUND_BEARISH:
        return "bearish"
    return "neutral"


# ---------------------------------------------------------------------------
# Public scoring function
# ---------------------------------------------------------------------------


def score(
    snapshot: Snapshot,
    config: TickerConfig,
    *,
    computed_at: Optional[datetime] = None,
) -> AgentSignal:
    """Score news sentiment via VADER + recency × source weighting. Pure function.

    Parameters
    ----------
    snapshot : Snapshot
        Per-ticker aggregate snapshot. snapshot.news (list[Headline]) is read.
    config : TickerConfig
        Per-ticker config. Currently unused — accepted for parity with the
        AnalystId Literal contract (Phase 5 routine calls every analyst with
        the same (snapshot, config) signature).
    computed_at : datetime, optional
        UTC timestamp to stamp on the returned signal AND use as the recency
        baseline. Defaults to datetime.now(timezone.utc) — pin explicitly in
        tests for reproducible output. Read ONCE at the top of this function;
        helpers receive it as a parameter (Pitfall #7).

    Returns
    -------
    AgentSignal
        Always non-None; analyst_id='news_sentiment'. Never raises for missing
        data — empty / all-undated / all-short / all-stale snapshots produce
        the canonical data_unavailable=True signal per the UNIFORM RULE.
    """
    now = computed_at if computed_at is not None else datetime.now(timezone.utc)

    # UNIFORM RULE empty-data guard.
    if snapshot.data_unavailable or not snapshot.news:
        return AgentSignal(
            ticker=snapshot.ticker,
            analyst_id="news_sentiment",
            computed_at=now,
            data_unavailable=True,
            evidence=["no news headlines available"],
        )

    weighted_compound, n_used, n_undated, n_short, n_stale = _aggregate(
        snapshot.news, now
    )

    # All-filtered case — n_used == 0 BUT len(snapshot.news) > 0. Distinguish
    # in evidence so downstream debugging can see WHY no headlines scored.
    if n_used == 0:
        reasons: list[str] = []
        if n_undated > 0:
            reasons.append(f"{n_undated} headlines lacked published_at")
        if n_short > 0:
            reasons.append(
                f"{n_short} headlines too short (<{MIN_TITLE_LEN} chars)"
            )
        if n_stale > 0:
            reasons.append(
                f"{n_stale} headlines older than {MAX_AGE_DAYS:.0f} days"
            )
        return AgentSignal(
            ticker=snapshot.ticker,
            analyst_id="news_sentiment",
            computed_at=now,
            data_unavailable=True,
            evidence=[
                f"all {len(snapshot.news)} headlines filtered: " + "; ".join(reasons)
            ],
        )

    verdict = _total_to_verdict(weighted_compound)
    # VADER compounds cluster in [-0.5, +0.5] for financial headlines; the
    # 2.5x multiplier stretches |compound|=0.4 to confidence=100.
    confidence = min(100, int(round(min(1.0, abs(weighted_compound) * 2.5) * 100)))

    evidence: list[str] = [
        f"{n_used} headlines (recency-weighted), avg VADER compound "
        f"{weighted_compound:+.2f} — {verdict.replace('_', ' ')}"
    ]
    if n_undated > 0:
        evidence.append(
            f"{n_undated} headlines lacked timestamps and were excluded"
        )
    if n_short > 0:
        evidence.append(
            f"{n_short} short-title headlines excluded (VADER noise floor)"
        )
    # n_stale is silent — covered by the recency-decay design and not
    # surfaced to keep evidence list compact.

    return AgentSignal(
        ticker=snapshot.ticker,
        analyst_id="news_sentiment",
        computed_at=now,
        verdict=verdict,
        confidence=confidence,
        evidence=evidence[:10],
    )
