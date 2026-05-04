import { Outlet, Link } from 'react-router'

// Wave 1 layout — header (with placeholder staleness slot, populated in Wave
// 2-4 by StalenessBadge) + main outlet. Notion-Clean spec: hairline border,
// generous gutters, no chrome.
export default function Root() {
  return (
    <div className="flex min-h-full flex-col bg-bg text-fg">
      <header className="border-b border-border px-6 py-4">
        <div className="flex items-center justify-between">
          <Link
            to="/scan/today"
            className="font-mono text-sm font-semibold tracking-tight text-fg"
            data-testid="brand-link"
          >
            MARKETS
          </Link>
          <div data-testid="staleness-slot" className="text-xs text-fg-muted">
            {/* Wave 2: <StalenessBadge /> */}
          </div>
        </div>
      </header>
      <main className="flex-1 px-6 py-8">
        <Outlet />
      </main>
    </div>
  )
}
