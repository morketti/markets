"""routine.persona_runner — async fan-out across 6 personas per ticker.

Pattern adapted from virattt/ai-hedge-fund/src/agents/ per-persona files:
warren_buffett.py, charlie_munger.py, cathie_wood.py, michael_burry.py,
peter_lynch.py — the per-persona-agent shape. Open Claude Analyst
(claude_analyst.md) has no virattt analog (novel-to-this-project; embodies
user MEMORY.md feedback 'include Claude's inherent reasoning, not just
personas').

Modifications from the reference implementation:
  * Markdown-loaded prompts (LLM-01 + LLM-02) — virattt hardcodes prompt
    content as Python strings; we load from prompts/personas/*.md at call
    time so the user can iterate prompts without code changes.
  * Anthropic-native via routine.llm_client.call_with_retry which uses
    client.messages.parse(output_format=AgentSignal) — virattt uses
    LangChain's with_structured_output abstraction.
  * Async fan-out via asyncio.gather (Pattern #3) — virattt is sync
    per-ticker. The 6 persona calls are independent (no inter-call data
    flow); parallel completes ~6x faster wall-clock.
  * AgentSignal output (5-state verdict + ≤10 evidence items) — virattt
    emits 3-field signal/confidence/reasoning. AnalystId Literal widened
    in Wave 0 (05-01) lets persona AgentSignals reuse the analytical
    AgentSignal class verbatim (Pattern #9).

Public surface (consumed by Wave 4 synthesizer + Wave 5 entrypoint):
    PERSONA_IDS              — canonical 6-persona iteration order
    PERSONA_MODEL            — "claude-sonnet-4-6" per Pattern #2
    PERSONA_MAX_TOKENS       — 2000 per Pattern #6 estimate
    PERSONA_PROMPT_DIR       — Path("prompts/personas")
    load_persona_prompt(id)  — disk read with lru_cache
    build_persona_user_context(...) — single shared user message per ticker
    run_one(...)             — single-persona LLM call
    run_persona_slate(...)   — async fan-out across all 6

Failure-isolation discipline (Pattern #3):
  * Per-LLM failures (ValidationError / APIStatusError / APIError) are
    absorbed by call_with_retry's default_factory (Wave 2 / 05-03).
  * Per-Python-level uncaught exceptions are absorbed by
    asyncio.gather(return_exceptions=True) + outer slot collapse to
    default-factory; the synthesizer's compute_dissent always sees 6
    AgentSignals every time, in PERSONA_IDS canonical order.
"""
from __future__ import annotations

import asyncio
import functools
from datetime import datetime
from pathlib import Path
from typing import Callable, Literal, get_args

from anthropic import AsyncAnthropic

from analysts.data.snapshot import Snapshot
from analysts.position_signal import PositionSignal
from analysts.schemas import TickerConfig
from analysts.signals import AgentSignal, AnalystId
from routine.llm_client import call_with_retry

PersonaId = Literal[
    "buffett", "munger", "wood", "burry", "lynch", "claude_analyst",
]

PERSONA_IDS: tuple[PersonaId, ...] = (
    "buffett", "munger", "wood", "burry", "lynch", "claude_analyst",
)

PERSONA_MODEL: str = "claude-sonnet-4-6"
PERSONA_MAX_TOKENS: int = 2000
PERSONA_PROMPT_DIR: Path = Path("prompts/personas")


@functools.lru_cache(maxsize=8)
def load_persona_prompt(persona_id: str) -> str:
    """Read prompts/personas/{persona_id}.md from disk; cached.

    Cache size 8 is conservative — 6 personas + headroom. The cache makes
    6xN_TICKERS fan-out a single read per persona regardless of N_TICKERS.

    Raises ValueError if persona_id is not in PERSONA_IDS (defensive: the
    AnalystId Literal validates downstream too, but caller-side error here
    surfaces typos earlier).

    Raises FileNotFoundError if prompts/personas/{persona_id}.md is missing.
    """
    if persona_id not in get_args(AnalystId) or persona_id not in PERSONA_IDS:
        raise ValueError(
            f"unknown persona_id {persona_id!r}; expected one of {PERSONA_IDS}"
        )
    path = PERSONA_PROMPT_DIR / f"{persona_id}.md"
    if not path.exists():
        raise FileNotFoundError(f"persona prompt missing: {path}")
    return path.read_text(encoding="utf-8")


def build_persona_user_context(
    snapshot: Snapshot,
    config: TickerConfig,
    fundamentals_signal: AgentSignal,
    technicals_signal: AgentSignal,
    news_sentiment_signal: AgentSignal,
    valuation_signal: AgentSignal,
    position_signal: PositionSignal,
) -> str:
    """Build the single shared user-message string. Built once per ticker.

    All 6 personas receive the same user_context (saves 6x build cost).
    Per-persona variation is in the SYSTEM prompt (markdown-loaded), not
    the user message.

    Returns deterministic output for identical inputs (no time-of-day
    branches, no dict-iteration ordering).
    """
    lines: list[str] = []
    lines.append(f"Ticker: {snapshot.ticker}")
    lines.append("")
    lines.append("# Snapshot Summary")
    if snapshot.data_unavailable:
        lines.append("data_unavailable=True")
    else:
        lines.append(_summarize_snapshot(snapshot))
    lines.append("")
    lines.append("# Analytical Signals")
    for sig in (fundamentals_signal, technicals_signal,
                news_sentiment_signal, valuation_signal):
        lines.append(_format_signal(sig))
    lines.append("")
    lines.append("# Position Signal")
    lines.append(_format_position_signal(position_signal))
    lines.append("")
    lines.append("# User TickerConfig")
    lines.append(_format_config(config))
    return "\n".join(lines)


def _summarize_snapshot(snapshot: Snapshot) -> str:
    """Compact summary — current price, recent prices summary, fundamentals high-level."""
    parts: list[str] = []
    if snapshot.prices is not None and not snapshot.prices.data_unavailable:
        if snapshot.prices.current_price is not None:
            parts.append(f"current_price={snapshot.prices.current_price}")
        if snapshot.prices.history:
            n = len(snapshot.prices.history)
            first = snapshot.prices.history[0].close
            last = snapshot.prices.history[-1].close
            parts.append(
                f"history: {n} bars, first close ${first:.2f}, last ${last:.2f}"
            )
    if (snapshot.fundamentals is not None
            and not snapshot.fundamentals.data_unavailable):
        f = snapshot.fundamentals
        if f.pe is not None:
            parts.append(f"P/E={f.pe}")
        if f.roe is not None:
            parts.append(f"ROE={f.roe}")
        if f.debt_to_equity is not None:
            parts.append(f"D/E={f.debt_to_equity}")
    return "; ".join(parts) if parts else "(no fundamentals/prices)"


def _format_signal(sig: AgentSignal) -> str:
    return (
        f"- {sig.analyst_id}: {sig.verdict} (conf={sig.confidence}) - "
        + ("; ".join(sig.evidence[:3]) if sig.evidence else "(no evidence)")
        + (" [data_unavailable]" if sig.data_unavailable else "")
    )


def _format_position_signal(p: PositionSignal) -> str:
    if p.data_unavailable:
        return "[data_unavailable]"
    return (
        f"state={p.state}, consensus_score={p.consensus_score:.2f}, "
        f"action_hint={p.action_hint}, confidence={p.confidence}, "
        f"trend_regime={p.trend_regime}"
    )


def _format_config(c: TickerConfig) -> str:
    parts = [
        f"long_term_lens={c.long_term_lens}",
        f"short_term_focus={c.short_term_focus}",
    ]
    if c.thesis_price is not None:
        parts.append(f"thesis_price={c.thesis_price}")
    if c.notes:
        parts.append(f"notes={c.notes[:100]}")
    return "; ".join(parts)


def _persona_default_factory(
    persona_id: PersonaId,
    ticker: str,
    computed_at: datetime,
) -> Callable[[], AgentSignal]:
    """Closure-bound default factory for one (persona, ticker) pair.

    Returned on retry exhaustion by call_with_retry per LLM-05 contract.
    Persona id + ticker + computed_at are captured at call site so each
    factory invocation produces the contextually-correct default.
    """
    def factory() -> AgentSignal:
        return AgentSignal(
            ticker=ticker,
            analyst_id=persona_id,
            computed_at=computed_at,
            verdict="neutral",
            confidence=0,
            evidence=["schema_failure"],
            data_unavailable=True,
        )
    return factory


async def run_one(
    client: AsyncAnthropic,
    persona_id: PersonaId,
    user_context: str,
    ticker: str,
    *,
    computed_at: datetime,
) -> AgentSignal:
    """Single-persona LLM call wrapping call_with_retry (LLM-04 + LLM-05).

    System prompt is loaded from prompts/personas/{persona_id}.md at call
    time (LLM-02 lock: never hardcoded as Python string). The lru_cache on
    load_persona_prompt makes the 6xN_TICKERS fan-out efficient.
    """
    system_prompt = load_persona_prompt(persona_id)
    return await call_with_retry(
        client,
        model=PERSONA_MODEL,
        system=system_prompt,
        user=user_context,
        output_format=AgentSignal,
        default_factory=_persona_default_factory(
            persona_id, ticker, computed_at,
        ),
        max_tokens=PERSONA_MAX_TOKENS,
        context_label=f"{persona_id}:{ticker}",
    )


async def run_persona_slate(
    client: AsyncAnthropic,
    *,
    ticker: str,
    snapshot: Snapshot,
    config: TickerConfig,
    analytical_signals: list[AgentSignal],
    position_signal: PositionSignal,
    computed_at: datetime,
) -> list[AgentSignal]:
    """Async fan-out across the 6 PERSONA_IDS via asyncio.gather (Pattern #3).

    Returns exactly 6 AgentSignals in PERSONA_IDS canonical order. Per-
    persona Python-level exceptions (NOT LLM failures — those are absorbed
    by call_with_retry's default_factory) collapse to the same default-
    factory shape so the synthesizer's compute_dissent always sees 6
    AgentSignals.

    Raises ValueError if analytical_signals does not contain exactly 4
    AgentSignals (defensive — the synthesizer expects fund/tech/nsen/val
    in that fixed order).
    """
    if len(analytical_signals) != 4:
        raise ValueError(
            f"expected 4 analytical_signals (fund/tech/nsen/val); got "
            f"{len(analytical_signals)}"
        )
    fund, tech, nsen, val = analytical_signals
    user_context = build_persona_user_context(
        snapshot, config, fund, tech, nsen, val, position_signal,
    )

    coros = [
        run_one(client, pid, user_context, ticker, computed_at=computed_at)
        for pid in PERSONA_IDS
    ]
    raw_results = await asyncio.gather(*coros, return_exceptions=True)

    # Collapse any uncaught Python-level exception into a default-factory
    # AgentSignal preserving PERSONA_IDS order.
    final: list[AgentSignal] = []
    for pid, r in zip(PERSONA_IDS, raw_results, strict=True):
        if isinstance(r, BaseException):
            final.append(_persona_default_factory(pid, ticker, computed_at)())
        else:
            final.append(r)
    return final
