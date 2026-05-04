---
phase: 05-claude-routine-wiring
plan: 03
subsystem: llm-client
tags: [phase-5, llm-client, anthropic-sdk, retry, default-factory, mock-fixture, tdd, wave-2, llm-04, llm-05]

# Dependency graph
requires:
  - phase: 05-claude-routine-wiring
    provides: "Plan 05-01 — anthropic SDK installed (>=0.95,<1) + AnalystId Literal widened to 10 IDs + 4 package markers (routine/, synthesis/, tests/routine/, tests/synthesis/) + tests/routine/conftest.py placeholder"
  - phase: 03-analytical-agents-deterministic-scoring
    provides: AgentSignal Pydantic v2 model — used as the canonical T payload for the generic call_with_retry wrapper in test fixtures
  - phase: 05-claude-routine-wiring
    provides: "Plan 05-02 — TickerDecision Pydantic v2 model — second canonical T payload (Wave 4 will pass output_format=TickerDecision to call_with_retry)"
provides:
  - "routine/llm_client.py — call_with_retry() async function generic over T bound=BaseModel; wraps client.messages.parse(output_format=PydanticModel) per 05-RESEARCH.md Pattern #2"
  - "Retry policy: DEFAULT_MAX_RETRIES=2 (cost-predictable per Pattern #8); 4 exception-path branches (ValidationError / APIStatusError / APIError / bare Exception → 'unknown_error')"
  - "Failure log: append-only JSONL at memory/llm_failures.jsonl; record fields {timestamp (ISO-8601 UTC), label, kind, message ≤1000 chars, raw ≤5000 chars or null}; sort_keys=True serialization (Phase 1/2 atomic-write discipline); mkdir(parents=True, exist_ok=True) so first call bootstraps memory/"
  - "Module constants: LLM_FAILURE_LOG (Path), DEFAULT_MAX_RETRIES (int=2)"
  - "Helpers: _try_extract_raw (best-effort raw extraction from ValidationError.errors()[0]['input']; defensive None on any failure) + _log_failure (writes one JSONL record)"
  - "Default-factory contract (LLM-05): on retry exhaustion, default_factory() is invoked exactly ONCE; its return value is propagated as the function return"
  - "Opus 4.7 BREAKING CHANGE adherence: NEVER passes temperature/top_p/top_k to messages.parse() (AST-grep test locks this)"
  - "tests/routine/conftest.py — MockAnthropicClient + MockMessages (fixture-replay pattern: queue_response / queue_exception → .calls list records every kwargs dict for assertions); mock_anthropic_client per-test fixture; isolated_failure_log autouse fixture (monkeypatches LLM_FAILURE_LOG → tmp_path so tests never pollute real memory/)"
  - "Provenance per INFRA-07: routine/llm_client.py docstring references virattt/ai-hedge-fund/src/utils/llm.py with 4 modifications enumerated (Anthropic SDK native vs LangChain abstraction; Pydantic-direct return vs JSON-extraction-with-fallback; async vs sync; single-vendor Claude only)"
affects: [05-04-personas, 05-05-synthesizer, 05-06-routine-entrypoint, phase-6-frontend, phase-8-mid-day-refresh]

# Tech tracking
tech-stack:
  added:
    - "pytest-asyncio>=0.23 (dev dep) — required for async test functions; configured asyncio_mode='auto' so @pytest.mark.asyncio decoration is implicit"
  patterns:
    - "Generic-over-T retry wrapper (TypeVar T bound=BaseModel) — single call_with_retry function services BOTH Wave 3 (output_format=AgentSignal) AND Wave 4 (output_format=TickerDecision) without code duplication"
    - "Fixture-replay mock pattern — tests register canned responses/exceptions ahead of the call; mock pops them in queue order; .calls list records kwargs for downstream assertions. Avoids brittle MagicMock-spy chains; gives tests a specification feel"
    - "Append-only JSONL failure log — sort_keys=True serialization + UTC timestamps + LF line endings + mkdir(parents=True) on first write; mirrors Phase 1/2 atomic-write discipline at the per-record level"
    - "isolated_failure_log autouse fixture — monkeypatches the module-level LLM_FAILURE_LOG constant to tmp_path; per-test isolation without filesystem cleanup ceremony; works for downstream Wave 3-5 tests that exercise call_with_retry through their runners"
    - "Defensive cascade prevention — bare `except Exception` in the retry loop (with kind='unknown_error' log) ensures an unexpected upstream exception (e.g. an SDK refactor that introduces a new exception type) cannot crash the per-ticker pipeline; the routine continues with default_factory()"

key-files:
  created:
    - "routine/llm_client.py — 193 LOC (provenance docstring + 4 module constants + TypeVar + call_with_retry async function + _try_extract_raw + _log_failure helpers)"
    - "tests/routine/test_llm_client.py — 17 tests covering happy path + 4 exception paths + retry-then-success + retry exhaustion + append-only contract + record shape (5 keys / UTC / sort_keys) + mkdir parents + truncation (direct unit tests on _log_failure) + raw=null on api_error + AST-grep no temp/top_p/top_k + INFRA-07 provenance + module constants + 2 defensive paths on _try_extract_raw"
  modified:
    - "tests/routine/conftest.py — replaced Wave 0 placeholder with MockAnthropicClient + MockMessages classes + mock_anthropic_client per-test fixture + isolated_failure_log autouse fixture"
    - "pyproject.toml — added pytest-asyncio>=0.23 to [dependency-groups].dev + asyncio_mode='auto' to [tool.pytest.ini_options]"

key-decisions:
  - "DEFAULT_MAX_RETRIES=2 (NOT 3) per Pattern #8 — keeps cost predictable; v1.x may add tenacity-backed exponential backoff for 429s but v1 ships flat retries"
  - "TypeVar T bound=BaseModel makes call_with_retry generic over the output_format parameter — single function services Wave 3 (AgentSignal payload) + Wave 4 (TickerDecision payload) without duplication. The Pydantic-validated return type is preserved at the type-checker level."
  - "Defensive `except Exception` (in addition to ValidationError + APIStatusError + APIError) — kind='unknown_error' branch — never let an unexpected exception propagate out of call_with_retry; the per-ticker pipeline must continue. AST-flake8 BLE001 silenced with explicit noqa + comment."
  - "Failure log truncation at the helper layer (1000 chars message / 5000 chars raw) — defensive against log file blowup if the SDK emits a multi-MB structured error. Direct unit tests on _log_failure exercise both caps."
  - "Sort_keys=True + UTC timestamp + LF line endings on each JSONL record — same byte-stable serialization discipline as Phase 1/2 atomic writes. Tests assert that re-serializing each record with sort_keys produces the on-disk byte sequence verbatim."
  - "Truncation tests target _log_failure DIRECTLY (not via call_with_retry) — Pydantic v2's ValidationError cannot be cleanly subclassed (its __new__ requires title + line_errors), and a real ValidationError's str() is auto-truncated at ~50 chars by Pydantic before reaching the wrapper. Direct unit tests on the helper are higher-fidelity than fighting Pydantic's exception machinery."
  - "_try_extract_raw is best-effort — uses exc.errors()[0]['input'] when available; broad Exception catch returns None on any extraction failure. Two dedicated tests lock the defensive paths (empty errors list + errors() raising)."
  - "isolated_failure_log fixture is autouse on tests/routine/* — every test in this directory automatically gets a tmp_path-backed log without explicit fixture declaration. Wave 3-5 tests benefit transparently."
  - "MockAnthropicClient is reusable by Wave 3-5 — populated here in Wave 2 to avoid duplication across tests/routine/test_persona_runner.py + test_synthesizer_runner.py + test_entrypoint.py."
  - "pytest-asyncio asyncio_mode='auto' — async test functions don't need @pytest.mark.asyncio decoration individually; the plugin discovers async test names and applies the marker. Cleaner test bodies."

patterns-established:
  - "Single LLM-IO boundary at routine/llm_client.py — Wave 3 (persona runner) + Wave 4 (synthesizer runner) + Wave 5 (entrypoint integration) ALL flow through call_with_retry; tests at every layer mock at exactly ONE point (AsyncAnthropic.messages.parse) via the mock_anthropic_client fixture"
  - "Fixture-replay over MagicMock-spy — tests register payloads with queue_response(parsed_output) / queue_exception(exc); mock yields them in order; .calls list captures every kwargs dict for assertions"
  - "Append-only JSONL discipline at the helper layer — _log_failure is the single write point for memory/llm_failures.jsonl; future debugging pipelines (e.g. Phase 8 telemetry surface) can grep this file without coordination"

requirements-completed:
  - LLM-04
  - LLM-05

# Metrics
duration: ~30 min
completed: 2026-05-04
---

# Phase 05 Plan 03: routine.llm_client (LLM-04 + LLM-05) Summary

**`routine/llm_client.py` (193 LOC) ships the thin Anthropic SDK wrapper at the project's single LLM-I/O boundary: `call_with_retry()` is async + generic over `T bound=BaseModel`, wraps `client.messages.parse(output_format=PydanticModel)` per Pattern #2, retries up to `DEFAULT_MAX_RETRIES=2` across 4 exception-path branches (ValidationError → log raw + retry; APIStatusError | APIError → log + retry; bare Exception → kind='unknown_error' defensive catch; all paths return `default_factory()` on exhaustion per LLM-05). Failure records append-only at `memory/llm_failures.jsonl` with sort_keys serialization + UTC timestamps + 1000-char message cap + 5000-char raw cap. NEVER passes temperature/top_p/top_k (Opus 4.7 400-rejection guard per Pattern #2; AST-grep test locks this). `tests/routine/conftest.py` populated with the `MockAnthropicClient` fixture-replay implementation + `mock_anthropic_client` per-test fixture + `isolated_failure_log` autouse fixture — reused by Wave 3 (persona runner) + Wave 4 (synthesizer runner) + Wave 5 (entrypoint integration). 17 tests in `tests/routine/test_llm_client.py` GREEN (above the ≥10 floor); coverage **100% line / 100% branch** on `routine/llm_client.py`. Full repo regression: **504 passed** (487 baseline + 17 new). Wave 3 + Wave 4 + Wave 5 unblocked.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-05-04 (during execution session)
- **Completed:** 2026-05-04
- **Tasks:** 1 (TDD; 2 commits — RED + GREEN)
- **Files created:** 2 (routine/llm_client.py, tests/routine/test_llm_client.py)
- **Files modified:** 2 (pyproject.toml, tests/routine/conftest.py)

## Accomplishments

- **`routine/llm_client.py` shipped (193 LOC)** — provenance docstring referencing `virattt/ai-hedge-fund/src/utils/llm.py` per INFRA-07 with 4 modifications enumerated (Anthropic SDK native vs LangChain; Pydantic-direct vs JSON-extraction; async vs sync; single-vendor Claude); 4 module constants (`LLM_FAILURE_LOG`, `DEFAULT_MAX_RETRIES=2`, `_MESSAGE_TRUNCATION_LIMIT=1000`, `_RAW_TRUNCATION_LIMIT=5000`); `TypeVar T = TypeVar("T", bound=BaseModel)`; `async call_with_retry(client, *, model, system, user, output_format, default_factory, max_tokens, max_retries=DEFAULT_MAX_RETRIES, context_label) -> T`; `_try_extract_raw(exc: ValidationError) -> object` helper (best-effort raw-response extraction from `exc.errors()[0]['input']`); `_log_failure(label, kind, message, raw)` helper (single write point for the JSONL log).
- **17 tests in `tests/routine/test_llm_client.py`** (above the ≥10 floor) covering: happy path + parse-call kwargs assertion (1); ValidationError → retry → success (1); ValidationError exhaustion → default_factory (1, includes default_factory invocation-count assertion); APIStatusError exhaustion (1); APIError exhaustion (1); unknown exception (ValueError) exhaustion (1); failure log append-only across 3 invocations (1, asserts 6 total records); record shape with EXACTLY {timestamp, label, kind, message, raw} keys + UTC timestamp + sort_keys serialization round-trip (1); mkdir parents from a deeply-nested non-existent path (1); _log_failure direct unit tests for message + raw truncation (1) and raw=None pass-through (1); raw=null on api_error path (1); AST-grep no temp/top_p/top_k in source (1); INFRA-07 provenance literal-substring grep (1); module constants exposed (1); _try_extract_raw defensive paths — empty errors() list (1) + errors() raises (1).
- **`tests/routine/conftest.py` populated** — replaced Wave 0 placeholder with the full fixture-replay implementation: `MockMessages` class (queue_response / queue_exception / async parse() that records kwargs in `.calls` list); `MockAnthropicClient` wrapper; `mock_anthropic_client` per-test fixture; `isolated_failure_log` autouse fixture that monkeypatches `routine.llm_client.LLM_FAILURE_LOG` to a tmp_path-backed log so tests never pollute real `memory/`. Wave 3 + Wave 4 + Wave 5 reuse this fixture suite.
- **`pyproject.toml` extended** — `pytest-asyncio>=0.23` added to `[dependency-groups].dev` (uv resolved 1.3.0); `asyncio_mode = "auto"` configured in `[tool.pytest.ini_options]` so async test functions don't need explicit `@pytest.mark.asyncio` decoration.
- **Coverage gates cleared** — `routine/llm_client.py` at **100% line / 100% branch** (gate ≥90% / ≥85%). Full repo regression: **504 passed** (487 baseline + 17 new). Phase 1-4 + Wave 0/1 untouched (pure-additive plan).
- **Wave 3 + Wave 4 + Wave 5 unblocked** — they import `call_with_retry` + `LLM_FAILURE_LOG` + `DEFAULT_MAX_RETRIES` from `routine.llm_client` and reuse `mock_anthropic_client` + `isolated_failure_log` from `tests/routine/conftest.py`. The fixture-replay pattern means each Wave-3+ test reads as a specification ("given the LLM returns X, then the runner returns Y") rather than a chain of MagicMock spies.

## Task Commits

Each task was committed atomically (TDD: RED + GREEN):

1. **Task 1 RED — `ded5bfc`** — `test(05-03): add failing tests for routine.llm_client.call_with_retry + mock_anthropic_client fixture (LLM-04 + LLM-05)`. pyproject.toml dep + asyncio_mode; conftest.py fixture-replay implementation; test_llm_client.py with 14 initial tests. RED state confirmed: `ModuleNotFoundError: No module named 'routine.llm_client'` on collection (module not yet implemented).
2. **Task 1 GREEN — `fe6a696`** — `feat(05-03): routine.llm_client.call_with_retry — Anthropic SDK wrapper with retry / default_factory / append-only memory/llm_failures.jsonl (LLM-04 + LLM-05)`. routine/llm_client.py implementation; +3 tests folded in (1 truncation pivot + 2 _try_extract_raw defensive-path tests for 100% coverage). 17/17 GREEN; full repo 504 passed.

**Plan metadata:** committed via `gmd-tools commit` after this SUMMARY.md lands alongside STATE.md / ROADMAP.md / REQUIREMENTS.md updates.

## Files Created/Modified

### Created
- `routine/llm_client.py` (193 LOC) — call_with_retry async wrapper + helpers + module constants
- `tests/routine/test_llm_client.py` (17 tests; ~480 LOC) — exercises every code path in routine/llm_client.py

### Modified
- `pyproject.toml` — pytest-asyncio>=0.23 in dev deps; asyncio_mode='auto' in [tool.pytest.ini_options]
- `tests/routine/conftest.py` — Wave 0 placeholder replaced with MockAnthropicClient + MockMessages + mock_anthropic_client + isolated_failure_log

## Decisions Made

- **DEFAULT_MAX_RETRIES=2** (not 3) per Pattern #8 — cost-predictable; v1.x may add backoff
- **TypeVar T bound=BaseModel** — generic wrapper services Wave 3 (AgentSignal) + Wave 4 (TickerDecision) without duplication
- **Defensive `except Exception` branch** — kind='unknown_error' — cascade prevention; never let unexpected exceptions propagate
- **Failure log truncation at helper layer** (1000 chars message / 5000 chars raw) — defensive against multi-MB structured errors
- **Sort_keys=True + UTC + LF** — byte-stable serialization mirrors Phase 1/2 atomic-write discipline at the per-record level
- **Truncation tests target `_log_failure` directly** — Pydantic v2 ValidationError cannot be cleanly subclassed; direct unit tests are higher-fidelity than fighting Pydantic exception machinery
- **`_try_extract_raw` is best-effort** — broad Exception catch returns None on any extraction failure; two dedicated defensive-path tests lock the contract
- **`isolated_failure_log` autouse on tests/routine/*** — Wave 3-5 tests benefit transparently from per-test log isolation
- **MockAnthropicClient reusable by Wave 3-5** — populated here in Wave 2 to avoid duplication
- **pytest-asyncio asyncio_mode='auto'** — async test functions don't need explicit decoration

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Truncation test pivot — Pydantic v2 prevents direct ValidationError subclassing**
- **Found during:** Task 1 GREEN (running tests/routine/test_llm_client.py)
- **Issue:** The plan's implementation_sketch test for the message-truncation contract subclassed `ValidationError`. Pydantic v2's `ValidationError.__new__` requires `title` and `line_errors` positional arguments and rejects bare `def __init__(self): pass` overrides with `TypeError`. A real ValidationError's `str(exc)` is also auto-truncated at ~50 chars by Pydantic before reaching the wrapper, so even constructing one with a >5000-char input doesn't exercise the message-truncation path through `call_with_retry`.
- **Fix:** Replaced the single test with two direct unit tests on `_log_failure`: `test_log_failure_truncates_message_and_raw` (passes `"X"*5000` message + `"Y"*6000` raw → asserts record["message"]=="X"*1000 and record["raw"]=="Y"*5000) + `test_log_failure_raw_none_passes_through` (asserts raw=null when None passed). Higher-fidelity than fighting Pydantic exception machinery; the contract being tested is a property of the helper, not the wrapper.
- **Files modified:** tests/routine/test_llm_client.py
- **Verification:** Both new tests pass; coverage on routine/llm_client.py increased from 92% → still 92% line (this fix is test-side; the next deviation closes the gap to 100%).
- **Committed in:** `fe6a696` (GREEN commit)

**2. [Rule 2 - Missing Critical] Add 2 defensive-path tests on `_try_extract_raw` to close coverage gap**
- **Found during:** Task 1 GREEN (running coverage report)
- **Issue:** After GREEN tests passed, coverage on `routine/llm_client.py` was 92% line / partial branch — lines 161-163 (the `except Exception: return None` defensive catch + the trailing `return None` for the empty-errs branch) were uncovered. The plan's success criteria require ≥90% line / ≥85% branch, which is met, but the missing branches lock-in observable contracts (best-effort extraction returning None) that downstream Wave 3-5 tests will rely on.
- **Fix:** Added `test_try_extract_raw_returns_none_when_errors_empty` (stub exception with empty errors() list → returns None) + `test_try_extract_raw_returns_none_on_extraction_exception` (stub exception whose errors() raises RuntimeError → returns None). Both bypass the `except ValidationError` matching by calling `_try_extract_raw` directly with duck-typed objects — same approach as the truncation tests.
- **Files modified:** tests/routine/test_llm_client.py
- **Verification:** 17/17 tests GREEN; coverage on routine/llm_client.py now **100% line / 100% branch**.
- **Committed in:** `fe6a696` (GREEN commit)

---

**Total deviations:** 2 auto-fixed (1 Rule 1 - Bug; 1 Rule 2 - Missing Critical).
**Impact on plan:** Both deviations are test-side hardening. The implementation in `routine/llm_client.py` matches the locked sketch byte-for-byte. The truncation pivot adopts a higher-fidelity approach to the same contract; the defensive-path tests close the line-coverage gap from 92% → 100% (well above the ≥90% gate). No scope creep in production code.

## Issues Encountered

None — RED produced the expected `ModuleNotFoundError`; GREEN passed all 14 initial tests on first run except the 1 truncation test (deviation #1 above); coverage gap (deviation #2) closed by two additional defensive-path tests. Full repo regression GREEN throughout (no Phase 1-4 / Wave 0-1 test broke).

## User Setup Required

None — `pytest-asyncio` is a dev dep auto-installed via `uv sync`; no external service configuration needed.

## Self-Check

- [x] `routine/llm_client.py` exists (193 LOC) with required public surface (`call_with_retry`, `LLM_FAILURE_LOG`, `DEFAULT_MAX_RETRIES`, `_log_failure`, `_try_extract_raw`)
- [x] `tests/routine/conftest.py` populated with `MockAnthropicClient` + `mock_anthropic_client` + `isolated_failure_log` (Wave 3-5 reuse this)
- [x] `tests/routine/test_llm_client.py` has 17 tests (above the ≥10 floor); all GREEN
- [x] Coverage on routine/llm_client.py: 100% line / 100% branch (gate ≥90/85 cleared with margin)
- [x] Full repo regression: 504 passed (487 baseline + 17 new); zero Phase 1-4 / Wave 0-1 test broke
- [x] AST-grep guard: no `temperature=` / `top_p=` / `top_k=` in routine/llm_client.py source
- [x] Provenance: routine/llm_client.py docstring contains literal substring `virattt/ai-hedge-fund/src/utils/llm.py`
- [x] Both task commits exist: `ded5bfc` (RED) + `fe6a696` (GREEN)
- [x] pytest-asyncio>=0.23 in pyproject.toml [dependency-groups].dev; asyncio_mode='auto' in [tool.pytest.ini_options]

## Self-Check: PASSED

## Next Phase Readiness

- **Wave 3 (05-04 personas) UNBLOCKED** — imports `from routine.llm_client import call_with_retry` and uses `mock_anthropic_client` fixture for persona-call tests
- **Wave 4 (05-05 synthesizer) UNBLOCKED** — same imports + same fixtures; passes `output_format=TickerDecision` instead of `AgentSignal`
- **Wave 5 (05-06 entrypoint integration) UNBLOCKED** — integration tests use the same mock client to drive the full per-ticker pipeline
- **No blockers** — Phase 5 progress: 3/6 plans complete; next is `/gmd:execute-plan 05-04` (persona runner)

---
*Phase: 05-claude-routine-wiring*
*Completed: 2026-05-04*
