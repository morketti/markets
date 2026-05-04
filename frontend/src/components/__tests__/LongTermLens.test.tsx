import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { LongTermLens } from '../lenses/LongTermLens'
import { makePositionRich } from '../../lib/__tests__/_loadScanFixtures'

describe('LongTermLens', () => {
  it('renders empty state when no thesis is weakening or broken', () => {
    const snapshots = {
      AAPL: makePositionRich('AAPL', 0, { long_term_thesis_status: 'intact' }),
      NVDA: makePositionRich('NVDA', 0, { long_term_thesis_status: 'improving' }),
    }
    render(
      <MemoryRouter>
        <LongTermLens date="2026-05-04" snapshots={snapshots} />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('long-term-lens-empty')).toBeInTheDocument()
  })

  it('filters to thesis_status ∈ {weakening, broken} only', () => {
    const snapshots = {
      AAPL: makePositionRich('AAPL', 0, { long_term_thesis_status: 'intact' }),
      NVDA: makePositionRich('NVDA', 0, { long_term_thesis_status: 'broken' }),
      MSFT: makePositionRich('MSFT', 0, { long_term_thesis_status: 'weakening' }),
      TSLA: makePositionRich('TSLA', 0, { long_term_thesis_status: 'improving' }),
      GOOG: makePositionRich('GOOG', 0, { long_term_thesis_status: 'n/a' }),
    }
    render(
      <MemoryRouter>
        <LongTermLens date="2026-05-04" snapshots={snapshots} />
      </MemoryRouter>,
    )
    const tickers = screen
      .getAllByTestId('ticker-symbol')
      .map((el) => el.textContent)
    expect(tickers.sort()).toEqual(['MSFT', 'NVDA'])
  })

  it('sorts broken first, then weakening, then by confidence ASC', () => {
    const snapshots = {
      // Two weakening with different confidence; broken should come first
      MSFT: makePositionRich('MSFT', 0, {
        long_term_thesis_status: 'weakening',
        long_term_confidence: 70,
      }),
      AAPL: makePositionRich('AAPL', 0, {
        long_term_thesis_status: 'weakening',
        long_term_confidence: 30,
      }),
      NVDA: makePositionRich('NVDA', 0, {
        long_term_thesis_status: 'broken',
        long_term_confidence: 60,
      }),
    }
    render(
      <MemoryRouter>
        <LongTermLens date="2026-05-04" snapshots={snapshots} />
      </MemoryRouter>,
    )
    const tickers = screen
      .getAllByTestId('ticker-symbol')
      .map((el) => el.textContent)
    // Broken first (NVDA), then weakening sorted by confidence ASC (AAPL@30 → MSFT@70)
    expect(tickers).toEqual(['NVDA', 'AAPL', 'MSFT'])
  })

  it('renders thesis_status pill and long_term summary', () => {
    const snapshots = {
      NVDA: makePositionRich('NVDA', 0, { long_term_thesis_status: 'broken' }),
    }
    render(
      <MemoryRouter>
        <LongTermLens date="2026-05-04" snapshots={snapshots} />
      </MemoryRouter>,
    )
    const thesis = screen.getByTestId('thesis-status')
    expect(thesis.getAttribute('data-thesis')).toBe('broken')
    expect(thesis.textContent).toBe('thesis: broken')
    expect(screen.getByTestId('long-term-summary').textContent).toBe(
      'NVDA long-term summary',
    )
  })

  it('row links to /ticker/:symbol/:date', () => {
    const snapshots = {
      NVDA: makePositionRich('NVDA', 0, { long_term_thesis_status: 'broken' }),
    }
    render(
      <MemoryRouter>
        <LongTermLens date="2026-05-04" snapshots={snapshots} />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('ticker-card-link').getAttribute('href')).toBe(
      '/ticker/NVDA/2026-05-04',
    )
  })
})
