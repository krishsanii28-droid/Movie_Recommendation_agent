import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '../api/client'
import type { AgentEvent, CareMessage, FeedbackSignal, MoodProfile, Recommendation } from '../api/types'
import { uid } from '../utils/format'
import { useUserStore } from './user'

export interface UserItem {
  id: string
  role: 'user'
  text: string
  chip?: string
}

export interface AssistantItem {
  id: string
  role: 'assistant'
  text: string
  status: string
  streaming: boolean
  mood?: MoodProfile
  members?: { name: string; mood: MoodProfile }[]
  care?: CareMessage
  question?: string
  options?: string[]
  recommendations?: Recommendation[]
  error?: string
  engine?: string
  kind: 'chat' | 'group' | 'surprise'
}

export type ChatItem = UserItem | AssistantItem

export const useChatStore = defineStore('chat', () => {
  const items = ref<ChatItem[]>([])
  const sessionId = ref<string | null>(null)
  const busy = ref(false)
  const reactions = ref<Record<number, FeedbackSignal>>({})
  let controller: AbortController | null = null

  const started = computed(() => items.value.length > 0)
  const pendingQuestion = computed(() => {
    const last = items.value[items.value.length - 1]
    return last && last.role === 'assistant' && !last.streaming && last.question ? last : null
  })

  async function run(kind: AssistantItem['kind'], events: (signal: AbortSignal) => AsyncGenerator<AgentEvent>) {
    controller?.abort()
    controller = new AbortController()
    const item: AssistantItem = { id: uid(), role: 'assistant', text: '', status: 'Thinking…', streaming: true, kind }
    items.value.push(item)
    const live = items.value[items.value.length - 1] as AssistantItem // reactive proxy
    busy.value = true
    try {
      for await (const ev of events(controller.signal)) apply(live, ev)
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        live.error = "I couldn't reach the film vault just now. Check your connection and try again?"
      }
    } finally {
      live.streaming = false
      busy.value = false
    }
  }

  function apply(item: AssistantItem, ev: AgentEvent) {
    switch (ev.type) {
      case 'session':
        sessionId.value = ev.session_id
        break
      case 'status':
        item.status = ev.text
        break
      case 'mood':
        item.mood = ev.mood
        if (ev.members) item.members = ev.members
        break
      case 'care':
        item.care = ev.care
        break
      case 'delta':
        item.text += ev.text
        break
      case 'question':
        item.question = ev.text
        item.options = ev.options
        break
      case 'recommendations':
        item.recommendations = ev.items
        break
      case 'done':
        item.engine = ev.engine
        break
      case 'error':
        item.error = ev.text
        break
    }
  }

  function send(text: string, chip?: { id: string; label: string; emoji: string }) {
    const user = useUserStore()
    const message = text.trim()
    if (!message && !chip) return
    items.value.push({ id: uid(), role: 'user', text: message || `${chip!.emoji} ${chip!.label}`, chip: chip?.id })
    return run('chat', (signal) =>
      api.chat(
        {
          user_id: user.userId,
          session_id: sessionId.value,
          message,
          chip: chip?.id ?? null,
          languages: user.languages,
          energy: user.energy,
          mood_shift: user.moodShift,
        },
        signal,
      ),
    )
  }

  function surprise() {
    const user = useUserStore()
    items.value.push({ id: uid(), role: 'user', text: '🎲 Surprise me' })
    return run('surprise', (signal) =>
      api.surprise({ user_id: user.userId, session_id: sessionId.value, languages: user.languages }, signal),
    )
  }

  function group(members: { name: string; mood: string }[]) {
    const user = useUserStore()
    items.value.push({
      id: uid(),
      role: 'user',
      text: '👥 Watching together — ' + members.map((m) => `${m.name}: “${m.mood}”`).join(' · '),
    })
    return run('group', (signal) =>
      api.group({ user_id: user.userId, session_id: sessionId.value, members, languages: user.languages }, signal),
    )
  }

  async function react(movieId: number, signal: FeedbackSignal) {
    const user = useUserStore()
    const previous = reactions.value[movieId]
    reactions.value[movieId] = signal
    try {
      await api.feedback(user.userId, movieId, signal)
    } catch {
      if (previous) reactions.value[movieId] = previous
      else delete reactions.value[movieId]
      throw new Error('feedback failed')
    }
  }

  function reset() {
    controller?.abort()
    items.value = []
    sessionId.value = null
    busy.value = false
  }

  return { items, sessionId, busy, reactions, started, pendingQuestion, send, surprise, group, react, reset }
})
