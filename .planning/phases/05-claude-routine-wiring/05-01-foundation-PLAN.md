---
phase: 05-claude-routine-wiring
plan: 01
type: tdd
wave: 0
depends_on: []
files_modified:
  - pyproject.toml
  - analysts/signals.py
  - routine/__init__.py
  - synthesis/__init__.py
  - prompts/personas/buffett.md
  - prompts/personas/munger.md
  - prompts/personas/wood.md
  - prompts/personas/burry.md
  - prompts/personas/lynch.md
  - prompts/personas/claude_analyst.md
  - prompts/synthesizer.md
  - tests/routine/__init__.py
  - tests/routine/conftest.py
  - tests/routine/test_smoke.py
  - tests/synthesis/__init__.py
  - tests/analysts/test_signals.py
autonomous: true
requirements: [LLM-01, LLM-02]
provides:
  - "anthropic>=0.95,<1 added to pyproject.toml [project].dependencies (locked at 0.95+ for messages.parse(output_format=PydanticModel) constrained-decoding API per 05-RESEARCH.md CORRECTION #3)"
  - "[tool.coverage.run].source extended to include 'routine' and 'synthesis' (Wave 0 module coverage gates)"
  - "[tool.hatch.build.targets.wheel].packages extended to include 'routine' and 'synthesis'"
  - "analysts/signals.py — AnalystId Literal widened from 4 IDs to 10 IDs (4 analytical + 6 persona): fundamentals, technicals, news_sentiment, valuation, buffett, munger, wood, burry, lynch, claude_analyst — closes Pattern #9 from 05-RESEARCH.md and unblocks Wave 3 persona AgentSignals"
  - "routine/__init__.py + synthesis/__init__.py + tests/routine/__init__.py + tests/synthesis/__init__.py + tests/routine/conftest.py — empty placeholder packages so Wave 1-5 plans can land modules without scaffolding overhead"
  - "prompts/personas/{buffett,munger,wood,burry,lynch,claude_analyst}.md + prompts/synthesizer.md — 7 placeholder markdown stubs with locked 5-section structure (Voice Signature / Input Context / Task / Output Schema). Wave 3 / Wave 4 fill in real content; Wave 0 stubs ensure file presence so LLM-01 file-existence tests can land in Wave 3 without ModuleNotFoundError-style 'no such file' failures during Wave 0 smoke."
  - "tests/routine/test_smoke.py — 1 smoke test (test_anthropic_sdk_imports) confirming `from anthropic import AsyncAnthropic, APIError, APIStatusError` works post-install"
  - "tests/analysts/test_signals.py extended with test_analyst_id_widened_to_10 — parametrized test that AgentSignal accepts each of the 10 IDs and rejects 'invalid_id'; existing 4-analytical tests stay GREEN"
tags: [phase-5, foundation, wave-0, sdk-install, analyst-id-widening, scaffolding, tdd]

must_haves:
  truths:
    - "pyproject.toml [project].dependencies contains exactly one new line `anthropic>=0.95,<1` and no other changes; `uv lock` (or `poetry lock`) produces a stable lockfile with anthropic 0.95+ resolved"
    - "[tool.coverage.run].source list includes 'routine' AND 'synthesis' (in addition to the existing 4 entries) — Wave 1-5 modules will be measured"
    - "[tool.hatch.build.targets.wheel].packages list includes 'routine' AND 'synthesis' — wheel build picks up the new packages"
    - "analysts/signals.py AnalystId Literal accepts EXACTLY these 10 string values in this order: fundamentals, technicals, news_sentiment, valuation, buffett, munger, wood, burry, lynch, claude_analyst — order matters for the persona-slate canonical iteration order in Wave 3"
    - "AgentSignal(analyst_id='buffett', ticker='AAPL', computed_at=frozen_now) constructs without ValidationError (i.e. 'buffett' is now a valid AnalystId)"
    - "AgentSignal(analyst_id='claude_analyst', ticker='AAPL', computed_at=frozen_now) constructs without ValidationError"
    - "AgentSignal(analyst_id='not_a_persona', ...) raises ValidationError with 'analyst_id' in loc — Literal narrowness preserved post-widening"
    - "All 6 placeholder persona markdown files exist at prompts/personas/{buffett,munger,wood,burry,lynch,claude_analyst}.md"
    - "Each placeholder persona file contains the 5 locked section headers in order: `# Persona: <Name>`, `## Voice Signature`, `## Input Context`, `## Task`, `## Output Schema` (Wave 3 fills in section bodies; Wave 0 ships with `(stub — Wave 3)` placeholder under each section)"
    - "prompts/synthesizer.md exists with placeholder sections (Wave 4 fills in the synthesizer-prompt locked content from 05-RESEARCH.md Pattern #7)"
    - "routine/__init__.py + synthesis/__init__.py exist as empty files (or single-line module docstrings)"
    - "tests/routine/__init__.py + tests/synthesis/__init__.py + tests/routine/conftest.py exist as empty placeholders (conftest.py will be filled in Wave 2 with the mock_anthropic_client fixture)"
    - "tests/routine/test_smoke.py::test_anthropic_sdk_imports passes after `uv sync` — confirms the new dep installs cleanly and the SDK exposes AsyncAnthropic + APIError + APIStatusError"
    - "tests/analysts/test_signals.py::test_analyst_id_widened_to_10 passes — parametrized over the 10 IDs"
    - "All Phase 1-4 existing tests stay GREEN after the AnalystId widening (regression invariant — widening is strict superset; existing 4 analytical IDs unchanged)"
    - "Coverage on analysts/signals.py stays ≥90% line / ≥85% branch (already at 100% from Phase 3; widening adds 6 Literal entries that don't change branch count)"
  artifacts:
    - path: "pyproject.toml"
      provides: "modified — new dep line `anthropic>=0.95,<1` in [project].dependencies; `routine` + `synthesis` appended to [tool.coverage.run].source AND [tool.hatch.build.targets.wheel].packages"
      min_lines: 50
    - path: "analysts/signals.py"
      provides: "AnalystId Literal widened from 4 to 10 IDs; ALL OTHER LINES UNCHANGED — the AgentSignal class, ConfigDict, validators, model_validator preserved verbatim from Phase 3"
      min_lines: 100
    - path: "routine/__init__.py"
      provides: "empty package marker — Wave 2-5 modules import from this package"
      min_lines: 1
    - path: "synthesis/__init__.py"
      provides: "empty package marker — Wave 1 + Wave 4 modules import from this package"
      min_lines: 1
    - path: "prompts/personas/buffett.md"
      provides: "5-section placeholder stub — Wave 3 fills in content"
      min_lines: 12
    - path: "prompts/personas/munger.md"
      provides: "5-section placeholder stub"
      min_lines: 12
    - path: "prompts/personas/wood.md"
      provides: "5-section placeholder stub"
      min_lines: 12
    - path: "prompts/personas/burry.md"
      provides: "5-section placeholder stub"
      min_lines: 12
    - path: "prompts/personas/lynch.md"
      provides: "5-section placeholder stub"
      min_lines: 12
    - path: "prompts/personas/claude_analyst.md"
      provides: "5-section placeholder stub — Open Claude Analyst (no virattt analog)"
      min_lines: 12
    - path: "prompts/synthesizer.md"
      provides: "synthesizer prompt placeholder — Wave 4 fills in content"
      min_lines: 10
    - path: "tests/routine/__init__.py"
      provides: "empty test package marker"
      min_lines: 1
    - path: "tests/routine/conftest.py"
      provides: "empty conftest placeholder — Wave 2 adds mock_anthropic_client fixture"
      min_lines: 1
    - path: "tests/routine/test_smoke.py"
      provides: "1 smoke test verifying `from anthropic import AsyncAnthropic, APIError, APIStatusError` works"
      min_lines: 10
    - path: "tests/synthesis/__init__.py"
      provides: "empty test package marker"
      min_lines: 1
    - path: "tests/analysts/test_signals.py"
      provides: "extended — 1 new parametrized test (test_analyst_id_widened_to_10) covering all 10 IDs accept + 'invalid_id' rejects; existing tests preserved verbatim"
      min_lines: 200
  key_links:
    - from: "analysts/signals.py"
      to: "Phase 5 routine/persona_runner.py + synthesis/synthesizer.py (downstream consumers)"
      via: "AnalystId Literal widening — persona AgentSignals will set analyst_id to one of the 6 new IDs; Pydantic validates against the widened Literal"
      pattern: "AnalystId = Literal\\["
    - from: "pyproject.toml"
      to: "anthropic Python SDK (PyPI; >=0.95,<1)"
      via: "dependency declaration — uv lock + uv sync resolves the SDK; Wave 2 routine/llm_client.py imports AsyncAnthropic"
      pattern: "anthropic>=0\\.95"
    - from: "tests/routine/test_smoke.py"
      to: "anthropic SDK module surface"
      via: "from anthropic import AsyncAnthropic, APIError, APIStatusError; smoke confirms public surface that Wave 2 depends on"
      pattern: "from anthropic import"
    - from: "prompts/personas/*.md"
      to: "Wave 3 routine/persona_runner.py (file existence + 5-section structure)"
      via: "Path('prompts/personas/{persona_id}.md').read_text() at call time — Wave 3 tests assert file presence + section headers; Wave 0 stubs ensure the path exists"
      pattern: "prompts/personas/[a-z_]+\\.md"
---

<objective>
Wave 0 / Foundation: install the Anthropic Python SDK at `anthropic>=0.95,<1` (locked per 05-RESEARCH.md CORRECTION #3 — `output_format=PydanticModel` shipped in 0.95); widen the `AnalystId` Literal in `analysts/signals.py` from 4 IDs to 10 IDs (4 analytical + 6 persona); scaffold empty `routine/` + `synthesis/` packages and their tests-package twins; drop 7 placeholder markdown stubs at `prompts/personas/*.md` + `prompts/synthesizer.md` with the locked 5-section structure (Wave 3 + Wave 4 fill in real content); ship 1 smoke test confirming the SDK installed cleanly + 1 parametrized regression test confirming the widened AnalystId accepts all 10 IDs and rejects others. ZERO behavior change in Phase 1-4 — every existing test must stay GREEN. This plan unblocks all five subsequent Phase 5 plans (05-02..05-06) which depend on the widened Literal, the package scaffolding, and the SDK presence.

Purpose: Phase 5's surface area is the largest in the project (~1,000-1,200 LOC of production Python + 700-1,000 LOC of markdown prompts + 600-800 LOC of tests across 7 new modules + 7 markdown files). Doing scaffolding inline with each Wave's substantive work would burn ~10% context per plan on plumbing. Wave 0 lands the plumbing in one focused plan so Waves 1-5 can be content-only. The AnalystId widening is the smallest possible Phase 3 surface change (a single Literal expansion); doing it here also surfaces any downstream regression (e.g., a Phase 3 test that hardcoded `assert len(AnalystId.__args__) == 4`) BEFORE Wave 3 needs `analyst_id="buffett"` to work.

The 7 markdown stubs are NOT noise: Wave 3's persona_runner tests assert that `prompts/personas/buffett.md` exists + contains `## Voice Signature`. Without Wave 0 stubs, those tests would fail "file not found" instead of "voice signature missing" — degrading the test failure signal. The 5-section structure is locked at LLM-03; placeholder content is `(stub — Wave 3 fills in)` under each header. Same shape for `prompts/synthesizer.md`.

Output: pyproject.toml with one new dep + two list extensions; analysts/signals.py with the AnalystId Literal widened to 10 entries (everything else unchanged); 4 new empty package files (`routine/__init__.py`, `synthesis/__init__.py`, `tests/routine/__init__.py`, `tests/synthesis/__init__.py`); 1 empty conftest placeholder; 7 markdown stubs with locked 5-section structure; tests/routine/test_smoke.py with 1 SDK-import smoke test; tests/analysts/test_signals.py extended with 1 parametrized AnalystId-widening test (existing tests preserved). All Phase 1-4 regression tests stay GREEN.
</objective>

<execution_context>
@C:/Users/Mohan/.claude/workflows/execute-plan.md
@C:/Users/Mohan/.claude/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/05-claude-routine-wiring/05-CONTEXT.md
@.planning/phases/05-claude-routine-wiring/05-RESEARCH.md

# Existing patterns to mirror
@analysts/signals.py
@analysts/position_signal.py
@tests/analysts/test_signals.py
@tests/analysts/conftest.py
@pyproject.toml

<interfaces>
<!-- Existing AnalystId Literal — analysts/signals.py:41 — to be widened -->

```python
# CURRENT (Phase 3, line 41):
AnalystId = Literal["fundamentals", "technicals", "news_sentiment", "valuation"]

# AFTER WIDENING (this plan):
AnalystId = Literal[
    # Phase 3 analytical analysts (existing 4) — order preserved:
    "fundamentals",
    "technicals",
    "news_sentiment",
    "valuation",
    # Phase 5 persona slate (new 6) — order matches the iteration order
    # used by routine/persona_runner.py asyncio.gather fan-out (Wave 3):
    "buffett",
    "munger",
    "wood",
    "burry",
    "lynch",
    "claude_analyst",
]
```

<!-- Wave 3 will reference this iteration order constant: -->
<!-- PERSONA_IDS = ("buffett", "munger", "wood", "burry", "lynch", "claude_analyst") -->
<!-- Wave 0 only widens the Literal; PERSONA_IDS is created in Wave 3. -->

<!-- pyproject.toml — current state (lines 5-15 + 31 + 46): -->

```toml
dependencies = [
    "pydantic>=2.10",
    "yfinance>=0.2.50,<0.3",
    "yahooquery>=2.3,<3",
    "requests>=2.31,<3",
    "feedparser>=6.0,<7",
    "beautifulsoup4>=4.12,<5",
    "vaderSentiment>=3.3,<4",
]

# [tool.hatch.build.targets.wheel]
packages = ["analysts", "watchlist", "cli", "ingestion"]

# [tool.coverage.run]
source = ["analysts", "watchlist", "cli", "ingestion"]
```

<!-- pyproject.toml — target state after this plan: -->

```toml
dependencies = [
    "pydantic>=2.10",
    "yfinance>=0.2.50,<0.3",
    "yahooquery>=2.3,<3",
    "requests>=2.31,<3",
    "feedparser>=6.0,<7",
    "beautifulsoup4>=4.12,<5",
    "vaderSentiment>=3.3,<4",
    "anthropic>=0.95,<1",          # NEW — locked per 05-RESEARCH.md CORRECTION #3
]

# [tool.hatch.build.targets.wheel]
packages = ["analysts", "watchlist", "cli", "ingestion", "routine", "synthesis"]

# [tool.coverage.run]
source = ["analysts", "watchlist", "cli", "ingestion", "routine", "synthesis"]
```
</interfaces>

<implementation_sketch>
<!-- The 7 placeholder markdown stubs follow this exact template
     (one per persona, with the persona's name in the H1):

  prompts/personas/buffett.md:
  ----------------------------
  # Persona: Warren Buffett

  ## Voice Signature

  (stub — Wave 3 / Plan 05-04 fills in the locked Voice Signature anchor:
  long-term value, owner earnings, moat-first analysis, circle of competence,
  capital allocation discipline. Cross-checked against
  ~/projects/reference/ai-hedge-fund/src/agents/warren_buffett.py.)

  ## Input Context

  (stub — Wave 3 fills in: Snapshot summary + 4 analytical AgentSignals +
  PositionSignal + TickerConfig.)

  ## Task

  (stub — Wave 3 fills in the persona-specific lens task instructions.)

  ## Output Schema

  (stub — Wave 3 fills in: AgentSignal JSON shape with analyst_id="buffett".)

The 6 persona files share this shape; only the H1 name differs:
  - buffett.md  → "# Persona: Warren Buffett"
  - munger.md   → "# Persona: Charlie Munger"
  - wood.md     → "# Persona: Cathie Wood"
  - burry.md    → "# Persona: Michael Burry"
  - lynch.md    → "# Persona: Peter Lynch"
  - claude_analyst.md → "# Persona: Open Claude Analyst"

prompts/synthesizer.md:
-----------------------
# Synthesizer: Per-Ticker Decision

(stub — Wave 4 / Plan 05-05 fills in the locked synthesizer prompt content
per 05-RESEARCH.md Pattern #7: input context, recommendation priority order,
conviction band rules, dual-timeframe summary instructions, dissent-section
rendering instruction, data_unavailable handling. Final length ~150-200 lines.)

## Input Context

(stub)

## Task

(stub)

## Output Schema

(stub)
-->

<!-- routine/__init__.py + synthesis/__init__.py:

  routine/__init__.py:
  --------------------
  """Phase 5 daily-routine package — orchestration for the scheduled Claude Code routine.

  Modules (filled in Waves 2-5):
      llm_client          — Anthropic SDK wrapper + retry + default-factory (Wave 2)
      persona_runner      — async fan-out across 6 personas per ticker (Wave 3)
      synthesizer_runner  — single-call wrapper over synthesis.synthesizer (Wave 4)
      storage             — atomic per-ticker JSON + _index + _status writes (Wave 5)
      git_publish         — git fetch / pull --rebase / add / commit / push (Wave 5)
      run_for_watchlist   — main per-ticker loop (Wave 5)
      entrypoint          — main() entry point invoked by Claude Code Routine (Wave 5)
      quota               — estimate_run_cost + per-call token constants (Wave 5)
  """

  synthesis/__init__.py:
  ----------------------
  """Phase 5 synthesizer package — TickerDecision schema + per-ticker synthesizer LLM call.

  Modules (filled in Waves 1, 4):
      decision     — TickerDecision + DissentSection + TimeframeBand schemas (Wave 1)
      synthesizer  — compute_dissent + synthesize() + per-ticker context build (Wave 4)
  """

tests/routine/__init__.py and tests/synthesis/__init__.py — empty:
  """Tests for the Phase 5 routine + synthesis packages."""

tests/routine/conftest.py — placeholder for Wave 2:
  """Phase 5 routine test fixtures.

  Wave 2 (Plan 05-03) populates this with mock_anthropic_client + fixture-replay.
  Wave 0 ships an empty placeholder so test discovery doesn't fail.
  """
-->

<!-- tests/routine/test_smoke.py — Wave 0 smoke:

  ```python
  """Wave 0 smoke test — confirms the anthropic SDK installed correctly.

  After Wave 0 ships pyproject.toml's anthropic>=0.95,<1 dep, this test
  verifies the public surface that Wave 2 (routine/llm_client.py) depends on
  is importable. If this test fails, Wave 1+ can't proceed.
  """
  from __future__ import annotations


  def test_anthropic_sdk_imports() -> None:
      """SDK public surface needed by routine/llm_client.py is importable."""
      from anthropic import AsyncAnthropic
      from anthropic import APIError
      from anthropic import APIStatusError

      assert AsyncAnthropic is not None
      assert APIError is not None
      assert APIStatusError is not None


  def test_anthropic_messages_parse_present() -> None:
      """messages.parse() is the canonical 2026 structured-output API.

      We can't call it without auth, but we can confirm the attribute path
      exists on a constructed client instance — a regression guard against
      a future SDK rename.
      """
      from anthropic import AsyncAnthropic
      # AsyncAnthropic() reads ANTHROPIC_API_KEY from env; if absent, constructor
      # raises. Use a dummy api_key to bypass — we never call .parse() here.
      client = AsyncAnthropic(api_key="sk-ant-test-not-real")
      assert hasattr(client.messages, "parse"), (
          "anthropic SDK must expose client.messages.parse — required by 05-RESEARCH.md "
          "Pattern #2; if this attribute is missing, the pinned dep version is wrong."
      )
  ```
-->

<!-- tests/analysts/test_signals.py — APPEND ONE new test after the existing tests:

  ```python
  # APPENDED at end of file (preserves all existing tests verbatim):

  import pytest


  @pytest.mark.parametrize(
      "analyst_id",
      [
          # Phase 3 analytical (existing 4):
          "fundamentals",
          "technicals",
          "news_sentiment",
          "valuation",
          # Phase 5 persona slate (new 6):
          "buffett",
          "munger",
          "wood",
          "burry",
          "lynch",
          "claude_analyst",
      ],
  )
  def test_analyst_id_widened_to_10(analyst_id: str, frozen_now) -> None:
      """AnalystId Literal accepts all 10 IDs after Wave 0 widening (Plan 05-01).

      4 analytical IDs are unchanged from Phase 3; the 6 persona IDs are added
      for Phase 5's persona slate (Buffett, Munger, Wood, Burry, Lynch, Open
      Claude Analyst). Persona AgentSignals will be produced in Wave 3 (Plan
      05-04 routine/persona_runner.py); this test locks the Literal contract.
      """
      from analysts.signals import AgentSignal

      signal = AgentSignal(
          ticker="AAPL",
          analyst_id=analyst_id,
          computed_at=frozen_now,
      )
      assert signal.analyst_id == analyst_id


  def test_analyst_id_rejects_invalid(frozen_now) -> None:
      """AnalystId Literal still rejects non-listed strings — narrowness preserved."""
      from pydantic import ValidationError
      from analysts.signals import AgentSignal

      with pytest.raises(ValidationError) as exc_info:
          AgentSignal(
              ticker="AAPL",
              analyst_id="not_a_persona",  # not in the 10 IDs
              computed_at=frozen_now,
          )
      # Loc must surface the offending field
      assert any("analyst_id" in str(err) for err in exc_info.value.errors())


  def test_analyst_id_literal_arity_is_10() -> None:
      """The widened Literal has exactly 10 args — guards against accidental further widening."""
      from typing import get_args
      from analysts.signals import AnalystId

      args = get_args(AnalystId)
      assert len(args) == 10, f"AnalystId widened beyond 10 IDs (got {len(args)}: {args})"
      assert set(args) == {
          "fundamentals", "technicals", "news_sentiment", "valuation",
          "buffett", "munger", "wood", "burry", "lynch", "claude_analyst",
      }
  ```
-->
</implementation_sketch>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: SDK install + pyproject.toml extensions + AnalystId widening (RED → GREEN, 3 tests)</name>
  <files>pyproject.toml, analysts/signals.py, tests/analysts/test_signals.py</files>
  <behavior>
    Mechanical edits + a Pydantic Literal extension. The widening is line-equivalent: 1 line becomes 13 lines (multi-line Literal for readability), but the AgentSignal class + ConfigDict + 3 validators stay verbatim from Phase 3. The 3 new tests in `tests/analysts/test_signals.py` lock the widened Literal contract.

    pyproject.toml changes (3 surgical edits):
    1. `[project].dependencies` — append `"anthropic>=0.95,<1"` as the 8th entry (after vaderSentiment).
    2. `[tool.hatch.build.targets.wheel].packages` — extend `["analysts", "watchlist", "cli", "ingestion"]` → `["analysts", "watchlist", "cli", "ingestion", "routine", "synthesis"]`.
    3. `[tool.coverage.run].source` — extend `["analysts", "watchlist", "cli", "ingestion"]` → `["analysts", "watchlist", "cli", "ingestion", "routine", "synthesis"]`.

    analysts/signals.py change (1 surgical edit):
    - Replace line 41 (`AnalystId = Literal["fundamentals", "technicals", "news_sentiment", "valuation"]`) with the 13-line multi-line Literal per implementation_sketch (4 analytical + 6 persona IDs, with comments delineating the two groups).
    - DO NOT MUTATE any other line. The AgentSignal class, ConfigDict, all 3 validators, the @model_validator, the module docstring — all preserved verbatim.

    Tests in `tests/analysts/test_signals.py` (3 new tests appended; ALL EXISTING TESTS PRESERVED VERBATIM):
    - test_analyst_id_widened_to_10: parametrized over the 10 IDs; each constructs cleanly.
    - test_analyst_id_rejects_invalid: 'not_a_persona' raises ValidationError with 'analyst_id' in error loc.
    - test_analyst_id_literal_arity_is_10: `len(get_args(AnalystId)) == 10`; set equality against the 10 IDs (guards future drift in either direction).
  </behavior>
  <action>
    RED:
    1. Edit `pyproject.toml` (use the Edit tool, 3 separate edits — do NOT rewrite the file):
       a. In `[project].dependencies` block: append `"anthropic>=0.95,<1",` as the line after `"vaderSentiment>=3.3,<4",`.
       b. In `[tool.hatch.build.targets.wheel]`: change `packages = ["analysts", "watchlist", "cli", "ingestion"]` → `packages = ["analysts", "watchlist", "cli", "ingestion", "routine", "synthesis"]`.
       c. In `[tool.coverage.run]`: change `source = ["analysts", "watchlist", "cli", "ingestion"]` → `source = ["analysts", "watchlist", "cli", "ingestion", "routine", "synthesis"]`.
    2. Run `uv sync` (or `poetry lock && poetry install`) to install the anthropic SDK; verify exit 0.
    3. Append the 3 new tests to `tests/analysts/test_signals.py` (do NOT modify any existing test). Add the imports `import pytest`, `from typing import get_args`, `from pydantic import ValidationError`, `from analysts.signals import AnalystId, AgentSignal` (or use the existing module imports if present).
    4. Run `poetry run pytest tests/analysts/test_signals.py::test_analyst_id_widened_to_10 -x -v` → some IDs pass (the 4 analytical) and 6 FAIL with ValidationError (the 6 persona IDs are not yet in the Literal).
    5. Commit (RED): `test(05-01): add failing tests for widened AnalystId Literal (4 analytical + 6 persona = 10 IDs)`.

    GREEN:
    6. Edit `analysts/signals.py` line 41: replace the single-line `AnalystId = Literal[...]` with the multi-line widened version per implementation_sketch (4 analytical + 6 persona, with `# Phase 3 analytical analysts (existing 4)` and `# Phase 5 persona slate (new 6)` separator comments). DO NOT mutate any other line.
    7. Run `poetry run pytest tests/analysts/test_signals.py -v` → all existing tests + 3 new tests GREEN.
    8. Coverage check: `poetry run pytest --cov=analysts.signals --cov-branch tests/analysts/test_signals.py` → ≥90% line / ≥85% branch (already at 100% from Phase 3; adding 6 Literal entries doesn't change branch count).
    9. Phase 1-4 regression: `poetry run pytest -x -q` → all 428+ existing tests still GREEN. Specifically watch for:
       - tests/analysts/test_invariants.py — already extended in Phase 4 with test_dark_snapshot_emits_pose_unavailable; these tests should pass unchanged.
       - tests/analysts/test_fundamentals.py / test_technicals.py / test_news_sentiment.py / test_valuation.py / test_position_adjustment.py — none of these construct AgentSignals with persona IDs, so they're agnostic to the widening.
    10. Sanity grep: `python -c "from typing import get_args; from analysts.signals import AnalystId; assert len(get_args(AnalystId)) == 10; print(get_args(AnalystId))"` outputs the 10-tuple in order.
    11. Commit (GREEN): `feat(05-01): widen AnalystId Literal to 10 IDs (4 analytical + 6 persona slate); add anthropic>=0.95,<1 dep; extend coverage + wheel packages for routine/synthesis`.
  </action>
  <verify>
    <automated>uv sync && poetry run pytest tests/analysts/test_signals.py -v && poetry run pytest --cov=analysts.signals --cov-branch tests/analysts/test_signals.py && poetry run pytest -x -q && python -c "from typing import get_args; from analysts.signals import AnalystId; ids = get_args(AnalystId); assert len(ids) == 10; assert set(ids) == {'fundamentals','technicals','news_sentiment','valuation','buffett','munger','wood','burry','lynch','claude_analyst'}; print('AnalystId widening OK:', ids)"</automated>
  </verify>
  <done>pyproject.toml updated (1 dep + 2 list extensions); analysts/signals.py AnalystId widened to 10 IDs (all other lines preserved); 3 new tests in tests/analysts/test_signals.py all GREEN (parametrized over 10 IDs + invalid-id reject + arity-10 lock); Phase 1-4 regression GREEN (428+ tests); both commits (RED + GREEN) landed; `uv sync` resolved anthropic 0.95+.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Package scaffolding + 7 markdown stubs + SDK smoke test (RED → GREEN, 2 tests)</name>
  <files>routine/__init__.py, synthesis/__init__.py, tests/routine/__init__.py, tests/routine/conftest.py, tests/routine/test_smoke.py, tests/synthesis/__init__.py, prompts/personas/buffett.md, prompts/personas/munger.md, prompts/personas/wood.md, prompts/personas/burry.md, prompts/personas/lynch.md, prompts/personas/claude_analyst.md, prompts/synthesizer.md</files>
  <behavior>
    Pure scaffolding — file creation, no logic. The 7 markdown stubs ship the locked 5-section structure (Voice Signature / Input Context / Task / Output Schema, with `# Persona: <Name>` H1 above) so Wave 3's voice-signature-presence assertions can land WITHOUT requiring Wave 0 to also write 80-150 line real prompts.

    Test file `tests/routine/test_smoke.py` (2 tests):
    - test_anthropic_sdk_imports: from anthropic import AsyncAnthropic, APIError, APIStatusError; assert all three are not None.
    - test_anthropic_messages_parse_present: instantiate AsyncAnthropic(api_key='sk-ant-test-not-real') (no real call); assert `hasattr(client.messages, 'parse')` — guards against SDK API rename in a future minor.

    The 6 persona stubs share the same 12-line template; only the H1 name differs. The synthesizer stub has `# Synthesizer: Per-Ticker Decision` H1 + 4 placeholder sections. Empty `__init__.py` files for routine/, synthesis/, tests/routine/, tests/synthesis/. Empty `conftest.py` placeholder for tests/routine/ (Wave 2 fills with mock_anthropic_client fixture).
  </behavior>
  <action>
    RED:
    1. Write `tests/routine/__init__.py` as an empty file (or single docstring `"""Tests for Phase 5 routine package."""`).
    2. Write `tests/routine/test_smoke.py` per implementation_sketch — 2 tests; uses `from anthropic import AsyncAnthropic, APIError, APIStatusError` and `AsyncAnthropic(api_key='sk-ant-test-not-real')` for the second test.
    3. Run `poetry run pytest tests/routine/test_smoke.py -x -v` → ImportError on `tests.routine` package OR ModuleNotFoundError if the package marker is missing.
       - If `tests/routine/__init__.py` is in place, pytest will still fail because `routine/__init__.py` itself doesn't exist yet (the test imports anthropic, but the test discovery requires the package marker). Either way, RED.
    4. Commit (RED): `test(05-01): add failing smoke test for anthropic SDK + tests/routine package marker`.

    GREEN — file creation:
    5. Write `routine/__init__.py` with the docstring per implementation_sketch (lists the 8 modules Waves 2-5 will fill).
    6. Write `synthesis/__init__.py` with the docstring per implementation_sketch (lists the 2 modules Waves 1 + 4 will fill).
    7. Write `tests/synthesis/__init__.py` as an empty file or 1-line docstring.
    8. Write `tests/routine/conftest.py` with the placeholder docstring per implementation_sketch (empty fixtures; Wave 2 populates).
    9. Create the 6 persona stub files at `prompts/personas/{persona}.md`. Each follows this exact template (only the H1 name + parenthetical persona-specific descriptor differs):

       ```markdown
       # Persona: <Full Name>

       ## Voice Signature

       (stub — Wave 3 / Plan 05-04 fills in the locked Voice Signature anchor.
       Cross-check against ~/projects/reference/ai-hedge-fund/src/agents/<file>.py
       for canonical persona traits.)

       ## Input Context

       (stub — Wave 3 fills in: Snapshot summary + 4 analytical AgentSignals +
       PositionSignal + TickerConfig.)

       ## Task

       (stub — Wave 3 fills in the persona-specific lens task instructions.)

       ## Output Schema

       (stub — Wave 3 fills in: AgentSignal JSON shape with analyst_id="<persona_id>".)
       ```

       The 6 persona-specific values are:
       - `buffett.md`  — `# Persona: Warren Buffett` ; reference `warren_buffett.py` ; `analyst_id="buffett"`
       - `munger.md`   — `# Persona: Charlie Munger` ; reference `charlie_munger.py` ; `analyst_id="munger"`
       - `wood.md`     — `# Persona: Cathie Wood` ; reference `cathie_wood.py` ; `analyst_id="wood"`
       - `burry.md`    — `# Persona: Michael Burry` ; reference `michael_burry.py` ; `analyst_id="burry"`
       - `lynch.md`    — `# Persona: Peter Lynch` ; reference `peter_lynch.py` ; `analyst_id="lynch"`
       - `claude_analyst.md` — `# Persona: Open Claude Analyst` ; reference `(no virattt analog — novel-to-this-project)` ; `analyst_id="claude_analyst"`

    10. Create `prompts/synthesizer.md`:

        ```markdown
        # Synthesizer: Per-Ticker Decision

        (stub — Wave 4 / Plan 05-05 fills in the locked synthesizer prompt content
        per 05-RESEARCH.md Pattern #7: input context, recommendation priority order,
        conviction band rules, dual-timeframe summary instructions, dissent-section
        rendering instruction, data_unavailable handling. Final length ~150-200 lines.)

        ## Input Context

        (stub)

        ## Task

        (stub)

        ## Output Schema

        (stub)
        ```

    11. Run `poetry run pytest tests/routine/test_smoke.py -v` → both tests GREEN (anthropic SDK installed in Task 1; the imports + AsyncAnthropic class instantiation work).
    12. Confirm file presence: `python -c "from pathlib import Path; pids = ['buffett','munger','wood','burry','lynch','claude_analyst']; missing = [p for p in pids if not Path(f'prompts/personas/{p}.md').exists()]; assert not missing, f'missing personas: {missing}'; assert Path('prompts/synthesizer.md').exists(); print('all 7 markdown stubs present')"`.
    13. Confirm 5-section structure in each stub: `python -c "from pathlib import Path; pids = ['buffett','munger','wood','burry','lynch','claude_analyst']; [print(p, all(s in Path(f'prompts/personas/{p}.md').read_text(encoding='utf-8') for s in ['## Voice Signature','## Input Context','## Task','## Output Schema'])) for p in pids]"` — all 6 print `True`.
    14. Phase 1-4 regression: `poetry run pytest -x -q` → all green; new packages don't break existing test discovery.
    15. Coverage source check: `poetry run pytest --cov` → coverage report includes `routine` + `synthesis` (both at 0% LOC since modules are empty docstrings; that's expected for Wave 0 — Wave 1+ adds the LOC).
    16. Commit (GREEN): `feat(05-01): scaffold routine/ + synthesis/ packages; drop 7 markdown stubs at prompts/{personas/*,synthesizer}.md with locked 5-section structure; SDK smoke test green`.
  </action>
  <verify>
    <automated>poetry run pytest tests/routine/test_smoke.py -v && poetry run pytest -x -q && python -c "from pathlib import Path; pids = ['buffett','munger','wood','burry','lynch','claude_analyst']; missing = [p for p in pids if not Path(f'prompts/personas/{p}.md').exists()]; assert not missing, f'missing: {missing}'; assert Path('prompts/synthesizer.md').exists(); [print(p, all(s in Path(f'prompts/personas/{p}.md').read_text(encoding='utf-8') for s in ['## Voice Signature','## Input Context','## Task','## Output Schema'])) for p in pids]; print('OK')"</automated>
  </verify>
  <done>routine/ + synthesis/ + tests/routine/ + tests/synthesis/ packages created with __init__.py markers; tests/routine/conftest.py placeholder ready for Wave 2; tests/routine/test_smoke.py with 2 SDK-import smoke tests GREEN; 6 persona stubs at prompts/personas/*.md + 1 synthesizer stub at prompts/synthesizer.md, all carrying the locked 5-section structure; Phase 1-4 regression GREEN; both commits (RED + GREEN) landed.</done>
</task>

</tasks>

<verification>
- 2 tasks, 4 commits (RED + GREEN per task). TDD discipline preserved.
- Coverage gate: ≥90% line / ≥85% branch on `analysts/signals.py` (already at 100%; widening doesn't change branch count).
- Phase 1-4 regression invariant: ALL 428+ existing tests stay GREEN. The widening is a strict superset of the prior Literal; no existing analyst constructs an AgentSignal with one of the 6 persona IDs.
- `uv sync` resolves `anthropic>=0.95,<1` cleanly; `from anthropic import AsyncAnthropic, APIError, APIStatusError` works post-install.
- 3 new tests added to `tests/analysts/test_signals.py` (parametrized over 10 IDs + invalid-id reject + arity-10 lock).
- 2 new tests added to `tests/routine/test_smoke.py` (SDK imports + messages.parse() attribute presence).
- 7 markdown stubs at `prompts/personas/{6 personas}.md` + `prompts/synthesizer.md` carry the locked 5-section structure; Wave 3 + Wave 4 fill in real content.
- 4 empty `__init__.py` files (routine/, synthesis/, tests/routine/, tests/synthesis/) + 1 placeholder conftest.py.
- pyproject.toml has 3 surgical edits: +1 dep, +2 list extensions; no other changes.
- Wave 1-5 unblocked: 05-02 (synthesis/decision.py + tests/synthesis/test_decision.py); 05-03 (routine/llm_client.py + uses tests/routine/conftest.py mock fixture); 05-04 (routine/persona_runner.py + 6 markdown stubs filled with real content); 05-05 (synthesis/synthesizer.py + prompts/synthesizer.md filled); 05-06 (routine/{storage,git_publish,run_for_watchlist,entrypoint}.py).

## Cross-Scope Risks

_vault_status=budget_exhausted; re-run /gmd:plan-phase --replan after vault-maintain_
</verification>

<success_criteria>
1. `pyproject.toml` contains `anthropic>=0.95,<1` in `[project].dependencies`; `uv sync` installs cleanly.
2. `pyproject.toml` `[tool.hatch.build.targets.wheel].packages` includes `routine` AND `synthesis`.
3. `pyproject.toml` `[tool.coverage.run].source` includes `routine` AND `synthesis`.
4. `analysts/signals.py` `AnalystId` Literal contains exactly these 10 string values in this order: `fundamentals, technicals, news_sentiment, valuation, buffett, munger, wood, burry, lynch, claude_analyst`. All other lines unchanged.
5. `tests/analysts/test_signals.py` has 3 new tests (parametrized over 10 IDs + invalid-id reject + arity-10 lock); all GREEN; existing tests preserved.
6. `tests/routine/test_smoke.py` has 2 SDK-import tests; both GREEN.
7. `routine/__init__.py`, `synthesis/__init__.py`, `tests/routine/__init__.py`, `tests/synthesis/__init__.py`, `tests/routine/conftest.py` all exist as empty/docstring placeholders.
8. 6 placeholder persona markdown files at `prompts/personas/{buffett,munger,wood,burry,lynch,claude_analyst}.md`; each contains the 5 locked section headers (`# Persona: <Name>`, `## Voice Signature`, `## Input Context`, `## Task`, `## Output Schema`).
9. 1 placeholder synthesizer markdown at `prompts/synthesizer.md`; contains 4 locked section headers.
10. Phase 1-4 regression: full repo `poetry run pytest -x -q` exits 0 with all 428+ existing tests + 5 new tests GREEN.
11. Coverage report includes `routine` + `synthesis` packages (at 0% LOC; expected — modules are docstring-only).
12. Wave 1-5 unblocked: subsequent plans can land production code without any further scaffolding.
</success_criteria>

<output>
After completion, create `.planning/phases/05-claude-routine-wiring/05-01-SUMMARY.md` summarizing the 4 commits, naming the AnalystId widening (4→10 IDs), the SDK pin (anthropic>=0.95,<1), the 4 new package markers, the 7 markdown stubs, and the regression invariant (428+ Phase 1-4 tests stayed GREEN). Reference 05-02 (TickerDecision schema) and 05-03 (LLM client) as immediate downstream Wave 1 + Wave 2 consumers.

Update `.planning/STATE.md` Recent Decisions with a 05-01 entry naming: AnalystId widening (Pattern #9 from 05-RESEARCH.md); anthropic SDK installed at >=0.95 (CORRECTION #3 — `output_format=PydanticModel` shipped in 0.95); routine/ + synthesis/ packages scaffolded; 7 markdown stubs landed; Wave 1-5 unblocked.
</output>
</content>
</invoke>