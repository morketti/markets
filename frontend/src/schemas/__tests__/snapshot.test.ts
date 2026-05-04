import { describe, expect, it } from 'vitest'

import {
  HeadlineSchema,
  IndicatorsSchema,
  OHLCBarSchema,
  SnapshotSchema,
} from '../snapshot'

// Real-shaped Phase 5 / Wave 0 fixture — 6 persona signals (matches the
// canonical PERSONA_IDS tuple from routine/persona_runner.py); 4 analytical
// signals; full v2 envelope. Catches a Phase 5 closeout drift if the
// persona_id Literal ever changes.
const baseSnapshot = {
  ticker: 'NVDA',
  schema_version: 2 as const,
  analytical_signals: [
    {
      ticker: 'NVDA',
      analyst_id: 'fundamentals' as const,
      computed_at: '2026-05-04T13:45:31Z',
      verdict: 'bullish' as const,
      confidence: 75,
      evidence: ['ROE 65%'],
      data_unavailable: false,
    },
    {
      ticker: 'NVDA',
      analyst_id: 'technicals' as const,
      computed_at: '2026-05-04T13:45:31Z',
      verdict: 'strong_bullish' as const,
      confidence: 80,
      evidence: ['Above MA200, ADX 35'],
      data_unavailable: false,
    },
    {
      ticker: 'NVDA',
      analyst_id: 'news_sentiment' as const,
      computed_at: '2026-05-04T13:45:31Z',
      verdict: 'bullish' as const,
      confidence: 60,
      evidence: ['recency-weighted +0.42'],
      data_unavailable: false,
    },
    {
      ticker: 'NVDA',
      analyst_id: 'valuation' as const,
      computed_at: '2026-05-04T13:45:31Z',
      verdict: 'bearish' as const,
      confidence: 65,
      evidence: ['P/E 38 vs target 28'],
      data_unavailable: false,
    },
  ],
  position_signal: {
    ticker: 'NVDA',
    computed_at: '2026-05-04T13:45:31Z',
    state: 'overbought' as const,
    consensus_score: 0.62,
    confidence: 70,
    action_hint: 'consider_trim' as const,
    indicators: { rsi_14: 72.5, bb_position: 0.85 },
    evidence: ['RSI > 70'],
    data_unavailable: false,
    trend_regime: true,
  },
  persona_signals: [
    'buffett',
    'munger',
    'wood',
    'burry',
    'lynch',
    'claude_analyst',
  ].map((id) => ({
    ticker: 'NVDA',
    analyst_id: id as
      | 'buffett'
      | 'munger'
      | 'wood'
      | 'burry'
      | 'lynch'
      | 'claude_analyst',
    computed_at: '2026-05-04T13:45:31Z',
    verdict: 'neutral' as const,
    confidence: 50,
    evidence: [`${id} reasoning`],
    data_unavailable: false,
  })),
  ticker_decision: {
    ticker: 'NVDA',
    computed_at: '2026-05-04T13:45:31Z',
    schema_version: 2 as const,
    recommendation: 'trim' as const,
    conviction: 'medium' as const,
    short_term: {
      summary: 'overbought',
      drivers: ['RSI > 70'],
      confidence: 70,
      thesis_status: 'n/a' as const,
    },
    long_term: {
      summary: 'AI capex cycle intact',
      drivers: ['data center +200% YoY'],
      confidence: 75,
      thesis_status: 'intact' as const,
    },
    open_observation: '',
    dissent: {
      has_dissent: false,
      dissenting_persona: null,
      dissent_summary: '',
    },
    data_unavailable: false,
  },
  ohlc_history: [
    {
      date: '2026-04-30',
      open: 950.5,
      high: 962.0,
      low: 948.1,
      close: 958.7,
      volume: 42_000_000,
    },
    {
      date: '2026-05-01',
      open: 959.0,
      high: 970.5,
      low: 955.2,
      close: 968.3,
      volume: 38_000_000,
    },
  ],
  indicators: {
    ma20: [null, 952.4],
    ma50: [null, null],
    bb_upper: [null, 980.1],
    bb_lower: [null, 920.5],
    rsi14: [null, 68.5],
  },
  headlines: [
    {
      source: 'yahoo-rss',
      published_at: '2026-05-04T11:23:00Z',
      title: 'NVIDIA announces next-gen AI chip',
      url: 'https://finance.yahoo.com/news/nvidia-12345',
    },
  ],
  errors: [],
}

describe('SnapshotSchema (per-ticker JSON v2)', () => {
  it('parses a happy-path Phase 5 / Wave 0 snapshot', () => {
    const parsed = SnapshotSchema.parse(baseSnapshot)
    expect(parsed.schema_version).toBe(2)
    expect(parsed.analytical_signals).toHaveLength(4)
    expect(parsed.persona_signals).toHaveLength(6)
    expect(parsed.ohlc_history).toHaveLength(2)
    expect(parsed.indicators.ma20).toEqual([null, 952.4])
  })

  it('REJECTS schema_version=1 (Wave 0 break)', () => {
    const result = SnapshotSchema.safeParse({
      ...baseSnapshot,
      schema_version: 1,
    })
    expect(result.success).toBe(false)
  })

  it('parses a snapshot with null position_signal (lite mode pre-PositionSignal)', () => {
    const parsed = SnapshotSchema.parse({
      ...baseSnapshot,
      position_signal: null,
    })
    expect(parsed.position_signal).toBeNull()
  })

  it('parses a snapshot with null ticker_decision (lite mode skip path)', () => {
    const parsed = SnapshotSchema.parse({
      ...baseSnapshot,
      ticker_decision: null,
    })
    expect(parsed.ticker_decision).toBeNull()
  })

  it('rejects ohlc_history entry with malformed date', () => {
    const result = SnapshotSchema.safeParse({
      ...baseSnapshot,
      ohlc_history: [{ ...baseSnapshot.ohlc_history[0], date: '2026/04/30' }],
    })
    expect(result.success).toBe(false)
  })

  it('rejects indicators with missing required series key', () => {
    const result = SnapshotSchema.safeParse({
      ...baseSnapshot,
      indicators: {
        ma20: [null],
        ma50: [null],
        bb_upper: [null],
        bb_lower: [null],
        // rsi14 omitted
      },
    })
    expect(result.success).toBe(false)
  })

  it('accepts all 5 indicator series with mixed null + number entries', () => {
    const parsed = SnapshotSchema.parse({
      ...baseSnapshot,
      indicators: {
        ma20: [null, null, 100, 101, 102],
        ma50: [null, null, null, null, null],
        bb_upper: [null, null, 110, 111, 112],
        bb_lower: [null, null, 90, 91, 92],
        rsi14: [null, 55, 56, 57, 58],
      },
    })
    expect(parsed.indicators.rsi14[0]).toBeNull()
    expect(parsed.indicators.rsi14[4]).toBe(58)
  })
})

describe('OHLCBarSchema', () => {
  it('parses a valid bar', () => {
    const bar = {
      date: '2026-05-04',
      open: 100,
      high: 105,
      low: 99,
      close: 103,
      volume: 1_000_000,
    }
    expect(OHLCBarSchema.parse(bar)).toEqual(bar)
  })

  it('rejects negative volume', () => {
    const result = OHLCBarSchema.safeParse({
      date: '2026-05-04',
      open: 100,
      high: 105,
      low: 99,
      close: 103,
      volume: -1,
    })
    expect(result.success).toBe(false)
  })
})

describe('IndicatorsSchema', () => {
  it('accepts all-null arrays (warmup)', () => {
    const parsed = IndicatorsSchema.parse({
      ma20: [null, null],
      ma50: [null, null],
      bb_upper: [null, null],
      bb_lower: [null, null],
      rsi14: [null, null],
    })
    expect(parsed.ma20).toEqual([null, null])
  })
})

describe('HeadlineSchema', () => {
  it('parses a valid headline', () => {
    const h = {
      source: 'google-news',
      published_at: '2026-05-04T10:00:00Z',
      title: 'Markets rally on inflation print',
      url: 'https://news.google.com/articles/x',
    }
    expect(HeadlineSchema.parse(h)).toEqual(h)
  })

  it('rejects malformed url', () => {
    const result = HeadlineSchema.safeParse({
      source: 'finviz',
      published_at: '2026-05-04T10:00:00Z',
      title: 'x',
      url: 'not-a-url',
    })
    expect(result.success).toBe(false)
  })
})
