import { describe, expect, it } from 'vitest'

import { StatusSchema } from '../status'

const baseStatus = {
  success: true,
  partial: false,
  completed_tickers: ['NVDA', 'AAPL', 'MSFT'],
  failed_tickers: [],
  skipped_tickers: [],
  llm_failure_count: 0,
  lite_mode: false,
}

describe('StatusSchema', () => {
  it('parses a happy-path success status', () => {
    const parsed = StatusSchema.parse(baseStatus)
    expect(parsed.success).toBe(true)
    expect(parsed.completed_tickers).toEqual(['NVDA', 'AAPL', 'MSFT'])
  })

  it('parses a partial-success status with failed tickers', () => {
    const parsed = StatusSchema.parse({
      ...baseStatus,
      success: false,
      partial: true,
      failed_tickers: ['XYZ'],
      llm_failure_count: 2,
    })
    expect(parsed.partial).toBe(true)
    expect(parsed.failed_tickers).toEqual(['XYZ'])
    expect(parsed.llm_failure_count).toBe(2)
  })

  it('parses a lite-mode status (partial=true, lite_mode=true, no decisions)', () => {
    const parsed = StatusSchema.parse({
      ...baseStatus,
      partial: true,
      lite_mode: true,
    })
    expect(parsed.lite_mode).toBe(true)
  })

  it('rejects missing required field (success)', () => {
    const { success: _omit, ...rest } = baseStatus
    const result = StatusSchema.safeParse(rest)
    expect(result.success).toBe(false)
  })

  it('rejects missing partial field', () => {
    const { partial: _omit, ...rest } = baseStatus
    const result = StatusSchema.safeParse(rest)
    expect(result.success).toBe(false)
  })

  it('rejects negative llm_failure_count', () => {
    const result = StatusSchema.safeParse({
      ...baseStatus,
      llm_failure_count: -1,
    })
    expect(result.success).toBe(false)
  })

  it('rejects non-boolean lite_mode', () => {
    const result = StatusSchema.safeParse({
      ...baseStatus,
      lite_mode: 'true',
    })
    expect(result.success).toBe(false)
  })
})
