# Phase 5 Plan Check

**Verified:** 2026-05-03
**Verdict:** PASS (two minor advisories on verify-block hygiene; nothing blocks /gmd:execute-plan 05-01)

## Verdict Summary

All 6 plans verify against the 12-dimension goal-backward review the user asked for. Every Phase 5 requirement (LLM-01..08 + INFRA-01..04) is covered by at least one plan's `requirements` frontmatter; the dependency graph is acyclic and matches the user's stated wave layering exactly; TDD discipline (RED -> GREEN) is preserved across all 14 commits; coverage gates >=90% line / >=85% branch are specified on every new Python module; the Anthropic SDK call shape is `messages.parse(output_format=PydanticModel)` everywhere (NOT `messages.create`); the two-tier model split is locked (`claude-sonnet-4-6` for personas; `claude-opus-4-7` for synthesizer); async fan-out is `asyncio.gather` within a ticker with sync-across-tickers; the three-phase storage write order (per-ticker -> _index -> _status LAST) is specified and tested; Python-computed dissent runs BEFORE the synthesizer LLM call; the `AnalystId` Literal widening from 4 to 10 lives in 05-01; the `MARKETS_DAILY_QUOTA_TOKENS` env var trigger and lite-mode emit `lite_mode=true, partial=true` per spec; REQUIREMENTS.md + ROADMAP.md closeout is the explicit final commit of 05-06.

Two non-blocking quality issues at the verify-block layer (cosmetic; they don't change the contract):

1. **05-05 Task 1 verify block has a duplicate/unclosed automated tag** (lines 1570-1571). The first opens but is not closed; the second is valid and complete. Mechanical fix during execution.
2. **05-06 Task 3 verify uses an in-line for loop in `python -c`** which is not valid one-liner Python syntax. Convert to a list-comprehension `assert all(...)`. Mechanical fix during execution.

Neither issue blocks the plans. Issue list at the end of this document.

---

## Dimension 1 - Coverage Completeness

Every one of the 12 Phase 5 requirements is named in at least one plan's `requirements` frontmatter:

| Requirement | Plan(s) declaring it | Where it gets implemented | Test surface |
|---|---|---|---|
| LLM-01 (markdown personas in prompts/personas/) | 05-01, 05-04 | 05-01 ships 6 placeholder stubs; 05-04 fills with full content | `test_persona_file_exists_and_nonempty` (parametrized x 6) |
| LLM-02 (loaded at runtime, never hardcoded) | 05-01, 05-04 | 05-04 `load_persona_prompt` reads from disk via `Path.read_text` with `lru_cache` | `test_load_persona_prompt_reads_file`, `test_load_persona_prompt_caches_repeat_calls` |
| LLM-03 (voice signature anchor section) | 05-04 | Locked 5-section structure in each persona md; voice-signature anchors per persona | `test_persona_voice_signature_keywords` (parametrized x 6); `test_claude_analyst_explicitly_not_a_persona` |
| LLM-04 (Pydantic-validated AgentSignal output) | 05-03, 05-04 | 05-03 `call_with_retry` wraps `messages.parse(output_format=AgentSignal)`; 05-04 `run_one`/`run_persona_slate` invoke it | `test_run_one_happy_path` (asserts `output_format=AgentSignal` in mock kwargs) |
| LLM-05 (default_factory + memory/llm_failures.jsonl) | 05-03 | `_log_failure` writes append-only JSONL; `default_factory` returned on retry exhaustion | `test_validation_error_exhaustion_returns_default_factory`; `test_failure_log_record_shape`; `test_failure_log_append_only_across_invocations` |
| LLM-06 (synthesizer + TickerDecision) | 05-02, 05-05 | 05-02 ships TickerDecision schema; 05-05 ships `synthesize` orchestrator | `tests/synthesis/test_decision.py` (>=18 tests); `test_synthesize_happy_path_returns_llm_decision` + 6 parametrized recommendation paths |
| LLM-07 (always-rendered Dissent section) | 05-05 | `synthesis/decision.DissentSection` always present; `synthesis/dissent.compute_dissent` Python-computed BEFORE the LLM call | `tests/synthesis/test_dissent.py` (>=12 tests covering 3 main scenarios + 9 edge/tie-break cases) |
| LLM-08 (_status.json schema) | 05-06 | `routine/storage.write_daily_snapshot` Phase C writes `_status.json` last | `test_status_json_schema_success` + `test_status_json_failed_tickers_populated_on_OSError` + `test_llm_failure_count_*` |
| INFRA-01 (scheduled routine; subscription auth) | 05-06 | `routine/entrypoint.main` is the single CLI entry; `AsyncAnthropic` constructed without API key (subscription auth) | `test_main_5_ticker_happy_path` |
| INFRA-02 (lite mode if estimate > quota) | 05-06 | `routine/quota.estimate_run_cost` + `MARKETS_DAILY_QUOTA_TOKENS` env var + `lite_mode` plumbed through `run_for_watchlist` + `synthesize` skip path | `test_main_lite_mode_path` (35-ticker forces lite_mode=True) |
| INFRA-03 (daily snapshots; per-ticker JSONs + _index) | 05-06 | Three-phase write Phase A + Phase B; deterministic `data/{date}/` folder | `test_three_phase_write_order` + `test_index_json_schema` + integration test |
| INFRA-04 (git commit + push from routine) | 05-06 | `routine/git_publish.commit_and_push` 5-step sequence | `tests/routine/test_git_publish.py` (>=6 tests) |

**Coverage Summary:** 12/12 requirements covered. Zero gaps. All 12 requirements appear in the union of `requirements:` frontmatter fields across the 6 plans. The closeout step in 05-06 Task 3 explicitly enumerates the 12 entries to flip to `[x]` in REQUIREMENTS.md and updates the traceability table at lines 178-185 (LLM-XX) and 208-211 (INFRA-XX).

**Project-level cross-check (PROJECT.md):** No PROJECT.md requirement that the ROADMAP.md maps to Phase 5 is silently dropped. INFRA-05 (Vercel) is Phase 6 (correctly excluded). INFRA-06 (memory log) is Phase 8 per CONTEXT.md reconciliation note (correctly deferred). INFRA-07 (provenance) is Phase 8 per ROADMAP.md but every plan still includes provenance-grep tests at the module level - defensively forward-compatible.

---

## Dimension 2 - Dependency Graph Soundness

```
05-01 (Wave 0, depends_on: [])
   |--> 05-02 (Wave 1, depends_on: [05-01])
   |--> 05-03 (Wave 2, depends_on: [05-01])
   |       |
   |       |--> 05-04 (Wave 3, depends_on: [05-02, 05-03])
   |       |
   |       |--> 05-05 (Wave 4, depends_on: [05-02, 05-03, 05-04])
   |
   |--> 05-06 (Wave 5, depends_on: [05-01, 05-02, 05-03, 05-04, 05-05])
```

| Plan | wave | depends_on | Match user spec? | Notes |
|------|------|-----------|-----------------|-------|
| 05-01 | 0 | `[]` | YES | No Phase 5 deps. Foundation. |
| 05-02 | 1 | `[05-01]` | YES | Schema lands as soon as the package scaffold + AnalystId widening is in. |
| 05-03 | 2 | `[05-01]` | YES | LLM client only needs the SDK install + the package scaffold; doesn't need TickerDecision schema. 05-03 in Wave 2 is independent of 05-02 in Wave 1. |
| 05-04 | 3 | `[05-02, 05-03]` | YES | Persona runner needs `call_with_retry` (Wave 2) AND TickerDecision-adjacent imports for tests; both deps real. |
| 05-05 | 4 | `[05-02, 05-03, 05-04]` | YES | Synthesizer imports TickerDecision (05-02), `call_with_retry` (05-03), and `PERSONA_IDS` for compute_dissent input shape (05-04). |
| 05-06 | 5 | `[05-01, 05-02, 05-03, 05-04, 05-05]` | YES | Entrypoint imports all five upstream surfaces. The 05-01 reference is technically transitive but explicit-is-fine. |

No cycles, no forward references, no missing references. Wave numbering = max(deps_wave) + 1 is consistent for every plan. **Dependency graph is sound.**

---

## Dimension 3 - TDD Discipline

| Plan | Task | RED commit | GREEN commit | Status |
|------|------|-----------|--------------|--------|
| 05-01 | Task 1 | test(05-01): add failing tests for widened AnalystId Literal | feat(05-01): widen AnalystId Literal to 10 IDs | OK |
| 05-01 | Task 2 | test(05-01): add failing smoke test for anthropic SDK | feat(05-01): scaffold routine/ + synthesis/ packages; drop 7 markdown stubs | OK |
| 05-02 | Task 1 | test(05-02): add failing tests for TickerDecision + TimeframeBand + DissentSection schemas | feat(05-02): TickerDecision + DissentSection + TimeframeBand schemas | OK |
| 05-03 | Task 1 | test(05-03): add failing tests for routine.llm_client.call_with_retry | feat(05-03): routine.llm_client.call_with_retry | OK |
| 05-04 | Task 1 | test(05-04): add failing tests for routine.persona_runner + 6 persona prompt content | feat(05-04): 6 persona markdown prompts + routine/persona_runner.py async fan-out | OK |
| 05-05 | Task 1 | test(05-05): add failing tests for synthesis.dissent.compute_dissent | feat(05-05): synthesis.dissent.compute_dissent | OK |
| 05-05 | Task 2 | test(05-05): add failing tests for synthesis.synthesizer + prompts/synthesizer.md content | feat(05-05): synthesis.synthesizer.synthesize + prompts/synthesizer.md | OK |
| 05-06 | Task 1 | test(05-06): add failing tests for routine.{quota, storage, git_publish} | feat(05-06): routine.{quota, storage, git_publish} | OK |
| 05-06 | Task 2 | test(05-06): add failing tests for routine.run_for_watchlist | feat(05-06): routine.run_for_watchlist | OK |
| 05-06 | Task 3 | test(05-06): add failing end-to-end integration tests for routine.entrypoint | feat(05-06): routine.entrypoint.main + docs(05-06): close Phase 5 (closeout commit) | OK |

**Total: 14 commits across 10 tasks** (10 RED + 10 GREEN, with 05-06 Task 3 splitting GREEN into entrypoint + closeout-docs for separation of concerns). Every action block names the explicit Run pytest -> ImportError or >=1 test fails RED step before each RED commit. **TDD discipline preserved.**

Special note on 05-04: the persona markdown content tests (file presence + section structure + voice-signature keywords) are pure-content tests with no Python-module dependency. The plan correctly notes that the RED phase will see partial pass (Wave 0 stub files exist but are <80 lines, so length-tests fail) + ImportError on `routine.persona_runner` for the runtime tests. Both failure modes are RED-valid.

---

## Dimension 4 - Coverage Gates

Every new Python module specifies >=90% line / >=85% branch coverage:

| Module | Plan | Coverage gate explicit in must_haves.truths | Gate verified in verify automated block |
|--------|------|---|---|
| analysts/signals.py (extension) | 05-01 | YES (>=90/85; already at 100% from Phase 3) | YES |
| synthesis/decision.py | 05-02 | YES | YES |
| routine/llm_client.py | 05-03 | YES | YES |
| routine/persona_runner.py | 05-04 | YES | YES |
| synthesis/dissent.py | 05-05 Task 1 | YES | YES |
| synthesis/synthesizer.py | 05-05 Task 2 | YES | YES |
| routine/quota.py | 05-06 Task 1 | YES | YES |
| routine/storage.py | 05-06 Task 1 | YES | YES |
| routine/git_publish.py | 05-06 Task 1 | YES | YES |
| routine/run_for_watchlist.py | 05-06 Task 2 | YES | YES |
| routine/entrypoint.py | 05-06 Task 3 | YES | YES |

Pyproject `[tool.coverage.run].source` extended in 05-01 Task 1 to include `routine` and `synthesis`. **Coverage discipline is end-to-end.**

---

## Dimension 5 - Anthropic SDK Call Shape

The user lock: `client.messages.parse(output_format=PydanticModel)` (NOT `messages.create()`).

| Plan | Where messages.parse is invoked | Verified? |
|------|--------------------------------|-----------|
| 05-01 Task 2 | Smoke test asserts `hasattr(client.messages, "parse")` (regression guard) | YES |
| 05-03 | `routine/llm_client.call_with_retry` body: `await client.messages.parse(model=..., system=..., messages=[...], output_format=output_format)` (line 334 of plan) | YES |
| 05-04 | `routine/persona_runner.run_one` invokes `call_with_retry(...)`; test asserts `calls[0]["output_format"] is AgentSignal` | YES (transitively) |
| 05-05 | `synthesis/synthesizer.synthesize` invokes `call_with_retry(...)`; test asserts `calls[0]["output_format"] is TickerDecision` | YES (transitively) |

**Zero occurrences of `messages.create(`** in any plan body - grep confirms only `.parse` is used. Plan 05-03 also adds an AST-grep test (`test_no_temperature_top_p_top_k_in_call_site`) defending against Opus 4.7 BREAKING CHANGE per Pattern #2 + CORRECTION #2 in 05-RESEARCH.md.

---

## Dimension 6 - Two-Tier Model Split

The user lock: Sonnet 4.6 for personas, Opus 4.7 for synthesizer.

| Plan | Constant | Value | Used by |
|------|----------|-------|---------|
| 05-04 | `PERSONA_MODEL` | `claude-sonnet-4-6` | `run_one(..., model=PERSONA_MODEL, ...)` |
| 05-05 | `SYNTHESIZER_MODEL` | `claude-opus-4-7` | `synthesize(...)` calls `call_with_retry(model=SYNTHESIZER_MODEL, ...)` |

Both values are also asserted in tests:

- `test_run_one_happy_path` - asserts `calls[0]["model"] == PERSONA_MODEL`
- `test_synthesize_happy_path_returns_llm_decision` - asserts `calls[0]["model"] == SYNTHESIZER_MODEL`

`max_tokens` also tiered correctly: persona = 2000; synthesizer = 4000. **Model split is locked at the constant + test layer.**

---

## Dimension 7 - Async Fan-Out

The user lock: `asyncio.gather` for the 6 personas WITHIN a ticker; sync across tickers (subscription single-bucket).

**Within-ticker fan-out (05-04):**

- `routine/persona_runner.run_persona_slate` line 1163: `raw_results = await asyncio.gather(*coros, return_exceptions=True)` where coros = [run_one(client, pid, ...) for pid in PERSONA_IDS].
- `return_exceptions=True` is the OUTER failure-isolation defense (Pattern #3). Per-LLM-failure isolation is INNER (the `call_with_retry` default_factory). Two-layer cascade prevention.
- Test `test_run_persona_slate_fan_out_order_preserved` asserts `len(set(systems)) == 6` (6 distinct system prompts in the mock calls list) and that the result list ordering matches `PERSONA_IDS` byte-for-byte.
- Test `test_run_persona_slate_single_failure_isolation` queues 5 successes + 2 ValidationErrors for one persona and asserts the other 5 are unaffected.

**Across-ticker sync (05-06):**

- `routine/run_for_watchlist.run_for_watchlist` body: `for ticker_config in watchlist.tickers:` - explicit Python for loop, sequential awaits.
- Plan docstring + Pattern #3 reference both name the rationale: subscription quota is single-bucket; 30 tickers x 7 LLM calls in parallel would 429 immediately.
- Test `test_sync_across_tickers_order_preserved` asserts result list ordering matches input order.

**Async + sync correctly separated.**

---

## Dimension 8 - Three-Phase Storage Write Order

The user lock: per-ticker JSONs first -> `_index.json` -> `_status.json` LAST. Per-ticker failures don't abort the run (collected into failed_tickers).

**Plan 05-06 storage.py implementation (lines 444-501):**

- Phase A loop: iterates over `results`; per-ticker `try/except OSError` to populate `failed.append(r.ticker)` without aborting; the loop continues.
- Phase B: `_atomic_write_json(folder / "_index.json", {...})` - only `completed` tickers listed (failed_tickers excluded from `_index.tickers`).
- Phase C: `_atomic_write_json(folder / "_status.json", {success: not failed, partial: lite_mode or bool(failed), completed_tickers, failed_tickers, skipped_tickers, llm_failure_count, lite_mode})` - written LAST as the run-final sentinel.

**Tests in tests/routine/test_storage.py:**

- `test_three_phase_write_order` - monkeypatches `_atomic_write_json`; asserts call-sequence order is `[ticker1.json, ticker2.json, ticker3.json, _index.json, _status.json]`.
- `test_status_json_failed_tickers_populated_on_OSError` - monkeypatches `_atomic_write_json` to raise OSError on the 2nd ticker only; verifies first ticker still successfully written + 2nd appended to failed_tickers + 3rd successfully written. Status reflects `success=False, partial=True, failed_tickers=[<2nd>]`.

**Three-phase order + cascade-prevention is locked at code + test layer.**

---

## Dimension 9 - Dissent Computation in Python (Before Synthesizer LLM Call)

The user lock: `synthesis/dissent.py` Python-computed BEFORE the synthesizer LLM call; the dissent string is then passed to the synthesizer prompt. NOT LLM-computed.

**Plan 05-05 architecture:**

- `synthesis/dissent.compute_dissent(persona_signals)` - pure Python; signed-weighted-vote majority direction; opposite-direction->=30-confidence trigger; tie-break by confidence-then-alphabetical-analyst_id.
- `synthesis/synthesizer.synthesize` body (line 828): `dissent_id, dissent_summary = compute_dissent(persona_signals)` is called BEFORE `load_synthesizer_prompt()` and BEFORE `call_with_retry(...)`. The pre-computed dissent is then passed to `build_synthesizer_user_context(...)` as the `dissent_persona_id` + `dissent_summary` kwargs (line 838-839).
- `prompts/synthesizer.md` (line 419+ of plan) explicitly instructs the LLM to RENDER the pre-computed dissent verbatim into `TickerDecision.dissent`, NOT to compute dissent itself.

**Tests in tests/synthesis/test_synthesizer.py:**

- `test_synthesize_dissent_pre_computed_in_user_context` - constructs a 5-bullish + 1-burry-bearish-conf-80 persona slate; calls `synthesize()`; reads `mock_anthropic_client.messages.calls[0]["user"]`; asserts the user message contains "burry" + "dissents" + "hidden risk" - which is the canonical Python-computed dissent summary, NOT something the LLM could have plausibly synthesized given that this is a mock.

The architecture is exactly as the user locked: Python computes dissent -> passes pre-computed string -> LLM renders it verbatim. **Locked at code + prompt + test layer.**

The plan also encodes the rationale in the `synthesis/dissent.py` provenance docstring (3 reasons: determinism, no hallucination risk, tie-break specificity) and references the 05-RESEARCH.md Anti-Pattern at line 1189 (signed-weighted-vote majority direction NOT mode-based majority).

---

## Dimension 10 - AnalystId Widening (4 -> 10)

The user lock: 05-01 should widen the `AnalystId` Literal in `analysts/signals.py` from 4 to 10 values.

**Plan 05-01 Task 1 body (lines 437-481):**

- `pyproject.toml` gets 3 surgical edits (anthropic dep + coverage source + wheel packages extension).
- `analysts/signals.py` line 41 gets a single-line replacement: `AnalystId = Literal["fundamentals", ...]` -> 13-line multi-line Literal with 4 analytical + 6 persona IDs in the canonical iteration order (`fundamentals, technicals, news_sentiment, valuation, buffett, munger, wood, burry, lynch, claude_analyst`).
- 3 new tests appended to `tests/analysts/test_signals.py`:
  - `test_analyst_id_widened_to_10` - parametrized over the 10 IDs; each constructs cleanly.
  - `test_analyst_id_rejects_invalid` - `not_a_persona` raises ValidationError.
  - `test_analyst_id_literal_arity_is_10` - `len(get_args(AnalystId)) == 10` + set equality against the 10 IDs.

**Phase 1-4 regression invariant locked:** "All 428+ existing tests stay GREEN after the AnalystId widening". The widening is a strict superset; no existing analyst constructs an AgentSignal with one of the 6 persona IDs; backwards-compatible by construction.

**The widening lock is correct.**

---

## Dimension 11 - Lite Mode (MARKETS_DAILY_QUOTA_TOKENS Trigger + lite_mode=true, partial=true)

The user lock: env var `MARKETS_DAILY_QUOTA_TOKENS` triggers lite mode; lite mode skips personas + synthesizer; emits `lite_mode=true, partial=true` in `_status.json`.

**Plan 05-06 implementation:**

- `routine/quota.estimate_run_cost(watchlist) -> int` - formula `n_tickers * (N_PERSONAS * (PERSONA_INPUT + PERSONA_OUTPUT) + SYNTHESIZER_INPUT + SYNTHESIZER_OUTPUT) = n_tickers * 19_800`.
- `DEFAULT_MARKETS_DAILY_QUOTA_TOKENS = 600_000`.
- `routine/entrypoint.main` reads `quota = int(os.environ.get("MARKETS_DAILY_QUOTA_TOKENS", str(DEFAULT_MARKETS_DAILY_QUOTA_TOKENS)))` and computes `lite_mode = (estimated > quota)` (line 821).
- `routine/run_for_watchlist._run_one_ticker` checks `if lite_mode:` and returns a TickerResult with `persona_signals=[]` + `ticker_decision=None` WITHOUT awaiting `run_persona_slate` or `synthesize` (lines 674-682).
- `synthesis/synthesizer.synthesize` has a dual lite-mode guard: when `not persona_signals:` it returns `_data_unavailable_decision(reason="lite_mode (no persona signals)")` WITHOUT calling the LLM (line 823). Defensive against the entrypoint forgetting to pass lite_mode.
- `routine/storage.write_daily_snapshot` Phase C writes `_status.json` with `lite_mode: lite_mode` and `partial: lite_mode or bool(failed)` (line 491).

**Tests:**

- `test_31_ticker_estimate_exceeds_default_quota` - 31-ticker watchlist -> 613_800 > 600_000 -> lite_mode triggered.
- `test_lite_mode_skips_persona_and_synthesizer` - `lite_mode=True`; result has empty persona_signals + None ticker_decision; mock client called ZERO times.
- `test_main_lite_mode_path` - 35-ticker watchlist forces estimate > quota; per-ticker JSONs have `persona_signals=[]` and `ticker_decision=null`; `_status.json.lite_mode=True, partial=True`.

**Lite mode is locked end-to-end.**

---

## Dimension 12 - REQUIREMENTS / ROADMAP Closeout

The user lock: 05-06 should flip LLM-01..08 + INFRA-01..04 to `[x]` in REQUIREMENTS.md and Phase 5 row to Complete in ROADMAP.md.

**Plan 05-06 Task 3 closeout step (lines 1056-1071):**

- Step 10: Edit `.planning/REQUIREMENTS.md`:
  - Flip 8 LLM checkbox lines (REQUIREMENTS.md lines 46-53) from `- [ ]` -> `- [x]`.
  - Flip 4 INFRA checkbox lines (REQUIREMENTS.md lines 88-91) from `- [ ]` -> `- [x]`.
  - Update traceability table rows for the 12 entries (REQUIREMENTS.md lines 178-185 LLM + 208-211 INFRA) from Pending -> Complete.
  - Update "Last updated" timestamp.
- Step 11: Edit `.planning/ROADMAP.md`:
  - Phase 5 row in the Phase Summary table (ROADMAP.md line 16) -> Complete.
  - Phase 5 detail block plan list populated with 6 `[x]` entries naming the 6 plan files.
- Step 13: Final commit `docs(05-06): close Phase 5 - flip LLM-01..08 + INFRA-01..04 to Complete in REQUIREMENTS.md; flip Phase 5 row to Complete in ROADMAP.md; populate plan list`.

**Verified line numbers** in REQUIREMENTS.md and ROADMAP.md match. The traceability table layout is exactly:

- LLM-01..08 rows at lines 178-185 (verified via grep).
- INFRA-01..04 rows at lines 208-211 (verified via grep).

**Closeout is well-specified, traceable, and consolidated to a single commit.**

---

## Strengths

- **Foundation-first wave layering.** 05-01 lands all the SDK + scaffolding + AnalystId widening in ONE plan so subsequent waves can be content-only. This avoids the common anti-pattern of re-installing or re-scaffolding inside each wave plan.
- **Two-layer cascade prevention is explicit.** Inner: `call_with_retry` default_factory absorbs LLM-level failures (ValidationError / APIStatusError / APIError / unknown). Outer: `asyncio.gather(return_exceptions=True)` absorbs Python-level failures. Outer-outer: `routine/run_for_watchlist` per-ticker try/except absorbs whole-pipeline failures. Outer-outer-outer: `routine/entrypoint.main()` top-level except + best-effort `write_failure_status`. Four layers of defense-in-depth, all named in plans.
- **Provenance per INFRA-07 is uniform.** Every new module ships with a docstring referencing the virattt or TauricResearch source file (or "novel-to-this-project" for `claude_analyst.md` + `routine/entrypoint.py` + `routine/quota.py` + `routine/git_publish.py`). Each plan verify block has a grep gate on the literal substring.
- **The Python-computed dissent is the strongest design call.** Pattern #7 from 05-RESEARCH.md (line 1189) is the locked rationale: determinism + no hallucination risk + tie-break specificity. The plan operationalizes this as a 3-rule `compute_dissent` Python function with 12+ tests covering 3 main scenarios + 9 edge/tie-break cases.
- **Three-phase storage write is locked at the test layer.** `test_three_phase_write_order` monkeypatches `_atomic_write_json` and asserts call-sequence order - not just call count. This catches a future refactor that accidentally interleaves the writes.
- **The claude_analyst.md persona embodies user MEMORY.md feedback_claude_knowledge.** Voice signature explicitly says "NOT a persona, NOT a lens - Claude's inherent reasoning surfaced." The test `test_claude_analyst_explicitly_not_a_persona` enforces this. Faithful to the user's stated preference.
- **5-step git sequence with `pull --rebase --autostash` BEFORE add/commit/push.** Pattern #11 anti-pattern lock against `git add -A` enforced via AST-grep test. Race-condition guard for the manual-vs-scheduled-run scenario is explicit.
- **TickerDecision schema invariant via @model_validator.** `data_unavailable=True ==> recommendation="hold" AND conviction="low"` matches Phase 3 AgentSignal + Phase 4 PositionSignal precedent. Closes Pitfall #4-class drift.

## Issues Found

### Issue 1 (advisory, non-blocking) - 05-05 Task 1 verify-block has a duplicate/unclosed automated tag

**Location:** `.planning/phases/05-claude-routine-wiring/05-05-synthesizer-PLAN.md` lines 1570-1571.

**Symptom:** The first `<automated>` tag at line 1570 opens but never closes; the second at line 1571 is well-formed. Most XML/markup parsers will tolerate this (taking the second one) but a strict parser will fail.

**Fix:** Delete line 1570 entirely. Keep line 1571.

**Severity:** advisory.

### Issue 2 (advisory, non-blocking) - 05-06 Task 3 verify-block uses an in-line for loop in `python -c`

**Location:** `.planning/phases/05-claude-routine-wiring/05-06-routine-entrypoint-PLAN.md` line 1074.

**Symptom:** the Python one-liner contains `... for n in needed: assert ...`. A `for` loop cannot be used as a single statement after a colon in `python -c`. The interpreter expects either a generator expression or a list comprehension. This will raise SyntaxError.

**Fix:** rewrite using `assert all(... for n in needed)` generator-expression form. Mechanical fix during execution.

**Severity:** advisory.

### Confirming non-issues

- **No scope creep from deferred ideas.** None of CONTEXT.md's deferred items (memory layer, mid-day refresh, persona signal trend view, GPT/Gemini fallback, user-configurable persona slate, synthesizer reflection loop, per-persona token budget, streaming output, retry-with-backoff for 429/503) appear in any plan body or task action. Clean scope discipline.
- **No contradictions with locked CONTEXT.md decisions.** TickerDecision schema (10 fields), 6-state DecisionRecommendation, 3-state ConvictionBand, dual-timeframe TimeframeBand, always-present DissentSection, the 6-persona slate (with claude_analyst as the explicit "NOT a persona" surface), the synthesizer prompt structure, the lite-mode threshold - all match CONTEXT.md letter-for-letter.
- **Phase 5 ROADMAP.md success-criteria reconciliation note is honored.** CONTEXT.md flagged that ROADMAP.md says "Memory log + reflection" but REQUIREMENTS.md puts INFRA-06 in Phase 8. The plans correctly stop at writing the daily snapshot folder + commit + push; the historical-signals memory log is NOT mentioned in any plan. Phase 5 boundary preserved.

## Recommendation

**PASS - proceed to /gmd:execute-plan 05-01.**

The 6 plans cover LLM-01..08 + INFRA-01..04 with ~115 net-new tests across 14 commits, >=90/85 coverage gates on all 11 new/extended Python modules, full Phase 1-4 regression invariant on the AnalystId widening, INFRA-07 provenance per module, end-to-end integration tests on the entrypoint with mocked Anthropic + mocked git, and an explicit REQUIREMENTS.md / ROADMAP.md closeout in 05-06 Task 3. TDD discipline (RED -> GREEN) preserved across every commit. Dependency graph acyclic and correctly waved. Anthropic SDK call shape, two-tier model split, async-within / sync-across, three-phase storage write, Python-computed dissent, AnalystId widening, lite-mode trigger, and closeout flips are all locked at the code + test + verify-block layer.

Issues 1 and 2 are verify-block hygiene polish - execution can proceed; the executor mechanically fixes both during the relevant Task. Neither changes the contract or the artifact.

---

*Phase: 05-claude-routine-wiring*
*Plan-checked: 2026-05-03*
