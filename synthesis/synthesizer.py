"""synthesis.synthesizer — single per-ticker LLM call producing TickerDecision.

Pattern adapted from TauricResearch/TradingAgents
tradingagents/agents/managers/{portfolio_manager.py, research_manager.py} —
the single-LLM-call decision-producer shape.

Modifications from the reference implementation:
  * 6-state DecisionRecommendation (vs TradingAgents' 5-state buy /
    overweight / hold / underweight / sell). Locked in 05-02 per user
    product requirements.
  * Explicit DissentSection — TradingAgents has no dissent surface;
    LLM-07 is novel-to-this-project.
  * Dual-timeframe TimeframeBand (short_term + long_term cards) —
    TradingAgents is single-timeframe.
  * Dissent computed in PYTHON (synthesis/dissent.py) BEFORE the LLM
    call — Pattern #7 lock. The LLM renders the pre-computed dissent
    verbatim; it never computes dissent itself. This guards against
    constrained-decoding accepting a hallucinated persona_id that
    schema-validates as `str | None` but doesn't match any of the 6
    canonical persona IDs.
  * Anthropic-native via routine.llm_client.call_with_retry which uses
    client.messages.parse(output_format=TickerDecision) — TradingAgents
    uses LangChain's structured-output abstraction. We're keyless via
    Claude Code Routine subscription (PROJECT.md lock).
  * Async — TradingAgents is sync per-ticker; we use AsyncAnthropic
    consistently with Wave 3 persona fan-out (Pattern #3). Wave 5
    entrypoint awaits this from inside its per-ticker loop.

Failure handling per LLM-05 / Pattern #8:
  * Snapshot.data_unavailable=True → no LLM call; return canonical
    _data_unavailable_decision (cost-saving + schema-invariant safe).
  * persona_signals == [] (lite mode — INFRA-02) → no LLM call; same
    canonical _data_unavailable_decision shape.
  * call_with_retry exhaustion → _decision_default_factory returns
    canonical _data_unavailable_decision (same shape; satisfies the
    @model_validator invariant from synthesis/decision.py).

Public surface (consumed by Wave 5 / 05-06 entrypoint):
    SYNTHESIZER_PROMPT_PATH       — Path("prompts/synthesizer.md")
    SYNTHESIZER_MODEL             — "claude-opus-4-7" per Pattern #2
    SYNTHESIZER_MAX_TOKENS        — 4000
    load_synthesizer_prompt()     — disk read with lru_cache
    build_synthesizer_user_context(...) — single user-message string
    synthesize(...)               — single LLM call producing TickerDecision
"""
from __future__ import annotations

import functools
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from anthropic import AsyncAnthropic

from analysts.data.snapshot import Snapshot
from analysts.position_signal import PositionSignal
from analysts.schemas import TickerConfig
from analysts.signals import AgentSignal
from routine.llm_client import call_with_retry
from synthesis.decision import (
    DissentSection,
    TickerDecision,
    TimeframeBand,
)
from synthesis.dissent import compute_dissent

# ---------------------------------------------------------------------------
# Module constants — single source of truth.
# ---------------------------------------------------------------------------

SYNTHESIZER_PROMPT_PATH: Path = Path("prompts/synthesizer.md")
SYNTHESIZER_MODEL: str = "claude-opus-4-7"
SYNTHESIZER_MAX_TOKENS: int = 4000


@functools.lru_cache(maxsize=2)
def load_synthesizer_prompt() -> str:
    """Read prompts/synthesizer.md from disk; cached.

    Cache size 2 is intentional: the prompt is read once per N_TICKERS in
    a routine run; lru_cache deduplicates so we hit disk exactly once per
    process. cache_clear() exposed for tests that monkeypatch the path
    constant.

    Raises FileNotFoundError if SYNTHESIZER_PROMPT_PATH is missing —
    defensive: catches a typo or missing-file deployment situation
    immediately rather than letting an empty string flow into the LLM.
    """
    if not SYNTHESIZER_PROMPT_PATH.exists():
        raise FileNotFoundError(
            f"synthesizer prompt missing: {SYNTHESIZER_PROMPT_PATH}"
        )
    return SYNTHESIZER_PROMPT_PATH.read_text(encoding="utf-8")


def build_synthesizer_user_context(
    *,
    ticker: str,
    snapshot: Snapshot,
    config: TickerConfig,
    analytical_signals: list[AgentSignal],
    position_signal: PositionSignal,
    persona_signals: list[AgentSignal],
    dissent_persona_id: Optional[str],
    dissent_summary: str,
) -> str:
    """Build the synthesizer user-message string.

    All sections always present, even when content is "no dissent" or
    "lite mode (empty persona slate)" — keeps the synthesizer prompt's
    section-anchor parsing deterministic. Two calls with identical
    inputs produce byte-identical output.

    Section layout:
      # Ticker: <symbol>
      ## Snapshot Summary
      ## 4 Analytical Signals
      ## PositionSignal
      ## 6 Persona Signals
      ## User TickerConfig
      ## Pre-computed Dissent
    """
    lines: list[str] = []
    lines.append(f"# Ticker: {ticker}")
    lines.append("")
    lines.append("## Snapshot Summary")
    lines.append(_summarize_snapshot(snapshot))
    lines.append("")
    lines.append("## 4 Analytical Signals")
    for s in analytical_signals:
        lines.append(_format_signal(s))
    lines.append("")
    lines.append("## PositionSignal")
    lines.append(_format_position_signal(position_signal))
    lines.append("")
    lines.append("## 6 Persona Signals")
    if persona_signals:
        for s in persona_signals:
            lines.append(_format_signal(s))
    else:
        lines.append("(empty — lite mode skipped persona slate)")
    lines.append("")
    lines.append("## User TickerConfig")
    lines.append(_format_config(config))
    lines.append("")
    lines.append("## Pre-computed Dissent")
    if dissent_persona_id is None:
        lines.append(
            "no dissent (has_dissent: false; render dissent.has_dissent=false)"
        )
    else:
        lines.append(f"dissenting_persona: {dissent_persona_id}")
        lines.append(f"dissent_summary: {dissent_summary}")
    return "\n".join(lines)


def _summarize_snapshot(snapshot: Snapshot) -> str:
    """Compact summary of the per-ticker Snapshot — current price + history + fundamentals.

    Uses actual schema field names from analysts.data.fundamentals.FundamentalsSnapshot:
    `pe`, `roe`, `debt_to_equity` (NOT `pe_ratio` / `return_on_equity`).
    """
    if snapshot.data_unavailable:
        return "data_unavailable=True"
    parts: list[str] = []
    if snapshot.prices is not None and not snapshot.prices.data_unavailable:
        if snapshot.prices.current_price is not None:
            parts.append(f"current_price={snapshot.prices.current_price}")
        if snapshot.prices.history:
            parts.append(f"history bars={len(snapshot.prices.history)}")
    if (
        snapshot.fundamentals is not None
        and not snapshot.fundamentals.data_unavailable
    ):
        f = snapshot.fundamentals
        if f.pe is not None:
            parts.append(f"P/E={f.pe}")
        if f.roe is not None:
            parts.append(f"ROE={f.roe}")
        if f.debt_to_equity is not None:
            parts.append(f"D/E={f.debt_to_equity}")
    return "; ".join(parts) if parts else "(no fundamentals/prices)"


def _format_signal(s: AgentSignal) -> str:
    """One-line summary of an AgentSignal — id, verdict, confidence, top-3 evidence."""
    return (
        f"- {s.analyst_id}: {s.verdict} (conf={s.confidence}) - "
        + ("; ".join(s.evidence[:3]) if s.evidence else "(no evidence)")
        + (" [data_unavailable]" if s.data_unavailable else "")
    )


def _format_position_signal(p: PositionSignal) -> str:
    """One-line summary of the PositionSignal — state, score, hint, confidence, regime."""
    if p.data_unavailable:
        return "[data_unavailable]"
    return (
        f"state={p.state}, consensus_score={p.consensus_score:.2f}, "
        f"action_hint={p.action_hint}, confidence={p.confidence}, "
        f"trend_regime={p.trend_regime}"
    )


def _format_config(c: TickerConfig) -> str:
    """One-line summary of TickerConfig — lens, focus, optional thesis_price + notes."""
    parts: list[str] = [
        f"long_term_lens={c.long_term_lens}",
        f"short_term_focus={c.short_term_focus}",
    ]
    if c.thesis_price is not None:
        parts.append(f"thesis_price={c.thesis_price}")
    if c.notes:
        parts.append(f"notes={c.notes[:200]}")
    return "; ".join(parts)


def _data_unavailable_decision(
    ticker: str, computed_at: datetime, reason: str,
) -> TickerDecision:
    """Build a TickerDecision satisfying the data_unavailable invariant.

    Used in 3 places:
      * Snapshot.data_unavailable=True skip path (synthesize early-return)
      * Lite-mode skip path (empty persona_signals)
      * call_with_retry exhaustion default_factory (LLM-05)

    Single source of truth so all 3 paths produce the same shape — the
    schema invariant from synthesis/decision.py
    (data_unavailable=True ⟹ recommendation='hold' AND conviction='low')
    is satisfied by construction.
    """
    return TickerDecision(
        ticker=ticker,
        computed_at=computed_at,
        recommendation="hold",
        conviction="low",
        short_term=TimeframeBand(
            summary=f"data unavailable: {reason}",
            drivers=[],
            confidence=0,
        ),
        long_term=TimeframeBand(
            summary=f"data unavailable: {reason}",
            drivers=[],
            confidence=0,
        ),
        open_observation=f"synthesizer skipped: {reason}",
        dissent=DissentSection(),
        data_unavailable=True,
    )


def _decision_default_factory(
    ticker: str, computed_at: datetime, reason: str = "schema_failure",
) -> Callable[[], TickerDecision]:
    """Closure-bound default_factory for routine.llm_client.call_with_retry.

    Returned on retry exhaustion per LLM-05 contract. ticker + computed_at
    + reason are captured at call site so each factory invocation produces
    the contextually-correct default. The closure indirection matches the
    persona_runner._persona_default_factory pattern (routine/persona_runner.py).
    """
    def factory() -> TickerDecision:
        return _data_unavailable_decision(ticker, computed_at, reason)
    return factory


async def synthesize(
    client: AsyncAnthropic,
    *,
    ticker: str,
    snapshot: Snapshot,
    config: TickerConfig,
    analytical_signals: list[AgentSignal],
    position_signal: PositionSignal,
    persona_signals: list[AgentSignal],
    computed_at: datetime,
) -> TickerDecision:
    """Single per-ticker synthesizer LLM call. Returns Pydantic-validated TickerDecision.

    Flow:
      1. Snapshot.data_unavailable=True → no LLM call; return canonical
         data_unavailable TickerDecision (Wave 5's per-ticker pipeline
         continues to the next ticker; this one's slot is filled).
      2. persona_signals == [] (lite mode — INFRA-02) → no LLM call;
         same canonical shape with reason='lite_mode (no persona signals)'.
      3. Otherwise: compute_dissent() in Python (Pattern #7 lock);
         build_synthesizer_user_context() with the pre-computed dissent
         injected; call_with_retry(model='claude-opus-4-7',
         output_format=TickerDecision) — LLM renders the dissent
         verbatim, never computes it. On call_with_retry exhaustion,
         _decision_default_factory returns the canonical data_unavailable
         shape (LLM-05 contract).

    Parameters
    ----------
    client
        AsyncAnthropic SDK client instantiated by the routine entrypoint.
        Lifecycle is owned by the caller; we just consume it.
    ticker
        Canonical ticker (already normalized — typically by the caller).
    snapshot
        Per-ticker Snapshot from Phase 2 ingestion. The synthesizer reads
        the summary; it doesn't re-fetch.
    config
        Per-ticker TickerConfig (user's thesis_price / target_multiples /
        long_term_lens / notes / technical_levels).
    analytical_signals
        4 AgentSignals from the analyst slate — order: fundamentals,
        technicals, news_sentiment, valuation. Defensive ordering not
        validated here (caller is the routine's _run_one_ticker which
        produces them in canonical order).
    position_signal
        PositionSignal from Phase 4 position_adjustment.score().
    persona_signals
        6 AgentSignals from the persona slate (PERSONA_IDS canonical
        order). Empty list signals lite mode.
    computed_at
        UTC timestamp pinned at the top of the per-ticker pipeline.
        Used as TickerDecision.computed_at on both happy and skip paths.

    Returns
    -------
    TickerDecision
        Pydantic-validated TickerDecision. Always non-None — failure
        modes route through _data_unavailable_decision /
        _decision_default_factory.
    """
    # Skip-path 1 — Snapshot is dark.
    if snapshot.data_unavailable:
        return _data_unavailable_decision(
            ticker, computed_at, "snapshot data_unavailable=True",
        )

    # Skip-path 2 — Lite mode (INFRA-02): persona slate skipped to save quota.
    if not persona_signals:
        return _data_unavailable_decision(
            ticker, computed_at, "lite_mode (no persona signals)",
        )

    # Pattern #7 lock — dissent computed in Python BEFORE the LLM call.
    dissent_id, dissent_summary = compute_dissent(persona_signals)

    system_prompt = load_synthesizer_prompt()
    user_context = build_synthesizer_user_context(
        ticker=ticker,
        snapshot=snapshot,
        config=config,
        analytical_signals=analytical_signals,
        position_signal=position_signal,
        persona_signals=persona_signals,
        dissent_persona_id=dissent_id,
        dissent_summary=dissent_summary,
    )

    return await call_with_retry(
        client,
        model=SYNTHESIZER_MODEL,
        system=system_prompt,
        user=user_context,
        output_format=TickerDecision,
        default_factory=_decision_default_factory(ticker, computed_at),
        max_tokens=SYNTHESIZER_MAX_TOKENS,
        context_label=f"synthesizer:{ticker}",
    )
