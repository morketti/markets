import { createBrowserRouter, redirect } from 'react-router'

import Root from './routes/Root'
import ScanRoute from './routes/ScanRoute'
import TickerRoute from './routes/TickerRoute'

// react-router v7 data-router. Three route shapes per CONTEXT.md:
//   /                            → redirect to /scan/today (Wave 4 will switch
//                                  to "latest available date" via _dates.json)
//   /scan/:date                  → Morning Scan view (Wave 2 fills in)
//   /ticker/:symbol/:date?       → Per-Ticker Deep-Dive (Wave 3 fills in)
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
    ],
  },
])
