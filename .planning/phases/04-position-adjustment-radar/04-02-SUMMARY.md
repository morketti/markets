---
phase: 04-position-adjustment-radar
plan: 02
subsystem: analysts
tags: [phase-4, schema, position-signal, tdd, wave-1, pose-02, pose-04]

requires:
  - phase: 04-position-adjustment-radar
    plan: 01
    provides: Wave 0 foundation refactor — analysts/_indicator_math.py + 3 synthetic-history builders. Plan 04-02 doesn't directly import any 04-01 output but conservatively waves after it (the schema is implementationally independent; this dep keeps the wave layering clean).
  - phase: 03-analytical-agents-deterministic-scoring
    plan: 01
    provides: 'analysts/signals.py — AgentSignal + Verdict + AnalystId. PositionSignal mirrors AgentSignal''s validator discipline (ticker normalization, evidence cap, @model_validator data_unavailable invariant) without subclassing — see PEER-not-subtype decision below.'
provides:
  - "analysts/position_signal.py — `PositionSignal` Pydantic v2 model (10 fields) + `PositionState` Literal (5 values) + `ActionHint` Literal (4 values)"
  - "Schema-level invariant via @model_validator(mode='after'): data_unavailable=True ⟹ state='fair' AND consensus_score==0.0 AND confidence==0 AND action_hint='hold_position' AND trend_regime==False (closes 04-RESEARCH.md Pitfall #1; mirrors AgentSignal's _data_unavailable_implies_neutral_zero pattern)"
  - "PEER-level peer to AgentSignal — separate Pydantic model, NOT subclass; ~30 LOC of validator duplication (ticker normalization + evidence cap) accepted per 04-RESEARCH.md Pattern #7"
  - "Single source of truth for Phase 4's output type — Phase 5 routine, Phase 6 frontend, Phase 7 Decision-Support all import PositionSignal from this module"
affects: [phase-4-plan-03-position-adjustment, phase-5-claude-routine, phase-6-frontend-mvp, phase-7-decision-support]

# Tech tracking
tech-stack:
  added: []  # No new dependencies — Pydantic v2 already locked at Phase 1
  patterns:
    - "PEER-not-subtype Pydantic schema pattern: when two output schemas share validator logic but diverge on field shape (verdict ladder vs state ladder + action_hint + indicators dict + trend_regime flag), accept ~30 LOC of validator duplication rather than force a shared base class with a string-typed discriminator field. The duplicated validators (ticker normalization, evidence per-string cap) are simple stateless delegations; drift surfaces in tests immediately."
    - "Schema-level invariant via @model_validator(mode='after'): catches the 'data_unavailable=True but other fields say something' bug class at construction time. Buggy analysts can never write a `PositionSignal(data_unavailable=True, state='oversold', consensus_score=-0.5, confidence=80, ...)` to disk; Phase 5/6 consumers can rely on the contract without defensive checks. Same shape as Phase 3's AgentSignal invariant — pattern is now well-established across the analyst suite."
    - "Module-level Literal types co-located with the consuming model: PositionState + ActionHint live in analysts/position_signal.py alongside PositionSignal. Importers do `from analysts.position_signal import PositionSignal, PositionState, ActionHint` in one statement. Mirrors analysts/signals.py pattern (Verdict + AnalystId + AgentSignal in one file)."
    - "Per-field error messages in @model_validator: when the invariant is violated, the error message includes the actual value of every offending field (state={value!r} (expected 'fair')) — debuggable and grep-friendly. The literal substring 'data_unavailable=True invariant violated' is locked into the error so violation tests can grep on it without coupling to specific field values."

key-files:
  created:
    - "analysts/position_signal.py (~150 lines — provenance docstring + 2 Literal types + PositionSignal class with 10 fields + 3 validators)"
    - "tests/analysts/test_position_signal.py (~350 lines, 35 tests including parametrized Literal coverage and 5 individual data_unavailable invariant violation tests)"
  modified: []  # No existing files touched

key-decisions:
  - "PEER-not-subtype contract for PositionSignal vs AgentSignal. Locked by `test_position_signal_not_subclass_of_agent_signal` (assertions: `not issubclass(PositionSignal, AgentSignal)` AND `not issubclass(AgentSignal, PositionSignal)`). Field shapes diverge (state ladder vs verdict ladder; action_hint + indicators dict + trend_regime flag are PositionSignal-only). Phase 5 synthesizer reads the four AgentSignals + this PositionSignal as a list-of-mixed-types — no shared-base type pull is needed."
  - "Schema-level @model_validator(mode='after') enforces the 5-field data_unavailable=True invariant: state='fair' AND consensus_score=0.0 AND confidence=0 AND action_hint='hold_position' AND trend_regime=False. Closes 04-RESEARCH.md Pitfall #1 (the 'buggy analyst writes data_unavailable=True with non-canonical other fields' bug class). Same pattern as AgentSignal's invariant in analysts/signals.py — if analyst code ever drifts, validation catches it at construction time."
  - "Default values match the canonical no-opinion shape (state='fair', consensus_score=0.0, confidence=0, action_hint='hold_position', indicators={}, evidence=[], data_unavailable=False, trend_regime=False). The schema is literally constructible with only ticker + computed_at — every other field defaults to the canonical 'we computed nothing useful' shape. Mirrors AgentSignal's default-shape philosophy."
  - "indicators is dict[str, float | None] — values are either floats (when the indicator computed cleanly) or None (when warm-up bars insufficient). Locked by test_indicators_dict_with_none_values which constructs a snapshot with all 7 indicator keys mapped to None (the empty-data warm-up case). Phase 4 Wave 2 will populate this dict during score() execution."
  - "PositionState 5-state ladder boundaries chosen to mirror Phase 3's verdict-ladder strict-> at ±0.6/±0.2 — but oriented around mean-reversion sign (negative consensus_score = oversold; positive = overbought). The same 5-state pattern lets Phase 6 frontend and Phase 7 Decision-Support reuse rendering helpers across both signal types (just swap the labels)."
  - "ActionHint 4-state ladder (consider_add / hold_position / consider_trim / consider_take_profits) — Phase 4's deterministic mapping from PositionState. consider_add collapses extreme_oversold + oversold (Phase 7 reads confidence to derive conviction band); consider_take_profits is the asymmetric counterpart to consider_add (extreme_overbought signals stronger profit-taking action than mere overbought). Locked by 04-CONTEXT.md mapping table; Wave 2 will implement the deterministic state → action_hint function."
  - "Validator duplication accepted: ~30 LOC of ticker normalization + evidence cap overlap with AgentSignal. A shared base class would have forced a generic schema with a `signal_type` discriminator field, breaking the clean PEER-not-subtype boundary and complicating downstream type-narrowing in Phase 5/6/7. The two validators are simple stateless delegations to analysts.schemas.normalize_ticker + len() — drift surfaces in tests immediately if either schema's discipline ever changes."
  - "Field(max_length=10) for evidence count + custom @field_validator for per-string ≤200 chars — same split as AgentSignal. Pydantic Field handles list-length cleanly; the per-string cap requires custom logic because Pydantic doesn't have a built-in 'every string in this list ≤ N chars' validator."
  - "JSON round-trip works out-of-the-box. Pydantic v2 handles datetime ISO-8601 serialization automatically; ConfigDict(extra='forbid') doesn't reject its own model_dump_json output. Locked by test_json_round_trip — non-trivial signal (state='overbought', consensus_score=0.45, action_hint='consider_trim', indicators with 3 floats, 2 evidence strings, trend_regime=True) round-trips to byte-equal object."

patterns-established:
  - "Schema with @model_validator(mode='after') for cross-field invariants: pattern from Phase 3's AgentSignal carries forward to Phase 4's PositionSignal. Future analyst output types (Phase 5 TickerDecision, Phase 9 Endorsement) should use the same shape — error message includes all violated fields' actual values for debuggability and a literal substring for grep-ability."
  - "PEER-not-subtype for divergent-shape sibling schemas: when two output types share validator logic but diverge on field shape, accept ~30 LOC of validator duplication. Drift catches in tests immediately. Reusable for the next time we add a peer schema (Phase 9 EndorsementSignal? Phase 5 TickerDecision?)."

requirements-completed: []  # 04-02 ships the schema; POSE-02 + POSE-04 close in Plan 04-03 when score() implements them

# Metrics
duration: ~15 minutes active execution (RED + GREEN; no Rule-1 fixes needed)
completed: 2026-05-03
---

# Phase 04 Plan 02: PositionSignal Schema Summary

**Wave 1 schema scaffold lands. `analysts/position_signal.py` (~150 LOC) ships `PositionSignal` Pydantic v2 model + `PositionState` Literal (5-state mean-reversion ladder: extreme_oversold | oversold | fair | overbought | extreme_overbought) + `ActionHint` Literal (4-state pre-recommendation hint: consider_add | hold_position | consider_trim | consider_take_profits). 10-field model with ConfigDict(extra='forbid'), 3 validators (ticker normalization delegating to analysts.schemas.normalize_ticker, evidence per-string ≤200-char cap, @model_validator(mode='after') enforcing the 5-field data_unavailable=True invariant — closes 04-RESEARCH.md Pitfall #1). PEER-not-subtype contract with AgentSignal locked by dedicated issubclass test. 35 tests / 100% line+branch coverage. Wave 2 (04-03 position_adjustment analyst) unblocked.**

## Performance

- **Duration:** ~15 minutes active execution. Both RED and GREEN passed on first run; no Rule-1 test-side fixes needed.
- **Tasks:** 1 (RED + GREEN per the plan).
- **Files created:** 2 (`analysts/position_signal.py` ~150 lines, `tests/analysts/test_position_signal.py` ~350 lines)
- **Files modified:** 0

## Accomplishments

- **`analysts/position_signal.py` (~150 lines)** ships the locked output schema for Phase 4. Public surface: `PositionSignal` (10 fields), `PositionState` (Literal of 5 values), `ActionHint` (Literal of 4 values).
- **All 10 fields validated:**
  - `ticker: str` — normalized via @field_validator delegating to `analysts.schemas.normalize_ticker`. Test: `test_ticker_normalization` asserts `'brk.b' → 'BRK-B'`.
  - `computed_at: datetime` — required.
  - `state: PositionState = 'fair'` — Literal of 5 values; default = canonical no-opinion.
  - `consensus_score: float = Field(ge=-1.0, le=1.0, default=0.0)` — range constrained.
  - `confidence: int = Field(ge=0, le=100, default=0)` — range constrained.
  - `action_hint: ActionHint = 'hold_position'` — Literal of 4 values; default = canonical no-opinion.
  - `indicators: dict[str, float | None] = Field(default_factory=dict)` — per-indicator readings; None for warm-up.
  - `evidence: list[str] = Field(default_factory=list, max_length=10)` + custom @field_validator for ≤200-char per-string cap.
  - `data_unavailable: bool = False`.
  - `trend_regime: bool = False`.
- **3 validators:**
  - `@field_validator('ticker', mode='before')` — delegates to `analysts.schemas.normalize_ticker` (single source of truth for ticker normalization across the codebase).
  - `@field_validator('evidence')` — walks the list, raises ValueError on any string > 200 chars. Field(max_length=10) handles count separately.
  - `@model_validator(mode='after')` — enforces the 5-field data_unavailable=True invariant. Error message includes ALL violated fields' actual values for debuggability AND the literal substring `"data_unavailable=True invariant violated"` for grep-ability.
- **5 violation cases for the data_unavailable invariant tested individually** (one test per offending field): state, consensus_score, confidence, action_hint, trend_regime. Each verifies the error message contains BOTH 'data_unavailable' AND the violated field name.
- **Tests/analysts/test_position_signal.py — 35 tests** (above plan ≥12 floor):
  - Shape / defaults: 2
  - Ticker normalization: 2
  - Literal coverage: 11 (5 PositionState parametrized + 4 ActionHint parametrized + 2 unknown rejection)
  - Range constraints: 6 (consensus_score boundaries / below / above; confidence boundaries / below / above)
  - Evidence caps: 4
  - Indicators dict: 2
  - data_unavailable invariant: 6 (clean path + 5 violation cases)
  - JSON round-trip: 1
  - PEER-not-subtype contract: 1
- **Coverage on `analysts/position_signal.py`: 100% line / 100% branch** (gate ≥90% line / ≥85% branch). Targeted suite runs in 0.06s.
- **Full repo regression: 368 passed** (333 baseline + 35 new). Phase 3 + 04-01 Wave 0 untouched.

## Task Commits

1. **Task 1 (RED) — `test(04-02): add failing tests for PositionSignal schema (5-state ladder, action_hint, data_unavailable invariant, JSON round-trip)`:** `e146a44` — `tests/analysts/test_position_signal.py` with 27 RED tests (parametrized expansion → 35 effective). Verified RED: `ModuleNotFoundError: No module named 'analysts.position_signal'`.
2. **Task 1 (GREEN) — `feat(04-02): PositionSignal Pydantic schema with 5-state state ladder + 4-state action_hint + data_unavailable invariant`:** `fa89b14` — `analysts/position_signal.py` (~150 lines). 35/35 tests green on first run; 100% coverage; full repo 368 passed; PEER-not-subtype verified.

## Files Created/Modified

### Created
- `analysts/position_signal.py` (~150 lines)
- `tests/analysts/test_position_signal.py` (~350 lines, 35 tests)

### Modified
- (none — pure additive plan)

### Modified at closeout
- `.planning/STATE.md` (Phase 4 progress 1/3 → 2/3; current_plan 2 → 3; recent decisions append)

## Decisions Made

- **PEER-not-subtype contract.** PositionSignal is NOT a subclass of AgentSignal; field shapes diverge cleanly. ~30 LOC of validator duplication (ticker normalization + evidence per-string cap) accepted as the cost of two clean peer models.
- **@model_validator data_unavailable invariant.** Schema-level enforcement of the 5-field "canonical no-opinion shape" contract; closes 04-RESEARCH.md Pitfall #1. Error message includes per-field actual values + literal grep-able substring.
- **Default values = canonical no-opinion.** state='fair', consensus_score=0.0, confidence=0, action_hint='hold_position', indicators={}, evidence=[], data_unavailable=False, trend_regime=False. Constructible with only ticker + computed_at.
- **indicators dict carries float | None values.** None marks "indicator warm-up insufficient." Phase 4 Wave 2 populates with all 7 keys (rsi_14, bb_position, zscore_50, stoch_k, williams_r, macd_histogram, adx_14).
- **Module-level Literal types co-located.** PositionState + ActionHint exported from same module as PositionSignal. Mirrors analysts/signals.py pattern.
- **Per-field error messages with grep-able substring.** Locked by 5 individual violation tests; pattern carries forward to future schema invariants.

## Deviations from Plan

**Total deviations: 0.** Implementation matches the plan's specifications byte-for-byte. All 35 tests passed on first GREEN run; no Rule-1 test-side fixes needed.

## Self-Check: PASSED

- [x] `analysts/position_signal.py` exists with provenance docstring
- [x] PositionState Literal exports 5 values; ActionHint Literal exports 4 values
- [x] PositionSignal has 10 fields with locked defaults
- [x] ConfigDict(extra='forbid') discipline
- [x] @field_validator('ticker', mode='before') delegates to normalize_ticker
- [x] @field_validator('evidence') enforces ≤200-char per-string cap
- [x] @model_validator(mode='after') enforces 5-field data_unavailable invariant
- [x] PEER-not-subtype: `not issubclass(PositionSignal, AgentSignal)` verified
- [x] JSON round-trip works
- [x] Commits `e146a44` (RED) + `fa89b14` (GREEN) in git log
- [x] 35/35 tests pass; 100% line / 100% branch coverage
- [x] Full repo regression: 368 passed (no Phase 3 / 04-01 regression)

## Next Phase Readiness

- **Plan 04-03 (position_adjustment analyst) UNBLOCKED.** Will import `PositionSignal`, `PositionState`, `ActionHint` from this module + `_build_df`, `_adx_14`, `ADX_TREND_ABOVE`, `ADX_RANGE_BELOW` from `analysts._indicator_math` (04-01) + the synthetic_*_history builders from `tests.analysts.conftest` (04-01).
- **No carry-overs / no blockers.**

---
*Phase: 04-position-adjustment-radar*
*Plan: 02-position-signal*
*Completed: 2026-05-03*
