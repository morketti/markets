// novel-to-this-project — Phase 8 Wave 1 TanStack hook tests. Mocks
// fetchAndParse via vi.mock('@/lib/fetchSnapshot', ...) so the test exercises
// the hook's queryKey / staleTime / placeholderData / retry behavior without
// going near the real fetch.

import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import {
  QueryClient,
  QueryClientProvider,
  type QueryClientConfig,
} from '@tanstack/react-query'
import React from 'react'

import type { RefreshResponse } from '@/schemas/refresh'

// Mock fetchAndParse at the module boundary. The hook imports it from
// @/lib/fetchSnapshot — we replace that single export with a vi.fn().
vi.mock('@/lib/fetchSnapshot', async () => {
  const actual = await vi.importActual<typeof import('@/lib/fetchSnapshot')>(
    '@/lib/fetchSnapshot',
  )
  return {
    ...actual,
    fetchAndParse: vi.fn(),
  }
})

import { fetchAndParse } from '@/lib/fetchSnapshot'
import { useRefreshData } from '../useRefreshData'

const mockedFetch = vi.mocked(fetchAndParse) as unknown as ReturnType<
  typeof vi.fn
>

const SUCCESS: RefreshResponse = {
  ticker: 'AAPL',
  current_price: 178.42,
  price_timestamp: '2026-05-04T19:32:11+00:00',
  recent_headlines: [],
  errors: [],
  partial: false,
}

const SUCCESS_MSFT: RefreshResponse = {
  ...SUCCESS,
  ticker: 'MSFT',
  current_price: 420.5,
}

function makeWrapper(config?: QueryClientConfig) {
  const qc = new QueryClient(
    config ?? {
      defaultOptions: { queries: { retry: 1, gcTime: 0 } },
    },
  )
  return {
    qc,
    wrapper: ({ children }: { children: React.ReactNode }) =>
      React.createElement(QueryClientProvider, { client: qc }, children),
  }
}

describe('useRefreshData', () => {
  beforeEach(() => {
    mockedFetch.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns_data_on_success — happy path resolves with current_price', async () => {
    mockedFetch.mockResolvedValueOnce(SUCCESS)
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useRefreshData('AAPL'), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toBeDefined()
    if (result.current.data && 'current_price' in result.current.data) {
      expect(result.current.data.current_price).toBe(178.42)
    }
  })

  it('error_state_on_500 — fetch rejection sets isError', async () => {
    mockedFetch.mockRejectedValue(new Error('500 Internal Server Error'))
    const { wrapper } = makeWrapper({
      defaultOptions: { queries: { retry: 1, gcTime: 0, staleTime: 0 } },
    })
    const { result } = renderHook(() => useRefreshData('AAPL'), { wrapper })

    await waitFor(() => expect(result.current.isError).toBe(true), {
      timeout: 3000,
    })
    expect(result.current.data).toBeUndefined()
  })

  it('dedup_by_query_key — two hooks on same symbol share one fetch', async () => {
    mockedFetch.mockResolvedValue(SUCCESS)
    const { wrapper } = makeWrapper()

    // Render TWO hooks on the same symbol in the same QueryClient.
    const { result: r1 } = renderHook(() => useRefreshData('AAPL'), { wrapper })
    const { result: r2 } = renderHook(() => useRefreshData('AAPL'), { wrapper })

    await waitFor(() => {
      expect(r1.current.isSuccess).toBe(true)
      expect(r2.current.isSuccess).toBe(true)
    })

    // TanStack Query dedupes by queryKey: ['refresh', symbol] — only ONE
    // network call even though TWO hooks mounted on the same symbol.
    expect(mockedFetch).toHaveBeenCalledTimes(1)
  })

  it('stale_time_5_minutes — re-render within 5min does not refetch', async () => {
    mockedFetch.mockResolvedValue(SUCCESS)
    const { wrapper, qc } = makeWrapper()
    const { result, rerender } = renderHook(() => useRefreshData('AAPL'), {
      wrapper,
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockedFetch).toHaveBeenCalledTimes(1)

    // Re-render — within staleTime window the cached value is fresh, no new
    // fetch fires.
    rerender()
    expect(mockedFetch).toHaveBeenCalledTimes(1)
    // Verify the query reports as fresh (not stale) — proxy for staleTime.
    const state = qc.getQueryState(['refresh', 'AAPL'])
    expect(state?.dataUpdateCount).toBe(1)
  })

  it('retry_count_one — failure retries once total (2 attempts)', async () => {
    mockedFetch.mockRejectedValue(new Error('boom'))
    const { wrapper } = makeWrapper({
      defaultOptions: { queries: { retry: 1, gcTime: 0, staleTime: 0 } },
    })
    const { result } = renderHook(() => useRefreshData('AAPL'), { wrapper })

    await waitFor(() => expect(result.current.isError).toBe(true), {
      timeout: 3000,
    })
    // retry: 1 → 1 initial + 1 retry = 2 total invocations.
    expect(mockedFetch).toHaveBeenCalledTimes(2)
  })

  it('keep_previous_data_on_symbol_swap — AAPL data lingers while MSFT loads', async () => {
    // First call (AAPL) resolves immediately; second call (MSFT) is held
    // pending so we can observe placeholderData behavior mid-swap.
    let resolveMsft: ((v: RefreshResponse) => void) | null = null
    const msftPromise = new Promise<RefreshResponse>((resolve) => {
      resolveMsft = resolve
    })
    mockedFetch.mockResolvedValueOnce(SUCCESS).mockReturnValueOnce(msftPromise)

    const { wrapper } = makeWrapper()
    let symbol = 'AAPL'
    const { result, rerender } = renderHook(() => useRefreshData(symbol), {
      wrapper,
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    if (result.current.data && 'current_price' in result.current.data) {
      expect(result.current.data.current_price).toBe(178.42)
    }

    // Swap symbol → MSFT. While MSFT is pending, data should STILL point at
    // the AAPL response (keepPreviousData behavior). isPlaceholderData=true.
    symbol = 'MSFT'
    rerender()
    // Mid-flight — MSFT promise unresolved, but data still defined.
    expect(result.current.data).toBeDefined()
    if (result.current.data && 'current_price' in result.current.data) {
      // Still the AAPL price — proves placeholderData: keepPreviousData.
      expect(result.current.data.current_price).toBe(178.42)
    }

    // Resolve MSFT — now data should swap to MSFT.
    await act(async () => {
      resolveMsft?.(SUCCESS_MSFT)
      await msftPromise
    })
    await waitFor(() => {
      const d = result.current.data
      if (d && 'current_price' in d) {
        expect(d.current_price).toBe(420.5)
      }
    })
  })

  it('does_not_fetch_when_symbol_is_empty — enabled gate', async () => {
    mockedFetch.mockResolvedValue(SUCCESS)
    const { wrapper } = makeWrapper()
    const { result } = renderHook(() => useRefreshData(''), { wrapper })

    // Brief wait — enabled: false means no fetch fires.
    await new Promise((r) => setTimeout(r, 50))
    expect(mockedFetch).not.toHaveBeenCalled()
    expect(result.current.isPending).toBe(true)
  })
})
