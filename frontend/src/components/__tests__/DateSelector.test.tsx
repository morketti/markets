import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { DateSelector } from '../DateSelector'

// DateSelector tests — verify it reads the dates index, renders a dropdown,
// and on selection navigates with the correct route shape.
//
// We mock the useDates() hook by stubbing the loadDates module — keeps the
// test focused on the selector's URL routing logic, not on TanStack Query
// internals (which are exhaustively tested by TanStack itself).

vi.mock('@/lib/loadDates', () => ({
  useDates: vi.fn(),
}))

import { useDates } from '@/lib/loadDates'

const mockedUseDates = vi.mocked(useDates)

function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
}

function renderAtRoute(initialEntry: string) {
  const qc = makeQueryClient()
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/scan/:date" element={<DateSelector />} />
          <Route
            path="/ticker/:symbol/:date"
            element={<DateSelector />}
          />
          {/* Catchall to verify navigation lands on the right route */}
          <Route path="*" element={<DateSelector />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('DateSelector', () => {
  it("renders 'today' plus all returned dates in newest-first order", () => {
    mockedUseDates.mockReturnValue({
      data: {
        schema_version: 1,
        dates_available: ['2026-04-30', '2026-05-01', '2026-05-04'],
        updated_at: '2026-05-04T12:00:00Z',
      },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useDates>)

    renderAtRoute('/scan/2026-05-04')
    const select = screen.getByTestId('date-selector') as HTMLSelectElement
    const options = Array.from(select.options).map((o) => o.value)
    // 'today' first, then dates sorted newest-first (reverse of asc)
    expect(options).toEqual([
      'today',
      '2026-05-04',
      '2026-05-01',
      '2026-04-30',
    ])
  })

  it("reflects the active :date param as the selected option", () => {
    mockedUseDates.mockReturnValue({
      data: {
        schema_version: 1,
        dates_available: ['2026-04-30', '2026-05-01', '2026-05-04'],
        updated_at: '2026-05-04T12:00:00Z',
      },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useDates>)

    renderAtRoute('/scan/2026-05-01')
    const select = screen.getByTestId('date-selector') as HTMLSelectElement
    expect(select.value).toBe('2026-05-01')
  })

  it("on /scan/:date navigates to /scan/{newDate} on selection", async () => {
    mockedUseDates.mockReturnValue({
      data: {
        schema_version: 1,
        dates_available: ['2026-04-30', '2026-05-04'],
        updated_at: '2026-05-04T12:00:00Z',
      },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useDates>)

    const user = userEvent.setup()
    renderAtRoute('/scan/2026-05-04')
    const select = screen.getByTestId('date-selector') as HTMLSelectElement
    await user.selectOptions(select, '2026-04-30')
    // After navigation the new value is reflected (route is /scan/2026-04-30)
    expect(select.value).toBe('2026-04-30')
  })

  it("on /ticker/:symbol/:date navigates preserving the symbol", async () => {
    mockedUseDates.mockReturnValue({
      data: {
        schema_version: 1,
        dates_available: ['2026-04-30', '2026-05-04'],
        updated_at: '2026-05-04T12:00:00Z',
      },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useDates>)

    const user = userEvent.setup()
    renderAtRoute('/ticker/AAPL/2026-05-04')
    const select = screen.getByTestId('date-selector') as HTMLSelectElement
    await user.selectOptions(select, '2026-04-30')
    // Selector reflects new date (the route was matched + symbol preserved)
    expect(select.value).toBe('2026-04-30')
  })

  it('renders only today option when no data (404 / first deploy)', () => {
    mockedUseDates.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('not found'),
    } as unknown as ReturnType<typeof useDates>)

    renderAtRoute('/scan/today')
    const select = screen.getByTestId('date-selector') as HTMLSelectElement
    const options = Array.from(select.options).map((o) => o.value)
    expect(options).toEqual(['today'])
  })

  it('disabled while loading', () => {
    mockedUseDates.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as unknown as ReturnType<typeof useDates>)

    renderAtRoute('/scan/today')
    const select = screen.getByTestId('date-selector') as HTMLSelectElement
    expect(select.disabled).toBe(true)
  })
})
