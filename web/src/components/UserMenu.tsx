import { LogOut } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../lib/auth';

export function UserMenu() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const close = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, []);
  if (!user) return null;
  return (
    <div ref={ref} className="relative">
      <button onClick={() => setOpen(!open)} aria-label="Account" className="grid size-9 place-items-center rounded-full bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 text-sm font-semibold text-white ring-2 ring-white transition hover:scale-105">
        {user.name.charAt(0).toUpperCase()}
      </button>
      {open && (
        <div className="absolute right-0 top-11 z-40 w-56 rounded-2xl bg-white p-1.5 shadow-xl ring-1 ring-zinc-950/5 animate-[pop-in_160ms_ease]">
          <div className="px-3 py-2">
            <div className="truncate text-sm font-medium text-zinc-900">{user.name}</div>
            <div className="truncate text-xs text-zinc-500">{user.email}</div>
          </div>
          <div className="my-1 h-px bg-zinc-100" />
          <button onClick={() => { setOpen(false); logout(); }} className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-100">
            <LogOut size={15} /> Sign out
          </button>
        </div>
      )}
    </div>
  );
}
