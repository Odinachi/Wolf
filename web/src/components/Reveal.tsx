import type { CSSProperties, ReactNode } from 'react';
import { useReveal } from '../lib/motion';

/** Fades its direct children up as they scroll into view, staggered by `stagger` ms. */
export function Reveal({ children, className = '', stagger = 90 }: { children: ReactNode; className?: string; stagger?: number }) {
  const ref = useReveal<HTMLDivElement>();
  const items = Array.isArray(children) ? children : [children];
  return (
    <div ref={ref} className={`reveal ${className}`}>
      {items.map((child, i) => (
        <div key={i} style={{ '--d': `${i * stagger}ms` } as CSSProperties} className="contents-reveal">{child}</div>
      ))}
    </div>
  );
}
