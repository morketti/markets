import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RecommendationBanner } from '../RecommendationBanner'
import type { ConvictionBand, DecisionRecommendation } from '@/schemas'

// RecommendationBanner test surface — 6 actions × 3 conviction bands = 18
// matrix tests + 1 a11y test = 19 total. Locked color × weight matrix from
// CONTEXT.md / PLAN frontmatter:
//
//   add → bullish/10 + bullish text + bullish/30 border
//   buy → bullish/15 + bullish text + bullish/40 border
//   hold → fg-muted/10 + fg-muted text + fg-muted/30 border
//   trim → amber/10 + amber text + amber/30 border
//   take_profits → amber/15 + amber text + amber/40 border
//   avoid → bearish/10 + bearish text + bearish/30 border
//
//   low → text-2xl font-medium  (1 filled dot)
//   medium → text-3xl font-semibold  (2 filled dots)
//   high → text-4xl font-bold  (3 filled dots)

const ACTIONS: ReadonlyArray<DecisionRecommendation> = [
  'add',
  'buy',
  'hold',
  'trim',
  'take_profits',
  'avoid',
]
const CONVICTIONS: ReadonlyArray<ConvictionBand> = ['low', 'medium', 'high']

const ACTION_COLOR_TOKEN: Record<DecisionRecommendation, string> = {
  add: 'bullish/10',
  buy: 'bullish/15',
  hold: 'fg-muted/10',
  trim: 'amber/10',
  take_profits: 'amber/15',
  avoid: 'bearish/10',
}

const ACTION_LABEL: Record<DecisionRecommendation, string> = {
  add: 'Add',
  buy: 'Buy',
  hold: 'Hold',
  trim: 'Trim',
  take_profits: 'Take Profits',
  avoid: 'Avoid',
}

const CONVICTION_FONT: Record<ConvictionBand, string> = {
  low: 'text-2xl',
  medium: 'text-3xl',
  high: 'text-4xl',
}

const CONVICTION_DOTS: Record<ConvictionBand, number> = {
  low: 1,
  medium: 2,
  high: 3,
}

describe('RecommendationBanner — 6×3 matrix', () => {
  for (const action of ACTIONS) {
    for (const conviction of CONVICTIONS) {
      it(`renders ${action} × ${conviction} with correct color + weight tokens`, () => {
        render(
          <RecommendationBanner
            recommendation={action}
            conviction={conviction}
          />,
        )
        const banner = screen.getByTestId('recommendation-banner')
        expect(banner.getAttribute('data-recommendation')).toBe(action)
        expect(banner.getAttribute('data-conviction')).toBe(conviction)
        // Action drives color
        expect(banner.className).toContain(`bg-${ACTION_COLOR_TOKEN[action]}`)
        // Action label visible
        expect(banner.textContent).toContain(ACTION_LABEL[action])
        // Conviction drives visual weight (font size)
        expect(banner.innerHTML).toContain(CONVICTION_FONT[conviction])
        // ConvictionDots embedded with correct filled count
        const dots = screen.getByTestId('conviction-dots')
        expect(dots.getAttribute('data-filled')).toBe(
          String(CONVICTION_DOTS[conviction]),
        )
      })
    }
  }
})

describe('RecommendationBanner — a11y', () => {
  it('has role="status" and aria-label combining action + conviction', () => {
    render(<RecommendationBanner recommendation="take_profits" conviction="high" />)
    const banner = screen.getByTestId('recommendation-banner')
    expect(banner.getAttribute('role')).toBe('status')
    const label = banner.getAttribute('aria-label') ?? ''
    expect(label).toContain('Take Profits')
    expect(label).toContain('high')
  })
})
