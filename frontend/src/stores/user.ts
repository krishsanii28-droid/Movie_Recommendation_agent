import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { uid } from '../utils/format'
import { load, save } from '../utils/storage'

export const useUserStore = defineStore('user', () => {
  const userId = ref<string>(load('mr-user', '') || uid())
  save('mr-user', userId.value)

  const theme = ref<'dark' | 'light'>(
    (() => {
      try {
        return localStorage.getItem('mr-theme') === 'light' ? 'light' : 'dark'
      } catch {
        return 'dark'
      }
    })(),
  )
  const languages = ref<string[]>(load('mr-langs', []))
  /** null = "auto" (let the agent infer it) */
  const energy = ref<number | null>(null)
  const moodShift = ref<number | null>(null)

  watch(languages, (v) => save('mr-langs', v), { deep: true })
  watch(
    theme,
    (t) => {
      document.documentElement.classList.toggle('dark', t === 'dark')
      try {
        localStorage.setItem('mr-theme', t)
      } catch {
        /* ignore */
      }
      document.querySelector('meta[name="theme-color"]')?.setAttribute('content', t === 'dark' ? '#0b0a10' : '#f7f3ec')
    },
    { immediate: true },
  )

  function toggleTheme() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
  }

  function toggleLanguage(code: string | null) {
    if (code === null) languages.value = []
    else if (languages.value.includes(code)) languages.value = languages.value.filter((c) => c !== code)
    else languages.value = [...languages.value, code]
  }

  return { userId, theme, languages, energy, moodShift, toggleTheme, toggleLanguage }
})
