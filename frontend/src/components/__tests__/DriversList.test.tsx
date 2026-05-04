import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DriversList } from '../DriversList'
import type { TimeframeBand } from '@/schemas'

// DriversList tests — 4 cases over (short populated/empty) × (long populated/
// empty). UNIFORM RULE (CONTEXT.md): when drivers.length === 0 the card is
// STILL rendered (empty-state copy "No drivers surfaced") — never collapsed.
// Cards always come in a side-by-side pair on lg, stacked on mobile.

function makeBand(
  drivers: string[],
  confidence = 70,
  thesis: TimeframeBand['thesis_status'] = 'intact',
): TimeframeBand {
  return {
    summary: 'summary text',
    drivers,
    confidence,
    thesis_status: thesis,
  }
}

describe('DriversList', () => {
  it('short populated + long populated → both cards have <li> children, no empty-state', () => {
    render(
      <DriversList
        shortTerm={makeBand(['short driver A', 'short driver B'])}
        longTerm={makeBand(['long driver A', 'long driver B', 'long driver C'])}
      />,
    )
    const cards = screen.getAllByTestId('drivers-card')
    expect(cards.length).toBe(2)
    const shortCard = cards.find(
      (c) => c.getAttribute('data-timeframe') === 'short_term',
    )!
    const longCard = cards.find(
      (c) => c.getAttribute('data-timeframe') === 'long_term',
    )!
    expect(shortCard.querySelectorAll('li').length).toBe(2)
    expect(longCard.querySelectorAll('li').length).toBe(3)
    expect(screen.queryByTestId('drivers-empty')).toBeNull()
  })

  it('short empty + long populated → short card has empty-state, long card has <li>', () => {
    render(
      <DriversList
        shortTerm={makeBand([])}
        longTerm={makeBand(['long alpha', 'long beta'])}
      />,
    )
    const cards = screen.getAllByTestId('drivers-card')
    expect(cards.length).toBe(2)
    const shortCard = cards.find(
      (c) => c.getAttribute('data-timeframe') === 'short_term',
    )!
    const longCard = cards.find(
      (c) => c.getAttribute('data-timeframe') === 'long_term',
    )!
    expect(shortCard.querySelector('[data-testid="drivers-empty"]')).not.toBeNull()
    expect(longCard.querySelectorAll('li').length).toBe(2)
  })

  it('short populated + long empty → short card has <li>, long card has empty-state', () => {
    render(
      <DriversList
        shortTerm={makeBand(['short A'])}
        longTerm={makeBand([])}
      />,
    )
    const cards = screen.getAllByTestId('drivers-card')
    const shortCard = cards.find(
      (c) => c.getAttribute('data-timeframe') === 'short_term',
    )!
    const longCard = cards.find(
      (c) => c.getAttribute('data-timeframe') === 'long_term',
    )!
    expect(shortCard.querySelectorAll('li').length).toBe(1)
    expect(longCard.querySelector('[data-testid="drivers-empty"]')).not.toBeNull()
  })

  it('UNIFORM RULE: both empty → both cards rendered with empty-state (NEVER collapsed)', () => {
    render(<DriversList shortTerm={makeBand([])} longTerm={makeBand([])} />)
    const cards = screen.getAllByTestId('drivers-card')
    // Both cards STILL present — slot not collapsed even when both empty
    expect(cards.length).toBe(2)
    const empties = screen.getAllByTestId('drivers-empty')
    expect(empties.length).toBe(2)
  })
})
