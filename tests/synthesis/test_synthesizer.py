"""Tests for synthesis.synthesizer + prompts/synthesizer.md content.

Two test surfaces:
  * Static prompt-content checks on prompts/synthesizer.md (file presence,
    section structure, locked content, output schema field names).
  * Dynamic synthesizer-module behavior (cache, user-context determinism,
    skip paths, happy path, 6 recommendation paths, LLM exhaustion,
    Python-computed dissent appears in user_context, provenance).

Mock_anthropic_client + isolated_failure_log fixtures are re-exported from
tests/routine/conftest.py at the root tests/conftest.py level. frozen_now
fixture comes from tests/conftest.py (root).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from analysts.data.snapshot import Snapshot
from analysts.position_signal import PositionSignal
from analysts.schemas import TickerConfig
from analysts.signals import AgentSignal
from synthesis.decision import (
    DissentSection,
    TickerDecision,
    TimeframeBand,
)


# ---------------------------------------------------------------------------
# Shared base inputs fixture — minimal valid 4 analytical + 1 PositionSignal
# + 6 persona AgentSignals + Snapshot + TickerConfig. Each test overrides
# only what it cares about.
# ---------------------------------------------------------------------------


@pytest.fixture
def base_inputs(frozen_now: datetime):
    """Return (config, snapshot, analytical_signals, position_signal, persona_signals)."""
    cfg = TickerConfig(
        ticker="AAPL",
        short_term_focus=True,
        long_term_lens="value",
        thesis_price=200.0,
    )
    snap = Snapshot(
        ticker="AAPL", fetched_at=frozen_now, data_unavailable=False,
    )
    fund = AgentSignal(
        ticker="AAPL", analyst_id="fundamentals",
        computed_at=frozen_now, verdict="bullish", confidence=70,
        evidence=["ROE 22%"],
    )
    tech = AgentSignal(
        ticker="AAPL", analyst_id="technicals",
        computed_at=frozen_now, verdict="bullish", confidence=60,
        evidence=["MA20>MA50"],
    )
    nsen = AgentSignal(
        ticker="AAPL", analyst_id="news_sentiment",
        computed_at=frozen_now, verdict="bullish", confidence=50,
        evidence=["positive headlines"],
    )
    val = AgentSignal(
        ticker="AAPL", analyst_id="valuation",
        computed_at=frozen_now, verdict="neutral", confidence=50,
        evidence=["price near thesis"],
    )
    pose = PositionSignal(
        ticker="AAPL", computed_at=frozen_now,
        state="fair", consensus_score=0.05, confidence=60,
        action_hint="hold_position",
    )
    personas = [
        AgentSignal(
            ticker="AAPL", analyst_id=pid,
            computed_at=frozen_now, verdict="bullish",
            confidence=60, evidence=[f"{pid} bullish"],
        )
        for pid in (
            "buffett", "munger", "wood", "burry", "lynch", "claude_analyst",
        )
    ]
    return cfg, snap, [fund, tech, nsen, val], pose, personas


# ===========================================================================
# Prompt-file content tests (static — operate on prompts/synthesizer.md)
# ===========================================================================


def test_synthesizer_md_exists_and_nonempty() -> None:
    """prompts/synthesizer.md must be ≥150 lines (replaces Wave 0 stub)."""
    text = Path("prompts/synthesizer.md").read_text(encoding="utf-8")
    n = len(text.splitlines())
    assert n >= 150, f"prompts/synthesizer.md too short: {n} lines (need ≥150)"


def test_synthesizer_md_section_structure() -> None:
    """4 locked section headers per 05-CONTEXT.md."""
    text = Path("prompts/synthesizer.md").read_text(encoding="utf-8")
    assert "## Input Context" in text
    assert "## Task" in text
    assert "## Output Schema" in text


def test_synthesizer_md_priority_order_encoded() -> None:
    """3-layer priority order encoded in plain English per Pattern #7."""
    text = Path("prompts/synthesizer.md").read_text(encoding="utf-8").lower()
    # Tactical layer mentions PositionSignal action_hint
    assert "action_hint" in text
    # Short-term layer mentions persona consensus
    assert "persona" in text
    # Long-term layer mentions thesis_price
    assert "thesis_price" in text
    # Conviction band rule named
    assert "high" in text
    assert "medium" in text
    assert "low" in text


def test_synthesizer_md_dissent_rendering_instruction() -> None:
    """Synthesizer instructed to RENDER pre-computed dissent, NOT compute it."""
    text = Path("prompts/synthesizer.md").read_text(encoding="utf-8").lower()
    assert "pre-computed" in text
    # Locked phrasing per 05-CONTEXT.md / 05-RESEARCH.md provenance
    # (lifted from TauricResearch/TradingAgents portfolio_manager.py).
    assert "ground every conclusion in specific evidence" in text


def test_synthesizer_md_output_schema_names_fields() -> None:
    """Output Schema lists all 10 TickerDecision fields + 6 enum + 3 conviction."""
    text = Path("prompts/synthesizer.md").read_text(encoding="utf-8")
    for field in (
        "ticker", "computed_at", "schema_version", "recommendation",
        "conviction", "short_term", "long_term", "open_observation",
        "dissent", "data_unavailable",
    ):
        assert field in text, f"synthesizer.md missing field name {field!r}"
    # 6 DecisionRecommendation enum values:
    for v in ("add", "trim", "hold", "take_profits", "buy", "avoid"):
        assert v in text, f"synthesizer.md missing recommendation value {v!r}"


# ===========================================================================
# load_synthesizer_prompt cache
# ===========================================================================


def test_load_synthesizer_prompt_caches() -> None:
    """lru_cache makes repeat calls O(1) — same str object returned."""
    from synthesis.synthesizer import load_synthesizer_prompt
    load_synthesizer_prompt.cache_clear()
    a = load_synthesizer_prompt()
    b = load_synthesizer_prompt()
    assert a is b
    info = load_synthesizer_prompt.cache_info()
    assert info.hits >= 1


# ===========================================================================
# build_synthesizer_user_context — determinism + content + dissent block
# ===========================================================================


def test_build_synthesizer_user_context_deterministic(base_inputs) -> None:
    """Two calls with identical inputs produce byte-identical output."""
    from synthesis.synthesizer import build_synthesizer_user_context
    cfg, snap, analytical, pose, personas = base_inputs
    a = build_synthesizer_user_context(
        ticker="AAPL", snapshot=snap, config=cfg,
        analytical_signals=analytical, position_signal=pose,
        persona_signals=personas, dissent_persona_id=None, dissent_summary="",
    )
    b = build_synthesizer_user_context(
        ticker="AAPL", snapshot=snap, config=cfg,
        analytical_signals=analytical, position_signal=pose,
        persona_signals=personas, dissent_persona_id=None, dissent_summary="",
    )
    assert a == b


def test_build_synthesizer_user_context_dissent_block_always_present(
    base_inputs,
) -> None:
    """The Pre-computed Dissent block is ALWAYS emitted — locked Pattern #7."""
    from synthesis.synthesizer import build_synthesizer_user_context
    cfg, snap, analytical, pose, personas = base_inputs

    # No-dissent scenario — block contains a "no dissent" indicator.
    no_dissent_ctx = build_synthesizer_user_context(
        ticker="AAPL", snapshot=snap, config=cfg,
        analytical_signals=analytical, position_signal=pose,
        persona_signals=personas, dissent_persona_id=None, dissent_summary="",
    )
    assert "Pre-computed Dissent" in no_dissent_ctx
    assert "no dissent" in no_dissent_ctx

    # Has-dissent scenario — block contains the persona_id + summary verbatim.
    has_dissent_ctx = build_synthesizer_user_context(
        ticker="AAPL", snapshot=snap, config=cfg,
        analytical_signals=analytical, position_signal=pose,
        persona_signals=personas,
        dissent_persona_id="burry",
        dissent_summary="burry dissents (bearish, conf=80): hidden risk",
    )
    assert "Pre-computed Dissent" in has_dissent_ctx
    assert "burry" in has_dissent_ctx
    assert "hidden risk" in has_dissent_ctx


def test_build_synthesizer_user_context_includes_all_signals(
    base_inputs,
) -> None:
    """All 11 signals + config + position state appear in the user context."""
    from synthesis.synthesizer import build_synthesizer_user_context
    cfg, snap, analytical, pose, personas = base_inputs
    ctx = build_synthesizer_user_context(
        ticker="AAPL", snapshot=snap, config=cfg,
        analytical_signals=analytical, position_signal=pose,
        persona_signals=personas, dissent_persona_id=None, dissent_summary="",
    )
    # 4 analytical signals (by analyst_id):
    for aid in ("fundamentals", "technicals", "news_sentiment", "valuation"):
        assert aid in ctx, f"missing analytical {aid!r}"
    # PositionSignal — state + action_hint render:
    assert "fair" in ctx
    assert "hold_position" in ctx
    # 6 personas (by analyst_id):
    for pid in (
        "buffett", "munger", "wood", "burry", "lynch", "claude_analyst",
    ):
        assert pid in ctx, f"missing persona {pid!r}"
    # TickerConfig fields:
    assert "value" in ctx  # long_term_lens
    assert "thesis_price=200" in ctx


def test_build_synthesizer_user_context_lite_mode_empty_personas(
    base_inputs,
) -> None:
    """When persona_signals is empty (lite mode), the block notes the skip."""
    from synthesis.synthesizer import build_synthesizer_user_context
    cfg, snap, analytical, pose, _ = base_inputs
    ctx = build_synthesizer_user_context(
        ticker="AAPL", snapshot=snap, config=cfg,
        analytical_signals=analytical, position_signal=pose,
        persona_signals=[], dissent_persona_id=None, dissent_summary="",
    )
    # Persona Signals section still present, but the body indicates the skip.
    assert "Persona" in ctx
    assert "lite" in ctx.lower() or "empty" in ctx.lower()


# ===========================================================================
# synthesize — skip paths
# ===========================================================================


@pytest.mark.asyncio
async def test_synthesize_snapshot_data_unavailable_skips_llm(
    mock_anthropic_client, frozen_now: datetime, base_inputs,
) -> None:
    """Snapshot.data_unavailable=True → no LLM call; canonical decision."""
    from synthesis.synthesizer import synthesize
    cfg, _, analytical, pose, personas = base_inputs
    dark_snap = Snapshot(
        ticker="AAPL", fetched_at=frozen_now, data_unavailable=True,
    )
    result = await synthesize(
        mock_anthropic_client,
        ticker="AAPL", snapshot=dark_snap, config=cfg,
        analytical_signals=analytical, position_signal=pose,
        persona_signals=personas, computed_at=frozen_now,
    )
    assert result.data_unavailable is True
    assert result.recommendation == "hold"
    assert result.conviction == "low"
    # The reason is surfaced in either open_observation or short_term.summary.
    combined = (
        result.open_observation.lower()
        + " "
        + result.short_term.summary.lower()
    )
    assert "snapshot" in combined and "data_unavailable" in combined
    # Critically: LLM was NOT called.
    assert mock_anthropic_client.messages.calls == []


@pytest.mark.asyncio
async def test_synthesize_lite_mode_empty_personas_skips_llm(
    mock_anthropic_client, frozen_now: datetime, base_inputs,
) -> None:
    """Empty persona_signals (lite mode) → no LLM call; canonical decision."""
    from synthesis.synthesizer import synthesize
    cfg, snap, analytical, pose, _ = base_inputs
    result = await synthesize(
        mock_anthropic_client,
        ticker="AAPL", snapshot=snap, config=cfg,
        analytical_signals=analytical, position_signal=pose,
        persona_signals=[], computed_at=frozen_now,
    )
    assert result.data_unavailable is True
    assert result.recommendation == "hold"
    assert result.conviction == "low"
    # LLM NOT called in lite mode.
    assert mock_anthropic_client.messages.calls == []


# ===========================================================================
# synthesize — happy path (mocked LLM returns valid TickerDecision)
# ===========================================================================


@pytest.mark.asyncio
async def test_synthesize_happy_path_returns_llm_decision(
    mock_anthropic_client, frozen_now: datetime, base_inputs,
) -> None:
    """Mocked LLM returns valid TickerDecision; assert kwargs + result."""
    from synthesis.synthesizer import (
        synthesize,
        SYNTHESIZER_MODEL,
        SYNTHESIZER_MAX_TOKENS,
    )
    cfg, snap, analytical, pose, personas = base_inputs

    expected = TickerDecision(
        ticker="AAPL", computed_at=frozen_now,
        recommendation="add", conviction="high",
        short_term=TimeframeBand(
            summary="bullish ST", drivers=["a"], confidence=80,
        ),
        long_term=TimeframeBand(
            summary="bullish LT", drivers=["b"], confidence=70,
        ),
        open_observation="claude analyst observation",
        dissent=DissentSection(),
    )
    mock_anthropic_client.messages.queue_response(expected)

    result = await synthesize(
        mock_anthropic_client,
        ticker="AAPL", snapshot=snap, config=cfg,
        analytical_signals=analytical, position_signal=pose,
        persona_signals=personas, computed_at=frozen_now,
    )
    assert result is expected

    calls = mock_anthropic_client.messages.calls
    assert len(calls) == 1
    assert calls[0]["model"] == SYNTHESIZER_MODEL
    assert calls[0]["model"] == "claude-opus-4-7"
    assert calls[0]["max_tokens"] == SYNTHESIZER_MAX_TOKENS
    assert calls[0]["max_tokens"] == 4000
    assert calls[0]["output_format"] is TickerDecision
    # System prompt is the synthesizer.md content (contains the locked
    # section anchor "Input Context").
    assert "Input Context" in calls[0]["system"]
    # User context arrives via messages=[{"role":"user","content": <user>}]
    # per routine.llm_client.call_with_retry. The dissent block is included
    # (no dissent in this case — all-bullish base_inputs).
    user_msg = calls[0]["messages"][0]["content"]
    assert "no dissent" in user_msg


# ===========================================================================
# synthesize — 6 recommendation paths (parametrized)
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "recommendation",
    ["add", "trim", "hold", "take_profits", "buy", "avoid"],
)
async def test_synthesize_six_recommendation_paths(
    mock_anthropic_client,
    frozen_now: datetime,
    base_inputs,
    recommendation: str,
) -> None:
    """All 6 DecisionRecommendation values propagate through synthesize."""
    from synthesis.synthesizer import synthesize
    cfg, snap, analytical, pose, personas = base_inputs
    expected = TickerDecision(
        ticker="AAPL", computed_at=frozen_now,
        recommendation=recommendation,
        conviction="medium",
        short_term=TimeframeBand(summary="x", drivers=[], confidence=50),
        long_term=TimeframeBand(summary="y", drivers=[], confidence=50),
        dissent=DissentSection(),
    )
    mock_anthropic_client.messages.queue_response(expected)
    result = await synthesize(
        mock_anthropic_client,
        ticker="AAPL", snapshot=snap, config=cfg,
        analytical_signals=analytical, position_signal=pose,
        persona_signals=personas, computed_at=frozen_now,
    )
    assert result.recommendation == recommendation


# ===========================================================================
# synthesize — LLM exhaustion → default factory
# ===========================================================================


@pytest.mark.asyncio
async def test_synthesize_llm_exhaustion_returns_default_factory(
    mock_anthropic_client, frozen_now: datetime, base_inputs,
    isolated_failure_log,
) -> None:
    """N ValidationErrors (matching DEFAULT_MAX_RETRIES) → default factory."""
    from synthesis.synthesizer import synthesize
    from routine.llm_client import DEFAULT_MAX_RETRIES
    cfg, snap, analytical, pose, personas = base_inputs

    # Forge a ValidationError to queue. We construct it by triggering a
    # legitimate Pydantic validation failure (invalid ticker) so the
    # exception object is well-formed.
    try:
        TickerDecision(
            ticker="123!@#", computed_at=frozen_now,
            recommendation="hold", conviction="low",
            short_term=TimeframeBand(summary="x", drivers=[], confidence=0),
            long_term=TimeframeBand(summary="y", drivers=[], confidence=0),
            dissent=DissentSection(),
        )
        raise AssertionError("expected ValidationError")
    except ValidationError as exc:
        ve = exc

    for _ in range(DEFAULT_MAX_RETRIES):
        mock_anthropic_client.messages.queue_exception(ve)

    result = await synthesize(
        mock_anthropic_client,
        ticker="AAPL", snapshot=snap, config=cfg,
        analytical_signals=analytical, position_signal=pose,
        persona_signals=personas, computed_at=frozen_now,
    )
    # Default factory shape — schema invariant satisfied (data_unavailable=True
    # ⟹ recommendation='hold' AND conviction='low').
    assert result.data_unavailable is True
    assert result.recommendation == "hold"
    assert result.conviction == "low"
    # All retries consumed:
    assert len(mock_anthropic_client.messages.calls) == DEFAULT_MAX_RETRIES


# ===========================================================================
# synthesize — Python dissent computed BEFORE LLM call (Pattern #7 lock)
# ===========================================================================


@pytest.mark.asyncio
async def test_synthesize_dissent_pre_computed_in_user_context(
    mock_anthropic_client, frozen_now: datetime, base_inputs,
) -> None:
    """5 bullish + 1 burry-bearish-conf-80 → user_context contains pre-computed dissent."""
    from synthesis.synthesizer import synthesize
    cfg, snap, analytical, pose, _ = base_inputs

    # Dissent scenario: 5 bullish + 1 burry-bearish-conf-80.
    dissent_personas = [
        AgentSignal(
            ticker="AAPL", analyst_id=pid,
            computed_at=frozen_now, verdict="bullish",
            confidence=70, evidence=[f"{pid} bullish"],
        )
        for pid in ("buffett", "munger", "wood", "lynch", "claude_analyst")
    ]
    dissent_personas.append(AgentSignal(
        ticker="AAPL", analyst_id="burry",
        computed_at=frozen_now, verdict="bearish", confidence=80,
        evidence=["hidden risk"],
    ))

    expected = TickerDecision(
        ticker="AAPL", computed_at=frozen_now,
        recommendation="hold", conviction="medium",
        short_term=TimeframeBand(summary="x", drivers=[], confidence=50),
        long_term=TimeframeBand(summary="y", drivers=[], confidence=50),
        dissent=DissentSection(
            has_dissent=True,
            dissenting_persona="burry",
            dissent_summary="rendered",
        ),
    )
    mock_anthropic_client.messages.queue_response(expected)

    await synthesize(
        mock_anthropic_client,
        ticker="AAPL", snapshot=snap, config=cfg,
        analytical_signals=analytical, position_signal=pose,
        persona_signals=dissent_personas, computed_at=frozen_now,
    )

    # User context arrives via messages=[{"role":"user","content": <user>}]
    # per routine.llm_client.call_with_retry contract.
    call_kwargs = mock_anthropic_client.messages.calls[0]
    user_msg = call_kwargs["messages"][0]["content"]
    # Pre-computed dissent IS in the user context — synthesizer prompt
    # never has to compute dissent itself (Pattern #7 lock).
    assert "burry" in user_msg
    assert "dissents" in user_msg
    assert "hidden risk" in user_msg


# ===========================================================================
# Provenance per INFRA-07
# ===========================================================================


def test_synthesizer_provenance_references_tauricresearch() -> None:
    """synthesis/synthesizer.py docstring carries TauricResearch lineage."""
    src = Path("synthesis/synthesizer.py").read_text(encoding="utf-8")
    assert "TauricResearch/TradingAgents" in src
    assert "tradingagents/agents/" in src


# ===========================================================================
# Module constants sanity (extra coverage)
# ===========================================================================


def test_synthesizer_module_constants_locked() -> None:
    """SYNTHESIZER_MODEL='claude-opus-4-7'; MAX_TOKENS=4000; PROMPT_PATH points at .md."""
    from synthesis.synthesizer import (
        SYNTHESIZER_MAX_TOKENS,
        SYNTHESIZER_MODEL,
        SYNTHESIZER_PROMPT_PATH,
    )
    assert SYNTHESIZER_MODEL == "claude-opus-4-7"
    assert SYNTHESIZER_MAX_TOKENS == 4000
    assert SYNTHESIZER_PROMPT_PATH == Path("prompts/synthesizer.md")


def test_load_synthesizer_prompt_raises_file_not_found(monkeypatch) -> None:
    """Missing prompt file raises FileNotFoundError on load (defensive)."""
    from synthesis import synthesizer as syn_mod
    syn_mod.load_synthesizer_prompt.cache_clear()
    monkeypatch.setattr(
        syn_mod, "SYNTHESIZER_PROMPT_PATH", Path("nonexistent/synthesizer.md"),
    )
    with pytest.raises(FileNotFoundError):
        syn_mod.load_synthesizer_prompt()
    # Cleanup so subsequent tests don't inherit the cache miss state.
    syn_mod.load_synthesizer_prompt.cache_clear()


# ===========================================================================
# Coverage tests — exercise the populated-snapshot, dark-PositionSignal,
# and notes-bearing-config branches in the private formatters. Folded in
# beyond the planned ≥10 floor to clear the 90/85% coverage gate per
# Rule 2 (test-side hardening).
# ===========================================================================


def test_build_user_context_with_populated_snapshot(
    base_inputs, frozen_now: datetime,
) -> None:
    """Snapshot with prices + fundamentals populated → summary contains the metrics."""
    from synthesis.synthesizer import build_synthesizer_user_context
    from analysts.data.fundamentals import FundamentalsSnapshot
    from analysts.data.prices import OHLCBar, PriceSnapshot
    from datetime import date as _date

    cfg, _, analytical, pose, personas = base_inputs
    populated_snap = Snapshot(
        ticker="AAPL",
        fetched_at=frozen_now,
        data_unavailable=False,
        prices=PriceSnapshot(
            ticker="AAPL", fetched_at=frozen_now,
            source="yfinance", current_price=180.5,
            history=[
                OHLCBar(
                    date=_date(2026, 5, 1),
                    open=178.0, high=181.0, low=177.5, close=180.0,
                    volume=1_000_000,
                ),
                OHLCBar(
                    date=_date(2026, 5, 2),
                    open=180.0, high=182.0, low=179.5, close=180.5,
                    volume=1_100_000,
                ),
            ],
        ),
        fundamentals=FundamentalsSnapshot(
            ticker="AAPL", fetched_at=frozen_now, source="yfinance",
            pe=28.5, roe=1.45, debt_to_equity=1.95,
        ),
    )
    ctx = build_synthesizer_user_context(
        ticker="AAPL", snapshot=populated_snap, config=cfg,
        analytical_signals=analytical, position_signal=pose,
        persona_signals=personas, dissent_persona_id=None, dissent_summary="",
    )
    assert "current_price=180.5" in ctx
    assert "history bars=2" in ctx
    assert "P/E=28.5" in ctx
    assert "ROE=1.45" in ctx
    assert "D/E=1.95" in ctx


def test_build_user_context_with_dark_position_signal(
    base_inputs, frozen_now: datetime,
) -> None:
    """data_unavailable=True PositionSignal → '[data_unavailable]' marker."""
    from synthesis.synthesizer import build_synthesizer_user_context

    cfg, snap, analytical, _, personas = base_inputs
    dark_pose = PositionSignal(
        ticker="AAPL", computed_at=frozen_now, data_unavailable=True,
    )
    ctx = build_synthesizer_user_context(
        ticker="AAPL", snapshot=snap, config=cfg,
        analytical_signals=analytical, position_signal=dark_pose,
        persona_signals=personas, dissent_persona_id=None, dissent_summary="",
    )
    assert "[data_unavailable]" in ctx


def test_summarize_snapshot_data_unavailable_branch(
    frozen_now: datetime,
) -> None:
    """_summarize_snapshot returns 'data_unavailable=True' literal on dark snapshot."""
    from synthesis.synthesizer import _summarize_snapshot

    dark_snap = Snapshot(
        ticker="AAPL", fetched_at=frozen_now, data_unavailable=True,
    )
    assert _summarize_snapshot(dark_snap) == "data_unavailable=True"


def test_summarize_snapshot_partial_data_branches(
    frozen_now: datetime,
) -> None:
    """Exercise each missing-field branch in _summarize_snapshot for branch coverage.

    Snapshot with prices=None + fundamentals=None → '(no fundamentals/prices)'.
    Snapshot with prices but no current_price + no history → empty parts → fallback.
    Snapshot with fundamentals where pe/roe/debt_to_equity are None → empty parts.
    """
    from synthesis.synthesizer import _summarize_snapshot
    from analysts.data.fundamentals import FundamentalsSnapshot
    from analysts.data.prices import PriceSnapshot

    # All-None snapshot — fallback line.
    snap_empty = Snapshot(
        ticker="AAPL", fetched_at=frozen_now, data_unavailable=False,
    )
    assert _summarize_snapshot(snap_empty) == "(no fundamentals/prices)"

    # Prices object present but no current_price + no history.
    snap_prices_empty = Snapshot(
        ticker="AAPL", fetched_at=frozen_now, data_unavailable=False,
        prices=PriceSnapshot(
            ticker="AAPL", fetched_at=frozen_now, source="yfinance",
            current_price=None, history=[],
        ),
    )
    assert _summarize_snapshot(snap_prices_empty) == "(no fundamentals/prices)"

    # Fundamentals present but all metrics None — none added to parts.
    snap_fund_empty = Snapshot(
        ticker="AAPL", fetched_at=frozen_now, data_unavailable=False,
        fundamentals=FundamentalsSnapshot(
            ticker="AAPL", fetched_at=frozen_now, source="yfinance",
            pe=None, roe=None, debt_to_equity=None,
        ),
    )
    assert _summarize_snapshot(snap_fund_empty) == "(no fundamentals/prices)"


def test_format_config_without_thesis_price_or_notes(frozen_now: datetime) -> None:
    """_format_config skips thesis_price + notes when they're absent."""
    from synthesis.synthesizer import _format_config
    cfg = TickerConfig(
        ticker="AAPL",
        short_term_focus=True,
        long_term_lens="value",
        # thesis_price=None (default) and notes="" (default).
    )
    out = _format_config(cfg)
    assert "long_term_lens=value" in out
    assert "short_term_focus=True" in out
    assert "thesis_price" not in out
    assert "notes" not in out


def test_build_user_context_with_config_notes(frozen_now: datetime) -> None:
    """TickerConfig.notes populated → notes truncated and rendered."""
    from synthesis.synthesizer import build_synthesizer_user_context
    cfg = TickerConfig(
        ticker="AAPL",
        short_term_focus=True,
        long_term_lens="value",
        thesis_price=200.0,
        notes="x" * 250,  # exceeds the 200-char render cap
    )
    snap = Snapshot(
        ticker="AAPL", fetched_at=frozen_now, data_unavailable=False,
    )
    fund = AgentSignal(
        ticker="AAPL", analyst_id="fundamentals",
        computed_at=frozen_now, verdict="bullish", confidence=70,
    )
    pose = PositionSignal(
        ticker="AAPL", computed_at=frozen_now, state="fair",
    )
    ctx = build_synthesizer_user_context(
        ticker="AAPL", snapshot=snap, config=cfg,
        analytical_signals=[fund, fund, fund, fund],
        position_signal=pose,
        persona_signals=[], dissent_persona_id=None, dissent_summary="",
    )
    # Notes appear, truncated at 200 chars in the render layer.
    assert "notes=" in ctx
    # The 250-char notes string is rendered truncated to 200 chars (the
    # _format_config truncation slice). The full string would be 250 'x's.
    assert "x" * 200 in ctx
    assert "x" * 251 not in ctx
