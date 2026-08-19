import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from './queryClient'
import './index.css'
import App from './App'

/**
 * Application entry point.
 *
 * React 18's createRoot API enables the new concurrent features (automatic batching,
 * transitions, Suspense improvements). The tree is wrapped in:
 *   1. StrictMode — activates additional checks and warnings for potential problems
 *      (only in development mode; does not affect production builds).
 *   2. QueryClientProvider — provides TanStack Query context to the entire tree,
 *      including App itself (which uses useQuery via useActivePedidosCount).
 *   3. BrowserRouter — provides client-side routing context via the History API.
 *      All route definitions live inside <App /> to keep the root entry small.
 */
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
