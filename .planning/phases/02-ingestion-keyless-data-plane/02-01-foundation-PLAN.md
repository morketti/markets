---
phase: 02-ingestion-keyless-data-plane
plan: 01
type: tdd
wave: 1
depends_on: []
files_modified:
  - pyproject.toml
  - ingestion/__init__.py
  - ingestion/http.py
  - ingestion/errors.py
  - analysts/data/__init__.py
  - analysts/data/prices.py
  - analysts/data/fundamentals.py
  - analysts/data/filings.py
  - analysts/data/news.py
  - analysts/data/social.py
  - tests/ingestion/__init__.py
  - tests/ingestion/conftest.py
  - tests/ingestion/test_http.py
  - tests/ingestion/test_errors.py
  - tests/ingestion/test_data_schemas.py
  - tests/ingestion/fixtures/.gitkeep
autonomous: true
requirements: [DATA-06]
must_haves:
  truths:
    - "A single shared requests.Session ships with an EDGAR-compliant User-Agent and 10s timeout"
    - "HTTP failures retry on 429/503 with backoff_factor=0.3 up to 3 times"
    - "Custom IngestionError / NetworkError / SchemaDriftError exceptions exist and inherit from a common base"
    - "Five Pydantic data schemas (PriceSnapshot, FundamentalsSnapshot, FilingMetadata, Headline, SocialSignal) validate their happy-path shapes and reject obvious garbage"
    - "Every schema includes ticker (normalized via analysts.schemas.normalize_ticker), fetched_at: datetime, source: Literal[...], data_unavailable: bool=False"
    - "responses>=0.25 is in dev deps; tests/ingestion/ collects cleanly under pytest"
    - "ingestion package is registered in [tool.hatch.build.targets.wheel] packages and analysts/data is importable"
  artifacts:
    - path: "pyproject.toml"
      provides: "yfinance/yahooquery/requests/feedparser/beautifulsoup4 runtime deps + responses dev dep + ingestion package"
      contains: "yfinance"
    - path: "ingestion/http.py"
      provides: "get_session() returning a configured requests.Session, polite_sleep helper"
      min_lines: 40
    - path: "ingestion/errors.py"
      provides: "IngestionError, NetworkError, SchemaDriftError"
      min_lines: 15
    - path: "analysts/data/prices.py"
      provides: "PriceSnapshot, OHLCBar Pydantic models"
      min_lines: 30
    - path: "analysts/data/fundamentals.py"
      provides: "FundamentalsSnapshot Pydantic model"
      min_lines: 25
    - path: "analysts/data/filings.py"
      provides: "FilingMetadata Pydantic model"
      min_lines: 25
    - path: "analysts/data/news.py"
      provides: "Headline Pydantic model"
      min_lines: 20
    - path: "analysts/data/social.py"
      provides: "SocialSignal, RedditPost, StockTwitsPost Pydantic models"
      min_lines: 25
    - path: "tests/ingestion/test_http.py"
      provides: "Probe 2-W1-01 (UA header) + 2-W1-02 (retry on 503/429)"
      min_lines: 30
    - path: "tests/ingestion/test_errors.py"
      provides: "Probe 2-W1-03 — exception hierarchy"
      min_lines: 15
    - path: "tests/ingestion/test_data_schemas.py"
      provides: "Pydantic shape probes for all five data schemas"
      min_lines: 40
  key_links:
    - from: "analysts/data/*.py"
      to: "analysts/schemas.normalize_ticker"
      via: "ticker field validator (mode='before')"
      pattern: "from analysts.schemas import normalize_ticker"
    - from: "ingestion/http.py"
      to: "requests.Session + HTTPAdapter"
      via: "Session-level User-Agent + Retry mount"
      pattern: "Retry\\(total=3"
    - from: "tests/ingestion/test_http.py"
      to: "ingestion.http.get_session()"
      via: "responses library mocks"
      pattern: "@responses.activate"
---

<objective>
Wave 1 foundation for the ingestion phase: shared HTTP session with EDGAR-compliant User-Agent and retry policy, custom exception hierarchy, five Pydantic data schemas (prices/fundamentals/filings/news/social), and the test scaffolding (fixture directory, responses dep) that downstream Wave-2 plans (02-02..02-05) consume.

Purpose: This plan exists because every Wave-2 plan needs (a) a single, audited HTTP client to make outbound requests, (b) typed Pydantic models to validate fetched data into, and (c) a shared exception vocabulary so the orchestrator (Wave 3) can distinguish network failures from schema drift. Building these once here prevents four parallel plans from each inventing their own session and exception types.

Output: `ingestion/` package with `http.py` and `errors.py`, `analysts/data/` sub-package with five schema modules, updated `pyproject.toml` with new runtime + dev deps and packages list, plus `tests/ingestion/` scaffolding with three probe-test files (W1-01 / W1-02 / W1-03) all green.
</objective>

<execution_context>
@C:/Users/Mohan/.claude/workflows/execute-plan.md
@C:/Users/Mohan/.claude/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/02-ingestion-keyless-data-plane/02-RESEARCH.md
@.planning/phases/02-ingestion-keyless-data-plane/02-VALIDATION.md

# Existing patterns this plan must follow
@analysts/schemas.py
@watchlist/loader.py
@pyproject.toml

<interfaces>
<!-- Key contracts the executor needs. Use these directly — no codebase exploration required. -->

From analysts/schemas.py (already shipped in Phase 1, reuse — do NOT duplicate):
```python
def normalize_ticker(s: str) -> Optional[str]:
    """Returns canonical hyphen form (BRK-B), or None on invalid input.
    Accepts dot/slash/underscore as separators. Single source of truth."""
```

From watchlist/loader.py (proven Phase 1 pattern — mirror for snapshot writes in Plan 02-06):
```python
# Deterministic byte-identical serialization:
payload = json.dumps(model.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
```

NEW contracts this plan creates (downstream plans import from here):

ingestion/http.py:
```python
def get_session() -> requests.Session:
    """Returns process-shared Session with EDGAR-compliant User-Agent,
    HTTPAdapter mounted with Retry(total=3, backoff_factor=0.3,
    status_forcelist=[429, 500, 502, 503, 504]), 10s default timeout
    (set on the Session as a wrapper). Idempotent — first call constructs,
    later calls return same instance."""

DEFAULT_TIMEOUT: float = 10.0
USER_AGENT: str = "Markets Personal Research (mohanraval15@gmail.com)"

def polite_sleep(source: str, last_call: dict[str, float], min_interval: float) -> None:
    """Sleeps just long enough that consecutive calls to `source` are at least
    `min_interval` seconds apart. Updates last_call[source] to time.monotonic()
    after sleeping. Caller passes a per-process dict for state."""
```

ingestion/errors.py:
```python
class IngestionError(Exception):
    """Base for all ingestion failures."""

class NetworkError(IngestionError):
    """HTTP-layer failure: timeout, connection error, 4xx/5xx after retries."""

class SchemaDriftError(IngestionError):
    """Upstream returned 200 but payload didn't match expected shape."""
```

analysts/data/prices.py:
```python
class OHLCBar(BaseModel):
    date: date  # ISO date, no time
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: int = Field(ge=0)

class PriceSnapshot(BaseModel):
    ticker: str  # validator delegates to normalize_ticker
    fetched_at: datetime  # UTC
    source: Literal["yfinance", "yahooquery"]
    data_unavailable: bool = False
    current_price: Optional[float] = None  # > 0 when set
    history: list[OHLCBar] = Field(default_factory=list)
```

analysts/data/fundamentals.py:
```python
class FundamentalsSnapshot(BaseModel):
    ticker: str
    fetched_at: datetime
    source: Literal["yfinance", "yahooquery"]
    data_unavailable: bool = False
    pe: Optional[float] = None
    ps: Optional[float] = None
    pb: Optional[float] = None
    roe: Optional[float] = None
    debt_to_equity: Optional[float] = None
    profit_margin: Optional[float] = None
    free_cash_flow: Optional[float] = None  # raw $, can be negative
    market_cap: Optional[float] = None
```

analysts/data/filings.py:
```python
class FilingMetadata(BaseModel):
    ticker: str
    fetched_at: datetime
    source: Literal["edgar"] = "edgar"
    data_unavailable: bool = False
    cik: Optional[str] = None  # zero-padded 10-digit
    form_type: Literal["10-K", "10-Q", "8-K", "DEF 14A", "S-1", "20-F", "6-K", "OTHER"]
    accession_number: Optional[str] = None
    filed_date: Optional[date] = None
    primary_document: Optional[str] = None  # URL fragment; full URL built by caller
    summary: str = ""
```
Note: per FilingMetadata, the OUTER list is what fetch_filings returns; each item is one filing. The schema validates a single filing.

analysts/data/news.py:
```python
class Headline(BaseModel):
    ticker: str
    fetched_at: datetime
    source: Literal["yahoo-rss", "google-news", "finviz"]
    data_unavailable: bool = False
    title: str = Field(min_length=1, max_length=500)
    url: str  # http(s) only
    published_at: Optional[datetime] = None  # parsed from feed; nullable when unparseable
    summary: str = Field(default="", max_length=2000)
    dedup_key: str  # caller-provided; set by ingestion/news.py to source+entry.id (or normalized title fallback)
```

analysts/data/social.py:
```python
class RedditPost(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    url: str
    subreddit: str
    published_at: Optional[datetime] = None
    score: Optional[int] = None  # may be missing in RSS

class StockTwitsPost(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    created_at: Optional[datetime] = None
    sentiment: Optional[Literal["bullish", "bearish"]] = None  # only when user-tagged

class SocialSignal(BaseModel):
    ticker: str
    fetched_at: datetime
    source: Literal["reddit-rss", "stocktwits", "combined"] = "combined"
    data_unavailable: bool = False
    reddit_posts: list[RedditPost] = Field(default_factory=list)
    stocktwits_posts: list[StockTwitsPost] = Field(default_factory=list)
    trending_rank: Optional[int] = None  # StockTwits trending position when present
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Update pyproject.toml + scaffold ingestion/ + analysts/data/ + tests/ingestion/</name>
  <files>pyproject.toml, ingestion/__init__.py, ingestion/errors.py, ingestion/http.py, analysts/data/__init__.py, tests/ingestion/__init__.py, tests/ingestion/conftest.py, tests/ingestion/fixtures/.gitkeep</files>
  <behavior>
    Goal: lay all the empty/scaffolding files so the test runner discovers them, deps resolve, and the editable wheel rebuilds with the new packages. NO production logic in this task — just empty exports + dep resolution + package registration.

    Validation evidence (driven by failing tests if applicable, or by import + uv sync exit code):
    - `uv sync --reinstall-package markets` exits 0 — confirms hatchling sees the new packages
    - `uv run python -c "import ingestion; import ingestion.http; import ingestion.errors; import analysts.data; from analysts.data import prices, fundamentals, filings, news, social"` exits 0 (modules importable, even if mostly empty)
    - `uv run pytest tests/ingestion/ --collect-only -q` exits 5 (no tests collected yet — empty dir is fine)
  </behavior>
  <action>
    1. Update `pyproject.toml`:
       - Bump `[project].dependencies` to add: `"yfinance>=0.2.50,<0.3"`, `"yahooquery>=2.3,<3"`, `"requests>=2.31,<3"`, `"feedparser>=6.0,<7"`, `"beautifulsoup4>=4.12,<5"`. Keep `"pydantic>=2.10"` (already present).
       - Update `[dependency-groups].dev` to add: `"responses>=0.25"`. Keep existing pytest/pytest-cov/ruff entries.
       - Update `[tool.hatch.build.targets.wheel].packages` from `["analysts", "watchlist", "cli"]` to `["analysts", "watchlist", "cli", "ingestion"]`. (`analysts/data/` is a sub-package of `analysts` and ships automatically once `analysts` is listed — no separate entry needed.)
       - Update `[tool.coverage.run].source` from `["analysts", "watchlist", "cli"]` to `["analysts", "watchlist", "cli", "ingestion"]`.

    2. Create empty `ingestion/__init__.py` with a one-line module docstring.

    3. Create `ingestion/errors.py` with:
       - Module docstring explaining the exception hierarchy (IngestionError = base, NetworkError = HTTP-level, SchemaDriftError = 200-but-wrong-shape).
       - `class IngestionError(Exception)`, `class NetworkError(IngestionError)`, `class SchemaDriftError(IngestionError)` — each with one-line docstrings, no `__init__` overrides (caller passes message via standard Exception constructor).

    4. Create `ingestion/http.py` STUB with the public symbols the interfaces block declares — actual logic lands in Task 2 (TDD style: tests fail until then). For now the stub raises `NotImplementedError("populated in Task 2")` from `get_session()` and `polite_sleep()`. Module-level constants (`USER_AGENT`, `DEFAULT_TIMEOUT`) are defined fully — they're plain values, not behavior.

    5. Create `analysts/data/__init__.py` re-exporting nothing yet (one-line module docstring; populated by re-exports in Task 3 once schemas exist).

    6. Create `tests/ingestion/__init__.py` (empty package marker).

    7. Create `tests/ingestion/conftest.py` with a session-scoped `fixtures_dir` fixture that returns `Path(__file__).parent / "fixtures"`. Tests in W2 will pass that into `read_text()` / `read_bytes()` for fixture loads.

    8. Create empty `tests/ingestion/fixtures/.gitkeep` so the directory exists in git even before W2 plans drop fixtures into it.

    9. Run `uv sync --reinstall-package markets` (per STATE.md hatchling gotcha — reinstall the editable wheel because new packages were added). If `uv` is not on PATH, prepend `C:/Users/Mohan/AppData/Roaming/Python/Python314/Scripts/` per STATE.md note.
  </action>
  <verify>
    <automated>uv sync --reinstall-package markets &amp;&amp; uv run python -c "import ingestion; import ingestion.http; import ingestion.errors"</automated>
    <note>The `analysts.data.*` submodules don't exist until Task 3 — they are NOT verified at Task 1 time. The Task-1 verify must FAIL LOUDLY if `uv sync` fails (don't mask it with `|| echo`). Submodule imports are reverified in Task 3's automated check.</note>
  </verify>
  <done>pyproject.toml updated with 5 runtime + 1 dev dep + ingestion package + coverage source. uv sync reinstalls the wheel cleanly. ingestion/http.py + ingestion/errors.py importable. tests/ingestion/ skeleton in place with fixtures/ dir.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: TDD ingestion/http.py — RED test_http.py + test_errors.py, then GREEN implementation</name>
  <files>tests/ingestion/test_http.py, tests/ingestion/test_errors.py, ingestion/http.py, ingestion/errors.py</files>
  <behavior>
    Probes 2-W1-01, 2-W1-02, 2-W1-03 from VALIDATION.md.

    test_http.py (probes 2-W1-01 + 2-W1-02):
    - test_session_has_compliant_user_agent: `get_session().headers["User-Agent"]` matches `r"^Markets Personal Research \(.+@.+\)$"` AND env override `MARKETS_USER_AGENT=foo@bar.com Test` is honored when set.
    - test_session_singleton: get_session() returns the same instance on repeated calls (object identity check).
    - test_session_has_default_timeout_constant: `ingestion.http.DEFAULT_TIMEOUT == 10.0` (constant exposed for callers; the Session object itself doesn't carry a timeout — callers pass `timeout=DEFAULT_TIMEOUT` per request).
    - test_retry_on_503_then_success (`@responses.activate`): mock `https://example.test/x` to return 503 once then 200; assert `get_session().get("https://example.test/x", timeout=DEFAULT_TIMEOUT)` returns status 200; assert responses.calls has at least 2 entries (proves retry fired).
    - test_retry_on_429_then_success (`@responses.activate`): same pattern with 429.
    - test_retry_gives_up_after_3 (`@responses.activate`): 503 four times in a row → final response.status_code == 503 (last attempt) OR raises requests.exceptions.RetryError. Either is acceptable; assert `len(responses.calls) >= 4` (1 initial + 3 retries) — proves retry policy is exactly 3.
    - test_polite_sleep_enforces_min_interval: pass a fresh dict, call polite_sleep("yahoo", state, 0.1) twice in a row; assert second call took at least 0.09s (give 10ms slack for monotonic clock granularity). Uses `time.monotonic()` deltas, no real network.

    test_errors.py (probe 2-W1-03):
    - test_exception_hierarchy: `issubclass(NetworkError, IngestionError)` and `issubclass(SchemaDriftError, IngestionError)` and `issubclass(IngestionError, Exception)`.
    - test_exceptions_carry_message: `raise NetworkError("timeout after 10s")` then `except NetworkError as e: assert str(e) == "timeout after 10s"`.

    All tests pass against the GREEN implementation in Task 2.
  </behavior>
  <action>
    Order: RED first (commit), then GREEN (commit). Two commits in this task.

    RED phase:
    1. Write `tests/ingestion/test_http.py` with the 7 tests above. Imports: `import responses`, `import pytest`, `import time`, `from ingestion.http import get_session, polite_sleep, DEFAULT_TIMEOUT, USER_AGENT`.
    2. Write `tests/ingestion/test_errors.py` with the 2 tests above. Imports: `import pytest`, `from ingestion.errors import IngestionError, NetworkError, SchemaDriftError`.
    3. Run `uv run pytest tests/ingestion/test_http.py tests/ingestion/test_errors.py -x -q` → expect failures (NotImplementedError or import errors). This is the RED state.
    4. Commit: `test(02-01): add failing tests for http session + error hierarchy (probes 2-W1-01..03)`

    GREEN phase:
    5. Implement `ingestion/http.py`:
       - Module docstring explaining the EDGAR-compliance + retry rationale (cite Pitfall #2 + Pitfall #1).
       - Module-level `_SESSION: Optional[requests.Session] = None`.
       - `USER_AGENT` constant: read from env `MARKETS_USER_AGENT` if set; else default `"Markets Personal Research (mohanraval15@gmail.com)"`. Compute at module import — overridable per-process via env, NOT per-call.
       - `DEFAULT_TIMEOUT: float = 10.0`.
       - `def get_session() -> requests.Session`: lazy-init `_SESSION` once, mount `HTTPAdapter(max_retries=Retry(total=3, backoff_factor=0.3, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=frozenset(["GET", "HEAD"])))` to both `http://` and `https://`, set `session.headers["User-Agent"] = USER_AGENT`. Return the singleton. Use `from urllib3.util.retry import Retry`.
       - `def polite_sleep(source: str, last_call: dict[str, float], min_interval: float) -> None`: read `last_call.get(source)`, compute time-since-last via `time.monotonic()`, sleep `max(0, min_interval - elapsed)`, update `last_call[source] = time.monotonic()`. (Confirm: only sleep when needed — first call for a source sleeps 0.)
    6. `ingestion/errors.py` already has the three classes (Task 1). No code change needed if Task 1 was correct; if a test fails at import, fix.
    7. Run `uv run pytest tests/ingestion/test_http.py tests/ingestion/test_errors.py -v` → all green.
    8. Run `uv run pytest --cov=ingestion.http --cov=ingestion.errors --cov-branch tests/ingestion/test_http.py tests/ingestion/test_errors.py` → coverage on `ingestion/http.py` ≥90% line / ≥85% branch; `ingestion/errors.py` 100% (trivial).
    9. Commit: `feat(02-01): implement shared HTTP session + ingestion exception hierarchy`

    Probe ID mapping (write into test docstrings — `# Probe 2-W1-01` comment above each function — so the validator can mechanically pair):
    - 2-W1-01 → `test_session_has_compliant_user_agent`
    - 2-W1-02 → `test_retry_on_503_then_success` (canonical) plus `test_retry_on_429_then_success` and `test_retry_gives_up_after_3` cover the same probe more thoroughly
    - 2-W1-03 → `test_exception_hierarchy` (canonical) plus `test_exceptions_carry_message`
  </action>
  <verify>
    <automated>uv run pytest tests/ingestion/test_http.py tests/ingestion/test_errors.py -v &amp;&amp; uv run pytest --cov=ingestion.http --cov=ingestion.errors --cov-branch tests/ingestion/test_http.py tests/ingestion/test_errors.py</automated>
  </verify>
  <done>9 tests green across test_http.py + test_errors.py. ingestion/http.py and ingestion/errors.py at ≥90% line / ≥85% branch coverage. RED commit + GREEN commit landed. Probes 2-W1-01, 2-W1-02, 2-W1-03 satisfied.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: TDD analysts/data/ schemas — RED test_data_schemas.py, then GREEN five schema modules</name>
  <files>tests/ingestion/test_data_schemas.py, analysts/data/__init__.py, analysts/data/prices.py, analysts/data/fundamentals.py, analysts/data/filings.py, analysts/data/news.py, analysts/data/social.py</files>
  <behavior>
    Probe 2-W1-03 (data schemas slice — note: VALIDATION.md re-uses 2-W1-03 for both errors AND schemas; we satisfy BOTH by giving each its own test file. The probe ID is a marker, not a unique-test constraint).

    test_data_schemas.py:
    - test_price_snapshot_happy: PriceSnapshot(ticker="AAPL", fetched_at=datetime(2026,5,1,tzinfo=timezone.utc), source="yfinance", current_price=180.5) round-trips via model_dump_json + model_validate_json byte-stable.
    - test_price_snapshot_normalizes_ticker: PriceSnapshot(ticker="brk.b", ...).ticker == "BRK-B".
    - test_price_snapshot_rejects_negative_price: PriceSnapshot(..., current_price=-1.0) raises ValidationError.
    - test_price_snapshot_rejects_bad_source: source="finnhub" raises ValidationError (Literal violation).
    - test_ohlc_bar_validates: OHLCBar(date=date(2026,5,1), open=180, high=185, low=179, close=183, volume=1_000_000) ok; volume=-1 fails.
    - test_fundamentals_snapshot_happy: FundamentalsSnapshot(ticker="NVDA", fetched_at=..., source="yfinance") with all-None metrics ok (everything optional).
    - test_fundamentals_snapshot_data_unavailable: FundamentalsSnapshot(..., data_unavailable=True) ok with no other fields.
    - test_fundamentals_rejects_bad_ticker: ticker="123!@#" raises ValidationError.
    - test_filing_metadata_happy: FilingMetadata(ticker="AAPL", fetched_at=..., form_type="10-K", filed_date=date(2026,4,1)) ok.
    - test_filing_metadata_rejects_unknown_form: form_type="13F" raises ValidationError (not in Literal).
    - test_filing_metadata_other_form_allowed: form_type="OTHER" ok.
    - test_headline_happy: Headline(ticker="AAPL", fetched_at=..., source="yahoo-rss", title="Apple beats", url="https://...", dedup_key="yahoo-rss::abc") ok.
    - test_headline_rejects_empty_title: title="" raises ValidationError.
    - test_headline_rejects_overlong_title: title="x"*501 raises ValidationError.
    - test_social_signal_happy: SocialSignal(ticker="GME", fetched_at=..., reddit_posts=[RedditPost(title="..", url="..", subreddit="wsb")]) ok.
    - test_social_signal_empty_collections_ok: all lists empty + data_unavailable=True ok.

    All schemas import normalize_ticker from analysts.schemas (single source of truth).
  </behavior>
  <action>
    RED phase:
    1. Write `tests/ingestion/test_data_schemas.py` with the ~16 tests above. Imports: `from datetime import datetime, date, timezone`, `import pytest`, `from pydantic import ValidationError`, `from analysts.data.prices import PriceSnapshot, OHLCBar`, `from analysts.data.fundamentals import FundamentalsSnapshot`, `from analysts.data.filings import FilingMetadata`, `from analysts.data.news import Headline`, `from analysts.data.social import SocialSignal, RedditPost, StockTwitsPost`.
    2. Run `uv run pytest tests/ingestion/test_data_schemas.py -x -q` → expect ImportError or attribute errors (modules empty).
    3. Commit: `test(02-01): add failing tests for analysts/data schemas`

    GREEN phase:
    4. Implement `analysts/data/prices.py`:
       - `from datetime import date, datetime`
       - `from typing import Literal, Optional`
       - `from pydantic import BaseModel, ConfigDict, Field, field_validator`
       - `from analysts.schemas import normalize_ticker`
       - `OHLCBar` per the interfaces block. Use `Field(gt=0)` for price fields and `Field(ge=0)` for volume.
       - `PriceSnapshot` per the interfaces block. `ticker` field uses a `@field_validator("ticker", mode="before")` that delegates to `normalize_ticker` (mirror the pattern in `analysts/schemas.TickerConfig._normalize_ticker_field`). `current_price`: `Optional[float] = Field(default=None, gt=0)` — validator only fires when not None (Pydantic's `gt=0` on Optional handles this natively).
       - Both classes use `model_config = ConfigDict(extra="forbid")`.

    5. Implement `analysts/data/fundamentals.py` per the interfaces block. Same pattern: ticker normalization + extra=forbid + Optional[float] fields with no positivity constraint (debt-to-equity can technically be 0; FCF can be negative; ROE can be negative). Only DOC the fact that bad data has been observed and downstream sanity checks enforce ranges, not the schema.

    6. Implement `analysts/data/filings.py` per the interfaces block. `form_type` is the Literal tuple from the interfaces. `cik` is `Optional[str] = Field(default=None, pattern=r"^\d{10}$")` — 10-digit zero-padded EDGAR CIK format.

    7. Implement `analysts/data/news.py` per the interfaces block. `title` uses `Field(min_length=1, max_length=500)`. `url` is `str` (basic Pydantic str — not HttpUrl, because HttpUrl rejects some legitimate Yahoo redirect URLs; downstream `ingestion/news.py` does its own validation).

    8. Implement `analysts/data/social.py` per the interfaces block. `RedditPost` and `StockTwitsPost` classes first, then `SocialSignal` referencing them.

    9. Update `analysts/data/__init__.py` to re-export everything cleanly:
       ```python
       """Pydantic schemas for ingested data — single source of truth for shapes
       fetched in Phase 2. Each module owns one domain (prices, fundamentals, etc).
       Plans 02-02..02-05 import from here; do not redefine."""
       from analysts.data.prices import OHLCBar, PriceSnapshot
       from analysts.data.fundamentals import FundamentalsSnapshot
       from analysts.data.filings import FilingMetadata
       from analysts.data.news import Headline
       from analysts.data.social import RedditPost, StockTwitsPost, SocialSignal

       __all__ = ["OHLCBar", "PriceSnapshot", "FundamentalsSnapshot", "FilingMetadata",
                  "Headline", "RedditPost", "StockTwitsPost", "SocialSignal"]
       ```

    10. Run `uv run pytest tests/ingestion/test_data_schemas.py -v` → all green.
    11. Run `uv run pytest --cov=analysts.data --cov-branch tests/ingestion/test_data_schemas.py` → ≥90% line / ≥85% branch.
    12. Run full suite to confirm nothing else broke: `uv run pytest -x -q`. Existing 33 phase-1 tests stay green.
    13. Commit: `feat(02-01): implement Pydantic schemas for ingested data (prices, fundamentals, filings, news, social)`
  </action>
  <verify>
    <automated>uv run pytest tests/ingestion/test_data_schemas.py -v &amp;&amp; uv run pytest --cov=analysts.data --cov-branch tests/ingestion/test_data_schemas.py &amp;&amp; uv run pytest -x -q</automated>
  </verify>
  <done>~16 schema tests green. Five schema modules ship at ≥90%/≥85% coverage. Full Phase 1 + Phase 2 (W1) suite green. analysts/data/__init__.py re-exports everything. All schemas use analysts.schemas.normalize_ticker — no ticker-regex duplication.</done>
</task>

</tasks>

<verification>
- `uv run pytest tests/ingestion/ -v` — all probes 2-W1-01, 2-W1-02, 2-W1-03 green
- `uv run pytest -x -q` — full suite (Phase 1 + new Phase 2 W1) green; ~50 tests
- `uv run pytest --cov=ingestion --cov=analysts.data --cov-branch tests/ingestion/` — ≥90% line / ≥85% branch on new files
- `uv run python -c "from ingestion.http import get_session; from ingestion.errors import IngestionError, NetworkError, SchemaDriftError; from analysts.data import PriceSnapshot, FundamentalsSnapshot, FilingMetadata, Headline, SocialSignal; print('imports ok')"` — clean
- `cat pyproject.toml` shows yfinance/yahooquery/requests/feedparser/beautifulsoup4 in `[project].dependencies`, responses in `[dependency-groups].dev`, ingestion in hatch packages and coverage source.

## Cross-Scope Risks

_vault_status=budget_exhausted; re-run /gmd:plan-phase --replan after vault-maintain_
</verification>

<success_criteria>
1. Three test files green: test_http.py (7 tests), test_errors.py (2 tests), test_data_schemas.py (~16 tests).
2. ingestion/http.py provides get_session() singleton with EDGAR-compliant UA, 3-retry HTTPAdapter on 429/5xx, DEFAULT_TIMEOUT=10.0, polite_sleep helper.
3. ingestion/errors.py provides 3-class hierarchy.
4. analysts/data/ sub-package provides all five schemas, all using analysts.schemas.normalize_ticker.
5. pyproject.toml has 5 new runtime + 1 new dev dep + ingestion in hatch packages + coverage source.
6. Coverage ≥90% line / ≥85% branch on every new ingestion/ and analysts/data/ file.
7. Probes 2-W1-01, 2-W1-02, 2-W1-03 all map to named test functions (probe-id comments above each test).
8. Wave 2 plans (02-02..02-05) can begin in parallel: every contract they import is now landed.
</success_criteria>

<output>
After completion, create `.planning/phases/02-ingestion-keyless-data-plane/02-01-SUMMARY.md`.
</output>
