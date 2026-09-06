<template>
  <section class="visit-info" aria-label="景点实用信息">
    <p class="ticket-estimate"><strong>门票预算估算：</strong>{{ budgetText }}</p>
    <p class="hint">非实时票价；是否免费、实际票价及优惠以官方政策为准。</p>
    <h4>开放与预约</h4>
    <p v-if="editing && !info" role="status">保存后查询景点开放信息</p>
    <p v-else-if="visitStatusLabel(info)" role="status">{{ visitStatusLabel(info) }}</p>
    <template v-if="info">
      <p v-if="showToday"><strong>今日开放时间（{{ info.opening.today_date }}）：</strong>{{ info.opening.today }}</p>
      <p v-if="info.opening.regular"><strong>常规开放安排：</strong>{{ info.opening.regular }}</p>
      <p v-if="info.fetched_at" class="hint">
        {{ info.source_name }}<br>查询时间：{{ queriedAt }}<br>上游更新时间：未提供
        <a v-if="sourceUrl" :href="sourceUrl" target="_blank" rel="noopener noreferrer">在高德查看地点</a>
      </p>
      <div v-if="info.official" class="official">
        <div class="link-row">
          <template v-for="link in info.official.links" :key="link.purpose + link.url">
            <a v-if="safeExternalUrl(link.url)" :href="safeExternalUrl(link.url)" target="_blank" rel="noopener noreferrer">{{ link.label }}</a>
          </template>
        </div>
        <p>{{ info.official.reservation_note }}</p>
        <p class="hint">来源：{{ info.official.source_name }} · 人工核验日期：{{ info.official.verified_at }}（非实时核验）</p>
      </div>
      <p v-else class="hint">暂无已核验官方入口</p>
    </template>
    <p class="notice">{{ VISIT_NOTICE }}</p>
    <h4>游玩攻略</h4>
    <div class="link-row">
      <a :href="guides.xiaohongshu" target="_blank" rel="noopener noreferrer">小红书攻略搜索</a>
      <a :href="guides.dianping" target="_blank" rel="noopener noreferrer">站外搜索大众点评攻略</a>
    </div>
    <div class="link-row">
      <button type="button" @click="copyKeyword">复制搜索词</button>
      <a href="https://www.xiaohongshu.com/" target="_blank" rel="noopener noreferrer">小红书官网</a>
      <a href="https://www.dianping.com/" target="_blank" rel="noopener noreferrer">大众点评官网</a>
    </div>
    <p class="search-keyword">搜索词：{{ guides.keyword }}</p>
    <p v-if="copyMessage" role="status">{{ copyMessage }}</p>
    <p class="hint">搜索结果未经过本项目审核；第三方平台可能需要登录或验证码。若入口失效，可复制搜索词到平台官网查询。</p>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { guideLinks, safeExternalUrl, VISIT_NOTICE, visitStatusLabel, type VisitInfo } from '@/services/visitInfo'
const props = defineProps<{ city: string; name: string; visitDate: string; ticketPrice?: number; info?: VisitInfo; editing?: boolean }>()
const guides = computed(() => guideLinks(props.city, props.name))
const budgetText = computed(() => typeof props.ticketPrice === 'number' && Number.isFinite(props.ticketPrice)
  ? '¥' + props.ticketPrice + '（仅预算参考）' : '暂无估算')
const sourceUrl = computed(() => safeExternalUrl(props.info?.source_url))
const showToday = computed(() => props.info?.opening.today && (!props.visitDate || props.visitDate === props.info?.opening.today_date))
const queriedAt = computed(() => {
  const value = props.info?.fetched_at
  if (!value) return ''
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? '未知' : new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  }).format(d) + '（北京时间）'
})
const copyMessage = ref('')
async function copyKeyword() {
  try {
    await navigator.clipboard.writeText(guides.value.keyword)
    copyMessage.value = '搜索词已复制'
  } catch { copyMessage.value = '复制失败，请选中下方搜索词手动复制' }
}
</script>

<style scoped>
.visit-info { margin-top: 14px; padding-top: 12px; border-top: 1px solid #e2e8f0; overflow-wrap: anywhere; }
.visit-info h4 { font-size: 14px; margin: 12px 0 8px; color: #0f172a; }
.visit-info p { margin: 6px 0; line-height: 1.65; }
.ticket-estimate { color: #334155; }
.hint, .search-keyword { color: #64748b; font-size: 12px; }
.notice { padding: 8px; background: #fff7ed; color: #9a3412; font-size: 12px; border-radius: 6px; }
.official { padding: 8px; border-radius: 6px; background: #f8fafc; }
.link-row { display: flex; gap: 8px; flex-wrap: wrap; margin: 8px 0; align-items: center; }
.link-row a, .link-row button { color: #1d4ed8; border: 1px solid #cbd5e1; border-radius: 5px; padding: 3px 8px; background: white; font-size: 12px; cursor: pointer; }
.link-row a:hover, .link-row button:hover { background: #eff6ff; }
.link-row a:focus-visible, .link-row button:focus-visible { outline: 2px solid #2563eb; outline-offset: 2px; }
</style>
