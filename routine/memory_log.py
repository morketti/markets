# Pattern adapted from routine/llm_client._log_failure (line 167) — same
# atomic JSONL-append discipline (mkdir parents=True; mode="a"; sort_keys=True;
# one record per line). Diverges only in the record schema.
"""routine.memory_log — append-only JSONL writer for per-(ticker, persona)
signal history. INFRA-06 implementation.

Schema (LOCKED — 08-CONTEXT.md):
    {"date": "YYYY-MM-DD", "ticker": "AAPL", "persona_id": "buffett",
     "verdict": "bullish", "confidence": 72, "evidence_count": 3}

Called from routine.run_for_watchlist Phase E after the per-ticker persona
pipeline produces 6 AgentSignals. ~30 tickers × 6 personas = 180 records/day.
~65K records/year ≈ ~10 MB JSONL — append every run (researcher rec #2:
change-detection adds complexity without trivial-storage payoff).

File location (default): memory/historical_signals.jsonl (gitignored).
Tests inject a tmp_path via the log_path parameter.

Validation policy:
    Inputs are validated synchronously and a ValueError is raised on the
    first offence. The schema mirrors AgentSignal's invariants (verdict
    ladder; confidence 0-100; evidence list ≤10 items) so a buggy caller
    cannot pollute the JSONL with shape drift.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Final

DEFAULT_LOG_PATH: Final[Path] = Path("memory/historical_signals.jsonl")

_DATE_RE: Final[re.Pattern[str]] = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_VALID_VERDICTS: Final[frozenset[str]] = frozenset({
    "strong_bullish",
    "bullish",
    "neutral",
    "bearish",
    "strong_bearish",
})


def append_memory_record(
    *,
    date: str,
    ticker: str,
    persona_id: str,
    verdict: str,
    confidence: int,
    evidence_count: int,
    log_path: Path | None = None,
) -> None:
    """Append one record to memory/historical_signals.jsonl.

    Validates inputs synchronously (raises ValueError on invalid). Mirrors
    the _log_failure atomic-append + sort_keys=True discipline.

    Args:
        date: ISO date string YYYY-MM-DD (10 chars, regex-validated).
        ticker: non-empty uppercase ticker (e.g. "AAPL", "BRK-B").
        persona_id: non-empty string (e.g. "buffett", "claude_analyst").
        verdict: one of the 5 ladder values
            (strong_bullish | bullish | neutral | bearish | strong_bearish).
        confidence: int in [0, 100].
        evidence_count: int in [0, 10] (matches AgentSignal max evidence cap).
        log_path: target JSONL file. Defaults to DEFAULT_LOG_PATH; tests
            inject a tmp_path.

    Raises:
        ValueError: any input fails validation. The first offending field
        is named in the message.
    """
    if not _DATE_RE.match(date):
        raise ValueError(f"date must be YYYY-MM-DD, got {date!r}")
    if not ticker or not ticker.isupper():
        raise ValueError(f"ticker must be non-empty uppercase, got {ticker!r}")
    if not persona_id:
        raise ValueError("persona_id required (non-empty string)")
    if verdict not in _VALID_VERDICTS:
        raise ValueError(
            f"verdict must be one of {sorted(_VALID_VERDICTS)}, got {verdict!r}"
        )
    if not isinstance(confidence, int) or not (0 <= confidence <= 100):
        raise ValueError(f"confidence must be int in [0, 100], got {confidence!r}")
    if not isinstance(evidence_count, int) or not (0 <= evidence_count <= 10):
        raise ValueError(
            f"evidence_count must be int in [0, 10], got {evidence_count!r}"
        )

    path = log_path if log_path is not None else DEFAULT_LOG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "date": date,
        "ticker": ticker,
        "persona_id": persona_id,
        "verdict": verdict,
        "confidence": confidence,
        "evidence_count": evidence_count,
    }
    line = json.dumps(record, sort_keys=True) + "\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(line)
