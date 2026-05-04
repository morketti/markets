import { test, expect } from '@playwright/test'

// Wave 1 smoke E2E — proves the scaffold boots end-to-end:
//   1. `/` redirects to `/scan/today` (react-router v7 loader works)
//   2. ScanRoute renders the placeholder heading (React + router + bundle ok)
//
// Wave 2-4 add real-content E2E specs around this. The smoke test is the
// CI/CD canary that flips RED if the build pipeline breaks.
test('redirects / to /scan/today and renders placeholder heading', async ({
  page,
}) => {
  await page.goto('/')
  await expect(page).toHaveURL(/\/scan\/today$/)
  await expect(
    page.getByRole('heading', { name: /Morning Scan — today/i }),
  ).toBeVisible()
})
