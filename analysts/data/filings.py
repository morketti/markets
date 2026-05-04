# novel-to-this-project — Phase 2 ingested-data schema (project-original).
"""SEC filings schema: FilingMetadata.

ingestion/filings.py (Plan 02-03) returns list[FilingMetadata] — one entry
per filing. Schema validates a single filing.

The form_type Literal covers the forms we care about for the watchlist; an
"OTHER" escape-hatch lets EDGAR return forms we don't enumerate (foreign
S-3, etc.) without 500ing the entire fetch — Plan 02-03 maps unknown forms
to "OTHER" rather than dropping them.

CIK pattern enforces the 10-digit zero-padded format SEC's submissions API
uses (e.g. "0000320193" for AAPL). Plan 02-03 zero-pads on lookup.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from analysts.schemas import normalize_ticker

FormType = Literal["10-K", "10-Q", "8-K", "DEF 14A", "S-1", "20-F", "6-K", "OTHER"]


class FilingMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str
    fetched_at: datetime
    source: Literal["edgar"] = "edgar"
    data_unavailable: bool = False
    cik: Optional[str] = Field(default=None, pattern=r"^\d{10}$")
    form_type: FormType
    accession_number: Optional[str] = None
    filed_date: Optional[date] = None
    primary_document: Optional[str] = None  # URL fragment; full URL built by caller
    summary: str = ""

    @field_validator("ticker", mode="before")
    @classmethod
    def _normalize_ticker_field(cls, v: object) -> str:
        norm = normalize_ticker(v) if isinstance(v, str) else None
        if norm is None:
            raise ValueError(f"invalid ticker {v!r}")
        return norm
