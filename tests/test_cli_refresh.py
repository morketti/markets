"""Integration tests for `markets refresh` (orchestrator CLI).

Probe 2-W3-05: end-to-end CLI surface for the refresh subcommand.

Tests
-----
- test_refresh_no_arg_invokes_full_refresh   — no positional arg → only_ticker=None
- test_refresh_with_ticker_arg               — positional ticker → only_ticker="AAPL"
- test_refresh_with_ticker_arg_normalizes    — `brk.b` → only_ticker="BRK-B"
- test_refresh_invalid_ticker_exits_1        — `123!@#` → stderr + exit 1
- test_refresh_prints_summary_to_stdout      — summary line shows N succeeded / N failed
- test_refresh_command_exit_0_on_partial_failure — exit 0 even when manifest.errors non-empty

run_refresh is patched at the cli.refresh module surface so the tests do
NOT actually hit yfinance / EDGAR / RSS / StockTwits — pure CLI shim
verification.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cli.main import main


def _stub_manifest(n_success: int = 1, n_fail: int = 0, errors: list[str] | None = None):
    """Build a stub Manifest object the CLI summary code can introspect."""
    from ingestion.manifest import Manifest, TickerOutcome

    outcomes: list[TickerOutcome] = []
    for i in range(n_success):
        outcomes.append(TickerOutcome(ticker=f"OK{i}", success=True, duration_ms=100))
    for i in range(n_fail):
        outcomes.append(
            TickerOutcome(
                ticker=f"BAD{i}",
                success=False,
                data_unavailable=True,
                duration_ms=10,
                error="all sources failed",
            )
        )
    return Manifest(
        schema_version=1,
        run_started_at=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
        run_completed_at=datetime(2026, 5, 1, 12, 0, 5, tzinfo=timezone.utc),
        snapshot_date=date(2026, 5, 1),
        tickers=outcomes,
        errors=errors or [],
    )


def _seed_watchlist(path: Path, tickers: tuple[str, ...] = ("AAPL",)) -> None:
    """Write a minimal watchlist.json containing the given tickers."""
    import json

    from analysts.schemas import TickerConfig, Watchlist

    wl = Watchlist(
        tickers={t: TickerConfig(ticker=t, long_term_lens="value") for t in tickers}
    )
    path.write_text(
        json.dumps(wl.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_refresh_no_arg_invokes_full_refresh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Probe 2-W3-05 (canonical): `markets refresh` (no arg) calls run_refresh with only_ticker=None."""
    monkeypatch.chdir(tmp_path)
    wl_path = tmp_path / "watchlist.json"
    _seed_watchlist(wl_path, ("AAPL",))

    with patch("cli.refresh.run_refresh") as mock_run:
        mock_run.return_value = _stub_manifest(n_success=1)
        rc = main(["refresh", "--watchlist", str(wl_path), "--snapshots-root", str(tmp_path / "snapshots")])

    assert rc == 0
    assert mock_run.call_count == 1
    kwargs = mock_run.call_args.kwargs
    assert kwargs["only_ticker"] is None


def test_refresh_with_ticker_arg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Probe 2-W3-05 (single-ticker): `markets refresh AAPL` calls run_refresh with only_ticker='AAPL'."""
    monkeypatch.chdir(tmp_path)
    wl_path = tmp_path / "watchlist.json"
    _seed_watchlist(wl_path, ("AAPL",))

    with patch("cli.refresh.run_refresh") as mock_run:
        mock_run.return_value = _stub_manifest(n_success=1)
        rc = main(
            [
                "refresh",
                "AAPL",
                "--watchlist",
                str(wl_path),
                "--snapshots-root",
                str(tmp_path / "snapshots"),
            ]
        )

    assert rc == 0
    kwargs = mock_run.call_args.kwargs
    assert kwargs["only_ticker"] == "AAPL"


def test_refresh_with_ticker_arg_normalizes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`markets refresh brk.b` normalizes to BRK-B before calling run_refresh."""
    monkeypatch.chdir(tmp_path)
    wl_path = tmp_path / "watchlist.json"
    _seed_watchlist(wl_path, ("BRK-B",))

    with patch("cli.refresh.run_refresh") as mock_run:
        mock_run.return_value = _stub_manifest(n_success=1)
        rc = main(
            [
                "refresh",
                "brk.b",
                "--watchlist",
                str(wl_path),
                "--snapshots-root",
                str(tmp_path / "snapshots"),
            ]
        )

    assert rc == 0
    kwargs = mock_run.call_args.kwargs
    assert kwargs["only_ticker"] == "BRK-B"


def test_refresh_invalid_ticker_exits_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`markets refresh 123!@#` (un-normalizable) → stderr message + exit 1; run_refresh NOT called."""
    monkeypatch.chdir(tmp_path)
    wl_path = tmp_path / "watchlist.json"
    _seed_watchlist(wl_path, ("AAPL",))

    with patch("cli.refresh.run_refresh") as mock_run:
        rc = main(
            [
                "refresh",
                "123!@#",
                "--watchlist",
                str(wl_path),
                "--snapshots-root",
                str(tmp_path / "snapshots"),
            ]
        )

    assert rc == 1
    assert mock_run.call_count == 0  # short-circuit before orchestrator
    err = capsys.readouterr().err
    assert "invalid" in err.lower()
    assert "123!@#" in err


def test_refresh_prints_summary_to_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Summary line shows total / succeeded / failed counts and the snapshot date."""
    monkeypatch.chdir(tmp_path)
    wl_path = tmp_path / "watchlist.json"
    _seed_watchlist(wl_path, ("AAPL", "NVDA", "BRK-B"))

    with patch("cli.refresh.run_refresh") as mock_run:
        mock_run.return_value = _stub_manifest(n_success=2, n_fail=1)
        rc = main(
            [
                "refresh",
                "--watchlist",
                str(wl_path),
                "--snapshots-root",
                str(tmp_path / "snapshots"),
            ]
        )

    assert rc == 0
    out = capsys.readouterr().out
    assert "3" in out  # total
    assert "2" in out  # succeeded
    assert "1" in out  # failed
    assert "2026-05-01" in out  # snapshot date


def test_refresh_command_exit_0_on_partial_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Run-level errors live in manifest.json — CLI still returns exit 0 (errors are data, not faults)."""
    monkeypatch.chdir(tmp_path)
    wl_path = tmp_path / "watchlist.json"
    _seed_watchlist(wl_path, ("AAPL",))

    with patch("cli.refresh.run_refresh") as mock_run:
        mock_run.return_value = _stub_manifest(
            n_success=0, n_fail=1, errors=["watchlist entry rejected"]
        )
        rc = main(
            [
                "refresh",
                "--watchlist",
                str(wl_path),
                "--snapshots-root",
                str(tmp_path / "snapshots"),
            ]
        )

    assert rc == 0
    err = capsys.readouterr().err
    assert "watchlist entry rejected" in err
