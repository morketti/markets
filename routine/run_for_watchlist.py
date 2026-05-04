"""routine.run_for_watchlist — sync-across-tickers loop with async-within (Pattern #3).

Per-ticker pipeline:
  1. Score 4 analyticals + PositionSignal (sync, fast).
  2. IF lite_mode: return TickerResult(persona_signals=[], ticker_decision=None).
  3. ELSE: await run_persona_slate (6-call asyncio.gather); await synthesize.

Sync across tickers: subscription quota is single-bucket; 30 tickers * 7 LLM
calls in parallel would 429 immediately. Per-ticker exception isolation:
caught at the loop level; appended as TickerResult(errors=[repr(exc)]); other
tickers continue (LLM-08 cascade-prevention).

Snapshot-loading: parameterized via snapshot_loader callable for testability.
Default loader is a stub for v1; Phase 8's mid-day refresh extends it.

Provenance: novel-to-this-project orchestration glue. The per-ticker shape
(score 4 analyticals → fan out 6 personas → synthesize) IS adapted from
the virattt/ai-hedge-fund + TauricResearch/TradingAgents agent-graph
patterns conceptually, but the explicit sync-across-tickers / async-within
choice (Pattern #3) is the project's own quota-aware design.
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Callable

from anthropic import AsyncAnthropic
from pydantic import BaseModel, ConfigDict, Field

from analysts import (
    fundamentals,
    news_sentiment,
    position_adjustment,
    technicals,
    valuation,
)
from analysts.data.prices import OHLCBar
from analysts.data.snapshot import Snapshot
from analysts.position_signal import PositionSignal
from analysts.schemas import TickerConfig, Watchlist
from analysts.signals import AgentSignal
from routine.persona_runner import run_persona_slate
from synthesis.decision import TickerDecision
from synthesis.synthesizer import synthesize

logger = logging.getLogger(__name__)


class TickerResult(BaseModel):
    """One ticker's complete pipeline result. Consumed by routine/storage.py.

    Fields (per 05-CONTEXT.md storage-format lock + Phase 6 / Plan 06-01
    Wave 0 amendment):
      ticker             — canonical ticker (matches snapshot.ticker).
      analytical_signals — 4 AgentSignals (fund/tech/nsen/val) by convention.
                            Empty on per-ticker pipeline failure (errors set).
      position_signal    — PositionSignal from position_adjustment.score().
                            None on per-ticker pipeline failure.
      persona_signals    — 6 AgentSignals (PERSONA_IDS canonical order) when
                            non-lite mode; len=0 in lite mode (INFRA-02 skip).
      ticker_decision    — TickerDecision from synthesize() when non-lite mode;
                            None in lite mode OR per-ticker pipeline failure.
      errors             — Per-ticker pipeline error reprs; default [] when
                            the pipeline ran cleanly.
      ohlc_history       — Phase 6 / Plan 06-01: list[OHLCBar] (last ~180
                            trading days) sourced from yfinance via the same
                            fetch the analytical signals consume; persisted
                            by storage so the frontend deep-dive chart can
                            render OHLC + indicator overlays without
                            re-fetching market data. Default [] for
                            data-unavailable / lite-mode / cold-start paths.
      headlines          — Phase 6 / Plan 06-01: list[dict] of raw
                            `{source, published_at, title, url}` records from
                            ingestion.news.fetch_news(return_raw=True);
                            persisted by storage for the frontend news feed
                            (VIEW-08). Default [] when ingestion fails or
                            returns empty.

    arbitrary_types_allowed=True — AgentSignal + PositionSignal + TickerDecision
    are nested Pydantic models from sibling packages. Pydantic v2 handles them
    natively, but the flag makes the intent explicit and survives forward-compat
    schema changes.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    ticker: str
    analytical_signals: list[AgentSignal] = Field(default_factory=list)
    position_signal: PositionSignal | None = None
    persona_signals: list[AgentSignal] = Field(default_factory=list)
    ticker_decision: TickerDecision | None = None
    errors: list[str] = Field(default_factory=list)
    # Phase 6 / Plan 06-01 — Wave 0 amendment fields.
    ohlc_history: list[OHLCBar] = Field(default_factory=list)
    headlines: list[dict] = Field(default_factory=list)


def _default_snapshot_loader(ticker: str) -> Snapshot:
    """v1 stub. Phase 8 mid-day refresh + production snapshot reads will replace.

    The production routine pre-fetches snapshots via the Phase 2 ingestion
    layer and persists them to data/{date}/snapshot/{TICKER}.json (or similar).
    Wave 5 ships only the orchestration loop; the snapshot-source plumbing
    is Phase 8's territory. Tests inject a custom loader.
    """
    raise NotImplementedError(
        f"snapshot_loader not configured; pass snapshot_loader= to run_for_watchlist "
        f"(ticker={ticker})"
    )


async def _run_one_ticker(
    client: AsyncAnthropic,
    ticker_config: TickerConfig,
    snapshot: Snapshot,
    *,
    lite_mode: bool,
    computed_at: datetime,
) -> TickerResult:
    """Per-ticker pipeline: 4 analyticals + PositionSignal + (conditional) personas + synthesizer.

    Order of operations (Pattern #3):
      1. Sync analyticals (fast, no I/O after Snapshot loaded):
         - fundamentals.score
         - technicals.score
         - news_sentiment.score
         - valuation.score
         - position_adjustment.score (PositionSignal — peer of AgentSignal)
      2. IF lite_mode: return analyticals-only TickerResult.
      3. ELSE: await run_persona_slate (6-call asyncio.gather; ~6x faster
         than sync); await synthesize (1 LLM call producing TickerDecision).
    """
    ticker = ticker_config.ticker

    # 1. Sync analyticals.
    fund = fundamentals.score(snapshot, ticker_config, computed_at=computed_at)
    tech = technicals.score(snapshot, ticker_config, computed_at=computed_at)
    nsen = news_sentiment.score(snapshot, ticker_config, computed_at=computed_at)
    val = valuation.score(snapshot, ticker_config, computed_at=computed_at)
    pose = position_adjustment.score(
        snapshot, ticker_config, computed_at=computed_at,
    )

    # Phase 6 / Plan 06-01 — Wave 0 amendment: thread ohlc_history + headlines
    # through TickerResult so storage can persist them in the per-ticker JSON.
    # Source data: the same Snapshot the analytical signals already consumed —
    # NO double-fetch (keyless data plane discipline). prices.history is
    # already a list[OHLCBar]; snapshot.news is list[Headline] which we
    # serialize to the 4-key raw shape used by the frontend deep-dive feed.
    ohlc_history: list[OHLCBar] = []
    if snapshot.prices is not None and not snapshot.prices.data_unavailable:
        ohlc_history = list(snapshot.prices.history)

    headlines_raw: list[dict] = []
    for h in snapshot.news:
        if h.data_unavailable:
            continue
        dumped = h.model_dump(mode="json")
        headlines_raw.append(
            {
                "source": dumped["source"],
                "published_at": dumped["published_at"],
                "title": dumped["title"],
                "url": dumped["url"],
            }
        )

    if lite_mode:
        return TickerResult(
            ticker=ticker,
            analytical_signals=[fund, tech, nsen, val],
            position_signal=pose,
            persona_signals=[],
            ticker_decision=None,
            errors=[],
            ohlc_history=ohlc_history,
            headlines=headlines_raw,
        )

    # 2. Persona fan-out + synthesizer.
    persona_signals = await run_persona_slate(
        client,
        ticker=ticker,
        snapshot=snapshot,
        config=ticker_config,
        analytical_signals=[fund, tech, nsen, val],
        position_signal=pose,
        computed_at=computed_at,
    )
    decision = await synthesize(
        client,
        ticker=ticker,
        snapshot=snapshot,
        config=ticker_config,
        analytical_signals=[fund, tech, nsen, val],
        position_signal=pose,
        persona_signals=persona_signals,
        computed_at=computed_at,
    )
    return TickerResult(
        ticker=ticker,
        analytical_signals=[fund, tech, nsen, val],
        position_signal=pose,
        persona_signals=persona_signals,
        ticker_decision=decision,
        errors=[],
        ohlc_history=ohlc_history,
        headlines=headlines_raw,
    )


async def run_for_watchlist(
    watchlist: Watchlist,
    *,
    lite_mode: bool,
    snapshots_root: Path,
    computed_at: datetime,
    client: AsyncAnthropic | None = None,
    snapshot_loader: Callable[[str], Snapshot] | None = None,
) -> list[TickerResult]:
    """Sync across tickers; async within ticker. Returns one TickerResult per ticker.

    Iteration order matches Watchlist.tickers dict order (insertion order
    preserved since Python 3.7). Per-ticker exceptions are caught at the
    loop level and converted to TickerResult(errors=[...]) — the routine
    NEVER aborts mid-watchlist (LLM-08 cascade-prevention).

    Parameters
    ----------
    watchlist
        Validated Watchlist (Phase 1 schema). watchlist.tickers is a
        dict[str, TickerConfig] iterated via .values() in insertion order.
    lite_mode
        True → skip persona + synthesizer LLM calls (INFRA-02 quota guard).
    snapshots_root
        Path to the data/ folder. Currently passed through for future use
        (Phase 8 mid-day refresh reads/writes from here); not consumed in
        Wave 5.
    computed_at
        UTC timestamp pinned at run-start. Same instant for every ticker
        (consistent across the daily snapshot folder).
    client
        AsyncAnthropic SDK client. Defaults to AsyncAnthropic() (production
        subscription auth path); tests inject the Wave 2 mock client.
    snapshot_loader
        Callable[[ticker], Snapshot]. Defaults to _default_snapshot_loader
        (v1 stub that raises NotImplementedError); tests inject closures.

    Returns
    -------
    list[TickerResult]
        One TickerResult per watchlist ticker, in input order. Per-ticker
        failures appear as TickerResult(ticker=..., errors=[repr(exc)]) with
        all other fields at default values.
    """
    if client is None:
        client = AsyncAnthropic()  # subscription auth in routine context
    if snapshot_loader is None:
        snapshot_loader = _default_snapshot_loader

    results: list[TickerResult] = []
    # watchlist.tickers is a dict[str, TickerConfig]; iterate values to get
    # the configs themselves (NOT the keys).
    for ticker_config in watchlist.tickers.values():
        ticker = ticker_config.ticker
        try:
            snapshot = snapshot_loader(ticker)
            result = await _run_one_ticker(
                client, ticker_config, snapshot,
                lite_mode=lite_mode, computed_at=computed_at,
            )
        except Exception as exc:  # noqa: BLE001 — cascade-prevention by design
            logger.exception("ticker %s pipeline failed", ticker)
            result = TickerResult(
                ticker=ticker,
                errors=[f"per-ticker pipeline failure: {exc!r}"],
            )
        results.append(result)
    return results
