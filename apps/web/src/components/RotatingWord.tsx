import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { prefersReducedMotion } from '../lib/motion';

/** Cycles through words with a vertical slide; the box eases to each word's width. */
export function RotatingWord({ words, interval = 2200, className = '' }: { words: string[]; interval?: number; className?: string }) {
  const [index, setIndex] = useState(0);
  const [widths, setWidths] = useState<number[]>([]);
  const measureRef = useRef<HTMLSpanElement>(null);

  useLayoutEffect(() => {
    const measure = () => {
      const spans = measureRef.current?.children;
      if (spans) setWidths(Array.from(spans, el => (el as HTMLElement).offsetWidth));
    };
    measure();
    // Re-measure once the web font has loaded and on resize (the heading size is responsive).
    document.fonts?.ready.then(measure);
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, [words]);

  useEffect(() => {
    if (prefersReducedMotion()) return;
    const t = setInterval(() => setIndex(i => (i + 1) % words.length), interval);
    return () => clearInterval(t);
  }, [words.length, interval]);

  return (
    <span
      className={`relative inline-grid overflow-hidden align-bottom transition-[width] duration-700 ease-[cubic-bezier(0.16,1,0.3,1)] ${className}`}
      style={{ width: widths[index] ? `${widths[index]}px` : undefined }}
    >
      <span ref={measureRef} aria-hidden className="pointer-events-none invisible absolute left-0 top-0 whitespace-nowrap">
        {words.map(w => <span key={w} className="inline-block">{w}</span>)}
      </span>
      <span className="sr-only">{words[index]}</span>
      {words.map((w, i) => (
        <span
          key={w}
          aria-hidden
          className="col-start-1 row-start-1 whitespace-nowrap text-center transition-all duration-700 ease-[cubic-bezier(0.16,1,0.3,1)]"
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
