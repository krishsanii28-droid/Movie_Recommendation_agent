<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api/client'
import type { MoodHistory } from '../api/types'
import { useUserStore } from '../stores/user'

const user = useUserStore()
const data = ref<MoodHistory | null>(null)
const error = ref(false)

onMounted(async () => {
  try {
    data.value = await api.moods(user.userId, 7)
  } catch {
    error.value = true
  }
})

const days = computed(() => {
  const out: { key: string; label: string; moods: string[] }[] = []
  for (let i = 6; i >= 0; i--) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    const key = d.toISOString().slice(0, 10)
    out.push({
      key,
      label: i === 0 ? 'Today' : d.toLocaleDateString(undefined, { weekday: 'short' }),
      moods: data.value?.by_day[key] ?? [],
    })
  }
  return out
})

const bars = computed(() => {
  if (!data.value) return []
  const max = Math.max(1, ...Object.values(data.value.counts))
  return Object.entries(data.value.counts)
    .sort((a, b) => b[1] - a[1])
    .map(([k, n]) => ({ key: k, n, pct: (n / max) * 100, ...(data.value!.labels[k] ?? { label: k, emoji: '🎬' }) }))
})

const NOTE: Record<string, string> = {
  tired: 'Mostly running on fumes this week — be gentle with yourself.',
  stressed: 'A stressy week. Low-stakes comfort films are your friend.',
  anxious: 'A restless week. Keep the cosy picks close.',
  sad: "A heavier week. It's okay — good films help.",
  heartbroken: 'Heart-mending week. One day at a time.',
  lonely: 'A bit of a lonely stretch — maybe a movie night with someone?',
  happy: 'A bright week! Keep that energy going.',
  excited: 'Party-mode week 🎉',
  curious: 'Big-brain week — you went for the thinkers.',
}
const note = computed(() => (data.value?.top ? NOTE[data.value.top] ?? 'An interesting mix this week.' : ''))
const emojiFor = (k: string) => data.value?.labels[k]?.emoji ?? '🎬'
</script>

<template>
  <section class="py-10" aria-labelledby="moods-title">
    <p class="eyebrow">Mood history</p>
    <h1 id="moods-title" class="mt-2 font-display text-4xl font-semibold tracking-tight">Your moods this week</h1>
    <p v-if="note" class="mt-2 text-muted">{{ note }}</p>

    <p v-if="error" class="card mt-8 p-6 text-muted">Couldn't load your mood history right now.</p>

    <div v-else-if="data && !data.entries.length" class="card mt-8 flex flex-col items-center gap-3 p-10 text-center">
      <span class="text-4xl" aria-hidden="true">📅</span>
      <p class="font-display text-xl">No moods logged yet</p>
      <p class="max-w-sm text-sm text-muted">Every time you tell me how you feel, it shows up here — a tiny diary, just for you.</p>
      <RouterLink to="/" class="btn-primary mt-2">Tell me how you feel</RouterLink>
    </div>

    <template v-else-if="data">
      <ol class="mt-8 grid grid-cols-7 gap-2" aria-label="Moods by day">
        <li v-for="d in days" :key="d.key" class="card flex min-h-36 flex-col items-center gap-1.5 p-2 sm:p-3">
          <span class="text-xs font-medium text-muted">{{ d.label }}</span>
          <span v-if="!d.moods.length" class="mt-auto text-xs text-muted/60" aria-label="no moods">·</span>
          <span v-for="(m, i) in d.moods.slice(-4)" :key="i" class="text-xl sm:text-2xl" :title="data.labels[m]?.label ?? m" role="img" :aria-label="data.labels[m]?.label ?? m">{{ emojiFor(m) }}</span>
        </li>
      </ol>

      <div class="card mt-6 p-5">
        <h2 class="font-display text-xl font-semibold">What came up most</h2>
        <ul class="mt-4 flex flex-col gap-3">
          <li v-for="b in bars" :key="b.key" class="flex items-center gap-3 text-sm">
            <span class="w-32 shrink-0 truncate"><span aria-hidden="true">{{ b.emoji }}</span> {{ b.label }}</span>
            <span class="h-2.5 flex-1 overflow-hidden rounded-full bg-surface-2">
              <span class="block h-full rounded-full bg-gradient-to-r from-accent to-accent-2 transition-all duration-700" :style="{ width: `${b.pct}%` }" />
            </span>
            <span class="w-6 text-right tabular-nums text-muted">{{ b.n }}</span>
          </li>
        </ul>
      </div>
    </template>

    <div v-else class="mt-8 grid grid-cols-7 gap-2">
      <div v-for="n in 7" :key="n" class="skeleton h-36 rounded-2xl" />
    </div>
  </section>
</template>
