# novel-to-this-project — Phase 2 schema package marker (project-original).
"""Pydantic schemas for ingested data — single source of truth for shapes
fetched in Phase 2. Each module owns one domain (prices, fundamentals,
filings, news, social, snapshot). Plans 02-02..02-06 import from here;
do not redefine.
"""
from analysts.data.filings import FilingMetadata
from analysts.data.fundamentals import FundamentalsSnapshot
from analysts.data.news import Headline
from analysts.data.prices import OHLCBar, PriceSnapshot
from analysts.data.snapshot import Snapshot
from analysts.data.social import RedditPost, SocialSignal, StockTwitsPost

__all__ = [
    "OHLCBar",
    "PriceSnapshot",
    "FundamentalsSnapshot",
    "FilingMetadata",
    "Headline",
    "RedditPost",
    "StockTwitsPost",
    "SocialSignal",
    "Snapshot",
]
