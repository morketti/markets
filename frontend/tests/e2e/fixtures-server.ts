import type { Page } from '@playwright/test'
import { readFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

// fixtures-server — Playwright route() interceptors that serve the local
// fixture JSONs in place of raw.githubusercontent.com fetches.
//
// Wave 2 design choice: instead of starting an HTTP server we use Playwright's
// page.route() to fulfill matched URLs with file content. This sidesteps
// CORS/HTTPS issues and keeps the fixture flow entirely in-process.
//
// run_completed_at + run_started_at are computed at request time so the
// staleness badge always shows GREEN (fresh fixture) regardless of when the
// fixture file was last regenerated.

const __dirname = dirname(fileURLToPath(import.meta.url))
// Fixtures live at frontend/tests/fixtures/scan/, this file at frontend/tests/e2e/.
const FIX_DIR = resolve(__dirname, '..', 'fixtures', 'scan')

function readFix(name: string): string {
  return readFileSync(resolve(FIX_DIR, name), 'utf-8')
}

export interface MountOptions {
  /** If true, ALL ticker fetches return 404 — used for the schema-mismatch / failure path. */
  failAllTickers?: boolean
  /** If true, only the AAPL fixture succeeds; NVDA/MSFT 404. */
  partialFailure?: boolean
  /** Ages run_completed_at by the given hours (defaults to 2h). */
  ageHours?: number
  /**
   * If true, MSFT.json route fulfills from MSFT-no-dissent.json instead.
   * Used by Phase 7 decision.spec.ts to exercise the has_dissent: false
   * branch of DissentPanel (Pitfall #12 — intentional silence path).
   */
  msftNoDissent?: boolean
}

export async function mountScanFixtures(
  page: Page,
  options: MountOptions = {},
): Promise<void> {
  const ageHours = options.ageHours ?? 2

  // _status.json
  await page.route(/raw\.githubusercontent\.com\/.+\/_status\.json$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: readFix('_status.json'),
    })
  })

  // _index.json — patch run_completed_at so staleness is fresh
  await page.route(/raw\.githubusercontent\.com\/.+\/_index\.json$/, async (route) => {
    const idx = JSON.parse(readFix('_index.json')) as Record<string, unknown>
    const now = Date.now()
    idx.run_completed_at = new Date(now - ageHours * 3_600_000).toISOString()
    idx.run_started_at = new Date(now - (ageHours + 0.5) * 3_600_000).toISOString()
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(idx),
    })
  })

  // Per-ticker JSONs (AAPL, NVDA, MSFT)
  await page.route(
    /raw\.githubusercontent\.com\/.+\/(AAPL|NVDA|MSFT)\.json$/,
    async (route) => {
      const url = route.request().url()
      const m = url.match(/(AAPL|NVDA|MSFT)\.json$/)
      if (!m) {
        await route.fulfill({ status: 404, body: 'no fixture match' })
        return
      }
      const ticker = m[1]
      if (options.failAllTickers) {
        await route.fulfill({ status: 404, body: 'simulated failure' })
        return
      }
      if (options.partialFailure && ticker !== 'AAPL') {
        await route.fulfill({ status: 404, body: 'simulated partial failure' })
        return
      }
      // Phase 7: optionally swap MSFT.json → MSFT-no-dissent.json for the
      // decision.spec.ts has_dissent: false branch.
      const fixtureName =
        options.msftNoDissent && ticker === 'MSFT'
          ? 'MSFT-no-dissent.json'
          : `${ticker}.json`
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: readFix(fixtureName),
      })
    },
  )
}
