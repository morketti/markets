"""Tests for the Plan 02-06 refresh orchestrator + per-ticker Snapshot + run Manifest.

This file grows across all three Task slots in Plan 02-06:

- Task 1 → schemas + atomic manifest writer (probe 2-W3-03).
- Task 2 → run_refresh orchestrator + partial-failure isolation + determinism
  (probes 2-W3-01, 2-W3-02, 2-W3-04).
- Task 3 → CLI smoke lives in tests/test_cli_refresh.py (probe 2-W3-05).

Test ordering matches the Plan's RED→GREEN→RED→GREEN cycles; fixtures are
local rather than fanned out into conftest because the orchestrator is the
only consumer.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from analysts.data.filings import FilingMetadata
from analysts.data.fundamentals import FundamentalsSnapshot
from analysts.data.news import Headline
from analysts.data.prices import PriceSnapshot
from analysts.data.snapshot import Snapshot
from analysts.data.social import SocialSignal
from ingestion.manifest import Manifest, TickerOutcome, write_manifest


# ---------------- Task 1: schema probes (2-W3-03) ----------------


def _stub_price_snapshot(ticker: str = "AAPL", *, available: bool = True) -> PriceSnapshot:
    if not available:
        return PriceSnapshot(
            ticker=ticker,
            fetched_at=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
            source="yfinance",
            data_unavailable=True,
            current_price=None,
            history=[],
        )
    return PriceSnapshot(
        ticker=ticker,
        fetched_at=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
        source="yfinance",
        data_unavailable=False,
        current_price=178.50,
        history=[],
    )


def _stub_fundamentals(ticker: str = "AAPL", *, available: bool = True) -> FundamentalsSnapshot:
    return FundamentalsSnapshot(
        ticker=ticker,
        fetched_at=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
        source="yfinance",
        data_unavailable=not available,
        pe=27.4 if available else None,
        market_cap=2.7e12 if available else None,
    )


def _stub_headline(ticker: str = "AAPL", suffix: str = "1") -> Headline:
    return Headline(
        ticker=ticker,
        fetched_at=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
        source="yahoo-rss",
        title=f"AAPL beats Q{suffix} estimates",
        url=f"https://example.com/aapl-{suffix}",
        published_at=datetime(2026, 4, 30, 10, 0, tzinfo=timezone.utc),
        summary="",
        dedup_key=f"yahoo-rss::aapl-{suffix}",
    )


def _stub_social(ticker: str = "AAPL", *, available: bool = True) -> SocialSignal:
    return SocialSignal(
        ticker=ticker,
        fetched_at=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
        source="combined",
        data_unavailable=not available,
        reddit_posts=[],
        stocktwits_posts=[],
        trending_rank=3 if available else None,
    )


def _stub_filing(ticker: str = "AAPL") -> FilingMetadata:
    return FilingMetadata(
        ticker=ticker,
        fetched_at=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
        source="edgar",
        data_unavailable=False,
        cik="0000320193",
        form_type="10-K",
        accession_number="0000320193-25-000001",
        filed_date=date(2026, 4, 15),
        primary_document="aapl-10k.htm",
        summary="",
    )


def test_manifest_schema():
    """Probe 2-W3-03: Manifest carries 3 outcomes, schema_version=1, datetime round-trips."""
    started = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    completed = datetime(2026, 5, 1, 12, 0, 5, tzinfo=timezone.utc)
    snapshot_date = date(2026, 5, 1)

    outcomes = [
        TickerOutcome(ticker="AAPL", success=True, duration_ms=120),
        TickerOutcome(ticker="NVDA", success=True, duration_ms=98),
        TickerOutcome(
            ticker="BRK-B",
            success=False,
            data_unavailable=True,
            duration_ms=15,
            error="all sources failed",
        ),
    ]
    m = Manifest(
        schema_version=1,
        run_started_at=started,
        run_completed_at=completed,
        snapshot_date=snapshot_date,
        tickers=outcomes,
        errors=[],
    )

    assert m.schema_version == 1
    assert m.run_started_at == started
    assert m.run_completed_at == completed
    assert m.snapshot_date == snapshot_date
    assert len(m.tickers) == 3
    assert m.tickers[2].error == "all sources failed"

    # Round-trip via JSON
    payload = m.model_dump_json()
    parsed = Manifest.model_validate_json(payload)
    assert parsed == m


def test_snapshot_aggregates_subfields():
    """Per-ticker Snapshot aggregates 5 sub-results and round-trips."""
    snap = Snapshot(
        ticker="AAPL",
        fetched_at=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
        data_unavailable=False,
        prices=_stub_price_snapshot(),
        fundamentals=_stub_fundamentals(),
        filings=[_stub_filing()],
        news=[_stub_headline(suffix="1"), _stub_headline(suffix="2")],
        social=_stub_social(),
    )

    payload = snap.model_dump_json()
    parsed = Snapshot.model_validate_json(payload)
    assert parsed.ticker == "AAPL"
    assert parsed.prices is not None and parsed.prices.current_price == 178.50
    assert parsed.fundamentals is not None and parsed.fundamentals.pe == 27.4
    assert len(parsed.news) == 2
    assert parsed.social is not None and parsed.social.trending_rank == 3
    assert len(parsed.filings) == 1


def test_snapshot_data_unavailable_when_all_subs_unavailable():
    """data_unavailable=True is allowed and serializes when caller sets it."""
    snap = Snapshot(
        ticker="ZZZZ",
        fetched_at=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
        data_unavailable=True,
        prices=None,
        fundamentals=None,
        filings=[],
        news=[],
        social=None,
        errors=["prices: timeout", "fundamentals: empty"],
    )

    payload = snap.model_dump_json()
    parsed = Snapshot.model_validate_json(payload)
    assert parsed.data_unavailable is True
    assert parsed.prices is None
    assert parsed.fundamentals is None
    assert parsed.filings == []
    assert parsed.news == []
    assert parsed.social is None
    assert parsed.errors == ["prices: timeout", "fundamentals: empty"]


def test_write_manifest_atomic(tmp_path: Path):
    """Probe 2-W3-03 (writer variant): write_manifest creates manifest.json atomically and byte-stably."""
    snap_dir = tmp_path / "snapshots" / "2026-05-01"
    started = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    completed = datetime(2026, 5, 1, 12, 0, 5, tzinfo=timezone.utc)

    m = Manifest(
        schema_version=1,
        run_started_at=started,
        run_completed_at=completed,
        snapshot_date=date(2026, 5, 1),
        tickers=[TickerOutcome(ticker="AAPL", success=True, duration_ms=100)],
        errors=[],
    )

    write_manifest(m, snap_dir)
    out_path = snap_dir / "manifest.json"
    assert out_path.exists()

    raw_first = out_path.read_bytes()

    # Round-trip via Pydantic
    reloaded = Manifest.model_validate_json(out_path.read_text(encoding="utf-8"))
    assert reloaded == m

    # Determinism: write again with same data -> byte-identical bytes
    write_manifest(m, snap_dir)
    raw_second = out_path.read_bytes()
    assert raw_first == raw_second

    # Trailing newline + sort_keys (loader-pattern parity) — verify by parsing manually.
    parsed = json.loads(raw_first.decode("utf-8"))
    assert "schema_version" in parsed
    assert raw_first.endswith(b"\n")

    # Confirm no orphan tmp file leaked in the dir
    leftover_tmps = [p for p in snap_dir.iterdir() if p.suffix == ".tmp" or ".tmp" in p.name]
    assert leftover_tmps == []


# ---------------- Task 1 coverage-completing probes ----------------


def test_snapshot_rejects_invalid_ticker():
    """Snapshot.ticker validator delegates to normalize_ticker; invalid input raises."""
    with pytest.raises(Exception):  # pydantic.ValidationError wraps the ValueError
        Snapshot(
            ticker="not a ticker",
            fetched_at=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
        )


def test_write_manifest_oserror_cleans_up_tmp(tmp_path: Path, monkeypatch):
    """When os.replace raises OSError, write_manifest deletes the tmp file and re-raises."""
    snap_dir = tmp_path / "snapshots" / "2026-05-01"
    m = Manifest(
        schema_version=1,
        run_started_at=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
        run_completed_at=datetime(2026, 5, 1, 12, 0, 5, tzinfo=timezone.utc),
        snapshot_date=date(2026, 5, 1),
        tickers=[],
        errors=[],
    )

    import ingestion.manifest as mm

    def _boom(src, dst):
        raise OSError("simulated rename failure")

    monkeypatch.setattr(mm.os, "replace", _boom)

    with pytest.raises(OSError, match="simulated rename failure"):
        write_manifest(m, snap_dir)

    # No tmp files should remain
    leftovers = [p for p in snap_dir.iterdir() if p.suffix == ".tmp" or ".tmp" in p.name]
    assert leftovers == []
    # No final manifest.json either
    assert not (snap_dir / "manifest.json").exists()


def test_read_manifest_round_trip(tmp_path: Path):
    """read_manifest convenience returns the Manifest written by write_manifest."""
    from ingestion.manifest import read_manifest

    snap_dir = tmp_path / "snapshots" / "2026-05-01"
    m = Manifest(
        schema_version=1,
        run_started_at=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
        run_completed_at=datetime(2026, 5, 1, 12, 0, 5, tzinfo=timezone.utc),
        snapshot_date=date(2026, 5, 1),
        tickers=[TickerOutcome(ticker="AAPL", success=True, duration_ms=100)],
        errors=[],
    )
    write_manifest(m, snap_dir)
    loaded = read_manifest(snap_dir)
    assert loaded == m


# ---------------- Task 2: orchestrator probes (2-W3-01, 02, 04) ----------------


@pytest.fixture
def seeded_watchlist_for_refresh(tmp_path: Path) -> Path:
    """Three-ticker watchlist file ready for orchestrator probes."""
    from analysts.schemas import TickerConfig, Watchlist
    path = tmp_path / "watchlist.json"
    wl = Watchlist(
        tickers={
            "AAPL": TickerConfig(ticker="AAPL", long_term_lens="value", thesis_price=200.0),
            "NVDA": TickerConfig(ticker="NVDA", long_term_lens="growth"),
            "BRK-B": TickerConfig(ticker="BRK-B", long_term_lens="value"),
        }
    )
    payload = json.dumps(wl.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    path.write_text(payload, encoding="utf-8")
    return path


def _ok_stubs(ticker: str):
    """Return canned successful sub-fetch results for a ticker."""
    return {
        "prices": _stub_price_snapshot(ticker),
        "fundamentals": _stub_fundamentals(ticker),
        "filings": [_stub_filing(ticker)],
        "news": [_stub_headline(ticker, suffix="x")],
        "social": _stub_social(ticker),
    }


def _patch_all_ok():
    """Patch all 5 ingestion entry points with happy-path returns. Each by-ticker."""
    def _prices(ticker, **_kw):
        return _stub_price_snapshot(ticker)

    def _fund(ticker, **_kw):
        return _stub_fundamentals(ticker)

    def _fil(ticker, **_kw):
        return [_stub_filing(ticker)]

    def _news(ticker, **_kw):
        return [_stub_headline(ticker, suffix="x")]

    def _social(ticker, **_kw):
        return _stub_social(ticker)

    return [
        patch("ingestion.refresh.fetch_prices", side_effect=_prices),
        patch("ingestion.refresh.fetch_fundamentals", side_effect=_fund),
        patch("ingestion.refresh.fetch_filings", side_effect=_fil),
        patch("ingestion.refresh.fetch_news", side_effect=_news),
        patch("ingestion.refresh.fetch_social", side_effect=_social),
    ]


def test_full_refresh(tmp_path: Path, seeded_watchlist_for_refresh: Path):
    """Probe 2-W3-01: 3-ticker watchlist refresh writes 3 snapshot files + manifest with 3 successes."""
    from ingestion.refresh import run_refresh

    fixed = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    snapshots_root = tmp_path / "snapshots"

    patches = _patch_all_ok()
    for p in patches:
        p.start()
    try:
        manifest = run_refresh(
            watchlist_path=seeded_watchlist_for_refresh,
            snapshots_root=snapshots_root,
            now=fixed,
        )
    finally:
        for p in patches:
            p.stop()

    snap_dir = snapshots_root / "2026-05-01"
    assert (snap_dir / "AAPL.json").exists()
    assert (snap_dir / "NVDA.json").exists()
    assert (snap_dir / "BRK-B.json").exists()
    assert (snap_dir / "manifest.json").exists()

    assert len(manifest.tickers) == 3
    assert all(t.success for t in manifest.tickers)
    assert manifest.errors == []

    # Each per-ticker JSON parses as a Snapshot
    for t in ("AAPL", "NVDA", "BRK-B"):
        snap = Snapshot.model_validate_json((snap_dir / f"{t}.json").read_text(encoding="utf-8"))
        assert snap.ticker == t
        assert snap.data_unavailable is False


def test_partial_failure(tmp_path: Path, seeded_watchlist_for_refresh: Path):
    """Probe 2-W3-02: one source raising for one ticker does NOT crash other tickers.

    Policy: per-source failure does NOT mark the ticker overall failed; the
    ticker's outcome.error captures the sub-source error message.
    """
    from ingestion.refresh import run_refresh

    fixed = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    snapshots_root = tmp_path / "snapshots"

    def _prices_picky(ticker, **_kw):
        if ticker == "NVDA":
            raise RuntimeError("upstream timeout")
        return _stub_price_snapshot(ticker)

    patches = [
        patch("ingestion.refresh.fetch_prices", side_effect=_prices_picky),
        patch("ingestion.refresh.fetch_fundamentals", side_effect=lambda t, **k: _stub_fundamentals(t)),
        patch("ingestion.refresh.fetch_filings", side_effect=lambda t, **k: [_stub_filing(t)]),
        patch("ingestion.refresh.fetch_news", side_effect=lambda t, **k: [_stub_headline(t, suffix="x")]),
        patch("ingestion.refresh.fetch_social", side_effect=lambda t, **k: _stub_social(t)),
    ]
    for p in patches:
        p.start()
    try:
        manifest = run_refresh(
            watchlist_path=seeded_watchlist_for_refresh,
            snapshots_root=snapshots_root,
            now=fixed,
        )
    finally:
        for p in patches:
            p.stop()

    snap_dir = snapshots_root / "2026-05-01"
    # All 3 ticker files exist (NVDA partial-success still gets a snapshot)
    for t in ("AAPL", "NVDA", "BRK-B"):
        assert (snap_dir / f"{t}.json").exists()

    nvda = Snapshot.model_validate_json((snap_dir / "NVDA.json").read_text(encoding="utf-8"))
    assert nvda.prices is None
    assert nvda.fundamentals is not None  # other sources succeeded
    assert nvda.data_unavailable is False  # at least one source produced data

    nvda_outcome = next(t for t in manifest.tickers if t.ticker == "NVDA")
    assert nvda_outcome.success is True
    assert nvda_outcome.error is not None
    assert "timeout" in nvda_outcome.error.lower()


def test_partial_failure_all_sources_fail(tmp_path: Path, seeded_watchlist_for_refresh: Path):
    """When every source raises for a ticker, that ticker is marked failed + data_unavailable; others survive."""
    from ingestion.refresh import run_refresh

    fixed = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    snapshots_root = tmp_path / "snapshots"

    def _maybe_fail(ticker, fail_for: str, ok):
        if ticker == fail_for:
            raise RuntimeError(f"{fail_for} broke")
        return ok(ticker)

    def _p(t, **_kw): return _maybe_fail(t, "BRK-B", _stub_price_snapshot)
    def _f(t, **_kw): return _maybe_fail(t, "BRK-B", _stub_fundamentals)
    def _fi(t, **_kw):
        if t == "BRK-B":
            raise RuntimeError("BRK-B filings broke")
        return [_stub_filing(t)]
    def _n(t, **_kw):
        if t == "BRK-B":
            raise RuntimeError("BRK-B news broke")
        return [_stub_headline(t, suffix="x")]
    def _s(t, **_kw): return _maybe_fail(t, "BRK-B", _stub_social)

    patches = [
        patch("ingestion.refresh.fetch_prices", side_effect=_p),
        patch("ingestion.refresh.fetch_fundamentals", side_effect=_f),
        patch("ingestion.refresh.fetch_filings", side_effect=_fi),
        patch("ingestion.refresh.fetch_news", side_effect=_n),
        patch("ingestion.refresh.fetch_social", side_effect=_s),
    ]
    for p in patches:
        p.start()
    try:
        manifest = run_refresh(
            watchlist_path=seeded_watchlist_for_refresh,
            snapshots_root=snapshots_root,
            now=fixed,
        )
    finally:
        for p in patches:
            p.stop()

    snap_dir = snapshots_root / "2026-05-01"
    brkb = Snapshot.model_validate_json((snap_dir / "BRK-B.json").read_text(encoding="utf-8"))
    assert brkb.data_unavailable is True
    assert brkb.prices is None
    assert brkb.fundamentals is None
    assert brkb.filings == []
    assert brkb.news == []
    assert brkb.social is None

    brkb_outcome = next(t for t in manifest.tickers if t.ticker == "BRK-B")
    assert brkb_outcome.success is False
    assert brkb_outcome.data_unavailable is True
    assert brkb_outcome.error is not None and brkb_outcome.error != ""

    # Other tickers still succeeded
    aapl_outcome = next(t for t in manifest.tickers if t.ticker == "AAPL")
    assert aapl_outcome.success is True


def test_only_ticker(tmp_path: Path, seeded_watchlist_for_refresh: Path):
    """Probe 2-W3-01 variant: only_ticker="AAPL" writes only AAPL.json."""
    from ingestion.refresh import run_refresh

    fixed = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    snapshots_root = tmp_path / "snapshots"

    patches = _patch_all_ok()
    for p in patches:
        p.start()
    try:
        manifest = run_refresh(
            watchlist_path=seeded_watchlist_for_refresh,
            snapshots_root=snapshots_root,
            only_ticker="AAPL",
            now=fixed,
        )
    finally:
        for p in patches:
            p.stop()

    snap_dir = snapshots_root / "2026-05-01"
    assert (snap_dir / "AAPL.json").exists()
    assert not (snap_dir / "NVDA.json").exists()
    assert not (snap_dir / "BRK-B.json").exists()
    assert len(manifest.tickers) == 1
    assert manifest.tickers[0].ticker == "AAPL"


def test_only_ticker_not_in_watchlist(tmp_path: Path, seeded_watchlist_for_refresh: Path):
    """only_ticker not in watchlist → manifest.errors describes it; no snapshots written; no exception."""
    from ingestion.refresh import run_refresh

    fixed = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    snapshots_root = tmp_path / "snapshots"

    patches = _patch_all_ok()
    for p in patches:
        p.start()
    try:
        manifest = run_refresh(
            watchlist_path=seeded_watchlist_for_refresh,
            snapshots_root=snapshots_root,
            only_ticker="ZZZZ",
            now=fixed,
        )
    finally:
        for p in patches:
            p.stop()

    snap_dir = snapshots_root / "2026-05-01"
    assert manifest.errors  # non-empty
    assert any("ZZZZ" in e for e in manifest.errors)
    assert manifest.tickers == []
    # No per-ticker files written
    leftover = [p for p in snap_dir.iterdir() if p.name != "manifest.json"]
    assert leftover == []


def test_determinism(tmp_path: Path, seeded_watchlist_for_refresh: Path):
    """Probe 2-W3-04: two runs with frozen `now` and identical mocks produce byte-identical files."""
    from ingestion.refresh import run_refresh

    fixed = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    snapshots_root_a = tmp_path / "run_a" / "snapshots"
    snapshots_root_b = tmp_path / "run_b" / "snapshots"

    for root in (snapshots_root_a, snapshots_root_b):
        patches = _patch_all_ok()
        for p in patches:
            p.start()
        try:
            run_refresh(
                watchlist_path=seeded_watchlist_for_refresh,
                snapshots_root=root,
                now=fixed,
            )
        finally:
            for p in patches:
                p.stop()

    for fname in ("AAPL.json", "NVDA.json", "BRK-B.json", "manifest.json"):
        a_bytes = (snapshots_root_a / "2026-05-01" / fname).read_bytes()
        b_bytes = (snapshots_root_b / "2026-05-01" / fname).read_bytes()
        assert a_bytes == b_bytes, f"non-deterministic output for {fname}"


def test_data_unavailable_propagates(tmp_path: Path, seeded_watchlist_for_refresh: Path):
    """When every source returns data_unavailable=True, the ticker Snapshot has data_unavailable=True."""
    from ingestion.refresh import run_refresh

    fixed = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    snapshots_root = tmp_path / "snapshots"

    def _prices_unavail(ticker, **_kw):
        return _stub_price_snapshot(ticker, available=False)

    def _fund_unavail(ticker, **_kw):
        return _stub_fundamentals(ticker, available=False)

    def _social_unavail(ticker, **_kw):
        return _stub_social(ticker, available=False)

    patches = [
        patch("ingestion.refresh.fetch_prices", side_effect=_prices_unavail),
        patch("ingestion.refresh.fetch_fundamentals", side_effect=_fund_unavail),
        patch("ingestion.refresh.fetch_filings", side_effect=lambda t, **k: []),
        patch("ingestion.refresh.fetch_news", side_effect=lambda t, **k: []),
        patch("ingestion.refresh.fetch_social", side_effect=_social_unavail),
    ]
    for p in patches:
        p.start()
    try:
        run_refresh(
            watchlist_path=seeded_watchlist_for_refresh,
            snapshots_root=snapshots_root,
            now=fixed,
        )
    finally:
        for p in patches:
            p.stop()

    snap_dir = snapshots_root / "2026-05-01"
    aapl = Snapshot.model_validate_json((snap_dir / "AAPL.json").read_text(encoding="utf-8"))
    assert aapl.data_unavailable is True


def test_run_refresh_default_now_uses_real_clock(
    tmp_path: Path, seeded_watchlist_for_refresh: Path
):
    """When now=None, run_refresh stamps with real clock (smoke — no determinism guarantee)."""
    from ingestion.refresh import run_refresh

    snapshots_root = tmp_path / "snapshots"
    patches = _patch_all_ok()
    for p in patches:
        p.start()
    try:
        manifest = run_refresh(
            watchlist_path=seeded_watchlist_for_refresh,
            snapshots_root=snapshots_root,
            only_ticker="AAPL",
        )
    finally:
        for p in patches:
            p.stop()

    assert manifest.run_completed_at is not None
    assert manifest.run_started_at is not None


def test_run_refresh_handles_missing_watchlist(tmp_path: Path):
    """Missing watchlist file returns a Manifest with no tickers; no exception escapes."""
    from ingestion.refresh import run_refresh

    fixed = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    snapshots_root = tmp_path / "snapshots"
    missing = tmp_path / "no_such_watchlist.json"

    patches = _patch_all_ok()
    for p in patches:
        p.start()
    try:
        manifest = run_refresh(
            watchlist_path=missing,
            snapshots_root=snapshots_root,
            now=fixed,
        )
    finally:
        for p in patches:
            p.stop()

    # Empty watchlist → no per-ticker outcomes and no per-ticker errors
    assert manifest.tickers == []
