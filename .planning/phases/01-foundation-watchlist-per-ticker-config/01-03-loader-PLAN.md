---
phase: 01-foundation-watchlist-per-ticker-config
plan: 03
type: tdd
wave: 3
depends_on: [01, 02]
files_modified:
  - watchlist/loader.py
  - tests/test_loader.py
autonomous: true
requirements: [WATCH-01, WATCH-02, WATCH-05]
must_haves:
  truths:
    - "load_watchlist on a 30+ ticker file returns a fully-validated Watchlist instance"
    - "load_watchlist on a non-existent path returns an empty Watchlist (not an error)"
    - "save_watchlist writes the file atomically — partial state never visible after failure"
    - "Round-trip load → save → re-load is byte-identical when no data changes"
    - "Malformed JSON raises ValidationError with a clear path indicator (not a generic JSONDecodeError surprise)"
    - "save_watchlist re-validates the model defensively before persisting (defense-in-depth)"
    - "Validation completes in <100ms for 50 tickers (perf sanity)"
  artifacts:
    - path: "watchlist/loader.py"
      provides: "load_watchlist(path) and save_watchlist(watchlist, path) — atomic stdlib I/O"
      exports: ["load_watchlist", "save_watchlist", "DEFAULT_PATH"]
      min_lines: 30
    - path: "tests/test_loader.py"
      provides: "5 unit tests covering WATCH-01 + WATCH-02 atomic save + WATCH-05 round-trip and error handling"
      contains: "test_load_30_ticker_watchlist, test_load_50_tickers_under_100ms, test_atomic_save_no_partial, test_malformed_json_raises, test_round_trip_byte_identical"
  key_links:
    - from: "watchlist/loader.py:save_watchlist"
      to: "tempfile.NamedTemporaryFile + os.replace"
      via: "atomic-write pattern (tmp file in same dir, close handle, replace)"
      pattern: "tempfile.NamedTemporaryFile.*os.replace"
    - from: "watchlist/loader.py:save_watchlist"
      to: "json.dumps(... sort_keys=True)"
      via: "deterministic serialization (NOT model_dump_json) per CONTEXT.md correction #3"
      pattern: "json.dumps.*sort_keys=True"
    - from: "watchlist/loader.py"
      to: "analysts.schemas.Watchlist"
      via: "from analysts.schemas import Watchlist"
      pattern: "from analysts.schemas import"
---

<objective>
Build the file-I/O foundation: `load_watchlist(path)` reads-and-validates `watchlist.json`, `save_watchlist(watchlist, path)` writes atomically with deterministic key ordering. After this plan, the CLI plans (04, 05) only have to mutate the in-memory `Watchlist` and call save — no plan re-implements file I/O.

Purpose: Per ROADMAP.md Phase 1 success criterion #1 ("watchlist.json schema with 30+ tickers loads and validates via Pydantic v2"), this is THE plan that delivers it. Atomicity matters for the user experience: a Ctrl-C during `markets add` must never leave a half-written `watchlist.json`. Determinism matters because the user owns the file in git — non-deterministic key ordering (Pydantic v2 default) makes every commit a needless reorder diff.

Output: `watchlist/loader.py` (~50 lines, two functions, all stdlib + Pydantic) + `tests/test_loader.py` (5 unit tests). Round-trip byte-identical test validates serialization determinism. `uv run pytest tests/test_schemas.py tests/test_loader.py -x` all green; coverage on `watchlist/loader.py` ≥ 90%.
</objective>

<execution_context>
@C:/Users/Mohan/.claude/workflows/execute-plan.md
@C:/Users/Mohan/.claude/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/01-foundation-watchlist-per-ticker-config/01-CONTEXT.md
@.planning/phases/01-foundation-watchlist-per-ticker-config/01-RESEARCH.md
@.planning/phases/01-foundation-watchlist-per-ticker-config/01-VALIDATION.md
@.planning/phases/01-foundation-watchlist-per-ticker-config/01-01-scaffold-SUMMARY.md
@.planning/phases/01-foundation-watchlist-per-ticker-config/01-02-schemas-SUMMARY.md
@analysts/schemas.py

<interfaces>
<!-- This plan creates the loader interface that Plans 04, 05 import. -->

```python
# watchlist/loader.py — public surface
from pathlib import Path
from analysts.schemas import Watchlist

DEFAULT_PATH: Path = Path("watchlist.json")

def load_watchlist(path: Path = DEFAULT_PATH) -> Watchlist:
    """Load and validate a watchlist file. Returns empty Watchlist if file does not exist.

    Raises:
        pydantic.ValidationError: if file content is malformed JSON or schema-invalid.
    """

def save_watchlist(watchlist: Watchlist, path: Path = DEFAULT_PATH) -> None:
    """Atomically persist a watchlist. Re-validates the model before writing.

    Atomic semantics: on POSIX and Windows, either the entire new content is visible
    OR the previous content is unchanged. No partial-write state is ever visible.
    """
```

CLI plans 04 and 05 will use these as `wl = load_watchlist(args.watchlist); save_watchlist(new_wl, args.watchlist)`. The path is always passed explicitly from the CLI (never read from cwd inside the loader) — per Pitfall #7.
</interfaces>

<corrections_callout>
This plan implements CONTEXT.md correction #3 directly:

**`json.dumps(model.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"`, NOT `model_dump_json(indent=2)`.**

Pydantic v2 issue #7424 means `model_dump_json` doesn't sort dict keys. With `Watchlist.tickers: dict[str, TickerConfig]`, insertion order leaks into the file — so adding NVDA after AAPL produces a different on-disk order than alphabetic. Git diffs are noisy and round-trip is non-byte-identical when the user manually re-orders the file in their editor.

The fix is to use stdlib `json.dumps` with `sort_keys=True`. The trailing `\n` is POSIX hygiene (most editors expect a final newline). The test `test_round_trip_byte_identical` enforces this end-to-end.

Note also Pitfall #2 (Windows file locking with NamedTemporaryFile): the `with tempfile.NamedTemporaryFile(...) as tmp:` context closes the handle when the block exits; we capture `tmp.name` inside the block, then call `os.replace` outside the `with`. This is verified working on the user's locked dev OS (Windows 11).

And Pitfall #7 (cwd-relative default): `DEFAULT_PATH` is `Path("watchlist.json")` (cwd-relative). Tests using `tmp_path` MUST pass an explicit path; never call `load_watchlist()` (default arg) from a test body — that would create files in the repo root and pollute. The `empty_watchlist_path`, `seeded_watchlist_path`, `large_watchlist_path` fixtures all give explicit `tmp_path / "watchlist.json"` for this reason.
</corrections_callout>
</context>

<feature>
  <name>load_watchlist + save_watchlist with atomic stdlib I/O and deterministic serialization</name>
  <files>watchlist/loader.py, tests/test_loader.py</files>
  <behavior>
**load_watchlist(path) behavior:**
- If `path` doesn't exist → returns `Watchlist()` (empty, version=1, tickers={})
- If `path` exists with valid content → returns `Watchlist.model_validate_json(text)` result
- If `path` exists with malformed JSON → raises `pydantic.ValidationError`
- If `path` exists with schema-violating content (e.g., negative thesis_price) → raises `pydantic.ValidationError` from Pydantic's parser

**save_watchlist(watchlist, path) behavior:**
- Re-validates the model (`Watchlist.model_validate(watchlist.model_dump())`) before writing — defense-in-depth against caller passing a constructed-but-mutated model
- Serializes via `json.dumps(watchlist.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"` (NOT `model_dump_json`)
- Writes to `tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, dir=path.parent or ".", prefix=path.name + ".", suffix=".tmp")` inside a `with` block that closes the handle
- After the `with` block, calls `os.replace(tmp_path, path)` outside the block (Pitfall #2 — Windows lock release)
- On `os.replace` failure, attempts `tmp_path.unlink(missing_ok=True)` and re-raises

**Test cases (RED → GREEN cycle, all 5 must end green):**
- `test_load_30_ticker_watchlist` — uses `large_watchlist_path` fixture (35 tickers); `wl = load_watchlist(large_watchlist_path); assert len(wl.tickers) == 35; assert "AAPL" in wl.tickers; assert "BRK-B" in wl.tickers; assert wl.tickers["AAPL"].ticker == "AAPL"` (probe 1-W2-01)
- `test_load_50_tickers_under_100ms` — generates 50 synthetic tickers in-memory, writes via save_watchlist, then times `load_watchlist` → assert `elapsed < 0.1` seconds (probe 1-W2-02)
- `test_atomic_save_no_partial` — uses `seeded_watchlist_path` fixture; mutates the watchlist (add a new ticker); calls `save_watchlist` and verifies (a) file content is the new state (b) no `*.tmp` files remain in the directory after success (probe 1-W2-03)
- `test_malformed_json_raises` — uses `empty_watchlist_path`; writes `'{not valid json'` to it; calls `load_watchlist(path)` — expects `pydantic.ValidationError` (NOT generic `JSONDecodeError` — Pydantic v2's `model_validate_json` wraps malformed JSON in ValidationError) (probe 1-W2-04)
- `test_round_trip_byte_identical` — uses `seeded_watchlist_path`; reads bytes; loads via `load_watchlist`; saves via `save_watchlist` to same path; re-reads bytes; asserts byte-identical (probe 1-W2-05)

Additional implicit cases:
- `load_watchlist` on non-existent path returns `Watchlist()` with empty tickers — covered indirectly by `test_atomic_save_no_partial` if the seeded fixture starts from empty path (we'll add an explicit assertion).
  </behavior>
  <implementation>
**TDD cycle (one commit per phase):**

**RED (commit `test(01-03): add failing loader tests`):**
1. Write `tests/test_loader.py` with all 5 test functions. Imports:
   ```python
   import json
   import os
   import time
   from pathlib import Path
   import pytest
   from pydantic import ValidationError
   from analysts.schemas import TickerConfig, Watchlist
   from watchlist.loader import load_watchlist, save_watchlist
   ```
2. Run `uv run pytest tests/test_loader.py -x` — confirm ALL FAIL with `ImportError` on `from watchlist.loader import load_watchlist, save_watchlist` (because `watchlist/loader.py` doesn't exist).

Test sketches:
```python
def test_load_30_ticker_watchlist(large_watchlist_path):
    wl = load_watchlist(large_watchlist_path)
    assert len(wl.tickers) == 35
    assert "AAPL" in wl.tickers
    assert "BRK-B" in wl.tickers
    assert wl.tickers["AAPL"].ticker == "AAPL"

def test_load_50_tickers_under_100ms(tmp_path):
    path = tmp_path / "watchlist.json"
    wl = Watchlist(tickers={f"T{i:03d}": TickerConfig(ticker=f"T{i:03d}") for i in range(50)})
    save_watchlist(wl, path)
    start = time.perf_counter()
    loaded = load_watchlist(path)
    elapsed = time.perf_counter() - start
    assert len(loaded.tickers) == 50
    assert elapsed < 0.1, f"load took {elapsed:.3f}s — expected <0.1s"

def test_atomic_save_no_partial(seeded_watchlist_path):
    wl = load_watchlist(seeded_watchlist_path)
    new_tickers = dict(wl.tickers)
    new_tickers["MSFT"] = TickerConfig(ticker="MSFT", long_term_lens="growth")
    new_wl = wl.model_copy(update={"tickers": new_tickers})
    save_watchlist(new_wl, seeded_watchlist_path)
    reloaded = load_watchlist(seeded_watchlist_path)
    assert "MSFT" in reloaded.tickers
    # No tmp files should remain
    parent = seeded_watchlist_path.parent
    tmps = [p for p in parent.iterdir() if p.suffix == ".tmp" or ".tmp" in p.name]
    assert tmps == [], f"orphan tmp files: {tmps}"

def test_malformed_json_raises(empty_watchlist_path):
    empty_watchlist_path.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_watchlist(empty_watchlist_path)

def test_round_trip_byte_identical(seeded_watchlist_path):
    original_bytes = seeded_watchlist_path.read_bytes()
    wl = load_watchlist(seeded_watchlist_path)
    save_watchlist(wl, seeded_watchlist_path)
    new_bytes = seeded_watchlist_path.read_bytes()
    assert original_bytes == new_bytes, (
        "round-trip not byte-identical — likely sort_keys=True is missing "
        "or model_dump_json was used instead of json.dumps"
    )

def test_load_nonexistent_returns_empty(empty_watchlist_path):
    # bonus: covers the "file doesn't exist" branch
    wl = load_watchlist(empty_watchlist_path)
    assert wl.tickers == {}
    assert wl.version == 1
```

**GREEN (commit `feat(01-03): implement watchlist loader with atomic save`):**
3. Write `watchlist/loader.py` per `01-RESEARCH.md` § Code Examples ("Loader / atomic save") — verbatim:

```python
"""Watchlist file I/O — atomic save, deterministic serialization, defense-in-depth validation.

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
    """Load and validate a watchlist file. Returns empty Watchlist if file does not exist."""
    path = Path(path)
    if not path.exists():
        return Watchlist()
    return Watchlist.model_validate_json(path.read_text(encoding="utf-8"))


def save_watchlist(watchlist: Watchlist, path: Path = DEFAULT_PATH) -> None:
    """Atomically persist a watchlist. Re-validates the model before writing.

    Atomicity: on POSIX and Windows (via os.replace → MoveFileEx), either the entire
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
```

4. Run `uv run pytest tests/test_loader.py -x` — confirm all 5+1 tests PASS.
5. Run combined `uv run pytest tests/test_schemas.py tests/test_loader.py -x` — confirm Wave 1+2 tests all green.
6. Coverage: `uv run pytest tests/test_loader.py --cov=watchlist.loader --cov-fail-under=90`.

**REFACTOR:** Skip. The loader is too small to refactor.

**Per-task verification map (probes from 01-VALIDATION.md):**
- 1-W2-01 → `test_load_30_ticker_watchlist`
- 1-W2-02 → `test_load_50_tickers_under_100ms`
- 1-W2-03 → `test_atomic_save_no_partial`
- 1-W2-04 → `test_malformed_json_raises`
- 1-W2-05 → `test_round_trip_byte_identical`
  </implementation>
</feature>

<verification>
After GREEN:
1. `uv run pytest tests/test_schemas.py tests/test_loader.py -x` — all tests pass
2. `uv run pytest tests/test_loader.py --cov=watchlist.loader --cov-fail-under=90` — coverage ≥90%
3. Manual atomicity sanity: `uv run python -c "from analysts.schemas import Watchlist, TickerConfig; from watchlist.loader import save_watchlist; from pathlib import Path; p = Path('/tmp/wl.json'); save_watchlist(Watchlist(tickers={'AAPL': TickerConfig(ticker='AAPL')}), p); print(p.read_text())"` — prints sorted-key JSON
4. Verify no orphan tmp files: after the test run, `find /tmp -name '*.tmp' -path '*watchlist*'` returns empty
</verification>

<success_criteria>
- [ ] `load_watchlist` returns empty Watchlist on missing file (no error)
- [ ] `save_watchlist` re-validates before writing (defense-in-depth)
- [ ] Serialization uses `json.dumps(..., sort_keys=True)` — NOT `model_dump_json` (CONTEXT.md correction #3)
- [ ] Atomic write: tmp file in same dir, close, then os.replace; tmp cleanup on failure
- [ ] Round-trip byte-identical test passes (proves determinism end-to-end)
- [ ] Malformed JSON raises ValidationError (Pydantic v2 wraps it; not bare JSONDecodeError)
- [ ] 50-ticker load completes in <100ms (perf sanity)
- [ ] Coverage on `watchlist/loader.py` ≥ 90%
- [ ] WATCH-01 covered: 2 probes (1-W2-01, 1-W2-02)
- [ ] WATCH-02 atomic-save covered: 1 probe (1-W2-03)
- [ ] WATCH-05 covered: 2 probes (1-W2-04, 1-W2-05)
- [ ] All Wave 1+2 tests still green (`uv run pytest tests/test_schemas.py tests/test_loader.py -x`)
</success_criteria>

<output>
After completion, create `.planning/phases/01-foundation-watchlist-per-ticker-config/01-03-loader-SUMMARY.md` documenting:
- Final line count of `watchlist/loader.py` (expect ~50-70)
- Coverage % on `watchlist/loader.py` (expect ≥90%)
- Confirmation of byte-identical round-trip (test_round_trip_byte_identical green)
- Confirmation that `json.dumps(... sort_keys=True)` is used (NOT `model_dump_json`) — CONTEXT.md correction #3
- Atomic-save behavior: confirmed no orphan `*.tmp` files after success
- Whether Windows file-lock issue (Pitfall #2) was encountered during dev — and how the `with`-block-exit + outside-block `os.replace` resolved it
- 50-ticker load timing measurement (expect well under 100ms)
- Any deviation from the 01-RESEARCH.md "Loader / atomic save" example and why
</output>
