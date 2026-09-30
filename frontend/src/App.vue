<script setup lang="ts">
import AppFooter from './components/AppFooter.vue'
import AppHeader from './components/AppHeader.vue'
import ToastHost from './components/ToastHost.vue'
</script>

<template>
  <a href="#main" class="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 btn-primary">Skip to content</a>
  <div class="flex min-h-dvh flex-col">
    <AppHeader />
    <main id="main" class="mx-auto w-full max-w-6xl flex-1 px-4 sm:px-6">
      <RouterView />
    </main>
    <AppFooter />
  </div>
  <ToastHost />
</template>
