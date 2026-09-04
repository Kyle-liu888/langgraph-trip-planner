<template>
  <main>
    <section class="progress-page">
      <a-alert v-if="error" type="error" show-icon :message="error" class="notice" />
      <a-spin v-if="loading" tip="正在读取行程…"><div style="min-height: 160px" /></a-spin>
      <a-empty v-else-if="!trip" description="无法加载此行程"><a-button @click="load">重试</a-button></a-empty>
      <template v-if="trip">
        <div class="progress-heading"><div><span class="eyebrow">行程工作区</span><h1>{{ trips.items.find(item => item.id === trip?.id)?.title || trip.title }}</h1></div>
          <a-tag :color="active(trip) ? 'processing' : trip.status === 'completed' ? 'success' : 'warning'">{{ statusLabels[trip.status] }}</a-tag>
        </div>
        <a-alert v-if="trip.status === 'fallback'" type="warning" show-icon :message="trip.message" />
        <a-card class="progress-card">
          <div class="current-node" aria-live="polite"><a-spin v-if="active(trip)" />
            <div><h2>{{ active(trip) ? nodeLabels[trip.current_node || ''] || '等待开始规划' : trip.message }}</h2>
              <p>{{ connection }}<span v-if="active(trip)"> · 本次页面观察 {{ elapsed }} 秒</span></p>
            </div>
          </div>
          <p class="help">这里显示真实节点与模型调用状态，不是模型的内部思考内容。离开或刷新页面不会取消后台任务。</p>
          <div v-if="['failed', 'interrupted'].includes(trip.status)" class="recovery">
            <p>继续规划将从最近保存的节点恢复；中断中的模型调用需要重新执行，可能再次产生 API 费用。</p>
            <a-button type="primary" :loading="resuming" @click="resume">从检查点继续规划</a-button>
          </div>
          <a-collapse ghost><a-collapse-panel key="events" :header="`执行记录（最近 ${events.length} 条）`">
            <a-empty v-if="!events.length" description="暂无执行记录，正在等待服务端事件" />
            <ol class="event-list"><li v-for="event in events" :key="event.sequence">
              <time>{{ new Date(event.timestamp).toLocaleTimeString() }}</time>
              <span>{{ eventText(event) }}</span>
              <small v-if="event.attempt">第 {{ event.attempt }} 次</small>
              <small v-if="event.elapsed_ms != null">{{ (event.elapsed_ms / 1000).toFixed(1) }} 秒</small>
            </li></ol>
          </a-collapse-panel></a-collapse>
          <p class="trace">行程编号：{{ trip.id }} · 运行编号：{{ trip.run_id }}</p>
        </a-card>
      </template>
    </section>
    <Result v-if="trip?.plan && !active(trip)" :key="trip.id" :record="trip" />
  </main>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import Result from './Result.vue'
import { getTrip, resumeTrip, active, nodeLabels, statusLabels, type TripRecord, type ProgressEvent } from '@/services/trips'
import { appendEvent, subscribeProgress } from '@/services/progress'
import { useTrips } from '@/stores/trips'
const route = useRoute(), trips = useTrips(), id = String(route.params.id)
const trip = ref<TripRecord | null>(null), events = ref<ProgressEvent[]>([])
const loading = ref(true), resuming = ref(false), error = ref(''), connection = ref('正在连接进度服务…'), elapsed = ref(0)
let controller = new AbortController(), disposed = false
const timer = setInterval(() => { if (trip.value && active(trip.value)) elapsed.value++ }, 1000)
function eventText(event: ProgressEvent) {
  const names: Record<string, string> = { 'node.started': '开始', 'node.completed': '完成', 'node.failed': '节点失败',
    'model.started': '正在调用模型', 'model.completed': '模型返回', 'model.failed': '模型调用或解析失败',
    'validation.failed': '候选校验未通过', 'retry.scheduled': '准备生成下一个候选' }
  return [names[event.type] || event.type, event.label || nodeLabels[event.node || ''] || '', event.model || '', event.error_type || ''].filter(Boolean).join(' · ')
}
async function refresh() {
  const record = await getTrip(id)
  if (disposed) return
  trip.value = record; trips.upsert(record)
}
async function stream() {
  controller.abort(); controller = new AbortController()
  const current = controller
  try {
    await subscribeProgress(id, current.signal, event => {
      events.value = appendEvent(events.value, event)
      if (trip.value && event.run_id === trip.value.run_id && event.type === 'node.started')
        trip.value.current_node = event.node || null
      if (trip.value && event.run_id === trip.value.run_id && event.type === 'run.started') trip.value.status = 'running'
    }, value => { connection.value = value })
    if (!current.signal.aborted) await refresh()
  } catch (e) { if (!current.signal.aborted) error.value = (e as Error).message }
}
async function load() {
  loading.value = true; error.value = ''
  try { await refresh(); if (!disposed) void stream() }
  catch (e) { error.value = (e as Error).message }
  finally { loading.value = false }
}
async function resume() {
  resuming.value = true; error.value = ''
  try { trip.value = await resumeTrip(id); trips.upsert(trip.value); elapsed.value = 0; void stream() }
  catch (e) { error.value = (e as Error).message }
  finally { resuming.value = false }
}
onMounted(load)
onUnmounted(() => { disposed = true; controller.abort(); clearInterval(timer) })
</script>

<style scoped>
.progress-page { max-width: 1280px; padding: 32px 24px 0; margin: auto; }
.progress-heading { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.eyebrow { color: #0f766e; font-size: 14px; } h1 { font-size: 26px; margin: 8px 0 24px; overflow-wrap: anywhere; }
.progress-card { margin: 16px 0 24px; border-left: 4px solid #0f766e; }
.current-node { display: flex; gap: 18px; align-items: center; } h2 { font-size: 19px; margin: 0 0 8px; }
p { color: #475569; font-size: 14px; line-height: 1.7; } .help { margin-top: 16px; }
.recovery { padding: 16px; background: #f8fafc; margin: 16px 0; } .trace { font-size: 12px; overflow-wrap: anywhere; margin-bottom: 0; }
.event-list { list-style: none; padding: 0; max-height: 360px; overflow: auto; }
.event-list li { display: flex; flex-wrap: wrap; gap: 12px; border-bottom: 1px solid #e2e8f0; padding: 10px 0; font-size: 14px; }
time, small { color: #64748b; } .notice { margin-bottom: 20px; }
@media(max-width: 600px) { .progress-page { padding: 20px 12px 0; } h1 { font-size: 22px; } }
</style>
