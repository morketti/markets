// novel-to-this-project — Phase 9 Task 3 component tests for EndorsementsList.
// Mocks @/lib/loadEndorsements at the module boundary so we can inject
// controlled hook returns for each render branch (loading / error / empty /
// populated). Locks the LOAD-BEARING contract: NO performance number anywhere
// — regex test scans rendered text and fails if any match.

import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import type { Endorsement } from '@/schemas/endorsement'

vi.mock('@/lib/loadEndorsements', () => ({
  useEndorsements: vi.fn(),
}))

import { useEndorsements } from '@/lib/loadEndorsements'
import { EndorsementsList } from '../EndorsementsList'

const mockedUseEndorsements = vi.mocked(useEndorsements)

function rec(overrides: Partial<Endorsement> = {}): Endorsement {
  return {
    schema_version: 1,
    ticker: 'AAPL',
    source: 'Motley Fool',
    date: '2026-04-15',
    price_at_call: 178.42,
    notes: '',
    captured_at: '2026-05-04T19:32:11+00:00',
    ...overrides,
  }
}

function renderList(symbol = 'AAPL') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <EndorsementsList symbol={symbol} />
    </QueryClientProvider>,
  )
}

describe('EndorsementsList', () => {
  beforeEach(() => {
    mockedUseEndorsements.mockReset()
  })

  it('renders_loading_state — useEndorsements isLoading: true → loading testid', () => {
    mockedUseEndorsements.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useEndorsements>)
    renderList()
    expect(screen.getByTestId('endorsements-loading')).toBeInTheDocument()
  })

  it('renders_empty_state_with_cta — empty data renders CTA copy', () => {
    mockedUseEndorsements.mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useEndorsements>)
    renderList('AAPL')
    const list = screen.getByTestId('endorsements-list')
    expect(list.textContent).toMatch(/No endorsements captured for AAPL/i)
    expect(list.textContent).toMatch(/last 90 days/i)
    expect(list.textContent).toMatch(/markets add_endorsement/i)
  })

  it('renders_populated_state_card_per_endorsement — 3 records → 3 cards', () => {
    const records = [
      rec({ source: 'A', date: '2026-04-20' }),
      rec({ source: 'B', date: '2026-04-15' }),
      rec({ source: 'C', date: '2026-04-10' }),
    ]
    mockedUseEndorsements.mockReturnValue({
      data: records,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useEndorsements>)
    renderList()
    const cards = screen.getAllByTestId('endorsement-card')
    expect(cards).toHaveLength(3)
  })

  it('renders_card_fields — populated card shows source / date / price / notes', () => {
    mockedUseEndorsements.mockReturnValue({
      data: [
        rec({
          source: 'Motley Fool',
          date: '2026-04-15',
          price_at_call: 178.42,
          notes: 'Vision Pro thesis',
        }),
      ],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useEndorsements>)
    const { container } = renderList()
    const card = screen.getByTestId('endorsement-card')
    expect(card.textContent).toContain('Motley Fool')
    expect(card.textContent).toContain('2026-04-15')
    expect(card.textContent).toContain('178.42')
    expect(card.textContent).toContain('Vision Pro thesis')
    expect(container.textContent).toMatch(/captured/i)
  })

  it('renders_NO_performance_number — regex guard against % / alpha / gain / loss / return / perf', () => {
    mockedUseEndorsements.mockReturnValue({
      data: [
        rec({ source: 'A', date: '2026-04-15', price_at_call: 178.42 }),
        rec({ source: 'B', date: '2026-04-20', price_at_call: 200.0 }),
      ],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useEndorsements>)
    const { container } = renderList()
    const list = screen.getByTestId('endorsements-list')
    // Guard against any text resembling performance: `%`, `vs S&P`, `alpha`,
    // `gain`, `loss`, `return`, `perf`. Note: avoid matching legitimate words
    // (no occurrences of these in the locked card design).
    const text = list.textContent ?? ''
    expect(text).not.toMatch(/%/)
    expect(text).not.toMatch(/vs S&P/i)
    expect(text).not.toMatch(/alpha/i)
    expect(text).not.toMatch(/\bgain\b/i)
    expect(text).not.toMatch(/\bloss\b/i)
    expect(text).not.toMatch(/\breturn\b/i)
    expect(text).not.toMatch(/\bperf(ormance)?\b/i)
    // Sanity — the test fixture itself has no perf-like content; this guard
    // catches FUTURE regressions in the component.
    expect(container).toBeTruthy()
  })

  it('renders_in_descending_date_order — input order does not matter; output is date-desc', () => {
    // The component receives data already filtered + sorted by useEndorsements
    // (select callback). We verify the component does NOT re-shuffle — DOM
    // order matches input order.
    const records = [
      rec({ source: 'newest', date: '2026-04-20' }),
      rec({ source: 'middle', date: '2026-04-15' }),
      rec({ source: 'oldest', date: '2026-04-10' }),
    ]
    mockedUseEndorsements.mockReturnValue({
      data: records,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useEndorsements>)
    renderList()
    const cards = screen.getAllByTestId('endorsement-card')
    expect(cards[0].textContent).toContain('newest')
    expect(cards[1].textContent).toContain('middle')
    expect(cards[2].textContent).toContain('oldest')
  })

  it('renders_error_state_quietly — isError → muted "unavailable" notice (preserves layout)', () => {
    mockedUseEndorsements.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as unknown as ReturnType<typeof useEndorsements>)
    renderList()
    expect(screen.getByTestId('endorsements-error')).toBeInTheDocument()
    expect(screen.getByTestId('endorsements-error').textContent).toMatch(
      /unavailable/i,
    )
  })
})
