"""routine.storage — three-phase atomic write per Pattern #4.

Order (locked, not-up-for-debate):
  Phase A: per-ticker JSONs at data/{date}/{TICKER}.json — atomic per file.
  Phase B: data/{date}/_index.json (run metadata + completed-ticker list).
  Phase C: data/{date}/_status.json — written LAST as the "run is final"
           sentinel. Phase 6 frontend reads _status.json first; if absent,
           the snapshot is in-progress (or the routine crashed mid-write)
           and the frontend renders "snapshot pending" rather than
           potentially-corrupt partial data.

Per-file atomic write reuses the watchlist/loader.save_watchlist +
ingestion/refresh._write_snapshot internal-precedent pattern: NamedTemporaryFile
+ os.replace + sort_keys=True serialization. Internal-precedent provenance
(Phase 1/2 atomic-write); NOT external (no virattt or TauricResearch pattern
adapted for the storage layer specifically).

Per-ticker write failure handling (LLM-08 cascade-prevention): if
_atomic_write_json raises OSError on a ticker, that ticker is appended
to failed_tickers; the loop continues; subsequent _index + _status reflect
the failure but the routine still produces output for the other 29 tickers.

llm_failure_count formula: count persona AgentSignals with data_unavailable=True
(across all completed tickers) + add 1 per ticker where ticker_decision is
None AND lite_mode=False (synthesizer failure; lite_mode skips synthesizer
by design and is NOT counted as a failure).

Public surface (consumed by routine.entrypoint):
    StorageOutcome           — frozen dataclass {completed, failed, llm_failure_count}
    write_daily_snapshot()   — three-phase A→B→C write
    write_failure_status()   — best-effort failure _status.json (entrypoint exception path)
    _atomic_write_json()     — single-file atomic write helper
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from routine.run_for_watchlist import TickerResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StorageOutcome:
    """Return value of write_daily_snapshot — what landed and what didn't."""

    completed: list[str]
    failed: list[str]
    llm_failure_count: int


def _atomic_write_json(path: Path, payload: dict) -> None:
    """Atomic write — tempfile + os.replace + sort_keys=True (Phase 1/2 lock).

    Mirrors watchlist/loader.save_watchlist + ingestion/refresh._write_snapshot.

    On os.replace failure: unlink the tmp file then re-raise — no orphan .tmp
    file in the parent directory. This matches Phase 1's atomic-write contract
    exactly.

    JSON serialization uses sort_keys=True + indent=2 + trailing LF for
    byte-stable output (Phase 1/2 lock).
    """
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
        dir=parent,
        prefix=path.name + ".",
        suffix=".tmp",
    ) as tmp:
        tmp.write(text)
        tmp_path = Path(tmp.name)
    # Handle is closed; safe to rename on Windows.
    try:
        os.replace(tmp_path, path)
    except OSError:
        tmp_path.unlink(missing_ok=True)
        raise


def _build_ticker_payload(r: "TickerResult") -> dict:
    """Serialize a TickerResult into the locked per-ticker JSON shape.

    Per 05-CONTEXT.md storage-format lock:
      {ticker, schema_version=1, analytical_signals, position_signal,
       persona_signals, ticker_decision, errors}
    """
    return {
        "ticker": r.ticker,
        "schema_version": 1,
        "analytical_signals": [
            s.model_dump(mode="json") for s in r.analytical_signals
        ],
        "position_signal": (
            r.position_signal.model_dump(mode="json")
            if r.position_signal is not None
            else None
        ),
        "persona_signals": [
            s.model_dump(mode="json") for s in r.persona_signals
        ],
        "ticker_decision": (
            r.ticker_decision.model_dump(mode="json")
            if r.ticker_decision is not None
            else None
        ),
        "errors": list(r.errors),
    }


def write_daily_snapshot(
    results: list["TickerResult"],
    *,
    date_str: str,
    run_started_at: datetime,
    run_completed_at: datetime,
    lite_mode: bool,
    total_token_count_estimate: int,
    snapshots_root: Path = Path("data"),
) -> StorageOutcome:
    """Three-phase write: per-ticker → _index → _status (LAST). Returns outcome.

    Phase A: per-ticker JSONs. Per-ticker write failures populate failed_tickers
    WITHOUT aborting the loop (LLM-08 cascade-prevention).

    Phase B: _index.json with completed tickers + run metadata.

    Phase C: _status.json — written LAST as the run-final sentinel.
    """
    folder = snapshots_root / date_str
    failed: list[str] = []
    completed: list[str] = []
    llm_failure_count = 0

    # Phase A: per-ticker JSONs.
    for r in results:
        try:
            payload = _build_ticker_payload(r)
            _atomic_write_json(folder / f"{r.ticker}.json", payload)
        except OSError as e:
            logger.error("ticker %s write failed: %s", r.ticker, e)
            failed.append(r.ticker)
            continue
        completed.append(r.ticker)
        # Count persona LLM failures (data_unavailable=True per persona).
        llm_failure_count += sum(
            1 for s in r.persona_signals if s.data_unavailable
        )
        # Synthesizer failure: ticker_decision is None outside lite mode.
        # In lite mode, ticker_decision is None by design — NOT a failure.
        if r.ticker_decision is None and not lite_mode:
            llm_failure_count += 1

    # Phase B: _index.json.
    _atomic_write_json(
        folder / "_index.json",
        {
            "date": date_str,
            "schema_version": 1,
            "run_started_at": run_started_at.isoformat(),
            "run_completed_at": run_completed_at.isoformat(),
            "tickers": completed,  # only successfully-written tickers
            "lite_mode": lite_mode,
            "total_token_count_estimate": total_token_count_estimate,
        },
    )

    # Phase C: _status.json (LAST — Pattern #4 sentinel).
    _atomic_write_json(
        folder / "_status.json",
        {
            "success": not failed,
            "partial": lite_mode or bool(failed),
            "completed_tickers": completed,
            "failed_tickers": failed,
            "skipped_tickers": [],
            "llm_failure_count": llm_failure_count,
            "lite_mode": lite_mode,
        },
    )
    return StorageOutcome(
        completed=completed,
        failed=failed,
        llm_failure_count=llm_failure_count,
    )


def write_failure_status(
    *,
    snapshots_root: Path,
    date_str: str,
    run_started_at: datetime,
    error_msg: str,
) -> None:
    """Best-effort failure _status.json — written from entrypoint exception path.

    Caller (routine.entrypoint.main) wraps THIS call in a nested try/except so
    the failure-status write itself can never crash the routine. Truncates the
    error_msg to 1000 chars defensively.
    """
    folder = snapshots_root / date_str
    _atomic_write_json(
        folder / "_status.json",
        {
            "success": False,
            "partial": True,
            "completed_tickers": [],
            "failed_tickers": [],
            "skipped_tickers": [],
            "llm_failure_count": 0,
            "lite_mode": False,
            "run_started_at": run_started_at.isoformat(),
            "error": error_msg[:1000],
        },
    )
