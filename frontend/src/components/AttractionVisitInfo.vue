<template>
  <section class="visit-info" aria-label="景点实用信息">
    <div class="ticket-estimate">
      <span><strong>门票预算估算：</strong>{{ budgetText }}</span>
      <InfoHint label="门票与开放信息说明">
        <p>非实时票价；零估算不代表免费，实际票价及优惠以官方政策为准。</p>
        <p v-if="info?.fetched_at">来源：{{ info.source_name }}<br>查询时间：{{ queriedAt }}<br>上游更新时间：未提供</p>
        <p v-if="info?.official">官方入口来源：{{ info.official.source_name }}<br>人工核验日期：{{ info.official.verified_at }}（非实时核验）</p>
        <p v-if="info && ['no_data', 'unmatched'].includes(info.status)">{{ visitStatusLabel(info) }}</p>
        <p>{{ VISIT_NOTICE }}</p>
      </InfoHint>
    </div>
    <div class="visit-columns">
    <section class="visit-section">
    <h4>开放与预约</h4>
    <p v-if="visibleStatus" role="status">{{ visibleStatus }}</p>
    <template v-if="info">
      <p v-if="showToday"><strong>今日开放时间（{{ info.opening.today_date }}）：</strong>{{ info.opening.today }}<span class="hint">（高德参考）</span></p>
      <p v-if="info.opening.regular"><strong>常规开放安排：</strong>{{ info.opening.regular }}<span class="hint">（高德参考）</span></p>
      <div v-if="sourceUrl" class="link-row"><a :href="sourceUrl" target="_blank" rel="noopener noreferrer">在高德查看地点</a></div>
      <div v-if="info.official" class="official">
        <div class="link-row">
          <template v-for="link in info.official.links" :key="link.purpose + link.url">
            <a v-if="safeExternalUrl(link.url)" :href="safeExternalUrl(link.url)" target="_blank" rel="noopener noreferrer">{{ link.label }}</a>
          </template>
        </div>
        <p>{{ info.official.reservation_note }}</p>
      </div>
      <p v-else class="hint">暂无已核验官方入口</p>
    </template>
    </section>
    <section class="visit-section guide-section">
    <div class="section-heading">
      <h4>游玩攻略</h4>
      <InfoHint label="攻略搜索说明">
        <p class="search-keyword">搜索词：{{ guides.keyword }}</p>
        <p>大众点评入口打开官网，不会自动搜索。可先复制搜索词，进入官网或 App 后粘贴查询。</p>
        <p>搜索结果未经过本项目审核；第三方平台可能需要登录或验证码。若入口失效，可复制搜索词到平台官网查询。</p>
        <p>电脑官网加载异常时，可试试以下入口。</p>
        <div class="link-row">
          <a href="https://www.xiaohongshu.com/" target="_blank" rel="noopener noreferrer">小红书官网</a>
          <a href="https://m.dianping.com/dphome" target="_blank" rel="noopener noreferrer">大众点评移动官网</a>
        </div>
      </InfoHint>
    </div>
    <div class="link-row guide-primary">
      <a :href="guides.xiaohongshu" target="_blank" rel="noopener noreferrer">小红书攻略搜索</a>
      <a :href="guides.dianping" target="_blank" rel="noopener noreferrer">大众点评官网</a>
      <button type="button" @click="copyKeyword">复制搜索词</button>
    </div>
    <p v-if="copyMessage" role="status">{{ copyMessage }}</p>
    <p v-if="copyFailed" class="search-keyword">搜索词：{{ guides.keyword }}</p>
    </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import InfoHint from '@/components/InfoHint.vue'
import { guideLinks, safeExternalUrl, VISIT_NOTICE, visitStatusLabel, type VisitInfo } from '@/services/visitInfo'
const props = defineProps<{ city: string; name: string; visitDate: string; ticketPrice?: number; info?: VisitInfo; editing?: boolean }>()
const guides = computed(() => guideLinks(props.city, props.name))
const budgetText = computed(() => typeof props.ticketPrice === 'number' && Number.isFinite(props.ticketPrice)
  ? '¥' + props.ticketPrice : '暂无估算')
const sourceUrl = computed(() => safeExternalUrl(props.info?.source_url))
const showToday = computed(() => props.info?.opening.today && (!props.visitDate || props.visitDate === props.info?.opening.today_date))
const visibleStatus = computed(() => {
  if (!props.info) return props.editing ? '保存后查询景点开放信息' : '正在查询开放时间…'
  return ({ no_data: '暂无开放时间参考', unmatched: '地点未匹配', permission_denied: '开放时间暂不可获取（接口权限不可用）',
    timeout: '开放时间查询超时，可稍后重试', unavailable: '开放时间暂不可获取' } as Partial<Record<VisitInfo['status'], string>>)[props.info.status] || ''
})
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
const copyFailed = ref(false)
watch(() => guides.value.keyword, () => { copyMessage.value = ''; copyFailed.value = false })
async function copyKeyword() {
  copyFailed.value = false
  try {
    await navigator.clipboard.writeText(guides.value.keyword)
    copyMessage.value = '搜索词已复制'
  } catch { copyFailed.value = true; copyMessage.value = '复制失败，请选中下方搜索词手动复制' }
}
</script>

<style scoped>
.visit-info { container-type: inline-size; margin-top: 20px; padding-top: 18px; border-top: 1px solid var(--color-line, #dce5df); overflow-wrap: anywhere; color: var(--color-ink, #203c38); font-size: 13px; }
.visit-info h4 { font-size: 14px; font-weight: 650; margin: 0 0 14px; color: var(--color-ink, #203c38); }
.visit-info p { margin: 7px 0; line-height: 1.8; }
.visit-info a { color: var(--color-primary, #176b5b); text-underline-offset: 3px; }
.ticket-estimate { display: flex; align-items: center; gap: 7px; color: var(--color-primary, #176b5b); }
.ticket-estimate strong { font-weight: 600; }
.section-heading { display: flex; align-items: center; gap: 7px; margin-bottom: 14px; }
.section-heading h4 { margin: 0; }
.hint, .search-keyword { color: var(--color-muted, #657873); font-size: 12px; }
.visit-columns { display: grid; gap: 20px; margin-top: 22px; }
.visit-section { min-width: 0; }
.guide-section { padding-top: 18px; border-top: 1px dashed var(--color-line, #dce5df); }
.official { padding: 12px; margin: 12px 0; border-radius: 7px; background: var(--color-paper, #f7f9f6); }
.link-row { display: flex; gap: 8px; flex-wrap: wrap; margin: 10px 0; align-items: center; }
.link-row a, .link-row button { display: inline-flex; align-items: center; min-height: 34px; color: var(--color-primary, #176b5b); border: 1px solid var(--color-line, #dce5df); border-radius: 6px; padding: 6px 10px; background: var(--color-surface, #fff); font: inherit; font-size: 12px; line-height: 1.5; text-decoration: none; cursor: pointer; }
.guide-primary a { background: #eef3eb; border-color: #d6e3d0; }
.link-row a:hover, .link-row button:hover { background: #e6efdf; border-color: #a7bca4; }
.visit-info a:focus-visible, .link-row button:focus-visible { outline: 2px solid var(--color-primary, #176b5b); outline-offset: 3px; }
.search-keyword { padding: 9px 0; user-select: text; }
@container (min-width: 700px) {
  .visit-columns { grid-template-columns: 1.15fr 1fr; gap: 26px; }
  .guide-section { border-top: 0; border-left: 1px dashed var(--color-line, #dce5df); padding: 0 0 0 26px; }
}
</style>
