"""Integration tests for `markets add_endorsement` subcommand (Phase 9 / Plan 01 / Task 1).

Mirrors tests/test_cli_add.py discipline: invoke via cli.main.main(argv=[...]) so the
SUBCOMMANDS dispatcher is exercised; assert exit codes + file contents.

Requirements covered: ENDORSE-01, ENDORSE-02.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

import cli.main as cli_main
from cli.add_endorsement import add_endorsement_command, build_add_endorsement_parser
from cli.main import main


@pytest.fixture
def tmp_endorsements_path(tmp_path: Path) -> Path:
    return tmp_path / "endorsements.jsonl"


def test_subcommand_registered() -> None:
    """cli.main.SUBCOMMANDS['add_endorsement'] points to (build, command) tuple."""
    assert "add_endorsement" in cli_main.SUBCOMMANDS
    build, handler = cli_main.SUBCOMMANDS["add_endorsement"]
    assert build is build_add_endorsement_parser
    assert handler is add_endorsement_command


def test_happy_path(tmp_endorsements_path: Path) -> None:
    """All flags → exit 0; endorsements.jsonl has 1 line; line parses back."""
    rc = main([
        "add_endorsement",
        "--ticker", "AAPL",
        "--source", "Motley Fool",
        "--date", "2026-04-15",
        "--price", "178.42",
        "--notes", "10-bagger thesis",
        "--path", str(tmp_endorsements_path),
    ])
    assert rc == 0
    assert tmp_endorsements_path.exists()
    lines = tmp_endorsements_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["ticker"] == "AAPL"
    assert rec["source"] == "Motley Fool"
    assert rec["date"] == "2026-04-15"
    assert rec["price_at_call"] == 178.42
    assert rec["notes"] == "10-bagger thesis"
    assert rec["schema_version"] == 1


def test_ticker_normalized(tmp_endorsements_path: Path) -> None:
    """--ticker brk.b → file contains 'ticker': 'BRK-B'."""
    rc = main([
        "add_endorsement",
        "--ticker", "brk.b",
        "--source", "Newsletter",
        "--date", "2026-04-15",
        "--price", "500.0",
        "--path", str(tmp_endorsements_path),
    ])
    assert rc == 0
    rec = json.loads(tmp_endorsements_path.read_text(encoding="utf-8").splitlines()[0])
    assert rec["ticker"] == "BRK-B"


def test_default_notes_empty(tmp_endorsements_path: Path) -> None:
    """Omit --notes → file contains 'notes': ''."""
    rc = main([
        "add_endorsement",
        "--ticker", "AAPL",
        "--source", "Newsletter",
        "--date", "2026-04-15",
        "--price", "178.42",
        "--path", str(tmp_endorsements_path),
    ])
    assert rc == 0
    rec = json.loads(tmp_endorsements_path.read_text(encoding="utf-8").splitlines()[0])
    assert rec["notes"] == ""


def test_invalid_ticker_exits_2(tmp_endorsements_path: Path) -> None:
    """--ticker '!!!' → exit 2; file UNCHANGED (or absent — atomic-on-success)."""
    rc = main([
        "add_endorsement",
        "--ticker", "!!!",
        "--source", "Newsletter",
        "--date", "2026-04-15",
        "--price", "178.42",
        "--path", str(tmp_endorsements_path),
    ])
    assert rc == 2
    # File must NOT have been written (atomic-on-success — Pydantic raised before append).
    assert not tmp_endorsements_path.exists()


def test_invalid_price_exits_2(tmp_endorsements_path: Path) -> None:
    """--price -42 → exit 2 (Pydantic ValidationError)."""
    rc = main([
        "add_endorsement",
        "--ticker", "AAPL",
        "--source", "Newsletter",
        "--date", "2026-04-15",
        "--price", "-42",
        "--path", str(tmp_endorsements_path),
    ])
    assert rc == 2
    assert not tmp_endorsements_path.exists()


def test_invalid_date_exits_2(tmp_endorsements_path: Path) -> None:
    """--date 'not-a-date' → exit 2; file UNCHANGED."""
    rc = main([
        "add_endorsement",
        "--ticker", "AAPL",
        "--source", "Newsletter",
        "--date", "not-a-date",
        "--price", "178.42",
        "--path", str(tmp_endorsements_path),
    ])
    assert rc == 2
    assert not tmp_endorsements_path.exists()


def test_blank_source_exits_2(tmp_endorsements_path: Path) -> None:
    """--source '' → exit 2; file UNCHANGED."""
    rc = main([
        "add_endorsement",
        "--ticker", "AAPL",
        "--source", "",
        "--date", "2026-04-15",
        "--price", "178.42",
        "--path", str(tmp_endorsements_path),
    ])
    assert rc == 2
    assert not tmp_endorsements_path.exists()


def test_captured_at_auto_populated(tmp_endorsements_path: Path) -> None:
    """Happy path → record's captured_at is parseable as ISO 8601 UTC datetime within last 60s."""
    before = datetime.now(timezone.utc)
    rc = main([
        "add_endorsement",
        "--ticker", "AAPL",
        "--source", "Newsletter",
        "--date", "2026-04-15",
        "--price", "178.42",
        "--path", str(tmp_endorsements_path),
    ])
    after = datetime.now(timezone.utc)
    assert rc == 0
    rec = json.loads(tmp_endorsements_path.read_text(encoding="utf-8").splitlines()[0])
    captured_at_str = rec["captured_at"]
    captured_at = datetime.fromisoformat(captured_at_str)
    # Must be UTC-aware
    assert captured_at.tzinfo is not None
    # Must be within the (before, after) bracket
    assert before <= captured_at <= after


def test_atomic_on_failure(tmp_endorsements_path: Path) -> None:
    """Invalid input on a SECOND call after a successful first call → file unchanged after fail."""
    rc1 = main([
        "add_endorsement",
        "--ticker", "AAPL",
        "--source", "First",
        "--date", "2026-04-15",
        "--price", "178.42",
        "--path", str(tmp_endorsements_path),
    ])
    assert rc1 == 0
    assert len(tmp_endorsements_path.read_text(encoding="utf-8").splitlines()) == 1

    rc2 = main([
        "add_endorsement",
        "--ticker", "!!!",  # invalid
        "--source", "Second",
        "--date", "2026-04-15",
        "--price", "178.42",
        "--path", str(tmp_endorsements_path),
    ])
    assert rc2 == 2
    # File still has exactly 1 line — failed call did not append.
    assert len(tmp_endorsements_path.read_text(encoding="utf-8").splitlines()) == 1
