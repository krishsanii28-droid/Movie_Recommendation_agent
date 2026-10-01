<script setup lang="ts">
import { computed } from 'vue'
import { useUserStore } from '../stores/user'

const user = useUserStore()

const energy = computed({
  get: () => user.energy ?? 0.5,
  set: (v: number) => (user.energy = Number(v)),
})
const shift = computed({
  get: () => user.moodShift ?? 0,
  set: (v: number) => (user.moodShift = Number(v)),
})
const energyLabel = computed(() =>
  user.energy === null ? 'Auto' : user.energy < 0.34 ? 'Low' : user.energy > 0.66 ? 'High' : 'Medium',
)
const shiftLabel = computed(() =>
  user.moodShift === null
    ? 'Auto'
    : user.moodShift < -0.33
      ? 'Stay in it'
      : user.moodShift > 0.33
        ? 'Change it'
        : 'Either way',
)
</script>

<template>
  <div class="grid gap-5 sm:grid-cols-2">
    <div>
      <div class="mb-2 flex items-center justify-between text-sm">
        <label for="energy" class="font-medium">Energy</label>
        <span class="flex items-center gap-2">
          <span class="rounded-full bg-surface-2 px-2 py-0.5 text-xs text-muted">{{ energyLabel }}</span>
          <button v-if="user.energy !== null" type="button" class="text-xs text-muted underline hover:text-ink" @click="user.energy = null">reset</button>
        </span>
      </div>
      <input id="energy" v-model="energy" type="range" min="0" max="1" step="0.01" :style="{ '--fill': `${energy * 100}%` }" aria-describedby="energy-hint" />
      <div id="energy-hint" class="mt-1.5 flex justify-between text-xs text-muted"><span>😴 Couch mode</span><span>⚡ Bring it on</span></div>
    </div>
    <div>
      <div class="mb-2 flex items-center justify-between text-sm">
        <label for="shift" class="font-medium">Mood goal</label>
        <span class="flex items-center gap-2">
          <span class="rounded-full bg-surface-2 px-2 py-0.5 text-xs text-muted">{{ shiftLabel }}</span>
          <button v-if="user.moodShift !== null" type="button" class="text-xs text-muted underline hover:text-ink" @click="user.moodShift = null">reset</button>
        </span>
      </div>
      <input id="shift" v-model="shift" type="range" min="-1" max="1" step="0.01" :style="{ '--fill': `${((shift + 1) / 2) * 100}%` }" aria-describedby="shift-hint" />
      <div id="shift-hint" class="mt-1.5 flex justify-between text-xs text-muted"><span>🫶 Stay in my mood</span><span>🌈 Change my mood</span></div>
    </div>
  </div>
</template>
