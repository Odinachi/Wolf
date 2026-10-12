import type { AppSchema, Screen, Theme } from '@wolf/schema';
import { idToken } from './firebase';

/** The backend's origin; empty means same origin (the dev server proxies /api). */
export const API_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '');

export async function authHeaders(): Promise<Record<string, string>> {
  const token = await idToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface User {
  id: string;
  name: string;
  email: string | null;
  avatar_url: string | null;
}

export type AuthProviderId = 'github' | 'google';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  changes: string[];
  version_id: string | null;
  created_at: string;
}

export interface ProjectSummary {
  id: string;
  name: string;
  updated_at: string;
  cover: { theme: Theme; screen: Screen | null };
}

export interface Project {
  id: string;
  name: string;
  schema: AppSchema;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
  generating: boolean;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(API_URL + path, {
      ...init,
      headers: { ...(init.body ? { 'Content-Type': 'application/json' } : {}), ...(await authHeaders()), ...init.headers },
    });
  } catch {
    throw new ApiError(0, "Can't reach the Wolf API. Is it running?");
  }
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = data?.detail;
    const message = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail[0]?.msg?.replace(/^Value error, /, '') : null;
    throw new ApiError(res.status, message || `Request failed (${res.status}).`);
  }
  return data as T;
}

const json = (body: unknown) => JSON.stringify(body);

export const api = {
  me: () => request<User>('/api/auth/me'),
  config: () => request<{ access_mode: 'open' | 'waitlist' }>('/api/config'),
  joinWaitlist: (body: { email: string; idea?: string; website?: string }) => request<{ ok: boolean }>('/api/waitlist', { method: 'POST', body: json(body) }),

  projects: () => request<ProjectSummary[]>('/api/projects'),
  createProject: (prompt: string) => request<Project>('/api/projects', { method: 'POST', body: json({ prompt }) }),
  project: (id: string) => request<Project>(`/api/projects/${id}`),
  renameProject: (id: string, name: string) => request<ProjectSummary>(`/api/projects/${id}`, { method: 'PATCH', body: json({ name }) }),
  deleteProject: (id: string) => request<void>(`/api/projects/${id}`, { method: 'DELETE' }),
  restoreVersion: (id: string, versionId: string) => request<Project>(`/api/projects/${id}/versions/${versionId}/restore`, { method: 'POST' }),
};
