---
phase: 03-analytical-agents-deterministic-scoring
plan: 05
type: tdd
wave: 2
depends_on: [03-01, 02-07]
files_modified:
  - analysts/valuation.py
  - tests/analysts/test_valuation.py
  - tests/analysts/test_invariants.py
autonomous: true
requirements: [ANLY-04]
provides:
  - "analysts.valuation.score(snapshot, config, *, computed_at=None) -> AgentSignal"
  - "Three-tier blend with explicit precedence: thesis_price (weight 1.0) → target_multiples (weight 0.7) → yfinance analyst consensus (weight 0.5)"
  - "When NONE of the three tiers is configured/available → AgentSignal(data_unavailable=True, verdict='neutral', confidence=0, evidence=['no thesis_price, no target_multiples, no consensus'])"
  - "Each available tier contributes one or more evidence strings; verdict = sign of weighted aggregate; confidence reflects both magnitude AND data density (more tiers available → higher confidence)"
  - "Closes Phase 2 amendment cycle: depends on 02-07 having shipped FundamentalsSnapshot.{analyst_target_mean, analyst_target_median, analyst_recommendation_mean, analyst_opinion_count} fields"
  - "Wave 2 closeout: removes @pytest.mark.xfail markers from tests/analysts/test_invariants.py (now that all four analyst modules exist, the cross-cutting invariant tests should flip green naturally)"
tags: [phase-3, analyst, valuation, tdd, pure-function, anly-04, wave-2-closeout, cross-phase-dep]

must_haves:
  truths:
    - "score(snapshot, config) returns AgentSignal with analyst_id='valuation' for every input — never None, never raises"
    - "Thesis-price-only path: config.thesis_price=200, snapshot.prices.current_price=170 → verdict ∈ {bullish, strong_bullish}; evidence contains 'thesis_price 200, current 170 — 15.0% gap'"
    - "Target-multiples-only path: config.target_multiples.pe_target=20, snapshot.fundamentals.pe=15 (no thesis_price, no consensus) → verdict ∈ {bullish, strong_bullish}; evidence references the P/E gap"
    - "Consensus-only path: config has no thesis_price, no target_multiples; snapshot.fundamentals.analyst_target_mean=120, current=100 → verdict bullish; evidence references analyst consensus and opinion count"
    - "All-three blend: thesis bullish + targets neutral + consensus bullish → verdict bullish; confidence higher than any single-tier-only path (density bonus)"
    - "Precedence weights: thesis=1.0, targets=0.7, consensus=0.5 (matches 03-CONTEXT.md scoring philosophy)"
    - "None-set → data_unavailable=True with evidence=['no thesis_price, no target_multiples, no consensus'] (UNIFORM RULE per 03-CONTEXT.md)"
    - "Empty-data UNIFORM RULE: snapshot.data_unavailable=True OR snapshot.prices is None OR snapshot.prices.current_price is None → AgentSignal(data_unavailable=True, evidence=['no current price'])"
    - "02-07 cross-phase dependency: snapshot.fundamentals.analyst_target_mean is read directly (not via getattr-defensive); fails loudly at AttributeError if 02-07 has NOT shipped — execute-phase MUST surface this in pre-flight"
    - "test_invariants.py xfail markers REMOVED in this plan's final task; both `test_always_four_signals` and `test_dark_snapshot_emits_four_unavailable` flip green naturally at the close of Wave 2"
    - "Provenance header names virattt/ai-hedge-fund/src/agents/valuation.py and lists modifications (multi-method weighted aggregation pattern adopted; methods diverge — virattt uses DCF + Owner Earnings + EV/EBITDA + Residual Income from financials, we use thesis_price + target_multiples + yfinance consensus per 03-CONTEXT.md scoring philosophy)"
    - "Coverage ≥90% line / ≥85% branch on analysts/valuation.py"
  artifacts:
    - path: "analysts/valuation.py"
      provides: "score() + per-tier helpers + density-weighted confidence + 5-state verdict; ~120 LOC"
      min_lines: 100
    - path: "tests/analysts/test_valuation.py"
      provides: "≥12 tests covering each tier alone + all-three blend + none-set + invariants + 02-07-dependency assertion"
      min_lines: 110
    - path: "tests/analysts/test_invariants.py"
      provides: "xfail markers removed; the 2 cross-cutting invariant tests flip green naturally"
      min_lines: 30
  key_links:
    - from: "analysts/valuation.py"
      to: "snapshot.prices.current_price"
      via: "primary anchor — every tier compares against this; data_unavailable=True when missing"
      pattern: "snapshot\\.prices\\.current_price"
    - from: "analysts/valuation.py"
      to: "config.thesis_price (Tier 1, weight 1.0)"
      via: "Optional[float] read; when set, contributes scaled gap evidence + sub-signal"
      pattern: "config\\.thesis_price"
    - from: "analysts/valuation.py"
      to: "config.target_multiples.{pe_target, ps_target, pb_target} (Tier 2, weight 0.7)"
      via: "iterate over the 3 multiples; for each set+matching-snapshot-fundamental, emit a sub-signal"
      pattern: "config\\.target_multiples"
    - from: "analysts/valuation.py"
      to: "snapshot.fundamentals.analyst_target_mean (Tier 3, weight 0.5) — REQUIRES 02-07"
      via: "direct attribute read; AttributeError if 02-07 not shipped"
      pattern: "snapshot\\.fundamentals\\.analyst_target_mean"
    - from: "analysts/valuation.py"
      to: "analysts.signals.AgentSignal"
      via: "constructor — only public output type"
      pattern: "from analysts.signals import AgentSignal"
---

<objective>
Wave 2 / ANLY-04: Valuation analyst — pure-function deterministic scoring of current price against three valuation anchors with explicit precedence: (1) `config.thesis_price` (weight 1.0) — user's locked thesis; (2) `config.target_multiples` (weight 0.7) — user's per-ticker P/E / P/S / P/B targets vs snapshot.fundamentals; (3) yfinance analyst consensus from `snapshot.fundamentals.analyst_target_mean` (weight 0.5) — sell-side mean target. Aggregates available tiers into one AgentSignal with 5-state verdict + density-weighted confidence (more tiers available → higher confidence). Adapted from virattt/ai-hedge-fund/src/agents/valuation.py multi-method weighted aggregation pattern, but the three methods themselves are different (virattt uses DCF / Owner Earnings / EV/EBITDA / Residual Income; we use thesis_price / target_multiples / analyst consensus per 03-CONTEXT.md scoring philosophy).

**CROSS-PHASE DEPENDENCY — 02-07 IS A HARD PREREQUISITE.** This plan reads `snapshot.fundamentals.analyst_target_mean`, `analyst_target_median`, `analyst_recommendation_mean`, `analyst_opinion_count` — four fields added to FundamentalsSnapshot by Plan 02-07 (`02-07-fundamentals-analyst-fields-PLAN.md`, already committed at HEAD per orchestrator decisions). Without 02-07 shipped, this plan fails at first import: `AttributeError: 'FundamentalsSnapshot' object has no attribute 'analyst_target_mean'`. The depends_on frontmatter list captures this. **execute-phase pre-flight MUST verify 02-07's commits are at HEAD before launching this plan's executor**; if not, abort with a clear "02-07 not yet shipped — plan-phase 03-05 cannot proceed" message rather than letting the executor hit AttributeError mid-task. This advisory is for the orchestrator, not the implementing agent.

**Wave 2 closeout responsibility:** This plan is the LAST of Wave 2 (per the dependency graph: 03-02 / 03-03 / 03-04 / 03-05 are all leaves of 03-01, but 03-05 also depends on 02-07 cross-phase, and is the natural place to close out the Wave-2 invariant scaffold). Its final task removes the `@pytest.mark.xfail(strict=True, reason=...)` markers from `tests/analysts/test_invariants.py` — at that point all four analyst modules exist, so the cross-cutting tests (`test_always_four_signals`, `test_dark_snapshot_emits_four_unavailable`) should flip green naturally. If they don't, that's a real bug in one of 03-02 / 03-03 / 03-04 / 03-05 to chase — NOT a reason to keep the markers.

Output: analysts/valuation.py (~130 LOC: provenance docstring + per-tier helpers + score() function); tests/analysts/test_valuation.py (~140 LOC: 12+ tests covering each tier alone + blends + none-set + density confidence); modified tests/analysts/test_invariants.py with xfail markers removed (2 tests flip green).
</objective>

<execution_context>
@/home/codespace/.claude/workflows/execute-plan.md
@/home/codespace/.claude/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/03-analytical-agents-deterministic-scoring/03-CONTEXT.md
@.planning/phases/03-analytical-agents-deterministic-scoring/03-RESEARCH.md
@.planning/phases/03-analytical-agents-deterministic-scoring/03-01-SUMMARY.md
@.planning/phases/02-ingestion-keyless-data-plane/02-07-fundamentals-analyst-fields-PLAN.md

# Existing patterns
@analysts/signals.py
@analysts/schemas.py
@analysts/data/snapshot.py
@analysts/data/prices.py
@analysts/data/fundamentals.py
@tests/analysts/conftest.py
@tests/analysts/test_invariants.py

<interfaces>
<!-- 03-01 outputs we consume: -->

```python
# AgentSignal contract — see 03-01-SUMMARY.md
```

<!-- 02-07 outputs we consume (PHASE 2 AMENDMENT — cross-phase prerequisite): -->

```python
# analysts/data/fundamentals.py — POST-02-07 shape:
class FundamentalsSnapshot(BaseModel):
    # ... existing fields (pe, ps, pb, roe, debt_to_equity, profit_margin, free_cash_flow, market_cap) ...
    # NEW (02-07):
    analyst_target_mean: Optional[float] = None         # mean sell-side price target
    analyst_target_median: Optional[float] = None       # median (robust to outliers)
    analyst_recommendation_mean: Optional[float] = None # 1.0=strong_buy ... 5.0=strong_sell
    analyst_opinion_count: Optional[int] = None         # n analysts contributing
```

<!-- TickerConfig (analysts/schemas.py): -->

```python
class TickerConfig(BaseModel):
    thesis_price: Optional[float] = None         # Tier 1 anchor (user's locked thesis)
    target_multiples: Optional[FundamentalTargets] = None  # Tier 2 anchor (user's per-ticker P/E/P/S/P/B targets)
    # ...

class FundamentalTargets(BaseModel):
    pe_target: Optional[float] = None
    ps_target: Optional[float] = None
    pb_target: Optional[float] = None
```

<!-- NEW contract this plan creates: -->

```python
# analysts/valuation.py
def score(
    snapshot: Snapshot,
    config: TickerConfig,
    *,
    computed_at: Optional[datetime] = None,
) -> AgentSignal:
    """Score valuation deterministically. Three-tier blend: thesis_price (weight 1.0) > target_multiples (0.7) > yfinance consensus (0.5). Pure function; never raises for missing data; data_unavailable=True only when ALL three tiers absent OR current price unavailable."""
```
</interfaces>

<implementation_sketch>
<!-- Module structure (per 03-RESEARCH.md Pattern 3 + Code Examples Valuation excerpt): -->

```python
from datetime import datetime, timezone
from typing import Optional

from analysts.data.snapshot import Snapshot
from analysts.schemas import TickerConfig
from analysts.signals import AgentSignal, Verdict

# Tier weights — see 03-CONTEXT.md scoring philosophy.
W_THESIS = 1.0
W_TARGETS = 0.7
W_CONSENSUS = 0.5

# A "100% gap" (current at 50% premium / 50% discount) saturates a single sub-signal at ±1.
# 50% premium → s = -1; 50% discount → s = +1. Linear in between.
GAP_SATURATION = 0.5  # half a stock = full saturation


def _signed_gap(anchor: float, current: float) -> float:
    """Signed gap in [-1, +1]: positive = current below anchor (bullish), negative = current above anchor.
    `anchor=200, current=170` → delta = -0.15 (15% below) → signal = +0.30 (clipped to ±1).
    """
    delta = (current - anchor) / anchor   # negative when undervalued
    s = -delta / GAP_SATURATION
    return max(-1.0, min(1.0, s))


def _total_to_verdict(normalized: float) -> Verdict:
    if normalized > 0.6: return "strong_bullish"
    if normalized > 0.2: return "bullish"
    if normalized < -0.6: return "strong_bearish"
    if normalized < -0.2: return "bearish"
    return "neutral"


def score(snapshot, config, *, computed_at=None):
    now = computed_at or datetime.now(timezone.utc)
    # Empty-data UNIFORM RULE — current price is the universal anchor; no current price → can't compare.
    if (snapshot.data_unavailable
        or snapshot.prices is None
        or snapshot.prices.data_unavailable
        or snapshot.prices.current_price is None
        or snapshot.prices.current_price <= 0):
        return AgentSignal(
            ticker=snapshot.ticker, analyst_id="valuation", computed_at=now,
            data_unavailable=True, evidence=["no current price"],
        )
    current = snapshot.prices.current_price
    fund = snapshot.fundamentals  # may be None or data_unavailable=True

    # Each sub-signal: (signal in [-1, +1], weight, evidence_str). Collected then aggregated.
    sub: list[tuple[float, float, str]] = []

    # Tier 1 — thesis_price
    if config.thesis_price is not None and config.thesis_price > 0:
        s = _signed_gap(config.thesis_price, current)
        gap_pct = (current - config.thesis_price) / config.thesis_price * 100
        sub.append((s, W_THESIS,
                    f"thesis_price {config.thesis_price:.0f}, current {current:.0f} — {gap_pct:+.1f}% gap"))

    # Tier 2 — target_multiples vs snapshot.fundamentals
    targets = config.target_multiples
    if targets is not None and fund is not None and not fund.data_unavailable:
        if targets.pe_target is not None and fund.pe is not None and targets.pe_target > 0:
            s = _signed_gap(targets.pe_target, fund.pe)
            sub.append((s, W_TARGETS, f"P/E {fund.pe:.1f} vs target {targets.pe_target:.0f}"))
        if targets.ps_target is not None and fund.ps is not None and targets.ps_target > 0:
            s = _signed_gap(targets.ps_target, fund.ps)
            sub.append((s, W_TARGETS, f"P/S {fund.ps:.1f} vs target {targets.ps_target:.0f}"))
        # P/B: schema FundamentalTargets has pb_target but FundamentalsSnapshot has pb (Optional[float])
        if targets.pb_target is not None and fund.pb is not None and targets.pb_target > 0:
            s = _signed_gap(targets.pb_target, fund.pb)
            sub.append((s, W_TARGETS, f"P/B {fund.pb:.1f} vs target {targets.pb_target:.0f}"))

    # Tier 3 — yfinance analyst consensus (REQUIRES 02-07; AttributeError otherwise)
    if fund is not None and not fund.data_unavailable and fund.analyst_target_mean is not None and fund.analyst_target_mean > 0:
        s = _signed_gap(fund.analyst_target_mean, current)
        gap_pct = (current - fund.analyst_target_mean) / fund.analyst_target_mean * 100
        n = fund.analyst_opinion_count
        n_str = f"n={n}" if n else "n=?"
        sub.append((s, W_CONSENSUS,
                    f"analyst consensus {fund.analyst_target_mean:.0f} ({n_str}), current {current:.0f} — {gap_pct:+.1f}% gap"))

    if not sub:
        return AgentSignal(
            ticker=snapshot.ticker, analyst_id="valuation", computed_at=now,
            data_unavailable=True,
            evidence=["no thesis_price, no target_multiples, no consensus"],
        )

    total_w = sum(w for _, w, _ in sub)
    aggregate = sum(s * w for s, w, _ in sub) / total_w
    verdict = _total_to_verdict(aggregate)
    # Density bonus: more tiers available → higher confidence.
    # max possible total_w = 1.0 + 0.7 * 3 (3 multiples) + 0.5 = 3.6; floor at the lowest single-tier (0.5) → 1.
    # Use total_w / 2.2 as density factor (saturates near 1.0 when 2+ tiers active with multiple multiples).
    density = min(1.0, total_w / 2.2)
    confidence = min(100, int(round(abs(aggregate) * 100 * density)))
    evidence = [e for _, _, e in sub][:10]
    return AgentSignal(
        ticker=snapshot.ticker, analyst_id="valuation", computed_at=now,
        verdict=verdict, confidence=confidence, evidence=evidence,
    )
```

<!-- Note for executor: `_signed_gap` saturates at GAP_SATURATION=0.5 → 50% premium clips to s=-1. Tunable; tests pin the formula. The density factor in confidence rewards multiple anchors agreeing. -->
</implementation_sketch>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Test scaffolding — each tier alone + blend + none-set + density (RED)</name>
  <files>tests/analysts/test_valuation.py</files>
  <behavior>
    Tests written first. Each tier is exercised in isolation (rest absent), then in combination, then with no tiers (data_unavailable). Density bonus is checked by comparing single-tier-bullish vs all-three-bullish confidence.

    Tests (≥14):

    THESIS-PRICE-ONLY:
    - test_thesis_only_undervalued: cfg.thesis_price=200; current=170; no target_multiples; fund.analyst_target_mean=None. Score → verdict ∈ {bullish, strong_bullish}; evidence contains "thesis_price 200, current 170" and gap pct.
    - test_thesis_only_overvalued: cfg.thesis_price=200; current=240. Verdict ∈ {bearish, strong_bearish}; evidence contains "+20.0% gap" or similar (positive percentage = overvalued).
    - test_thesis_only_at_target: cfg.thesis_price=200; current=200. Verdict='neutral' (gap=0); evidence shows "0.0% gap".
    - test_thesis_only_strong_undervalued: cfg.thesis_price=200; current=100 (50% below). _signed_gap saturates at +1.0; verdict='strong_bullish'; confidence reflects density=1.0/2.2 ≈ 0.45 → ~45 (not 100, because only one tier).

    TARGETS-ONLY:
    - test_targets_only_pe_bullish: cfg.target_multiples.pe_target=20; fund.pe=15; no thesis_price; fund.analyst_target_mean=None. Verdict ∈ {bullish, strong_bullish}; evidence contains "P/E 15.0 vs target 20".
    - test_targets_only_ps_bearish: cfg.target_multiples.ps_target=3; fund.ps=6; rest absent. Verdict ∈ {bearish, strong_bearish}; evidence contains "P/S 6.0 vs target 3".
    - test_targets_pe_and_ps_blend: cfg has pe_target=20 + ps_target=3; fund.pe=15 (bullish) + fund.ps=2 (bullish). Both contribute. Confidence higher than test_targets_only_pe_bullish (more tiers).

    CONSENSUS-ONLY (REQUIRES 02-07):
    - test_consensus_only_bullish: cfg has no thesis_price, no target_multiples; fund.analyst_target_mean=120, fund.analyst_opinion_count=42; current=100. Verdict ∈ {bullish, strong_bullish}; evidence contains "analyst consensus 120 (n=42), current 100".
    - test_consensus_only_bearish: fund.analyst_target_mean=80, current=100. Verdict ∈ {bearish, strong_bearish}.
    - test_consensus_opinion_count_none: fund.analyst_target_mean=120, fund.analyst_opinion_count=None. Evidence shows "n=?" (defensive).

    ALL-THREE BLEND:
    - test_all_three_bullish: cfg.thesis_price=200 (current=170 = bullish); cfg.target_multiples.pe_target=20 + fund.pe=15 (bullish); fund.analyst_target_mean=190 (bullish). All three agree. Verdict bullish or strong_bullish; confidence higher than any single-tier-only path (density bonus active).
    - test_all_three_mixed: thesis bullish + targets neutral + consensus bullish. Verdict bullish (positive aggregate); confidence reflects density.

    NONE-SET (UNIFORM RULE):
    - test_none_configured_data_unavailable: cfg.thesis_price=None; cfg.target_multiples=None; fund.analyst_target_mean=None; current=170. Score → AgentSignal(data_unavailable=True, evidence=["no thesis_price, no target_multiples, no consensus"]).

    EMPTY-DATA UNIFORM RULE (current price gate):
    - test_no_current_price: snapshot.prices=None. Score → data_unavailable=True; evidence=["no current price"].
    - test_current_price_zero_or_negative: snapshot.prices.current_price=0 (Pydantic should reject this at schema layer via gt=0; defensive test bypasses schema validation OR uses None — recommend testing via prices.current_price=None which is the schema-allowed empty case).
    - test_snapshot_data_unavailable_true: make_snapshot(data_unavailable=True). Score → data_unavailable=True signal.

    02-07 CROSS-PHASE-DEPENDENCY ASSERTION:
    - test_02_07_dependency_present: import `from analysts.data.fundamentals import FundamentalsSnapshot`; assert hasattr(FundamentalsSnapshot, 'model_fields') and 'analyst_target_mean' in FundamentalsSnapshot.model_fields. Documents the cross-phase contract; if 02-07 ever gets reverted this test flags it loudly.

    DETERMINISM + PROVENANCE:
    - test_deterministic: call score() twice with same inputs; model_dump_json identical.
    - test_computed_at_passes_through: pass explicit computed_at=frozen_now; signal.computed_at == frozen_now.
    - test_provenance_header_present: read analysts/valuation.py; assert "virattt/ai-hedge-fund/src/agents/valuation.py" + the divergence note.

    DENSITY-CONFIDENCE INVARIANT:
    - test_density_bonus_more_tiers_more_confidence: build two snapshots with the SAME signed gap on each tier (e.g., all bullish with similar magnitude). Snapshot A has only thesis_price set; Snapshot B has all three. Assert: B.confidence > A.confidence (density factor active).

    Use `make_snapshot`, `make_ticker_config`, `frozen_now`. Build PriceSnapshot + FundamentalsSnapshot inline.
  </behavior>
  <action>
    RED:
    1. Write `tests/analysts/test_valuation.py` with the ≥18 tests above. Imports: `import pytest`; `from datetime import datetime, timezone`; `from analysts.data.fundamentals import FundamentalsSnapshot`; `from analysts.data.prices import PriceSnapshot`; `from analysts.schemas import FundamentalTargets, TickerConfig`; `from analysts.signals import AgentSignal`; `from analysts.valuation import score`. Build a helper `_fund(**kwargs)` that constructs a minimal FundamentalsSnapshot with `ticker, fetched_at, source="yfinance"` defaults plus the test's specific fields.
    2. Run `poetry run pytest tests/analysts/test_valuation.py -x -q` → ImportError on `analysts.valuation`.
    3. Pre-flight check (orchestrator concern, but worth verifying here): `poetry run python -c "from analysts.data.fundamentals import FundamentalsSnapshot; assert 'analyst_target_mean' in FundamentalsSnapshot.model_fields, '02-07 not shipped — abort 03-05'"` — if this fails, STOP and surface the cross-phase dependency to the user.
    4. Commit: `test(03-05): add failing tests for valuation analyst (3-tier blend + density confidence + 02-07 dep)`
  </action>
  <verify>
    <automated>poetry run python -c "from analysts.data.fundamentals import FundamentalsSnapshot; assert 'analyst_target_mean' in FundamentalsSnapshot.model_fields, '02-07 not shipped'" && poetry run pytest tests/analysts/test_valuation.py -x -q 2>&1 | grep -E "(error|ImportError|ModuleNotFoundError)" | head -3</automated>
  </verify>
  <done>tests/analysts/test_valuation.py committed with ≥18 RED tests; pytest fails as expected (ImportError on analysts.valuation); 02-07 cross-phase dep verified at HEAD via the FundamentalsSnapshot.model_fields assertion.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: analysts/valuation.py — score() implementation (GREEN)</name>
  <files>analysts/valuation.py</files>
  <behavior>
    Implement per implementation_sketch in <context>. Three tiers iterated in fixed precedence order; each yields zero or more sub-signals; aggregate; 5-state verdict; density-weighted confidence.

    Module structure:
    1. Provenance docstring (15-20 lines) per PROJECT.md INFRA-07. Name virattt/ai-hedge-fund/src/agents/valuation.py and explicit divergence: "virattt's multi-method weighted aggregation pattern adopted (when method's value ≤ 0 → exclude from weights; recompute total_weight from remaining methods); methods diverge — virattt uses DCF + Owner Earnings + EV/EBITDA + Residual Income (all derived from financials), we use thesis_price (user's locked thesis) + target_multiples (user's per-ticker P/E/P/S/P/B targets vs snapshot.fundamentals) + yfinance analyst consensus from FundamentalsSnapshot.analyst_target_mean (added in Plan 02-07). Pure function (snapshot, config) -> AgentSignal signature replaces graph-node ainvoke."
    2. Imports per the sketch.
    3. Module constants: W_THESIS=1.0, W_TARGETS=0.7, W_CONSENSUS=0.5, GAP_SATURATION=0.5.
    4. Private helpers: `_signed_gap(anchor, current)`, `_total_to_verdict(normalized)`.
    5. Public `score(snapshot, config, *, computed_at=None) -> AgentSignal` with the empty-data UNIFORM RULE guards (snapshot.data_unavailable, prices=None, prices.data_unavailable, current_price None or ≤0), then per-tier sub-signal collection, then aggregation, then verdict + confidence + evidence assembly.

    Tier-iteration discipline:
    - Tier 1 (thesis_price): single sub-signal when set. weight = 1.0.
    - Tier 2 (target_multiples): up to 3 sub-signals (pe / ps / pb), one per multiple set AND with matching snapshot.fundamentals field present. weight = 0.7 each.
    - Tier 3 (consensus): single sub-signal when fund.analyst_target_mean set AND > 0. weight = 0.5.

    Per-tier guards:
    - All three tiers gate on appropriate Optional[float] presence + > 0 (no division by zero).
    - Tier 2 + Tier 3 gate on `fund is not None and not fund.data_unavailable` first, then on the specific field.

    Density-weighted confidence:
    - `total_w = sum of active weights`. With all three tiers maxed (thesis + 3 multiples + consensus), max = 1.0 + 0.7*3 + 0.5 = 3.6.
    - `density = min(1.0, total_w / 2.2)` — saturates at 1.0 when 2+ tiers active with multiple multiples; ~0.45 when only thesis_price set; ~0.32 when only target_multiples.pe_target set.
    - `confidence = min(100, int(round(abs(aggregate) * 100 * density)))`.

    Test `test_density_bonus_more_tiers_more_confidence` verifies the density math is monotonic in number of active tiers.
  </behavior>
  <action>
    GREEN:
    1. Implement `analysts/valuation.py` per the sketch.
    2. Run `poetry run pytest tests/analysts/test_valuation.py -v` → all ≥18 tests green.
    3. Coverage: `poetry run pytest --cov=analysts.valuation --cov-branch tests/analysts/test_valuation.py` → ≥90% line / ≥85% branch.
    4. Full repo regression: `poetry run pytest -x -q` → all green (177+ pre-existing + 03-01..03-04 + 18+ here).
    5. Verify provenance + 02-07 dependency:
       - `grep -q "virattt/ai-hedge-fund/src/agents/valuation.py" analysts/valuation.py`
       - `grep -q "analyst_target_mean" analysts/valuation.py` (Tier 3 reads the 02-07 field)
       - `grep -q "02-07" analysts/valuation.py` (provenance comment notes the cross-phase dependency)
    6. Commit: `feat(03-05): valuation analyst — thesis/targets/consensus 3-tier blend with density-weighted confidence`
  </action>
  <verify>
    <automated>poetry run pytest tests/analysts/test_valuation.py -v && poetry run pytest --cov=analysts.valuation --cov-branch tests/analysts/test_valuation.py && poetry run pytest -x -q && grep -q "virattt/ai-hedge-fund/src/agents/valuation.py" analysts/valuation.py && grep -q "analyst_target_mean" analysts/valuation.py</automated>
  </verify>
  <done>analysts/valuation.py shipped with score() + 3-tier blend; all ≥18 tests green; coverage ≥90/85; full repo regression green; provenance + 02-07-dep notes present.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Wave 2 closeout — remove xfail markers from test_invariants.py</name>
  <files>tests/analysts/test_invariants.py</files>
  <behavior>
    All four analyst modules now exist (`fundamentals`, `technicals`, `news_sentiment`, `valuation`). The 2 cross-cutting invariant tests in `tests/analysts/test_invariants.py` should flip green naturally — remove the `@pytest.mark.xfail(strict=True, ...)` decorators and run pytest to confirm they pass.

    If they DON'T pass after marker removal, that's a bug in one of 03-02 / 03-03 / 03-04 / 03-05 — chase it to root cause. Common candidates: an analyst module's `analyst_id` field doesn't match the Literal in AgentSignal (typo); an analyst's `score()` raises instead of returning data_unavailable=True for a particular empty-data path; the dark-snapshot test's expected fields not all set to data_unavailable.

    No new tests written here — this task is purely a marker-removal + green-confirmation.
  </behavior>
  <action>
    1. Edit `tests/analysts/test_invariants.py`:
       - Remove the `@pytest.mark.xfail(strict=True, reason="Wave 2 plans 03-02..03-05 ship the four analyst modules; flips green when last lands")` decorators from both `test_always_four_signals` and `test_dark_snapshot_emits_four_unavailable`.
       - Remove the file-header comment block that explains the xfail intent (since the markers are gone, the intent is moot — replace with a one-line comment naming the cross-cutting invariants).
    2. Run `poetry run pytest tests/analysts/test_invariants.py -v` → both tests should pass NATURALLY (not xfail, not skip — actual green).
    3. If a test fails:
       - For `test_always_four_signals`: verify each analyst module's score() returns an AgentSignal with the expected analyst_id Literal. If one is misspelled (e.g., "newssentiment" instead of "news_sentiment"), fix it in the offending analyst module — this is a real cross-module bug surfaced by the integration test. Update that module's tests too, then re-run.
       - For `test_dark_snapshot_emits_four_unavailable`: verify each analyst module's empty-data UNIFORM RULE branch handles `snapshot.data_unavailable=True` AND `snapshot.prices=None` / `snapshot.fundamentals=None` / `snapshot.news=[]` cleanly. If one analyst returns `verdict='bullish'` because it has a non-empty config + the upstream check missed a branch, fix the analyst. The invariant test is correct; the analyst is buggy.
    4. Run full repo regression: `poetry run pytest -x -q` → 177+ pre-existing + 16+ schema (03-01) + 18 fundamentals + 18+ technicals + 18+ news_sentiment + 18+ valuation + 2 invariants → all green.
    5. Commit: `test(03-05): close Wave 2 — remove xfail markers from test_invariants.py (all 4 analyst modules shipped)`
  </action>
  <verify>
    <automated>poetry run pytest tests/analysts/test_invariants.py -v 2>&1 | grep -E "(PASSED|2 passed)" && ! grep -E "@pytest\\.mark\\.xfail" tests/analysts/test_invariants.py && poetry run pytest -x -q</automated>
  </verify>
  <done>Wave 2 closeout: tests/analysts/test_invariants.py xfail markers removed; both `test_always_four_signals` and `test_dark_snapshot_emits_four_unavailable` flip green naturally; full repo regression green; commit landed.</done>
</task>

</tasks>

<verification>
- 3 tasks, 3 commits (RED test scaffold, GREEN implementation, Wave 2 closeout marker removal). TDD discipline preserved on the analyst implementation; closeout is a docs-style task.
- Coverage gate: ≥90% line / ≥85% branch on `analysts/valuation.py`.
- Full repo regression at end of plan: 177+ pre-existing + 16+ schema (03-01) + 18 fundamentals (03-02) + 18+ technicals (03-03) + 18+ news_sentiment (03-04) + 18+ valuation (03-05) + 2 cross-cutting invariants → all green.
- ANLY-04 requirement satisfied: 3-tier blend (thesis_price > target_multiples > yfinance consensus) + 5-state ladder + density-weighted confidence + UNIFORM RULE empty-data + cross-phase dependency on 02-07.
- Provenance header in analysts/valuation.py names virattt source file AND documents the methods divergence (DCF/Owner Earnings/EV/EBITDA/Residual Income → thesis/targets/consensus) per INFRA-07.
- 02-07 cross-phase dependency captured in `depends_on: [03-01, 02-07]` frontmatter; pre-flight assertion in Task 1 verifies FundamentalsSnapshot.analyst_target_mean field exists at HEAD before launching the test scaffold.
- Wave 2 closeout: test_invariants.py xfail markers removed; the 2 cross-cutting invariant tests flip green naturally — the "always 4 signals" + "dark snapshot ⇒ 4 data_unavailable=True" contracts from 03-CONTEXT.md are now enforced by integration tests.

## Cross-Scope Risks

_vault_status=budget_exhausted; re-run /gmd:plan-phase --replan after vault-maintain_

_If 02-07 is NOT at HEAD when this plan executes_, Task 1's pre-flight assertion fails loudly. Cross-phase dependency. Surface to user as: "Plan 02-07 (Phase 2 amendment) must ship before Plan 03-05 (valuation analyst) can proceed. Run `/gmd:execute-phase 02 --plan 02-07` first."
</verification>

<success_criteria>
1. `analysts/valuation.py:score(snapshot, config, *, computed_at=None) -> AgentSignal` is a pure function ~130 LOC.
2. Three-tier blend: Tier 1 thesis_price (weight 1.0), Tier 2 target_multiples.{pe/ps/pb}_target (weight 0.7 each), Tier 3 fund.analyst_target_mean (weight 0.5).
3. Each tier scored via `_signed_gap` linearization, saturated at GAP_SATURATION=0.5 → ±1.
4. Density-weighted confidence: more active tiers → higher confidence (density factor saturates at 1.0 when 2+ tiers active with multiple multiples).
5. Empty-data UNIFORM RULE: no current price OR none of the 3 tiers configured/available → AgentSignal(data_unavailable=True, evidence=[reason]).
6. Cross-phase 02-07 dependency: `snapshot.fundamentals.analyst_target_mean` read directly (no getattr-defensive); pre-flight assertion verifies the field exists.
7. Provenance header names virattt/ai-hedge-fund/src/agents/valuation.py with explicit methods-divergence note per INFRA-07.
8. ≥18 tests in tests/analysts/test_valuation.py, all green; coverage ≥90% line / ≥85% branch.
9. Wave 2 closeout: tests/analysts/test_invariants.py xfail markers removed; both cross-cutting tests flip green naturally.
10. ANLY-04 requirement closed; fourth-of-four Wave 2 analyst modules shipped; Phase 3 analyst implementation complete.
</success_criteria>

<output>
After completion, create `.planning/phases/03-analytical-agents-deterministic-scoring/03-05-SUMMARY.md` summarizing the 3 commits, the score() signature, the 3-tier blend with weights, the cross-phase dependency on 02-07, and the Wave 2 closeout (xfail markers removed, all-four-analysts contract enforced).

Update `.planning/STATE.md` Recent Decisions with a Phase-3-complete entry pointing to all 5 plan SUMMARYs (03-01..03-05) and ANLY-01..04 marked complete in REQUIREMENTS.md.

Update `.planning/REQUIREMENTS.md` Traceability table — flip ANLY-01..04 status from "Pending" to "Complete".

Update `.planning/ROADMAP.md` Phase 3 plan list — flip all 5 entries from `[ ]` to `[x]`.
</output>
