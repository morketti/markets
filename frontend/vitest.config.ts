/// <reference types="vitest" />
import { defineConfig, mergeConfig } from 'vitest/config'
import viteConfig from './vite.config'

// Vitest 2.x ships its own Vite 5 peer, so importing { defineConfig } from
// 'vite' in this file collides with vitest/config's narrower types when both
// load 'react()' as a plugin. The supported pattern is mergeConfig() which
// accepts the host vite config (Vite 6) and overlays the test-only fields.
//
// Once vitest 3.x lands (Vite 6 peer), this file collapses back to a single
// defineConfig with a test: {} block and imports react() directly.
export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: ['./src/setupTests.ts'],
      css: false,
      // Wave 1 lib + schemas only; component tests land in Wave 2-3.
      include: ['src/**/*.{test,spec}.{ts,tsx}'],
      exclude: ['tests/e2e/**', 'node_modules/**', 'dist/**'],
      coverage: {
        provider: 'v8',
        include: ['src/schemas/**', 'src/lib/**'],
        thresholds: {
          lines: 90,
          branches: 85,
        },
      },
    },
  }),
)
