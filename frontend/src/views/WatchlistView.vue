<script setup lang="ts">
import { onMounted } from 'vue'
import { useToast } from '../composables/useToast'
import { useWatchlistStore } from '../stores/watchlist'
import PosterArt from '../components/PosterArt.vue'
import ProviderBadges from '../components/ProviderBadges.vue'
import { runtime } from '../utils/format'

const watchlist = useWatchlistStore()
const toast = useToast()

onMounted(() => watchlist.load().catch(() => toast.show("Couldn't load your watchlist", 'error')))
</script>

<template>
  <section class="py-10" aria-labelledby="wl-title">
    <p class="eyebrow">Saved for later</p>
    <h1 id="wl-title" class="mt-2 font-display text-4xl font-semibold tracking-tight">Your watchlist</h1>

    <div v-if="watchlist.loading && !watchlist.entries.length" class="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
      <div v-for="n in 5" :key="n" class="skeleton aspect-[2/3] rounded-xl" />
    </div>

    <div v-else-if="!watchlist.entries.length" class="card mt-8 flex flex-col items-center gap-3 p-10 text-center">
      <span class="text-4xl" aria-hidden="true">🍿</span>
      <p class="font-display text-xl">Nothing saved yet</p>
      <p class="max-w-sm text-sm text-muted">Tap “+ Watchlist” on any recommendation and it'll wait for you here.</p>
      <RouterLink to="/" class="btn-primary mt-2">Find something to watch</RouterLink>
    </div>

    <TransitionGroup v-else name="list" tag="ul" appear class="mt-8 grid grid-cols-2 gap-x-4 gap-y-6 sm:grid-cols-3 lg:grid-cols-5">
      <li v-for="(e, i) in watchlist.entries" :key="e.movie_id" :style="{ '--i': i }" class="group flex flex-col">
        <PosterArt :movie="e.movie" />
        <h2 class="mt-2 font-display text-base font-semibold leading-snug">{{ e.movie.title }}</h2>
        <p class="text-xs text-muted">{{ e.movie.year }} · {{ e.movie.language_name }} · {{ runtime(e.movie.runtime) }}</p>
        <div class="mt-1.5"><ProviderBadges :providers="e.movie.providers" :max="2" /></div>
        <div class="mt-2 flex gap-3 text-xs">
          <a v-if="e.movie.providers.link" :href="e.movie.providers.link" target="_blank" rel="noopener" class="font-medium text-accent hover:underline">Where to watch ↗</a>
          <button type="button" class="text-muted hover:text-ink" @click="watchlist.toggle(e.movie)">Remove</button>
        </div>
      </li>
    </TransitionGroup>
  </section>
</template>
