"""Fundamentals schema: FundamentalsSnapshot.

All metrics are Optional[float] with NO positivity constraint at the schema
layer because real-world data legitimately includes negatives (free cash flow,
ROE for losing firms) and zeros (debt-to-equity for unlevered companies).
Downstream sanity checks in ingestion/fundamentals.py and analyst scoring
enforce ranges where the math demands it; the schema is just shape.

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

    @field_validator("ticker", mode="before")
    @classmethod
    def _normalize_ticker_field(cls, v: object) -> str:
        norm = normalize_ticker(v) if isinstance(v, str) else None
        if norm is None:
            raise ValueError(f"invalid ticker {v!r}")
        return norm
