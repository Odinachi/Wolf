import { FRAME_HEIGHT, FRAME_WIDTH, type AppSchema } from '@wolf/schema';
import { Maximize, Minus, Plus } from 'lucide-react';
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react';
import { PhoneFrame } from '../renderer/PhoneFrame';

interface Props {
  schema: AppSchema;
  generating: boolean;
  selection: { screenId: string | null; nodeId: string | null };
  onSelect: (sel: { screenId: string | null; nodeId: string | null }) => void;
}

const BEZEL = 20; // PhoneFrame padding on both sides
const LABEL = 34;
const MIN_ZOOM = 0.15;
const MAX_ZOOM = 2;

/** An infinite canvas of phone frames: drag to pan, pinch or ⌘/Ctrl + scroll to zoom. */
export function Canvas({ schema, generating, selection, onSelect }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [view, setView] = useState({ x: 0, y: 0, scale: 0.6 });
  const [hovered, setHovered] = useState<string | null>(null);
  const drag = useRef<{ x: number; y: number; vx: number; vy: number; moved: boolean } | null>(null);

  const fit = useCallback(() => {
    const el = ref.current;
    if (!el || schema.screens.length === 0) return;
    const { width, height } = el.getBoundingClientRect();
    if (!width || !height) return; // hidden
    const xs = schema.screens.map(s => s.frame.x);
    const ys = schema.screens.map(s => s.frame.y);
    const minX = Math.min(...xs);
    const minY = Math.min(...ys) - LABEL;
    const maxX = Math.max(...xs) + FRAME_WIDTH + BEZEL;
    const maxY = Math.max(...ys) + FRAME_HEIGHT + BEZEL;
    const pad = 64;
    const scale = Math.min(MAX_ZOOM, 0.85, (width - pad * 2) / (maxX - minX), (height - pad * 2) / (maxY - minY));
    setView({
      scale,
      x: (width - (maxX - minX) * scale) / 2 - minX * scale,
      y: (height - (maxY - minY) * scale) / 2 - minY * scale,
    });
  }, [schema.screens]);

  // Re-fit when screens are added or removed (e.g. while the AI builds).
  const count = schema.screens.length;
  useLayoutEffect(() => { fit(); }, [count]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const el = ref.current!;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = el.getBoundingClientRect();
      if (e.ctrlKey || e.metaKey) {
        const px = e.clientX - rect.left;
        const py = e.clientY - rect.top;
        setView(v => {
          const scale = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, v.scale * Math.exp(-e.deltaY * 0.01)));
          const k = scale / v.scale;
          return { scale, x: px - (px - v.x) * k, y: py - (py - v.y) * k };
        });
      } else {
        setView(v => ({ ...v, x: v.x - e.deltaX, y: v.y - e.deltaY }));
      }
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    const observer = new ResizeObserver(() => fit());
    observer.observe(el);
    return () => { el.removeEventListener('wheel', onWheel); observer.disconnect(); };
  }, [fit]);

  const zoomBy = (factor: number) => {
    const rect = ref.current!.getBoundingClientRect();
    const px = rect.width / 2;
    const py = rect.height / 2;
    setView(v => {
      const scale = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, v.scale * factor));
      const k = scale / v.scale;
      return { scale, x: px - (px - v.x) * k, y: py - (py - v.y) * k };
    });
  };

  const onPointerDown = (e: ReactPointerEvent) => {
    // Pan from empty canvas, or anywhere with the middle mouse button.
    const onFrame = (e.target as HTMLElement).closest('[data-frame]');
    if (onFrame && e.button !== 1) return;
    drag.current = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y, moved: false };
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  };
  const onPointerMove = (e: ReactPointerEvent) => {
    const d = drag.current;
    if (!d) return;
    const dx = e.clientX - d.x;
    const dy = e.clientY - d.y;
    if (Math.abs(dx) + Math.abs(dy) > 3) d.moved = true;
    setView(v => ({ ...v, x: d.vx + dx, y: d.vy + dy }));
  };
  const onPointerUp = () => {
    if (drag.current && !drag.current.moved) onSelect({ screenId: null, nodeId: null });
    drag.current = null;
  };

  return (
    <div
      ref={ref}
      className="canvas-grid relative h-full w-full touch-none overflow-hidden select-none"
      style={{ cursor: drag.current?.moved ? 'grabbing' : 'grab', backgroundPosition: `${view.x}px ${view.y}px`, backgroundSize: `${24 * view.scale}px ${24 * view.scale}px` }}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
    >
      <div className="absolute left-0 top-0 origin-top-left" style={{ transform: `translate(${view.x}px, ${view.y}px) scale(${view.scale})` }}>
        {schema.screens.map(screen => {
          const isSelected = selection.screenId === screen.id;
          const empty = screen.root.children.length === 0;
          return (
            <div key={screen.id} data-frame className="absolute animate-[frame-in_500ms_cubic-bezier(0.16,1,0.3,1)]" style={{ left: screen.frame.x, top: screen.frame.y }}>
              <button
                onClick={() => onSelect({ screenId: screen.id, nodeId: screen.root.id })}
                className={`absolute -top-[34px] left-2 flex items-center gap-1.5 whitespace-nowrap rounded-md px-1.5 py-0.5 text-[15px] font-medium transition ${isSelected ? 'text-violet-700' : 'text-zinc-500 hover:text-zinc-900'}`}
                style={{ transform: `scale(${Math.min(2.2, 1 / view.scale)})`, transformOrigin: 'bottom left' }}
              >
                {screen.name}
              </button>
              <div className={`relative rounded-[54px] transition-shadow ${isSelected ? 'ring-4 ring-violet-500/40' : ''}`}>
                <PhoneFrame
                  screen={screen}
                  theme={schema.theme}
                  navigation={schema.navigation}
                  ctx={{
                    selectedId: selection.screenId === screen.id ? selection.nodeId : null,
                    hoveredId: hovered,
                    onHover: setHovered,
                    onSelect: id => onSelect({ screenId: screen.id, nodeId: id }),
                  }}
                />
                {empty && generating ? <BuildingOverlay /> : null}
              </div>
            </div>
          );
        })}
      </div>

      <div className="absolute bottom-4 right-4 flex items-center gap-0.5 rounded-xl bg-white/90 p-1 text-zinc-600 shadow-lg shadow-zinc-950/5 ring-1 ring-zinc-950/5 backdrop-blur" onPointerDown={e => e.stopPropagation()}>
        <button onClick={() => zoomBy(1 / 1.25)} className="grid size-8 place-items-center rounded-lg hover:bg-zinc-100" aria-label="Zoom out"><Minus size={15} /></button>
        <span className="w-12 text-center text-xs font-medium tabular-nums">{Math.round(view.scale * 100)}%</span>
        <button onClick={() => zoomBy(1.25)} className="grid size-8 place-items-center rounded-lg hover:bg-zinc-100" aria-label="Zoom in"><Plus size={15} /></button>
        <div className="mx-0.5 h-5 w-px bg-zinc-200" />
        <button onClick={fit} className="grid size-8 place-items-center rounded-lg hover:bg-zinc-100" aria-label="Fit all screens"><Maximize size={14} /></button>
      </div>
    </div>
  );
}

/** Shimmering placeholder drawn over an empty screen while the AI is building. */
function BuildingOverlay() {
  return (
    <div className="pointer-events-none absolute inset-[10px] overflow-hidden rounded-[44px] bg-white/70 px-6 pt-24 backdrop-blur-[2px]">
      <div className="space-y-4">
        {[60, 90, 160, 40, 110, 110].map((h, i) => (
          <div key={i} className="skeleton rounded-2xl" style={{ height: h, width: i === 0 ? '55%' : i === 3 ? '35%' : '100%', animationDelay: `${i * 120}ms` }} />
        ))}
      </div>
    </div>
  );
}
