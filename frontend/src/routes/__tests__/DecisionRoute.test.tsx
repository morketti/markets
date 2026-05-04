import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import DecisionRoute from '../DecisionRoute'
import type { Snapshot, TickerDecision } from '@/schemas'
import {
  FetchNotFoundError,
  SchemaMismatchError,
} from '@/lib/fetchSnapshot'

// DecisionRoute tests — 5 cases mirroring TickerRoute's loading/error/data
// branches, plus the data_unavailable=true happy path. We mock useTickerData
// at the loadTickerData module boundary; this keeps the test focused on the
// route's composition + branch logic.

vi.mock('@/lib/loadTickerData', () => ({
  useTickerData: vi.fn(),
}))

import { useTickerData } from '@/lib/loadTickerData'
const mockedUseTickerData = vi.mocked(useTickerData)

function makeDecision(overrides: Partial<TickerDecision> = {}): TickerDecision {
  return {
    ticker: 'AAPL',
    computed_at: '2026-05-04T12:28:00Z',
    schema_version: 2,
    recommendation: 'buy',
    conviction: 'medium',
    short_term: {
      summary: 'AAPL short-term: buy',
      drivers: ['short A', 'short B'],
      confidence: 80,
      thesis_status: 'n/a',
    },
    long_term: {
      summary: 'AAPL long-term thesis: intact',
      drivers: ['long A', 'long B'],
      confidence: 70,
      thesis_status: 'intact',
    },
    open_observation: 'AAPL: open observation text',
    dissent: {
      has_dissent: true,
      dissenting_persona: 'burry',
      dissent_summary: 'AAPL: Burry persona flags risk',
    },
    data_unavailable: false,
    ...overrides,
  }
}

function makeSnapshot(decision: TickerDecision | null): Snapshot {
  return {
    ticker: 'AAPL',
    schema_version: 2,
    analytical_signals: [],
    position_signal: null,
    persona_signals: [],
    ticker_decision: decision,
    ohlc_history: [],
    indicators: {
      ma20: [],
      ma50: [],
      bb_upper: [],
      bb_lower: [],
      rsi14: [],
    },
    headlines: [],
    errors: [],
  }
}

function renderRoute() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/decision/AAPL/2026-05-04']}>
        <Routes>
          <Route
            path="/decision/:symbol/:date?"
            element={<DecisionRoute />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('DecisionRoute', () => {
  it('loading branch → renders decision-loading testid', () => {
    mockedUseTickerData.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as unknown as ReturnType<typeof useTickerData>)
    renderRoute()
    expect(screen.getByTestId('decision-loading')).toBeInTheDocument()
  })

  it('FetchNotFoundError → 404 banner with "{symbol} not in snapshot for {date}"', () => {
    mockedUseTickerData.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new FetchNotFoundError('https://example/AAPL.json'),
    } as unknown as ReturnType<typeof useTickerData>)
    renderRoute()
    const errBox = screen.getByTestId('decision-error')
    expect(errBox.textContent).toContain('AAPL not in snapshot for 2026-05-04')
  })

  it('SchemaMismatchError → "Schema upgrade required" banner', () => {
    // Construct a SchemaMismatchError with a minimal ZodError stub
    const stubErr = {
      issues: [],
      message: 'parse failed',
    } as unknown as import('zod').ZodError
    mockedUseTickerData.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new SchemaMismatchError('https://example/AAPL.json', stubErr),
    } as unknown as ReturnType<typeof useTickerData>)
    renderRoute()
    const errBox = screen.getByTestId('decision-error')
    expect(errBox.textContent).toContain('Schema upgrade required')
  })

  it('happy has_dissent: true → banner + drivers + dissent + Phase 8 placeholder all present', () => {
    mockedUseTickerData.mockReturnValue({
      data: makeSnapshot(makeDecision()),
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useTickerData>)
    renderRoute()
    expect(screen.getByTestId('recommendation-banner')).toBeInTheDocument()
    expect(screen.getByTestId('drivers-list')).toBeInTheDocument()
    const dissentPanel = screen.getByTestId('dissent-panel')
    expect(dissentPanel.getAttribute('data-has-dissent')).toBe('true')
    // Phase 8 hookpoint — load-bearing for downstream grep
    expect(
      screen.getByTestId('current-price-placeholder'),
    ).toBeInTheDocument()
  })

  it('data_unavailable: true → muted notice ABOVE banner, Hold/low rendered', () => {
    mockedUseTickerData.mockReturnValue({
      data: makeSnapshot(
        makeDecision({
          data_unavailable: true,
          recommendation: 'hold',
          conviction: 'low',
        }),
      ),
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useTickerData>)
    renderRoute()
    expect(screen.getByTestId('data-unavailable-notice')).toBeInTheDocument()
    const banner = screen.getByTestId('recommendation-banner')
    expect(banner.getAttribute('data-recommendation')).toBe('hold')
    expect(banner.getAttribute('data-conviction')).toBe('low')
  })
})
