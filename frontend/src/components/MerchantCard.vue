<template>
  <article class="merchant-card" :data-kind="kind" :aria-label="`${merchant.name}门店资料`">
    <header class="merchant-heading">
      <div class="merchant-title-line">
        <span v-if="mealLabel" class="meal-label">{{ mealLabel }}</span><h3>{{ merchant.name }}</h3>
        <InfoHint label="门店资料说明">
          <h6>预算与行程建议</h6>
          <p>仅预算参考，非实时{{ kind === 'hotel' ? '房价或房态' : '菜单价格' }}；零估算不代表免费。</p>
          <p v-if="hotelType || distance">{{ [hotelType, distance].filter(Boolean).join('；') }}（行程建议，未独立核验）</p>
          <p v-if="generic && kind === 'food' && merchant.name.includes('早餐')">是否包含早餐请向住处确认。</p>
          <template v-if="!generic">
            <h6>资料来源</h6>
            <p v-if="info?.source">来源：{{ info.source.name }}</p>
            <p v-if="info?.source?.queried_at || info?.queried_at">查询时间：{{ merchantQueryTime(info?.source?.queried_at || info?.queried_at) }}<br>上游更新时间：未提供</p>
            <p v-if="trustedRating">高德参考评分并非实时评价，详见来源平台。</p>
            <p v-if="kind === 'food' && info?.source && info.food_tags.length">餐饮特色来自高德字段，不是完整菜单。</p>
            <p v-if="info?.match_status === 'matched' && info.data_status === 'available' && info.message">{{ info.message }}</p>
            <template v-if="info?.photos.length">
              <h6>参考图片</h6>
              <p>图片来源：高德地图；未独立核验拍摄时间和具体房型／菜品。点击图片可放大并查看原始说明。</p>
            </template>
            <h6>平台与搜索</h6>
            <p v-if="links.length">人工核验日期：{{ links.map(link => `${platformNames[link.platform]} ${link.verified_at}`).join('；') }}。非实时核验，链接可能变化。</p>
            <p v-if="amapUrl || links.length">评价与更多图片请在平台查看；目标页面不保证有评价。</p>
            <p>小红书按钮是搜索入口，不是已核验评价；平台可能要求登录。入口失效时，可复制搜索词到小红书查询。</p>
            <p class="search-keyword">搜索词：{{ search.keyword }}</p>
          </template>
        </InfoHint>
      </div>
      <p class="merchant-estimate"><span>{{ kind === 'hotel' ? '住宿预算估算' : '餐饮预算估算' }}</span><strong>{{ budget }}</strong></p>
    </header>
    <div class="merchant-body">
      <p v-if="description" class="plan-suggestion"><span>行程建议：</span>{{ description }}</p>
      <p v-if="generic" class="merchant-status" role="status">尚未指定具体{{ kind === 'hotel' ? '住处' : '门店' }}。</p>
      <template v-else>
        <section class="merchant-facts" aria-label="门店来源资料">
          <p v-if="info?.place?.address"><span class="fact-label">来源地址</span>{{ info.place.address }}</p>
          <p v-else-if="merchant.address"><span class="fact-label">行程地址（未核验）</span>{{ merchant.address }}</p>
          <p v-if="trustedRating"><span class="fact-label">高德参考评分</span><strong class="merchant-rating">{{ trustedRating }}</strong></p>
          <p v-else-if="info" class="merchant-note">暂无可核验评分</p>
          <p v-if="kind === 'food' && info?.source && info.food_tags.length"><span class="fact-label">高德餐饮特色</span>{{ info.food_tags.join('、') }}</p>
          <p v-if="status" class="merchant-status" role="status">{{ status }}</p>
        </section>
        <div v-if="photos.length" class="merchant-photos" aria-label="高德门店参考图片">
          <figure v-for="(photo, index) in photos" :key="photo.url">
            <button type="button" class="photo-open" :aria-label="`放大${merchant.name}门店参考图 ${index + 1}`" @click="openPhoto(photo)">
              <img :src="photo.url" :alt="`${merchant.name}门店参考图 ${index + 1}`" loading="lazy" referrerpolicy="no-referrer" @error="failedPhotos.add(photo.url)">
            </button>
          </figure>
        </div>
        <p v-if="photos.length" class="merchant-note">门店参考图 · 高德</p>
        <p v-else-if="info" class="merchant-note">{{ failedPhotos.size ? '参考图片暂时无法加载' : '暂无可用门店参考图' }}</p>
        <section class="merchant-links" aria-label="平台门店入口">
          <div class="merchant-link-row">
            <a v-if="amapUrl" :href="amapUrl" target="_blank" rel="noopener noreferrer">在高德查看门店</a>
            <a v-for="link in links" :key="link.platform" :href="link.url" target="_blank" rel="noopener noreferrer">在{{ platformNames[link.platform] }}查看门店</a>
          </div>
        </section>
        <section class="merchant-search" aria-label="小红书搜索入口">
          <div class="merchant-link-row">
            <a :href="search.url" target="_blank" rel="noopener noreferrer">{{ kind === 'hotel' ? '小红书搜这家酒店' : '小红书搜这家店' }}</a>
            <button type="button" @click="copyKeyword">复制搜索词</button>
          </div>
          <p v-if="copyFailed" class="merchant-note search-keyword">搜索词：{{ search.keyword }}</p>
          <p v-if="copyMessage" role="status" class="merchant-note">{{ copyMessage }}</p>
        </section>
      </template>
    </div>
    <dialog ref="previewDialog" class="merchant-preview" :aria-label="`${merchant.name}门店参考图预览`" @click="closeFromBackdrop" @close="selectedPhoto = undefined">
      <button type="button" class="preview-close" @click="previewDialog?.close()">关闭图片</button>
      <img v-if="selectedPhoto" :src="selectedPhoto.url" :alt="`${merchant.name}门店参考图`" referrerpolicy="no-referrer">
      <p>门店参考图<span v-if="selectedPhoto?.title && selectedPhoto.title !== '门店参考图'">：{{ selectedPhoto.title }}</span>（图片来源：高德地图）</p>
    </dialog>
  </article>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import InfoHint from '@/components/InfoHint.vue'
import { isGenericMerchant, merchantKey, merchantQueryTime, merchantSearch, safeMerchantLink,
  type MerchantIdentity, type MerchantInfo, type MerchantKind } from '@/services/merchantInfo'
import { safeExternalUrl } from '@/services/visitInfo'
const props = defineProps<{ city: string; kind: MerchantKind; merchant: MerchantIdentity; info?: MerchantInfo;
  estimatedCost?: number; priceRange?: string; description?: string; hotelType?: string; distance?: string; mealLabel?: string }>()
const platformNames = { dianping: '大众点评', meituan: '美团', ctrip: '携程' }
const generic = computed(() => isGenericMerchant(props.kind, props.city, props.merchant.name) || props.info?.match_status === 'generic')
const budget = computed(() => typeof props.estimatedCost === 'number' && Number.isFinite(props.estimatedCost)
  ? `¥${props.estimatedCost}` : props.priceRange || '暂无估算')
const trustedRating = computed(() => props.info?.source && props.info.match_status === 'matched' ? props.info.rating : null)
const amapUrl = computed(() => props.info?.source ? safeMerchantLink(props.info.source.url, 'amap') : undefined)
const links = computed(() => (props.info?.links || []).flatMap(link => {
  if (props.kind === 'food' && link.platform === 'ctrip' || props.kind === 'hotel' && link.platform === 'dianping') return []
  const url = safeMerchantLink(link.url, link.platform)
  return url ? [{ ...link, url }] : []
}))
const failedPhotos = ref(new Set<string>())
const photos = computed(() => props.info?.source ? props.info.photos.filter(photo => safeExternalUrl(photo.url) && !failedPhotos.value.has(photo.url)).slice(0, 3) : [])
const status = computed(() => {
  const info = props.info
  if (!info) return '正在核验门店资料…'
  if (/登录已失效|请重新登录|账号已切换/.test(info.message)) return '登录已失效，请重新登录'
  // Operational failures stay visible; successful source notices belong in the help panel.
  if (info.data_status === 'timeout') return '门店资料查询超时，可稍后重试'
  if (info.data_status === 'permission_denied') return '接口权限不可用，暂无法查询门店资料'
  if (info.data_status === 'unavailable') return '门店资料暂不可获取，可稍后重试'
  if (info.match_status === 'ambiguous') return '有多家同名门店，暂未确认'
  if (info.match_status === 'insufficient') return '门店信息不足，暂未确认'
  if (info.match_status === 'unmatched') return '未找到可确认的同一家门店'
  if (info.data_status === 'no_data') return '暂无更多门店资料'
  return ''
})
const search = computed(() => merchantSearch(props.city, props.merchant.name, props.kind))
const copyMessage = ref('')
const copyFailed = ref(false)
const previewDialog = ref<HTMLDialogElement>()
const selectedPhoto = ref<MerchantInfo['photos'][number]>()
watch(() => merchantKey(props.city, { kind: props.kind, merchant: props.merchant }), () => {
  failedPhotos.value = new Set(); copyMessage.value = ''; copyFailed.value = false; previewDialog.value?.close(); selectedPhoto.value = undefined
})
async function openPhoto(photo: MerchantInfo['photos'][number]) {
  selectedPhoto.value = photo
  await nextTick()
  previewDialog.value?.showModal()
}
function closeFromBackdrop(event: MouseEvent) { if (event.target === previewDialog.value) previewDialog.value?.close() }
async function copyKeyword() {
  try { await navigator.clipboard.writeText(search.value.keyword); copyFailed.value = false; copyMessage.value = '搜索词已复制' }
  catch { copyFailed.value = true; copyMessage.value = '复制失败，请选中上方搜索词手动复制' }
}
</script>

<style scoped>
.merchant-card { min-width: 0; color: var(--color-ink, #203c38); border: 1px solid var(--color-line, #dce5df); border-radius: 9px; overflow-wrap: anywhere; background: var(--color-surface, #fff); }
.merchant-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; padding: 16px 18px; background: var(--color-paper, #f7f9f6); border-bottom: 1px solid var(--color-line, #dce5df); }
.merchant-title-line { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; min-width: 0; }
.merchant-heading h3 { display: inline; margin: 0; font: inherit; font-size: 17px; font-weight: 650; line-height: 1.7; }
.meal-label { display: inline-block; margin-right: 2px; color: var(--color-primary, #176b5b); font-size: 12px; border-bottom: 2px solid #aac9aa; vertical-align: 2px; }
.merchant-estimate { flex-shrink: 0; display: grid; gap: 4px; margin: 0; font-size: 11px; color: var(--color-muted, #657873); text-align: right; }
.merchant-estimate strong { color: var(--color-primary, #176b5b); font-size: 16px; font-weight: 600; font-variant-numeric: tabular-nums; max-width: 180px; }
.merchant-body { padding: 14px 18px 18px; font-size: 13px; line-height: 1.85; }
.merchant-body p { margin: 6px 0; }
.plan-suggestion span, .fact-label { color: var(--color-muted, #657873); }
.fact-label { display: inline-block; margin-right: 10px; }
.merchant-note { color: var(--color-muted, #657873); font-size: 12px; }
.merchant-facts { margin: 16px 0; }
.merchant-rating { color: var(--color-primary, #176b5b); font-size: 17px; margin-right: 9px; }
.merchant-status { padding-left: 10px; border-left: 2px solid #aac9aa; }
.merchant-photos { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 9px; max-width: 650px; margin-top: 16px; }
.merchant-photos figure { margin: 0; min-width: 0; }
.photo-open { display: block; width: 100%; padding: 0; border: 0; border-radius: 6px; overflow: hidden; background: #eef3eb; cursor: zoom-in; }
.photo-open img { display: block; width: 100%; aspect-ratio: 4 / 3; object-fit: cover; }
.merchant-link-row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.merchant-links { margin-top: 16px; }
.merchant-link-row a, .merchant-link-row button { display: inline-flex; min-height: 36px; align-items: center; border: 1px solid var(--color-line, #dce5df); background: var(--color-surface, #fff); border-radius: 6px; padding: 6px 10px; font: inherit; font-size: 12px; color: var(--color-primary, #176b5b); text-decoration: none; cursor: pointer; }
.merchant-link-row a:hover, .merchant-link-row button:hover { background: #eef3eb; border-color: #a7bca4; }
.merchant-search { margin-top: 16px; padding-top: 14px; border-top: 1px dashed var(--color-line, #dce5df); }
.search-keyword { user-select: text; }
.merchant-card a:focus-visible, .merchant-card button:focus-visible { outline: 2px solid var(--color-primary, #176b5b); outline-offset: 3px; }
.merchant-preview { width: min(900px, calc(100vw - 32px)); max-height: calc(100dvh - 40px); border: 0; border-radius: 10px; padding: 18px; color: var(--color-ink, #203c38); }
.merchant-preview::backdrop { background: rgba(15, 35, 30, .72); }
.merchant-preview img { display: block; max-width: 100%; max-height: 70dvh; margin: 12px auto; object-fit: contain; }
.merchant-preview p { font-size: 13px; }
.preview-close { display: block; margin-left: auto; padding: 8px 12px; background: #eef3eb; border: 1px solid #dce5df; border-radius: 6px; color: #176b5b; cursor: pointer; }
@media (max-width: 600px) {
  .merchant-heading { flex-wrap: wrap; gap: 10px; padding: 12px; }
  .merchant-heading > div { width: 100%; }
  .merchant-estimate { display: flex; align-items: baseline; gap: 10px; text-align: left; }
  .merchant-estimate strong { max-width: none; }
  .merchant-body { padding: 10px 12px 14px; }
  .merchant-photos { gap: 6px; }
}
</style>
