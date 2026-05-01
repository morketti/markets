"""Watchlist file I/O -- atomic save, deterministic serialization, defense-in-depth validation.

Per CONTEXT.md correction #3: serialize via json.dumps(... sort_keys=True), NOT
model_dump_json(indent=2). Pydantic v2 issue #7424 means model_dump_json doesn't sort
dict keys, which produces noisy git diffs and breaks byte-identical round-trip.

Per Pitfall #2: NamedTemporaryFile must be closed before os.replace on Windows.
Capture tmp.name inside the `with` block; call os.replace outside.

Per Pitfall #7: never read cwd inside this module; callers always pass explicit paths.
The DEFAULT_PATH is only resolved at the CLI argparse layer.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from analysts.schemas import Watchlist

DEFAULT_PATH = Path("watchlist.json")


def load_watchlist(path: Path = DEFAULT_PATH) -> Watchlist:
    """Load and validate a watchlist file. Returns empty Watchlist if file does not exist.

    Raises:
        pydantic.ValidationError: if file content is malformed JSON or schema-invalid.
    """
    path = Path(path)
    if not path.exists():
        return Watchlist()
    return Watchlist.model_validate_json(path.read_text(encoding="utf-8"))


def save_watchlist(watchlist: Watchlist, path: Path = DEFAULT_PATH) -> None:
    """Atomically persist a watchlist. Re-validates the model before writing.

    Atomicity: on POSIX and Windows (via os.replace -> MoveFileEx), either the entire
    new content is visible OR the previous content is unchanged. No partial state
    is ever visible.
    """
    path = Path(path)
    parent = path.parent if str(path.parent) else Path(".")
    # Defense-in-depth: re-validate before persisting (catches caller passing a
    # constructed-but-mutated model that bypassed validate_assignment somehow).
    Watchlist.model_validate(watchlist.model_dump())
    # Per CONTEXT.md correction #3: stdlib json.dumps with sort_keys=True for
    # deterministic output. mode="json" coerces datetime/Decimal to JSON-friendly types.
    payload = json.dumps(watchlist.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    # Per Pitfall #2: delete=False + manual close + os.replace outside the `with` block.
    # dir=parent ensures tmp file is on the same filesystem as target (atomicity prereq).
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
        dir=parent,
        prefix=path.name + ".",
        suffix=".tmp",
    ) as tmp:
        tmp.write(payload)
        tmp_path = Path(tmp.name)
    # Handle is closed; safe to rename on Windows.
    try:
        os.replace(tmp_path, path)
    except OSError:
        tmp_path.unlink(missing_ok=True)
        raise
