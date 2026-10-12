import { FirebaseError } from 'firebase/app';
import {
  GithubAuthProvider,
  GoogleAuthProvider,
  onIdTokenChanged,
  signInWithPopup,
  signInWithRedirect,
  signOut,
} from 'firebase/auth';
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { ApiError, api, type AuthProviderId, type User } from './api';
import { firebaseAuth, firebaseEnabled } from './firebase';

export type AccessMode = 'open' | 'waitlist';

interface AuthState {
  user: User | null;
  loading: boolean;
  enabled: boolean;
  /** 'waitlist' before launch: the site collects signups and only invited people can sign in. */
  accessMode: AccessMode | null;
  /** Why the last sign-in was refused (e.g. not invited yet). */
  accessError: string | null;
  clearAccessError: () => void;
  /** Signs in with a popup (falling back to a redirect if popups are blocked). Throws a readable error. */
  signIn: (provider: AuthProviderId) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

function providerFor(id: AuthProviderId) {
  if (id === 'github') return new GithubAuthProvider();
  const google = new GoogleAuthProvider();
  google.setCustomParameters({ prompt: 'select_account' });
  return google;
}

function readable(error: unknown): string | null {
  const code = error instanceof FirebaseError ? error.code : '';
  if (code === 'auth/popup-closed-by-user' || code === 'auth/cancelled-popup-request') return null; // the user changed their mind
  if (code === 'auth/account-exists-with-different-credential') {
    return 'You already signed up with the same email using the other provider. Sign in with that one instead.';
  }
  if (code === 'auth/unauthorized-domain') return 'This site isn’t allowed to sign in yet. Add its domain in the Firebase console.';
  if (code === 'auth/network-request-failed') return 'Network problem. Check your connection and try again.';
  return 'Sign-in failed. Please try again.';
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(firebaseEnabled);
  const [accessMode, setAccessMode] = useState<AccessMode | null>(null);
  const [accessError, setAccessError] = useState<string | null>(null);

  useEffect(() => {
    api.config()
      .then(c => setAccessMode(c.access_mode))
      // If the backend can't be reached, a production site stays closed rather than open.
      .catch(() => setAccessMode(import.meta.env.PROD ? 'waitlist' : 'open'));
  }, []);

  useEffect(() => {
    const auth = firebaseAuth();
    if (!auth) return;
    // Fires on sign-in, sign-out and token refresh. The backend creates the user on first /me.
    return onIdTokenChanged(auth, async fbUser => {
      if (!fbUser) {
        setUser(null);
        setLoading(false);
        return;
      }
      try {
        setUser(await api.me());
        setAccessError(null);
      } catch (e) {
        setUser(null);
        if (e instanceof ApiError && e.status === 403) {
          // Signed in with Firebase but not allowed in (e.g. not invited yet): don't stay half signed in.
          setAccessError(e.message);
          await signOut(auth);
        }
      } finally {
        setLoading(false);
      }
    });
  }, []);

  const signIn = useCallback(async (id: AuthProviderId) => {
    const auth = firebaseAuth();
    if (!auth) throw new Error('Sign-in isn’t set up for this site.');
    try {
      await signInWithPopup(auth, providerFor(id));
    } catch (error) {
      if (error instanceof FirebaseError && error.code === 'auth/popup-blocked') {
        await signInWithRedirect(auth, providerFor(id));
        return;
      }
      const message = readable(error);
      if (message) throw new Error(message);
      throw new DOMException('cancelled', 'AbortError');
    }
  }, []);

  const logout = useCallback(async () => {
    const auth = firebaseAuth();
    if (auth) await signOut(auth);
    setUser(null);
  }, []);

  const clearAccessError = useCallback(() => setAccessError(null), []);
  const value = useMemo(
    () => ({ user, loading, enabled: firebaseEnabled, accessMode, accessError, clearAccessError, signIn, logout }),
    [user, loading, accessMode, accessError, clearAccessError, signIn, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
