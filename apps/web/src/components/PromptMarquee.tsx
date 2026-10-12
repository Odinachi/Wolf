import { Sparkles } from 'lucide-react';

/** Two rows of prompt ideas drifting in opposite directions. Clicking one fills the prompt box. */
export function PromptMarquee({ rows, onPick }: { rows: string[][]; onPick: (prompt: string) => void }) {
  return (
    <div className="marquee-mask relative space-y-2.5 overflow-hidden py-2 sm:space-y-3">
      {rows.map((items, r) => (
        <div key={r} className="marquee-row flex w-max gap-3" style={{ animationDirection: r % 2 ? 'reverse' : 'normal', animationDuration: `${48 + r * 10}s` }}>
          {/* Two copies so the loop is seamless. */}
          {[...items, ...items].map((item, i) => (
            <button
              key={i}
              onClick={() => onPick(item)}
              tabIndex={i >= items.length ? -1 : 0}
              aria-hidden={i >= items.length}
              className="group flex shrink-0 items-center gap-2 rounded-full bg-white px-3.5 py-1.5 text-[13px] text-zinc-600 sm:px-4 sm:py-2 sm:text-sm shadow-sm ring-1 ring-zinc-950/[0.06] transition hover:-translate-y-0.5 hover:text-zinc-950 hover:shadow-md hover:ring-violet-300"
            >
              <Sparkles size={13} className="text-zinc-300 transition group-hover:rotate-12 group-hover:text-violet-500" />
              {item}
            </button>
          ))}
        </div>
      ))}
    </div>
  );
}
