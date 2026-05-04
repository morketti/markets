import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { ShortTermLens } from '../lenses/ShortTermLens'
import { makePositionRich } from '../../lib/__tests__/_loadScanFixtures'

describe('ShortTermLens', () => {
  it('renders empty state when no snapshots have a bullish recommendation', () => {
    const snapshots = {
      AAPL: makePositionRich('AAPL', 0, {
        short_term_recommendation: 'hold',
        short_term_confidence: 50,
      }),
    }
    render(
      <MemoryRouter>
        <ShortTermLens date="2026-05-04" snapshots={snapshots} />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('short-term-lens-empty')).toBeInTheDocument()
  })

  it('filters to bullish-direction (add/buy) recommendations only', () => {
    const snapshots = {
      AAPL: makePositionRich('AAPL', 0, {
        short_term_recommendation: 'add',
        short_term_confidence: 70,
      }),
      NVDA: makePositionRich('NVDA', 0, {
        short_term_recommendation: 'take_profits',
        short_term_confidence: 80,
      }),
      MSFT: makePositionRich('MSFT', 0, {
        short_term_recommendation: 'buy',
        short_term_confidence: 85,
      }),
      TSLA: makePositionRich('TSLA', 0, {
        short_term_recommendation: 'hold',
        short_term_confidence: 90,
      }),
    }
    render(
      <MemoryRouter>
        <ShortTermLens date="2026-05-04" snapshots={snapshots} />
      </MemoryRouter>,
    )
    const tickers = screen
      .getAllByTestId('ticker-symbol')
      .map((el) => el.textContent)
    // AAPL (add, 70) and MSFT (buy, 85) survive. NVDA (take_profits) and TSLA (hold) drop out.
    expect(tickers.sort()).toEqual(['AAPL', 'MSFT'])
  })

  it('sorts surviving rows by short_term.confidence DESCENDING', () => {
    const snapshots = {
      AAPL: makePositionRich('AAPL', 0, {
        short_term_recommendation: 'add',
        short_term_confidence: 70,
      }),
      MSFT: makePositionRich('MSFT', 0, {
        short_term_recommendation: 'buy',
        short_term_confidence: 85,
      }),
      GOOG: makePositionRich('GOOG', 0, {
        short_term_recommendation: 'add',
        short_term_confidence: 50,
      }),
    }
    render(
      <MemoryRouter>
        <ShortTermLens date="2026-05-04" snapshots={snapshots} />
      </MemoryRouter>,
    )
    const tickers = screen
      .getAllByTestId('ticker-symbol')
      .map((el) => el.textContent)
    // Expected: MSFT (85) → AAPL (70) → GOOG (50)
    expect(tickers).toEqual(['MSFT', 'AAPL', 'GOOG'])
  })

  it('renders recommendation badge and short_term summary', () => {
    const snapshots = {
      AAPL: makePositionRich('AAPL', 0, {
        short_term_recommendation: 'buy',
        short_term_confidence: 85,
      }),
    }
    render(
      <MemoryRouter>
        <ShortTermLens date="2026-05-04" snapshots={snapshots} />
      </MemoryRouter>,
    )
    expect(
      screen.getByTestId('short-term-recommendation').getAttribute('data-recommendation'),
    ).toBe('buy')
    expect(screen.getByTestId('short-term-summary').textContent).toBe(
      'AAPL short-term summary',
    )
  })

  it('row links to /ticker/:symbol/:date', () => {
    const snapshots = {
      AAPL: makePositionRich('AAPL', 0, {
        short_term_recommendation: 'add',
        short_term_confidence: 60,
      }),
    }
    render(
      <MemoryRouter>
        <ShortTermLens date="2026-05-04" snapshots={snapshots} />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('ticker-card-link').getAttribute('href')).toBe(
      '/ticker/AAPL/2026-05-04',
    )
  })
})
