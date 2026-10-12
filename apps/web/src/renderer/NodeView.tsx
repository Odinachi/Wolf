import type { CrossAxisAlignment, MainAxisAlignment, Node, NodeStyle } from '@wolf/schema';
import type { CSSProperties, MouseEvent, ReactNode } from 'react';
import { cssColor } from './theme';

/**
 * Renders a component tree the way the Flutter compiler (packages/flutter-codegen) lays it out,
 * using Material 3 sizing. Keep the two in step when changing either.
 */

export interface RenderContext {
  selectedId?: string | null;
  hoveredId?: string | null;
  onSelect?: (id: string) => void;
  onHover?: (id: string | null) => void;
  /** Set when rendering a static thumbnail: no pointer interaction. */
  passive?: boolean;
}

const TEXT_VARIANTS: Record<string, CSSProperties> = {
  display: { fontSize: 36, lineHeight: '44px', fontWeight: 400, letterSpacing: 0 },
  headline: { fontSize: 24, lineHeight: '32px', fontWeight: 400 },
  title: { fontSize: 16, lineHeight: '24px', fontWeight: 500, letterSpacing: '0.15px' },
  body: { fontSize: 14, lineHeight: '20px', fontWeight: 400, letterSpacing: '0.25px' },
  label: { fontSize: 14, lineHeight: '20px', fontWeight: 500, letterSpacing: '0.1px' },
  caption: { fontSize: 12, lineHeight: '16px', fontWeight: 400, letterSpacing: '0.4px', color: 'var(--m-muted)' },
};

const MAIN: Record<MainAxisAlignment, CSSProperties['justifyContent']> = {
  start: 'flex-start', center: 'center', end: 'flex-end',
  spaceBetween: 'space-between', spaceAround: 'space-around', spaceEvenly: 'space-evenly',
};
const CROSS: Record<CrossAxisAlignment, CSSProperties['alignItems']> = {
  start: 'flex-start', center: 'center', end: 'flex-end', stretch: 'stretch',
};

function sides(v: NodeStyle['padding']): string | undefined {
  if (typeof v === 'number') return `${v}px`;
  if (Array.isArray(v) && v.length === 4) return v.map(n => `${n}px`).join(' ');
  return undefined;
}

export function Icon({ name, size = 24, color, style }: { name?: unknown; size?: number; color?: string; style?: CSSProperties }) {
  return (
    <span className="material-icons-round" aria-hidden style={{ fontSize: size, width: size, height: size, lineHeight: 1, color, flexShrink: 0, ...style }}>
      {typeof name === 'string' && name ? name : 'help_outline'}
    </span>
  );
}

function str(v: unknown, fallback = ''): string {
  return typeof v === 'string' ? v : v == null ? fallback : String(v);
}
function num(v: unknown, fallback: number): number {
  return typeof v === 'number' && Number.isFinite(v) ? v : fallback;
}

type Axis = 'vertical' | 'horizontal' | null;

export function NodeView({ node, ctx, axis = null }: { node: Node; ctx: RenderContext; axis?: Axis }) {
  const s = node.style ?? {};
  const p = node.props ?? {};
  const inRow = axis === 'horizontal';
  const children = (childAxis: Axis) => node.children.map(c => <NodeView key={c.id} node={c} ctx={ctx} axis={childAxis} />);

  // Box styles shared by every node (Flutter: Padding / SizedBox / outer Padding).
  const box: CSSProperties = {
    position: 'relative',
    padding: sides(s.padding),
    margin: sides(s.margin),
    height: s.height,
    width: s.width === 'fill' ? (inRow ? undefined : '100%') : s.width,
    flex: s.expand || (inRow && s.width === 'fill') ? '1 1 0' : undefined,
    // Like Flutter, children of a Column keep their size instead of shrinking to fit.
    flexShrink: axis === 'vertical' && !s.expand ? 0 : undefined,
    minWidth: inRow ? 0 : undefined,
    boxSizing: 'border-box',
  };
  const gap = s.gap ? `${s.gap}px` : undefined;
  const textStyle: CSSProperties = {
    color: cssColor(s.color),
    fontSize: s.fontSize,
    fontWeight: s.fontWeight,
    textAlign: s.textAlign,
  };

  let content: ReactNode;
  let own: CSSProperties = {};

  switch (node.type) {
    case 'Column':
    case 'Row': {
      const vertical = node.type === 'Column';
      own = {
        display: 'flex',
        flexDirection: vertical ? 'column' : 'row',
        gap,
        justifyContent: MAIN[s.mainAxisAlignment ?? 'start'],
        alignItems: CROSS[s.crossAxisAlignment ?? (vertical ? 'stretch' : 'center')],
      };
      content = children(vertical ? 'vertical' : 'horizontal');
      break;
    }
    case 'Stack':
      own = { display: 'grid' };
      content = node.children.map(c => (
        <div key={c.id} style={{ gridArea: '1 / 1' }}><NodeView node={c} ctx={ctx} /></div>
      ));
      break;
    case 'Container':
      own = {
        display: 'flex', flexDirection: 'column', gap, alignItems: 'stretch',
        background: cssColor(s.backgroundColor),
        borderRadius: s.borderRadius,
        border: s.borderColor || s.borderWidth ? `${s.borderWidth ?? 1}px solid ${cssColor(s.borderColor) ?? 'var(--m-outline-variant)'}` : undefined,
      };
      content = children('vertical');
      break;
    case 'Card':
      own = {
        display: 'flex', flexDirection: 'column', gap, alignItems: 'stretch', overflow: 'hidden',
        background: cssColor(s.backgroundColor) ?? 'var(--m-surface)',
        borderRadius: s.borderRadius ?? 12,
        boxShadow: s.elevation === 0 ? 'inset 0 0 0 1px var(--m-outline-variant)' : `0 ${Math.min(1 + (s.elevation ?? 1), 6)}px ${3 + 3 * (s.elevation ?? 1)}px rgb(0 0 0 / 0.12), 0 1px 2px rgb(0 0 0 / 0.08)`,
      };
      content = children('vertical');
      break;
    case 'ListView': {
      const horizontal = p.direction === 'horizontal';
      own = horizontal
        ? { display: 'flex', flexDirection: 'row', gap, overflowX: 'auto', height: s.height ?? 140, alignItems: 'stretch', scrollbarWidth: 'none' }
        : { display: 'flex', flexDirection: 'column', gap, alignItems: 'stretch' };
      content = horizontal
        ? node.children.map(c => <div key={c.id} style={{ flexShrink: 0, display: 'flex' }}><NodeView node={c} ctx={ctx} axis="horizontal" /></div>)
        : children('vertical');
      break;
    }
    case 'Grid': {
      const columns = Math.max(1, Math.round(num(p.columns, 2)));
      const ratio = num(p.aspectRatio, 0.8);
      own = { display: 'grid', gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`, gap };
      content = node.children.map(c => (
        <div key={c.id} style={{ aspectRatio: String(ratio), overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <NodeView node={c} ctx={ctx} />
        </div>
      ));
      break;
    }
    case 'Spacer':
      own = s.height ? { [inRow ? 'width' : 'height']: s.height, flexShrink: 0 } : { flex: '1 1 0' };
      if (inRow && s.height) own.height = undefined;
      break;
    case 'Divider':
      own = { height: 1, background: 'var(--m-outline-variant)', alignSelf: 'stretch' };
      break;
    case 'Text':
      own = { ...TEXT_VARIANTS[str(p.variant, 'body')] ?? TEXT_VARIANTS.body, ...stripUndefined(textStyle), whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' };
      content = str(p.text);
      break;
    case 'Image':
      own = { overflow: 'hidden', borderRadius: s.borderRadius, background: 'var(--m-surface-high)', height: s.height ?? 180, flexShrink: 0 };
      content = p.src ? (
        <img src={str(p.src)} alt="" draggable={false} style={{ width: '100%', height: '100%', objectFit: (str(p.fit, 'cover') as CSSProperties['objectFit']), display: 'block' }} />
      ) : null;
      break;
    case 'Icon':
      own = { display: 'inline-flex' };
      content = <Icon name={p.icon} size={num(p.size, 24)} color={cssColor(s.color) ?? 'var(--m-muted)'} />;
      break;
    case 'Avatar': {
      const size = num(p.size, 40);
      own = {
        width: size, height: size, borderRadius: '50%', overflow: 'hidden', flexShrink: 0, display: 'grid', placeItems: 'center',
        background: cssColor(s.backgroundColor) ?? 'var(--m-primary-container)', color: 'var(--m-text)', fontSize: size * 0.4, fontWeight: 500,
      };
      content = p.src ? <img src={str(p.src)} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : str(p.initials);
      break;
    }
    case 'Chip': {
      const selected = !!p.selected;
      own = {
        display: 'inline-flex', alignItems: 'center', gap: 8, height: 32, padding: '0 16px 0 12px', borderRadius: 8, fontSize: 14, fontWeight: 500,
        background: selected ? 'var(--m-secondary-container)' : 'transparent',
        boxShadow: selected ? undefined : 'inset 0 0 0 1px var(--m-outline)', whiteSpace: 'nowrap', alignSelf: 'flex-start',
      };
      content = (
        <>
          {selected ? <Icon name="check" size={18} /> : p.icon ? <Icon name={p.icon} size={18} /> : null}
          {str(p.label)}
        </>
      );
      break;
    }
    case 'ListTile':
      own = { display: 'flex', alignItems: 'center', gap: 16, minHeight: p.subtitle ? 72 : 56 };
      content = (
        <>
          {p.leadingIcon ? <Icon name={p.leadingIcon} color="var(--m-muted)" /> : null}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 16, lineHeight: '24px', letterSpacing: '0.5px' }}>{str(p.title)}</div>
            {p.subtitle ? <div style={{ fontSize: 14, lineHeight: '20px', color: 'var(--m-muted)' }}>{str(p.subtitle)}</div> : null}
          </div>
          {p.trailingIcon ? <Icon name={p.trailingIcon} color="var(--m-muted)" /> : null}
        </>
      );
      break;
    case 'ProgressBar': {
      const value = Math.max(0, Math.min(1, num(p.value, 0.5)));
      own = { height: 6, borderRadius: s.borderRadius ?? 4, background: 'var(--m-primary-container)', overflow: 'hidden', flexShrink: 0 };
      content = <div style={{ width: `${value * 100}%`, height: '100%', background: 'var(--m-primary)', borderRadius: 'inherit' }} />;
      break;
    }
    case 'Button': {
      const variant = str(p.variant, 'filled');
      const looks: Record<string, CSSProperties> = {
        filled: { background: 'var(--m-primary)', color: 'var(--m-on-primary)' },
        tonal: { background: 'var(--m-secondary-container)', color: 'var(--m-text)' },
        outlined: { boxShadow: 'inset 0 0 0 1px var(--m-outline)', color: 'var(--m-primary)' },
        text: { color: 'var(--m-primary)' },
      };
      own = {
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, minHeight: 48, padding: '0 24px',
        borderRadius: 'var(--m-radius)', fontSize: 14, fontWeight: 500, letterSpacing: '0.1px', whiteSpace: 'nowrap',
        ...looks[variant] ?? looks.filled, ...stripUndefined({ color: cssColor(s.color), background: cssColor(s.backgroundColor) }),
      };
      content = <>{p.icon ? <Icon name={p.icon} size={18} /> : null}{str(p.label)}</>;
      break;
    }
    case 'IconButton':
      own = { width: 40, height: 40, borderRadius: '50%', display: 'grid', placeItems: 'center', flexShrink: 0 };
      content = <Icon name={p.icon} color={cssColor(s.color) ?? 'var(--m-muted)'} />;
      break;
    case 'TextField': {
      const label = str(p.label);
      const hint = str(p.hint);
      own = { position: 'relative', minHeight: 56, borderRadius: 'var(--m-radius)', boxShadow: 'inset 0 0 0 1px var(--m-outline)', display: 'flex', alignItems: 'center', gap: 12, padding: '0 16px' };
      content = (
        <>
          {p.icon ? <Icon name={p.icon} color="var(--m-muted)" /> : null}
          <span style={{ fontSize: 16, color: 'var(--m-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {hint && label ? (p.obscure ? '••••••••' : hint) : label || hint}
          </span>
          {hint && label ? (
            <span style={{ position: 'absolute', top: -8, left: 12, padding: '0 4px', fontSize: 12, lineHeight: '16px', color: 'var(--m-muted)', background: 'var(--m-bg-behind, var(--m-background))' }}>
              {label}
            </span>
          ) : null}
        </>
      );
      break;
    }
    case 'Switch': {
      const on = !!p.value;
      own = { display: 'flex', alignItems: 'center', justifyContent: 'space-between', minHeight: 56, gap: 16 };
      content = (
        <>
          <span style={{ fontSize: 16 }}>{str(p.label)}</span>
          <span style={{ width: 52, height: 32, borderRadius: 16, flexShrink: 0, position: 'relative', background: on ? 'var(--m-primary)' : 'var(--m-surface-high)', boxShadow: on ? undefined : 'inset 0 0 0 2px var(--m-outline)' }}>
            <span style={{ position: 'absolute', top: on ? 4 : 8, left: on ? 24 : 8, width: on ? 24 : 16, height: on ? 24 : 16, borderRadius: '50%', background: on ? 'var(--m-on-primary)' : 'var(--m-outline)' }} />
          </span>
        </>
      );
      break;
    }
    case 'Checkbox': {
      const on = !!p.value;
      own = { display: 'flex', alignItems: 'center', gap: 16, minHeight: 56 };
      content = (
        <>
          <span style={{ width: 18, height: 18, borderRadius: 2, flexShrink: 0, display: 'grid', placeItems: 'center', background: on ? 'var(--m-primary)' : undefined, boxShadow: on ? undefined : 'inset 0 0 0 2px var(--m-muted)' }}>
            {on ? <Icon name="check" size={16} color="var(--m-on-primary)" /> : null}
          </span>
          <span style={{ fontSize: 16 }}>{str(p.label)}</span>
        </>
      );
      break;
    }
    case 'Slider': {
      const value = Math.max(0, Math.min(1, num(p.value, 0.5)));
      own = { height: 44, display: 'flex', alignItems: 'center', padding: '0 12px' };
      content = (
        <div style={{ position: 'relative', flex: 1, height: 4, borderRadius: 2, background: 'var(--m-primary-container)' }}>
          <div style={{ width: `${value * 100}%`, height: '100%', borderRadius: 2, background: 'var(--m-primary)' }} />
          <div style={{ position: 'absolute', top: -8, left: `calc(${value * 100}% - 10px)`, width: 20, height: 20, borderRadius: '50%', background: 'var(--m-primary)' }} />
        </div>
      );
      break;
    }
    case 'AppBar':
      // App bars are lifted into the screen chrome; one elsewhere renders as a title (like Flutter).
      own = { fontSize: 22, lineHeight: '28px' };
      content = str(p.title);
      break;
    default:
      own = { padding: 8, fontSize: 12, color: '#B91C1C', background: '#FEF2F2' };
      content = `Unknown component: ${node.type}`;
  }

  const interactive = !ctx.passive && ctx.onSelect;
  const selected = ctx.selectedId === node.id;
  const hovered = !selected && ctx.hoveredId === node.id;
  return (
    <div
      data-node-id={node.id}
      style={{
        ...box,
        ...own,
        ...(box.height !== undefined && own.height === undefined ? { height: box.height } : {}),
        outline: selected ? '2px solid #7C3AED' : hovered ? '1px solid rgb(124 58 237 / 0.6)' : undefined,
        outlineOffset: selected || hovered ? -1 : undefined,
        cursor: interactive ? 'default' : undefined,
      }}
      onClick={interactive ? (e: MouseEvent) => { e.stopPropagation(); ctx.onSelect!(node.id); } : undefined}
      onMouseOver={interactive ? (e: MouseEvent) => { e.stopPropagation(); ctx.onHover?.(node.id); } : undefined}
    >
      {content}
    </div>
  );
}

function stripUndefined<T extends object>(o: T): Partial<T> {
  return Object.fromEntries(Object.entries(o).filter(([, v]) => v !== undefined)) as Partial<T>;
}
