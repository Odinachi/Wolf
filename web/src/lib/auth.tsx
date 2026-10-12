import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { api, type AuthProvider, type User } from './api';

interface AuthState {
  user: User | null;
  loading: boolean;
  /** Leaves the app to sign in with the provider, then comes back to `next`. */
  signIn: (provider: AuthProvider, next?: string) => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.me().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false));
  }, []);

  const signIn = useCallback((provider: AuthProvider, next = window.location.pathname) => {
    window.location.assign(`/api/auth/${provider}/login?next=${encodeURIComponent(next)}`);
  }, []);
  const logout = useCallback(async () => {
    await api.logout().catch(() => undefined);
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, loading, signIn, logout }), [user, loading, signIn, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
