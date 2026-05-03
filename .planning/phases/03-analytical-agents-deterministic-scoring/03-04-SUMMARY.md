---
phase: 03-analytical-agents-deterministic-scoring
plan: 04
subsystem: analysts
tags: [phase-3, analyst, news-sentiment, tdd, pure-function, anly-03, wave-2, vader]

# Dependency graph
requires:
  - phase: 03-analytical-agents-deterministic-scoring
    plan: 01
    provides: analysts.signals.AgentSignal (5-state Verdict ladder + 0-100 confidence + evidence list + data_unavailable invariant), analysts.signals.Verdict + AnalystId Literals, tests/analysts/conftest.py (frozen_now / make_snapshot / make_ticker_config fixtures), vaderSentiment >= 3.3 dependency added at 03-01 Task 1
  - phase: 02-ingestion-keyless-data-plane
    plan: 04
    provides: analysts.data.news.Headline (ticker / source Literal['yahoo-rss','google-news','finviz'] / title / url / published_at: Optional[datetime] / dedup_key)
  - phase: 02-ingestion-keyless-data-plane
    plan: 06
    provides: analysts.data.snapshot.Snapshot (per-ticker aggregate carrying optional news sub-field plus snapshot-level data_unavailable bool)
provides:
  - "analysts.news_sentiment.score(snapshot, config, *, computed_at=None) -> AgentSignal — pure function, no I/O, lazy VADER singleton, never raises for missing data"
  - "Per-headline VADER compound polarity scoring via lazy module-level singleton (_VADER = None + _vader() accessor)"
  - "Exponential recency decay (3-day half-life: DECAY_K = math.log(2.0) / 3.0 ≈ 0.231)"
  - "Source-credibility weighting: yahoo-rss=1.0, google-news=1.0, finviz=0.7, press-wires=0.5 (forward-compat dead code per 03-RESEARCH.md Pitfall #6)"
  - "Headline filters: undated drop / short-title drop (<20 chars) / stale drop (>14 days)"
  - "All-filtered case: n_used==0 BUT len(news) > 0 → data_unavailable signal with evidence enumerating filter reasons"
  - "Empty-data UNIFORM RULE: snapshot.data_unavailable=True OR snapshot.news=[] → data_unavailable signal"
  - "Verdict tiering with VADER-tuned boundaries: 0.4 / 0.05 / -0.05 / -0.4 (tighter than fundamentals/technicals 0.6/0.2 because VADER compounds for financial headlines cluster in [-0.5, +0.5])"
  - "Confidence stretching: min(100, int(round(min(1.0, abs(weighted_compound) * 2.5) * 100))) — 2.5x multiplier maps |compound|=0.4 to confidence=100"
  - "Determinism: `now` read ONCE at top of score(); helpers receive `now` as parameter (Pitfall #7)"
  - "Provenance header (INFRA-07) names virattt/ai-hedge-fund/src/agents/news_sentiment.py and explicitly documents LLM-vs-VADER divergence + recency-and-source-weighting additions"
affects: [phase-3-plan-05-valuation-analyst, phase-5-claude-routine (reads AgentSignal from disk via JSON), phase-6-frontend-deep-dive (renders evidence list), v1.x-FinVADER-or-Loughran-McDonald-swap (deferred per 03-CONTEXT.md)]

# Tech tracking
tech-stack:
  added: []  # vaderSentiment was added at 03-01 — this plan finally exercises it
  patterns:
    - "Lazy module-level singleton pattern (`_VADER = None` + `_vader()` accessor with lazy import inside the accessor): keeps schema-only test runs from paying VADER's import cost. Generalizes to any future analyst with an expensive-to-construct dependency (e.g., a tokenizer or LLM client)."
    - "`now` read ONCE at top of score(); helpers receive `now` as parameter. Locks Pitfall #7 — every Wave 2 analyst (and every future analyst) follows this discipline. Verified by AST walk (test_no_module_level_clock_in_helpers): no helper function — anything that isn't `score` — calls datetime.now() directly."
    - "Filter-then-aggregate pattern: explicit per-headline filters (undated / short / stale) with counts captured, then weighted aggregate. The all-filtered case (n_used==0) returns data_unavailable with evidence enumerating which filter reasons fired. Generalizes to any analyst that scores a list of items with per-item filter rules."
    - "VADER-tuned verdict boundaries (0.4 / 0.05): the boundary thresholds match the natural distribution of the input metric. Unlike fundamentals/technicals (which aggregate ±1 sub-scores into a normalized [-1, +1] where 0.6/0.2 are reasonable strong/weak boundaries), VADER compounds for financial headlines cluster in [-0.5, +0.5] — picking 0.6 as the strong boundary would mean strong tier never fires. Pattern: pick verdict boundaries from the empirical distribution of the input, not by analogy to other analysts."
    - "Forward-compat dead-code documentation: SOURCE_WEIGHTS includes 'press-wires': 0.5 even though Headline.source Literal does not currently support 'press-wires'. The dict entry never fires in v1; it activates when ingestion/news.py adds press-wires support. Comment + docstring + dedicated test (test_press_wires_source_in_dict_dead_code_doc) lock the forward-compat intent and prevent future cleanup PRs from removing it 'because it's unused'."

key-files:
  created:
    - "analysts/news_sentiment.py (~225 lines — provenance docstring + lazy VADER singleton + 7 module-level constants + _score_one + _aggregate + _total_to_verdict + score())"
    - "tests/analysts/test_news_sentiment.py (~525 lines, 22 tests covering lazy-init / 3 happy paths / 2 recency / 2 source / 3 filtering / 2 all-filtered / 2 empty-data / 8 determinism+provenance+meta)"
  modified: []  # No existing files touched aside from docs at closeout

key-decisions:
  - "VADER, not LLM-call_llm — full sentiment-classifier divergence from virattt/ai-hedge-fund. virattt's reference uses async call_llm() (paid, non-deterministic, latency-bound, incompatible with INFRA-02 lite-mode). VADER is deterministic, free, runs synchronously, and survives quota exhaustion. Documented accuracy gap: VADER ~55-68% on financial headlines vs FinBERT ~85% per published comparison studies; FinVADER and Loughran-McDonald deferred to v1.x per 03-CONTEXT.md deferred ideas. Provenance docstring documents this explicitly so future maintainers don't think we forgot to swap classifiers."
  - "Lazy VADER singleton (_VADER = None + _vader() accessor with lazy import inside the accessor). Module import does not pay VADER's cost; first score() call constructs the analyzer; subsequent calls reuse. Verified by test_lazy_vader_init_is_none_at_import_time (greppable assertion against the module-level pattern + the function definition). The schema-only test_signals.py + conftest.py do not import vaderSentiment at all."
  - "3-day half-life recency decay (DECAY_K = math.log(2.0) / 3.0 ≈ 0.231). A 3-day-old headline contributes 50% weight; 6-day = 25%; 10-day ≈ 9.9%; 14-day < 4%. Past 14 days the headline is dropped silently (no evidence string for stale headlines — research suggests overcomplicated UX). The choice of 3-day half-life is from 03-CONTEXT.md threshold defaults; tunable by editing NEWS_HALFLIFE_DAYS."
  - "Source weights: yahoo-rss=1.0, google-news=1.0, finviz=0.7. yahoo+google are publisher-curated first-tier; finviz scrapes are noisier and sometimes pick up press-release flak. Unknown sources (defensive default in SOURCE_WEIGHTS.get) return 0.5 — a future ingestion plan adding a new source path won't crash the analyst, just downweights it pending an explicit weight assignment."
  - "press-wires=0.5 in SOURCE_WEIGHTS is forward-compat dead code per Pitfall #6. Headline.source Literal does not currently include 'press-wires' — Pydantic v2 will reject any Headline with that source at the schema layer, so the SOURCE_WEIGHTS entry never fires in v1. Locked into place by test_press_wires_source_in_dict_dead_code_doc (asserts the key exists AND a comment mentioning forward-compat / dead code / Pitfall #6). When ingestion/news.py adds press-wires support in a future plan, this entry activates with no analyst-side change."
  - "Verdict boundaries 0.4 / 0.05 / -0.05 / -0.4 — tighter than fundamentals/technicals 0.6/0.2. Reason: VADER compounds for typical financial headlines cluster in [-0.5, +0.5]; picking 0.6 as the strong boundary would mean strong_bullish never fires. Pattern: pick verdict boundaries from the empirical distribution of the input metric, not by analogy to other analysts. The COMPOUND_BULLISH=0.05 boundary is the canonical VADER-paper threshold for 'positive sentiment'."
  - "Confidence formula: min(100, int(round(min(1.0, abs(weighted_compound) * 2.5) * 100))). The 2.5x multiplier stretches |compound|=0.4 → confidence=100. Documented in a comment at the call site so future readers don't tweak it without understanding the VADER-distribution rationale. Same defensive min(100, ...) cap as fundamentals/technicals — survives any future refactor that loosens the multiplier."
  - "Filters in order: undated → short-title → stale. published_at=None checked first because it's the cheapest check and the most actionable signal (can't compute age without a timestamp). Short-title check next (cheap len() comparison). Stale check last (requires the now-published_at subtraction). Per-headline filtering inside _aggregate keeps the helper functions composable — _score_one is pure, _aggregate handles the bookkeeping (n_undated / n_short / n_stale counters)."
  - "n_stale is silent in evidence (NOT enumerated). Stale headlines are dropped by the recency-decay design; mentioning them in evidence would make the user re-think a working invariant. n_undated and n_short are surfaced because they indicate ingestion-side bugs the user might want to know about. The all-filtered case enumerates ALL three reasons (undated / short / stale) in the evidence string for full diagnostic transparency."
  - "Pure-function discipline (Pitfall #7): `now` is read ONCE at the top of score(). _score_one and _aggregate accept `now` as a parameter. Locked by test_no_module_level_clock_in_helpers — AST walk confirms no helper function calls datetime.now() directly. Reason: helper functions called multiple times during one score() invocation must agree on a single `now` for determinism; calling datetime.now() per-helper would produce non-determinism within the same call (different ages for different headlines)."
  - "ROADMAP.md plan-progress edit done MANUALLY per the precedent set in Plans 02-07 / 03-01 / 03-02 / 03-03 closeouts. The `gmd-tools roadmap update-plan-progress 3` command mangles the descriptive Phase Summary row format; the row is bumped 3/5 → 4/5 manually here."

patterns-established:
  - "Lazy module-level singleton with lazy import inside the accessor: keeps schema-only test runs from paying expensive-dependency import costs. Pattern reusable for any future analyst that needs an expensive resource (tokenizer, LLM client, FinBERT model). The `_RESOURCE = None` + `_resource()` accessor + `global _RESOURCE` pattern is short, greppable, and locks the lazy-init contract."
  - "Pitfall #7 / single-now discipline: `now` read ONCE in score(); helpers receive `now` as parameter. AST-walk test (test_no_module_level_clock_in_helpers) verifies no helper calls datetime.now() — same kind of test that the v1.x maintainer can copy verbatim into a new analyst module."
  - "Forward-compat dead code with explicit doc + dedicated test: SOURCE_WEIGHTS['press-wires'] never fires in v1 but the entry survives because (a) the docstring explains why, (b) a dedicated test asserts the entry + commentary exist. Future cleanup PRs can't remove it without breaking that test, which forces the maintainer to read the docstring and decide explicitly. Pattern: any deliberate dead code gets a docstring rationale + a test that locks it in place."

requirements-completed: [ANLY-03]

# Metrics
duration: ~30 minutes active execution (RED + GREEN + 1 Rule-1 test fix + closeout)
completed: 2026-05-03
---

# Phase 03 Plan 04: News/Sentiment Analyst — VADER + 3-Day-Half-Life Recency + Source Weighting Summary

**Wave 2 / third analyst lands: pure-function `analysts.news_sentiment.score(snapshot, config, *, computed_at=None) -> AgentSignal` deterministically scores per-headline VADER compound polarity, weights by exponential recency decay (3-day half-life: `DECAY_K = math.log(2.0) / 3.0 ≈ 0.231`) and source credibility (yahoo-rss/google-news=1.0, finviz=0.7, press-wires=0.5 forward-compat dead code per Pitfall #6), and aggregates to a 5-state verdict using VADER-tuned boundaries (0.4 / 0.05 — tighter than fundamentals/technicals 0.6/0.2 because VADER compounds for financial headlines cluster in [-0.5, +0.5]). Headline filters drop undated (published_at=None), short-title (<20 chars), and stale (>14 days) headlines; the all-filtered case (n_used==0 BUT len(news) > 0) returns a data_unavailable signal with evidence enumerating which filter reasons fired. Lazy VADER singleton (`_VADER = None` + `_vader()` accessor with lazy import inside the accessor) keeps schema-only test runs fast. `now` read ONCE at top of `score()`; helpers receive `now` as parameter (locked by AST-walk test per Pitfall #7). Provenance header (INFRA-07) names virattt/ai-hedge-fund/src/agents/news_sentiment.py and explicitly documents the full LLM-vs-VADER sentiment-classifier divergence (virattt uses paid, non-deterministic call_llm(); we use VADER for keyless / lite-mode compatibility) plus the additive recency + source weighting. ANLY-03 closed.**

## Performance

- **Duration:** ~30 minutes active execution including TDD RED + GREEN + 1 Rule-1 test-side fix + closeout.
- **Tasks:** 2 — Task 1 (RED): write 22 failing tests covering lazy-init / 3 happy paths / 2 recency / 2 source / 3 filtering / 2 all-filtered / 2 empty-data / 8 determinism+provenance+meta. Task 2 (GREEN): implement `analysts/news_sentiment.py` + 1 Rule-1 test fix folded into the same commit (substring-vs-AST scope on `test_no_module_level_clock_in_helpers`).
- **Files created:** 2 (`analysts/news_sentiment.py` ~225 lines, `tests/analysts/test_news_sentiment.py` ~525 lines)
- **Files modified:** 0 (pure additive plan — no existing production files touched)

## Accomplishments

- **`analysts/news_sentiment.py` (~225 lines)** ships the locked Wave 2 analyst contract for news sentiment. Public surface is the single function `score(snapshot: Snapshot, config: TickerConfig, *, computed_at: Optional[datetime] = None) -> AgentSignal` — pure, deterministic (modulo the lazy VADER singleton's first-call construction), never raises for missing data, always returns an AgentSignal with `analyst_id="news_sentiment"`. Provenance header (INFRA-07) names `virattt/ai-hedge-fund/src/agents/news_sentiment.py` and explicitly documents the LLM-vs-VADER sentiment-classifier divergence plus the additive recency + source weighting + UNIFORM RULE empty-data guard.
- **Lazy VADER singleton:** `_VADER = None` at module-import time; `_vader()` accessor lazy-imports `from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer` and constructs the analyzer on first call. Subsequent calls reuse the cached instance. Schema-only test runs (e.g. `test_signals.py` + `conftest.py`) do not import vaderSentiment at all.
- **Module-level constants** make every threshold tunable: `NEWS_HALFLIFE_DAYS=3.0`, `DECAY_K=math.log(2.0)/3.0`, `SOURCE_WEIGHTS` dict (yahoo-rss/google-news=1.0, finviz=0.7, press-wires=0.5 forward-compat), `COMPOUND_BULLISH=0.05`, `COMPOUND_BEARISH=-0.05`, `COMPOUND_STRONG_BULLISH=0.4`, `COMPOUND_STRONG_BEARISH=-0.4`, `MIN_TITLE_LEN=20`, `MAX_AGE_DAYS=14.0`.
- **Three private helpers** orchestrate the scoring:
  - `_score_one(h, now) -> tuple[Optional[float], Optional[float]]` — score one headline. Returns (compound, weight) on success or (None, None) on filter-out. Filters in order: undated → short-title → stale. Weight = recency_w * source_w; unknown sources default to 0.5 (defensive).
  - `_aggregate(headlines, now) -> tuple[float, int, int, int, int]` — returns (weighted_avg_compound, n_used, n_undated, n_short, n_stale). Tracks per-filter counters for evidence-string composition.
  - `_total_to_verdict(weighted_compound) -> Verdict` — 5-state ladder with VADER-tuned strict-> boundaries at 0.4 / 0.05 / -0.05 / -0.4.
- **`score()` orchestration:** (1) Establish `now` from `computed_at` kwarg or `datetime.now(timezone.utc)` default. (2) UNIFORM RULE empty-data guard at the top — `snapshot.data_unavailable` OR `not snapshot.news` → return data_unavailable signal with evidence `["no news headlines available"]`. (3) `weighted_compound, n_used, n_undated, n_short, n_stale = _aggregate(snapshot.news, now)`. (4) All-filtered guard: `n_used == 0` BUT `len(snapshot.news) > 0` → return data_unavailable signal with evidence enumerating all three filter reasons. (5) Compute verdict + confidence. (6) Assemble evidence: top-line summary always; n_undated mention if > 0; n_short mention if > 0; n_stale silent (covered by the recency design). (7) Construct and return `AgentSignal(...)` with `evidence[:10]` cap.
- **Verdict boundaries are VADER-tuned (0.4 / 0.05 / -0.05 / -0.4) — tighter than the 0.6/0.2 used by fundamentals + technicals.** Reason: VADER compounds for financial headlines cluster in [-0.5, +0.5]; picking 0.6 as the strong boundary would mean `strong_bullish` never fires. Pattern: pick boundaries from the empirical distribution of the input metric, not by analogy to other analysts.
- **Confidence formula `min(100, int(round(min(1.0, abs(weighted_compound) * 2.5) * 100)))`.** The 2.5x multiplier stretches `|compound|=0.4` to `confidence=100`, matching the natural data distribution. Documented in a comment so future readers don't tweak it without understanding the rationale.
- **Pitfall #7 single-now discipline locked by AST-walk test** — `test_no_module_level_clock_in_helpers` parses the module's AST and verifies no helper function (anything that isn't `score`) calls `datetime.now()`. Substring scans were rejected (would false-positive on docstring text — same Rule-1 pattern as 03-03's pandas-ta test).
- **Filter behaviors locked by dedicated tests:**
  - `test_filter_undated_dropped` — 2 undated + 1 dated bullish → aggregate uses 1; evidence mentions "2 ... lacked timestamps".
  - `test_filter_short_title_dropped` — 2 short-title + 1 full bullish → evidence mentions "short" / "noise floor".
  - `test_filter_stale_dropped` — 1 stale (20d) + 2 fresh bullish → aggregate uses 2; stale silently dropped (no evidence string).
  - `test_all_undated_data_unavailable` + `test_all_short_data_unavailable` — n_used==0 path returns data_unavailable with evidence enumerating filter reasons.
- **Recency math locked by `test_recency_fresh_bullish_dominates_stale_bearish`** — 1 fresh bullish (recency_w=1.0) + 1 10-day-old bearish (recency_w ≈ 0.099) → tilts bullish. Test imports `DECAY_K` and computes `expected_stale_w = math.exp(-DECAY_K * 10.0)` to assert the decay constant matches the docstring claim.
- **Source-weight precedence locked by `test_source_weight_yahoo_dominates_finviz`** — yahoo-rss bullish (weight 1.0) + finviz bearish (weight 0.7), same timestamp → never lands bearish.
- **Press-wires forward-compat dead code locked by dedicated test** — `test_press_wires_source_in_dict_dead_code_doc` asserts SOURCE_WEIGHTS contains the "press-wires" key AND a comment mentioning "forward-compat" / "dead code" / "Pitfall #6". Future cleanup PRs can't silently remove the entry without breaking this test.
- **Coverage on `analysts/news_sentiment.py`: 91% line+branch combined** (gate ≥90% line / ≥85% branch). 22/22 tests green; targeted suite runs in 0.08s. **Full repo regression: 285 passed + 2 xfailed** (up from 263 + 2 xfailed at end of 03-03: +22 new news_sentiment tests). The 2 xfail markers in `tests/analysts/test_invariants.py` held strict — they remained xfail (strict=True is honored), confirming that 03-04's analyst module is correctly recognized but the cross-cutting "always 4 signals" + "dark snapshot → 4 data_unavailable=True" invariants still need 1 more analyst module (03-05 valuation) to flip GREEN.
- **No new dependencies** — vaderSentiment was added at 03-01 Task 1 alongside the AgentSignal schema scaffold, specifically for this plan to consume. `pyproject.toml` untouched. Lockfile untouched.

## Task Commits

1. **Task 1 (RED) — `test(03-04): add failing tests for news/sentiment analyst (VADER + recency + source weighting + filters)`:** `7787aee` — `tests/analysts/test_news_sentiment.py` with 22 RED tests; `pytest tests/analysts/test_news_sentiment.py` failed at the `from analysts.news_sentiment import score` line with `ImportError: cannot import name 'news_sentiment' from 'analysts'`. Verified the expected RED state.
2. **Task 2 (GREEN) — `feat(03-04): news/sentiment analyst — VADER + 3-day-half-life recency + source weighting`:** `c26a65b` — `analysts/news_sentiment.py` (~225 lines) implementing the score() function per implementation_sketch + 1 Rule-1 test-side fix folded into the same commit (substring-vs-AST scope on `test_no_module_level_clock_in_helpers`). All 22 tests green; 91% line+branch coverage; full repo regression 285 passed + 2 xfailed.

**Plan metadata commit:** added in this closeout (covers SUMMARY.md, STATE.md, ROADMAP.md plan-progress row, REQUIREMENTS.md ANLY-03 traceability flip).

## Files Created/Modified

### Created
- `analysts/news_sentiment.py` (~225 lines — provenance docstring + lazy VADER singleton + 9 module-level constants + `_score_one` + `_aggregate` + `_total_to_verdict` + `score()`)
- `tests/analysts/test_news_sentiment.py` (~525 lines, 22 tests)

### Modified
- (none — pure additive plan)

### Modified at closeout
- `.planning/STATE.md` (Phase 3 progress 3/5 → 4/5; current_plan 4 → 5; recent decisions append)
- `.planning/ROADMAP.md` (Phase 3 row 3/5 → 4/5; Plans list `[ ] 03-04` → `[x] 03-04`)
- `.planning/REQUIREMENTS.md` (ANLY-03 traceability Pending → Complete; checkbox `[ ] **ANLY-03**` → `[x] **ANLY-03**`)

## Decisions Made

- **VADER, not LLM-call_llm.** Full sentiment-classifier divergence from virattt/ai-hedge-fund. Documented LLM-vs-VADER tradeoff: virattt is paid + non-deterministic + INFRA-02-incompatible; VADER is free + deterministic + lite-mode-friendly. Accuracy gap (~55-68% vs FinBERT's ~85%) acknowledged in docstring with a forward pointer to FinVADER / Loughran-McDonald deferred ideas in 03-CONTEXT.md.
- **Lazy VADER singleton (`_VADER = None` + `_vader()` accessor with lazy import).** Schema-only test runs don't pay VADER's cost. Verified at runtime by test_lazy_vader_init_is_none_at_import_time.
- **3-day half-life recency decay; 14-day stale-drop floor.** Per 03-CONTEXT.md threshold defaults; tunable via NEWS_HALFLIFE_DAYS / MAX_AGE_DAYS module constants.
- **Source weights yahoo-rss/google-news=1.0, finviz=0.7. Unknown sources default to 0.5 (defensive).**
- **press-wires=0.5 is forward-compat dead code per Pitfall #6.** Headline.source Literal does not currently include "press-wires"; the SOURCE_WEIGHTS entry never fires in v1 but survives in the dict + docstring + dedicated test (test_press_wires_source_in_dict_dead_code_doc) so future cleanup PRs can't silently remove it.
- **Verdict boundaries 0.4 / 0.05 / -0.05 / -0.4 — VADER-distribution-tuned.** Tighter than fundamentals/technicals 0.6/0.2 because VADER compounds for financial headlines cluster in [-0.5, +0.5].
- **Confidence stretching: `min(100, int(round(min(1.0, abs(weighted_compound) * 2.5) * 100)))`.** 2.5x multiplier maps |compound|=0.4 → confidence=100. Documented at the call site.
- **Filters in order: undated → short-title → stale.** Cheapest checks first.
- **n_stale silent in evidence; n_undated + n_short surfaced.** Stale headlines are dropped by the recency-decay design and not actionable for the user; undated and short-title indicate ingestion-side bugs the user might want to know about. The all-filtered case enumerates ALL three reasons for full diagnostic transparency.
- **`now` read ONCE at top of score(); helpers receive `now` as parameter (Pitfall #7).** Locked by AST-walk test (test_no_module_level_clock_in_helpers).
- **ROADMAP.md plan-progress edit done MANUALLY** per the precedent set in Plans 02-07 / 03-01 / 03-02 / 03-03 closeouts.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Test-side bug] `test_no_module_level_clock_in_helpers` substring scope was too wide**
- **Found during:** Task 2 GREEN initial test run — the test asserted `src.count("datetime.now(") <= 1`, which false-positives on the provenance docstring (which legitimately mentions `datetime.now(timezone.utc)` 3 times to document the contract that score() reads `now` once at the top with that exact default expression).
- **Issue:** The test's intent is "no helper function CALLS datetime.now()" — Pitfall #7. Substring counting was the wrong tool because docstring + comment text counts toward the total. Same kind of false positive as 03-03's `test_pandas_imported_no_pandas_ta`.
- **Fix:** Switched to AST walk. Parse the module source via `ast.parse`, iterate top-level function definitions, walk each non-`score` function's AST looking for `Call` nodes whose func is `Attribute(value=Name(id='datetime'), attr='now')`. Locked by `import ast` + `ast.iter_child_nodes(tree)` + `ast.walk(node)`.
- **Files modified:** `tests/analysts/test_news_sentiment.py` (lines ~470-498, scope tightened from substring count to AST walk)
- **Verification:** Test passes against the implemented module; would still fail loudly if `_score_one` or `_aggregate` were ever refactored to call `datetime.now()` directly. Confirmed by mental model: substituting `datetime.now(timezone.utc)` into a helper function body would make the AST walk find the call inside that function and fail the assertion.
- **Committed in:** `c26a65b` (GREEN commit folds in the test fix alongside the implementation)

---

**Total deviations:** 1 auto-fixed (Rule 1 — test-side bug surfaced during GREEN). **Impact:** test-side only. The implementation matches the plan's specifications byte-for-byte; the fix tightens the test scaffolding so it correctly exercises the implementation.

## Issues Encountered

- **Same vaderSentiment DeprecationWarning** — `vaderSentiment 3.3.x` uses `codecs.open()` which emits a DeprecationWarning under Python 3.14. Two warnings emitted on first VADER construction (lexicon + emoji). Not actionable — vaderSentiment library issue, not ours. Suppressing via `pytest.ini` filterwarnings would mask the signal if the library bumps to a real error in a future Python release. Left untouched.

## Self-Check: PASSED

- [x] `analysts/news_sentiment.py` exists — FOUND (~225 lines)
- [x] `tests/analysts/test_news_sentiment.py` exists — FOUND (~525 lines, 22 tests)
- [x] Provenance header in `analysts/news_sentiment.py` references `virattt/ai-hedge-fund/src/agents/news_sentiment.py` AND mentions VADER divergence — VERIFIED via Grep
- [x] `score()` signature is `(snapshot: Snapshot, config: TickerConfig, *, computed_at: Optional[datetime] = None) -> AgentSignal` — VERIFIED in source
- [x] `_VADER = None` module-level + `_vader()` accessor present — VERIFIED
- [x] `_score_one`, `_aggregate`, `_total_to_verdict` helpers all present — VERIFIED
- [x] Module-level constants present (NEWS_HALFLIFE_DAYS / DECAY_K / SOURCE_WEIGHTS dict / COMPOUND_BULLISH/BEARISH/STRONG_BULLISH/STRONG_BEARISH / MIN_TITLE_LEN / MAX_AGE_DAYS) — VERIFIED
- [x] SOURCE_WEIGHTS contains "press-wires": 0.5 with forward-compat / Pitfall #6 doc — VERIFIED
- [x] Empty-data UNIFORM RULE present (snapshot.data_unavailable OR not snapshot.news) — VERIFIED
- [x] All-filtered guard present (n_used == 0 BUT len(snapshot.news) > 0) — VERIFIED
- [x] `now` read ONCE in score(); no helper calls datetime.now() — VERIFIED via AST walk in test_no_module_level_clock_in_helpers
- [x] Commit `7787aee` (Task 1 RED — failing tests for news/sentiment analyst) — FOUND in git log
- [x] Commit `c26a65b` (Task 2 GREEN — analysts/news_sentiment.py implementation + 1 test-side fix) — FOUND in git log
- [x] `pytest tests/analysts/test_news_sentiment.py -v` — 22/22 PASSED in 0.08s
- [x] `pytest -q` (full repo regression) — **285 passed + 2 xfailed** (up from 263 + 2 xfailed at end of 03-03: +22 news_sentiment tests; the 2 xfail markers in test_invariants.py held strict and remained xfail as expected — Wave 2 still needs 1 more analyst module to flip them green; 03-05 removes the markers as its final task)
- [x] Coverage on `analysts/news_sentiment.py`: **91% line+branch combined** (gate ≥90% line / ≥85% branch)
- [x] Pure-function discipline: no I/O, lazy-only mutable state (`_VADER` singleton initialized once), no clock reads inside helpers — VERIFIED by source inspection + AST walk test
- [x] xfail markers in `tests/analysts/test_invariants.py` UNTOUCHED — VERIFIED via `git diff 10121ea..c26a65b -- tests/analysts/test_invariants.py` returns empty
- [x] Determinism contract: two calls with identical inputs → byte-identical AgentSignal model_dump_json — VERIFIED by `test_deterministic`

### Expected-RED tests (NOT failures)

The 2 tests in `tests/analysts/test_invariants.py` REMAIN xfail at end of 03-04 — same as end of 03-02 / 03-03. The lazy `from analysts import fundamentals, news_sentiment, technicals, valuation` import line still fails on the missing 1 module (valuation):

- `tests/analysts/test_invariants.py::test_always_four_signals` — XFAIL (valuation module doesn't exist yet)
- `tests/analysts/test_invariants.py::test_dark_snapshot_emits_four_unavailable` — XFAIL (same)

Plan 03-05 (the LAST Wave 2 plan) MUST remove the `@pytest.mark.xfail` markers in its final task. The `strict=True` on each marker held during this run — they remained xfail and didn't unexpectedly turn GREEN, confirming that 03-04 didn't accidentally over-ship the cross-cutting contract.

## Next Phase Readiness

- **Wave 2 progress: 3/4 analysts shipped** (fundamentals + technicals + news_sentiment). One remaining: 03-05 (valuation). 03-05 wraps Wave 2 by removing the `@pytest.mark.xfail(strict=True)` markers from `tests/analysts/test_invariants.py` as its final task — at that point both cross-cutting tests flip GREEN naturally as all four analyst modules exist and respect the dark-snapshot UNIFORM RULE.
- **Lazy-singleton pattern is locked** — Phase 4 POSE-01..05 (Position-Adjustment Radar) and Phase 5 (LLM personas + synthesizer) can reuse the `_RESOURCE = None` + `_resource()` accessor pattern for any expensive-to-construct dependency (tokenizers, FinBERT models, LLM clients). The pattern is greppable, testable, and keeps schema-only test runs fast.
- **Pitfall #7 single-now discipline + AST-walk test pattern is locked** — every future analyst module follows the same shape: `now = computed_at if computed_at is not None else datetime.now(timezone.utc)` at the top of score(); helpers receive `now` as parameter. The AST-walk test (test_no_module_level_clock_in_helpers) is copy-pasta-ready into 03-05's test suite.
- **Forward-compat-dead-code-with-test pattern is locked** — SOURCE_WEIGHTS['press-wires'] never fires in v1 but survives because docstring + dedicated test lock it in place. Future analyst modules with similar forward-compat needs (e.g., a target_multiples sub-field that the current TickerConfig doesn't yet expose) follow the same docstring-rationale + dedicated-test pattern.
- **No carry-overs / no blockers from this plan.** Wave 2 progress: 3/4 analysts complete. ANLY-03 closed in REQUIREMENTS.md.

---
*Phase: 03-analytical-agents-deterministic-scoring*
*Plan: 04-news-sentiment*
*Completed: 2026-05-03*
