import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'

import App from './App'
import './styles/global.css'

const queryClient = new QueryClient({
  defaultOptions: {
    // r011 redirect-03：切回窗口立刻刷新（原来 false，从别的窗口回来会停在旧状态，观感「没反应」）
    queries: { retry: 1, refetchOnWindowFocus: true, staleTime: 3_000 },
  },
})

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
