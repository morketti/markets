import { test, expect } from '@playwright/test'
import { mountScanFixtures } from './fixtures-server'

// Playwright happy-path E2E for the Per-Ticker Deep-Dive view.
//
// fixtures-server intercepts raw.githubusercontent.com fetches and serves
// the same AAPL.json / NVDA.json / MSFT.json fixtures used by the morning-
// scan E2E. The fixtures already include 30 ohlc bars + indicators + 9
// headlines (AAPL) / 3 headlines (NVDA, MSFT) + 6 persona_signals + ticker
// _decision with both timeframes populated.
//
// Critical assertions:
//   1. Click NVDA row from /scan → land on /ticker/NVDA/2026-05-04
//   2. OpenClaudePin visible at TOP (VIEW-09 lock)
//   3. Chart container rendered (lightweight-charts mounted)
//   4. PersonaCards grid has exactly 5 cards (claude_analyst excluded)
//   5. NewsList rendered with at least one source group
//   6. Two TimeframeCards (short_term + long_term)
//   7. Ticker search input navigates to /ticker/:typed/:date

test.describe('deep dive', () => {
  test.beforeEach(async ({ page }) => {
    await mountScanFixtures(page)
  })

  test('click ticker from scan navigates to deep-dive with all sections', async ({
    page,
  }) => {
    await page.goto('/scan/2026-05-04')
    // First row in PositionLens is NVDA (|0.78| highest)
    await page
      .getByTestId('position-lens')
      .locator('[data-testid="ticker-card-link"]')
      .first()
      .click()
    await expect(page).toHaveURL(/\/ticker\/NVDA\/2026-05-04/)
    // Heading
    await expect(page.getByTestId('ticker-heading')).toHaveText('NVDA')
    // OpenClaudePin pinned at top
    await expect(page.getByTestId('open-claude-pin')).toBeVisible()
    // 2 TimeframeCards
    const timeframes = page.getByTestId('timeframe-card')
    await expect(timeframes).toHaveCount(2)
    // Chart container present
    await expect(page.getByTestId('chart-container')).toBeVisible()
    // 5 PersonaCards in grid (claude_analyst excluded)
    const personas = page.getByTestId('persona-card')
    await expect(personas).toHaveCount(5)
    // None of them are claude_analyst (VIEW-09 separation lock)
    const personaIds = await personas.evaluateAll((els) =>
      els.map((el) => el.getAttribute('data-persona')),
    )
    expect(personaIds).not.toContain('claude_analyst')
    // News feed section header visible
    await expect(
      page.getByRole('heading', { name: /News Feed/i }),
    ).toBeVisible()
  })

  test('VIEW-09 OpenClaudePin always renders even when navigating directly', async ({
    page,
  }) => {
    await page.goto('/ticker/AAPL/2026-05-04')
    const pin = page.getByTestId('open-claude-pin')
    await expect(pin).toBeVisible()
    // The AAPL fixture has a non-data-unavailable claude_analyst signal so
    // data-muted should be 'false' here.
    await expect(pin).toHaveAttribute('data-muted', 'false')
  })

  test('NewsList groups headlines by source on AAPL deep-dive', async ({
    page,
  }) => {
    await page.goto('/ticker/AAPL/2026-05-04')
    await expect(page.getByTestId('news-list')).toBeVisible()
    const groups = page.getByTestId('news-source-group')
    // AAPL fixture: 3 sources (Yahoo Finance / Reuters / Bloomberg RSS)
    await expect(groups).toHaveCount(3)
    const sources = await groups.evaluateAll((els) =>
      els.map((el) => el.getAttribute('data-source')),
    )
    expect(sources).toContain('Yahoo Finance')
    expect(sources).toContain('Reuters')
    expect(sources).toContain('Bloomberg RSS')
  })

  test('VIEW-13 ticker search input navigates to /ticker/:symbol', async ({
    page,
  }) => {
    await page.goto('/scan/2026-05-04')
    const input = page.getByTestId('ticker-search-input')
    await input.fill('AAPL')
    await input.press('Enter')
    await expect(page).toHaveURL(/\/ticker\/AAPL\/2026-05-04/)
    // After navigation the deep-dive renders
    await expect(page.getByTestId('ticker-heading')).toHaveText('AAPL')
  })

  test('VIEW-13 ticker search uppercases lowercase input', async ({ page }) => {
    await page.goto('/scan/2026-05-04')
    const input = page.getByTestId('ticker-search-input')
    await input.fill('aapl')
    await input.press('Enter')
    await expect(page).toHaveURL(/\/ticker\/AAPL\//)
  })

  test('back-to-scan link returns from deep-dive', async ({ page }) => {
    await page.goto('/ticker/NVDA/2026-05-04')
    await page.getByTestId('back-to-scan-link').click()
    await expect(page).toHaveURL(/\/scan\/2026-05-04/)
  })
})
