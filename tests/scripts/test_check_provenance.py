"""Tests for scripts/check_provenance.py — INFRA-07 enforcement.

Walks tracked Python + persona prompt files and asserts each carries one of
three provenance marker forms in the first 30 lines:
    - "Pattern adapted from <ref>/<path>"
    - "Adapted from <ref>/<path>"
    - "# novel-to-this-project"

Markdown files accept the comment form `<!-- ... -->`.

Phase 8 / Plan 08-01 / Task 3.
"""
from __future__ import annotations

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# 1. Accepts canonical "Pattern adapted from <ref>/<path>".
# ---------------------------------------------------------------------------


def test_accepts_pattern_adapted_from(tmp_path: Path) -> None:
    from scripts.check_provenance import check_file

    f = tmp_path / "module.py"
    f.write_text(
        "# Pattern adapted from virattt/ai-hedge-fund/src/agents/x.py\n"
        '"""Doc."""\n'
        "x = 1\n",
        encoding="utf-8",
    )
    assert check_file(f) is None


# ---------------------------------------------------------------------------
# 2. Accepts short form "Adapted from <ref>/<path>".
# ---------------------------------------------------------------------------


def test_accepts_adapted_from_short_form(tmp_path: Path) -> None:
    from scripts.check_provenance import check_file

    f = tmp_path / "module.py"
    f.write_text(
        "# Adapted from TauricResearch/TradingAgents/managers/portfolio.py\n"
        "x = 1\n",
        encoding="utf-8",
    )
    assert check_file(f) is None


# ---------------------------------------------------------------------------
# 3. Accepts "# novel-to-this-project".
# ---------------------------------------------------------------------------


def test_accepts_novel_to_this_project(tmp_path: Path) -> None:
    from scripts.check_provenance import check_file

    f = tmp_path / "module.py"
    f.write_text(
        "# novel-to-this-project — orchestration glue\n"
        "x = 1\n",
        encoding="utf-8",
    )
    assert check_file(f) is None


# ---------------------------------------------------------------------------
# 4. Marker found anywhere in the first 30 lines passes.
# ---------------------------------------------------------------------------


def test_accepts_marker_within_first_30_lines(tmp_path: Path) -> None:
    from scripts.check_provenance import check_file

    f = tmp_path / "module.py"
    body = '"""Module docstring.\n\nLong description.\n"""\n' * 1
    f.write_text(
        body
        + "from __future__ import annotations\n"
        + "\n"
        + "# novel-to-this-project — line 7\n"
        + "x = 1\n",
        encoding="utf-8",
    )
    assert check_file(f) is None


# ---------------------------------------------------------------------------
# 5. Marker beyond line 30 → offender.
# ---------------------------------------------------------------------------


def test_rejects_marker_at_line_31_or_later(tmp_path: Path) -> None:
    from scripts.check_provenance import check_file

    f = tmp_path / "module.py"
    # 30 filler lines, then the marker on line 31 → outside the scan window.
    lines = ["# filler\n"] * 30 + ["# novel-to-this-project\n", "x = 1\n"]
    f.write_text("".join(lines), encoding="utf-8")
    msg = check_file(f)
    assert msg is not None
    assert "missing provenance marker" in msg


# ---------------------------------------------------------------------------
# 6. No marker at all → offender record.
# ---------------------------------------------------------------------------


def test_rejects_no_marker(tmp_path: Path) -> None:
    from scripts.check_provenance import check_file

    f = tmp_path / "module.py"
    f.write_text(
        '"""No provenance here."""\n'
        "x = 1\n",
        encoding="utf-8",
    )
    msg = check_file(f)
    assert msg is not None
    assert "missing provenance marker" in msg


# ---------------------------------------------------------------------------
# 7. Markdown HTML-comment marker form accepted.
# ---------------------------------------------------------------------------


def test_markdown_html_comment_form_accepted(tmp_path: Path) -> None:
    from scripts.check_provenance import check_file

    f = tmp_path / "persona.md"
    f.write_text(
        "<!-- Pattern adapted from virattt/ai-hedge-fund/prompts/buffett.md -->\n"
        "# Buffett persona\n"
        "...\n",
        encoding="utf-8",
    )
    assert check_file(f) is None


def test_markdown_novel_form_accepted(tmp_path: Path) -> None:
    from scripts.check_provenance import check_file

    f = tmp_path / "synthesizer.md"
    f.write_text(
        "<!-- novel-to-this-project — synthesizer prompt -->\n"
        "# Synthesizer\n",
        encoding="utf-8",
    )
    assert check_file(f) is None


def test_markdown_no_marker_rejected(tmp_path: Path) -> None:
    from scripts.check_provenance import check_file

    f = tmp_path / "persona.md"
    f.write_text("# Some persona\n\nNo marker here.\n", encoding="utf-8")
    msg = check_file(f)
    assert msg is not None
    assert "missing provenance marker" in msg


# ---------------------------------------------------------------------------
# 8. main() walks Python files in roots argument; exits 0 when clean.
# ---------------------------------------------------------------------------


def test_exit_code_zero_when_clean(tmp_path: Path, capsys) -> None:
    from scripts.check_provenance import main

    src = tmp_path / "src"
    src.mkdir()
    (src / "ok.py").write_text(
        "# novel-to-this-project\nx = 1\n", encoding="utf-8",
    )

    rc = main(["--roots", str(src)])
    assert rc == 0


# ---------------------------------------------------------------------------
# 9. main() exits 1 when offenders present + prints offender list.
# ---------------------------------------------------------------------------


def test_exit_code_one_when_offenders(tmp_path: Path, capsys) -> None:
    from scripts.check_provenance import main

    src = tmp_path / "src"
    src.mkdir()
    (src / "bad.py").write_text("x = 1\n", encoding="utf-8")
    (src / "good.py").write_text(
        "# novel-to-this-project\nx = 1\n", encoding="utf-8",
    )

    rc = main(["--roots", str(src)])
    assert rc == 1
    captured = capsys.readouterr()
    assert "bad.py" in captured.err or "bad.py" in captured.out


# ---------------------------------------------------------------------------
# 10. Empty __init__.py files are skipped (treated as package markers).
# ---------------------------------------------------------------------------


def test_empty_init_files_skipped(tmp_path: Path) -> None:
    from scripts.check_provenance import main

    src = tmp_path / "src"
    src.mkdir()
    # Empty __init__.py — no marker. Should still return 0 (skipped).
    (src / "__init__.py").write_text("", encoding="utf-8")
    (src / "real.py").write_text(
        "# novel-to-this-project\nx = 1\n", encoding="utf-8",
    )

    rc = main(["--roots", str(src)])
    assert rc == 0


# ---------------------------------------------------------------------------
# 11. Walks recursively into subdirectories (rglob).
# ---------------------------------------------------------------------------


def test_walks_subdirectories(tmp_path: Path) -> None:
    from scripts.check_provenance import main

    src = tmp_path / "src"
    sub = src / "sub" / "deeper"
    sub.mkdir(parents=True)
    (sub / "bad.py").write_text("x = 1\n", encoding="utf-8")

    rc = main(["--roots", str(src)])
    assert rc == 1
