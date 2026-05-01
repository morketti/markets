---
phase: 03-analytical-agents-deterministic-scoring
plan: 02
type: tdd
wave: 2
depends_on: [03-01]
files_modified:
  - analysts/fundamentals.py
  - tests/analysts/test_fundamentals.py
autonomous: true
requirements: [ANLY-01]
provides:
  - "analysts.fundamentals.score(snapshot, config, *, computed_at=None) -> AgentSignal"
  - "Per-config (TickerConfig.target_multiples) + hard-coded fallback band scoring across 5 metrics: P/E, P/S, ROE, debt/equity, profit margin"
  - "5-state ladder verdict via total_to_verdict(normalized_aggregate) helper"
  - "Per-metric isolation: missing one metric does not poison the others (each contributes 0 to aggregate, no evidence string)"
  - "Empty-data uniform rule: snapshot.fundamentals=None or snapshot.data_unavailable=True or snapshot.fundamentals.data_unavailable=True → AgentSignal(data_unavailable=True, verdict='neutral', confidence=0, evidence=[reason])"
  - "Module-level threshold constants at top of file (PE_BULLISH_BELOW, PE_BEARISH_ABOVE, etc.) — tunable by editing this file"
tags: [phase-3, analyst, fundamentals, tdd, pure-function, anly-01]

must_haves:
  truths:
    - "score(snapshot, config) returns an AgentSignal with analyst_id='fundamentals' for every input — never None, never raises for missing data"
    - "Per-config path: when config.target_multiples.pe_target is set, P/E < target * 0.8 → +1 contribution; > target * 1.2 → -1 contribution; within ±20% → 0"
    - "Fallback path: when config.target_multiples is None or pe_target is None, P/E < PE_BULLISH_BELOW → +1; > PE_BEARISH_ABOVE → -1; in between → 0. Same shape for P/S, ROE, D/E, profit_margin against their own constants"
    - "Per-metric isolation: snapshot.fundamentals with pe=None contributes 0 to aggregate but other 4 metrics still score normally; evidence list omits the P/E string but includes the others"
    - "5-state ladder mapping: aggregate normalized to [-1, +1] via total_to_verdict; |x| > 0.6 → strong_*, |x| > 0.2 → directional, else neutral"
    - "Empty-data UNIFORM RULE: when snapshot.data_unavailable=True OR snapshot.fundamentals is None OR snapshot.fundamentals.data_unavailable=True → AgentSignal(data_unavailable=True, verdict='neutral', confidence=0, evidence=[<reason>])"
    - "Provenance header comment names virattt/ai-hedge-fund/src/agents/fundamentals.py and lists the modifications (5-metric vs 13-metric, per-config target_multiples overrides, module-level constants, 5-state verdict)"
    - "Test coverage ≥90% line / ≥85% branch on analysts/fundamentals.py"
  artifacts:
    - path: "analysts/fundamentals.py"
      provides: "score(snapshot, config, *, computed_at=None) -> AgentSignal — pure function, no I/O, no module-level mutable state"
      min_lines: 100
    - path: "tests/analysts/test_fundamentals.py"
      provides: "≥12 tests covering happy path, fallback path, per-metric isolation, empty data, 5-state ladder edges"
      min_lines: 100
  key_links:
    - from: "analysts/fundamentals.py"
      to: "analysts.signals.AgentSignal"
      via: "constructor — only public output type"
      pattern: "from analysts.signals import AgentSignal"
    - from: "analysts/fundamentals.py"
      to: "analysts.data.snapshot.Snapshot + analysts.schemas.TickerConfig"
      via: "score(snapshot: Snapshot, config: TickerConfig) signature — pure function"
      pattern: "def score\\(snapshot: Snapshot, config: TickerConfig"
    - from: "analysts/fundamentals.py"
      to: "snapshot.fundamentals.{pe, ps, roe, debt_to_equity, profit_margin}"
      via: "Optional[float] reads — defensive against None at every metric"
      pattern: "snapshot\\.fundamentals\\.(pe|ps|roe|debt_to_equity|profit_margin)"
    - from: "analysts/fundamentals.py"
      to: "config.target_multiples.{pe_target, ps_target, pb_target}"
      via: "Optional FundamentalTargets reads — fallback to module constants when None"
      pattern: "config\\.target_multiples"
---

<objective>
Wave 2 / ANLY-01: Fundamentals analyst — pure-function deterministic scoring of P/E, P/S, ROE, debt/equity, profit margin against per-`TickerConfig.target_multiples` overrides (when set) or hard-coded fallback bands. Emits one AgentSignal per call. Adapted from virattt/ai-hedge-fund/src/agents/fundamentals.py point-system threshold pattern, narrowed from 13 metrics to the 5 our FundamentalsSnapshot actually carries.

Purpose: First of the four Wave 2 analyst plans. Schema-light, math-light — five Optional[float] reads, five threshold compares, one aggregation. Most direct exercise of the 03-01 AgentSignal contract; cleanest demonstration of the empty-data uniform rule and per-metric isolation. Becomes the template every other Wave 2 analyst follows in shape.

Output: analysts/fundamentals.py (~120 LOC: provenance docstring + module constants + private per-metric helpers + score() function + total_to_verdict helper); tests/analysts/test_fundamentals.py (~150 LOC: 12+ tests covering happy/fallback/per-metric-isolation/empty-data/5-state-ladder edges).
</objective>

<execution_context>
@/home/codespace/.claude/workflows/execute-plan.md
@/home/codespace/.claude/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/03-analytical-agents-deterministic-scoring/03-CONTEXT.md
@.planning/phases/03-analytical-agents-deterministic-scoring/03-RESEARCH.md
@.planning/phases/03-analytical-agents-deterministic-scoring/03-01-SUMMARY.md

# Existing patterns
@analysts/signals.py
@analysts/schemas.py
@analysts/data/snapshot.py
@analysts/data/fundamentals.py
@tests/analysts/conftest.py

<interfaces>
<!-- Wave 1 (03-01) outputs we consume: -->

```python
# analysts/signals.py
Verdict = Literal["strong_bullish", "bullish", "neutral", "bearish", "strong_bearish"]
AnalystId = Literal["fundamentals", "technicals", "news_sentiment", "valuation"]

class AgentSignal(BaseModel):
    ticker: str          # normalized via analysts.schemas.normalize_ticker
    analyst_id: AnalystId
    computed_at: datetime
    verdict: Verdict = "neutral"
    confidence: int = Field(ge=0, le=100, default=0)
    evidence: list[str] = Field(default_factory=list, max_length=10)
    data_unavailable: bool = False
    # @model_validator: data_unavailable=True ⟹ verdict='neutral' AND confidence=0
```

<!-- Existing FundamentalsSnapshot (analysts/data/fundamentals.py) — 5 fields we score: -->

```python
class FundamentalsSnapshot(BaseModel):
    pe: Optional[float] = None              # raw, can be negative for losing firms
    ps: Optional[float] = None
    roe: Optional[float] = None             # decimal — yfinance returns 0.18 for 18%
    debt_to_equity: Optional[float] = None  # raw, can be 0 for unlevered firms
    profit_margin: Optional[float] = None   # decimal — 0.15 for 15%
    # ... pb, free_cash_flow, market_cap, analyst_target_* — IGNORED here
    data_unavailable: bool = False
```

<!-- Existing TickerConfig.target_multiples (analysts/schemas.py): -->

```python
class FundamentalTargets(BaseModel):
    pe_target: Optional[float] = None  # > 0 if set
    ps_target: Optional[float] = None  # > 0 if set
    pb_target: Optional[float] = None  # IGNORED here (no FundamentalsSnapshot.pb scoring in v1)
```

<!-- NEW contract this plan creates: -->

```python
# analysts/fundamentals.py
def score(
    snapshot: Snapshot,
    config: TickerConfig,
    *,
    computed_at: Optional[datetime] = None,
) -> AgentSignal:
    """Score fundamentals deterministically; pure function; never raises for missing data."""
```
</interfaces>

<implementation_sketch>
<!-- Module structure (referenced from 03-RESEARCH.md Pattern 1+2+3): -->

```python
# Module-level constants at top:
PE_BULLISH_BELOW = 15.0
PE_BEARISH_ABOVE = 30.0
PS_BULLISH_BELOW = 2.0
PS_BEARISH_ABOVE = 8.0
ROE_BULLISH_ABOVE = 0.15
ROE_BEARISH_BELOW = 0.05
DE_BULLISH_BELOW = 0.5
DE_BEARISH_ABOVE = 1.5
PM_BULLISH_ABOVE = 0.15
PM_BEARISH_BELOW = 0.05

PER_CONFIG_BAND = 0.20  # ±20% around target_multiples values

# Per-metric helpers (each returns (score: int in {-1,0,+1}, evidence: Optional[str])):
def _score_pe(pe: Optional[float], target: Optional[float]) -> tuple[int, Optional[str]]: ...
def _score_ps(ps: Optional[float], target: Optional[float]) -> tuple[int, Optional[str]]: ...
def _score_roe(roe: Optional[float]) -> tuple[int, Optional[str]]: ...   # no per-config target
def _score_de(de: Optional[float]) -> tuple[int, Optional[str]]: ...     # no per-config target
def _score_pm(pm: Optional[float]) -> tuple[int, Optional[str]]: ...     # no per-config target

# Verdict tiering (private helper — see 03-RESEARCH.md Pattern 3):
def _total_to_verdict(normalized: float) -> Verdict:
    if normalized > 0.6: return "strong_bullish"
    if normalized > 0.2: return "bullish"
    if normalized < -0.6: return "strong_bearish"
    if normalized < -0.2: return "bearish"
    return "neutral"

def score(snapshot, config, *, computed_at=None):
    now = computed_at or datetime.now(timezone.utc)
    # UNIFORM RULE empty-data guard:
    if snapshot.data_unavailable or snapshot.fundamentals is None or snapshot.fundamentals.data_unavailable:
        return AgentSignal(
            ticker=snapshot.ticker,
            analyst_id="fundamentals",
            computed_at=now,
            data_unavailable=True,
            evidence=["fundamentals snapshot unavailable"],
        )
    fund = snapshot.fundamentals
    targets = config.target_multiples  # may be None
    pe_target = targets.pe_target if targets else None
    ps_target = targets.ps_target if targets else None
    sub = [
        _score_pe(fund.pe, pe_target),
        _score_ps(fund.ps, ps_target),
        _score_roe(fund.roe),
        _score_de(fund.debt_to_equity),
        _score_pm(fund.profit_margin),
    ]
    total = sum(s for s, _ in sub)
    n_scored = sum(1 for s, _ in sub if s != 0 or _ is not None)  # metric was readable
    if n_scored == 0:
        return AgentSignal(
            ticker=snapshot.ticker, analyst_id="fundamentals", computed_at=now,
            data_unavailable=True,
            evidence=["all 5 fundamentals metrics missing"],
        )
    # Normalize to [-1, +1] using max-possible-score = 5 (sum of all-bullish per-metric +1's)
    normalized = total / 5.0
    verdict = _total_to_verdict(normalized)
    confidence = min(100, int(round(abs(normalized) * 100)))
    evidence = [s for _, s in sub if s is not None]
    return AgentSignal(
        ticker=snapshot.ticker, analyst_id="fundamentals", computed_at=now,
        verdict=verdict, confidence=confidence, evidence=evidence,
    )
```

Per-metric helper detail (P/E shown — others mirror it):

```python
def _score_pe(pe, target):
    if pe is None:
        return 0, None
    if target is not None:
        if pe < target * (1 - PER_CONFIG_BAND):
            return +1, f"P/E {pe:.1f} vs target {target:.0f} — undervalued by {(1 - pe/target)*100:.0f}%"
        if pe > target * (1 + PER_CONFIG_BAND):
            return -1, f"P/E {pe:.1f} vs target {target:.0f} — overvalued by {(pe/target - 1)*100:.0f}%"
        return 0, f"P/E {pe:.1f} near target {target:.0f}"
    # Fallback bands
    if pe < PE_BULLISH_BELOW:
        return +1, f"P/E {pe:.1f} (below {PE_BULLISH_BELOW:.0f} bullish band)"
    if pe > PE_BEARISH_ABOVE:
        return -1, f"P/E {pe:.1f} (above {PE_BEARISH_ABOVE:.0f} bearish band)"
    return 0, f"P/E {pe:.1f} (neutral band)"
```

ROE / D/E / profit_margin: no per-config target in TickerConfig (FundamentalTargets only carries pe_target / ps_target / pb_target — these three score against module constants only).
</implementation_sketch>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Test scaffolding — happy + fallback + per-metric isolation cases</name>
  <files>tests/analysts/test_fundamentals.py</files>
  <behavior>
    Tests written FIRST (RED) — no implementation yet. Each test name maps to a 03-VALIDATION.md requirement-test row.

    Tests (≥12):
    - test_per_config_pe_bullish_undervalued: cfg.target_multiples.pe_target=20; fund.pe=15. Score → bullish or strong_bullish (depends on other metrics; assert verdict ∈ {bullish, strong_bullish}); evidence contains "P/E 15.0 vs target 20" with "undervalued" substring.
    - test_per_config_pe_bearish_overvalued: cfg.target_multiples.pe_target=20; fund.pe=30. Verdict ∈ {bearish, strong_bearish}; evidence contains "overvalued".
    - test_per_config_pe_neutral_within_band: cfg.target_multiples.pe_target=20; fund.pe=22 (within ±20%). Score for P/E alone = 0; evidence contains "near target".
    - test_fallback_pe_bullish: cfg.target_multiples=None; fund.pe=12 (< 15). Evidence contains "below 15 bullish band".
    - test_fallback_pe_bearish: cfg.target_multiples=None; fund.pe=35 (> 30). Evidence contains "above 30 bearish band".
    - test_fallback_pe_neutral: cfg.target_multiples=None; fund.pe=22 (15..30). Evidence contains "neutral band".
    - test_per_metric_isolation_pe_missing: fund.pe=None, fund.ps=2.5, fund.roe=0.20, fund.debt_to_equity=0.3, fund.profit_margin=0.18 (4 bullish + 1 missing). Verdict bullish (or strong_bullish at total=4); evidence list omits any "P/E" string but includes the other 4.
    - test_per_metric_isolation_all_missing: fund.pe=None, fund.ps=None, fund.roe=None, fund.debt_to_equity=None, fund.profit_margin=None, fund.data_unavailable=False. Returns AgentSignal(data_unavailable=True, verdict='neutral', confidence=0, evidence=["all 5 fundamentals metrics missing"]).
    - test_empty_data_snapshot_data_unavailable_true: make_snapshot(data_unavailable=True). Returns data_unavailable=True signal with verdict='neutral', confidence=0.
    - test_empty_data_fundamentals_none: make_snapshot(fundamentals=None). Same data_unavailable signal.
    - test_empty_data_fundamentals_data_unavailable_true: make_snapshot(fundamentals=FundamentalsSnapshot(data_unavailable=True, ...)). Same data_unavailable signal.
    - test_5_state_ladder_strong_bullish: all 5 metrics maxed bullish (pe=10, ps=1.0, roe=0.30, de=0.1, pm=0.30). Verdict='strong_bullish'; total=5, normalized=1.0, confidence=100.
    - test_5_state_ladder_strong_bearish: all 5 metrics maxed bearish (pe=40, ps=10, roe=0.02, de=2.0, pm=0.02). Verdict='strong_bearish'; total=-5, confidence=100.
    - test_5_state_ladder_neutral: all 5 metrics in neutral band (pe=22, ps=5, roe=0.10, de=1.0, pm=0.10). Verdict='neutral'; total=0; confidence=0.
    - test_5_state_ladder_bullish_partial: 3 bullish, 2 neutral. Total=3, normalized=0.6 (boundary — verdict='bullish', NOT 'strong_bullish' since strong_bullish requires > 0.6 strict).
    - test_provenance_header_present: read analysts/fundamentals.py source; assert it contains "virattt/ai-hedge-fund/src/agents/fundamentals.py" reference (provenance comment per PROJECT.md INFRA-07).
    - test_computed_at_passes_through: pass explicit computed_at=frozen_now; assert returned signal.computed_at == frozen_now.
    - test_computed_at_default_uses_now: don't pass computed_at; verify the signal has a recent UTC datetime (within 1 second of `datetime.now(timezone.utc)`).
    - test_ticker_normalized_in_signal: snapshot.ticker="brk.b" via constructor → signal.ticker == "BRK-B" (delegates to AgentSignal's normalizer; this test verifies the analyst doesn't accidentally bypass it).

    Use `make_snapshot`, `make_ticker_config`, `frozen_now` fixtures from conftest. For FundamentalsSnapshot construction inside tests, import directly: `from analysts.data.fundamentals import FundamentalsSnapshot`.
  </behavior>
  <action>
    RED:
    1. Write `tests/analysts/test_fundamentals.py` with the 18 tests above. Imports: `from datetime import datetime, timezone`; `import pytest`; `from analysts.data.fundamentals import FundamentalsSnapshot`; `from analysts.schemas import FundamentalTargets, TickerConfig`; `from analysts.signals import AgentSignal`; `from analysts.fundamentals import score` (this import will fail in RED state — the module doesn't exist).
    2. Run `poetry run pytest tests/analysts/test_fundamentals.py -x -q` → ImportError on `analysts.fundamentals`.
    3. Commit: `test(03-02): add failing tests for fundamentals analyst (happy / fallback / per-metric / empty / 5-state ladder)`
  </action>
  <verify>
    <automated>poetry run pytest tests/analysts/test_fundamentals.py -x -q 2>&1 | grep -E "(error|ImportError|ModuleNotFoundError)" | head -3</automated>
  </verify>
  <done>tests/analysts/test_fundamentals.py committed with 18 RED tests; pytest fails as expected (ImportError); no implementation yet.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: analysts/fundamentals.py — score() implementation (GREEN)</name>
  <files>analysts/fundamentals.py</files>
  <behavior>
    Implement the score() function per the implementation_sketch in <context>. Pure function — no I/O, no module-level mutable state, no clock reads inside helpers (pass `now` explicitly to evidence-building if any are time-dependent — fundamentals don't have time-decay so this is moot but the discipline matters).

    Module structure:
    1. Provenance header docstring (10-15 lines) per PROJECT.md INFRA-07 — name virattt/ai-hedge-fund/src/agents/fundamentals.py and list modifications: "five-metric scoring (P/E, P/S, ROE, debt/equity, profit_margin) instead of 13-metric; per-`TickerConfig.target_multiples` overrides; module-level threshold constants instead of inline literals; 5-state Verdict (strong_bullish..strong_bearish) instead of 3-state; pure function (snapshot, config) -> AgentSignal signature replaces graph-node ainvoke."
    2. Imports: `from __future__ import annotations`; `from datetime import datetime, timezone`; `from typing import Optional`; `from analysts.data.snapshot import Snapshot`; `from analysts.schemas import TickerConfig`; `from analysts.signals import AgentSignal, Verdict`.
    3. Module-level constants per the sketch (PE_BULLISH_BELOW etc., 10 floats, PER_CONFIG_BAND).
    4. Five private per-metric helpers `_score_{pe,ps,roe,de,pm}` returning `tuple[int, Optional[str]]`. P/E and P/S take a `target` parameter (Optional); ROE / D/E / profit_margin do not (FundamentalTargets schema has no roe_target / de_target / pm_target).
    5. Private `_total_to_verdict(normalized: float) -> Verdict` helper per Pattern 3 in 03-RESEARCH.md.
    6. Public `score(snapshot: Snapshot, config: TickerConfig, *, computed_at: Optional[datetime] = None) -> AgentSignal` with the empty-data UNIFORM RULE guard at the top, then sub-scoring, normalization, evidence assembly, and AgentSignal construction.

    Defensive details:
    - Cap `confidence = min(100, int(round(abs(normalized) * 100)))` — never > 100.
    - When `n_scored == 0` (every metric None despite `data_unavailable=False` on the snapshot — defensive case for upstream bug), return data_unavailable=True with the explicit reason string.
    - Evidence list MUST NOT exceed 10 items (we only ever produce ≤5 strings, well under the cap).

    Determinism: no randomness, no time-dependent math (the fundamentals analyst has nothing time-relative). Two calls with identical (snapshot, config) → identical AgentSignal (modulo computed_at if not pinned).
  </behavior>
  <action>
    GREEN:
    1. Implement `analysts/fundamentals.py` per the structure above.
    2. Run `poetry run pytest tests/analysts/test_fundamentals.py -v` → all 18 tests green.
    3. Coverage: `poetry run pytest --cov=analysts.fundamentals --cov-branch tests/analysts/test_fundamentals.py` → ≥90% line / ≥85% branch. If coverage falls below, add tests for the uncovered branch (likely an unreachable defensive branch that should be either deleted or directly tested).
    4. Full repo regression: `poetry run pytest -x -q` → 177+ pre-existing + 16+ Plan 03-01 + 18 here = all green.
    5. Spot-check the provenance header by `grep -n "virattt/ai-hedge-fund/src/agents/fundamentals.py" analysts/fundamentals.py` — must return at least one match.
    6. Commit: `feat(03-02): fundamentals analyst — 5-metric per-config + fallback band scoring with 5-state verdict`
  </action>
  <verify>
    <automated>poetry run pytest tests/analysts/test_fundamentals.py -v && poetry run pytest --cov=analysts.fundamentals --cov-branch tests/analysts/test_fundamentals.py && poetry run pytest -x -q && grep -q "virattt/ai-hedge-fund/src/agents/fundamentals.py" analysts/fundamentals.py</automated>
  </verify>
  <done>analysts/fundamentals.py shipped with score() function; all 18 tests green; coverage ≥90/85; full repo regression green; provenance header present.</done>
</task>

</tasks>

<verification>
- 2 tasks, 2 commits (RED then GREEN). TDD discipline preserved.
- Coverage gate: ≥90% line / ≥85% branch on `analysts/fundamentals.py`.
- Full repo regression: 177+ pre-existing + 16+ Plan 03-01 schema tests + 18 Plan 03-02 fundamentals tests → all green.
- ANLY-01 requirement satisfied: 5-state ladder verdict + confidence + evidence list, per-config + fallback paths, per-metric isolation, empty-data uniform rule, provenance comment.
- Provenance header in analysts/fundamentals.py names virattt/ai-hedge-fund/src/agents/fundamentals.py per INFRA-07.
- Pure function: no I/O, no module-level mutable state, no module-level clock reads.

## Cross-Scope Risks

_vault_status=budget_exhausted; re-run /gmd:plan-phase --replan after vault-maintain_
</verification>

<success_criteria>
1. `analysts/fundamentals.py:score(snapshot, config, *, computed_at=None) -> AgentSignal` is a pure function ~120 LOC.
2. Module-level threshold constants (PE_BULLISH_BELOW=15.0, PE_BEARISH_ABOVE=30.0, …) at top of file — tunable by editing.
3. Per-config (TickerConfig.target_multiples.pe_target / ps_target) and fallback paths both work; per-config takes precedence when set.
4. Per-metric isolation verified: missing one metric does not zero-out the other four.
5. Empty-data uniform rule: snapshot.data_unavailable=True or fundamentals=None or fundamentals.data_unavailable=True → AgentSignal(data_unavailable=True, verdict='neutral', confidence=0, evidence=[reason]).
6. 5-state ladder verdict mapping verified at strong_bullish / bullish / neutral / bearish / strong_bearish edges.
7. Provenance header names virattt source file per INFRA-07.
8. ≥18 tests in tests/analysts/test_fundamentals.py, all green; coverage ≥90% line / ≥85% branch on analysts/fundamentals.py.
9. ANLY-01 requirement closed; Phase 3 invariant test (test_invariants.py::test_always_four_signals) advances by one analyst module landing.
</success_criteria>

<output>
After completion, create `.planning/phases/03-analytical-agents-deterministic-scoring/03-02-SUMMARY.md` summarizing the 2 commits, the score() function signature, and the threshold constant values shipped. Reference 03-01 (AgentSignal contract this analyst implements) and forward-flag that 03-05 (valuation) and the test_invariants.py xfail-clear at end of Wave 2 still depend on the other three Wave 2 analysts landing.
</output>
