"""routine.run_for_watchlist — sync-across-tickers loop with async-within (Pattern #3).

This module is shipped in two task halves:
  * Task 1 (this commit): TickerResult Pydantic v2 model lands here as the
    type used by routine/storage.py to build per-ticker JSON payloads. The
    storage layer needs the shape contract before the orchestration layer
    needs the loop logic.
  * Task 2 (next commit): _run_one_ticker async helper + run_for_watchlist
    sync-across-tickers loop with per-ticker exception isolation +
    lite-mode skip path.

Per-ticker pipeline (Task 2):
  1. Score 4 analyticals + PositionSignal (sync, fast).
  2. IF lite_mode: return TickerResult(persona_signals=[], ticker_decision=None).
  3. ELSE: await run_persona_slate (6-call asyncio.gather); await synthesize.

Sync across tickers: subscription quota is single-bucket; 30 tickers * 7 LLM
calls in parallel would 429 immediately. Per-ticker exception isolation:
caught at the loop level; appended as TickerResult(errors=[...]); other
tickers continue.

Snapshot-loading: parameterized via snapshot_loader callable for testability.
Default loader is a stub for v1; Phase 8's mid-day refresh extends it.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from analysts.position_signal import PositionSignal
from analysts.signals import AgentSignal
from synthesis.decision import TickerDecision


class TickerResult(BaseModel):
    """One ticker's complete pipeline result. Consumed by routine/storage.py.

    Fields (per 05-CONTEXT.md storage-format lock):
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
