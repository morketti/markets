import { describe, expect, it } from 'vitest'

import { DatesIndexSchema } from '../dates_index'

describe('DatesIndexSchema', () => {
  it('parses a happy-path dates index', () => {
    const parsed = DatesIndexSchema.parse({
      schema_version: 1,
      dates_available: ['2026-04-30', '2026-05-01', '2026-05-04'],
      updated_at: '2026-05-04T13:55:55Z',
    })
    expect(parsed.schema_version).toBe(1)
    expect(parsed.dates_available).toHaveLength(3)
  })

  it('parses an empty dates index (first run, no folders yet)', () => {
    const parsed = DatesIndexSchema.parse({
      schema_version: 1,
      dates_available: [],
      updated_at: '2026-05-04T13:55:55Z',
    })
    expect(parsed.dates_available).toEqual([])
  })

  it('REJECTS schema_version != 1', () => {
    const result = DatesIndexSchema.safeParse({
      schema_version: 2,
      dates_available: [],
      updated_at: '2026-05-04T13:55:55Z',
    })
    expect(result.success).toBe(false)
  })

  it('rejects malformed date string', () => {
    const result = DatesIndexSchema.safeParse({
      schema_version: 1,
      dates_available: ['2026/05/04'],
      updated_at: '2026-05-04T13:55:55Z',
    })
    expect(result.success).toBe(false)
  })

  it('rejects partial date string (missing day)', () => {
    const result = DatesIndexSchema.safeParse({
      schema_version: 1,
      dates_available: ['2026-05'],
      updated_at: '2026-05-04T13:55:55Z',
    })
    expect(result.success).toBe(false)
  })

  it('does NOT enforce sortedness (storage.py guarantees but schema is loose)', () => {
    // Per CONTEXT.md: storage.py writes them sorted; the schema accepts any
    // order so we don't accidentally reject a manually-edited index that's
    // technically valid.
    const parsed = DatesIndexSchema.parse({
      schema_version: 1,
      dates_available: ['2026-05-04', '2026-04-30', '2026-05-01'],
      updated_at: '2026-05-04T13:55:55Z',
    })
    expect(parsed.dates_available).toEqual([
      '2026-05-04',
      '2026-04-30',
      '2026-05-01',
    ])
  })

  it('rejects missing updated_at field', () => {
    const result = DatesIndexSchema.safeParse({
      schema_version: 1,
      dates_available: ['2026-05-04'],
    })
    expect(result.success).toBe(false)
  })
})
