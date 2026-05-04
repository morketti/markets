// Number / date / ticker formatters — all centered on JetBrains Mono numeric
// rendering (CONTEXT.md typography lock). Centralized so we don't sprinkle
// Intl.NumberFormat-with-locale-options across components.

const NUMBER_FORMATTER = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 2,
})

const PERCENT_FORMATTER = new Intl.NumberFormat('en-US', {
  style: 'percent',
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})

const COMPACT_FORMATTER = new Intl.NumberFormat('en-US', {
  notation: 'compact',
  maximumFractionDigits: 1,
})

export function formatNumber(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return '—'
  return NUMBER_FORMATTER.format(n)
}

export function formatPercent(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return '—'
  return PERCENT_FORMATTER.format(n)
}

export function formatCompact(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return '—'
  return COMPACT_FORMATTER.format(n)
}

// formatDate — accepts ISO-8601 strings, Date objects, or null/undefined.
// Renders YYYY-MM-DD by default (matches the data/{date}/ folder names so
// URL params and display strings stay legibly identical).
export function formatDate(input: string | Date | null | undefined): string {
  if (input === null || input === undefined) return '—'
  const date = typeof input === 'string' ? new Date(input) : input
  if (Number.isNaN(date.getTime())) return '—'
  const yyyy = date.getUTCFullYear()
  const mm = String(date.getUTCMonth() + 1).padStart(2, '0')
  const dd = String(date.getUTCDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

// formatTicker — uppercase + hyphen normalize (mirrors
// analysts.schemas.normalize_ticker conceptually). The frontend NEVER trusts
// inbound ticker casing for routing/display — always normalize first.
export function formatTicker(symbol: string): string {
  return symbol.trim().toUpperCase().replace(/\./g, '-')
}
