import { fetchEventSource } from '@microsoft/fetch-event-source'
import { API_BASE_URL } from './api'
import { clearSession } from './auth'
import type { ProgressEvent } from './trips'

class FatalStreamError extends Error {}

export function appendEvent(events: ProgressEvent[], incoming: ProgressEvent): ProgressEvent[] {
  if (events.some(event => event.sequence === incoming.sequence)) return events
  return [...events, incoming].slice(-200)
}

/** Reconnect only the subscription. Never re-submit a model job. */
export async function subscribeProgress(id: string, signal: AbortSignal,
  onEvent: (event: ProgressEvent) => void, onStatus: (status: string) => void): Promise<void> {
  let cursor = 0, retries = 0
  while (!signal.aborted) {
    const controller = new AbortController()
    const abort = () => controller.abort()
    signal.addEventListener('abort', abort, { once: true })
    let finished = false, refresh = false
    let lastReceived = Date.now(), timedOut = false
    const watchdog = setInterval(() => {
      if (Date.now() - lastReceived > 90000) { timedOut = true; controller.abort() }
    }, 10000)
    try {
      if (signal.aborted) return
      await fetchEventSource(`${API_BASE_URL}/api/trips/${id}/events`, {
        method: 'GET', signal: controller.signal, openWhenHidden: true, credentials: 'include',
        headers: { 'Last-Event-ID': String(cursor) },
        async onopen(response) {
          lastReceived = Date.now()
          if (response.status === 401) { clearSession(); throw new FatalStreamError('登录已过期，请重新登录') }
          if ([403, 404, 422].includes(response.status)) throw new FatalStreamError('无法订阅此行程，请返回历史列表重试')
          if (!response.ok || !response.headers.get('content-type')?.includes('text/event-stream'))
            throw new Error('进度连接暂不可用')
          retries = 0; onStatus('实时连接已建立')
        },
        onmessage(message) {
          lastReceived = Date.now() // Includes server heartbeat comments.
          if (message.event === 'session.expired') { refresh = true; controller.abort(); return }
          if (message.event === 'stream.closed') { finished = true; return }
          if (message.event === 'trip.deleted') throw new FatalStreamError('该行程已删除')
          if (!message.id || !message.data) return
          const sequence = Number(message.id)
          if (!Number.isSafeInteger(sequence) || sequence <= cursor) return
          const payload = JSON.parse(message.data) as ProgressEvent
          cursor = sequence
          onEvent(payload)
        },
        onclose() { if (!finished) throw new Error('进度连接已断开') },
        onerror(error) { throw error }
      })
      if (finished) { onStatus('执行已结束'); return }
      if (refresh) { clearSession(); throw new FatalStreamError('登录已过期，请重新登录；后台任务不会重新提交') }
      if (timedOut) throw new Error('进度心跳超时')
    } catch (error) {
      if (signal.aborted) return
      if (error instanceof FatalStreamError) throw error
      retries++
      onStatus(`连接中断，正在重连（第 ${retries} 次）；后台规划不会重新提交`)
      await new Promise<void>(resolve => {
        const done = () => { clearTimeout(timer); signal.removeEventListener('abort', done); resolve() }
        const timer = setTimeout(done, Math.min(15000, 1000 * 2 ** Math.min(retries, 4)))
        signal.addEventListener('abort', done, { once: true })
        if (signal.aborted) done()
      })
    } finally { clearInterval(watchdog); signal.removeEventListener('abort', abort) }
  }
}
