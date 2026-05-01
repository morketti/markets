"""Run manifest — Plan 02-06 / DATA-06.

Every refresh run writes one `manifest.json` per snapshot directory under
`snapshots/{YYYY-MM-DD}/manifest.json`. The manifest carries:

- run_started_at / run_completed_at: bracketing timestamps
- snapshot_date: the YYYY-MM-DD folder name (date, not datetime)
- tickers: list[TickerOutcome] — one per ticker actually attempted
- errors: whole-run errors (e.g. failed-to-load-watchlist) — distinct from
  per-ticker errors which live in TickerOutcome.error

`write_manifest` mirrors `watchlist/loader.save_watchlist` exactly:
- json.dumps(... sort_keys=True, indent=2) + trailing "\n" for byte-stable output
  (NOT model_dump_json — Pydantic v2 issue #7424 means it does not sort dict keys)
- NamedTemporaryFile(delete=False, dir=parent) → write → close → os.replace
  (Pitfall #2: Windows file-lock release before rename)
- defense-in-depth re-validate before persisting
- on OSError, unlink tmp file and re-raise — never leave orphans

The schema_version=1 leaves room for additive evolution; Phase 3 readers
should branch on this field if they need to tolerate older runs.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TickerOutcome(BaseModel):
    """Per-ticker result of one refresh run."""

    model_config = ConfigDict(extra="forbid")

    ticker: str
    success: bool
    data_unavailable: bool = False
    duration_ms: int
    error: Optional[str] = None  # populated when at least one source failed


class Manifest(BaseModel):
    """Run-level manifest for one refresh execution."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    run_started_at: datetime
    run_completed_at: datetime
    snapshot_date: date  # YYYY-MM-DD folder name
    tickers: list[TickerOutcome] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


def write_manifest(manifest: Manifest, snapshot_dir: Path) -> None:
    """Atomically write `manifest.json` into `snapshot_dir`.

    Mirrors `watchlist/loader.save_watchlist`:
    - re-validates the model
    - serializes via stdlib json with sort_keys=True for byte-stable output
    - writes via NamedTemporaryFile(delete=False, dir=snapshot_dir) → close → os.replace
    - cleans up the tmp file on OSError before re-raising
    """
    snapshot_dir = Path(snapshot_dir)
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    target = snapshot_dir / "manifest.json"

    # Defense-in-depth: re-validate before persisting.
    Manifest.model_validate(manifest.model_dump())

    payload = json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
        dir=snapshot_dir,
        prefix="manifest.",
        suffix=".tmp",
    ) as tmp:
        tmp.write(payload)
        tmp_path = Path(tmp.name)
    try:
        os.replace(tmp_path, target)
    except OSError:
        tmp_path.unlink(missing_ok=True)
        raise


def read_manifest(snapshot_dir: Path) -> Manifest:
    """Read and validate `snapshot_dir/manifest.json`.

    Convenience for downstream readers (Phase 3+). Raises FileNotFoundError if
    the directory has no manifest yet, or pydantic.ValidationError on schema
    drift.
    """
    snapshot_dir = Path(snapshot_dir)
    return Manifest.model_validate_json(
        (snapshot_dir / "manifest.json").read_text(encoding="utf-8")
    )
