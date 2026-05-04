import { test, expect } from '@playwright/test'
import { mountScanFixtures } from './fixtures-server'

// Playwright happy-path E2E for the Morning Scan view.
//
// The fixtures-server helper intercepts raw.githubusercontent.com fetches and
// serves the 3 fixture JSONs (AAPL, NVDA, MSFT) plus _index.json + _status.json.
// run_completed_at is patched at request time so staleness stays GREEN.
//
// Critical assertions:
//   1. 3 lens tab triggers visible
//   2. Default lens=position; NVDA (highest |consensus_score|) appears first
//   3. Switching tabs updates ?lens query param AND swaps content (one-lens-at-a-time)
//   4. ?lens=long shows NVDA (broken) + MSFT (weakening), excludes AAPL (intact)
//   5. StalenessBadge renders GREEN

test.describe('morning scan', () => {
  test.beforeEach(async ({ page }) => {
    await mountScanFixtures(page)
  })

  test('renders 3 lens tabs and only the active lens content', async ({ page }) => {
    await page.goto('/scan/2026-05-04')

    // 3 tab triggers visible
    await expect(page.getByRole('tab', { name: 'Position Adjustment' })).toBeVisible()
    await expect(
      page.getByRole('tab', { name: 'Short-Term Opportunities' }),
    ).toBeVisible()
    await expect(
      page.getByRole('tab', { name: 'Long-Term Thesis Status' }),
    ).toBeVisible()

    // Default lens=position — NVDA appears first (|consensus_score|=0.78 highest)
    const positionLens = page.getByTestId('position-lens')
    await expect(positionLens).toBeVisible()
    const positionTickers = await positionLens
      .locator('[data-testid="ticker-symbol"]')
      .allTextContents()
    expect(positionTickers).toEqual(['NVDA', 'AAPL', 'MSFT'])
  })

  test('switching lens tabs updates URL and swaps content', async ({ page }) => {
    await page.goto('/scan/2026-05-04')

    // Click Short-Term Opportunities tab
    await page.getByRole('tab', { name: 'Short-Term Opportunities' }).click()
    await expect(page).toHaveURL(/\?lens=short/)

    // ShortTermLens shows: AAPL (add, conf=70) and MSFT (buy, conf=85)
    // sorted by confidence DESC: MSFT first.
    const shortLens = page.getByTestId('short-term-lens')
    await expect(shortLens).toBeVisible()
    const shortTickers = await shortLens
      .locator('[data-testid="ticker-symbol"]')
      .allTextContents()
    expect(shortTickers).toEqual(['MSFT', 'AAPL'])

    // PositionLens content NOT visible (one-lens-at-a-time / Pitfall #8)
    await expect(page.getByTestId('position-lens')).not.toBeVisible()
  })

  test('long-term lens filters to weakening or broken thesis only', async ({
    page,
  }) => {
    await page.goto('/scan/2026-05-04?lens=long')

    const longLens = page.getByTestId('long-term-lens')
    await expect(longLens).toBeVisible()
    // NVDA (broken) sorts before MSFT (weakening); AAPL (intact) excluded.
    const longTickers = await longLens
      .locator('[data-testid="ticker-symbol"]')
      .allTextContents()
    expect(longTickers).toEqual(['NVDA', 'MSFT'])
  })

  test('staleness badge renders GREEN for 2h-old fixture', async ({ page }) => {
    await page.goto('/scan/2026-05-04')
    const badge = page.getByTestId('staleness-badge')
    await expect(badge).toBeVisible()
    await expect(badge).toHaveAttribute('data-level', 'GREEN')
  })

  test('clicking a ticker row deep-links to /ticker/:symbol/:date', async ({
    page,
  }) => {
    await page.goto('/scan/2026-05-04')
    // First row in PositionLens is NVDA
    const firstRow = page
      .getByTestId('position-lens')
      .locator('[data-testid="ticker-card-link"]')
      .first()
    await expect(firstRow).toHaveAttribute('href', '/ticker/NVDA/2026-05-04')
  })
})
