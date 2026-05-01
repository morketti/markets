"""Price-data schemas: PriceSnapshot (current + history) and OHLCBar.

Single source of truth for the shape ingestion/prices.py emits. All ticker
normalization delegates to analysts.schemas.normalize_ticker — no regex
duplication.

Source Literal mirrors the data-source decision tree in 02-RESEARCH.md:
yfinance is primary; yahooquery is the fallback when yfinance returns empty
(Pitfall #1).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from analysts.schemas import normalize_ticker


class OHLCBar(BaseModel):
    """One open/high/low/close/volume bar — daily granularity for the history field."""

    model_config = ConfigDict(extra="forbid")

    date: date
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: int = Field(ge=0)


class PriceSnapshot(BaseModel):
    """Current price + optional history bars for one ticker, one fetch."""

    model_config = ConfigDict(extra="forbid")

    ticker: str
    fetched_at: datetime
    source: Literal["yfinance", "yahooquery"]
    data_unavailable: bool = False
    current_price: Optional[float] = Field(default=None, gt=0)
    history: list[OHLCBar] = Field(default_factory=list)

    @field_validator("ticker", mode="before")
    @classmethod
    def _normalize_ticker_field(cls, v: object) -> str:
        norm = normalize_ticker(v) if isinstance(v, str) else None
        if norm is None:
            raise ValueError(f"invalid ticker {v!r}")
        return norm
