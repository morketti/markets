import { Component, type ErrorInfo, type ReactNode } from 'react'
import { Link } from 'react-router'

import { FetchNotFoundError, SchemaMismatchError } from '@/lib/fetchSnapshot'

// ErrorBoundary — VIEW-15 + CONTEXT.md UNIFORM RULE.
//
// Catches errors thrown during render of the wrapped subtree and renders an
// EXPLICIT error UI per failure mode — never a white-screen crash, never a
// silent fallback, never a "data unavailable" toast.
//
// Three branches:
//
//   1. SchemaMismatchError — surfaces BOTH versions ("frontend expects v2,
//      snapshot is older"). Per CONTEXT.md: "Re-run today's routine or
//      upgrade frontend." with a link back to /scan/today.
//
//   2. FetchNotFoundError — context-sensitive based on the URL pattern:
//        - /{TICKER}.json    → "{ticker} not in run for {date}."
//        - /_index.json or /_status.json → "No snapshot for {date}."
//
//   3. Generic Error → muted "Something went wrong: {message}" with a reload
//      link.
//
// Why a class component in React 19? Error boundaries STILL require class
// components in React 19 — the function-component error-boundary RFC has not
// shipped. ErrorBoundary is one of the few places where the class API is the
// only API.
//
// IMPORTANT: TanStack Query queries do NOT throw to the boundary by default;
// errors live in `query.error`. Routes (ScanRoute / TickerRoute) handle
// query errors INLINE (rendering their own typed error sections). This
// boundary is the LAST-RESORT catch — for errors thrown OUTSIDE of TanStack
// Query (component lifecycle errors, render errors, errors from non-query
// fetches). It's the safety net, not the primary error-handling surface.

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Console-log for devtools; production can layer in Sentry/etc later.
    // eslint-disable-next-line no-console
    console.error('ErrorBoundary caught:', error, info)
  }

  reset = (): void => {
    this.setState({ error: null })
  }

  render(): ReactNode {
    const { error } = this.state
    if (!error) return this.props.children

    if (error instanceof SchemaMismatchError) {
      return <SchemaMismatchView error={error} reset={this.reset} />
    }
    if (error instanceof FetchNotFoundError) {
      return <NotFoundView error={error} reset={this.reset} />
    }
    return <GenericErrorView error={error} reset={this.reset} />
  }
}

// ----- Render branches -----

interface BranchProps<E extends Error> {
  error: E
  reset: () => void
}

function SchemaMismatchView({ error, reset }: BranchProps<SchemaMismatchError>) {
  // Frontend version is locked to v2 by SnapshotSchema.schema_version literal.
  const frontendVersion = 2
  // Try to extract the actual snapshot version from the zodError issues.
  // SnapshotSchema declares schema_version: z.literal(2) → on mismatch, the
  // issue is at path ['schema_version'] with `received` carrying the bad value.
  let snapshotVersion: string | number | undefined
  for (const issue of error.zodError.issues) {
    const last = issue.path[issue.path.length - 1]
    if (last === 'schema_version') {
      const received = (issue as { received?: unknown }).received
      if (received !== undefined) {
        snapshotVersion = String(received)
      }
      break
    }
  }

  return (
    <section
      className="rounded-md border border-bearish/30 bg-bearish/10 px-4 py-6 text-sm"
      data-testid="error-boundary-schema-mismatch"
    >
      <h2 className="font-mono text-base font-semibold text-bearish">
        Schema version mismatch
      </h2>
      <p className="mt-2 text-fg">
        Frontend expects schema <span className="font-mono">v{frontendVersion}</span>
        {snapshotVersion !== undefined ? (
          <>
            , snapshot is <span className="font-mono">v{snapshotVersion}</span>
          </>
        ) : (
          <>, snapshot is older</>
        )}
        . Re-run today's routine or upgrade the frontend.
      </p>
      <p className="mt-4 text-xs text-fg-muted">
        URL: <span className="font-mono break-all">{error.url}</span>
      </p>
      <div className="mt-4 flex items-center gap-3">
        <Link
          to="/scan/today"
          onClick={reset}
          className="font-mono text-xs uppercase tracking-wider text-accent hover:text-fg"
          data-testid="error-boundary-reset"
        >
          Reload
        </Link>
      </div>
    </section>
  )
}

function NotFoundView({ error, reset }: BranchProps<FetchNotFoundError>) {
  // Detect URL shape: per-ticker JSON ends in /{TICKER}.json (uppercase letters
  // / digits / dots / hyphens — uppercase first to disambiguate _index/_status).
  const url = error.url
  const tickerMatch = url.match(/\/([A-Z0-9][A-Z0-9.-]*)\.json$/)
  const dateMatch = url.match(/\/data\/(\d{4}-\d{2}-\d{2}|today)\//)
  const date = dateMatch ? dateMatch[1] : 'today'

  if (tickerMatch) {
    const ticker = tickerMatch[1]
    return (
      <section
        className="rounded-md border border-bearish/30 bg-bearish/10 px-4 py-6 text-sm"
        data-testid="error-boundary-not-found"
        data-kind="ticker"
      >
        <h2 className="font-mono text-base font-semibold text-bearish">
          {ticker} not in run for {date}
        </h2>
        <p className="mt-2 text-fg">
          The selected ticker has no data for this date. It may have failed
          during the routine — see the scan view for the day's run status.
        </p>
        <div className="mt-4 flex items-center gap-3">
          <Link
            to={`/scan/${date}`}
            onClick={reset}
            className="font-mono text-xs uppercase tracking-wider text-accent hover:text-fg"
            data-testid="error-boundary-reset"
          >
            Back to scan
          </Link>
        </div>
      </section>
    )
  }

  // Snapshot-level 404 (_index.json or _status.json or _dates.json).
  return (
    <section
      className="rounded-md border border-bearish/30 bg-bearish/10 px-4 py-6 text-sm"
      data-testid="error-boundary-not-found"
      data-kind="snapshot"
    >
      <h2 className="font-mono text-base font-semibold text-bearish">
        No snapshot for {date}
      </h2>
      <p className="mt-2 text-fg">
        No scan data is available for the selected date. Try a different date
        from the dropdown, or return to today's scan.
      </p>
      <div className="mt-4 flex items-center gap-3">
        <Link
          to="/scan/today"
          onClick={reset}
          className="font-mono text-xs uppercase tracking-wider text-accent hover:text-fg"
          data-testid="error-boundary-reset"
        >
          Today's scan
        </Link>
      </div>
    </section>
  )
}

function GenericErrorView({ error, reset }: BranchProps<Error>) {
  return (
    <section
      className="rounded-md border border-bearish/30 bg-bearish/10 px-4 py-6 text-sm"
      data-testid="error-boundary-generic"
    >
      <h2 className="font-mono text-base font-semibold text-bearish">
        Something went wrong
      </h2>
      <p className="mt-2 text-fg">{error.message}</p>
      <div className="mt-4 flex items-center gap-3">
        <Link
          to="/scan/today"
          onClick={reset}
          className="font-mono text-xs uppercase tracking-wider text-accent hover:text-fg"
          data-testid="error-boundary-reset"
        >
          Reload
        </Link>
      </div>
    </section>
  )
}
