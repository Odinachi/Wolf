import { COMPONENTS, findNode, type AppSchema } from '@wolf/schema';
import { ChevronLeft, Loader2 } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router';
import { Canvas } from '../components/Canvas';
import { ChatPanel, type LiveRun } from '../components/ChatPanel';
import { LogoMark } from '../components/Logo';
import { UserMenu } from '../components/UserMenu';
import { api, type ChatMessage, type Project } from '../lib/api';
import { useAuth } from '../lib/auth';
import { streamChat } from '../lib/chat';
import { useMediaQuery } from '../lib/useMediaQuery';

type Selection = { screenId: string | null; nodeId: string | null };

export function Workspace() {
  const { id = '' } = useParams();
  const { user, loading: authLoading } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [schema, setSchema] = useState<AppSchema | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [live, setLive] = useState<LiveRun | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selection, setSelection] = useState<Selection>({ screenId: null, nodeId: null });
  const abortRef = useRef<AbortController | null>(null);
  const autostarted = useRef(false);
  // On narrow screens only one pane fits; toggle between them.
  const narrow = useMediaQuery('(max-width: 899px)');
  const [pane, setPane] = useState<'chat' | 'preview'>('chat');

  const load = useCallback(async () => {
    try {
      const p = await api.project(id);
      setProject(p);
      setSchema(p.schema);
      setMessages(p.messages);
      return p;
    } catch (e) {
      setLoadError((e as Error).message);
      return null;
    }
  }, [id]);

  useEffect(() => {
    if (!authLoading && !user) navigate('/', { replace: true });
  }, [authLoading, user, navigate]);

  useEffect(() => {
    if (user) load();
    return () => abortRef.current?.abort();
  }, [user, load]);

  // Another tab may be generating: poll until it finishes.
  useEffect(() => {
    if (!project?.generating || live) return;
    const t = setInterval(async () => {
      const p = await load();
      if (p && !p.generating) clearInterval(t);
    }, 2500);
    return () => clearInterval(t);
  }, [project?.generating, live, load]);

  const send = useCallback(async (prompt: string) => {
    if (abortRef.current) return;
    const controller = new AbortController();
    abortRef.current = controller;
    const sel = selection.nodeId ? selection : null;
    setMessages(m => [...m, { id: `local-${Date.now()}`, role: 'user', content: prompt, changes: [], version_id: null, created_at: new Date().toISOString() }]);
    setLive({ text: '', changes: [], error: null });
    try {
      await streamChat(id, { prompt, selection: sel ?? undefined }, {
        onText: d => setLive(l => l && { ...l, text: l.text + d }),
        onDiscard: () => setLive(l => l && { ...l, text: '' }),
        onChange: c => setLive(l => l && { ...l, changes: [...l.changes, c] }),
        onSchema: s => setSchema(s),
        onError: msg => setLive(l => l && { ...l, error: msg }),
      }, controller.signal);
    } catch (e) {
      if ((e as Error).name !== 'AbortError') setLive(l => l && { ...l, error: (e as Error).message });
    } finally {
      abortRef.current = null;
      // The server has saved the run (even if stopped); sync with it.
      const p = await load();
      if (p) setLive(null);
    }
  }, [id, selection, load]);

  // Start generating straight away when arriving from the landing page prompt.
  useEffect(() => {
    const autostart = (location.state as { autostart?: string } | null)?.autostart;
    if (!project || !autostart || autostarted.current) return;
    autostarted.current = true;
    navigate(location.pathname, { replace: true, state: null });
    if (project.messages.length === 0 && !project.generating) send(autostart);
  }, [project, location, navigate, send]);

  const restore = async (versionId: string) => {
    if (!confirm('Restore the app to how it was before this change? Later changes are saved as a version too.')) return;
    const p = await api.restoreVersion(id, versionId);
    setProject(p);
    setSchema(p.schema);
    setMessages(p.messages);
  };

  const selectionLabel = useMemo(() => {
    if (!schema || !selection.nodeId || !selection.screenId) return null;
    const screen = schema.screens.find(s => s.id === selection.screenId);
    if (!screen) return null;
    if (screen.root.id === selection.nodeId) return `${screen.name} screen`;
    const node = findNode(screen.root, selection.nodeId);
    if (!node) return null;
    const text = (node.props.text ?? node.props.label ?? node.props.title) as string | undefined;
    return `${node.name ?? COMPONENTS[node.type]?.label ?? node.type}${text ? ` “${String(text).slice(0, 24)}”` : ''} on ${screen.name}`;
  }, [schema, selection]);

  if (loadError) {
    return (
      <div className="grid h-dvh place-items-center bg-zinc-50 text-center">
        <div>
          <p className="text-zinc-600">{loadError}</p>
          <Link to="/" className="mt-4 inline-block text-sm font-medium text-violet-700 hover:underline">Back to home</Link>
        </div>
      </div>
    );
  }
  if (!project || !schema) {
    return <div className="grid h-dvh place-items-center bg-zinc-50"><Loader2 className="animate-spin text-zinc-400" /></div>;
  }

  const busy = !!live || project.generating;

  return (
    <div className="flex h-dvh flex-col bg-[#F6F6F8]">
      <header className="flex h-14 shrink-0 items-center justify-between px-3">
        <div className="flex min-w-0 items-center gap-2">
          <Link to="/" className="flex items-center gap-1 rounded-lg p-1.5 text-zinc-500 transition hover:bg-zinc-950/5 hover:text-zinc-900" aria-label="Back to home">
            <ChevronLeft size={18} />
            <LogoMark size={24} />
          </Link>
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold">{schema.name || project.name}</div>
            <div className="text-[11px] text-zinc-500">
              {busy ? <span className="text-violet-600">Building…</span> : `${schema.screens.length} screen${schema.screens.length === 1 ? '' : 's'} · Flutter`}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {narrow && (
            <div className="flex rounded-full bg-zinc-950/5 p-0.5 text-xs font-medium">
              {(['chat', 'preview'] as const).map(p => (
                <button key={p} onClick={() => setPane(p)} className={`rounded-full px-3 py-1.5 capitalize transition ${pane === p ? 'bg-white text-zinc-950 shadow-sm' : 'text-zinc-500'}`}>
                  {p}
                </button>
              ))}
            </div>
          )}
          <UserMenu />
        </div>
      </header>

      <div className="flex min-h-0 flex-1 gap-2 px-2 pb-2">
        <aside className={`flex shrink-0 flex-col overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-zinc-950/5 ${narrow ? (pane === 'chat' ? 'w-full' : 'hidden') : 'w-[400px]'}`}>
          <ChatPanel
            messages={messages}
            live={live}
            busy={busy}
            selectionLabel={selectionLabel}
            onClearSelection={() => setSelection({ screenId: null, nodeId: null })}
            onSend={send}
            onStop={() => abortRef.current?.abort()}
            onRestore={restore}
          />
        </aside>
        <main className={`relative min-w-0 flex-1 overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-zinc-950/5 ${narrow && pane !== 'preview' ? 'hidden' : ''}`}>
          <Canvas schema={schema} generating={busy} selection={selection} onSelect={setSelection} />
        </main>
      </div>
    </div>
  );
}
