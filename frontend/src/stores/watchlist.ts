import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '../api/client'
import type { Movie, WatchlistEntry } from '../api/types'
import { useUserStore } from './user'

export const useWatchlistStore = defineStore('watchlist', () => {
  const entries = ref<WatchlistEntry[]>([])
  const loaded = ref(false)
  const loading = ref(false)
  const ids = computed(() => new Set(entries.value.map((e) => e.movie_id)))

  async function load() {
    const user = useUserStore()
    loading.value = true
    try {
      entries.value = await api.watchlist(user.userId)
      loaded.value = true
    } finally {
      loading.value = false
    }
  }

  async function toggle(movie: Movie): Promise<boolean> {
    const user = useUserStore()
    if (ids.value.has(movie.id)) {
      const before = entries.value
      entries.value = entries.value.filter((e) => e.movie_id !== movie.id)
      try {
        await api.removeFromWatchlist(user.userId, movie.id)
      } catch (e) {
        entries.value = before
        throw e
      }
      return false
    }
    entries.value = [{ movie_id: movie.id, note: '', added_at: new Date().toISOString(), movie }, ...entries.value]
    try {
      await api.addToWatchlist(user.userId, movie.id)
    } catch (e) {
      entries.value = entries.value.filter((x) => x.movie_id !== movie.id)
      throw e
    }
    return true
  }

  return { entries, loaded, loading, ids, load, toggle }
})
