import { z } from 'zod'

// AgentSignal — mirror of analysts/signals.py.
//
// Verdict ladder (5 states): same names, same order as the Python Literal so
// frontend display logic and Python verdict logic agree byte-identically.
export const VerdictSchema = z.enum([
  'strong_bullish',
  'bullish',
  'neutral',
  'bearish',
  'strong_bearish',
])
export type Verdict = z.infer<typeof VerdictSchema>

// AnalystId — 4 analytical (Phase 3) + 6 persona (Phase 5 widening) = 10 ids.
// Order MUST match analysts/signals.py exactly (analytical first, then the
// PERSONA_IDS canonical tuple from routine/persona_runner.py).
export const AnalystIdSchema = z.enum([
  'fundamentals',
  'technicals',
  'news_sentiment',
  'valuation',
  'buffett',
  'munger',
  'wood',
  'burry',
  'lynch',
  'claude_analyst',
])
export type AnalystId = z.infer<typeof AnalystIdSchema>

// AgentSignal Pydantic model → zod equivalent.
//
// The data_unavailable invariant from analysts/signals.py
// (_data_unavailable_implies_neutral_zero) is enforced here as a refine() so
// the same contract holds at parse time on the frontend: a (data_unavailable,
// verdict='bullish', confidence=80) record from a buggy analyst is rejected
// the same way Pydantic would reject it server-side.
export const AgentSignalSchema = z
  .object({
    ticker: z.string().min(1),
    analyst_id: AnalystIdSchema,
    computed_at: z.string(),
    verdict: VerdictSchema,
    confidence: z.number().int().min(0).max(100),
    evidence: z.array(z.string().max(200)).max(10),
    data_unavailable: z.boolean(),
  })
  .refine(
    (d) =>
      !d.data_unavailable || (d.verdict === 'neutral' && d.confidence === 0),
    {
      message:
        "data_unavailable=true requires verdict='neutral' AND confidence=0",
    },
  )
export type AgentSignal = z.infer<typeof AgentSignalSchema>
