<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Movie } from '../api/types'
import { posterGradient } from '../utils/format'

const props = defineProps<{ movie: Movie }>()
const failed = ref(false)
const bg = computed(() => posterGradient(props.movie.title))
</script>

<template>
  <div class="relative aspect-[2/3] w-full overflow-hidden rounded-xl bg-surface-2">
    <img
      v-if="movie.poster_url && !failed"
      :src="movie.poster_url"
      :alt="`Poster for ${movie.title} (${movie.year ?? 'n/a'})`"
      loading="lazy"
      class="h-full w-full object-cover"
      @error="failed = true"
    />
    <div
      v-else
      role="img"
      :aria-label="`Poster for ${movie.title} (${movie.year ?? 'n/a'})`"
      class="flex h-full w-full flex-col justify-between p-2.5 text-white"
      :style="{ background: bg }"
    >
      <!-- film perforations -->
      <div class="flex justify-between opacity-40" aria-hidden="true">
        <span v-for="n in 5" :key="n" class="h-1.5 w-2 rounded-sm bg-white/80" />
      </div>
      <div>
        <p class="font-display text-[15px] font-semibold leading-tight [text-wrap:balance] drop-shadow sm:text-lg">{{ movie.title }}</p>
        <p class="mt-1 text-[10px] uppercase tracking-widest text-white/70">{{ movie.language_name }} · {{ movie.year }}</p>
      </div>
      <div class="flex justify-between opacity-40" aria-hidden="true">
        <span v-for="n in 5" :key="n" class="h-1.5 w-2 rounded-sm bg-white/80" />
      </div>
    </div>
  </div>
</template>
