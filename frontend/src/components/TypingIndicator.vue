<script setup lang="ts">
defineProps<{ status?: string }>()
</script>

<template>
  <div class="flex items-center gap-3 text-sm text-muted">
    <span class="flex gap-1" aria-hidden="true">
      <span class="dot h-2 w-2 rounded-full bg-accent" />
      <span class="dot h-2 w-2 rounded-full bg-accent" style="animation-delay: 0.15s" />
      <span class="dot h-2 w-2 rounded-full bg-accent" style="animation-delay: 0.3s" />
    </span>
    <span>{{ status || 'Thinking…' }}</span>
  </div>
</template>
