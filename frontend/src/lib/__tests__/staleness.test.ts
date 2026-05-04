import { describe, expect, it } from 'vitest'

import {
  computeStaleness,
  SIX_HOURS_MS,
  TWENTY_FOUR_HOURS_MS,
} from '../staleness'

// Frozen reference now — every test computes snapshotIso = NOW - ageMs so
// boundary-arithmetic is exact and timezone-independent.
const NOW = new Date('2026-05-04T18:00:00Z')

function ageAgo(ms: number): string {
  return new Date(NOW.getTime() - ms).toISOString()
}

describe('computeStaleness — VIEW-11 thresholds', () => {
  it('GREEN: age < 6h, partial=false', () => {
    expect(computeStaleness(ageAgo(60 * 60 * 1000), false, NOW)).toBe('GREEN')
  })

  it('GREEN: age = 1ms, partial=false', () => {
    expect(computeStaleness(ageAgo(1), false, NOW)).toBe('GREEN')
  })

  it('AMBER: age < 6h, partial=true (partial overrides green)', () => {
    expect(computeStaleness(ageAgo(60 * 60 * 1000), true, NOW)).toBe('AMBER')
  })

  it('AMBER: age = exactly 6h, partial=false (boundary inclusive)', () => {
    expect(computeStaleness(ageAgo(SIX_HOURS_MS), false, NOW)).toBe('AMBER')
  })

  it('AMBER: age = exactly 6h, partial=true', () => {
    expect(computeStaleness(ageAgo(SIX_HOURS_MS), true, NOW)).toBe('AMBER')
  })

  it('AMBER: age = 12h, partial=false', () => {
    expect(computeStaleness(ageAgo(12 * 60 * 60 * 1000), false, NOW)).toBe(
      'AMBER',
    )
  })

  it('AMBER: age = 12h, partial=true', () => {
    expect(computeStaleness(ageAgo(12 * 60 * 60 * 1000), true, NOW)).toBe(
      'AMBER',
    )
  })

  it('AMBER: age = exactly 24h, partial=false (boundary inclusive — > strict)', () => {
    expect(computeStaleness(ageAgo(TWENTY_FOUR_HOURS_MS), false, NOW)).toBe(
      'AMBER',
    )
  })

  it('AMBER: age = exactly 24h, partial=true', () => {
    expect(computeStaleness(ageAgo(TWENTY_FOUR_HOURS_MS), true, NOW)).toBe(
      'AMBER',
    )
  })

  it('RED: age = 24h + 1ms, partial=false (just past boundary)', () => {
    expect(
      computeStaleness(ageAgo(TWENTY_FOUR_HOURS_MS + 1), false, NOW),
    ).toBe('RED')
  })

  it('RED: age = 36h, partial=false', () => {
    expect(computeStaleness(ageAgo(36 * 60 * 60 * 1000), false, NOW)).toBe(
      'RED',
    )
  })

  it('RED: age = 36h, partial=true (RED dominates partial)', () => {
    expect(computeStaleness(ageAgo(36 * 60 * 60 * 1000), true, NOW)).toBe(
      'RED',
    )
  })

  it('RED: defensive — unparseable ISO returns RED', () => {
    expect(computeStaleness('not-a-date', false, NOW)).toBe('RED')
  })

  it('uses Date.now() default when now arg omitted', () => {
    // Smoke check that the default-argument path is exercised. Build a
    // snapshotIso 1 second in the past from real wall-clock; expect GREEN.
    const oneSecondAgo = new Date(Date.now() - 1000).toISOString()
    expect(computeStaleness(oneSecondAgo, false)).toBe('GREEN')
  })
})

describe('staleness module constants', () => {
  it('SIX_HOURS_MS equals 6 * 60 * 60 * 1000', () => {
    expect(SIX_HOURS_MS).toBe(21_600_000)
  })

  it('TWENTY_FOUR_HOURS_MS equals 24 * 60 * 60 * 1000', () => {
    expect(TWENTY_FOUR_HOURS_MS).toBe(86_400_000)
  })
})
