import { test, expect } from '@playwright/test'
import { mountScanFixtures } from './fixtures-server'

// Playwright E2E for the Decision-Support View at /decision/:symbol/:date?.
//
// Round-trip flow validates the full Phase 7 surface:
//   /scan → /ticker → /decision → /ticker (date preserved)
//
// Critical assertions:
//   - URL preservation: :date round-trips through both cross-links
//   - banner / drivers / dissent / Phase-8 placeholder all visible at first paint
//   - drivers-card count = 2 (short_term + long_term)
//   - dissent-panel data-has-dissent="true" (NVDA fixture has burry dissent)

test.describe('decision', () => {
  test.beforeEach(async ({ page }) => {
    await mountScanFixtures(page)
  })

  test('round-trip /scan → /ticker → /decision → /ticker preserves date and renders banner + drivers + dissent', async ({
    page,
  }) => {
    // 1. Start at scan, click first ticker (NVDA — |consensus_score| highest)
    await page.goto('/scan/2026-05-04')
    await page
      .getByTestId('position-lens')
      .locator('[data-testid="ticker-card-link"]')
      .first()
      .click()
    await expect(page).toHaveURL(/\/ticker\/NVDA\/2026-05-04/)

    // 2. From deep-dive, follow the "→ Decision view" cross-link
    await page.getByTestId('to-decision-link').click()
    await expect(page).toHaveURL(/\/decision\/NVDA\/2026-05-04/)

    // 3. Hero banner present + correct recommendation attr (NVDA fixture =
    //    take_profits per the locked routine output)
    const banner = page.getByTestId('recommendation-banner')
    await expect(banner).toBeVisible()
    await expect(banner).toHaveAttribute('data-recommendation', 'take_profits')

    // 4. Drivers list present with exactly 2 cards (short + long)
    await expect(page.getByTestId('drivers-list')).toBeVisible()
    await expect(page.locator('[data-testid="drivers-card"]')).toHaveCount(2)

    // 5. Dissent panel always rendered; NVDA fixture has has_dissent: true
    const dissent = page.getByTestId('dissent-panel')
    await expect(dissent).toBeVisible()
    await expect(dissent).toHaveAttribute('data-has-dissent', 'true')

    // 6. Phase 8 hookpoint — placeholder visible
    await expect(
      page.getByTestId('current-price-placeholder'),
    ).toBeVisible()

    // 7. Cross-link back to deep-dive preserves date
    await page.getByTestId('back-to-deep-dive-link').click()
    await expect(page).toHaveURL(/\/ticker\/NVDA\/2026-05-04/)
  })
})
