import { useParams } from 'react-router'

// Wave 1 stub — Wave 2 populates with three lens tabs (Position Adjustment /
// Short-Term Opportunities / Long-Term Thesis Status), URL-synced via
// ?lens=... query param.
//
// The placeholder heading is what tests/e2e/smoke.spec.ts asserts for "page
// renders SOMETHING after redirect from /".
export default function ScanRoute() {
  const { date } = useParams<{ date: string }>()
  return (
    <section>
      <h1 className="text-2xl font-semibold tracking-tight">
        Morning Scan — {date ?? 'today'}
      </h1>
      <p className="mt-2 text-sm text-fg-muted">
        Wave 2 will fill in the three-lens view here.
      </p>
    </section>
  )
}
