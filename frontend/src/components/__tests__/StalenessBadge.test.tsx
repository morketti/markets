import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StalenessBadge } from '../StalenessBadge'

// StalenessBadge tests — Wave 1's computeStaleness has 16 boundary tests; here
// we just confirm the component wires the level → color class mapping correctly
// and surfaces the snapshot age + partial flag in the title tooltip.

const NOW = new Date('2026-05-04T14:00:00Z')

function isoMinusHours(hours: number): string {
  return new Date(NOW.getTime() - hours * 3_600_000).toISOString()
}

describe('StalenessBadge', () => {
  it('renders GREEN level when age < 6h and not partial', () => {
    render(<StalenessBadge snapshotIso={isoMinusHours(1)} partial={false} now={NOW} />)
    const badge = screen.getByTestId('staleness-badge')
    expect(badge).toHaveAttribute('data-level', 'GREEN')
    expect(badge.textContent).toBe('GREEN')
    // Notion-Clean palette token: bullish color class applied
    expect(badge.className).toMatch(/text-bullish/)
  })

  it('renders AMBER level when age is 12h', () => {
    render(<StalenessBadge snapshotIso={isoMinusHours(12)} partial={false} now={NOW} />)
    const badge = screen.getByTestId('staleness-badge')
    expect(badge).toHaveAttribute('data-level', 'AMBER')
    expect(badge.className).toMatch(/text-amber/)
  })

  it('renders RED level when age > 24h', () => {
    render(<StalenessBadge snapshotIso={isoMinusHours(30)} partial={false} now={NOW} />)
    const badge = screen.getByTestId('staleness-badge')
    expect(badge).toHaveAttribute('data-level', 'RED')
    expect(badge.className).toMatch(/text-bearish/)
  })

  it('renders AMBER when age < 6h but partial=true', () => {
    render(<StalenessBadge snapshotIso={isoMinusHours(1)} partial={true} now={NOW} />)
    const badge = screen.getByTestId('staleness-badge')
    expect(badge).toHaveAttribute('data-level', 'AMBER')
  })

  it('surfaces age in title tooltip', () => {
    render(<StalenessBadge snapshotIso={isoMinusHours(2)} partial={false} now={NOW} />)
    const badge = screen.getByTestId('staleness-badge')
    expect(badge.getAttribute('title')).toMatch(/2\.0h/)
  })

  it('surfaces partial detail in title when partial=true', () => {
    render(<StalenessBadge snapshotIso={isoMinusHours(1)} partial={true} now={NOW} />)
    const badge = screen.getByTestId('staleness-badge')
    expect(badge.getAttribute('title')).toMatch(/partial/)
  })
})
