---
phase: 05-claude-routine-wiring
plan: 05
type: tdd
wave: 4
depends_on: [05-02, 05-03, 05-04]
files_modified:
  - prompts/synthesizer.md
  - synthesis/synthesizer.py
  - synthesis/dissent.py
  - tests/synthesis/test_synthesizer.py
  - tests/synthesis/test_dissent.py
autonomous: true
requirements: [LLM-06, LLM-07]
provides:
  - "prompts/synthesizer.md — full synthesizer prompt (~150-200 lines, 4 sections: Input Context / Task / Output Schema / data_unavailable handling) per Pattern #7. Replaces Wave 0 stub. Encodes recommendation priority order in plain English (POSE.action_hint drives intraday tactical → persona consensus drives short_term → valuation thesis_price gap drives long_term thesis); conviction band rules; dual-timeframe summary instructions; pre-computed dissent rendering instruction (verbatim — synthesizer does NOT compute dissent)."
  - "synthesis/dissent.py — `compute_dissent(persona_signals: list[AgentSignal]) -> tuple[Optional[str], str]` per Pattern #7 / LLM-07. Module constants: VERDICT_TO_DIRECTION (5-key dict, strong_bullish/bullish=+1, neutral=0, bearish/strong_bearish=-1); DISSENT_THRESHOLD=30 (boundary inclusive). Returns (None, '') when <2 valid personas OR direction_score==0 OR no opposite-direction personas at ≥30 confidence. Tie-break: highest confidence first; alphabetical analyst_id second (deterministic)."
  - "synthesis/synthesizer.py — `synthesize(client, *, ticker, snapshot, config, analytical_signals, position_signal, persona_signals, computed_at) -> TickerDecision`. Single-call wrapper around routine.llm_client.call_with_retry(model='claude-opus-4-7', max_tokens=4000, output_format=TickerDecision). Loads prompts/synthesizer.md via lru_cache. Computes dissent in Python BEFORE the LLM call (Pattern #7 lock); injects pre-computed dissent string into the user_context. On Snapshot.data_unavailable=True or downstream LLM exhaustion → returns _data_unavailable_decision (closure-bound default_factory)."
  - "Module constants in synthesis/synthesizer.py: SYNTHESIZER_PROMPT_PATH=Path('prompts/synthesizer.md'); SYNTHESIZER_MODEL='claude-opus-4-7'; SYNTHESIZER_MAX_TOKENS=4000."
  - "load_synthesizer_prompt() -> str — lru_cache disk read, parallel of routine/persona_runner.load_persona_prompt; cache_clear() exposed for tests."
  - "build_synthesizer_user_context(ticker, snapshot, config, analytical_signals, position_signal, persona_signals, dissent_persona_id, dissent_summary) -> str — deterministic; sections: # Ticker / # Snapshot Summary / # 4 Analytical Signals / # PositionSignal / # 6 Persona Signals / # User TickerConfig / # Pre-computed Dissent (always present, even when no dissent — block contains 'no dissent' literal in that case)"
  - "_decision_default_factory(ticker, computed_at, reason) -> Callable[[], TickerDecision] — closure-bound LLM-05 default; returns TickerDecision with data_unavailable=True, recommendation='hold', conviction='low', short_term/long_term carrying single 'data unavailable: <reason>' driver, dissent=DissentSection() default. Satisfies the @model_validator invariant from 05-02."
  - "tests/synthesis/test_dissent.py — ~12 tests covering 3 dissent scenarios (no dissent / mild dissent at exactly 30 / extreme dissent) + 5+ tie-break scenarios + edge cases (all-data-unavailable; <2 valid; direction_score==0 zero-sum; ≥2 dissenters confidence-tied with alphabetical fallback; verdict='neutral' personas don't count as dissent in either direction)"
  - "tests/synthesis/test_synthesizer.py — ~10 tests covering: file-presence + content shape on prompts/synthesizer.md; load_synthesizer_prompt cache; build_synthesizer_user_context determinism + content (includes dissent block always); 6 recommendation-derivation paths via mocked LLM responses (add/trim/hold/take_profits/buy/avoid); lite-mode skip path (Snapshot.data_unavailable=True returns _data_unavailable_decision WITHOUT calling LLM); LLM-exhaustion path returns default-factory; provenance header references TauricResearch/TradingAgents"
tags: [phase-5, synthesizer, dissent, ticker-decision, llm-06, llm-07, async, tdd, wave-4]

must_haves:
  truths:
    - "prompts/synthesizer.md exists with full content (≥150 lines, NOT the Wave 0 stub); contains the 4 locked section headers: # Synthesizer (or similar H1) / ## Input Context / ## Task / ## Output Schema; ALSO contains a section/subsection naming the data_unavailable handling rule"
    - "prompts/synthesizer.md Task section encodes the recommendation priority order in plain English: PositionSignal.action_hint drives intraday tactical layer FIRST; persona consensus drives short_term WHEN action_hint is 'hold_position'; valuation thesis_price gap drives long_term thesis updates"
    - "prompts/synthesizer.md Task section names the conviction-band rule: 'high' = ≥5 of 11 signals agree AND no dissent; 'medium' = 3-4 agree OR mild dissent; 'low' = ≤2 agree OR non-empty dissent_summary AND signals split"
    - "prompts/synthesizer.md instructs the synthesizer to render the PRE-COMPUTED dissent string into TickerDecision.dissent verbatim — the synthesizer must NOT compute dissent itself (Pattern #7 lock)"
    - "prompts/synthesizer.md contains literal substring 'ground every conclusion in specific evidence' (lifted near-verbatim from TauricResearch/TradingAgents portfolio_manager.py per 05-RESEARCH.md line 904)"
    - "prompts/synthesizer.md Output Schema section names the TickerDecision fields verbatim: ticker, computed_at, schema_version, recommendation, conviction, short_term, long_term, open_observation, dissent, data_unavailable; AND lists the 6 DecisionRecommendation enum values + 3 ConvictionBand values"
    - "synthesis/dissent.py exports compute_dissent (function) + VERDICT_TO_DIRECTION (dict) + DISSENT_THRESHOLD (int constant = 30)"
    - "VERDICT_TO_DIRECTION maps EXACTLY: 'strong_bearish': -1, 'bearish': -1, 'neutral': 0, 'bullish': 1, 'strong_bullish': 1 (5 keys)"
    - "DISSENT_THRESHOLD == 30 (LLM-07 boundary inclusive: ≥30 confidence on opposite direction triggers dissent)"
    - "compute_dissent — no-dissent scenario: 6 bullish AgentSignals (all verdict='bullish', confidence ≥30) → returns (None, '')"
    - "compute_dissent — clear-dissent scenario: 5 bullish (verdict='bullish', confidence=70 each) + 1 bearish (analyst_id='burry', verdict='bearish', confidence=80, evidence=['hidden risk in margin compression']) → direction_score=+5*70-80=+270 >0 (majority bullish); burry on opposite direction with conf 80 ≥30 → returns ('burry', 'burry dissents (bearish, conf=80): hidden risk in margin compression')"
    - "compute_dissent — boundary-inclusive at exactly 30: 5 bullish (conf=50 each) + 1 bearish (conf=30, ANY analyst_id) → returns (analyst_id, summary) — confidence==DISSENT_THRESHOLD triggers"
    - "compute_dissent — boundary-exclusive at 29: 5 bullish (conf=50 each) + 1 bearish (conf=29) → returns (None, '') — strictly below threshold"
    - "compute_dissent — <2 valid personas: 1 valid + 5 data_unavailable=True OR 1 valid + 5 confidence=0 → returns (None, '') (cannot define 'majority' from <2 signals)"
    - "compute_dissent — all data_unavailable: 6 personas all .data_unavailable=True → returns (None, '')"
    - "compute_dissent — direction_score==0 zero-sum: 3 bullish (conf=50 each, total +150) + 3 bearish (conf=50 each, total -150) → direction_score=0 → returns (None, '') (no clear majority direction)"
    - "compute_dissent — neutral personas don't count as dissent: 5 bullish (conf=70 each, total +350) + 1 neutral (verdict='neutral', conf=80) → returns (None, '') (neutral has direction=0, not opposite to majority +1)"
    - "compute_dissent — multiple dissenters tie-break by confidence (highest wins): 4 bullish + 2 bearish (one conf=40, one conf=70) → returns the higher-confidence bearish persona"
    - "compute_dissent — confidence-tied dissenters tie-break alphabetically by analyst_id: 4 bullish + 2 bearish at SAME confidence=70 (e.g. burry + munger) → returns 'burry' (alphabetical first)"
    - "compute_dissent — return shape: (Optional[str], str). The persona_id is exactly one of the 6 PersonaId Literal values OR None; the summary is empty string '' when persona_id is None and ≤500 chars (DissentSection.dissent_summary max_length) when persona_id is non-None"
    - "compute_dissent — summary format: 'analyst_id dissents (verdict, conf=N): evidence_strings_joined_by_;'; example 'burry dissents (bearish, conf=80): hidden risk in margin compression'; truncated to ≤500 chars defensively"
    - "synthesis/synthesizer.py exports synthesize (async function) + load_synthesizer_prompt + build_synthesizer_user_context + 3 module constants (SYNTHESIZER_PROMPT_PATH, SYNTHESIZER_MODEL='claude-opus-4-7', SYNTHESIZER_MAX_TOKENS=4000)"
    - "synthesize Snapshot.data_unavailable=True path: returns a TickerDecision with .data_unavailable=True, .recommendation='hold', .conviction='low' (satisfies the schema invariant from 05-02), .open_observation containing 'snapshot data_unavailable=True' (or similar reason); LLM is NOT called in this path"
    - "synthesize lite-mode skip — when persona_signals is empty (length 0): returns _data_unavailable_decision with reason 'lite_mode (no persona signals)' WITHOUT calling LLM; LLM is NOT called"
    - "synthesize happy path — mocked LLM returns valid TickerDecision: synthesize returns that TickerDecision; mock recorded EXACTLY 1 messages.parse() call with model='claude-opus-4-7', max_tokens=4000, output_format=TickerDecision, system=<synthesizer.md content>"
    - "synthesize LLM exhaustion → default_factory: 2 ValidationError exceptions queued (matches DEFAULT_MAX_RETRIES=2) → synthesize returns TickerDecision with .data_unavailable=True, .recommendation='hold', .conviction='low'"
    - "synthesize 6 recommendation-derivation paths (mocked): mock returns TickerDecision with recommendation='add' / 'trim' / 'hold' / 'take_profits' / 'buy' / 'avoid' (parametrized over 6 values; each constructs cleanly + propagates through synthesize unchanged)"
    - "build_synthesizer_user_context: contains 'Pre-computed Dissent' (or similar) section ALWAYS — when no dissent computed, the block contains a literal 'no dissent' or 'has_dissent: false' indicator (so the synthesizer prompt always sees a clear instruction either way)"
    - "build_synthesizer_user_context: deterministic — two calls with identical inputs produce byte-identical output strings"
    - "build_synthesizer_user_context: includes ALL 11 input signals' verdict/confidence/evidence: 4 analytical signals (fund/tech/nsen/val) + 1 PositionSignal (state, consensus_score, action_hint) + 6 persona signals (each with analyst_id + verdict + confidence + top-3 evidence)"
    - "Wave 4 IS the dissent-in-Python lock: synthesis/dissent.py exists; synthesis/synthesizer.py imports `from synthesis.dissent import compute_dissent`; the synthesizer prompt does NOT instruct the LLM to compute dissent (only to render the pre-computed string)"
    - "Provenance per INFRA-07: synthesis/synthesizer.py docstring contains literal 'TauricResearch/TradingAgents' AND specifically 'tradingagents/agents/' (per CONTEXT.md provenance lock); names the modifications (6-state recommendation, dissent-section, dual-timeframe, dissent-in-Python rather than LLM-computed)"
    - "Coverage ≥90% line / ≥85% branch on synthesis/synthesizer.py AND synthesis/dissent.py"
    - "Phase 1-4 + Wave 0 + Wave 1 + Wave 2 + Wave 3 regression invariant: existing tests stay GREEN"
  artifacts:
    - path: "prompts/synthesizer.md"
      provides: "Full synthesizer prompt content per Pattern #7. ~150-200 lines. 4 sections + data_unavailable handling. Encodes priority order, conviction rules, dissent rendering instruction."
      min_lines: 150
    - path: "synthesis/dissent.py"
      provides: "compute_dissent + VERDICT_TO_DIRECTION + DISSENT_THRESHOLD + signed-weighted-vote majority + tie-break (confidence first, alphabetical analyst_id second). ~70-90 LOC including provenance docstring."
      min_lines: 60
    - path: "synthesis/synthesizer.py"
      provides: "synthesize + load_synthesizer_prompt + build_synthesizer_user_context + _decision_default_factory + 3 module constants + provenance docstring referencing TauricResearch/TradingAgents/tradingagents/agents/. ~130-170 LOC."
      min_lines: 120
    - path: "tests/synthesis/test_dissent.py"
      provides: "≥12 tests covering 3 main scenarios + 5+ tie-break/edge cases + boundary inclusive/exclusive at 30 + zero-sum direction_score + neutral-doesn't-count + return-shape contract. ~250 LOC."
      min_lines: 200
    - path: "tests/synthesis/test_synthesizer.py"
      provides: "≥10 tests covering prompt file presence + load cache + user-context determinism + 6 recommendation-paths + lite-mode skip + LLM-exhaustion default-factory + Snapshot data_unavailable skip + provenance + dissent-block-always-present. ~300 LOC."
      min_lines: 250
  key_links:
    - from: "synthesis/synthesizer.py"
      to: "synthesis.decision (Wave 1 / 05-02)"
      via: "imports TickerDecision + DissentSection + TimeframeBand + DecisionRecommendation + ConvictionBand for output_format and default_factory shapes"
      pattern: "from synthesis\\.decision import"
    - from: "synthesis/synthesizer.py"
      to: "synthesis.dissent (this plan)"
      via: "imports compute_dissent — Python-computed BEFORE the LLM call per Pattern #7"
      pattern: "from synthesis\\.dissent import compute_dissent"
    - from: "synthesis/synthesizer.py"
      to: "routine.llm_client.call_with_retry (Wave 2 / 05-03)"
      via: "single per-ticker LLM call wrapping messages.parse(output_format=TickerDecision)"
      pattern: "from routine\\.llm_client import call_with_retry"
    - from: "synthesis/synthesizer.py"
      to: "prompts/synthesizer.md"
      via: "load_synthesizer_prompt() reads SYNTHESIZER_PROMPT_PATH at call time; lru_cache for re-use across N tickers in a routine run"
      pattern: "prompts/synthesizer\\.md"
    - from: "synthesis/dissent.py"
      to: "analysts.signals.AgentSignal + Verdict (Phase 3)"
      via: "compute_dissent input is list[AgentSignal] of 6 persona signals; iterates over .verdict / .confidence / .evidence / .analyst_id / .data_unavailable"
      pattern: "from analysts\\.signals import"
    - from: "synthesis/synthesizer.py docstring"
      to: "TauricResearch/TradingAgents/tradingagents/agents/ (INFRA-07 provenance per 05-CONTEXT.md)"
      via: "module docstring carries the lineage + 4 modifications (6-state recommendation, explicit DissentSection, dual-timeframe, dissent-in-Python)"
      pattern: "TauricResearch/TradingAgents"
    - from: "tests/synthesis/test_synthesizer.py"
      to: "tests.routine.conftest.mock_anthropic_client (Wave 2 fixture)"
      via: "all LLM-call tests use the shared MockAnthropicClient + isolated_failure_log autouse fixture; tests/synthesis/conftest.py re-imports them OR pytest auto-discovers from tests/routine/ via root conftest"
      pattern: "mock_anthropic_client"
---

<objective>
Wave 4 / LLM-06 + LLM-07: ship the synthesizer triad — `prompts/synthesizer.md` (full ~150-200 line prompt encoding the recommendation priority order, conviction band rules, dual-timeframe summary instructions, dissent-rendering instruction, data_unavailable handling per Pattern #7), `synthesis/dissent.py` (the Python-computed dissent rule per LLM-07 — signed-weighted-vote majority direction + opposite-direction-≥30-confidence trigger + tie-break by confidence-then-alphabetical), `synthesis/synthesizer.py` (single per-ticker LLM call wrapping `routine.llm_client.call_with_retry` with `model='claude-opus-4-7'`, `output_format=TickerDecision`).

Purpose: closes LLM-06 + LLM-07 — the final 2 LLM-XX requirements (LLM-08 closes in Wave 5). The synthesizer is the per-ticker decision producer; it consumes 4 analytical AgentSignals + 1 PositionSignal + 6 persona AgentSignals (all available after Wave 3) + Snapshot + TickerConfig and produces ONE Pydantic-validated TickerDecision (Wave 1's schema).

The dissent-in-Python lock (Pattern #7) is the biggest design decision in this plan: LLM-07 is a structural rule ("≥1 persona disagrees by ≥30 confidence on opposite direction"), so we compute it deterministically in Python BEFORE the synthesizer LLM call and pass the pre-computed `dissent_summary` string to the synthesizer prompt. The synthesizer's job is to RENDER the pre-computed dissent verbatim into the TickerDecision.dissent field, not to compute the dissent. Three reasons (per 05-RESEARCH.md Pattern #7 + Anti-Patterns):
1. **Determinism.** A Python computation over 6 AgentSignals is testable (3 main scenarios + tie-break variants), reproducible, and shows the contract surface clearly.
2. **No hallucination risk.** If the LLM picked the dissenting persona, constrained-decoding only validates type (`str | None`), not "this string is one of the 6 persona IDs". A typo'd `"warrenbufett"` would pass schema validation but break Phase 6 frontend rendering.
3. **Tie-breaking specificity.** The user's lock requires "highest confidence wins; alphabetical analyst_id breaks ties". An LLM's tie-breaking is ad-hoc.

The signed-weighted-vote majority direction (per Pattern #7 + Anti-Pattern at line 1189): `direction_score = sum(VERDICT_TO_DIRECTION[s.verdict] * s.confidence for s in valid_personas)`. NOT majority verdict (mode). Reason: a 2-strong_bullish (verdict-mode bullish) + 4-bullish slate has direction_score=+400, but a 4-bullish + 2-strong_bullish-but-with-confidence-90 slate has direction_score=+(4×60)+(2×90)=+420 — the magnitude of conviction matters, not just the count.

The synthesizer prompt encodes the recommendation priority order in plain English (per Pattern #7):
1. **Tactical (intraday) layer:** PositionSignal.action_hint drives. consider_take_profits + bullish persona consensus → 'take_profits'. consider_add + bullish consensus → 'add'. consider_trim + bearish consensus → 'trim'.
2. **Short-term layer:** persona consensus drives when action_hint is 'hold_position'. Bullish-leaning personas + 'hold_position' → 'add' or 'buy' depending on whether user already holds the position.
3. **Long-term layer:** valuation analyst's verdict + persona consensus on long-term lens drives. Strong-bullish valuation + ≥4 bullish personas + price < thesis_price → 'buy'. Strong-bearish valuation + ≥4 bearish personas → 'avoid'.

The 6 enum values (DecisionRecommendation): `add` (own; increase), `trim` (own; reduce), `hold` (no action; default for mixed signals), `take_profits` (own; sell some/all on extreme overbought), `buy` (don't own; initiate), `avoid` (don't own; do not initiate).

Output: prompts/synthesizer.md (~180 lines, full content); synthesis/dissent.py (~80 LOC); synthesis/synthesizer.py (~150 LOC); tests/synthesis/test_dissent.py (~250 LOC, ≥12 tests covering 3 main scenarios + tie-breaks + boundary cases + zero-sum + neutral-doesn't-count); tests/synthesis/test_synthesizer.py (~300 LOC, ≥10 tests covering prompt presence + load cache + user-context determinism + 6 recommendation-paths + lite-mode skip + Snapshot data_unavailable skip + LLM-exhaustion default-factory + dissent block always present + provenance).

Provenance per INFRA-07: synthesis/synthesizer.py docstring references TauricResearch/TradingAgents/tradingagents/agents/{managers/portfolio_manager.py, managers/research_manager.py} — adapted with 4 modifications:
1. **6-state DecisionRecommendation** (vs TradingAgents' 5-state buy/overweight/hold/underweight/sell). Locked in 05-02.
2. **Explicit DissentSection** — TradingAgents has no analog dissent surface. LLM-07 is novel-to-this-project.
3. **Dual-timeframe TimeframeBand** (short_term + long_term) — TradingAgents is single-timeframe.
4. **Dissent computed in Python** — TradingAgents (and most LLM-orchestration patterns) defer dissent reasoning to the LLM. Pattern #7 locks ours in Python for determinism.
</objective>

<execution_context>
@C:/Users/Mohan/.claude/workflows/execute-plan.md
@C:/Users/Mohan/.claude/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/05-claude-routine-wiring/05-CONTEXT.md
@.planning/phases/05-claude-routine-wiring/05-RESEARCH.md
@.planning/phases/05-claude-routine-wiring/05-01-foundation-PLAN.md
@.planning/phases/05-claude-routine-wiring/05-02-decision-schema-PLAN.md
@.planning/phases/05-claude-routine-wiring/05-03-llm-client-PLAN.md
@.planning/phases/05-claude-routine-wiring/05-04-personas-PLAN.md

# Existing patterns to mirror
@analysts/signals.py
@analysts/position_signal.py
@routine/llm_client.py
@routine/persona_runner.py
@synthesis/decision.py
@tests/routine/conftest.py
@tests/synthesis/test_decision.py
@tests/conftest.py

<interfaces>
<!-- 05-01 + 05-02 + 05-03 + 05-04 outputs we consume: -->

```python
# analysts.signals (Wave 0 widening):
class AgentSignal(BaseModel):
    ticker: str
    analyst_id: AnalystId
    computed_at: datetime
    verdict: Verdict
    confidence: int = Field(ge=0, le=100)
    evidence: list[str]
    data_unavailable: bool = False

Verdict = Literal[
    "strong_bullish", "bullish", "neutral", "bearish", "strong_bearish",
]

# analysts.position_signal:
class PositionSignal(BaseModel):
    ticker: str
    computed_at: datetime
    state: PositionState
    consensus_score: float
    confidence: int
    action_hint: ActionHint
    indicators: dict[str, float | None]
    evidence: list[str]
    data_unavailable: bool
    trend_regime: bool

# synthesis.decision (Wave 1 / 05-02):
DecisionRecommendation = Literal[
    "add", "trim", "hold", "take_profits", "buy", "avoid",
]
ConvictionBand = Literal["low", "medium", "high"]
Timeframe = Literal["short_term", "long_term"]

class TimeframeBand(BaseModel):
    summary: str
    drivers: list[str]
    confidence: int

class DissentSection(BaseModel):
    has_dissent: bool = False
    dissenting_persona: str | None = None
    dissent_summary: str = ""

class TickerDecision(BaseModel):
    ticker: str
    computed_at: datetime
    schema_version: int = 1
    recommendation: DecisionRecommendation
    conviction: ConvictionBand
    short_term: TimeframeBand
    long_term: TimeframeBand
    open_observation: str = ""
    dissent: DissentSection
    data_unavailable: bool = False
    # @model_validator: data_unavailable=True ⟹ recommendation='hold' AND conviction='low'

# routine.llm_client (Wave 2 / 05-03):
async def call_with_retry(
    client: AsyncAnthropic, *,
    model: str, system: str, user: str,
    output_format: type[T],
    default_factory: Callable[[], T],
    max_tokens: int,
    max_retries: int = DEFAULT_MAX_RETRIES,
    context_label: str,
) -> T: ...

# routine.persona_runner (Wave 3 / 05-04):
PERSONA_IDS = ("buffett", "munger", "wood", "burry", "lynch", "claude_analyst")
```

<!-- New types this plan creates: -->

```python
# synthesis.dissent
VERDICT_TO_DIRECTION: dict[Verdict, int] = {
    "strong_bearish": -1, "bearish": -1,
    "neutral": 0,
    "bullish": 1, "strong_bullish": 1,
}
DISSENT_THRESHOLD: int = 30  # boundary inclusive

def compute_dissent(persona_signals: list[AgentSignal]) -> tuple[Optional[str], str]: ...

# synthesis.synthesizer
SYNTHESIZER_PROMPT_PATH = Path("prompts/synthesizer.md")
SYNTHESIZER_MODEL = "claude-opus-4-7"
SYNTHESIZER_MAX_TOKENS = 4000

@functools.lru_cache(maxsize=2)
def load_synthesizer_prompt() -> str: ...

def build_synthesizer_user_context(
    ticker: str,
    snapshot: Snapshot,
    config: TickerConfig,
    analytical_signals: list[AgentSignal],   # 4: fund / tech / nsen / val
    position_signal: PositionSignal,
    persona_signals: list[AgentSignal],      # 6: PERSONA_IDS order
    dissent_persona_id: Optional[str],
    dissent_summary: str,
) -> str: ...

def _decision_default_factory(
    ticker: str, computed_at: datetime, reason: str,
) -> Callable[[], TickerDecision]: ...

async def synthesize(
    client: AsyncAnthropic, *,
    ticker: str,
    snapshot: Snapshot,
    config: TickerConfig,
    analytical_signals: list[AgentSignal],   # 4 — order: fund, tech, nsen, val
    position_signal: PositionSignal,
    persona_signals: list[AgentSignal],      # 6 in PERSONA_IDS order; can be []
    computed_at: datetime,
) -> TickerDecision: ...
```
</interfaces>

<implementation_sketch>
<!-- ============================================================
     prompts/synthesizer.md (~180 lines; full content)
     ============================================================ -->

```markdown
# Synthesizer: Per-Ticker Decision

You are the synthesizer for a personal stock-research dashboard. You receive
11 input signals about ONE ticker plus user configuration, plus a
PRE-COMPUTED dissent string. You produce ONE TickerDecision capturing the
short-term tactical view, the long-term thesis view, an overall
recommendation, conviction, an open observation, and the dissent surface.

Be decisive. Ground every conclusion in specific evidence from the input
signals. Do NOT invent numbers not present in the input snapshot. Do NOT
soften the recommendation by hand-waving — pick one of the 6 enum values
and commit.

## Input Context

You will receive (in this order):

- **Snapshot summary** — current price, recent prices (last 30 days),
  fundamentals (P/E, P/S, ROE, debt/equity, margins, FCF), recent headlines.
- **4 analytical AgentSignals** — `fundamentals`, `technicals`,
  `news_sentiment`, `valuation` (deterministic Python; trustworthy as
  factual inputs).
- **1 PositionSignal** — multi-indicator overbought/oversold consensus
  with `state`, `consensus_score`, `action_hint`, `confidence`,
  `trend_regime`.
- **6 persona AgentSignals** — `buffett`, `munger`, `wood`, `burry`,
  `lynch`, `claude_analyst` (each LLM-produced; each carries verdict +
  confidence + evidence).
- **TickerConfig** — `thesis_price`, `target_multiples`, `long_term_lens`,
  `short_term_focus`, `notes`, `technical_levels`.
- **Pre-computed Dissent** — when ≥1 persona disagrees by ≥30 confidence
  points from the majority direction (signed-weighted vote), this section
  identifies them by persona_id and summarizes their reasoning. This block
  is ALWAYS PRESENT — when no dissent, the block contains "no dissent".

## Task

Produce a `TickerDecision` covering:

### `recommendation` (one of): `add` | `trim` | `hold` | `take_profits` | `buy` | `avoid`

Apply this priority order — the FIRST rule that fires wins:

1. **Tactical (intraday) layer — PositionSignal.action_hint drives.**
   - `action_hint == 'consider_take_profits'` AND persona consensus is
     bullish-leaning → `take_profits`.
   - `action_hint == 'consider_add'` AND persona consensus is
     bullish-leaning → `add`.
   - `action_hint == 'consider_trim'` AND persona consensus is
     bearish-leaning → `trim`.
   - `action_hint == 'hold_position'` → fall through to short-term layer.

2. **Short-term layer — persona consensus drives WHEN tactical is
   `hold_position`.**
   - ≥4 of 6 personas bullish (verdict ∈ {bullish, strong_bullish}) + user
     `short_term_focus=True` → `add` (assume position exists) OR `buy`
     (initiate). Lean toward `add` when user has notes referencing existing
     position; lean toward `buy` otherwise. Default to `add` when ambiguous.
   - ≥4 of 6 personas bearish → `trim` or `avoid` symmetrically.
   - Mixed (2-3 vs 2-3) → fall through.

3. **Long-term layer — valuation analyst + persona long-term lens drive.**
   - Strong-bullish valuation (verdict='strong_bullish') + ≥4 bullish
     personas + price < `thesis_price` (when set) → `buy`.
   - Strong-bearish valuation (verdict='strong_bearish') + ≥4 bearish
     personas → `avoid`.
   - Otherwise → `hold`.

4. **Default fallback:** when none of the above fires cleanly → `hold`.

The 6 enum values map to:
- `add` — already own; increase position.
- `trim` — already own; reduce position.
- `hold` — no action this cycle. The default for mixed signals.
- `take_profits` — already own; sell some/all on extreme overbought.
- `buy` — do NOT own; initiate a new position.
- `avoid` — do NOT own; do NOT initiate.

### `conviction`: `low` | `medium` | `high`

Apply this rule:
- **`high`** — ≥5 of 11 input signals (4 analytical + 1 PositionSignal +
  6 personas) AGREE on the direction (signed: bullish-leaning vs
  bearish-leaning vs neutral) AND the pre-computed dissent block is "no
  dissent".
- **`medium`** — 3-4 signals agree OR the dissent block has content but
  the dissent is mild (single persona just over the 30 threshold).
- **`low`** — ≤2 signals agree (signals are split) OR dissent_summary is
  non-empty AND signals are otherwise split AND ≤3 agree.

### `short_term`: `TimeframeBand` (1-week-to-1-month tactical horizon)

- **`summary`** (1-500 chars): one paragraph capturing the next 1-week-to-
  1-month outlook. LEAD WITH the PositionSignal's state ("AAPL is in a
  fair regime with consensus_score=+0.05, no urgent positional action…").
  Mention the most directionally-confident analytical signal. Cite at
  most 2 personas' short-term-relevant reasoning. End with the
  recommendation rationale tied to TickerConfig.short_term_focus.
- **`drivers`** (≤10 short strings, each ≤200 chars): the specific
  reasons. Pull from analytical evidence + persona evidence; do NOT
  fabricate. Format: "<source>: <reason>" e.g. "PositionSignal: state=fair,
  consensus_score=+0.05".
- **`confidence`** (0-100): your confidence in this short-term framing.

### `long_term`: `TimeframeBand` (1-year-to-5-year strategic horizon)

Same shape; 1-year-to-5-year horizon. LEAD WITH the valuation analyst
verdict + the long-term-lens-aligned personas (Buffett + Munger for
value; Wood for growth/innovation; Lynch for GARP). Compare current
price to `TickerConfig.thesis_price` if user provided one. Discuss
moat durability + capital allocation arc + secular trajectory. End
with whether the long-term recommendation aligns with or modifies
the short-term recommendation.

### `open_observation` (≤500 chars)

Pin the Open Claude Analyst's observation here verbatim (or a tight
≤500-char summary). This is the "what does Claude reason outside the
persona frame" surface — the user's MEMORY.md feedback explicitly
requires this slot. If `claude_analyst` produced
`data_unavailable=True` or confidence=0, set `open_observation=""`.

### `dissent`: `DissentSection`

The dissent has been PRE-COMPUTED for you (in Python; deterministic).
Read the pre-computed dissent block from the user message:

- If pre-computed dissent_summary is non-empty:
  - `dissent.has_dissent`: `true`
  - `dissent.dissenting_persona`: copy the persona_id from the pre-
    computed block VERBATIM (must match one of: `buffett`, `munger`,
    `wood`, `burry`, `lynch`, `claude_analyst`).
  - `dissent.dissent_summary`: render the pre-computed dissent string
    into a coherent sentence — keep the persona_id, the verdict, and
    the top 1-2 reasons. Do NOT editorialize or downweight the dissent.
    Do NOT exceed 500 chars.

- If pre-computed dissent_summary is empty (the block says "no dissent"):
  - `dissent.has_dissent`: `false`
  - `dissent.dissenting_persona`: `null`
  - `dissent.dissent_summary`: `""`

### `data_unavailable`

`true` ONLY when Snapshot.data_unavailable is true (i.e., the input
snapshot lacked critical data). When true:
- `recommendation`: `hold`
- `conviction`: `low`
- `short_term.summary`: `"data unavailable: snapshot missing"` (or
  similar single-line explanation)
- `short_term.drivers`: `[]`
- `short_term.confidence`: `0`
- `long_term.summary`: same shape
- `long_term.drivers`: `[]`
- `long_term.confidence`: `0`
- `open_observation`: explain what data was missing
- `dissent.has_dissent`: `false`

## Output Schema

Return ONLY a JSON object matching the TickerDecision schema:

- `ticker` — the ticker symbol (echoed from input).
- `computed_at` — ISO 8601 UTC timestamp (echoed from input).
- `schema_version` — `1` (forward-compat hook for v1.x; do NOT bump).
- `recommendation` — one of: `add` | `trim` | `hold` | `take_profits` |
  `buy` | `avoid`.
- `conviction` — one of: `low` | `medium` | `high`.
- `short_term` — TimeframeBand (summary, drivers, confidence).
- `long_term` — TimeframeBand (summary, drivers, confidence).
- `open_observation` — ≤500 chars; pin Open Claude Analyst observation.
- `dissent` — DissentSection (has_dissent, dissenting_persona,
  dissent_summary).
- `data_unavailable` — boolean.

Be decisive on `recommendation` — pick one of the 6 enum values; do NOT
hedge. Ground every claim in specific evidence from the input signals
(quote numbers from analytical signals + cite persona evidence
verbatim where load-bearing). Do NOT invent numbers not present in
the input snapshot.
```

<!-- ============================================================
     synthesis/dissent.py (~80 LOC)
     ============================================================ -->

```python
"""synthesis.dissent — Python-computed dissent rule per LLM-07 + Pattern #7.

The dissent rule is structural: "≥1 persona disagrees by ≥30 confidence
points on the OPPOSITE direction from the signed-weighted-vote majority".
This is a deterministic computation over 6 AgentSignals; Python is the
right tool. Pre-computed dissent_summary is passed to the synthesizer
prompt; the synthesizer renders it verbatim into TickerDecision.dissent.

Three reasons to compute in Python (not the LLM):
  1. Determinism — testable, reproducible, debuggable.
  2. No hallucination risk — constrained-decoding only validates that
     dissenting_persona is `str | None`, not "this string is one of the
     6 persona IDs". Python guarantees a valid persona_id.
  3. Tie-break specificity — the user-locked rule (highest confidence
     wins; alphabetical analyst_id breaks ties) is precise; LLM
     tie-breaking is ad-hoc.

Per 05-RESEARCH.md Anti-Pattern at line 1189: dissent uses MAJORITY
DIRECTION (signed-weighted vote, factoring confidence) NOT MAJORITY
VERDICT (mode). Reason: a 4-bullish (conf 60 each) + 2-strong_bullish
(conf 90 each) slate has direction_score=+(4*60)+(2*90)=+420 — magnitude
matters, not just count.

Public surface:
    VERDICT_TO_DIRECTION  — 5-key map (strong_bullish/bullish→+1; neutral→0;
                             bearish/strong_bearish→-1)
    DISSENT_THRESHOLD     — 30 (LLM-07 boundary inclusive)
    compute_dissent(...)  — returns (Optional[persona_id], summary_str)
"""
from __future__ import annotations

from typing import Optional

from analysts.signals import AgentSignal, Verdict

VERDICT_TO_DIRECTION: dict[Verdict, int] = {
    "strong_bearish": -1,
    "bearish": -1,
    "neutral": 0,
    "bullish": 1,
    "strong_bullish": 1,
}

DISSENT_THRESHOLD: int = 30  # LLM-07 boundary inclusive — confidence==30 triggers


def compute_dissent(
    persona_signals: list[AgentSignal],
) -> tuple[Optional[str], str]:
    """Return (dissenting_persona_id, dissent_summary).

    Returns (None, "") when:
      * <2 valid persona signals (data_unavailable filters; confidence>0 also filters)
      * direction_score == 0 (zero-sum; no clear majority direction)
      * no opposite-direction personas at confidence ≥ DISSENT_THRESHOLD

    When ≥1 dissenter qualifies:
      * Tie-break: highest confidence first
      * Tie-break secondary: alphabetical analyst_id (deterministic)

    summary format: "<analyst_id> dissents (<verdict>, conf=<N>): <evidence>"
    where <evidence> is the joined-by-"; " concatenation of the dissenter's
    top-3 evidence strings; truncated to 500 chars defensively (matches
    DissentSection.dissent_summary max_length).
    """
    valid = [
        s for s in persona_signals
        if not s.data_unavailable and s.confidence > 0
    ]
    if len(valid) < 2:
        return None, ""

    direction_score = sum(
        VERDICT_TO_DIRECTION[s.verdict] * s.confidence for s in valid
    )
    if direction_score == 0:
        return None, ""
    majority_dir = 1 if direction_score > 0 else -1

    dissenters = [
        s for s in valid
        if VERDICT_TO_DIRECTION[s.verdict] == -majority_dir
        and s.confidence >= DISSENT_THRESHOLD
    ]
    if not dissenters:
        return None, ""

    # Tie-break: highest confidence first; alphabetical analyst_id second.
    dissenter = max(dissenters, key=lambda s: (s.confidence, _neg_alpha(s.analyst_id)))
    summary = (
        f"{dissenter.analyst_id} dissents ({dissenter.verdict}, "
        f"conf={dissenter.confidence}): "
        + "; ".join(dissenter.evidence[:3] if dissenter.evidence else [])
    )
    return dissenter.analyst_id, summary[:500]


def _neg_alpha(analyst_id: str) -> tuple[int, ...]:
    """Tuple-of-negated-codepoints sort key — smaller string sorts LATER.

    This makes `max(...)` with this key as a secondary tie-breaker pick the
    ALPHABETICALLY-FIRST analyst_id. Equivalent to `sorted(..., key=alpha)[0]`
    but composes cleanly with a `max` over a multi-key tuple.
    """
    return tuple(-ord(c) for c in analyst_id)
```

<!-- ============================================================
     synthesis/synthesizer.py (~150 LOC)
     ============================================================ -->

```python
"""synthesis.synthesizer — single per-ticker LLM call producing TickerDecision.

Pattern adapted from TauricResearch/TradingAgents
tradingagents/agents/managers/{portfolio_manager.py, research_manager.py}.

Modifications from the reference implementation:
  * 6-state DecisionRecommendation (vs TradingAgents' 5-state buy/overweight/
    hold/underweight/sell). Locked in 05-02 per user product requirements.
  * Explicit DissentSection — TradingAgents has no dissent surface; LLM-07
    is novel-to-this-project.
  * Dual-timeframe TimeframeBand (short_term + long_term cards) — TradingAgents
    is single-timeframe.
  * Dissent computed in PYTHON (synthesis/dissent.py) BEFORE the LLM call —
    Pattern #7 lock. The LLM renders the pre-computed dissent verbatim;
    it never computes dissent itself.
  * Anthropic-native via routine.llm_client.call_with_retry which uses
    client.messages.parse(output_format=TickerDecision) — TradingAgents uses
    LangChain's structured-output abstraction. We're keyless via Claude
    Code Routine subscription (PROJECT.md lock).
  * Async — TradingAgents is sync per-ticker; we use AsyncAnthropic
    consistently with Wave 3 persona fan-out (Pattern #3).

Public surface:
    SYNTHESIZER_PROMPT_PATH       — Path("prompts/synthesizer.md")
    SYNTHESIZER_MODEL             — "claude-opus-4-7" per Pattern #2
    SYNTHESIZER_MAX_TOKENS        — 4000
    load_synthesizer_prompt()     — disk read, lru_cache
    build_synthesizer_user_context(...) — single user-message string
    synthesize(...)               — single LLM call producing TickerDecision
"""
from __future__ import annotations

import functools
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from anthropic import AsyncAnthropic

from analysts.data.snapshot import Snapshot
from analysts.position_signal import PositionSignal
from analysts.schemas import TickerConfig
from analysts.signals import AgentSignal
from routine.llm_client import call_with_retry
from synthesis.decision import (
    DissentSection,
    TickerDecision,
    TimeframeBand,
)
from synthesis.dissent import compute_dissent

SYNTHESIZER_PROMPT_PATH: Path = Path("prompts/synthesizer.md")
SYNTHESIZER_MODEL: str = "claude-opus-4-7"
SYNTHESIZER_MAX_TOKENS: int = 4000


@functools.lru_cache(maxsize=2)
def load_synthesizer_prompt() -> str:
    """Read prompts/synthesizer.md from disk; cached.

    Cache size 2 is intentional: the prompt is read once per N_TICKERS in
    a routine run; lru_cache deduplicates. cache_clear() exposed for tests.
    """
    if not SYNTHESIZER_PROMPT_PATH.exists():
        raise FileNotFoundError(
            f"synthesizer prompt missing: {SYNTHESIZER_PROMPT_PATH}"
        )
    return SYNTHESIZER_PROMPT_PATH.read_text(encoding="utf-8")


def build_synthesizer_user_context(
    ticker: str,
    snapshot: Snapshot,
    config: TickerConfig,
    analytical_signals: list[AgentSignal],
    position_signal: PositionSignal,
    persona_signals: list[AgentSignal],
    dissent_persona_id: Optional[str],
    dissent_summary: str,
) -> str:
    """Build the synthesizer user-message string.

    All sections always present, even when content is "no dissent" or
    "data_unavailable" — keeps the synthesizer prompt's section-anchor
    parsing deterministic.
    """
    lines: list[str] = []
    lines.append(f"# Ticker: {ticker}")
    lines.append("")
    lines.append("## Snapshot Summary")
    lines.append(_summarize_snapshot(snapshot))
    lines.append("")
    lines.append("## 4 Analytical Signals")
    for s in analytical_signals:
        lines.append(_format_signal(s))
    lines.append("")
    lines.append("## PositionSignal")
    lines.append(_format_position_signal(position_signal))
    lines.append("")
    lines.append("## 6 Persona Signals")
    if persona_signals:
        for s in persona_signals:
            lines.append(_format_signal(s))
    else:
        lines.append("(empty — lite mode skipped persona slate)")
    lines.append("")
    lines.append("## User TickerConfig")
    lines.append(_format_config(config))
    lines.append("")
    lines.append("## Pre-computed Dissent")
    if dissent_persona_id is None:
        lines.append("no dissent (has_dissent: false; render dissent.has_dissent=false)")
    else:
        lines.append(
            f"dissenting_persona: {dissent_persona_id}\n"
            f"dissent_summary: {dissent_summary}"
        )
    return "\n".join(lines)


def _summarize_snapshot(snapshot: Snapshot) -> str:
    if snapshot.data_unavailable:
        return "data_unavailable=True"
    parts: list[str] = []
    if snapshot.prices is not None and not snapshot.prices.data_unavailable:
        if snapshot.prices.current_price is not None:
            parts.append(f"current_price={snapshot.prices.current_price}")
        if snapshot.prices.history:
            parts.append(f"history bars={len(snapshot.prices.history)}")
    if snapshot.fundamentals is not None and not snapshot.fundamentals.data_unavailable:
        f = snapshot.fundamentals
        if f.pe_ratio is not None:
            parts.append(f"P/E={f.pe_ratio}")
        if f.return_on_equity is not None:
            parts.append(f"ROE={f.return_on_equity}")
    return "; ".join(parts) if parts else "(no fundamentals/prices)"


def _format_signal(s: AgentSignal) -> str:
    return (
        f"- {s.analyst_id}: {s.verdict} (conf={s.confidence}) — "
        + ("; ".join(s.evidence[:3]) if s.evidence else "(no evidence)")
        + (" [data_unavailable]" if s.data_unavailable else "")
    )


def _format_position_signal(p: PositionSignal) -> str:
    if p.data_unavailable:
        return "[data_unavailable]"
    return (
        f"state={p.state}, consensus_score={p.consensus_score:.2f}, "
        f"action_hint={p.action_hint}, confidence={p.confidence}, "
        f"trend_regime={p.trend_regime}"
    )


def _format_config(c: TickerConfig) -> str:
    parts = [
        f"long_term_lens={c.long_term_lens}",
        f"short_term_focus={c.short_term_focus}",
    ]
    if c.thesis_price is not None:
        parts.append(f"thesis_price={c.thesis_price}")
    if c.notes:
        parts.append(f"notes={c.notes[:200]}")
    return "; ".join(parts)


def _data_unavailable_decision(
    ticker: str, computed_at: datetime, reason: str,
) -> TickerDecision:
    """Build a TickerDecision satisfying the data_unavailable invariant."""
    return TickerDecision(
        ticker=ticker,
        computed_at=computed_at,
        recommendation="hold",
        conviction="low",
        short_term=TimeframeBand(
            summary=f"data unavailable: {reason}",
            drivers=[],
            confidence=0,
        ),
        long_term=TimeframeBand(
            summary=f"data unavailable: {reason}",
            drivers=[],
            confidence=0,
        ),
        open_observation=f"synthesizer skipped: {reason}",
        dissent=DissentSection(),
        data_unavailable=True,
    )


def _decision_default_factory(
    ticker: str, computed_at: datetime, reason: str = "schema_failure",
) -> Callable[[], TickerDecision]:
    """Closure-bound default_factory for routine.llm_client.call_with_retry."""
    def factory() -> TickerDecision:
        return _data_unavailable_decision(ticker, computed_at, reason)
    return factory


async def synthesize(
    client: AsyncAnthropic,
    *,
    ticker: str,
    snapshot: Snapshot,
    config: TickerConfig,
    analytical_signals: list[AgentSignal],
    position_signal: PositionSignal,
    persona_signals: list[AgentSignal],
    computed_at: datetime,
) -> TickerDecision:
    """Single per-ticker synthesizer LLM call. Returns Pydantic-validated TickerDecision.

    Skip-path 1 (Snapshot.data_unavailable=True) — no LLM call; return the
    canonical data_unavailable TickerDecision.

    Skip-path 2 (lite_mode — empty persona_signals) — no LLM call; return
    a data_unavailable TickerDecision noting the skip reason.

    Otherwise: compute dissent in Python (Pattern #7), build user_context,
    fire 1 LLM call via call_with_retry, return parsed TickerDecision.
    """
    if snapshot.data_unavailable:
        return _data_unavailable_decision(
            ticker, computed_at, "snapshot data_unavailable=True",
        )
    if not persona_signals:
        return _data_unavailable_decision(
            ticker, computed_at, "lite_mode (no persona signals)",
        )

    dissent_id, dissent_summary = compute_dissent(persona_signals)

    system_prompt = load_synthesizer_prompt()
    user_context = build_synthesizer_user_context(
        ticker=ticker,
        snapshot=snapshot,
        config=config,
        analytical_signals=analytical_signals,
        position_signal=position_signal,
        persona_signals=persona_signals,
        dissent_persona_id=dissent_id,
        dissent_summary=dissent_summary,
    )

    return await call_with_retry(
        client,
        model=SYNTHESIZER_MODEL,
        system=system_prompt,
        user=user_context,
        output_format=TickerDecision,
        default_factory=_decision_default_factory(ticker, computed_at),
        max_tokens=SYNTHESIZER_MAX_TOKENS,
        context_label=f"synthesizer:{ticker}",
    )
```

<!-- ============================================================
     tests/synthesis/test_dissent.py (~250 LOC, ≥12 tests)
     ============================================================ -->

```python
"""Tests for synthesis.dissent.compute_dissent + module constants."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from analysts.signals import AgentSignal
from synthesis.dissent import (
    DISSENT_THRESHOLD,
    VERDICT_TO_DIRECTION,
    compute_dissent,
)


def _persona(
    analyst_id: str,
    verdict: str,
    confidence: int,
    evidence: list[str] | None = None,
    *, data_unavailable: bool = False,
    computed_at: datetime,
) -> AgentSignal:
    return AgentSignal(
        ticker="AAPL",
        analyst_id=analyst_id,
        computed_at=computed_at,
        verdict=verdict,
        confidence=confidence,
        evidence=evidence or [f"{analyst_id} reasoning"],
        data_unavailable=data_unavailable,
    )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

def test_dissent_threshold_is_30():
    assert DISSENT_THRESHOLD == 30


def test_verdict_to_direction_mapping():
    assert VERDICT_TO_DIRECTION == {
        "strong_bearish": -1,
        "bearish": -1,
        "neutral": 0,
        "bullish": 1,
        "strong_bullish": 1,
    }


# ---------------------------------------------------------------------------
# Scenario 1: no dissent
# ---------------------------------------------------------------------------

def test_no_dissent_all_bullish(frozen_now):
    signals = [
        _persona("buffett", "bullish", 70, computed_at=frozen_now),
        _persona("munger", "bullish", 80, computed_at=frozen_now),
        _persona("wood", "strong_bullish", 60, computed_at=frozen_now),
        _persona("burry", "bullish", 50, computed_at=frozen_now),
        _persona("lynch", "bullish", 65, computed_at=frozen_now),
        _persona("claude_analyst", "bullish", 55, computed_at=frozen_now),
    ]
    pid, summary = compute_dissent(signals)
    assert pid is None
    assert summary == ""


# ---------------------------------------------------------------------------
# Scenario 2: clear dissent
# ---------------------------------------------------------------------------

def test_clear_dissent_burry_bearish(frozen_now):
    signals = [
        _persona("buffett", "bullish", 70, computed_at=frozen_now),
        _persona("munger", "bullish", 70, computed_at=frozen_now),
        _persona("wood", "bullish", 70, computed_at=frozen_now),
        _persona("burry", "bearish", 80,
                 evidence=["hidden risk in margin compression"],
                 computed_at=frozen_now),
        _persona("lynch", "bullish", 70, computed_at=frozen_now),
        _persona("claude_analyst", "bullish", 70, computed_at=frozen_now),
    ]
    pid, summary = compute_dissent(signals)
    assert pid == "burry"
    assert "burry dissents" in summary
    assert "bearish" in summary
    assert "conf=80" in summary
    assert "hidden risk in margin compression" in summary


# ---------------------------------------------------------------------------
# Scenario 3: boundary at exactly 30 (inclusive)
# ---------------------------------------------------------------------------

def test_dissent_boundary_inclusive_at_30(frozen_now):
    signals = [
        _persona("buffett", "bullish", 50, computed_at=frozen_now),
        _persona("munger", "bullish", 50, computed_at=frozen_now),
        _persona("wood", "bullish", 50, computed_at=frozen_now),
        _persona("burry", "bearish", 30, computed_at=frozen_now),
        _persona("lynch", "bullish", 50, computed_at=frozen_now),
        _persona("claude_analyst", "bullish", 50, computed_at=frozen_now),
    ]
    pid, summary = compute_dissent(signals)
    assert pid == "burry"
    assert "conf=30" in summary


def test_dissent_boundary_exclusive_below_30(frozen_now):
    signals = [
        _persona("buffett", "bullish", 50, computed_at=frozen_now),
        _persona("munger", "bullish", 50, computed_at=frozen_now),
        _persona("wood", "bullish", 50, computed_at=frozen_now),
        _persona("burry", "bearish", 29, computed_at=frozen_now),
        _persona("lynch", "bullish", 50, computed_at=frozen_now),
        _persona("claude_analyst", "bullish", 50, computed_at=frozen_now),
    ]
    pid, summary = compute_dissent(signals)
    assert pid is None
    assert summary == ""


# ---------------------------------------------------------------------------
# Edge: <2 valid persona signals
# ---------------------------------------------------------------------------

def test_dissent_lt_2_valid_signals(frozen_now):
    signals = [
        _persona("buffett", "bullish", 70, computed_at=frozen_now),
    ] + [
        _persona(pid, "neutral", 0, data_unavailable=True, computed_at=frozen_now)
        for pid in ("munger", "wood", "burry", "lynch", "claude_analyst")
    ]
    pid, summary = compute_dissent(signals)
    assert pid is None
    assert summary == ""


def test_dissent_all_data_unavailable(frozen_now):
    signals = [
        _persona(pid, "neutral", 0, data_unavailable=True, computed_at=frozen_now)
        for pid in ("buffett", "munger", "wood", "burry", "lynch", "claude_analyst")
    ]
    pid, summary = compute_dissent(signals)
    assert pid is None
    assert summary == ""


# ---------------------------------------------------------------------------
# Edge: zero-sum direction_score
# ---------------------------------------------------------------------------

def test_dissent_zero_sum_direction(frozen_now):
    """3 bullish (+150) + 3 bearish (-150) = direction_score 0 → no clear majority."""
    signals = [
        _persona("buffett", "bullish", 50, computed_at=frozen_now),
        _persona("munger", "bullish", 50, computed_at=frozen_now),
        _persona("wood", "bullish", 50, computed_at=frozen_now),
        _persona("burry", "bearish", 50, computed_at=frozen_now),
        _persona("lynch", "bearish", 50, computed_at=frozen_now),
        _persona("claude_analyst", "bearish", 50, computed_at=frozen_now),
    ]
    pid, summary = compute_dissent(signals)
    assert pid is None
    assert summary == ""


# ---------------------------------------------------------------------------
# Edge: neutral personas don't count as dissent
# ---------------------------------------------------------------------------

def test_dissent_neutral_doesnt_count(frozen_now):
    """5 bullish + 1 neutral (high conf): neutral has direction=0, not opposite."""
    signals = [
        _persona("buffett", "bullish", 70, computed_at=frozen_now),
        _persona("munger", "bullish", 70, computed_at=frozen_now),
        _persona("wood", "bullish", 70, computed_at=frozen_now),
        _persona("burry", "neutral", 80, computed_at=frozen_now),
        _persona("lynch", "bullish", 70, computed_at=frozen_now),
        _persona("claude_analyst", "bullish", 70, computed_at=frozen_now),
    ]
    pid, summary = compute_dissent(signals)
    assert pid is None
    assert summary == ""


# ---------------------------------------------------------------------------
# Tie-break 1: confidence (highest wins)
# ---------------------------------------------------------------------------

def test_dissent_tie_break_by_confidence(frozen_now):
    """2 bearish dissenters at conf 40 vs 70 → conf=70 wins."""
    signals = [
        _persona("buffett", "bullish", 50, computed_at=frozen_now),
        _persona("munger", "bullish", 50, computed_at=frozen_now),
        _persona("wood", "bullish", 50, computed_at=frozen_now),
        _persona("burry", "bearish", 40, computed_at=frozen_now),
        _persona("lynch", "bullish", 50, computed_at=frozen_now),
        _persona("claude_analyst", "bearish", 70, computed_at=frozen_now),
    ]
    pid, summary = compute_dissent(signals)
    assert pid == "claude_analyst"
    assert "conf=70" in summary


# ---------------------------------------------------------------------------
# Tie-break 2: alphabetical (when confidence ties)
# ---------------------------------------------------------------------------

def test_dissent_tie_break_alphabetical_when_conf_ties(frozen_now):
    """2 bearish dissenters at conf 70 each: burry vs munger → burry alphabetical."""
    signals = [
        _persona("buffett", "bullish", 80, computed_at=frozen_now),
        _persona("munger", "bearish", 70, computed_at=frozen_now),
        _persona("wood", "bullish", 80, computed_at=frozen_now),
        _persona("burry", "bearish", 70, computed_at=frozen_now),
        _persona("lynch", "bullish", 80, computed_at=frozen_now),
        _persona("claude_analyst", "bullish", 80, computed_at=frozen_now),
    ]
    pid, summary = compute_dissent(signals)
    assert pid == "burry"  # burry < munger alphabetically


# ---------------------------------------------------------------------------
# Return shape contracts
# ---------------------------------------------------------------------------

def test_dissent_return_shape_no_dissent_is_tuple(frozen_now):
    signals = [
        _persona(pid, "bullish", 70, computed_at=frozen_now)
        for pid in ("buffett", "munger", "wood", "burry", "lynch", "claude_analyst")
    ]
    result = compute_dissent(signals)
    assert isinstance(result, tuple) and len(result) == 2
    assert result[0] is None
    assert isinstance(result[1], str)


def test_dissent_summary_truncated_at_500(frozen_now):
    long_evidence = ["x" * 200, "y" * 200, "z" * 200]  # joined with "; " → ≈600 chars
    signals = [
        _persona("buffett", "bullish", 70, computed_at=frozen_now),
        _persona("munger", "bullish", 70, computed_at=frozen_now),
        _persona("wood", "bullish", 70, computed_at=frozen_now),
        _persona("burry", "bearish", 80, evidence=long_evidence,
                 computed_at=frozen_now),
        _persona("lynch", "bullish", 70, computed_at=frozen_now),
        _persona("claude_analyst", "bullish", 70, computed_at=frozen_now),
    ]
    pid, summary = compute_dissent(signals)
    assert pid == "burry"
    assert len(summary) <= 500
```

<!-- ============================================================
     tests/synthesis/test_synthesizer.py (~300 LOC, ≥10 tests)
     ============================================================ -->

```python
"""Tests for synthesis.synthesizer.synthesize + helpers + prompt presence."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from analysts.signals import AgentSignal
from analysts.position_signal import PositionSignal
from analysts.schemas import TickerConfig
from analysts.data.snapshot import Snapshot
from synthesis.decision import (
    DissentSection, TickerDecision, TimeframeBand,
)


@pytest.fixture
def base_inputs(frozen_now):
    cfg = TickerConfig(ticker="AAPL", short_term_focus=True, long_term_lens="value",
                       thesis_price=200.0)
    snap = Snapshot(ticker="AAPL", fetched_at=frozen_now, data_unavailable=False)
    fund = AgentSignal(
        ticker="AAPL", analyst_id="fundamentals",
        computed_at=frozen_now, verdict="bullish", confidence=70,
        evidence=["ROE 22%"],
    )
    tech = AgentSignal(
        ticker="AAPL", analyst_id="technicals",
        computed_at=frozen_now, verdict="bullish", confidence=60,
        evidence=["MA20>MA50"],
    )
    nsen = AgentSignal(
        ticker="AAPL", analyst_id="news_sentiment",
        computed_at=frozen_now, verdict="bullish", confidence=50,
        evidence=["positive headlines"],
    )
    val = AgentSignal(
        ticker="AAPL", analyst_id="valuation",
        computed_at=frozen_now, verdict="neutral", confidence=50,
        evidence=["price near thesis"],
    )
    pose = PositionSignal(
        ticker="AAPL", computed_at=frozen_now,
        state="fair", consensus_score=0.05, confidence=60,
        action_hint="hold_position",
    )
    personas = [
        AgentSignal(ticker="AAPL", analyst_id=pid,
                    computed_at=frozen_now, verdict="bullish",
                    confidence=60, evidence=[f"{pid} bullish"])
        for pid in ("buffett", "munger", "wood", "burry", "lynch", "claude_analyst")
    ]
    return cfg, snap, [fund, tech, nsen, val], pose, personas


# ---------------------------------------------------------------------------
# Test 1: prompt file presence
# ---------------------------------------------------------------------------

def test_synthesizer_md_exists_and_nonempty():
    text = Path("prompts/synthesizer.md").read_text(encoding="utf-8")
    assert len(text.splitlines()) >= 150


def test_synthesizer_md_section_structure():
    text = Path("prompts/synthesizer.md").read_text(encoding="utf-8")
    assert "## Input Context" in text
    assert "## Task" in text
    assert "## Output Schema" in text


def test_synthesizer_md_priority_order_encoded():
    """The 3-layer priority order from Pattern #7 + 05-CONTEXT.md is in plain English."""
    text = Path("prompts/synthesizer.md").read_text(encoding="utf-8").lower()
    # Tactical layer mentions PositionSignal action_hint
    assert "action_hint" in text
    # Short-term layer mentions persona consensus
    assert "persona consensus" in text or "persona" in text
    # Long-term layer mentions valuation analyst + thesis_price
    assert "thesis_price" in text
    # Conviction band rules named
    assert "high" in text and "medium" in text and "low" in text


def test_synthesizer_md_dissent_rendering_instruction():
    """Synthesizer must be instructed to render PRE-COMPUTED dissent verbatim."""
    text = Path("prompts/synthesizer.md").read_text(encoding="utf-8").lower()
    assert "pre-computed" in text
    # Locked phrasing per 05-CONTEXT.md / 05-RESEARCH.md provenance
    assert "ground every conclusion in specific evidence" in text


def test_synthesizer_md_output_schema_names_fields():
    text = Path("prompts/synthesizer.md").read_text(encoding="utf-8")
    for field in (
        "ticker", "computed_at", "schema_version", "recommendation",
        "conviction", "short_term", "long_term", "open_observation",
        "dissent", "data_unavailable",
    ):
        assert field in text, f"synthesizer.md missing field name {field!r}"
    # 6 enum values:
    for v in ("add", "trim", "hold", "take_profits", "buy", "avoid"):
        assert v in text


# ---------------------------------------------------------------------------
# Test 2: load_synthesizer_prompt cache
# ---------------------------------------------------------------------------

def test_load_synthesizer_prompt_caches():
    from synthesis.synthesizer import load_synthesizer_prompt
    load_synthesizer_prompt.cache_clear()
    a = load_synthesizer_prompt()
    b = load_synthesizer_prompt()
    assert a is b
    assert load_synthesizer_prompt.cache_info().hits >= 1


# ---------------------------------------------------------------------------
# Test 3: build_synthesizer_user_context determinism + content
# ---------------------------------------------------------------------------

def test_build_synthesizer_user_context_deterministic(base_inputs, frozen_now):
    from synthesis.synthesizer import build_synthesizer_user_context
    cfg, snap, analytical, pose, personas = base_inputs
    a = build_synthesizer_user_context(
        ticker="AAPL", snapshot=snap, config=cfg,
        analytical_signals=analytical, position_signal=pose,
        persona_signals=personas, dissent_persona_id=None, dissent_summary="",
    )
    b = build_synthesizer_user_context(
        ticker="AAPL", snapshot=snap, config=cfg,
        analytical_signals=analytical, position_signal=pose,
        persona_signals=personas, dissent_persona_id=None, dissent_summary="",
    )
    assert a == b


def test_build_synthesizer_user_context_dissent_block_always_present(
    base_inputs, frozen_now,
):
    """The dissent block is always emitted — 'no dissent' literal when none."""
    from synthesis.synthesizer import build_synthesizer_user_context
    cfg, snap, analytical, pose, personas = base_inputs

    no_dissent_ctx = build_synthesizer_user_context(
        ticker="AAPL", snapshot=snap, config=cfg,
        analytical_signals=analytical, position_signal=pose,
        persona_signals=personas, dissent_persona_id=None, dissent_summary="",
    )
    assert "Pre-computed Dissent" in no_dissent_ctx
    assert "no dissent" in no_dissent_ctx

    has_dissent_ctx = build_synthesizer_user_context(
        ticker="AAPL", snapshot=snap, config=cfg,
        analytical_signals=analytical, position_signal=pose,
        persona_signals=personas,
        dissent_persona_id="burry",
        dissent_summary="burry dissents (bearish, conf=80): hidden risk",
    )
    assert "burry" in has_dissent_ctx
    assert "hidden risk" in has_dissent_ctx


def test_build_synthesizer_user_context_includes_all_signals(
    base_inputs, frozen_now,
):
    from synthesis.synthesizer import build_synthesizer_user_context
    cfg, snap, analytical, pose, personas = base_inputs
    ctx = build_synthesizer_user_context(
        ticker="AAPL", snapshot=snap, config=cfg,
        analytical_signals=analytical, position_signal=pose,
        persona_signals=personas, dissent_persona_id=None, dissent_summary="",
    )
    # 4 analytical
    for aid in ("fundamentals", "technicals", "news_sentiment", "valuation"):
        assert aid in ctx
    # PositionSignal
    assert "fair" in ctx
    assert "hold_position" in ctx
    # 6 personas
    for pid in ("buffett", "munger", "wood", "burry", "lynch", "claude_analyst"):
        assert pid in ctx
    # config
    assert "value" in ctx  # long_term_lens
    assert "thesis_price=200.0" in ctx or "thesis_price=200" in ctx


# ---------------------------------------------------------------------------
# Test 4-5: synthesize skip-paths (Snapshot data_unavailable + lite-mode)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_synthesize_snapshot_data_unavailable_skips_llm(
    mock_anthropic_client, frozen_now, base_inputs,
):
    from synthesis.synthesizer import synthesize
    cfg, _, analytical, pose, personas = base_inputs
    dark_snap = Snapshot(
        ticker="AAPL", fetched_at=frozen_now, data_unavailable=True,
    )
    result = await synthesize(
        mock_anthropic_client, ticker="AAPL", snapshot=dark_snap,
        config=cfg, analytical_signals=analytical, position_signal=pose,
        persona_signals=personas, computed_at=frozen_now,
    )
    assert result.data_unavailable is True
    assert result.recommendation == "hold"
    assert result.conviction == "low"
    assert "snapshot data_unavailable" in result.open_observation.lower() or \
           "snapshot data_unavailable" in result.short_term.summary.lower()
    # LLM was NOT called
    assert mock_anthropic_client.messages.calls == []


@pytest.mark.asyncio
async def test_synthesize_lite_mode_empty_personas_skips_llm(
    mock_anthropic_client, frozen_now, base_inputs,
):
    from synthesis.synthesizer import synthesize
    cfg, snap, analytical, pose, _ = base_inputs
    result = await synthesize(
        mock_anthropic_client, ticker="AAPL", snapshot=snap,
        config=cfg, analytical_signals=analytical, position_signal=pose,
        persona_signals=[], computed_at=frozen_now,
    )
    assert result.data_unavailable is True
    assert result.recommendation == "hold"
    assert result.conviction == "low"
    assert mock_anthropic_client.messages.calls == []


# ---------------------------------------------------------------------------
# Test 6: synthesize happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_synthesize_happy_path_returns_llm_decision(
    mock_anthropic_client, frozen_now, base_inputs,
):
    from synthesis.synthesizer import (
        synthesize, SYNTHESIZER_MODEL, SYNTHESIZER_MAX_TOKENS,
    )
    cfg, snap, analytical, pose, personas = base_inputs

    expected = TickerDecision(
        ticker="AAPL", computed_at=frozen_now,
        recommendation="add", conviction="high",
        short_term=TimeframeBand(summary="bullish ST", drivers=["a"], confidence=80),
        long_term=TimeframeBand(summary="bullish LT", drivers=["b"], confidence=70),
        open_observation="claude analyst observation",
        dissent=DissentSection(),
    )
    mock_anthropic_client.messages.queue_response(expected)

    result = await synthesize(
        mock_anthropic_client, ticker="AAPL", snapshot=snap,
        config=cfg, analytical_signals=analytical, position_signal=pose,
        persona_signals=personas, computed_at=frozen_now,
    )
    assert result is expected
    calls = mock_anthropic_client.messages.calls
    assert len(calls) == 1
    assert calls[0]["model"] == SYNTHESIZER_MODEL
    assert calls[0]["max_tokens"] == SYNTHESIZER_MAX_TOKENS
    assert calls[0]["output_format"] is TickerDecision
    # System prompt is the synthesizer.md content
    assert "Input Context" in calls[0]["system"]
    # User context contains the dissent block (no dissent in this case — all bullish)
    assert "no dissent" in calls[0]["user"]


# ---------------------------------------------------------------------------
# Test 7: 6 recommendation paths (parametrized)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("recommendation", [
    "add", "trim", "hold", "take_profits", "buy", "avoid",
])
async def test_synthesize_six_recommendation_paths(
    mock_anthropic_client, frozen_now, base_inputs, recommendation,
):
    from synthesis.synthesizer import synthesize
    cfg, snap, analytical, pose, personas = base_inputs
    expected = TickerDecision(
        ticker="AAPL", computed_at=frozen_now,
        recommendation=recommendation,
        conviction="medium",
        short_term=TimeframeBand(summary="x", drivers=[], confidence=50),
        long_term=TimeframeBand(summary="y", drivers=[], confidence=50),
        dissent=DissentSection(),
    )
    mock_anthropic_client.messages.queue_response(expected)
    result = await synthesize(
        mock_anthropic_client, ticker="AAPL", snapshot=snap,
        config=cfg, analytical_signals=analytical, position_signal=pose,
        persona_signals=personas, computed_at=frozen_now,
    )
    assert result.recommendation == recommendation


# ---------------------------------------------------------------------------
# Test 8: LLM exhaustion → default factory
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_synthesize_llm_exhaustion_returns_default_factory(
    mock_anthropic_client, frozen_now, base_inputs, isolated_failure_log,
):
    from synthesis.synthesizer import synthesize
    from routine.llm_client import DEFAULT_MAX_RETRIES
    cfg, snap, analytical, pose, personas = base_inputs

    # Forge ValidationError
    try:
        TickerDecision(
            ticker="!!!", computed_at=datetime.now(timezone.utc),
            recommendation="hold", conviction="low",
            short_term=TimeframeBand(summary="x", drivers=[], confidence=0),
            long_term=TimeframeBand(summary="y", drivers=[], confidence=0),
            dissent=DissentSection(),
        )
    except ValidationError as exc:
        ve = exc

    for _ in range(DEFAULT_MAX_RETRIES):
        mock_anthropic_client.messages.queue_exception(ve)

    result = await synthesize(
        mock_anthropic_client, ticker="AAPL", snapshot=snap,
        config=cfg, analytical_signals=analytical, position_signal=pose,
        persona_signals=personas, computed_at=frozen_now,
    )
    assert result.data_unavailable is True
    assert result.recommendation == "hold"
    assert result.conviction == "low"


# ---------------------------------------------------------------------------
# Test 9: Python dissent computed BEFORE LLM call
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_synthesize_dissent_pre_computed_in_user_context(
    mock_anthropic_client, frozen_now, base_inputs,
):
    """Locked: dissent computed in Python (Pattern #7); LLM receives pre-computed string."""
    from synthesis.synthesizer import synthesize
    cfg, snap, analytical, pose, _ = base_inputs

    # Construct a dissent scenario: 5 bullish + 1 burry-bearish-conf-80
    dissent_personas = [
        AgentSignal(ticker="AAPL", analyst_id=pid,
                    computed_at=frozen_now, verdict="bullish",
                    confidence=70, evidence=[f"{pid} bullish"])
        for pid in ("buffett", "munger", "wood", "lynch", "claude_analyst")
    ]
    dissent_personas.append(AgentSignal(
        ticker="AAPL", analyst_id="burry",
        computed_at=frozen_now, verdict="bearish", confidence=80,
        evidence=["hidden risk"],
    ))

    expected = TickerDecision(
        ticker="AAPL", computed_at=frozen_now,
        recommendation="hold", conviction="medium",
        short_term=TimeframeBand(summary="x", drivers=[], confidence=50),
        long_term=TimeframeBand(summary="y", drivers=[], confidence=50),
        dissent=DissentSection(
            has_dissent=True, dissenting_persona="burry",
            dissent_summary="rendered",
        ),
    )
    mock_anthropic_client.messages.queue_response(expected)

    await synthesize(
        mock_anthropic_client, ticker="AAPL", snapshot=snap,
        config=cfg, analytical_signals=analytical, position_signal=pose,
        persona_signals=dissent_personas, computed_at=frozen_now,
    )

    user_msg = mock_anthropic_client.messages.calls[0]["user"]
    # The pre-computed dissent IS in the user context — synthesizer prompt
    # never has to compute dissent itself.
    assert "burry" in user_msg
    assert "dissents" in user_msg
    assert "hidden risk" in user_msg


# ---------------------------------------------------------------------------
# Test 10: provenance per INFRA-07
# ---------------------------------------------------------------------------

def test_synthesizer_provenance_references_tauricresearch():
    src = Path("synthesis/synthesizer.py").read_text(encoding="utf-8")
    assert "TauricResearch/TradingAgents" in src
    assert "tradingagents/agents/" in src
```
</implementation_sketch>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: synthesis/dissent.py + ≥12 tests (RED → GREEN)</name>
  <files>synthesis/dissent.py, tests/synthesis/test_dissent.py</files>
  <behavior>
    Pure-function dissent computation per LLM-07 + Pattern #7. No LLM dependency. Uses VERDICT_TO_DIRECTION map + DISSENT_THRESHOLD=30 (boundary inclusive). Returns (None, "") on degenerate cases (<2 valid; direction_score==0; no dissenter ≥30). Tie-break: highest confidence first; alphabetical analyst_id second.

    Tests in tests/synthesis/test_dissent.py (≥12):
    - 2 module-constant locks (DISSENT_THRESHOLD == 30; VERDICT_TO_DIRECTION exact 5-key map).
    - test_no_dissent_all_bullish: 6 all-bullish → (None, '').
    - test_clear_dissent_burry_bearish: 5 bullish + 1 burry-bearish-conf-80 → ('burry', summary mentioning bearish + conf=80 + 'hidden risk').
    - test_dissent_boundary_inclusive_at_30: 5 bullish + 1 bearish-conf-30 → triggers.
    - test_dissent_boundary_exclusive_below_30: 5 bullish + 1 bearish-conf-29 → (None, '').
    - test_dissent_lt_2_valid_signals: 1 valid + 5 data_unavailable → (None, '').
    - test_dissent_all_data_unavailable: 6 data_unavailable → (None, '').
    - test_dissent_zero_sum_direction: 3 bullish-conf-50 + 3 bearish-conf-50 → direction_score=0 → (None, '').
    - test_dissent_neutral_doesnt_count: 5 bullish + 1 neutral-conf-80 → no dissent (neutral has direction=0).
    - test_dissent_tie_break_by_confidence: 2 bearish dissenters at conf 40 vs 70 → conf=70 wins.
    - test_dissent_tie_break_alphabetical_when_conf_ties: burry vs munger at same conf=70 → burry wins.
    - test_dissent_return_shape: tuple of (Optional[str], str).
    - test_dissent_summary_truncated_at_500: long evidence → summary ≤500 chars.

    Total: ≥12 tests; coverage ≥90% line / ≥85% branch on synthesis/dissent.py.
  </behavior>
  <action>
    RED:
    1. Write `tests/synthesis/test_dissent.py` per implementation_sketch — ≥12 tests. Imports include `from synthesis.dissent import compute_dissent, DISSENT_THRESHOLD, VERDICT_TO_DIRECTION` and helpers.
    2. Run `poetry run pytest tests/synthesis/test_dissent.py -x -q` → ImportError on `synthesis.dissent` (module does not exist).
    3. Commit (RED): `test(05-05): add failing tests for synthesis.dissent.compute_dissent (LLM-07; ≥12 tests covering 3 main scenarios + tie-breaks + edge cases)`.

    GREEN:
    4. Implement `synthesis/dissent.py` per implementation_sketch verbatim:
       - Provenance docstring (~25 lines) referencing Pattern #7 + LLM-07 + the 3 reasons (determinism, no hallucination, tie-break specificity) + the signed-weighted-vote anti-pattern note.
       - Imports: `from __future__ import annotations`; `from typing import Optional`; `from analysts.signals import AgentSignal, Verdict`.
       - Module constants: `VERDICT_TO_DIRECTION` (5-key dict), `DISSENT_THRESHOLD = 30`.
       - `compute_dissent(persona_signals)` function — filters valid (not data_unavailable AND confidence > 0); checks len < 2; computes direction_score = sum(VERDICT_TO_DIRECTION[s.verdict] * s.confidence for s in valid); checks zero-sum; finds dissenters on opposite direction with confidence ≥ DISSENT_THRESHOLD; tie-breaks via `max(dissenters, key=lambda s: (s.confidence, _neg_alpha(s.analyst_id)))`; builds summary and truncates to 500.
       - `_neg_alpha` helper — tuple of negated codepoints so `max` picks alphabetically-first id.
    5. Run `poetry run pytest tests/synthesis/test_dissent.py -v` → all ≥12 tests GREEN.
    6. Coverage check: `poetry run pytest --cov=synthesis.dissent --cov-branch tests/synthesis/test_dissent.py` → ≥90% line / ≥85% branch.
    7. Phase 1-4 + Wave 0-3 regression: `poetry run pytest -x -q` → all existing tests still GREEN.
    8. Commit (GREEN): `feat(05-05): synthesis.dissent.compute_dissent — Python-computed dissent rule with signed-weighted-vote majority + ≥30-confidence opposite-direction trigger + tie-break (LLM-07; Pattern #7)`.
  </action>
  <verify>
    <automated>poetry run pytest tests/synthesis/test_dissent.py -v && poetry run pytest --cov=synthesis.dissent --cov-branch tests/synthesis/test_dissent.py && poetry run pytest -x -q && python -c "from synthesis.dissent import DISSENT_THRESHOLD, VERDICT_TO_DIRECTION, compute_dissent; assert DISSENT_THRESHOLD == 30; assert len(VERDICT_TO_DIRECTION) == 5; print('OK')"</automated>
  </verify>
  <done>synthesis/dissent.py shipped (~80 LOC) with VERDICT_TO_DIRECTION + DISSENT_THRESHOLD=30 module constants + compute_dissent function (signed-weighted-vote majority direction + opposite-direction-30+-confidence trigger + tie-break by confidence-then-alphabetical-analyst_id) + _neg_alpha helper; 12+ tests in tests/synthesis/test_dissent.py all GREEN (3 main scenarios + boundary inclusive/exclusive at 30 + lt-2-valid + zero-sum + neutral-doesnt-count + 2 tie-break variants + return-shape + truncation); coverage 90%+ line / 85%+ branch on synthesis/dissent.py; full repo regression GREEN; both commits (RED + GREEN) landed.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: prompts/synthesizer.md + synthesis/synthesizer.py + 10+ tests (RED -> GREEN)</name>
  <files>prompts/synthesizer.md, synthesis/synthesizer.py, tests/synthesis/test_synthesizer.py</files>
  <behavior>
    Single TDD task — the synthesizer markdown prompt + the synthesizer module + tests land together because they are co-dependent: tests assert prompt content via load_synthesizer_prompt; the synthesizer module reads the prompt at call time; the prompt encodes the locked recommendation priority order + dissent-rendering instruction.

    PRE-WORK: tests/synthesis/test_synthesizer.py imports mock_anthropic_client and isolated_failure_log fixtures from tests/routine/conftest.py. These fixtures live in tests/routine/conftest.py (Wave 2 / 05-03), but tests/synthesis/ is a sibling package — pytest does NOT auto-discover sibling-package conftests. SOLUTION: extend tests/conftest.py (root-level conftest, already extended in 05-02 with frozen_now) to ALSO export the mock_anthropic_client + isolated_failure_log fixtures (lift the implementation; do not duplicate the class definitions — import them from tests.routine.conftest). Alternatively, create tests/synthesis/conftest.py that re-imports.

    Per implementation_sketch above (verbatim):
    - prompts/synthesizer.md (~180 lines): 4 sections (Input Context / Task / Output Schema) + data_unavailable handling subsection. Encodes recommendation priority order in plain English (3 layers: tactical -> short-term -> long-term + default fallback). Conviction band rule (5+ agree + no dissent -> high; 3-4 agree OR mild dissent -> medium; 2 or fewer agree OR non-empty dissent -> low). short_term + long_term TimeframeBand instructions. Dissent rendering instruction (synthesizer renders pre-computed verbatim; does NOT compute). Output schema names all 10 TickerDecision fields + 6 DecisionRecommendation enum values + 3 ConvictionBand values. Provenance phrase: "ground every conclusion in specific evidence" (lifted from TauricResearch/TradingAgents portfolio_manager.py).
    - synthesis/synthesizer.py (~150 LOC):
      * Provenance docstring (~30 lines) referencing TauricResearch/TradingAgents/tradingagents/agents/managers/{portfolio_manager.py, research_manager.py} + 4 modifications.
      * Module constants: SYNTHESIZER_PROMPT_PATH=Path('prompts/synthesizer.md'); SYNTHESIZER_MODEL='claude-opus-4-7'; SYNTHESIZER_MAX_TOKENS=4000.
      * @functools.lru_cache(maxsize=2) def load_synthesizer_prompt() -> str — reads file; raises FileNotFoundError on missing.
      * build_synthesizer_user_context(...) — returns deterministic string with all 6 sections (Ticker, Snapshot Summary, 4 Analytical Signals, PositionSignal, 6 Persona Signals, User TickerConfig, Pre-computed Dissent — block ALWAYS present).
      * 4 small private formatters (_summarize_snapshot, _format_signal, _format_position_signal, _format_config).
      * _data_unavailable_decision(ticker, computed_at, reason) -> TickerDecision — builds canonical TickerDecision satisfying the schema invariant.
      * _decision_default_factory(ticker, computed_at, reason) — closure-bound default for call_with_retry.
      * async def synthesize(...) — 2 skip paths (Snapshot.data_unavailable + empty persona_signals lite-mode); compute_dissent(); load_synthesizer_prompt(); build_synthesizer_user_context(); call_with_retry(model='claude-opus-4-7', output_format=TickerDecision, default_factory=_decision_default_factory).

    Tests in tests/synthesis/test_synthesizer.py (~10 tests):
    - 5 prompt-file tests: file exists + 150+ lines; section structure; priority order encoded; dissent rendering instruction; Output Schema names all 10 fields + 6 recommendation values.
    - 1 load_synthesizer_prompt cache test.
    - 3 build_synthesizer_user_context tests: determinism; dissent block always present ("no dissent" literal when none + persona_id verbatim when has dissent); includes all 11 signals + config.
    - 2 synthesize skip-path tests: Snapshot.data_unavailable=True -> no LLM call + canonical decision; lite-mode (empty persona_signals) -> no LLM call + canonical decision.
    - 1 synthesize happy-path test: mock returns valid TickerDecision; asserts exactly 1 call with model='claude-opus-4-7' + max_tokens=4000 + output_format=TickerDecision; user_context contains 'no dissent' (since all bullish).
    - 1 synthesize parametrized 6-recommendation test (parametrize over 6 enum values).
    - 1 synthesize LLM-exhaustion test: 2 ValidationErrors queued -> result is default-factory.
    - 1 synthesize Python-dissent-pre-computed test: 5 bullish + 1 burry-bearish-conf-80 -> user_context contains "burry" + "dissents" + the burry evidence string (proves dissent computed in Python BEFORE LLM call).
    - 1 provenance test.

    Total: 10+ distinct tests (parametrized 6-recommendation expands to ~15 instances).
  </behavior>
  <action>
    PRE-WORK: ensure mock_anthropic_client + isolated_failure_log fixtures are visible from tests/synthesis/.
    0. Check tests/conftest.py. If frozen_now exists but mock fixtures dont, EXTEND tests/conftest.py to also import + re-export the fixtures from tests.routine.conftest:

       Add at end of tests/conftest.py:

       # Re-export Wave 2 (05-03) fixtures so tests/synthesis/ can use them.
       from tests.routine.conftest import (  # noqa: F401
           MockAnthropicClient,
           MockMessages,
           mock_anthropic_client,
           isolated_failure_log,
       )

       Verify: poetry run pytest tests/synthesis/ -x -q --collect-only shows test discovery works.

       ALTERNATIVELY: create tests/synthesis/conftest.py with the same re-export. Either approach works; root-level is preferred so Wave 5 (05-06) tests/routine/test_entrypoint.py inherits the fixtures uniformly.

    RED:
    1. Write tests/synthesis/test_synthesizer.py per implementation_sketch — 10+ tests with parametrization expansion. Imports include from synthesis.synthesizer import (synthesize, load_synthesizer_prompt, build_synthesizer_user_context, SYNTHESIZER_MODEL, SYNTHESIZER_MAX_TOKENS) and the fixtures.
    2. Run poetry run pytest tests/synthesis/test_synthesizer.py -x -q -> expect failures: (a) prompt-file tests fail because Wave 0 stub is <150 lines and missing the priority-order content; (b) ImportError on synthesis.synthesizer.
    3. Commit (RED): test(05-05): add failing tests for synthesis.synthesizer + prompts/synthesizer.md content (LLM-06; 10+ tests covering prompt content + skip paths + 6 recommendation paths + dissent-pre-computation + provenance).

    GREEN — synthesizer markdown prompt FIRST so prompt-file tests can pass before the module exists:
    4. Replace prompts/synthesizer.md with the full content per implementation_sketch (150+ lines). Critical content:
       - 4 main sections: ## Input Context, ## Task, ## Output Schema + data_unavailable handling subsection.
       - Recommendation priority order with 3 layers (tactical -> short-term -> long-term + default fallback) named explicitly with PositionSignal.action_hint + persona consensus + thesis_price.
       - Conviction band rule (high / medium / low with the count + dissent thresholds).
       - short_term and long_term TimeframeBand instructions.
       - Dissent rendering instruction ("PRE-COMPUTED"; render verbatim; do NOT compute).
       - Output Schema lists all 10 TickerDecision fields + 6 DecisionRecommendation enum values + 3 ConvictionBand values.
       - Locked phrase: "ground every conclusion in specific evidence" (TauricResearch/TradingAgents provenance).

    GREEN — synthesizer module:
    5. Implement synthesis/synthesizer.py per implementation_sketch (~150 LOC):
       - Provenance docstring referencing TauricResearch/TradingAgents/tradingagents/agents/managers/{portfolio_manager.py, research_manager.py} + 4 modifications.
       - Imports: from __future__ import annotations; stdlib (functools, datetime, pathlib, typing); from anthropic import AsyncAnthropic; project schemas (Snapshot, PositionSignal, TickerConfig, AgentSignal); from routine.llm_client import call_with_retry; from synthesis.decision import (DissentSection, TickerDecision, TimeframeBand); from synthesis.dissent import compute_dissent.
       - 3 module constants: SYNTHESIZER_PROMPT_PATH, SYNTHESIZER_MODEL, SYNTHESIZER_MAX_TOKENS.
       - load_synthesizer_prompt with lru_cache(maxsize=2) + FileNotFoundError on missing.
       - build_synthesizer_user_context + 4 private formatters.
       - _data_unavailable_decision + _decision_default_factory (satisfy the @model_validator invariant from 05-02).
       - async def synthesize — 2 skip paths first, then dissent computation + user_context build + call_with_retry.
    6. Run poetry run pytest tests/synthesis/test_synthesizer.py -v -> all 10+ tests (~15 parametrized instances) GREEN.
    7. Coverage check: poetry run pytest --cov=synthesis.synthesizer --cov-branch tests/synthesis/test_synthesizer.py -> 90%+ line / 85%+ branch.
    8. Phase 1-4 + Wave 0-3 + Task 1 regression: poetry run pytest -x -q -> all existing tests still GREEN.
    9. Sanity grep — provenance: grep -n "TauricResearch/TradingAgents" synthesis/synthesizer.py returns 1+ match; grep -n "tradingagents/agents/" synthesis/synthesizer.py returns 1+ match.
    10. Sanity grep — locked phrase: grep -n "ground every conclusion in specific evidence" prompts/synthesizer.md returns 1+ match.
    11. Sanity prompt linecount check via Python.
    12. Commit (GREEN): feat(05-05): synthesis.synthesizer.synthesize — single per-ticker LLM call producing TickerDecision; prompts/synthesizer.md full content (Pattern #7) — Python-computed dissent BEFORE LLM call (LLM-06 + LLM-07).
  </action>
  <verify>
    <automated>poetry run pytest tests/synthesis/test_synthesizer.py -v && poetry run pytest --cov=synthesis.synthesizer --cov-branch tests/synthesis/test_synthesizer.py && poetry run pytest -x -q && grep -n "TauricResearch/TradingAgents" synthesis/synthesizer.py && grep -n "tradingagents/agents/" synthesis/synthesizer.py && grep -n "ground every conclusion in specific evidence" prompts/synthesizer.md && python -c "from pathlib import Path; n = len(Path('prompts/synthesizer.md').read_text(encoding='utf-8').splitlines()); assert n >= 150, f'too short: {n}'; print('OK lines:', n)" && python -c "from synthesis.synthesizer import SYNTHESIZER_MODEL, SYNTHESIZER_MAX_TOKENS, load_synthesizer_prompt; assert SYNTHESIZER_MODEL == 'claude-opus-4-7'; assert SYNTHESIZER_MAX_TOKENS == 4000; load_synthesizer_prompt.cache_clear(); txt = load_synthesizer_prompt(); assert 'Input Context' in txt; print('OK')"</automated>
  </verify>
  <done>prompts/synthesizer.md fully populated (150+ lines, replacing Wave 0 stub; 4 sections + data_unavailable handling; 3-layer recommendation priority order; conviction band rule; dual-timeframe instructions; dissent-rendering instruction; locked TauricResearch "ground every conclusion in specific evidence" phrase; Output Schema names all 10 TickerDecision fields + 6 recommendation enum + 3 conviction enum); synthesis/synthesizer.py shipped (~150 LOC) with 3 module constants + load_synthesizer_prompt (lru_cache) + build_synthesizer_user_context (deterministic, dissent block ALWAYS present) + 4 formatters + _data_unavailable_decision + _decision_default_factory + async synthesize (2 skip paths + dissent-in-Python BEFORE LLM call); 10+ tests in tests/synthesis/test_synthesizer.py all GREEN (5 prompt-content + 1 cache + 3 user-context + 2 skip paths + 1 happy path + 1 parametrized 6-recommendation + 1 LLM-exhaustion + 1 dissent-pre-computed + 1 provenance); coverage 90%+ line / 85%+ branch on synthesis/synthesizer.py; provenance per INFRA-07 grep passes; Phase 1-4 + Wave 0-3 + Task 1 regression GREEN; both commits (RED + GREEN) landed.</done>
</task>

</tasks>

<verification>
- 2 tasks, 4 commits (RED + GREEN per task). TDD discipline preserved.
- Coverage gate: 90%+ line / 85%+ branch on synthesis/dissent.py AND synthesis/synthesizer.py.
- Phase 1-4 + Wave 0 + Wave 1 + Wave 2 + Wave 3 regression invariant: existing tests stay GREEN. The 2 new modules + the synthesizer.md content drop are additive only — nothing imports synthesize yet (Wave 5 entrypoint will).
- synthesis/dissent.py exports compute_dissent + VERDICT_TO_DIRECTION (5-key map: strong_bullish/bullish=+1; neutral=0; bearish/strong_bearish=-1) + DISSENT_THRESHOLD=30 (boundary inclusive per LLM-07).
- compute_dissent uses signed-weighted-vote majority direction (Pattern #7); rejects mode-based majority per Anti-Pattern at 05-RESEARCH.md line 1189; tie-breaks via max(dissenters, key=(confidence, _neg_alpha(analyst_id))) so highest-confidence wins; alphabetical-first analyst_id breaks ties.
- 3 main scenarios + 9 edge/boundary tests covered: no dissent (all bullish); clear dissent (5 bullish + 1 burry-bearish-conf-80); boundary inclusive at conf=30; boundary exclusive at conf=29; <2 valid; all data_unavailable; zero-sum direction_score; neutral doesnt count; tie-break by confidence; tie-break alphabetical; return-shape contract; summary truncation at 500.
- synthesis/synthesizer.py exports synthesize (async) + load_synthesizer_prompt (lru_cache) + build_synthesizer_user_context + 3 module constants (SYNTHESIZER_PROMPT_PATH, SYNTHESIZER_MODEL='claude-opus-4-7', SYNTHESIZER_MAX_TOKENS=4000).
- synthesize 2 skip paths: Snapshot.data_unavailable=True OR empty persona_signals (lite-mode) -> returns _data_unavailable_decision WITHOUT calling LLM.
- synthesize happy path: compute_dissent -> build_synthesizer_user_context (with pre-computed dissent in user message) -> call_with_retry(model='claude-opus-4-7', output_format=TickerDecision, default_factory=_decision_default_factory). Pattern #7 dissent-in-Python lock confirmed.
- prompts/synthesizer.md content (150+ lines) encodes: 3-layer recommendation priority order in plain English (tactical -> short-term -> long-term + default fallback); conviction band rule; dual-timeframe instructions; dissent rendering instruction (pre-computed; render verbatim; do NOT compute); locked TauricResearch phrase "ground every conclusion in specific evidence"; Output Schema lists all 10 TickerDecision fields + 6 DecisionRecommendation enum values + 3 ConvictionBand values.
- _data_unavailable_decision satisfies the schema invariant from 05-02 (recommendation='hold' + conviction='low' when data_unavailable=True).
- Provenance per INFRA-07: synthesis/synthesizer.py docstring contains TauricResearch/TradingAgents + tradingagents/agents/; references portfolio_manager.py + research_manager.py + 4 modifications.
- Wave 5 (05-06 entrypoint) unblocked: synthesize is the per-ticker decision producer the routines _run_one_ticker calls after run_persona_slate returns the 6 AgentSignals.
- LLM-06 + LLM-07 closed (LLM-08 closes in Wave 5 with _status.json).

## Cross-Scope Risks

_vault_status=budget_exhausted; re-run /gmd:plan-phase --replan after vault-maintain_
</verification>

<success_criteria>
1. prompts/synthesizer.md fully populated (150+ lines) replacing Wave 0 stub; contains the 4 locked sections + data_unavailable handling.
2. prompts/synthesizer.md Task section encodes 3-layer recommendation priority order + conviction band rule + dual-timeframe instructions + dissent rendering instruction (pre-computed verbatim).
3. prompts/synthesizer.md contains literal "ground every conclusion in specific evidence" (TauricResearch provenance).
4. prompts/synthesizer.md Output Schema names all 10 TickerDecision fields + 6 DecisionRecommendation enum values + 3 ConvictionBand values.
5. synthesis/dissent.py exports compute_dissent + VERDICT_TO_DIRECTION (exact 5-key map) + DISSENT_THRESHOLD=30.
6. compute_dissent uses signed-weighted-vote majority + tie-break (confidence first; alphabetical analyst_id second).
7. 12+ tests in tests/synthesis/test_dissent.py all GREEN.
8. synthesis/synthesizer.py exports synthesize (async) + load_synthesizer_prompt (lru_cache) + build_synthesizer_user_context + 3 module constants.
9. synthesize has 2 skip paths (Snapshot.data_unavailable + lite-mode empty persona_signals) that return canonical _data_unavailable_decision WITHOUT calling LLM.
10. synthesize calls call_with_retry with model='claude-opus-4-7', max_tokens=4000, output_format=TickerDecision; user_context contains pre-computed dissent block ALWAYS (Pattern #7).
11. 10+ tests in tests/synthesis/test_synthesizer.py all GREEN (~15 parametrized instances).
12. Coverage 90%+ line / 85%+ branch on both new modules.
13. Provenance per INFRA-07: synthesis/synthesizer.py docstring contains TauricResearch/TradingAgents + tradingagents/agents/.
14. tests/conftest.py extended (or tests/synthesis/conftest.py created) so mock_anthropic_client + isolated_failure_log fixtures are inherited by tests/synthesis/.
15. Full repo regression GREEN.
16. LLM-06 + LLM-07 closed (REQUIREMENTS.md update happens in Wave 5 / 05-06 closeout).
17. Wave 5 (05-06 entrypoint) unblocked.
</success_criteria>

<output>
After completion, create .planning/phases/05-claude-routine-wiring/05-05-SUMMARY.md summarizing the 4 commits, naming the dissent rule (signed-weighted-vote majority + 30+ threshold + tie-break by confidence-then-alphabetical), the synthesizer triad (prompt + module + dissent), the 2 skip paths (Snapshot.data_unavailable + lite-mode empty persona_signals), the Pattern #7 dissent-in-Python lock, and the LLM-06 + LLM-07 closure. Reference 05-06 (entrypoint) as immediate downstream Wave 5 consumer.

Update .planning/STATE.md Recent Decisions with a 05-05 entry naming: synthesis/dissent.py + synthesis/synthesizer.py + prompts/synthesizer.md shipped; Pattern #7 dissent-in-Python lock; signed-weighted-vote majority; tie-break highest-confidence-then-alphabetical-analyst_id; LLM-06 + LLM-07 closed; Wave 5 (05-06 entrypoint) unblocked.
</output>
