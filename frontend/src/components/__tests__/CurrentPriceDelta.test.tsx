// novel-to-this-project — Phase 8 Wave 1 component tests for the
// <CurrentPriceDelta /> hero element. Mocks useRefreshData at the module
// boundary so the test exercises render branches (loading / 4 happy /
// partial / full-failure / isError) without any TanStack Query setup.

import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'

import type { RefreshResponse } from '@/schemas/refresh'

vi.mock('@/lib/useRefreshData', () => ({
  useRefreshData: vi.fn(),
}))

import { useRefreshData } from '@/lib/useRefreshData'
import { CurrentPriceDelta } from '../CurrentPriceDelta'

const mockedHook = vi.mocked(useRefreshData)

type HookReturn = ReturnType<typeof useRefreshData>

function makeReturn(overrides: Partial<HookReturn>): HookReturn {
  return {
    data: undefined,
    isPending: false,
    isError: false,
    isSuccess: false,
    isLoading: false,
    isFetching: false,
    isPlaceholderData: false,
    dataUpdatedAt: Date.now(),
    error: null,
    ...overrides,
  } as unknown as HookReturn
}

const SUCCESS: RefreshResponse = {
  ticker: 'AAPL',
  current_price: 180.0,
  price_timestamp: '2026-05-04T19:32:11+00:00',
  recent_headlines: [],
  errors: [],
  partial: false,
}

const PARTIAL: RefreshResponse = {
  ticker: 'AAPL',
  current_price: 178.42,
  price_timestamp: '2026-05-04T19:32:11+00:00',
  recent_headlines: [],
  errors: ['rss-unavailable'],
  partial: true,
}

const FAILURE: RefreshResponse = {
  ticker: 'AAPL',
  error: true,
  errors: ['yfinance-unavailable', 'yahooquery-unavailable'],
  partial: true,
}

describe('CurrentPriceDelta', () => {
  beforeEach(() => {
    mockedHook.mockReset()
  })

  it('renders_loading_state — isPending shows muted "Refreshing" + preserves data-testid', () => {
    mockedHook.mockReturnValue(makeReturn({ isPending: true }))
    render(<CurrentPriceDelta symbol="AAPL" snapshotLastPrice={178} />)
    const el = screen.getByTestId('current-price-placeholder')
    expect(el).toBeInTheDocument()
    expect(el.textContent).toMatch(/Refreshing/i)
  })

  it('renders_success_with_positive_delta — bullish color class', () => {
    mockedHook.mockReturnValue(
      makeReturn({ data: SUCCESS, isSuccess: true }),
    )
    const { container } = render(
      <CurrentPriceDelta
        symbol="AAPL"
        snapshotLastPrice={178}
        snapshotComputedAt="2026-05-04T12:00:00Z"
      />,
    )
    const el = screen.getByTestId('current-price-placeholder')
    expect(el).toBeInTheDocument()
    expect(el.textContent).toContain('$180.00')
    // delta = (180 - 178) / 178 = +1.12%
    expect(el.textContent).toContain('+1.12%')
    // bullish color via CSS-variable token (no inline hex).
    expect(container.innerHTML).toMatch(/text-bullish/)
  })

  it('renders_success_with_negative_delta — bearish color class', () => {
    const negData: RefreshResponse = { ...SUCCESS, current_price: 176 }
    mockedHook.mockReturnValue(
      makeReturn({ data: negData, isSuccess: true }),
    )
    const { container } = render(
      <CurrentPriceDelta symbol="AAPL" snapshotLastPrice={178} />,
    )
    const el = screen.getByTestId('current-price-placeholder')
    expect(el.textContent).toContain('$176.00')
    // delta = (176 - 178) / 178 = -1.12% (rendered with minus sign of any kind)
    expect(el.textContent).toMatch(/[-−]1\.12%/)
    expect(container.innerHTML).toMatch(/text-bearish/)
  })

  it('renders_zero_delta_neutral — same prices, no bullish/bearish class on the delta', () => {
    const sameData: RefreshResponse = { ...SUCCESS, current_price: 178 }
    mockedHook.mockReturnValue(
      makeReturn({ data: sameData, isSuccess: true }),
    )
    render(<CurrentPriceDelta symbol="AAPL" snapshotLastPrice={178} />)
    const el = screen.getByTestId('current-price-placeholder')
    expect(el.textContent).toContain('$178.00')
    expect(el.textContent).toContain('0.00%')
    // Zero delta — the delta span uses the muted token (no color class).
    const deltaSpan = el.querySelector('[data-testid="price-delta"]')
    expect(deltaSpan).not.toBeNull()
    expect(deltaSpan?.className).not.toMatch(/text-bullish|text-bearish/)
  })

  it('renders_no_snapshot_price_baseline — no delta % when snapshotLastPrice undefined', () => {
    mockedHook.mockReturnValue(
      makeReturn({ data: SUCCESS, isSuccess: true }),
    )
    render(<CurrentPriceDelta symbol="AAPL" />)
    const el = screen.getByTestId('current-price-placeholder')
    expect(el.textContent).toContain('$180.00')
    // No delta percentage rendered when there's no baseline.
    expect(el.querySelector('[data-testid="price-delta"]')).toBeNull()
  })

  it('renders_partial_response — current_price renders + Headlines unavailable note', () => {
    mockedHook.mockReturnValue(
      makeReturn({ data: PARTIAL, isSuccess: true }),
    )
    render(<CurrentPriceDelta symbol="AAPL" snapshotLastPrice={178} />)
    const el = screen.getByTestId('current-price-placeholder')
    expect(el.textContent).toContain('$178.42')
    expect(el.textContent).toMatch(/Headlines unavailable/i)
  })

  it('renders_full_failure_envelope — "Refresh unavailable" notice, snapshot price as fallback', () => {
    mockedHook.mockReturnValue(
      makeReturn({ data: FAILURE, isSuccess: true }),
    )
    render(<CurrentPriceDelta symbol="AAPL" snapshotLastPrice={178} />)
    const el = screen.getByTestId('current-price-placeholder')
    expect(el).toBeInTheDocument()
    expect(el.textContent).toMatch(/Refresh unavailable/i)
    expect(el.textContent).toContain('$178.00')
  })

  it('renders_isError_fallback — network failure falls back to snapshot price', () => {
    mockedHook.mockReturnValue(
      makeReturn({ isError: true, error: new Error('boom') }),
    )
    render(<CurrentPriceDelta symbol="AAPL" snapshotLastPrice={178} />)
    const el = screen.getByTestId('current-price-placeholder')
    expect(el).toBeInTheDocument()
    expect(el.textContent).toMatch(/Refresh unavailable|showing snapshot price/i)
    expect(el.textContent).toContain('$178.00')
  })

  it('renders_isError_fallback_no_baseline — gracefully shows em-dash when no snapshot', () => {
    mockedHook.mockReturnValue(makeReturn({ isError: true }))
    render(<CurrentPriceDelta symbol="AAPL" />)
    const el = screen.getByTestId('current-price-placeholder')
    expect(el).toBeInTheDocument()
    expect(el.textContent).toMatch(/Refresh unavailable/i)
    // No snapshot baseline — em-dash rendered (NEVER a crash).
    expect(el.textContent).toMatch(/—|\$—/)
  })
})
