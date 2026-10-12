import type { HTMLAttributes, MouseEvent } from 'react';

/** A card with a soft light that follows the cursor. */
export function Spotlight({ className = '', children, ...rest }: HTMLAttributes<HTMLDivElement>) {
  const onMove = (e: MouseEvent<HTMLDivElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    e.currentTarget.style.setProperty('--sx', `${e.clientX - r.left}px`);
    e.currentTarget.style.setProperty('--sy', `${e.clientY - r.top}px`);
  };
  return (
    <div onMouseMove={onMove} className={`spotlight ${className}`} {...rest}>
      {children}
    </div>
  );
}
