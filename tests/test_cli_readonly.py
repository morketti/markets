"""Integration tests for `markets list` and `markets show` (read-only) subcommands.

Probes:
- WATCH-01 demo surface: `markets list` over a 30+ ticker watchlist prints all rows
- WATCH-03 ergonomics extension: `markets show UNKNOWN` mirrors remove's did-you-mean

Test list:
- test_list_empty                       — empty watchlist message + exit 0
- test_list_with_tickers                — alphabetical ordering of seeded tickers
- test_list_30_plus_tickers             — WATCH-01 user-facing demo (35-ticker fixture)
- test_show_existing_ticker             — full structured dump for AAPL
- test_show_unknown_ticker              — WATCH-03 mirror: did-you-mean on typo
- test_example_file_loads_cleanly       — `watchlist.example.json` integrity probe
"""
from __future__ import annotations

from pathlib import Path

import pytest

from cli.main import main
from watchlist.loader import load_watchlist


def test_list_empty(empty_watchlist_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """`markets list` on a non-existent watchlist prints empty-message; exits 0."""
    rc = main(["list", "--watchlist", str(empty_watchlist_path)])
    assert rc == 0
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "empty" in output.lower(), (
        f"expected 'empty' marker in output; got stdout={captured.out!r} stderr={captured.err!r}"
    )


def test_list_with_tickers(
    seeded_watchlist_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`markets list` prints AAPL, BRK-B, NVDA in alphabetical order; exit 0."""
    rc = main(["list", "--watchlist", str(seeded_watchlist_path)])
    assert rc == 0
    captured = capsys.readouterr()
    out = captured.out
    assert "AAPL" in out
    assert "BRK-B" in out
    assert "NVDA" in out
    # Alphabetical order — AAPL before BRK-B before NVDA in the printed body.
    aapl_idx = out.index("AAPL")
    brk_idx = out.index("BRK-B")
    nvda_idx = out.index("NVDA")
    assert aapl_idx < brk_idx < nvda_idx, (
        f"expected alphabetical order AAPL<BRK-B<NVDA; got positions "
        f"{aapl_idx}, {brk_idx}, {nvda_idx} in:\n{out}"
    )


def test_list_30_plus_tickers(
    large_watchlist_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """WATCH-01 user-facing demo — `markets list` over 35-ticker watchlist prints all 35."""
    rc = main(["list", "--watchlist", str(large_watchlist_path)])
    assert rc == 0
    captured = capsys.readouterr()
    expected = [
        "AAPL", "MSFT", "NVDA", "GOOG", "AMZN", "META", "TSLA", "BRK-B", "JPM", "V",
        "XOM", "UNH", "JNJ", "PG", "HD", "MA", "CVX", "ABBV", "KO", "PFE",
        "PEP", "WMT", "BAC", "TMO", "COST", "DIS", "CRM", "ORCL", "NKE", "ADBE",
        "AMD", "NFLX", "INTC", "CSCO", "QCOM",
    ]
    out = captured.out
    for sym in expected:
        assert sym in out, f"expected {sym!r} in `markets list` output for 35-ticker fixture"
    # Also sanity-check the row count: split lines, drop blanks/header — should be ≥35 rows.
    body_lines = [ln for ln in out.splitlines() if ln.strip()]
    assert len(body_lines) >= len(expected), (
        f"expected at least {len(expected)} non-empty lines (header + 35 rows); "
        f"got {len(body_lines)}:\n{out}"
    )


def test_show_existing_ticker(
    seeded_watchlist_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`markets show AAPL` prints structured dump containing key fields; exit 0."""
    rc = main(["show", "AAPL", "--watchlist", str(seeded_watchlist_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "TICKER: AAPL" in out
    assert "long_term_lens: value" in out
    # thesis_price: 200.0 (Pydantic float) — accept either "200" or "200.0" string forms.
    assert "thesis_price: 200" in out, f"expected thesis_price line in output:\n{out}"


def test_show_unknown_ticker(
    seeded_watchlist_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """WATCH-03 ergonomics mirror — `markets show AAPK` (typo) suggests `AAPL`; exit 1."""
    rc = main(["show", "AAPK", "--watchlist", str(seeded_watchlist_path)])
    assert rc == 1
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "did you mean" in output, (
        f"expected 'did you mean' in output; got stdout={captured.out!r} stderr={captured.err!r}"
    )
    assert "AAPL" in output


def test_show_invalid_ticker_format(
    seeded_watchlist_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`markets show '!@#'` returns exit 2 with 'invalid ticker format' on stderr."""
    rc = main(["show", "!@#", "--watchlist", str(seeded_watchlist_path)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "invalid ticker format" in err, (
        f"expected 'invalid ticker format' in stderr; got {err!r}"
    )


def test_show_with_technical_and_targets(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Show prints technical_levels + target_multiples blocks when set; covers both branches."""
    from analysts.schemas import (
        FundamentalTargets,
        TechnicalLevels,
        TickerConfig,
        Watchlist,
    )
    from watchlist.loader import save_watchlist

    wl_path = tmp_path / "watchlist.json"
    wl = Watchlist(
        tickers={
            "AAPL": TickerConfig(
                ticker="AAPL",
                long_term_lens="value",
                thesis_price=200.0,
                technical_levels=TechnicalLevels(support=175.0, resistance=220.0),
                target_multiples=FundamentalTargets(pe_target=25.0, ps_target=7.0),
                notes="reload zone test",
            ),
        }
    )
    save_watchlist(wl, wl_path)
    rc = main(["show", "AAPL", "--watchlist", str(wl_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "technical_levels:" in out
    assert "support: 175" in out
    assert "resistance: 220" in out
    assert "target_multiples:" in out
    assert "pe_target: 25" in out
    assert "ps_target: 7" in out
    assert "pb_target: -" in out
    assert "notes: reload zone test" in out


def test_list_truncates_long_notes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`markets list` truncates notes longer than 40 chars with `...` suffix."""
    from analysts.schemas import TickerConfig, Watchlist
    from watchlist.loader import save_watchlist

    wl_path = tmp_path / "watchlist.json"
    long_note = "x" * 100  # well over 40 chars
    wl = Watchlist(tickers={"AAPL": TickerConfig(ticker="AAPL", notes=long_note)})
    save_watchlist(wl, wl_path)
    rc = main(["list", "--watchlist", str(wl_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "..." in out, f"expected truncation marker '...' in output:\n{out}"
    # The full 100-char note should NOT be present.
    assert long_note not in out


def test_example_file_loads_cleanly() -> None:
    """`watchlist.example.json` exists at repo root, has 5 tickers, spans 4 lenses, BRK-B (no BRK.B)."""
    example_path = Path("watchlist.example.json")
    if not example_path.exists():
        pytest.skip("watchlist.example.json not yet generated (run during GREEN task)")
    wl = load_watchlist(example_path)
    assert len(wl.tickers) == 5, (
        f"expected exactly 5 tickers in watchlist.example.json; got {len(wl.tickers)}: "
        f"{list(wl.tickers.keys())}"
    )
    lenses = {cfg.long_term_lens for cfg in wl.tickers.values()}
    expected_lenses = {"value", "growth", "contrarian", "mixed"}
    assert lenses == expected_lenses, (
        f"expected example file to span all four lenses {expected_lenses}; got {lenses}"
    )
    # CONTEXT.md correction #1 sentinel: BRK uses HYPHEN form (not BRK.B).
    assert "BRK-B" in wl.tickers, "expected BRK-B (hyphen form) in example file"
    assert "BRK.B" not in wl.tickers, "BRK.B (dot form) must not appear — schema normalizes"
    # Raw bytes check — the on-disk file must use BRK-B literally too (not just normalize).
    raw = example_path.read_text(encoding="utf-8")
    assert "BRK-B" in raw
    assert "BRK.B" not in raw, "watchlist.example.json must use BRK-B form on disk"
