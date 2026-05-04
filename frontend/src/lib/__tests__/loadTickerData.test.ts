import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// loadTickerData tests — single per-ticker GitHub raw fetch via fetchAndParse.
// Uses the makeSnapshot fixture builder to construct a v2-shape snapshot that
// passes SnapshotSchema. Three failure modes:
//   1. Happy path → returns parsed Snapshot
//   2. 404         → throws FetchNotFoundError
//   3. zod mismatch → throws SchemaMismatchError

import { makeSnapshot } from './_loadScanFixtures'
import {
  FetchNotFoundError,
  SchemaMismatchError,
} from '@/lib/fetchSnapshot'

async function loadTickerModule() {
  const mod = await import('../loadTickerData')
  return mod as unknown as {
    __loadTickerForTest: (
      date: string,
      symbol: string,
    ) => Promise<unknown>
  }
}

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('loadTickerData (__loadTickerForTest)', () => {
  let originalFetch: typeof fetch

  beforeEach(() => {
    originalFetch = global.fetch
  })

  afterEach(() => {
    global.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it('returns parsed Snapshot when fetch + zod parse succeed', async () => {
    const { __loadTickerForTest } = await loadTickerModule()
    global.fetch = vi.fn(async (url: RequestInfo | URL) => {
      const u = String(url)
      if (u.endsWith('AAPL.json')) return jsonResponse(makeSnapshot('AAPL'))
      return new Response('not found', { status: 404 })
    }) as unknown as typeof fetch
    const result = (await __loadTickerForTest('2026-05-04', 'AAPL')) as {
      ticker: string
      schema_version: number
    }
    expect(result.ticker).toBe('AAPL')
    expect(result.schema_version).toBe(2)
  })

  it('throws FetchNotFoundError on 404', async () => {
    const { __loadTickerForTest } = await loadTickerModule()
    global.fetch = vi.fn(
      async () => new Response('nope', { status: 404 }),
    ) as unknown as typeof fetch
    await expect(__loadTickerForTest('2026-05-04', 'AAPL')).rejects.toBeInstanceOf(
      FetchNotFoundError,
    )
  })

  it('throws SchemaMismatchError on zod parse failure (wrong shape)', async () => {
    const { __loadTickerForTest } = await loadTickerModule()
    global.fetch = vi.fn(async () =>
      jsonResponse({ totally: 'wrong shape' }),
    ) as unknown as typeof fetch
    await expect(__loadTickerForTest('2026-05-04', 'AAPL')).rejects.toBeInstanceOf(
      SchemaMismatchError,
    )
  })

  it('throws SchemaMismatchError on schema_version=1 (v1 snapshot rejected)', async () => {
    const { __loadTickerForTest } = await loadTickerModule()
    const v1Snap = { ...makeSnapshot('AAPL'), schema_version: 1 }
    global.fetch = vi.fn(async () =>
      jsonResponse(v1Snap),
    ) as unknown as typeof fetch
    // CONTEXT.md UNIFORM RULE — v1 snapshots MUST surface as schema mismatch.
    await expect(__loadTickerForTest('2026-05-04', 'AAPL')).rejects.toBeInstanceOf(
      SchemaMismatchError,
    )
  })
})
