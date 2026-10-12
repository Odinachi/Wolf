import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { prefersReducedMotion } from '../lib/motion';

/** Cycles through words with a vertical slide; the box eases to each word's width. */
export function RotatingWord({ words, interval = 2200, className = '' }: { words: string[]; interval?: number; className?: string }) {
  const [index, setIndex] = useState(0);
  const [widths, setWidths] = useState<number[]>([]);
  const measureRef = useRef<HTMLSpanElement>(null);

  useLayoutEffect(() => {
    const el = measureRef.current;
    if (!el) return;
    const measure = () => setWidths(Array.from(el.children, c => (c as HTMLElement).getBoundingClientRect().width));
    measure();
    // The words change size when the web font loads and when the heading's responsive size changes.
    const observer = new ResizeObserver(measure);
    Array.from(el.children).forEach(c => observer.observe(c));
    return () => observer.disconnect();
  }, [words]);

  useEffect(() => {
    if (prefersReducedMotion()) return;
    const t = setInterval(() => setIndex(i => (i + 1) % words.length), interval);
    return () => clearInterval(t);
  }, [words.length, interval]);

  return (
    <span
      className={`relative inline-grid align-bottom transition-[width] duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] ${className}`}
      style={{
        // Grow instantly to fit a longer word (so it's never cropped), ease when shrinking.
        width: widths[index] ? `${Math.ceil(widths[index]) + 4}px` : undefined,
        transitionDuration: (widths[index] ?? 0) >= (widths[(index - 1 + words.length) % words.length] ?? 0) ? '0ms' : undefined,
        // Room for descenders (g, p, y) under the tight headline line height, clipped vertically only.
        paddingBottom: '0.14em',
        marginBottom: '-0.14em',
        clipPath: 'inset(0 -50vw)',
        // One column exactly as wide as the box, so each word centers in it (instead of in a
        // column sized to the widest word).
        gridTemplateColumns: '100%',
      }}
    >
      <span ref={measureRef} aria-hidden className="pointer-events-none invisible absolute left-0 top-0 whitespace-nowrap">
        {words.map(w => <span key={w} className="inline-block">{w}</span>)}
      </span>
      <span className="sr-only">{words[index]}</span>
      {words.map((w, i) => (
        <span
          key={w}
          aria-hidden
          className="col-start-1 row-start-1 justify-self-center whitespace-nowrap transition-all duration-700 ease-[cubic-bezier(0.16,1,0.3,1)]"
          style={{
            transform: `translateY(${i === index ? 0 : i === (index - 1 + words.length) % words.length ? -110 : 110}%)`,
            opacity: i === index ? 1 : 0,
            filter: i === index ? 'none' : 'blur(6px)',
          }}
        >
          {w}
        </span>
      ))}
    </span>
  );
}
