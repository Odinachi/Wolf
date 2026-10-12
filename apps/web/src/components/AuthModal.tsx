import { Loader2, X } from 'lucide-react';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useAuth } from '../lib/auth';
import { LogoMark } from './Logo';

interface Props {
  open: boolean;
  initialMode?: 'signup' | 'login';
  /** Shown when the user was asked to sign in to run their prompt. */
  reason?: string;
  onClose: () => void;
  onSuccess: () => void;
}

export function AuthModal({ open, initialMode = 'signup', reason, onClose, onSuccess }: Props) {
  const { signup, login } = useAuth();
  const [mode, setMode] = useState(initialMode);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const firstField = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    setMode(initialMode);
    setError(null);
    const t = setTimeout(() => firstField.current?.focus(), 50);
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => { clearTimeout(t); window.removeEventListener('keydown', onKey); };
  }, [open, initialMode, onClose]);

  if (!open) return null;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === 'signup') await signup({ name, email, password });
      else await login({ email, password });
      onSuccess();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const input = 'w-full rounded-xl border border-zinc-200 bg-white px-3.5 py-2.5 text-[15px] outline-none transition placeholder:text-zinc-400 focus:border-violet-400 focus:ring-4 focus:ring-violet-500/10';

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
        <h2 id="auth-title" className="mt-5 text-2xl font-semibold tracking-tight text-zinc-950">
          {mode === 'signup' ? 'Create your account' : 'Welcome back'}
        </h2>
        <p className="mt-1.5 text-[15px] text-zinc-500">
          {reason ?? (mode === 'signup' ? 'Start building apps with Wolf.' : 'Sign in to keep building.')}
        </p>

        <form onSubmit={submit} className="mt-6 space-y-3">
          {mode === 'signup' && (
            <input ref={firstField} className={input} placeholder="Your name" autoComplete="name" value={name} onChange={e => setName(e.target.value)} required />
          )}
          <input ref={mode === 'login' ? firstField : undefined} className={input} type="email" placeholder="Email" autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} required />
          <input className={input} type="password" placeholder={mode === 'signup' ? 'Password (8+ characters)' : 'Password'} autoComplete={mode === 'signup' ? 'new-password' : 'current-password'} minLength={mode === 'signup' ? 8 : undefined} value={password} onChange={e => setPassword(e.target.value)} required />
          {error && <p className="rounded-xl bg-red-50 px-3.5 py-2.5 text-sm text-red-700 ring-1 ring-red-200">{error}</p>}
          <button type="submit" disabled={busy} className="flex w-full items-center justify-center gap-2 rounded-xl bg-zinc-950 py-3 text-[15px] font-medium text-white transition hover:bg-zinc-800 disabled:opacity-60">
            {busy && <Loader2 size={16} className="animate-spin" />}
            {mode === 'signup' ? 'Create account' : 'Sign in'}
          </button>
        </form>

        <p className="mt-5 text-center text-sm text-zinc-500">
          {mode === 'signup' ? 'Already have an account?' : 'New to Wolf?'}{' '}
          <button className="font-medium text-zinc-950 underline-offset-4 hover:underline" onClick={() => { setMode(mode === 'signup' ? 'login' : 'signup'); setError(null); }}>
            {mode === 'signup' ? 'Sign in' : 'Create an account'}
          </button>
        </p>
      </div>
    </div>
  );
}
