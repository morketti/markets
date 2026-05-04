import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { z } from 'zod'

import { ErrorBoundary } from '../ErrorBoundary'
import { FetchNotFoundError, SchemaMismatchError } from '@/lib/fetchSnapshot'

// ErrorBoundary tests — three render branches, one passthrough.
//
// React 19 error boundaries log to console.error during recovery — that's
// noisy in test output, so we silence console.error in beforeEach and
// restore in afterEach. We still assert via `componentDidCatch` indirectly
// (the boundary state machine is what matters; the console log is incidental).

function Thrower({ error }: { error: Error }): never {
  throw error
}

function HappyChild() {
  return <div data-testid="happy-child">All good</div>
}

function renderBoundary(child: React.ReactNode) {
  return render(
    <MemoryRouter>
      <ErrorBoundary>{child}</ErrorBoundary>
    </MemoryRouter>,
  )
}

describe('ErrorBoundary', () => {
  let consoleErr: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    consoleErr = vi.spyOn(console, 'error').mockImplementation(() => undefined)
  })

  afterEach(() => {
    consoleErr.mockRestore()
  })

  it('passes through happy children unchanged', () => {
    renderBoundary(<HappyChild />)
    expect(screen.getByTestId('happy-child')).toBeInTheDocument()
  })

  it('renders schema-mismatch UI when child throws SchemaMismatchError', () => {
    // Build a real ZodError by parsing something against z.literal(2)
    const parse = z.literal(2).safeParse(1)
    expect(parse.success).toBe(false)
    const zerr = parse.success
      ? null
      : (parse as { success: false; error: z.ZodError }).error
    if (!zerr) throw new Error('test setup: expected zodError')

    const err = new SchemaMismatchError(
      'https://raw.githubusercontent.com/u/r/main/data/2026-05-04/AAPL.json',
      zerr,
    )
    renderBoundary(<Thrower error={err} />)
    expect(
      screen.getByTestId('error-boundary-schema-mismatch'),
    ).toBeInTheDocument()
    // Schema-mismatch wording surfaces both versions
    expect(screen.getByText(/Schema version mismatch/i)).toBeInTheDocument()
    expect(screen.getByText(/v2/i)).toBeInTheDocument()
  })

  it('renders schema-mismatch UI surfacing the offending URL', () => {
    const parse = z.object({ a: z.string() }).safeParse({ a: 1 })
    const zerr = parse.success
      ? null
      : (parse as { success: false; error: z.ZodError }).error
    if (!zerr) throw new Error('test setup: expected zodError')

    const url = 'https://raw.githubusercontent.com/u/r/main/data/2026-05-04/_index.json'
    const err = new SchemaMismatchError(url, zerr)
    renderBoundary(<Thrower error={err} />)
    expect(screen.getByText(url)).toBeInTheDocument()
  })

  it('renders ticker-not-found UI when FetchNotFoundError points at a per-ticker JSON', () => {
    const err = new FetchNotFoundError(
      'https://raw.githubusercontent.com/u/r/main/data/2026-05-04/AAPL.json',
    )
    renderBoundary(<Thrower error={err} />)
    const region = screen.getByTestId('error-boundary-not-found')
    expect(region).toBeInTheDocument()
    expect(region.getAttribute('data-kind')).toBe('ticker')
    // Ticker + date both surfaced in the heading
    expect(screen.getByText(/AAPL not in run for 2026-05-04/i)).toBeInTheDocument()
  })

  it('renders snapshot-not-found UI when FetchNotFoundError points at _index.json', () => {
    const err = new FetchNotFoundError(
      'https://raw.githubusercontent.com/u/r/main/data/2099-12-31/_index.json',
    )
    renderBoundary(<Thrower error={err} />)
    const region = screen.getByTestId('error-boundary-not-found')
    expect(region).toBeInTheDocument()
    expect(region.getAttribute('data-kind')).toBe('snapshot')
    expect(screen.getByText(/No snapshot for 2099-12-31/i)).toBeInTheDocument()
  })

  it('renders snapshot-not-found UI when FetchNotFoundError points at _status.json', () => {
    const err = new FetchNotFoundError(
      'https://raw.githubusercontent.com/u/r/main/data/2099-12-31/_status.json',
    )
    renderBoundary(<Thrower error={err} />)
    const region = screen.getByTestId('error-boundary-not-found')
    expect(region.getAttribute('data-kind')).toBe('snapshot')
  })

  it('renders generic UI for plain Error', () => {
    const err = new Error('Something broke')
    renderBoundary(<Thrower error={err} />)
    expect(
      screen.getByTestId('error-boundary-generic'),
    ).toBeInTheDocument()
    expect(screen.getByText(/Something went wrong/i)).toBeInTheDocument()
    expect(screen.getByText(/Something broke/)).toBeInTheDocument()
  })

  it('every error branch exposes a Reload/back link', () => {
    // Schema branch
    const parse = z.literal(2).safeParse(1)
    const zerr = parse.success
      ? null
      : (parse as { success: false; error: z.ZodError }).error
    if (!zerr) throw new Error('test setup: expected zodError')

    const { unmount } = renderBoundary(
      <Thrower
        error={
          new SchemaMismatchError(
            'https://raw.githubusercontent.com/u/r/main/data/2026-05-04/AAPL.json',
            zerr,
          )
        }
      />,
    )
    expect(screen.getByTestId('error-boundary-reset')).toBeInTheDocument()
    unmount()

    // Not-found branch
    const { unmount: u2 } = renderBoundary(
      <Thrower
        error={
          new FetchNotFoundError(
            'https://raw.githubusercontent.com/u/r/main/data/2026-05-04/AAPL.json',
          )
        }
      />,
    )
    expect(screen.getByTestId('error-boundary-reset')).toBeInTheDocument()
    u2()

    // Generic branch
    renderBoundary(<Thrower error={new Error('boom')} />)
    expect(screen.getByTestId('error-boundary-reset')).toBeInTheDocument()
  })
})
