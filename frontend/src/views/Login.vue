<template>
  <main class="login-page">
    <a-card class="login-card">
      <div class="login-mark">L</div>
      <h1>把下一站，交给旅行助手</h1>
      <p>登录后创建行程、查看实时规划进度，随时回来继续。</p>
      <a-alert v-if="auth.error" type="warning" show-icon :message="auth.error" />
        <a-alert v-if="notice" :type="noticeType" :message="notice" show-icon class="notice" />
        <a-form :model="credentials" layout="vertical" @finish="submit" @finish-failed="validationFailed" novalidate>
          <a-form-item label="邮箱" name="email" :rules="emailRules"><a-input v-model:value="credentials.email" type="email" autocomplete="email" /></a-form-item>
          <a-form-item label="密码" name="password" :rules="passwordRules"><a-input-password v-model:value="credentials.password" :autocomplete="register ? 'new-password' : 'current-password'" /></a-form-item>
          <a-button type="primary" html-type="submit" block :loading="busy">{{ register ? '注册账号' : '登录' }}</a-button>
        </a-form>
        <a-button type="link" block :disabled="busy" @click="register = !register; notice = ''">{{ register ? '已有账号？去登录' : '还没有账号？注册' }}</a-button>
        <p class="login-note">账号和行程保存在你的本地数据库。邮箱仅作为登录标识，不发送验证邮件。密码为 8–128 个字符。</p>
    </a-card>
  </main>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import type { Rule } from 'ant-design-vue/es/form'
import { useRouter, useRoute } from 'vue-router'
import { useAuth } from '@/stores/auth'
const auth = useAuth(), router = useRouter(), route = useRoute()
const credentials = reactive({ email: '', password: '' })
const register = ref(false), busy = ref(false), notice = ref('')
const emailRules: Rule[] = [
  { required: true, message: '请输入邮箱' },
  { type: 'email', transform: value => value.trim(), message: '请输入有效的邮箱地址' }
]
const passwordRules: Rule[] = [
  { required: true, message: '请输入密码' },
  { min: 8, max: 128, message: '密码需要 8–128 个字符' }
]
const noticeType = ref<'error' | 'success'>('error')
function validationFailed() {
  noticeType.value = 'error'
  notice.value = '请检查邮箱和密码，修正下方提示后重试'
}
function destination() {
  const value = route.query.redirect
  return typeof value === 'string' && /^\/trips\/(new|[a-f0-9-]+)$/.test(value) ? value : '/trips/new'
}
onMounted(async () => {
  await auth.init()
  if (auth.user) await router.replace(destination())
})
async function submit() {
  if (busy.value) return
  busy.value = true; notice.value = ''; noticeType.value = 'error'
  try {
    await auth.authenticate({ email: credentials.email.trim(), password: credentials.password }, register.value)
    credentials.password = ''
    await router.replace(destination())
  } catch (e) { notice.value = (e as Error).message }
  finally { busy.value = false }
}
</script>

<style scoped>
.login-page { min-height: 85vh; display: grid; place-items: center; padding: 24px; }
.login-card { width: min(100%, 460px); }
.login-mark { background: #0f766e; color: white; width: 42px; height: 42px; display: grid; place-items: center; border-radius: 8px; font-size: 24px; }
h1 { font-size: 24px; margin: 24px 0 12px; } p { color: #475569; font-size: 16px; line-height: 1.7; }
.notice { margin: 20px 0; } .login-note { font-size: 14px; margin-top: 20px; }
</style>
