export type Energy = 'low' | 'medium' | 'high'
export type MoodGoal = 'stay' | 'shift' | 'unclear'
export type FeedbackSignal = 'loved' | 'disliked' | 'seen' | 'too_slow' | 'too_heavy'

export interface Provider {
  name: string
  logo_url: string | null
}

export interface WatchProviders {
  stream: Provider[]
  rent: Provider[]
  buy: Provider[]
  link: string | null
  indicative: boolean
}

export interface Movie {
  id: number
  title: string
  year: number | null
  language: string
  language_name: string
  overview: string
  genres: string[]
  keywords: string[]
  tones: string[]
  content_flags: string[]
  runtime: number | null
  rating: number
  vote_count: number
  poster_url: string | null
  providers: WatchProviders
}

export interface MoodContext {
  company: 'alone' | 'partner' | 'family' | 'friends' | 'unknown'
  time_available: number | null
  languages: string[]
  avoid: string[]
}

export interface MoodProfile {
  primary: string
  secondary: string | null
  intensity: number
  energy: Energy
  goal: MoodGoal
  context: MoodContext
  target_tones: string[]
  requested_tones: string[]
  distress: 'none' | 'elevated' | 'crisis'
  summary: string
  key_phrase: string
  vague: boolean
}

export interface Why {
  matched_tones: string[]
  mood_goal: string
  score: number
  notes: string[]
}

export interface Recommendation {
  movie: Movie
  reason: string
  slot: string
  why: Why
}

export interface CareMessage {
  text: string
  helplines: { name: string; contact: string }[]
}

export type AgentEvent =
  | { type: 'session'; session_id: string }
  | { type: 'status'; text: string }
  | { type: 'mood'; mood: MoodProfile; members?: { name: string; mood: MoodProfile }[] }
  | { type: 'care'; care: CareMessage }
  | { type: 'delta'; text: string }
  | { type: 'question'; text: string; options: string[] }
  | { type: 'recommendations'; items: Recommendation[] }
  | { type: 'done'; engine: string; steps: string[] }
  | { type: 'error'; text: string }

export interface Chip {
  id: string
  label: string
  emoji: string
  text: string
}

export interface Meta {
  chips: Chip[]
  languages: { code: string; name: string }[]
  attribution: { tmdb: string; justwatch: string }
}

export interface WatchlistEntry {
  movie_id: number
  note: string
  added_at: string
  movie: Movie
}

export interface MoodEntry {
  primary: string
  secondary: string | null
  energy: Energy
  goal: MoodGoal
  intensity: number
  text: string
  created_at: string
}

export interface MoodHistory {
  entries: MoodEntry[]
  counts: Record<string, number>
  by_day: Record<string, string[]>
  labels: Record<string, { label: string; emoji: string }>
  top: string | null
}
