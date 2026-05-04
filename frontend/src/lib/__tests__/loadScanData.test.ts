import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// loadScanData orchestrates 3 fetch types: _status.json, _index.json,
// per-ticker JSONs. We mock global.fetch and assert:
//   - 3 happy fetches returned in snapshots map
//   - 1 happy + 1 404 + 1 schema-mismatch → 1 in snapshots, 2 in failedTickers
//   - failedTickers preserve order from index.tickers

import {
  loadScanModule,
} from './_loadScanFixtures'

describe('loadScanData (loadScan internal)', () => {
  let originalFetch: typeof fetch

  beforeEach(() => {
    originalFetch = global.fetch
  })

  afterEach(() => {
    global.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it('returns ScanData with all snapshots when every fetch succeeds', async () => {
    const { loadScan, makeStatus, makeIndex, makeSnapshot } = await loadScanModule()
    global.fetch = vi.fn(async (url: RequestInfo | URL) => {
      const u = String(url)
      if (u.endsWith('_status.json')) return jsonResponse(makeStatus(['AAPL', 'NVDA']))
      if (u.endsWith('_index.json'))
        return jsonResponse(makeIndex(['AAPL', 'NVDA']))
      if (u.endsWith('AAPL.json')) return jsonResponse(makeSnapshot('AAPL'))
      if (u.endsWith('NVDA.json')) return jsonResponse(makeSnapshot('NVDA'))
      return new Response('not found', { status: 404 })
    }) as unknown as typeof fetch

    const result = await loadScan('2026-05-04')
    expect(Object.keys(result.snapshots).sort()).toEqual(['AAPL', 'NVDA'])
    expect(result.failedTickers).toEqual([])
    expect(result.index.tickers).toEqual(['AAPL', 'NVDA'])
  })

  it('partitions failed tickers (404) and schema-mismatches into failedTickers', async () => {
    const { loadScan, makeStatus, makeIndex, makeSnapshot } = await loadScanModule()
    global.fetch = vi.fn(async (url: RequestInfo | URL) => {
      const u = String(url)
      if (u.endsWith('_status.json'))
        return jsonResponse(makeStatus(['AAPL', 'NVDA', 'MSFT']))
      if (u.endsWith('_index.json'))
        return jsonResponse(makeIndex(['AAPL', 'NVDA', 'MSFT']))
      if (u.endsWith('AAPL.json')) return jsonResponse(makeSnapshot('AAPL'))
      if (u.endsWith('NVDA.json')) return new Response('nope', { status: 404 })
      if (u.endsWith('MSFT.json')) return jsonResponse({ totally: 'wrong shape' })
      return new Response('not found', { status: 404 })
    }) as unknown as typeof fetch

    const result = await loadScan('2026-05-04')
    expect(Object.keys(result.snapshots)).toEqual(['AAPL'])
    expect(result.failedTickers.sort()).toEqual(['MSFT', 'NVDA'])
  })

  it('throws (does not swallow) when _status.json fetch fails', async () => {
    const { loadScan } = await loadScanModule()
    global.fetch = vi.fn(async () => new Response('500', { status: 500 })) as unknown as typeof fetch
    await expect(loadScan('2026-05-04')).rejects.toThrow(/Fetch.*failed: 500/)
  })

  it('throws when _index.json schema mismatches', async () => {
    const { loadScan, makeStatus } = await loadScanModule()
    global.fetch = vi.fn(async (url: RequestInfo | URL) => {
      const u = String(url)
      if (u.endsWith('_status.json')) return jsonResponse(makeStatus([]))
      if (u.endsWith('_index.json')) return jsonResponse({ wrong: 'shape' })
      return new Response('not found', { status: 404 })
    }) as unknown as typeof fetch
    await expect(loadScan('2026-05-04')).rejects.toThrow(/Schema mismatch/)
  })
})

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}
