import { ArrowRight, Check, Loader2, X } from 'lucide-react';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { api } from '../lib/api';
import { LogoMark } from './Logo';

interface Props {
  open: boolean;
  /** Prefills "what would you build" (e.g. the prompt they typed). */
  idea?: string;
  onClose: () => void;
  /** Invited people can still sign in. */
  onSignIn: () => void;
}

export function WaitlistModal({ open, idea: initialIdea = '', onClose, onSignIn }: Props) {
  const [email, setEmail] = useState('');
  const [idea, setIdea] = useState(initialIdea);
  const [website, setWebsite] = useState(''); // honeypot
  const [state, setState] = useState<'idle' | 'sending' | 'done'>('idle');
  const [error, setError] = useState<string | null>(null);
  const emailRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    setIdea(initialIdea);
    setError(null);
    if (state !== 'done') setState('idle');
    const t = setTimeout(() => emailRef.current?.focus(), 50);
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => { clearTimeout(t); window.removeEventListener('keydown', onKey); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, initialIdea, onClose]);

  if (!open) return null;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setState('sending');
    setError(null);
    try {
      await api.joinWaitlist({ email, idea: idea.trim() || undefined, website: website || undefined });
      setState('done');
    } catch (err) {
      setError((err as Error).message);
      setState('idle');
    }
  };

  const input = 'w-full rounded-xl border border-zinc-200 bg-white px-3.5 py-2.5 text-[15px] outline-none transition placeholder:text-zinc-400 focus:border-violet-400 focus:ring-4 focus:ring-violet-500/10';

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-zinc-950/30 p-4 backdrop-blur-sm animate-[fade-in_160ms_ease]" onMouseDown={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="waitlist-title"
        className="relative w-full max-w-[420px] overflow-hidden rounded-3xl bg-white p-8 shadow-2xl ring-1 ring-zinc-950/5 animate-[pop-in_260ms_cubic-bezier(0.16,1,0.3,1)]"
        onMouseDown={e => e.stopPropagation()}
      >
        <div aria-hidden className="pointer-events-none absolute -right-16 -top-24 size-64 rounded-full bg-gradient-to-br from-indigo-400/25 via-fuchsia-400/20 to-orange-300/20 blur-3xl" />
        <button onClick={onClose} aria-label="Close" className="absolute right-4 top-4 rounded-lg p-1.5 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700">
          <X size={18} />
        </button>

        {state === 'done' ? (
          <div className="relative py-4 text-center animate-[fade-up_400ms_ease_both]">
            <div className="mx-auto grid size-14 place-items-center rounded-full bg-emerald-50 text-emerald-600 ring-8 ring-emerald-50/60">
              <Check size={26} strokeWidth={2.6} />
            </div>
            <h2 id="waitlist-title" className="mt-6 text-2xl font-semibold tracking-tight text-zinc-950">You’re on the list</h2>
            <p className="mx-auto mt-2 max-w-xs text-[15px] leading-relaxed text-zinc-500">
              We’ll email <span className="font-medium text-zinc-700">{email}</span> as soon as your spot opens up.
            </p>
            <button onClick={onClose} className="mt-7 rounded-full bg-zinc-950 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-zinc-800">
              Back to Wolf
            </button>
          </div>
        ) : (
          <div className="relative">
            <LogoMark size={40} />
            <span className="mt-5 inline-flex items-center gap-1.5 rounded-full bg-violet-50 px-2.5 py-1 text-xs font-medium text-violet-700 ring-1 ring-violet-200">
              <span className="size-1.5 animate-pulse rounded-full bg-violet-500" /> Early access
            </span>
            <h2 id="waitlist-title" className="mt-3 text-2xl font-semibold tracking-tight text-zinc-950">Join the Wolf waitlist</h2>
            <p className="mt-1.5 text-[15px] leading-relaxed text-zinc-500">
              We’re letting people in a few at a time. Leave your email and we’ll invite you soon.
            </p>

            <form onSubmit={submit} className="mt-6 space-y-3">
              <input ref={emailRef} className={input} type="email" placeholder="you@example.com" autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} required />
              <textarea
                className={`${input} resize-none`}
                rows={3}
                maxLength={2000}
                placeholder="What would you build? (optional)"
                value={idea}
                onChange={e => setIdea(e.target.value)}
              />
              {/* Honeypot: invisible to people, tempting to bots. */}
              <input tabIndex={-1} autoComplete="off" aria-hidden className="absolute -left-[9999px] h-0 w-0 opacity-0" value={website} onChange={e => setWebsite(e.target.value)} name="website" />
              {error && <p className="rounded-xl bg-red-50 px-3.5 py-2.5 text-sm text-red-700 ring-1 ring-red-200">{error}</p>}
              <button type="submit" disabled={state === 'sending'} className="flex w-full items-center justify-center gap-2 rounded-xl bg-zinc-950 py-3 text-[15px] font-medium text-white transition hover:bg-zinc-800 disabled:opacity-60">
                {state === 'sending' ? <Loader2 size={16} className="animate-spin" /> : <>Join the waitlist <ArrowRight size={16} /></>}
              </button>
            </form>

            <p className="mt-5 text-center text-sm text-zinc-500">
              Already invited?{' '}
              <button onClick={onSignIn} className="font-medium text-zinc-950 underline-offset-4 hover:underline">Sign in</button>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
