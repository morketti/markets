"""Tests for routine.persona_runner — async fan-out across 6 personas.

Mocks AsyncAnthropic via tests/routine/conftest.py mock_anthropic_client
fixture (Wave 2 fixture-replay). The 6 persona markdown files are loaded
from disk; tests assert their structure + content.

Test groups:
  1. Persona file presence + 5-section structure (parametrized over 6 IDs)
  2. Voice signature keywords per persona (LLM-03 anchors)
  3. Output schema names AgentSignal fields verbatim
  4. claude_analyst.md explicit "NOT a persona" framing per user MEMORY.md
  5. PERSONA_IDS canonical iteration order + AnalystId Literal subset
  6. load_persona_prompt — disk read + lru_cache + invalid id rejection
  7. build_persona_user_context — content + determinism
  8. run_one — happy path
  9. run_one — default_factory on validation failure
  10. run_persona_slate — fan-out, 6 calls, order preserved
  11. run_persona_slate — single-persona failure isolation
  12. run_persona_slate — input validation
  13. provenance per INFRA-07
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from analysts.signals import AgentSignal


PERSONA_IDS_TUPLE = (
    "buffett", "munger", "wood", "burry", "lynch", "claude_analyst",
)
PERSONA_NAMES = {
    "buffett": "Warren Buffett",
    "munger": "Charlie Munger",
    "wood": "Cathie Wood",
    "burry": "Michael Burry",
    "lynch": "Peter Lynch",
    "claude_analyst": "Open Claude Analyst",
}
PERSONA_VOICE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "buffett": ("owner earnings", "moat", "margin of safety"),
    "munger": ("mental model", "invert"),
    "wood": ("disruptive innovation", "exponential"),
    "burry": ("contrarian",),
    "lynch": ("PEG", "10-bagger"),
    "claude_analyst": ("NOT a", "Claude", "inherent"),
}


# ---------------------------------------------------------------------------
# Test 1: persona file presence + ≥80 lines
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("persona_id", PERSONA_IDS_TUPLE)
def test_persona_file_exists_and_nonempty(persona_id):
    path = Path(f"prompts/personas/{persona_id}.md")
    assert path.exists(), f"missing persona file: {path}"
    text = path.read_text(encoding="utf-8")
    line_count = len(text.splitlines())
    assert line_count >= 80, (
        f"{path}: expected >=80 lines, got {line_count}"
    )


# ---------------------------------------------------------------------------
# Test 2: 5-section locked structure (H1 + 4 ## sections)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("persona_id", PERSONA_IDS_TUPLE)
def test_persona_file_has_5_section_structure(persona_id):
    text = Path(f"prompts/personas/{persona_id}.md").read_text(encoding="utf-8")
    h1 = f"# Persona: {PERSONA_NAMES[persona_id]}"
    assert h1 in text, f"{persona_id}: missing H1 {h1!r}"
    for section in ("## Voice Signature", "## Input Context",
                    "## Task", "## Output Schema"):
        assert section in text, f"{persona_id}: missing section {section!r}"


# ---------------------------------------------------------------------------
# Test 3: Voice Signature keywords (LLM-03 + Pattern #5 anchors)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("persona_id", PERSONA_IDS_TUPLE)
def test_persona_voice_signature_keywords(persona_id):
    """Voice signature contains persona-specific anchors per LLM-03."""
    text = Path(f"prompts/personas/{persona_id}.md").read_text(encoding="utf-8")
    m = re.search(
        r"## Voice Signature\n(.*?)(?=\n## )",
        text, flags=re.DOTALL,
    )
    assert m is not None, f"{persona_id}: cannot extract Voice Signature section"
    section = m.group(1)
    for keyword in PERSONA_VOICE_KEYWORDS[persona_id]:
        assert keyword.lower() in section.lower(), (
            f"{persona_id}: Voice Signature missing keyword {keyword!r}"
        )


# ---------------------------------------------------------------------------
# Test 4: claude_analyst.md explicit "NOT a persona" framing per user MEMORY.md
# ---------------------------------------------------------------------------

def test_claude_analyst_explicitly_not_a_persona():
    """User MEMORY.md feedback_claude_knowledge: 'NOT a persona, NOT a lens'."""
    text = Path("prompts/personas/claude_analyst.md").read_text(encoding="utf-8")
    assert "NOT a" in text, (
        "claude_analyst.md must explicitly say 'NOT a persona' or similar"
    )
    assert "Claude" in text
    assert ("inherent" in text.lower() or "general financial" in text.lower())
    # Provenance: explicitly novel-to-this-project (no virattt analog)
    assert ("no virattt analog" in text.lower()
            or "novel-to-this-project" in text.lower()), (
        "claude_analyst.md must declare novelty (no virattt analog)"
    )


# ---------------------------------------------------------------------------
# Test 5: Output Schema names AgentSignal fields verbatim
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("persona_id", PERSONA_IDS_TUPLE)
def test_persona_output_schema_names_agentsignal_fields(persona_id):
    text = Path(f"prompts/personas/{persona_id}.md").read_text(encoding="utf-8")
    m = re.search(r"## Output Schema\n(.*)$", text, flags=re.DOTALL)
    assert m is not None
    schema = m.group(1)
    for field in ("ticker", "analyst_id", "verdict", "confidence",
                  "evidence", "data_unavailable"):
        assert field in schema, (
            f"{persona_id}: Output Schema missing field {field!r}"
        )
    # 5-state Verdict ladder named verbatim:
    assert "strong_bullish" in schema
    assert "strong_bearish" in schema
    # analyst_id locked to this persona
    assert f'"{persona_id}"' in schema or f"'{persona_id}'" in schema or f"`{persona_id}`" in schema


# ---------------------------------------------------------------------------
# Test 6: PERSONA_IDS canonical order + AnalystId subset
# ---------------------------------------------------------------------------

def test_persona_ids_canonical_order():
    from routine.persona_runner import PERSONA_IDS
    assert PERSONA_IDS == PERSONA_IDS_TUPLE
    assert isinstance(PERSONA_IDS, tuple)


def test_persona_ids_subset_of_widened_analyst_id():
    from typing import get_args
    from analysts.signals import AnalystId
    from routine.persona_runner import PERSONA_IDS

    analyst_id_values = set(get_args(AnalystId))
    for pid in PERSONA_IDS:
        assert pid in analyst_id_values, (
            f"persona id {pid!r} not in widened AnalystId Literal"
        )


def test_persona_runner_module_constants():
    from pathlib import Path as _Path
    from routine.persona_runner import (
        PERSONA_MODEL,
        PERSONA_MAX_TOKENS,
        PERSONA_PROMPT_DIR,
    )
    assert PERSONA_MODEL == "claude-sonnet-4-6"
    assert PERSONA_MAX_TOKENS == 2000
    assert PERSONA_PROMPT_DIR == _Path("prompts/personas")


# ---------------------------------------------------------------------------
# Test 7: load_persona_prompt — disk read + lru_cache + invalid id
# ---------------------------------------------------------------------------

def test_load_persona_prompt_reads_file():
    from routine.persona_runner import load_persona_prompt
    load_persona_prompt.cache_clear()
    text = load_persona_prompt("buffett")
    assert "Warren Buffett" in text
    assert "## Voice Signature" in text


def test_load_persona_prompt_caches_repeat_calls():
    from routine.persona_runner import load_persona_prompt
    load_persona_prompt.cache_clear()
    t1 = load_persona_prompt("munger")
    t2 = load_persona_prompt("munger")
    assert t1 is t2
    info = load_persona_prompt.cache_info()
    assert info.hits >= 1


def test_load_persona_prompt_rejects_unknown_id():
    from routine.persona_runner import load_persona_prompt
    load_persona_prompt.cache_clear()
    with pytest.raises(ValueError) as exc_info:
        load_persona_prompt("not_a_persona")
    assert "not_a_persona" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test 8: build_persona_user_context — content + determinism
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_inputs(frozen_now):
    """Provide minimal valid Snapshot + TickerConfig + 4 AgentSignals + PositionSignal."""
    from analysts.position_signal import PositionSignal
    from analysts.schemas import TickerConfig
    from analysts.data.snapshot import Snapshot

    cfg = TickerConfig(ticker="AAPL", short_term_focus=True, long_term_lens="value")
    snap = Snapshot(ticker="AAPL", fetched_at=frozen_now, data_unavailable=True)
    fund = AgentSignal(
        ticker="AAPL", analyst_id="fundamentals",
        computed_at=frozen_now, verdict="bullish", confidence=70,
        evidence=["ROE 22%", "low D/E"],
    )
    tech = AgentSignal(
        ticker="AAPL", analyst_id="technicals",
        computed_at=frozen_now, verdict="neutral", confidence=40,
        evidence=["mixed momentum"],
    )
    nsen = AgentSignal(
        ticker="AAPL", analyst_id="news_sentiment",
        computed_at=frozen_now, verdict="bullish", confidence=55,
        evidence=["positive headline flow"],
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
    return cfg, snap, fund, tech, nsen, val, pose


def test_build_persona_user_context_nonempty_contains_ticker(sample_inputs):
    from routine.persona_runner import build_persona_user_context
    cfg, snap, fund, tech, nsen, val, pose = sample_inputs
    ctx = build_persona_user_context(snap, cfg, fund, tech, nsen, val, pose)
    assert isinstance(ctx, str) and ctx
    assert "AAPL" in ctx
    # Each analytical signal verdict surfaces
    assert "fundamentals" in ctx and "bullish" in ctx
    assert "technicals" in ctx
    assert "news_sentiment" in ctx
    assert "valuation" in ctx
    # PositionSignal surfaces
    assert "fair" in ctx
    assert "hold_position" in ctx
    # Config surfaces (long_term_lens="value")
    assert "value" in ctx


def test_build_persona_user_context_deterministic(sample_inputs):
    from routine.persona_runner import build_persona_user_context
    cfg, snap, fund, tech, nsen, val, pose = sample_inputs
    a = build_persona_user_context(snap, cfg, fund, tech, nsen, val, pose)
    b = build_persona_user_context(snap, cfg, fund, tech, nsen, val, pose)
    assert a == b


# ---------------------------------------------------------------------------
# Test 9: run_one — happy path
# ---------------------------------------------------------------------------

async def test_run_one_happy_path(mock_anthropic_client, frozen_now):
    from routine.persona_runner import run_one, PERSONA_MODEL, PERSONA_MAX_TOKENS

    expected = AgentSignal(
        ticker="AAPL", analyst_id="buffett", computed_at=frozen_now,
        verdict="bullish", confidence=70, evidence=["moat intact"],
    )
    mock_anthropic_client.messages.queue_response(expected)

    result = await run_one(
        mock_anthropic_client, "buffett", "user context", "AAPL",
        computed_at=frozen_now,
    )
    assert result is expected
    calls = mock_anthropic_client.messages.calls
    assert len(calls) == 1
    assert calls[0]["model"] == PERSONA_MODEL
    assert calls[0]["max_tokens"] == PERSONA_MAX_TOKENS
    assert calls[0]["output_format"] is AgentSignal
    # System prompt is the buffett.md content
    assert "Warren Buffett" in calls[0]["system"]
    assert "## Voice Signature" in calls[0]["system"]


# ---------------------------------------------------------------------------
# Test 10: run_one — default_factory on validation failure
# ---------------------------------------------------------------------------

async def test_run_one_default_factory_on_validation_failure(
    mock_anthropic_client, frozen_now,
):
    from routine.persona_runner import run_one
    from routine.llm_client import DEFAULT_MAX_RETRIES

    try:
        AgentSignal(
            ticker="!!!", analyst_id="buffett",
            computed_at=datetime.now(timezone.utc),
        )
    except ValidationError as exc:
        ve = exc

    for _ in range(DEFAULT_MAX_RETRIES):
        mock_anthropic_client.messages.queue_exception(ve)

    result = await run_one(
        mock_anthropic_client, "buffett", "user context", "AAPL",
        computed_at=frozen_now,
    )
    assert result.ticker == "AAPL"
    assert result.analyst_id == "buffett"
    assert result.computed_at == frozen_now
    assert result.verdict == "neutral"
    assert result.confidence == 0
    assert result.evidence == ["schema_failure"]
    assert result.data_unavailable is True


# ---------------------------------------------------------------------------
# Test 11: run_persona_slate — fan-out, 6 calls, order preserved
# ---------------------------------------------------------------------------

async def test_run_persona_slate_fan_out_order_preserved(
    mock_anthropic_client, frozen_now, sample_inputs,
):
    from routine.persona_runner import run_persona_slate, PERSONA_IDS

    cfg, snap, fund, tech, nsen, val, pose = sample_inputs
    verdict_by_pid = {
        "buffett": "bullish",
        "munger": "neutral",
        "wood": "strong_bullish",
        "burry": "bearish",
        "lynch": "bullish",
        "claude_analyst": "neutral",
    }
    for pid in PERSONA_IDS:
        sig = AgentSignal(
            ticker="AAPL", analyst_id=pid,
            computed_at=frozen_now, verdict=verdict_by_pid[pid],
            confidence=50, evidence=[f"{pid} evidence"],
        )
        mock_anthropic_client.messages.queue_response(sig)

    results = await run_persona_slate(
        mock_anthropic_client,
        ticker="AAPL", snapshot=snap, config=cfg,
        analytical_signals=[fund, tech, nsen, val],
        position_signal=pose, computed_at=frozen_now,
    )

    assert len(results) == 6
    for i, pid in enumerate(PERSONA_IDS):
        assert results[i].analyst_id == pid, (
            f"order mismatch at index {i}: expected {pid}, got {results[i].analyst_id}"
        )
        assert results[i].verdict == verdict_by_pid[pid]

    # 6 distinct system prompts (one per persona)
    systems = [c["system"] for c in mock_anthropic_client.messages.calls]
    assert len(systems) == 6
    assert len(set(systems)) == 6


# ---------------------------------------------------------------------------
# Test 12: run_persona_slate — single-persona failure isolation
# ---------------------------------------------------------------------------

async def test_run_persona_slate_single_failure_isolation(
    mock_anthropic_client, frozen_now, sample_inputs,
):
    """One persona's call_with_retry exhausts -> default_factory; other 5 succeed."""
    from routine.persona_runner import run_persona_slate, PERSONA_IDS
    from routine.llm_client import DEFAULT_MAX_RETRIES

    cfg, snap, fund, tech, nsen, val, pose = sample_inputs

    try:
        AgentSignal(ticker="!!!", analyst_id="buffett",
                    computed_at=datetime.now(timezone.utc))
    except ValidationError as exc:
        ve = exc

    for pid in PERSONA_IDS:
        if pid == "wood":
            for _ in range(DEFAULT_MAX_RETRIES):
                mock_anthropic_client.messages.queue_exception(ve)
        else:
            sig = AgentSignal(
                ticker="AAPL", analyst_id=pid,
                computed_at=frozen_now, verdict="bullish",
                confidence=50, evidence=[f"{pid} evidence"],
            )
            mock_anthropic_client.messages.queue_response(sig)

    results = await run_persona_slate(
        mock_anthropic_client,
        ticker="AAPL", snapshot=snap, config=cfg,
        analytical_signals=[fund, tech, nsen, val],
        position_signal=pose, computed_at=frozen_now,
    )

    assert len(results) == 6
    for i, pid in enumerate(PERSONA_IDS):
        assert results[i].analyst_id == pid
        if pid == "wood":
            assert results[i].verdict == "neutral"
            assert results[i].data_unavailable is True
            assert results[i].evidence == ["schema_failure"]
        else:
            assert results[i].verdict == "bullish"
            assert results[i].data_unavailable is False


# ---------------------------------------------------------------------------
# Test 13: run_persona_slate — input validation
# ---------------------------------------------------------------------------

async def test_run_persona_slate_rejects_wrong_signal_count(
    mock_anthropic_client, frozen_now, sample_inputs,
):
    from routine.persona_runner import run_persona_slate
    cfg, snap, fund, tech, nsen, val, pose = sample_inputs
    with pytest.raises(ValueError, match="4 analytical_signals"):
        await run_persona_slate(
            mock_anthropic_client,
            ticker="AAPL", snapshot=snap, config=cfg,
            analytical_signals=[fund, tech, nsen],  # 3, not 4
            position_signal=pose, computed_at=frozen_now,
        )


# ---------------------------------------------------------------------------
# Test 14: provenance per INFRA-07
# ---------------------------------------------------------------------------

def test_provenance_header_references_virattt():
    src = Path("routine/persona_runner.py").read_text(encoding="utf-8")
    assert "virattt/ai-hedge-fund/src/agents/" in src
    assert ("warren_buffett.py" in src
            or "charlie_munger.py" in src
            or "cathie_wood.py" in src
            or "michael_burry.py" in src
            or "peter_lynch.py" in src)
