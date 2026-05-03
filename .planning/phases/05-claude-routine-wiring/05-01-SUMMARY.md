---
phase: 05-claude-routine-wiring
plan: 01
subsystem: foundation
tags: [phase-5, foundation, wave-0, sdk-install, analyst-id-widening, scaffolding, tdd]
duration: ~20 minutes
completed: 2026-05-03
requirements-completed: []  # 05-01 is foundation; LLM-01 + LLM-02 close in 05-04 when persona prompts have real content
---

# Phase 05 Plan 01: Foundation — SDK Install + AnalystId Widening + Scaffolding Summary

**Wave 0 lands. `pyproject.toml` updated with 3 surgical edits (anthropic>=0.95,<1 dep + routine/synthesis added to wheel.packages + coverage.source). `analysts/signals.py` AnalystId Literal widened from 4 IDs to 10 IDs (4 analytical + 6 persona slate: buffett, munger, wood, burry, lynch, claude_analyst). 4 empty package markers (routine/, synthesis/, tests/routine/, tests/synthesis/) + placeholder conftest. 7 markdown stubs at prompts/personas/{6 personas}.md + prompts/synthesizer.md with locked 5-section structure (Wave 3 + Wave 4 fill in real content). 2 SDK smoke tests + 12 widening tests; 442 total passed (440 baseline + 14 new). Phase 1-4 regression invariant held: all existing tests stayed GREEN.**

## Task Commits

1. **Task 1 RED — `test(05-01): add failing tests for widened AnalystId Literal + scaffold routine/synthesis packages`:** committed pyproject.toml edits + 4 package markers + tests/analysts/test_signals.py with 3 new tests (parametrized over 10 IDs + invalid-id reject + arity-10 lock).
2. **Task 1 GREEN — `feat(05-01): widen AnalystId Literal to 10 IDs (4 analytical + 6 persona slate)`:** widened the AnalystId Literal in analysts/signals.py from 4 to 10 IDs. 36/36 test_signals.py tests green. Full repo: 440 passed.
3. **Task 2 GREEN — `feat(05-01): scaffold prompts/personas/ stubs + synthesizer.md + SDK smoke test`:** 6 persona markdown stubs + synthesizer stub + 2-test SDK smoke suite. Full repo: 442 passed.

## Files Created/Modified

### Created
- `routine/__init__.py` (package docstring)
- `synthesis/__init__.py` (package docstring)
- `tests/routine/__init__.py` (empty marker)
- `tests/routine/conftest.py` (placeholder for Wave 2)
- `tests/synthesis/__init__.py` (empty marker)
- `tests/routine/test_smoke.py` (2 SDK smoke tests)
- `prompts/personas/buffett.md` (5-section stub)
- `prompts/personas/munger.md` (5-section stub)
- `prompts/personas/wood.md` (5-section stub)
- `prompts/personas/burry.md` (5-section stub)
- `prompts/personas/lynch.md` (5-section stub)
- `prompts/personas/claude_analyst.md` (5-section stub)
- `prompts/synthesizer.md` (4-section stub)

### Modified
- `pyproject.toml` (3 surgical edits: +1 dep, +2 list extensions)
- `analysts/signals.py` (AnalystId Literal 4→10 IDs; all other lines preserved)
- `tests/analysts/test_signals.py` (+3 new tests appended; existing tests preserved)

## Decisions Made

- **anthropic SDK pinned at >=0.95,<1** per 05-RESEARCH.md CORRECTION #3 (the `output_format=PydanticModel` parameter shipped in 0.95). uv resolved 0.97.0.
- **AnalystId widening preserves order** (4 analytical first, 6 persona slate second). Wave 3 PERSONA_IDS tuple will iterate in this order.
- **Persona output IS an AgentSignal** (verbatim — no separate PersonaSignal class). Phase 5's only schema change in analysts/ is the Literal widening.
- **5-section markdown structure locked at Wave 0** so Wave 3's voice-signature-presence assertions surface actionable failures (not "file not found").
- **`uv.lock` stays gitignored** per pre-existing project convention; the lockfile is treated as a build artifact.

## Self-Check: PASSED

- [x] anthropic SDK installed (0.97.0); `from anthropic import AsyncAnthropic, APIError, APIStatusError` works.
- [x] `client.messages.parse` attribute present on AsyncAnthropic instance.
- [x] AnalystId Literal has exactly 10 args; all 10 IDs construct cleanly via parametrized test.
- [x] Invalid ID raises ValidationError with 'analyst_id' in error loc.
- [x] All 7 markdown stubs present at the locked paths with the locked 5-section headers.
- [x] 4 package markers + placeholder conftest in place.
- [x] Full repo regression: 442 passed (no Phase 1-4 test regression).
- [x] Coverage on analysts/signals.py: 100% line + branch (unchanged from Phase 3).

## Next Phase Readiness

- **Plan 05-02 (TickerDecision schema)** UNBLOCKED. Will land synthesis/decision.py + ~12 schema tests.
- **Plan 05-03 (LLM client)** UNBLOCKED. Will land routine/llm_client.py + retry + default-factory.
- **Plans 05-04 (personas) + 05-05 (synthesizer) + 05-06 (entrypoint)** UNBLOCKED.

---
*Phase: 05-claude-routine-wiring*
*Plan: 01-foundation*
*Completed: 2026-05-03*
