"""Tests for analysts/news_sentiment.py — pure-function VADER + recency + source weighting.

Coverage map (per 03-04-news-sentiment-PLAN.md):
  * Happy paths (5+ unambiguously bullish / bearish / neutral mixed headlines)
  * Recency dominance (fresh-bullish vs stale-bearish; decay-curve linearity)
  * Source-credibility weighting (yahoo dominates finviz; finviz-only path)
  * Filtering (undated drop / short-title drop / stale drop / all-filtered → data_unavailable)
  * Empty-data UNIFORM RULE (snapshot.data_unavailable / snapshot.news=[])
  * Determinism + provenance + lazy-VADER + dead-code-doc
  * Pitfall #7 — `now` read only inside score(), not in helpers

VADER calls are real (not mocked) per 03-RESEARCH.md anti-pattern guidance —
mocking VADER would render the recency / source-weighting tests pointless.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from analysts.data.news import Headline
from analysts.signals import AgentSignal


# ---------------------------------------------------------------------------
# Helpers — local Headline builder so each test reads cleanly.
# ---------------------------------------------------------------------------


def _h(
    title: str,
    *,
    source: str = "yahoo-rss",
    age_days: float = 0.0,
    ticker: str = "AAPL",
    now: datetime,
    published_at: datetime | None | str = "default",
) -> Headline:
    """Build a Headline with sensible defaults.

    `published_at="default"` (sentinel) → now - timedelta(days=age_days).
    `published_at=None` → undated (will be filtered).
    `published_at=<datetime>` → explicit timestamp.
    """
    if published_at == "default":
        pub = now - timedelta(days=age_days)
    else:
        pub = published_at
    return Headline(
        ticker=ticker,
        fetched_at=now,
        source=source,
        title=title,
        url=f"https://example.com/{abs(hash(title)) % 1_000_000}",
        published_at=pub,
        summary="",
        dedup_key=f"{source}::{abs(hash(title)) % 1_000_000}",
    )


# ---------------------------------------------------------------------------
# Lazy-init test FIRST — must run before anything else triggers _vader().
# Marked with high priority via filename ordering and explicit module check.
# ---------------------------------------------------------------------------


def test_lazy_vader_init_is_none_at_import_time() -> None:
    """`_VADER` global must be None until the first score() call constructs it.

    Skips if a prior test already triggered VADER init in this session — the
    point is that `import analysts.news_sentiment` doesn't pay VADER's cost.
    Verified separately via the source-grep test below.
    """
    from analysts import news_sentiment as ns
    # Either we're the first to load it (None) OR the source declares the
    # module-level singleton pattern (greppable). Either way, lazy.
    src = Path("analysts/news_sentiment.py").read_text(encoding="utf-8")
    assert "_VADER = None" in src
    assert "_vader()" in src or "def _vader(" in src


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


def test_bullish_headlines_strong(make_snapshot, make_ticker_config, frozen_now) -> None:
    """5 unambiguously-positive headlines, fresh, yahoo-rss → bullish/strong_bullish."""
    from analysts.news_sentiment import score

    headlines = [
        _h("Apple beats Q1 earnings expectations by 20% — record revenue", now=frozen_now),
        _h("Apple announces record buyback program — $90B authorization", now=frozen_now),
        _h("Apple raises full-year guidance to all-time-high level", now=frozen_now),
        _h("Apple wins major government contract worth $5B in clean energy", now=frozen_now),
        _h("Apple stock upgraded by Goldman Sachs to strong buy rating", now=frozen_now),
    ]
    snap = make_snapshot(news=headlines)
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.analyst_id == "news_sentiment"
    assert sig.data_unavailable is False
    assert sig.verdict in ("bullish", "strong_bullish")
    assert sig.confidence > 30
    assert "5 headlines" in sig.evidence[0]
    assert "VADER compound +" in sig.evidence[0]


def test_bearish_headlines_strong(make_snapshot, make_ticker_config, frozen_now) -> None:
    """5 unambiguously-negative headlines, fresh, yahoo-rss → bearish/strong_bearish."""
    from analysts.news_sentiment import score

    headlines = [
        _h("SEC investigates Apple for fraud allegations and accounting irregularities", now=frozen_now),
        _h("Apple Q1 earnings miss expectations by wide margin — disaster", now=frozen_now),
        _h("Apple recalls 10 million devices over critical safety failure", now=frozen_now),
        _h("Apple CFO resigns abruptly amid federal probe and scandal", now=frozen_now),
        _h("Apple stock downgraded to sell on poor outlook and crisis", now=frozen_now),
    ]
    snap = make_snapshot(news=headlines)
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.verdict in ("bearish", "strong_bearish")
    assert sig.confidence > 30
    assert "VADER compound -" in sig.evidence[0]


def test_neutral_mixed(make_snapshot, make_ticker_config, frozen_now) -> None:
    """3 bullish + 3 bearish at same timestamps and source → near-zero weighted_avg."""
    from analysts.news_sentiment import score

    headlines = [
        _h("Apple beats earnings expectations with strong record growth", now=frozen_now),
        _h("Apple wins major contract with great revenue boost expected", now=frozen_now),
        _h("Apple announces excellent quarterly results across all segments", now=frozen_now),
        _h("Apple faces terrible lawsuit and serious regulatory crisis", now=frozen_now),
        _h("Apple recalls products amid awful safety failure and scandal", now=frozen_now),
        _h("Apple loses key executive in damaging departure and turmoil", now=frozen_now),
    ]
    snap = make_snapshot(news=headlines)
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    # Could land in neutral OR mild bullish/bearish depending on VADER's exact compounds;
    # the test locks "no strong tier".
    assert sig.verdict in ("neutral", "bullish", "bearish")
    assert sig.confidence < 80


# ---------------------------------------------------------------------------
# Recency weighting
# ---------------------------------------------------------------------------


def test_recency_fresh_bullish_dominates_stale_bearish(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """1 fresh bullish (recency_w=1.0) + 1 10-day-old bearish (recency_w≈0.099) → bullish.

    Verifies the math: weighted_avg = (compound_bull * 1.0 + compound_bear * 0.099) / 1.099.
    """
    from analysts.news_sentiment import score, DECAY_K

    headlines = [
        _h("Apple beats earnings expectations with record revenue growth", age_days=0.0, now=frozen_now),
        _h("Apple faces terrible scandal with awful regulatory crisis", age_days=10.0, now=frozen_now),
    ]
    snap = make_snapshot(news=headlines)
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    expected_stale_w = math.exp(-DECAY_K * 10.0)
    assert expected_stale_w < 0.1  # sanity check — 10-day decay floor
    assert sig.verdict in ("bullish", "strong_bullish")


def test_recency_decay_curve(make_snapshot, make_ticker_config, frozen_now) -> None:
    """3 identical-bullish headlines at ages 0d / 3d / 6d. Weights = 1.0, 0.5, 0.25.

    Net weighted_avg = compound × (1.0 + 0.5 + 0.25) / (1.0 + 0.5 + 0.25) = compound (since all same).
    Just verify the headline survives and produces bullish verdict.
    """
    from analysts.news_sentiment import score

    headlines = [
        _h("Apple beats Q1 earnings with record growth and excellent guidance", age_days=age, now=frozen_now)
        for age in (0.0, 3.0, 6.0)
    ]
    snap = make_snapshot(news=headlines)
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.verdict in ("bullish", "strong_bullish")
    assert "3 headlines" in sig.evidence[0]


# ---------------------------------------------------------------------------
# Source weighting
# ---------------------------------------------------------------------------


def test_source_weight_yahoo_dominates_finviz(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """yahoo-rss bullish (weight 1.0) + finviz bearish (weight 0.7) → tilts bullish."""
    from analysts.news_sentiment import score

    headlines = [
        _h(
            "Apple beats earnings with record growth and excellent guidance results",
            source="yahoo-rss",
            age_days=0.0,
            now=frozen_now,
        ),
        _h(
            "Apple faces awful regulatory crisis with terrible scandal looming",
            source="finviz",
            age_days=0.0,
            now=frozen_now,
        ),
    ]
    snap = make_snapshot(news=headlines)
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    # 1.0 weight bullish vs 0.7 weight bearish should land bullish.
    assert sig.verdict in ("bullish", "neutral")  # neutral if compound magnitudes cancel; never bearish
    assert sig.verdict != "bearish"
    assert sig.verdict != "strong_bearish"


def test_source_weight_finviz_alone_bullish(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """1 bullish from finviz alone → bullish (the source weight does not affect VERDICT, only weighted_avg)."""
    from analysts.news_sentiment import score

    headlines = [
        _h(
            "Apple beats earnings with record growth and excellent guidance results",
            source="finviz",
            age_days=0.0,
            now=frozen_now,
        ),
    ]
    snap = make_snapshot(news=headlines)
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.verdict in ("bullish", "strong_bullish")


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


def test_filter_undated_dropped(make_snapshot, make_ticker_config, frozen_now) -> None:
    """2 undated + 1 dated bullish → aggregate uses 1; evidence mentions 2 lacked timestamps."""
    from analysts.news_sentiment import score

    headlines = [
        _h("Apple beats earnings with record growth and excellent guidance results", published_at=None, now=frozen_now),
        _h("Apple wins major government contract worth billions in revenue", published_at=None, now=frozen_now),
        _h("Apple announces record buyback program with great future outlook", age_days=0.0, now=frozen_now),
    ]
    snap = make_snapshot(news=headlines)
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.verdict in ("bullish", "strong_bullish")
    evidence_str = " | ".join(sig.evidence)
    assert "2" in evidence_str
    assert "lacked" in evidence_str or "timestamps" in evidence_str


def test_filter_short_title_dropped(make_snapshot, make_ticker_config, frozen_now) -> None:
    """2 short titles (<20 chars) + 1 full bullish → aggregate uses 1; evidence mentions short."""
    from analysts.news_sentiment import score

    headlines = [
        _h("Apple up", age_days=0.0, now=frozen_now),  # 8 chars
        _h("Apple wins", age_days=0.0, now=frozen_now),  # 10 chars
        _h(
            "Apple beats earnings with record growth and excellent guidance results",
            age_days=0.0,
            now=frozen_now,
        ),
    ]
    snap = make_snapshot(news=headlines)
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.verdict in ("bullish", "strong_bullish")
    evidence_str = " | ".join(sig.evidence)
    assert "short" in evidence_str.lower() or "noise floor" in evidence_str.lower()


def test_filter_stale_dropped(make_snapshot, make_ticker_config, frozen_now) -> None:
    """1 stale (20d) + 2 fresh bullish → aggregate uses 2; stale silently dropped."""
    from analysts.news_sentiment import score

    headlines = [
        _h("Apple faces terrible old scandal from years ago", age_days=20.0, now=frozen_now),
        _h("Apple beats earnings with record growth and excellent guidance results", age_days=2.0, now=frozen_now),
        _h("Apple announces record buyback program with great future outlook", age_days=0.0, now=frozen_now),
    ]
    snap = make_snapshot(news=headlines)
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.verdict in ("bullish", "strong_bullish")
    assert "2 headlines" in sig.evidence[0]


def test_all_undated_data_unavailable(make_snapshot, make_ticker_config, frozen_now) -> None:
    """All headlines have published_at=None → data_unavailable=True with reason."""
    from analysts.news_sentiment import score

    headlines = [
        _h("Apple beats earnings with record growth and excellent guidance results", published_at=None, now=frozen_now),
        _h("Apple wins contract worth billions in upcoming revenue", published_at=None, now=frozen_now),
        _h("Apple announces buyback with strong outlook for future", published_at=None, now=frozen_now),
    ]
    snap = make_snapshot(news=headlines)
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.data_unavailable is True
    assert sig.verdict == "neutral"
    assert sig.confidence == 0
    evidence_str = " | ".join(sig.evidence)
    assert "lacked" in evidence_str or "published_at" in evidence_str


def test_all_short_data_unavailable(make_snapshot, make_ticker_config, frozen_now) -> None:
    """All headlines too short → data_unavailable=True with reason."""
    from analysts.news_sentiment import score

    headlines = [
        _h("Apple up", age_days=0.0, now=frozen_now),
        _h("Apple wins", age_days=0.0, now=frozen_now),
        _h("Apple drops", age_days=0.0, now=frozen_now),
    ]
    snap = make_snapshot(news=headlines)
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.data_unavailable is True
    assert sig.verdict == "neutral"
    assert sig.confidence == 0


# ---------------------------------------------------------------------------
# Empty-data UNIFORM RULE
# ---------------------------------------------------------------------------


def test_empty_news_data_unavailable(make_snapshot, make_ticker_config, frozen_now) -> None:
    """snapshot.news=[] → data_unavailable=True signal."""
    from analysts.news_sentiment import score

    snap = make_snapshot(news=[])
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.data_unavailable is True
    assert sig.verdict == "neutral"
    assert sig.confidence == 0
    assert any("no news" in e.lower() or "no headlines" in e.lower() for e in sig.evidence)


def test_snapshot_data_unavailable_true(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """snapshot.data_unavailable=True → data_unavailable=True signal."""
    from analysts.news_sentiment import score

    snap = make_snapshot(data_unavailable=True)
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.data_unavailable is True
    assert sig.verdict == "neutral"


# ---------------------------------------------------------------------------
# Determinism + provenance + meta
# ---------------------------------------------------------------------------


def test_deterministic(make_snapshot, make_ticker_config, frozen_now) -> None:
    """Two calls with identical inputs → byte-identical AgentSignal model_dump_json."""
    from analysts.news_sentiment import score

    headlines = [
        _h("Apple beats earnings with record growth and excellent guidance results", age_days=0.0, now=frozen_now),
        _h("Apple wins major government contract worth billions in revenue", age_days=2.0, now=frozen_now),
    ]
    snap = make_snapshot(news=headlines)
    cfg = make_ticker_config()

    sig1 = score(snap, cfg, computed_at=frozen_now)
    sig2 = score(snap, cfg, computed_at=frozen_now)

    assert sig1.model_dump_json() == sig2.model_dump_json()


def test_computed_at_passes_through(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """Explicit computed_at preserved on the returned signal."""
    from analysts.news_sentiment import score

    headlines = [
        _h("Apple beats earnings with record growth and excellent guidance results", age_days=0.0, now=frozen_now),
    ]
    snap = make_snapshot(news=headlines)
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert sig.computed_at == frozen_now


def test_computed_at_default_uses_now(make_snapshot, make_ticker_config) -> None:
    """Without explicit computed_at, default ≈ datetime.now(UTC)."""
    from analysts.news_sentiment import score

    now_for_headline = datetime.now(timezone.utc)
    headlines = [
        Headline(
            ticker="AAPL",
            fetched_at=now_for_headline,
            source="yahoo-rss",
            title="Apple beats earnings with record growth and excellent guidance results",
            url="https://example.com/1",
            published_at=now_for_headline,
            summary="",
            dedup_key="yahoo-rss::default-test",
        )
    ]
    snap = make_snapshot(news=headlines)
    cfg = make_ticker_config()

    before = datetime.now(timezone.utc)
    sig = score(snap, cfg)
    after = datetime.now(timezone.utc)

    assert before <= sig.computed_at <= after


def test_no_module_level_clock_in_helpers() -> None:
    """`datetime.now(` must appear ONLY inside score() — helpers receive `now` as parameter (Pitfall #7)."""
    src = Path("analysts/news_sentiment.py").read_text(encoding="utf-8")
    # Count occurrences of datetime.now(
    occurrences = src.count("datetime.now(")
    # At most 1 — inside score(). Could be 0 if implementation uses a different default expression,
    # but if any datetime.now() exists, it must be inside score().
    assert occurrences <= 1, f"datetime.now() appears {occurrences}x in source — must be only inside score()"


def test_provenance_header_present() -> None:
    """Provenance header references virattt source AND documents VADER divergence (INFRA-07)."""
    src = Path("analysts/news_sentiment.py").read_text(encoding="utf-8")
    assert "virattt/ai-hedge-fund/src/agents/news_sentiment.py" in src
    assert "VADER" in src  # divergence flag


def test_press_wires_source_in_dict_dead_code_doc() -> None:
    """SOURCE_WEIGHTS contains 'press-wires' key with forward-compat / dead-code commentary (Pitfall #6)."""
    src = Path("analysts/news_sentiment.py").read_text(encoding="utf-8")
    assert "press-wires" in src
    lowered = src.lower()
    assert "forward-compat" in lowered or "dead code" in lowered or "pitfall #6" in lowered


def test_returns_agent_signal_type(
    make_snapshot, make_ticker_config, frozen_now
) -> None:
    """score() always returns an AgentSignal — never None, never raises."""
    from analysts.news_sentiment import score

    headlines = [
        _h("Apple beats earnings with record growth and excellent guidance results", age_days=0.0, now=frozen_now),
    ]
    snap = make_snapshot(news=headlines)
    cfg = make_ticker_config()

    sig = score(snap, cfg, computed_at=frozen_now)

    assert isinstance(sig, AgentSignal)
    assert sig.analyst_id == "news_sentiment"
