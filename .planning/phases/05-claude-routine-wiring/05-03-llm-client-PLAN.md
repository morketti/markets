---
phase: 05-claude-routine-wiring
plan: 03
type: tdd
wave: 2
depends_on: [05-01]
files_modified:
  - routine/llm_client.py
  - tests/routine/conftest.py
  - tests/routine/test_llm_client.py
autonomous: true
requirements: [LLM-04, LLM-05]
provides:
  - "routine/llm_client.py — `call_with_retry()` async function wrapping `client.messages.parse(output_format=PydanticModel)` per 05-RESEARCH.md Pattern #2 + Pattern #8"
  - "Retry policy: 2 attempts (max_retries=2 default; not 3 — keep cost predictable per Pattern #8); on `pydantic.ValidationError` OR `anthropic.APIError`/`APIStatusError` OR any unexpected exception → log to `memory/llm_failures.jsonl` and retry; on retry exhaustion → return `default_factory()` (LLM-05)"
  - "Failure log: append-only JSONL at `memory/llm_failures.jsonl`; one JSON object per record; fields {timestamp (ISO-8601 UTC), label, kind, message (≤1000 chars), raw (≤5000 chars or null)}; sort_keys=True for stable serialization; LF line endings"
  - "Module constants: `LLM_FAILURE_LOG = Path('memory/llm_failures.jsonl')` + `DEFAULT_MAX_RETRIES = 2`"
  - "Helper `_log_failure(label, kind, message, raw)` writes one JSONL record with `mkdir(parents=True, exist_ok=True)` on the parent dir"
  - "TypeVar T bound=BaseModel; `call_with_retry` is generic over T — Wave 3 calls with output_format=AgentSignal; Wave 4 calls with output_format=TickerDecision"
  - "Opus 4.7 BREAKING CHANGE adherence — NEVER pass temperature/top_p/top_k to messages.parse(); standardize on omitting (Pattern #2 lock)"
  - "tests/routine/conftest.py — populated with `mock_anthropic_client` fixture (fixture-replay pattern: maps (model, system_hash, user_hash) → canned PydanticModel response or canned exception); also exports `make_response(parsed_output)` helper that builds a mock response object whose `.parsed_output` attribute returns the supplied PydanticModel instance"
  - "tests/routine/test_llm_client.py — ≥10 tests covering happy path, ValidationError → default_factory, APIStatusError → default_factory, APIError → default_factory, retry-twice-then-fail, retry-once-then-succeed, failure log append-only contract, raw response captured on ValidationError, no real network call (mock asserts), unknown exception path"
tags: [phase-5, llm-client, anthropic-sdk, retry, default-factory, mock-fixture, tdd, wave-2, llm-04, llm-05]

must_haves:
  truths:
    - "routine/llm_client.py exports `call_with_retry` (async function) + `LLM_FAILURE_LOG` (Path constant) + `DEFAULT_MAX_RETRIES` (int constant)"
    - "Happy path: mock client returns response whose .parsed_output is a valid AgentSignal → `call_with_retry(...)` returns that AgentSignal; client.messages.parse called exactly ONCE; failure log has 0 records"
    - "ValidationError path: mock client.messages.parse raises pydantic.ValidationError on first call → second attempt succeeds → `call_with_retry` returns the second-attempt AgentSignal; failure log has exactly 1 record (kind='validation_error'); messages.parse called exactly TWICE"
    - "ValidationError exhaustion: mock raises ValidationError on BOTH attempts → `call_with_retry` returns `default_factory()` instance; failure log has exactly 2 records; messages.parse called exactly TWICE"
    - "APIStatusError path: mock raises anthropic.APIStatusError(429) → retry; if exhausted, return default_factory; failure log records `kind='api_error'` and includes the original message"
    - "APIError path: mock raises anthropic.APIError(...) → retry; same behavior as APIStatusError"
    - "Unknown exception path: mock raises ValueError('weird') → caught, logged with `kind='unknown_error'`, retried; on exhaustion return default_factory (defensive — never let an unexpected exception propagate out of call_with_retry)"
    - "Default factory invocation: when all retries exhausted, default_factory is called EXACTLY ONCE; its return value is propagated as the function return"
    - "Failure log append-only: 3 sequential failures across separate call_with_retry invocations → memory/llm_failures.jsonl has exactly 3 records; each is a valid standalone JSON object on its own line; second invocation does NOT truncate the file"
    - "Failure log directory creation: when memory/ does not exist before the first call, _log_failure creates it via mkdir(parents=True, exist_ok=True); subsequent records append cleanly"
    - "Failure log record fields: each record is a JSON object with EXACTLY these top-level keys: timestamp, label, kind, message, raw — no extras; values match expected types (timestamp is ISO-8601 string with timezone offset; raw is null when absent)"
    - "Failure log message truncation: a 5000-char ValidationError message is truncated to ≤1000 chars in the log record (defensive against log file blowup)"
    - "Failure log raw truncation: a raw response > 5000 chars is truncated to ≤5000 chars in the log record"
    - "Failure log timestamp is UTC: record['timestamp'].endswith('+00:00') OR ends with 'Z' — timezone-aware UTC always (no naive datetime.now() per Phase 3 Pitfall #6 lock)"
    - "Sort_keys serialization: each record's JSON keys appear in alphabetical order — same stable-serialization discipline as Phase 1/2/4 atomic writes"
    - "No temperature/top_p/top_k passed to messages.parse: AST-walk on routine/llm_client.py finds zero occurrences of these parameter names in the messages.parse() call site (defensive against Opus 4.7 400 errors per Pattern #2)"
    - "No real network call: mock_anthropic_client fixture is a pure Python mock; tests never reach api.anthropic.com (verified by absence of `responses` library or aiohttp socket patch — the AsyncAnthropic client is mocked at the messages.parse() boundary)"
    - "Coverage ≥90% line / ≥85% branch on routine/llm_client.py"
  artifacts:
    - path: "routine/llm_client.py"
      provides: "call_with_retry() + _log_failure() + module constants + provenance docstring referencing virattt/ai-hedge-fund/src/utils/llm.py per INFRA-07. ~100-130 LOC."
      min_lines: 90
    - path: "tests/routine/conftest.py"
      provides: "mock_anthropic_client fixture (fixture-replay pattern) + make_response helper; ~80-120 LOC."
      min_lines: 60
    - path: "tests/routine/test_llm_client.py"
      provides: "≥10 tests covering: happy path; ValidationError → retry → success; ValidationError exhaustion → default_factory; APIStatusError → default_factory; APIError → default_factory; unknown exception → default_factory; failure log append-only contract; raw response captured; sort_keys serialization; UTC timestamp; no temp/top_p/top_k in call site (AST-grep). ~250-350 LOC."
      min_lines: 200
  key_links:
    - from: "routine/llm_client.py"
      to: "anthropic.AsyncAnthropic + anthropic.APIError + anthropic.APIStatusError"
      via: "imports for the SDK client + the two locked exception types per 05-RESEARCH.md Pattern #8"
      pattern: "from anthropic import"
    - from: "routine/llm_client.py"
      to: "pydantic.BaseModel + pydantic.ValidationError + typing.TypeVar"
      via: "TypeVar T bound=BaseModel makes call_with_retry generic over the output_format parameter"
      pattern: "TypeVar\\(.*bound.*BaseModel"
    - from: "routine/llm_client.py"
      to: "memory/llm_failures.jsonl (append-only file)"
      via: "_log_failure writes via Path('memory/llm_failures.jsonl').open('a', encoding='utf-8')"
      pattern: "memory/llm_failures\\.jsonl"
    - from: "routine/llm_client.py"
      to: "Wave 3 routine/persona_runner.py + Wave 4 synthesis/synthesizer.py (downstream consumers)"
      via: "call_with_retry(output_format=AgentSignal, default_factory=_persona_default_factory(...)) for personas; call_with_retry(output_format=TickerDecision, default_factory=_decision_default_factory(...)) for synthesizer"
      pattern: "call_with_retry"
    - from: "tests/routine/conftest.py mock_anthropic_client"
      to: "tests/routine/test_llm_client.py + tests/routine/test_persona_runner.py + tests/routine/test_synthesizer_runner.py + tests/routine/test_entrypoint.py"
      via: "shared fixture — Wave 3, 4, 5 tests all use this mock client; populated here in Wave 2 to avoid duplication"
      pattern: "mock_anthropic_client"
    - from: "routine/llm_client.py docstring"
      to: "virattt/ai-hedge-fund/src/utils/llm.py (INFRA-07 provenance)"
      via: "module docstring carries the lineage + the divergence note (constrained-decoding via messages.parse() vs prompt-engineered JSON; Anthropic native vs LangChain abstraction; Pydantic-direct vs JSON-extraction-with-fallback)"
      pattern: "virattt/ai-hedge-fund/src/utils/llm\\.py"
---

<objective>
Wave 2 / LLM-04 + LLM-05: ship the thin Anthropic SDK wrapper at `routine/llm_client.py` with retry-with-default-factory discipline. The wrapper is generic over the Pydantic output type (TypeVar T bound=BaseModel) — Wave 3 calls it with `output_format=AgentSignal` for personas; Wave 4 calls it with `output_format=TickerDecision` for the synthesizer. Failures are logged to `memory/llm_failures.jsonl` (append-only); on retry exhaustion, the function returns `default_factory()` so the per-ticker pipeline can continue with a default-factory signal/decision (LLM-05 contract). Also populates `tests/routine/conftest.py` with the `mock_anthropic_client` fixture used by every Wave 2-5 routine test.

Purpose: this is the single point of LLM I/O in the entire Phase 5 routine. Wave 3 + Wave 4 + Wave 5 all flow through `call_with_retry` — by isolating the retry/log/default-factory discipline here, the per-persona + synthesizer + integration tests can mock at exactly ONE boundary (`AsyncAnthropic.messages.parse`) and exercise the cascade. Without this plan, every downstream test would re-implement the mock pattern inline; with it, each test is short and intent-focused.

The retry-with-default-factory pattern is the project's primary defense against the LLM-failure cascade: when Buffett's call fails, the routine returns a default-factory AgentSignal (verdict='neutral', confidence=0, evidence=['schema_failure'], data_unavailable=True), the synthesizer reads it with the rest of the persona slate, and the run continues. The `_status.json.llm_failure_count` field surfaces the cascade in Phase 6 frontend so the user sees "12 LLM failures today" and investigates. This is preferable to the alternative (abort the run, lose 30 tickers' data); per 05-RESEARCH.md Pitfall #3 the discipline is locked.

The mock fixture in `tests/routine/conftest.py` follows the fixture-replay pattern: tests register canned responses (or canned exceptions) keyed by call signature; the mock returns or raises accordingly. This avoids brittle MagicMock-spy chains and lets tests read like specification: "given the LLM returns this AgentSignal, then call_with_retry returns that AgentSignal".

Provenance per INFRA-07: `routine/llm_client.py` docstring references `virattt/ai-hedge-fund/src/utils/llm.py` (`call_llm()` retry pattern) — adapted with 4 modifications: (a) Anthropic-native messages.parse() not LangChain with_structured_output(); (b) Pydantic-direct returned object not extract_json_from_response() regex parsing; (c) Anthropic-only (no multi-provider abstraction); (d) async (AsyncAnthropic) not sync.

Output: routine/llm_client.py (~100-130 LOC: provenance docstring + 2 module constants + TypeVar + call_with_retry async function + _log_failure helper); tests/routine/conftest.py (~80-120 LOC: mock_anthropic_client fixture + make_response helper + tmp_failure_log auto-fixture for test isolation); tests/routine/test_llm_client.py (~250-350 LOC, ≥10 tests, all GREEN).
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
@.planning/phases/05-claude-routine-wiring/05-01-foundation-PLAN.md

# Existing patterns to mirror — atomic-write + Path stability + Phase 1/2 stable serialization
@analysts/signals.py
@analysts/position_signal.py
@watchlist/loader.py
@ingestion/refresh.py
@tests/analysts/conftest.py

<interfaces>
<!-- Anthropic SDK public surface — verified in Wave 0 smoke test: -->

```python
from anthropic import AsyncAnthropic, APIError, APIStatusError

# AsyncAnthropic.messages.parse signature (verified per 05-RESEARCH.md Pattern #2):
async def parse(
    self,
    *,
    model: str,
    max_tokens: int,
    system: str,
    messages: list[dict],
    output_format: type[BaseModel],
    # NOTE: temperature, top_p, top_k MUST NOT be passed — Opus 4.7 returns 400.
) -> ParsedResponse:
    """Returns a response object with `.parsed_output: BaseModel` attribute."""
```

<!-- Wave 3 + Wave 4 will call call_with_retry like this (preview): -->

```python
# Wave 3 — routine/persona_runner.py:
signal = await call_with_retry(
    client,
    model="claude-sonnet-4-6",
    system=persona_prompt,
    user=user_context,
    output_format=AgentSignal,
    default_factory=_persona_default_factory(persona_id, ticker, computed_at),
    max_tokens=2000,
    context_label=f"{persona_id}:{ticker}",
)

# Wave 4 — synthesis/synthesizer.py:
decision = await call_with_retry(
    client,
    model="claude-opus-4-7",
    system=synthesizer_prompt,
    user=user_context,
    output_format=TickerDecision,
    default_factory=_decision_default_factory(ticker, computed_at),
    max_tokens=4000,
    context_label=f"synthesizer:{ticker}",
)
```

<!-- Mock client fixture-replay pattern — tests/routine/conftest.py: -->

```python
class MockAnthropicClient:
    """Pure-Python mock; replays canned responses keyed by call count.

    Tests register a list of (response_or_exception, ...) tuples; the mock's
    .messages.parse() yields them in order. After all canned items consumed,
    raises StopIteration (catchable by tests asserting the call count).
    """
    def __init__(self):
        self.messages = MockMessages()


class MockMessages:
    def __init__(self):
        self._queue: list = []
        self.calls: list[dict] = []  # records every kwargs dict for assertions

    def queue_response(self, parsed_output: BaseModel) -> None:
        """Queue a successful response."""
        self._queue.append(("response", parsed_output))

    def queue_exception(self, exc: BaseException) -> None:
        """Queue an exception to raise on next call."""
        self._queue.append(("exception", exc))

    async def parse(self, **kwargs) -> object:
        """Mock messages.parse — pops next queued item; raises if exception, returns mock response if response."""
        self.calls.append(dict(kwargs))
        if not self._queue:
            raise RuntimeError("MockMessages: no more queued items (test setup mismatch)")
        kind, payload = self._queue.pop(0)
        if kind == "exception":
            raise payload
        # kind == "response" — return a mock response object with .parsed_output
        class _MockResponse:
            parsed_output = payload
        return _MockResponse()
```
</interfaces>

<implementation_sketch>
<!-- routine/llm_client.py — full file content. Wave 5 (entrypoint integration) will
     instantiate AsyncAnthropic() and pass it to call_with_retry; this module never
     instantiates the client itself (separation of concerns: client lifecycle is
     entrypoint's job; this module is just the call wrapper). -->

```python
"""routine.llm_client — Anthropic SDK call wrapper with retry + default-factory.

Pattern adapted from virattt/ai-hedge-fund/src/utils/llm.py call_llm() —
adapted for our Anthropic-only / messages.parse-direct / async stack.

Modifications from the reference implementation:
  * Anthropic SDK native (AsyncAnthropic + messages.parse(output_format=...))
    instead of LangChain's with_structured_output() abstraction over multiple
    providers.
  * Pydantic-direct returned object — `response.parsed_output: PydanticModel`
    is already-validated (constrained-decoding-backed); no manual JSON
    extraction or extract_json_from_response() pre-parser needed.
  * Async (await client.messages.parse(...)) — Wave 3 fans out 6 personas in
    parallel via asyncio.gather; sync would 6× wall-clock per ticker.
  * Single LLM vendor (Claude only); no provider abstraction. Matches
    PROJECT.md "All LLM I/O is Claude only" lock.

Failure handling per 05-RESEARCH.md Pattern #8:
  * pydantic.ValidationError (constrained-decoding produced JSON-shape-valid
    output that nonetheless violates a Pydantic semantic validator — e.g.,
    a min_length=1 list field with an empty list) → retry once → if still
    failing, return default_factory() and log to memory/llm_failures.jsonl.
  * anthropic.APIStatusError (429 rate-limit / 5xx server errors) → retry →
    return default_factory() on exhaustion.
  * anthropic.APIError (network errors, malformed body, etc.) → same as
    APIStatusError.
  * Any other unexpected exception → defensive catch → log as
    'unknown_error' kind → retry → default_factory() on exhaustion. We never
    let an unexpected exception propagate out of call_with_retry; the per-
    ticker pipeline must continue.

LLM-05 contract: on validation failure (any kind) the raw response (when
available — only on ValidationError) is logged to memory/llm_failures.jsonl
along with timestamp + label + kind + message. Append-only.

NEVER pass temperature/top_p/top_k to messages.parse() — Opus 4.7 returns
400 on any non-default value (05-RESEARCH.md CORRECTION #2 + Pattern #2).
Sonnet 4.6 still accepts them but we standardize on omitting for both.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, TypeVar

from anthropic import APIError, APIStatusError, AsyncAnthropic
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

# Module constants — single source of truth.
LLM_FAILURE_LOG: Path = Path("memory/llm_failures.jsonl")
DEFAULT_MAX_RETRIES: int = 2
DEFAULT_FACTORY_LOG_TRUNCATION_MESSAGE: int = 1000
DEFAULT_FACTORY_LOG_TRUNCATION_RAW: int = 5000

T = TypeVar("T", bound=BaseModel)


async def call_with_retry(
    client: AsyncAnthropic,
    *,
    model: str,
    system: str,
    user: str,
    output_format: type[T],
    default_factory: Callable[[], T],
    max_tokens: int,
    max_retries: int = DEFAULT_MAX_RETRIES,
    context_label: str,
) -> T:
    """Call Claude with retry; return Pydantic-validated output or default_factory().

    Parameters
    ----------
    client : AsyncAnthropic
        Pre-instantiated SDK client (entrypoint owns lifecycle).
    model : str
        Claude model ID — "claude-sonnet-4-6" for personas, "claude-opus-4-7"
        for synthesizer per Pattern #2.
    system : str
        System prompt — for personas, the markdown-loaded persona prompt;
        for synthesizer, the synthesizer prompt.
    user : str
        User-message content — per-ticker context dict serialized to a string.
    output_format : type[T]
        Pydantic model class to use for constrained decoding + validation.
        T is bound to BaseModel.
    default_factory : Callable[[], T]
        Zero-arg callable returning a T instance — used when all retries
        exhausted. Closure captures ticker/persona_id/computed_at from caller
        so the factory produces a contextually-correct default (LLM-05).
    max_tokens : int
        Per-call max output tokens — 2000 for personas, 4000 for synthesizer.
    max_retries : int, default DEFAULT_MAX_RETRIES (=2)
        Attempt count, NOT the retry count beyond the first attempt; total
        attempts = max_retries. v1 ships at 2; v1.x may add tenacity-backed
        exponential backoff for 429s.
    context_label : str
        Diagnostic label for failure log records — e.g. "buffett:AAPL" or
        "synthesizer:AAPL".

    Returns
    -------
    T
        Pydantic-validated output_format instance, OR default_factory() return
        if all retries exhausted.

    Notes
    -----
    NEVER passes temperature/top_p/top_k — Opus 4.7 rejects them (Pattern #2).
    """
    last_exc: BaseException | None = None
    last_raw: object = None  # captured on ValidationError when available

    for attempt in range(max_retries):
        last_raw = None
        try:
            response = await client.messages.parse(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_format=output_format,
            )
            return response.parsed_output
        except ValidationError as e:
            last_exc = e
            # The SDK exposes raw response content on ValidationError when
            # constrained-decoding produced shape-valid JSON that still failed
            # Pydantic semantic validation. Try to surface it for the log.
            last_raw = _try_extract_raw(e)
            _log_failure(
                context_label, "validation_error", str(e), last_raw,
            )
        except (APIStatusError, APIError) as e:
            last_exc = e
            _log_failure(context_label, "api_error", str(e), None)
        except Exception as e:  # noqa: BLE001 — defensive cascade prevention
            last_exc = e
            _log_failure(context_label, "unknown_error", repr(e), None)

    # All retries exhausted — return default factory; log the cascade.
    logger.warning(
        "llm_client(%s) exhausted %d retries; returning default_factory. last: %r",
        context_label, max_retries, last_exc,
    )
    return default_factory()


def _try_extract_raw(exc: ValidationError) -> object:
    """Best-effort extraction of raw response from a ValidationError.

    Pydantic's ValidationError.input attribute (per Pydantic v2 docs) carries
    the input that failed validation when available. For ValidationErrors
    raised by the SDK on parsed_output, this is typically the raw JSON dict
    or string. Returns None if extraction fails.
    """
    try:
        # Pydantic v2: ValidationError carries .errors() dicts; each error has
        # 'input' (the offending value). Aggregate the first 'input' as the raw.
        errs = exc.errors()
        if errs and isinstance(errs[0], dict) and "input" in errs[0]:
            return errs[0]["input"]
    except Exception:  # noqa: BLE001 — extraction is best-effort only
        return None
    return None


def _log_failure(label: str, kind: str, message: str, raw: object) -> None:
    """Append failure record to memory/llm_failures.jsonl (append-only)."""
    LLM_FAILURE_LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "label": label,
        "kind": kind,
        "message": message[:DEFAULT_FACTORY_LOG_TRUNCATION_MESSAGE],
        "raw": (
            str(raw)[:DEFAULT_FACTORY_LOG_TRUNCATION_RAW]
            if raw is not None
            else None
        ),
    }
    line = json.dumps(record, sort_keys=True) + "\n"
    with LLM_FAILURE_LOG.open("a", encoding="utf-8") as f:
        f.write(line)
```

<!-- tests/routine/conftest.py — populates the mock_anthropic_client fixture
     used by Wave 2-5 tests. ALSO adds tmp_failure_log auto-fixture so tests
     get an isolated memory/llm_failures.jsonl path (avoids cross-test pollution). -->

```python
"""Phase 5 routine test fixtures — mock Claude client + isolated failure log.

The mock client is a pure-Python fixture-replay implementation: tests register
canned responses (or canned exceptions) before invoking call_with_retry;
the mock yields them in queue order on each .messages.parse() call.

This avoids the brittleness of MagicMock-spy chains and gives tests a
specification feel: "given the LLM returns this AgentSignal, then call_with_retry
returns that AgentSignal".

Wave 3 + Wave 4 + Wave 5 reuse this same fixture; the mock object's `.calls`
list captures every kwargs dict for downstream assertion (e.g., "synthesizer
test asserts model='claude-opus-4-7' was passed").
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pydantic import BaseModel


class MockMessages:
    """Mock Anthropic SDK messages object with queueable responses/exceptions."""

    def __init__(self) -> None:
        self._queue: list[tuple[str, object]] = []
        self.calls: list[dict] = []

    def queue_response(self, parsed_output: "BaseModel") -> None:
        """Append a successful response to the queue."""
        self._queue.append(("response", parsed_output))

    def queue_exception(self, exc: BaseException) -> None:
        """Append an exception (raised on next .parse() call)."""
        self._queue.append(("exception", exc))

    async def parse(self, **kwargs) -> object:
        """Mock parse — record kwargs, pop next queued item, return or raise."""
        self.calls.append(dict(kwargs))
        if not self._queue:
            raise RuntimeError(
                f"MockMessages: queue empty on call {len(self.calls)} "
                f"(test setup error — queued fewer responses than test "
                f"expected). kwargs.keys={list(kwargs.keys())}"
            )
        kind, payload = self._queue.pop(0)
        if kind == "exception":
            raise payload  # type: ignore[misc]

        class _Response:
            parsed_output = payload

        return _Response()


class MockAnthropicClient:
    """Mock AsyncAnthropic — exposes a .messages property that's the MockMessages."""

    def __init__(self) -> None:
        self.messages = MockMessages()


@pytest.fixture
def mock_anthropic_client() -> MockAnthropicClient:
    """Per-test fresh MockAnthropicClient. Tests register queued items inline."""
    return MockAnthropicClient()


@pytest.fixture(autouse=True)
def isolated_failure_log(tmp_path, monkeypatch) -> Path:
    """Redirect memory/llm_failures.jsonl to a temp dir for test isolation.

    Auto-applied to every test in tests/routine/ so tests don't pollute the
    real memory/ folder. Yields the temp Path so tests can read records.
    """
    # Patch the module-level LLM_FAILURE_LOG constant so _log_failure() writes
    # to tmp_path instead of repo memory/.
    log_path = tmp_path / "memory" / "llm_failures.jsonl"
    # Lazy import to avoid circular issues if routine.llm_client isn't importable yet.
    import routine.llm_client as llm_client_mod

    monkeypatch.setattr(llm_client_mod, "LLM_FAILURE_LOG", log_path)
    return log_path
```

<!-- tests/routine/test_llm_client.py — ≥10 tests:

  ```python
  """Tests for routine.llm_client.call_with_retry + _log_failure (LLM-04 + LLM-05).

  Mocks the AsyncAnthropic boundary via tests/routine/conftest.py's
  mock_anthropic_client fixture (fixture-replay pattern). Tests register canned
  responses or exceptions; call_with_retry's behavior is asserted via the
  mock's .calls list and the isolated_failure_log file.
  """
  from __future__ import annotations

  import json
  from datetime import datetime, timezone
  from pathlib import Path

  import pytest
  from anthropic import APIError, APIStatusError
  from pydantic import BaseModel, Field, ValidationError

  from analysts.signals import AgentSignal
  from routine.llm_client import (
      DEFAULT_MAX_RETRIES,
      LLM_FAILURE_LOG,
      call_with_retry,
  )


  # Test helper — build a valid AgentSignal for queueing as a "response" payload.
  def _make_signal(
      ticker: str = "AAPL",
      analyst_id: str = "buffett",
      verdict: str = "bullish",
      confidence: int = 70,
  ) -> AgentSignal:
      return AgentSignal(
          ticker=ticker,
          analyst_id=analyst_id,
          computed_at=datetime(2026, 5, 1, 13, 30, 0, tzinfo=timezone.utc),
          verdict=verdict,
          confidence=confidence,
          evidence=["test evidence string"],
          data_unavailable=False,
      )


  def _default_factory_signal(ticker: str = "AAPL") -> AgentSignal:
      """Default-factory function returning a neutral / data_unavailable signal."""
      return AgentSignal(
          ticker=ticker,
          analyst_id="buffett",
          computed_at=datetime(2026, 5, 1, 13, 30, 0, tzinfo=timezone.utc),
          verdict="neutral",
          confidence=0,
          evidence=["schema_failure"],
          data_unavailable=True,
      )


  @pytest.mark.asyncio
  async def test_happy_path_returns_parsed_output(mock_anthropic_client) -> None:
      """Single successful call returns the parsed AgentSignal."""
      expected = _make_signal()
      mock_anthropic_client.messages.queue_response(expected)

      result = await call_with_retry(
          mock_anthropic_client,
          model="claude-sonnet-4-6",
          system="You are Warren Buffett.",
          user="Analyze AAPL.",
          output_format=AgentSignal,
          default_factory=lambda: _default_factory_signal(),
          max_tokens=2000,
          context_label="buffett:AAPL",
      )

      assert result is expected
      assert len(mock_anthropic_client.messages.calls) == 1
      call_kwargs = mock_anthropic_client.messages.calls[0]
      assert call_kwargs["model"] == "claude-sonnet-4-6"
      assert call_kwargs["max_tokens"] == 2000
      assert call_kwargs["output_format"] is AgentSignal


  @pytest.mark.asyncio
  async def test_validation_error_then_success(mock_anthropic_client, isolated_failure_log) -> None:
      """First call ValidationError → second call success → returns second-attempt signal; 1 failure logged."""
      # Forge a ValidationError by trying to construct an invalid AgentSignal.
      try:
          AgentSignal(ticker="!!!", analyst_id="buffett", computed_at=datetime.now(timezone.utc))
      except ValidationError as exc:
          ve = exc

      success = _make_signal(verdict="strong_bullish")
      mock_anthropic_client.messages.queue_exception(ve)
      mock_anthropic_client.messages.queue_response(success)

      result = await call_with_retry(
          mock_anthropic_client,
          model="claude-sonnet-4-6",
          system="...",
          user="...",
          output_format=AgentSignal,
          default_factory=lambda: _default_factory_signal(),
          max_tokens=2000,
          context_label="buffett:AAPL",
      )

      assert result is success
      assert len(mock_anthropic_client.messages.calls) == 2

      records = [json.loads(line) for line in isolated_failure_log.read_text(encoding="utf-8").splitlines()]
      assert len(records) == 1
      assert records[0]["kind"] == "validation_error"
      assert records[0]["label"] == "buffett:AAPL"


  @pytest.mark.asyncio
  async def test_validation_error_exhaustion_returns_default_factory(mock_anthropic_client, isolated_failure_log) -> None:
      """All retries fail with ValidationError → return default_factory(); 2 failures logged."""
      try:
          AgentSignal(ticker="!!!", analyst_id="buffett", computed_at=datetime.now(timezone.utc))
      except ValidationError as exc:
          ve = exc

      mock_anthropic_client.messages.queue_exception(ve)
      mock_anthropic_client.messages.queue_exception(ve)

      result = await call_with_retry(
          mock_anthropic_client,
          model="claude-sonnet-4-6",
          system="...",
          user="...",
          output_format=AgentSignal,
          default_factory=lambda: _default_factory_signal(),
          max_tokens=2000,
          context_label="buffett:AAPL",
      )

      assert result.verdict == "neutral"
      assert result.data_unavailable is True
      assert result.evidence == ["schema_failure"]
      assert len(mock_anthropic_client.messages.calls) == DEFAULT_MAX_RETRIES

      records = [json.loads(line) for line in isolated_failure_log.read_text(encoding="utf-8").splitlines()]
      assert len(records) == DEFAULT_MAX_RETRIES
      assert all(r["kind"] == "validation_error" for r in records)


  @pytest.mark.asyncio
  async def test_api_status_error_returns_default_factory(mock_anthropic_client, isolated_failure_log) -> None:
      """All APIStatusError(429) → default_factory; 2 records with kind='api_error'."""
      err = APIStatusError("rate limit", response=None, body=None)  # construction depends on SDK ver; adapt as needed
      # Some SDK versions require positional args; if construction fails, use a mock subclass.
      # FALLBACK: use a manual subclass (no SDK dep on internal __init__):
      class _FakeStatus(APIStatusError):
          def __init__(self): pass
          def __str__(self): return "rate limit"
      err = _FakeStatus()

      mock_anthropic_client.messages.queue_exception(err)
      mock_anthropic_client.messages.queue_exception(err)

      result = await call_with_retry(
          mock_anthropic_client,
          model="claude-sonnet-4-6", system="...", user="...",
          output_format=AgentSignal,
          default_factory=lambda: _default_factory_signal(),
          max_tokens=2000, context_label="buffett:AAPL",
      )
      assert result.data_unavailable is True
      records = [json.loads(line) for line in isolated_failure_log.read_text(encoding="utf-8").splitlines()]
      assert len(records) == 2
      assert all(r["kind"] == "api_error" for r in records)


  @pytest.mark.asyncio
  async def test_api_error_returns_default_factory(mock_anthropic_client, isolated_failure_log) -> None:
      """APIError (network etc.) → retry → default_factory."""
      class _FakeApiError(APIError):
          def __init__(self): pass
          def __str__(self): return "network down"
      err = _FakeApiError()

      mock_anthropic_client.messages.queue_exception(err)
      mock_anthropic_client.messages.queue_exception(err)

      result = await call_with_retry(
          mock_anthropic_client,
          model="claude-sonnet-4-6", system="...", user="...",
          output_format=AgentSignal,
          default_factory=lambda: _default_factory_signal(),
          max_tokens=2000, context_label="buffett:AAPL",
      )
      assert result.data_unavailable is True


  @pytest.mark.asyncio
  async def test_unknown_exception_logged_and_default_factory_returned(mock_anthropic_client, isolated_failure_log) -> None:
      """Defensive — any other Exception is caught, logged with kind='unknown_error', retried."""
      mock_anthropic_client.messages.queue_exception(ValueError("weird non-API error"))
      mock_anthropic_client.messages.queue_exception(ValueError("weird non-API error"))

      result = await call_with_retry(
          mock_anthropic_client,
          model="claude-sonnet-4-6", system="...", user="...",
          output_format=AgentSignal,
          default_factory=lambda: _default_factory_signal(),
          max_tokens=2000, context_label="buffett:AAPL",
      )
      assert result.data_unavailable is True
      records = [json.loads(line) for line in isolated_failure_log.read_text(encoding="utf-8").splitlines()]
      assert all(r["kind"] == "unknown_error" for r in records)


  @pytest.mark.asyncio
  async def test_failure_log_append_only_across_invocations(mock_anthropic_client, isolated_failure_log) -> None:
      """3 sequential failing calls → 3 records; second call doesn't truncate first call's record."""
      try:
          AgentSignal(ticker="!!!", analyst_id="buffett", computed_at=datetime.now(timezone.utc))
      except ValidationError as exc:
          ve = exc

      for _ in range(3):
          mock_anthropic_client.messages.queue_exception(ve)
          mock_anthropic_client.messages.queue_exception(ve)
          await call_with_retry(
              mock_anthropic_client,
              model="claude-sonnet-4-6", system="...", user="...",
              output_format=AgentSignal,
              default_factory=lambda: _default_factory_signal(),
              max_tokens=2000, context_label="buffett:AAPL",
          )

      records = [json.loads(line) for line in isolated_failure_log.read_text(encoding="utf-8").splitlines()]
      assert len(records) == 3 * DEFAULT_MAX_RETRIES  # 6 records total


  @pytest.mark.asyncio
  async def test_failure_log_record_shape(mock_anthropic_client, isolated_failure_log) -> None:
      """Each record has EXACTLY {timestamp, label, kind, message, raw} keys; UTC timestamp; sort_keys."""
      try:
          AgentSignal(ticker="!!!", analyst_id="buffett", computed_at=datetime.now(timezone.utc))
      except ValidationError as exc:
          ve = exc

      mock_anthropic_client.messages.queue_exception(ve)
      mock_anthropic_client.messages.queue_exception(ve)
      await call_with_retry(
          mock_anthropic_client,
          model="claude-sonnet-4-6", system="...", user="...",
          output_format=AgentSignal,
          default_factory=lambda: _default_factory_signal(),
          max_tokens=2000, context_label="buffett:AAPL",
      )

      lines = isolated_failure_log.read_text(encoding="utf-8").splitlines()
      record = json.loads(lines[0])
      assert set(record.keys()) == {"timestamp", "label", "kind", "message", "raw"}
      # UTC timestamp:
      assert record["timestamp"].endswith("+00:00")
      # sort_keys: serialized as alphabetical order — re-serialize and compare:
      reserialized = json.dumps(record, sort_keys=True)
      assert reserialized == lines[0].rstrip("\n")  # first line should match sorted form


  @pytest.mark.asyncio
  async def test_failure_log_message_truncation(mock_anthropic_client, isolated_failure_log) -> None:
      """A 5000-char ValidationError message is truncated to ≤1000 chars in the log."""
      class _LargeException(ValidationError):
          def __init__(self): pass
          def __str__(self): return "X" * 5000
          def errors(self): return [{"input": "Y" * 6000, "msg": "x", "type": "x", "loc": ("x",)}]

      mock_anthropic_client.messages.queue_exception(_LargeException())
      mock_anthropic_client.messages.queue_exception(_LargeException())

      await call_with_retry(
          mock_anthropic_client,
          model="claude-sonnet-4-6", system="...", user="...",
          output_format=AgentSignal,
          default_factory=lambda: _default_factory_signal(),
          max_tokens=2000, context_label="buffett:AAPL",
      )
      records = [json.loads(line) for line in isolated_failure_log.read_text(encoding="utf-8").splitlines()]
      assert len(records[0]["message"]) <= 1000
      assert records[0]["raw"] is not None
      assert len(records[0]["raw"]) <= 5000


  def test_no_temperature_top_p_top_k_in_call_site() -> None:
      """AST grep: routine/llm_client.py never passes temperature/top_p/top_k to messages.parse.

      Opus 4.7 returns 400 on these parameters per Pattern #2.
      """
      source = Path("routine/llm_client.py").read_text(encoding="utf-8")
      assert "temperature=" not in source
      assert "top_p=" not in source
      assert "top_k=" not in source


  def test_provenance_header_references_virattt() -> None:
      """INFRA-07: routine/llm_client.py docstring names the virattt source file."""
      source = Path("routine/llm_client.py").read_text(encoding="utf-8")
      assert "virattt/ai-hedge-fund/src/utils/llm.py" in source
  ```

NOTE on async testing: pytest-asyncio is needed. Verify with `poetry show pytest-asyncio` —
if absent, the GREEN action adds it to [dependency-groups].dev (alongside pytest-cov).
The fixture decorator pattern matches `@pytest.mark.asyncio` for async test functions.
-->
</implementation_sketch>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: routine/llm_client.py + mock_anthropic_client fixture + ≥10 tests (RED → GREEN)</name>
  <files>routine/llm_client.py, tests/routine/conftest.py, tests/routine/test_llm_client.py, pyproject.toml</files>
  <behavior>
    Single TDD task — the entire wave 2 wrapper + tests + fixture land together because they are co-dependent (the tests need the fixture; the fixture is generic enough to be re-used by Waves 3-5; the wrapper exists to be tested).

    PRE-WORK: verify `pytest-asyncio` is in `[dependency-groups].dev`. The Phase 5 routine wrapper is async (uses `await client.messages.parse(...)`); tests need `@pytest.mark.asyncio` to run async test functions. If absent, append `"pytest-asyncio>=0.23"` to the dev group and run `uv sync`. This is a one-line pyproject.toml change separate from the analysts widening edits.

    Implementation per implementation_sketch above:
    - `routine/llm_client.py`: provenance docstring (~25 lines, references virattt/ai-hedge-fund/src/utils/llm.py per INFRA-07; lists 4 modifications); module constants; TypeVar T bound=BaseModel; `call_with_retry` async function (parameters as locked in 05-RESEARCH.md Pattern #8); `_try_extract_raw` helper (best-effort raw-response extraction from ValidationError); `_log_failure` helper (write JSONL record with sort_keys, mkdir parents).
    - `tests/routine/conftest.py`: replaces the Wave 0 placeholder with the full fixture-replay mock implementation; exports `mock_anthropic_client` per-test fresh fixture + `isolated_failure_log` autouse fixture (monkeypatches LLM_FAILURE_LOG → tmp_path).
    - `tests/routine/test_llm_client.py`: ≥10 tests as specified in implementation_sketch.

    Critical correctness invariants:
    - `call_with_retry` MUST NOT pass temperature/top_p/top_k to messages.parse (Opus 4.7 400 error per Pattern #2).
    - On ValidationError, the SDK's raw response IS captured when available via `_try_extract_raw` and logged in record["raw"].
    - `_log_failure` writes ONE line per record (LF-terminated); records are JSON objects with sort_keys=True for stable serialization (mirrors Phase 1/2 atomic-write discipline).
    - `_log_failure` creates the `memory/` parent dir via `mkdir(parents=True, exist_ok=True)` — the directory does not need to pre-exist.
    - The `isolated_failure_log` autouse fixture monkeypatches the module-level `LLM_FAILURE_LOG` constant, NOT the file system; tests are isolated via tmp_path.
    - On retry exhaustion, `default_factory()` is called EXACTLY ONCE; tests assert this via call counter on the factory closure.
  </behavior>
  <action>
    PRE-WORK:
    0. Check pytest-asyncio: `poetry show pytest-asyncio 2>&1 | head -5` — if installed, skip step 1. If absent, edit pyproject.toml `[dependency-groups].dev` and append `"pytest-asyncio>=0.23",` after `"pytest-cov>=5.0",`. Run `uv sync`. Verify install: `poetry run python -c "import pytest_asyncio; print(pytest_asyncio.__version__)"`. Configure pytest mode for asyncio in `[tool.pytest.ini_options]`: append `asyncio_mode = "auto"` (so test functions don't all need `@pytest.mark.asyncio` decorator individually — auto mode discovers async test functions and applies the marker). Verify with a trivial test.

    RED:
    1. Write `tests/routine/conftest.py` per implementation_sketch — full content (replaces Wave 0 docstring placeholder). Includes:
       - MockMessages class with `queue_response`, `queue_exception`, async `parse(**kwargs)`, `.calls` recording.
       - MockAnthropicClient class wrapping MockMessages.
       - `mock_anthropic_client` per-test fixture.
       - `isolated_failure_log` autouse fixture (patches LLM_FAILURE_LOG to tmp_path).
    2. Write `tests/routine/test_llm_client.py` per implementation_sketch — ≥10 tests covering happy path, all 4 exception paths (ValidationError, APIStatusError, APIError, unknown), retry exhaustion, retry-then-success, append-only contract, record shape, truncation, no temp/top_p/top_k, provenance header.
       - Imports include `from routine.llm_client import call_with_retry, LLM_FAILURE_LOG, DEFAULT_MAX_RETRIES`.
       - Use `_make_signal()` + `_default_factory_signal()` helpers for forging valid + default-factory AgentSignals.
       - Forge ValidationError by attempting `AgentSignal(ticker='!!!', ...)` inside try/except.
       - Forge APIStatusError + APIError via subclass workaround if the SDK's __init__ requires HTTPx response objects (use `class _FakeStatus(APIStatusError): def __init__(self): pass`).
    3. Run `poetry run pytest tests/routine/test_llm_client.py -x -q` → ImportError on `routine.llm_client` (module does not exist; only `routine/__init__.py` from Wave 0).
    4. Commit (RED): `test(05-03): add failing tests for routine.llm_client.call_with_retry + mock_anthropic_client fixture (LLM-04 + LLM-05; ≥10 tests covering retry/default_factory/failure-log)`.

    GREEN:
    5. Implement `routine/llm_client.py` per implementation_sketch verbatim:
       - Provenance docstring referencing virattt/ai-hedge-fund/src/utils/llm.py per INFRA-07 + the 4 modifications.
       - Imports: `from __future__ import annotations`; stdlib (json, logging, datetime, pathlib, typing.Callable, typing.TypeVar); `from anthropic import APIError, APIStatusError, AsyncAnthropic`; `from pydantic import BaseModel, ValidationError`.
       - Module constants: `LLM_FAILURE_LOG: Path = Path("memory/llm_failures.jsonl")`; `DEFAULT_MAX_RETRIES: int = 2`; truncation constants for message + raw.
       - `T = TypeVar("T", bound=BaseModel)`.
       - `call_with_retry` async function with all 9 parameters per signature; for-loop over `range(max_retries)` with try/except trio (ValidationError → APIStatusError/APIError → bare Exception); on any exception, log + continue; on success, return `response.parsed_output`; after loop, return `default_factory()`.
       - `_try_extract_raw(exc: ValidationError) -> object` helper using `exc.errors()[0]['input']` with try/except for defensive None on extraction failure.
       - `_log_failure(label, kind, message, raw)` helper: mkdir parents, build record dict with sort_keys=True JSON, append-write to LLM_FAILURE_LOG.
    6. Run `poetry run pytest tests/routine/test_llm_client.py -v` → all ≥10 tests green.
    7. Coverage check: `poetry run pytest --cov=routine.llm_client --cov-branch tests/routine/test_llm_client.py` → ≥90% line / ≥85% branch on `routine/llm_client.py`.
    8. Phase 1-4 + Wave 0 + Wave 1 regression: `poetry run pytest -x -q` → all existing tests still GREEN. The new module is additive only.
    9. Sanity grep — provenance: `grep -n 'virattt/ai-hedge-fund/src/utils/llm.py' routine/llm_client.py` returns ≥1 match.
    10. Sanity grep — no temp/top_p/top_k: `grep -nE 'temperature=|top_p=|top_k=' routine/llm_client.py` returns ZERO matches.
    11. Sanity SDK call: `poetry run python -c "from routine.llm_client import call_with_retry, LLM_FAILURE_LOG, DEFAULT_MAX_RETRIES; assert DEFAULT_MAX_RETRIES == 2; assert str(LLM_FAILURE_LOG) == 'memory/llm_failures.jsonl' or str(LLM_FAILURE_LOG).endswith('memory/llm_failures.jsonl') or str(LLM_FAILURE_LOG).endswith('memory\\\\llm_failures.jsonl'); print('OK')"`.
    12. Commit (GREEN): `feat(05-03): routine.llm_client.call_with_retry — Anthropic SDK wrapper with retry / default_factory / append-only memory/llm_failures.jsonl (LLM-04 + LLM-05)`.
  </action>
  <verify>
    <automated>poetry run pytest tests/routine/test_llm_client.py -v && poetry run pytest --cov=routine.llm_client --cov-branch tests/routine/test_llm_client.py && poetry run pytest -x -q && grep -n 'virattt/ai-hedge-fund/src/utils/llm.py' routine/llm_client.py && python -c "import re, pathlib; src = pathlib.Path('routine/llm_client.py').read_text(encoding='utf-8'); forbidden = ['temperature=', 'top_p=', 'top_k=']; bad = [p for p in forbidden if p in src]; assert not bad, f'forbidden parameters present: {bad}'; print('no temp/top_p/top_k in call site OK')"</automated>
  </verify>
  <done>routine/llm_client.py shipped (~100-130 LOC) with call_with_retry async function + _log_failure + _try_extract_raw helpers + 4 module constants + provenance docstring referencing virattt/ai-hedge-fund/src/utils/llm.py per INFRA-07; tests/routine/conftest.py populated with MockAnthropicClient + mock_anthropic_client + isolated_failure_log fixtures (used by Wave 3-5 tests too); ≥10 tests in tests/routine/test_llm_client.py all GREEN (happy path + 4 exception paths + retry exhaustion + retry-then-success + append-only contract + record shape + truncation + no-temp-param + provenance); coverage ≥90% line / ≥85% branch on routine/llm_client.py; pytest-asyncio added to dev deps (if not already present); both commits (RED + GREEN) landed.</done>
</task>

</tasks>

<verification>
- 1 task, 2 commits (RED + GREEN). TDD discipline preserved.
- Coverage gate: ≥90% line / ≥85% branch on `routine/llm_client.py`.
- Phase 1-4 + Wave 0 + Wave 1 regression invariant: existing tests stay GREEN.
- pytest-asyncio added to [dependency-groups].dev (if not already present); `asyncio_mode = "auto"` configured in [tool.pytest.ini_options] for ergonomic async test discovery.
- routine/llm_client.py never passes temperature/top_p/top_k to messages.parse (Opus 4.7 400-rejection guard per Pattern #2; verified by grep test).
- Failure log discipline: append-only JSONL, sort_keys serialization, UTC timestamps, message ≤1000 chars + raw ≤5000 chars truncation, mkdir parents on memory/ dir.
- Default-factory contract: invoked exactly ONCE on retry exhaustion; never invoked when any retry succeeds.
- mock_anthropic_client fixture is reusable by Wave 3-5 tests (persona_runner / synthesizer_runner / entrypoint integration).
- isolated_failure_log autouse fixture per-test isolates the JSONL file in tmp_path; no test pollutes the real memory/ dir.
- Wave 3 (05-04 persona runner) unblocked: imports `call_with_retry` + uses `mock_anthropic_client` fixture for persona-call tests.
- Wave 4 (05-05 synthesizer) unblocked: imports `call_with_retry` + uses same fixtures.
- Wave 5 (05-06 entrypoint integration) unblocked: integration tests use the same mock client to drive the full pipeline.

## Cross-Scope Risks

_vault_status=budget_exhausted; re-run /gmd:plan-phase --replan after vault-maintain_
</verification>

<success_criteria>
1. `routine/llm_client.py` exports `call_with_retry` (async generic over T bound=BaseModel) + `LLM_FAILURE_LOG` (Path) + `DEFAULT_MAX_RETRIES` (int=2).
2. `call_with_retry` signature accepts: client, model, system, user, output_format, default_factory, max_tokens, max_retries=DEFAULT_MAX_RETRIES, context_label.
3. On `pydantic.ValidationError`: log to memory/llm_failures.jsonl with kind='validation_error' AND raw extracted via `_try_extract_raw`; retry; on exhaustion return `default_factory()`.
4. On `anthropic.APIStatusError` OR `anthropic.APIError`: log with kind='api_error'; retry; on exhaustion return default_factory.
5. On any other Exception: log with kind='unknown_error' (defensive cascade prevention); retry; on exhaustion return default_factory.
6. `_log_failure` records have EXACTLY 5 keys: timestamp, label, kind, message, raw — sort_keys=True serialization; UTC timestamps; mkdir parents on parent dir.
7. NEVER passes temperature/top_p/top_k to messages.parse — verified via grep test (Opus 4.7 400-rejection guard).
8. tests/routine/conftest.py populated with MockAnthropicClient + mock_anthropic_client per-test fixture + isolated_failure_log autouse fixture (Wave 3-5 reuse this).
9. ≥10 tests in tests/routine/test_llm_client.py, all GREEN — covers happy path; ValidationError → retry → success; ValidationError exhaustion; APIStatusError; APIError; unknown exception; failure log append-only across invocations; record shape (5 keys, UTC, sort_keys); message + raw truncation; no temp/top_p/top_k AST grep; provenance header.
10. Coverage ≥90% line / ≥85% branch on routine/llm_client.py.
11. Provenance per INFRA-07: routine/llm_client.py docstring contains literal substring `virattt/ai-hedge-fund/src/utils/llm.py`.
12. Full repo regression GREEN (Phase 1 + Phase 2 + Phase 3 + Phase 4 + Wave 0 + Wave 1 + this plan).
13. pytest-asyncio configured (auto-mode); async tests run cleanly.
14. Wave 3 + Wave 4 + Wave 5 unblocked — call_with_retry + mock fixtures available.
</success_criteria>

<output>
After completion, create `.planning/phases/05-claude-routine-wiring/05-03-SUMMARY.md` summarizing the 2 commits, naming the call_with_retry contract (3 module constants + 1 async function + 2 helpers + 4 exception-path branches), the mock fixture-replay pattern (reused by Waves 3-5), and the append-only failure-log discipline (memory/llm_failures.jsonl with sort_keys + UTC timestamps + truncation). Reference 05-04 (persona runner) and 05-05 (synthesizer) as immediate downstream Wave 3 + Wave 4 consumers.

Update `.planning/STATE.md` Recent Decisions with a 05-03 entry naming: routine.llm_client.call_with_retry — Anthropic SDK wrapper with constrained-decoding via messages.parse(output_format=PydanticModel) per Pattern #2; retry policy = 2 attempts (DEFAULT_MAX_RETRIES); 4 exception-path branches (ValidationError / APIStatusError / APIError / unknown); append-only failure log at memory/llm_failures.jsonl per Pattern #8 + LLM-05; mock_anthropic_client fixture-replay pattern landed in tests/routine/conftest.py (reused by Waves 3-5); pytest-asyncio added; Wave 3 (05-04 persona runner) + Wave 4 (05-05 synthesizer) unblocked.
</output>
</content>
</invoke>