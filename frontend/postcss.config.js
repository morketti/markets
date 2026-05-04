// Tailwind v4 uses the dedicated @tailwindcss/vite plugin (configured in
// vite.config.ts) instead of a PostCSS plugin chain. This file exists only
// so editor integrations + Tailwind LSP find it; it intentionally exports
// no plugins (Vite plugin owns the pipeline).
export default {
  plugins: {},
}
