---
phase: 05-claude-routine-wiring
plan: 04
subsystem: persona-orchestration
tags: [phase-5, persona-runner, async-fan-out, asyncio.gather, markdown-prompts, lru-cache, llm-01, llm-02, llm-03, llm-04, tdd, wave-3]

# Dependency graph
requires:
  - phase: 05-claude-routine-wiring (Wave 0 / 05-01)
    provides: AnalystId Literal widened 4->10 (4 analytical + 6 persona slate); 6 placeholder persona stubs at prompts/personas/; anthropic SDK >=0.95,<1 dep
  - phase: 05-claude-routine-wiring (Wave 2 / 05-03)
    provides: routine.llm_client.call_with_retry async wrapper + DEFAULT_MAX_RETRIES + LLM_FAILURE_LOG; tests/routine/conftest.py mock_anthropic_client + isolated_failure_log fixtures
provides:
  - 6 persona markdown prompts at prompts/personas/{buffett,munger,wood,burry,lynch,claude_analyst}.md (98-106 lines each; 5-section locked structure; voice-signature anchors per LLM-03)
  - routine/persona_runner.py module exporting PERSONA_IDS, PERSONA_MODEL, PERSONA_MAX_TOKENS, PERSONA_PROMPT_DIR, load_persona_prompt, build_persona_user_context, _persona_default_factory, run_one, run_persona_slate
  - Async fan-out over 6 personas per ticker via asyncio.gather(return_exceptions=True) — Pattern #3 (async-within-ticker)
  - Closure-bound _persona_default_factory(persona_id, ticker, computed_at) — LLM-05 cascade-prevention shape
  - Per-Python-level uncaught-exception isolation via gather(return_exceptions=True) outer slot collapse
affects: [05-05-synthesizer, 05-06-entrypoint, phase-6-frontend, phase-7-decision-support]

# Tech tracking
tech-stack:
  added: []  # No new deps; reuses anthropic SDK from 05-01 + call_with_retry from 05-03
  patterns:
    - "Markdown-loaded prompts (LLM-02 lock) — never hardcoded as Python string; @functools.lru_cache(maxsize=8) makes 6xN_TICKERS fan-out a single read per persona"
    - "Async fan-out within ticker (Pattern #3) — asyncio.gather(return_exceptions=True) over 6 PERSONA_IDS coroutines; sync across tickers (cross-ticker loop in Wave 5's run_for_watchlist stays sync)"
    - "5-section persona prompt structure — H1 + Voice Signature + Input Context + Task + Output Schema (LLM-03 anchor; voice signature contains persona-specific keywords for cross-run drift detection)"
    - "Two-tier failure isolation — per-LLM failure absorbed by call_with_retry's default_factory (Wave 2); per-Python-level exception absorbed by gather(return_exceptions=True) + outer slot collapse"

key-files:
  created:
    - routine/persona_runner.py
    - tests/routine/test_persona_runner.py
  modified:
    - prompts/personas/buffett.md
    - prompts/personas/munger.md
    - prompts/personas/wood.md
    - prompts/personas/burry.md
    - prompts/personas/lynch.md
    - prompts/personas/claude_analyst.md

key-decisions:
  - "Reuse AgentSignal verbatim for persona output — no separate PersonaSignal class. AnalystId Literal widening from 05-01 (Wave 0) lets persona AgentSignals share the analytical AgentSignal contract end-to-end (Pattern #9)."
  - "Prompts loaded at call time via Path(prompts/personas/{persona_id}.md).read_text — wrapped in @functools.lru_cache(maxsize=8) so 6xN_TICKERS fan-out is one read per persona regardless of N_TICKERS. LLM-02 lock: never as Python string."
  - "Single shared user_context per ticker — built once via build_persona_user_context, passed to all 6 persona calls. Per-persona variation lives entirely in the SYSTEM prompt (markdown), saving 6x context-build cost."
  - "Closure-bound _persona_default_factory(persona_id, ticker, computed_at) — captures all 3 contextual values at call site so each retry-exhaustion produces a contextually-correct AgentSignal(verdict='neutral', confidence=0, evidence=['schema_failure'], data_unavailable=True) with the correct analyst_id."
  - "PERSONA_IDS as immutable tuple (NOT list) — usable as dict key, hashable, and the canonical iteration order for asyncio.gather (preserves submission order in result list, byte-for-byte matches PERSONA_IDS)."
  - "asyncio.gather(return_exceptions=True) — outer defense beyond call_with_retry's per-LLM retry. If a Python-level exception fires inside run_one (e.g., a bug in build_persona_user_context for a malformed config), the other 5 personas still complete; the exception slot collapses to default_factory so synthesizer always sees 6 AgentSignals."
  - "claude_analyst.md framed as 'NOT a persona, NOT a lens — Claude's inherent reasoning surfaced' per user MEMORY.md feedback ('include Claude's inherent reasoning, not just personas — never let lenses replace inherent reasoning'). Explicit 'novel-to-this-project' provenance — no virattt analog."
  - "Explicit run_persona_slate validation: len(analytical_signals) == 4 raises ValueError early — defensive against synthesizer-side ordering bugs ('fund/tech/nsen/val expected'). Saves a downstream cryptic IndexError."
  - "Auto-fix Rule 1 — _summarize_snapshot used wrong attribute names (pe_ratio / return_on_equity) which don't exist on FundamentalsSnapshot (the real fields are pe / roe / debt_to_equity). Fixed to actual schema field names; this was dead code at runtime that would have raised AttributeError when Wave 5's entrypoint passes populated snapshots."

patterns-established:
  - "Persona-prompt 5-section structure (LLM-03 lock): # Persona: <Name> H1 -> ## Voice Signature -> ## Input Context -> ## Task -> ## Output Schema. Voice Signature contains 3-5 persona-specific keyword anchors (Buffett: owner earnings/moat/margin of safety; Munger: mental model/invert; Wood: disruptive innovation/exponential; Burry: contrarian; Lynch: PEG/10-bagger; Claude: NOT a/Claude/inherent)."
  - "Async fan-out pattern (Pattern #3): asyncio.gather(*[coro for pid in PERSONA_IDS], return_exceptions=True) -> per-slot exception collapse to default_factory. Order preserved by gather submission order matching PERSONA_IDS canonical order."
  - "Markdown-loaded prompt (LLM-02): Path(PROMPT_DIR / f'{id}.md').read_text(encoding='utf-8') wrapped in @functools.lru_cache. ValueError on unknown id (defensive — earlier than AnalystId Literal validation downstream); FileNotFoundError on missing file (defensive — surfaces deployment-asset gaps)."
  - "Two-tier failure isolation: (a) per-LLM (ValidationError/APIError) -> call_with_retry default_factory (Wave 2); (b) per-Python-level uncaught exception -> gather(return_exceptions=True) outer collapse to default_factory. Both paths produce contextually-correct AgentSignals; cascade prevention beyond a single mechanism."

requirements-completed: [LLM-01, LLM-02, LLM-03, LLM-04]

# Metrics
duration: ~28min
completed: 2026-05-04
---

# Phase 5 Plan 04: Persona Slate + Async Fan-Out Runner Summary

**6 markdown persona prompts (Buffett/Munger/Wood/Burry/Lynch/Open Claude Analyst) + routine/persona_runner.py async fan-out via asyncio.gather(return_exceptions=True) over PERSONA_IDS, AgentSignal-validated through call_with_retry, with closure-bound default-factory cascade prevention.**

## Performance

- **Duration:** ~28 min
- **Started:** 2026-05-04 (post 05-03 close)
- **Completed:** 2026-05-04
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files created:** 2 (routine/persona_runner.py, tests/routine/test_persona_runner.py)
- **Files modified:** 6 (the 6 persona markdown stubs replaced with full content)

## Accomplishments

- 6 persona markdown prompts shipped at `prompts/personas/{buffett,munger,wood,burry,lynch,claude_analyst}.md` — 98 to 106 lines each (Wave 0 stubs were ~12-22 lines); 5-section locked structure (H1 + Voice Signature + Input Context + Task + Output Schema) verified by 6 parametrized tests; voice-signature keyword anchors per persona verified by another 6 parametrized tests (LLM-03 lock).
- `claude_analyst.md` (106 lines) explicitly distinguishes itself from the 5 canonical personas per user MEMORY.md feedback_claude_knowledge: "NOT a persona, NOT a lens — Claude's inherent reasoning surfaced when given the per-ticker snapshot + analytical signals". Declares "novel-to-this-project" (no virattt analog).
- `routine/persona_runner.py` (289 lines including docstring + helpers) ships the async-within-ticker fan-out pattern. Public surface: PERSONA_IDS canonical tuple, 3 module constants (PERSONA_MODEL='claude-sonnet-4-6', PERSONA_MAX_TOKENS=2000, PERSONA_PROMPT_DIR=Path('prompts/personas')), load_persona_prompt with lru_cache + ValueError + FileNotFoundError, build_persona_user_context (deterministic), _persona_default_factory closure builder, run_one async, run_persona_slate async with asyncio.gather(return_exceptions=True) + count validation + outer slot collapse.
- 45 tests in `tests/routine/test_persona_runner.py` (well above the >=14 floor with parametrization expansion to 39 instances + 6 coverage tests). All GREEN. Coverage: **100% line / 100% branch** on routine/persona_runner.py (gate >=90/85).
- Full repo regression: **549 passed** (504 baseline + 45 new). Phase 1-4 + Wave 0 + Wave 1 + Wave 2 untouched (pure-additive plan; persona_runner not yet imported anywhere — Wave 5 entrypoint will import it).

## Task Commits

TDD discipline preserved — each phase committed atomically:

1. **Task 1 RED** — `ffb5132` (test): 14 tests (40+ parametrized instances) covering file presence + 5-section structure + voice-signature keyword anchors + Output Schema field names + claude_analyst "NOT a persona" framing + PERSONA_IDS canonical order + AnalystId Literal subset + module constants + load_persona_prompt cache/invalid-id + user_context content/determinism + run_one happy/default_factory + run_persona_slate fan-out/single-failure-isolation/wrong-signal-count + provenance. RED state: 28 failed (line-count + ImportError + provenance), 11 passed (some structural tests on stubs already passed).
2. **Task 1 GREEN** — `b205064` (feat): 6 persona markdown files with full content (102/102/102/98/100/106 lines) + routine/persona_runner.py implementation + 6 additional coverage tests folded in (populated-snapshot, dark-position-signal, empty-snapshot-data, partial-fundamentals, python-exception-isolation, file-not-found). All 45 tests GREEN; 100% line / 100% branch coverage; full repo 549 passed.

## Files Created/Modified

- `routine/persona_runner.py` (created, 289 lines) — async fan-out across 6 personas; PERSONA_IDS tuple + 3 module constants + load_persona_prompt (lru_cache) + build_persona_user_context (deterministic) + 4 small private formatters (_summarize_snapshot, _format_signal, _format_position_signal, _format_config) + _persona_default_factory closure builder + async run_one + async run_persona_slate. Provenance docstring references virattt/ai-hedge-fund/src/agents/ + 4 modifications enumerated.
- `tests/routine/test_persona_runner.py` (created, 689 lines) — 45 tests (file presence + structure + voice keywords + Output Schema fields + claude_analyst novelty + PERSONA_IDS order + AnalystId subset + module constants + load_persona_prompt cache/invalid-id/file-not-found + user_context content/determinism/populated/dark/empty/partial + run_one happy/default_factory + run_persona_slate fan-out/single-failure/python-exception-isolation/wrong-signal-count + provenance).
- `prompts/personas/buffett.md` (modified, 102 lines) — long-term value, owner earnings, moat-first analysis, margin of safety, circle of competence, capital allocation discipline. Provenance ref to virattt/.../warren_buffett.py.
- `prompts/personas/munger.md` (modified, 102 lines) — multidisciplinary mental models, "invert always invert", lollapalooza effects, quality over price, brutal honesty about what you don't know. Provenance ref to virattt/.../charlie_munger.py.
- `prompts/personas/wood.md` (modified, 102 lines) — disruptive innovation, exponential not linear adoption, 5-year platform horizon, S-curve, TAM-driven, convergence of multiple platforms. Provenance ref to virattt/.../cathie_wood.py.
- `prompts/personas/burry.md` (modified, 98 lines) — macro contrarian, hidden-risk surfacing, asymmetric payoffs, short-bias when facts demand, deep balance-sheet skepticism. Provenance ref to virattt/.../michael_burry.py.
- `prompts/personas/lynch.md` (modified, 100 lines) — invest in what you know, PEG ratio, 10-bagger framework, GARP, six categories of stocks. Provenance ref to virattt/.../peter_lynch.py.
- `prompts/personas/claude_analyst.md` (modified, 106 lines) — explicit "NOT a persona, NOT a lens"; Claude's inherent reasoning surfaced; general financial knowledge beyond snapshot; comparable precedent; knowledge-cutoff acknowledgment. "novel-to-this-project" provenance (no virattt analog) per user MEMORY.md feedback.

## Decisions Made

- **PERSONA_IDS as immutable tuple, not list** — usable as dict key, hashable, canonical iteration order for asyncio.gather submission (gather preserves submission order in the result list, NOT completion order; this is verified by test_run_persona_slate_fan_out_order_preserved).
- **Single shared user_context per ticker** — `build_persona_user_context` builds once; all 6 persona calls receive the same user message. Per-persona variation lives entirely in the SYSTEM prompt (markdown). Saves 6x context-build cost; tested for byte-identical determinism.
- **Closure-bound default factory** — `_persona_default_factory(persona_id, ticker, computed_at)` returns a zero-arg `factory()` callable; call_with_retry invokes it on retry exhaustion, producing AgentSignal with the correct analyst_id + ticker + computed_at + canonical "schema_failure" evidence shape per LLM-05.
- **`asyncio.gather(return_exceptions=True)` outer defense** — beyond call_with_retry's per-LLM retry/default_factory, an UNCAUGHT Python-level exception in run_one (e.g., a bug in build_persona_user_context for one persona's input shape) collapses to default_factory at the outer layer. The synthesizer's compute_dissent always sees 6 AgentSignals, in canonical PERSONA_IDS order.
- **5-section persona-prompt structure (LLM-03 lock)** — H1 + Voice Signature + Input Context + Task + Output Schema. Voice Signature contains 3-5 persona-specific keyword anchors verified by parametrized tests (Buffett: owner earnings + moat + margin of safety; Munger: mental model + invert; Wood: disruptive innovation + exponential; Burry: contrarian; Lynch: PEG + 10-bagger; Claude: NOT a + Claude + inherent). The keyword presence test catches voice-drift across prompt edits.
- **claude_analyst.md framed as "NOT a persona"** — per user MEMORY.md feedback_claude_knowledge: "in agent systems, include an Open Claude Analyst alongside canonical personas — never let lenses replace inherent reasoning". The 5 reference personas constrain to lenses by design — that's their value. claude_analyst's value is the COMPLEMENTARY surface (training-data context, comparable precedent, knowledge-cutoff acknowledgment, what-the-personas-don't-say). Explicit "novel-to-this-project" provenance.
- **Defensive validation in run_persona_slate** — `len(analytical_signals) == 4` raises ValueError("expected 4 analytical_signals (fund/tech/nsen/val); got {N}") at function entry. Defensive against synthesizer-side ordering bugs; saves cryptic downstream IndexError.
- **`@functools.lru_cache(maxsize=8)` on load_persona_prompt** — 6 personas + headroom for test fixtures using non-canonical ids. Cache makes 6xN_TICKERS fan-out a single disk read per persona regardless of N_TICKERS. ValueError on unknown id is the defensive guard before disk hit.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Wrong FundamentalsSnapshot attribute names in `_summarize_snapshot`**
- **Found during:** Task 1 GREEN coverage push (after the 39-test happy path passed; the partial-fundamentals coverage test exposed it)
- **Issue:** The plan's implementation_sketch used `f.pe_ratio` / `f.return_on_equity` for the FundamentalsSnapshot fundamentals fields. The actual schema (analysts/data/fundamentals.py) uses `pe` / `roe` / `debt_to_equity`. This was dead code at runtime — would have raised AttributeError the first time Wave 5's entrypoint passed a populated (non-data_unavailable) snapshot to build_persona_user_context.
- **Fix:** Updated `_summarize_snapshot` to use the actual field names (`f.pe`, `f.roe`, `f.debt_to_equity`).
- **Files modified:** routine/persona_runner.py
- **Verification:** New test `test_build_user_context_with_populated_snapshot` asserts `"P/E=28.5"`, `"ROE=0.42"`, `"D/E=0.55"` surface in the user_context after the fix. Coverage on the previously-dead branch went from 0% to 100%.
- **Committed in:** `b205064` (Task 1 GREEN — same commit as the runner module since the bug was in the new file before any external consumer)

**2. [Rule 2 - Missing Critical] Added 6 coverage tests to clear the 90/85% gate**
- **Found during:** Task 1 GREEN coverage check (initial 39 tests gave 66% line / partial branch — well below the >=90/85 gate)
- **Issue:** The plan's 14-test floor (which expanded via parametrization to 39 instances) did NOT exercise: `_summarize_snapshot` populated-prices/populated-fundamentals branches; `_format_signal` empty-evidence and data_unavailable branches; `_format_position_signal` data_unavailable branch; `_format_config` thesis_price/notes branches; `_summarize_snapshot` partial-fundamentals (None values); `run_persona_slate` Python-level exception path (only LLM-failure path was tested); `load_persona_prompt` FileNotFoundError path.
- **Fix:** Added 6 coverage tests: `test_build_user_context_with_populated_snapshot`, `test_build_user_context_with_dark_position_signal`, `test_build_user_context_with_empty_snapshot_data`, `test_summarize_snapshot_partial_fundamentals`, `test_run_persona_slate_python_exception_isolated` (uses monkeypatch to inject a faulty run_one that raises RuntimeError for one persona), `test_load_persona_prompt_raises_file_not_found_when_file_missing` (uses monkeypatch to redirect PERSONA_PROMPT_DIR to an empty tmp dir).
- **Files modified:** tests/routine/test_persona_runner.py
- **Verification:** Coverage went from 66% combined -> 96% (after first 5 tests) -> 100% line / 100% branch (after the partial-fundamentals test landed the last 5 partial-branch cases).
- **Committed in:** `b205064` (Task 1 GREEN — folded into the same commit as the runner since the gate is plan-level)

---

**Total deviations:** 2 auto-fixed (1 Rule 1 bug — wrong attribute names; 1 Rule 2 missing critical — coverage gate).

**Impact on plan:** Both deviations are tightening, no scope creep. The Rule 1 fix prevents a runtime AttributeError when Wave 5 entrypoint passes populated snapshots; the Rule 2 fix clears the 90/85% coverage gate locked by the plan's verification block. Production module surface matches the locked sketch byte-for-byte (apart from the 2-character attribute-name fix). Test count grew from "≥14" to 45 — still focused on locked-surface invariants, no behavioral creep.

## Issues Encountered

- **One test failure on first GREEN run** — `test_provenance_header_references_virattt` failed because the docstring used brace-expansion notation (`{warren_buffett,charlie_munger,...}_agent.py`) rather than literal `warren_buffett.py`; the test grep was looking for the literal substrings. Fixed in-place by rewriting the docstring to spell out all 5 reference filenames literally. Test passed on retry; no separate commit (production-side docstring tweak inside the same GREEN commit).

## User Setup Required

None — no external service configuration. The 6 persona prompts are content drops; the runner module is consumed only by Wave 4 + Wave 5 (still pending). The Anthropic SDK + AsyncAnthropic + messages.parse(output_format=...) wiring all came from Wave 0 (05-01) + Wave 2 (05-03).

## Next Phase Readiness

**Wave 4 (05-05 synthesizer + dissent rule) UNBLOCKED.** The 6 AgentSignals returned by `run_persona_slate` are exactly the input shape the synthesizer's `compute_dissent` Python rule reads. Length is guaranteed exactly 6 (in PERSONA_IDS canonical order); per-persona shape is always AgentSignal (verdict + confidence + evidence + data_unavailable); per-persona LLM/Python failures collapse cleanly to default-factory (data_unavailable=True, verdict='neutral', confidence=0). The dissent rule can compute median verdict + check ≥30 confidence-point opposite-direction outliers without defensive checks.

**Wave 5 (05-06 routine entrypoint) UNBLOCKED.** `run_persona_slate(client, *, ticker, snapshot, config, analytical_signals, position_signal, computed_at)` is the per-ticker persona-call surface the routine's `_run_one_ticker` will call between analytical-signal scoring (Phase 3) and the synthesizer call (Wave 4). Async fan-out within ticker (~6x faster wall-clock); sync across tickers — Wave 5's run_for_watchlist enforces sync across the watchlist.

**No blockers** for Wave 4 / Wave 5. Phase 5 status: 4/6 plans complete (Wave 0 + Wave 1 + Wave 2 + Wave 3 done; Waves 4 + 5 pending).

## Self-Check: PASSED

- [x] routine/persona_runner.py exists (289 lines)
- [x] tests/routine/test_persona_runner.py exists (689 lines)
- [x] 6 persona markdown files all ≥80 lines (102/102/102/98/100/106)
- [x] Commit `ffb5132` (RED) exists in git log
- [x] Commit `b205064` (GREEN) exists in git log
- [x] 100% line / 100% branch coverage on routine/persona_runner.py
- [x] Full repo regression: 549 tests pass (504 baseline + 45 new)
- [x] Provenance grep passes (virattt for runner; novel-to-this-project for claude_analyst)

---
*Phase: 05-claude-routine-wiring*
*Completed: 2026-05-04*
