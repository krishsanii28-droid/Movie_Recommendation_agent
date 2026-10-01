<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps<{ busy?: boolean; autofocus?: boolean; large?: boolean }>()
const emit = defineEmits<{ send: [text: string] }>()

const text = ref('')
const el = ref<HTMLTextAreaElement | null>(null)
const examples = [
  'Long day, want something cosy…',
  'Heartbroken. Make me laugh.',
  'Bore adikkunnu, comedy venam',
  'Friends over, party mood!',
  'Stressed, only have 90 mins',
  'Something that makes me think',
]
const placeholder = ref(examples[0])
let timer: number | undefined

function resize() {
  if (!el.value) return
  el.value.style.height = 'auto'
  el.value.style.height = Math.min(el.value.scrollHeight, 180) + 'px'
}

function submit() {
  const value = text.value.trim()
  if (!value || props.busy) return
  emit('send', value)
  text.value = ''
  nextTick(resize)
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    submit()
  }
}

watch(text, () => nextTick(resize))
onMounted(() => {
  if (props.autofocus && window.matchMedia('(min-width: 640px)').matches) el.value?.focus()
  let i = 0
  timer = window.setInterval(() => {
    i = (i + 1) % examples.length
    placeholder.value = examples[i]
  }, 3800)
})
onUnmounted(() => window.clearInterval(timer))
defineExpose({ focus: () => el.value?.focus() })
</script>

<template>
  <form
    class="group flex items-end gap-2 rounded-3xl border border-line bg-surface p-2 shadow-card transition focus-within:border-accent/70"
    :class="large ? 'sm:p-3' : ''"
    @submit.prevent="submit"
  >
    <label for="mood-input" class="sr-only">Tell MoodReel how you're feeling</label>
    <textarea
      id="mood-input"
      ref="el"
      v-model="text"
      rows="1"
      :placeholder="placeholder"
      class="max-h-44 min-h-11 min-w-0 flex-1 resize-none bg-transparent px-3 py-2.5 text-ink placeholder:text-muted/80 focus:outline-none focus-visible:outline-none"
      :class="large ? 'text-lg' : 'text-base'"
      maxlength="2000"
      enterkeyhint="send"
      @keydown="onKey"
    />
    <button
      type="submit"
      class="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-accent text-[#1b1206] transition hover:brightness-110 active:scale-95 disabled:opacity-40"
      :disabled="busy || !text.trim()"
      aria-label="Send"
    >
      <svg v-if="!busy" viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" /></svg>
      <span v-else class="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden="true" />
    </button>
  </form>
</template>
