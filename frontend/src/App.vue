<template>
  <div id="app">
    <a-layout class="app-layout">
      <a-layout-header class="app-header">
        <div class="app-brand">
          <span class="brand-mark">H</span>
          <span>HelloAgents 智能旅行助手</span>
        </div>
      </a-layout-header>
      <a-layout-content class="app-content">
        <router-view />
      </a-layout-content>
      <a-layout-footer class="app-footer">
        HelloAgents 智能旅行助手 ©2026
      </a-layout-footer>
    </a-layout>
  </div>
</template>

<script setup lang="ts">
</script>

<style>
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
