import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Vite 6 + React 19 + Tailwind v4 (CSS-first via @tailwindcss/vite plugin).
// Path alias `@` → `./src` mirrors the tsconfig.json paths entry so import
// resolution agrees between the build (Vite) and the typechecker (tsc).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
  },
  preview: {
    port: 4173,
  },
})
