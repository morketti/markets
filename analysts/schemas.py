"""Pydantic v2 schemas for the markets watchlist.

This module is the locked source of truth for ticker configuration shape and
validation rules. Downstream phases (loader Plan 03, CLI Plans 04-05, ingestion
Phase 2, agents Phase 3, etc.) MUST import from here and never duplicate the
schema or its validators.

Public surface:
    TechnicalLevels, FundamentalTargets, TickerConfig, Watchlist
    normalize_ticker(s)  -- module-level helper, returns canonical hyphen form
                            or None on invalid input. Reused by cli/* without
                            duplication.

Naming note: lives in `analysts/` rather than `watchlist/` because every analyst
package (Phase 3) needs to import the per-ticker config to score against the
user's thesis_price / technical_levels / target_multiples. Putting it in
`analysts/` keeps imports flowing one direction (analysts <- watchlist) and
avoids a circular dependency once Phase 3 lands.
"""
from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# yfinance uses hyphenated class-share notation (BRK-B, RDS-A); we normalize to
# that form for downstream Phase 2 compatibility. The matcher allows BOTH dot
# and hyphen so a user mistakenly typing "BRK.B" doesn't get a misleading
# "regex mismatch" error before the normalizer runs -- the normalizer always
# emits hyphen form. See 01-CONTEXT.md correction #1.
_TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]{0,8}$")


def normalize_ticker(s: str) -> Optional[str]:
    """Normalize a ticker string to canonical hyphen form, or return None if invalid.

    Accepts dot, slash, underscore, hyphen as class-share separators; emits hyphen.
    Strips whitespace, uppercases, collapses repeated hyphens.
    Returns None when the result doesn't match _TICKER_PATTERN -- caller decides
    how to error (the schema's @field_validator raises ValueError; CLI plans
    print a friendly message and exit non-zero).

    This is the single source of truth for ticker normalization across the
    codebase. Plans 04 and 05 (cli/remove_ticker.py, cli/show_ticker.py) MUST
    import and call this helper rather than duplicate the logic.
    """
    if not isinstance(s, str):
        return None
    norm = s.strip().upper().replace(".", "-").replace("/", "-").replace("_", "-")
    norm = re.sub(r"-+", "-", norm)
    return norm if _TICKER_PATTERN.match(norm) else None


class TechnicalLevels(BaseModel):
    """Optional support / resistance pair for a ticker.

    Both bounds independently must be > 0 when set; together support must be
    strictly less than resistance (cross-field rule via @model_validator since
    @field_validator only sees partial state).
    """

    model_config = ConfigDict(validate_assignment=True, extra="forbid")
    support: Optional[float] = None
    resistance: Optional[float] = None

    @field_validator("support", "resistance")
    @classmethod
    def positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("must be positive")
        return v

    @model_validator(mode="after")
    def support_below_resistance(self) -> "TechnicalLevels":
        if self.support is not None and self.resistance is not None:
            if self.support >= self.resistance:
                raise ValueError(
                    f"support ({self.support}) must be less than resistance "
                    f"({self.resistance})"
                )
        return self


class FundamentalTargets(BaseModel):
    """Optional valuation-multiple targets used by analyst scoring.

    Each multiple, when set, must be strictly > 0 (a P/E of 0 is meaningless;
    a negative target is almost certainly a typo). All single-field rules, so
    @field_validator is sufficient.
    """

    model_config = ConfigDict(validate_assignment=True, extra="forbid")
    pe_target: Optional[float] = None
    ps_target: Optional[float] = None
    pb_target: Optional[float] = None

    @field_validator("pe_target", "ps_target", "pb_target")
    @classmethod
    def positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("must be positive")
        return v


class TickerConfig(BaseModel):
    """Per-ticker configuration: short-term/long-term focus, thesis, levels, targets.

    The `ticker` field is the primary key; it is normalized in place via the
    @field_validator(mode="before") which delegates to the module-level
    normalize_ticker() helper. This keeps the normalization rule in exactly one
    place across schema + CLI.
    """

    model_config = ConfigDict(validate_assignment=True, extra="forbid")
    ticker: str
    short_term_focus: bool = True
    long_term_lens: Literal["value", "growth", "contrarian", "mixed"] = "mixed"
    thesis_price: Optional[float] = None
    technical_levels: Optional[TechnicalLevels] = None
    target_multiples: Optional[FundamentalTargets] = None
    notes: str = Field(default="", max_length=1000)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @field_validator("ticker", mode="before")
    @classmethod
    def _normalize_ticker_field(cls, v: object) -> str:
        # Delegate to module-level helper (single source of truth).
        # Helper returns None on any invalid input (non-string, regex mismatch);
        # we translate that into a ValueError so Pydantic surfaces a
        # ValidationError with "ticker" in the loc path.
        norm = normalize_ticker(v) if isinstance(v, str) else None
        if norm is None:
            raise ValueError(
                f"invalid ticker {v!r}: must match {_TICKER_PATTERN.pattern} "
                f"after normalization (uppercase, dot/slash/underscore -> hyphen)"
            )
        return norm

    @field_validator("thesis_price")
    @classmethod
    def thesis_price_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("thesis_price must be positive")
        return v


class Watchlist(BaseModel):
    """Top-level watchlist file shape: version + dict of ticker configs.

    Strict mode: every dict key must equal its value's `.ticker` field after
    normalization. We do NOT silently rewrite the key to match -- that would
    mask user typos and produce surprise behavior in `git diff watchlist.json`
    (per 01-RESEARCH.md Pitfall #4).
    """

    model_config = ConfigDict(validate_assignment=True, extra="forbid")
    version: int = 1
    tickers: dict[str, TickerConfig] = Field(default_factory=dict)

    @model_validator(mode="after")
    def keys_match_tickers(self) -> "Watchlist":
        for k, v in self.tickers.items():
            if k != v.ticker:
                raise ValueError(
                    f"watchlist key {k!r} does not match its ticker field "
                    f"{v.ticker!r} (after normalization). Fix the key in "
                    f"watchlist.json or use the CLI to re-add the ticker."
                )
        return self
