# novel-to-this-project — Phase 2 per-ticker aggregate schema (project-original).
"""Per-ticker Snapshot — Plan 02-06 / DATA-06 / DATA-07.

A Snapshot is the per-ticker JSON object the Plan 02-06 orchestrator writes
to `snapshots/{YYYY-MM-DD}/{ticker}.json` after running all five Wave-2
sub-fetches for a single ticker. It is the durable handoff from Phase 2
(ingestion) to Phase 3+ (analysts) — they read the per-ticker JSON files
without ever touching the upstream APIs.

Shape:
    Snapshot:
        ticker: str (normalized via analysts.schemas.normalize_ticker)
        fetched_at: datetime
        data_unavailable: bool — True ONLY when EVERY sub-fetch came back
            with no useful data (per-source data_unavailable=True or
            empty list). Drives the "this ticker is dark today" branch in
            downstream analysts.
        prices: Optional[PriceSnapshot]
        fundamentals: Optional[FundamentalsSnapshot]
        filings: list[FilingMetadata]    (default [])
        news: list[Headline]              (default [])
        social: Optional[SocialSignal]
        errors: list[str] — per-source error messages from this run.

The fields exactly mirror the public surfaces of ingestion/{prices,
fundamentals, filings, news, social}.py. The orchestrator (ingestion/refresh.py)
catches per-source exceptions, sets the relevant field to None / [], and
appends an error string to `errors` — Snapshot itself enforces only the
shape contract.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from analysts.data.filings import FilingMetadata
from analysts.data.fundamentals import FundamentalsSnapshot
from analysts.data.news import Headline
from analysts.data.prices import PriceSnapshot
from analysts.data.social import SocialSignal
from analysts.schemas import normalize_ticker


class Snapshot(BaseModel):
    """Per-ticker aggregate snapshot of one refresh run.

    Caller (ingestion.refresh.run_refresh) is responsible for setting
    `data_unavailable=True` when ALL five sub-fetches reported unavailable
    or failed; this schema does not infer it from the sub-fields.
    """

    model_config = ConfigDict(extra="forbid")

    ticker: str
    fetched_at: datetime
    data_unavailable: bool = False
    prices: Optional[PriceSnapshot] = None
    fundamentals: Optional[FundamentalsSnapshot] = None
    filings: list[FilingMetadata] = Field(default_factory=list)
    news: list[Headline] = Field(default_factory=list)
    social: Optional[SocialSignal] = None
    errors: list[str] = Field(default_factory=list)

    @field_validator("ticker", mode="before")
    @classmethod
    def _normalize_ticker_field(cls, v: object) -> str:
        norm = normalize_ticker(v) if isinstance(v, str) else None
        if norm is None:
            raise ValueError(f"invalid ticker {v!r}")
        return norm
