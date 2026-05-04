import { z } from 'zod'

// TickerDecision — mirror of synthesis/decision.py POST Wave 0.
//
// schema_version is z.literal(2) (NOT z.number) — strict literal so v1
// snapshots are REJECTED at parse time. Per CONTEXT.md UNIFORM RULE this
// surfaces as an explicit "schema upgrade required — re-run today's routine"
// banner via SchemaMismatchError, not a silent fallback or coercion.

export const DecisionRecommendationSchema = z.enum([
  'add',
  'trim',
  'hold',
  'take_profits',
  'buy',
  'avoid',
])
export type DecisionRecommendation = z.infer<typeof DecisionRecommendationSchema>

export const ConvictionBandSchema = z.enum(['low', 'medium', 'high'])
export type ConvictionBand = z.infer<typeof ConvictionBandSchema>

export const TimeframeSchema = z.enum(['short_term', 'long_term'])
export type Timeframe = z.infer<typeof TimeframeSchema>

// ThesisStatus — Phase 6 / Wave 0 NEW field. 5-state Literal that drives the
// Long-Term Thesis Status lens (VIEW-04). Default 'n/a' on the Pydantic side
// makes the field non-breaking; frontend zod schema accepts all 5 values.
export const ThesisStatusSchema = z.enum([
  'intact',
  'weakening',
  'broken',
  'improving',
  'n/a',
])
export type ThesisStatus = z.infer<typeof ThesisStatusSchema>

// TimeframeBand — per-timeframe synthesis content; thesis_status is the
// Wave 0 addition. Drivers list capped at 10 with each ≤200 chars (matches
// AgentSignal.evidence cap).
export const TimeframeBandSchema = z.object({
  summary: z.string().min(1).max(500),
  drivers: z.array(z.string().max(200)).max(10),
  confidence: z.number().int().min(0).max(100),
  thesis_status: ThesisStatusSchema,
})
export type TimeframeBand = z.infer<typeof TimeframeBandSchema>

// DissentSection — always present (has_dissent: false case still serializes).
// Frontend renders the dissenting-persona summary only when has_dissent=true.
export const DissentSectionSchema = z.object({
  has_dissent: z.boolean(),
  dissenting_persona: z.string().nullable(),
  dissent_summary: z.string().max(500),
})
export type DissentSection = z.infer<typeof DissentSectionSchema>

// TickerDecision — schema_version: z.literal(2) is the load-bearing assertion.
// data_unavailable invariant (synthesis/decision.py
// _data_unavailable_implies_safe_defaults) enforced via refine().
export const TickerDecisionSchema = z
  .object({
    ticker: z.string().min(1),
    computed_at: z.string(),
    schema_version: z.literal(2),
    recommendation: DecisionRecommendationSchema,
    conviction: ConvictionBandSchema,
    short_term: TimeframeBandSchema,
    long_term: TimeframeBandSchema,
    open_observation: z.string().max(500),
    dissent: DissentSectionSchema,
    data_unavailable: z.boolean(),
  })
  .refine(
    (d) =>
      !d.data_unavailable ||
      (d.recommendation === 'hold' && d.conviction === 'low'),
    {
      message:
        "data_unavailable=true requires recommendation='hold' AND conviction='low'",
    },
  )
export type TickerDecision = z.infer<typeof TickerDecisionSchema>
