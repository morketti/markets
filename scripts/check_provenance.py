# novel-to-this-project — INFRA-07 enforcement: walks tracked source files,
# asserts each carries one of three provenance marker forms in the first
# 30 lines. Self-documenting (no allow-list to maintain); survives file
# moves; explicit per-file ownership statement.
"""scripts/check_provenance — pre-commit + CI provenance enforcement.

Walks specific roots (analysts/, routine/, synthesis/, ingestion/, api/,
scripts/, prompts/personas/*.md, prompts/synthesizer.md). For each tracked
source file, asserts the first 30 lines contain ONE of:

  - "Pattern adapted from <ref>/<path>"   (canonical form)
  - "Adapted from <ref>/<path>"            (short form)
  - "# novel-to-this-project"              (explicit no-adaptation marker)

Markdown files accept the comment form `<!-- Pattern adapted from ... -->`.

Exit code 0 when clean; 1 when any offender. CLI:

    python scripts/check_provenance.py
        # walks DEFAULT_ROOTS + MD_TARGETS from the repo root.

    python scripts/check_provenance.py --roots /tmp/some_dir
        # test hook — overrides DEFAULT_ROOTS and skips MD_TARGETS.

Empty __init__.py files (zero-byte package markers) are skipped — they
have no content to provenance-mark.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Final, Iterable

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]

DEFAULT_ROOTS: Final[tuple[Path, ...]] = (
    REPO_ROOT / "analysts",
    REPO_ROOT / "routine",
    REPO_ROOT / "synthesis",
    REPO_ROOT / "ingestion",
    REPO_ROOT / "api",
    REPO_ROOT / "scripts",
)

MD_TARGETS: Final[tuple[Path, ...]] = (
    REPO_ROOT / "prompts" / "personas",   # all *.md inside
    REPO_ROOT / "prompts" / "synthesizer.md",
)

SCAN_LINE_LIMIT: Final[int] = 30

# Three accepted marker forms. The `\S+/` token anchors the reference path
# so we don't accept "Pattern adapted from somewhere" without an actual
# <ref>/<path> identifier.
#
# Markers are accepted in EITHER comment form (`# ...` / `<!-- ... -->`) OR
# inside a module docstring — the marker text is what carries the
# information; the comment syntax is incidental. Phase 3-5 modules already
# carry "Adapted from virattt/ai-hedge-fund/src/agents/x.py" inside their
# docstrings; this regex honors that existing provenance.
_PY_MARKERS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"[Pp]attern adapted from\s+\S+/"),
    re.compile(r"[Aa]dapted from\s+\S+/"),
    re.compile(r"novel-to-this-project\b"),
)
# Markdown personas use the same loose form (the marker can live in an HTML
# comment OR a plain text line at the top of the file).
_MD_MARKERS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"[Pp]attern adapted from\s+\S+/"),
    re.compile(r"[Aa]dapted from\s+\S+/"),
    re.compile(r"novel-to-this-project\b"),
)


def _has_marker(path: Path) -> bool:
    """Return True if the file has any accepted provenance marker in first 30 lines."""
    try:
        with path.open("r", encoding="utf-8") as f:
            lines: list[str] = []
            for i, line in enumerate(f):
                if i >= SCAN_LINE_LIMIT:
                    break
                lines.append(line)
    except (OSError, UnicodeDecodeError):
        return False

    markers = _MD_MARKERS if path.suffix == ".md" else _PY_MARKERS
    head = "".join(lines)
    return any(m.search(head) for m in markers)


def _is_skippable(path: Path) -> bool:
    """Return True for files that don't need a provenance marker.

    Skip:
      - __pycache__ entries
      - empty __init__.py (zero-byte package markers — no content to mark)
    """
    if "__pycache__" in path.parts:
        return True
    try:
        if path.name == "__init__.py" and path.stat().st_size == 0:
            return True
    except OSError:
        return False
    return False


def _iter_targets(roots: Iterable[Path], md_targets: Iterable[Path]) -> Iterable[Path]:
    """Yield every (.py + .md) source path under the given roots / markdown targets."""
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*.py"):
            if _is_skippable(p):
                continue
            yield p
    for md_target in md_targets:
        if md_target.is_dir():
            for p in md_target.rglob("*.md"):
                yield p
        elif md_target.is_file():
            yield md_target


def check_file(path: Path) -> str | None:
    """Return None if file has marker, else an offender message.

    Skippable files (empty __init__.py, __pycache__) return None — they
    aren't offenders. The caller (main / iter_targets) excludes them anyway,
    but we double-defend here for direct callers in tests.
    """
    if _is_skippable(path):
        return None
    if _has_marker(path):
        return None
    try:
        rel = path.relative_to(REPO_ROOT)
    except ValueError:
        rel = path  # path is outside REPO_ROOT (e.g. tmp_path in tests)
    return (
        f"{rel}: missing provenance marker "
        f"(one of: 'Pattern adapted from <ref>/<path>', "
        f"'Adapted from <ref>/<path>', '# novel-to-this-project')"
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Return 0 (clean) or 1 (offenders found)."""
    parser = argparse.ArgumentParser(description="Verify provenance markers (INFRA-07).")
    parser.add_argument(
        "--roots",
        nargs="*",
        default=None,
        help="Override DEFAULT_ROOTS (test hook).",
    )
    args = parser.parse_args(argv)

    if args.roots is not None:
        roots = [Path(r) for r in args.roots]
        md_targets: list[Path] = []
    else:
        roots = list(DEFAULT_ROOTS)
        md_targets = list(MD_TARGETS)

    offenders: list[str] = []
    scanned = 0
    for path in _iter_targets(roots, md_targets):
        scanned += 1
        msg = check_file(path)
        if msg is not None:
            offenders.append(msg)

    if offenders:
        print("Provenance check FAILED — offenders:", file=sys.stderr)
        for o in offenders:
            print(f"  {o}", file=sys.stderr)
        return 1
    print(f"Provenance check OK ({scanned} files scanned).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
