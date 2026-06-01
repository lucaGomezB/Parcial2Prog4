import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'

/**
 * Application entry point.
 *
 * React 18's createRoot API enables the new concurrent features (automatic batching,
 * transitions, Suspense improvements). The tree is wrapped in:
 *   1. StrictMode — activates additional checks and warnings for potential problems
 *      (only in development mode; does not affect production builds).
 *   2. BrowserRouter — provides client-side routing context via the History API.
 *      All route definitions live inside <App /> to keep the root entry small.
 */
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
