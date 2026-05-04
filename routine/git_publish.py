"""routine.git_publish — fail-loudly git publish per Pattern #11.

5-step sequence, each via subprocess.run(check=True, timeout=60):
  1. git fetch origin main
  2. git pull --rebase --autostash origin main
  3. git add data/{date_str}/
  4. git commit -m "data: snapshot {date_str}"
  5. git push origin main

Rationale (Pattern #11 Anti-Patterns):
  * pull --rebase --autostash BEFORE add/commit/push handles manual-vs-
    scheduled run race conditions. Autostash handles dirty-working-tree
    edge cases.
  * `git add data/{date_str}/` is SCOPED — never the all-files variant
    (defensive against accidentally committing temp files; locked by
    AST-grep test that scans this source).
  * On any CalledProcessError, the routine fails loudly (next morning's
    run is the retry). Git failures are usually configuration issues
    (token expired, push permission revoked) that need human attention,
    not transient blips.

Subprocess kwargs locked: check=True, capture_output=True, text=True,
timeout=60, cwd=str(repo_root). The cwd parameterization makes the routine
testable from any working directory (tests inject a tmp_path).

Provenance: novel-to-this-project. Git CLI invocation is project-specific
glue — not adapted from any reference repo. Pattern #11's 5-step sequence
+ anti-pattern lock against the all-files variant is the project's own discipline
(05-RESEARCH.md Pattern #11).
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def commit_and_push(
    date_str: str,
    *,
    repo_root: Path = Path("."),
) -> None:
    """Commit + push the snapshot. Raises subprocess.CalledProcessError on failure.

    5-step sequence (Pattern #11):
      1. git fetch origin main
      2. git pull --rebase --autostash origin main
      3. git add data/{date_str}/
      4. git commit -m "data: snapshot {date_str}"
      5. git push origin main

    Parameters
    ----------
    date_str
        ISO date string (e.g. "2026-05-04") used in the snapshot folder path
        AND the commit message.
    repo_root
        Path to the git repo root. Defaults to "." (the routine's cwd).
        Tests inject tmp_path-like values.

    Raises
    ------
    subprocess.CalledProcessError
        On any of the 5 git commands failing (timeout=60s, check=True).
        Caller (routine.entrypoint.main) catches at the top level.
    """
    cmds: list[list[str]] = [
        ["git", "fetch", "origin", "main"],
        ["git", "pull", "--rebase", "--autostash", "origin", "main"],
        ["git", "add", f"data/{date_str}/"],
        ["git", "commit", "-m", f"data: snapshot {date_str}"],
        ["git", "push", "origin", "main"],
    ]
    for cmd in cmds:
        try:
            subprocess.run(
                cmd,
                cwd=str(repo_root),
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            logger.info("git: %s — ok", " ".join(cmd))
        except subprocess.CalledProcessError as e:
            logger.error(
                "git: %s — failed (returncode=%d, stderr=%s)",
                " ".join(cmd), e.returncode, e.stderr,
            )
            raise
