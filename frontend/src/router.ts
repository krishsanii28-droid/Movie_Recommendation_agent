import { createRouter, createWebHistory } from 'vue-router'
import DiscoverView from './views/DiscoverView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'discover', component: DiscoverView, meta: { title: 'MoodReel — movies for how you feel' } },
    { path: '/watchlist', name: 'watchlist', component: () => import('./views/WatchlistView.vue'), meta: { title: 'Watchlist · MoodReel' } },
    { path: '/moods', name: 'moods', component: () => import('./views/MoodsView.vue'), meta: { title: 'Your moods · MoodReel' } },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

router.afterEach((to) => {
  document.title = (to.meta.title as string) ?? 'MoodReel'
})
