import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { VerdictBadge } from '../VerdictBadge'
import { ActionHintBadge } from '../ActionHintBadge'

// Smoke tests for the lightweight badge components — verify color mapping
// applied per state and the verdict/hint text rendered.

describe('VerdictBadge', () => {
  it('renders bullish color for strong_bullish', () => {
    render(<VerdictBadge verdict="strong_bullish" />)
    const badge = screen.getByTestId('verdict-badge')
    expect(badge).toHaveAttribute('data-verdict', 'strong_bullish')
    expect(badge.className).toMatch(/text-bullish/)
  })

  it('renders neutral muted color', () => {
    render(<VerdictBadge verdict="neutral" />)
    expect(screen.getByTestId('verdict-badge').className).toMatch(/text-fg-muted/)
  })

  it('renders bearish color for strong_bearish', () => {
    render(<VerdictBadge verdict="strong_bearish" />)
    expect(screen.getByTestId('verdict-badge').className).toMatch(/text-bearish/)
  })
})

describe('ActionHintBadge', () => {
  it('renders bullish color for consider_add', () => {
    render(<ActionHintBadge hint="consider_add" />)
    const badge = screen.getByTestId('action-hint-badge')
    expect(badge).toHaveAttribute('data-hint', 'consider_add')
    expect(badge.className).toMatch(/text-bullish/)
    expect(badge.textContent).toBe('consider add')
  })

  it('renders amber color for consider_trim', () => {
    render(<ActionHintBadge hint="consider_trim" />)
    expect(screen.getByTestId('action-hint-badge').className).toMatch(/text-amber/)
  })

  it('renders bearish color for consider_take_profits', () => {
    render(<ActionHintBadge hint="consider_take_profits" />)
    expect(screen.getByTestId('action-hint-badge').className).toMatch(/text-bearish/)
  })

  it('renders muted color for hold_position', () => {
    render(<ActionHintBadge hint="hold_position" />)
    expect(screen.getByTestId('action-hint-badge').className).toMatch(/text-fg-muted/)
  })
})
