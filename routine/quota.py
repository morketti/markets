"""routine.quota — estimate-run-cost helper + per-call token constants.

Pattern #6 (INFRA-02): conservative pre-run estimate compared against env-
overridable quota; on overshoot, the routine entrypoint sets lite_mode=True
which skips the persona + synthesizer LLM layers (analyticals only).

The constants are tunable (5 sub-fields):
  PERSONA_INPUT_TOKENS_PER_TICKER  = 2000  (~6KB markdown prompt + ~1KB context)
  PERSONA_OUTPUT_TOKENS_PER_TICKER = 300   (~10 evidence items * 100 chars / 4)
  SYNTHESIZER_INPUT_TOKENS_PER_TICKER = 5500  (~3KB prompt + 11 signals + dissent)
  SYNTHESIZER_OUTPUT_TOKENS_PER_TICKER = 500  (TickerDecision JSON ~2KB / 4)
  N_PERSONAS = 6

Locked formula: n_tickers * (N_PERSONAS * (PERSONA_INPUT + PERSONA_OUTPUT)
                              + SYNTHESIZER_INPUT + SYNTHESIZER_OUTPUT)
              = n_tickers * (6 * 2300 + 6000)
              = n_tickers * 19_800

For 30 tickers: 30 * 19800 = 594000 (under 600000 default).
For 31 tickers: 31 * 19800 = 613800 (over default → lite_mode=True).

Tunable via env: MARKETS_DAILY_QUOTA_TOKENS overrides DEFAULT_MARKETS_DAILY_QUOTA_TOKENS.
The env-var read happens in routine/entrypoint.py at run-start; this module
only exports the default constant.

Provenance: novel-to-this-project. The estimate-then-lite-mode pattern is
the project's INFRA-02 design and not adapted from a reference repo.
"""
from __future__ import annotations

from analysts.schemas import Watchlist

# ---------------------------------------------------------------------------
# Per-call token constants — locked per 05-CONTEXT.md "Lite-Mode Token Estimate".
# ---------------------------------------------------------------------------

N_PERSONAS: int = 6
PERSONA_INPUT_TOKENS_PER_TICKER: int = 2000
PERSONA_OUTPUT_TOKENS_PER_TICKER: int = 300
SYNTHESIZER_INPUT_TOKENS_PER_TICKER: int = 5500
SYNTHESIZER_OUTPUT_TOKENS_PER_TICKER: int = 500

# Default daily quota (env-overridable via MARKETS_DAILY_QUOTA_TOKENS).
DEFAULT_MARKETS_DAILY_QUOTA_TOKENS: int = 600_000


def estimate_run_cost(watchlist: Watchlist) -> int:
    """Conservative per-run token estimate. Used by INFRA-02 lite-mode trigger.

    Returns
    -------
    int
        Total estimated tokens for one full run (all personas + synthesizer
        across all watchlist tickers). 0 for empty watchlist.
    """
    n_tickers = len(watchlist.tickers)
    per_ticker = (
        N_PERSONAS
        * (PERSONA_INPUT_TOKENS_PER_TICKER + PERSONA_OUTPUT_TOKENS_PER_TICKER)
        + SYNTHESIZER_INPUT_TOKENS_PER_TICKER
        + SYNTHESIZER_OUTPUT_TOKENS_PER_TICKER
    )
    return n_tickers * per_ticker
