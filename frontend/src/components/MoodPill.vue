<script setup lang="ts">
import { computed } from 'vue'
import type { MoodProfile } from '../api/types'

const props = defineProps<{ mood: MoodProfile }>()

const EMOJI: Record<string, string> = {
  tired: '😴', stressed: '😤', anxious: '😟', lonely: '🫂', heartbroken: '💔', sad: '😔', angry: '😠',
  scared: '😨', bored: '🥱', curious: '🤯', nostalgic: '🌅', romantic: '💞', excited: '🎉', happy: '😄',
  calm: '😌', neutral: '🎬',
}
const emoji = computed(() => EMOJI[props.mood.primary] ?? '🎬')
const langs = computed(() => props.mood.context.languages.map((l) => l.toUpperCase()).join(' · '))
const AVOID: Record<string, string> = {
  horror: 'no horror', violence: 'no violence', heavy: 'nothing heavy', 'tone:romantic': 'nothing cheesy',
  'tone:slow-burn': 'nothing slow', 'tone:musical': 'no song breaks', 'tone:intense': 'nothing intense',
}
const avoid = computed(() => props.mood.context.avoid.map((a) => AVOID[a]).filter(Boolean))
</script>

<template>
  <div class="inline-flex max-w-full flex-wrap items-center gap-x-2 gap-y-1 rounded-2xl border border-line bg-surface-2/70 px-3 py-1.5 text-xs text-muted">
    <span aria-hidden="true" class="text-sm">{{ emoji }}</span>
    <span class="sr-only">What I understood:</span>
    <span class="font-medium text-ink">{{ mood.summary }}</span>
    <span v-if="langs" class="rounded-full bg-surface px-2 py-0.5">{{ langs }}</span>
    <span v-if="mood.context.time_available" class="rounded-full bg-surface px-2 py-0.5">≤ {{ mood.context.time_available }} min</span>
    <span v-for="a in avoid" :key="a" class="rounded-full bg-surface px-2 py-0.5">{{ a }}</span>
  </div>
</template>
