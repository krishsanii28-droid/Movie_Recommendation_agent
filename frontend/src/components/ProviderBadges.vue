<script setup lang="ts">
import type { WatchProviders } from '../api/types'

defineProps<{ providers: WatchProviders; max?: number }>()
</script>

<template>
  <div class="flex flex-wrap items-center gap-1.5">
    <template v-if="providers.stream.length">
      <span
        v-for="p in providers.stream.slice(0, max ?? 3)"
        :key="p.name"
        class="inline-flex items-center gap-1.5 rounded-md border border-line bg-surface-2 px-2 py-0.5 text-xs font-medium"
      >
        <img v-if="p.logo_url" :src="p.logo_url" :alt="''" class="h-4 w-4 rounded" loading="lazy" />
        <span aria-hidden="true" v-else class="text-[10px]">▶</span>
        {{ p.name }}
      </span>
    </template>
    <span v-else-if="providers.rent.length || providers.buy.length" class="text-xs text-muted">Rent or buy</span>
    <span v-else class="text-xs text-muted">Not streaming in India right now</span>
  </div>
</template>
