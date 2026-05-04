// novel-to-this-project — Phase 9 Task 2 loader tests. Two surfaces:
//   1. fetchEndorsementsJsonl — fetch + JSONL line-split + zod-parse + 404 → []
//   2. filterRecent90 — pure helper: ticker filter + 90-day filter on `date`
//      (NOT captured_at, Pitfall #2) + date-desc sort

import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'

import {
  fetchEndorsementsJsonl,
  filterRecent90,
} from '../loadEndorsements'
import { SchemaMismatchError } from '../fetchSnapshot'
import type { Endorsement } from '@/schemas/endorsement'

// Helper — build a valid Endorsement record literal.
function rec(overrides: Partial<Endorsement> = {}): Endorsement {
  return {
    schema_version: 1,
    ticker: 'AAPL',
    source: 'Motley Fool',
    date: '2026-04-15',
    price_at_call: 178.42,
    notes: '',
    captured_at: '2026-05-04T19:32:11+00:00',
    ...overrides,
  }
}

function jsonl(records: object[]): string {
  return records.map((r) => JSON.stringify(r)).join('\n') + '\n'
}

describe('fetchEndorsementsJsonl', () => {
  let fetchSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    fetchSpy = vi.spyOn(globalThis, 'fetch') as unknown as ReturnType<
      typeof vi.spyOn
    >
  })

  afterEach(() => {
    fetchSpy.mockRestore()
  })

  it('returns_empty_on_404 — file optional, never crash', async () => {
    fetchSpy.mockResolvedValue(
      new Response('', { status: 404 }) as unknown as Response,
    )
    const result = await fetchEndorsementsJsonl()
    expect(result).toEqual([])
  })

  it('throws_on_5xx — non-404 non-OK propagates as Error', async () => {
    fetchSpy.mockResolvedValue(
      new Response('', { status: 500 }) as unknown as Response,
    )
    await expect(fetchEndorsementsJsonl()).rejects.toThrow(/500/)
  })

  it('parses_multiple_lines — 3 valid JSONL lines yields 3 records', async () => {
    const body = jsonl([
      rec({ ticker: 'AAPL', source: 'A' }),
      rec({ ticker: 'AAPL', source: 'B' }),
      rec({ ticker: 'MSFT', source: 'C' }),
    ])
    fetchSpy.mockResolvedValue(
      new Response(body, { status: 200 }) as unknown as Response,
    )
    const result = await fetchEndorsementsJsonl()
    expect(result).toHaveLength(3)
    expect(result[0].source).toBe('A')
    expect(result[1].source).toBe('B')
    expect(result[2].source).toBe('C')
  })

  it('skips_blank_lines — `{json}\\n\\n{json}\\n` returns 2 records', async () => {
    const body = JSON.stringify(rec({ source: 'A' })) + '\n\n' +
                 JSON.stringify(rec({ source: 'B' })) + '\n'
    fetchSpy.mockResolvedValue(
      new Response(body, { status: 200 }) as unknown as Response,
    )
    const result = await fetchEndorsementsJsonl()
    expect(result).toHaveLength(2)
  })

  it('throws_SchemaMismatchError_on_invalid_line — schema_version: 99 fails', async () => {
    const body =
      JSON.stringify({ ...rec(), schema_version: 99 }) + '\n'
    fetchSpy.mockResolvedValue(
      new Response(body, { status: 200 }) as unknown as Response,
    )
    await expect(fetchEndorsementsJsonl()).rejects.toBeInstanceOf(
      SchemaMismatchError,
    )
  })

  it('handles_trailing_newline — body ending in `\\n` does not crash on JSON.parse(\'\')', async () => {
    const body = JSON.stringify(rec()) + '\n' // single record + trailing newline
    fetchSpy.mockResolvedValue(
      new Response(body, { status: 200 }) as unknown as Response,
    )
    const result = await fetchEndorsementsJsonl()
    expect(result).toHaveLength(1)
  })
})

describe('filterRecent90', () => {
  // Anchor `now` at 2026-05-04 so the 90-day window is 2026-02-03 (today-90d).
  const NOW = new Date('2026-05-04T12:00:00Z')

  it('filter_by_ticker_active — array of mixed tickers; AAPL filter returns AAPL only', () => {
    const all: Endorsement[] = [
      rec({ ticker: 'AAPL', source: 'A1', date: '2026-04-15' }),
      rec({ ticker: 'AAPL', source: 'A2', date: '2026-04-20' }),
      rec({ ticker: 'MSFT', source: 'M1', date: '2026-04-15' }),
      rec({ ticker: 'GOOGL', source: 'G1', date: '2026-04-15' }),
    ]
    const result = filterRecent90(all, 'AAPL', NOW)
    expect(result).toHaveLength(2)
    expect(result.every((e) => e.ticker === 'AAPL')).toBe(true)
  })

  it('filter_excludes_records_older_than_90_days — date today-91d excluded', () => {
    const all: Endorsement[] = [
      rec({ ticker: 'AAPL', date: '2026-02-02' }), // 91 days ago — EXCLUDE
      rec({ ticker: 'AAPL', date: '2026-02-04' }), // 89 days ago — INCLUDE
    ]
    const result = filterRecent90(all, 'AAPL', NOW)
    expect(result).toHaveLength(1)
    expect(result[0].date).toBe('2026-02-04')
  })

  it('sort_descending_by_date — out-of-order input produces dates[i] >= dates[i+1]', () => {
    const all: Endorsement[] = [
      rec({ ticker: 'AAPL', source: 'mid', date: '2026-04-10' }),
      rec({ ticker: 'AAPL', source: 'newest', date: '2026-04-20' }),
      rec({ ticker: 'AAPL', source: 'oldest', date: '2026-04-01' }),
    ]
    const result = filterRecent90(all, 'AAPL', NOW)
    expect(result.map((e) => e.source)).toEqual(['newest', 'mid', 'oldest'])
  })

  it('filter_uses_call_date_NOT_captured_at — Pitfall #2 lock', () => {
    // Endorsement made 100 days ago (2026-01-24) but captured_at is recent.
    // Filter must EXCLUDE based on `date`, even though `captured_at` is fresh.
    const all: Endorsement[] = [
      rec({
        ticker: 'AAPL',
        date: '2026-01-24', // 100 days before NOW — outside 90-day window
        captured_at: '2026-05-04T10:00:00+00:00', // captured today
      }),
    ]
    const result = filterRecent90(all, 'AAPL', NOW)
    expect(result).toHaveLength(0)
  })

  it('ticker_match_is_uppercase_canonical — symbol arg is upcased before compare', () => {
    const all: Endorsement[] = [rec({ ticker: 'AAPL', date: '2026-04-15' })]
    expect(filterRecent90(all, 'aapl', NOW)).toHaveLength(1)
    expect(filterRecent90(all, 'AAPL', NOW)).toHaveLength(1)
  })
})
