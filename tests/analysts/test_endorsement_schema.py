"""Tests for analysts.endorsement_schema.Endorsement (Phase 9 / Plan 01 / Task 1).

Locks the LOAD-BEARING schema_version: Literal[1] = 1 contract — v1.x ENDORSE-04..07
will bump to Literal[2] non-breakingly (v1 readers cannot silently misread future
records as "0% performance"). Mirrors analysts/schemas.py + analysts/data/* Pydantic
v2 discipline (extra="forbid", field_validator for ticker normalization).

Requirements covered: ENDORSE-01.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from analysts.endorsement_schema import Endorsement


def _kwargs(**overrides: object) -> dict[str, object]:
    """Build a minimal-valid Endorsement kwarg dict; tests override fields."""
    base: dict[str, object] = {
        "ticker": "AAPL",
        "source": "Motley Fool",
        "date": date(2026, 4, 15),
        "price_at_call": 178.42,
        "captured_at": datetime(2026, 5, 4, 19, 26, 39, tzinfo=timezone.utc),
    }
    base.update(overrides)
    return base


def test_happy_minimal() -> None:
    """Required fields only → valid; notes defaults to ''."""
    e = Endorsement(**_kwargs())
    assert e.ticker == "AAPL"
    assert e.source == "Motley Fool"
    assert e.date == date(2026, 4, 15)
    assert e.price_at_call == 178.42
    assert e.notes == ""
    assert e.schema_version == 1


def test_happy_full() -> None:
    """All fields including notes → valid."""
    e = Endorsement(**_kwargs(notes="10-bagger thesis around Vision Pro adoption"))
    assert e.notes == "10-bagger thesis around Vision Pro adoption"


def test_schema_version_default_is_1() -> None:
    """Omitting schema_version → instance has schema_version == 1 (locked default)."""
    e = Endorsement(**_kwargs())
    assert e.schema_version == 1


def test_schema_version_locked_rejects_2() -> None:
    """schema_version=2 → ValidationError (Literal[1] mismatch — v1.x lock)."""
    with pytest.raises(ValidationError) as exc:
        Endorsement(**_kwargs(schema_version=2))
    assert "schema_version" in str(exc.value)


def test_schema_version_locked_rejects_0() -> None:
    """schema_version=0 → ValidationError."""
    with pytest.raises(ValidationError):
        Endorsement(**_kwargs(schema_version=0))


def test_ticker_normalized_brk_b() -> None:
    """ticker='brk.b' → instance.ticker == 'BRK-B' (normalize_ticker reuse)."""
    e = Endorsement(**_kwargs(ticker="brk.b"))
    assert e.ticker == "BRK-B"


def test_ticker_normalized_aapl_lower() -> None:
    """ticker='aapl' → 'AAPL'."""
    e = Endorsement(**_kwargs(ticker="aapl"))
    assert e.ticker == "AAPL"


def test_ticker_invalid_raises() -> None:
    """ticker='!!!' → ValidationError naming 'ticker'."""
    with pytest.raises(ValidationError) as exc:
        Endorsement(**_kwargs(ticker="!!!"))
    assert "ticker" in str(exc.value)


def test_price_must_be_positive_zero() -> None:
    """price_at_call=0 → ValidationError (gt=0)."""
    with pytest.raises(ValidationError):
        Endorsement(**_kwargs(price_at_call=0))


def test_price_must_be_positive_negative() -> None:
    """price_at_call=-1 → ValidationError (gt=0)."""
    with pytest.raises(ValidationError):
        Endorsement(**_kwargs(price_at_call=-1))


def test_source_min_length_blank_rejects() -> None:
    """source='' → ValidationError (min_length=1)."""
    with pytest.raises(ValidationError):
        Endorsement(**_kwargs(source=""))


def test_source_one_char_ok() -> None:
    """source='x' → ok (min_length=1)."""
    e = Endorsement(**_kwargs(source="x"))
    assert e.source == "x"


def test_notes_max_length_2000_ok() -> None:
    """notes='a' * 2000 → ok (max_length=2000)."""
    e = Endorsement(**_kwargs(notes="a" * 2000))
    assert len(e.notes) == 2000


def test_notes_max_length_2001_rejects() -> None:
    """notes='a' * 2001 → ValidationError (max_length=2000)."""
    with pytest.raises(ValidationError):
        Endorsement(**_kwargs(notes="a" * 2001))


def test_extra_field_forbidden() -> None:
    """Endorsement(..., bogus='x') → ValidationError (extra='forbid')."""
    with pytest.raises(ValidationError):
        Endorsement(**_kwargs(bogus="x"))


def test_date_field_is_python_date() -> None:
    """date=date(2026, 4, 15) → instance.date is a datetime.date."""
    e = Endorsement(**_kwargs(date=date(2026, 4, 15)))
    assert isinstance(e.date, date)
    assert e.date.isoformat() == "2026-04-15"


def test_model_dump_json_roundtrip() -> None:
    """Endorsement.model_validate_json(e.model_dump_json()) round-trips equal."""
    e1 = Endorsement(**_kwargs(notes="round trip test"))
    e2 = Endorsement.model_validate_json(e1.model_dump_json())
    assert e1 == e2
