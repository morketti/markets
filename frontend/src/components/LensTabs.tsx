import type { ReactNode } from 'react'
import { useSearchParams } from 'react-router'

import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs'
import { cn } from '@/lib/utils'

// LensTabs — three-lens UI for the Morning Scan view (VIEW-01 / Pitfall #8).
//
// CRITICAL DISCIPLINE: only ONE lens content area is in the DOM at any time.
// Radix Tabs.Content (the shadcn wrapper) defaults to forceMount=false →
// only the active tab's children mount. We deliberately do NOT pass
// forceMount=true. This is the test-locked invariant.
//
// URL sync: ?lens=position|short|long drives the active tab. setSearchParams
// uses { replace: true } so tab clicks don't pollute history (back-button
// would otherwise step through every lens click).
//
// Default: ?lens missing → 'position' (the headline lens per POSE-05).
// Invalid ?lens value → falls back to 'position' too.

export type LensId = 'position' | 'short' | 'long'

const VALID_LENS: ReadonlySet<LensId> = new Set(['position', 'short', 'long'])

export interface LensTabsProps {
  positionContent: ReactNode
  shortContent: ReactNode
  longContent: ReactNode
  className?: string
}

export function LensTabs({
  positionContent,
  shortContent,
  longContent,
  className,
}: LensTabsProps) {
  const [params, setParams] = useSearchParams()
  const lensParam = params.get('lens')
  const lens: LensId =
    lensParam && VALID_LENS.has(lensParam as LensId)
      ? (lensParam as LensId)
      : 'position'

  function setLens(next: LensId): void {
    const np = new URLSearchParams(params)
    np.set('lens', next)
    setParams(np, { replace: true })
  }

  return (
    <Tabs
      value={lens}
      onValueChange={(v) => setLens(v as LensId)}
      className={cn('w-full', className)}
    >
      {/* TabsList: explicit Notion-Clean palette overrides. The shadcn default
          uses bg-muted (which we don't have); we replace with bg-surface +
          border-border for the strip and rely on data-[state=active] hooks
          to surface the accent underline. */}
      <TabsList className="h-auto w-full justify-start gap-2 rounded-md border border-border bg-surface p-1 text-fg-muted">
        <TabsTrigger
          value="position"
          className="rounded-sm px-3 py-1.5 text-sm font-medium data-[state=active]:bg-bg data-[state=active]:text-accent data-[state=active]:shadow-none"
          data-testid="lens-tab-position"
        >
          Position Adjustment
        </TabsTrigger>
        <TabsTrigger
          value="short"
          className="rounded-sm px-3 py-1.5 text-sm font-medium data-[state=active]:bg-bg data-[state=active]:text-accent data-[state=active]:shadow-none"
          data-testid="lens-tab-short"
        >
          Short-Term Opportunities
        </TabsTrigger>
        <TabsTrigger
          value="long"
          className="rounded-sm px-3 py-1.5 text-sm font-medium data-[state=active]:bg-bg data-[state=active]:text-accent data-[state=active]:shadow-none"
          data-testid="lens-tab-long"
        >
          Long-Term Thesis Status
        </TabsTrigger>
      </TabsList>
      {/* Each TabsContent only mounts its children when value===lens.
          DO NOT pass forceMount — that would defeat Pitfall #8. */}
      <TabsContent value="position" data-testid="lens-content-position">
        {positionContent}
      </TabsContent>
      <TabsContent value="short" data-testid="lens-content-short">
        {shortContent}
      </TabsContent>
      <TabsContent value="long" data-testid="lens-content-long">
        {longContent}
      </TabsContent>
    </Tabs>
  )
}
