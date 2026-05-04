// novel-to-this-project — Phase 8 Wave 1 mount-point assertion for
// TickerRoute. We mock useTickerData (snapshot fetch) AND useRefreshData
// (refresh fetch) so the test focuses on the route's composition: the
// <CurrentPriceDelta /> mounts when snapshot data is available and the
// data-testid="current-price-placeholder" attribute is preserved through
// the new component.

import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import TickerRoute from '../TickerRoute'
import type { Snapshot } from '@/schemas'

vi.mock('@/lib/loadTickerData', () => ({
  useTickerData: vi.fn(),
}))

vi.mock('@/lib/useRefreshData', () => ({
  useRefreshData: vi.fn(),
}))

// Mock the Chart component — lightweight-charts requires WebGL/canvas APIs
// that jsdom lacks (window.matchMedia, devicePixelRatio observable). The
// component itself is covered by Chart.test.tsx; here we just need a stub
// that renders the container testid so TickerRoute composition is testable.
vi.mock('@/components/Chart', () => ({
  Chart: () => <div data-testid="chart-container" />,
}))

import { useTickerData } from '@/lib/loadTickerData'
import { useRefreshData } from '@/lib/useRefreshData'

const mockedUseTickerData = vi.mocked(useTickerData)
const mockedUseRefreshData = vi.mocked(useRefreshData)

function makeSnapshot(): Snapshot {
  return {
    ticker: 'AAPL',
    schema_version: 2,
    analytical_signals: [],
    position_signal: null,
    persona_signals: [],
    ticker_decision: null,
    ohlc_history: [
      {
        date: '2026-05-04',
        open: 177,
        high: 179,
        low: 176,
        close: 178,
        volume: 1000000,
      },
    ],
    indicators: {
      ma20: [null],
      ma50: [null],
      bb_upper: [null],
      bb_lower: [null],
      rsi14: [null],
    },
    headlines: [],
    errors: [],
  } as unknown as Snapshot
  // (computed_at omitted from this minimal shape — TickerRoute falls back
  //  to position_signal.computed_at then epoch-zero per its own logic.)
}

function renderRoute() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/ticker/AAPL/2026-05-04']}>
        <Routes>
          <Route path="/ticker/:symbol/:date?" element={<TickerRoute />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('TickerRoute mount point', () => {
  it('TickerRoute_mounts_CurrentPriceDelta — placeholder testid present in happy state', () => {
    mockedUseTickerData.mockReturnValue({
      data: makeSnapshot(),
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useTickerData>)
    // Refresh hook mocked to isPending — the component still renders the
    // testid in the loading state, satisfying the grep contract.
    mockedUseRefreshData.mockReturnValue({
      data: undefined,
      isPending: true,
      isError: false,
      isSuccess: false,
      isLoading: true,
      isFetching: true,
      isPlaceholderData: false,
      dataUpdatedAt: 0,
      error: null,
    } as unknown as ReturnType<typeof useRefreshData>)

    renderRoute()
    expect(screen.getByTestId('current-price-placeholder')).toBeInTheDocument()
  })
})
