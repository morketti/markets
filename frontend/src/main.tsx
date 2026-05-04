import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from 'react-router/dom'

import { router } from './App'
import './index.css'

// TanStack Query defaults tuned for the GitHub-as-DB read-mostly model:
//   staleTime 5min → snapshot JSONs change at most once per day, so 5min
//                    is conservatively short while avoiding a refetch storm.
//   refetchOnWindowFocus false → tab focus shouldn't trigger a network round-
//                                trip when nothing about the data has changed.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

const rootEl = document.getElementById('root')
if (!rootEl) {
  throw new Error('Root element #root not found in index.html')
}

createRoot(rootEl).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
)
