<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { api } from '../api/client'
import type { Chip } from '../api/types'
import AssistantMessage from '../components/AssistantMessage.vue'
import Composer from '../components/Composer.vue'
import FineTune from '../components/FineTune.vue'
import GroupModeDialog from '../components/GroupModeDialog.vue'
import LanguageFilter from '../components/LanguageFilter.vue'
import MoodChips from '../components/MoodChips.vue'
import { useChatStore } from '../stores/chat'
import { useUserStore } from '../stores/user'
import { useWatchlistStore } from '../stores/watchlist'
import { greeting } from '../utils/format'

const chat = useChatStore()
const user = useUserStore()
const watchlist = useWatchlistStore()

const FALLBACK_CHIPS: Chip[] = [
  { id: 'drained', label: 'Drained', emoji: '😴', text: '' },
  { id: 'happy', label: 'Happy', emoji: '😄', text: '' },
  { id: 'heartbroken', label: 'Heartbroken', emoji: '💔', text: '' },
  { id: 'stressed', label: 'Stressed', emoji: '😤', text: '' },
  { id: 'think', label: 'Want to think', emoji: '🤯', text: '' },
  { id: 'party', label: 'Party mood', emoji: '🎉', text: '' },
]
const chips = ref<Chip[]>(FALLBACK_CHIPS)
const hello = greeting()
const showTune = ref(false)
const showFilters = ref(false)
const groupDialog = ref<InstanceType<typeof GroupModeDialog> | null>(null)
const thread = ref<HTMLElement | null>(null)

onMounted(async () => {
  try {
    chips.value = (await api.meta()).chips
  } catch {
    /* keep fallback chips */
  }
  if (!watchlist.loaded) watchlist.load().catch(() => {})
})

// Bring each new assistant turn into view (start of the message, not the bottom).
watch(
  () => chat.items.length,
  async () => {
    await nextTick()
    const nodes = thread.value?.querySelectorAll('[data-role="assistant"]')
    nodes?.[nodes.length - 1]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  },
)

function pickChip(chip: Chip) {
  chat.send('', chip)
}
function retry() {
  const lastUser = [...chat.items].reverse().find((i) => i.role === 'user')
  if (lastUser && lastUser.role === 'user') chat.send(lastUser.text)
}
</script>

<template>
  <!-- Landing -->
  <section v-if="!chat.started" class="mx-auto flex max-w-3xl flex-col items-center pb-10 pt-10 text-center sm:pt-20" aria-labelledby="hero-title">
    <p class="eyebrow animate-rise">{{ hello.emoji }} {{ hello.text }}</p>
    <h1 id="hero-title" class="animate-rise mt-3 font-display text-4xl font-semibold leading-[1.08] tracking-tight [text-wrap:balance] sm:text-6xl" style="animation-delay: 60ms">
      How are you feeling <span class="bg-gradient-to-r from-accent to-accent-2 bg-clip-text italic text-transparent">right now?</span>
    </h1>
    <p class="animate-rise mt-4 max-w-xl text-muted [text-wrap:pretty] sm:text-lg" style="animation-delay: 120ms">
      Say it however it comes out — English, Manglish, Hinglish. I'll find films that fit, and tell you where to stream them.
    </p>

    <div class="animate-rise mt-8 w-full" style="animation-delay: 180ms">
      <Composer large autofocus :busy="chat.busy" @send="chat.send($event)" />
    </div>

    <p class="eyebrow mt-8">or just pick a vibe</p>
    <div class="mt-3"><MoodChips :chips="chips" :disabled="chat.busy" @pick="pickChip" /></div>

    <div class="mt-8 flex flex-wrap justify-center gap-2">
      <button type="button" class="btn-ghost" @click="chat.surprise()"><span aria-hidden="true">🎲</span> Surprise me</button>
      <button type="button" class="btn-ghost" @click="groupDialog?.open()"><span aria-hidden="true">👥</span> Watching with others</button>
      <button type="button" class="btn-ghost" :aria-expanded="showTune" aria-controls="tune" @click="showTune = !showTune">
        <span aria-hidden="true">🎚️</span> Fine-tune
      </button>
    </div>

    <Transition name="fade">
      <div v-if="showTune" id="tune" class="card mt-5 w-full p-5 text-left">
        <FineTune />
        <div class="mt-5 border-t border-line pt-4">
          <p class="mb-2 text-sm font-medium">Languages</p>
          <LanguageFilter />
        </div>
      </div>
    </Transition>
    <div v-if="!showTune" class="mt-6"><LanguageFilter /></div>
  </section>

  <!-- Conversation -->
  <section v-else class="mx-auto max-w-5xl pb-44 pt-6 sm:pb-56" aria-label="Conversation">
    <div ref="thread" role="log" aria-live="polite" aria-relevant="additions" class="flex flex-col gap-7">
      <template v-for="(item, i) in chat.items" :key="item.id">
        <div v-if="item.role === 'user'" class="animate-rise flex justify-end">
          <p class="max-w-[85%] rounded-3xl rounded-br-md bg-accent-soft px-4 py-2.5 text-[15px] sm:max-w-[70%]">
            <span class="sr-only">You said:</span>{{ item.text }}
          </p>
        </div>
        <div v-else data-role="assistant" class="scroll-mt-24">
          <AssistantMessage :item="item" :is-last="i === chat.items.length - 1" @option="chat.send($event)" @retry="retry" />
        </div>
      </template>
    </div>
  </section>

  <!-- Sticky composer during a conversation -->
  <div v-if="chat.started" class="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-bg/85 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-3 backdrop-blur-xl">
    <div class="mx-auto flex max-w-5xl flex-col gap-2.5 px-4 sm:px-6">
      <div class="hidden items-center gap-2 overflow-x-auto pb-0.5 [scrollbar-width:none] sm:flex">
        <MoodChips :chips="chips" compact :disabled="chat.busy" class="!flex-nowrap" @pick="pickChip" />
      </div>
      <Transition name="fade">
        <div v-if="showFilters" class="card p-4">
          <FineTune />
          <div class="mt-4"><LanguageFilter /></div>
        </div>
      </Transition>
      <Composer :busy="chat.busy" @send="chat.send($event)" />
      <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
        <button type="button" class="hover:text-ink" @click="chat.surprise()">🎲 Surprise me</button>
        <button type="button" class="hover:text-ink" @click="groupDialog?.open()">👥 Watching with others</button>
        <button type="button" class="hover:text-ink" :aria-expanded="showFilters" @click="showFilters = !showFilters">
          🎚️ Filters<span v-if="user.languages.length"> · {{ user.languages.map((l) => l.toUpperCase()).join(', ') }}</span>
        </button>
        <button type="button" class="ml-auto hover:text-ink" @click="chat.reset()">↺ New chat</button>
      </div>
    </div>
  </div>

  <GroupModeDialog ref="groupDialog" @submit="chat.group($event)" />
</template>
