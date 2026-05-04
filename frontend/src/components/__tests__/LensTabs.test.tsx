import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router'
import { LensTabs } from '../LensTabs'

// LensTabs tests — the discipline tests are:
//   1. URL ?lens=position|short|long sync (read + write)
//   2. Default lens=position when ?lens missing
//   3. Invalid ?lens value → falls back to position
//   4. ONE-LENS-AT-A-TIME — switching tabs unmounts the previous lens content

function renderWithRouter(initialEntry: string) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route
          path="/scan/:date"
          element={
            <LensTabs
              positionContent={
                <div data-testid="position-marker">POSITION CONTENT</div>
              }
              shortContent={<div data-testid="short-marker">SHORT CONTENT</div>}
              longContent={<div data-testid="long-marker">LONG CONTENT</div>}
            />
          }
        />
      </Routes>
    </MemoryRouter>,
  )
}

describe('LensTabs', () => {
  it('renders the 3 tab triggers with correct labels', () => {
    renderWithRouter('/scan/2026-05-04')
    expect(
      screen.getByRole('tab', { name: 'Position Adjustment' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('tab', { name: 'Short-Term Opportunities' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('tab', { name: 'Long-Term Thesis Status' }),
    ).toBeInTheDocument()
  })

  it('defaults to Position Adjustment when ?lens is missing', () => {
    renderWithRouter('/scan/2026-05-04')
    expect(screen.getByTestId('position-marker')).toBeInTheDocument()
    // Critical: the other lens content is NOT in the DOM
    expect(screen.queryByTestId('short-marker')).toBeNull()
    expect(screen.queryByTestId('long-marker')).toBeNull()
  })

  it('honors ?lens=short query param', () => {
    renderWithRouter('/scan/2026-05-04?lens=short')
    expect(screen.getByTestId('short-marker')).toBeInTheDocument()
    expect(screen.queryByTestId('position-marker')).toBeNull()
    expect(screen.queryByTestId('long-marker')).toBeNull()
  })

  it('honors ?lens=long query param', () => {
    renderWithRouter('/scan/2026-05-04?lens=long')
    expect(screen.getByTestId('long-marker')).toBeInTheDocument()
    expect(screen.queryByTestId('position-marker')).toBeNull()
    expect(screen.queryByTestId('short-marker')).toBeNull()
  })

  it('falls back to position when ?lens has an invalid value', () => {
    renderWithRouter('/scan/2026-05-04?lens=garbage')
    expect(screen.getByTestId('position-marker')).toBeInTheDocument()
    expect(screen.queryByTestId('short-marker')).toBeNull()
  })

  it('switching tabs unmounts the previous content (Pitfall #8 / VIEW-01 lock)', async () => {
    // userEvent simulates real pointer events (pointerdown + click + focus)
    // which Radix Tabs needs — fireEvent.click alone doesn't dispatch the
    // pointerdown that Radix's tab trigger handler watches for.
    const user = userEvent.setup()
    renderWithRouter('/scan/2026-05-04')
    // Initial: position visible
    expect(screen.getByTestId('position-marker')).toBeInTheDocument()
    // Click Short-Term tab
    await user.click(
      screen.getByRole('tab', { name: 'Short-Term Opportunities' }),
    )
    // After click: short visible, position GONE from DOM (Radix Tabs.Content
    // unmounts inactive tabs by default — we explicitly do not pass forceMount)
    expect(screen.getByTestId('short-marker')).toBeInTheDocument()
    expect(screen.queryByTestId('position-marker')).toBeNull()
    // Click Long-Term
    await user.click(
      screen.getByRole('tab', { name: 'Long-Term Thesis Status' }),
    )
    expect(screen.getByTestId('long-marker')).toBeInTheDocument()
    expect(screen.queryByTestId('short-marker')).toBeNull()
  })
})
