/** The Wolf mark: a low-poly wolf head. Mirrors public/logo.svg. */
export function LogoMark({ size = 28, className }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" className={className} aria-hidden>
      <defs>
        <linearGradient id="wolf-mark-bg" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#4F46E5" />
          <stop offset="0.55" stopColor="#9333EA" />
          <stop offset="1" stopColor="#EC4899" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="16" fill="url(#wolf-mark-bg)" />
      <path d="M16 12 L26 22 L32 22 L32 55 L24 47 L13 43 L18 39 L9 34 L15 30 Z" fill="#FFFFFF" />
      <path d="M48 12 L38 22 L32 22 L32 55 L40 47 L51 43 L46 39 L55 34 L49 30 Z" fill="#FFFFFF" fillOpacity="0.82" />
      <path d="M18.5 17.5 L24 22.5 L19 25 Z" fill="#7C3AED" fillOpacity="0.35" />
      <path d="M45.5 17.5 L40 22.5 L45 25 Z" fill="#7C3AED" fillOpacity="0.35" />
      <path d="M20.5 31 L28.5 33 L27.5 36 Z" fill="#3B1C8C" />
      <path d="M43.5 31 L35.5 33 L36.5 36 Z" fill="#3B1C8C" />
      <path d="M28.5 45.5 L35.5 45.5 L32 50 Z" fill="#3B1C8C" />
    </svg>
  );
}

export function Logo({ size = 28 }: { size?: number }) {
  return (
    <span className="flex items-center gap-2">
      <LogoMark size={size} />
      <span className="text-[19px] font-semibold tracking-tight text-zinc-950">Wolf</span>
    </span>
  );
}
