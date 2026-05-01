"""Unit tests for watchlist.loader: load_watchlist + save_watchlist.

Probes (per .planning/phases/01-foundation-watchlist-per-ticker-config/01-VALIDATION.md):
    1-W2-01 -> test_load_30_ticker_watchlist
    1-W2-02 -> test_load_50_tickers_under_100ms
    1-W2-03 -> test_atomic_save_no_partial
    1-W2-04 -> test_malformed_json_raises
    1-W2-05 -> test_round_trip_byte_identical

Plus one bonus test (test_load_nonexistent_returns_empty) covering the "missing
file" branch of load_watchlist explicitly per the plan's <behavior> note.

All ticker-using tests reuse fixtures from tests/conftest.py
(empty_watchlist_path, seeded_watchlist_path, large_watchlist_path) so that
file-I/O happens entirely under tmp_path -- never in the repo root (Pitfall #7).
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest
from pydantic import ValidationError

from analysts.schemas import TickerConfig, Watchlist
from watchlist.loader import load_watchlist, save_watchlist


def test_load_30_ticker_watchlist(large_watchlist_path: Path) -> None:
    """Probe 1-W2-01: a 30+ ticker watchlist loads and validates fully (WATCH-01)."""
    wl = load_watchlist(large_watchlist_path)
    assert len(wl.tickers) == 35
    assert "AAPL" in wl.tickers
    assert "BRK-B" in wl.tickers
    assert wl.tickers["AAPL"].ticker == "AAPL"


def test_load_50_tickers_under_100ms(tmp_path: Path) -> None:
    """Probe 1-W2-02: 50-ticker load completes in <100ms (perf sanity, WATCH-01)."""
    path = tmp_path / "watchlist.json"
    wl = Watchlist(
        tickers={f"T{i:03d}": TickerConfig(ticker=f"T{i:03d}") for i in range(50)}
    )
    save_watchlist(wl, path)
    start = time.perf_counter()
    loaded = load_watchlist(path)
    elapsed = time.perf_counter() - start
    assert len(loaded.tickers) == 50
    assert elapsed < 0.1, f"load took {elapsed:.3f}s -- expected <0.1s"


def test_atomic_save_no_partial(seeded_watchlist_path: Path) -> None:
    """Probe 1-W2-03: save is atomic; no orphan tmp files after success (WATCH-02)."""
    wl = load_watchlist(seeded_watchlist_path)
    new_tickers = dict(wl.tickers)
    new_tickers["MSFT"] = TickerConfig(ticker="MSFT", long_term_lens="growth")
    new_wl = wl.model_copy(update={"tickers": new_tickers})
    save_watchlist(new_wl, seeded_watchlist_path)

    reloaded = load_watchlist(seeded_watchlist_path)
    assert "MSFT" in reloaded.tickers
    assert reloaded.tickers["MSFT"].long_term_lens == "growth"

    # No tmp files should remain in the directory after a successful save.
    parent = seeded_watchlist_path.parent
    tmps = [
        p
        for p in parent.iterdir()
        if p.is_file() and (p.suffix == ".tmp" or ".tmp" in p.name)
    ]
    assert tmps == [], f"orphan tmp files: {tmps}"


def test_malformed_json_raises(empty_watchlist_path: Path) -> None:
    """Probe 1-W2-04: malformed JSON raises ValidationError (WATCH-05).

    Pydantic v2's model_validate_json wraps JSON decode errors in ValidationError
    -- we should NOT see a bare json.JSONDecodeError surface to the caller.
    """
    empty_watchlist_path.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_watchlist(empty_watchlist_path)


def test_round_trip_byte_identical(seeded_watchlist_path: Path) -> None:
    """Probe 1-W2-05: load -> save -> re-load is byte-identical (WATCH-05).

    This is the end-to-end determinism check that enforces CONTEXT.md
    correction #3: serialization MUST use json.dumps(... sort_keys=True),
    not model_dump_json (which doesn't sort dict keys per Pydantic v2 #7424).
    """
    original_bytes = seeded_watchlist_path.read_bytes()
    wl = load_watchlist(seeded_watchlist_path)
    save_watchlist(wl, seeded_watchlist_path)
    new_bytes = seeded_watchlist_path.read_bytes()
    assert original_bytes == new_bytes, (
        "round-trip not byte-identical -- likely sort_keys=True is missing "
        "or model_dump_json was used instead of json.dumps"
    )


def test_load_nonexistent_returns_empty(empty_watchlist_path: Path) -> None:
    """Bonus: load_watchlist on a missing path returns an empty Watchlist (no error).

    Covers the "file does not exist" branch of load_watchlist explicitly so the
    behavior is locked under regression. Per the plan's <behavior> section:
    "If `path` doesn't exist -> returns Watchlist() (empty, version=1, tickers={})."
    """
    assert not empty_watchlist_path.exists()
    wl = load_watchlist(empty_watchlist_path)
    assert wl.tickers == {}
    assert wl.version == 1


def test_save_cleanup_on_replace_failure(
    empty_watchlist_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """save_watchlist re-raises and removes the tmp file when os.replace fails.

    Locks the failure-cleanup contract: a half-written tmp file must NOT pollute
    the user's directory after a failed save. Without this guarantee, a single
    Ctrl-C during `markets add` could litter `git status` with orphan *.tmp
    files. Monkeypatches watchlist.loader.os.replace to raise; asserts the
    OSError surfaces AND no .tmp file remains.
    """
    import watchlist.loader as loader_mod

    wl = Watchlist(tickers={"AAPL": TickerConfig(ticker="AAPL")})

    def fake_replace(_src: object, _dst: object) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(loader_mod.os, "replace", fake_replace)

    with pytest.raises(OSError, match="simulated replace failure"):
        save_watchlist(wl, empty_watchlist_path)

    # Cleanup contract: no orphan tmp files.
    parent = empty_watchlist_path.parent
    tmps = [
        p
        for p in parent.iterdir()
        if p.is_file() and (p.suffix == ".tmp" or ".tmp" in p.name)
    ]
    assert tmps == [], f"orphan tmp files after failed save: {tmps}"
    # Target file was never created (replace was the only writer).
    assert not empty_watchlist_path.exists()
