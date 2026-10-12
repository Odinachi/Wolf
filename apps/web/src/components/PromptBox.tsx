import { ArrowUp, Loader2, Sparkles } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

interface Props {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  busy?: boolean;
  /** Example prompts cycled through as a typing placeholder while the box is empty. */
  ideas: string[];
}

function useTypingPlaceholder(ideas: string[], active: boolean) {
  const [text, setText] = useState('');
  useEffect(() => {
    if (!active || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setText(ideas[0] ?? '');
      return;
    }
    let idea = 0;
    let chars = 0;
    let deleting = false;
    let timer: ReturnType<typeof setTimeout>;
    const tick = () => {
      const full = ideas[idea];
      chars += deleting ? -1 : 1;
      setText(full.slice(0, chars));
      let delay = deleting ? 18 : 38 + Math.random() * 40;
      if (!deleting && chars === full.length) { deleting = true; delay = 1800; }
      else if (deleting && chars === 0) { deleting = false; idea = (idea + 1) % ideas.length; delay = 300; }
      timer = setTimeout(tick, delay);
    };
    timer = setTimeout(tick, 400);
    return () => clearTimeout(timer);
  }, [ideas, active]);
  return text;
}

/** The big hero prompt box. */
export function PromptBox({ value, onChange, onSubmit, busy, ideas }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const placeholder = useTypingPlaceholder(ideas, value.length === 0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 220)}px`;
  }, [value]);

  return (
    <div className="prompt-glow">
    <form
      onSubmit={e => { e.preventDefault(); if (value.trim() && !busy) onSubmit(); }}
      className="group relative w-full rounded-[28px] bg-white/95 p-2 shadow-[0_1px_2px_rgb(24_24_27/0.04),0_24px_60px_-20px_rgb(76_29_149/0.35)] backdrop-blur-xl"
    >
      <textarea
        ref={ref}
        rows={2}
        value={value}
        onChange={e => onChange(e.target.value)}
        onKeyDown={e => {
          if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); if (value.trim() && !busy) onSubmit(); }
        }}
        placeholder={`Ask Wolf to build ${placeholder ? placeholder.charAt(0).toLowerCase() + placeholder.slice(1) : ''}`}
        aria-label="Describe the app you want to build"
        className="block min-h-[64px] w-full resize-none bg-transparent px-4 pt-3 text-[17px] leading-relaxed text-zinc-900 outline-none placeholder:text-zinc-400"
      />
      <div className="flex items-center justify-between px-2 pb-1">
        <span className="flex items-center gap-1.5 rounded-full bg-zinc-100/80 px-2.5 py-1 text-xs font-medium text-zinc-500">
          <Sparkles size={12} className="text-violet-500" /> Flutter · iOS & Android
        </span>
        <button
          type="submit"
          disabled={!value.trim() || busy}
          aria-label="Build it"
          className="grid size-10 place-items-center rounded-full bg-zinc-950 text-white transition hover:bg-zinc-800 active:scale-95 disabled:bg-zinc-200 disabled:text-zinc-400"
        >
          {busy ? <Loader2 size={18} className="animate-spin" /> : <ArrowUp size={19} strokeWidth={2.4} />}
        </button>
      </div>
    </form>
    </div>
  );
}
