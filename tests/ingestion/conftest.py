"""Shared fixtures for tests/ingestion/.

The `fixtures_dir` fixture points at tests/ingestion/fixtures/ — Wave-2 plans
(02-02..02-05) drop recorded JSON / XML / HTML fixtures into that directory and
read them via `(fixtures_dir / "name").read_text()` etc.
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Return the absolute path to tests/ingestion/fixtures/."""
    return Path(__file__).parent / "fixtures"
