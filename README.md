# Markets — Personal Stock Research Dashboard

Phase 1: Watchlist + Per-Ticker Config. A keyless, single-user research tool that surfaces — every morning, in one screen — which watchlist tickers need attention today and why, across short-term tactical and long-term strategic horizons.

This phase ships the foundation: a Pydantic-validated `watchlist.json` schema, atomic file I/O, and a four-subcommand CLI (`add`, `remove`, `list`, `show`).

## Quick start

**Prerequisites:** Python 3.12+ and [uv](https://docs.astral.sh/uv/) on `PATH`.

Install dependencies:

```
uv sync --dev
```

Try the example watchlist (5 tickers spanning all four lenses):

```
cp watchlist.example.json watchlist.json
uv run markets list
uv run markets show AAPL
```

Add and remove your own tickers:

```
uv run markets add MSFT --lens growth --thesis 450
uv run markets add BRK.B --lens value          # auto-normalizes to BRK-B
uv run markets remove GME --yes
```

See all flags for any subcommand:

```
uv run markets add --help
uv run markets show --help
```

If you typo a symbol the CLI suggests the closest match:

```
$ uv run markets show AAPK
error: ticker 'AAPK' not in watchlist. did you mean 'AAPL'?
```

## Per-ticker config schema

`watchlist.json` is a top-level `{version, tickers}` object. Each ticker entry conforms to `TickerConfig` (`analysts/schemas.py`):

| Field              | Type                                   | Description                                              |
| ------------------ | -------------------------------------- | -------------------------------------------------------- |
| `ticker`           | str                                    | Symbol; auto-normalized (uppercase, hyphen class shares) |
| `short_term_focus` | bool                                   | Whether short-term tactical analysis runs for this ticker |
| `long_term_lens`   | "value" / "growth" / "contrarian" / "mixed" | Strategic frame for synthesizer + persona prompts   |
| `thesis_price`     | float \| null                          | Long-term price target; positive when set                |
| `technical_levels` | `{support, resistance}` \| null        | Optional support/resistance pair (`support < resistance`)|
| `target_multiples` | `{pe_target, ps_target, pb_target}` \| null | Optional valuation-multiple targets                |
| `notes`            | str (≤ 1000)                           | Freeform notes                                           |
| `created_at`       | ISO-8601 str \| null                   | UTC timestamp; `+00:00` form (round-trips natively)      |
| `updated_at`       | ISO-8601 str \| null                   | UTC timestamp                                            |

Invalid configs are rejected with a multi-line `validation failed (N errors): ...` message and exit code 2 — no raw Python tracebacks. See `analysts/schemas.py` for the canonical definition (single source of truth).

## Run tests

```
uv run pytest
uv run pytest --cov=analysts --cov=watchlist --cov=cli --cov-report=term
```

Phase 1 ships with > 90% coverage across `analysts`, `watchlist`, and `cli`.

## Project structure

```
analysts/        Pydantic schemas (and Phase 3+ analyst modules)
watchlist/       Watchlist file I/O (load + atomic save)
cli/             Subcommand modules (add, remove, list, show, _errors)
tests/           Pytest suite
.planning/       Roadmap, requirements, per-phase plans + summaries
```

The roadmap (9 phases) lives at `.planning/ROADMAP.md`. Phase status, recent decisions, and open items are tracked in `.planning/STATE.md`.

## Provenance

Phase 1 has no direct adaptations from the surveyed reference repos (`virattt/ai-hedge-fund`, `TauricResearch/TradingAgents`) — neither carries a persistent watchlist abstraction at this layer. Future phases that adapt reference code will carry header-comment provenance notes naming the source file and the modifications made.
