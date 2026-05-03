"""Cross-cutting invariant tests for the four Wave 2 Phase 3 analysts.

Both tests exercise contracts that span all four analyst modules:
`test_always_four_signals` confirms each (snapshot, config) input produces
exactly 4 AgentSignals (one per analyst); `test_dark_snapshot_emits_four_unavailable`
confirms the UNIFORM RULE — every analyst's empty-data path emits a
data_unavailable=True signal with verdict='neutral', confidence=0, and
exactly one explanatory evidence string.
"""
from __future__ import annotations


def test_always_four_signals(make_snapshot, make_ticker_config, frozen_now) -> None:
    """For any (snapshot, config) combination, exactly 4 AgentSignals are produced.

    Confirms the 'always 4 signals per ticker, never fewer, never more'
    invariant from 03-CONTEXT.md. Phase 5 synthesizer and Phase 6 frontend
    rely on this contract.
    """
    from analysts import fundamentals, news_sentiment, technicals, valuation
    from analysts.signals import AgentSignal

    snap = make_snapshot()
    cfg = make_ticker_config(thesis_price=200.0)

    signals = [
        fundamentals.score(snap, cfg),
        technicals.score(snap, cfg),
        news_sentiment.score(snap, cfg),
        valuation.score(snap, cfg),
    ]

    assert len(signals) == 4
    for sig in signals:
        assert isinstance(sig, AgentSignal)

    analyst_ids = {sig.analyst_id for sig in signals}
    assert analyst_ids == {"fundamentals", "technicals", "news_sentiment", "valuation"}


def test_dark_snapshot_emits_four_unavailable(
    make_snapshot,
    make_ticker_config,
    frozen_now,
) -> None:
    """A dark snapshot (every source returned nothing useful) → all four
    analysts emit data_unavailable=True with verdict='neutral' + confidence=0
    + exactly one explanatory evidence string.

    Confirms the UNIFORM RULE from 03-CONTEXT.md: "any time the analyst
    can't form an opinion from the inputs available, emit
    AgentSignal(verdict='neutral', confidence=0, data_unavailable=True,
    evidence=[<reason>])".
    """
    from analysts import fundamentals, news_sentiment, technicals, valuation

    snap = make_snapshot(
        data_unavailable=True,
        prices=None,
        fundamentals=None,
        news=[],
        social=None,
        filings=[],
    )
    cfg = make_ticker_config()

    signals = [
        fundamentals.score(snap, cfg),
        technicals.score(snap, cfg),
        news_sentiment.score(snap, cfg),
        valuation.score(snap, cfg),
    ]

    for sig in signals:
        assert sig.data_unavailable is True
        assert sig.verdict == "neutral"
        assert sig.confidence == 0
        assert len(sig.evidence) == 1
