<script setup lang="ts">
import { useUserStore } from '../stores/user'

const user = useUserStore()
</script>

<template>
  <button
    type="button"
    class="ml-1 grid h-9 w-9 place-items-center rounded-full border border-line text-lg transition hover:bg-surface-2"
    :aria-label="user.theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'"
    :title="user.theme === 'dark' ? 'Light theme' : 'Dark theme'"
    @click="user.toggleTheme()"
  >
    <span aria-hidden="true">{{ user.theme === 'dark' ? '☀️' : '🌙' }}</span>
  </button>
</template>
