export function runtime(minutes: number | null | undefined): string {
  if (!minutes) return ''
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return h ? `${h}h ${m.toString().padStart(2, '0')}m` : `${m}m`
}

/** Deterministic pleasant gradient for a title (used when there's no poster). */
export function posterGradient(seed: string): string {
  let h = 0
  for (const ch of seed) h = (h * 31 + ch.charCodeAt(0)) >>> 0
  const hue = h % 360
  const hue2 = (hue + 40 + (h % 60)) % 360
  return `linear-gradient(160deg, hsl(${hue} 55% 32%) 0%, hsl(${hue2} 60% 18%) 55%, hsl(${hue2} 50% 9%) 100%)`
}

export function greeting(date = new Date()): { text: string; emoji: string } {
  const hr = date.getHours()
  if (hr < 5) return { text: 'Up late', emoji: '🌙' }
  if (hr < 12) return { text: 'Good morning', emoji: '☀️' }
  if (hr < 17) return { text: 'Good afternoon', emoji: '🌤️' }
  if (hr < 21) return { text: 'Good evening', emoji: '🌆' }
  return { text: 'Hey, night owl', emoji: '🌙' }
}

export function uid(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID()
  return Math.random().toString(36).slice(2) + Date.now().toString(36)
}

export const LANGUAGES = [
  { code: 'ml', name: 'Malayalam' },
  { code: 'hi', name: 'Hindi' },
  { code: 'ta', name: 'Tamil' },
  { code: 'te', name: 'Telugu' },
  { code: 'en', name: 'English' },
]
