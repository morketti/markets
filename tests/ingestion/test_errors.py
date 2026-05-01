"""Probe 2-W1-03 (errors slice) — exception hierarchy for ingestion."""
from __future__ import annotations

import pytest

from ingestion.errors import IngestionError, NetworkError, SchemaDriftError


# Probe 2-W1-03 — class tree
def test_exception_hierarchy() -> None:
    assert issubclass(IngestionError, Exception)
    assert issubclass(NetworkError, IngestionError)
    assert issubclass(SchemaDriftError, IngestionError)
    # Concrete subclasses do not inherit from each other.
    assert not issubclass(NetworkError, SchemaDriftError)
    assert not issubclass(SchemaDriftError, NetworkError)


def test_exceptions_carry_message() -> None:
    with pytest.raises(NetworkError) as excinfo:
        raise NetworkError("timeout after 10s")
    assert str(excinfo.value) == "timeout after 10s"

    with pytest.raises(SchemaDriftError) as excinfo:
        raise SchemaDriftError("missing field 'open' in OHLC payload")
    assert "missing field" in str(excinfo.value)

    # Catching the base catches all subclasses.
    with pytest.raises(IngestionError):
        raise NetworkError("any")
    with pytest.raises(IngestionError):
        raise SchemaDriftError("any")
