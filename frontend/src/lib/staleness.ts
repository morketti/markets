// Staleness logic — VIEW-11 thresholds locked to REQUIREMENTS.md (NOT
// ROADMAP.md's earlier 2h/12h text, which would flip the badge AMBER before
// noon on a normal 6am ET routine day).
//
// Decision matrix (see CONTEXT.md "Staleness Thresholds — LOCKED" section):
//
//   age <  6h && !partial  → GREEN
//   age <  6h &&  partial  → AMBER  (6-24h-equivalent: partial run is
//                                    intrinsically less trustworthy)
//   6h ≤ age ≤ 24h         → AMBER  (regardless of partial flag)
//   age >  24h             → RED    (regardless of partial flag — at this
//                                    point staleness dominates over partial)
//
// Boundary semantics:
//   - exactly 6h  → AMBER  (>= SIX_HOURS_MS comparison)
//   - exactly 24h → AMBER  (<= TWENTY_FOUR_HOURS_MS — the > check on RED is
//                           strict-greater-than, so 24h-on-the-dot stays AMBER)
//
// `now` is injectable for deterministic tests (Date.now() default).

export type StalenessLevel = 'GREEN' | 'AMBER' | 'RED'

export const SIX_HOURS_MS = 6 * 60 * 60 * 1000
export const TWENTY_FOUR_HOURS_MS = 24 * 60 * 60 * 1000

export function computeStaleness(
  snapshotIso: string,
  partial: boolean,
  now: Date = new Date(),
): StalenessLevel {
  const snapshotMs = new Date(snapshotIso).getTime()
  if (Number.isNaN(snapshotMs)) {
    // Defensive — an unparseable timestamp is functionally as stale as
    // possible. Wave 4 ErrorBoundary will catch the upstream parse error
    // separately; here we fail loud on the badge.
    return 'RED'
  }
  const ageMs = now.getTime() - snapshotMs

  if (ageMs > TWENTY_FOUR_HOURS_MS) return 'RED'
  if (ageMs >= SIX_HOURS_MS) return 'AMBER'
  // age < 6h
  return partial ? 'AMBER' : 'GREEN'
}
