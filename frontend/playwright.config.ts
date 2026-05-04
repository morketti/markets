import { defineConfig, devices } from '@playwright/test'

// Three projects per VALIDATION.md sampling: chromium-desktop is the smoke
// project for Wave 1; mobile-safari + mobile-chrome become the manual-phone-
// test stand-ins in Wave 4 (VIEW-12 mobile responsive).
//
// baseURL points to `pnpm preview` (port 4173) so the production build is
// what's tested — closer to the Vercel deploy than `pnpm dev`.
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:4173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium-desktop',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 14'] },
    },
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 7'] },
    },
  ],
  webServer: {
    command: 'pnpm preview',
    port: 4173,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
})
