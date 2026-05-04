// novel-to-this-project — Phase 9 Task 2 zod schema tests for Endorsement
// records. Mirrors the locked Pydantic shape (schema_version: Literal[1] = 1).
// Forces the lock: rejecting v0 + v2+ at parse time so v1 readers cannot
// silently misinterpret future v1.x records as "0% performance".

import { describe, expect, it } from 'vitest'

import { EndorsementSchema } from '../endorsement'

const VALID = {
  schema_version: 1,
  ticker: 'AAPL',
  source: 'Motley Fool',
  date: '2026-04-15',
  price_at_call: 178.42,
  notes: '10-bagger thesis around Vision Pro adoption',
  captured_at: '2026-05-04T19:32:11+00:00',
}

describe('EndorsementSchema', () => {
  it('parses_valid_endorsement — happy-path fields equal input', () => {
    const result = EndorsementSchema.safeParse(VALID)
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.ticker).toBe('AAPL')
      expect(result.data.source).toBe('Motley Fool')
      expect(result.data.date).toBe('2026-04-15')
      expect(result.data.price_at_call).toBe(178.42)
      expect(result.data.schema_version).toBe(1)
    }
  })

  it('rejects_schema_version_2 — v1.x records explicitly fail at parse time', () => {
    const bad = { ...VALID, schema_version: 2 }
    const result = EndorsementSchema.safeParse(bad)
    expect(result.success).toBe(false)
  })

  it('rejects_schema_version_0 — pre-v1 records explicitly fail', () => {
    const bad = { ...VALID, schema_version: 0 }
    const result = EndorsementSchema.safeParse(bad)
    expect(result.success).toBe(false)
  })

  it('rejects_negative_price — gt(0) lock', () => {
    const bad = { ...VALID, price_at_call: -10 }
    const result = EndorsementSchema.safeParse(bad)
    expect(result.success).toBe(false)
  })

  it('rejects_zero_price — gt(0) lock', () => {
    const bad = { ...VALID, price_at_call: 0 }
    const result = EndorsementSchema.safeParse(bad)
    expect(result.success).toBe(false)
  })

  it('rejects_blank_source — min(1) lock', () => {
    const bad = { ...VALID, source: '' }
    const result = EndorsementSchema.safeParse(bad)
    expect(result.success).toBe(false)
  })

  it('rejects_notes_too_long — max(2000) lock', () => {
    const bad = { ...VALID, notes: 'x'.repeat(2001) }
    const result = EndorsementSchema.safeParse(bad)
    expect(result.success).toBe(false)
  })

  it('accepts_notes_at_2000 — boundary check', () => {
    const ok = { ...VALID, notes: 'x'.repeat(2000) }
    const result = EndorsementSchema.safeParse(ok)
    expect(result.success).toBe(true)
  })

  it('rejects_invalid_date_format — non-ISO date string fails', () => {
    const bad = { ...VALID, date: 'April 15 2026' }
    const result = EndorsementSchema.safeParse(bad)
    expect(result.success).toBe(false)
  })

  it('accepts_iso_date_string — happy date parse', () => {
    const ok = { ...VALID, date: '2026-04-15' }
    const result = EndorsementSchema.safeParse(ok)
    expect(result.success).toBe(true)
  })

  it('accepts_empty_notes — default empty string ok', () => {
    const ok = { ...VALID, notes: '' }
    const result = EndorsementSchema.safeParse(ok)
    expect(result.success).toBe(true)
  })

  it('rejects_extra_unknown_field — strict mirrors Pydantic extra=forbid', () => {
    const bad = { ...VALID, bogus_field: 'should-fail' }
    const result = EndorsementSchema.safeParse(bad)
    expect(result.success).toBe(false)
  })
})
