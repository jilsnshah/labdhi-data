import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { HashRouter } from 'react-router-dom';

import './styles.css';

import { App } from './App';
import { AuthProvider } from '@/lib/auth';
import { initNative } from '@/lib/native';

// Hash routing: the APK serves the bundle from a file-like origin, where a
// history-based router would break on reload.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: true,
      staleTime: 10_000,
      // Keep showing the last known schedule when the phone loses signal.
      gcTime: 60 * 60 * 1000,
    },
  },
});

void initNative();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <HashRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </HashRouter>
    </QueryClientProvider>
  </StrictMode>,
);
