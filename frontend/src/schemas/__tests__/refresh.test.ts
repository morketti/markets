// novel-to-this-project — Phase 8 Wave 1 zod schema tests for the refresh
// response. Mirrors the locked api/refresh.py envelope shapes (success /
// partial / full-failure) via z.union of the success and failure variants.

import { describe, expect, it } from 'vitest'

import {
  RefreshResponseSchema,
  isRefreshFailure,
  type RefreshResponse,
} from '../refresh'

const SUCCESS_FIXTURE = {
  ticker: 'AAPL',
  current_price: 178.42,
  price_timestamp: '2026-05-04T19:32:11+00:00',
  recent_headlines: [
    {
      source: 'Reuters',
      published_at: '2026-05-04T19:00:00+00:00',
      title: 'AAPL ships record quarter',
      url: 'https://example.com/aapl',
    },
  ],
  errors: [],
  partial: false,
}

const PARTIAL_FIXTURE = {
  ticker: 'AAPL',
  current_price: 178.42,
  price_timestamp: '2026-05-04T19:32:11+00:00',
  recent_headlines: [],
  errors: ['rss-unavailable'],
  partial: true,
}

const FULL_FAILURE_FIXTURE = {
  ticker: 'AAPL',
  error: true,
  errors: ['yfinance-unavailable', 'yahooquery-unavailable'],
  partial: true,
}

describe('RefreshResponseSchema', () => {
  it('parses_success_shape — happy path with current_price + headlines', () => {
    const result = RefreshResponseSchema.safeParse(SUCCESS_FIXTURE)
    expect(result.success).toBe(true)
    if (result.success) {
      // Narrowing: success branch has current_price.
      expect('current_price' in result.data).toBe(true)
      if ('current_price' in result.data) {
        expect(result.data.current_price).toBe(178.42)
      }
      expect(result.data.partial).toBe(false)
      expect(result.data.ticker).toBe('AAPL')
    }
  })

  it('parses_partial_shape_rss_unavailable — price OK, headlines empty', () => {
    const result = RefreshResponseSchema.safeParse(PARTIAL_FIXTURE)
    expect(result.success).toBe(true)
    if (result.success && 'current_price' in result.data) {
      expect(result.data.current_price).toBe(178.42)
      expect(result.data.recent_headlines).toEqual([])
      expect(result.data.errors).toContain('rss-unavailable')
      expect(result.data.partial).toBe(true)
    }
  })

  it('parses_full_failure_shape — error: true, no current_price', () => {
    const result = RefreshResponseSchema.safeParse(FULL_FAILURE_FIXTURE)
    expect(result.success).toBe(true)
    if (result.success) {
      expect(isRefreshFailure(result.data)).toBe(true)
      if (isRefreshFailure(result.data)) {
        expect(result.data.errors).toContain('yfinance-unavailable')
        expect(result.data.errors).toContain('yahooquery-unavailable')
      }
    }
  })

  it('rejects_invalid_current_price — negative price fails', () => {
    const bad = { ...SUCCESS_FIXTURE, current_price: -1 }
    const result = RefreshResponseSchema.safeParse(bad)
    expect(result.success).toBe(false)
  })

  it('rejects_invalid_current_price — string instead of number fails', () => {
    const bad = { ...SUCCESS_FIXTURE, current_price: '178.42' }
    const result = RefreshResponseSchema.safeParse(bad)
    expect(result.success).toBe(false)
  })

  it('rejects_missing_ticker — both shapes require ticker', () => {
    const bad1: Record<string, unknown> = { ...SUCCESS_FIXTURE }
    delete bad1.ticker
    expect(RefreshResponseSchema.safeParse(bad1).success).toBe(false)

    const bad2: Record<string, unknown> = { ...FULL_FAILURE_FIXTURE }
    delete bad2.ticker
    expect(RefreshResponseSchema.safeParse(bad2).success).toBe(false)
  })

  it('rejects_invalid_iso_timestamp — non-ISO price_timestamp fails', () => {
    const bad = { ...SUCCESS_FIXTURE, price_timestamp: 'not a date' }
    const result = RefreshResponseSchema.safeParse(bad)
    expect(result.success).toBe(false)
  })

  it('isRefreshFailure narrows correctly across all 3 shapes', () => {
    const ok = RefreshResponseSchema.parse(SUCCESS_FIXTURE) as RefreshResponse
    const partial = RefreshResponseSchema.parse(PARTIAL_FIXTURE) as RefreshResponse
    const fail = RefreshResponseSchema.parse(FULL_FAILURE_FIXTURE) as RefreshResponse

    expect(isRefreshFailure(ok)).toBe(false)
    expect(isRefreshFailure(partial)).toBe(false)
    expect(isRefreshFailure(fail)).toBe(true)
  })
})
