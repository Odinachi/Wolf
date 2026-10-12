import { useEffect, useRef } from 'react';

const COLORS = ['#6366F1', '#A855F7', '#EC4899', '#FB923C'];

/**
 * The animated hero backdrop: soft gradient ribbons (blurred) with fine silk strands flowing over
 * them. Leans toward the cursor, pauses off-screen, and holds still for reduced-motion users.
 */
export function WaveBackground() {
  const glowRef = useRef<HTMLCanvasElement>(null);
  const silkRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const glow = glowRef.current!;
    const silk = silkRef.current!;
    const g = glow.getContext('2d')!;
    const s = silk.getContext('2d')!;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let width = 0;
    let height = 0;
    let frame = 0;
    let visible = true;
    let pointer = 0.5; // normalized x of the cursor, eased
    let pointerTarget = 0.5;
    const start = performance.now();

    function resize() {
      const rect = silk.getBoundingClientRect();
      width = rect.width;
      height = rect.height;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      silk.width = width * dpr;
      silk.height = height * dpr;
      s.setTransform(dpr, 0, 0, dpr, 0, 0);
      // The glow is blurred anyway, so render it at low resolution.
      glow.width = width / 4;
      glow.height = height / 4;
      g.setTransform(0.25, 0, 0, 0.25, 0, 0);
    }

    function gradient(ctx: CanvasRenderingContext2D, alpha: number, shift: number) {
      const grad = ctx.createLinearGradient(0, 0, width, 0);
      COLORS.forEach((c, i) => {
        const stop = Math.min(1, Math.max(0, i / (COLORS.length - 1) + shift));
        grad.addColorStop(stop, c + Math.round(alpha * 255).toString(16).padStart(2, '0'));
      });
      return grad;
    }

    function wave(x: number, t: number, base: number, amp: number, phase: number) {
      const lean = (pointer - 0.5) * 0.8;
      return (
        height * base +
        amp * Math.sin(x * 0.0026 + t * 0.35 + phase + lean) +
        amp * 0.45 * Math.sin(x * 0.0061 - t * 0.5 + phase * 1.7) +
        amp * 0.2 * Math.sin(x * 0.013 + t * 0.8 + phase * 0.6)
      );
    }

    function draw(now: number) {
      const t = reduced ? 8 : (now - start) / 1000;
      pointer += (pointerTarget - pointer) * 0.04;

      g.clearRect(0, 0, width, height);
      const ribbons = [
        { base: 0.74, amp: 46, phase: 0, alpha: 0.55, shift: 0 },
        { base: 0.82, amp: 60, phase: 2.1, alpha: 0.5, shift: -0.15 },
        { base: 0.9, amp: 38, phase: 4.2, alpha: 0.6, shift: 0.12 },
      ];
      for (const r of ribbons) {
        g.beginPath();
        g.moveTo(0, height);
        for (let x = 0; x <= width; x += 12) g.lineTo(x, wave(x, t, r.base, r.amp, r.phase));
        g.lineTo(width, height);
        g.closePath();
        g.fillStyle = gradient(g, r.alpha, r.shift + Math.sin(t * 0.2) * 0.08);
        g.fill();
      }

      s.clearRect(0, 0, width, height);
      const strands = 28;
      for (let j = 0; j < strands; j++) {
        const k = j / (strands - 1);
        s.beginPath();
        for (let x = -10; x <= width + 10; x += 8) {
          const spread = (k - 0.5) * (70 + 40 * Math.sin(x * 0.002 + t * 0.3));
          const y = wave(x, t, 0.72, 34, k * 1.4) + spread;
          if (x === -10) s.moveTo(x, y);
          else s.lineTo(x, y);
        }
        s.strokeStyle = gradient(s, 0.12 + 0.35 * Math.sin(Math.PI * k), Math.sin(t * 0.25 + k) * 0.1);
        s.lineWidth = 1;
        s.stroke();
      }

      if (!reduced && visible) frame = requestAnimationFrame(draw);
    }

    resize();
    frame = requestAnimationFrame(draw);

    const onResize = () => { resize(); if (reduced) draw(performance.now()); };
    const onMove = (e: PointerEvent) => { pointerTarget = e.clientX / window.innerWidth; };
    const observer = new IntersectionObserver(([entry]) => {
      const wasVisible = visible;
      visible = entry.isIntersecting;
      if (visible && !wasVisible && !reduced) frame = requestAnimationFrame(draw);
    });
    observer.observe(silk);
    window.addEventListener('resize', onResize);
    window.addEventListener('pointermove', onMove);
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      window.removeEventListener('resize', onResize);
      window.removeEventListener('pointermove', onMove);
    };
  }, []);

  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
      <div className="hero-aurora absolute inset-0" />
      <canvas ref={glowRef} className="absolute inset-0 h-full w-full" style={{ filter: 'blur(48px) saturate(1.3)', opacity: 0.9 }} />
      <canvas ref={silkRef} className="absolute inset-0 h-full w-full" />
      {/* Fade the top into the page so the wave rises from below. */}
      <div className="absolute inset-x-0 top-0 h-1/2 bg-gradient-to-b from-[#FCFCFD] to-transparent" />
      {/* ...and settle into the page below instead of ending in a hard edge. */}
      <div className="absolute inset-x-0 bottom-0 h-28 bg-gradient-to-t from-[#FCFCFD] to-transparent" />
    </div>
  );
}
