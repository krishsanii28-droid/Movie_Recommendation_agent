<script setup lang="ts">
import { useUserStore } from '../stores/user'
import { LANGUAGES } from '../utils/format'

const user = useUserStore()
</script>

<template>
  <div role="group" aria-label="Languages" class="flex flex-wrap items-center gap-1.5">
    <button
      type="button"
      class="rounded-full border px-3 py-1.5 text-xs font-medium transition"
      :class="user.languages.length === 0 ? 'border-accent bg-accent-soft text-ink' : 'border-line text-muted hover:text-ink'"
      :aria-pressed="user.languages.length === 0"
      @click="user.toggleLanguage(null)"
    >
      Any language
    </button>
    <button
      v-for="lang in LANGUAGES"
      :key="lang.code"
      type="button"
      class="rounded-full border px-3 py-1.5 text-xs font-medium transition"
      :class="user.languages.includes(lang.code) ? 'border-accent bg-accent-soft text-ink' : 'border-line text-muted hover:text-ink'"
      :aria-pressed="user.languages.includes(lang.code)"
      @click="user.toggleLanguage(lang.code)"
    >
      {{ lang.name }}
    </button>
  </div>
</template>
