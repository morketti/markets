"""routine.entrypoint — Phase 5 daily-routine entry point.

novel-to-this-project — orchestration glue. No virattt or TauricResearch
analog; the layer-of-layers (load_watchlist → estimate_run_cost →
run_for_watchlist → write_daily_snapshot → commit_and_push) is project-
specific. The persona slate (Wave 3), synthesizer (Wave 4), and per-call
LLM client (Wave 2) all carry their own external provenance; main() is
the project-internal stitching that ties them together.

Wired by a Claude Code Cloud Routine fired Mon-Fri 06:00 ET (Pattern #1).
The Cloud Routine clones the repo fresh each run, executes
`python -m routine.entrypoint`, captures exit code, and surfaces any error
to the routine UI for the next-day view.

Top-level flow:
  1. logging.basicConfig
  2. load_watchlist (abort with exit 1 if empty)
  3. estimate_run_cost vs MARKETS_DAILY_QUOTA_TOKENS env → lite_mode
  4. asyncio.run(run_for_watchlist(...))
  5. write_daily_snapshot (three-phase atomic per Pattern #4)
  6. commit_and_push (5-step git per Pattern #11)
  7. return 0

Top-level exception path:
  * logger.exception('routine failed')
  * Best-effort write_failure_status (nested try/except so the failure-
    status write itself can never crash the routine)
  * return 1
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from analysts.data.snapshot import Snapshot
from ingestion.refresh import run_refresh
from routine.git_publish import commit_and_push
from routine.quota import (
    DEFAULT_MARKETS_DAILY_QUOTA_TOKENS,
    estimate_run_cost,
)
from routine.run_for_watchlist import run_for_watchlist
from routine.storage import write_daily_snapshot, write_failure_status
from watchlist.loader import load_watchlist

logger = logging.getLogger(__name__)


def main() -> int:
    """Single entry point. Exit code: 0 success, 1 any failure.

    Reads env var MARKETS_DAILY_QUOTA_TOKENS (default 600_000) for the
    lite-mode threshold. estimate_run_cost > quota → lite_mode=True →
    persona + synthesizer LLM calls skipped (analyticals only).
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run_started_at = datetime.now(timezone.utc)
    date_str = run_started_at.astimezone(timezone.utc).strftime("%Y-%m-%d")
    snapshots_root = Path("data")

    try:
        watchlist = load_watchlist()
        if not watchlist.tickers:
            logger.error("watchlist is empty; nothing to do")
            return 1

        quota = int(
            os.environ.get(
                "MARKETS_DAILY_QUOTA_TOKENS",
                str(DEFAULT_MARKETS_DAILY_QUOTA_TOKENS),
            )
        )
        estimated = estimate_run_cost(watchlist)
        lite_mode = estimated > quota
        logger.info(
            "token estimate: %d; quota: %d; lite_mode: %s",
            estimated, quota, lite_mode,
        )

        ingestion_root = Path("snapshots")
        logger.info("running ingestion refresh into %s", ingestion_root)
        manifest = run_refresh(
            snapshots_root=ingestion_root,
            now=run_started_at,
        )
        logger.info(
            "ingestion: %d tickers fetched, %d run errors",
            len(manifest.tickers),
            len(manifest.errors),
        )

        def _load_snapshot_from_disk(ticker: str) -> Snapshot:
            path = ingestion_root / date_str / f"{ticker}.json"
            return Snapshot.model_validate_json(path.read_text(encoding="utf-8"))

        results = asyncio.run(
            run_for_watchlist(
                watchlist,
                lite_mode=lite_mode,
                snapshots_root=snapshots_root,
                computed_at=run_started_at,
                snapshot_loader=_load_snapshot_from_disk,
            )
        )

        run_completed_at = datetime.now(timezone.utc)
        outcome = write_daily_snapshot(
            results,
            date_str=date_str,
            run_started_at=run_started_at,
            run_completed_at=run_completed_at,
            lite_mode=lite_mode,
            total_token_count_estimate=estimated,
            snapshots_root=snapshots_root,
        )
        logger.info(
            "snapshot written: %d completed, %d failed, %d llm_failures",
            len(outcome.completed),
            len(outcome.failed),
            outcome.llm_failure_count,
        )

        commit_and_push(date_str)
        return 0

    except Exception as exc:  # noqa: BLE001 — top-level catch by design
        logger.exception("routine failed")
        try:
            write_failure_status(
                snapshots_root=snapshots_root,
                date_str=date_str,
                run_started_at=run_started_at,
                error_msg=repr(exc),
            )
        except Exception:  # noqa: BLE001 — failure-status write must not crash
            logger.exception("could not write failure _status.json")
        return 1


if __name__ == "__main__":
    sys.exit(main())
