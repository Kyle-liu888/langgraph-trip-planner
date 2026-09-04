import { describe, it, expect, vi, beforeEach } from 'vitest'
import { appendEvent, subscribeProgress } from './progress'
import type { ProgressEvent } from './trips'
import { fetchEventSource } from '@microsoft/fetch-event-source'

vi.mock('@microsoft/fetch-event-source', () => ({ fetchEventSource: vi.fn() }))
vi.mock('./api', () => ({ API_BASE_URL: '' }))
vi.mock('./supabase', () => ({ accessToken: vi.fn(async () => 'test-token'), supabase: { auth: { refreshSession: vi.fn() } } }))

const event = (sequence: number): ProgressEvent => ({ sequence, type: 'node.started', timestamp: '2026-09-04T00:00:00Z', run_id: 'run' })

describe('durable progress subscription', () => {
  beforeEach(() => { vi.clearAllMocks(); vi.useRealTimers() })
  it('deduplicates replayed events and bounds memory', () => {
    const initial = [event(1)]
    expect(appendEvent(initial, event(1))).toBe(initial)
    const rows = Array.from({ length: 200 }, (_, index) => event(index + 1))
    const result = appendEvent(rows, event(201))
    expect(result).toHaveLength(200)
    expect(result[0].sequence).toBe(2)
  })
  it('uses bearer auth and finishes only on stream.closed', async () => {
    vi.mocked(fetchEventSource).mockImplementation(async (_url, options) => {
      expect(options!.headers).toMatchObject({ Authorization: 'Bearer test-token', 'Last-Event-ID': '0' })
      await options!.onopen!(new Response('', { headers: { 'content-type': 'text/event-stream' } }))
      options!.onmessage!({ id: '1', event: 'node.started', data: JSON.stringify(event(1)) })
      options!.onmessage!({ id: '1', event: 'node.started', data: JSON.stringify(event(1)) })
      options!.onmessage!({ id: '', event: 'stream.closed', data: '{}' })
      options!.onclose!()
    })
    const receive = vi.fn()
    await subscribeProgress('trip', new AbortController().signal, receive, vi.fn())
    expect(receive).toHaveBeenCalledTimes(1)
  })
  it('reconnects with Last-Event-ID without submitting a new trip', async () => {
    vi.useFakeTimers()
    vi.mocked(fetchEventSource).mockImplementationOnce(async (_url, options) => {
      options!.onmessage!({ id: '5', event: 'node.started', data: JSON.stringify(event(5)) })
      throw new Error('network disconnected')
    }).mockImplementationOnce(async (url, options) => {
      expect(url).toBe('/api/trips/trip/events')
      expect(options!.method).toBe('GET')
      expect(options!.headers).toMatchObject({ 'Last-Event-ID': '5' })
      options!.onmessage!({ id: '', event: 'stream.closed', data: '{}' })
    })
    const running = subscribeProgress('trip', new AbortController().signal, vi.fn(), vi.fn())
    await vi.advanceTimersByTimeAsync(2000)
    await running
    expect(fetchEventSource).toHaveBeenCalledTimes(2)
    vi.useRealTimers()
  })
  it('stops on forbidden or missing trip instead of retrying forever', async () => {
    vi.mocked(fetchEventSource).mockImplementation(async (_url, options) => {
      await options!.onopen!(new Response('', { status: 404 }))
    })
    await expect(subscribeProgress('trip', new AbortController().signal, vi.fn(), vi.fn())).rejects.toThrow('无法订阅')
    expect(fetchEventSource).toHaveBeenCalledTimes(1)
  })
})
