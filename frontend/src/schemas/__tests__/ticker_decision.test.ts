import { describe, expect, it } from 'vitest'

import {
  ConvictionBandSchema,
  DecisionRecommendationSchema,
  ThesisStatusSchema,
  TickerDecisionSchema,
} from '../ticker_decision'

const baseDecision = {
  ticker: 'NVDA',
  computed_at: '2026-05-04T13:45:31Z',
  schema_version: 2 as const,
  recommendation: 'hold' as const,
  conviction: 'medium' as const,
  short_term: {
    summary: 'Position-Adjustment signal is oversold; PositionState=oversold',
    drivers: ['RSI 28.5', 'BB position -0.92'],
    confidence: 70,
    thesis_status: 'n/a' as const,
  },
  long_term: {
    summary: 'AI capex cycle intact; valuation stretched but durable moat',
    drivers: ['ROE 65%', 'data center revenue +200% YoY'],
    confidence: 80,
    thesis_status: 'intact' as const,
  },
  open_observation:
    'Claude observation: tactical entry vs strategic compounder split is real here.',
  dissent: {
    has_dissent: false,
    dissenting_persona: null,
    dissent_summary: '',
  },
  data_unavailable: false,
}

describe('TickerDecisionSchema', () => {
  it('parses a happy-path decision with schema_version=2', () => {
    const parsed = TickerDecisionSchema.parse(baseDecision)
    expect(parsed.schema_version).toBe(2)
    expect(parsed.recommendation).toBe('hold')
    expect(parsed.long_term.thesis_status).toBe('intact')
  })

  it('REJECTS schema_version=1 (CONTEXT.md UNIFORM RULE — schema-mismatch error)', () => {
    const result = TickerDecisionSchema.safeParse({
      ...baseDecision,
      schema_version: 1,
    })
    expect(result.success).toBe(false)
  })

  it('rejects schema_version=3 (forward-incompat without explicit upgrade)', () => {
    const result = TickerDecisionSchema.safeParse({
      ...baseDecision,
      schema_version: 3,
    })
    expect(result.success).toBe(false)
  })

  it('rejects recommendation outside the 6-state Literal', () => {
    const result = TickerDecisionSchema.safeParse({
      ...baseDecision,
      recommendation: 'sell',
    })
    expect(result.success).toBe(false)
  })

  it('rejects conviction outside the 3-state Literal', () => {
    const result = TickerDecisionSchema.safeParse({
      ...baseDecision,
      conviction: 'extreme',
    })
    expect(result.success).toBe(false)
  })

  it('rejects thesis_status outside the 5-state Literal', () => {
    const result = TickerDecisionSchema.safeParse({
      ...baseDecision,
      long_term: { ...baseDecision.long_term, thesis_status: 'mixed' },
    })
    expect(result.success).toBe(false)
  })

  it('accepts all 5 thesis_status values', () => {
    for (const s of ['intact', 'weakening', 'broken', 'improving', 'n/a']) {
      const parsed = TickerDecisionSchema.parse({
        ...baseDecision,
        long_term: { ...baseDecision.long_term, thesis_status: s },
      })
      expect(parsed.long_term.thesis_status).toBe(s)
    }
  })

  it('parses a decision with dissent populated', () => {
    const parsed = TickerDecisionSchema.parse({
      ...baseDecision,
      dissent: {
        has_dissent: true,
        dissenting_persona: 'burry',
        dissent_summary: 'Burry sees overextension at 15x sales — contrarian short setup.',
      },
    })
    expect(parsed.dissent.has_dissent).toBe(true)
    expect(parsed.dissent.dissenting_persona).toBe('burry')
  })

  it('rejects data_unavailable=true with recommendation != hold (invariant)', () => {
    const result = TickerDecisionSchema.safeParse({
      ...baseDecision,
      data_unavailable: true,
      recommendation: 'buy',
      conviction: 'low',
    })
    expect(result.success).toBe(false)
  })

  it('rejects data_unavailable=true with conviction != low (invariant)', () => {
    const result = TickerDecisionSchema.safeParse({
      ...baseDecision,
      data_unavailable: true,
      recommendation: 'hold',
      conviction: 'high',
    })
    expect(result.success).toBe(false)
  })

  it('accepts the canonical data_unavailable shape', () => {
    const parsed = TickerDecisionSchema.parse({
      ...baseDecision,
      data_unavailable: true,
      recommendation: 'hold',
      conviction: 'low',
    })
    expect(parsed.data_unavailable).toBe(true)
  })
})

describe('DecisionRecommendationSchema', () => {
  it('accepts all 6 recommendations', () => {
    for (const r of ['add', 'trim', 'hold', 'take_profits', 'buy', 'avoid']) {
      expect(DecisionRecommendationSchema.parse(r)).toBe(r)
    }
  })
})

describe('ConvictionBandSchema', () => {
  it('accepts all 3 bands', () => {
    for (const b of ['low', 'medium', 'high']) {
      expect(ConvictionBandSchema.parse(b)).toBe(b)
    }
  })
})

describe('ThesisStatusSchema', () => {
  it('accepts all 5 thesis statuses including n/a', () => {
    for (const s of ['intact', 'weakening', 'broken', 'improving', 'n/a']) {
      expect(ThesisStatusSchema.parse(s)).toBe(s)
    }
  })
})
