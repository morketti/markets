"""Tests for routine.quota — token-cost estimator + 5 per-call constants.

Verifies the locked formula:
    estimate_run_cost(watchlist) =
        n_tickers * (N_PERSONAS * (PERSONA_INPUT + PERSONA_OUTPUT)
                     + SYNTHESIZER_INPUT + SYNTHESIZER_OUTPUT)
    = n_tickers * (6 * 2300 + 6000)
    = n_tickers * 19_800

DEFAULT_MARKETS_DAILY_QUOTA_TOKENS = 600_000:
  * 30 tickers → 594_000 (under quota; lite_mode=False)
  * 31 tickers → 613_800 (over quota; lite_mode=True)
"""
from __future__ import annotations

import pytest


def test_constants_locked() -> None:
    """5 per-call constants + DEFAULT quota all match Pattern #6 spec exactly."""
    from routine.quota import (
        DEFAULT_MARKETS_DAILY_QUOTA_TOKENS,
        N_PERSONAS,
        PERSONA_INPUT_TOKENS_PER_TICKER,
        PERSONA_OUTPUT_TOKENS_PER_TICKER,
        SYNTHESIZER_INPUT_TOKENS_PER_TICKER,
        SYNTHESIZER_OUTPUT_TOKENS_PER_TICKER,
    )

    assert N_PERSONAS == 6
    assert PERSONA_INPUT_TOKENS_PER_TICKER == 2000
    assert PERSONA_OUTPUT_TOKENS_PER_TICKER == 300
    assert SYNTHESIZER_INPUT_TOKENS_PER_TICKER == 5500
    assert SYNTHESIZER_OUTPUT_TOKENS_PER_TICKER == 500
    assert DEFAULT_MARKETS_DAILY_QUOTA_TOKENS == 600_000


def test_empty_watchlist_returns_zero() -> None:
    """estimate_run_cost on empty Watchlist (0 tickers) → 0 tokens."""
    from analysts.schemas import Watchlist

    from routine.quota import estimate_run_cost

    wl = Watchlist()
    assert estimate_run_cost(wl) == 0


def test_30_ticker_estimate_under_default_quota() -> None:
    """30-ticker watchlist → 594_000 tokens (< 600_000 default → lite_mode=False)."""
    from analysts.schemas import TickerConfig, Watchlist

    from routine.quota import DEFAULT_MARKETS_DAILY_QUOTA_TOKENS, estimate_run_cost

    sample = [
        "AAPL", "MSFT", "NVDA", "GOOG", "AMZN",
        "META", "TSLA", "JPM", "V", "JNJ",
        "PG", "HD", "MA", "CVX", "ABBV",
        "KO", "PFE", "PEP", "WMT", "BAC",
        "TMO", "COST", "DIS", "CRM", "ORCL",
        "NKE", "ADBE", "AMD", "NFLX", "INTC",
    ]
    wl = Watchlist(tickers={t: TickerConfig(ticker=t) for t in sample})
    assert len(wl.tickers) == 30
    assert estimate_run_cost(wl) == 594_000
    assert estimate_run_cost(wl) < DEFAULT_MARKETS_DAILY_QUOTA_TOKENS


def test_31_ticker_estimate_exceeds_default_quota() -> None:
    """31-ticker watchlist → 613_800 tokens (> 600_000 → lite_mode triggers)."""
    from analysts.schemas import TickerConfig, Watchlist

    from routine.quota import DEFAULT_MARKETS_DAILY_QUOTA_TOKENS, estimate_run_cost

    sample = [
        "AAPL", "MSFT", "NVDA", "GOOG", "AMZN",
        "META", "TSLA", "JPM", "V", "JNJ",
        "PG", "HD", "MA", "CVX", "ABBV",
        "KO", "PFE", "PEP", "WMT", "BAC",
        "TMO", "COST", "DIS", "CRM", "ORCL",
        "NKE", "ADBE", "AMD", "NFLX", "INTC",
        "QCOM",
    ]
    wl = Watchlist(tickers={t: TickerConfig(ticker=t) for t in sample})
    assert len(wl.tickers) == 31
    assert estimate_run_cost(wl) == 613_800
    assert estimate_run_cost(wl) > DEFAULT_MARKETS_DAILY_QUOTA_TOKENS


@pytest.mark.parametrize("n_tickers", [1, 5, 10, 30])
def test_estimate_formula_correctness(n_tickers: int) -> None:
    """Locked formula: n_tickers * 19_800 (= 6 * 2300 + 6000)."""
    from analysts.schemas import TickerConfig, Watchlist

    from routine.quota import estimate_run_cost

    # Synthesize a watchlist with n_tickers entries (deterministic naming).
    base = ["AAPL", "MSFT", "NVDA", "GOOG", "AMZN",
            "META", "TSLA", "JPM", "V", "JNJ",
            "PG", "HD", "MA", "CVX", "ABBV",
            "KO", "PFE", "PEP", "WMT", "BAC",
            "TMO", "COST", "DIS", "CRM", "ORCL",
            "NKE", "ADBE", "AMD", "NFLX", "INTC"]
    pick = base[:n_tickers]
    wl = Watchlist(tickers={t: TickerConfig(ticker=t) for t in pick})
    assert estimate_run_cost(wl) == n_tickers * 19_800
