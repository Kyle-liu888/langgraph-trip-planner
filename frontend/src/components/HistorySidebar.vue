<template>
  <aside class="sidebar">
    <router-link class="sidebar-brand" to="/trips/new" @click="emit('navigate')"><BrandMark /><span>旅行助手<small>我的旅行手账</small></span></router-link>
    <a-button class="new-trip" type="primary" block size="large" @click="navigate('/trips/new')"><PlusOutlined /> 新增行程</a-button>
    <div class="history-label">历史行程 <a-button type="text" size="small" aria-label="刷新历史行程" @click="trips.load()"><ReloadOutlined /></a-button></div>
    <div class="history-list">
      <a-alert v-if="trips.error" type="error" :message="trips.error" show-icon />
      <div v-if="trips.loading" class="history-loading"><a-spin size="small" /><span>正在读取行程</span></div>
      <div v-if="!trips.loading && !trips.error && !trips.items.length" class="history-empty"><EnvironmentOutlined /><p>还没有行程</p><span>点击「新增行程」，<br />写下第一个想去的地方。</span></div>
      <article v-for="item in trips.items" :key="item.id" :class="['history-item', { selected: route.params.id === item.id }]">
        <router-link :to="`/trips/${item.id}`" :aria-current="route.params.id === item.id ? 'page' : undefined" @click="emit('navigate')"><span class="trip-title">{{ item.title }}</span>
          <span class="trip-meta"><span :class="['status-dot', item.status]" aria-hidden="true"></span>{{ statusLabels[item.status] }}<time :datetime="item.created_at">{{ new Date(item.created_at).toLocaleDateString() }}</time></span></router-link>
        <a-dropdown :trigger="['click']"><a-button type="text" size="small" :aria-label="`管理行程：${item.title}`"><MoreOutlined /></a-button>
          <template #overlay><a-menu>
            <a-menu-item key="rename" @click="action('rename', item)">重命名</a-menu-item><a-menu-item key="delete" danger :disabled="active(item)" @click="action('delete', item)">删除行程</a-menu-item>
          </a-menu></template>
        </a-dropdown>
      </article>
      <a-button v-if="trips.cursor" class="load-more" block :loading="trips.loading" @click="trips.load(true)">加载更多</a-button>
    </div>
    <div class="account"><div class="account-identity"><span class="account-avatar" aria-hidden="true">{{ auth.user?.email?.slice(0, 1).toUpperCase() || '旅' }}</span><span class="account-detail"><span class="account-email" :title="auth.user?.email">{{ auth.user?.email || '已登录账号' }}</span><small>本地账号</small></span></div><a-button class="logout" type="text" block @click="logout"><LogoutOutlined /> 退出登录</a-button></div>
    <a-modal v-model:open="renaming" title="重命名行程" :confirm-loading="saving" @ok="rename">
      <a-input v-model:value="title" :maxlength="160" aria-label="行程标题" @press-enter="rename" />
    </a-modal>
  </aside>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Modal, message } from 'ant-design-vue'
import { PlusOutlined, MoreOutlined, ReloadOutlined, EnvironmentOutlined, LogoutOutlined } from '@ant-design/icons-vue'
import BrandMark from '@/components/BrandMark.vue'
import { useAuth } from '@/stores/auth'
import { useTrips } from '@/stores/trips'
import { active, statusLabels, type TripRecord } from '@/services/trips'
import api from '@/services/api'
const emit = defineEmits<{ navigate: [] }>()
const route = useRoute(), router = useRouter(), auth = useAuth(), trips = useTrips()
const renaming = ref(false), saving = ref(false), title = ref(''), target = ref<TripRecord | null>(null)
function navigate(path: string) { void router.push(path); emit('navigate') }
async function logout() {
  try { await auth.signOut(); trips.reset(); navigate('/login') }
  catch (e) { message.error((e as Error).message) }
}
function action(key: string, item: TripRecord) {
  if (key === 'rename') { target.value = item; title.value = item.title; renaming.value = true; return }
  Modal.confirm({ title: '删除此行程？', content: '行程、执行记录和检查点将被永久删除，无法恢复。已使用的规划次数不会返还。',
    okText: '删除', okType: 'danger', cancelText: '取消', async onOk() {
      try {
        await api.delete(`/api/trips/${item.id}`)
        if (route.params.id === item.id) navigate('/trips/new')
        await trips.load()
      } catch (e) { message.error((e as Error).message); throw e }
    } })
}
async function rename() {
  if (!title.value.trim() || !target.value || saving.value) return
  saving.value = true
  try {
    const { data } = await api.patch(`/api/trips/${target.value.id}`, { title: title.value.trim() })
    trips.upsert(data); renaming.value = false
  } catch (e) { message.error((e as Error).message) }
  finally { saving.value = false }
}
</script>
<style scoped>
.sidebar { display: flex; flex-direction: column; height: 100%; min-height: 0; padding: 30px 18px 16px; background: #203c38; color: #e7eee8; }
.sidebar-brand { display: flex; align-items: center; gap: 12px; margin: 0 6px 34px; color: #f4f8f0; text-decoration: none; font-size: 19px; font-weight: 650; }
.sidebar-brand:hover { color: #f4f8f0; }
.sidebar-brand :deep(svg) { width: 36px; height: 36px; flex-shrink: 0; color: #c7df9b; --brand-arrow-color: #203c38; --brand-detail-color: #c7df9b; }
.sidebar-brand small { display: block; font-size: 11px; font-weight: 400; color: #b2c5bb; margin-top: 4px; }
.new-trip.ant-btn-primary { height: 44px; background: #c7df9b; border-color: #c7df9b; color: #203c38; font-size: 14px; font-weight: 650; box-shadow: none; }
.new-trip.ant-btn-primary:not(:disabled):hover { background: #d8eab7; border-color: #d8eab7; color: #203c38; }
.history-label { display: flex; justify-content: space-between; align-items: center; color: #b7cbbf; font-size: 12px; margin: 32px 6px 12px; }
.history-label :deep(.ant-btn), .history-item :deep(.ant-btn) { color: #b7cbbf; }
.history-label :deep(.ant-btn:hover), .history-item :deep(.ant-btn:hover) { color: #f4f8f0; background: #39584b; }
.history-list { overflow: auto; flex: 1; min-height: 0; scrollbar-width: thin; scrollbar-color: #567367 transparent; }
.history-item { display: flex; align-items: center; border-radius: 9px; margin: 5px 0; padding: 12px 4px 12px 12px; border: 1px solid transparent; }
.history-item:hover { background: #2c4942; }
.history-item.selected { background: #36534a; border-color: #527365; box-shadow: inset 3px 0 #c7df9b; }
.history-item a { min-width: 0; flex: 1; color: #e6eee8; text-decoration: none; }
.trip-title { display: block; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; font-size: 13px; line-height: 1.6; font-weight: 500; }
.trip-meta { display: flex; align-items: center; gap: 5px; font-size: 10px; color: #b8cbbf; margin-top: 7px; white-space: nowrap; }
.trip-meta time { margin-left: auto; padding-left: 4px; }
.status-dot { display: inline-block; width: 5px; height: 5px; border-radius: 50%; background: #afc5b9; flex: 0 0 auto; }
.status-dot.completed { background: #c7df9b; }
.status-dot.running, .status-dot.queued { background: #e7cf8e; }
.status-dot.failed, .status-dot.interrupted { background: #e4ae94; }
.history-loading { display: flex; align-items: center; gap: 10px; padding: 16px 10px; color: #b8cbbf; font-size: 12px; }
.history-loading :deep(.ant-spin-dot-item) { background: #c7df9b; }
.history-empty { margin: 32px 8px; color: #b8cbbf; font-size: 12px; line-height: 1.9; }
.history-empty > :deep(.anticon) { font-size: 28px; margin-bottom: 8px; color: #c7df9b; }
.history-empty p { font-size: 14px; color: #e6eee8; margin: 4px 0 8px; }
.load-more { margin-top: 12px; border-color: #638073; background: transparent; color: #e6eee8; }
.load-more:not(:disabled):hover { border-color: #c7df9b; color: #c7df9b; background: #2c4942; }
.account { border-top: 1px solid #456157; padding: 18px 4px 0; margin-top: 16px; }
.account-identity { display: flex; gap: 10px; align-items: center; min-width: 0; }
.account-avatar { flex: 0 0 34px; width: 34px; height: 34px; border-radius: 50%; background: #3e5b50; color: #e4eccd; font-size: 14px; font-weight: 650; display: grid; place-items: center; }
.account-detail { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.account-email { color: #e6eee8; font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.account-detail small { font-size: 10px; color: #b2c5bb; }
.logout { margin-top: 12px; color: #bed0c6; font-size: 12px; text-align: left; }
.logout:not(:disabled):hover { background: #2c4942; color: #f4f8f0; }
.sidebar a:focus-visible, .sidebar :deep(button:focus-visible) { outline: 2px solid #c7df9b; outline-offset: 2px; }
</style>
