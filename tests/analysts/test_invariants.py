"""Cross-cutting invariant tests for the four Wave 2 Phase 3 analysts.

These two tests are integration-style — they exercise the contract every
Wave 2 analyst plan promises but require all four analyst modules
(analysts/{fundamentals,technicals,news_sentiment,valuation}.py) to be
importable. They xfail until Plans 03-02 / 03-03 / 03-04 / 03-05 ship
and flip GREEN naturally as the LAST Wave 2 plan lands.

Wave 2 close-out checkpoint: Plan 03-05 (the last Wave 2 plan to commit
per the dependency graph) MUST remove the @pytest.mark.xfail markers in
its final task. This is documented in 03-05's plan body so the markers
are not forgotten.

`strict=True` on every xfail marker — a passing test will fail loudly
(an unexpected GREEN means a Wave 2 plan over-shipped or these xfail
markers were left in place after Wave 2 close), and the natural RED
state during Wave 1 is reported as XFAIL (exit code 0).
"""
from __future__ import annotations

import pytest


@pytest.mark.xfail(
    reason="Wave 2 plans 03-02..03-05 ship the four analyst modules; "
    "test flips green when the last Wave 2 plan lands. Plan 03-05 removes "
    "this xfail marker as its final task.",
    strict=True,
)
def test_always_four_signals(make_snapshot, make_ticker_config, frozen_now) -> None:
    """For any (snapshot, config) combination, exactly 4 AgentSignals are produced.

    Confirms the 'always 4 signals per ticker, never fewer, never more'
    invariant from 03-CONTEXT.md. Phase 5 synthesizer and Phase 6 frontend
    rely on this contract.

    Imported lazily inside the test body so the file COLLECTS cleanly even
    before 03-02..03-05 land — ImportError at the import line is the
    expected RED state during Wave 1.
    """
    # Lazy imports — the four analyst modules don't exist yet at end of Wave 1.
    from analysts import fundamentals, news_sentiment, technicals, valuation
    from analysts.signals import AgentSignal

    # A representative populated Snapshot — caller passes a make_snapshot
    # factory that's been pre-populated with the per-source sub-fields each
    # analyst needs. The exact populating logic moves into the Wave 2 plans
    # as they land (each plan supplies the inputs its analyst module reads).
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


@pytest.mark.xfail(
    reason="Wave 2 plans 03-02..03-05 ship the four analyst modules; "
    "test flips green when the last Wave 2 plan lands. Plan 03-05 removes "
    "this xfail marker as its final task.",
    strict=True,
)
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
