import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { FetchNotFoundError } from '@/lib/fetchSnapshot'

// loadDates tests — the dates index loader is a thin TanStack-Query wrapper
// around fetchAndParse(datesUrl(), DatesIndexSchema). We test the loader
// function directly via the __loadDatesForTest export — three failure paths:
//   1. Happy path → parsed DatesIndex
//   2. 404 → FetchNotFoundError (UI gracefully degrades to 'today'-only)
//   3. Wrong shape → SchemaMismatchError

async function loadDatesModule() {
  const mod = await import('../loadDates')
  return mod as unknown as {
    __loadDatesForTest: () => Promise<unknown>
  }
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('loadDates (__loadDatesForTest)', () => {
  let originalFetch: typeof fetch

  beforeEach(() => {
    originalFetch = global.fetch
  })

  afterEach(() => {
    global.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it('returns parsed DatesIndex on happy path', async () => {
    const { __loadDatesForTest } = await loadDatesModule()
    global.fetch = vi.fn(async () =>
      jsonResponse({
        schema_version: 1,
        dates_available: ['2026-04-30', '2026-05-01', '2026-05-04'],
        updated_at: '2026-05-04T12:00:00Z',
      }),
    ) as unknown as typeof fetch
    const result = (await __loadDatesForTest()) as {
      dates_available: string[]
    }
    expect(result.dates_available).toEqual([
      '2026-04-30',
      '2026-05-01',
      '2026-05-04',
    ])
  })

  it('throws FetchNotFoundError on 404 (first-deploy scenario)', async () => {
    const { __loadDatesForTest } = await loadDatesModule()
    global.fetch = vi.fn(async () =>
      new Response('not found', { status: 404 }),
    ) as unknown as typeof fetch
    // Caller (DateSelector) handles the rejection by rendering only 'today'
    // — but the loader itself should surface the 404 as a FetchNotFoundError.
    await expect(__loadDatesForTest()).rejects.toBeInstanceOf(
      FetchNotFoundError,
    )
  })

  it('throws on wrong schema_version (DatesIndexSchema is z.literal(1))', async () => {
    const { __loadDatesForTest } = await loadDatesModule()
    global.fetch = vi.fn(async () =>
      jsonResponse({
        schema_version: 2, // wrong — schema is locked to literal 1
        dates_available: ['2026-05-04'],
        updated_at: '2026-05-04T12:00:00Z',
      }),
    ) as unknown as typeof fetch
    await expect(__loadDatesForTest()).rejects.toBeDefined()
  })

  it('rejects malformed date strings (not YYYY-MM-DD)', async () => {
    const { __loadDatesForTest } = await loadDatesModule()
    global.fetch = vi.fn(async () =>
      jsonResponse({
        schema_version: 1,
        dates_available: ['not-a-date'],
        updated_at: '2026-05-04T12:00:00Z',
      }),
    ) as unknown as typeof fetch
    await expect(__loadDatesForTest()).rejects.toBeDefined()
  })
})
