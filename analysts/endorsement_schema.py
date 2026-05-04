# novel-to-this-project — endorsement signal capture for newsletter/service calls.
"""Pydantic v2 Endorsement record. Append-only; performance math deferred to v1.x.

schema_version: Literal[1] = 1 is LOAD-BEARING — v1.x ENDORSE-04..07 will bump
to Literal[2] (or introduce Union[V1Endorsement, V2Endorsement]) so v1 records
cannot be silently misread as "0% performance" once perf fields exist.

Mirrors analysts/schemas.py discipline: ConfigDict(extra='forbid'), reuses
analysts.schemas.normalize_ticker as the single source of truth for canonical
ticker form (BRK.B -> BRK-B, aapl -> AAPL).
"""
from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from analysts.schemas import normalize_ticker


class Endorsement(BaseModel):
    """One newsletter / service / analyst call. Append-only.

    schema_version locks forward-compatibility — v1.x will introduce Literal[2]
    (or a discriminated union) so future readers cannot silently misinterpret
    v1 records as having implicit "0% performance" once perf fields land.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    ticker: str
    source: str = Field(min_length=1, max_length=200)
    date: date_type
    price_at_call: float = Field(gt=0)
    notes: str = Field(default="", max_length=2000)
    captured_at: datetime

    @field_validator("ticker", mode="before")
    @classmethod
    def _normalize_ticker_field(cls, v: object) -> str:
        norm = normalize_ticker(v) if isinstance(v, str) else None
        if norm is None:
            raise ValueError(f"invalid ticker {v!r}")
        return norm
