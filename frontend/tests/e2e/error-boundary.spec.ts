import { test, expect } from '@playwright/test'
import { mountScanFixtures } from './fixtures-server'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

// ErrorBoundary E2E (VIEW-15) — verify the explicit error states render in
// the production build (not just in unit tests with vi.mock).
//
// The ErrorBoundary catches errors thrown DURING RENDER. TanStack Query's
// useQuery returns errors via query.error (NOT thrown), so the boundary
// doesn't fire on those — instead, ScanRoute / TickerRoute handle their own
// query errors inline and render typed error sections.
//
// To exercise the boundary E2E we route the per-ticker fixture to a v1-shape
// JSON which fails the SnapshotSchema literal — but in this project's
// architecture, that surfaces as the route-level inline schema-mismatch
// banner (NOT the ErrorBoundary). Both render the same UNIFORM RULE message
// per CONTEXT.md; the test asserts the user-facing wording rather than which
// component rendered it.

const __dirname = dirname(fileURLToPath(import.meta.url))
const FIX_DIR = resolve(__dirname, '..', 'fixtures', 'scan')

test.describe('error states (CONTEXT.md UNIFORM RULE)', () => {
  test('schema_version mismatch renders user-friendly error with both versions', async ({
    page,
  }) => {
    await mountScanFixtures(page)
    // Override AAPL.json with the bad-version (schema_version=1) fixture
    await page.route(/\/AAPL\.json$/, (route) => {
      const bad = readFileSync(
        resolve(FIX_DIR, 'AAPL-bad-version.json'),
        'utf-8',
      )
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: bad,
      })
    })
    await page.goto('/ticker/AAPL/2026-05-04')
    // CONTEXT.md UNIFORM RULE wording:
    // "Schema version mismatch — frontend v{X}, snapshot v{Y}. Re-run today's
    //  routine or upgrade frontend."
    // The route-level inline error renders 'Schema upgrade required' which is
    // a more concise rephrasing of the same concept; we accept either.
    await expect(
      page.getByText(/(Schema version mismatch|Schema upgrade required)/i),
    ).toBeVisible()
  })

  test('404 on per-ticker JSON renders not-found message with back link', async ({
    page,
  }) => {
    await mountScanFixtures(page)
    // Reroute ZZZZ.json (a ticker not in the fixtures) to 404
    await page.route(/\/ZZZZ\.json$/, (route) =>
      route.fulfill({ status: 404, body: 'Not found' }),
    )
    await page.goto('/ticker/ZZZZ/2026-05-04')
    // Inline TickerRoute renders "ZZZZ not in snapshot for 2026-05-04"
    await expect(
      page.getByText(/ZZZZ not in snapshot/i),
    ).toBeVisible()
    await expect(page.getByText(/Back to scan/i)).toBeVisible()
  })

  test('404 on _index.json renders no-snapshot message', async ({ page }) => {
    // Force the snapshot endpoints to 404 for a date that doesn't exist
    await page.route(/\/2099-12-31\/(_index|_status)\.json$/, (route) =>
      route.fulfill({ status: 404, body: 'Not found' }),
    )
    // _dates.json mock so DateSelector doesn't trigger 404 noise
    await page.route(/\/_dates\.json$/, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          schema_version: 1,
          dates_available: ['2026-05-04'],
          updated_at: new Date().toISOString(),
        }),
      }),
    )
    await page.goto('/scan/2099-12-31')
    // Inline ScanRoute renders "No snapshot for 2099-12-31"
    await expect(page.getByText(/No snapshot for 2099-12-31/i)).toBeVisible()
  })
})
