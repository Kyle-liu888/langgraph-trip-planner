import { ref } from 'vue'

export interface LocalSession {
  user: { id: string; email: string; email_verified: false } | null
  csrf_token: string
}
export const localSession = ref<LocalSession | null>(null)
let sessionVersion = 0
export function replaceSession(value: LocalSession | null) {
  sessionVersion++
  localSession.value = value
}
export function clearSession() { replaceSession(null) }
const base = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/$/, '')

export async function authRequest(path: string, body?: object): Promise<LocalSession | null> {
  const response = await fetch(`${base}/api/auth/${path}`, {
    method: body ? 'POST' : 'GET', credentials: 'include',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': localSession.value?.csrf_token || '' },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(15000)
  })
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail?.message || '无法连接本地登录服务，请检查后端日志')
  }
  return response.status === 204 ? null : response.json()
}

export async function refreshSession() {
  const version = sessionVersion
  const value = await authRequest('session')
  if (version === sessionVersion) replaceSession(value)
}
