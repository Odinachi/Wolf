import type { Theme } from '@wolf/schema';
import type { CSSProperties } from 'react';

/** Mixes a hex color with white (amount > 0) or black (amount < 0). */
function mix(hex: string, amount: number): string {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex.length === 9 ? '#' + hex.slice(3) : hex);
  if (!m) return hex;
  const n = parseInt(m[1], 16);
  const target = amount > 0 ? 255 : 0;
  const a = Math.abs(amount);
  const ch = (shift: number) => Math.round(((n >> shift) & 255) * (1 - a) + target * a);
  return `rgb(${ch(16)} ${ch(8)} ${ch(0)})`;
}

export function cssColor(value: unknown): string | undefined {
  if (typeof value !== 'string') return undefined;
  if (/^#[0-9a-f]{8}$/i.test(value)) {
    // Flutter's #AARRGGBB -> CSS #RRGGBBAA
    return `#${value.slice(3)}${value.slice(1, 3)}`;
  }
  return /^#[0-9a-f]{6}$/i.test(value) ? value : undefined;
}

/** CSS variables approximating the Material 3 color scheme Flutter derives from the theme. */
export function themeVars(theme: Theme): CSSProperties {
  const dark = theme.brightness === 'dark';
  return {
    '--m-primary': theme.primary,
    '--m-on-primary': '#FFFFFF',
    '--m-primary-container': mix(theme.primary, dark ? -0.6 : 0.82),
    '--m-secondary-container': mix(theme.secondary, dark ? -0.6 : 0.8),
    '--m-background': theme.background,
    '--m-surface': theme.surface,
    '--m-surface-high': mix(theme.surface, dark ? 0.08 : -0.05),
    '--m-text': theme.text,
    '--m-muted': theme.mutedText,
    '--m-outline': dark ? 'rgb(255 255 255 / 0.22)' : 'rgb(0 0 0 / 0.22)',
    '--m-outline-variant': dark ? 'rgb(255 255 255 / 0.12)' : 'rgb(0 0 0 / 0.1)',
    '--m-radius': `${theme.radius}px`,
    fontFamily: `'${theme.fontFamily}', 'Roboto', system-ui, sans-serif`,
    color: theme.text,
  } as CSSProperties;
}

const loadedFonts = new Set<string>();

/** Loads a Google Font on demand so previews match the app's theme font. */
export function loadFont(family: string): void {
  if (!family || loadedFonts.has(family)) return;
  loadedFonts.add(family);
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = `https://fonts.googleapis.com/css2?family=${encodeURIComponent(family).replace(/%20/g, '+')}:wght@400;500;600;700;800&display=swap`;
  document.head.appendChild(link);
}
