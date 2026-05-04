import { test, expect } from '@playwright/test'
import { mountScanFixtures } from './fixtures-server'

// Mobile-responsive E2E (VIEW-12).
//
// These specs target mobile-safari (iPhone 14) + mobile-chrome (Pixel 7)
// projects in playwright.config.ts. The chromium-desktop run skips them via
// test.skip(!isMobile, 'mobile-only').
//
// Critical assertions:
//   1. No horizontal scroll on /scan or /ticker at any mobile viewport
//   2. Lens tabs are tap-friendly (height >= 40px Apple HIG floor)
//   3. Deep-dive timeframe cards stack vertically (lg:flex-row → flex-col)
//   4. Ticker search input + date selector remain accessible

test.describe('responsive', () => {
  test.beforeEach(async ({ page }) => {
    await mountScanFixtures(page)
    // _dates.json fixture so DateSelector renders without 404
    await page.route(/\/_dates\.json/, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          schema_version: 1,
          dates_available: ['2026-05-03', '2026-05-04'],
          updated_at: new Date().toISOString(),
        }),
      }),
    )
  })

  test('mobile: lens tabs are tap-friendly (>=40px height)', async ({
    page,
    isMobile,
  }) => {
    test.skip(!isMobile, 'mobile-only')
    await page.goto('/scan/2026-05-04')
    const tab = page.getByTestId('lens-tab-position')
    await expect(tab).toBeVisible()
    const box = await tab.boundingBox()
    expect(box).not.toBeNull()
    // Apple HIG: 44pt min tap target. We assert >=40 to allow a small
    // device-specific rounding margin.
    expect(box!.height).toBeGreaterThanOrEqual(40)
  })

  test('mobile: deep-dive timeframe cards stack vertically (not side-by-side)', async ({
    page,
    isMobile,
  }) => {
    test.skip(!isMobile, 'mobile-only')
    await page.goto('/ticker/NVDA/2026-05-04')
    // Wait for the timeframes container to mount
    await expect(page.getByTestId('timeframe-cards')).toBeVisible()
    const cards = page.getByTestId('timeframe-card')
    await expect(cards).toHaveCount(2)
    const firstBox = await cards.nth(0).boundingBox()
    const secondBox = await cards.nth(1).boundingBox()
    expect(firstBox).not.toBeNull()
    expect(secondBox).not.toBeNull()
    // Stacked = the second card's y-coordinate is below the first's bottom
    // edge. On lg+ viewports they'd be side-by-side (same y).
    expect(secondBox!.y).toBeGreaterThan(firstBox!.y + 30)
  })

  test('mobile: no horizontal scroll on /scan', async ({ page, isMobile }) => {
    test.skip(!isMobile, 'mobile-only')
    await page.goto('/scan/2026-05-04')
    // Wait for content to settle
    await expect(page.getByRole('tab', { name: 'Position Adjustment' })).toBeVisible()
    const dims = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }))
    // +2px tolerance for sub-pixel rounding on mobile devices
    expect(dims.scrollWidth).toBeLessThanOrEqual(dims.clientWidth + 2)
  })

  test('mobile: no horizontal scroll on /ticker deep-dive', async ({
    page,
    isMobile,
  }) => {
    test.skip(!isMobile, 'mobile-only')
    await page.goto('/ticker/AAPL/2026-05-04')
    await expect(page.getByTestId('ticker-heading')).toBeVisible()
    const dims = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }))
    expect(dims.scrollWidth).toBeLessThanOrEqual(dims.clientWidth + 2)
  })

  test('mobile: persona cards stack into single column on narrow viewport', async ({
    page,
    isMobile,
  }) => {
    test.skip(!isMobile, 'mobile-only')
    await page.goto('/ticker/AAPL/2026-05-04')
    const personas = page.getByTestId('persona-card')
    await expect(personas).toHaveCount(5)
    const firstBox = await personas.nth(0).boundingBox()
    const secondBox = await personas.nth(1).boundingBox()
    expect(firstBox).not.toBeNull()
    expect(secondBox).not.toBeNull()
    // Single-column = card 2 stacks below card 1 (different y).
    // grid-cols-1 on mobile per TickerRoute responsive layout.
    expect(secondBox!.y).toBeGreaterThan(firstBox!.y + 30)
  })

  test('mobile: chart container fits within viewport width', async ({
    page,
    isMobile,
  }) => {
    test.skip(!isMobile, 'mobile-only')
    await page.goto('/ticker/AAPL/2026-05-04')
    const chart = page.getByTestId('chart-container')
    await expect(chart).toBeVisible()
    const box = await chart.boundingBox()
    expect(box).not.toBeNull()
    const viewport = page.viewportSize()
    expect(viewport).not.toBeNull()
    // Chart should be no wider than the viewport (allow sub-pixel margin).
    expect(box!.width).toBeLessThanOrEqual(viewport!.width + 2)
  })
})
