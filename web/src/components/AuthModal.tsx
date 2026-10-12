import { Github, Loader2, X } from 'lucide-react';
import { useEffect, useState, type ReactNode } from 'react';
import type { AuthProviderId } from '../lib/api';
import { useAuth } from '../lib/auth';
import { LogoMark } from './Logo';

interface Props {
  open: boolean;
  /** Shown when the user was asked to sign in to run their prompt. */
  reason?: string;
  /** Called just before sign-in starts (e.g. to remember a pending prompt across a redirect). */
  onBeforeSignIn?: () => void;
  /** Called when sign-in was cancelled or failed. */
  onSignInFailed?: () => void;
  onClose: () => void;
}

function GoogleLogo() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden>
      <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z" />
      <path fill="#FF3D00" d="m6.3 14.7 6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
      <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-7.9l-6.5 5C9.5 39.6 16.2 44 24 44z" />
      <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C36.9 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z" />
    </svg>
  );
}

const PROVIDERS: Record<AuthProviderId, { label: string; icon: ReactNode; className: string }> = {
  github: { label: 'Continue with GitHub', icon: <Github size={18} />, className: 'bg-zinc-950 text-white hover:bg-zinc-800' },
  google: { label: 'Continue with Google', icon: <GoogleLogo />, className: 'bg-white text-zinc-900 ring-1 ring-zinc-200 hover:bg-zinc-50' },
};

export function AuthModal({ open, reason, onBeforeSignIn, onSignInFailed, onClose }: Props) {
  const { signIn, enabled, user, accessError, clearAccessError } = useAuth();
  const [busy, setBusy] = useState<AuthProviderId | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setBusy(null);
    setError(null);
    clearAccessError();
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose, clearAccessError]);

  // Sign-in was refused by the server (e.g. not invited yet): stop the spinner and say why.
  useEffect(() => {
    if (accessError) {
      setBusy(null);
      onSignInFailed?.();
    }
  }, [accessError, onSignInFailed]);

  // Close once signed in.
  useEffect(() => {
    if (open && user) onClose();
  }, [open, user, onClose]);

  if (!open) return null;

  const go = async (provider: AuthProviderId) => {
    setBusy(provider);
    setError(null);
    clearAccessError();
    onBeforeSignIn?.();
    try {
      await signIn(provider);
    } catch (e) {
      onSignInFailed?.();
      if ((e as Error).name !== 'AbortError') setError((e as Error).message);
      setBusy(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-zinc-950/30 p-4 backdrop-blur-sm animate-[fade-in_160ms_ease]" onMouseDown={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-title"
        className="relative w-full max-w-[400px] rounded-3xl bg-white p-8 shadow-2xl ring-1 ring-zinc-950/5 animate-[pop-in_260ms_cubic-bezier(0.16,1,0.3,1)]"
        onMouseDown={e => e.stopPropagation()}
      >
        <button onClick={onClose} aria-label="Close" className="absolute right-4 top-4 rounded-lg p-1.5 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700">
          <X size={18} />
        </button>
        <LogoMark size={40} />
        <h2 id="auth-title" className="mt-5 text-2xl font-semibold tracking-tight text-zinc-950">Sign in to Wolf</h2>
        <p className="mt-1.5 text-[15px] text-zinc-500">{reason ?? 'Use your GitHub or Google account. New here? This creates your account.'}</p>

        <div className="mt-7 space-y-2.5">
          {!enabled ? (
            <p className="rounded-xl bg-amber-50 px-4 py-3 text-sm leading-relaxed text-amber-800 ring-1 ring-amber-200">
              Sign-in isn’t set up for this site yet. Add your Firebase web config to <code>web/.env</code> (see <code>.env.example</code>).
            </p>
          ) : (
            (Object.keys(PROVIDERS) as AuthProviderId[]).map(p => (
              <button
                key={p}
                onClick={() => go(p)}
                disabled={busy !== null}
                className={`flex w-full items-center justify-center gap-2.5 rounded-xl py-3 text-[15px] font-medium transition disabled:opacity-70 ${PROVIDERS[p].className}`}
              >
                {busy === p ? <Loader2 size={18} className="animate-spin" /> : PROVIDERS[p].icon}
                {PROVIDERS[p].label}
              </button>
            ))
          )}
          {(error || accessError) && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-200">{error || accessError}</p>}
        </div>
        <p className="mt-6 text-center text-xs leading-relaxed text-zinc-400">
          Wolf only reads your name, email and avatar.
        </p>
      </div>
    </div>
  );
}
