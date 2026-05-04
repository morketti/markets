import type { ZodError, ZodType } from 'zod'

// fetchSnapshot — the project's single GitHub-raw read boundary.
//
// All per-ticker JSONs, _status.json, _index.json, and _dates.json flow
// through fetchAndParse(url, schema). Three failure modes mapped to typed
// errors so consumers (TanStack Query queries + Wave 4 ErrorBoundary) can
// render distinct UI:
//
//   FetchNotFoundError      → 404 from GitHub raw (snapshot missing for
//                             this date / ticker not in today's run)
//   SchemaMismatchError     → zod parse failure (CONTEXT.md UNIFORM RULE —
//                             explicit error banner, NOT a silent coercion)
//   Error (generic)         → other non-2xx (rate-limited, CDN error, etc.)

export class SchemaMismatchError extends Error {
  readonly url: string
  readonly zodError: ZodError

  constructor(url: string, zodError: ZodError) {
    super(`Schema mismatch at ${url}: ${zodError.message}`)
    this.name = 'SchemaMismatchError'
    this.url = url
    this.zodError = zodError
  }
}

export class FetchNotFoundError extends Error {
  readonly url: string

  constructor(url: string) {
    super(`Not found: ${url}`)
    this.name = 'FetchNotFoundError'
    this.url = url
  }
}

// Build-time env vars — Vite inlines these at build, so the static bundle
// already has the right raw.githubusercontent.com URL hardcoded. .env.local
// (placeholder) keeps dev mode booting; production reads from Vercel env.
const GH_USER = (import.meta.env.VITE_GH_USER as string | undefined) ?? 'example-user'
const GH_REPO = (import.meta.env.VITE_GH_REPO as string | undefined) ?? 'example-repo'

export const RAW_BASE = `https://raw.githubusercontent.com/${GH_USER}/${GH_REPO}/main`

// URL builders — single source of truth for snapshot path layout. If
// routine/storage.py ever changes the directory layout, only this file
// updates (consumers import the builders, not raw template strings).
export const snapshotUrl = (date: string, ticker: string): string =>
  `${RAW_BASE}/data/${date}/${ticker}.json`

export const indexUrl = (date: string): string =>
  `${RAW_BASE}/data/${date}/_index.json`

export const statusUrl = (date: string): string =>
  `${RAW_BASE}/data/${date}/_status.json`

export const datesUrl = (): string => `${RAW_BASE}/data/_dates.json`

// fetchAndParse — TanStack Query queryFn. Generic over T = z.infer<schema>.
// Doubles as the unit-of-truth for fetch + parse — the only place fetch()
// is called in the read layer (Wave 2-4 components compose this via
// useQuery(['snapshot', date, ticker], () => fetchAndParse(snapshotUrl(...),
// SnapshotSchema)).
export async function fetchAndParse<T>(
  url: string,
  schema: ZodType<T>,
): Promise<T> {
  const res = await fetch(url, { headers: { Accept: 'application/json' } })
  if (res.status === 404) {
    throw new FetchNotFoundError(url)
  }
  if (!res.ok) {
    throw new Error(`Fetch ${url} failed: ${res.status} ${res.statusText}`)
  }
  const json = (await res.json()) as unknown
  const result = schema.safeParse(json)
  if (!result.success) {
    throw new SchemaMismatchError(url, result.error)
  }
  return result.data
}
