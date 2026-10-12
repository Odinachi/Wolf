import { AlertCircle, ArrowUp, Check, ChevronDown, History, MousePointerClick, Square, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import type { ChatMessage } from '../lib/api';
import { LogoMark } from './Logo';

export interface LiveRun {
  text: string;
  changes: string[];
  error: string | null;
}

interface Props {
  messages: ChatMessage[];
  live: LiveRun | null;
  busy: boolean;
  selectionLabel: string | null;
  onClearSelection: () => void;
  onSend: (prompt: string) => void;
  onStop: () => void;
  onRestore: (versionId: string) => void;
}

export function ChatPanel({ messages, live, busy, selectionLabel, onClearSelection, onSend, onStop, onRestore }: Props) {
  const [input, setInput] = useState('');
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages.length, live?.changes.length, live?.text]);

  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [input]);

  const send = () => {
    const text = input.trim();
    if (!text || busy) return;
    onSend(text);
    setInput('');
  };

  return (
    <div className="flex h-full flex-col">
      <div ref={listRef} className="flex-1 space-y-6 overflow-y-auto px-5 py-6">
        {messages.length === 0 && !live && (
          <div className="mt-10 text-center text-sm text-zinc-500">
            <LogoMark size={36} className="mx-auto mb-3" />
            Describe the app you want, or a change to make.
          </div>
        )}
        {messages.map(m => m.role === 'user'
          ? <UserBubble key={m.id} text={m.content} />
          : <AssistantMessage key={m.id} text={m.content} changes={m.changes} onRestore={m.version_id ? () => onRestore(m.version_id!) : undefined} />)}
        {live && <AssistantMessage text={live.text} changes={live.changes} streaming error={live.error} />}
      </div>

      <div className="p-3">
        <div className="rounded-2xl bg-white p-2 shadow-sm ring-1 ring-zinc-950/10 transition focus-within:ring-violet-400/70">
          {selectionLabel && (
            <div className="mb-1 flex items-center gap-1.5 px-1.5">
              <span className="flex min-w-0 items-center gap-1.5 rounded-lg bg-violet-50 px-2 py-1 text-xs font-medium text-violet-700 ring-1 ring-violet-200">
                <MousePointerClick size={12} className="shrink-0" />
                <span className="truncate">Editing {selectionLabel}</span>
                <button onClick={onClearSelection} aria-label="Clear selection" className="-mr-0.5 rounded hover:bg-violet-100"><X size={12} /></button>
              </span>
            </div>
          )}
          <textarea
            ref={inputRef}
            rows={2}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
            placeholder={selectionLabel ? 'What should change here?' : 'Ask Wolf to add a screen, restyle, or change anything…'}
            className="block w-full resize-none bg-transparent px-2 py-1 text-[15px] leading-relaxed outline-none placeholder:text-zinc-400"
          />
          <div className="flex items-center justify-between px-1">
            <span className="text-[11px] text-zinc-400">{busy ? 'Wolf is building…' : 'Enter to send · Shift+Enter for a new line'}</span>
            {busy ? (
              <button onClick={onStop} aria-label="Stop" className="grid size-8 place-items-center rounded-full bg-white text-zinc-900 ring-1 ring-zinc-300 transition hover:bg-zinc-50">
                <Square size={11} fill="currentColor" />
              </button>
            ) : (
              <button onClick={send} disabled={!input.trim()} aria-label="Send" className="grid size-8 place-items-center rounded-full bg-zinc-950 text-white transition hover:bg-zinc-800 disabled:bg-zinc-200 disabled:text-zinc-400">
                <ArrowUp size={16} strokeWidth={2.4} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function UserBubble({ text }: { text: string }) {
  return (
    <div className="flex justify-end animate-[fade-up_300ms_ease_both]">
      <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-zinc-100 px-4 py-2.5 text-[15px] leading-relaxed text-zinc-900">{text}</div>
    </div>
  );
}

function AssistantMessage({ text, changes, streaming, error, onRestore }: { text: string; changes: string[]; streaming?: boolean; error?: string | null; onRestore?: () => void }) {
  const [open, setOpen] = useState(true);
  const shown = open ? changes : changes.slice(-3);
  return (
    <div className="flex gap-3 animate-[fade-up_300ms_ease_both]">
      <LogoMark size={26} className={`mt-0.5 shrink-0 ${streaming ? 'animate-[breathe_1.6s_ease-in-out_infinite]' : ''}`} />
      <div className="min-w-0 flex-1 space-y-3">
        {changes.length > 0 && (
          <div className="overflow-hidden rounded-xl bg-zinc-50 ring-1 ring-zinc-950/5">
            <button onClick={() => setOpen(!open)} className="flex w-full items-center justify-between px-3 py-2 text-xs font-medium text-zinc-600">
              <span>{streaming ? 'Building' : 'Made'} {changes.length} change{changes.length === 1 ? '' : 's'}</span>
              <ChevronDown size={14} className={`transition ${open ? 'rotate-180' : ''}`} />
            </button>
            <ul className="space-y-1 px-3 pb-2.5">
              {shown.map((c, i) => (
                <li key={`${i}-${c}`} className="flex items-start gap-2 text-[13px] text-zinc-600 animate-[fade-up_250ms_ease_both]">
                  <Check size={13} strokeWidth={3} className="mt-0.5 shrink-0 text-emerald-500" />
                  <span>{c}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {text ? <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-zinc-800">{text}</p> : streaming && !error ? (
          <p className="text-shimmer-muted text-[15px] font-medium">{changes.length ? 'Building your app…' : 'Thinking…'}</p>
        ) : null}
        {error && (
          <p className="flex items-start gap-2 rounded-xl bg-red-50 px-3 py-2.5 text-sm text-red-700 ring-1 ring-red-200">
            <AlertCircle size={15} className="mt-0.5 shrink-0" /> {error}
          </p>
        )}
        {onRestore && changes.length > 0 && (
          <button onClick={onRestore} className="flex items-center gap-1.5 text-xs font-medium text-zinc-400 transition hover:text-zinc-900">
            <History size={13} /> Restore to before this
          </button>
        )}
      </div>
    </div>
  );
}
