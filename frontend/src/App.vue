<template>
  <a-config-provider :theme="travelTheme">
  <div class="app-shell">
    <a href="#main-content" class="skip-link">跳到主要内容</a>
    <div v-if="auth.user" class="desktop-sidebar"><HistorySidebar /></div>
    <a-drawer v-if="auth.user" v-model:open="menuOpen" placement="left" :width="280" :body-style="{ padding: 0 }" title="旅行工作区">
      <HistorySidebar v-if="auth.user" @navigate="menuOpen = false" />
    </a-drawer>
    <a-layout :class="['app-layout', { 'with-sidebar': auth.user }]">
      <a-layout-header class="app-header">
        <div class="app-brand">
          <a-button v-if="auth.user" class="mobile-menu" aria-label="打开历史行程" @click="menuOpen = true"><MenuOutlined /></a-button>
          <BrandMark class="header-symbol" />
          <span>旅行助手</span>
          <span class="header-divider" aria-hidden="true"></span>
          <span class="page-label">{{ route.path === '/trips/new' ? '新增行程' : route.path.startsWith('/trips/') ? '我的行程' : '为下一次出发做准备' }}</span>
        </div>
        <span class="header-note">把时间留给风景</span>
      </a-layout-header>
      <a-layout-content id="main-content" class="app-content" tabindex="-1">
        <router-view :key="`${auth.user?.id || 'guest'}:${route.path}`" />
      </a-layout-content>
      <a-layout-footer class="app-footer">
        <span>旅行助手</span><span>行程由 AI 辅助生成，出行信息请以官方公告为准</span>
      </a-layout-footer>
    </a-layout>
  </div>
  </a-config-provider>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MenuOutlined } from '@ant-design/icons-vue'
import HistorySidebar from './components/HistorySidebar.vue'
import BrandMark from './components/BrandMark.vue'
import { travelTheme } from './styles/theme'
import { useAuth } from './stores/auth'
import { useTrips } from './stores/trips'
const auth = useAuth(), trips = useTrips(), route = useRoute(), router = useRouter()
const menuOpen = ref(false)
watch(() => route.fullPath, () => { menuOpen.value = false })
watch(() => auth.user?.id, id => {
  // Auth changes can unmount the sidebar before its navigation event is emitted.
  menuOpen.value = false
  trips.reset()
  if (id) void trips.load()
  else if (route.path.startsWith('/trips/')) void router.replace('/login')
}, { immediate: true })
</script>

<style>
.desktop-sidebar { width: 248px; position: fixed; inset: 0 auto 0 0; z-index: 20; }
.with-sidebar { margin-left: 248px; }
.mobile-menu { display: none; }
.app-shell { font-family: var(--font-body); color: var(--color-ink); }
.app-layout { min-height: 100vh; background: var(--color-paper); }
.app-layout .app-header { display: flex; align-items: center; justify-content: space-between; gap: 20px; height: 72px; padding: 0 36px; border-bottom: 1px solid var(--color-line); background: var(--color-paper); line-height: 1.4; }
.app-brand { display: flex; align-items: center; gap: 12px; min-width: 0; font-size: 16px; font-weight: 650; }
.app-brand .header-symbol { width: 30px; height: 30px; }
.header-divider { height: 17px; width: 1px; background: var(--color-line); margin: 0 6px; }
.page-label { color: var(--color-muted); font-size: 13px; font-weight: 400; }
.header-note { color: var(--color-muted); font-size: 12px; white-space: nowrap; }
.app-content { padding: 0; min-width: 0; }
.app-content:focus { outline: none; }
.app-layout .app-footer { display: flex; justify-content: space-between; gap: 20px; padding: 22px 36px; border-top: 1px solid var(--color-line); background: var(--color-paper); color: var(--color-muted); font-size: 12px; }
.skip-link { position: fixed; z-index: 1100; top: -80px; left: 16px; padding: 12px 18px; background: white; border: 2px solid var(--color-primary); border-radius: 8px; }
.skip-link:focus { top: 12px; }
@media (max-width: 960px) {
  .desktop-sidebar { display: none; }
  .with-sidebar { margin-left: 0; }
  .mobile-menu { display: inline-flex; align-items: center; justify-content: center; }
}
@media (max-width: 600px) {
  .app-layout .app-header { padding: 0 16px; height: 64px; }
  .app-brand { gap: 8px; font-size: 15px; }
  .header-note, .header-divider { display: none; }
  .page-label { font-size: 12px; }
  .app-layout .app-footer { padding: 20px; flex-direction: column; gap: 6px; }
}
</style>
