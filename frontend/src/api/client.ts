import { readSSE } from '../utils/sse'
import type { AgentEvent, FeedbackSignal, Meta, MoodHistory, WatchlistEntry } from './types'

const BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ?? ''

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

async function* stream(path: string, body: unknown, signal?: AbortSignal): AsyncGenerator<AgentEvent> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify(body),
    signal,
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  yield* readSSE<AgentEvent>(res)
}

export interface ChatPayload {
  user_id: string
  session_id: string | null
  message: string
  chip?: string | null
  languages: string[]
  energy?: number | null
  mood_shift?: number | null
}

export const api = {
  meta: () => json<Meta>('/api/meta'),
  chat: (p: ChatPayload, signal?: AbortSignal) => stream('/api/chat', p, signal),
  group: (
    p: { user_id: string; session_id: string | null; members: { name: string; mood: string }[]; languages: string[] },
    signal?: AbortSignal,
  ) => stream('/api/group', p, signal),
  surprise: (p: { user_id: string; session_id: string | null; languages: string[] }, signal?: AbortSignal) =>
    stream('/api/surprise', p, signal),
  feedback: (user_id: string, movie_id: number, signal: FeedbackSignal) =>
    json<{ ok: boolean }>('/api/feedback', { method: 'POST', body: JSON.stringify({ user_id, movie_id, signal }) }),
  watchlist: (user_id: string) => json<WatchlistEntry[]>(`/api/watchlist?user_id=${encodeURIComponent(user_id)}`),
  addToWatchlist: (user_id: string, movie_id: number) =>
    json<{ ok: boolean }>('/api/watchlist', { method: 'POST', body: JSON.stringify({ user_id, movie_id }) }),
  removeFromWatchlist: (user_id: string, movie_id: number) =>
    json<{ ok: boolean }>(`/api/watchlist/${movie_id}?user_id=${encodeURIComponent(user_id)}`, { method: 'DELETE' }),
  moods: (user_id: string, days = 7) =>
    json<MoodHistory>(`/api/moods?user_id=${encodeURIComponent(user_id)}&days=${days}`),
}
