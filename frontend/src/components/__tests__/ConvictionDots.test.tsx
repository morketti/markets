import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ConvictionDots } from '../ConvictionDots'

// ConvictionDots — 3-dot conviction indicator (1/2/3 filled for low/medium/
// high). Pitfall #6 guard: ALWAYS renders 3 dots in total — never collapses
// to N children when filled<3. The "empty" trailing dots provide the visual
// scan-friendly secondary cue that conviction is a 1-of-3 / 2-of-3 / 3-of-3.

describe('ConvictionDots', () => {
  it('low conviction → 1 filled + 2 empty (3 total dots)', () => {
    render(<ConvictionDots filled={1} />)
    const container = screen.getByTestId('conviction-dots')
    expect(container.getAttribute('data-filled')).toBe('1')
    const dots = container.querySelectorAll('[data-testid="conviction-dot"]')
    expect(dots.length).toBe(3)
    const filled = container.querySelectorAll('[data-state="filled"]')
    const empty = container.querySelectorAll('[data-state="empty"]')
    expect(filled.length).toBe(1)
    expect(empty.length).toBe(2)
  })

  it('medium conviction → 2 filled + 1 empty (3 total dots)', () => {
    render(<ConvictionDots filled={2} />)
    const container = screen.getByTestId('conviction-dots')
    expect(container.getAttribute('data-filled')).toBe('2')
    const dots = container.querySelectorAll('[data-testid="conviction-dot"]')
    expect(dots.length).toBe(3)
    const filled = container.querySelectorAll('[data-state="filled"]')
    const empty = container.querySelectorAll('[data-state="empty"]')
    expect(filled.length).toBe(2)
    expect(empty.length).toBe(1)
  })

  it('high conviction → 3 filled + 0 empty (3 total dots)', () => {
    render(<ConvictionDots filled={3} />)
    const container = screen.getByTestId('conviction-dots')
    expect(container.getAttribute('data-filled')).toBe('3')
    const dots = container.querySelectorAll('[data-testid="conviction-dot"]')
    expect(dots.length).toBe(3)
    const filled = container.querySelectorAll('[data-state="filled"]')
    const empty = container.querySelectorAll('[data-state="empty"]')
    expect(filled.length).toBe(3)
    expect(empty.length).toBe(0)
  })
})
