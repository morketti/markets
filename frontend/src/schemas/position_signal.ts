import { z } from 'zod'

// PositionSignal — mirror of analysts/position_signal.py.
//
// 5-state PositionState (mean-reversion ladder; PEER of AgentSignal's Verdict
// directional ladder per 04-RESEARCH.md Pattern #7).
export const PositionStateSchema = z.enum([
  'extreme_oversold',
  'oversold',
  'fair',
  'overbought',
  'extreme_overbought',
])
export type PositionState = z.infer<typeof PositionStateSchema>

// 4-state ActionHint — pre-recommendation hint surfaced in deep-dive view.
export const ActionHintSchema = z.enum([
  'consider_add',
  'hold_position',
  'consider_trim',
  'consider_take_profits',
])
export type ActionHint = z.infer<typeof ActionHintSchema>

// PositionSignal — adds consensus_score [-1,1] + indicators dict +
// trend_regime flag on top of the AgentSignal-shaped fields.
//
// data_unavailable invariant from analysts/position_signal.py
// (_data_unavailable_implies_fair_zero) enforced via refine() — every leg of
// the canonical no-opinion shape must hold (state='fair', consensus_score=0,
// confidence=0, action_hint='hold_position', trend_regime=false).
export const PositionSignalSchema = z
  .object({
    ticker: z.string().min(1),
    computed_at: z.string(),
    state: PositionStateSchema,
    consensus_score: z.number().min(-1).max(1),
    confidence: z.number().int().min(0).max(100),
    action_hint: ActionHintSchema,
    indicators: z.record(z.string(), z.number().nullable()),
    evidence: z.array(z.string().max(200)).max(10),
    data_unavailable: z.boolean(),
    trend_regime: z.boolean(),
  })
  .refine(
    (d) =>
      !d.data_unavailable ||
      (d.state === 'fair' &&
        d.consensus_score === 0 &&
        d.confidence === 0 &&
        d.action_hint === 'hold_position' &&
        d.trend_regime === false),
    {
      message:
        "data_unavailable=true requires the canonical no-opinion shape (state='fair', consensus_score=0, confidence=0, action_hint='hold_position', trend_regime=false)",
    },
  )
export type PositionSignal = z.infer<typeof PositionSignalSchema>
