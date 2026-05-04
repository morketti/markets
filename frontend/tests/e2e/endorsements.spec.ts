// novel-to-this-project — Phase 9 Playwright E2E for /decision/:symbol/:date?
// EndorsementsList panel. Mocks the JSONL fetch via page.route() to lock the
// 4 user-facing contracts:
//   1. empty state — 404 on endorsements.jsonl renders CTA copy + DissentPanel
//      + CurrentPriceDelta still render (panel does not unmount peers)
//   2. populated state — 200 with mixed-ticker JSONL renders only AAPL cards
//      in date-desc order; NO performance number anywhere within the panel
//   3. 90-day cutoff — 200 with one record outside 90d → that card excluded
//
// Run on chromium-desktop only (Playwright spec count: 72 baseline + 3 = 75).

import { test, expect } from '@playwright/test'

import { mountScanFixtures } from './fixtures-server'

const FIXTURE_TICKER = 'AAPL'
const FIXTURE_DATE = '2026-05-04'

// Helper — build a JSONL body from a list of record objects.
function jsonl(records: object[]): string {
  return records.map((r) => JSON.stringify(r)).join('\n') + '\n'
}

// Build a valid Endorsement record dict with overrides.
function rec(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    schema_version: 1,
    ticker: 'AAPL',
    source: 'Motley Fool',
    date: '2026-04-15',
    price_at_call: 178.42,
    notes: '',
    captured_at: '2026-05-04T10:00:00+00:00',
    ...overrides,
  }
}

// Compute an ISO date `daysAgo` days before today (UTC).
function daysAgo(n: number): string {
  const d = new Date()
  d.setUTCDate(d.getUTCDate() - n)
  return d.toISOString().slice(0, 10)
}

test.describe('endorsements panel', () => {
  test.beforeEach(async ({ page }) => {
    await mountScanFixtures(page)
  })

  test('empty state — 404 on endorsements.jsonl renders CTA + DissentPanel intact', async ({
    page,
  }) => {
    // Intercept the endorsements.jsonl fetch BEFORE navigation.
    await page.route(/raw\.githubusercontent\.com\/.+\/endorsements\.jsonl$/, (route) =>
      route.fulfill({ status: 404, body: '' }),
    )
    // Also stub the on-mount /api/refresh call so it doesn't surface as a
    // generic failure noise — we only care about the endorsements behavior.
    await page.route('**/api/refresh*', (route) =>
      route.fulfill({ status: 500, body: '' }),
    )

    await page.goto(`/decision/${FIXTURE_TICKER}/${FIXTURE_DATE}`)

    // EndorsementsList renders empty state with CTA copy.
    const list = page.getByTestId('endorsements-list')
    await expect(list).toBeVisible()
    await expect(list).toContainText(
      `No endorsements captured for ${FIXTURE_TICKER}`,
    )
    await expect(list).toContainText('last 90 days')
    await expect(list).toContainText('markets add_endorsement')

    // Sibling components still render — proves the panel did not unmount peers.
    await expect(page.getByTestId('dissent-panel')).toBeVisible()
    await expect(page.getByTestId('current-price-placeholder')).toBeVisible()
    // No card present
    await expect(page.locator('[data-testid="endorsement-card"]')).toHaveCount(0)
  })

  test('populated state — 3 records (2 AAPL within 90d + 1 MSFT) → 2 AAPL cards in date-desc; NO performance number', async ({
    page,
  }) => {
    // NOTE: source names deliberately exclude "Seeking Alpha" / "Performance"
    // / "% Daily Gains" etc. — those legitimate publication names would trip
    // the regex guard below (which scans for performance vocabulary). The
    // guard is a regression sentinel for the COMPONENT, so we use neutral
    // newsletter names that don't accidentally introduce false positives.
    const records = [
      rec({ ticker: 'AAPL', source: 'Motley Fool', date: '2026-04-20' }),
      rec({ ticker: 'AAPL', source: 'Stock Picks Weekly', date: '2026-04-15' }),
      rec({ ticker: 'MSFT', source: 'Other Newsletter', date: '2026-04-15' }),
    ]
    await page.route(
      /raw\.githubusercontent\.com\/.+\/endorsements\.jsonl$/,
      (route) =>
        route.fulfill({
          status: 200,
          contentType: 'text/plain',
          body: jsonl(records),
        }),
    )
    await page.route('**/api/refresh*', (route) =>
      route.fulfill({ status: 500, body: '' }),
    )

    await page.goto(`/decision/${FIXTURE_TICKER}/${FIXTURE_DATE}`)

    const list = page.getByTestId('endorsements-list')
    await expect(list).toBeVisible()

    const cards = page.locator('[data-testid="endorsement-card"]')
    await expect(cards).toHaveCount(2) // MSFT filtered out

    // Date-desc order: 2026-04-20 first, 2026-04-15 second.
    const card0 = cards.nth(0)
    const card1 = cards.nth(1)
    await expect(card0).toContainText('Motley Fool')
    await expect(card0).toContainText('2026-04-20')
    await expect(card1).toContainText('Stock Picks Weekly')
    await expect(card1).toContainText('2026-04-15')

    // NO performance number anywhere within the EndorsementsList region.
    const listText = (await list.textContent()) ?? ''
    expect(listText).not.toMatch(/%/)
    expect(listText).not.toMatch(/vs S&P/i)
    expect(listText).not.toMatch(/alpha/i)
    expect(listText).not.toMatch(/\bgain\b/i)
    expect(listText).not.toMatch(/\bperf(ormance)?\b/i)
  })

  test('90-day cutoff — record at today-95d excluded; today-30d + today-89d included', async ({
    page,
  }) => {
    const records = [
      rec({ ticker: 'AAPL', source: 'recent', date: daysAgo(30) }),
      rec({ ticker: 'AAPL', source: 'edge', date: daysAgo(89) }),
      rec({ ticker: 'AAPL', source: 'too_old', date: daysAgo(95) }),
    ]
    await page.route(
      /raw\.githubusercontent\.com\/.+\/endorsements\.jsonl$/,
      (route) =>
        route.fulfill({
          status: 200,
          contentType: 'text/plain',
          body: jsonl(records),
        }),
    )
    await page.route('**/api/refresh*', (route) =>
      route.fulfill({ status: 500, body: '' }),
    )

    await page.goto(`/decision/${FIXTURE_TICKER}/${FIXTURE_DATE}`)

    const cards = page.locator('[data-testid="endorsement-card"]')
    await expect(cards).toHaveCount(2)
    // Most recent first
    await expect(cards.nth(0)).toContainText('recent')
    await expect(cards.nth(1)).toContainText('edge')
    // The 95-day-old record must NOT appear anywhere in the list.
    const list = page.getByTestId('endorsements-list')
    await expect(list).not.toContainText('too_old')
  })
})
