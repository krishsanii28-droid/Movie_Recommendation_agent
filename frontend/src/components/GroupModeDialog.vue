<script setup lang="ts">
import { nextTick, ref } from 'vue'

const emit = defineEmits<{ submit: [members: { name: string; mood: string }[]] }>()
const dialog = ref<HTMLDialogElement | null>(null)
const members = ref([
  { name: '', mood: '' },
  { name: '', mood: '' },
])
const error = ref('')
const hints = ['exhausted after work', 'want to laugh', 'in the mood for a thriller', 'nothing too long', 'feeling nostalgic']

async function open() {
  error.value = ''
  dialog.value?.showModal()
  await nextTick()
  dialog.value?.querySelector<HTMLInputElement>('input')?.focus()
}
function close() {
  dialog.value?.close()
}
function add() {
  if (members.value.length < 6) members.value.push({ name: '', mood: '' })
}
function remove(i: number) {
  if (members.value.length > 2) members.value.splice(i, 1)
}
function submit() {
  const filled = members.value
    .map((m, i) => ({ name: m.name.trim() || `Friend ${i + 1}`, mood: m.mood.trim() }))
    .filter((m) => m.mood)
  if (filled.length < 2) {
    error.value = 'Add at least two people and how they feel.'
    return
  }
  emit('submit', filled)
  close()
  members.value = [{ name: '', mood: '' }, { name: '', mood: '' }]
}
defineExpose({ open })
</script>

<template>
  <dialog
    ref="dialog"
    aria-labelledby="group-title"
    class="m-auto w-[min(34rem,calc(100vw-2rem))] rounded-3xl border border-line bg-surface p-0 text-ink shadow-card backdrop:bg-black/60 backdrop:backdrop-blur-sm"
    @click.self="close"
  >
    <form class="flex flex-col gap-4 p-5 sm:p-6" @submit.prevent="submit">
      <div>
        <p class="eyebrow">Group mode</p>
        <h2 id="group-title" class="mt-1 font-display text-2xl font-semibold">Who's watching tonight?</h2>
        <p class="mt-1 text-sm text-muted">Tell me how each person feels — I'll blend the moods into picks everyone can enjoy.</p>
      </div>
      <ul class="flex flex-col gap-2.5">
        <li v-for="(m, i) in members" :key="i" class="flex items-center gap-2">
          <label :for="`gm-name-${i}`" class="sr-only">Name {{ i + 1 }}</label>
          <input :id="`gm-name-${i}`" v-model="m.name" :placeholder="`Name ${i + 1}`" maxlength="40" class="w-28 shrink-0 rounded-xl border border-line bg-surface-2 px-3 py-2 text-sm focus:border-accent focus:outline-none" />
          <label :for="`gm-mood-${i}`" class="sr-only">How {{ m.name || `person ${i + 1}` }} feels</label>
          <input :id="`gm-mood-${i}`" v-model="m.mood" :placeholder="hints[i % hints.length]" maxlength="300" class="min-w-0 flex-1 rounded-xl border border-line bg-surface-2 px-3 py-2 text-sm focus:border-accent focus:outline-none" />
          <button type="button" class="grid h-9 w-9 shrink-0 place-items-center rounded-full text-muted hover:bg-surface-2 hover:text-ink disabled:opacity-30" :disabled="members.length <= 2" :aria-label="`Remove person ${i + 1}`" @click="remove(i)">✕</button>
        </li>
      </ul>
      <button v-if="members.length < 6" type="button" class="self-start text-sm font-medium text-accent hover:underline" @click="add">+ Add someone</button>
      <p v-if="error" class="text-sm text-accent-2" role="alert">{{ error }}</p>
      <div class="flex justify-end gap-2">
        <button type="button" class="btn-ghost" @click="close">Cancel</button>
        <button type="submit" class="btn-primary">Blend our moods</button>
      </div>
    </form>
  </dialog>
</template>
