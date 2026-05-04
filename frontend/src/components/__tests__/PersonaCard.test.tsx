import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PersonaCard } from '../PersonaCard'
import type { AgentSignal } from '@/schemas'

function makePersona(
  analyst_id: AgentSignal['analyst_id'],
  overrides: Partial<AgentSignal> = {},
): AgentSignal {
  return {
    ticker: 'AAPL',
    analyst_id,
    computed_at: '2026-05-04T12:20:00Z',
    verdict: 'bullish',
    confidence: 65,
    evidence: [
      'AAPL: Wide moat with pricing power',
      'driver one',
      'driver two',
      'driver three',
    ],
    data_unavailable: false,
    ...overrides,
  }
}

describe('PersonaCard', () => {
  it('renders persona label, verdict badge, confidence, reasoning', () => {
    render(<PersonaCard signal={makePersona('buffett')} />)
    expect(screen.getByTestId('persona-label').textContent).toBe('Warren Buffett')
    expect(screen.getByTestId('verdict-badge').textContent).toBe('bullish')
    expect(screen.getByTestId('persona-confidence').textContent).toBe('conf 65')
    expect(screen.getByTestId('persona-reasoning').textContent).toBe(
      'AAPL: Wide moat with pricing power',
    )
  })

  it('maps each canonical persona analyst_id to friendly label', () => {
    const ids: AgentSignal['analyst_id'][] = [
      'buffett',
      'munger',
      'wood',
      'burry',
      'lynch',
    ]
    const expected = [
      'Warren Buffett',
      'Charlie Munger',
      'Cathie Wood',
      'Michael Burry',
      'Peter Lynch',
    ]
    for (let i = 0; i < ids.length; i++) {
      const { unmount } = render(<PersonaCard signal={makePersona(ids[i])} />)
      expect(screen.getByTestId('persona-label').textContent).toBe(expected[i])
      unmount()
    }
  })

  it('renders muted "data unavailable" body when data_unavailable=true', () => {
    render(
      <PersonaCard
        signal={makePersona('buffett', {
          data_unavailable: true,
          verdict: 'neutral',
          confidence: 0,
          evidence: [],
        })}
      />,
    )
    expect(screen.getByTestId('persona-data-unavailable').textContent).toBe(
      'data unavailable',
    )
    // No verdict badge / reasoning rendered when muted
    expect(screen.queryByTestId('verdict-badge')).toBeNull()
    expect(screen.queryByTestId('persona-reasoning')).toBeNull()
    expect(screen.queryByTestId('persona-confidence')).toBeNull()
  })

  it('exposes data-persona attribute for E2E selector hooks', () => {
    render(<PersonaCard signal={makePersona('munger')} />)
    expect(
      screen.getByTestId('persona-card').getAttribute('data-persona'),
    ).toBe('munger')
  })
})
