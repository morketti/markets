---
phase: 02-ingestion-keyless-data-plane
plan: 02
type: tdd
wave: 2
depends_on: [02-01]
files_modified:
  - ingestion/prices.py
  - ingestion/fundamentals.py
  - tests/ingestion/test_prices.py
  - tests/ingestion/test_fundamentals.py
  - tests/ingestion/test_fallback.py
  - tests/ingestion/fixtures/yfinance_aapl_history.json
  - tests/ingestion/fixtures/yfinance_aapl_info.json
  - tests/ingestion/fixtures/yfinance_empty_history.json
  - tests/ingestion/fixtures/yahooquery_aapl_price.json
autonomous: true
requirements: [DATA-01, DATA-02, DATA-07, DATA-08]
must_haves:
  truths:
    - "fetch_prices(ticker) returns a PriceSnapshot with current_price > 0 and >=1 OHLC bar when yfinance has data"
    - "fetch_prices(ticker) returns PriceSnapshot(data_unavailable=True) when yfinance returns empty AND yahooquery also fails"
    - "fetch_prices(ticker) returns PriceSnapshot(source='yahooquery') when yfinance is empty but yahooquery has valid data"
    - "fetch_fundamentals(ticker) returns a FundamentalsSnapshot populated with at least P/E and market_cap when yfinance.info has data"
    - "fetch_fundamentals(ticker) marks data_unavailable=True when expected keys are missing — does NOT raise KeyError"
    - "All yfinance/yahooquery calls go through unittest.mock.patch in tests — zero real network during pytest"
  artifacts:
    - path: "ingestion/prices.py"
      provides: "fetch_prices(ticker) -> PriceSnapshot with yfinance primary + yahooquery fallback"
      min_lines: 60
    - path: "ingestion/fundamentals.py"
      provides: "fetch_fundamentals(ticker) -> FundamentalsSnapshot from yfinance.info / fast_info"
      min_lines: 50
    - path: "tests/ingestion/test_prices.py"
      provides: "Probes 2-W2-01 (happy) + 2-W2-02 (empty)"
      min_lines: 40
    - path: "tests/ingestion/test_fundamentals.py"
      provides: "Probes 2-W2-04 (happy) + 2-W2-05 (missing keys)"
      min_lines: 40
    - path: "tests/ingestion/test_fallback.py"
      provides: "Probe 2-W2-03 (yfinance empty → yahooquery success)"
      min_lines: 30
  key_links:
    - from: "ingestion/prices.py"
      to: "yfinance.Ticker(...).history() + .fast_info"
      via: "yfinance import + sanity check"
      pattern: "yfinance.Ticker"
    - from: "ingestion/prices.py"
      to: "yahooquery.Ticker(...).price"
      via: "fallback path triggered when yfinance returns empty"
      pattern: "yahooquery.Ticker"
    - from: "ingestion/prices.py"
      to: "analysts.data.PriceSnapshot"
      via: "Pydantic validation at return"
      pattern: "PriceSnapshot\\("
    - from: "ingestion/fundamentals.py"
      to: "analysts.data.FundamentalsSnapshot"
      via: "Pydantic validation at return"
      pattern: "FundamentalsSnapshot\\("
---

<objective>
Wave 2 / Source A: yfinance-backed price + fundamentals fetch with yahooquery fallback for prices. Implements DATA-01 (daily OHLC + current price), DATA-02 (P/E, P/S, ROE, debt/equity, margins, FCF), DATA-07 (data_unavailable flag), DATA-08 (yahooquery fallback).

Purpose: Prices and fundamentals come from the same source family (Yahoo via yfinance) and share the fallback story to yahooquery. Bundling them into one plan keeps the yfinance-pitfall logic (sanity checks for silent breakage per Pitfall #1) in one mental model and one test file. Splitting them would force two plans to each independently mock yfinance.Ticker.

Output: ingestion/prices.py + ingestion/fundamentals.py with happy-path + empty-path + fallback paths. Three test files (test_prices.py, test_fundamentals.py, test_fallback.py) covering probes 2-W2-01..05. Four fixture files committed.
</objective>

<execution_context>
@C:/Users/Mohan/.claude/workflows/execute-plan.md
@C:/Users/Mohan/.claude/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/02-ingestion-keyless-data-plane/02-RESEARCH.md
@.planning/phases/02-ingestion-keyless-data-plane/02-VALIDATION.md
@.planning/phases/02-ingestion-keyless-data-plane/02-01-SUMMARY.md

# Existing patterns
@analysts/schemas.py

<interfaces>
<!-- Wave 1 contracts this plan consumes (all landed in Plan 02-01) -->

From ingestion/http.py:
```python
def get_session() -> requests.Session  # not strictly needed here — yfinance manages its own; consume for any direct quote calls
DEFAULT_TIMEOUT: float = 10.0
USER_AGENT: str = "Markets Personal Research (...)"
```

From ingestion/errors.py:
```python
class IngestionError(Exception)
class NetworkError(IngestionError)
class SchemaDriftError(IngestionError)
```

From analysts/data/prices.py:
```python
class OHLCBar(BaseModel):
    date: date; open: float; high: float; low: float; close: float; volume: int
class PriceSnapshot(BaseModel):
    ticker: str; fetched_at: datetime; source: Literal["yfinance", "yahooquery"]
    data_unavailable: bool = False; current_price: Optional[float] = None
    history: list[OHLCBar] = []
```

From analysts/data/fundamentals.py:
```python
class FundamentalsSnapshot(BaseModel):
    ticker: str; fetched_at: datetime; source: Literal["yfinance", "yahooquery"]
    data_unavailable: bool = False
    pe: Optional[float]; ps: Optional[float]; pb: Optional[float]
    roe: Optional[float]; debt_to_equity: Optional[float]; profit_margin: Optional[float]
    free_cash_flow: Optional[float]; market_cap: Optional[float]
```

NEW contracts this plan creates (Plan 02-06 imports from here):

ingestion/prices.py:
```python
def fetch_prices(ticker: str, *, period: str = "3mo") -> PriceSnapshot:
    """Fetch daily OHLC + current price for `ticker`. yfinance primary,
    yahooquery fallback. Always returns a PriceSnapshot — sets
    data_unavailable=True when both sources fail. Never raises for upstream
    breakage; only raises ValidationError if our schema rejects the result
    (which would be a bug, not a runtime condition)."""
```

ingestion/fundamentals.py:
```python
def fetch_fundamentals(ticker: str) -> FundamentalsSnapshot:
    """Fetch fundamentals dict from yfinance.Ticker(t).info. Returns
    FundamentalsSnapshot populated with all available keys. When .info is
    empty/missing the canonical 'trailingPE' marker key, returns
    FundamentalsSnapshot(data_unavailable=True) — does NOT raise KeyError."""
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: TDD ingestion/prices.py + fallback path</name>
  <files>tests/ingestion/test_prices.py, tests/ingestion/test_fallback.py, tests/ingestion/fixtures/yfinance_aapl_history.json, tests/ingestion/fixtures/yfinance_empty_history.json, tests/ingestion/fixtures/yahooquery_aapl_price.json, ingestion/prices.py</files>
  <behavior>
    Probes 2-W2-01 (happy), 2-W2-02 (empty path), 2-W2-03 (yahooquery fallback).

    test_prices.py:
    - test_prices_happy: patch `yfinance.Ticker` to return a Mock whose `.history(period="3mo")` returns a 60-row pandas DataFrame loaded from `yfinance_aapl_history.json` (json round-tripped to DataFrame), and whose `.fast_info` returns `{"last_price": 180.5, "lastPrice": 180.5}`. Assert: result.ticker == "AAPL", result.source == "yfinance", result.data_unavailable is False, result.current_price == 180.5, len(result.history) == 60, result.history[0].close > 0.
    - test_prices_empty: patch `yfinance.Ticker` to return a Mock whose `.history()` returns an empty DataFrame and whose `.fast_info` raises (or has no last_price). ALSO patch `yahooquery.Ticker` to also fail (return `{"AAPL": "Quote not found"}` shape). Assert: result.data_unavailable is True, result.current_price is None, result.history == [].
    - test_prices_yfinance_fast_info_missing_falls_to_info: patch yfinance so `.fast_info.last_price` raises AttributeError but `.info["regularMarketPrice"] == 175.0`. Assert: result.current_price == 175.0, result.source == "yfinance" (still primary).
    - test_prices_normalizes_ticker_for_yfinance_call: call `fetch_prices("brk.b")` and assert `yfinance.Ticker` was called with "BRK-B" (normalized form — yfinance expects hyphen for class shares).

    test_fallback.py (probe 2-W2-03):
    - test_yfinance_empty_yahooquery_succeeds: patch yfinance to return empty history (data_unavailable trigger) AND patch yahooquery.Ticker so `.price` returns `{"AAPL": {"regularMarketPrice": 178.0, "regularMarketTime": 1714579200, ...}}` from yahooquery_aapl_price.json fixture. Assert: result.source == "yahooquery", result.data_unavailable is False, result.current_price == 178.0. (yahooquery doesn't supply OHLC history in the simple .price call — for fallback we accept current_price only and history may be empty; spec says fallback is a price source, not full history.)
    - test_yahooquery_quote_not_found: patch yfinance empty + patch yahooquery to return `{"AAPL": "Quote not found"}` (yahooquery's actual error shape — a string instead of a dict). Assert: result.data_unavailable is True, result.source ∈ {"yfinance", "yahooquery"} (whichever was the last attempted; we accept either — caller cares about data_unavailable, not source ID, when nothing worked). Document this in test docstring.
    - test_yahooquery_network_error: patch yfinance empty + patch yahooquery.Ticker to raise an arbitrary requests.exceptions.RequestException. Assert: data_unavailable is True (no propagation of upstream exception).
  </behavior>
  <action>
    RED phase:
    1. Create fixtures:
       - `yfinance_aapl_history.json`: a list of 60 daily bars `[{"date": "2026-02-01", "open": 175.5, "high": 178.2, "low": 174.8, "close": 177.1, "volume": 50000000}, ...]`. Use a simple synthetic generator script in the test file's docstring; commit the file as plain JSON. The test loads this and converts to a pandas DataFrame.
       - `yfinance_empty_history.json`: `[]` (empty list — represents an empty DataFrame).
       - `yahooquery_aapl_price.json`: `{"AAPL": {"regularMarketPrice": 178.0, "regularMarketTime": 1714579200, "regularMarketDayHigh": 179.5, "regularMarketDayLow": 177.0, "currency": "USD"}}` — minimal yahooquery .price shape.
    2. Write `tests/ingestion/test_prices.py` with the 4 tests. Use `unittest.mock.patch("ingestion.prices.yfinance.Ticker")` (mocking at the boundary inside the module under test). Helper to load fixture as DataFrame: `pd.DataFrame.from_records(json.loads(path.read_text()))` — convert "date" column to datetime index.
    3. Write `tests/ingestion/test_fallback.py` with the 3 tests. Patches both `yfinance.Ticker` and `yahooquery.Ticker`.
    4. Run `uv run pytest tests/ingestion/test_prices.py tests/ingestion/test_fallback.py -x -q` → fails (ingestion/prices.py is empty/missing).
    5. Commit: `test(02-02): add failing tests for fetch_prices + yahooquery fallback (probes 2-W2-01..03)`

    GREEN phase:
    6. Implement `ingestion/prices.py`:
       - Module docstring: cite Pitfall #1 (silent breakage — sanity checks mandatory) and DATA-08 (yahooquery fallback contract).
       - `import yfinance`, `import yahooquery`, `from datetime import datetime, timezone`, `from analysts.schemas import normalize_ticker`, `from analysts.data.prices import OHLCBar, PriceSnapshot`.
       - `def _fetch_yfinance(ticker: str, period: str) -> PriceSnapshot | None`: try yfinance.Ticker(ticker); call .history(period=period); if df is empty → return None. Else build OHLCBar list. For current_price: try `t.fast_info.last_price` first; if AttributeError or None, try `t.info.get("regularMarketPrice")`; if still None and history non-empty, use history[-1].close. Sanity check: current_price > 0 AND len(history) >= 1, else return None. On any Exception (yfinance internals), return None — never propagate.
       - `def _fetch_yahooquery(ticker: str) -> PriceSnapshot | None`: try yahooquery.Ticker(ticker); access .price; expected shape `{ticker: {regularMarketPrice: float, ...}}`. If the value at .price[ticker] is a string (yahooquery's "Quote not found" error shape) or dict missing regularMarketPrice → return None. Else build PriceSnapshot with source="yahooquery", history=[] (yahooquery .price doesn't supply history; that's a documented limitation). Wrap in try/except for any RequestException or AttributeError → return None.
       - `def fetch_prices(ticker: str, *, period: str = "3mo") -> PriceSnapshot`:
         - normalize ticker via `normalize_ticker(ticker)`; if None, return PriceSnapshot(ticker=ticker, fetched_at=datetime.now(timezone.utc), source="yfinance", data_unavailable=True). (Pydantic would reject the bad ticker on construction; we hand-construct with the original-ish input but mark unavailable. Better path: raise ValueError? Decision: for ingestion, soft-fail for bad tickers — they shouldn't reach here, and surfacing them as data_unavailable lets the orchestrator continue.)
         - Try `_fetch_yfinance(normalized, period)`; if non-None, return it.
         - Try `_fetch_yahooquery(normalized)`; if non-None, return it.
         - Both failed → return PriceSnapshot(ticker=normalized, fetched_at=datetime.now(timezone.utc), source="yfinance", data_unavailable=True). (We pick "yfinance" for the source field as the canonical primary attempt; data_unavailable=True signals nothing worked.)
       - DataFrame → OHLCBar conversion: iterate `df.itertuples()` or `df.iterrows()`, build OHLCBar with `date=row.Index.date()` (yfinance returns DatetimeIndex). Drop rows with NaN.
    7. Run `uv run pytest tests/ingestion/test_prices.py tests/ingestion/test_fallback.py -v` → all 7 tests green.
    8. Coverage: `uv run pytest --cov=ingestion.prices --cov-branch tests/ingestion/test_prices.py tests/ingestion/test_fallback.py` → ≥90% line / ≥85% branch on ingestion/prices.py.
    9. Commit: `feat(02-02): implement fetch_prices with yahooquery fallback`

    Probe ID test docstring comments:
    - 2-W2-01 → `test_prices_happy`
    - 2-W2-02 → `test_prices_empty` (canonical) + `test_prices_yfinance_fast_info_missing_falls_to_info` (variant)
    - 2-W2-03 → `test_yfinance_empty_yahooquery_succeeds`
  </action>
  <verify>
    <automated>uv run pytest tests/ingestion/test_prices.py tests/ingestion/test_fallback.py -v &amp;&amp; uv run pytest --cov=ingestion.prices --cov-branch tests/ingestion/test_prices.py tests/ingestion/test_fallback.py</automated>
  </verify>
  <done>7 tests green across test_prices.py + test_fallback.py. ingestion/prices.py at ≥90% line / ≥85% branch. Three fixture files committed. Probes 2-W2-01, 2-W2-02, 2-W2-03 satisfied. fetch_prices is the single entry point used by Plan 02-06.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: TDD ingestion/fundamentals.py</name>
  <files>tests/ingestion/test_fundamentals.py, tests/ingestion/fixtures/yfinance_aapl_info.json, ingestion/fundamentals.py</files>
  <behavior>
    Probes 2-W2-04 (happy) + 2-W2-05 (missing keys → data_unavailable, NOT KeyError).

    test_fundamentals.py:
    - test_fund_happy: patch yfinance.Ticker to return Mock whose `.info` is loaded from `yfinance_aapl_info.json` (real-shape dict with trailingPE, priceToSalesTrailing12Months, priceToBook, returnOnEquity, debtToEquity, profitMargins, freeCashflow, marketCap). Assert: result.ticker == "AAPL", result.source == "yfinance", result.pe ≈ value, result.market_cap > 0, result.data_unavailable is False.
    - test_fund_missing: patch .info to return `{}` (empty dict — Yahoo silent-breakage symptom). Assert: result.data_unavailable is True, all metric fields None. NO KeyError surfaces.
    - test_fund_partial: patch .info to return only `{"trailingPE": 28.5, "marketCap": 3_000_000_000_000}`. Assert: result.pe == 28.5, result.market_cap == 3_000_000_000_000, result.ps is None, result.roe is None, result.data_unavailable is False (we treat "some keys present" as available; downstream sanity checks decide).
    - test_fund_yfinance_raises: patch yfinance.Ticker to raise an arbitrary Exception on construction. Assert: result.data_unavailable is True (no propagation).
    - test_fund_normalizes_ticker: fetch_fundamentals("BRK.B") → ticker == "BRK-B" and yfinance was called with "BRK-B".
  </behavior>
  <action>
    RED phase:
    1. Create `yfinance_aapl_info.json`: a 30-key snapshot of yfinance's .info dict for AAPL — `{"trailingPE": 28.5, "priceToSalesTrailing12Months": 7.2, "priceToBook": 45.0, "returnOnEquity": 1.65, "debtToEquity": 1.85, "profitMargins": 0.25, "freeCashflow": 100_000_000_000, "marketCap": 3_000_000_000_000, "regularMarketPrice": 180.5, "longName": "Apple Inc.", "currency": "USD"}` — minimal but realistic.
    2. Write `tests/ingestion/test_fundamentals.py` with 5 tests above. Use `unittest.mock.patch("ingestion.fundamentals.yfinance.Ticker")`.
    3. Run `uv run pytest tests/ingestion/test_fundamentals.py -x -q` → fails (module empty).
    4. Commit: `test(02-02): add failing tests for fetch_fundamentals (probes 2-W2-04..05)`

    GREEN phase:
    5. Implement `ingestion/fundamentals.py`:
       - Module docstring: cite DATA-02 (key list) and DATA-06 (sanity check / data_unavailable contract).
       - `import yfinance`, `from datetime import datetime, timezone`, `from analysts.schemas import normalize_ticker`, `from analysts.data.fundamentals import FundamentalsSnapshot`.
       - `def fetch_fundamentals(ticker: str) -> FundamentalsSnapshot`:
         - normalize ticker; if None → return FundamentalsSnapshot(ticker=ticker_input_or_placeholder, fetched_at=now_utc, source="yfinance", data_unavailable=True). Use a sentinel valid ticker like "INVALID" if the user input fails normalization — Pydantic must accept; document.
         - try block around `info = yfinance.Ticker(normalized).info`. On any Exception (yfinance internals, network), return FundamentalsSnapshot(ticker=normalized, fetched_at=now_utc, source="yfinance", data_unavailable=True).
         - If info is empty dict OR missing all of the canonical-marker keys (trailingPE AND marketCap both None/missing) → mark data_unavailable=True.
         - Build FundamentalsSnapshot with: pe=info.get("trailingPE"), ps=info.get("priceToSalesTrailing12Months"), pb=info.get("priceToBook"), roe=info.get("returnOnEquity"), debt_to_equity=info.get("debtToEquity"), profit_margin=info.get("profitMargins"), free_cash_flow=info.get("freeCashflow"), market_cap=info.get("marketCap").
         - For type safety, wrap `info.get(k)` in `_safe_float` that returns None on TypeError or non-numeric strings — yfinance occasionally returns "Infinity" or other oddities. Local helper inside the module.
    6. Run `uv run pytest tests/ingestion/test_fundamentals.py -v` → all 5 green.
    7. Coverage: `uv run pytest --cov=ingestion.fundamentals --cov-branch tests/ingestion/test_fundamentals.py` → ≥90% line / ≥85% branch.
    8. Run plan-scoped suite: `uv run pytest tests/ingestion/ -v` → confirm Wave-1 + new Wave-2 tests all green together.
    9. Commit: `feat(02-02): implement fetch_fundamentals with missing-key tolerance`

    Probe ID test docstring comments:
    - 2-W2-04 → `test_fund_happy`
    - 2-W2-05 → `test_fund_missing`
  </action>
  <verify>
    <automated>uv run pytest tests/ingestion/test_fundamentals.py -v &amp;&amp; uv run pytest --cov=ingestion.fundamentals --cov-branch tests/ingestion/test_fundamentals.py &amp;&amp; uv run pytest tests/ingestion/ -v</automated>
  </verify>
  <done>5 fundamentals tests green. ingestion/fundamentals.py at ≥90% line / ≥85% branch. Probes 2-W2-04 + 2-W2-05 satisfied. fetch_fundamentals tolerates empty .info, missing keys, partial data, raised exceptions — never KeyErrors. Combined Wave 1 + Plan 02-02 tests all green.</done>
</task>

</tasks>

<verification>
- Probes covered: 2-W2-01, 2-W2-02, 2-W2-03, 2-W2-04, 2-W2-05.
- Requirements satisfied: DATA-01 (OHLC + current price), DATA-02 (P/E + P/S + ROE + D/E + margins + FCF), DATA-07 (data_unavailable flag), DATA-08 (yahooquery fallback).
- Coverage gates: ≥90% line / ≥85% branch on ingestion/prices.py and ingestion/fundamentals.py.
- Zero real network in test suite — all yfinance/yahooquery calls go through unittest.mock.patch.
- `uv run pytest -x -q` (whole repo) — all green; total ~50+12 = 62 tests.

## Cross-Scope Risks

_vault_status=budget_exhausted; re-run /gmd:plan-phase --replan after vault-maintain_
</verification>

<success_criteria>
1. fetch_prices(ticker) returns valid PriceSnapshot for happy yfinance, falls back to yahooquery on yfinance empty, marks data_unavailable when both fail. Never raises for upstream breakage.
2. fetch_fundamentals(ticker) returns FundamentalsSnapshot with all available metrics; tolerates missing keys, empty dicts, exceptions; never raises KeyError.
3. All five probes (2-W2-01..05) map to named test functions with probe-id comments.
4. Three fixture files committed (yfinance happy history, yfinance empty history, yahooquery price).
5. Plan 02-06 can import fetch_prices and fetch_fundamentals as the public price/fundamental entry points.
</success_criteria>

<output>
After completion, create `.planning/phases/02-ingestion-keyless-data-plane/02-02-SUMMARY.md`.
</output>
