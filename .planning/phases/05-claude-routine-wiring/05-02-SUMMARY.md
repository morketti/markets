---
phase: 05-claude-routine-wiring
plan: 02
subsystem: schema
tags: [phase-5, schema, decision, ticker-decision, dissent, timeframe-band, pydantic-v2, tdd, wave-1, llm-06]

# Dependency graph
requires:
  - phase: 03-analytical-agents-deterministic-scoring
    provides: AgentSignal Pydantic v2 pattern (ConfigDict extra='forbid', @field_validator('ticker') normalize_ticker delegation, @model_validator(mode='after') data_unavailable invariant)
  - phase: 04-position-adjustment-radar
    provides: PositionSignal PEER-not-subtype precedent + multi-field data_unavailable invariant pattern
  - phase: 05-claude-routine-wiring
    provides: Plan 05-01 — anthropic SDK installed + AnalystId widened to 10 IDs + synthesis/__init__.py package marker
provides:
  - "synthesis/decision.py — TickerDecision Pydantic v2 model + DecisionRecommendation Literal (6-state) + ConvictionBand Literal (3-state) + Timeframe Literal (2-state) + TimeframeBand peer model + DissentSection peer model + 3 validators"
  - "TickerDecision: 10 fields (ticker, computed_at, schema_version, recommendation, conviction, short_term, long_term, open_observation, dissent, data_unavailable); ConfigDict(extra='forbid'); @field_validator('ticker') delegating to analysts.schemas.normalize_ticker; @model_validator(mode='after') enforcing data_unavailable=True ⟹ recommendation='hold' AND conviction='low'"
  - "TimeframeBand: summary (str, 1-500 chars), drivers (list[str], ≤10 items, ≤200 chars per item via custom @field_validator), confidence (int 0-100); ConfigDict(extra='forbid')"
  - "DissentSection: has_dissent (bool=False), dissenting_persona (str|None=None), dissent_summary (str, default='', ≤500 chars); ConfigDict(extra='forbid')"
  - "schema_version=1 forward-compat hook (Phase 9 + v1.x can additively extend; backward-incompatible field additions require deliberate version bump)"
affects: [05-03-llm-client, 05-04-personas, 05-05-synthesizer, 05-06-routine-entrypoint, phase-6-frontend, phase-7-decision-support, phase-8-mid-day-refresh, phase-9-endorsements]

# Tech tracking
tech-stack:
  added: []  # No new dependencies — Pydantic v2 already locked from Phase 1; anthropic SDK landed in 05-01
  patterns:
    - "TickerDecision is a PEER-not-subtype of AgentSignal AND PositionSignal — three independent schema families coexist in the same module-import path with zero subclass relationships"
    - "Three Literal types co-located at module level (DecisionRecommendation, ConvictionBand, Timeframe) — same single-source-of-truth pattern as analysts/signals.py (Verdict, AnalystId) and analysts/position_signal.py (PositionState, ActionHint)"
    - "Two-tier nesting via Pydantic v2 (TimeframeBand + DissentSection nested inside TickerDecision) survives JSON round-trip cleanly with model_dump_json → model_validate_json"
    - "schema_version=1 forward-compat hook combined with extra='forbid' — extends-only growth; structural changes force a deliberate version bump"
    - "@model_validator(mode='after') invariant matches the Phase 3 + Phase 4 precedent — schema layer guarantees the data_unavailable=True ⟹ safe-defaults contract; downstream consumers (Phase 5 synthesizer, Phase 6 frontend, Phase 7 decision-support) need no defensive checks"

key-files:
  created:
    - "synthesis/decision.py — 212 LOC (provenance docstring + 3 Literal types + TimeframeBand + DissentSection + TickerDecision + 3 validators)"
    - "tests/synthesis/test_decision.py — 483 LOC (45 tests; ≥18 floor; covers shape/defaults, ticker normalization, all 6+3+2 enum values, length caps, confidence range, data_unavailable invariant 4 paths, JSON round-trip, PEER-not-subtype, computed_at UTC preservation)"
  modified: []  # Pure-additive plan — no Phase 1-4 file touched

key-decisions:
  - "Schema-level @model_validator(mode='after') enforces data_unavailable=True ⟹ recommendation='hold' AND conviction='low' (closes Pitfall #4-class drift; matches Phase 3 AgentSignal _data_unavailable_implies_neutral_zero + Phase 4 PositionSignal _data_unavailable_implies_fair_zero precedent; Open Question #3 from 05-RESEARCH.md explicitly recommends include)"
  - "TimeframeBand confidence has NO default — caller MUST set; avoids silent zero-confidence (different from AgentSignal where confidence=0 is the canonical 'inconclusive' default — TimeframeBand is per-timeframe synthesis content, not a verdict)"
  - "TimeframeBand summary has min_length=1 — empty summaries are a synthesizer bug, not a valid state"
  - "DissentSection.dissenting_persona is `str | None`, NOT a Literal of the 6 persona IDs — keeps the dissent contract decoupled from the analyst-id Literal in analysts/signals.py (Phase 5 may extend the persona slate via markdown drop without forcing a schema migration)"
  - "schema_version=1 default + forward-compat hook (Phase 9 + v1.x add fields like endorsement_refs / performance numbers; the version field lets the frontend tolerate forward-compat additions)"
  - "PEER-not-subtype contract — TickerDecision is NOT a subclass of AgentSignal or PositionSignal; locked by dedicated test_ticker_decision_not_subclass_of_other_signals (mirrors Phase 4's PEER-not-subtype lock)"
  - "Provenance per INFRA-07 — module docstring references TauricResearch/TradingAgents portfolio_manager.py PortfolioDecision shape with explicit 6-modification list (6-state vs 5-state recommendation; explicit DissentSection — novel-to-this-project for LLM-07; dual-timeframe TimeframeBand vs single-timeframe; ConfigDict extra='forbid'; ticker normalize delegation; @model_validator data_unavailable invariant)"

patterns-established:
  - "Three nested Pydantic v2 models in one module file (synthesis/decision.py) — peer composition via field types rather than inheritance; matches the analysts/signals.py + analysts/position_signal.py disposition where each module owns one schema family"
  - "Drivers per-string cap as a custom @field_validator (≤200 chars per string), Field(max_length=10) for the count cap — same dual-validator shape as AgentSignal.evidence + PositionSignal.evidence (count cap declarative; per-string cap procedural)"
  - "Forward-compat schema_version field + extra='forbid' as a coordinated pair — Phase 9 + v1.x amendments declare a version bump; field additions are extends-only"

requirements-completed:
  - LLM-06  # TickerDecision shape with short_term + long_term + recommendation + open_observation locked at the schema layer; LLM-06 closes when 05-05 synthesizer ships the prompt that produces this shape, but the schema contract is locked here

# Metrics
duration: ~10 minutes (executor reconciliation; original RED+GREEN commits landed in prior session)
completed: 2026-05-04
---

# Phase 05 Plan 02: TickerDecision Schema (Wave 1 / LLM-06) Summary

**`synthesis/decision.py` (212 LOC) ships the locked Phase 5 synthesizer-output contract: `TickerDecision` Pydantic v2 model + `TimeframeBand` + `DissentSection` nested peer models + 3 module-level Literal types (`DecisionRecommendation` 6-state, `ConvictionBand` 3-state, `Timeframe` 2-state) + 3 validators. Schema-level `@model_validator(mode='after')` enforces `data_unavailable=True ⟹ recommendation='hold' AND conviction='low'` (matches Phase 3 + Phase 4 precedent; closes Pitfall #4-class drift). 45 tests in `tests/synthesis/test_decision.py` (well above the ≥18 floor) GREEN; coverage on the new module **100% line / 100% branch**. Full repo regression: 487 passed (442 baseline + 45 new). PEER-not-subtype contract with AgentSignal AND PositionSignal locked. Wave 2 (05-03 LLM client) + Wave 4 (05-05 synthesizer) + Wave 5 (05-06 routine-entrypoint) all unblocked — they can now `from synthesis.decision import TickerDecision, DissentSection, TimeframeBand, DecisionRecommendation, ConvictionBand, Timeframe`.**

## Performance

- **Duration:** ~10 min (executor reconciliation; the actual RED + GREEN commits landed in the prior session — see Task Commits)
- **Started (executor reconciliation):** 2026-05-04T11:17:00Z
- **Completed:** 2026-05-04T11:30:00Z
- **Tasks:** 1 (TDD; 2 commits — RED + GREEN)
- **Files created:** 2 (synthesis/decision.py, tests/synthesis/test_decision.py)
- **Files modified:** 0

## Accomplishments

- **`synthesis/decision.py` shipped (212 LOC)** — TickerDecision with all 10 locked fields (ticker, computed_at, schema_version, recommendation, conviction, short_term, long_term, open_observation, dissent, data_unavailable); TimeframeBand + DissentSection nested peer models; 3 module-level Literal types; 3 validators (ticker normalization delegating to `analysts.schemas.normalize_ticker`; drivers per-string cap; data_unavailable invariant).
- **45 tests in `tests/synthesis/test_decision.py`** (483 LOC) — well above the ≥18 floor — covering: shape/defaults (4), ticker normalization (2), enum coverage with parametrized expansion over 6 + 3 + 2 Literal values + arity locks (8), TimeframeBand boundaries (10), DissentSection (4), open_observation cap (3), data_unavailable invariant 4 paths (clean + 3 violation flavours), JSON round-trip 2 paths (minimal + fully populated with schema_version=2), PEER-not-subtype lock (1), UTC datetime round-trip preservation (1).
- **PEER-not-subtype contract locked** — TickerDecision, TimeframeBand, DissentSection are all confirmed NOT subclasses of AgentSignal or PositionSignal via dedicated `test_ticker_decision_not_subclass_of_other_signals`. The synthesizer reads a list-of-mixed-types (4 analytical AgentSignals + PositionSignal + 6 persona AgentSignals) and produces a TickerDecision; none inherit from the others.
- **Full repo regression GREEN** — 487 passed (442 baseline post-05-01 + 45 new). Phase 1-4 + Wave 0 untouched (pure-additive plan; no Phase 1-4 file modified).
- **Coverage gates cleared** — synthesis/decision.py at **100% line / 100% branch** (gate ≥90% / ≥85%).

## Task Commits

Each task was committed atomically per TDD discipline:

1. **Task 1 RED — `test(05-02): add failing tests for TickerDecision + TimeframeBand + DissentSection schemas`** — `d0054e9`
   - 45 failing tests added to `tests/synthesis/test_decision.py`. Imports `synthesis.decision` (the module didn't exist) → `ImportError`. RED state confirmed before GREEN.
2. **Task 1 GREEN — `feat(05-02): TickerDecision + DissentSection + TimeframeBand Pydantic schemas with data_unavailable invariant + 6/3/2-state Literal enums`** — `287dc72`
   - `synthesis/decision.py` shipped (212 LOC). All 45 tests flipped to GREEN. Coverage on `synthesis/decision.py`: 100% line / 100% branch. Full repo regression: 487 passed.

**Plan metadata commit:** `f055a33` — `docs(05-02): close out plan with SUMMARY + STATE/ROADMAP/REQUIREMENTS update` (also folds in deferred 05-01 metadata closeout — the prior `fe7a818` commit only added 05-01-SUMMARY.md without touching STATE/ROADMAP/REQUIREMENTS)

_Note: This plan ran a single TDD task with a clean RED → GREEN cycle; no REFACTOR commit needed (the GREEN implementation matched the locked sketch verbatim and passed all tests on first run)._

## Files Created/Modified

### Created

- **`synthesis/decision.py`** (212 LOC) — Provenance docstring (~30 lines, references TauricResearch/TradingAgents portfolio_manager.py per INFRA-07; enumerates 6 modifications) + 3 module-level Literal types (DecisionRecommendation 6-state, ConvictionBand 3-state, Timeframe 2-state) + TimeframeBand class (ConfigDict extra='forbid'; summary/drivers/confidence; _drivers_strings_capped @field_validator) + DissentSection class (3 fields with locked defaults) + TickerDecision class (10 fields; _normalize_ticker_field @field_validator delegating to `analysts.schemas.normalize_ticker`; _data_unavailable_implies_safe_defaults @model_validator with debuggable error message format including the literal substring "data_unavailable=True invariant violated").
- **`tests/synthesis/test_decision.py`** (483 LOC) — 45 tests organized by section (SHAPE/DEFAULTS, TICKER NORMALIZATION, ENUM COVERAGE with parametrized expansion, TIMEFRAMEBAND, DISSENT SECTION, OPEN OBSERVATION, DATA_UNAVAILABLE INVARIANT, JSON ROUND-TRIP, INDEPENDENCE, computed_at UTC preservation). Local module-level builder helpers `_band(...)` + `_decision(frozen_now, **overrides)` (mirrors the make_ticker_config / make_snapshot pattern from tests/analysts/conftest.py without promoting these to fixtures — the tests are simple enough that local helpers stay clearer).

### Modified

- None. The plan is pure-additive: zero Phase 1-4 files touched, zero existing test files modified. `tests/conftest.py` already had `frozen_now` (lifted to root in 05-01); `tests/analysts/conftest.py` unchanged (its synthetic_*_history builders preserved). 

## Decisions Made

- **Schema-level @model_validator(mode='after') enforces the data_unavailable invariant.** Buggy synthesizer code can never write a `(data_unavailable=True, recommendation='buy', conviction='high')` TickerDecision to disk. Phase 5 / 6 / 7 consumers can rely on the contract without defensive checks. Matches the AgentSignal.`_data_unavailable_implies_neutral_zero` + PositionSignal.`_data_unavailable_implies_fair_zero` precedent.
- **Error message includes BOTH offending values + the literal substring `data_unavailable=True invariant violated`** so violation tests can `assert "data_unavailable=True invariant violated" in msg` and downstream debugging can see exactly what was wrong.
- **TimeframeBand has NO confidence default** — caller MUST set explicitly. Avoids the silent-zero-confidence trap (different from AgentSignal where confidence=0 is the canonical "we looked, inconclusive" default; TimeframeBand is synthesis content per-timeframe, not a verdict).
- **TimeframeBand.summary has min_length=1** — empty summaries are a synthesizer bug, not a valid state. The `data_unavailable=True` clean path uses summary='data unavailable: snapshot missing' (locked by `test_data_unavailable_clean_path`).
- **DissentSection.dissenting_persona is `str | None`** (NOT a Literal of the 6 persona IDs). Keeps the dissent contract decoupled from `analysts.signals.AnalystId` — Phase 5+ may extend the persona slate (markdown file drop) without forcing a schema migration. The Python dissent computation in Wave 4 (`synthesis/synthesizer.py / compute_dissent`) populates it with one of the 6 known IDs.
- **schema_version=1 + extra='forbid' as coordinated pair** — Phase 9 + v1.x can additively extend (endorsement_refs, performance numbers); structural changes require a deliberate version bump that the frontend can detect.
- **PEER-not-subtype with AgentSignal AND PositionSignal** — locked by `test_ticker_decision_not_subclass_of_other_signals`. Three peer schema families coexist; none inherit from any other.
- **Provenance per INFRA-07** — module docstring references `TauricResearch/TradingAgents/tradingagents/agents/managers/portfolio_manager.py` and explicitly enumerates 6 modifications (6-state vs 5-state recommendation; explicit DissentSection — novel; dual-timeframe TimeframeBand vs single-timeframe; ConfigDict extra='forbid'; ticker normalize delegation; @model_validator data_unavailable invariant).

## Deviations from Plan

**None — plan executed exactly as written.** All 45 tests passed on first GREEN run; the implementation matched the locked sketch verbatim. Zero auto-fixes, zero Rule-1/2/3 deviations, zero Rule-4 architectural escalations.

Notable confirmations of the locked plan:

- `tests/conftest.py` already had `frozen_now` (lifted in 05-01 closeout) — no PRE-WORK conftest extension needed; `tests/synthesis/test_decision.py` consumed it via root-level pytest discovery.
- The `synthesis/__init__.py` package marker already existed (scaffolded in 05-01) — no Wave 0 reshuffle needed.
- The `analysts.schemas.normalize_ticker` import path was a single-line drop; the same delegation pattern as AgentSignal + PositionSignal + every analysts.data.* sub-schema; round-trip `'brk.b' → 'BRK-B'` worked first try (locked by `test_ticker_normalization`).

## Self-Check: PASSED

- [x] `synthesis/decision.py` exists at `C:/Users/Mohan/markets/synthesis/decision.py` (212 LOC)
- [x] `tests/synthesis/test_decision.py` exists at `C:/Users/Mohan/markets/tests/synthesis/test_decision.py` (483 LOC; 45 tests)
- [x] RED commit `d0054e9` exists in `git log`
- [x] GREEN commit `287dc72` exists in `git log`
- [x] All 45 `test_decision.py` tests GREEN under `python -m pytest tests/synthesis/test_decision.py -v`
- [x] Coverage on `synthesis/decision.py`: **100% line / 100% branch** (gate ≥90% / ≥85%)
- [x] Full repo regression: **487 passed** (442 baseline post-05-01 + 45 new) — Phase 1-4 + Wave 0 untouched
- [x] PEER-not-subtype contract: `not issubclass(TickerDecision, AgentSignal)` AND `not issubclass(TickerDecision, PositionSignal)` AND same for TimeframeBand AND DissentSection — all confirmed (`peer-not-subtype OK` print)
- [x] Provenance string `TauricResearch/TradingAgents` present in `synthesis/decision.py` (line 3)
- [x] Literal arity locks: `get_args(DecisionRecommendation) == ('add', 'trim', 'hold', 'take_profits', 'buy', 'avoid')`; `get_args(ConvictionBand) == ('low', 'medium', 'high')`; `get_args(Timeframe) == ('short_term', 'long_term')` — all confirmed
- [x] Ticker normalization delegation: `TickerDecision(ticker='brk.b', ...).ticker == 'BRK-B'` (locked by `test_ticker_normalization`)
- [x] data_unavailable invariant fires correctly: 3 violation tests (recommendation / conviction / both) AND 1 clean-path test all GREEN
- [x] JSON round-trip preserves nested models + UTC datetime (2 tests + 1 dedicated UTC test all GREEN)

## Next Phase Readiness

- **Plan 05-03 (LLM client)** UNBLOCKED. Can now `from synthesis.decision import TickerDecision` if it needs to type-hint synthesizer return values (though the LLM client itself wraps `claude.messages.parse(... output_format=PydanticModel)` and will likely receive AgentSignal for persona calls; TickerDecision lands as the synthesizer's output type).
- **Plan 05-04 (personas)** UNBLOCKED. Personas output `AgentSignal` (analyst_id=persona-id), not `TickerDecision`; this plan doesn't directly consume synthesis.decision but ships in parallel under the same Wave structure.
- **Plan 05-05 (synthesizer)** UNBLOCKED — the primary downstream consumer. Wave 4 imports `TickerDecision`, `DissentSection`, `TimeframeBand`, `DecisionRecommendation`, `ConvictionBand`, `Timeframe` from `synthesis.decision`. The synthesizer's `_data_unavailable_decision` helper will populate the safe-defaults shape that satisfies the @model_validator invariant locked here.
- **Plan 05-06 (routine entrypoint)** UNBLOCKED. `routine/storage.py` will JSON-serialize the TickerDecision into `data/YYYY-MM-DD/{ticker}.json` alongside the 4 analytical AgentSignals + PositionSignal + 6 persona AgentSignals.
- **Phase 6 (frontend)** TickerDecision contract is now stable for the v1 schema_version. Frontend zod validators key off `schema_version: 1`; forward-compat field additions in Phase 9 / v1.x will bump the version and let the frontend gracefully degrade.
- **Phase 7 (Decision-Support View)** has its banner contract locked: recommendation ∈ {add, trim, hold, take_profits, buy, avoid}, conviction ∈ {low, medium, high}, dissent.has_dissent drives the dissent panel rendering.
- **LLM-06** schema half closes here. The full LLM-06 requirement (synthesizer prompt PRODUCES this shape via `claude.messages.parse(... output_format=TickerDecision)`) closes when 05-05 ships the synthesizer prompt + Python orchestrator.

---
*Phase: 05-claude-routine-wiring*
*Plan: 02-decision-schema*
*Completed: 2026-05-04*
