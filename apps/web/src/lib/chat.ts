import type { AppSchema } from '@wolf/schema';
import { ApiError, type ChatMessage } from './api';

export interface ChatHandlers {
  onStart?: (data: { user_message_id: string; version_id: string }) => void;
  onText?: (delta: string) => void;
  onChange?: (text: string) => void;
  onSchema?: (schema: AppSchema) => void;
  onError?: (message: string) => void;
  onMessage?: (message: Omit<ChatMessage, 'role' | 'created_at'>) => void;
}

/** Streams an AI run for a project. Resolves when the server closes the stream. */
export async function streamChat(
  projectId: string,
  body: { prompt: string; selection?: { screenId?: string | null; nodeId?: string | null } },
  handlers: ChatHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`/api/projects/${projectId}/chat`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) {
    const data = await res.json().catch(() => null);
    throw new ApiError(res.status, data?.detail || `The AI request failed (${res.status}).`);
  }

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = '';
  for (;;) {
    const { value, done } = await reader.read();
    if (done) return;
    buffer += value;
    let sep: number;
    while ((sep = buffer.indexOf('\n\n')) !== -1) {
      const block = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      let event = 'message';
      let data = '';
      for (const line of block.split('\n')) {
        if (line.startsWith('event: ')) event = line.slice(7);
        else if (line.startsWith('data: ')) data += line.slice(6);
      }
      const payload = data ? JSON.parse(data) : {};
      switch (event) {
        case 'start': handlers.onStart?.(payload); break;
        case 'text': handlers.onText?.(payload.delta); break;
        case 'change': handlers.onChange?.(payload.text); break;
        case 'schema': handlers.onSchema?.(payload.schema); break;
        case 'error': handlers.onError?.(payload.message); break;
        case 'message': handlers.onMessage?.(payload); break;
      }
    }
  }
}
