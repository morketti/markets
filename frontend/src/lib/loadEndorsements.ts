// novel-to-this-project — Phase 9 JSONL loader + 90-day filter + ticker filter
// + date-desc sort for endorsements. Mirrors useRefreshData TanStack hook
// pattern; fetches text (NOT JSON) since the wire format is JSONL (one record
// per line). Reuses RAW_BASE + SchemaMismatchError from fetchSnapshot.ts —
// zero new dependencies, zero new error classes.
//
// 90-day filter operates on `date` (the call date), NOT captured_at (the
// entry date) — Pitfall #2 from 09-RESEARCH.md. Test
// `filter_uses_call_date_NOT_captured_at` locks this contract.

import { useQuery } from '@tanstack/react-query'

import { RAW_BASE, SchemaMismatchError } from '@/lib/fetchSnapshot'
import { EndorsementSchema, type Endorsement } from '@/schemas/endorsement'

export const endorsementsUrl = (): string => `${RAW_BASE}/endorsements.jsonl`

const NINETY_DAYS_MS = 90 * 24 * 60 * 60 * 1000

export async function fetchEndorsementsJsonl(): Promise<Endorsement[]> {
  const url = endorsementsUrl()
  const res = await fetch(url, { headers: { Accept: 'text/plain' } })
  if (res.status === 404) return [] // file optional — never crash
  if (!res.ok) {
    throw new Error(`Fetch ${url} failed: ${res.status} ${res.statusText}`)
  }
  const text = await res.text()
  const out: Endorsement[] = []
  for (const line of text.split('\n')) {
    if (!line.trim()) continue // skip blank + trailing newline
    const json: unknown = JSON.parse(line)
    const result = EndorsementSchema.safeParse(json)
    if (!result.success) {
      throw new SchemaMismatchError(url, result.error)
    }
    out.push(result.data)
  }
  return out
}

/**
 * Pure helper — filter to a single ticker's endorsements within the last 90
 * days, sorted by call date descending. Tested directly without a fetch
 * dependency.
 *
 * @param all     full endorsements list (from fetchEndorsementsJsonl)
 * @param symbol  active ticker (case-insensitive — upcased before compare)
 * @param now     reference "today" — defaults to new Date(); tests inject
 *                a fixed Date for deterministic 90-day boundary checks
 */
export function filterRecent90(
  all: Endorsement[],
  symbol: string,
  now: Date = new Date(),
): Endorsement[] {
  const cutoff = now.getTime() - NINETY_DAYS_MS
  const sym = symbol.toUpperCase()
  return all
    .filter((e) => e.ticker === sym)
    .filter((e) => new Date(`${e.date}T00:00:00Z`).getTime() >= cutoff)
    .sort((a, b) => b.date.localeCompare(a.date))
}

export function useEndorsements(symbol: string) {
  return useQuery<Endorsement[]>({
    queryKey: ['endorsements'], // global key — full file is small, client filters
    queryFn: fetchEndorsementsJsonl,
    staleTime: 10 * 60 * 1000,
    enabled: symbol.length > 0,
    select: (all) => filterRecent90(all, symbol),
  })
}
