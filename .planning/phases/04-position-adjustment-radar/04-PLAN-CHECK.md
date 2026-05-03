# Phase 4 Plan Check

**Verified:** 2026-05-03
**Verdict:** PASS (one advisory note; nothing blocks `/gmd:execute-plan 04-01`)

## Coverage Matrix

| Requirement | Plan(s) | Test surface |
|---|---|---|
| POSE-01 (multi-indicator consensus from RSI/BB/zscore/Stoch/Williams/MACD) | 04-03 (must_haves truths) + 04-01 (extracts `_adx_14`) | `test_rsi_*`, `test_bb_position_*`, `test_stoch_k_extremes`, `test_williams_r_extremes`, `test_zscore_extremes`, `test_macd_zscore_signed`, `test_macd_scale_invariance` (≥9 tests) |
| POSE-02 (5-state ladder + consensus_score [-1,+1] + agreement-confidence) | 04-02 (schema lock) + 04-03 (functional behaviour) | 04-02: ≥12 schema tests covering `PositionState` literal, ranges, `data_unavailable` invariant. 04-03: state ladder + consensus_score + confidence (full agreement / abstain / near-zero caps) |
| POSE-03 (ADX > 25 trend-regime gating) | 04-01 (extracts `_adx_14` + ADX_TREND_ABOVE/RANGE_BELOW) + 04-03 (gating behavior) | `test_adx_trend_regime_uptrend`, `test_adx_range_regime_sideways`, `test_adx_ambiguous_zone`, `test_adx_warmup_no_gating`, `test_adx_boundary_25_exact`, `test_trend_regime_downweights_mean_reversion` |
| POSE-04 (action_hint mapping) | 04-02 (`ActionHint` literal + invariant) + 04-03 (`_state_to_action_hint`) | 04-02: action_hint literal accepted/rejected + invariant tests. 04-03: `test_state_to_action_hint_mapping` (parametrized over all 5 states) |
| POSE-05 (headline morning-scan lens) | 04-03 (regression tests) | `test_known_oversold_regression`, `test_known_overbought_regression`, `test_known_sideways_fair`, plus cross-cutting `test_dark_snapshot_emits_pose_unavailable` extension in `test_invariants.py` |

All 5 requirement IDs appear in at least one plan's `requirements` frontmatter and have multiple covering tests. **No coverage gap.**

## Dependency Graph

```
04-01 (Wave 1, depends_on: [])
   ├──▶ 04-02 (Wave 2, depends_on: [04-01])    [conservative — see note]
   └──▶ 04-03 (Wave 3, depends_on: [04-01, 04-02])
```

- **04-01** has no Phase 4 deps. Correct.
- **04-02** declares `depends_on: [04-01]`. Mild observation: 04-02 actually only consumes the pre-existing Phase 3 `frozen_now` fixture; it does NOT import `_indicator_math` or any new synthetic builders. The dep is conservative (correct sequencing, but Wave 2 could run in parallel with Wave 1). Not a blocker — preserves clean wave layering.
- **04-03** declares `depends_on: [04-01, 04-02]`. Both real: imports `_build_df`, `_adx_14`, `ADX_TREND_ABOVE`, `ADX_RANGE_BELOW` from 04-01 and `PositionSignal`, `PositionState`, `ActionHint` from 04-02. Synthetic_oversold/overbought/mean_reverting fixtures from 04-01's conftest extension drive regression tests.
- No cycles, no forward references, no missing references.

## TDD Discipline

| Plan | RED commit | GREEN commit | OK |
|---|---|---|---|
| 04-01 Task 1 | `test(04-01): add failing tests for shared analysts._indicator_math helpers` | `refactor(04-01): extract _build_df + _adx_14 + _total_to_verdict` | YES |
| 04-01 Task 2 | `test(04-01): add failing tests for synthetic_oversold/overbought/mean_reverting fixtures` | `test(04-01): add synthetic_*_history builders` | YES |
| 04-02 Task 1 | `test(04-02): add failing tests for PositionSignal schema` | `feat(04-02): PositionSignal Pydantic schema` | YES |
| 04-03 Task 1 (RED-only) | `test(04-03): add failing tests for position_adjustment analyst` | (rolls into Task 2) | YES |
| 04-03 Task 2 | (continuation) | `feat(04-03): position_adjustment analyst` | YES |

Pattern is correct: RED commits land failing tests; GREEN commits land implementation. All `<action>` blocks include the explicit `Run pytest → ImportError` step before each RED commit.

## Threshold Constants Coverage

23/23 user-listed module constants + `CONFIDENCE_ABSTAIN_THRESHOLD` are all named in 04-03 (verified by grep on plan body). `ADX_PERIOD`, `ADX_MIN_BARS`, `ADX_STABLE_BARS` correctly live in `analysts/_indicator_math.py` per 04-01 (architectural separation — they belong with `_adx_14`).

## Indicator Coverage

All 6 POSE-01 indicators have a dedicated helper named in 04-03 with a dedicated test:

| Indicator | Helper | Sub-signal mapper | Dedicated test |
|---|---|---|---|
| RSI(14) | `_rsi_14` | `_rsi_to_subsignal` | `test_rsi_oversold_regression`, `test_rsi_overbought_regression` |
| Bollinger position | `_bollinger_position` | `_bb_to_subsignal` | `test_bb_position_oversold_regression`, `test_bb_position_overbought_regression` |
| z-score vs MA50 | `_zscore_vs_ma50` | `_zscore_to_subsignal` | `test_zscore_extremes` |
| Stochastic %K | `_stoch_k_14` | `_stoch_to_subsignal` | `test_stoch_k_extremes` |
| Williams %R | `_williams_r_14` | `_williams_to_subsignal` | `test_williams_r_extremes` |
| MACD histogram (z-scored) | `_macd_histogram_zscore` | `_macd_z_to_subsignal` | `test_macd_zscore_signed`, `test_macd_scale_invariance` |

Plus warm-up tier tests (`test_warmup_tier_14_to_19_only_stoch_williams` through `test_warmup_tier_ge_94_all_indicators`) confirm graceful degradation across the warm-up boundary table.

## UNIFORM RULE Branches

5 branches implemented:

1. `snapshot.data_unavailable=True` → evidence=`["snapshot data_unavailable=True"]`
2. `snapshot.prices is None` → evidence=`["prices snapshot missing"]`
3. `snapshot.prices.data_unavailable=True` → evidence=`["prices.data_unavailable=True"]`
4. `not snapshot.prices.history` → evidence=`["prices history is empty"]`
5. `len(df) < MIN_BARS_FOR_ANY_INDICATOR` → evidence=`["history has N bars; need ≥14 for any indicator"]`

Each has a dedicated test plus the cross-cutting `test_dark_snapshot_emits_pose_unavailable` in `test_invariants.py`.

**Advisory (not blocking):** CONTEXT.md line 82 lists `current_price None or ≤0` as a UNIFORM RULE trigger. The plan does NOT include a `current_price` guard. This is functionally correct — `score()` reads `df["close"].iloc[-1]` from `history`, never from `current_price`. When current_price is None, history is typically also empty, so branch #4 catches the realistic failure mode. Two options for execution-time refinement:
- **Accept the divergence (recommended):** add a one-line note in 04-03's `<verification>` block stating that current_price is metadata-only at the analyst layer.
- **Add the branch:** insert a 4.5th guard between branches 3 and 4. Mechanical.

Either is fine.

## Wave 0 Refactor Safety

04-01 is explicit and exhaustive:
- Frontmatter `provides`: Phase 3 regression invariant — *"all 25 existing tests in test_technicals.py + 18 in test_fundamentals.py + 12 in test_valuation.py + 2 in test_invariants.py PASS unchanged after the refactor"*
- `must_haves.truths`: enumerates all four test files and their counts
- `<action>` final step: runs full Phase 3 test suite as the final GREEN gate
- `<verify>` block: includes `pytest tests/analysts/ -v && pytest -x -q` chain
- Sanity grep step: confirms zero `def _total_to_verdict` remains outside `analysts/_indicator_math.py`

`_adx_evidence` correctly stays in `technicals.py` (not moved) — tightly coupled to technicals' evidence-string formatting.

**Wave 0 refactor risk is well-managed.**

## Provenance / INFRA-07

04-03 explicitly requires the virattt provenance reference (`virattt/ai-hedge-fund/src/agents/risk_manager.py`):
- `must_haves.truths` line: literal substring assertion
- Implementation_sketch: actual docstring with the URL
- Test `test_provenance_header_present`
- Test `test_no_ta_library_imports` (forbids `pandas_ta`, `talib`, etc.)
- `<verify>` block: grep gate on the literal URL

**INFRA-07 fully addressed.**

## REQUIREMENTS / ROADMAP Closeout

04-03's `<output>` block requires:
- POSE-01..05 marked `[x]` in REQUIREMENTS.md (lines 38-42)
- Requirement-coverage table updated to 'Complete' / 'Phase 4' (lines 173-177)
- Phase 4 plans marked `[x]` in ROADMAP.md

Specific line numbers given match REQUIREMENTS.md actual layout. **Closeout is well-specified and traceable.**

## Coverage Gates

All three plans specify ≥90% line / ≥85% branch on their respective new modules (`_indicator_math.py`, `position_signal.py`, `position_adjustment.py`).

## Issues Found

1. **(advisory only — not blocking)** Empty-data UNIFORM RULE branch count differs from CONTEXT.md letter (current_price guard). Plan is functionally correct. See "UNIFORM RULE Branches" section above for resolution options.
2. **(observation, not an issue)** 04-02's `depends_on: [04-01]` is conservative — only consumes Phase 3 fixtures. Preserves clean wave layering. No change recommended.
3. **(no issue, confirming)** None of CONTEXT.md's `<deferred>` items (per-sector scoring, per-ticker thresholds, OBV/MFI, multi-timeframe, ML regime, real-time, trend view, action_hint refinement) appear in any plan. **No scope creep.**

## Strengths

- **Boundary discipline tight** — strict `>` / `<` boundaries with dedicated tests covering 12 boundary cases for state ladder + ADX=25 boundary precision via `_adx_14` monkeypatch.
- **Pitfall closures explicit** — Pitfall #1 (data_unavailable invariant) → @model_validator. Pitfall #3 (cross-ticker scale invariance) → `test_macd_scale_invariance`. Pitfall #6 (now-read-once) → must_haves truth + AST-walk test. Pitfall #2 (ambiguous-zone discontinuity) → locked design at weight=1.0 in 20-25 zone.
- **Cross-cutting test extension** — `test_dark_snapshot_emits_pose_unavailable` added to `test_invariants.py` alongside preserved 2 AgentSignal invariants.
- **Hand-rolled discipline locked by negative test** — `test_no_ta_library_imports` forbids future drift to TA libraries.
- **Determinism end-to-end** — model_dump_json round-trip + byte-equal synthetic builder output + computed_at pass-through.

## Recommendation

**PASS — proceed to `/gmd:execute-plan 04-01`.**

The three plans cover POSE-01..05 with ~46 net-new tests, ≥90/85 coverage gates on all 3 new production modules, full Phase 3 regression invariant on the Wave 0 refactor, INFRA-07 provenance, and explicit REQUIREMENTS.md / ROADMAP.md closeout. TDD discipline (RED → GREEN) preserved across all 5 commits. Dependency graph acyclic and correctly waved.

Issue #1 (current_price guard) is documentation polish — execution can proceed; the executor adds a one-line clarification or the branch as a Rule-2 deviation if encountered.

---

*Phase: 04-position-adjustment-radar*
*Plan-checked: 2026-05-03*
