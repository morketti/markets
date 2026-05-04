# novel-to-this-project — Phase 2 refresh orchestrator (project-original).
"""Refresh orchestrator — Plan 02-06 / DATA-06 + DATA-07.

The integration story for Phase 2: ties together all five Wave-2 ingestion
modules into one end-to-end refresh routine.

For each ticker in the watchlist (or just `only_ticker` when supplied):
    1. Try fetch_prices, fetch_fundamentals, fetch_filings, fetch_news,
       fetch_social — wrap each in its own try/except so a single source
       failure does NOT abort the others.
    2. Build a Snapshot aggregating whatever returned, plus an `errors` list
       capturing per-source failure messages.
    3. Write the Snapshot to `snapshots/{YYYY-MM-DD}/{ticker}.json` via
       json.dumps(... sort_keys=True, indent=2) + atomic NamedTemporaryFile
       → os.replace pattern (mirroring watchlist/loader.save_watchlist).
    4. Record a TickerOutcome (success / data_unavailable / duration_ms /
       error) for the run manifest.

After the per-ticker loop, write `snapshots/{YYYY-MM-DD}/manifest.json` via
ingestion.manifest.write_manifest. The manifest captures whole-run errors
(e.g. failed-to-load-watchlist, only_ticker not in watchlist) separately
from per-ticker errors.

Determinism (probe 2-W3-04): when `now` is supplied (test mode), it is used
both for run_started_at AND run_completed_at — no real-clock reads — so two
runs with frozen mocks produce byte-identical output. When `now` is None
(production), the real clock is read for run_completed_at.

CRITICAL EXPRESSION: run_completed_at must be
    `now if now is not None else datetime.now(timezone.utc)`
NOT the inverted `datetime.now(timezone.utc) if now else now` (which yields
None when now is None and breaks Pydantic validation).

Public surface:
    run_refresh(*, watchlist_path, snapshots_root, only_ticker, now) -> Manifest
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from analysts.data.snapshot import Snapshot
from analysts.schemas import Watchlist, normalize_ticker
from ingestion.filings import fetch_filings
from ingestion.fundamentals import fetch_fundamentals
from ingestion.manifest import Manifest, TickerOutcome, write_manifest
from ingestion.news import fetch_news
from ingestion.prices import fetch_prices
from ingestion.social import fetch_social
from watchlist.loader import load_watchlist

logger = logging.getLogger(__name__)


def _fetch_one(ticker: str, now: datetime) -> tuple[Snapshot, TickerOutcome]:
    """Fetch all 5 sources for one ticker; assemble Snapshot; return (snapshot, outcome).

    Catches per-source exceptions — they NEVER propagate. A source-level
    exception sets the relevant Snapshot field to None / [] and appends an
    error string to the Snapshot's `errors` list.

    `outcome.success` is True when AT LEAST ONE source produced a result
    (either a non-data_unavailable Pydantic object OR a non-empty list).
    `outcome.data_unavailable` is True ONLY when nothing useful came back.
    """
    started_monotonic = time.monotonic()

    errors: list[str] = []

    prices = None
    try:
        prices = fetch_prices(ticker)
    except Exception as e:  # noqa: BLE001 — per-source isolation
        logger.warning("refresh(%s): prices source failed: %s", ticker, e)
        errors.append(f"prices: {e}")

    fundamentals = None
    try:
        fundamentals = fetch_fundamentals(ticker)
    except Exception as e:  # noqa: BLE001
        logger.warning("refresh(%s): fundamentals source failed: %s", ticker, e)
        errors.append(f"fundamentals: {e}")

    filings: list = []
    try:
        filings = fetch_filings(ticker)
    except Exception as e:  # noqa: BLE001
        logger.warning("refresh(%s): filings source failed: %s", ticker, e)
        errors.append(f"filings: {e}")

    news: list = []
    try:
        news = fetch_news(ticker)
    except Exception as e:  # noqa: BLE001
        logger.warning("refresh(%s): news source failed: %s", ticker, e)
        errors.append(f"news: {e}")

    social = None
    try:
        social = fetch_social(ticker)
    except Exception as e:  # noqa: BLE001
        logger.warning("refresh(%s): social source failed: %s", ticker, e)
        errors.append(f"social: {e}")

    # Useful-data check: at least one source returned non-unavailable data.
    has_prices = prices is not None and not prices.data_unavailable
    has_fundamentals = fundamentals is not None and not fundamentals.data_unavailable
    has_filings = len(filings) > 0
    has_news = len(news) > 0
    has_social = social is not None and not social.data_unavailable

    any_useful = has_prices or has_fundamentals or has_filings or has_news or has_social
    data_unavailable = not any_useful

    snap = Snapshot(
        ticker=ticker,
        fetched_at=now,
        data_unavailable=data_unavailable,
        prices=prices,
        fundamentals=fundamentals,
        filings=filings,
        news=news,
        social=social,
        errors=errors,
    )

    duration_ms = int((time.monotonic() - started_monotonic) * 1000)
    # Outcome.success: did at least one source produce something usable?
    outcome = TickerOutcome(
        ticker=snap.ticker,
        success=any_useful,
        data_unavailable=data_unavailable,
        duration_ms=duration_ms,
        error=("; ".join(errors) if errors else None),
    )
    return snap, outcome


def _write_snapshot(snap: Snapshot, snapshot_dir: Path) -> None:
    """Atomically write `{snap.ticker}.json` into `snapshot_dir`.

    Mirrors watchlist/loader.save_watchlist exactly:
    - re-validate the model (defense-in-depth)
    - serialize via stdlib json.dumps with sort_keys=True for byte-stable output
    - NamedTemporaryFile(delete=False, dir=snapshot_dir) → close → os.replace
    - on OSError, unlink tmp file and re-raise
    """
    snapshot_dir = Path(snapshot_dir)
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    target = snapshot_dir / f"{snap.ticker}.json"

    Snapshot.model_validate(snap.model_dump())
    payload = json.dumps(snap.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
        dir=snapshot_dir,
        prefix=f"{snap.ticker}.",
        suffix=".tmp",
    ) as tmp:
        tmp.write(payload)
        tmp_path = Path(tmp.name)
    try:
        os.replace(tmp_path, target)
    except OSError:
        tmp_path.unlink(missing_ok=True)
        raise


def run_refresh(
    *,
    watchlist_path: Path = Path("watchlist.json"),
    snapshots_root: Path = Path("snapshots"),
    only_ticker: Optional[str] = None,
    now: Optional[datetime] = None,
) -> Manifest:
    """Run a full or single-ticker refresh against the watchlist.

    Args:
        watchlist_path: path to watchlist.json (default ./watchlist.json).
        snapshots_root: root dir for outputs (default ./snapshots). The actual
            files land at {snapshots_root}/{YYYY-MM-DD}/{ticker}.json plus
            {snapshots_root}/{YYYY-MM-DD}/manifest.json.
        only_ticker: if supplied, process only that ticker (must be in the
            watchlist after normalization). Other tickers are skipped.
        now: injectable datetime for determinism tests; production callers
            pass None and the real clock is used.

    Returns:
        The Manifest object (also persisted to disk).

    Never raises for upstream weather: per-source exceptions are absorbed
    inside _fetch_one; whole-run errors (failed-to-load-watchlist, only_ticker
    miss) populate manifest.errors but do not raise.
    """
    run_started = now if now is not None else datetime.now(timezone.utc)
    snapshot_date = run_started.date()
    snapshot_dir = Path(snapshots_root) / snapshot_date.isoformat()
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    errors_run: list[str] = []

    # Load watchlist — failure is whole-run, not per-ticker.
    try:
        watchlist = load_watchlist(Path(watchlist_path))
    except Exception as e:  # noqa: BLE001 — orchestrator fault tolerance
        logger.warning("refresh: failed to load watchlist %s: %s", watchlist_path, e)
        errors_run.append(f"failed to load watchlist {watchlist_path}: {e}")
        watchlist = Watchlist()

    tickers_to_process: list[str] = list(watchlist.tickers.keys())

    if only_ticker is not None:
        normalized = normalize_ticker(only_ticker)
        if normalized is None or normalized not in tickers_to_process:
            errors_run.append(
                f"ticker {only_ticker!r} not in watchlist (normalized: {normalized!r})"
            )
            tickers_to_process = []
        else:
            tickers_to_process = [normalized]

    outcomes: list[TickerOutcome] = []
    for t in tickers_to_process:
        snap, outcome = _fetch_one(t, run_started)
        try:
            _write_snapshot(snap, snapshot_dir)
        except OSError as e:
            # Disk write failed for this ticker — record but continue.
            logger.warning("refresh(%s): snapshot write failed: %s", t, e)
            outcome = TickerOutcome(
                ticker=t,
                success=False,
                data_unavailable=True,
                duration_ms=outcome.duration_ms,
                error=f"snapshot write failed: {e}",
            )
        outcomes.append(outcome)

    # Determinism: when now was supplied (test mode), use it for completion too;
    # else read the real clock. CRITICAL — keep this expression intact:
    #   `now if now is not None else datetime.now(timezone.utc)`
    run_completed = now if now is not None else datetime.now(timezone.utc)

    manifest = Manifest(
        schema_version=1,
        run_started_at=run_started,
        run_completed_at=run_completed,
        snapshot_date=snapshot_date,
        tickers=outcomes,
        errors=errors_run,
    )
    write_manifest(manifest, snapshot_dir)
    return manifest
