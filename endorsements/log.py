# Pattern adapted from routine/memory_log.py — JSONL atomic append discipline
# (mkdir parents=True; mode='a'; sort_keys=True; one record per line).
"""endorsements.log — append-only JSONL writer + reader for Endorsement records.

DEFAULT_PATH is `endorsements.jsonl` at repo root. Diverges from
routine/memory_log.py's `memory/historical_signals.jsonl` (gitignored, transient)
because PROJECT.md frames endorsements as "first-class signal" — the file is
COMMITTED so the frontend can read it via raw.githubusercontent.com.

Append discipline: mkdir parents=True (defensive — repo root always exists, but
tests may inject tmp paths with a `subdir/endorsements.jsonl` shape); mode='a'
single-writer-safe on POSIX + Windows for sub-PIPE_BUF lines (record << 4 KB);
json.dumps(..., sort_keys=True) for stable, grep-friendly output.

load_endorsements() is used by tests + future v1.x routine integration. The
frontend does NOT use this — it reads the JSONL directly via fetch + zod.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Final

from analysts.endorsement_schema import Endorsement

DEFAULT_PATH: Final[Path] = Path("endorsements.jsonl")


def append_endorsement(e: Endorsement, *, path: Path | None = None) -> None:
    """Append one Endorsement to endorsements.jsonl.

    Mirrors routine.memory_log.append_memory_record discipline.

    Args:
        e: validated Endorsement record (Pydantic invariants already enforced).
        path: target JSONL file. Defaults to DEFAULT_PATH; tests inject tmp_path.
    """
    target = path if path is not None else DEFAULT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(e.model_dump(mode="json"), sort_keys=True) + "\n"
    with target.open("a", encoding="utf-8") as f:
        f.write(line)


def load_endorsements(*, path: Path | None = None) -> list[Endorsement]:
    """Read all endorsements. Skips blank lines. Pydantic-validates each.

    Args:
        path: target JSONL file. Defaults to DEFAULT_PATH; tests inject tmp_path.

    Returns:
        Empty list when the file does not exist (graceful first-deploy case).
        Otherwise list of Endorsement instances in file order.

    Raises:
        ValidationError: any line fails Pydantic validation (schema drift,
            corrupted record, etc.). Mirrors load-time strictness convention.
    """
    target = path if path is not None else DEFAULT_PATH
    if not target.exists():
        return []
    out: list[Endorsement] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(Endorsement.model_validate_json(line))
    return out
