// novel-to-this-project — Phase 8 Wave 1 resilience E2E spec. Locks the
// user-facing failure-mode contract: a refresh fetch failing (5xx /
// network / partial) MUST NOT crash the page. Snapshot stays canonical;
// CurrentPriceDelta degrades gracefully.
//
// Three specs:
//   1. /api/refresh returns 500 → /ticker/AAPL/2026-05-04 renders snapshot
//      side normally + "Refresh unavailable" notice in the placeholder
//   2. /api/refresh returns 500 → /decision/AAPL/2026-05-04 renders banner
//      + drivers + dissent normally + "Refresh unavailable" notice
//   3. /api/refresh returns the partial-response shape (RSS unavailable
//      but price OK) → price renders + Headlines unavailable footnote
//
// Mounts the same fixture-server interceptors as the Phase 6/7 specs so
// snapshot fetches succeed via local fixture JSONs; the only NEW intercept
// is /api/refresh*.

import { test, expect } from '@playwright/test'

import { mountScanFixtures } from './fixtures-server'

const FIXTURE_TICKER = 'AAPL'
const FIXTURE_DATE = '2026-05-04'

test.describe('refresh resilience', () => {
  test.beforeEach(async ({ page }) => {
    await mountScanFixtures(page)
  })

  test('refresh 500 does not crash TickerRoute — snapshot stays canonical', async ({
    page,
  }) => {
    // Intercept BEFORE navigation so the very first /api/refresh call hits
    // the mock (TanStack hook fires on mount).
    await page.route('**/api/refresh*', (route) =>
      route.fulfill({ status: 500, body: '' }),
    )

    await page.goto(`/ticker/${FIXTURE_TICKER}/${FIXTURE_DATE}`)

    // Snapshot side renders — ticker hero is visible. Use the existing
    // testid set by TickerRoute (Phase 6 contract).
    await expect(page.getByTestId('ticker-heading')).toHaveText(
      FIXTURE_TICKER,
    )

    // CurrentPriceDelta placeholder is visible with the failure copy.
    const placeholder = page.getByTestId('current-price-placeholder')
    await expect(placeholder).toBeVisible()
    await expect(placeholder).toContainText(/Refresh unavailable/i)

    // OpenClaudePin (Phase 6 VIEW-09 lock) still renders — proves the
    // refresh failure didn't unmount the rest of the route.
    await expect(page.getByTestId('open-claude-pin')).toBeVisible()
  })

  test('refresh 500 does not crash DecisionRoute — banner + drivers + dissent intact', async ({
    page,
  }) => {
    await page.route('**/api/refresh*', (route) =>
      route.fulfill({ status: 500, body: '' }),
    )

    await page.goto(`/decision/${FIXTURE_TICKER}/${FIXTURE_DATE}`)

    // Phase 7 hero + supporting elements all present.
    await expect(page.getByTestId('recommendation-banner')).toBeVisible()
    await expect(page.getByTestId('drivers-list')).toBeVisible()
    await expect(page.getByTestId('dissent-panel')).toBeVisible()

    // CurrentPriceDelta in failure-fallback state — testid preserved
    // (Phase 7 grep contract); copy contains the locked muted notice.
    const placeholder = page.getByTestId('current-price-placeholder')
    await expect(placeholder).toBeVisible()
    await expect(placeholder).toContainText(/Refresh unavailable/i)
  })

  test('refresh partial response renders price + headlines-unavailable note', async ({
    page,
  }) => {
    // Locked partial-response shape from api/refresh.py: price OK, RSS
    // unavailable. CurrentPriceDelta should render the price hero + the
    // muted "Headlines unavailable" footnote.
    await page.route('**/api/refresh*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ticker: FIXTURE_TICKER,
          current_price: 178.42,
          price_timestamp: '2026-05-04T19:32:11+00:00',
          recent_headlines: [],
          errors: ['rss-unavailable'],
          partial: true,
        }),
      }),
    )

    await page.goto(`/ticker/${FIXTURE_TICKER}/${FIXTURE_DATE}`)

    const placeholder = page.getByTestId('current-price-placeholder')
    await expect(placeholder).toBeVisible()
    await expect(placeholder).toContainText('$178.42')
    await expect(placeholder).toContainText(/Headlines unavailable/i)
  })
})
