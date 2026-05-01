---
phase: 02-ingestion-keyless-data-plane
plan: 06
type: tdd
wave: 3
depends_on: [02-01, 02-02, 02-03, 02-04, 02-05]
files_modified:
  - ingestion/refresh.py
  - ingestion/manifest.py
  - cli/refresh.py
  - cli/main.py
  - tests/ingestion/test_refresh.py
  - tests/test_cli_refresh.py
  - analysts/data/__init__.py
  - analysts/data/snapshot.py
autonomous: true
requirements: [DATA-06, DATA-07]
must_haves:
  truths:
    - "`markets refresh` (no arg) loads watchlist.json, fetches all sources for every ticker, writes snapshots/{YYYY-MM-DD}/{ticker}.json + manifest.json"
    - "`markets refresh AAPL` fetches one ticker only and writes snapshots/{YYYY-MM-DD}/AAPL.json + an updated manifest entry"
    - "When 1 of N tickers raises an unhandled exception, the other N-1 still complete; manifest.errors lists the failed ticker"
    - "Two consecutive refresh runs with frozen time + frozen mocks produce byte-identical snapshot JSON files (deterministic serialization)"
    - "Manifest schema (run_started_at, run_completed_at, snapshot_date, tickers, errors, durations_ms) validates via Pydantic"
    - "Per-ticker Snapshot Pydantic model aggregates prices + fundamentals + filings + news + social with data_unavailable=True when ALL sub-fetches fail"
  artifacts:
    - path: "ingestion/refresh.py"
      provides: "run_refresh(watchlist) → writes snapshots; per-ticker Snapshot assembly; partial-failure isolation"
      min_lines: 80
    - path: "ingestion/manifest.py"
      provides: "Manifest Pydantic model + writer/reader"
      min_lines: 30
    - path: "analysts/data/snapshot.py"
      provides: "Snapshot Pydantic model aggregating per-ticker data"
      min_lines: 30
    - path: "cli/refresh.py"
      provides: "refresh_command argparse handler — thin shim to ingestion.refresh"
      min_lines: 50
    - path: "tests/ingestion/test_refresh.py"
      provides: "Probes 2-W3-01..04"
      min_lines: 80
    - path: "tests/test_cli_refresh.py"
      provides: "Probe 2-W3-05 (CLI end-to-end)"
      min_lines: 30
  key_links:
    - from: "cli/main.py SUBCOMMANDS"
      to: "cli/refresh.py (build_refresh_parser, refresh_command)"
      via: "dict entry append — exactly the documented extension pattern"
      pattern: "\"refresh\": \\(build_refresh_parser, refresh_command\\)"
    - from: "ingestion/refresh.py"
      to: "ingestion.prices.fetch_prices, ingestion.fundamentals.fetch_fundamentals, ingestion.filings.fetch_filings, ingestion.news.fetch_news, ingestion.social.fetch_social"
      via: "imports + calls per ticker"
      pattern: "fetch_prices|fetch_fundamentals|fetch_filings|fetch_news|fetch_social"
    - from: "ingestion/refresh.py"
      to: "snapshots/{YYYY-MM-DD}/{ticker}.json + manifest.json"
      via: "json.dumps(... sort_keys=True, indent=2) + atomic write (mirror watchlist/loader.py pattern)"
      pattern: "sort_keys=True"
    - from: "ingestion/refresh.py"
      to: "watchlist.loader.load_watchlist"
      via: "load watchlist before iterating tickers"
      pattern: "load_watchlist"
---

<objective>
Wave 3 / Orchestrator: ties together all four Wave-2 ingestion modules into a single end-to-end refresh routine, exposes it as the `markets refresh` CLI subcommand, and writes deterministic per-ticker snapshots + a run manifest. Implements the integration story behind DATA-06 (Pydantic-validated outputs end-to-end) and DATA-07 (data_unavailable propagated to disk). Bridges Phase 2's data plane to whatever Phase 3 reads.

Purpose: Each Wave-2 plan delivers a single source. This plan is where they become a working pipeline: load watchlist → for each ticker, gather all 5 sub-fetches → assemble Snapshot → atomically write JSON → record outcomes in manifest. It's also where the user-facing CLI surface lands (`markets refresh` with optional positional ticker), inheriting Phase 1's argparse + SUBCOMMANDS dict pattern (proven 4-line patch precedent from Plan 1-05).

Output: ingestion/refresh.py (orchestrator) + ingestion/manifest.py (Manifest model) + analysts/data/snapshot.py (per-ticker aggregate) + cli/refresh.py (thin CLI shim) + cli/main.py SUBCOMMANDS dict extended with `refresh`. Five probes covered (2-W3-01..05). Snapshots written under `snapshots/YYYY-MM-DD/` with a manifest.json per run.
</objective>

<execution_context>
@C:/Users/Mohan/.claude/workflows/execute-plan.md
@C:/Users/Mohan/.claude/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/02-ingestion-keyless-data-plane/02-RESEARCH.md
@.planning/phases/02-ingestion-keyless-data-plane/02-VALIDATION.md
@.planning/phases/02-ingestion-keyless-data-plane/02-01-SUMMARY.md
@.planning/phases/02-ingestion-keyless-data-plane/02-02-SUMMARY.md
@.planning/phases/02-ingestion-keyless-data-plane/02-03-SUMMARY.md
@.planning/phases/02-ingestion-keyless-data-plane/02-04-SUMMARY.md
@.planning/phases/02-ingestion-keyless-data-plane/02-05-SUMMARY.md

# Existing patterns to mirror
@watchlist/loader.py
@cli/main.py
@cli/list_watchlist.py
@cli/_errors.py
@analysts/schemas.py

<interfaces>
<!-- Wave 1 + Wave 2 contracts this plan integrates -->

From watchlist/loader.py:
```python
DEFAULT_PATH = Path("watchlist.json")
def load_watchlist(path: Path = DEFAULT_PATH) -> Watchlist
# Atomic-write pattern with json.dumps(... sort_keys=True, indent=2) + "\n" — MIRROR for snapshot writes
```

From analysts/schemas.py:
```python
class Watchlist:
    version: int
    tickers: dict[str, TickerConfig]  # iterate via watchlist.tickers.values()
def normalize_ticker(s: str) -> Optional[str]
```

From ingestion/* (Wave 2 entry points):
```python
def fetch_prices(ticker: str, *, period: str = "3mo") -> PriceSnapshot
def fetch_fundamentals(ticker: str) -> FundamentalsSnapshot
def fetch_filings(ticker: str, *, forms=("10-K","10-Q","8-K"), limit=20) -> list[FilingMetadata]
def fetch_news(ticker: str, *, dedup_window_days: int = 7) -> list[Headline]
def fetch_social(ticker: str) -> SocialSignal
```

From cli/main.py:
```python
SUBCOMMANDS: dict[str, tuple[Callable, Callable]] = {
    "add": ..., "remove": ..., "list": ..., "show": ...,
}
# 4-line patch precedent: 2 import lines + 2 dict entries. NO other dispatcher changes.
```

NEW contracts this plan creates:

analysts/data/snapshot.py:
```python
class Snapshot(BaseModel):
    """Per-ticker aggregate of one refresh run. Written to
    snapshots/{YYYY-MM-DD}/{ticker}.json."""
    ticker: str  # normalized
    fetched_at: datetime
    data_unavailable: bool = False  # True only when ALL sub-fetches reported unavailable
    prices: Optional[PriceSnapshot] = None
    fundamentals: Optional[FundamentalsSnapshot] = None
    filings: list[FilingMetadata] = Field(default_factory=list)
    news: list[Headline] = Field(default_factory=list)
    social: Optional[SocialSignal] = None
    errors: list[str] = Field(default_factory=list)  # per-source error messages
```

ingestion/manifest.py:
```python
class TickerOutcome(BaseModel):
    ticker: str
    success: bool
    data_unavailable: bool = False
    duration_ms: int
    error: Optional[str] = None  # populated when success=False

class Manifest(BaseModel):
    schema_version: int = 1
    run_started_at: datetime
    run_completed_at: datetime
    snapshot_date: date  # the YYYY-MM-DD folder name
    tickers: list[TickerOutcome]
    errors: list[str] = Field(default_factory=list)  # whole-run errors (e.g., watchlist failed to load)

def write_manifest(manifest: Manifest, snapshot_dir: Path) -> None:
    """Write manifest.json atomically (same pattern as watchlist/loader.save_watchlist)."""
```

ingestion/refresh.py:
```python
def run_refresh(
    *,
    watchlist_path: Path = Path("watchlist.json"),
    snapshots_root: Path = Path("snapshots"),
    only_ticker: Optional[str] = None,
    now: Optional[datetime] = None,  # injectable for determinism tests
) -> Manifest:
    """Run a refresh against the watchlist. When only_ticker is set,
    process only that one ticker (must already exist in watchlist).
    Writes per-ticker snapshot JSONs and a manifest.json under
    snapshots/{snapshot_date}/. Returns the Manifest object."""

def _fetch_one(ticker: str, now: datetime) -> tuple[Snapshot, TickerOutcome]:
    """Fetch all 5 sources for one ticker; assemble Snapshot; return (snapshot, outcome).
    Catches exceptions per source and per ticker — never propagates."""
```

cli/refresh.py:
```python
def build_refresh_parser(parser: argparse.ArgumentParser) -> None:
    """Adds positional optional `ticker` and --watchlist / --snapshots-root flags."""

def refresh_command(args: argparse.Namespace) -> int:
    """Calls run_refresh; prints summary; returns exit code 0 (always — manifest carries errors)."""
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Schemas — analysts/data/snapshot.py + ingestion/manifest.py + tests</name>
  <files>analysts/data/snapshot.py, analysts/data/__init__.py, ingestion/manifest.py, tests/ingestion/test_refresh.py (partial — manifest probe only)</files>
  <behavior>
    Foundation for the orchestrator: Pydantic models for the per-ticker Snapshot and the run-level Manifest, plus the manifest writer (atomic file write mirroring watchlist/loader.save_watchlist).

    Probe 2-W3-03 (manifest schema) is satisfied here; the rest land in Task 2 + Task 3.

    test_refresh.py (probe 2-W3-03 only in this task — `test_manifest_schema` and `test_manifest_round_trip`):
    - test_manifest_schema: build a Manifest with 3 TickerOutcomes; assert all fields, datetime serialization round-trips, schema_version == 1.
    - test_snapshot_aggregates_subfields: build a Snapshot with stub PriceSnapshot + FundamentalsSnapshot + 2 Headlines; serialize via model_dump_json; deserialize; equality check (or field-by-field).
    - test_snapshot_data_unavailable_when_all_subs_unavailable: build Snapshot with prices=None, fundamentals=None, filings=[], news=[], social=None; pass data_unavailable=True; assert serializes correctly.
    - test_write_manifest_atomic: build a Manifest; call write_manifest(m, tmp_path/"snapshots"/"2026-05-01"); assert tmp_path/"snapshots"/"2026-05-01"/"manifest.json" exists; read back via Manifest.model_validate_json; assert equal. Assert byte-stable: write twice with same data, files are byte-identical.
  </behavior>
  <action>
    RED:
    1. Write the 4 tests above in `tests/ingestion/test_refresh.py` (this file will grow across all 3 tasks). Use `from datetime import datetime, date, timezone`, `from analysts.data.snapshot import Snapshot`, `from ingestion.manifest import Manifest, TickerOutcome, write_manifest`.
    2. Run `uv run pytest tests/ingestion/test_refresh.py -x -q` → import errors (modules don't exist).
    3. Commit: `test(02-06): add failing tests for Snapshot + Manifest schemas (probe 2-W3-03)`

    GREEN:
    4. Implement `analysts/data/snapshot.py`:
       - Imports: `from datetime import datetime`, `from typing import Optional`, `from pydantic import BaseModel, ConfigDict, Field, field_validator`, `from analysts.schemas import normalize_ticker`, `from analysts.data.prices import PriceSnapshot`, `from analysts.data.fundamentals import FundamentalsSnapshot`, `from analysts.data.filings import FilingMetadata`, `from analysts.data.news import Headline`, `from analysts.data.social import SocialSignal`.
       - `class Snapshot(BaseModel)` per the interfaces block. ConfigDict(extra="forbid"). ticker validator delegates to normalize_ticker. errors: list[str] tracks per-source failure messages (caller fills).
    5. Update `analysts/data/__init__.py` to re-export `Snapshot`.
    6. Implement `ingestion/manifest.py`:
       - Imports per Pydantic + datetime + pathlib + tempfile + os + json patterns from watchlist/loader.py.
       - `class TickerOutcome(BaseModel)` and `class Manifest(BaseModel)` per the interfaces block.
       - `def write_manifest(manifest: Manifest, snapshot_dir: Path) -> None`:
         - Mirror watchlist/loader.save_watchlist exactly: `Manifest.model_validate(manifest.model_dump())` (defense-in-depth re-validate); `payload = json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"`; tempfile.NamedTemporaryFile(delete=False, dir=snapshot_dir, prefix="manifest.", suffix=".tmp"); write; close; os.replace(tmp_path, snapshot_dir / "manifest.json"); on OSError tmp_path.unlink(missing_ok=True) + raise. snapshot_dir.mkdir(parents=True, exist_ok=True) before tempfile creation.
    7. Run `uv run pytest tests/ingestion/test_refresh.py -v -k "manifest or snapshot"` → all 4 green.
    8. Coverage check on these two new files: `uv run pytest --cov=analysts.data.snapshot --cov=ingestion.manifest --cov-branch tests/ingestion/test_refresh.py` → ≥90% line / ≥85% branch.
    9. Commit: `feat(02-06): Snapshot + Manifest Pydantic models with atomic writer`

    Probe ID test docstring comment:
    - 2-W3-03 → `test_manifest_schema` (canonical) + `test_write_manifest_atomic` (variant)
  </action>
  <verify>
    <automated>uv run pytest tests/ingestion/test_refresh.py -v -k "manifest or snapshot" &amp;&amp; uv run pytest --cov=analysts.data.snapshot --cov=ingestion.manifest --cov-branch tests/ingestion/test_refresh.py</automated>
  </verify>
  <done>4 tests green for the schemas + writer. analysts/data/snapshot.py + ingestion/manifest.py shipped, ≥90%/≥85% coverage. Probe 2-W3-03 satisfied.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Orchestrator — ingestion/refresh.py + integration probes (2-W3-01, 02, 04)</name>
  <files>ingestion/refresh.py, tests/ingestion/test_refresh.py</files>
  <behavior>
    Probes 2-W3-01 (full watchlist refresh), 2-W3-02 (partial failure isolation), 2-W3-04 (byte-identical determinism).

    test_refresh.py (additional tests):
    - test_full_refresh (probe 2-W3-01): create a 3-ticker watchlist (AAPL, NVDA, BRK-B) at tmp_path/"watchlist.json"; patch all 5 ingestion entry points (fetch_prices, fetch_fundamentals, fetch_filings, fetch_news, fetch_social) to return canned Pydantic objects; call run_refresh(watchlist_path=..., snapshots_root=tmp_path/"snapshots", now=fixed_dt). Assert: 3 files at snapshots/2026-05-01/{AAPL,NVDA,BRK-B}.json exist; manifest.json exists; manifest.tickers length == 3; all outcomes.success == True; manifest.errors == []; each per-ticker JSON parses as a Snapshot.
    - test_partial_failure (probe 2-W3-02): same setup, but for ticker "NVDA" patch fetch_prices to raise RuntimeError("upstream timeout"). Assert: AAPL.json + BRK-B.json exist with success=True; NVDA.json STILL exists (with prices=None, fundamentals=ok, etc., data_unavailable=False because OTHER subs succeeded); manifest.tickers has 3 entries; the NVDA outcome has success=True (one source failed but ticker overall succeeded) AND its error field describes the price-source failure. Adjustment: if the user wants "ticker overall failed", we'd need a stricter rule. Document the policy in the test: "per-source failure does NOT mark ticker failed; ticker fails only when ALL sources error." Keep this test docstring explicit so policy is obvious.
    - test_partial_failure_all_sources_fail: alternative test where ALL 5 fetch_* raise for one ticker. Assert: that ticker's JSON exists with data_unavailable=True; outcome.success=False; outcome.error non-empty; manifest.errors lists the ticker.
    - test_only_ticker (probe 2-W3-01 variant — `markets refresh AAPL` codepath): same setup; pass `only_ticker="AAPL"`; assert ONLY snapshots/2026-05-01/AAPL.json exists (not NVDA.json or BRK-B.json); manifest.tickers length == 1.
    - test_only_ticker_not_in_watchlist: pass only_ticker="ZZZZ" (not in watchlist). Assert: manifest.errors contains a clear message; no per-ticker file written; exit cleanly (no exception).
    - test_determinism (probe 2-W3-04): call run_refresh TWICE with frozen `now` and identical mocks; assert the two AAPL.json files have IDENTICAL bytes (read both via .read_bytes() and compare). Same for manifest.json (since timestamps and contents are frozen, output should be byte-identical).
    - test_data_unavailable_propagates: patch fetch_prices to return PriceSnapshot(data_unavailable=True), patch others to return data_unavailable=True objects too. Run refresh. Assert: per-ticker snapshot file has data_unavailable=True at the top level.

    Use unittest.mock.patch on the ingestion module surface, e.g., `@patch("ingestion.refresh.fetch_prices")` — refresh.py imports them at module level.
  </behavior>
  <action>
    RED:
    1. Append 7 tests above to `tests/ingestion/test_refresh.py`.
    2. Run `uv run pytest tests/ingestion/test_refresh.py -x -q` → fails on tests that need run_refresh (NameError / ImportError).
    3. Commit: `test(02-06): add failing tests for run_refresh orchestrator (probes 2-W3-01,02,04)`

    GREEN:
    4. Implement `ingestion/refresh.py`:
       - Module docstring: cite the goal of integrating 5 ingestion modules + DATA-06/07 propagation + the determinism contract.
       - Imports: `from datetime import datetime, date, timezone`, `from pathlib import Path`, `from typing import Optional`, `import json`, `import logging`, `import os`, `import tempfile`, `import time`, `from analysts.schemas import normalize_ticker, Watchlist`, `from analysts.data.snapshot import Snapshot`, `from watchlist.loader import load_watchlist`, `from ingestion.prices import fetch_prices`, `from ingestion.fundamentals import fetch_fundamentals`, `from ingestion.filings import fetch_filings`, `from ingestion.news import fetch_news`, `from ingestion.social import fetch_social`, `from ingestion.manifest import Manifest, TickerOutcome, write_manifest`.
       - `def _fetch_one(ticker: str, now: datetime) -> tuple[Snapshot, TickerOutcome]`:
         - errors: list[str] = []
         - For each of 5 sources, wrap in try/except Exception → on exception, log + append to errors + set the relevant Snapshot field to None (or empty list).
         - prices = try fetch_prices(ticker) except → None
         - fundamentals = try fetch_fundamentals(ticker) except → None
         - filings = try fetch_filings(ticker) except → []
         - news = try fetch_news(ticker) except → []
         - social = try fetch_social(ticker) except → None
         - all_sources_ok = (prices is not None and not prices.data_unavailable) OR (fundamentals is not None and not fundamentals.data_unavailable) OR (len(filings) > 0) OR (len(news) > 0) OR (social is not None and not social.data_unavailable)
         - data_unavailable = NOT all_sources_ok (i.e., true only when nothing came back useful)
         - Snapshot(ticker=ticker, fetched_at=now, data_unavailable=data_unavailable, prices=prices, fundamentals=fundamentals, filings=filings, news=news, social=social, errors=errors)
         - outcome.success = (len(errors) < 5)  # at least one source worked
         - outcome.error = "; ".join(errors) if errors else None
         - duration tracked via time.monotonic() at function entry/exit.
       - `def _write_snapshot(snap: Snapshot, snapshot_dir: Path) -> None`:
         - Mirror watchlist/loader.save_watchlist atomic-write pattern. Same json.dumps(... sort_keys=True, indent=2) + "\n". File at snapshot_dir / f"{snap.ticker}.json".
       - `def run_refresh(*, watchlist_path=Path("watchlist.json"), snapshots_root=Path("snapshots"), only_ticker=None, now=None) -> Manifest`:
         - now = now or datetime.now(timezone.utc).
         - snapshot_date = now.date()
         - snapshot_dir = snapshots_root / snapshot_date.isoformat()
         - snapshot_dir.mkdir(parents=True, exist_ok=True)
         - run_started_at = now
         - errors_run: list[str] = []
         - try: watchlist = load_watchlist(watchlist_path); except Exception as e: errors_run.append(f"failed to load watchlist: {e}"); watchlist = Watchlist()
         - tickers_to_process = list(watchlist.tickers.keys())
         - if only_ticker: normalized = normalize_ticker(only_ticker); if normalized not in tickers_to_process: errors_run.append(f"ticker {only_ticker} not in watchlist"); tickers_to_process = []; else: tickers_to_process = [normalized]
         - outcomes: list[TickerOutcome] = []
         - for t in tickers_to_process: snap, outcome = _fetch_one(t, now); _write_snapshot(snap, snapshot_dir); outcomes.append(outcome)
         - manifest = Manifest(schema_version=1, run_started_at=run_started_at, run_completed_at=(now if now is not None else datetime.now(timezone.utc)), snapshot_date=snapshot_date, tickers=outcomes, errors=errors_run)
           — IMPORTANT for determinism (probe 2-W3-04): when `now` is supplied (test mode), set run_completed_at=now too (no real clock). When `now` is None (production), use the real clock. The expression `(now if now is not None else datetime.now(...))` honors this — do NOT write `datetime.now(...) if now else now` (inverted: yields None when now is None and breaks Pydantic validation).
         - write_manifest(manifest, snapshot_dir)
         - return manifest.
    5. Run `uv run pytest tests/ingestion/test_refresh.py -v` → all green.
    6. Coverage: `uv run pytest --cov=ingestion.refresh --cov-branch tests/ingestion/test_refresh.py` → ≥90% line / ≥85% branch.
    7. Run plan-scoped: `uv run pytest tests/ingestion/ -v` → 30+ tests across the phase all green.
    8. Commit: `feat(02-06): implement run_refresh orchestrator with partial-failure isolation + deterministic snapshot writes`

    Probe ID test docstring comments:
    - 2-W3-01 → `test_full_refresh`
    - 2-W3-02 → `test_partial_failure` (canonical) + `test_partial_failure_all_sources_fail`
    - 2-W3-04 → `test_determinism`
  </action>
  <verify>
    <automated>uv run pytest tests/ingestion/test_refresh.py -v &amp;&amp; uv run pytest --cov=ingestion.refresh --cov-branch tests/ingestion/test_refresh.py &amp;&amp; uv run pytest tests/ingestion/ -v</automated>
  </verify>
  <done>7 new orchestrator tests green. ingestion/refresh.py at ≥90% line / ≥85% branch. Per-ticker isolation works (one ticker error doesn't crash run). Determinism probe passes (frozen-time double-run = byte-identical files). data_unavailable propagates from sub-fetches to top-level Snapshot. Probes 2-W3-01, 2-W3-02, 2-W3-04 satisfied.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: CLI surface — cli/refresh.py + cli/main.py SUBCOMMANDS extension + smoke (probe 2-W3-05)</name>
  <files>tests/test_cli_refresh.py, cli/refresh.py, cli/main.py</files>
  <behavior>
    Probe 2-W3-05 (CLI end-to-end): `markets refresh` and `markets refresh AAPL` both work.

    test_cli_refresh.py:
    - test_refresh_no_arg_invokes_full_refresh: monkeypatch.chdir(tmp_path); seed a watchlist.json (AAPL only); patch ingestion.refresh.run_refresh to a Mock that returns a stub Manifest; call `cli.main.main(["refresh"])`; assert exit code 0; assert run_refresh was called with only_ticker=None.
    - test_refresh_with_ticker_arg: same setup; call `cli.main.main(["refresh", "AAPL"])`; assert exit 0; assert run_refresh called with only_ticker="AAPL".
    - test_refresh_with_ticker_arg_normalizes: call `cli.main.main(["refresh", "brk.b"])`; assert run_refresh called with only_ticker="BRK-B" (or whatever the normalization yields — verify via the call args).
    - test_refresh_invalid_ticker_exits_2: call `cli.main.main(["refresh", "123!@#"])`; assert exit code 2 (ValidationError → format_validation_error path) OR exit 1 with a clear stderr message — pick one and document. Recommendation: validate via normalize_ticker BEFORE calling run_refresh; if it returns None, print error to stderr and exit 1 (consistent with FileNotFoundError exit code in Phase 1).
    - test_refresh_prints_summary_to_stdout: capture stdout; patch run_refresh to return a Manifest with 3 tickers (2 success, 1 failure); assert stdout contains "3 tickers", "2 succeeded", "1 failed", and shows snapshot_date.
    - test_refresh_command_exit_0_on_partial_failure: per the policy "errors live in manifest.json, exit code 0 always"; verify by calling refresh on a watchlist that produces partial failure; assert exit code is 0 even though manifest.errors is non-empty.
  </behavior>
  <action>
    RED:
    1. Write `tests/test_cli_refresh.py` with the 6 tests above. Use `monkeypatch.chdir`, the existing `seeded_watchlist_path` fixture pattern (or a local equivalent), and `monkeypatch.setattr("ingestion.refresh.run_refresh", mock)` (or patch via `unittest.mock.patch`).
    2. Run `uv run pytest tests/test_cli_refresh.py -x -q` → fails (cli.refresh missing, SUBCOMMANDS doesn't have "refresh").
    3. Commit: `test(02-06): add failing tests for markets refresh CLI (probe 2-W3-05)`

    GREEN:
    4. Implement `cli/refresh.py`:
       - Module docstring: thin shim — argparse → run_refresh → summary print → exit code. Mirrors cli/list_watchlist.py's structure.
       - Imports: `from __future__ import annotations`, `import argparse`, `import sys`, `from pathlib import Path`, `from analysts.schemas import normalize_ticker`, `from ingestion.refresh import run_refresh`.
       - `def build_refresh_parser(parser: argparse.ArgumentParser) -> None`:
         - parser.add_argument("ticker", nargs="?", default=None, help="optional single ticker; default: refresh whole watchlist")
         - parser.add_argument("--watchlist", type=Path, default=Path("watchlist.json"), help="path to watchlist.json")
         - parser.add_argument("--snapshots-root", type=Path, default=Path("snapshots"), help="root dir for snapshot output")
       - `def refresh_command(args: argparse.Namespace) -> int`:
         - if args.ticker is not None: normalized = normalize_ticker(args.ticker); if normalized is None: print(f"error: invalid ticker {args.ticker!r}", file=sys.stderr); return 1; only_ticker = normalized; else: only_ticker = None
         - manifest = run_refresh(watchlist_path=args.watchlist, snapshots_root=args.snapshots_root, only_ticker=only_ticker)
         - n_total = len(manifest.tickers); n_success = sum(1 for t in manifest.tickers if t.success); n_fail = n_total - n_success
         - print(f"refreshed {n_total} ticker{'s' if n_total != 1 else ''}: {n_success} succeeded, {n_fail} failed")
         - print(f"snapshot: {args.snapshots_root}/{manifest.snapshot_date.isoformat()}/")
         - if manifest.errors: print("run errors:", file=sys.stderr); for err in manifest.errors: print(f"  - {err}", file=sys.stderr)
         - return 0  # always — failure detail lives in manifest
    5. Update `cli/main.py` SUBCOMMANDS dict (4-line patch precedent — this is the documented extension point):
       - Add import: `from cli.refresh import build_refresh_parser, refresh_command` (next to other cli.* imports, alphabetical).
       - Add dict entry: `"refresh": (build_refresh_parser, refresh_command),` (after "show" entry).
       - NO other lines change. Verify by diff that the patch is exactly +4 lines.
    6. Run `uv run pytest tests/test_cli_refresh.py -v` → all 6 green.
    7. Run full repo suite: `uv run pytest -x -q` → ALL 33 (Phase 1) + ~50 (Phase 2 W1+W2) + ~13 (Phase 2 W3) ≈ 96+ tests green.
    8. Coverage check on the new CLI file: `uv run pytest --cov=cli.refresh --cov-branch tests/test_cli_refresh.py` → ≥90% line / ≥85% branch.
    9. Smoke verification (manual, captured in done): `uv run markets refresh --help` exits 0; `uv run markets --help` lists "refresh" alongside add/remove/list/show.
    10. Commit: `feat(02-06): wire markets refresh CLI subcommand + extension to SUBCOMMANDS dict`

    Probe ID test docstring comment:
    - 2-W3-05 → `test_refresh_no_arg_invokes_full_refresh` (canonical) + `test_refresh_with_ticker_arg` (single-ticker codepath)
  </action>
  <verify>
    <automated>uv run pytest tests/test_cli_refresh.py -v &amp;&amp; uv run pytest -x -q &amp;&amp; uv run pytest --cov=cli.refresh --cov-branch tests/test_cli_refresh.py &amp;&amp; uv run markets refresh --help</automated>
  </verify>
  <done>6 CLI tests green. cli/refresh.py at ≥90% line / ≥85% branch. cli/main.py SUBCOMMANDS extended with "refresh" via 4-line patch (matching Plan 1-05 precedent). Whole-repo suite green (~96 tests). `uv run markets refresh --help` and `uv run markets refresh AAPL` work. Probe 2-W3-05 satisfied.</done>
</task>

</tasks>

<verification>
- Probes covered: 2-W3-01, 2-W3-02, 2-W3-03, 2-W3-04, 2-W3-05.
- Requirements satisfied: DATA-06 (Pydantic-validated snapshots end-to-end), DATA-07 (data_unavailable propagated to disk).
- Phase-wide probe coverage check: 24 probes from VALIDATION.md mapped 1:1 to test functions across Plans 02-01 through 02-06. Run `uv run pytest tests/ingestion/ tests/test_cli_refresh.py -v --co | grep -i "test_"` to enumerate.
- Coverage gates: ≥90% line / ≥85% branch on every new ingestion/* and analysts/data/* file.
- Phase-wide full suite green: `uv run pytest -x -q --cov=analysts --cov=watchlist --cov=cli --cov=ingestion --cov-branch` reports 96+ tests, no failures, coverage gate met.
- Manual: `uv run markets refresh --help`, `uv run markets refresh` (against the existing example watchlist), inspect `snapshots/YYYY-MM-DD/{ticker}.json` and `manifest.json` — verify byte-stable output, sort_keys, deterministic.
- ROADMAP.md DATA-01..08 entries can be flipped to `[x]` after Phase 2 completion.

## Cross-Scope Risks

_vault_status=budget_exhausted; re-run /gmd:plan-phase --replan after vault-maintain_
</verification>

<success_criteria>
1. `markets refresh` (no arg) walks the watchlist, fetches all 5 sources per ticker, writes snapshots/{date}/{ticker}.json + manifest.json, prints summary, exits 0.
2. `markets refresh AAPL` fetches one ticker only and updates that one snapshot file + manifest.
3. Per-ticker partial failure (1 of N raises) doesn't crash the run — manifest carries error detail; other tickers complete.
4. Two consecutive runs with frozen time + frozen mocks → byte-identical snapshot JSON + byte-identical manifest.json (deterministic serialization).
5. Manifest schema validates via Pydantic; loads/round-trips cleanly.
6. SUBCOMMANDS dict extension matches the 4-line patch precedent from Plan 1-05 (proves the extension surface is stable).
7. All 5 Wave-3 probes (2-W3-01..05) mapped to named test functions with probe-id docstring comments.
8. Phase-wide: full suite (Phase 1 + Phase 2) green; coverage ≥90% line / ≥85% branch on every new file.
</success_criteria>

<output>
After completion, create `.planning/phases/02-ingestion-keyless-data-plane/02-06-SUMMARY.md`.

Then update REQUIREMENTS.md DATA-01..08 to `[x]` (move them to Complete) and update STATE.md `## Recent Decisions` with a Phase-2-complete entry pointing to all 6 plan SUMMARYs.
</output>
