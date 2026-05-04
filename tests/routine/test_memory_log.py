"""Tests for routine.memory_log — INFRA-06 append-only JSONL writer.

Schema (LOCKED — 08-CONTEXT.md):
    {"date": "YYYY-MM-DD", "ticker": "AAPL", "persona_id": "buffett",
     "verdict": "bullish", "confidence": 72, "evidence_count": 3}

Mirrors routine.llm_client._log_failure atomic-append pattern verbatim
(mkdir parents=True, mode='a', sort_keys=True, one record per line).

Phase 8 / Plan 08-01 / Task 2.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# 1. Single record produces exactly one valid JSONL line.
# ---------------------------------------------------------------------------


def test_append_single_record_writes_one_jsonl_line(tmp_path: Path) -> None:
    """Single append → file exists, one line, parses to expected dict."""
    from routine.memory_log import append_memory_record

    log_path = tmp_path / "memory" / "historical_signals.jsonl"
    append_memory_record(
        date="2026-05-04",
        ticker="AAPL",
        persona_id="buffett",
        verdict="bullish",
        confidence=72,
        evidence_count=3,
        log_path=log_path,
    )

    assert log_path.exists()
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record == {
        "date": "2026-05-04",
        "ticker": "AAPL",
        "persona_id": "buffett",
        "verdict": "bullish",
        "confidence": 72,
        "evidence_count": 3,
    }


# ---------------------------------------------------------------------------
# 2. Multiple records append (NOT overwrite) and preserve order.
# ---------------------------------------------------------------------------


def test_multiple_records_append_not_overwrite(tmp_path: Path) -> None:
    """Two calls produce two lines; iteration order matches call order."""
    from routine.memory_log import append_memory_record

    log_path = tmp_path / "log.jsonl"
    append_memory_record(
        date="2026-05-04",
        ticker="AAPL",
        persona_id="buffett",
        verdict="bullish",
        confidence=72,
        evidence_count=3,
        log_path=log_path,
    )
    append_memory_record(
        date="2026-05-04",
        ticker="MSFT",
        persona_id="munger",
        verdict="neutral",
        confidence=50,
        evidence_count=2,
        log_path=log_path,
    )

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    rec1 = json.loads(lines[0])
    rec2 = json.loads(lines[1])
    assert rec1["ticker"] == "AAPL"
    assert rec1["persona_id"] == "buffett"
    assert rec2["ticker"] == "MSFT"
    assert rec2["persona_id"] == "munger"


# ---------------------------------------------------------------------------
# 3. Parent directory auto-created.
# ---------------------------------------------------------------------------


def test_parent_directory_auto_created(tmp_path: Path) -> None:
    """Path under non-existent parent dirs → mkdir(parents=True) creates the chain."""
    from routine.memory_log import append_memory_record

    log_path = tmp_path / "new" / "deep" / "dir" / "file.jsonl"
    assert not log_path.parent.exists()

    append_memory_record(
        date="2026-05-04",
        ticker="AAPL",
        persona_id="buffett",
        verdict="bullish",
        confidence=72,
        evidence_count=3,
        log_path=log_path,
    )
    assert log_path.exists()
    assert log_path.parent.is_dir()


# ---------------------------------------------------------------------------
# 4. sort_keys=True produces byte-identical lines for the same record.
# ---------------------------------------------------------------------------


def test_sort_keys_stable_serialization(tmp_path: Path) -> None:
    """Two appends of the same logical record → byte-identical lines.

    Mirrors the _log_failure sort_keys=True discipline so memory log
    diffs are noise-free across runs.
    """
    from routine.memory_log import append_memory_record

    log_path = tmp_path / "log.jsonl"
    for _ in range(2):
        append_memory_record(
            date="2026-05-04",
            ticker="AAPL",
            persona_id="buffett",
            verdict="bullish",
            confidence=72,
            evidence_count=3,
            log_path=log_path,
        )

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert lines[0] == lines[1]


# ---------------------------------------------------------------------------
# 5. Schema strictness — invalid confidence / verdict raises ValueError.
# ---------------------------------------------------------------------------


def test_rejects_invalid_confidence_negative(tmp_path: Path) -> None:
    from routine.memory_log import append_memory_record

    log_path = tmp_path / "log.jsonl"
    with pytest.raises(ValueError, match="confidence"):
        append_memory_record(
            date="2026-05-04",
            ticker="AAPL",
            persona_id="buffett",
            verdict="bullish",
            confidence=-1,
            evidence_count=3,
            log_path=log_path,
        )


def test_rejects_invalid_confidence_over_100(tmp_path: Path) -> None:
    from routine.memory_log import append_memory_record

    log_path = tmp_path / "log.jsonl"
    with pytest.raises(ValueError, match="confidence"):
        append_memory_record(
            date="2026-05-04",
            ticker="AAPL",
            persona_id="buffett",
            verdict="bullish",
            confidence=101,
            evidence_count=3,
            log_path=log_path,
        )


def test_rejects_invalid_verdict(tmp_path: Path) -> None:
    from routine.memory_log import append_memory_record

    log_path = tmp_path / "log.jsonl"
    with pytest.raises(ValueError, match="verdict"):
        append_memory_record(
            date="2026-05-04",
            ticker="AAPL",
            persona_id="buffett",
            verdict="invalid",
            confidence=50,
            evidence_count=3,
            log_path=log_path,
        )


# ---------------------------------------------------------------------------
# 6. Evidence count must be 0-10 (matches AgentSignal max_length=10 cap).
# ---------------------------------------------------------------------------


def test_rejects_evidence_count_over_10(tmp_path: Path) -> None:
    from routine.memory_log import append_memory_record

    log_path = tmp_path / "log.jsonl"
    with pytest.raises(ValueError, match="evidence_count"):
        append_memory_record(
            date="2026-05-04",
            ticker="AAPL",
            persona_id="buffett",
            verdict="bullish",
            confidence=72,
            evidence_count=11,
            log_path=log_path,
        )


# ---------------------------------------------------------------------------
# 7. Date format strictness — must be YYYY-MM-DD (10 chars, regex match).
# ---------------------------------------------------------------------------


def test_rejects_loose_date_format(tmp_path: Path) -> None:
    from routine.memory_log import append_memory_record

    log_path = tmp_path / "log.jsonl"
    with pytest.raises(ValueError, match="date"):
        append_memory_record(
            date="2026-5-4",  # missing zero-padding
            ticker="AAPL",
            persona_id="buffett",
            verdict="bullish",
            confidence=72,
            evidence_count=3,
            log_path=log_path,
        )


# ---------------------------------------------------------------------------
# 8. Default log path is exposed via DEFAULT_LOG_PATH module constant.
# ---------------------------------------------------------------------------


def test_default_log_path_constant() -> None:
    from routine.memory_log import DEFAULT_LOG_PATH

    assert DEFAULT_LOG_PATH == Path("memory/historical_signals.jsonl")


# ---------------------------------------------------------------------------
# 9. Ticker must be non-empty uppercase.
# ---------------------------------------------------------------------------


def test_rejects_lowercase_ticker(tmp_path: Path) -> None:
    from routine.memory_log import append_memory_record

    log_path = tmp_path / "log.jsonl"
    with pytest.raises(ValueError, match="ticker"):
        append_memory_record(
            date="2026-05-04",
            ticker="aapl",
            persona_id="buffett",
            verdict="bullish",
            confidence=72,
            evidence_count=3,
            log_path=log_path,
        )


def test_rejects_empty_ticker(tmp_path: Path) -> None:
    from routine.memory_log import append_memory_record

    log_path = tmp_path / "log.jsonl"
    with pytest.raises(ValueError, match="ticker"):
        append_memory_record(
            date="2026-05-04",
            ticker="",
            persona_id="buffett",
            verdict="bullish",
            confidence=72,
            evidence_count=3,
            log_path=log_path,
        )


# ---------------------------------------------------------------------------
# 10. Persona_id must be non-empty.
# ---------------------------------------------------------------------------


def test_rejects_empty_persona_id(tmp_path: Path) -> None:
    from routine.memory_log import append_memory_record

    log_path = tmp_path / "log.jsonl"
    with pytest.raises(ValueError, match="persona_id"):
        append_memory_record(
            date="2026-05-04",
            ticker="AAPL",
            persona_id="",
            verdict="bullish",
            confidence=72,
            evidence_count=3,
            log_path=log_path,
        )
