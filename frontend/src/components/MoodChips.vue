<script setup lang="ts">
import type { Chip } from '../api/types'

defineProps<{ chips: Chip[]; disabled?: boolean; compact?: boolean }>()
const emit = defineEmits<{ pick: [chip: Chip] }>()
</script>

<template>
  <ul class="flex flex-wrap gap-2" :class="compact ? '' : 'justify-center'" aria-label="Quick moods">
    <li v-for="(chip, i) in chips" :key="chip.id" class="animate-rise" :style="{ animationDelay: `${i * 50}ms` }">
      <button type="button" class="chip" :disabled="disabled" @click="emit('pick', chip)">
        <span aria-hidden="true" class="text-base">{{ chip.emoji }}</span>
        <span>{{ chip.label }}</span>
      </button>
    </li>
  </ul>
</template>
