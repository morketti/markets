import { createBrowserRouter, redirect } from 'react-router'

import Root from './routes/Root'
import ScanRoute from './routes/ScanRoute'
import TickerRoute from './routes/TickerRoute'
import DecisionRoute from './routes/DecisionRoute'

// react-router v7 data-router. Three pillar route shapes per CONTEXT.md:
//   /                            → redirect to /scan/today (Wave 4 will switch
//                                  to "latest available date" via _dates.json)
//   /scan/:date                  → Morning Scan view (3-lens tabs, Phase 6)
//   /ticker/:symbol/:date?       → Per-Ticker Deep-Dive (Phase 6) — analysis-first
//   /decision/:symbol/:date?     → Decision-Support View (Phase 7) — recommendation-first
//
// Cross-link symmetry between TickerRoute and DecisionRoute: each header has a
// small link to the other route preserving :symbol and :date so the user can
// flip between "what's the data" and "what should I do" with date integrity.
//
// Root is the layout (header + outlet). The redirect from "/" runs as a
// loader so it fires before any rendering happens — no flash of placeholder.
export const router = createBrowserRouter([
  {
    path: '/',
    loader: () => redirect('/scan/today'),
  },
  {
    path: '/',
    element: <Root />,
    children: [
      {
        path: 'scan/:date',
        element: <ScanRoute />,
      },
      {
        path: 'ticker/:symbol/:date?',
        element: <TickerRoute />,
      },
      {
        path: 'decision/:symbol/:date?',
        element: <DecisionRoute />,
      },
    ],
  },
])
