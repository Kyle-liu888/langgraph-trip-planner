import { describe, expect, it } from 'vitest'
import { eventText } from './progressText'

describe('model progress feedback', () => {
  it('shows the backend reason for a timeout instead of only an event identifier', () => {
    const text = eventText({ type: 'model.failed', label: '模型请求超时',
      error_type: 'ModelRequestTimeout', sequence: 1, timestamp: '', run_id: 'run' })
    expect(text).toContain('模型请求超时')
    expect(text).not.toContain('model.failed')
  })
  it('does not describe waiting as generated content', () => {
    expect(eventText({ type: 'model.waiting', label: '请求仍在等待模型响应',
      sequence: 2, timestamp: '', run_id: 'run' })).toBe('等待模型 · 请求仍在等待模型响应')
  })
})
