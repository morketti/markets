---
phase: 03-analytical-agents-deterministic-scoring
plan: 01
type: tdd
wave: 1
depends_on: []
files_modified:
  - analysts/signals.py
  - tests/analysts/__init__.py
  - tests/analysts/conftest.py
  - tests/analysts/test_signals.py
  - tests/analysts/test_invariants.py
  - pyproject.toml
  - poetry.lock
  - .planning/REQUIREMENTS.md
  - .planning/ROADMAP.md
autonomous: true
requirements: [ANLY-01, ANLY-02, ANLY-03, ANLY-04]
provides:
  - "AgentSignal Pydantic v2 schema (verdict 5-state, confidence 0-100, evidence list[str], data_unavailable bool, ticker normalization, @model_validator data-unavailable invariant)"
  - "Verdict + AnalystId Literal types — public surface re-imported by all four analyst modules"
  - "tests/analysts/ package + shared conftest fixtures (make_snapshot, make_ticker_config, frozen_now, synthetic_uptrend/downtrend/sideways_history(n))"
  - "vaderSentiment >= 3.3, < 4 added to project dependencies + locked in poetry.lock"
  - "REQUIREMENTS.md ANLY-01..04 wording widened from 3-state to 5-state ladder"
  - "ROADMAP.md Phase 3 goal corrected from 'Five Python analyst modules' to 'Four Python analyst modules' (5th lives in Phase 4 POSE)"
tags: [phase-3, schema, signals, foundation, tdd, wave-0-deps, docs-touch-up]

must_haves:
  truths:
    - "AgentSignal validates: 5-state verdict literal, confidence 0..100 integer, evidence ≤ 10 items each ≤ 200 chars, data_unavailable bool, ticker normalized via analysts.schemas.normalize_ticker, ConfigDict(extra='forbid')"
    - "AgentSignal @model_validator(mode='after') rejects (data_unavailable=True, verdict!='neutral') and (data_unavailable=True, confidence!=0) — invariant enforced at the schema layer"
    - "AgentSignal round-trips through model_dump_json → model_validate_json byte-stable (Pydantic v2 default ISO-8601 datetime serialization)"
    - "tests/analysts/conftest.py exposes make_snapshot, make_ticker_config, frozen_now, synthetic_uptrend_history(n), synthetic_downtrend_history(n), synthetic_sideways_history(n) factory fixtures usable by all four downstream analyst test files"
    - "vaderSentiment >= 3.3, < 4 lands in [project.dependencies] and is resolved into poetry.lock"
    - "REQUIREMENTS.md ANLY-01..04 mention the 5-state ladder explicitly (strong_bullish | bullish | neutral | bearish | strong_bearish)"
    - "ROADMAP.md Phase 3 row says 'Four' Python analyst modules (not 'Five')"
    - "test_invariants.py::test_always_four_signals + test_dark_snapshot_emits_four_unavailable are RED at end of Wave 1 (gated on Wave 2 analyst modules) — file is committed with explicit @pytest.mark.xfail or skip-with-reason markers that flip green by Wave 2 close"
  artifacts:
    - path: "analysts/signals.py"
      provides: "AgentSignal + Verdict + AnalystId types — public schema for all Phase 3 analysts"
      min_lines: 50
    - path: "tests/analysts/__init__.py"
      provides: "package marker — required for pytest collection of tests/analysts/"
      min_lines: 0
    - path: "tests/analysts/conftest.py"
      provides: "shared fixtures: make_snapshot, make_ticker_config, frozen_now, synthetic_*_history(n)"
      min_lines: 100
    - path: "tests/analysts/test_signals.py"
      provides: "≥10 schema tests covering shape, validators, invariants, round-trip"
      min_lines: 80
    - path: "tests/analysts/test_invariants.py"
      provides: "cross-cutting invariant tests (always 4 signals, dark snapshot ⇒ 4 data_unavailable=True signals); RED-then-GREEN across Waves"
      min_lines: 30
  key_links:
    - from: "analysts/signals.py"
      to: "analysts.schemas.normalize_ticker"
      via: "field_validator(mode='before') reuses single-source-of-truth normalizer (same pattern as analysts/data/*.py)"
      pattern: "from analysts.schemas import normalize_ticker"
    - from: "analysts/signals.py"
      to: "Pydantic v2 model_validator(mode='after')"
      via: "data_unavailable=True ⟹ verdict='neutral' AND confidence=0 invariant"
      pattern: "@model_validator\\(mode=\"after\"\\)"
    - from: "tests/analysts/conftest.py"
      to: "analysts.data.snapshot.Snapshot + analysts.data.{prices,fundamentals,news,social}"
      via: "factory fixtures construct synthetic Snapshot objects in-memory (no I/O)"
      pattern: "from analysts.data.snapshot import Snapshot"
    - from: "pyproject.toml"
      to: "vaderSentiment package on PyPI"
      via: "[project.dependencies] entry — locks ≥3.3,<4 (MIT, ~126KB wheel, pure-Python, no transitive deps)"
      pattern: "vaderSentiment"
---

<objective>
Wave 1 / Foundation: ship the AgentSignal schema, the tests/analysts/ package + shared fixture toolbox, the vaderSentiment dependency, and the REQUIREMENTS.md / ROADMAP.md doc touch-ups that align the requirement text with the locked 5-state schema. This plan is the prerequisite every Wave 2 analyst plan (03-02, 03-03, 03-04, 03-05) imports from. Includes the cross-cutting invariant test scaffold that goes RED here and flips GREEN as Wave 2 lands the four analyst modules.

Purpose: AgentSignal is the locked output contract. Without it shipped first, the four Wave 2 analysts can't be written. The test fixtures (make_snapshot, synthetic_*_history) are equally foundational — Wave 2 plans build on them, not on bespoke per-file fixtures. The doc touch-ups close the 3-state-vs-5-state wording drift and the "Five → Four" miscount in ROADMAP.md flagged in 03-CONTEXT.md and 03-RESEARCH.md Open Question #5. The vaderSentiment dep MUST be installed at Wave 1 so 03-04 (news/sentiment analyst) can `from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer` without a Wave 0 reshuffle.

Output: analysts/signals.py (~80 LOC schema + Literal types + @model_validator invariant); tests/analysts/__init__.py + tests/analysts/conftest.py (~150 LOC fixture toolbox); tests/analysts/test_signals.py (~120 LOC, ≥10 schema tests, all GREEN); tests/analysts/test_invariants.py (~50 LOC, 2 cross-cutting tests, marked xfail until Wave 2); pyproject.toml + poetry.lock with vaderSentiment; REQUIREMENTS.md + ROADMAP.md touch-ups committed atomically.
</objective>

<execution_context>
@/home/codespace/.claude/workflows/execute-plan.md
@/home/codespace/.claude/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/03-analytical-agents-deterministic-scoring/03-CONTEXT.md
@.planning/phases/03-analytical-agents-deterministic-scoring/03-RESEARCH.md
@.planning/phases/03-analytical-agents-deterministic-scoring/03-VALIDATION.md

# Existing patterns to mirror
@analysts/schemas.py
@analysts/data/snapshot.py
@analysts/data/prices.py
@analysts/data/fundamentals.py
@analysts/data/news.py
@analysts/data/social.py
@tests/conftest.py

<interfaces>
<!-- Existing Pydantic v2 + ConfigDict(extra="forbid") + ticker-normalization pattern (analysts/data/*.py): -->

```python
# analysts/data/prices.py — exemplar pattern (33 LOC)
from analysts.schemas import normalize_ticker

class PriceSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticker: str
    fetched_at: datetime
    # ... fields ...

    @field_validator("ticker", mode="before")
    @classmethod
    def _normalize_ticker_field(cls, v: object) -> str:
        norm = normalize_ticker(v) if isinstance(v, str) else None
        if norm is None:
            raise ValueError(f"invalid ticker {v!r}")
        return norm
```

<!-- Existing Snapshot aggregate (analysts/data/snapshot.py — Plan 02-06 output): -->

```python
class Snapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticker: str  # normalized
    fetched_at: datetime
    data_unavailable: bool = False
    prices: Optional[PriceSnapshot] = None
    fundamentals: Optional[FundamentalsSnapshot] = None
    filings: list[FilingMetadata] = []
    news: list[Headline] = []
    social: Optional[SocialSignal] = None
    errors: list[str] = []
```

<!-- TickerConfig contract (analysts/schemas.py): -->

```python
class TickerConfig(BaseModel):
    ticker: str  # normalized
    short_term_focus: bool = True
    long_term_lens: Literal["value", "growth", "contrarian", "mixed"] = "mixed"
    thesis_price: Optional[float] = None
    technical_levels: Optional[TechnicalLevels] = None
    target_multiples: Optional[FundamentalTargets] = None  # pe_target, ps_target, pb_target
    notes: str = ""
```

<!-- NEW contract this plan creates — analysts/signals.py: -->

```python
Verdict = Literal["strong_bullish", "bullish", "neutral", "bearish", "strong_bearish"]
AnalystId = Literal["fundamentals", "technicals", "news_sentiment", "valuation"]


class AgentSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticker: str
    analyst_id: AnalystId
    computed_at: datetime
    verdict: Verdict = "neutral"
    confidence: int = Field(ge=0, le=100, default=0)
    evidence: list[str] = Field(default_factory=list, max_length=10)
    data_unavailable: bool = False

    @field_validator("ticker", mode="before")
    @classmethod
    def _normalize_ticker_field(cls, v: object) -> str: ...

    @field_validator("evidence")
    @classmethod
    def _evidence_strings_capped(cls, v: list[str]) -> list[str]:
        # Each string ≤ 200 chars (matches LLM-04 reasoning cap)
        ...

    @model_validator(mode="after")
    def _data_unavailable_implies_neutral_zero(self) -> "AgentSignal":
        # data_unavailable=True ⟹ verdict='neutral' AND confidence=0
        # Closes Pitfall #4 from 03-RESEARCH.md.
        ...
```

<!-- NEW contract — tests/analysts/conftest.py fixtures: -->

```python
@pytest.fixture
def frozen_now() -> datetime:
    """Pinned UTC datetime for reproducibility — same value as 02-06 test fixtures use."""
    return datetime(2026, 5, 1, 13, 30, 0, tzinfo=timezone.utc)

@pytest.fixture
def make_ticker_config(): ...  # returns a builder closure

@pytest.fixture
def make_snapshot(frozen_now): ...  # returns a builder closure

# Synthetic price-history builders for technicals fixtures.
# Each returns list[OHLCBar] with len==n bars, daily-spaced, ending at frozen_now.date().
def synthetic_uptrend_history(n: int = 252, start: float = 100.0, drift: float = 0.05) -> list[OHLCBar]: ...
def synthetic_downtrend_history(n: int = 252, start: float = 200.0, drift: float = -0.05) -> list[OHLCBar]: ...
def synthetic_sideways_history(n: int = 252, start: float = 150.0, amplitude: float = 0.02) -> list[OHLCBar]: ...
```

<!-- pyproject.toml [project.dependencies] CURRENT (line 6-13):
       "pydantic>=2.10",
       "yfinance>=0.2.50,<0.3",
       "yahooquery>=2.3,<3",
       "requests>=2.31,<3",
       "feedparser>=6.0,<7",
       "beautifulsoup4>=4.12,<5",

     APPEND ONE LINE:
       "vaderSentiment>=3.3,<4",   # NEW — news sentiment analyst (Phase 3 / 03-04)
-->

<!-- pandas + numpy NOTE: already transitive via yfinance (pandas 3.0.2, numpy 2.4.4 in poetry.lock).
     03-03 (technicals analyst) imports them as needed — DO NOT add as direct deps. -->

<!-- REQUIREMENTS.md current text (lines 31-34):
       - [ ] **ANLY-01**: ... bullish/bearish/neutral verdict + confidence + evidence list
       - [ ] **ANLY-02**: ... covering MA crossovers, momentum (1m/3m/6m), ADX-based trend strength
       - [ ] **ANLY-03**: ... recency weighting and headline-level sentiment classification
       - [ ] **ANLY-04**: ... compares to analyst consensus from yfinance

     UPDATE TO (5-state ladder added; rest preserved):
       - [ ] **ANLY-01**: Fundamentals analyst produces an `AgentSignal` per ticker scoring P/E, P/S, ROE, debt/equity, margins with **5-state ladder verdict (strong_bullish | bullish | neutral | bearish | strong_bearish)** + confidence (0-100) + evidence list
       - [ ] **ANLY-02**: ... 5-state ladder verdict ...
       - [ ] **ANLY-03**: ... 5-state ladder verdict ...
       - [ ] **ANLY-04**: ... 5-state ladder verdict ...
-->

<!-- ROADMAP.md current text (line 14):
       | 3 | Analytical Agents — Deterministic Scoring | Five Python analyst modules emit structured signals per ticker | ANLY-01..04 | 5 | Phase 2 |

     AND line 84:
       **Goal:** Five Python analyst modules produce structured signals per ticker, all pure-function and unit-testable.

     UPDATE TO "Four" — fifth analyst is Position-Adjustment in Phase 4. -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add vaderSentiment dependency + lock</name>
  <files>pyproject.toml, poetry.lock</files>
  <behavior>
    Single additive change to [project.dependencies]: append `"vaderSentiment>=3.3,<4"`. Then resolve poetry.lock so 03-04 (news sentiment analyst, Wave 2) can import the package without a Wave 0 reshuffle.

    No tests for this task in isolation — Task 2 imports the package indirectly via the schema's neighbours; Task 5 (test_invariants xfail) does NOT import VADER. The success criterion is: `python -c "from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer; SentimentIntensityAnalyzer().polarity_scores('test')"` runs cleanly inside the project's venv.

    No code changes outside pyproject.toml + poetry.lock. No imports of vaderSentiment land in this plan.
  </behavior>
  <action>
    1. Edit `pyproject.toml` — append `"vaderSentiment>=3.3,<4",` to `[project.dependencies]` after the `beautifulsoup4` line. Preserve formatting (4-space indent, trailing comma, alphabetical-by-vendor order is not required since the existing list isn't sorted).
    2. Resolve dependencies: `poetry lock --no-update` (preserves existing pin set; only adds the new dep). If the project uses `uv` (poetry.lock present in repo per `git status`), use `poetry lock --no-update`; if `uv lock` is the actual workflow check `which uv` first and run `uv lock --upgrade-package vaderSentiment` instead. Note 03-RESEARCH.md Wave 0 Gaps point #5: lockfile is poetry.lock per actual repo state.
    3. Install: `poetry install` (or `uv sync`). Verify: `poetry run python -c "from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer; print(SentimentIntensityAnalyzer().polarity_scores('great quarter beats expectations'))"` should print a dict with keys `neg/neu/pos/compound`.
    4. Commit: `chore(03-01): add vaderSentiment>=3.3,<4 dependency for Phase 3 news/sentiment analyst`
  </action>
  <verify>
    <automated>poetry run python -c "from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer; s = SentimentIntensityAnalyzer().polarity_scores('great quarter beats expectations'); assert 'compound' in s and s['compound'] &gt; 0, s"</automated>
  </verify>
  <done>vaderSentiment ≥3.3 importable inside the project venv; poetry.lock updated; pyproject.toml `[project.dependencies]` lists the package; commit landed.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: tests/analysts/ package + shared conftest fixtures</name>
  <files>tests/analysts/__init__.py, tests/analysts/conftest.py</files>
  <behavior>
    Foundation for all Wave 2 test files. Pure fixture work — no production code touched yet. The schema tests in Task 3 and the four analyst-specific test files in Wave 2 (03-02..03-05) all consume these fixtures.

    Fixtures provided:

    1. `frozen_now` (function-scoped) — `datetime(2026, 5, 1, 13, 30, 0, tzinfo=timezone.utc)`. Single pinned UTC datetime; downstream tests pass it as `computed_at=` to score() functions for byte-stable assertions.

    2. `make_ticker_config` (function-scoped, returns a closure) — keyword-arg builder defaulting to a minimal valid TickerConfig:
       ```python
       def _build(**overrides) -> TickerConfig:
           kwargs = {"ticker": "AAPL"} | overrides
           return TickerConfig(**kwargs)
       return _build
       ```
       Lets tests do `cfg = make_ticker_config(ticker="NVDA", thesis_price=900.0)`.

    3. `make_snapshot` (function-scoped, returns a closure, takes `frozen_now`) — keyword-arg builder defaulting to a minimal valid Snapshot:
       ```python
       def _build(**overrides) -> Snapshot:
           kwargs = {"ticker": "AAPL", "fetched_at": frozen_now} | overrides
           return Snapshot(**kwargs)
       return _build
       ```
       Lets tests do `snap = make_snapshot(prices=PriceSnapshot(...), fundamentals=...)`.

    4. `synthetic_uptrend_history(n: int = 252, start: float = 100.0, daily_drift: float = 0.005) -> list[OHLCBar]` — n bars of daily OHLC ending at frozen_now.date(); each close = previous_close * (1 + daily_drift) + tiny deterministic noise (e.g. `+ 0.001 * (i % 5 - 2)` for HLC variance). open=close*0.998, high=close*1.01, low=close*0.99, volume=1_000_000.

    5. `synthetic_downtrend_history(n, start=200.0, daily_drift=-0.005)` — mirror of #4 with negative drift.

    6. `synthetic_sideways_history(n, start=150.0, amplitude=0.02)` — n bars where close = start * (1 + amplitude * sin(2πi/20)) + tiny noise. Mean reverts; ADX should be low (< 20) on this fixture.

    These three builders are MODULE-level (not pytest fixtures) so they're importable directly from test files: `from tests.analysts.conftest import synthetic_uptrend_history`. Pytest fixtures wrap them when needed; tests can call directly when they want to specify n.

    Determinism: builders use a deterministic noise pattern (no `random.random()`). Two calls with identical args produce identical OHLCBar lists. Verified by Task 5 invariant test indirectly.
  </behavior>
  <action>
    1. Create `tests/analysts/__init__.py` — empty file (just the byte `\n` is fine; pytest needs the package marker so `from tests.analysts.conftest import ...` works in deeper test files).

    2. Create `tests/analysts/conftest.py` with the fixture toolbox:
       - Module docstring referencing 03-RESEARCH.md Pattern 2 (factory fixtures over fixture classes).
       - Imports: `from datetime import date, datetime, timedelta, timezone`, `import math`, `import pytest`, `from analysts.schemas import TickerConfig`, `from analysts.data.snapshot import Snapshot`, `from analysts.data.prices import OHLCBar`.
       - Constant: `FROZEN_DT = datetime(2026, 5, 1, 13, 30, 0, tzinfo=timezone.utc)`.
       - Module-level `synthetic_uptrend_history(n, start=100.0, daily_drift=0.005)` builder. Use frozen_now.date() - timedelta(days=n - 1) as start date; iterate forward day-by-day; each close = prev * (1 + daily_drift) + 0.001 * ((i % 5) - 2); open = close * 0.998; high = close * 1.01; low = close * 0.99; volume = 1_000_000 + (i * 100). Build OHLCBar(date=d, open=o, high=h, low=l, close=c, volume=v).
       - Module-level `synthetic_downtrend_history(n, start=200.0, daily_drift=-0.005)` — same shape, negative drift, low high inversion preserved (high > close > low).
       - Module-level `synthetic_sideways_history(n, start=150.0, amplitude=0.02)` — close = start * (1 + amplitude * math.sin(2 * math.pi * i / 20)) + tiny noise.
       - `@pytest.fixture def frozen_now() -> datetime: return FROZEN_DT`.
       - `@pytest.fixture def make_ticker_config():` returns a closure as described.
       - `@pytest.fixture def make_snapshot(frozen_now):` returns a closure as described.

       Add inline guard rails: each builder asserts `n >= 1` (raises `ValueError` otherwise so a typo in a test surfaces clearly), and asserts `start > 0` (price positivity).

    3. Smoke-verify the fixtures load by running `poetry run pytest tests/analysts/conftest.py --collect-only -q`. Expected: zero tests collected (it's a conftest), zero errors. If errors surface, fix before commit.

    4. Commit: `test(03-01): scaffold tests/analysts/ package + shared fixture toolbox (frozen_now, make_snapshot, make_ticker_config, synthetic_*_history)`

    Determinism note (in module docstring): "Builders use no random sources; two calls with identical args produce byte-identical OHLCBar lists. Tests that depend on this property pin n explicitly."
  </action>
  <verify>
    <automated>poetry run pytest tests/analysts/ --collect-only -q &amp;&amp; poetry run python -c "from tests.analysts.conftest import synthetic_uptrend_history, synthetic_downtrend_history, synthetic_sideways_history; up = synthetic_uptrend_history(252); dn = synthetic_downtrend_history(252); sw = synthetic_sideways_history(252); assert len(up) == len(dn) == len(sw) == 252; assert up[-1].close &gt; up[0].close; assert dn[-1].close &lt; dn[0].close; print('OK', up[-1].close, dn[-1].close)"</automated>
  </verify>
  <done>tests/analysts/__init__.py exists; tests/analysts/conftest.py defines frozen_now + make_ticker_config + make_snapshot fixtures + 3 synthetic_*_history(n) module-level builders; pytest collects the package without errors; smoke import of the three builders works; commit landed.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: AgentSignal schema (RED → GREEN, ≥10 tests)</name>
  <files>tests/analysts/test_signals.py, analysts/signals.py</files>
  <behavior>
    Locked schema per 03-CONTEXT.md, with the @model_validator invariant from 03-RESEARCH.md Pitfall #4 included (CONTEXT.md `extra="forbid"` discipline says: enforce invariants at the schema layer, not at caller convention).

    Tests in `tests/analysts/test_signals.py` (≥10):
    - test_signal_minimum_valid: AgentSignal(ticker="AAPL", analyst_id="fundamentals", computed_at=frozen_now) — defaults: verdict="neutral", confidence=0, evidence=[], data_unavailable=False. All four field defaults assert.
    - test_ticker_normalization: AgentSignal(ticker="brk.b", ...) → .ticker == "BRK-B" (delegates to analysts.schemas.normalize_ticker — same pattern as Snapshot, PriceSnapshot).
    - test_ticker_invalid_raises: AgentSignal(ticker="123!@#", ...) → ValidationError with "ticker" in loc.
    - test_verdict_literal_rejects_unknown: AgentSignal(..., verdict="moonshot") → ValidationError.
    - test_verdict_5_state_accepts_all: parametrize over ["strong_bullish", "bullish", "neutral", "bearish", "strong_bearish"] — each constructs cleanly (ALL must be acceptable; the model_validator only fires when data_unavailable=True so non-default verdict is fine when data_unavailable=False).
    - test_confidence_range_lo: AgentSignal(..., confidence=-1) → ValidationError.
    - test_confidence_range_hi: AgentSignal(..., confidence=101) → ValidationError.
    - test_confidence_accepts_0_and_100: AgentSignal(..., confidence=0) cleanly; AgentSignal(..., confidence=100) cleanly.
    - test_evidence_max_items: AgentSignal(..., evidence=["a"] * 11) → ValidationError ("evidence" + "max_length" or similar).
    - test_evidence_string_too_long: AgentSignal(..., evidence=["x" * 201]) → ValidationError.
    - test_evidence_empty_list_ok: AgentSignal(..., evidence=[]) cleanly.
    - test_extra_field_forbidden: AgentSignal(ticker="AAPL", analyst_id="fundamentals", computed_at=frozen_now, metadata={"x": 1}) → ValidationError ("metadata" extra not allowed).
    - test_data_unavailable_invariant_violation_verdict: AgentSignal(..., data_unavailable=True, verdict="bullish") → ValidationError mentioning "data_unavailable" and "verdict". Closes Pitfall #4.
    - test_data_unavailable_invariant_violation_confidence: AgentSignal(..., data_unavailable=True, confidence=80) → ValidationError mentioning "data_unavailable" and "confidence".
    - test_data_unavailable_clean_path: AgentSignal(..., data_unavailable=True) (verdict default "neutral", confidence default 0, evidence=["reason"]) — VALID.
    - test_json_round_trip: build a signal; `s2 = AgentSignal.model_validate_json(s1.model_dump_json())`; `assert s1 == s2`. Verifies datetime ISO-8601 round-trip + extra="forbid" doesn't choke on its own JSON output.
    - test_byte_stable_serialization: `json.dumps(s.model_dump(mode="json"), sort_keys=True, indent=2) + "\n"` produces byte-identical output across two calls (mirrors watchlist/loader pattern). This is forward-compat scaffolding for Phase 5 snapshot writes that will include AgentSignal.

    Implementation in `analysts/signals.py`:
    - Module docstring: provenance comment block per PROJECT.md / 03-RESEARCH.md Reference Repo File Mapping section. Adapted from virattt's signal/confidence/reasoning Pydantic shape; modifications: 5-state Verdict (vs 3-state), evidence: list[str] (vs reasoning: str), ConfigDict(extra="forbid"), ticker normalization, data_unavailable bool, @model_validator invariant.
    - Verdict + AnalystId Literal types at module level.
    - AgentSignal class per the interfaces block at the top of the plan, INCLUDING the @model_validator(mode="after") that enforces data_unavailable=True ⟹ verdict="neutral" AND confidence=0.
  </behavior>
  <action>
    RED:
    1. Write `tests/analysts/test_signals.py` with the ≥16 tests above. Imports: `from datetime import datetime, timezone`, `import json`, `import pytest`, `from pydantic import ValidationError`, `from analysts.signals import AgentSignal, Verdict, AnalystId`. Use `frozen_now` fixture from conftest.
    2. Run `poetry run pytest tests/analysts/test_signals.py -x -q` → ImportError on `analysts.signals` (module does not exist).
    3. Commit: `test(03-01): add failing tests for AgentSignal schema (5-state verdict, invariants, round-trip)`

    GREEN:
    4. Implement `analysts/signals.py` per the interfaces block:
       - `from __future__ import annotations`
       - Imports: `from datetime import datetime`, `from typing import Literal`, `from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator`, `from analysts.schemas import normalize_ticker`.
       - Module docstring with the provenance comment block (~10 lines) — name virattt source file, list our modifications.
       - `Verdict = Literal["strong_bullish", "bullish", "neutral", "bearish", "strong_bearish"]`
       - `AnalystId = Literal["fundamentals", "technicals", "news_sentiment", "valuation"]`
       - `class AgentSignal(BaseModel):` with `model_config = ConfigDict(extra="forbid")` and 7 fields as specced.
       - `@field_validator("ticker", mode="before")` delegating to normalize_ticker (mirror analysts/data/prices.py exactly).
       - `@field_validator("evidence")` walking the list, raising ValueError on any string > 200 chars (Pydantic Field(max_length=10) handles count; the per-string cap needs the validator).
       - `@model_validator(mode="after")` enforcing `data_unavailable=True ⟹ verdict=="neutral" AND confidence==0`. Error message includes both fields' actual values for debuggability.
    5. Run `poetry run pytest tests/analysts/test_signals.py -v` → all green.
    6. Coverage check: `poetry run pytest --cov=analysts.signals --cov-branch tests/analysts/test_signals.py` → ≥90% line / ≥85% branch.
    7. Full repo regression: `poetry run pytest -x -q` → 177+ existing tests still green; new schema tests pass.
    8. Commit: `feat(03-01): AgentSignal Pydantic schema with 5-state verdict + data_unavailable invariant`
  </action>
  <verify>
    <automated>poetry run pytest tests/analysts/test_signals.py -v && poetry run pytest --cov=analysts.signals --cov-branch tests/analysts/test_signals.py && poetry run pytest -x -q</automated>
  </verify>
  <done>analysts/signals.py shipped with AgentSignal + Verdict + AnalystId + @model_validator invariant; ≥16 tests green; coverage ≥90/85; full repo regression green; commits landed.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 4: Cross-cutting invariant scaffold (RED until Wave 2 ships)</name>
  <files>tests/analysts/test_invariants.py</files>
  <behavior>
    Tests cover behavior that REQUIRES all four Wave 2 analyst modules to be present. They go RED at end of Wave 1 (analyst modules don't exist yet); they MUST flip GREEN by end of Wave 2. We commit the file with explicit `pytest.mark.xfail(reason=..., strict=True)` markers — strict=True so an unexpected GREEN fails loudly (a Wave 2 plan accidentally over-shipped) and so the natural "RED until 03-02..03-05 land" state isn't a CI block.

    Two tests:

    1. `test_always_four_signals(make_snapshot, make_ticker_config, frozen_now)`:
       Imports the four analyst modules (`from analysts import fundamentals, technicals, news_sentiment, valuation`); for a representative populated Snapshot + TickerConfig, calls each `score()`, asserts: each call returns an AgentSignal; the four returned analyst_id values are exactly {"fundamentals", "technicals", "news_sentiment", "valuation"}. Confirms the "always 4 signals per ticker" invariant from 03-CONTEXT.md.

       Marker: `@pytest.mark.xfail(reason="Wave 2 plans 03-02..03-05 ship the four analyst modules; flips green when last lands", strict=True)`.

    2. `test_dark_snapshot_emits_four_unavailable(make_snapshot, make_ticker_config, frozen_now)`:
       Build a snapshot with `data_unavailable=True, prices=None, fundamentals=None, news=[], social=None, filings=[]`. Call all four analyst score() functions. Assert: each returned signal has `data_unavailable=True`, `verdict="neutral"`, `confidence=0`, exactly one evidence string explaining the unavailability. Confirms the UNIFORM RULE from 03-CONTEXT.md.

       Same xfail marker.

    File header comment: "These two tests are integration-style — they exercise the contract every Wave 2 analyst plan promises. They xfail until Plans 03-02 / 03-03 / 03-04 / 03-05 ship; the LAST Wave 2 plan must remove the @pytest.mark.xfail markers and verify the tests pass naturally."

    Wave 2 close-out checkpoint: 03-05 (the last Wave 2 plan to commit per dependency graph) explicitly removes the xfail markers in its final task. This is documented in 03-05's plan body to prevent the markers being forgotten.
  </behavior>
  <action>
    1. Create `tests/analysts/test_invariants.py` with the file header comment and 2 xfail-marked tests as described.
    2. Imports: `import pytest`, `from datetime import datetime, timezone`. The four analyst-module imports go inside each test (so the file collects cleanly even before 03-02..03-05 land — `ImportError` inside an xfail test is the expected RED state).
    3. Run `poetry run pytest tests/analysts/test_invariants.py -v` — expect both tests to be reported as XFAIL (expected failure, OK exit). If pytest version doesn't surface them as XFAIL, ensure markers use `strict=True`.
    4. Commit: `test(03-01): scaffold cross-cutting invariant tests (xfail until Wave 2 analysts ship)`

    Document in this task's commit message: "Tests xfail until Wave 2 plans 03-02..03-05 ship the four analyst modules. Plan 03-05 removes the markers and the tests flip green naturally."
  </action>
  <verify>
    <automated>poetry run pytest tests/analysts/test_invariants.py -v --no-header 2>&1 | grep -E "(XFAIL|xfailed|2 xfailed)" && poetry run pytest tests/analysts/ -v</automated>
  </verify>
  <done>tests/analysts/test_invariants.py committed with 2 xfail-marked tests. Pytest runs cleanly (XFAIL state, exit 0). 03-05 will remove the markers in its final task.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 5: REQUIREMENTS.md ANLY-01..04 wording widening (3-state → 5-state ladder)</name>
  <files>.planning/REQUIREMENTS.md</files>
  <behavior>
    Atomic doc-touch: lines 31-34 of REQUIREMENTS.md currently say "bullish/bearish/neutral verdict" (3-state). The locked AgentSignal schema is 5-state. Widen the requirement text to explicitly name the 5 states. No code change; no test change.

    Single-commit doc fix. Surgical — preserve all surrounding text.
  </behavior>
  <action>
    1. Read `.planning/REQUIREMENTS.md` lines 30-35 to confirm exact current wording.
    2. Use Edit tool on `.planning/REQUIREMENTS.md` for each of 4 entries (or one Edit each). Target text and replacement:

       ANLY-01:
         FROM: `... margins with bullish/bearish/neutral verdict + confidence + evidence list`
         TO:   `... margins with 5-state ladder verdict (strong_bullish | bullish | neutral | bearish | strong_bearish) + confidence (0-100 int) + evidence list (≤10 items, each ≤200 chars)`

       ANLY-02:
         FROM: `... covering MA crossovers, momentum (1m/3m/6m), ADX-based trend strength`
         TO:   `... covering MA crossovers, momentum (1m/3m/6m), ADX-based trend strength; 5-state ladder verdict (strong_bullish | bullish | neutral | bearish | strong_bearish) + confidence (0-100 int) + evidence list`

       ANLY-03:
         FROM: `... with recency weighting and headline-level sentiment classification`
         TO:   `... with recency weighting (3-day half-life) and per-headline sentiment via VADER; 5-state ladder verdict + confidence + evidence list`

       ANLY-04:
         FROM: `... compares to analyst consensus from yfinance`
         TO:   `... compares to analyst consensus from yfinance (when available); 5-state ladder verdict + confidence + evidence list`

    3. Verify diff is ONLY these 4 lines: `git diff .planning/REQUIREMENTS.md` should show four hunks, each a single-line change. No other lines mutated.
    4. Commit: `docs(03-01): widen REQUIREMENTS ANLY-01..04 verdict wording to 5-state ladder`
  </action>
  <verify>
    <automated>grep -c "5-state ladder" .planning/REQUIREMENTS.md | grep -E "^[4-9]$|^[1-9][0-9]$" && ! grep -E "ANLY-0[1-4].*bullish/bearish/neutral" .planning/REQUIREMENTS.md</automated>
  </verify>
  <done>REQUIREMENTS.md ANLY-01..04 mention "5-state ladder" with the explicit Literal values; old "bullish/bearish/neutral" wording removed from those four entries; surrounding requirements unchanged; single docs-only commit.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 6: ROADMAP.md "Five → Four" Phase 3 wording correction</name>
  <files>.planning/ROADMAP.md</files>
  <behavior>
    Atomic doc-touch: ROADMAP.md says "Five Python analyst modules" in two places (line 14 of the Phase Summary table and line 84 of the Phase 3 Goal section). Per 03-CONTEXT.md and 03-RESEARCH.md Open Question #5, the 5th analyst is Position-Adjustment which lives in Phase 4. Phase 3 ships exactly four. Update both occurrences to "Four".

    Also update the existing `Plans:` section under Phase 3 to enumerate 03-01..03-05 with brief objectives (replaces whatever placeholder ROADMAP.md currently has, if any). This step is what `update_roadmap` of the planner workflow normally handles; we explicitly script it here so the touch-up is a single deterministic commit.
  </behavior>
  <action>
    1. Edit `.planning/ROADMAP.md`:
       - Line 14 (Phase Summary table row): change `Five Python analyst modules emit structured signals per ticker` → `Four Python analyst modules emit structured signals per ticker (5th is Phase 4 POSE)`
       - Line 84 (Phase 3 Goal): change `**Goal:** Five Python analyst modules produce structured signals per ticker, all pure-function and unit-testable.` → `**Goal:** Four Python analyst modules produce structured signals per ticker, all pure-function and unit-testable. (5th analyst — Position-Adjustment — lives in Phase 4 / POSE-01..05.)`
       - Append a `**Plans:** 5 plans` line under Phase 3's `**Pitfalls addressed:**` line (around line 97), and below it a `Plans:` checkbox list:
         ```
         Plans:
         - [ ] 03-01-signals-PLAN.md — AgentSignal schema + tests/analysts/ scaffold + vaderSentiment dep + REQUIREMENTS/ROADMAP touch-ups
         - [ ] 03-02-fundamentals-PLAN.md — fundamentals analyst (5-metric per-config + fallback bands + 5-state ladder)
         - [ ] 03-03-technicals-PLAN.md — technicals analyst (MA20/50/200 + momentum 1m/3m/6m + ADX(14) + warm-up guards; hand-rolled pandas math)
         - [ ] 03-04-news-sentiment-PLAN.md — news/sentiment analyst (VADER per-headline + 3-day-half-life recency + source weighting)
         - [ ] 03-05-valuation-PLAN.md — valuation analyst (thesis_price > target_multiples > yfinance consensus blend; depends on 02-07)
         ```
    2. Verify diff: `git diff .planning/ROADMAP.md` shows the 2 single-line wording changes + the appended Plans block. No other lines mutated.
    3. Commit: `docs(03-01): correct ROADMAP Phase 3 'Five → Four' analyst count + populate plan list`
  </action>
  <verify>
    <automated>! grep -E "Five Python analyst" .planning/ROADMAP.md && grep -c "Four Python analyst" .planning/ROADMAP.md | grep -E "^[2-9]$|^[1-9][0-9]$" && grep -c "03-0[1-5].*PLAN.md" .planning/ROADMAP.md | grep -E "^5$"</automated>
  </verify>
  <done>ROADMAP.md Phase 3 row and Phase 3 detail Goal both say "Four"; "Five Python analyst" string removed; Plans list lists 03-01..03-05 as `- [ ]` checkboxes with brief objectives; single docs-only commit.</done>
</task>

</tasks>

<verification>
- All 6 tasks ship as atomic commits (Task 1 chore, Tasks 2-4 TDD-style with separate red/green commits, Tasks 5-6 docs).
- Coverage gate: ≥90% line / ≥85% branch on `analysts/signals.py`. (No coverage requirement on conftest fixtures or test files — those are exercised by Wave 2.)
- Full repo regression after each commit: `poetry run pytest -x -q` ≥ 177 pre-existing tests + 16+ new schema tests + 2 xfail invariant tests = all green (or XFAIL where expected).
- vaderSentiment importable inside the venv (Task 1 verify).
- tests/analysts/conftest.py fixtures importable + builders deterministic (Task 2 verify).
- AgentSignal schema enforces every invariant locked in 03-CONTEXT.md, including the @model_validator from 03-RESEARCH.md Pitfall #4.
- test_invariants.py committed with strict xfail markers — pytest exits 0 with XFAIL summary; 03-05 removes the markers as its final task and the tests flip green.
- REQUIREMENTS.md ANLY-01..04 read "5-state ladder" + the explicit Literal values; no "bullish/bearish/neutral" residue in those four entries.
- ROADMAP.md Phase 3 says "Four", lists 03-01..03-05 plans, points 5th-analyst-style module to Phase 4 / POSE.

## Cross-Scope Risks

_vault_status=budget_exhausted; re-run /gmd:plan-phase --replan after vault-maintain_
</verification>

<success_criteria>
1. `analysts/signals.py` exports `AgentSignal`, `Verdict`, `AnalystId` with the locked schema + @model_validator invariant.
2. `tests/analysts/__init__.py` exists; `tests/analysts/conftest.py` provides `frozen_now`, `make_ticker_config`, `make_snapshot` fixtures + 3 module-level synthetic-history builders.
3. `tests/analysts/test_signals.py` has ≥16 tests, all green, ≥90% line / ≥85% branch on `analysts/signals.py`.
4. `tests/analysts/test_invariants.py` has 2 xfail-marked tests covering "always 4 signals" + "dark snapshot ⇒ 4 data_unavailable=True"; pytest exits 0 with XFAIL summary.
5. `pyproject.toml` `[project.dependencies]` lists `vaderSentiment>=3.3,<4`; `poetry.lock` resolved; `from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer` works in venv.
6. REQUIREMENTS.md ANLY-01..04 widened to "5-state ladder" wording.
7. ROADMAP.md Phase 3 corrected to "Four" + populated Plans list with 03-01..03-05.
8. Phase 1 + Phase 2 regression suite (177+ tests) still green; new tests additive only.
</success_criteria>

<output>
After completion, create `.planning/phases/03-analytical-agents-deterministic-scoring/03-01-SUMMARY.md` summarizing the 6 commits, naming the AgentSignal contract, the fixture toolbox, the dep addition, and the doc touch-ups. Reference 03-02 / 03-03 / 03-04 / 03-05 as downstream consumers (all of Wave 2 imports `AgentSignal` from `analysts.signals`).

Update `.planning/STATE.md` Recent Decisions with a 03-01 entry naming: AgentSignal schema locked, vaderSentiment dep added, REQUIREMENTS/ROADMAP wording aligned with 5-state ladder, tests/analysts/ scaffolded, Wave 2 unblocked.
</output>
