---
phase: 3
phase_name: Analytical Agents — Deterministic Scoring
researched: 2026-05-01
domain: Pure-function deterministic scoring (fundamentals + technicals + sentiment + valuation) — no LLM, no I/O
confidence: HIGH
research_tier: normal
vault_status: not_attempted
vault_reads: []
---

# Phase 3: Analytical Agents — Deterministic Scoring — Research

**Researched:** 2026-05-01
**Domain:** Python deterministic scoring — Pydantic schemas + pandas indicator math + VADER sentiment + per-config valuation gates
**Confidence:** HIGH (every locked decision has a clear execution path; one factual issue with the **valuation analyst's required input field** must be surfaced before planning — see CORRECTIONS block)

## CORRECTIONS TO CONTEXT.md

> CONTEXT.md is overwhelmingly correct and the locked decisions stand. There is **one factual gap** the planner MUST resolve before writing the valuation plan:

| # | Topic | CONTEXT.md says | Research finds | Recommendation |
|---|-------|-----------------|----------------|----------------|
| 1 | Valuation analyst tertiary input | "yfinance analyst consensus" feeds the valuation analyst as a tertiary blend signal | `FundamentalsSnapshot` (the schema actually written by `ingestion/fundamentals.py`) does **NOT** carry `targetMeanPrice` / `recommendationMean` / `numberOfAnalystOpinions`. yfinance exposes these via `Ticker.info["targetMeanPrice"]` etc. AND via `Ticker.analyst_price_targets` (returns `{mean, median, low, high, current}`), but Plan 02-02 chose not to capture them. The valuation analyst as written has **no consensus to read**. | **Phase 2 amendment, NOT a Phase 3 task.** Add three Optional[float] fields to `FundamentalsSnapshot` (`analyst_target_mean`, `analyst_target_median`, `analyst_recommendation_mean`) plus an `Optional[int] analyst_opinion_count`; populate them in `ingestion/fundamentals.py` from `info.get("targetMeanPrice")` etc. with the same `_safe_float` coercion. Phase 3 valuation analyst then reads `snapshot.fundamentals.analyst_target_mean` cleanly. **Planner decision required:** ship the Phase 2 patch as a tiny pre-Phase-3 plan (e.g. `02-07-fundamentals-analyst-fields-PLAN.md`) OR fold it into the valuation analyst's plan as a Wave 0 prep task. Recommend the former — it's a 1-task patch (3 schema fields + 4 dict reads + 5 tests) and keeps Phase 3 plans pure pure-function code. |

**Confidence:** HIGH — verified via yfinance source `yfinance/scrapers/analysis.py` and existing examples on PyPI / Yahoo. The fields exist; we just chose not to capture them in Phase 2.

Everything else in CONTEXT.md is consistent with what the actual code requires. The schema, module layout, scoring philosophy, empty-data rule, threshold defaults, and provenance discipline are all correct and lockable.

## Summary

Phase 3 is the first "thinking" phase — deterministic Python that turns the per-ticker `Snapshot` (locked by Plan 02-06) into four `AgentSignal` objects. Pure functions, no I/O, no LLM. Surface area: ~550 LOC of production Python (1 schema file ~50 LOC + 4 analyst modules ~100-150 LOC each), ~600 LOC of tests, one new pip dep (`vaderSentiment`). All locked decisions in CONTEXT.md align cleanly with the existing codebase.

**The four risks the planner must execute around:**

1. **Indicator warm-up / min-bars guard.** ADX(14) needs 27 bars to produce a valid value, MA200 needs 200 trading days, and `fetch_prices` defaults to `period="3mo"` (~63 trading days). The technicals analyst MUST guard each indicator with an explicit min-bars check and emit `data_unavailable=True` when the snapshot's history is too short rather than silently producing garbage. Plan 02-06 does NOT pre-fill 200+ bars. Phase 3 either accepts the limitation (no MA200 score for cold-start tickers) or amends Plan 02-02 to default `period="2y"`. **Recommendation:** explicit min-bars guards + a small Phase 2 amendment to bump default period to `"1y"` (~252 bars — covers MA200 with margin and adds <100KB per ticker on disk).

2. **VADER's documented weakness on financial text.** VADER is a social-media-tuned lexicon; financial headlines tonally diverge from social media. Published comparison studies show VADER underperforms Loughran-McDonald and FinBERT on finance-specific text — but VADER is locked for v1 by CONTEXT.md. The planner doesn't relitigate the choice; the research lays out exact preprocessing recommendations and the threshold tuning that makes VADER serviceable, plus a v1.x re-evaluation flag.

3. **Pandas dependency posture.** `pandas` (3.0.2) and `numpy` (2.4.4) are already in the lockfile transitively via yfinance — they cost zero install size to use. `pandas-ta` is unmaintained; `ta-lib` requires a C library; `pandas-ta-classic` is MIT-licensed and active. **Recommendation:** hand-roll MA / momentum / ADX directly with `pandas.Series.rolling()` and `.ewm()` — virattt does the same, the ~30 LOC of indicator math is well-understood, and we avoid taking on a library we'll have to maintain through Phase 4. POSE Phase 4 will share the same 30 LOC.

4. **AgentSignal serialization for Phase 5.** `AgentSignal` will round-trip through JSON (Phase 5 writes `data/YYYY-MM-DD/{ticker}.json` containing four AgentSignals + the Snapshot). Pydantic v2 serializes `datetime` as ISO-8601 by default. Use the same `json.dumps(model.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"` pattern as `watchlist/loader.save_watchlist` (verified in Phase 1 / Phase 2) for byte-stable output. No work needed in Phase 3; the schema as locked in CONTEXT.md round-trips cleanly.

**Primary recommendation:** Build in three waves — Wave 0 amends `FundamentalsSnapshot` (analyst-consensus fields) AND optionally `fetch_prices` default period; Wave 1 ships `analysts/signals.py` and `analysts/fundamentals.py` + `analysts/valuation.py` (schema-heavy, low math); Wave 2 ships `analysts/technicals.py` + `analysts/news_sentiment.py` (math-heavy, depend on Wave 1 schema). Test fixtures construct synthetic `Snapshot` objects in-memory; zero I/O, zero mocking of upstream APIs.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **AgentSignal schema** lives at `analysts/signals.py`:
  - `verdict: Literal["strong_bullish","bullish","neutral","bearish","strong_bearish"]` (5-state)
  - `confidence: int` ∈ [0, 100]
  - `evidence: list[str]` ≤ 10 items, each ≤ 200 chars
  - `ticker`, `analyst_id` (Literal of the four ids), `computed_at: datetime`, `data_unavailable: bool`
  - `extra="forbid"`; ticker normalized via existing `analysts.schemas.normalize_ticker`
- **Module layout:** `analysts/{fundamentals,technicals,news_sentiment,valuation}.py`. Module name `news_sentiment.py` (not `news.py`) to avoid collision with `analysts/data/news.py`.
- **Public surface per analyst:** `def score(snapshot: Snapshot, config: TickerConfig) -> AgentSignal:` — pure, no I/O, no module-level mutable state.
- **Empty / partial data — UNIFORM RULE:** any time the analyst can't form an opinion, emit `AgentSignal(verdict="neutral", confidence=0, data_unavailable=True, evidence=[<reason>])`. Always 4 signals per ticker, never fewer.
- **Scoring philosophy** (locked):
  - Fundamentals: per-config when set, hard-coded fallback bands otherwise. Five inputs (P/E, P/S, ROE, debt/equity, profit margin).
  - Technicals: MA20/50/200 alignment + momentum (1m/3m/6m) + ADX(14) regime gating. **NO support/resistance** — that's POSE Phase 4.
  - News/Sentiment: VADER per-headline + recency decay (3-day half-life) + source-credibility weights (yahoo-rss/google-news=1.0, finviz=0.7, press-wires=0.5). Note: `Headline.source` is currently the Literal `["yahoo-rss","google-news","finviz"]` — press wires are NOT a separate source in the schema, see Pitfall #6.
  - Valuation: thesis_price (primary) → target_multiples (secondary) → yfinance analyst consensus (tertiary). All-three blend; sign of weighted aggregate determines verdict.
- **Threshold home:** module-level constants at top of each analyst file (e.g. `PE_BULLISH_BELOW = 15`). No central thresholds module. No TOML/YAML config.
- **New dep:** `vaderSentiment >= 3.3, < 4` added to `[project.dependencies]`. MIT, ~126KB wheel, pure-Python.
- **Provenance comments mandatory** on each adapted file naming `virattt/ai-hedge-fund/src/agents/{name}.py` source — file-by-file mapping in this research below.

### Claude's Discretion

- Threshold default values (CONTEXT.md provides starting values — tune via tests).
- VADER preprocessing depth (strip ticker tags? expand abbreviations like "EPS"/"FCF"?) — research recommends MINIMAL preprocessing (see Pitfall #5).
- Recency decay form (linear / exponential / step). Locked to **exponential half-life**; CONTEXT.md gives the half-life value (3 days).
- Whether `analysts/news_sentiment.py` lazily imports `vaderSentiment.SentimentIntensityAnalyzer` (recommended — keeps schema-only test runs fast).
- Test fixture organization (`tests/analysts/fixtures/` for synthetic snapshot builders, or in-test factory functions). Recommend: factory functions in `tests/analysts/conftest.py` (DRY across the four analyst test files).
- Whether `score()` reads `datetime.now(UTC)` once or accepts an explicit `computed_at` parameter for determinism. Recommend: optional `computed_at: datetime | None = None` parameter; default reads `datetime.now(timezone.utc)` exactly once.

### Deferred Ideas (OUT OF SCOPE)

- 5th analyst (Position-Adjustment) — Phase 4 (POSE-01..05).
- Persona prompts, Synthesizer, `TickerDecision`, `_status.json`, scheduling — Phase 5.
- Frontend rendering — Phase 6.
- Mid-day refresh wiring — Phase 8.
- 3-state vs 5-state verdict deliberation — locked to 5-state.
- VADER vs Loughran-McDonald deliberation — locked to VADER.
- Structured `evidence` types — locked to `list[str]`.
- Z-score scoring vs ticker's own historical fundamentals/technicals — needs ≥30 days of accumulated snapshots; revisit post-Phase-5.
- Per-sector / peer-relative scoring — v1.x SEC-01.
- TOML/YAML threshold config — YAGNI for single-user.
- Real-time / on-demand recompute — v1.x OND-01.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ANLY-01 | Fundamentals analyst produces an `AgentSignal` per ticker scoring P/E, P/S, ROE, debt/equity, margins with bullish/bearish/neutral verdict + confidence + evidence list | Hand-rolled per-metric threshold compare (no math libraries); `FundamentalsSnapshot.{pe,ps,roe,debt_to_equity,profit_margin}` already exist; per-config override via `TickerConfig.target_multiples.{pe_target,ps_target,pb_target}` already exists. Note: REQUIREMENTS.md ANLY-01 wording must be widened from 3-state to 5-state to match the locked schema (planner roadmap-touch step). |
| ANLY-02 | Technicals analyst produces an `AgentSignal` per ticker covering MA crossovers, momentum (1m/3m/6m), ADX-based trend strength | `pandas.Series.rolling().mean()` for MAs (already a transitive dep — pandas 3.0.2 in lockfile); momentum is `(close[-1] / close[-N] - 1)`; ADX requires Wilder smoothing (~25 LOC of pandas) — virattt's `technicals.py` is the exact reference implementation. **Min-bars guard** mandatory per pitfall #1. **REQUIREMENTS.md text widening from 3-state to 5-state same as ANLY-01.** |
| ANLY-03 | News/sentiment analyst aggregates RSS, applies recency weighting, classifies headline-level sentiment, emits `AgentSignal` | `vaderSentiment.SentimentIntensityAnalyzer().polarity_scores(title)` returns `{compound, pos, neu, neg}`; aggregate compound × source_weight × exp(-Δdays / 3 / ln 2) ≈ exp(-0.231 × Δdays). Empty-headlines case: `data_unavailable=True`. Note `Headline.source` Literal does NOT include "press-wires" today — see Pitfall #6. **REQUIREMENTS.md text widening same as above.** |
| ANLY-04 | Valuation analyst compares price vs `thesis_price` and `target_multiples`; deterministic compare to analyst consensus from yfinance; emits `AgentSignal` | Reads `TickerConfig.thesis_price` and `target_multiples` (already exist); reads `snapshot.fundamentals.analyst_target_mean` (**WHICH DOES NOT EXIST YET** — Phase 2 amendment per CORRECTION #1). All-three blend per CONTEXT.md. When NONE configured/available → `data_unavailable=True`. **REQUIREMENTS.md text widening same as above.** |

## Reference Repo (virattt/ai-hedge-fund) File Mapping

The reference repo at `~/projects/reference/ai-hedge-fund/` is **not currently present in this codespace** — verified via `find / -name ai-hedge-fund -type d` (no results). Provenance comments must reference the canonical GitHub URLs. Confirmed via web inspection of `https://github.com/virattt/ai-hedge-fund/tree/main/src/agents`:

| Our Phase 3 module | Reference source file (URL fragment) | Adopt | Diverge |
|--------------------|--------------------------------------|-------|---------|
| `analysts/signals.py` | (header pattern, no single source) | Pydantic `signal/confidence/reasoning` shape | Replace `reasoning: str` with `evidence: list[str]`; `extra="forbid"`; ticker normalization; data_unavailable bool |
| `analysts/fundamentals.py` | `src/agents/fundamentals.py` | **Hand-rolled point-system threshold compare** (no pandas needed); per-metric sub-signal evidence strings | Five metrics not thirteen (we only have P/E, P/S, ROE, debt/equity, profit margin in our `FundamentalsSnapshot` — virattt's 13 metrics include current ratio, FCF/EPS conversion, growth rates we don't capture); per-`TickerConfig.target_multiples` overrides; module-level constants instead of inline literals |
| `analysts/technicals.py` | `src/agents/technicals.py` | **Pure pandas math**: `ewm(span=N, adjust=False).mean()` for EMA, manual gain/loss for RSI, Wilder smoothing for ADX. Uses `pandas` + `numpy` only — no ta-lib, no pandas-ta. | We use SMA not EMA per CONTEXT.md (`MA20/50/200` alignment, not 8/21/55 EMA); we score MA stack + momentum + ADX only (NO RSI / Bollinger / Hurst — those belong to Phase 4 POSE); we add **explicit min-bars guards** (Pitfall #1 — virattt does NOT guard, see "Critical gaps" in their code) |
| `analysts/news_sentiment.py` | `src/agents/news_sentiment.py` | **Per-headline aggregation pattern** (np.where mapping → bullish/bearish/neutral) | virattt uses LLM sentiment via `call_llm()` — we use VADER (deterministic, free, no LLM). virattt has NO recency or source weighting — we add both. Almost a complete divergence; provenance comment is "structural pattern adapted from..." rather than line-for-line. |
| `analysts/valuation.py` | `src/agents/valuation.py` | **Multi-method weighted aggregation pattern**: when method's value ≤ 0 → exclude from weights; recompute total_weight from remaining methods | virattt uses DCF + Owner Earnings + EV/EBITDA + Residual Income (all derived from financials), NO analyst consensus — we use thesis_price + target_multiples + yfinance consensus (different methods, same aggregation pattern) |

**Mandatory provenance header format** (already established by Phase 1/2 — pattern from `ingestion/refresh.py` not used; pattern from PROJECT.md is the standard):

```python
# Pattern adapted from virattt/ai-hedge-fund/src/agents/fundamentals.py —
# https://github.com/virattt/ai-hedge-fund/blob/main/src/agents/fundamentals.py
# Modifications: pure-function score(snapshot, config) signature replaces ainvoke graph node;
# five-metric scoring (P/E, P/S, ROE, debt/equity, profit_margin) instead of 13-metric;
# per-TickerConfig.target_multiples overrides; module-level threshold constants;
# 5-state verdict (strong_bullish..strong_bearish) instead of 3-state.
```

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | ≥ 2.10 (already pinned, 2.13.3 in lockfile) | `AgentSignal` schema | Locked across project; v2 core is Rust; field/model_validator already used |
| vaderSentiment | ≥ 3.3, < 4 (3.3.2 is current) | News headline sentiment | Locked by CONTEXT.md; pure-Python, MIT, ~126KB wheel, no transitive deps, deterministic |
| pandas | already transitive (3.0.2) | Indicator math (rolling, ewm, diff) | Already in lockfile via yfinance; zero new install; `Series.rolling(N).mean()` for MA, `.ewm(span=N, adjust=False).mean()` for Wilder smoothing path |
| numpy | already transitive (2.4.4) | Math primitives (NaN handling, `np.where` aggregation) | Already in lockfile via pandas |
| pytest / pytest-cov | already pinned | Tests | Standard project pattern |

### Stdlib (no new install)
| Module | Purpose | Note |
|--------|---------|------|
| `datetime` (with `timezone.utc`) | `computed_at` timestamps; recency-decay age computation | Same UTC pattern as everywhere else in codebase |
| `math` | `math.exp` for recency decay | Pure stdlib; no library overhead |
| `typing.Literal` | 5-state Verdict, AnalystId | Already used by `TickerConfig.long_term_lens` |
| `re` | (none expected — VADER does its own tokenization, headlines need only minimal preprocessing) | |

### Alternatives Considered

| Instead of | Could Use | Tradeoff | Recommendation |
|------------|-----------|----------|----------------|
| Hand-rolled pandas indicator math | `ta-lib` (`pip install ta-lib` — wheels available since 0.6.5 / Oct 2025) | ta-lib has every TA indicator and is C-fast, but adds a 100MB+ binary dep and a maintenance posture (we'd need to lock C-version too) | **Hand-roll with pandas.** ~25 LOC for ADX, ~5 LOC each for MA / momentum. virattt does the same. POSE Phase 4 reuses the same code. Avoid ta-lib unless Phase 4 hits a perf wall. |
| Hand-rolled pandas indicator math | `pandas-ta-classic` (MIT, active, 192 indicators) | Pulls in pandas + numpy (already there) + optional numba; gives us MA/RSI/ADX/Stochastic/Bollinger out of the box. | **Skip for Phase 3.** We only need 3 indicators in Phase 3 (MA, momentum, ADX) — net LOC saved is small. Phase 4 needs 6 indicators (RSI, Bollinger, z-score, Stochastic %K, Williams %R, MACD divergence) — **revisit at Phase 4 plan-phase**. If Phase 4 chooses pandas-ta-classic, Phase 3's hand-rolled MA/momentum/ADX can be migrated in-place at zero risk. |
| `vaderSentiment` | `FinVADER` (Apache-2.0, finance-tuned via SentiBignomics + Henry's word list, requires NLTK) | Better accuracy on finance text per published benchmarks; pulls NLTK as transitive dep; needs `use_sentibignomics=True` flag (not drop-in) | **VADER is locked.** Document FinVADER as a v1.x evaluation candidate (defer Pitfall #5 says: revisit if news quality is the limiting factor downstream). |
| `vaderSentiment` | `transformers` (FinBERT) | Better accuracy still; ~500MB model download; needs `torch`; LLM-tier compute | **Hard no.** Violates keyless / lite-mode constraint (INFRA-02). FinBERT cannot ship in lite mode by definition. |
| Hand-rolled valuation blend | `pandas` weighted-mean | The blend is 1-3 numbers; pandas would be overkill | **Stdlib.** `sum(w*s for w,s in zip(weights, signals)) / sum(weights)` is 2 LOC. |
| `dataclasses` for AgentSignal | Pydantic | Pydantic gives validation, JSON round-trip, `extra="forbid"` for free | **Pydantic.** Already locked, consistent with rest of codebase. |

**No new dependencies beyond `vaderSentiment`.** Pyproject patch:

```toml
dependencies = [
    "pydantic>=2.10",
    "yfinance>=0.2.50,<0.3",
    "yahooquery>=2.3,<3",
    "requests>=2.31,<3",
    "feedparser>=6.0,<7",
    "beautifulsoup4>=4.12,<5",
    "vaderSentiment>=3.3,<4",   # NEW — news sentiment analyst (Phase 3)
]
```

## Architecture Patterns

### Recommended Module Structure (this phase only)

```
analysts/
├── schemas.py             # EXISTING — TickerConfig, Watchlist, normalize_ticker (no changes)
├── data/                  # EXISTING — Snapshot + sub-schemas (no changes EXCEPT Phase 2 amendment to fundamentals.py per CORRECTION #1)
├── signals.py             # NEW — AgentSignal + Verdict + AnalystId types (~50 LOC)
├── fundamentals.py        # NEW — score(snapshot, config) -> AgentSignal (~120 LOC)
├── technicals.py          # NEW — score(snapshot, config) -> AgentSignal (~150 LOC)
├── news_sentiment.py      # NEW — score(snapshot, config) -> AgentSignal (~150 LOC)
└── valuation.py           # NEW — score(snapshot, config) -> AgentSignal (~120 LOC)

tests/analysts/
├── __init__.py
├── conftest.py            # NEW — synthetic Snapshot / TickerConfig factory fixtures
├── test_signals.py        # AgentSignal schema (~10 tests)
├── test_fundamentals.py   # ~12 tests
├── test_technicals.py     # ~15 tests (warm-up case + happy path)
├── test_news_sentiment.py # ~12 tests
└── test_valuation.py      # ~12 tests
```

**Coverage source already includes `analysts`** (verified in `pyproject.toml` line 45: `source = ["analysts", "watchlist", "cli", "ingestion"]`) — no `pyproject.toml` changes for coverage.

### Pattern 1: Pure-function `score()` signature

**What:** Each analyst exposes exactly one public function with the same signature.

**Why:** Caller in Phase 5 (and unit tests today) treats them uniformly — `for analyst_module in [fundamentals, technicals, news_sentiment, valuation]: signal = analyst_module.score(snap, cfg)`. No state, no init, no setup.

**Example:**
```python
# analysts/fundamentals.py
"""Fundamentals analyst — deterministic per-metric scoring.

Pattern adapted from virattt/ai-hedge-fund/src/agents/fundamentals.py
(see https://github.com/virattt/ai-hedge-fund/blob/main/src/agents/fundamentals.py).
Modifications: pure-function score(snapshot, config) signature; five-metric
scoring (P/E, P/S, ROE, debt/equity, profit_margin) matching our
FundamentalsSnapshot shape; per-TickerConfig.target_multiples overrides.
"""
from datetime import datetime, timezone
from typing import Optional

from analysts.data.snapshot import Snapshot
from analysts.schemas import TickerConfig
from analysts.signals import AgentSignal

# Module-level threshold constants — tune by editing this file and re-running tests.
PE_BULLISH_BELOW = 15.0
PE_BEARISH_ABOVE = 30.0
PS_BULLISH_BELOW = 2.0
PS_BEARISH_ABOVE = 8.0
ROE_BULLISH_ABOVE = 0.15   # 15% as decimal (yfinance returns ROE as decimal)
ROE_BEARISH_BELOW = 0.05
DE_BULLISH_BELOW = 0.5
DE_BEARISH_ABOVE = 1.5
PM_BULLISH_ABOVE = 0.15
PM_BEARISH_BELOW = 0.05


def score(snapshot: Snapshot, config: TickerConfig, *, computed_at: Optional[datetime] = None) -> AgentSignal:
    now = computed_at or datetime.now(timezone.utc)
    # Empty-data guard
    if snapshot.data_unavailable or snapshot.fundamentals is None or snapshot.fundamentals.data_unavailable:
        return AgentSignal(
            ticker=snapshot.ticker,
            analyst_id="fundamentals",
            computed_at=now,
            data_unavailable=True,
            evidence=["fundamentals snapshot unavailable"],
        )
    # ... per-metric scoring ...
```

### Pattern 2: Per-metric sub-scores accumulating evidence

**What:** Each metric contributes a `+1` (bullish) / `-1` (bearish) / `0` (neutral) and one evidence string. Verdict is sign of total; confidence is `|total| / max_total * 100`.

**Why:** Maps cleanly to the `evidence: list[str]` shape (≤ 10 items, well within five metrics). Per-metric breakdowns are what users want to see in Phase 6 deep-dive (per CONTEXT.md frontend convention).

**Example:**
```python
def _score_pe(pe: Optional[float], target: Optional[float]) -> tuple[int, str | None]:
    if pe is None:
        return 0, None
    if target is not None:
        # Per-config band: ±20% around target
        if pe < target * 0.8:
            return +1, f"P/E {pe:.1f} vs target {target:.0f} — undervalued by {(1 - pe/target)*100:.0f}%"
        if pe > target * 1.2:
            return -1, f"P/E {pe:.1f} vs target {target:.0f} — overvalued by {(pe/target - 1)*100:.0f}%"
        return 0, f"P/E {pe:.1f} near target {target:.0f}"
    # Fallback bands
    if pe < PE_BULLISH_BELOW:
        return +1, f"P/E {pe:.1f} (below {PE_BULLISH_BELOW} bullish band)"
    if pe > PE_BEARISH_ABOVE:
        return -1, f"P/E {pe:.1f} (above {PE_BEARISH_ABOVE} bearish band)"
    return 0, f"P/E {pe:.1f} (neutral band)"


# Aggregate at score() level:
# total = sum(score for score, _ in sub_scores)
# verdict = _total_to_verdict(total, max_abs=5)
# evidence = [s for _, s in sub_scores if s is not None]
```

### Pattern 3: Verdict tiering from numeric total

**What:** Map a numeric score (any range) to the 5-state Literal.

**Why:** Single helper avoids drift across analysts. Each analyst can normalize to [-1, +1] then apply the same tiering thresholds.

**Example:**
```python
# Lives in analysts/signals.py (alongside AgentSignal) or each module — TBD by planner.
from typing import Literal

Verdict = Literal["strong_bullish", "bullish", "neutral", "bearish", "strong_bearish"]


def total_to_verdict(score_normalized: float) -> Verdict:
    """Map a [-1, +1] aggregate to a 5-state verdict.
    Thresholds: |x| > 0.6 → strong, |x| > 0.2 → directional, else neutral.
    """
    if score_normalized > 0.6:
        return "strong_bullish"
    if score_normalized > 0.2:
        return "bullish"
    if score_normalized < -0.6:
        return "strong_bearish"
    if score_normalized < -0.2:
        return "bearish"
    return "neutral"
```

### Pattern 4: Pandas-based MA / Momentum / ADX

**What:** Convert `snapshot.prices.history: list[OHLCBar]` to a `pandas.DataFrame` once at the top of technicals `score()`, run all indicator math against it.

**Why:** Pandas is in the lockfile already; the math is well-understood; ~5 LOC per indicator.

**Min-bars guards** (per Pitfall #1 — MUST):

| Indicator | Minimum bars to produce ANY value | Minimum bars for STABLE value | Action when below |
|-----------|-----------------------------------|-------------------------------|-------------------|
| MA20 | 20 | 20 | Skip MA20 score, evidence string omitted |
| MA50 | 50 | 50 | Skip MA50 score |
| MA200 | 200 | 200 | Skip MA200 score (will be the common case with default `period="3mo"`) |
| 1m momentum | 21 | 21 | Skip 1m momentum |
| 3m momentum | 63 | 63 | Skip 3m momentum |
| 6m momentum | 126 | 126 | Skip 6m momentum |
| ADX(14) | 27 | ~150 | Skip ADX entirely below 27; emit ADX with confidence-degraded evidence between 27 and 150 |

**If ALL of MA / momentum / ADX are skipped due to insufficient bars** → emit `data_unavailable=True` with evidence `[f"history has only {n} bars; need ≥20 for any indicator"]`.

**Example (excerpt):**
```python
import pandas as pd

def _build_df(history: list[OHLCBar]) -> pd.DataFrame:
    """list[OHLCBar] -> DataFrame indexed by date with Close column."""
    if not history:
        return pd.DataFrame()
    return pd.DataFrame(
        {"close": [b.close for b in history]},
        index=pd.to_datetime([b.date for b in history]),
    ).sort_index()


def _ma_alignment(df: pd.DataFrame) -> tuple[int, str | None]:
    """MA20 > MA50 > MA200 = bullish stack (+1); reverse = bearish (-1); mixed = 0."""
    if len(df) < 200:
        if len(df) < 50:
            return 0, None  # nothing to say
        # Mid-tier: only MA20 vs MA50
        ma20 = df["close"].rolling(20).mean().iloc[-1]
        ma50 = df["close"].rolling(50).mean().iloc[-1]
        if ma20 > ma50:
            return +1, f"MA20 ({ma20:.1f}) > MA50 ({ma50:.1f}); MA200 unavailable ({len(df)} bars)"
        if ma20 < ma50:
            return -1, f"MA20 ({ma20:.1f}) < MA50 ({ma50:.1f}); MA200 unavailable ({len(df)} bars)"
        return 0, f"MA20 ≈ MA50; MA200 unavailable ({len(df)} bars)"
    ma20, ma50, ma200 = (df["close"].rolling(n).mean().iloc[-1] for n in (20, 50, 200))
    if ma20 > ma50 > ma200:
        return +1, f"MA20 ({ma20:.1f}) > MA50 ({ma50:.1f}) > MA200 ({ma200:.1f}) — bullish stack"
    if ma20 < ma50 < ma200:
        return -1, f"MA20 ({ma20:.1f}) < MA50 ({ma50:.1f}) < MA200 ({ma200:.1f}) — bearish stack"
    return 0, f"MA stack mixed (20={ma20:.1f}, 50={ma50:.1f}, 200={ma200:.1f})"


def _adx_14(df: pd.DataFrame) -> Optional[float]:
    """Wilder-smoothed ADX(14). Returns None when fewer than 27 bars."""
    if len(df) < 27:
        return None
    # Caller has only `close` column; for ADX we need high/low/close — see note.
    # ...
```

> **NOTE for planner:** ADX uses high + low + close. Our `OHLCBar` carries `high`, `low`, `close` (verified in `analysts/data/prices.py`), so the technicals analyst's `_build_df` should include all three columns, not just close. The example above is simplified; the plan should specify HOLC.

### Pattern 5: VADER scoring + recency × source weighting

**What:** Per headline → VADER compound score → multiply by source_weight × exp(-Δdays / half_life_in_days * ln 2). Aggregate, then normalize.

**Why:** Closed-form, deterministic, ~30 LOC.

**Example:**
```python
import math
from datetime import datetime, timezone
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Module-level — VADER is thread-safe and stateless after construction.
# Lazy-construct so test runs that don't touch news don't pay the import cost.
_VADER: Optional[SentimentIntensityAnalyzer] = None

def _vader() -> SentimentIntensityAnalyzer:
    global _VADER
    if _VADER is None:
        _VADER = SentimentIntensityAnalyzer()
    return _VADER

# Source weights — Headline.source Literal = ["yahoo-rss", "google-news", "finviz"]
SOURCE_WEIGHTS = {
    "yahoo-rss": 1.0,
    "google-news": 1.0,
    "finviz": 0.7,
    # No "press-wires" key today; news ingestion would need extending in a future phase.
}

NEWS_HALFLIFE_DAYS = 3.0
DECAY_K = math.log(2.0) / NEWS_HALFLIFE_DAYS  # ≈ 0.231

# VADER compound classification thresholds (canonical).
COMPOUND_BULLISH = 0.05
COMPOUND_BEARISH = -0.05


def _score_headlines(headlines: list[Headline], now: datetime) -> tuple[float, int]:
    """Return (weighted_avg_compound, n_used). 0.0, 0 when no usable headlines."""
    analyzer = _vader()
    weighted_sum, total_weight = 0.0, 0.0
    n_used = 0
    for h in headlines:
        # Drop headlines without a published_at — can't recency-weight them.
        if h.published_at is None:
            continue
        age_days = max(0.0, (now - h.published_at).total_seconds() / 86400.0)
        # Drop headlines older than 14 days (decay weight < 4%, noise floor)
        if age_days > 14:
            continue
        recency_w = math.exp(-DECAY_K * age_days)
        source_w = SOURCE_WEIGHTS.get(h.source, 0.5)
        compound = analyzer.polarity_scores(h.title)["compound"]
        w = recency_w * source_w
        weighted_sum += compound * w
        total_weight += w
        n_used += 1
    if total_weight == 0.0:
        return 0.0, 0
    return weighted_sum / total_weight, n_used
```

### Anti-Patterns to Avoid

- **Mocking VADER in unit tests.** VADER is deterministic and adds ~5ms per analyzer construction; constructing once at module level and calling `polarity_scores()` is fast enough that real VADER calls in tests are fine. Mocking would make the recency/source-weighting tests pointless (the test would just assert the mock was called). Test against real VADER output for hand-picked bullish/bearish/neutral fixture headlines.
- **Importing yfinance at the top of `valuation.py`.** Valuation reads `snapshot.fundamentals.analyst_target_mean` (post Phase 2 amendment) — it does NOT call yfinance. Importing yfinance would couple this pure-function module to ingestion.
- **Module-level mutable state.** `_VADER` global is OK because it's a singleton lazy init — it's not mutated after construction. Avoid anything that accumulates per-call.
- **`extra="allow"` on AgentSignal.** Locked to `extra="forbid"` per CONTEXT.md. If a future analyst wants structured numbers, the right answer is a NEW field with explicit type, not metadata escape.
- **Direct `datetime.now()` reads inside helper functions.** Compute `now` once at the top of `score()` (or accept it as parameter); pass down. Otherwise tests that pin time can't reproduce.
- **Touching `snapshot.errors` in scoring logic.** It's diagnostic data for Phase 6/8 staleness banner; analysts shouldn't condition verdicts on it.
- **Building DataFrames inside loops.** `_build_df(history)` once at the top of technicals `score()`; pass to per-indicator helpers.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sentiment classification of free-text headlines | Naive bag-of-words / regex word-list | `vaderSentiment.SentimentIntensityAnalyzer.polarity_scores()` | VADER handles negation, intensifiers, capitalization, emoticons, slang. A hand-rolled lexicon would re-implement 7000+ word entries plus negation rules. |
| Moving average over a series | `sum(closes[i-N:i])/N` in a Python loop | `df["close"].rolling(N).mean()` | Pandas C-extension is ~50× faster; handles NaN propagation; Phase 4 will reuse the same DataFrame. |
| Wilder smoothing for ADX | Python loop with mutable accumulator | `df["dx"].ewm(alpha=1/14, adjust=False).mean()` (Wilder is mathematically equivalent to EMA with α=1/N, adjust=False) | Pandas EMA is C-fast; the equivalence is a published identity (Wilder's recursive formula = pandas `ewm(alpha=1/N, adjust=False).mean()`); avoids accumulator bugs. |
| ISO-8601 datetime serialization for AgentSignal | `dt.strftime("%Y-%m-%dT%H:%M:%S%z")` | Pydantic v2 default `.model_dump(mode="json")` | Pydantic emits ISO-8601 with offset. Already proven byte-stable in `Snapshot` round-trip tests (probe 2-W3-04). |
| Pydantic ValidationError for evidence cap | Manual `if len(s) > 200: raise` outside the model | `@field_validator` + `Field(max_length=10)` (locked in CONTEXT.md schema) | Schema-as-source-of-truth. ValidationError surfaces field path automatically. |
| Recency decay function | Step function ("0-1 day = 100%, 1-3 days = 70%, …") | Continuous exponential `exp(-k * age_days)` | Continuous function avoids discontinuities at boundary days that produce noisy verdicts when one headline straddles a step. Half-life form is single-parameter and intuitive. |

**Key insight:** Phase 3 deliberately avoids math libraries for the indicator analyst. Hand-rolling MA/momentum/ADX with `pandas.Series.rolling().mean()` and `.ewm()` is ~30 LOC, deterministic, well-tested by pandas itself, and reusable in Phase 4. The temptation to install `pandas-ta-classic` for "future indicator needs" is a YAGNI trap — Phase 4 plan-phase decides that, not Phase 3.

## Common Pitfalls

### Pitfall 1: ADX(14) needs 27 bars; MA200 needs 200; default snapshot has ~63
**What goes wrong:** `fetch_prices` defaults to `period="3mo"` (~63 trading days). MA200, 6m momentum (126 bars), and stable ADX (~150 bars for convergence) all need more. If the technicals analyst doesn't guard, `df.rolling(200).mean().iloc[-1]` returns `NaN`, comparisons return `False` for all branches, and verdict silently lands at "neutral" with confidence 0 — BUT the analyst still emits `data_unavailable=False`, which is a lie.
**Why it happens:** Pandas rolling silently emits NaN before the window fills; comparisons with NaN are `False` so no exception fires.
**How to avoid:**
1. Explicit `if len(df) < N` guards before each indicator call.
2. When NO indicator can run (`< 20` bars), emit `AgentSignal(data_unavailable=True, evidence=[f"history has {len(df)} bars; need ≥20"])`.
3. When SOME indicators run but others don't (e.g. 100 bars: MA20/50 yes, MA200 no), score what you can and add evidence string `f"MA200 unavailable ({len(df)} bars)"` so the user sees the limitation.
4. **Recommended Phase 2 amendment** (small, optional, not blocking Phase 3): bump `fetch_prices` default `period` from `"3mo"` to `"1y"` (~252 trading days). This unlocks MA200 + 6m momentum for tickers that actually have 1+ year of history. Cost: ~3KB extra per snapshot per ticker × 50 tickers = 150KB/day on disk. Trivial. **Planner decision:** include this as a tiny pre-Phase-3 plan or fold into the technicals analyst plan as a Wave 0 step.
**Warning signs:** If unit tests pass but produce `verdict="neutral"` for every fixture, the min-bars guards are silently swallowing all scores.

### Pitfall 2: VADER is not financial-domain-tuned
**What goes wrong:** VADER's lexicon is social-media-trained. Words like "miss" (financial: bearish, social: neutral) and "beats" (financial: bullish, social: violence) score wrong. Published comparison studies (Das et al. 2021, scitepress 2024) show VADER classification accuracy on financial headlines is typically ~55-68% vs FinBERT's ~85% and Loughran-McDonald's ~70-80%. VADER is locked for v1; this pitfall is about acknowledging the ceiling, not changing the choice.
**Why it happens:** Lexicon trained on tweets, movie reviews, NYT editorials — none of which use earnings vocabulary.
**How to avoid:**
1. Use the canonical compound thresholds (compound > 0.05 = positive, < -0.05 = negative) — these are validated for VADER's calibration.
2. **Minimal preprocessing.** VADER's algorithm relies on capitalization, punctuation, and intensifier words. Stripping these (e.g. lowercasing, ticker tag removal) DEGRADES accuracy. Strip nothing except trailing publisher tags ("Apple beats Q1 - Reuters" → keep as-is; VADER tokenizes on " - " fine). **Do NOT** expand abbreviations like "EPS" → "earnings per share" — VADER treats unknown tokens as neutral, which is correct for jargon.
3. **Drop VERY short titles** (`< 20 chars`) before scoring — too little signal; lexicon false positive rate spikes on 2-word headlines.
4. **Aggregate over many headlines.** A single bad classification matters less when 10+ headlines are recency × source-weighted. The variance washes out.
5. **Document VADER's limitations in the analyst module's docstring** so a future maintainer doesn't think we forgot to swap it for FinBERT.
6. **v1.x flag:** revisit FinVADER (`pip install finvader`, Apache-2.0, requires NLTK) once we have ≥30 days of headline corpus to A/B against. Tracked as deferred per CONTEXT.md.
**Warning signs:** Recurring news_sentiment verdicts that contradict the price action — if news_sentiment says bearish on a day prices ripped +5% on an earnings beat, VADER probably classified "Apple beats earnings" as neutral or negative.

### Pitfall 3: yfinance analyst consensus fields not in our FundamentalsSnapshot
**What goes wrong:** Valuation analyst tries to read `snapshot.fundamentals.analyst_target_mean` and that attribute does not exist on `FundamentalsSnapshot`. Either the analyst raises `AttributeError` (programmer bug) or has to call `getattr(..., None)` (defensive but ugly) or has to re-fetch from yfinance (violates the pure-function / no-I/O constraint).
**Why it happens:** Plan 02-02 captured P/E, P/S, ROE, debt/equity, profit margin, FCF, market cap — but NOT `targetMeanPrice` or `recommendationMean`. The fields are easy to add (1-line dict reads) but not retroactively addable inside Phase 3.
**How to avoid:** **Phase 2 amendment in Wave 0 of Phase 3.** Three tasks:
1. Add `analyst_target_mean: Optional[float]`, `analyst_target_median: Optional[float]`, `analyst_recommendation_mean: Optional[float]`, `analyst_opinion_count: Optional[int]` to `analysts/data/fundamentals.py:FundamentalsSnapshot`.
2. Update `ingestion/fundamentals.py:fetch_fundamentals` to read those four keys via `_safe_float(info.get("targetMeanPrice"))` etc., plus `info.get("numberOfAnalystOpinions")` (note: int, not float — needs separate coercion).
3. 4-5 tests in `tests/ingestion/test_fundamentals.py` covering happy / partial / missing-all-four paths.
This is ~30 LOC of code, ~50 LOC of tests, fully backward-compatible (Optional fields default to None — old snapshot JSON files round-trip without re-validation issues). **Crucial:** Phase 3 valuation plan can NOT proceed without this; surface it as Wave 0 of Phase 3 OR a tiny Phase 2 follow-up plan (`02-07`).
**Warning signs:** If the valuation plan starts referencing `getattr(snapshot.fundamentals, "analyst_target_mean", None)`, the amendment was skipped.

### Pitfall 4: Pydantic ValidationError on `data_unavailable=True` with non-default verdict/confidence/evidence
**What goes wrong:** Schema as locked in CONTEXT.md has `verdict: Verdict = "neutral"` and `confidence: int = ... default=0` — defaults already match the empty-data invariant. BUT if an analyst returns `AgentSignal(data_unavailable=True, verdict="bearish", confidence=80, evidence=[...])` (i.e. populated despite no data), the schema accepts it. There is no model_validator enforcing the empty-data invariant.
**Why it happens:** The locked CONTEXT.md schema has no cross-field rule like "if data_unavailable then verdict='neutral'". Easy to drift in implementation.
**How to avoid:**
1. **Plan-level convention:** every analyst's empty-data branch constructs `AgentSignal` with EXACTLY the four locked-CONTEXT.md defaults: `verdict="neutral"` (omit, use default), `confidence=0` (omit, use default), `evidence=[reason]` (one string), `data_unavailable=True`.
2. **Optional belt-and-suspenders:** add a `@model_validator(mode="after")` to `AgentSignal` that asserts `data_unavailable=True ⟹ verdict=="neutral" and confidence==0`. CONTEXT.md doesn't lock this validator one way or the other; recommend adding it to enforce the invariant at the schema layer. **Planner decision:** include or skip; recommend include (closes a class of bugs at zero cost).
3. **Test it:** `test_signals.py::test_data_unavailable_implies_neutral_zero_confidence` enforces the contract.
**Warning signs:** A test passes `AgentSignal(data_unavailable=True, verdict="bullish", confidence=99)` and the schema accepts it.

### Pitfall 5: Headlines without `published_at` timestamps
**What goes wrong:** `Headline.published_at: Optional[datetime] = None`. RSS feeds occasionally drop pubDate. If news_sentiment includes them in the recency-weighted aggregate, it has to invent an age (default to 0? to infinity? to "now"?). Each choice biases the score.
**Why it happens:** Yahoo Finance RSS reliably has pubDate; Google News usually; FinViz sometimes; press wires often missing.
**How to avoid:** **Drop headlines with `published_at=None` from the recency aggregate.** Document in the docstring. Count them in evidence (`f"{n_dropped} headlines lacked timestamps and were excluded"` if n_dropped > 0). If ALL headlines are dropped, fall back to `data_unavailable=True` with evidence `["all headlines lacked published_at timestamps"]`.
**Warning signs:** Confidence numbers that don't change as you add/remove old headlines — the aggregate is being polluted by undated entries.

### Pitfall 6: `Headline.source` Literal does not include "press-wires"
**What goes wrong:** CONTEXT.md scoring philosophy says "press wires (PRNewswire/BusinessWire) = 0.5" weight. But `Headline.source: Literal["yahoo-rss", "google-news", "finviz"]` (verified — `analysts/data/news.py` line 27). There's currently no path for a `Headline` with `source="press-wires"` to reach the analyst. Plan 02-04 (news ingestion) didn't build a press-wire ingestion module — Yahoo Finance + Google News already syndicate wire releases (per 02-RESEARCH.md), so we get press wires INDIRECTLY through the existing two sources.
**Why it happens:** Phase 2 chose "skip dedicated wire feeds; rely on Yahoo + Google syndication" (documented in 02-RESEARCH.md line 56). CONTEXT.md scoring spec is referencing a hypothetical future wire-source case.
**How to avoid:** **The press-wires weight is dead code in v1.** The analyst's `SOURCE_WEIGHTS` dict can include `"press-wires": 0.5` for forward-compat, but it'll never fire because no `Headline.source` will be `"press-wires"`. **Document this in the analyst module docstring and CONTEXT.md ideas-deferred** ("press wires currently surface via Yahoo/Google syndication; dedicated source weighting unused"). No corrective action needed unless Phase 2 ships a wire-feed module later.
**Warning signs:** None in v1 — the weight just doesn't fire. Only matters if a future phase adds `Headline.source="press-wires"`.

### Pitfall 7: Determinism — `datetime.now(UTC)` reads in helper functions
**What goes wrong:** Analyst tests want to pin `computed_at` for snapshot-comparison stability. If `score()` calls `datetime.now()` AND then internal helpers also call `datetime.now()` (e.g. for recency math), the two times differ by microseconds and snapshot tests are flaky.
**Why it happens:** Plausible refactor: news_sentiment helper computes `age_days = (datetime.now(UTC) - h.published_at).total_seconds() / 86400`.
**How to avoid:** **Read `datetime.now(timezone.utc)` exactly ONCE at the top of `score()`** — into local `now`, pass to helpers. Same pattern as `ingestion/refresh.py` `run_refresh` ("CRITICAL EXPRESSION" comment in the file) — the discipline is already established in the codebase.
**Warning signs:** Tests asserting `signal.computed_at == fixture_dt` flake; tests using `freezegun` work but tests without it fail.

### Pitfall 8: Pandas `iloc[-1]` on an indicator series with NaN tail
**What goes wrong:** `df["close"].rolling(20).mean().iloc[-1]` is `NaN` if the LAST row of the close series is NaN (yfinance occasionally emits NaN on dividend days; `_bars_from_dataframe` already drops these but `OHLCBar` itself constructs cleanly so shouldn't carry NaN). But if Phase 5 ever feeds in a Snapshot with a last-row NaN close, `iloc[-1]` is NaN and comparisons silently fail (Pitfall #1 generalized).
**Why it happens:** Trust assumption — we trust ingestion to drop NaN rows, but defense-in-depth says don't.
**How to avoid:**
1. After `_build_df(history)`, run `df = df.dropna(subset=["close"])`.
2. Recheck `len(df)` for min-bars guards AFTER the dropna.
3. (Belt-and-suspenders) `_check_finite(value, name)` helper that returns None if NaN/inf; use on every `iloc[-1]` extraction.
**Warning signs:** Same as Pitfall #1 — silent neutral verdicts.

## Code Examples

### AgentSignal schema (verbatim from CONTEXT.md, with optional model_validator from Pitfall #4)

```python
# analysts/signals.py
"""AgentSignal — locked output schema for all four Phase 3 analysts.

Pattern adapted from virattt/ai-hedge-fund Pydantic signal/confidence/reasoning
convention; modifications: 5-state Verdict (vs 3-state); evidence as list[str]
(vs reasoning: str); ticker normalization via analysts.schemas.normalize_ticker;
data_unavailable bool flag; ConfigDict(extra="forbid").
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from analysts.schemas import normalize_ticker

Verdict = Literal["strong_bullish", "bullish", "neutral", "bearish", "strong_bearish"]
AnalystId = Literal["fundamentals", "technicals", "news_sentiment", "valuation"]


class AgentSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str
    analyst_id: AnalystId
    computed_at: datetime
    verdict: Verdict = "neutral"
    confidence: int = Field(ge=0, le=100, default=0)
    evidence: list[str] = Field(default_factory=list, max_length=10)
    data_unavailable: bool = False

    @field_validator("ticker", mode="before")
    @classmethod
    def _normalize_ticker_field(cls, v: object) -> str:
        norm = normalize_ticker(v) if isinstance(v, str) else None
        if norm is None:
            raise ValueError(f"invalid ticker {v!r}")
        return norm

    @field_validator("evidence")
    @classmethod
    def _evidence_strings_capped(cls, v: list[str]) -> list[str]:
        for s in v:
            if len(s) > 200:
                raise ValueError("evidence string exceeds 200 chars")
        return v

    @model_validator(mode="after")
    def _data_unavailable_implies_neutral_zero(self) -> "AgentSignal":
        # Optional invariant — see 03-RESEARCH.md Pitfall #4.
        # Recommend including; planner may strip if user objects.
        if self.data_unavailable:
            if self.verdict != "neutral" or self.confidence != 0:
                raise ValueError(
                    f"data_unavailable=True requires verdict='neutral' and confidence=0; "
                    f"got verdict={self.verdict!r} confidence={self.confidence}"
                )
        return self
```

### Wilder ADX(14) via pandas (~25 LOC, hand-rolled)

```python
# Inside analysts/technicals.py
import pandas as pd

def _adx_14(df: pd.DataFrame) -> Optional[float]:
    """Wilder-smoothed ADX(14). df must have 'high', 'low', 'close' columns
    indexed by date. Returns None when fewer than 27 bars.

    Wilder smoothing is mathematically equivalent to pandas EMA with
    alpha=1/N and adjust=False — verified against StockCharts canonical
    walkthrough.
    Source: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/average-directional-index-adx
    """
    if len(df) < 27:
        return None
    high, low, close = df["high"], df["low"], df["close"]

    # True Range
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)

    # Directional movement
    up = high.diff()
    dn = -low.diff()
    plus_dm = pd.Series(0.0, index=df.index).where(~((up > dn) & (up > 0)), up)
    minus_dm = pd.Series(0.0, index=df.index).where(~((dn > up) & (dn > 0)), dn)

    # Wilder smoothing = EMA with alpha=1/14, adjust=False
    alpha = 1 / 14
    atr = tr.ewm(alpha=alpha, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=alpha, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=alpha, adjust=False).mean() / atr

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.ewm(alpha=alpha, adjust=False).mean()

    val = adx.iloc[-1]
    if val != val:  # NaN check
        return None
    return float(val)
```

### Recency × source weighting (news_sentiment)

```python
# Already shown in Pattern 5 above — repeated here for completeness.
# Key invariant: drop headlines with published_at=None; drop > 14 days; total_weight=0 → 0.0
```

### Valuation all-three blend (post Phase 2 amendment)

```python
# analysts/valuation.py — illustrative excerpt
def score(snapshot: Snapshot, config: TickerConfig, *, computed_at: Optional[datetime] = None) -> AgentSignal:
    now = computed_at or datetime.now(timezone.utc)
    if snapshot.data_unavailable or snapshot.prices is None or snapshot.prices.current_price is None:
        return AgentSignal(ticker=snapshot.ticker, analyst_id="valuation", computed_at=now,
                           data_unavailable=True, evidence=["no current price"])
    current = snapshot.prices.current_price
    sub_signals: list[tuple[float, float, str]] = []  # (signal in [-1,+1], weight, evidence)

    # Tier 1 — thesis_price (weight 1.0)
    if config.thesis_price is not None:
        delta = (current - config.thesis_price) / config.thesis_price
        s = max(-1.0, min(1.0, -delta * 2))  # 50% premium = -1, 50% discount = +1
        sub_signals.append((s, 1.0, f"thesis_price {config.thesis_price:.0f}, current {current:.0f} — {-delta*100:.1f}% gap"))

    # Tier 2 — target_multiples vs snapshot.fundamentals (weight 0.7)
    fmt = config.target_multiples
    fund = snapshot.fundamentals
    if fmt is not None and fund is not None and not fund.data_unavailable:
        if fmt.pe_target is not None and fund.pe is not None:
            gap = (fund.pe - fmt.pe_target) / fmt.pe_target
            s = max(-1.0, min(1.0, -gap * 2))
            sub_signals.append((s, 0.7, f"P/E {fund.pe:.1f} vs target {fmt.pe_target:.0f}"))
        # ... ps_target, pb_target similar ...

    # Tier 3 — yfinance analyst consensus (weight 0.5)  [requires Phase 2 amendment]
    if fund is not None and fund.analyst_target_mean is not None:
        delta = (current - fund.analyst_target_mean) / fund.analyst_target_mean
        s = max(-1.0, min(1.0, -delta * 2))
        sub_signals.append((s, 0.5,
            f"analyst consensus {fund.analyst_target_mean:.0f} (n={fund.analyst_opinion_count or '?'}), "
            f"current {current:.0f}"))

    if not sub_signals:
        return AgentSignal(ticker=snapshot.ticker, analyst_id="valuation", computed_at=now,
                           data_unavailable=True,
                           evidence=["no thesis_price, no target_multiples, no consensus"])

    total_w = sum(w for _, w, _ in sub_signals)
    aggregate = sum(s * w for s, w, _ in sub_signals) / total_w
    verdict = total_to_verdict(aggregate)
    confidence = int(round(min(100, abs(aggregate) * 100 * (total_w / 2.2))))  # density bonus
    evidence = [e for _, _, e in sub_signals][:10]
    return AgentSignal(ticker=snapshot.ticker, analyst_id="valuation", computed_at=now,
                       verdict=verdict, confidence=confidence, evidence=evidence)
```

## State of the Art

| Old approach | Current approach | When changed | Impact |
|--------------|------------------|--------------|--------|
| Hand-rolled lexicons for sentiment | Pre-trained transformer models (FinBERT, FinGPT) | 2020+ | Best accuracy on financial headlines (~85% vs VADER's ~65%); requires GPU/CPU compute, ~500MB model. Out of scope for v1 keyless / lite-mode. |
| `ta-lib` C library for indicators | Pandas-native (`rolling`, `ewm`) | 2018+ pandas EWM matures | Pandas approach is sufficient for our 3 (Phase 3) → 6 (Phase 4) indicators; ta-lib only wins at 100+ indicator scale. |
| `pandas-ta` (original) | `pandas-ta-classic` (community fork, MIT) | 2024 — original maintenance status flagged "inactive" | If we ever need a TA library, classic is the choice. Not needed in Phase 3. |
| 3-state verdicts (bullish/bearish/neutral) | 5-state with strong tier | This project's CONTEXT.md decision | Captures magnitude useful for Phase 5 dissent calc and Phase 6 conviction-band rendering. |
| Equal-weighted news aggregation | Recency × source-credibility weighted | Modern sentiment finance literature (sentometrics R package, Information Shock by Context Analytics) | Matches how human readers process news — fresh + reputable signals carry more weight. |

**Deprecated/outdated:**
- VADER's repo is in low-maintenance mode (last release 3.3.2 in May 2020) — the lexicon is stable; library is "done" rather than abandoned. Pin `>=3.3,<4` is safe.
- yfinance `.info["recommendationMean"]` access pattern works as of 0.2.50+ but Yahoo's quoteSummary endpoint shape has shifted before; `Ticker.analyst_price_targets` is a more stable wrapper around the same data per yfinance source code. Either is acceptable in the Phase 2 amendment; recommend `info["targetMeanPrice"]` for consistency with our existing `_safe_float(info.get(...))` pattern.
- Loughran-McDonald dictionary is 2011-2014 vintage (last update circa 2018) — still the de-facto baseline for finance sentiment but losing ground to FinBERT and GPT-based classifiers.

## Open Questions

1. **Optional `@model_validator` on AgentSignal enforcing data_unavailable invariant?**
   - What we know: CONTEXT.md schema doesn't lock this validator; Pitfall #4 shows the invariant CAN drift.
   - What's unclear: whether the planner views the validator as scope creep.
   - Recommendation: **include it.** Two-line model_validator, prevents a class of bugs, no schema-shape change (still emits the same JSON for valid inputs). Plan-Check can flag if the user objects.

2. **Phase 2 amendment: bump `fetch_prices` default `period` from `"3mo"` to `"1y"`?**
   - What we know: `period="3mo"` ≈ 63 bars, insufficient for MA200 / 6m momentum / stable ADX.
   - What's unclear: whether bumping to `"1y"` affects existing Phase 2 tests (Phase 2 tests pin specific bar counts in fixtures — they should be insensitive to default period since they pass `period=` explicitly).
   - Recommendation: **include as a Wave 0 task in Phase 3.** If Phase 2 tests fail, revert (the tests pass `period="3mo"` explicitly so they shouldn't). The cost is negligible (~150KB/day disk extra) and unlocks the technicals analyst's full feature set.

3. **Phase 2 amendment: add 4 analyst-consensus fields to `FundamentalsSnapshot` (CORRECTION #1)?**
   - What we know: The fields don't exist; valuation analyst can't read them; yfinance exposes them via `info["targetMeanPrice"]` etc.
   - What's unclear: whether the planner ships this as a separate `02-07` plan or as Wave 0 of Phase 3.
   - Recommendation: **separate `02-07` plan.** Keeps Phase 3 plans pure Phase 3 (pure-function scoring); Phase 2 amendment is mechanical schema + ingestion patch + tests. Total: ~1 hour of work, 1 commit. Phase 3 can plan-phase normally; Wave 1 of Phase 3 starts AFTER the 02-07 amendment lands.

4. **VADER `SentimentIntensityAnalyzer` lazy init or module-level eager?**
   - What we know: Constructing the analyzer costs ~5ms and reads a bundled lexicon file; calling `polarity_scores()` is ~10µs per headline.
   - What's unclear: whether eager construction (module-level) creates test-collection-time issues for tests that don't touch news.
   - Recommendation: **lazy init** via `_VADER` global (Pattern 5 above). Keeps `tests/analysts/test_signals.py` fast and lets users import `analysts.signals` without paying VADER's cost.

5. **REQUIREMENTS.md ANLY-01..04 wording — 3-state vs 5-state?**
   - What we know: REQUIREMENTS.md line 31 says "bullish/bearish/neutral verdict"; CONTEXT.md locks 5-state.
   - What's unclear: planner's roadmap-touch step needs to flip this (CONTEXT.md flagged it but the actual flip is the planner's task).
   - Recommendation: **planner widens REQUIREMENTS.md ANLY-01..04 wording during the roadmap-touch step**, e.g. "5-state verdict (strong_bullish/bullish/neutral/bearish/strong_bearish)". Same touch should flip ROADMAP.md Phase 3 goal from "Five Python analyst modules" to "Four Python analyst modules" (5th is POSE).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-cov 7.1.0 (already pinned in `[dependency-groups].dev`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]`, `addopts = "-ra --strict-markers"` |
| Quick run command | `uv run pytest tests/analysts -x` |
| Full suite command | `uv run pytest --cov` |
| Coverage gate (per project precedent) | ≥90% line / ≥85% branch on `analysts/{signals,fundamentals,technicals,news_sentiment,valuation}.py` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ANLY-01 (happy: target_multiples set) | P/E < target → bullish evidence | unit | `pytest tests/analysts/test_fundamentals.py::test_pe_per_target_bullish -x` | Wave 1 |
| ANLY-01 (fallback: no target_multiples) | P/E < 15 → bullish via fallback band | unit | `pytest tests/analysts/test_fundamentals.py::test_pe_fallback_bullish -x` | Wave 1 |
| ANLY-01 (empty data) | `snapshot.fundamentals=None` → data_unavailable=True | unit | `pytest tests/analysts/test_fundamentals.py::test_data_unavailable -x` | Wave 1 |
| ANLY-01 (per-metric isolation) | Single-metric exercise per metric (P/E, P/S, ROE, D/E, profit margin) | unit | `pytest tests/analysts/test_fundamentals.py -k metric -x` | Wave 1 |
| ANLY-01 (5-state ladder) | total ∈ {-5..-3..0..+3..+5} maps to {strong_bearish..bearish..neutral..bullish..strong_bullish} | unit | `pytest tests/analysts/test_fundamentals.py::test_verdict_tiering -x` | Wave 1 |
| ANLY-02 (MA bullish stack) | MA20 > MA50 > MA200 with 200+ bars → bullish evidence | unit | `pytest tests/analysts/test_technicals.py::test_ma_bullish_stack -x` | Wave 2 |
| ANLY-02 (MA bearish stack) | MA20 < MA50 < MA200 → bearish | unit | `pytest tests/analysts/test_technicals.py::test_ma_bearish_stack -x` | Wave 2 |
| ANLY-02 (mixed MA) | MA20 > MA50 < MA200 → mixed/neutral | unit | `pytest tests/analysts/test_technicals.py::test_ma_mixed_neutral -x` | Wave 2 |
| ANLY-02 (cold-start: <200 bars) | 100-bar history → MA200 evidence omitted, MA20/MA50 still scored, no NaN leakage | unit | `pytest tests/analysts/test_technicals.py::test_warmup_partial_indicators -x` | Wave 2 |
| ANLY-02 (very cold: <20 bars) | 10-bar history → data_unavailable=True | unit | `pytest tests/analysts/test_technicals.py::test_warmup_data_unavailable -x` | Wave 2 |
| ANLY-02 (momentum) | 1m positive, 3m positive, 6m positive → strong bullish momentum evidence | unit | `pytest tests/analysts/test_technicals.py::test_momentum_all_positive -x` | Wave 2 |
| ANLY-02 (ADX trend regime) | ADX > 25 → trend evidence; mean-reversion future (Phase 4) downweight comment in evidence | unit | `pytest tests/analysts/test_technicals.py::test_adx_trend_regime -x` | Wave 2 |
| ANLY-02 (ADX warm-up: <27 bars) | ADX returns None; no ADX evidence string | unit | `pytest tests/analysts/test_technicals.py::test_adx_warmup -x` | Wave 2 |
| ANLY-02 (regression vs known fixture) | 252-bar synthetic uptrend → strong_bullish; 252-bar synthetic downtrend → strong_bearish; 252-bar sideways → neutral | unit | `pytest tests/analysts/test_technicals.py::test_known_regimes -x` | Wave 2 |
| ANLY-03 (VADER bullish headlines) | 5 unambiguously-positive headlines → bullish | unit | `pytest tests/analysts/test_news_sentiment.py::test_bullish_headlines -x` | Wave 2 |
| ANLY-03 (VADER bearish headlines) | 5 unambiguously-negative headlines → bearish | unit | `pytest tests/analysts/test_news_sentiment.py::test_bearish_headlines -x` | Wave 2 |
| ANLY-03 (recency weighting) | one fresh-bullish + one stale-bearish (10 days) → bullish; verify older has < 0.1 weight | unit | `pytest tests/analysts/test_news_sentiment.py::test_recency_weight_dominates -x` | Wave 2 |
| ANLY-03 (source weighting) | yahoo-rss bullish vs finviz bearish at same timestamp → yahoo wins | unit | `pytest tests/analysts/test_news_sentiment.py::test_source_weight_dominates -x` | Wave 2 |
| ANLY-03 (empty headlines) | `snapshot.news=[]` → data_unavailable=True | unit | `pytest tests/analysts/test_news_sentiment.py::test_empty_headlines -x` | Wave 2 |
| ANLY-03 (no published_at) | All headlines have published_at=None → data_unavailable=True | unit | `pytest tests/analysts/test_news_sentiment.py::test_all_undated -x` | Wave 2 |
| ANLY-03 (mix dated + undated) | 3 dated + 2 undated → 3 used; 2 dropped silently or with evidence string | unit | `pytest tests/analysts/test_news_sentiment.py::test_mixed_dated -x` | Wave 2 |
| ANLY-04 (thesis_price only, undervalued) | current=80, thesis=100 → bullish evidence "thesis_price 100, current 80 — 20% gap" | unit | `pytest tests/analysts/test_valuation.py::test_thesis_only_undervalued -x` | Wave 1 |
| ANLY-04 (target_multiples only) | no thesis_price, pe_target=20, fund.pe=15 → bullish | unit | `pytest tests/analysts/test_valuation.py::test_target_multiples_only -x` | Wave 1 |
| ANLY-04 (analyst consensus only) | no thesis, no targets, fund.analyst_target_mean=120, current=100 → bullish (REQUIRES Phase 2 amendment) | unit | `pytest tests/analysts/test_valuation.py::test_consensus_only -x` | Wave 1 (gated on 02-07) |
| ANLY-04 (all three blend) | thesis bullish + targets neutral + consensus bullish → bullish, confidence higher than any single source | unit | `pytest tests/analysts/test_valuation.py::test_all_three_blend -x` | Wave 1 |
| ANLY-04 (none configured) | no thesis, no targets, no consensus → data_unavailable=True | unit | `pytest tests/analysts/test_valuation.py::test_none_configured -x` | Wave 1 |
| AgentSignal (schema validation) | extra="forbid" rejects unknown field; evidence > 200 chars rejected; ≥ 11 evidence items rejected; confidence range 0-100 enforced; ticker normalized | unit | `pytest tests/analysts/test_signals.py -x` | Wave 1 |
| AgentSignal (data_unavailable invariant) | data_unavailable=True with verdict='bullish' → ValidationError (per Pitfall #4 model_validator) | unit | `pytest tests/analysts/test_signals.py::test_data_unavailable_invariant -x` | Wave 1 |
| AgentSignal (round-trip) | model_dump_json → json.loads → model_validate_json yields equal object | unit | `pytest tests/analysts/test_signals.py::test_json_round_trip -x` | Wave 1 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/analysts -x` (target: < 5 sec for all four analyst test files)
- **Per wave merge:** `uv run pytest --cov` (full repo suite + coverage gate ≥ 90%)
- **Phase gate:** Full suite green AND coverage ≥ 90% line / ≥ 85% branch on each new analyst module before `/gmd:verify-work`

### Wave 0 Gaps

- [ ] `tests/analysts/__init__.py` — empty file marking the package
- [ ] `tests/analysts/conftest.py` — synthetic Snapshot + TickerConfig factory fixtures (~5 builders: `bullish_fundamentals_snapshot`, `bearish_fundamentals_snapshot`, `partial_data_snapshot`, `synthetic_uptrend_history(252)`, `synthetic_downtrend_history(252)`)
- [ ] **Phase 2 amendment plan `02-07-fundamentals-analyst-fields-PLAN.md`** (per CORRECTION #1 / Pitfall #3): add 4 fields to `FundamentalsSnapshot` + populate in `ingestion/fundamentals.py` + 5 tests. Blocks `analysts/valuation.py` plan.
- [ ] **OPTIONAL** Phase 2 amendment: bump `fetch_prices` default `period` from `"3mo"` to `"1y"` (per Pitfall #1 / Open Question #2). Can be deferred — analyst guards handle the cold-start case correctly without this.
- [ ] `vaderSentiment` dependency added to `pyproject.toml` `[project.dependencies]` + `uv lock --upgrade-package vaderSentiment` (or equivalent Poetry command — note the lockfile is poetry.lock per the actual repo state, not uv.lock as the agent README assumes).

**Determinism / regression test for technicals:** ship 3 fixed synthetic price histories (uptrend, downtrend, sideways) of exactly 252 bars each. The expected verdicts are locked-in by the test (e.g. `assert signal.verdict == "strong_bullish"`); coverage of the warm-up branches comes from cold-start fixture variants (10/100/252-bar versions).

## Sources

### Primary (HIGH confidence)
- yfinance source code (analyst_price_targets) — https://github.com/ranaroussi/yfinance/blob/main/yfinance/scrapers/analysis.py
- yfinance API docs — https://ranaroussi.github.io/yfinance/reference/yfinance.analysis.html (returns dict with mean/median/low/high/current keys)
- VADER repository — https://github.com/cjhutto/vaderSentiment (deterministic; bundled lexicon; Python 3 supported)
- vaderSentiment PyPI — https://pypi.org/project/vaderSentiment/ (3.3.2 current; MIT; 126KB wheel; pure-Python)
- StockCharts ADX walkthrough — https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/average-directional-index-adx (Wilder smoothing; ~28 bars to first valid value; ~150 for stable)
- virattt/ai-hedge-fund agents directory — https://github.com/virattt/ai-hedge-fund/tree/main/src/agents (file mapping)
- virattt fundamentals.py — https://github.com/virattt/ai-hedge-fund/blob/main/src/agents/fundamentals.py (point-system threshold pattern)
- virattt technicals.py — https://github.com/virattt/ai-hedge-fund/blob/main/src/agents/technicals.py (pandas-only, no ta-lib; min-bars guards missing — flagged in Pitfall #1)
- virattt valuation.py — https://github.com/virattt/ai-hedge-fund/blob/main/src/agents/valuation.py (multi-method weighted aggregation pattern; no analyst consensus path — we add that)
- virattt news_sentiment.py — https://github.com/virattt/ai-hedge-fund/blob/main/src/agents/news_sentiment.py (LLM-based; we diverge to VADER)
- Existing project source — `/workspaces/markets/analysts/data/{prices,fundamentals,news,social,filings,snapshot}.py`, `/workspaces/markets/ingestion/refresh.py`, `/workspaces/markets/pyproject.toml`, `/workspaces/markets/poetry.lock`

### Secondary (MEDIUM confidence — verified across multiple sources)
- VADER vs Loughran-McDonald comparison — Das et al. 2021 referenced via https://jds-online.org/journal/JDS/article/1441/file/pdf and https://wseas.com/journals/fe/2024/a30fe-017(2024).pdf
- FinVADER (finance-tuned VADER) — https://github.com/PetrKorab/FinVADER (Apache-2.0; SentiBignomics + Henry's word list; requires NLTK)
- pandas-ta-classic — https://pypi.org/project/pandas-ta-classic/ (MIT; active; 192 indicators; would unify Phase 4 if chosen there)
- ta-lib Python wrapper status — https://pypi.org/project/TA-Lib/ (binary wheels available since 0.6.5 / Oct 2025; bundles C library)
- Exponential decay for sentiment weighting — Stanford EWMM https://web.stanford.edu/~boyd/papers/pdf/ewmm.pdf (canonical statistical foundation); sentometrics R package (production usage in finance)
- yfinance recommendation discussion — https://github.com/ranaroussi/yfinance/discussions/1307 (recommendationTrend module)
- VADER compound thresholds (>=0.05 / -0.05) — https://blog.quantinsti.com/vader-sentiment/ + GitHub README

### Tertiary (LOW confidence — single source, marked for plan-time validation)
- 252 trading days/year is a US-market convention — folklore-level certain but not formally cited here (any quant text will confirm)
- VADER 5ms construction time — back-of-envelope from PyPI install size; not benchmarked

## Metadata

**Confidence breakdown:**
- AgentSignal schema: HIGH — locked verbatim from CONTEXT.md, all field types verified against existing codebase patterns
- Standard stack (pandas/numpy already present, vaderSentiment new): HIGH — verified poetry.lock has pandas 3.0.2 / numpy 2.4.4
- Architecture / pure-function pattern: HIGH — direct mirror of established codebase patterns (`fetch_prices`, `fetch_fundamentals`, etc.)
- Indicator math (MA, momentum, ADX): HIGH — math is standard, pandas API is stable
- VADER applicability to financial headlines: MEDIUM — VADER's known weakness is documented in published literature; CONTEXT.md locks it anyway
- yfinance analyst consensus availability: HIGH — both `info["targetMeanPrice"]` and `Ticker.analyst_price_targets` are documented and verified
- virattt source-file mapping: HIGH — verified via GitHub directory listing
- Wilder's smoothing equivalence to pandas EMA(α=1/N): HIGH — published mathematical identity, cross-verified with StockCharts walkthrough
- Min-bars guards needed: HIGH — direct consequence of Plan 02-02's `period="3mo"` default (verified in source)
- Phase 2 amendment necessity (CORRECTION #1): HIGH — verified by inspecting `analysts/data/fundamentals.py` and `ingestion/fundamentals.py`

**Research date:** 2026-05-01
**Valid until:** 2026-06-01 (30-day window — Phase 3 components are stable; primary risks are external library breakage, all of which would surface as test failures rather than research-correctness issues)
