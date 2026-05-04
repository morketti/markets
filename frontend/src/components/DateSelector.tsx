import { useLocation, useNavigate, useParams } from 'react-router'

import { useDates } from '@/lib/loadDates'

// DateSelector — header dropdown listing every snapshot date the routine has
// produced (read from data/_dates.json — Wave 0 file).
//
// VIEW-14: selecting a date navigates the router to the same route shape with
// the new :date param. Examples:
//   /scan/today           → /scan/2026-04-30   (after picking 2026-04-30)
//   /ticker/AAPL/today    → /ticker/AAPL/2026-04-30
//
// Native <select> chosen for v1 — Notion-Clean is restraint-first; native
// controls are mobile-friendly (iOS picker UI), keyboard-accessible by
// default, no layout shift, no extra Radix primitive to vendor. Future v1.x
// could switch to a shadcn Select for richer styling.
//
// Loading + error states: render an unobtrusive disabled select so the header
// layout doesn't shift around. Once data lands, options populate. If the
// fetch errors (e.g. _dates.json doesn't exist yet on a fresh deploy), we
// render only the "today" option — the user can still navigate, they just
// don't see a dropdown of historical dates.

export function DateSelector() {
  const { data, isLoading, error } = useDates()
  const navigate = useNavigate()
  const params = useParams<{ date?: string; symbol?: string }>()
  const location = useLocation()

  const currentDate = params.date ?? 'today'

  function onChange(newDate: string) {
    // Preserve route shape: /scan/:date vs /ticker/:symbol/:date
    if (location.pathname.startsWith('/ticker/') && params.symbol) {
      navigate(`/ticker/${params.symbol}/${newDate}${location.search}`)
    } else {
      navigate(`/scan/${newDate}${location.search}`)
    }
  }

  // Newest-first dropdown ordering — storage writes ascending; reverse here
  // so the most recent date is at the top under "today".
  const dates = data?.dates_available ?? []
  const datesDesc = [...dates].reverse()

  return (
    <select
      value={currentDate}
      onChange={(e) => onChange(e.target.value)}
      className="rounded border border-border bg-bg px-3 py-1.5 font-mono text-sm text-fg focus:border-accent focus:outline-none"
      data-testid="date-selector"
      aria-label="Select snapshot date"
      disabled={isLoading || (!!error && dates.length === 0)}
    >
      <option value="today">today</option>
      {datesDesc.map((d) => (
        <option key={d} value={d}>
          {d}
        </option>
      ))}
    </select>
  )
}
