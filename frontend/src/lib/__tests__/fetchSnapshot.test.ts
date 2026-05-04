import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { z } from 'zod'

import {
  FetchNotFoundError,
  RAW_BASE,
  SchemaMismatchError,
  datesUrl,
  fetchAndParse,
  indexUrl,
  snapshotUrl,
  statusUrl,
} from '../fetchSnapshot'

// Tiny inline schema — keeps fetch tests focused on the fetch + parse
// behavior, not the real snapshot shape (which is exhaustively tested
// elsewhere in src/schemas/__tests__/).
const TinySchema = z.object({ foo: z.string() })

function mockFetch(impl: (url: string) => Response | Promise<Response>): void {
  vi.stubGlobal(
    'fetch',
    vi.fn(((input: RequestInfo | URL) => Promise.resolve(impl(String(input)))) as typeof fetch),
  )
}

describe('fetchAndParse', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('happy path — parses 200 + valid JSON via the supplied schema', async () => {
    mockFetch(() =>
      new Response(JSON.stringify({ foo: 'bar' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    const result = await fetchAndParse('https://example.test/x.json', TinySchema)
    expect(result).toEqual({ foo: 'bar' })
  })

  it('throws FetchNotFoundError on 404', async () => {
    mockFetch(() => new Response('not found', { status: 404 }))
    await expect(
      fetchAndParse('https://example.test/missing.json', TinySchema),
    ).rejects.toBeInstanceOf(FetchNotFoundError)
  })

  it('FetchNotFoundError carries the offending url', async () => {
    mockFetch(() => new Response('not found', { status: 404 }))
    try {
      await fetchAndParse('https://example.test/missing.json', TinySchema)
      expect.fail('should have thrown FetchNotFoundError')
    } catch (e) {
      expect(e).toBeInstanceOf(FetchNotFoundError)
      expect((e as FetchNotFoundError).url).toBe(
        'https://example.test/missing.json',
      )
    }
  })

  it('throws generic Error on non-404 non-2xx (e.g. 500)', async () => {
    mockFetch(() => new Response('server error', { status: 500 }))
    await expect(
      fetchAndParse('https://example.test/oops.json', TinySchema),
    ).rejects.toThrow(/500/)
  })

  it('throws SchemaMismatchError on zod parse failure', async () => {
    mockFetch(() =>
      new Response(JSON.stringify({ wrong_field: 42 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    await expect(
      fetchAndParse('https://example.test/bad.json', TinySchema),
    ).rejects.toBeInstanceOf(SchemaMismatchError)
  })

  it('SchemaMismatchError carries the url AND the underlying zodError', async () => {
    mockFetch(() =>
      new Response(JSON.stringify({ wrong_field: 42 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    try {
      await fetchAndParse('https://example.test/bad.json', TinySchema)
      expect.fail('should have thrown SchemaMismatchError')
    } catch (e) {
      expect(e).toBeInstanceOf(SchemaMismatchError)
      const err = e as SchemaMismatchError
      expect(err.url).toBe('https://example.test/bad.json')
      expect(err.zodError).toBeDefined()
      expect(err.zodError.issues.length).toBeGreaterThan(0)
    }
  })

  it('Accept header set to application/json', async () => {
    const fetchSpy = vi.fn(((_input: RequestInfo | URL) =>
      Promise.resolve(
        new Response(JSON.stringify({ foo: 'x' }), { status: 200 }),
      )) as typeof fetch)
    vi.stubGlobal('fetch', fetchSpy)
    await fetchAndParse('https://example.test/y.json', TinySchema)
    const call = fetchSpy.mock.calls[0]
    expect(call?.[1]).toMatchObject({
      headers: { Accept: 'application/json' },
    })
  })
})

describe('URL builders', () => {
  it('RAW_BASE points at raw.githubusercontent.com (CDN read path)', () => {
    expect(RAW_BASE).toMatch(/^https:\/\/raw\.githubusercontent\.com\//)
  })

  it('snapshotUrl assembles per-ticker JSON path', () => {
    const url = snapshotUrl('2026-05-04', 'NVDA')
    expect(url).toMatch(/\/data\/2026-05-04\/NVDA\.json$/)
    expect(url.startsWith(RAW_BASE)).toBe(true)
  })

  it('indexUrl assembles _index.json path for the given date', () => {
    expect(indexUrl('2026-05-04')).toMatch(/\/data\/2026-05-04\/_index\.json$/)
  })

  it('statusUrl assembles _status.json path for the given date', () => {
    expect(statusUrl('2026-05-04')).toMatch(/\/data\/2026-05-04\/_status\.json$/)
  })

  it('datesUrl points at repo-root data/_dates.json', () => {
    expect(datesUrl()).toMatch(/\/data\/_dates\.json$/)
  })
})

describe('SchemaMismatchError', () => {
  it('has name = SchemaMismatchError', () => {
    const fakeZodError = TinySchema.safeParse({}).success
      ? null
      : (TinySchema.safeParse({}) as { success: false; error: z.ZodError }).error
    if (!fakeZodError) {
      throw new Error('test setup: expected parse failure')
    }
    const err = new SchemaMismatchError('https://x.test/y.json', fakeZodError)
    expect(err.name).toBe('SchemaMismatchError')
    expect(err.url).toBe('https://x.test/y.json')
  })
})

describe('FetchNotFoundError', () => {
  it('has name = FetchNotFoundError', () => {
    const err = new FetchNotFoundError('https://x.test/missing.json')
    expect(err.name).toBe('FetchNotFoundError')
    expect(err.url).toBe('https://x.test/missing.json')
    expect(err.message).toContain('Not found')
  })
})
