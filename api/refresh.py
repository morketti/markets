# novel-to-this-project — Vercel Python serverless adapter; thin wrapper
# over ingestion.prices.fetch_prices + ingestion.news.fetch_news. NO LLM
# calls. Designed for sub-10s execution under Vercel's 30s maxDuration cap.
"""api/refresh.py — Vercel Python serverless mid-day refresh.

Public surface:
    GET /api/refresh?ticker=AAPL
        → 200 JSON {ticker, current_price, price_timestamp,
                    recent_headlines, errors, partial}

Response shapes (LOCKED in 08-CONTEXT.md):

    Success:
        {"ticker":"AAPL","current_price":178.42,"price_timestamp":"...",
         "recent_headlines":[...],"errors":[],"partial":false}

    Partial (RSS unavailable, price OK):
        {"ticker":"AAPL","current_price":178.42,"price_timestamp":"...",
         "recent_headlines":[],"errors":["rss-unavailable"],"partial":true}

    Full failure (yfinance + yahooquery both throw or data_unavailable):
        {"ticker":"AAPL","error":true,
         "errors":["yfinance-unavailable","yahooquery-unavailable"],
         "partial":true}
        (NO current_price field in this shape)

Behaviour:
    - data_unavailable=True from fetch_prices → full-failure shape
    - empty headlines from fetch_news → partial=true with rss-unavailable
    - any caught exception in upstream calls → mapped to error envelope, NEVER 5xx
    - missing/empty ?ticker= → 400 with errors=["missing-ticker-param" |
      "invalid-ticker"]

Why no LLM here:
    PROJECT.md keyless data plane lock + REFRESH-02 explicit "no LLM calls".
    routine.llm_client must NOT be imported.

Why no CORS headers:
    Frontend (xxx.vercel.app/scan/today) and this function (xxx.vercel.app/api/refresh)
    are SAME-ORIGIN — browser never preflights. Confirmed via Vercel KB.
"""
from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Prepend repo root so `from ingestion.prices import fetch_prices` works under
# Vercel's serverless Python runtime. The function file sits at api/refresh.py;
# repo_root is parents[1]. Vercel's Python runtime does NOT add sibling
# top-level packages to sys.path by default — this bootstrap is load-bearing.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from analysts.schemas import normalize_ticker  # noqa: E402
from ingestion.news import fetch_news  # noqa: E402
from ingestion.prices import fetch_prices  # noqa: E402


def _build_response(path: str) -> tuple[dict, int]:
    """Pure builder: parse query string, fan out to upstream calls, compose envelope.

    Returns (payload_dict, http_status). Tests drive this directly to bypass
    BaseHTTPRequestHandler plumbing.
    """
    parsed = urlparse(path)
    # keep_blank_values=True so we can distinguish ?ticker= (empty value
    # → "invalid-ticker") from /api/refresh with no query string at all
    # (→ "missing-ticker-param"). Without this flag parse_qs drops the
    # empty entry and both shapes look identical.
    query = parse_qs(parsed.query, keep_blank_values=True)

    # 1. Validate ticker query param.
    if "ticker" not in query:
        return ({"error": True, "errors": ["missing-ticker-param"]}, 400)
    ticker_raw = (query.get("ticker") or [""])[0]
    if not ticker_raw:
        return ({"error": True, "errors": ["invalid-ticker"]}, 400)

    normalized = normalize_ticker(ticker_raw)
    if normalized is None:
        return ({"error": True, "errors": ["invalid-ticker"]}, 400)

    errors: list[str] = []

    # 2. Fetch price (yfinance + yahooquery internal fallback already in
    #    ingestion.prices). data_unavailable=True OR a thrown exception both
    #    map to the (yfinance-unavailable + yahooquery-unavailable) error pair.
    current_price: float | None = None
    price_timestamp: str | None = None
    price_failed = False
    try:
        snap = fetch_prices(normalized, period="1d")
        if snap.data_unavailable or snap.current_price is None:
            price_failed = True
        else:
            current_price = float(snap.current_price)
            price_timestamp = snap.fetched_at.isoformat()
    except Exception:  # noqa: BLE001 — defensive; fetch_prices SHOULDN'T raise
        price_failed = True

    if price_failed:
        errors.append("yfinance-unavailable")
        errors.append("yahooquery-unavailable")

    # 3. Fetch news (per-source isolation already inside ingestion.news; an
    #    empty list IS the failure signal — distinguishes "no headlines today"
    #    from "RSS broken" by treating both as "no fresh headlines to surface").
    recent_headlines: list[dict] = []
    try:
        result = fetch_news(normalized, return_raw=True)
        # fetch_news(return_raw=True) → (list[Headline], list[dict])
        # We use the raw dict list directly — already in the 4-key shape
        # {source, published_at, title, url} the frontend expects.
        if isinstance(result, tuple) and len(result) == 2:
            _, raw = result
            recent_headlines = list(raw) if raw else []
        else:
            recent_headlines = []
    except Exception:  # noqa: BLE001 — defensive
        recent_headlines = []

    if not recent_headlines:
        errors.append("rss-unavailable")

    # 4. Compose response. partial = any errors. error=True ONLY when price
    #    failed (locked full-failure shape has no current_price field).
    partial = bool(errors)

    if price_failed:
        # Full-failure shape — NO current_price field per the lock.
        payload: dict = {
            "ticker": normalized,
            "error": True,
            "errors": errors,
            "partial": partial,
        }
    else:
        payload = {
            "ticker": normalized,
            "current_price": current_price,
            "price_timestamp": price_timestamp,
            "recent_headlines": recent_headlines,
            "errors": errors,
            "partial": partial,
        }

    return (payload, 200)


class handler(BaseHTTPRequestHandler):
    """Vercel Python runtime convention — class MUST be named `handler` (lowercase).

    do_GET delegates to _build_response (the pure builder) so tests can
    exercise the whole envelope-shaping logic without HTTP plumbing.
    """

    def do_GET(self) -> None:  # noqa: N802 — required by BaseHTTPRequestHandler
        try:
            payload, status = _build_response(self.path)
        except Exception as exc:  # noqa: BLE001 — top-level safety net
            payload = {
                "error": True,
                "errors": [f"unhandled: {exc!r}"],
                "partial": True,
            }
            status = 500

        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A002, N802
        # Silence default stderr access-log spew (Vercel captures its own).
        return
