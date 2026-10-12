import { useEffect, useRef } from 'react';

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
