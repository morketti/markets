---
phase: 03-analytical-agents-deterministic-scoring
plan: 04
type: tdd
wave: 2
depends_on: [03-01]
files_modified:
  - analysts/news_sentiment.py
  - tests/analysts/test_news_sentiment.py
autonomous: true
requirements: [ANLY-03]
provides:
  - "analysts.news_sentiment.score(snapshot, config, *, computed_at=None) -> AgentSignal"
  - "Per-headline VADER compound polarity scoring"
  - "Recency weighting via exponential decay (3-day half-life: w_recency = exp(-ln(2)/3 * age_days))"
  - "Source-credibility weighting (yahoo-rss=1.0, google-news=1.0, finviz=0.7; press-wires=0.5 included for forward-compat though Headline.source Literal does not yet support it — see 03-RESEARCH.md Pitfall #6)"
  - "Headline filtering: drop undated headlines (Headline.published_at=None); drop very-short titles (<20 chars); drop headlines older than 14 days (decay weight < 4%, noise floor)"
  - "5-state verdict from compound × recency × source weighted aggregate"
  - "Lazy VADER analyzer init (module-level singleton via `_vader()` accessor — keeps schema-only test runs fast)"
tags: [phase-3, analyst, news-sentiment, tdd, pure-function, anly-03, vader]

must_haves:
  truths:
    - "score(snapshot, config) returns AgentSignal with analyst_id='news_sentiment' for every input — never None, never raises"
    - "Bullish path: 5+ unambiguously-positive headlines (e.g., 'Q4 earnings beat estimates by 20%') with fresh published_at dates → verdict ∈ {bullish, strong_bullish}; weighted_avg_compound > +0.05"
    - "Bearish path: 5+ unambiguously-negative headlines (e.g., 'SEC investigates company for fraud') → verdict ∈ {bearish, strong_bearish}; weighted_avg_compound < -0.05"
    - "Recency dominance: one fresh-bullish (age=0d) + one stale-bearish (age=10d) → verdict tilts bullish; the stale headline contributes < 0.1 weight (recency_w = exp(-ln(2)/3 * 10) ≈ 0.099)"
    - "Source weighting dominance: yahoo-rss bullish + finviz bearish at same timestamp → verdict tilts bullish (1.0 vs 0.7 source weights)"
    - "Headline filtering — undated drop: headlines with published_at=None excluded from aggregate; if ALL headlines are undated → AgentSignal(data_unavailable=True, evidence=['all headlines lacked published_at timestamps'])"
    - "Headline filtering — short-title drop: titles < 20 chars excluded from aggregate (VADER noise floor)"
    - "Headline filtering — stale drop: headlines older than 14 days excluded (decay weight < 4%, noise floor)"
    - "Mixed dated/undated: 3 dated + 2 undated → 3 used; evidence string mentions 'N headlines lacked timestamps and were excluded' if N > 0"
    - "Empty-data UNIFORM RULE: snapshot.data_unavailable=True OR snapshot.news == [] → AgentSignal(data_unavailable=True, verdict='neutral', confidence=0, evidence=[<reason>])"
    - "VADER analyzer initialized lazily via module-level `_vader()` accessor — first call constructs SentimentIntensityAnalyzer, subsequent calls reuse"
    - "Determinism: `now` read once at top of score() (or accepted as `computed_at` parameter); helpers receive `now`, never call `datetime.now()` themselves (per 03-RESEARCH.md Pitfall #7)"
    - "Provenance header names virattt/ai-hedge-fund/src/agents/news_sentiment.py and explicitly states the divergence: virattt uses LLM sentiment via call_llm(), we use VADER (deterministic, free, no LLM); virattt has NO recency or source weighting, we add both"
    - "Coverage ≥90% line / ≥85% branch on analysts/news_sentiment.py"
  artifacts:
    - path: "analysts/news_sentiment.py"
      provides: "score() + lazy VADER + recency/source weighting + headline filters; ~150 LOC"
      min_lines: 130
    - path: "tests/analysts/test_news_sentiment.py"
      provides: "≥12 tests covering bullish/bearish/recency/source/empty/undated/filtering paths"
      min_lines: 120
  key_links:
    - from: "analysts/news_sentiment.py"
      to: "vaderSentiment.vaderSentiment.SentimentIntensityAnalyzer"
      via: "lazy module-level singleton (`_vader()` accessor)"
      pattern: "from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer"
    - from: "analysts/news_sentiment.py"
      to: "snapshot.news (list[Headline])"
      via: "iterate, filter (published_at, title length, age), VADER score, weight, aggregate"
      pattern: "snapshot\\.news"
    - from: "analysts/news_sentiment.py"
      to: "math.exp + math.log (stdlib)"
      via: "exponential recency decay: DECAY_K = math.log(2.0) / 3.0 ≈ 0.231; w = math.exp(-DECAY_K * age_days)"
      pattern: "math\\.exp|math\\.log"
    - from: "analysts/news_sentiment.py"
      to: "analysts.signals.AgentSignal"
      via: "constructor — only public output type"
      pattern: "from analysts.signals import AgentSignal"
---

<objective>
Wave 2 / ANLY-03: News/sentiment analyst — pure-function deterministic per-headline VADER scoring with exponential recency decay (3-day half-life) and source-credibility weighting (yahoo-rss/google-news=1.0, finviz=0.7). Aggregates per-snapshot headlines into one AgentSignal with 5-state verdict. Adapted from virattt/ai-hedge-fund/src/agents/news_sentiment.py aggregation pattern but diverges materially — virattt uses an LLM call for sentiment classification; we use VADER for determinism, freeness, and lite-mode (INFRA-02) compatibility.

Purpose: Third of the four Wave 2 analyst plans. The most divergent from virattt — provenance comment must explicitly call out "structural pattern adapted from … but full sentiment-classifier divergence: VADER lexicon-based (deterministic) vs virattt's LLM call (non-deterministic, costs)." Recency × source weighting closed-form math (~30 LOC).

**VADER-on-financial-text caveat (don't re-litigate):** VADER's published accuracy on financial headlines is ~55-68% vs FinBERT's ~85% (03-RESEARCH.md Pitfall #2). VADER is locked for v1 by 03-CONTEXT.md per the keyless / lite-mode constraint. The analyst module's docstring MUST document VADER's known weakness with a v1.x reevaluation flag (FinVADER tracked in 03-CONTEXT.md deferred ideas), so a future maintainer doesn't think we forgot to swap classifiers.

**Press-wires source weight (forward-compat dead code per 03-RESEARCH.md Pitfall #6):** Headline.source Literal is currently `["yahoo-rss", "google-news", "finviz"]` — no "press-wires" path through the schema. We include `"press-wires": 0.5` in SOURCE_WEIGHTS for forward-compat (CONTEXT.md scoring spec mentions it), but it never fires in v1. Document this in the analyst module's docstring.

Output: analysts/news_sentiment.py (~150 LOC: provenance docstring + module constants + lazy VADER + filter/score/aggregate helpers + score() function); tests/analysts/test_news_sentiment.py (~140 LOC: 12+ tests covering all decision paths).
</objective>

<execution_context>
@/home/codespace/.claude/workflows/execute-plan.md
@/home/codespace/.claude/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/03-analytical-agents-deterministic-scoring/03-CONTEXT.md
@.planning/phases/03-analytical-agents-deterministic-scoring/03-RESEARCH.md
@.planning/phases/03-analytical-agents-deterministic-scoring/03-01-SUMMARY.md

# Existing patterns
@analysts/signals.py
@analysts/data/snapshot.py
@analysts/data/news.py
@tests/analysts/conftest.py

<interfaces>
<!-- 03-01 outputs we consume: -->

```python
# AgentSignal contract — see 03-01-SUMMARY.md
# vaderSentiment >= 3.3, < 4 dependency added in 03-01 Task 1
```

<!-- Existing Headline (analysts/data/news.py): -->

```python
class Headline(BaseModel):
    ticker: str
    fetched_at: datetime
    source: Literal["yahoo-rss", "google-news", "finviz"]   # NO "press-wires" — see Pitfall #6
    data_unavailable: bool = False
    title: str = Field(min_length=1, max_length=500)
    url: str
    published_at: Optional[datetime] = None    # may be None — drop these per Pitfall #5
    summary: str = Field(default="", max_length=2000)
    dedup_key: str
```

<!-- NEW contract this plan creates: -->

```python
# analysts/news_sentiment.py
def score(
    snapshot: Snapshot,
    config: TickerConfig,
    *,
    computed_at: Optional[datetime] = None,
) -> AgentSignal:
    """Score news sentiment via VADER + recency × source weighting. Pure function."""
```
</interfaces>

<implementation_sketch>
<!-- Module structure (per 03-RESEARCH.md Pattern 5 + Pitfalls #5/#6/#7): -->

```python
import math
from datetime import datetime, timezone
from typing import Optional

from analysts.data.news import Headline
from analysts.data.snapshot import Snapshot
from analysts.schemas import TickerConfig
from analysts.signals import AgentSignal, Verdict

# Lazy VADER analyzer — constructed on first call, reused thereafter.
_VADER = None
def _vader():
    global _VADER
    if _VADER is None:
        # Lazy import here too — keeps schema-only test runs from paying VADER's import cost.
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        _VADER = SentimentIntensityAnalyzer()
    return _VADER

# Recency decay: 3-day half-life (per 03-CONTEXT.md threshold defaults)
NEWS_HALFLIFE_DAYS = 3.0
DECAY_K = math.log(2.0) / NEWS_HALFLIFE_DAYS  # ≈ 0.231

# Source credibility weights
SOURCE_WEIGHTS = {
    "yahoo-rss": 1.0,
    "google-news": 1.0,
    "finviz": 0.7,
    "press-wires": 0.5,   # Forward-compat — Headline.source Literal does not currently include this; dead code in v1 per 03-RESEARCH.md Pitfall #6.
}

# VADER compound classification thresholds (canonical)
COMPOUND_BULLISH = 0.05
COMPOUND_BEARISH = -0.05

# Filter thresholds
MIN_TITLE_LEN = 20             # VADER noise floor on very short titles (Pitfall #2 mitigation #3)
MAX_AGE_DAYS = 14.0            # decay weight < 4% past this — noise floor (Pattern 5 invariant)


def _score_one(h: Headline, now: datetime) -> tuple[Optional[float], Optional[float]]:
    """Return (compound_score_or_None, weight_or_None). None when the headline is filtered out."""
    if h.published_at is None:
        return None, None
    if len(h.title) < MIN_TITLE_LEN:
        return None, None
    age_days = max(0.0, (now - h.published_at).total_seconds() / 86400.0)
    if age_days > MAX_AGE_DAYS:
        return None, None
    recency_w = math.exp(-DECAY_K * age_days)
    source_w = SOURCE_WEIGHTS.get(h.source, 0.5)   # default 0.5 for unknown sources (defensive)
    compound = _vader().polarity_scores(h.title)["compound"]
    return compound, recency_w * source_w


def _aggregate(headlines: list[Headline], now: datetime) -> tuple[float, int, int, int]:
    """Return (weighted_avg_compound, n_used, n_undated, n_short)."""
    weighted_sum, total_weight = 0.0, 0.0
    n_used = n_undated = n_short = 0
    for h in headlines:
        if h.published_at is None:
            n_undated += 1
            continue
        if len(h.title) < MIN_TITLE_LEN:
            n_short += 1
            continue
        compound, w = _score_one(h, now)
        if compound is None or w is None:
            continue
        weighted_sum += compound * w
        total_weight += w
        n_used += 1
    if total_weight == 0.0:
        return 0.0, 0, n_undated, n_short
    return weighted_sum / total_weight, n_used, n_undated, n_short


def _total_to_verdict(weighted_compound: float) -> Verdict:
    # Same 5-state tier as fundamentals/technicals — but our raw input is in [-1, +1] (VADER compound)
    # and naturally tighter than fundamentals (most headlines cluster |compound| < 0.5).
    if weighted_compound > 0.4: return "strong_bullish"
    if weighted_compound > COMPOUND_BULLISH: return "bullish"
    if weighted_compound < -0.4: return "strong_bearish"
    if weighted_compound < COMPOUND_BEARISH: return "bearish"
    return "neutral"


def score(snapshot, config, *, computed_at=None):
    now = computed_at or datetime.now(timezone.utc)
    # UNIFORM RULE empty-data guard
    if snapshot.data_unavailable or not snapshot.news:
        return AgentSignal(
            ticker=snapshot.ticker, analyst_id="news_sentiment", computed_at=now,
            data_unavailable=True, evidence=["no news headlines available"],
        )
    weighted_compound, n_used, n_undated, n_short = _aggregate(snapshot.news, now)
    if n_used == 0:
        # Could be all-undated, all-short, or all-stale — distinguish in evidence
        reasons = []
        if n_undated > 0: reasons.append(f"{n_undated} headlines lacked published_at")
        if n_short > 0:   reasons.append(f"{n_short} headlines too short (<{MIN_TITLE_LEN} chars)")
        n_stale = len(snapshot.news) - n_undated - n_short
        if n_stale > 0:   reasons.append(f"{n_stale} headlines older than {MAX_AGE_DAYS:.0f} days")
        return AgentSignal(
            ticker=snapshot.ticker, analyst_id="news_sentiment", computed_at=now,
            data_unavailable=True,
            evidence=[f"all {len(snapshot.news)} headlines filtered: " + "; ".join(reasons)],
        )
    verdict = _total_to_verdict(weighted_compound)
    confidence = min(100, int(round(min(1.0, abs(weighted_compound) * 2.5) * 100)))
    # Evidence: top-line summary + per-source breakdown if room
    evidence = [
        f"{n_used} headlines (7-day weighted), avg VADER compound {weighted_compound:+.2f} — {verdict.replace('_', ' ')}"
    ]
    if n_undated > 0:
        evidence.append(f"{n_undated} headlines lacked timestamps and were excluded")
    if n_short > 0:
        evidence.append(f"{n_short} short-title headlines excluded (VADER noise floor)")
    return AgentSignal(
        ticker=snapshot.ticker, analyst_id="news_sentiment", computed_at=now,
        verdict=verdict, confidence=confidence, evidence=evidence[:10],
    )
```

<!-- Confidence formula note: weighted_compound is in [-1, +1] but VADER compounds for typical financial headlines cluster in [-0.5, +0.5]. Multiplying by 2.5 stretches the range so a |compound| of 0.4 maps to confidence 100. Tunable; tests pin the exact formula. -->
</implementation_sketch>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Test scaffolding — bullish/bearish/recency/source/filter cases (RED)</name>
  <files>tests/analysts/test_news_sentiment.py</files>
  <behavior>
    Tests written first. VADER is deterministic, so we use real VADER calls (no mocking) per 03-RESEARCH.md Anti-Pattern guidance — mocking VADER would render the recency/source-weighting tests pointless (the test would just assert the mock was called).

    Tests (≥14):

    HAPPY PATHS:
    - test_bullish_headlines_strong: 5 headlines with unambiguously-positive financial titles ("Apple beats Q1 earnings expectations by 20%", "Apple announces record buyback program", "Apple raises full-year guidance", "Apple wins major government contract", "Apple stock upgraded by Goldman to buy"); all published_at = frozen_now (age=0); all source="yahoo-rss". Score → verdict ∈ {bullish, strong_bullish}; confidence > 30; evidence[0] contains "5 headlines" and "VADER compound +".
    - test_bearish_headlines_strong: 5 unambiguously-negative ("SEC investigates Apple for fraud", "Apple Q1 earnings miss by wide margin", "Apple recalls 10M devices over safety", "Apple CFO resigns amid probe", "Apple stock downgraded to sell"). Score → verdict ∈ {bearish, strong_bearish}; evidence[0] contains "VADER compound -".
    - test_neutral_mixed: 3 bullish + 3 bearish at same timestamps + same source. Score → verdict='neutral'; weighted_avg near 0.

    RECENCY WEIGHTING:
    - test_recency_fresh_bullish_dominates_stale_bearish: 1 bullish at age=0d (recency_w=1.0) + 1 bearish at age=10d (recency_w ≈ 0.099). Verdict → bullish; weighted_avg positive. Verify the math by computing expected weighted_avg = (compound_bull * 1.0 + compound_bear * 0.099) / (1.0 + 0.099) and assert score within 0.01 of that.
    - test_recency_decay_curve: 3 identical-bullish headlines at ages 0d / 3d / 6d. Each weight = 1.0, 0.5, 0.25 (3-day half-life). Verify by direct computation.

    SOURCE WEIGHTING:
    - test_source_weight_yahoo_dominates_finviz: 1 bullish from yahoo-rss + 1 bearish from finviz, same timestamp (age=0d). yahoo recency_w * source_w = 1.0 * 1.0 = 1.0; finviz = 1.0 * 0.7 = 0.7. Net positive. Verdict → bullish.
    - test_source_weight_finviz_alone_bullish: 1 bullish headline from finviz, age=0d. weight = 0.7. weighted_avg = compound (single-headline). Verify confidence is computed from compound, not from weight.

    FILTERING:
    - test_filter_undated_dropped: 3 headlines: 2 with published_at=None, 1 dated+bullish at age=0d. Score: aggregate uses just the 1; verdict = bullish; evidence mentions "2 headlines lacked timestamps".
    - test_filter_short_title_dropped: 3 headlines: 2 with title="Apple up" (9 chars, < MIN_TITLE_LEN), 1 with full title at age=0d. Aggregate uses 1; evidence mentions "2 short-title headlines excluded".
    - test_filter_stale_dropped: 3 headlines all bullish: 1 at age=20d (stale), 1 at age=2d, 1 at age=0d. Aggregate uses 2 (the two recent ones); the 20d one is silently dropped (no evidence string for stale ones in v1 — research suggests overcomplicated UX).
    - test_all_undated_data_unavailable: all 5 headlines have published_at=None. Score → AgentSignal(data_unavailable=True, evidence contains "5 headlines lacked published_at" or similar).
    - test_all_short_data_unavailable: all 5 headlines title="X" (1 char). Score → AgentSignal(data_unavailable=True).

    EMPTY-DATA UNIFORM RULE:
    - test_empty_news_data_unavailable: make_snapshot(news=[]). Score → AgentSignal(data_unavailable=True, evidence=["no news headlines available"]).
    - test_snapshot_data_unavailable_true: make_snapshot(data_unavailable=True). Score → data_unavailable=True signal.

    DETERMINISM + PROVENANCE:
    - test_deterministic: call score() twice with same snapshot + frozen_now. Compare model_dump_json — byte-identical.
    - test_computed_at_passes_through: pass explicit computed_at=frozen_now; signal.computed_at == frozen_now.
    - test_no_module_level_clock_in_helpers: read analysts/news_sentiment.py source; verify the only `datetime.now(` call is inside `score()` (not in `_aggregate`, `_score_one`, `_vader`). grep is sufficient.
    - test_lazy_vader_init: call `from analysts.news_sentiment import _VADER` AT IMPORT TIME — must be None. Then call score() with at least one valid headline; verify _VADER is now a SentimentIntensityAnalyzer instance.
    - test_provenance_header_present: read source; assert "virattt/ai-hedge-fund/src/agents/news_sentiment.py" present AND "VADER" present (the divergence-from-virattt signal).
    - test_press_wires_source_in_dict_dead_code_doc: read source; assert SOURCE_WEIGHTS contains "press-wires" key (forward-compat per Pitfall #6) AND a comment mentioning "dead code" or "forward-compat" or "Pitfall #6".

    Use `make_snapshot`, `make_ticker_config`, `frozen_now` fixtures. Build `Headline` directly via `from analysts.data.news import Headline`.
  </behavior>
  <action>
    RED:
    1. Write `tests/analysts/test_news_sentiment.py` with the ≥18 tests above. Imports: `import math`; `import pytest`; `from datetime import datetime, timedelta, timezone`; `from analysts.data.news import Headline`; `from analysts.signals import AgentSignal`; `from analysts.news_sentiment import score`. Build a helper `_h(title, *, source="yahoo-rss", age_days=0.0, ticker="AAPL", now=frozen_now)` that constructs a Headline at frozen_now - timedelta(days=age_days) — keeps tests readable.
    2. Run `poetry run pytest tests/analysts/test_news_sentiment.py -x -q` → ImportError on `analysts.news_sentiment`.
    3. Commit: `test(03-04): add failing tests for news/sentiment analyst (VADER + recency + source weighting + filters)`
  </action>
  <verify>
    <automated>poetry run pytest tests/analysts/test_news_sentiment.py -x -q 2>&1 | grep -E "(error|ImportError|ModuleNotFoundError)" | head -3</automated>
  </verify>
  <done>tests/analysts/test_news_sentiment.py committed with ≥18 RED tests; pytest fails as expected (ImportError); _h() helper in place; all decision paths covered.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: analysts/news_sentiment.py — score() implementation (GREEN)</name>
  <files>analysts/news_sentiment.py</files>
  <behavior>
    Implement per implementation_sketch in <context>. Lazy VADER init, single `now` read in `score()` (Pitfall #7), explicit headline filters, recency × source weighted aggregation, 5-state verdict mapping.

    Module structure:
    1. Provenance docstring (15-20 lines) per PROJECT.md INFRA-07. Name virattt/ai-hedge-fund/src/agents/news_sentiment.py. Explicit divergence note: "virattt uses LLM sentiment via call_llm() — non-deterministic, paid; we use VADER (vaderSentiment ≥3.3) for determinism, freeness, lite-mode (INFRA-02) compatibility. virattt has NO recency or source weighting — we add both per 03-CONTEXT.md scoring philosophy. Almost a complete divergence; provenance comment is 'structural pattern adapted from … with full sentiment-classifier substitution.'" Also: "VADER's accuracy on financial headlines is ~55-68% per published comparison studies; FinVADER / Loughran-McDonald deferred to v1.x per 03-CONTEXT.md deferred ideas. Press-wires source weight (0.5) is forward-compat dead code — Headline.source Literal does not currently include 'press-wires' (see 03-RESEARCH.md Pitfall #6)."
    2. Imports: `from __future__ import annotations`; `import math`; `from datetime import datetime, timezone`; `from typing import Optional`; `from analysts.data.news import Headline`; `from analysts.data.snapshot import Snapshot`; `from analysts.schemas import TickerConfig`; `from analysts.signals import AgentSignal, Verdict`. NOTE: `vaderSentiment` is imported INSIDE `_vader()` — lazy.
    3. Module-level constants per the sketch: `NEWS_HALFLIFE_DAYS`, `DECAY_K`, `SOURCE_WEIGHTS`, `COMPOUND_BULLISH`, `COMPOUND_BEARISH`, `MIN_TITLE_LEN`, `MAX_AGE_DAYS`. Comment SOURCE_WEIGHTS["press-wires"] line as "forward-compat — see Pitfall #6".
    4. Module-level `_VADER = None` + `_vader()` accessor (lazy import + lazy construction).
    5. Private helpers: `_score_one(h, now)`, `_aggregate(headlines, now)`, `_total_to_verdict(weighted_compound)`.
    6. Public `score(snapshot, config, *, computed_at=None) -> AgentSignal` with the empty-data UNIFORM RULE guard, then aggregation, then evidence assembly, then AgentSignal construction.

    Critical determinism point (Pitfall #7): `now` is computed ONCE at the top of `score()`. `_score_one` and `_aggregate` accept `now` as a parameter. NO helper function calls `datetime.now()` directly. Tests can pin via `computed_at=frozen_now`.

    Edge case the implementation MUST handle:
    - n_used == 0 BUT len(snapshot.news) > 0 (all filtered): return data_unavailable=True with evidence enumerating the filter reasons. Tests `test_all_undated_data_unavailable` and `test_all_short_data_unavailable` exercise this.
    - When n_used > 0, evidence list contains the top-line summary AND optional notes about filtered headlines. Cap at 10 items.

    Confidence formula: `min(100, int(round(min(1.0, abs(weighted_compound) * 2.5) * 100)))`. Stretches the typical [-0.5, +0.5] VADER compound range to fill [0, 100]. Document in a comment ("VADER compounds cluster in [-0.5, +0.5] for financial headlines; the 2.5x multiplier maps |compound|=0.4 to confidence=100").
  </behavior>
  <action>
    GREEN:
    1. Implement `analysts/news_sentiment.py` per the structure above.
    2. Run `poetry run pytest tests/analysts/test_news_sentiment.py -v` → all ≥18 tests green.
    3. Coverage: `poetry run pytest --cov=analysts.news_sentiment --cov-branch tests/analysts/test_news_sentiment.py` → ≥90% line / ≥85% branch.
    4. Full repo regression: `poetry run pytest -x -q` → all green (177+ pre-existing + 03-01 + 03-02 + 03-03 + 18+ here).
    5. Verify provenance + lazy-VADER pattern:
       - `grep -q "virattt/ai-hedge-fund/src/agents/news_sentiment.py" analysts/news_sentiment.py`
       - `grep -q "VADER" analysts/news_sentiment.py` (divergence flag)
       - `grep -q "_VADER = None" analysts/news_sentiment.py` (lazy singleton)
       - `grep -q "press-wires" analysts/news_sentiment.py` (forward-compat dead-code comment present)
    6. Commit: `feat(03-04): news/sentiment analyst — VADER + 3-day-half-life recency + source weighting`
  </action>
  <verify>
    <automated>poetry run pytest tests/analysts/test_news_sentiment.py -v && poetry run pytest --cov=analysts.news_sentiment --cov-branch tests/analysts/test_news_sentiment.py && poetry run pytest -x -q && grep -q "virattt/ai-hedge-fund/src/agents/news_sentiment.py" analysts/news_sentiment.py && grep -q "_VADER = None" analysts/news_sentiment.py</automated>
  </verify>
  <done>analysts/news_sentiment.py shipped with score() + lazy VADER + filters + recency/source aggregation; ≥18 tests green; coverage ≥90/85; full repo regression green; provenance + divergence note present; lazy-init pattern verified.</done>
</task>

</tasks>

<verification>
- 2 tasks, 2 commits (RED then GREEN). TDD discipline preserved.
- Coverage gate: ≥90% line / ≥85% branch on `analysts/news_sentiment.py`.
- Full repo regression: 177+ pre-existing + 16+ schema (03-01) + 18 fundamentals (03-02) + 18+ technicals (03-03) + 18+ news_sentiment (03-04) → all green.
- ANLY-03 requirement satisfied: per-headline VADER + recency weighting (3-day half-life) + source-credibility weighting + 5-state ladder verdict + filtering rules (undated drop, short-title drop, stale drop).
- Provenance header in analysts/news_sentiment.py names virattt source file AND explicitly documents the LLM-vs-VADER divergence per INFRA-07.
- Lazy VADER init pattern (module-level `_VADER = None` + `_vader()` accessor) keeps schema-only test runs fast — Plan 03-01's test_signals.py and the conftest fixture-load do NOT pay VADER's import cost.
- Press-wires forward-compat dead-code comment present per Pitfall #6.
- `now` read once at top of score(); helpers receive `now` as parameter (Pitfall #7).

## Cross-Scope Risks

_vault_status=budget_exhausted; re-run /gmd:plan-phase --replan after vault-maintain_
</verification>

<success_criteria>
1. `analysts/news_sentiment.py:score(snapshot, config, *, computed_at=None) -> AgentSignal` is a pure function ~150 LOC.
2. VADER imported lazily via `_vader()` accessor; `_VADER` is None at module-import time.
3. Recency decay: exponential, 3-day half-life (`DECAY_K = math.log(2.0) / 3.0 ≈ 0.231`).
4. Source weights: yahoo-rss=1.0, google-news=1.0, finviz=0.7, press-wires=0.5 (forward-compat dead code per Pitfall #6).
5. Filters: undated headlines dropped; titles < 20 chars dropped; headlines older than 14 days dropped.
6. Empty-data uniform rule honored: snapshot.data_unavailable=True OR snapshot.news==[] → data_unavailable=True signal.
7. All-filtered case (n_used == 0 BUT len(news) > 0) → data_unavailable=True with evidence enumerating filter reasons.
8. Provenance header names virattt source file AND documents LLM-vs-VADER divergence per INFRA-07.
9. ≥18 tests in tests/analysts/test_news_sentiment.py, all green; coverage ≥90% line / ≥85% branch.
10. ANLY-03 requirement closed; third of four Wave 2 analyst modules shipped.
</success_criteria>

<output>
After completion, create `.planning/phases/03-analytical-agents-deterministic-scoring/03-04-SUMMARY.md` summarizing the 2 commits, the score() signature, and the VADER divergence-from-virattt design choice. Reference 03-01 (AgentSignal contract; vaderSentiment dep; conftest) and forward-flag the test_invariants.py xfail status (still RED — needs 03-05 to flip green at end of Wave 2).
</output>
