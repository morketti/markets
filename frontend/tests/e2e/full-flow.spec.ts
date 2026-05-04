import { test, expect } from '@playwright/test'
import { mountScanFixtures } from './fixtures-server'

// Full-flow happy-path E2E — the complete user journey end to end:
//
//   1. Open /scan/2026-05-04
//   2. See staleness badge (rendered from _index.json + _status.json)
//   3. Switch lenses (Position → Short → Long), verify ?lens= URL param
//   4. Click a ticker row → land on /ticker/:symbol/:date
//   5. Verify deep-dive sections all rendered
//      (OpenClaudePin + Chart + PersonaCards + AnalyticalSignals + News)
//   6. Use DateSelector to navigate to a different date, preserving the
//      ticker (route shape /ticker/:symbol/:newDate)
//
// Runs by default on ALL Playwright projects (chromium-desktop +
// mobile-safari + mobile-chrome) — the multi-device E2E discipline locked
// in playwright.config.ts.

test.describe('full flow', () => {
  test.beforeEach(async ({ page }) => {
    await mountScanFixtures(page)
    // _dates.json fixture so DateSelector renders with multiple dates
    await page.route(/\/_dates\.json$/, (route) =>
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
    // 2026-05-03 fixtures (re-use 2026-05-04 ones)
    await page.route(
      /\/2026-05-03\/(_index|_status|AAPL|NVDA|MSFT)\.json$/,
      async (route) => {
        const url = route.request().url()
        if (url.endsWith('_status.json')) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: '{"date": "2026-05-03", "schema_version": 2, "computed_at": "2026-05-03T12:00:00Z", "successful_ticker_count": 3, "failed_tickers": [], "skipped_tickers": [], "partial": false, "llm_failure_count": 0}',
          })
        } else if (url.endsWith('_index.json')) {
          const idxBody = JSON.stringify({
            date: '2026-05-03',
            schema_version: 2,
            run_started_at: new Date(Date.now() - 3 * 3_600_000).toISOString(),
            run_completed_at: new Date(Date.now() - 2 * 3_600_000).toISOString(),
            tickers: ['AAPL', 'NVDA', 'MSFT'],
            lite_mode: false,
            total_token_count_estimate: 0,
          })
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: idxBody,
          })
        } else {
          // For ticker JSONs, fall through to the date-agnostic per-ticker
          // mock from mountScanFixtures (which doesn't bind to a date).
          // mountScanFixtures' regex matches any /(AAPL|NVDA|MSFT)\.json$/
          // so this should be handled there.
          await route.fallback()
        }
      },
    )
  })

  test('scan → switch lenses → click ticker → deep-dive → date selector', async ({
    page,
  }) => {
    // 1. Open scan
    await page.goto('/scan/2026-05-04')
    await expect(
      page.getByRole('tab', { name: 'Position Adjustment' }),
    ).toBeVisible()

    // 2. Staleness badge visible (the badge text is GREEN/AMBER/RED depending
    // on age — fixtures-server patches age=2h → GREEN)
    await expect(page.getByTestId('staleness-slot')).toBeVisible()

    // 3. Switch to Short-Term lens
    await page.getByRole('tab', { name: 'Short-Term Opportunities' }).click()
    await expect(page).toHaveURL(/lens=short/)

    // 4. Switch to Long-Term lens
    await page.getByRole('tab', { name: 'Long-Term Thesis Status' }).click()
    await expect(page).toHaveURL(/lens=long/)

    // 5. Switch back to Position and click first ticker row
    await page.getByRole('tab', { name: 'Position Adjustment' }).click()
    const firstTicker = page
      .getByTestId('position-lens')
      .locator('[data-testid="ticker-card-link"]')
      .first()
    await expect(firstTicker).toBeVisible()
    const tickerSymbol = await firstTicker.getAttribute('data-ticker')
    expect(tickerSymbol).toBeTruthy()
    await firstTicker.click()
    await expect(page).toHaveURL(
      new RegExp(`/ticker/${tickerSymbol}/2026-05-04`),
    )

    // 6. Deep-dive sections all rendered
    await expect(page.getByTestId('open-claude-pin')).toBeVisible()
    await expect(page.getByTestId('chart-container')).toBeVisible()
    await expect(
      page.getByRole('heading', { name: /Persona Signals/i }),
    ).toBeVisible()
    await expect(
      page.getByRole('heading', { name: /News Feed/i }),
    ).toBeVisible()

    // 7. Use DateSelector to switch to 2026-05-03; verify symbol preserved
    const dateSelector = page.getByTestId('date-selector')
    await expect(dateSelector).toBeVisible()
    await dateSelector.selectOption('2026-05-03')
    await expect(page).toHaveURL(
      new RegExp(`/ticker/${tickerSymbol}/2026-05-03`),
    )
  })
})
