// Tailwind v4 is CSS-first via the @tailwindcss/vite plugin + @theme directive
// in src/index.css. This config is intentionally minimal — it exists for IDE
// integration (VS Code Tailwind plugin) and as an explicit content-scanning
// hint for editor tooling. The palette tokens themselves live in src/index.css.
import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
}

export default config
