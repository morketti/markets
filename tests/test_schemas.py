"""Schema validation tests for analysts.schemas (Plan 01-02).

Covers WATCH-04 (per-ticker config schema) and WATCH-05 (validation rules).

Each test maps to one probe from 01-VALIDATION.md:
    test_long_term_lens_enum             -> 1-W1-01
    test_support_below_resistance        -> 1-W1-02
    test_target_multiples_positive       -> 1-W1-03
    test_notes_max_length                -> 1-W1-04
    test_thesis_price_negative_rejected  -> 1-W1-05
    test_support_equals_resistance_rejected -> 1-W1-06
    test_watchlist_key_mismatch          -> 1-W1-07
    test_ticker_normalization            -> 1-W1-08
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from analysts.schemas import (
    FundamentalTargets,
    TechnicalLevels,
    TickerConfig,
    Watchlist,
    normalize_ticker,
)


# ----------------------------------------------------------------------
# 1-W1-01: long_term_lens enum
# ----------------------------------------------------------------------
def test_long_term_lens_enum() -> None:
    # Each valid value succeeds.
    for lens in ("value", "growth", "contrarian", "mixed"):
        cfg = TickerConfig(ticker="AAPL", long_term_lens=lens)
        assert cfg.long_term_lens == lens

    # An invalid lens raises with the field name in the error path.
    with pytest.raises(ValidationError) as exc_info:
        TickerConfig(ticker="AAPL", long_term_lens="invalid_lens")
    errors = exc_info.value.errors()
    assert any("long_term_lens" in e["loc"] for e in errors)


# ----------------------------------------------------------------------
# 1-W1-02: TechnicalLevels.support < resistance (cross-field)
# ----------------------------------------------------------------------
def test_support_below_resistance() -> None:
    # Happy path: support strictly below resistance.
    levels = TechnicalLevels(support=100.0, resistance=200.0)
    assert levels.support == 100.0
    assert levels.resistance == 200.0

    # support > resistance must raise and mention both names.
    with pytest.raises(ValidationError) as exc_info:
        TechnicalLevels(support=200.0, resistance=100.0)
    msg = str(exc_info.value)
    assert "support" in msg
    assert "resistance" in msg


# ----------------------------------------------------------------------
# 1-W1-03: FundamentalTargets — every *_target must be positive when set
# ----------------------------------------------------------------------
def test_target_multiples_positive() -> None:
    # Single positive target: succeeds.
    assert FundamentalTargets(pe_target=15).pe_target == 15

    # Defaults (all None) succeed.
    assert FundamentalTargets().pe_target is None

    # Negative is rejected.
    with pytest.raises(ValidationError):
        FundamentalTargets(pe_target=-1)

    # Zero is rejected (strict > 0).
    with pytest.raises(ValidationError):
        FundamentalTargets(pe_target=0)

    # Mixed valid + invalid: error must name the invalid field.
    with pytest.raises(ValidationError) as exc_info:
        FundamentalTargets(pe_target=15, ps_target=-1)
    errors = exc_info.value.errors()
    assert any("ps_target" in e["loc"] for e in errors)

    # All three set valid: succeeds.
    ft = FundamentalTargets(pe_target=15, ps_target=4, pb_target=2)
    assert (ft.pe_target, ft.ps_target, ft.pb_target) == (15, 4, 2)


# ----------------------------------------------------------------------
# 1-W1-04: notes max_length=1000
# ----------------------------------------------------------------------
def test_notes_max_length() -> None:
    # Exactly 1000 chars: succeeds.
    cfg = TickerConfig(ticker="AAPL", notes="x" * 1000)
    assert len(cfg.notes) == 1000

    # 1001 chars: rejected, with "notes" in the loc path.
    with pytest.raises(ValidationError) as exc_info:
        TickerConfig(ticker="AAPL", notes="x" * 1001)
    errors = exc_info.value.errors()
    assert any("notes" in e["loc"] for e in errors)


# ----------------------------------------------------------------------
# 1-W1-05: thesis_price > 0 when set; None and positive succeed
# ----------------------------------------------------------------------
def test_thesis_price_negative_rejected() -> None:
    # Negative: rejected, with thesis_price in loc.
    with pytest.raises(ValidationError) as exc_info:
        TickerConfig(ticker="AAPL", thesis_price=-100)
    assert any("thesis_price" in e["loc"] for e in exc_info.value.errors())

    # Zero: rejected (strict > 0).
    with pytest.raises(ValidationError) as exc_info:
        TickerConfig(ticker="AAPL", thesis_price=0)
    assert any("thesis_price" in e["loc"] for e in exc_info.value.errors())

    # Positive: succeeds.
    assert TickerConfig(ticker="AAPL", thesis_price=100).thesis_price == 100

    # None: succeeds (the default; field is optional).
    assert TickerConfig(ticker="AAPL", thesis_price=None).thesis_price is None


# ----------------------------------------------------------------------
# 1-W1-06: support == resistance is rejected (use >=, not >)
# ----------------------------------------------------------------------
def test_support_equals_resistance_rejected() -> None:
    with pytest.raises(ValidationError):
        TechnicalLevels(support=100.0, resistance=100.0)


# ----------------------------------------------------------------------
# 1-W1-07: Watchlist key must equal value.ticker (strict mode, no rewrite)
# ----------------------------------------------------------------------
def test_watchlist_key_mismatch() -> None:
    # Mismatched key raises and the offending key appears in the message.
    with pytest.raises(ValidationError) as exc_info:
        Watchlist(tickers={"aapl": TickerConfig(ticker="AAPL")})
    assert "aapl" in str(exc_info.value)

    # Matching key succeeds.
    wl = Watchlist(tickers={"AAPL": TickerConfig(ticker="AAPL")})
    assert "AAPL" in wl.tickers


# ----------------------------------------------------------------------
# 1-W1-08: ticker normalization — exercise field validator AND module helper
# ----------------------------------------------------------------------
def test_ticker_normalization() -> None:
    # Case insensitive uppercase.
    assert TickerConfig(ticker="aapl").ticker == "AAPL"

    # Class-share separators all collapse to hyphen.
    assert TickerConfig(ticker="BRK.B").ticker == "BRK-B"
    assert TickerConfig(ticker="BRK/B").ticker == "BRK-B"
    assert TickerConfig(ticker="BRK_B").ticker == "BRK-B"
    assert TickerConfig(ticker="brk-b").ticker == "BRK-B"

    # Whitespace stripping.
    assert TickerConfig(ticker=" AAPL ").ticker == "AAPL"

    # Invalid forms.
    with pytest.raises(ValidationError):
        TickerConfig(ticker="^GSPC")  # starts with non-alpha
    with pytest.raises(ValidationError):
        TickerConfig(ticker="EURUSD=X")  # contains '='
    with pytest.raises(ValidationError):
        TickerConfig(ticker="1AAPL")  # starts with digit
    with pytest.raises(ValidationError):
        TickerConfig(ticker="TOOLONGTICKER")  # > 9 chars
    with pytest.raises(ValidationError):
        TickerConfig(ticker="")  # empty
    with pytest.raises(ValidationError):
        TickerConfig(ticker=123)  # non-string

    # Module-level helper called directly.
    assert normalize_ticker("brk.b") == "BRK-B"
    assert normalize_ticker("AAPL") == "AAPL"
    assert normalize_ticker(" aapl ") == "AAPL"
    assert normalize_ticker("^GSPC") is None
    assert normalize_ticker(123) is None  # type: ignore[arg-type]
    assert normalize_ticker("") is None
