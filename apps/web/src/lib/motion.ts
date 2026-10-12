import { useEffect, useRef, useState } from 'react';

export function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/** Adds `data-revealed` to the element the first time it scrolls into view (see .reveal in styles.css). */
export function useReveal<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (prefersReducedMotion()) { el.dataset.revealed = ''; return; }
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        el.dataset.revealed = '';
        observer.disconnect();
      }
    }, { rootMargin: '0px 0px -12% 0px' });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  return ref;
}

/** The pointer position relative to the window center, from -1 to 1, eased. */
export function usePointerParallax(): { x: number; y: number } {
  const [pos, setPos] = useState({ x: 0, y: 0 });
  useEffect(() => {
    if (prefersReducedMotion()) return;
    let frame = 0;
    let target = { x: 0, y: 0 };
    let current = { x: 0, y: 0 };
    const onMove = (e: PointerEvent) => {
      target = { x: (e.clientX / window.innerWidth) * 2 - 1, y: (e.clientY / window.innerHeight) * 2 - 1 };
    };
    const tick = () => {
      current = { x: current.x + (target.x - current.x) * 0.06, y: current.y + (target.y - current.y) * 0.06 };
      setPos(p => (Math.abs(p.x - current.x) + Math.abs(p.y - current.y) > 0.001 ? current : p));
      frame = requestAnimationFrame(tick);
    };
    window.addEventListener('pointermove', onMove);
    frame = requestAnimationFrame(tick);
    return () => { window.removeEventListener('pointermove', onMove); cancelAnimationFrame(frame); };
  }, []);
  return pos;
}
