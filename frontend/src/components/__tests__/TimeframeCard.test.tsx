import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TimeframeCard } from '../TimeframeCard'
import type { TimeframeBand } from '@/schemas'

function makeBand(overrides: Partial<TimeframeBand> = {}): TimeframeBand {
  return {
    summary: 'AAPL short-term: add',
    drivers: ['driver 1', 'driver 2', 'driver 3', 'driver 4', 'driver 5', 'driver 6'],
    confidence: 70,
    thesis_status: 'n/a',
    ...overrides,
  }
}

describe('TimeframeCard', () => {
  it('renders label, status badge, confidence, summary', () => {
    render(<TimeframeCard label="Short-Term (1w-1m)" band={makeBand()} />)
    expect(screen.getByTestId('timeframe-label').textContent).toBe(
      'Short-Term (1w-1m)',
    )
    expect(screen.getByTestId('thesis-status-badge').textContent).toBe('n/a')
    expect(screen.getByTestId('timeframe-confidence').textContent).toBe(
      'conf 70',
    )
    expect(screen.getByTestId('timeframe-summary').textContent).toBe(
      'AAPL short-term: add',
    )
  })

  it('caps drivers list at top 5', () => {
    render(<TimeframeCard label="x" band={makeBand()} />)
    const drivers = screen.getByTestId('timeframe-drivers')
    expect(drivers.querySelectorAll('li')).toHaveLength(5)
  })

  it('renders no drivers list when band.drivers is empty', () => {
    render(<TimeframeCard label="x" band={makeBand({ drivers: [] })} />)
    expect(screen.queryByTestId('timeframe-drivers')).toBeNull()
  })

  it.each([
    ['intact', 'text-bullish'],
    ['improving', 'text-bullish'],
    ['weakening', 'text-amber'],
    ['broken', 'text-bearish'],
    ['n/a', 'text-fg-muted'],
  ] as const)('maps %s thesis_status to %s color class', (status, color) => {
    const band = makeBand({ thesis_status: status })
    const { unmount } = render(<TimeframeCard label="x" band={band} />)
    const badge = screen.getByTestId('thesis-status-badge')
    expect(badge.className).toContain(color)
    expect(badge.getAttribute('data-thesis-status')).toBe(status)
    unmount()
  })
})
