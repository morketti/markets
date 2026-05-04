import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { OpenClaudePin } from '../OpenClaudePin'
import type { AgentSignal } from '@/schemas'

function makeClaude(overrides: Partial<AgentSignal> = {}): AgentSignal {
  return {
    ticker: 'AAPL',
    analyst_id: 'claude_analyst',
    computed_at: '2026-05-04T12:20:00Z',
    verdict: 'neutral',
    confidence: 55,
    evidence: [
      'AAPL: Mixed signals — directional view low conviction',
      'driver alpha',
      'driver beta',
    ],
    data_unavailable: false,
    ...overrides,
  }
}

describe('OpenClaudePin', () => {
  it('renders accent-styled pin with label, verdict, confidence, reasoning', () => {
    render(<OpenClaudePin signal={makeClaude()} />)
    expect(screen.getByTestId('open-claude-pin')).toBeInTheDocument()
    expect(screen.getByTestId('open-claude-label').textContent).toBe(
      'Open Claude Analyst',
    )
    expect(screen.getByTestId('verdict-badge').textContent).toBe('neutral')
    expect(screen.getByTestId('open-claude-reasoning').textContent).toBe(
      'AAPL: Mixed signals — directional view low conviction',
    )
  })

  it('applies accent border + accent-tinted background class (CONTEXT.md visual lock)', () => {
    render(<OpenClaudePin signal={makeClaude()} />)
    const pin = screen.getByTestId('open-claude-pin')
    expect(pin.className).toMatch(/border-accent\/40/)
    expect(pin.className).toMatch(/bg-accent\/5/)
  })

  it('VIEW-09 LOCK: always renders even when signal is undefined', () => {
    // Wave 3 invariant — claude_analyst missing from snapshot.persona_signals
    // (e.g. lite-mode skipped persona LLM): pin still in DOM with muted state.
    render(<OpenClaudePin signal={undefined} />)
    expect(screen.getByTestId('open-claude-pin')).toBeInTheDocument()
    expect(
      screen.getByTestId('open-claude-data-unavailable').textContent,
    ).toMatch(/data unavailable/i)
    expect(
      screen.getByTestId('open-claude-pin').getAttribute('data-muted'),
    ).toBe('true')
  })

  it('VIEW-09 LOCK: always renders even when data_unavailable=true', () => {
    render(
      <OpenClaudePin
        signal={makeClaude({
          data_unavailable: true,
          verdict: 'neutral',
          confidence: 0,
          evidence: [],
        })}
      />,
    )
    expect(screen.getByTestId('open-claude-pin')).toBeInTheDocument()
    expect(
      screen.getByTestId('open-claude-data-unavailable'),
    ).toBeInTheDocument()
    // No verdict badge / reasoning when muted
    expect(screen.queryByTestId('verdict-badge')).toBeNull()
    expect(screen.queryByTestId('open-claude-reasoning')).toBeNull()
  })

  it('renders up to 4 evidence bullets', () => {
    render(
      <OpenClaudePin
        signal={makeClaude({
          evidence: [
            'reasoning summary',
            'driver 1',
            'driver 2',
            'driver 3',
            'driver 4',
            'driver 5',
            'driver 6',
          ],
        })}
      />,
    )
    const ul = screen.getByTestId('open-claude-evidence')
    expect(ul.querySelectorAll('li')).toHaveLength(4)
  })
})
