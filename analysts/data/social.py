"""Social-signal schemas: SocialSignal aggregating RedditPost + StockTwitsPost.

Three nested models because the shapes are genuinely different — Reddit RSS
emits a (title, url, subreddit) triple plus optional score; StockTwits emits
a free-form `body` plus an optional user-tagged sentiment. Trying to flatten
into a single "Post" type would lose meaningful structure.

`SocialSignal.source` is "combined" by default because the orchestrator in
Plan 02-05 typically merges Reddit + StockTwits into one snapshot per ticker.
The field still accepts "reddit-rss" / "stocktwits" alone if a caller wants
to record a partial fetch.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from analysts.schemas import normalize_ticker


class RedditPost(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=500)
    url: str
    subreddit: str
    published_at: Optional[datetime] = None
    score: Optional[int] = None  # may be missing in RSS


class StockTwitsPost(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1, max_length=2000)
    created_at: Optional[datetime] = None
    sentiment: Optional[Literal["bullish", "bearish"]] = None  # only when user-tagged


class SocialSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str
    fetched_at: datetime
    source: Literal["reddit-rss", "stocktwits", "combined"] = "combined"
    data_unavailable: bool = False
    reddit_posts: list[RedditPost] = Field(default_factory=list)
    stocktwits_posts: list[StockTwitsPost] = Field(default_factory=list)
    trending_rank: Optional[int] = None  # StockTwits trending position when present

    @field_validator("ticker", mode="before")
    @classmethod
    def _normalize_ticker_field(cls, v: object) -> str:
        norm = normalize_ticker(v) if isinstance(v, str) else None
        if norm is None:
            raise ValueError(f"invalid ticker {v!r}")
        return norm
