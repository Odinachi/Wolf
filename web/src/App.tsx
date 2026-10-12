import { Analytics, type BeforeSendEvent } from '@vercel/analytics/react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router';
import { AuthProvider } from './lib/auth';
import { Landing } from './pages/Landing';
import { Workspace } from './pages/Workspace';

/** Group workspace pages and keep project ids out of analytics: /p/prj_abc -> /p/[id]. */
function redactProjectIds(event: BeforeSendEvent): BeforeSendEvent {
  return { ...event, url: event.url.replace(/\/p\/[^/?#]+/, '/p/[id]') };
}

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/p/:id" element={<Workspace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      {/* Vercel Web Analytics: page views only, no cookies. Active on Vercel deployments. */}
      <Analytics beforeSend={redactProjectIds} />
    </AuthProvider>
  );
}
