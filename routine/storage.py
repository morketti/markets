# novel-to-this-project — Phase 5 atomic-write orchestration (Pattern #4 — project-original).
"""routine.storage — three-phase atomic write per Pattern #4.

Order (locked, not-up-for-debate):
  Phase A: per-ticker JSONs at data/{date}/{TICKER}.json — atomic per file.
  Phase B: data/{date}/_index.json (run metadata + completed-ticker list).
  Phase C: data/{date}/_status.json — written LAST as the "run is final"
           sentinel. Phase 6 frontend reads _status.json first; if absent,
           the snapshot is in-progress (or the routine crashed mid-write)
           and the frontend renders "snapshot pending" rather than
           potentially-corrupt partial data.
  Phase D: data/_dates.json (Phase 6 / Plan 06-01) — repo-root index of
           dates_available, regenerated each run by enumerating
           snapshots_root subfolders containing a _status.json sentinel.

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

Phase 6 / Plan 06-01 (Wave 0 amendment): per-ticker payload extended with
4 new fields (ohlc_history, indicators, headlines, schema_version=2);
adds the data/_dates.json writer. Indicator math uses
analysts/_indicator_math series helpers — byte-identical at iloc[-1] to
the scalar math the analyst verdicts use, so frontend overlays never
disagree with the verdict signals.

Public surface (consumed by routine.entrypoint):
    StorageOutcome           — frozen dataclass {completed, failed, llm_failure_count}
    write_daily_snapshot()   — three-phase A→B→C write + Phase D dates index
    write_failure_status()   — best-effort failure _status.json (entrypoint exception path)
    _atomic_write_json()     — single-file atomic write helper
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from analysts._indicator_math import _bb_series, _ma_series, _rsi_series
from analysts.data.prices import OHLCBar

if TYPE_CHECKING:
    from routine.run_for_watchlist import TickerResult

logger = logging.getLogger(__name__)

# Phase 6 / Plan 06-01: regex for the snapshots_root subfolder name pattern
# (YYYY-MM-DD). Used by _write_dates_index to enumerate available dates.
_DATE_FOLDER_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


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


def _series_to_jsonable(series: pd.Series) -> list:
    """Convert a pandas Series of floats to a JSON-safe list (float | None).

    NaN entries (warmup window) → None. Inf entries (RSI saturation edge case)
    → None as well, since JSON has no native inf. The frontend zod schema
    expects (number | null), so this is the safe boundary.
    """
    out: list = []
    for v in series.tolist():
        if v is None:
            out.append(None)
            continue
        # NaN check covers both numpy.nan and pandas.NA. inf gets converted to
        # None for JSON-safety (json.dumps would otherwise serialize it as
        # "Infinity" which violates strict JSON).
        if isinstance(v, float):
            if math.isnan(v) or math.isinf(v):
                out.append(None)
                continue
        out.append(float(v))
    return out


def _compute_indicator_series(history: list[OHLCBar]) -> dict:
    """Compute MA20, MA50, BB(20, 2σ) upper/lower, RSI(14) series aligned to history.

    Phase 6 / Plan 06-01 helper. Returns a dict with 5 keys:
      ma20, ma50, bb_upper, bb_lower, rsi14
    Each value is a list of (float | None) the same length as `history`,
    aligned 1:1 with the history's OHLCBars by index. Warmup positions are
    None — first 19 for ma20/bb_*, first 49 for ma50, first 14 for rsi14.

    Math is byte-identical at iloc[-1] to the scalar computations in
    analysts/technicals (MA20/MA50) and analysts/position_adjustment (BB
    rolling primitives, RSI Wilder smoothing) — locked by the 3
    `*_byte_identical_to_single_point` tests in
    tests/analysts/test_indicator_math.py.
    """
    n = len(history)
    if n == 0:
        return {
            "ma20": [],
            "ma50": [],
            "bb_upper": [],
            "bb_lower": [],
            "rsi14": [],
        }

    close = pd.Series([float(b.close) for b in history])

    ma20 = _ma_series(close, 20)
    ma50 = _ma_series(close, 50)
    bb_upper, bb_lower = _bb_series(close, window=20, sigma=2.0)
    rsi14 = _rsi_series(close, period=14)

    return {
        "ma20": _series_to_jsonable(ma20),
        "ma50": _series_to_jsonable(ma50),
        "bb_upper": _series_to_jsonable(bb_upper),
        "bb_lower": _series_to_jsonable(bb_lower),
        "rsi14": _series_to_jsonable(rsi14),
    }


def _build_ticker_payload(r: "TickerResult") -> dict:
    """Serialize a TickerResult into the locked per-ticker JSON shape.

    Per 05-CONTEXT.md storage-format lock + Phase 6 / Plan 06-01 Wave 0
    amendment:
      {ticker, schema_version=2, analytical_signals, position_signal,
       persona_signals, ticker_decision, errors,
       ohlc_history, indicators, headlines}

    Phase 6 / Plan 06-01 fields:
      ohlc_history — list of OHLCBar dicts (date ISO, OHLC + volume).
                     Read by frontend deep-dive chart (VIEW-06).
      indicators   — dict of 5 series (ma20/ma50/bb_upper/bb_lower/rsi14)
                     aligned 1:1 to ohlc_history dates. Read by frontend
                     chart overlays. Series-form math byte-identical at
                     iloc[-1] to the scalar math used by the analyst
                     verdicts (locked by tests/analysts/test_indicator_math.py).
      headlines    — list of raw {source, published_at, title, url} dicts
                     from ingestion.news. Read by frontend deep-dive news
                     feed (VIEW-08).
    """
    return {
        "ticker": r.ticker,
        # Phase 6 / Plan 06-01: bumped 1→2 alongside the 4 new fields below.
        "schema_version": 2,
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
        # Wave 0 amendment fields — frontend Phase 6 reads these directly.
        "ohlc_history": [b.model_dump(mode="json") for b in r.ohlc_history],
        "indicators": _compute_indicator_series(r.ohlc_history),
        "headlines": list(r.headlines),
    }


def _write_dates_index(snapshots_root: Path) -> None:
    """Write data/_dates.json at the snapshots root — frontend date selector index.

    Phase 6 / Plan 06-01 helper. Enumerates `snapshots_root` for subfolders
    matching the YYYY-MM-DD pattern that contain a `_status.json` sentinel
    (i.e. completed runs, not in-progress writes); writes the sorted list
    plus an updated_at timestamp to `snapshots_root/_dates.json`.

    The frontend (Phase 6 Wave 1) fetches this single file once to
    enumerate available snapshot dates without making N GitHub directory-
    listing calls. Schema_version is INDEPENDENT of the per-ticker JSON
    schema_version — this index is its own contract (1 = original shape).

    Best-effort: if the snapshots_root doesn't exist or has no completed
    folders, writes an empty dates_available list. Never raises (any
    OSError from _atomic_write_json bubbles up to the caller, which is
    write_daily_snapshot — losing the dates index is non-fatal but loud).
    """
    dates_available: list[str] = []
    if snapshots_root.is_dir():
        for child in snapshots_root.iterdir():
            if not child.is_dir():
                continue
            if not _DATE_FOLDER_RE.match(child.name):
                continue
            if (child / "_status.json").exists():
                dates_available.append(child.name)
    dates_available.sort()
    _atomic_write_json(
        snapshots_root / "_dates.json",
        {
            "schema_version": 1,
            "dates_available": dates_available,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )


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

    # Phase D (Phase 6 / Plan 06-01): regenerate data/_dates.json at repo
    # root after Phase C has landed (so today's date is included in the
    # enumeration). Best-effort — the dates index is a frontend convenience,
    # not a routine-success precondition.
    _write_dates_index(snapshots_root)

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
