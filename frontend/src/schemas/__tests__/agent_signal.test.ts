import { describe, expect, it } from 'vitest'

import { AgentSignalSchema, AnalystIdSchema, VerdictSchema } from '../agent_signal'

const baseSignal = {
  ticker: 'NVDA',
  analyst_id: 'fundamentals' as const,
  computed_at: '2026-05-04T13:45:31Z',
  verdict: 'bullish' as const,
  confidence: 75,
  evidence: ['ROE 65%', 'P/E 38 vs sector 28'],
  data_unavailable: false,
}

describe('AgentSignalSchema', () => {
  it('parses a happy-path analytical signal and narrows the type', () => {
    const parsed = AgentSignalSchema.parse(baseSignal)
    expect(parsed.ticker).toBe('NVDA')
    expect(parsed.verdict).toBe('bullish')
    expect(parsed.confidence).toBe(75)
    expect(parsed.evidence).toHaveLength(2)
  })

  it('parses a happy-path persona signal (claude_analyst)', () => {
    const parsed = AgentSignalSchema.parse({
      ...baseSignal,
      analyst_id: 'claude_analyst',
    })
    expect(parsed.analyst_id).toBe('claude_analyst')
  })

  it('rejects an analyst_id outside the 10-id Literal', () => {
    const result = AgentSignalSchema.safeParse({
      ...baseSignal,
      analyst_id: 'warren_buffett', // typo'd id — must reject
    })
    expect(result.success).toBe(false)
  })

  it('rejects a verdict outside the 5-state ladder', () => {
    const result = AgentSignalSchema.safeParse({
      ...baseSignal,
      verdict: 'mildly_bullish',
    })
    expect(result.success).toBe(false)
  })

  it('rejects confidence above 100', () => {
    const result = AgentSignalSchema.safeParse({ ...baseSignal, confidence: 150 })
    expect(result.success).toBe(false)
  })

  it('rejects evidence list with > 10 items', () => {
    const result = AgentSignalSchema.safeParse({
      ...baseSignal,
      evidence: Array(11).fill('x'),
    })
    expect(result.success).toBe(false)
  })

  it('rejects data_unavailable=true with non-neutral verdict (invariant)', () => {
    const result = AgentSignalSchema.safeParse({
      ...baseSignal,
      data_unavailable: true,
      verdict: 'bullish',
      confidence: 0,
    })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues[0].message).toContain('data_unavailable')
    }
  })

  it('rejects data_unavailable=true with non-zero confidence (invariant)', () => {
    const result = AgentSignalSchema.safeParse({
      ...baseSignal,
      data_unavailable: true,
      verdict: 'neutral',
      confidence: 50,
    })
    expect(result.success).toBe(false)
  })

  it('accepts the canonical data_unavailable shape (verdict=neutral, confidence=0)', () => {
    const parsed = AgentSignalSchema.parse({
      ...baseSignal,
      data_unavailable: true,
      verdict: 'neutral',
      confidence: 0,
      evidence: ['data unavailable: yfinance fetch failed'],
    })
    expect(parsed.data_unavailable).toBe(true)
  })
})

describe('AnalystIdSchema', () => {
  it('accepts all 4 analytical ids', () => {
    for (const id of ['fundamentals', 'technicals', 'news_sentiment', 'valuation']) {
      expect(AnalystIdSchema.parse(id)).toBe(id)
    }
  })

  it('accepts all 6 persona ids', () => {
    for (const id of ['buffett', 'munger', 'wood', 'burry', 'lynch', 'claude_analyst']) {
      expect(AnalystIdSchema.parse(id)).toBe(id)
    }
  })
})

describe('VerdictSchema', () => {
  it('accepts all 5 ladder values', () => {
    for (const v of [
      'strong_bullish',
      'bullish',
      'neutral',
      'bearish',
      'strong_bearish',
    ]) {
      expect(VerdictSchema.parse(v)).toBe(v)
    }
  })
})
