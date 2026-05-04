import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DissentPanel } from '../DissentPanel'
import type { DissentSection } from '@/schemas'

// DissentPanel tests — Pitfall #12 always-render lock + Pitfall #2 Open
// Claude accent treatment lock. 6 tests cover:
//   1. has_dissent: false → muted "All personas converged" panel
//   2. has_dissent: true + generic persona (burry) → amber styling
//   3. has_dissent: true + claude_analyst → ACCENT styling (Pitfall #2)
//   4. has_dissent: true + dissenting_persona null → "Unknown persona"
//   5. has_dissent: true + empty dissent_summary → fallback
//   6. has_dissent: false → STILL rendered (Pitfall #12 explicit guard —
//      asserts panel IS in document, NOT that it's null)

function makeDissent(overrides: Partial<DissentSection> = {}): DissentSection {
  return {
    has_dissent: false,
    dissenting_persona: null,
    dissent_summary: '',
    ...overrides,
  }
}

describe('DissentPanel', () => {
  it('has_dissent: false → muted "All personas converged" panel', () => {
    render(<DissentPanel dissent={makeDissent({ has_dissent: false })} />)
    const panel = screen.getByTestId('dissent-panel')
    expect(panel.getAttribute('data-has-dissent')).toBe('false')
    expect(panel.textContent).toMatch(/All personas converged/)
    expect(panel.textContent).toMatch(/No dissent surfaced/)
  })

  it('has_dissent: true + dissenting_persona="burry" → amber styling, persona label', () => {
    render(
      <DissentPanel
        dissent={makeDissent({
          has_dissent: true,
          dissenting_persona: 'burry',
          dissent_summary:
            'Burry persona flags ≥30-pt confidence gap vs consensus',
        })}
      />,
    )
    const panel = screen.getByTestId('dissent-panel')
    expect(panel.getAttribute('data-has-dissent')).toBe('true')
    expect(panel.getAttribute('data-dissenter')).toBe('burry')
    expect(panel.className).toMatch(/border-amber\/30/)
    expect(panel.textContent).toContain('Michael Burry')
    expect(panel.textContent).toMatch(/≥30-pt confidence gap/)
  })

  it('Pitfall #2: dissenting_persona="claude_analyst" → ACCENT styling, "Open Claude Dissent" header', () => {
    render(
      <DissentPanel
        dissent={makeDissent({
          has_dissent: true,
          dissenting_persona: 'claude_analyst',
          dissent_summary: 'Open Claude flags structural risk obscured by sentiment',
        })}
      />,
    )
    const panel = screen.getByTestId('dissent-panel')
    expect(panel.getAttribute('data-dissenter')).toBe('claude_analyst')
    // Accent treatment — matches OpenClaudePin (Pitfall #2 lock)
    expect(panel.className).toMatch(/border-accent\/40/)
    expect(panel.className).toMatch(/bg-accent\/5/)
    // Header text reads "Open Claude Dissent" (not "Open Claude Analyst Dissents")
    expect(panel.textContent).toMatch(/Open Claude/)
    expect(panel.textContent).toContain('Open Claude Analyst')
  })

  it('has_dissent: true + dissenting_persona=null → "Unknown persona" label, amber styling', () => {
    render(
      <DissentPanel
        dissent={makeDissent({
          has_dissent: true,
          dissenting_persona: null,
          dissent_summary: 'a summary text',
        })}
      />,
    )
    const panel = screen.getByTestId('dissent-panel')
    expect(panel.textContent).toContain('Unknown persona')
    expect(panel.className).toMatch(/border-amber\/30/)
  })

  it('has_dissent: true + empty dissent_summary → fallback "No summary provided"', () => {
    render(
      <DissentPanel
        dissent={makeDissent({
          has_dissent: true,
          dissenting_persona: 'lynch',
          dissent_summary: '',
        })}
      />,
    )
    expect(screen.getByTestId('dissent-summary-missing')).toBeInTheDocument()
    expect(
      screen.getByTestId('dissent-summary-missing').textContent,
    ).toMatch(/No summary provided/)
  })

  it('Pitfall #12 LOCK: has_dissent: false STILL renders the panel (NOT null)', () => {
    render(<DissentPanel dissent={makeDissent({ has_dissent: false })} />)
    // EXPLICIT positive assertion — would fail if component did
    // `if (!has_dissent) return null`
    expect(screen.getByTestId('dissent-panel')).toBeInTheDocument()
  })
})
