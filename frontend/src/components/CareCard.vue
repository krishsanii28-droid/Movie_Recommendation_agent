<script setup lang="ts">
import type { CareMessage } from '../api/types'

defineProps<{ care: CareMessage }>()

const telHref = (contact: string) => `tel:${(contact.split(' ')[0] ?? contact).replace(/-/g, '')}`
</script>

<template>
  <aside class="card animate-rise border-accent/40 p-4 sm:p-5" aria-label="A note of care">
    <p class="flex gap-3 text-[15px] leading-relaxed">
      <span aria-hidden="true" class="text-xl">💛</span>
      <span>{{ care.text }}</span>
    </p>
    <ul v-if="care.helplines.length" class="mt-3 grid gap-2 sm:grid-cols-2">
      <li v-for="h in care.helplines" :key="h.name" class="rounded-xl bg-surface-2 px-3 py-2 text-sm">
        <span class="block text-xs text-muted">{{ h.name }}</span>
        <a
          v-if="/^[\d\s-]+/.test(h.contact)"
          :href="telHref(h.contact)"
          class="font-semibold text-accent underline-offset-2 hover:underline"
        >{{ h.contact }}</a>
        <a v-else :href="`https://${h.contact}`" target="_blank" rel="noopener" class="font-semibold text-accent underline-offset-2 hover:underline">{{ h.contact }}</a>
      </li>
    </ul>
  </aside>
</template>
