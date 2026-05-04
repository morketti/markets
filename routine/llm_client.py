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
    parallel via asyncio.gather; sync would 6x wall-clock per ticker.
  * Single LLM vendor (Claude only); no provider abstraction. Matches
    PROJECT.md "All LLM I/O is Claude only" lock.

Failure handling per 05-RESEARCH.md Pattern #8:
  * pydantic.ValidationError (constrained-decoding produced JSON-shape-valid
    output that nonetheless violates a Pydantic semantic validator — e.g.,
    a min_length=1 list field with an empty list) -> retry once -> if still
    failing, return default_factory() and log to memory/llm_failures.jsonl.
  * anthropic.APIStatusError (429 rate-limit / 5xx server errors) -> retry ->
    return default_factory() on exhaustion.
  * anthropic.APIError (network errors, malformed body, etc.) -> same as
    APIStatusError.
  * Any other unexpected exception -> defensive catch -> log as
    'unknown_error' kind -> retry -> default_factory() on exhaustion. We never
    let an unexpected exception propagate out of call_with_retry; the per-
    ticker pipeline must continue.

LLM-05 contract: on validation failure (any kind) the raw response (when
available — only on ValidationError, via _try_extract_raw) is logged to
memory/llm_failures.jsonl along with timestamp + label + kind + message.
Append-only.

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
_MESSAGE_TRUNCATION_LIMIT: int = 1000
_RAW_TRUNCATION_LIMIT: int = 5000

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
    client
        Pre-instantiated AsyncAnthropic SDK client (entrypoint owns lifecycle).
    model
        Claude model ID — "claude-sonnet-4-6" for personas, "claude-opus-4-7"
        for synthesizer per Pattern #2.
    system
        System prompt — for personas, the markdown-loaded persona prompt; for
        synthesizer, the synthesizer prompt.
    user
        User-message content — per-ticker context dict serialized to a string.
    output_format
        Pydantic model class to use for constrained decoding + validation.
        T is bound to BaseModel (generic over the output type).
    default_factory
        Zero-arg callable returning a T instance — used when all retries
        exhausted. Closure captures ticker/persona_id/computed_at from caller
        so the factory produces a contextually-correct default (LLM-05).
    max_tokens
        Per-call max output tokens — 2000 for personas, 4000 for synthesizer.
    max_retries
        Total attempt count (NOT retries beyond the first attempt). Default 2
        keeps cost predictable per Pattern #8.
    context_label
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

    for _attempt in range(max_retries):
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
            raw = _try_extract_raw(e)
            _log_failure(context_label, "validation_error", str(e), raw)
        except (APIStatusError, APIError) as e:
            last_exc = e
            _log_failure(context_label, "api_error", str(e), None)
        except Exception as e:  # noqa: BLE001 — defensive cascade prevention
            last_exc = e
            _log_failure(context_label, "unknown_error", repr(e), None)

    # All retries exhausted — return default factory; log the cascade once.
    logger.warning(
        "llm_client(%s) exhausted %d retries; returning default_factory. last: %r",
        context_label,
        max_retries,
        last_exc,
    )
    return default_factory()


def _try_extract_raw(exc: ValidationError) -> object:
    """Best-effort extraction of raw response from a ValidationError.

    Pydantic v2's ValidationError.errors() returns a list of error dicts; each
    dict carries an 'input' key (the offending value) when available. We pull
    the first error's input as the raw — which for SDK-emitted ValidationErrors
    is typically the offending sub-tree of the parsed JSON. Best-effort: returns
    None on any extraction failure (broad exception catch is intentional).
    """
    try:
        errs = exc.errors()
        if errs and isinstance(errs[0], dict) and "input" in errs[0]:
            return errs[0]["input"]
    except Exception:  # noqa: BLE001 — extraction is best-effort only
        return None
    return None


def _log_failure(label: str, kind: str, message: str, raw: object) -> None:
    """Append failure record to memory/llm_failures.jsonl (append-only).

    Record fields (EXACTLY 5 top-level keys):
      timestamp — ISO-8601 UTC (timezone-aware via datetime.now(timezone.utc))
      label     — caller-supplied context_label (e.g. 'buffett:AAPL')
      kind      — one of {'validation_error', 'api_error', 'unknown_error'}
      message   — exception text, truncated to <=1000 chars
      raw       — extracted raw response (ValidationError only) or None;
                  truncated to <=5000 chars

    Serialization uses sort_keys=True for stable byte-identical lines (mirrors
    Phase 1/2 atomic-write discipline). Parent directory is created via
    mkdir(parents=True, exist_ok=True) so the very first call on a clean repo
    bootstraps memory/ cleanly.
    """
    LLM_FAILURE_LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "label": label,
        "kind": kind,
        "message": message[:_MESSAGE_TRUNCATION_LIMIT],
        "raw": (
            str(raw)[:_RAW_TRUNCATION_LIMIT] if raw is not None else None
        ),
    }
    line = json.dumps(record, sort_keys=True) + "\n"
    with LLM_FAILURE_LOG.open("a", encoding="utf-8") as f:
        f.write(line)
