<template>
  <aside class="sidebar">
    <router-link class="sidebar-brand" to="/trips/new" @click="emit('navigate')">L / 旅行工作区</router-link>
    <a-button type="primary" block size="large" @click="navigate('/trips/new')"><PlusOutlined /> 新增行程</a-button>
    <div class="history-label">历史行程 <a-button type="text" size="small" aria-label="刷新历史行程" @click="trips.load()"><ReloadOutlined /></a-button></div>
    <div class="history-list">
      <a-alert v-if="trips.error" type="error" :message="trips.error" show-icon />
      <a-spin v-if="trips.loading" />
      <a-empty v-if="!trips.loading && !trips.error && !trips.items.length" description="还没有行程，从新增开始" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
      <article v-for="item in trips.items" :key="item.id" :class="['history-item', { selected: route.params.id === item.id }]">
        <router-link :to="`/trips/${item.id}`" @click="emit('navigate')"><span class="trip-title">{{ item.title }}</span>
          <span class="trip-meta">{{ statusLabels[item.status] }} · {{ new Date(item.created_at).toLocaleDateString() }}</span></router-link>
        <a-dropdown :trigger="['click']"><a-button type="text" size="small" :aria-label="`管理行程：${item.title}`"><MoreOutlined /></a-button>
          <template #overlay><a-menu>
            <a-menu-item key="rename" @click="action('rename', item)">重命名</a-menu-item><a-menu-item key="delete" danger :disabled="active(item)" @click="action('delete', item)">删除行程</a-menu-item>
          </a-menu></template>
        </a-dropdown>
      </article>
      <a-button v-if="trips.cursor" block :loading="trips.loading" @click="trips.load(true)">加载更多</a-button>
    </div>
    <div class="account"><span>{{ auth.user?.email || '已登录账号' }}</span><a-button block @click="logout">退出登录</a-button></div>
    <a-modal v-model:open="renaming" title="重命名行程" :confirm-loading="saving" @ok="rename">
      <a-input v-model:value="title" :maxlength="160" aria-label="行程标题" @press-enter="rename" />
    </a-modal>
  </aside>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Empty, Modal, message } from 'ant-design-vue'
import { PlusOutlined, MoreOutlined, ReloadOutlined } from '@ant-design/icons-vue'
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
.sidebar { display: flex; flex-direction: column; height: 100%; padding: 24px 16px 16px; background: #eef3f5; }
.sidebar-brand { font-size: 18px; font-weight: 750; color: #134e4a; margin-bottom: 28px; }
.history-label { display: flex; justify-content: space-between; align-items: center; color: #475569; font-size: 14px; margin: 26px 0 12px; }
.history-list { overflow: auto; flex: 1; min-height: 0; }
.history-item { display: flex; align-items: center; border-radius: 8px; margin: 4px 0; padding: 10px 6px 10px 12px; }
.history-item:hover { background: #e2e8f0; } .history-item.selected { background: #d3e8e5; box-shadow: inset 3px 0 #0f766e; }
.history-item a { min-width: 0; flex: 1; color: #1e293b; } .trip-title { display: block; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; font-size: 14px; }
.trip-meta { font-size: 12px; color: #526375; display: block; margin-top: 5px; }
.account { border-top: 1px solid #cbd5e1; padding-top: 16px; margin-top: 16px; } .account span { display: block; overflow-wrap: anywhere; margin-bottom: 12px; color: #334155; font-size: 14px; }
</style>
