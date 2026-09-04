import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { Session } from '@supabase/supabase-js'
import { supabase } from '@/services/supabase'

export const useAuth = defineStore('auth', () => {
  const session = ref<Session | null>(null)
  const user = computed(() => session.value?.user ?? null)
  const configured = Boolean(supabase)
  let initialization: Promise<void> | undefined
  function init() {
    return initialization ??= (async () => {
      if (!supabase) return
      supabase.auth.onAuthStateChange((_event, value) => { session.value = value })
      const { data, error } = await supabase.auth.getSession()
      if (error) throw new Error('无法读取登录状态，请刷新重试')
      session.value = data.session
    })().catch(error => { initialization = undefined; throw error })
  }
  async function signOut() {
    const { error } = await supabase!.auth.signOut({ scope: 'local' })
    if (error) throw error
    session.value = null
  }
  return { session, user, configured, init, signOut }
})
