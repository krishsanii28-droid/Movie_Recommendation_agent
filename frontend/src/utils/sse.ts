/**
 * Minimal Server-Sent Events parser for fetch() streams (EventSource can't POST).
 * Feed it text chunks; it returns complete `data:` payloads as they arrive.
 */
export function createSSEParser() {
  let buffer = ''
  return function push(chunk: string): string[] {
    buffer += chunk.replace(/\r\n/g, '\n')
    const out: string[] = []
    let idx: number
    while ((idx = buffer.indexOf('\n\n')) !== -1) {
      const block = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 2)
      const data = block
        .split('\n')
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.slice(5).replace(/^ /, ''))
        .join('\n')
      if (data) out.push(data)
    }
    return out
  }
}

export async function* readSSE<T>(response: Response): AsyncGenerator<T> {
  if (!response.body) return
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  const parse = createSSEParser()
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    for (const data of parse(decoder.decode(value, { stream: true }))) {
      try {
        yield JSON.parse(data) as T
      } catch {
        /* ignore malformed frame */
      }
    }
  }
}
