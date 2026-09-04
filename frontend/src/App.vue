<template>
  <div id="app">
    <aside v-if="auth.user" class="desktop-sidebar"><HistorySidebar /></aside>
    <a-drawer v-model:open="menuOpen" placement="left" :width="280" :body-style="{ padding: 0 }" title="旅行工作区">
      <HistorySidebar v-if="auth.user" @navigate="menuOpen = false" />
    </a-drawer>
    <a-layout :class="['app-layout', { 'with-sidebar': auth.user }]">
      <a-layout-header class="app-header">
        <div class="app-brand">
          <a-button v-if="auth.user" class="mobile-menu" aria-label="打开历史行程" @click="menuOpen = true"><MenuOutlined /></a-button>
          <span class="brand-mark">L</span>
          <span>LangGraph 智能旅行助手</span>
        </div>
      </a-layout-header>
      <a-layout-content class="app-content">
        <router-view :key="`${auth.user?.id || 'guest'}:${route.path}`" />
      </a-layout-content>
      <a-layout-footer class="app-footer">
        LangGraph 智能旅行助手 ©2026
      </a-layout-footer>
    </a-layout>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MenuOutlined } from '@ant-design/icons-vue'
import HistorySidebar from './components/HistorySidebar.vue'
import { useAuth } from './stores/auth'
import { useTrips } from './stores/trips'
const auth = useAuth(), trips = useTrips(), route = useRoute(), router = useRouter()
const menuOpen = ref(false)
watch(() => auth.user?.id, id => {
  trips.reset()
  if (id) void trips.load()
  else if (route.path.startsWith('/trips/')) void router.replace('/login')
}, { immediate: true })
</script>

<style>
.desktop-sidebar { width: 270px; position: fixed; inset: 0 auto 0 0; z-index: 20; }
.with-sidebar { margin-left: 270px; }
.mobile-menu { display: none; }
@media (max-width: 960px) {
  .desktop-sidebar { display: none; }
  .with-sidebar { margin-left: 0; }
  .mobile-menu { display: inline-flex; }
}
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    'Noto Sans', sans-serif;
}

.app-layout {
  min-height: 100vh;
  background: #f6f8fb;
}

.app-header {
  display: flex;
  align-items: center;
  height: 64px;
  padding: 0 40px;
  border-bottom: 1px solid #e2e8f0;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(12px);
}

.app-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #0f172a;
  font-size: 18px;
  font-weight: 720;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #0f766e;
  color: #ffffff;
  font-size: 16px;
  font-weight: 800;
}

.app-content {
  padding: 0;
}

.app-footer {
  border-top: 1px solid #e2e8f0;
  background: #ffffff;
  color: #64748b;
  text-align: center;
}

@media (max-width: 720px) {
  .app-header {
    padding: 0 16px;
  }

  .app-brand {
    font-size: 16px;
  }
}
</style>
