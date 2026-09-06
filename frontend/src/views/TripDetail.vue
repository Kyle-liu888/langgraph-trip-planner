<template>
  <div class="trip-workspace">
    <section class="progress-page">
      <a-alert v-if="error" type="error" show-icon :message="error" class="notice" />
      <a-spin v-if="loading" tip="正在读取行程…"><div style="min-height: 160px" /></a-spin>
      <a-empty v-else-if="!trip" description="无法加载此行程"><a-button @click="load">重试</a-button></a-empty>
      <template v-if="trip">
        <div class="progress-heading">
          <h1>{{ trips.items.find(item => item.id === trip?.id)?.title || trip.title }}</h1>
          <a-tag :color="active(trip) ? 'processing' : trip.status === 'completed' ? 'success' : 'warning'">{{ statusLabels[trip.status] }}</a-tag>
        </div>
        <a-alert v-if="trip.status === 'fallback'" type="warning" show-icon :message="trip.message" class="notice" />
        <a-card :class="['progress-card', { 'is-active': active(trip), 'is-settled': !active(trip) && trip.plan }]">
          <div class="current-node" aria-live="polite">
            <a-spin v-if="active(trip)" />
            <span v-else-if="trip.status === 'completed'" class="completion-mark" aria-hidden="true">✓</span>
            <div class="node-content">
              <h2>{{ active(trip) ? nodeLabels[trip.current_node || ''] || '等待开始规划' : trip.status === 'completed' ? '行程已准备好，可以查看、编辑或导出。' : trip.message }}</h2>
              <p v-if="active(trip)" class="connection">{{ connection }}<span> · 本次页面观察 {{ elapsed }} 秒</span></p>
              <p v-if="active(trip) && latestModelEvent" class="model-status" role="status">{{ eventText(latestModelEvent) }}<span v-if="latestModelEvent.elapsed_ms != null"> · 已用 {{ (latestModelEvent.elapsed_ms / 1000).toFixed(0) }} 秒</span></p>
            </div>
          </div>
          <div v-if="['failed', 'interrupted'].includes(trip.status)" class="recovery">
            <p>继续规划将从最近保存的节点恢复；中断中的模型调用需要重新执行，可能再次产生 API 费用。</p>
            <a-button type="primary" :loading="resuming" @click="resume">从检查点继续规划</a-button>
          </div>
          <details class="execution-details">
            <summary>查看规划记录 <span>{{ events.length }} 条</span></summary>
            <p v-if="!active(trip)" class="connection">{{ connection }}</p>
            <p v-if="trip.status === 'completed'" class="help">{{ trip.message }}</p>
            <p class="help">这里显示真实节点与模型调用状态，不是模型的内部思考内容。离开或刷新页面不会取消后台任务。</p>
            <a-empty v-if="!events.length" description="暂无执行记录，正在等待服务端事件" />
            <ol class="event-list"><li v-for="event in events" :key="event.sequence">
              <time>{{ new Date(event.timestamp).toLocaleTimeString() }}</time>
              <span>{{ eventText(event) }}</span>
              <small v-if="event.attempt">第 {{ event.attempt }} 次</small>
              <small v-if="event.elapsed_ms != null">{{ (event.elapsed_ms / 1000).toFixed(1) }} 秒</small>
            </li></ol>
            <p class="trace">行程编号：{{ trip.id }}<br>运行编号：{{ trip.run_id }}</p>
          </details>
        </a-card>
      </template>
    </section>
    <Result v-if="trip?.plan && !active(trip)" :key="trip.id" :record="trip" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import Result from './Result.vue'
import { getTrip, resumeTrip, active, nodeLabels, statusLabels, type TripRecord, type ProgressEvent } from '@/services/trips'
import { appendEvent, subscribeProgress } from '@/services/progress'
import { eventText } from '@/services/progressText'
import { useTrips } from '@/stores/trips'
const route = useRoute(), trips = useTrips(), id = String(route.params.id)
const trip = ref<TripRecord | null>(null), events = ref<ProgressEvent[]>([])
const loading = ref(true), resuming = ref(false), error = ref(''), connection = ref('正在连接进度服务…'), elapsed = ref(0)
let controller = new AbortController(), disposed = false
const timer = setInterval(() => { if (trip.value && active(trip.value)) elapsed.value++ }, 1000)
const latestModelEvent = computed(() => trip.value?.current_node === 'generate_candidate'
  ? [...events.value].reverse().find(event => event.run_id === trip.value?.run_id &&
      (event.type.startsWith('model.') || event.type === 'retry.scheduled'))
  : undefined)
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
.trip-workspace { color: var(--color-ink, #203c38); min-width: 0; }
.progress-page { max-width: 1440px; padding: 34px 36px 0; margin: auto; }
.progress-heading { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 22px; }
h1 { font-family: STKaiti, KaiTi, 'Noto Serif CJK SC', serif; font-size: clamp(25px, 2.5vw, 34px); margin: 0; line-height: 1.4; overflow-wrap: anywhere; }
.progress-heading :deep(.ant-tag) { flex-shrink: 0; border-radius: 5px; padding: 3px 10px; margin: 0; }
.progress-card { margin: 0 0 24px; background: var(--color-surface, #fff); border: 1px solid var(--color-line, #dce5df); border-radius: 12px; box-shadow: none; }
.progress-card :deep(.ant-card-body) { padding: 22px 24px; }
.is-active { border-left: 3px solid var(--color-primary, #176b5b); }
.current-node { display: flex; gap: 16px; align-items: center; }
.node-content { min-width: 0; flex: 1; }
h2 { color: var(--color-ink, #203c38); font-size: 18px; line-height: 1.6; margin: 0; overflow-wrap: anywhere; }
p { color: var(--color-muted, #657873); font-size: 13px; line-height: 1.8; }
.connection { margin: 7px 0 0; font-size: 12px; }
.model-status { margin: 12px 0 0; padding: 10px 14px; border-radius: 7px; background: #eef3eb; color: var(--color-primary, #176b5b); overflow-wrap: anywhere; }
.completion-mark { display: grid; place-items: center; width: 25px; height: 25px; border-radius: 50%; color: var(--color-primary, #176b5b); background: #e5efdc; font-size: 15px; flex-shrink: 0; }
.is-settled :deep(.ant-card-body) { padding: 16px 20px; }
.is-settled h2 { font-size: 14px; font-weight: 500; }
.execution-details { margin-top: 16px; }
.execution-details summary { color: var(--color-muted, #657873); cursor: pointer; width: fit-content; font-size: 12px; line-height: 26px; border-radius: 3px; }
.execution-details summary span { margin-left: 8px; color: var(--color-muted, #657873); font-variant-numeric: tabular-nums; }
.execution-details summary:hover { color: var(--color-primary, #176b5b); }
.execution-details summary:focus-visible { outline: 2px solid var(--color-primary, #176b5b); outline-offset: 4px; }
.execution-details[open] { padding-top: 12px; border-top: 1px solid var(--color-line, #dce5df); }
.is-settled .execution-details { margin-top: 8px; }
.help { margin: 12px 0; }
.recovery { padding: 16px 18px; border-radius: 8px; background: #faf6e8; margin: 18px 0; }
.recovery p { margin: 0 0 14px; color: #756039; }
.trace { font-size: 11px; overflow-wrap: anywhere; margin-bottom: 0; color: var(--color-muted, #657873); }
.event-list { list-style: none; padding: 0; margin: 14px 0; max-height: 300px; overflow: auto; }
.event-list li { display: flex; flex-wrap: wrap; gap: 6px 12px; border-bottom: 1px solid var(--color-line, #dce5df); padding: 11px 0; font-size: 12px; line-height: 1.8; overflow-wrap: anywhere; }
.event-list li > span { flex: 1 1 200px; }
time, small { color: var(--color-muted, #657873); font-size: 11px; font-variant-numeric: tabular-nums; }
.notice { margin-bottom: 20px; }
@media (max-width: 1180px) { .progress-page { padding: 28px 24px 0; } }
@media (max-width: 760px) {
  .progress-page { padding: 24px 16px 0; }
  .progress-heading { align-items: flex-start; gap: 10px; margin-bottom: 18px; }
  .progress-heading :deep(.ant-tag) { padding: 2px 7px; margin-top: 4px; font-size: 11px; }
  .progress-card :deep(.ant-card-body) { padding: 16px; }
  h1 { font-size: 25px; } h2 { font-size: 16px; }
  .current-node { gap: 12px; }
  .event-list li > span { flex-basis: 150px; }
}
</style>
