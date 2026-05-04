# novel-to-this-project — Phase 2 ingested-data schema (project-original).
"""Fundamentals schema: FundamentalsSnapshot.

All metrics are Optional[float] with NO positivity constraint at the schema
layer because real-world data legitimately includes negatives (free cash flow,
ROE for losing firms) and zeros (debt-to-equity for unlevered companies).
Downstream sanity checks in ingestion/fundamentals.py and analyst scoring
enforce ranges where the math demands it; the schema is just shape.

Plan 02-07 amendment — adds 4 yfinance analyst-consensus fields
(analyst_target_mean / analyst_target_median / analyst_recommendation_mean /
analyst_opinion_count) consumed by Phase 3's valuation analyst (ANLY-04)
as the tertiary blend tier. All four are Optional and additive; existing
serialized snapshots round-trip cleanly through the new schema.

ticker normalization delegates to analysts.schemas.normalize_ticker.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from analysts.schemas import normalize_ticker


class FundamentalsSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

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

    # NEW (Plan 02-07): yfinance analyst-consensus fields. Optional;
    # populated by ingestion/fundamentals.py from info["targetMeanPrice"]
    # / info["targetMedianPrice"] / info["recommendationMean"] /
    # info["numberOfAnalystOpinions"]. Consumed in Phase 3 by
    # analysts/valuation.py (tertiary blend tier — falls back to thesis_price
    # and target_multiples when configured).
    #
    # recommendationMean is on Yahoo's 1.0..5.0 scale: 1.0=strong_buy,
    # 2.0=buy, 3.0=hold, 4.0=underperform, 5.0=strong_sell. Downstream
    # scoring re-bins to a {-1, 0, +1} verdict.
    analyst_target_mean: Optional[float] = None
    analyst_target_median: Optional[float] = None
    analyst_recommendation_mean: Optional[float] = None
    analyst_opinion_count: Optional[int] = None

    @field_validator("ticker", mode="before")
    @classmethod
    def _normalize_ticker_field(cls, v: object) -> str:
        norm = normalize_ticker(v) if isinstance(v, str) else None
        if norm is None:
            raise ValueError(f"invalid ticker {v!r}")
        return norm
