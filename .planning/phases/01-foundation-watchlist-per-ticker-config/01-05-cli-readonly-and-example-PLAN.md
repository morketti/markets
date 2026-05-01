---
phase: 01-foundation-watchlist-per-ticker-config
plan: 05
type: tdd
wave: 4
depends_on: [01, 02, 03, 04]
files_modified:
  - cli/list_watchlist.py
  - cli/show_ticker.py
  - cli/main.py
  - tests/test_cli_readonly.py
  - watchlist.example.json
  - README.md
autonomous: true
requirements: [WATCH-01]
must_haves:
  truths:
    - "`markets list` prints all watchlist tickers in deterministic (alphabetical) order with key fields (ticker, lens, thesis, notes preview)"
    - "`markets show AAPL` prints the full TickerConfig as a human-readable structured dump"
    - "`markets show ZZZZZ` (not in watchlist) errors cleanly with non-zero exit and 'did you mean' suggestion (mirrors remove behavior)"
    - "`watchlist.example.json` exists at repo root with 5 representative tickers (AAPL, NVDA, BRK-B, GME, V) spanning all four long_term_lens values; loads cleanly via load_watchlist"
    - "README.md documents the copy-and-edit pattern: `cp watchlist.example.json watchlist.json && markets add NEW_TICKER ...`"
  artifacts:
    - path: "cli/list_watchlist.py"
      provides: "build_list_parser(p); list_command(args) → exit_code"
      exports: ["build_list_parser", "list_command"]
    - path: "cli/show_ticker.py"
      provides: "build_show_parser(p); show_command(args) → exit_code"
      exports: ["build_show_parser", "show_command"]
    - path: "cli/main.py"
      provides: "EXTENDED — adds 'list' and 'show' to SUBCOMMANDS dict from Plan 04"
      contains: "list_command, show_command imports and dict entries"
    - path: "tests/test_cli_readonly.py"
      provides: "Tests for list and show subcommands; verifies WATCH-01 30+ ticker readback via list"
      contains: "test_list_empty, test_list_with_tickers, test_list_30_plus_tickers, test_show_existing_ticker, test_show_unknown_ticker"
    - path: "watchlist.example.json"
      provides: "5-ticker seed file demonstrating the schema; spans all four long_term_lens values"
    - path: "README.md"
      provides: "Project README with quick-start: install (uv), add/remove/list/show commands, copy-and-edit pattern, schema reference link"
      min_lines: 40
  key_links:
    - from: "cli/main.py:SUBCOMMANDS"
      to: "cli/list_watchlist.py:build_list_parser, list_command AND cli/show_ticker.py:build_show_parser, show_command"
      via: "dict registration extending Plan 04's pattern"
      pattern: "\"list\": (build_list_parser, list_command)"
    - from: "watchlist.example.json"
      to: "watchlist/loader.py:load_watchlist"
      via: "load test verifies the example file is valid (would catch a schema regression in the example)"
      pattern: "load_watchlist(Path(\"watchlist.example.json\"))"
    - from: "README.md"
      to: "watchlist.example.json + cli commands"
      via: "documentation pointing user to copy-and-edit + CLI quick reference"
      pattern: "cp watchlist.example.json"
---

<objective>
Ship the read-only CLI surface (`markets list`, `markets show`), the `watchlist.example.json` seed file, and a minimal README documenting the copy-and-edit onboarding pattern. After this plan, a new user (or future-self) can clone the repo, run `cp watchlist.example.json watchlist.json && uv run markets list`, and immediately see how the system works without reading source code.

Purpose: Closes the "Claude's Discretion" deliverables flagged in CONTEXT.md ("Whether to include a `cli/list_watchlist.py` or `cli/show_ticker.py` for read-only inspection — recommended: yes, low cost, high QoL") and ("Whether to ship a `watchlist.example.json` with 3-5 example tickers — recommended: yes"). Also provides the WATCH-01 confirmation surface — `markets list` on a 30+ ticker file is the user-facing demo of the requirement.

This plan runs **in parallel with Plan 04** (same wave 4) — both touch `cli/main.py` but at the SUBCOMMANDS dict level only. Plan 04 ships a 2-entry dict; Plan 05 appends 2 more entries. Conflict surface is one block of dict literal — easy merge. To minimize friction, Plan 05 should be executed AFTER Plan 04 commits (which the wave-4 dependency ordering naturally produces).

Output: 2 production files, 1 extension to `cli/main.py`, 1 test file with 5 tests, 1 example data file, 1 README. Coverage on `cli/list_watchlist.py` + `cli/show_ticker.py` ≥ 85%. WATCH-01's user-facing demo working: `markets list` on a 35-ticker file prints 35 lines.
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
@.planning/phases/01-foundation-watchlist-per-ticker-config/01-03-loader-SUMMARY.md
@.planning/phases/01-foundation-watchlist-per-ticker-config/01-04-cli-core-SUMMARY.md
@analysts/schemas.py
@watchlist/loader.py
@cli/main.py
@cli/add_ticker.py
@cli/remove_ticker.py

<interfaces>
<!-- This plan extends Plan 04's CLI surface. -->

```python
# cli/list_watchlist.py — public surface
def build_list_parser(p: argparse.ArgumentParser) -> None:
    """Register --watchlist flag (path, default Path('watchlist.json'))."""

def list_command(args: argparse.Namespace) -> int:
    """Print all tickers (sorted alphabetically) with: ticker | lens | thesis | notes preview.
    Returns 0 on success, even for empty watchlist (prints '(empty watchlist)' message)."""

# cli/show_ticker.py — public surface
def build_show_parser(p: argparse.ArgumentParser) -> None:
    """Register positional 'ticker' argument and --watchlist flag."""

def show_command(args: argparse.Namespace) -> int:
    """Print full TickerConfig as a structured dump.
    Returns 1 if ticker not in watchlist (with did-you-mean suggestion mirror of remove behavior)."""
```

Plan 04's `SUBCOMMANDS` dict in `cli/main.py` gets two new entries:
```python
SUBCOMMANDS: dict[str, ...] = {
    "add": (build_add_parser, add_command),
    "remove": (build_remove_parser, remove_command),
    "list": (build_list_parser, list_command),       # ADDED IN THIS PLAN
    "show": (build_show_parser, show_command),       # ADDED IN THIS PLAN
}
```

Plus the imports at the top of `cli/main.py`:
```python
from cli.list_watchlist import build_list_parser, list_command  # ADDED
from cli.show_ticker import build_show_parser, show_command     # ADDED
```
</interfaces>

<corrections_callout>
This plan inherits all three CONTEXT.md corrections from Plans 02-04 (hyphen normalization, model_validator(after), json.dumps(sort_keys=True)). It does NOT introduce new normalization or validation logic — it READS what Plans 02-04 produce and prints it.

One specific implication: the `watchlist.example.json` MUST use hyphenated form for BRK-B (the ticker is in the seed). If we accidentally write `BRK.B` in the example file, the file would still load (the schema normalizes) but the test `test_example_file_loads_cleanly` would catch the regression by re-saving (round-trip mismatch — the file on disk would be `BRK.B` but the loaded model has `BRK-B`, then save_watchlist writes `BRK-B`, breaking byte-identity). The test enforces correctness.

The `markets show` command for an unknown ticker mirrors `markets remove` behavior — same `difflib.get_close_matches(cutoff=0.6)` suggestion logic. Code reuse: extract a `_suggest_ticker(unknown, known)` helper into `cli/_errors.py` (which is the natural shared-utilities home from Plan 04) and call from both `remove_command` and `show_command`. **This is a Plan-04-revision touch** — note in SUMMARY. Acceptable because: (a) the change is additive (new helper, doesn't break existing tests), (b) `_errors.py` is already a shared module, (c) <10 lines.
</corrections_callout>
</context>

<feature>
  <name>cli/list_watchlist.py + cli/show_ticker.py + cli/main.py extension + watchlist.example.json + README</name>
  <files>cli/list_watchlist.py, cli/show_ticker.py, cli/main.py, tests/test_cli_readonly.py, watchlist.example.json, README.md</files>
  <behavior>
**`cli/list_watchlist.py:list_command(args)` behavior:**
- Loads via `load_watchlist(args.watchlist)`
- If empty: prints `"(empty watchlist — try: markets add AAPL --lens value --thesis 200)"` and returns 0
- Otherwise: prints a header line + one line per ticker SORTED ALPHABETICALLY by key:
  ```
  TICKER  LENS         THESIS    NOTES
  AAPL    value        200.00    AI infra play, reload zone $...
  BRK-B   value        -         -
  NVDA    growth       -         AI infra play
  ```
- Notes are truncated at 40 chars with `...` suffix; missing thesis is `-`
- Returns 0
- Output format is plain text (no colors/tables — keep stdlib-only; argparse output is the precedent)

**`cli/show_ticker.py:show_command(args)` behavior:**
- Loads via `load_watchlist(args.watchlist)`
- Normalizes input (same logic as remove): `args.ticker` → canonical hyphen form
- If normalized ticker present: prints structured dump:
  ```
  TICKER: AAPL
  short_term_focus: True
  long_term_lens: value
  thesis_price: 200.0
  technical_levels:
    support: 175.0
    resistance: 220.0
  target_multiples: -
  notes: (none)
  created_at: 2026-04-30T12:34:56+00:00
  updated_at: 2026-04-30T12:34:56+00:00
  ```
  Returns 0.
- If not present: same suggestion behavior as remove (uses `_suggest_ticker` helper from `cli/_errors.py`); prints `"error: ticker {X!r} not in watchlist."` plus optional `" did you mean {Y!r}?"`; returns 1.

**`cli/main.py` extension:**
- Append two imports: `from cli.list_watchlist import ...` and `from cli.show_ticker import ...`
- Append two entries to SUBCOMMANDS dict
- Verify all four subcommands appear in `markets --help` output

**`watchlist.example.json` content:**
- 5 tickers: AAPL (value, thesis 200), NVDA (growth, notes "AI infra"), BRK-B (value), GME (contrarian, notes "volatility test"), V (mixed, pe_target 30)
- Spans all four `long_term_lens` values
- BRK-B uses hyphen form (NOT BRK.B) per CONTEXT.md correction #1
- Generated by:
  ```
  uv run markets add AAPL --lens value --thesis 200 --watchlist watchlist.example.json
  uv run markets add NVDA --lens growth --notes "AI infra" --watchlist watchlist.example.json
  uv run markets add BRK-B --lens value --watchlist watchlist.example.json
  uv run markets add GME --lens contrarian --notes "volatility test" --watchlist watchlist.example.json
  uv run markets add V --lens mixed --pe-target 30 --watchlist watchlist.example.json
  ```
  (This dogfoods the CLI — proves end-to-end correctness while producing the example.)

**`README.md` content (~50-80 lines):**
- Project tagline (one sentence: "Personal stock research dashboard — Phase 1: Watchlist + Per-Ticker Config")
- Quick-start section:
  ```
  ## Quick start
  
  Prerequisites: Python 3.12+, uv (https://docs.astral.sh/uv/)
  
  Install:
      uv sync --dev
  
  Try the example watchlist:
      cp watchlist.example.json watchlist.json
      uv run markets list
      uv run markets show AAPL
  
  Add/remove tickers:
      uv run markets add MSFT --lens growth --thesis 450
      uv run markets remove GME --yes
  
  See all flags:
      uv run markets add --help
  ```
- Schema reference: 8-line table of TickerConfig fields with description; pointer to `analysts/schemas.py`
- Run tests: `uv run pytest`
- Phase ROADMAP pointer: link to `.planning/ROADMAP.md`
- Provenance note: `Phase 1 has no direct adaptations from reference repos (virattt/ai-hedge-fund, TauricResearch/TradingAgents) — neither has a persistent watchlist abstraction. Future phases will carry header-comment provenance.`

**Test cases (RED → GREEN):**

`tests/test_cli_readonly.py:` (uses `empty_watchlist_path`, `seeded_watchlist_path`, `large_watchlist_path` fixtures)
- `test_list_empty` — call `main(["list", "--watchlist", str(empty_watchlist_path)])`; capture stdout; assert exit 0, stdout contains "empty"
- `test_list_with_tickers` — call `main(["list", "--watchlist", str(seeded_watchlist_path)])`; assert exit 0, stdout contains "AAPL", "BRK-B", "NVDA"; assert order is alphabetical (AAPL before BRK-B before NVDA)
- `test_list_30_plus_tickers` — call `main(["list", "--watchlist", str(large_watchlist_path)])`; assert exit 0, stdout contains all 35 ticker symbols (count lines minus header — should be 35) — **this is WATCH-01's user-facing demo probe**
- `test_show_existing_ticker` — call `main(["show", "AAPL", "--watchlist", str(seeded_watchlist_path)])`; assert exit 0, stdout contains "TICKER: AAPL", "long_term_lens: value", "thesis_price: 200"
- `test_show_unknown_ticker` — call `main(["show", "AAPK", "--watchlist", str(seeded_watchlist_path)])` (typo); assert exit 1, stdout/stderr contains "did you mean" and "AAPL"

Plus an example-file integrity test (file existence may be skipped in tmp_path tests but should still verify):
- `test_example_file_loads_cleanly` — assert `Path("watchlist.example.json").exists()` (relative to repo root); `wl = load_watchlist(Path("watchlist.example.json"))`; assert `len(wl.tickers) == 5`; assert all four lenses represented; assert `"BRK-B" in wl.tickers and "BRK.B" not in wl.tickers` (CONTEXT.md correction #1 sentinel)

For this last test, use a marker `@pytest.mark.skipif(not Path("watchlist.example.json").exists(), reason="example file not yet generated")` OR run the test from repo root via `cwd` — pytest discovers from `testpaths=["tests"]` so cwd is repo root; relative `Path("watchlist.example.json")` resolves correctly.
  </behavior>
  <implementation>
**TDD cycle:**

**RED — commit `test(01-05): add failing readonly + example-file tests`:**
1. Write `tests/test_cli_readonly.py` with 6 tests above. Imports include `from cli.main import main` and `from watchlist.loader import load_watchlist`.
2. Run `uv run pytest tests/test_cli_readonly.py -x` — confirm all FAIL with ImportError on `cli.list_watchlist` / `cli.show_ticker` OR argparse "invalid choice: 'list'" (since they're not yet registered in the dispatcher).

**GREEN — commit `feat(01-05): implement list/show + example file + README`:**

3. Refactor `cli/_errors.py` to add `_suggest_ticker(unknown, known)` helper:
   ```python
   import difflib
   
   def suggest_ticker(unknown: str, known: list[str]) -> str | None:
       matches = difflib.get_close_matches(unknown, known, n=1, cutoff=0.6)
       return matches[0] if matches else None
   ```
   Update `cli/remove_ticker.py` to use this helper instead of inline `difflib.get_close_matches` (small refactor; keeps test_cli_remove green; reduces dup).

4. Write `cli/list_watchlist.py`:
   ```python
   """`markets list` — read-only watchlist dump."""
   from __future__ import annotations
   import argparse
   from pathlib import Path
   from watchlist.loader import load_watchlist
   
   
   def build_list_parser(p: argparse.ArgumentParser) -> None:
       p.add_argument("--watchlist", type=Path, default=Path("watchlist.json"))
   
   
   def list_command(args: argparse.Namespace) -> int:
       wl = load_watchlist(args.watchlist)
       if not wl.tickers:
           print("(empty watchlist — try: markets add AAPL --lens value --thesis 200)")
           return 0
       print(f"{'TICKER':<8}{'LENS':<13}{'THESIS':<10}NOTES")
       for ticker in sorted(wl.tickers.keys()):
           cfg = wl.tickers[ticker]
           thesis_str = f"{cfg.thesis_price:.2f}" if cfg.thesis_price is not None else "-"
           notes = cfg.notes or "-"
           if len(notes) > 40:
               notes = notes[:37] + "..."
           print(f"{ticker:<8}{cfg.long_term_lens:<13}{thesis_str:<10}{notes}")
       return 0
   ```

5. Write `cli/show_ticker.py`:
   ```python
   """`markets show TICKER` — full per-ticker config dump."""
   from __future__ import annotations
   import argparse
   import re
   import sys
   from pathlib import Path
   from watchlist.loader import load_watchlist
   from cli._errors import suggest_ticker
   
   _TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]{0,8}$")
   
   
   def _normalize(s: str) -> str | None:
       norm = s.strip().upper().replace(".", "-").replace("/", "-").replace("_", "-")
       norm = re.sub(r"-+", "-", norm)
       return norm if _TICKER_PATTERN.match(norm) else None
   
   
   def build_show_parser(p: argparse.ArgumentParser) -> None:
       p.add_argument("ticker")
       p.add_argument("--watchlist", type=Path, default=Path("watchlist.json"))
   
   
   def show_command(args: argparse.Namespace) -> int:
       normalized = _normalize(args.ticker)
       if not normalized:
           print(f"error: invalid ticker format {args.ticker!r}", file=sys.stderr)
           return 2
       wl = load_watchlist(args.watchlist)
       if normalized not in wl.tickers:
           hint = suggest_ticker(normalized, list(wl.tickers.keys()))
           msg = f"error: ticker {normalized!r} not in watchlist."
           if hint:
               msg += f" did you mean {hint!r}?"
           print(msg, file=sys.stderr)
           return 1
       cfg = wl.tickers[normalized]
       print(f"TICKER: {cfg.ticker}")
       print(f"short_term_focus: {cfg.short_term_focus}")
       print(f"long_term_lens: {cfg.long_term_lens}")
       print(f"thesis_price: {cfg.thesis_price if cfg.thesis_price is not None else '-'}")
       if cfg.technical_levels:
           print("technical_levels:")
           print(f"  support: {cfg.technical_levels.support if cfg.technical_levels.support is not None else '-'}")
           print(f"  resistance: {cfg.technical_levels.resistance if cfg.technical_levels.resistance is not None else '-'}")
       else:
           print("technical_levels: -")
       if cfg.target_multiples:
           print("target_multiples:")
           print(f"  pe_target: {cfg.target_multiples.pe_target if cfg.target_multiples.pe_target is not None else '-'}")
           print(f"  ps_target: {cfg.target_multiples.ps_target if cfg.target_multiples.ps_target is not None else '-'}")
           print(f"  pb_target: {cfg.target_multiples.pb_target if cfg.target_multiples.pb_target is not None else '-'}")
       else:
           print("target_multiples: -")
       print(f"notes: {cfg.notes if cfg.notes else '(none)'}")
       print(f"created_at: {cfg.created_at or '-'}")
       print(f"updated_at: {cfg.updated_at or '-'}")
       return 0
   ```

6. Edit `cli/main.py` (Plan 04's output) — append imports and SUBCOMMANDS entries:
   ```python
   from cli.list_watchlist import build_list_parser, list_command  # ADD
   from cli.show_ticker import build_show_parser, show_command     # ADD
   
   SUBCOMMANDS: dict[...] = {
       "add": (build_add_parser, add_command),
       "remove": (build_remove_parser, remove_command),
       "list": (build_list_parser, list_command),       # ADD
       "show": (build_show_parser, show_command),       # ADD
   }
   ```
   Verify `uv run markets --help` lists all four subcommands.

7. Generate `watchlist.example.json` by running the 5 commands from the behavior section. Verify the result loads cleanly and round-trips byte-identically (run save_watchlist on the loaded model, compare bytes).

8. Write `README.md` per content spec.

9. Run `uv run pytest tests/test_cli_readonly.py -x` — all 6 tests pass.

10. Run full Phase 1 suite: `uv run pytest --cov=analysts --cov=watchlist --cov=cli --cov-fail-under=90` — global coverage gate. If under 90%, identify uncovered branches and either add tests or accept (with note in SUMMARY) that the gate is at 88-90% due to e.g. argparse help-text branches.

11. Manual smoke test (use real `watchlist.example.json`):
    ```
    cp watchlist.example.json /tmp/wl.json
    uv run markets list --watchlist /tmp/wl.json
    uv run markets show AAPL --watchlist /tmp/wl.json
    uv run markets show ZZZZZ --watchlist /tmp/wl.json   # exit 1 with no suggestion
    uv run markets show AAPK --watchlist /tmp/wl.json    # exit 1 with did-you-mean AAPL
    ```

**REFACTOR (skip):** Code is already minimal.

**Note on `_normalize` duplication:** `cli/show_ticker.py:_normalize` and `cli/remove_ticker.py:remove_command`'s normalization both re-implement what `analysts.schemas.TickerConfig.normalize_ticker` does. This is acknowledged in Plan 04's CORRECTIONS callout. The cleanest fix is to extract a module-level `normalize_ticker(s: str) -> str | None` helper in `analysts/schemas.py` and have all three call sites use it. **If Plan 04's SUMMARY noted that the classmethod-call route worked**, prefer that; otherwise extract the helper here as a Plan-02-revision touch. Either way, document in this plan's SUMMARY.
  </implementation>
</feature>

<verification>
After GREEN:
1. `uv run pytest tests/test_cli_readonly.py -x` — all 6 tests pass
2. Full Phase 1 suite: `uv run pytest -x` — all 22 tests pass (8 schema + 6 loader + 9 cli core + 6 cli readonly minus duplicates = 22-ish)
3. Coverage gate: `uv run pytest --cov=analysts --cov=watchlist --cov=cli --cov-fail-under=90` — passes
4. `uv run markets --help` lists all four subcommands: add, remove, list, show
5. `cp watchlist.example.json /tmp/wl.json && uv run markets list --watchlist /tmp/wl.json` shows 5 tickers in alphabetical order spanning all four lenses
6. `uv run markets show AAPL --watchlist /tmp/wl.json` shows complete structured dump
7. README.md exists and contains the quick-start section with the copy-and-edit pattern
8. `watchlist.example.json` exists at repo root and contains BRK-B (NOT BRK.B)
</verification>

<success_criteria>
- [ ] All 6 readonly tests pass (`uv run pytest tests/test_cli_readonly.py -x`)
- [ ] Full Phase 1 suite green (`uv run pytest -x`)
- [ ] Phase coverage gate ≥ 90% across `analysts`, `watchlist`, `cli` (`--cov-fail-under=90`)
- [ ] `markets list` on `large_watchlist_path` (35 tickers) prints 35 ticker lines — WATCH-01 user-facing demo
- [ ] `markets show AAPL` on seeded watchlist prints full structured dump (all 9 fields visible or "-")
- [ ] `markets show AAPK` (typo) suggests AAPL via difflib — mirror of remove behavior
- [ ] `cli/main.py` SUBCOMMANDS dict has all four entries; `markets --help` lists add, remove, list, show
- [ ] `watchlist.example.json` exists at repo root, contains exactly 5 tickers (AAPL, NVDA, BRK-B, GME, V), spans all four `long_term_lens` values
- [ ] BRK-B in example file uses HYPHEN (CONTEXT.md correction #1 sentinel; `grep "BRK.B" watchlist.example.json` returns no matches)
- [ ] README.md exists with quick-start (uv sync → cp example → markets list/show), schema reference, run-tests instruction
- [ ] WATCH-01 covered: 1 user-facing probe (test_list_30_plus_tickers) + 1 example-file integrity probe
</success_criteria>

<output>
After completion, create `.planning/phases/01-foundation-watchlist-per-ticker-config/01-05-cli-readonly-and-example-SUMMARY.md` documenting:
- Final line counts for `cli/list_watchlist.py`, `cli/show_ticker.py`, `README.md`
- Coverage % on `cli/list_watchlist.py` and `cli/show_ticker.py`
- Confirmation that `markets --help` lists all four subcommands
- Whether `_suggest_ticker` was extracted to `cli/_errors.py` (touches Plan 04 output) — and whether `cli/remove_ticker.py` was updated to use it
- Whether `_normalize` ticker logic was extracted to `analysts/schemas.py` (touches Plan 02 output) OR remains duplicated in show/remove — and rationale
- Output of `markets list --watchlist /tmp/wl.json` after copying example file (paste actual output)
- Output of `markets show AAPL` (paste actual output)
- Final phase coverage % from `uv run pytest --cov=analysts --cov=watchlist --cov=cli --cov-report=term`
- Confirmation that `watchlist.example.json` contains BRK-B (hyphen) — `grep "BRK[\\.\\-]B" watchlist.example.json` shows hyphenated form only
- Phase 1 closeout: confirm all 4 ROADMAP success criteria are met:
  1. ✓ watchlist.json schema with 30+ tickers loads and validates via Pydantic v2
  2. ✓ CLI utilities cli/add_ticker.py and cli/remove_ticker.py work end-to-end
  3. ✓ Per-ticker config supports all 6 fields
  4. ✓ Invalid configs are rejected with actionable Pydantic error messages
- Recommendation for `/gmd:verify-work`: ready to run, all 21 probes covered.
</output>
