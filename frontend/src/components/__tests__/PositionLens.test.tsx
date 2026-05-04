import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PositionLens } from '../lenses/PositionLens'
import { makePositionRich } from '../../lib/__tests__/_loadScanFixtures'

describe('PositionLens', () => {
  it('renders empty state when no snapshots have position_signal', () => {
    render(
      <MemoryRouter>
        <PositionLens date="2026-05-04" snapshots={{}} />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('position-lens-empty')).toBeInTheDocument()
  })

  it('sorts rows by |consensus_score| DESCENDING', () => {
    const snapshots = {
      AAPL: makePositionRich('AAPL', -0.65, {
        state: 'oversold',
        action_hint: 'consider_add',
      }),
      NVDA: makePositionRich('NVDA', 0.78, {
        state: 'overbought',
        action_hint: 'consider_take_profits',
      }),
      MSFT: makePositionRich('MSFT', 0.05, {
        state: 'fair',
        action_hint: 'hold_position',
      }),
    }
    render(
      <MemoryRouter>
        <PositionLens date="2026-05-04" snapshots={snapshots} />
      </MemoryRouter>,
    )
    const tickers = screen
      .getAllByTestId('ticker-symbol')
      .map((el) => el.textContent)
    // Expected order: NVDA (|0.78|) → AAPL (|0.65|) → MSFT (|0.05|)
    expect(tickers).toEqual(['NVDA', 'AAPL', 'MSFT'])
  })

  it('drops snapshots with data_unavailable=true position_signal', () => {
    const snapshots = {
      AAPL: makePositionRich('AAPL', -0.65, { state: 'oversold' }),
      // MSFT manually set to data_unavailable=true with canonical no-opinion shape
      MSFT: {
        ...makePositionRich('MSFT', 0, { state: 'fair' }),
        position_signal: {
          ticker: 'MSFT',
          computed_at: new Date().toISOString(),
          state: 'fair' as const,
          consensus_score: 0,
          confidence: 0,
          action_hint: 'hold_position' as const,
          indicators: {},
          evidence: ['data unavailable'],
          data_unavailable: true,
          trend_regime: false,
        },
      },
    }
    render(
      <MemoryRouter>
        <PositionLens date="2026-05-04" snapshots={snapshots} />
      </MemoryRouter>,
    )
    const tickers = screen
      .getAllByTestId('ticker-symbol')
      .map((el) => el.textContent)
    expect(tickers).toEqual(['AAPL'])
  })

  it('renders state, action_hint, and evidence for each row', () => {
    const snapshots = {
      AAPL: makePositionRich('AAPL', -0.65, {
        state: 'oversold',
        action_hint: 'consider_add',
        evidence: ['evidence 1', 'evidence 2'],
      }),
    }
    render(
      <MemoryRouter>
        <PositionLens date="2026-05-04" snapshots={snapshots} />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('position-state').textContent).toBe('state=oversold')
    expect(screen.getByTestId('action-hint-badge').textContent).toBe(
      'consider add',
    )
    expect(screen.getByTestId('evidence-list')).toBeInTheDocument()
  })

  it('each row links to /ticker/:symbol/:date', () => {
    const snapshots = {
      AAPL: makePositionRich('AAPL', -0.65),
    }
    render(
      <MemoryRouter>
        <PositionLens date="2026-05-04" snapshots={snapshots} />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('ticker-card-link').getAttribute('href')).toBe(
      '/ticker/AAPL/2026-05-04',
    )
  })
})
