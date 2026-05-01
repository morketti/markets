"""Shared pytest fixtures for the markets test suite.

Fixtures here are imported by tests in:
- tests/test_schemas.py     (Plan 02)
- tests/test_loader.py      (Plan 03)
- tests/test_cli_add.py     (Plan 04)
- tests/test_cli_remove.py  (Plan 04)
- tests/test_cli_errors.py  (Plan 04)
- tests/test_cli_readonly.py (Plan 05)

The fixtures import schemas lazily so this conftest collects cleanly even
before Plan 02 lands the schema module.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


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
