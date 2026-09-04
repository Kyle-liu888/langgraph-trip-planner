<template>
  <main class="login-page">
    <a-card class="login-card">
      <div class="login-mark">L</div>
      <h1>把下一站，交给旅行助手</h1>
      <p>登录后创建行程、查看实时规划进度，随时回来继续。</p>
      <a-alert v-if="!auth.configured" type="warning" show-icon message="尚未配置 Supabase"
        description="请按 docs/SUPABASE_LOCAL_SETUP.md 填写前端环境变量并重启 Vite。不会自动开通或购买任何服务。" />
      <template v-else>
        <a-alert v-if="notice" :type="noticeType" :message="notice" show-icon class="notice" />
        <a-form layout="vertical" @finish="submit">
          <a-form-item label="邮箱"><a-input v-model:value="email" type="email" autocomplete="email" required /></a-form-item>
          <a-form-item label="密码"><a-input-password v-model:value="password" :autocomplete="register ? 'new-password' : 'current-password'" :minlength="8" required /></a-form-item>
          <a-button type="primary" html-type="submit" block :loading="busy">{{ register ? '注册账号' : '登录' }}</a-button>
        </a-form>
        <a-button type="link" block @click="register = !register">{{ register ? '已有账号？去登录' : '还没有账号？注册' }}</a-button>
        <a-divider>或</a-divider>
        <a-button block :disabled="busy" @click="github"><GithubOutlined /> 使用 GitHub 登录</a-button>
        <p class="login-note">邮箱注册后可能需要先确认邮件。GitHub 登录需在 Supabase 中启用。</p>
      </template>
    </a-card>
  </main>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { GithubOutlined } from '@ant-design/icons-vue'
import { supabase } from '@/services/supabase'
import { useAuth } from '@/stores/auth'
const auth = useAuth(), router = useRouter(), route = useRoute()
const email = ref(''), password = ref(''), register = ref(false), busy = ref(false), notice = ref('')
const noticeType = ref<'error' | 'success'>('error')
function destination() {
  const value = route.query.redirect
  return typeof value === 'string' && /^\/trips\/(new|[a-f0-9-]+)$/.test(value) ? value : '/trips/new'
}
onMounted(async () => {
  await auth.init()
  if (auth.user) await router.replace(destination())
  else if (route.path === '/auth/callback') {
    notice.value = '登录回调未完成或链接已过期，请重试登录。'
  }
})
async function submit() {
  if (!supabase) return
  busy.value = true; notice.value = ''; noticeType.value = 'error'
  try {
    const credentials = { email: email.value.trim(), password: password.value }
    const { data, error } = register.value
      ? await supabase.auth.signUp({ ...credentials, options: { emailRedirectTo: `${location.origin}/auth/callback` } })
      : await supabase.auth.signInWithPassword(credentials)
    if (error) throw error
    password.value = ''
    if (data.session) await router.replace(destination())
    else { noticeType.value = 'success'; notice.value = '请查收确认邮件；如果未收到，请检查 Supabase 邮件服务设置。' }
  } catch (e) { notice.value = (e as Error).message }
  finally { busy.value = false }
}
async function github() {
  const { error } = await supabase!.auth.signInWithOAuth({ provider: 'github', options: { redirectTo: `${location.origin}/auth/callback` } })
  if (error) { noticeType.value = 'error'; notice.value = error.message }
}
</script>

<style scoped>
.login-page { min-height: 85vh; display: grid; place-items: center; padding: 24px; }
.login-card { width: min(100%, 460px); }
.login-mark { background: #0f766e; color: white; width: 42px; height: 42px; display: grid; place-items: center; border-radius: 8px; font-size: 24px; }
h1 { font-size: 24px; margin: 24px 0 12px; } p { color: #475569; font-size: 16px; line-height: 1.7; }
.notice { margin: 20px 0; } .login-note { font-size: 14px; margin-top: 20px; }
</style>
