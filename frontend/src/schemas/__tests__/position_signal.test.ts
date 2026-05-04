import { describe, expect, it } from 'vitest'

import {
  ActionHintSchema,
  PositionSignalSchema,
  PositionStateSchema,
} from '../position_signal'

const basePosition = {
  ticker: 'AAPL',
  computed_at: '2026-05-04T13:45:31Z',
  state: 'oversold' as const,
  consensus_score: -0.42,
  confidence: 65,
  action_hint: 'consider_add' as const,
  indicators: {
    rsi_14: 28.5,
    bb_position: -0.92,
    zscore_50: -1.8,
    stoch_k: 18.4,
    williams_r: -85.0,
    macd_histogram: -0.45,
    adx_14: 19.2,
  },
  evidence: ['RSI 28.5 < 30', 'BB position -0.92'],
  data_unavailable: false,
  trend_regime: false,
}

describe('PositionSignalSchema', () => {
  it('parses a happy-path oversold signal', () => {
    const parsed = PositionSignalSchema.parse(basePosition)
    expect(parsed.state).toBe('oversold')
    expect(parsed.consensus_score).toBeCloseTo(-0.42)
    expect(parsed.indicators.rsi_14).toBe(28.5)
  })

  it('rejects state outside the 5-state ladder', () => {
    const result = PositionSignalSchema.safeParse({
      ...basePosition,
      state: 'super_oversold',
    })
    expect(result.success).toBe(false)
  })

  it('rejects action_hint outside the 4-state Literal', () => {
    const result = PositionSignalSchema.safeParse({
      ...basePosition,
      action_hint: 'sell',
    })
    expect(result.success).toBe(false)
  })

  it('rejects consensus_score > 1', () => {
    const result = PositionSignalSchema.safeParse({
      ...basePosition,
      consensus_score: 1.5,
    })
    expect(result.success).toBe(false)
  })

  it('rejects consensus_score < -1', () => {
    const result = PositionSignalSchema.safeParse({
      ...basePosition,
      consensus_score: -1.5,
    })
    expect(result.success).toBe(false)
  })

  it('accepts indicators with null entries (warmup window)', () => {
    const parsed = PositionSignalSchema.parse({
      ...basePosition,
      indicators: { rsi_14: null, bb_position: 0.1 },
    })
    expect(parsed.indicators.rsi_14).toBeNull()
  })

  it('rejects data_unavailable=true with non-fair state (invariant)', () => {
    const result = PositionSignalSchema.safeParse({
      ...basePosition,
      data_unavailable: true,
      state: 'oversold',
      consensus_score: 0,
      confidence: 0,
      action_hint: 'hold_position',
      trend_regime: false,
    })
    expect(result.success).toBe(false)
  })

  it('rejects data_unavailable=true with non-zero consensus_score (invariant)', () => {
    const result = PositionSignalSchema.safeParse({
      ...basePosition,
      data_unavailable: true,
      state: 'fair',
      consensus_score: 0.3,
      confidence: 0,
      action_hint: 'hold_position',
      trend_regime: false,
    })
    expect(result.success).toBe(false)
  })

  it('accepts the canonical data_unavailable shape', () => {
    const parsed = PositionSignalSchema.parse({
      ...basePosition,
      data_unavailable: true,
      state: 'fair',
      consensus_score: 0,
      confidence: 0,
      action_hint: 'hold_position',
      trend_regime: false,
      indicators: {},
      evidence: ['data unavailable'],
    })
    expect(parsed.data_unavailable).toBe(true)
  })

  it('accepts trend_regime=true on non-data-unavailable signal', () => {
    const parsed = PositionSignalSchema.parse({
      ...basePosition,
      trend_regime: true,
    })
    expect(parsed.trend_regime).toBe(true)
  })
})

describe('PositionStateSchema', () => {
  it('accepts all 5 states', () => {
    for (const s of [
      'extreme_oversold',
      'oversold',
      'fair',
      'overbought',
      'extreme_overbought',
    ]) {
      expect(PositionStateSchema.parse(s)).toBe(s)
    }
  })
})

describe('ActionHintSchema', () => {
  it('accepts all 4 hints', () => {
    for (const h of [
      'consider_add',
      'hold_position',
      'consider_trim',
      'consider_take_profits',
    ]) {
      expect(ActionHintSchema.parse(h)).toBe(h)
    }
  })
})
