import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { TickerCard } from '../TickerCard'

// TickerCard tests — confirms ticker symbol rendered in mono font, lens-
// specific children rendered inside, and the click-through Link href is
// /ticker/:symbol/:date.

describe('TickerCard', () => {
  it('renders ticker text in mono font', () => {
    render(
      <MemoryRouter>
        <TickerCard ticker="AAPL" date="2026-05-04">
          <span>content</span>
        </TickerCard>
      </MemoryRouter>,
    )
    const symbol = screen.getByTestId('ticker-symbol')
    expect(symbol.textContent).toBe('AAPL')
    expect(symbol.className).toMatch(/font-mono/)
  })

  it('renders children inside the card body', () => {
    render(
      <MemoryRouter>
        <TickerCard ticker="NVDA" date="2026-05-04">
          <span data-testid="lens-content">lens-specific content</span>
        </TickerCard>
      </MemoryRouter>,
    )
    expect(screen.getByTestId('lens-content').textContent).toBe(
      'lens-specific content',
    )
  })

  it('href deep-links to /ticker/:symbol/:date', () => {
    render(
      <MemoryRouter>
        <TickerCard ticker="AAPL" date="2026-05-04">
          <span>x</span>
        </TickerCard>
      </MemoryRouter>,
    )
    const link = screen.getByTestId('ticker-card-link')
    expect(link.getAttribute('href')).toBe('/ticker/AAPL/2026-05-04')
  })

  it('uses Notion-Clean palette tokens (bg-surface + border-border)', () => {
    const { container } = render(
      <MemoryRouter>
        <TickerCard ticker="MSFT" date="2026-05-04">
          <span>x</span>
        </TickerCard>
      </MemoryRouter>,
    )
    // The Card child div carries the palette classes
    const card = container.querySelector('[data-testid="ticker-card-link"] > div')
    expect(card?.className).toMatch(/bg-surface/)
    expect(card?.className).toMatch(/border-border/)
  })
})
