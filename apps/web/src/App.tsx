import { BrowserRouter, Navigate, Route, Routes } from 'react-router';
import { AuthProvider } from './lib/auth';
import { Landing } from './pages/Landing';
import { Workspace } from './pages/Workspace';

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
    </AuthProvider>
  );
}
