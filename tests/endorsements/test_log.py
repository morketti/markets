"""Tests for endorsements.log (Phase 9 / Plan 01 / Task 1).

Mirrors routine.memory_log discipline tests: atomic-append + sort_keys + skip-blank
on load + Pydantic round-trip.

Requirements covered: ENDORSE-01.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from analysts.endorsement_schema import Endorsement
from endorsements.log import append_endorsement, load_endorsements


@pytest.fixture
def tmp_endorsements_path(tmp_path: Path) -> Path:
    """Per-test endorsements.jsonl path (no parent mkdir needed — tmp_path exists)."""
    return tmp_path / "endorsements.jsonl"


def _make(**overrides: object) -> Endorsement:
    base: dict[str, object] = {
        "ticker": "AAPL",
        "source": "Motley Fool",
        "date": date(2026, 4, 15),
        "price_at_call": 178.42,
        "captured_at": datetime(2026, 5, 4, 19, 26, 39, tzinfo=timezone.utc),
    }
    base.update(overrides)
    return Endorsement(**base)


def test_append_creates_file(tmp_endorsements_path: Path) -> None:
    """Empty path → first append creates the file with one JSON line + trailing newline."""
    e = _make()
    append_endorsement(e, path=tmp_endorsements_path)
    assert tmp_endorsements_path.exists()
    content = tmp_endorsements_path.read_text(encoding="utf-8")
    assert content.endswith("\n")
    assert len(content.splitlines()) == 1


def test_append_appends_to_existing(tmp_endorsements_path: Path) -> None:
    """Second append leaves first line intact + adds second."""
    e1 = _make(source="Motley Fool")
    e2 = _make(source="Seeking Alpha")
    append_endorsement(e1, path=tmp_endorsements_path)
    append_endorsement(e2, path=tmp_endorsements_path)
    lines = tmp_endorsements_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    rec1 = json.loads(lines[0])
    rec2 = json.loads(lines[1])
    assert rec1["source"] == "Motley Fool"
    assert rec2["source"] == "Seeking Alpha"


def test_append_writes_sort_keys(tmp_endorsements_path: Path) -> None:
    """Line is json.dumps(..., sort_keys=True) so keys are alphabetical."""
    e = _make()
    append_endorsement(e, path=tmp_endorsements_path)
    line = tmp_endorsements_path.read_text(encoding="utf-8").rstrip("\n")
    # Parse keys preserving order (json preserves insertion order in py3.7+).
    rec = json.loads(line)
    keys = list(rec.keys())
    assert keys == sorted(keys), f"keys not sorted: {keys}"
    # Hard-check: 'captured_at' (alphabetically first) precedes 'ticker' (last).
    assert keys[0] == "captured_at"
    assert keys[-1] == "ticker"


def test_load_returns_empty_when_file_missing(tmp_endorsements_path: Path) -> None:
    """load_endorsements(missing_path) → []."""
    assert not tmp_endorsements_path.exists()
    result = load_endorsements(path=tmp_endorsements_path)
    assert result == []


def test_load_skips_blank_lines(tmp_endorsements_path: Path) -> None:
    """File with `{...}\\n\\n{...}\\n` parses to 2 records."""
    e1 = _make(source="A")
    e2 = _make(source="B")
    append_endorsement(e1, path=tmp_endorsements_path)
    # Inject a blank line manually
    with tmp_endorsements_path.open("a", encoding="utf-8") as f:
        f.write("\n")
    append_endorsement(e2, path=tmp_endorsements_path)

    loaded = load_endorsements(path=tmp_endorsements_path)
    assert len(loaded) == 2
    assert loaded[0].source == "A"
    assert loaded[1].source == "B"


def test_load_validates_each_line(tmp_endorsements_path: Path) -> None:
    """File with one malformed JSON line → ValidationError raised on load."""
    e = _make()
    append_endorsement(e, path=tmp_endorsements_path)
    # Inject a malformed-from-Pydantic line
    bad = {"ticker": "!!!", "source": "x", "date": "2026-04-15",
           "price_at_call": 1.0, "notes": "", "captured_at": "2026-05-04T00:00:00+00:00",
           "schema_version": 1}
    with tmp_endorsements_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(bad) + "\n")

    with pytest.raises(ValidationError):
        load_endorsements(path=tmp_endorsements_path)


def test_round_trip_via_pydantic(tmp_endorsements_path: Path) -> None:
    """Append e1, e2; load → [e1, e2] preserving field equality."""
    e1 = _make(ticker="AAPL", source="A", price_at_call=100.0)
    e2 = _make(ticker="MSFT", source="B", price_at_call=420.5,
               date=date(2026, 4, 1))
    append_endorsement(e1, path=tmp_endorsements_path)
    append_endorsement(e2, path=tmp_endorsements_path)
    loaded = load_endorsements(path=tmp_endorsements_path)
    assert loaded == [e1, e2]
