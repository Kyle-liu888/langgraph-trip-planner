import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { authRequest, clearSession, localSession, refreshSession, replaceSession } from '@/services/auth'

export const useAuth = defineStore('auth', () => {
  const session = localSession
  const user = computed(() => session.value?.user ?? null)
  const error = ref('')
  let initialization: Promise<void> | undefined
  const channel = typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel('trip-auth') : null
  function expire() { clearSession(); initialization = undefined }
  async function refresh() {
    try { await refreshSession(); error.value = '' }
    catch (e) { expire(); error.value = (e as Error).message }
  }
  if (channel) channel.onmessage = () => { expire(); void refresh() }
  if (typeof window !== 'undefined') window.addEventListener('focus', () => { void refresh() })
  function init() { return initialization ??= refresh() }
  async function authenticate(credentials: { email: string; password: string }, register: boolean) {
    await refreshSession()
    replaceSession(await authRequest(register ? 'register' : 'login', credentials))
    error.value = ''
    channel?.postMessage('changed') // Never broadcast tokens or user records.
  }
  async function signOut() {
    await authRequest('logout', {})
    expire()
    channel?.postMessage('changed')
  }
  return { session, user, error, init, signOut, authenticate, expire }
})
