<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useChatStore } from '../stores/chat'
import { useWatchlistStore } from '../stores/watchlist'
import ThemeToggle from './ThemeToggle.vue'

const chat = useChatStore()
const watchlist = useWatchlistStore()
const route = useRoute()

const links = [
  { to: '/', label: 'Discover', icon: '✨' },
  { to: '/watchlist', label: 'Watchlist', icon: '🔖' },
  { to: '/moods', label: 'My moods', icon: '📅' },
]

function home() {
  if (route.path === '/' && chat.started) chat.reset()
}
</script>

<template>
  <header class="sticky top-0 z-30 border-b border-line bg-bg/75 backdrop-blur-xl">
    <div class="mx-auto flex h-16 max-w-6xl items-center gap-3 px-4 sm:px-6">
      <RouterLink to="/" class="group flex items-center gap-2.5" aria-label="MoodReel home — start over" @click="home">
        <span class="grid h-9 w-9 place-items-center rounded-full bg-gradient-to-br from-accent to-accent-2 shadow-card transition group-hover:rotate-45">
          <svg viewBox="0 0 24 24" class="h-5 w-5" aria-hidden="true">
            <circle cx="12" cy="12" r="2.2" fill="var(--bg)" />
            <circle cx="12" cy="5.5" r="2.4" fill="var(--bg)" />
            <circle cx="12" cy="18.5" r="2.4" fill="var(--bg)" />
            <circle cx="5.5" cy="12" r="2.4" fill="var(--bg)" />
            <circle cx="18.5" cy="12" r="2.4" fill="var(--bg)" />
          </svg>
        </span>
        <span class="font-display text-xl font-semibold tracking-tight">Mood<span class="text-accent">Reel</span></span>
      </RouterLink>

      <nav aria-label="Main" class="ml-auto flex items-center gap-1">
        <RouterLink
          v-for="l in links"
          :key="l.to"
          :to="l.to"
          class="relative rounded-full px-3 py-2 text-sm text-muted transition hover:text-ink"
          active-class="!text-ink bg-surface-2"
          exact-active-class="!text-ink bg-surface-2"
        >
          <span aria-hidden="true" class="sm:hidden">{{ l.icon }}</span>
          <span class="sr-only sm:not-sr-only">{{ l.label }}</span>
          <span
            v-if="l.to === '/watchlist' && watchlist.entries.length"
            class="absolute -right-0.5 -top-0.5 grid h-4 min-w-4 place-items-center rounded-full bg-accent px-1 text-[10px] font-bold text-[#1b1206]"
          >{{ watchlist.entries.length }}</span>
        </RouterLink>
        <ThemeToggle />
      </nav>
    </div>
  </header>
</template>
