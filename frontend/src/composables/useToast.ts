import { ref } from 'vue'

export interface Toast {
  id: number
  text: string
  tone: 'info' | 'success' | 'error'
}

const toasts = ref<Toast[]>([])
let next = 1

export function useToast() {
  function show(text: string, tone: Toast['tone'] = 'info', ms = 2600) {
    const id = next++
    toasts.value.push({ id, text, tone })
    setTimeout(() => {
      toasts.value = toasts.value.filter((t) => t.id !== id)
    }, ms)
  }
  return { toasts, show }
}
