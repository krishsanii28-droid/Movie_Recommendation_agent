<script setup lang="ts">
import { computed, ref } from 'vue'
import type { FeedbackSignal, Recommendation } from '../api/types'
import { useToast } from '../composables/useToast'
import { useChatStore } from '../stores/chat'
import { useWatchlistStore } from '../stores/watchlist'
import { runtime } from '../utils/format'
import PosterArt from './PosterArt.vue'
import ProviderBadges from './ProviderBadges.vue'

const props = defineProps<{ rec: Recommendation; index?: number }>()
const chat = useChatStore()
const watchlist = useWatchlistStore()
const toast = useToast()

const showWhy = ref(false)
const showWhere = ref(false)
const showNotForMe = ref(false)
const movie = computed(() => props.rec.movie)
const reaction = computed(() => chat.reactions[movie.value.id])
const inWatchlist = computed(() => watchlist.ids.has(movie.value.id))
const dismissed = computed(() => ['disliked', 'too_slow', 'too_heavy'].includes(reaction.value ?? ''))
const uid = `m${props.rec.movie.id}-${props.index ?? 0}`

const SLOT: Record<string, { icon: string; cls: string }> = {
  'Safe pick': { icon: '🛡️', cls: 'text-ok' },
  'Top pick': { icon: '⭐', cls: 'text-accent' },
  'Hidden gem': { icon: '💎', cls: 'text-[#7cc4ff]' },
  Wildcard: { icon: '🃏', cls: 'text-accent-2' },
  'Also great': { icon: '✨', cls: 'text-accent' },
}
const slot = computed(() => SLOT[props.rec.slot] ?? { icon: '🎬', cls: 'text-accent' })

const MESSAGES: Record<FeedbackSignal, string> = {
  loved: "Noted — I'll find more like this 💛",
  disliked: "Got it — I'll steer away from films like this.",
  seen: "Marked as seen. I won't suggest it again.",
  too_slow: "Too slow — I'll keep things pacier for you.",
  too_heavy: "Too heavy — I'll keep it lighter next time.",
}

async function react(signal: FeedbackSignal) {
  showNotForMe.value = false
  try {
    await chat.react(movie.value.id, signal)
    toast.show(MESSAGES[signal], 'success')
  } catch {
    toast.show("Couldn't save that — try again?", 'error')
  }
}

async function toggleWatchlist() {
  try {
    const added = await watchlist.toggle(movie.value)
    toast.show(added ? `Added ${movie.value.title} to your watchlist` : 'Removed from watchlist', 'success')
  } catch {
    toast.show("Couldn't update your watchlist", 'error')
  }
}
</script>

<template>
  <article
    class="card group relative flex gap-3 p-3 transition duration-300 hover:-translate-y-0.5 hover:border-accent/40 sm:gap-4 sm:p-4"
    :class="{ 'opacity-55 saturate-50': dismissed }"
    :aria-labelledby="`${uid}-title`"
  >
    <div class="w-24 shrink-0 sm:w-32">
      <PosterArt :movie="movie" />
    </div>

    <div class="flex min-w-0 flex-1 flex-col">
      <p class="eyebrow flex items-center gap-1.5" :class="slot.cls">
        <span aria-hidden="true">{{ slot.icon }}</span>{{ rec.slot }}
      </p>
      <h3 :id="`${uid}-title`" class="mt-1 font-display text-lg font-semibold leading-snug sm:text-xl">
        {{ movie.title }}
      </h3>
      <p class="mt-0.5 flex flex-wrap gap-x-2 text-xs text-muted">
        <span>{{ movie.year }}</span><span aria-hidden="true">·</span>
        <span>{{ movie.language_name }}</span>
        <template v-if="movie.runtime"><span aria-hidden="true">·</span><span>{{ runtime(movie.runtime) }}</span></template>
        <span aria-hidden="true">·</span>
        <span><span aria-hidden="true" class="text-accent">★</span><span class="sr-only">Rating</span> {{ movie.rating.toFixed(1) }}</span>
      </p>

      <p class="mt-2 text-[15px] leading-relaxed">{{ rec.reason }}</p>

      <div class="mt-2.5"><ProviderBadges :providers="movie.providers" /></div>

      <!-- actions -->
      <div class="mt-3 flex flex-wrap items-center gap-1.5" role="group" :aria-label="`Actions for ${movie.title}`">
        <button type="button" class="btn-ghost !px-3 !py-1.5 !text-xs" :aria-expanded="showWhere" :aria-controls="`${uid}-where`" @click="showWhere = !showWhere">
          <span aria-hidden="true">▶</span> Where to watch
        </button>
        <button type="button" class="btn-ghost !px-2.5 !py-1.5 !text-xs" :aria-pressed="reaction === 'loved'" :class="reaction === 'loved' ? '!border-ok !text-ok' : ''" @click="react('loved')">
          <span aria-hidden="true">👍</span><span class="hidden sm:inline">Love it</span><span class="sm:hidden sr-only">Love it</span>
        </button>
        <button type="button" class="btn-ghost !px-2.5 !py-1.5 !text-xs" :aria-expanded="showNotForMe" :aria-pressed="dismissed" @click="showNotForMe = !showNotForMe">
          <span aria-hidden="true">👎</span><span class="hidden sm:inline">Not for me</span><span class="sm:hidden sr-only">Not for me</span>
        </button>
        <button type="button" class="btn-ghost !px-2.5 !py-1.5 !text-xs" :aria-pressed="reaction === 'seen'" :class="reaction === 'seen' ? '!border-accent' : ''" @click="react('seen')">
          <span aria-hidden="true">✓</span><span class="hidden sm:inline">Seen it</span><span class="sm:hidden sr-only">Seen it</span>
        </button>
        <button type="button" class="btn-ghost !px-2.5 !py-1.5 !text-xs" :aria-pressed="inWatchlist" :class="inWatchlist ? '!border-accent !bg-accent-soft' : ''" @click="toggleWatchlist">
          <span aria-hidden="true">{{ inWatchlist ? '🔖' : '+' }}</span>{{ inWatchlist ? 'Saved' : 'Watchlist' }}
        </button>
      </div>

      <Transition name="fade">
        <div v-if="showNotForMe" class="mt-2 flex flex-wrap items-center gap-1.5 text-xs">
          <span class="text-muted">What was off?</span>
          <button type="button" class="chip !px-2.5 !py-1 !text-xs" @click="react('too_slow')">🐢 Too slow</button>
          <button type="button" class="chip !px-2.5 !py-1 !text-xs" @click="react('too_heavy')">🪨 Too heavy</button>
          <button type="button" class="chip !px-2.5 !py-1 !text-xs" @click="react('disliked')">🙅 Just not my thing</button>
        </div>
      </Transition>

      <Transition name="fade">
        <div v-if="showWhere" :id="`${uid}-where`" class="mt-2 rounded-xl bg-surface-2 p-3 text-sm">
          <p v-if="movie.providers.stream.length">
            Streaming in India on <strong>{{ movie.providers.stream.map((p) => p.name).join(', ') }}</strong>.
          </p>
          <p v-if="movie.providers.rent.length" class="text-muted">Rent: {{ movie.providers.rent.map((p) => p.name).join(', ') }}</p>
          <p v-if="movie.providers.indicative" class="mt-1 text-xs text-muted">Availability changes often — double-check before you settle in.</p>
          <a v-if="movie.providers.link" :href="movie.providers.link" target="_blank" rel="noopener" class="mt-2 inline-flex items-center gap-1 text-accent underline-offset-2 hover:underline">
            See all options on JustWatch <span aria-hidden="true">↗</span>
          </a>
        </div>
      </Transition>

      <button
        type="button"
        class="mt-2 self-start text-xs font-medium text-muted underline decoration-dotted underline-offset-4 hover:text-ink"
        :aria-expanded="showWhy"
        :aria-controls="`${uid}-why`"
        @click="showWhy = !showWhy"
      >
        {{ showWhy ? 'Hide reasoning' : 'Why this?' }}
      </button>
      <Transition name="fade">
        <div v-if="showWhy" :id="`${uid}-why`" class="mt-2 rounded-xl border border-dashed border-line p-3 text-xs text-muted">
          <p v-if="rec.why.matched_tones.length" class="flex flex-wrap items-center gap-1">
            <span>Matches your mood:</span>
            <span v-for="t in rec.why.matched_tones" :key="t" class="rounded-full bg-accent-soft px-2 py-0.5 text-ink">{{ t }}</span>
          </p>
          <p class="mt-1.5">Mood goal: <strong class="text-ink">{{ { stay: 'lean into the feeling', shift: 'lift the mood', unclear: 'keep it balanced' }[rec.why.mood_goal] ?? rec.why.mood_goal }}</strong></p>
          <ul class="mt-1.5 list-inside list-disc space-y-0.5">
            <li v-for="n in rec.why.notes" :key="n">{{ n }}</li>
          </ul>
          <div class="mt-2 flex items-center gap-2">
            <span>Fit</span>
            <span class="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-2">
              <span class="block h-full rounded-full bg-gradient-to-r from-accent to-accent-2" :style="{ width: `${Math.min(100, Math.max(8, rec.why.score * 90))}%` }" />
            </span>
          </div>
        </div>
      </Transition>
    </div>
  </article>
</template>
