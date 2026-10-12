import { COMPONENTS, type Node } from '@wolf/schema';
import { Check } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import type { Example } from '../examples';
import { prefersReducedMotion } from '../lib/motion';
import { useMediaQuery } from '../lib/useMediaQuery';
import { PhoneThumbnail } from '../renderer/PhoneFrame';
import { LogoMark } from './Logo';

type Phase = 'typing' | 'thinking' | 'building' | 'done';

function describe(node: Node): string {
  const label = COMPONENTS[node.type]?.label ?? node.type;
  const text = (node.props.title ?? node.props.text ?? node.props.label) as string | undefined;
  if (node.children.length && !text) return `Added a ${label.toLowerCase()} with ${node.children.length} items`;
  return `Added ${label.toLowerCase()}${text ? ` “${String(text).slice(0, 26)}”` : ''}`;
}

/**
 * A looping demo of Wolf at work: a prompt types itself, then the phone assembles component by
 * component while the change list fills in, then on to the next example.
 */
export function BuildDemo({ examples }: { examples: Example[] }) {
  const reduced = useMemo(prefersReducedMotion, []);
  const compact = useMediaQuery('(max-width: 639px)');
  const [index, setIndex] = useState(0);
  const [phase, setPhase] = useState<Phase>(reduced ? 'done' : 'typing');
  const [typed, setTyped] = useState(0);
  const [built, setBuilt] = useState(reduced ? Infinity : 0);
  // Only runs while on screen, so visitors always see it from the start.
  const [visible, setVisible] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const example = examples[index];
  const children = example.screen.root.children;

  useEffect(() => {
    const el = rootRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(([entry]) => setVisible(entry.isIntersecting), { threshold: 0.35 });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (reduced || !visible) return;
    let t: ReturnType<typeof setTimeout>;
    if (phase === 'typing') {
      if (typed < example.prompt.length) t = setTimeout(() => setTyped(n => n + 1), 32 + Math.random() * 38);
      else t = setTimeout(() => setPhase('thinking'), 400);
    } else if (phase === 'thinking') {
      t = setTimeout(() => setPhase('building'), 900);
    } else if (phase === 'building') {
      if (built < children.length) t = setTimeout(() => setBuilt(n => n + 1), 520);
      else t = setTimeout(() => setPhase('done'), 300);
    } else {
      t = setTimeout(() => {
        setIndex(i => (i + 1) % examples.length);
        setTyped(0);
        setBuilt(0);
        setPhase('typing');
      }, 3200);
    }
    return () => clearTimeout(t);
  }, [phase, typed, built, children.length, example.prompt.length, examples.length, reduced, visible]);

  const partial = { ...example.screen, root: { ...example.screen.root, children: children.slice(0, built) } };
  const changes = children.slice(0, built).map(describe);
  const prompt = reduced ? example.prompt : example.prompt.slice(0, typed);

  return (
    <div ref={rootRef} className="grid items-center gap-6 sm:gap-10 lg:grid-cols-[1fr_auto] lg:gap-16">
      {/* Chat */}
      <div className="relative mx-auto w-full max-w-md rounded-3xl bg-white p-4 shadow-[0_30px_80px_-30px_rgb(76_29_149/0.35)] ring-1 ring-zinc-950/5 sm:rounded-[28px] sm:p-5">
        <div className="mb-4 flex items-center gap-2 border-b border-zinc-100 pb-3">
          <span className="size-2.5 rounded-full bg-red-400/80" />
          <span className="size-2.5 rounded-full bg-amber-400/80" />
          <span className="size-2.5 rounded-full bg-emerald-400/80" />
          <span className="ml-2 text-xs font-medium text-zinc-400">wolf.dev / new app</span>
        </div>
        <div className="flex justify-end">
          <div className="min-h-[44px] max-w-[85%] rounded-2xl rounded-br-md bg-zinc-100 px-4 py-2.5 text-[15px] text-zinc-900">
            {prompt}
            {phase === 'typing' && <span className="ml-0.5 inline-block h-4 w-[2px] translate-y-0.5 animate-[blink_1s_steps(1)_infinite] bg-violet-500" />}
          </div>
        </div>
        <div className="mt-4 flex min-h-[150px] gap-3 sm:min-h-[230px]">
          {phase !== 'typing' && (
            <>
              <LogoMark size={26} className={`shrink-0 ${phase === 'done' ? '' : 'animate-[breathe_1.6s_ease-in-out_infinite]'}`} />
              <div className="min-w-0 flex-1">
                {phase === 'thinking' ? (
                  <p className="text-shimmer-muted text-[15px] font-medium">Planning screens, theme and data…</p>
                ) : (
                  <div className="rounded-xl bg-zinc-50 p-3 ring-1 ring-zinc-950/5">
                    <div className="mb-1.5 text-xs font-medium text-zinc-500">
                      {phase === 'done' ? `Made ${changes.length} changes` : `Building · ${changes.length} of ${children.length}`}
                    </div>
                    <ul className="space-y-1">
                      {changes.slice(compact ? -3 : -6).map((c, i) => (
                        <li key={`${index}-${changes.length - Math.min(compact ? 3 : 6, changes.length) + i}`} className="flex items-start gap-2 text-[13px] text-zinc-600 animate-[fade-up_300ms_ease_both]">
                          <Check size={13} strokeWidth={3} className="mt-0.5 shrink-0 text-emerald-500" />
                          <span className="truncate">{c}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {phase === 'done' && (
                  <p className="mt-3 text-[15px] text-zinc-700 animate-[fade-up_400ms_ease_both]">
                    Your {example.name} home screen is ready. Want me to add the next screen?
                  </p>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Phone */}
      <div className="relative mx-auto">
        <div aria-hidden className="absolute -inset-10 -z-10 rounded-full opacity-60 blur-3xl transition-colors duration-1000" style={{ background: `radial-gradient(closest-side, ${example.theme.primary}55, transparent)` }} />
        <div key={example.name} className="build-demo animate-[frame-in_700ms_cubic-bezier(0.16,1,0.3,1)]">
          <PhoneThumbnail screen={partial} theme={example.theme} navigation={built >= children.length ? example.navigation : undefined} width={compact ? 250 : 300} />
        </div>
        {phase === 'building' && (
          <div className="absolute -right-2 top-12 rounded-full sm:-right-4 sm:top-16 bg-zinc-950 px-3 py-1.5 text-xs font-medium text-white shadow-lg animate-[pop-in_300ms_ease]">
            Generating…
          </div>
        )}
      </div>
    </div>
  );
}
