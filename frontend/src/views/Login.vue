<template>
  <div class="login-page">
    <section class="login-story" aria-labelledby="welcome-title">
      <div class="story-brand"><BrandMark /><span>旅行助手</span></div>
      <h1 id="welcome-title">把下一站，<br />写进行程里。</h1>
      <p class="story-intro">从一个想去的地方开始。把沿途的风景、<br class="desktop-break" />每天的安排，慢慢变成你的旅行。</p>
      <JourneySketch class="login-sketch" aria-hidden="true" />
      <p class="story-footnote">规划路线、保存行程，随时回来继续。</p>
    </section>
    <section class="login-form-panel" aria-labelledby="form-title">
      <div class="login-card">
      <h2 id="form-title">{{ register ? '创建你的账号' : '欢迎回来' }}</h2>
      <p class="form-intro">{{ register ? '保存第一份行程，从这里出发。' : '登录，继续准备下一次出发。' }}</p>
      <a-alert v-if="auth.error" type="warning" show-icon :message="auth.error" />
        <a-alert v-if="notice" :type="noticeType" :message="notice" show-icon class="notice" />
        <a-form :model="credentials" layout="vertical" @finish="submit" @finish-failed="validationFailed" novalidate>
          <a-form-item label="邮箱" name="email" :rules="emailRules"><a-input v-model:value="credentials.email" size="large" type="email" autocomplete="email" placeholder="输入你的邮箱地址" /></a-form-item>
          <a-form-item label="密码" name="password" :rules="passwordRules"><a-input-password v-model:value="credentials.password" size="large" :autocomplete="register ? 'new-password' : 'current-password'" placeholder="8–128 个字符" /></a-form-item>
          <a-button class="login-submit" type="primary" size="large" html-type="submit" block :loading="busy">{{ register ? '注册账号' : '登录' }}</a-button>
        </a-form>
        <a-button class="switch-mode" type="link" block :disabled="busy" @click="register = !register; notice = ''">{{ register ? '已有账号？去登录' : '还没有账号？注册' }}</a-button>
        <p class="login-note"><LockOutlined /> 账号和行程保存在本地数据库。邮箱仅作为登录标识，不发送验证邮件。密码为 8–128 个字符。</p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import type { Rule } from 'ant-design-vue/es/form'
import { useRouter, useRoute } from 'vue-router'
import { useAuth } from '@/stores/auth'
import { LockOutlined } from '@ant-design/icons-vue'
import BrandMark from '@/components/BrandMark.vue'
import JourneySketch from '@/components/JourneySketch.vue'
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
.login-page { display: grid; grid-template-columns: 1.08fr 1fr; min-height: min(760px, calc(100vh - 160px)); max-width: 1160px; margin: 36px auto; border: 1px solid var(--color-line); border-radius: 24px; overflow: hidden; background: var(--color-surface); }
.login-story { position: relative; display: flex; flex-direction: column; align-items: flex-start; overflow: hidden; padding: 42px 48px 32px; background: #edf3e9; color: var(--color-ink); }
.story-brand { display: flex; align-items: center; gap: 10px; font-size: 16px; font-weight: 650; }
.story-brand :deep(svg) { width: 34px; height: 34px; color: var(--color-primary); }
.login-story h1 { position: relative; z-index: 1; margin: 44px 0 18px; font-family: 'STKaiti', 'KaiTi', 'Noto Serif CJK SC', serif; font-weight: 600; font-size: clamp(36px, 3.5vw, 52px); line-height: 1.4; letter-spacing: .025em; }
.story-intro { position: relative; z-index: 1; font-size: 15px; line-height: 1.9; margin: 0; color: #52675b; }
.login-sketch { width: 100%; max-height: 248px; margin: 16px 0 8px; flex: 1; min-height: 170px; }
.story-footnote { position: relative; z-index: 1; margin: auto 0 0; padding-top: 12px; color: #53685a; font-size: 12px; }
.login-form-panel { display: flex; align-items: center; justify-content: center; padding: 48px; }
.login-card { width: 100%; max-width: 360px; }
.login-card h2 { font-size: 28px; line-height: 1.4; font-weight: 650; margin: 0 0 10px; color: var(--color-ink); }
.form-intro { color: var(--color-muted); font-size: 14px; line-height: 1.7; margin: 0 0 36px; }
.login-card :deep(.ant-form-item-label > label) { color: var(--color-ink); font-weight: 550; }
.login-card :deep(.ant-input-lg), .login-card :deep(.ant-input-affix-wrapper-lg) { border-radius: 9px; font-size: 14px; }
.login-card :deep(.ant-input-affix-wrapper-lg .ant-input) { border-radius: 0; }
.login-submit { height: 46px; margin-top: 4px; font-weight: 600; }
.switch-mode { margin-top: 12px; font-size: 13px; }
.notice, .login-card > :deep(.ant-alert) { margin-bottom: 20px; }
.login-note { border-top: 1px solid var(--color-line); padding-top: 24px; margin: 28px 0 0; color: var(--color-muted); font-size: 12px; line-height: 1.9; }
.login-note :deep(.anticon) { margin-right: 4px; }
.login-card :deep(button:focus-visible) { outline: 3px solid var(--color-primary); outline-offset: 3px; }
@media (max-width: 1100px) { .login-page { margin: 24px; } .login-story { padding: 36px 32px 28px; } .login-form-panel { padding: 40px 32px; } }
@media (max-width: 720px) { .login-page { display: block; margin: 16px; min-height: auto; border-radius: 18px; } .login-story { padding: 26px 28px; } .story-brand { font-size: 14px; } .story-brand :deep(svg) { width: 28px; height: 28px; } .login-story h1 { margin: 22px 0 12px; font-size: 36px; } .story-intro { max-width: 290px; font-size: 13px; } .login-sketch { position: absolute; width: 180px; height: 160px; min-height: 0; right: -56px; bottom: -36px; opacity: .55; margin: 0; } .story-footnote { display: none; } .desktop-break { display: none; } .login-form-panel { padding: 32px 28px; } .login-card { max-width: 440px; } .login-card h2 { font-size: 24px; } .form-intro { margin-bottom: 24px; } }
@media (max-width: 720px) { .login-sketch { display: none; } }
@media (max-width: 380px) { .login-page { margin: 10px; } .login-story, .login-form-panel { padding: 24px; } .login-story h1 { font-size: 32px; } }
</style>
