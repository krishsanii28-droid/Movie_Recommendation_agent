<script setup lang="ts">
import { useToast } from '../composables/useToast'

const { toasts } = useToast()
</script>

<template>
  <div class="pointer-events-none fixed inset-x-0 bottom-4 z-50 flex flex-col items-center gap-2 px-4" aria-live="polite" role="status">
    <TransitionGroup name="fade">
      <div
        v-for="t in toasts"
        :key="t.id"
        class="pointer-events-auto rounded-full border border-line bg-surface px-4 py-2 text-sm shadow-card"
        :class="{ 'text-ok': t.tone === 'success', 'text-accent-2': t.tone === 'error' }"
      >
        {{ t.text }}
      </div>
    </TransitionGroup>
  </div>
</template>
