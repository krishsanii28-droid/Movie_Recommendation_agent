<script setup lang="ts">
import { computed } from 'vue'
import type { AssistantItem } from '../stores/chat'
import CareCard from './CareCard.vue'
import MoodPill from './MoodPill.vue'
import MovieCard from './MovieCard.vue'
import MovieCardSkeleton from './MovieCardSkeleton.vue'
import TypingIndicator from './TypingIndicator.vue'

const props = defineProps<{ item: AssistantItem; isLast: boolean }>()
const emit = defineEmits<{ option: [text: string]; retry: [] }>()

const searching = computed(
  () => props.item.streaming && !props.item.question && !props.item.recommendations && props.item.status.startsWith('Finding'),
)
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="flex items-start gap-3">
      <span class="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-gradient-to-br from-accent to-accent-2 text-sm" aria-hidden="true">🎬</span>
      <div class="flex min-w-0 flex-1 flex-col gap-2.5">
        <MoodPill v-if="item.mood && item.kind !== 'surprise'" :mood="item.mood" />
        <div v-if="item.members?.length" class="flex flex-wrap gap-1.5 text-xs">
          <span v-for="m in item.members" :key="m.name" class="rounded-full border border-line px-2.5 py-1 text-muted">
            <strong class="text-ink">{{ m.name }}</strong> · {{ m.mood.summary.split(' · ')[0] }}
          </span>
        </div>
        <CareCard v-if="item.care" :care="item.care" />
        <p v-if="item.text" class="max-w-2xl font-display text-lg leading-snug sm:text-xl">
          {{ item.text }}<span v-if="item.streaming && !item.recommendations && !item.question" class="ml-0.5 inline-block h-5 w-0.5 translate-y-1 animate-pulse bg-accent" aria-hidden="true" />
        </p>
        <TypingIndicator v-else-if="item.streaming" :status="item.status" />
        <div v-if="item.error" class="flex flex-wrap items-center gap-3 rounded-xl border border-accent-2/40 bg-accent-2/10 px-3 py-2 text-sm">
          <span>{{ item.error }}</span>
          <button v-if="isLast" type="button" class="btn-ghost !py-1 !text-xs" @click="emit('retry')">Try again</button>
        </div>
        <div v-if="item.question && item.options?.length && isLast" class="flex flex-wrap gap-2" role="group" aria-label="Quick replies">
          <button v-for="o in item.options" :key="o" type="button" class="chip animate-rise" @click="emit('option', o)">{{ o }}</button>
        </div>
      </div>
    </div>

    <div v-if="searching" class="grid gap-3 lg:grid-cols-2" aria-busy="true" aria-label="Loading recommendations">
      <MovieCardSkeleton v-for="n in 4" :key="n" />
    </div>
    <TransitionGroup v-if="item.recommendations?.length" name="list" tag="div" appear class="grid gap-3 lg:grid-cols-2">
      <MovieCard v-for="(rec, i) in item.recommendations" :key="rec.movie.id" :rec="rec" :index="i" :style="{ '--i': i }" />
    </TransitionGroup>
    <p v-if="item.recommendations && !item.recommendations.length && !item.streaming" class="text-sm text-muted">
      Nothing fit all of that — try loosening the language filter?
    </p>
  </div>
</template>
