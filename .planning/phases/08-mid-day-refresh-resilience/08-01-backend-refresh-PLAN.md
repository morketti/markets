---
phase: 08-mid-day-refresh-resilience
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - api/refresh.py
  - vercel.json
  - frontend/vercel.json
  - tests/api/__init__.py
  - tests/api/test_refresh.py
  - routine/memory_log.py
  - routine/run_for_watchlist.py
  - tests/routine/test_memory_log.py
  - tests/routine/test_run_for_watchlist.py
  - scripts/__init__.py
  - scripts/check_provenance.py
  - tests/scripts/__init__.py
  - tests/scripts/test_check_provenance.py
  - .pre-commit-config.yaml
  - tests/ingestion/test_prices.py
  - tests/ingestion/test_news.py
  - .gitignore
autonomous: true
requirements: [REFRESH-01, REFRESH-04, INFRA-06, INFRA-07]

must_haves:
  truths:
    - "GET /api/refresh?ticker=AAPL returns valid JSON within Vercel maxDuration=30s budget for happy / partial / full-failure cases"
    - "yfinance throws -> yahooquery fallback rescues -> snapshot saves with no error (verified by resilience test)"
    - "Both yfinance + yahooquery throw -> snapshot saves with data_unavailable=True + clear error (verified by resilience test)"
    - "RSS unavailable -> fetch_news returns ([], 0.0) and refresh function returns partial: true with errors=['rss-unavailable']"
    - "memory/historical_signals.jsonl gets one record per (ticker, persona) appended every routine run"
    - "scripts/check_provenance.py walks analysts/, routine/, synthesis/, ingestion/, prompts/personas/*.md, prompts/synthesizer.md and accepts 3 marker forms; existing codebase passes (or is fixed if any file lacks a marker)"
    - "Pre-commit hook + the same script invokable in CI fail loudly when a tracked file lacks a provenance marker"
    - "vercel.json at repo root configures api/refresh.py with maxDuration=30; frontend/vercel.json SPA rewrite is narrowed to /((?!api/).*) so /api/* requests are NOT silently rewritten to index.html"
  artifacts:
    - path: api/refresh.py
      provides: "Vercel Python serverless handler exposing GET /api/refresh?ticker=X"
      contains: "class handler(BaseHTTPRequestHandler)"
    - path: vercel.json
      provides: "Repo-root Vercel config — api/refresh.py maxDuration=30"
      contains: "\"functions\""
    - path: frontend/vercel.json
      provides: "SPA rewrite narrowed so /api/* is NOT rewritten to /index.html"
      contains: "/((?!api/).*)"
    - path: routine/memory_log.py
      provides: "append_memory_record(date, ticker, persona_id, verdict, confidence, evidence_count) writing JSONL"
      contains: "def append_memory_record"
    - path: routine/run_for_watchlist.py
      provides: "Phase E memory log write per (ticker, persona) after persona pipeline"
      contains: "append_memory_record"
    - path: scripts/check_provenance.py
      provides: "CLI that walks tracked Python + persona prompt files, asserts presence of one provenance marker form, exits non-zero on offenders"
      contains: "def main"
    - path: .pre-commit-config.yaml
      provides: "Pre-commit hook entry invoking scripts/check_provenance.py"
      contains: "scripts/check_provenance.py"
    - path: tests/api/test_refresh.py
      provides: "8-10 tests covering happy path + 4 failure modes + timeout simulation"
      min_lines: 130
    - path: tests/routine/test_memory_log.py
      provides: "JSONL contract + atomic append + record schema + Phase E integration via test_run_for_watchlist extension"
      min_lines: 70
    - path: tests/scripts/test_check_provenance.py
      provides: "Accept/reject regex tests for the 3 marker forms + offender list output"
      min_lines: 60
  key_links:
    - from: api/refresh.py
      to: ingestion.prices.fetch_prices
      via: "sys.path.insert(0, repo_root) then `from ingestion.prices import fetch_prices`"
      pattern: "from ingestion\\.prices import fetch_prices"
    - from: api/refresh.py
      to: ingestion.news.fetch_news
      via: "fetch_news(ticker, return_raw=True) returning (headlines, sentiment_score) — refresh uses headlines list only"
      pattern: "fetch_news\\(.*return_raw=True"
    - from: routine/memory_log.py
      to: routine.llm_client._log_failure
      via: "Same atomic-append pattern (mkdir parents=True; open mode='a'; json.dumps sort_keys=True; one record per line)"
      pattern: "open\\(.*['\"]a['\"]"
    - from: routine/run_for_watchlist.py
      to: routine.memory_log.append_memory_record
      via: "Phase E: after _run_one_ticker returns persona_signals, loop over them and call append_memory_record per (ticker, persona)"
      pattern: "append_memory_record"
    - from: .pre-commit-config.yaml
      to: scripts/check_provenance.py
      via: "local hook entry running `python scripts/check_provenance.py`"
      pattern: "check_provenance"
---

<objective>
Wave 0 — Backend refresh function + memory log + provenance + ingestion resilience.

Purpose: Stand up the load-bearing backend pieces of Phase 8 — the Vercel Python serverless function that powers on-open refresh, the per-run JSONL memory log that v1.x trend surfacing will consume, and the provenance check that codifies INFRA-07 — plus codify the existing yfinance+yahooquery and RSS resilience into explicit failure-mode tests. Wave 1 (frontend) builds against the deployed function shape.

Output: api/refresh.py + vercel.json (root) + frontend/vercel.json narrowing + routine/memory_log.py + routine/run_for_watchlist.py Phase E hook + scripts/check_provenance.py + .pre-commit-config.yaml + tests across tests/api/, tests/routine/, tests/scripts/, plus 3 new resilience tests in tests/ingestion/. Closes REFRESH-01, INFRA-06, INFRA-07; closes REFRESH-04 backend portion (frontend half closes in 08-02).
</objective>

<execution_context>
@C:/Users/Mohan/.claude/workflows/execute-plan.md
@C:/Users/Mohan/.claude/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/08-mid-day-refresh-resilience/08-CONTEXT.md
@.planning/phases/08-mid-day-refresh-resilience/08-RESEARCH.md
@.planning/phases/08-mid-day-refresh-resilience/08-VALIDATION.md

# Reusable assets — extract patterns from these:
@ingestion/prices.py
@ingestion/news.py
@routine/llm_client.py
@routine/run_for_watchlist.py

<interfaces>
<!-- Contracts the executor will consume directly. NO codebase exploration needed. -->

From `ingestion/prices.py` (existing — DO NOT MODIFY in this plan):
```python
def fetch_prices(ticker: str, *, period: str = "1y") -> PriceSnapshot:
    """Always returns a PriceSnapshot. Sets data_unavailable=True when both
    yfinance + yahooquery fail. NEVER raises for upstream breakage; only
    Pydantic ValidationError can escape (programmer bug, not runtime)."""

# PriceSnapshot relevant fields (from analysts/data/prices.py):
class PriceSnapshot(BaseModel):
    ticker: str
    current_price: float | None        # None when data_unavailable
    fetched_at: datetime               # tz-aware UTC
    data_unavailable: bool = False
    history: list[OHLCBar]             # may be empty when data_unavailable
```

From `ingestion/news.py` (existing — DO NOT MODIFY in this plan):
```python
@overload
def fetch_news(ticker: str, *, dedup_window_days: int = 7) -> list[Headline]: ...
@overload
def fetch_news(
    ticker: str, *, dedup_window_days: int = 7, return_raw: bool = True,
) -> tuple[list[Headline], float]:
    """When return_raw=True: returns (headlines_list, sentiment_score).
    Each source helper returns [] on any failure. Aggregation never raises."""
```

From `routine/llm_client.py` line 167 — the JSONL append pattern memory_log.py mirrors verbatim:
```python
def _log_failure(label: str, kind: str, message: str, raw: object) -> None:
    LLM_FAILURE_LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "label": label,
        "kind": kind,
        "message": message[:_MESSAGE_TRUNCATION_LIMIT],
        "raw": str(raw)[:_RAW_TRUNCATION_LIMIT] if raw is not None else None,
    }
    line = json.dumps(record, sort_keys=True) + "\n"
    with LLM_FAILURE_LOG.open("a", encoding="utf-8") as f:
        f.write(line)
```

From `routine/run_for_watchlist.py`:
```python
async def _run_one_ticker(
    client, ticker_config, snapshot, *, lite_mode, computed_at,
) -> TickerResult:
    # ... returns TickerResult with persona_signals: list[AgentSignal]

# AgentSignal relevant fields (from analysts/signals.py):
class AgentSignal(BaseModel):
    analyst_id: str          # 'buffett' / 'munger' / 'wood' / 'burry' / 'lynch' / 'claude_analyst'
    signal: Literal['strong_bullish','bullish','neutral','bearish','strong_bearish']
    confidence: int          # 0-100
    evidence: list[str]      # <=10 items
```

Vercel Python runtime entrypoint convention:
```python
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        # parse self.path; write self.send_response(...); self.wfile.write(json_bytes)
        ...
```

Refresh response shapes (LOCKED in 08-CONTEXT.md):
```jsonc
// SUCCESS
{"ticker":"AAPL","current_price":178.42,"price_timestamp":"...","recent_headlines":[...],"errors":[],"partial":false}
// PARTIAL (RSS unavailable)
{"ticker":"AAPL","current_price":178.42,"price_timestamp":"...","recent_headlines":[],"errors":["rss-unavailable"],"partial":true}
// FULL FAILURE (yfinance + yahooquery both throw or data_unavailable)
{"ticker":"AAPL","error":true,"errors":["yfinance-unavailable","yahooquery-unavailable"],"partial":true}
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: api/refresh.py Vercel function + vercel.json + SPA-narrowing fix + tests</name>
  <files>api/refresh.py, vercel.json, frontend/vercel.json, tests/api/__init__.py, tests/api/test_refresh.py</files>
  <behavior>
    Test surface (8-10 cases in tests/api/test_refresh.py — all use monkeypatch to stub `ingestion.prices.fetch_prices` and `ingestion.news.fetch_news` so the tests are pure-Python and never hit the network):

    1. **happy_path** — fetch_prices stub returns PriceSnapshot(current_price=178.42, fetched_at=tz-aware UTC, data_unavailable=False). fetch_news stub returns ([Headline(...), Headline(...)], 0.0). Invoke handler.do_GET via a fabricated request (use `unittest.mock.MagicMock` for self.wfile / self.headers / self.send_response, OR import handler and call do_GET against a fixture-constructed instance — pick whichever is simpler). Assert response status=200, JSON parses, body == `{"ticker":"AAPL","current_price":178.42,"price_timestamp":"...","recent_headlines":[{"source":...,"published_at":...,"title":...,"url":...}, ...],"errors":[],"partial":false}`. Verify recent_headlines preserves the 4-key Headline shape.
    2. **missing_ticker_param** — request path `/api/refresh` (no ?ticker=). Status=400, body contains `errors: ["missing-ticker-param"]`.
    3. **invalid_ticker** — `?ticker=` (empty). Status=400, errors=["invalid-ticker"].
    4. **rss_unavailable** — fetch_prices stub OK; fetch_news stub returns ([], 0.0). Status=200, body partial=true, errors=["rss-unavailable"], current_price still set, recent_headlines=[].
    5. **price_data_unavailable** — fetch_prices stub returns PriceSnapshot with data_unavailable=True; fetch_news returns headlines fine. Status=200, body has `error: true`, partial=true, errors contains "yfinance-unavailable" AND "yahooquery-unavailable", no current_price field (or current_price=None — pick one shape and lock it).
    6. **both_data_layers_fail** — fetch_prices data_unavailable=True AND fetch_news returns ([], 0.0). Status=200, body error=true, partial=true, errors=["yfinance-unavailable","yahooquery-unavailable","rss-unavailable"].
    7. **fetch_prices_raises** — fetch_prices stub raises a RuntimeError (defensive — fetch_prices SHOULD never raise but the function must be hardened anyway). Status=200 with error=true, errors contains "yfinance-unavailable".
    8. **fetch_news_raises** — fetch_news stub raises RuntimeError. Status=200, partial=true, errors=["rss-unavailable"], current_price still set.
    9. **timeout_simulation** — Use `unittest.mock.patch` to wrap fetch_prices in a `time.sleep` that exceeds a small test budget (e.g. 2s with a 1s test cap), wrap the handler call in a wrapper that enforces the timeout via concurrent.futures or signal — assert handler returns partial response with errors containing "timeout" rather than hanging. (Implementation note: Vercel's actual timeout is enforced by the platform, not by Python code; the in-process timeout wrapper just verifies our error envelope is correct WHEN we explicitly return one. If wrapping the handler in a timeout-enforcer is too brittle, fall back to a stub that has fetch_prices return an "errors" entry and skip the wall-clock simulation.)
    10. **headlines_serialize_correctly** — fetch_news returns `[Headline(source="Reuters", published_at=datetime(2026,5,4,19,32,11,tzinfo=UTC), title="...", url="...")]`. Body's recent_headlines[0] has keys exactly {source, published_at, title, url}, published_at is ISO-8601 string with UTC offset.

    All tests run against a stubbed Headline import and `tests/api/__init__.py` exists so pytest discovers the package.
  </behavior>
  <action>
    Create `api/refresh.py` (~80 LOC) — Vercel Python serverless handler.

    **File header (REQUIRED — INFRA-07 provenance marker):**
    ```python
    # novel-to-this-project — Vercel Python serverless adapter; thin wrapper
    # over ingestion.prices.fetch_prices + ingestion.news.fetch_news. NO LLM
    # calls. Designed for sub-10s execution under Vercel's 30s maxDuration cap.
    ```

    **Imports + sys.path setup** (Vercel runtime can't `import` sibling top-level packages by default):
    ```python
    from __future__ import annotations
    import json
    import sys
    from http.server import BaseHTTPRequestHandler
    from pathlib import Path
    from urllib.parse import urlparse, parse_qs

    # Prepend repo root so `from ingestion.prices import fetch_prices` works
    # under Vercel's serverless Python runtime. The function file sits at
    # api/refresh.py; repo_root is parents[1].
    _REPO_ROOT = Path(__file__).resolve().parents[1]
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

    from ingestion.prices import fetch_prices  # noqa: E402
    from ingestion.news import fetch_news      # noqa: E402
    ```

    **Handler class — Vercel naming convention `handler` (lowercase):**
    ```python
    class handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            try:
                payload, status = _build_response(self.path)
            except Exception as exc:  # noqa: BLE001 — defensive top-level
                payload = {"error": True, "errors": [f"unhandled: {exc!r}"], "partial": True}
                status = 500
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
    ```

    **Pure builder for testability — `_build_response(path: str) -> tuple[dict, int]`:**
    1. Parse `?ticker=`. Empty / missing → return `({"error": True, "errors": ["missing-ticker-param"]}, 400)` or `["invalid-ticker"]` for empty string.
    2. Normalize ticker via `analysts.schemas.normalize_ticker` (uppercase + strip — already used by ingestion modules).
    3. Call `fetch_prices(ticker, period="1d")` inside try/except. On exception OR `snap.data_unavailable=True`: errors += ["yfinance-unavailable", "yahooquery-unavailable"], current_price=None, price_timestamp=None.
    4. Call `fetch_news(ticker, return_raw=True)` inside try/except. On exception OR empty headlines list: errors += ["rss-unavailable"], recent_headlines=[]. Otherwise serialize each Headline to `{source, published_at, title, url}` (use `h.model_dump(mode="json")` for ISO-8601 string).
    5. Compose response dict per the locked shapes. `partial = bool(errors)`. Set `error: True` ONLY when current_price is None (full failure shape).
    6. Status: 200 for success/partial/full-failure-with-error-envelope. 400 ONLY for missing/invalid ticker param.

    **NO CORS headers** (same-origin per LOCK in 08-CONTEXT.md).
    **NO LLM calls.**

    Create `vercel.json` at repo root:
    ```json
    {
      "functions": {
        "api/refresh.py": {
          "maxDuration": 30
        }
      }
    }
    ```

    Modify `frontend/vercel.json` — narrow the SPA rewrite from `/(.*)` to `/((?!api/).*)`:
    ```json
    {
      "framework": "vite",
      "installCommand": "pnpm install",
      "buildCommand": "pnpm build",
      "outputDirectory": "dist",
      "rewrites": [
        { "source": "/((?!api/).*)", "destination": "/index.html" }
      ]
    }
    ```

    Create `tests/api/__init__.py` (empty file — package marker).

    Create `tests/api/test_refresh.py` (~150 LOC) implementing the 10 test cases above. Use `monkeypatch.setattr` to stub `api.refresh.fetch_prices` and `api.refresh.fetch_news`. For the handler-invocation pattern, the cleanest approach is:

    ```python
    from io import BytesIO
    from unittest.mock import MagicMock
    from api.refresh import handler, _build_response

    def _invoke(path):
        # Test the pure builder directly (preferred — no HTTP plumbing).
        return _build_response(path)
    ```

    Most tests should drive `_build_response` directly; reserve 1-2 tests for the full `do_GET` path (validates send_response / wfile.write integration via MagicMock).

    Verify the file you wrote passes `python scripts/check_provenance.py` once Task 3 lands — the `# novel-to-this-project` header is required.
  </action>
  <verify>
    <automated>uv run pytest tests/api/ -q</automated>
  </verify>
  <done>
    All 10 tests in tests/api/test_refresh.py pass. api/refresh.py + vercel.json + frontend/vercel.json updated. _build_response covers all 4 failure modes (missing ticker, RSS unavailable, price unavailable, both unavailable) + happy path + headline serialization. The narrowed SPA rewrite is in place (verified by inspecting frontend/vercel.json — `/((?!api/).*)`).
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: routine/memory_log.py + run_for_watchlist Phase E + tests</name>
  <files>routine/memory_log.py, routine/run_for_watchlist.py, tests/routine/test_memory_log.py, tests/routine/test_run_for_watchlist.py, .gitignore</files>
  <behavior>
    Test surface in `tests/routine/test_memory_log.py` (~80 LOC, ~10 tests):

    1. **append_single_record_writes_one_jsonl_line** — Call `append_memory_record(date="2026-05-04", ticker="AAPL", persona_id="buffett", verdict="bullish", confidence=72, evidence_count=3, log_path=tmp_path/"memory/historical_signals.jsonl")`. File exists; contains exactly one line; `json.loads(line) == {"date":"2026-05-04","ticker":"AAPL","persona_id":"buffett","verdict":"bullish","confidence":72,"evidence_count":3}`.
    2. **multiple_records_append_not_overwrite** — Two calls with different (ticker, persona). File has 2 lines; both records preserved; iteration order matches call order.
    3. **parent_directory_auto_created** — Pass log_path under `tmp_path/"new/dir/file.jsonl"` (parent doesn't exist). Function creates `new/dir/` via `mkdir(parents=True, exist_ok=True)` and writes successfully.
    4. **sort_keys_stable_serialization** — Two calls with the same record passed via different dict insertion orders both produce byte-identical lines (sort_keys=True discipline matches `_log_failure` line 167).
    5. **schema_strictness** — Calling with confidence=-1 OR confidence=101 OR verdict="invalid" raises ValueError (defensive — Pydantic-equivalent runtime validation in pure-Python form, OR use a Pydantic BaseModel internally). Pick one approach and lock it; tests assert the chosen behavior.
    6. **truncation_long_evidence_count** — evidence_count is an int 0-10 (matches AgentSignal max 10 evidence). evidence_count=11 raises (consistent with schema lock).
    7. **utc_date_format** — Date string MUST be YYYY-MM-DD (10 chars). Pass "2026-5-4" → ValueError.

    Test surface in `tests/routine/test_run_for_watchlist.py` extension (~3 new tests appended to existing file):

    8. **phase_e_writes_one_record_per_persona** — Construct a 1-ticker watchlist; mock the persona slate to return 6 AgentSignals (one per persona_id in PERSONA_IDS). Run `run_for_watchlist(...)`. Assert `memory/historical_signals.jsonl` (or test-injected path) has exactly 6 lines, one per (ticker="AAPL", persona_id) combination.
    9. **lite_mode_skips_phase_e** — Run with `lite_mode=True` (no persona signals). Assert NO memory log entries written for the LLM personas (verifies the Phase E hook is gated by lite_mode).
    10. **phase_e_per_ticker_failure_skips_log** — Per-ticker pipeline raises (TickerResult.errors set, persona_signals=[]). Assert no memory log records written for that ticker — phase E only fires when persona_signals is populated.

    All run_for_watchlist tests inject the log path via a new optional `memory_log_path: Path | None = None` parameter on `run_for_watchlist` (defaults to `Path("memory/historical_signals.jsonl")`).
  </behavior>
  <action>
    Create `routine/memory_log.py` (~70 LOC).

    **File header:**
    ```python
    # Pattern adapted from routine/llm_client._log_failure (line 167) — same
    # atomic JSONL-append discipline (mkdir parents=True; mode="a"; sort_keys=True;
    # one record per line). Diverges only in the record schema.
    ```

    **Module body:**
    ```python
    """routine.memory_log — append-only JSONL writer for per-(ticker, persona)
    signal history. INFRA-06 implementation.

    Schema (LOCKED — 08-CONTEXT.md):
        {"date": "YYYY-MM-DD", "ticker": "AAPL", "persona_id": "buffett",
         "verdict": "bullish", "confidence": 72, "evidence_count": 3}

    Called from routine.run_for_watchlist Phase E after the per-ticker
    persona pipeline produces 6 AgentSignals. ~30 tickers x 6 personas = 180
    records/day. ~65K records/year ≈ ~10 MB JSONL — append every run
    (researcher rec #2: change-detection adds complexity without trivial-
    storage payoff).

    File location (default): memory/historical_signals.jsonl (gitignored).
    Tests inject a tmp_path via the log_path parameter.
    """
    from __future__ import annotations

    import json
    import re
    from pathlib import Path
    from typing import Final

    DEFAULT_LOG_PATH: Final[Path] = Path("memory/historical_signals.jsonl")

    _DATE_RE: Final[re.Pattern[str]] = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    _VALID_VERDICTS: Final[frozenset[str]] = frozenset({
        "strong_bullish", "bullish", "neutral", "bearish", "strong_bearish",
    })

    def append_memory_record(
        *,
        date: str,
        ticker: str,
        persona_id: str,
        verdict: str,
        confidence: int,
        evidence_count: int,
        log_path: Path | None = None,
    ) -> None:
        """Append one record to memory/historical_signals.jsonl.

        Validates inputs synchronously (raises ValueError on invalid). Mirrors
        the _log_failure atomic-append + sort_keys=True pattern.
        """
        if not _DATE_RE.match(date):
            raise ValueError(f"date must be YYYY-MM-DD, got {date!r}")
        if not ticker or not ticker.isupper():
            raise ValueError(f"ticker must be non-empty uppercase, got {ticker!r}")
        if not persona_id:
            raise ValueError("persona_id required")
        if verdict not in _VALID_VERDICTS:
            raise ValueError(
                f"verdict must be one of {sorted(_VALID_VERDICTS)}, got {verdict!r}"
            )
        if not (0 <= confidence <= 100):
            raise ValueError(f"confidence must be 0-100, got {confidence!r}")
        if not (0 <= evidence_count <= 10):
            raise ValueError(f"evidence_count must be 0-10, got {evidence_count!r}")

        path = log_path if log_path is not None else DEFAULT_LOG_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "date": date,
            "ticker": ticker,
            "persona_id": persona_id,
            "verdict": verdict,
            "confidence": confidence,
            "evidence_count": evidence_count,
        }
        line = json.dumps(record, sort_keys=True) + "\n"
        with path.open("a", encoding="utf-8") as f:
            f.write(line)
    ```

    Modify `routine/run_for_watchlist.py` — add Phase E after `_run_one_ticker` returns:

    1. Add `from routine.memory_log import append_memory_record, DEFAULT_LOG_PATH` to imports.
    2. Extend `run_for_watchlist(...)` signature with `memory_log_path: Path | None = None` parameter (defaults to None; downstream uses DEFAULT_LOG_PATH).
    3. After the per-ticker `result = TickerResult(...)` is appended, run Phase E **only when** `result.persona_signals` is non-empty (skips lite_mode AND per-ticker failures):
       ```python
       # Phase E — INFRA-06 memory log. Skip when persona_signals empty
       # (lite_mode quota guard OR per-ticker pipeline failure both leave the
       # list empty). One record per (ticker, persona).
       if result.persona_signals:
           date_str = computed_at.date().isoformat()
           for persona_signal in result.persona_signals:
               try:
                   append_memory_record(
                       date=date_str,
                       ticker=result.ticker,
                       persona_id=persona_signal.analyst_id,
                       verdict=persona_signal.signal,
                       confidence=persona_signal.confidence,
                       evidence_count=len(persona_signal.evidence),
                       log_path=memory_log_path,
                   )
               except Exception as exc:  # noqa: BLE001
                   logger.warning(
                       "memory_log append failed for %s/%s: %r",
                       result.ticker, persona_signal.analyst_id, exc,
                   )
                   # Memory log failure is non-fatal — routine continues.
       ```
    4. Update the existing module docstring's "Per-ticker pipeline" comment block to enumerate Phase E.

    Update `.gitignore` — add:
    ```
    # Phase 8 — memory log (local-only by default; v1.x revisits GitHub-write)
    memory/historical_signals.jsonl
    memory/llm_failures.jsonl
    ```

    Create `tests/routine/test_memory_log.py` implementing tests 1-7. Use pytest's `tmp_path` fixture + monkeypatch for log_path injection.

    Extend `tests/routine/test_run_for_watchlist.py` — APPEND tests 8-10 (DO NOT replace existing tests; this file already has ~50 tests from Phase 5). Build TickerResults with mock persona_signals using existing test fixtures from `tests/routine/conftest.py` (the MockAnthropicClient pattern).
  </action>
  <verify>
    <automated>uv run pytest tests/routine/test_memory_log.py tests/routine/test_run_for_watchlist.py -q</automated>
  </verify>
  <done>
    All ~10 memory_log tests pass + 3 new run_for_watchlist tests pass. routine/memory_log.py exists with the 7-arg signature and atomic-append discipline. routine/run_for_watchlist.py Phase E hook fires once per (ticker, persona) when persona_signals non-empty, skipped in lite_mode and on per-ticker failure. memory/*.jsonl gitignored.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: scripts/check_provenance.py + pre-commit + ingestion resilience tests + codebase audit</name>
  <files>scripts/__init__.py, scripts/check_provenance.py, tests/scripts/__init__.py, tests/scripts/test_check_provenance.py, .pre-commit-config.yaml, tests/ingestion/test_prices.py, tests/ingestion/test_news.py</files>
  <behavior>
    Test surface in `tests/scripts/test_check_provenance.py` (~80 LOC, ~10 tests):

    1. **accepts_pattern_adapted_from** — Write a temp file with `# Pattern adapted from virattt/ai-hedge-fund/src/agents/x.py` in line 1. `check_file(path)` returns `None` (no offender).
    2. **accepts_adapted_from_short_form** — `# Adapted from TauricResearch/TradingAgents/...`. Returns None.
    3. **accepts_novel_to_this_project** — `# novel-to-this-project — orchestration glue`. Returns None.
    4. **accepts_marker_anywhere_in_first_30_lines** — Marker on line 7 (after a docstring). Returns None.
    5. **rejects_marker_at_line_31_or_later** — Marker on line 31. Returns offender record.
    6. **rejects_no_marker** — File with zero markers. Returns offender record with the file path + "missing provenance marker (one of: ...)".
    7. **markdown_html_comment_form_accepted** — `<!-- Pattern adapted from ... -->` in a `.md` file. Returns None.
    8. **walks_correct_directories** — `main()` walks `analysts/`, `routine/`, `synthesis/`, `ingestion/`, `prompts/personas/*.md`, `prompts/synthesizer.md`, `api/`, `scripts/`. Skips `tests/`, `frontend/`, `__pycache__`. Test by giving a temp directory tree mirroring this layout.
    9. **exit_code_zero_when_clean** — `main(roots=[clean_tree])` returns 0; prints nothing or success summary.
    10. **exit_code_one_when_offenders** — `main(roots=[tree_with_offender])` returns 1; prints offender list to stderr in the format `<path>: missing provenance marker`.

    Test surface in `tests/ingestion/test_prices.py` (~2 new resilience tests appended):

    11. **yfinance_throws_yahooquery_rescues** — monkeypatch yfinance.Ticker to raise on `.history()` call; monkeypatch yahooquery.Ticker to return valid data. Assert `fetch_prices(...)` returns PriceSnapshot with current_price set + data_unavailable=False (the yahooquery fallback rescued).
    12. **both_yfinance_and_yahooquery_throw** — Both raise. Assert returned PriceSnapshot has `data_unavailable=True` and current_price=None. The function MUST NOT raise.

    Test surface in `tests/ingestion/test_news.py` (~1 new resilience test appended):

    13. **all_rss_sources_unavailable** — monkeypatch `requests.get` (or `feedparser.parse`) to raise on every URL; monkeypatch the FinViz scrape similarly. Assert `fetch_news("AAPL")` returns `[]` AND `fetch_news("AAPL", return_raw=True)` returns `([], 0.0)`. Function MUST NOT raise.
  </behavior>
  <action>
    Create `scripts/__init__.py` (empty package marker — Python needs this for tests/scripts/ to import scripts/).

    Create `scripts/check_provenance.py` (~140 LOC).

    **File header:**
    ```python
    # novel-to-this-project — INFRA-07 enforcement: walks tracked source files,
    # asserts each carries one of three provenance marker forms in the first
    # 30 lines. Self-documenting (no allow-list to maintain); survives file
    # moves; explicit per-file ownership statement.
    ```

    **Module body:**
    ```python
    """scripts/check_provenance — pre-commit + CI provenance enforcement.

    Walks specific roots (analysts/, routine/, synthesis/, ingestion/, api/,
    scripts/, prompts/personas/*.md, prompts/synthesizer.md). For each tracked
    source file, asserts the first 30 lines contain ONE of:

      - "Pattern adapted from <ref>/<path>"   (canonical form)
      - "Adapted from <ref>/<path>"            (short form)
      - "# novel-to-this-project"              (explicit no-adaptation marker)

    Markdown files accept the comment form `<!-- Pattern adapted from ... -->`.

    Exit code 0 when clean; 1 when any offender. CLI: `python scripts/check_provenance.py`
    (no args needed — walks the project's standard roots from the repo root).
    """
    from __future__ import annotations

    import argparse
    import re
    import sys
    from pathlib import Path
    from typing import Final, Iterable

    REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]

    DEFAULT_ROOTS: Final[tuple[Path, ...]] = (
        REPO_ROOT / "analysts",
        REPO_ROOT / "routine",
        REPO_ROOT / "synthesis",
        REPO_ROOT / "ingestion",
        REPO_ROOT / "api",
        REPO_ROOT / "scripts",
    )

    MD_TARGETS: Final[tuple[Path, ...]] = (
        REPO_ROOT / "prompts" / "personas",   # all *.md inside
        REPO_ROOT / "prompts" / "synthesizer.md",
    )

    SCAN_LINE_LIMIT: Final[int] = 30

    # Three accepted marker forms. Compiled once.
    _PY_MARKERS: Final[tuple[re.Pattern[str], ...]] = (
        re.compile(r"#\s*Pattern adapted from\s+\S+/"),
        re.compile(r"#\s*Adapted from\s+\S+/"),
        re.compile(r"#\s*novel-to-this-project\b"),
    )
    _MD_MARKERS: Final[tuple[re.Pattern[str], ...]] = (
        re.compile(r"<!--\s*Pattern adapted from\s+\S+/"),
        re.compile(r"<!--\s*Adapted from\s+\S+/"),
        re.compile(r"<!--\s*novel-to-this-project\b"),
    )

    def _has_marker(path: Path) -> bool:
        try:
            with path.open("r", encoding="utf-8") as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= SCAN_LINE_LIMIT:
                        break
                    lines.append(line)
        except (OSError, UnicodeDecodeError):
            return False
        markers = _MD_MARKERS if path.suffix == ".md" else _PY_MARKERS
        head = "".join(lines)
        return any(m.search(head) for m in markers)

    def _iter_targets(roots: Iterable[Path], md_targets: Iterable[Path]) -> Iterable[Path]:
        for root in roots:
            if not root.exists():
                continue
            for p in root.rglob("*.py"):
                # Skip __pycache__, dotfiles, test files (already covered by py
                # roots which exclude tests/).
                if "__pycache__" in p.parts or p.name == "__init__.py" and p.stat().st_size == 0:
                    # Empty __init__.py files are package markers — skip.
                    continue
                yield p
        for md_target in md_targets:
            if md_target.is_dir():
                yield from md_target.rglob("*.md")
            elif md_target.is_file():
                yield md_target

    def check_file(path: Path) -> str | None:
        """Return None if file has marker, else an offender message."""
        if _has_marker(path):
            return None
        return (
            f"{path.relative_to(REPO_ROOT)}: missing provenance marker "
            f"(one of: 'Pattern adapted from <ref>/<path>', "
            f"'Adapted from <ref>/<path>', '# novel-to-this-project')"
        )

    def main(argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(description="Verify provenance markers.")
        parser.add_argument("--roots", nargs="*", default=None, help="Override DEFAULT_ROOTS (test hook).")
        args = parser.parse_args(argv)
        roots = [Path(r) for r in args.roots] if args.roots else list(DEFAULT_ROOTS)
        md_targets = list(MD_TARGETS) if not args.roots else []

        offenders: list[str] = []
        for path in _iter_targets(roots, md_targets):
            msg = check_file(path)
            if msg is not None:
                offenders.append(msg)

        if offenders:
            print("Provenance check FAILED — offenders:", file=sys.stderr)
            for o in offenders:
                print(f"  {o}", file=sys.stderr)
            return 1
        print(f"Provenance check OK ({len(list(_iter_targets(roots, md_targets)))} files scanned).")
        return 0

    if __name__ == "__main__":
        raise SystemExit(main())
    ```

    Create `tests/scripts/__init__.py` (empty package marker).

    Create `tests/scripts/test_check_provenance.py` implementing tests 1-10. Use `tmp_path` to build temp directory trees with marker / no-marker files and pass `roots=[tmp_path]` to `main()`.

    Create `.pre-commit-config.yaml` at repo root (NEW file):
    ```yaml
    # Phase 8 — INFRA-07 provenance enforcement.
    # Run on `pre-commit` stage; CI runs the same script directly on every push.
    repos:
      - repo: local
        hooks:
          - id: provenance-check
            name: Verify provenance markers (INFRA-07)
            entry: python scripts/check_provenance.py
            language: system
            pass_filenames: false
            always_run: true
            stages: [pre-commit]
    ```

    Extend `tests/ingestion/test_prices.py` — APPEND tests 11-12. Use `monkeypatch.setattr` on `yfinance.Ticker` and `yahooquery.Ticker`. The existing test_fallback.py may already cover similar ground; if so, add the explicit tests anyway and reference them from this plan's resilience surface.

    Extend `tests/ingestion/test_news.py` — APPEND test 13. Pattern: monkeypatch `feedparser.parse` (raises) + monkeypatch the FinViz fetcher (raises) + monkeypatch the `requests.Session.get` used by the `ingestion.http` module. Assert both `fetch_news(ticker)` and `fetch_news(ticker, return_raw=True)` return the empty-list / empty-tuple shapes WITHOUT raising.

    **Codebase audit pass (REQUIRED before declaring task done):** Run `python scripts/check_provenance.py` once against the actual codebase. The output may flag existing files that need provenance markers added. For EACH offender:
    - If the file is genuinely adapted from a reference repo, add `# Pattern adapted from <ref>/<path>` matching the closest known origin. Phase 4 + Phase 5 SUMMARYs document many origins (`virattt/ai-hedge-fund` for analyst patterns; `TauricResearch/TradingAgents` for synthesizer patterns).
    - If the file is project-original glue / orchestration, add `# novel-to-this-project` with a brief why-comment.
    - Re-run the script until it returns 0.

    Document any added markers in the SUMMARY at plan close.
  </action>
  <verify>
    <automated>uv run pytest tests/scripts/test_check_provenance.py tests/ingestion/test_prices.py tests/ingestion/test_news.py -q && python scripts/check_provenance.py</automated>
  </verify>
  <done>
    All 10 provenance tests + 2 prices resilience tests + 1 news resilience test pass. `python scripts/check_provenance.py` exits 0 against the actual codebase (any prior offenders received explicit markers). `.pre-commit-config.yaml` exists with the local hook entry. The pre-commit hook runs successfully via `pre-commit run --all-files provenance-check` (manual sanity check — not part of automated verify because pre-commit may not be installed in the test runner).
  </done>
</task>

</tasks>

<verification>
**Automated (full suite):**

```bash
uv run pytest tests/api/ tests/routine/test_memory_log.py tests/routine/test_run_for_watchlist.py tests/scripts/test_check_provenance.py tests/ingestion/test_prices.py tests/ingestion/test_news.py -q
python scripts/check_provenance.py
```

Both must exit 0.

**Frontmatter validation:**

```bash
node "C:/Users/Mohan/.claude/bin/gmd-tools.cjs" frontmatter validate .planning/phases/08-mid-day-refresh-resilience/08-01-backend-refresh-PLAN.md --schema plan
node "C:/Users/Mohan/.claude/bin/gmd-tools.cjs" verify plan-structure .planning/phases/08-mid-day-refresh-resilience/08-01-backend-refresh-PLAN.md
```

**Manual (deferred to Wave 1 close):** Vercel preview deploy + cold-start measurement. See 08-VALIDATION.md "Manual-Only Verifications" table.
</verification>

<success_criteria>
- All 3 tasks pass their automated verify commands
- `tests/api/test_refresh.py` covers happy path + 4 failure modes + timeout simulation (10 tests)
- `tests/routine/test_memory_log.py` + extension to `test_run_for_watchlist.py` cover JSONL contract + Phase E hook (~10 + 3 tests)
- `tests/scripts/test_check_provenance.py` covers 3 marker forms + walk semantics + exit codes (10 tests)
- `tests/ingestion/test_prices.py` + `test_news.py` extensions cover 2+1 resilience cases
- `python scripts/check_provenance.py` returns 0 against the actual codebase (offenders fixed, OR existing codebase already passes)
- `vercel.json` at repo root configures `api/refresh.py` with maxDuration=30
- `frontend/vercel.json` SPA rewrite narrowed to `/((?!api/).*)`
- `memory/*.jsonl` entries added to `.gitignore`
- `.pre-commit-config.yaml` provenance hook entry present
- All 4 requirements (REFRESH-01, REFRESH-04 backend, INFRA-06, INFRA-07) closed
</success_criteria>

<output>
After completion, create `.planning/phases/08-mid-day-refresh-resilience/08-01-backend-refresh-SUMMARY.md` documenting:
- 3 tasks executed
- Test counts (~13 in tests/api/ + ~10 memory_log + 3 run_for_watchlist + 10 provenance + 3 ingestion resilience)
- Any provenance markers added during the codebase audit pass (file path + form chosen)
- Final line counts (api/refresh.py + memory_log.py + check_provenance.py production LOC)
- REFRESH-01, INFRA-06, INFRA-07 marked Complete; REFRESH-04 marked "Backend Complete (frontend half: 08-02)"
</output>
