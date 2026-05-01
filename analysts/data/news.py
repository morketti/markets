"""News-headline schema: Headline.

ingestion/news.py (Plan 02-04) returns list[Headline] — one per parsed RSS
entry / FinViz row. Cross-source dedup is handled by the caller via the
`dedup_key` field (e.g. "yahoo-rss::<entry.id>" or normalized-title fallback).

`url` is a plain str (not pydantic.HttpUrl): Yahoo redirect URLs sometimes
fail HttpUrl's strict scheme/host checks even when the URL is functional.
ingestion/news.py does its own minimum validation (must start with http) on
the way in.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from analysts.schemas import normalize_ticker


class Headline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str
    fetched_at: datetime
    source: Literal["yahoo-rss", "google-news", "finviz"]
    data_unavailable: bool = False
    title: str = Field(min_length=1, max_length=500)
    url: str
    published_at: Optional[datetime] = None
    summary: str = Field(default="", max_length=2000)
    dedup_key: str

    @field_validator("ticker", mode="before")
    @classmethod
    def _normalize_ticker_field(cls, v: object) -> str:
        norm = normalize_ticker(v) if isinstance(v, str) else None
        if norm is None:
            raise ValueError(f"invalid ticker {v!r}")
        return norm
