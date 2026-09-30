import { describe, expect, it } from 'vitest'
import { createSSEParser } from '../sse'
import { posterGradient, runtime } from '../format'

describe('createSSEParser', () => {
  it('parses events split across chunks', () => {
    const push = createSSEParser()
    expect(push('event: delta\ndata: {"type":"del')).toEqual([])
    expect(push('ta","text":"hi"}\n\nevent: done\ndata: {"type":"done"}\n\n')).toEqual([
      '{"type":"delta","text":"hi"}',
      '{"type":"done"}',
    ])
  })

  it('handles CRLF and ignores comments', () => {
    const push = createSSEParser()
    expect(push(': ping\r\n\r\ndata: 1\r\n\r\n')).toEqual(['1'])
  })
})

describe('format', () => {
  it('formats runtimes', () => {
    expect(runtime(104)).toBe('1h 44m')
    expect(runtime(45)).toBe('45m')
    expect(runtime(null)).toBe('')
  })
  it('makes stable gradients', () => {
    expect(posterGradient('Premalu')).toBe(posterGradient('Premalu'))
    expect(posterGradient('Premalu')).not.toBe(posterGradient('96'))
  })
})
