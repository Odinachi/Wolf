import { FRAME_HEIGHT, FRAME_WIDTH, type Navigation, type Screen, type Theme } from '@wolf/schema';
import { useEffect, type CSSProperties } from 'react';
import { Icon, NodeView, type RenderContext } from './NodeView';
import { cssColor, loadFont, themeVars } from './theme';

interface Props {
  screen: Screen;
  theme: Theme;
  navigation?: Navigation;
  ctx?: RenderContext;
  /** Draws the device bezel around the screen. */
  bezel?: boolean;
  style?: CSSProperties;
}

/** A phone-sized render of one screen: status bar, app bar, scrolling body and bottom tabs. */
export function PhoneFrame({ screen, theme, navigation, ctx = {}, bezel = true, style }: Props) {
  useEffect(() => loadFont(theme.fontFamily), [theme.fontFamily]);

  const children = screen.root.children;
  const appBar = children[0]?.type === 'AppBar' ? children[0] : null;
  const body = appBar ? children.slice(1) : children;
  const tabs = navigation?.type === 'tabs' && navigation.tabs.length >= 2 ? navigation.tabs : null;
  const tabIndex = tabs ? tabs.findIndex(t => t.screenId === screen.id) : -1;
  const background = cssColor(screen.backgroundColor) ?? cssColor(screen.root.style.backgroundColor) ?? theme.background;
  const dark = theme.brightness === 'dark';
  const root = screen.root;
  const rootStyle = root.style ?? {};
  const pad = typeof rootStyle.padding === 'number' ? `${rootStyle.padding}px` : Array.isArray(rootStyle.padding) ? rootStyle.padding.map(n => `${n}px`).join(' ') : undefined;
  const selectable = !ctx.passive && ctx.onSelect;

  const screenEl = (
    <div
      style={{
        ...themeVars(theme),
        ['--m-bg-behind' as string]: background,
        width: FRAME_WIDTH,
        height: FRAME_HEIGHT,
        background,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        borderRadius: bezel ? 44 : 0,
        position: 'relative',
        WebkitFontSmoothing: 'antialiased',
      }}
      onMouseLeave={() => ctx.onHover?.(null)}
    >
      {/* Status bar */}
      <div style={{ height: 50, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 34px 0 40px', fontSize: 15, fontWeight: 600, fontFamily: 'system-ui, sans-serif', color: dark ? '#fff' : '#000' }}>
        <span>9:41</span>
        <span style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <Icon name="signal_cellular_alt" size={17} />
          <Icon name="wifi" size={17} />
          <Icon name="battery_full" size={19} style={{ transform: 'rotate(90deg)' }} />
        </span>
      </div>

      {appBar ? (
        <div
          data-node-id={appBar.id}
          onClick={selectable ? e => { e.stopPropagation(); ctx.onSelect!(appBar.id); } : undefined}
          onMouseOver={selectable ? e => { e.stopPropagation(); ctx.onHover?.(appBar.id); } : undefined}
          style={{
            height: 64, flexShrink: 0, display: 'flex', alignItems: 'center', gap: 4, padding: '0 4px 0 4px',
            background: cssColor(appBar.style.backgroundColor), color: cssColor(appBar.style.color),
            outline: ctx.selectedId === appBar.id ? '2px solid #7C3AED' : ctx.hoveredId === appBar.id ? '1px solid rgb(124 58 237 / 0.6)' : undefined,
            outlineOffset: -1,
          }}
        >
          {appBar.props.showBack ? <span style={{ width: 48, height: 48, display: 'grid', placeItems: 'center' }}><Icon name="arrow_back" /></span> : <span style={{ width: 12 }} />}
          <span style={{ flex: 1, fontSize: 22, lineHeight: '28px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{String(appBar.props.title ?? '')}</span>
          {appBar.props.actionIcon ? <span style={{ width: 48, height: 48, display: 'grid', placeItems: 'center' }}><Icon name={appBar.props.actionIcon} /></span> : null}
        </div>
      ) : null}

      {/* Body: the screen root Column */}
      <div
        data-node-id={root.id}
        className="wolf-scroll"
        onClick={selectable ? e => { e.stopPropagation(); ctx.onSelect!(root.id); } : undefined}
        style={{
          flex: 1, minHeight: 0, overflowY: ctx.passive ? 'hidden' : 'auto', padding: pad,
          display: 'flex', flexDirection: 'column', gap: rootStyle.gap, alignItems: 'stretch',
          justifyContent: rootStyle.mainAxisAlignment === 'center' ? 'center' : rootStyle.mainAxisAlignment === 'end' ? 'flex-end' : rootStyle.mainAxisAlignment === 'spaceBetween' ? 'space-between' : undefined,
          outline: ctx.selectedId === root.id ? '2px solid #7C3AED' : undefined, outlineOffset: -2,
        }}
      >
        {body.map(child => <NodeView key={child.id} node={child} ctx={ctx} axis="vertical" />)}
      </div>

      {tabs && tabIndex >= 0 ? (
        <div style={{ height: 80, flexShrink: 0, display: 'flex', background: 'var(--m-surface-high)', paddingBottom: 12 }}>
          {tabs.map((t, i) => (
            <div key={t.screenId} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 4, fontSize: 12, fontWeight: 500 }}>
              <span style={{ width: 64, height: 32, borderRadius: 16, display: 'grid', placeItems: 'center', background: i === tabIndex ? 'var(--m-secondary-container)' : undefined }}>
                <Icon name={t.icon} />
              </span>
              <span style={{ color: i === tabIndex ? 'var(--m-text)' : 'var(--m-muted)' }}>{t.label}</span>
            </div>
          ))}
        </div>
      ) : null}

      {/* Home indicator */}
      <div style={{ position: 'absolute', bottom: 8, left: '50%', transform: 'translateX(-50%)', width: 134, height: 5, borderRadius: 3, background: dark ? '#fff' : '#000', opacity: 0.85, pointerEvents: 'none' }} />
      {bezel ? <div style={{ position: 'absolute', top: 11, left: '50%', transform: 'translateX(-50%)', width: 120, height: 34, borderRadius: 20, background: '#000', pointerEvents: 'none' }} /> : null}
    </div>
  );

  if (!bezel) return screenEl;
  return (
    <div style={{ padding: 10, borderRadius: 54, background: '#0B0B0F', boxShadow: '0 0 0 1.5px #2A2A30, 0 40px 80px -24px rgb(24 24 27 / 0.45), 0 20px 30px -20px rgb(24 24 27 / 0.3)', ...style }}>
      {screenEl}
    </div>
  );
}

/** A scaled-down, non-interactive render for cards and showcases. */
export function PhoneThumbnail({ screen, theme, navigation, width = 180, bezel = true }: { screen: Screen; theme: Theme; navigation?: Navigation; width?: number; bezel?: boolean }) {
  const outer = bezel ? FRAME_WIDTH + 20 : FRAME_WIDTH;
  const scale = width / outer;
  const outerH = bezel ? FRAME_HEIGHT + 20 : FRAME_HEIGHT;
  return (
    <div style={{ width, height: outerH * scale, position: 'relative', pointerEvents: 'none' }}>
      <div style={{ transform: `scale(${scale})`, transformOrigin: 'top left', position: 'absolute', top: 0, left: 0 }}>
        <PhoneFrame screen={screen} theme={theme} navigation={navigation} bezel={bezel} ctx={{ passive: true }} />
      </div>
    </div>
  );
}
