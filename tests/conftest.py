"""Shared pytest fixtures for the markets test suite.

Fixtures here are imported by tests in:
- tests/test_schemas.py     (Plan 02)
- tests/test_loader.py      (Plan 03)
- tests/test_cli_add.py     (Plan 04)
- tests/test_cli_remove.py  (Plan 04)
- tests/test_cli_errors.py  (Plan 04)
- tests/test_cli_readonly.py (Plan 05)
- tests/synthesis/test_decision.py (Phase 5 / Plan 02 — TickerDecision schema)

The fixtures import schemas lazily so this conftest collects cleanly even
before Plan 02 lands the schema module.

The `frozen_now` fixture is lifted here so tests/synthesis/ + tests/routine/
(Phase 5) inherit it without re-declaring. tests/analysts/conftest.py
continues to host its own `frozen_now` (and the analyst-specific
synthetic_*_history builders) — pytest fixture resolution picks the closest
one in the directory tree, so Phase 3+4 analyst tests are unaffected.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Pinned UTC datetime — same constant as tests/analysts/conftest.py FROZEN_DT
# (kept in sync deliberately; both surfaces resolve to the same instant so
# Phase 3+4 tests and Phase 5 tests share a deterministic clock).
FROZEN_DT = datetime(2026, 5, 1, 13, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def frozen_now() -> datetime:
    """Pinned UTC datetime — pass as `computed_at=` for byte-stable assertions."""
    return FROZEN_DT


@pytest.fixture
def empty_watchlist_path(tmp_path: Path) -> Path:
    """Returns a path to a non-existent watchlist file in a tmp directory."""
    return tmp_path / "watchlist.json"


@pytest.fixture
def seeded_watchlist_path(tmp_path: Path) -> Path:
    """Returns a path to a 3-ticker watchlist file (AAPL value, NVDA growth, BRK-B value).

    Note: BRK-B uses HYPHEN (not BRK.B) — yfinance compatibility per 01-RESEARCH.md
    correction. The schema normalizes inputs to hyphen form.
    """
    from analysts.schemas import TickerConfig, Watchlist

    path = tmp_path / "watchlist.json"
    wl = Watchlist(
        tickers={
            "AAPL": TickerConfig(ticker="AAPL", long_term_lens="value", thesis_price=200.0),
            "NVDA": TickerConfig(ticker="NVDA", long_term_lens="growth"),
            "BRK-B": TickerConfig(ticker="BRK-B", long_term_lens="value"),
        }
    )
    # Per 01-RESEARCH.md correction #3: use json.dumps(... sort_keys=True) for deterministic output
    payload = json.dumps(wl.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    path.write_text(payload, encoding="utf-8")
    return path


@pytest.fixture
def large_watchlist_path(tmp_path: Path) -> Path:
    """Returns a path to a 35-ticker synthetic watchlist (for WATCH-01 30+ probe)."""
    from analysts.schemas import TickerConfig, Watchlist

    path = tmp_path / "watchlist.json"
    sample = [
        "AAPL", "MSFT", "NVDA", "GOOG", "AMZN", "META", "TSLA", "BRK-B", "JPM", "V",
        "XOM", "UNH", "JNJ", "PG", "HD", "MA", "CVX", "ABBV", "KO", "PFE",
        "PEP", "WMT", "BAC", "TMO", "COST", "DIS", "CRM", "ORCL", "NKE", "ADBE",
        "AMD", "NFLX", "INTC", "CSCO", "QCOM",
    ]
    wl = Watchlist(tickers={t: TickerConfig(ticker=t) for t in sample})
    payload = json.dumps(wl.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    path.write_text(payload, encoding="utf-8")
    return path
