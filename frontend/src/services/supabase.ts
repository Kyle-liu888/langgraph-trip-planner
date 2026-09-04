import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL?.trim()
const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY?.trim()
export const supabase = url && key ? createClient(url, key, {
  auth: { flowType: 'pkce', persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
}) : null

export async function accessToken(): Promise<string> {
  if (!supabase) throw new Error('请先配置前端 Supabase 环境变量')
  const { data, error } = await supabase.auth.getSession()
  if (error || !data.session) throw new Error('登录已失效，请重新登录')
  return data.session.access_token
}
