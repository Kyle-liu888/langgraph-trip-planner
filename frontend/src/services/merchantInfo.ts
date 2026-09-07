import api from './api'
import type { Location } from '@/types'
import { safeExternalUrl } from './visitInfo'

export type MerchantKind = 'food' | 'hotel'
export interface MerchantIdentity { name: string; address?: string; poi_id?: string; location?: Location | null }
export interface MerchantStop { kind: MerchantKind; merchant: MerchantIdentity }
export interface MerchantInfo {
  match_status: 'matched' | 'unmatched' | 'ambiguous' | 'insufficient' | 'generic'
  data_status: 'available' | 'no_data' | 'permission_denied' | 'timeout' | 'unavailable'
  message: string
  place: { poi_id: string; name: string; address: string; city: string; location: Location | null } | null
  photos: { url: string; title: string }[]
  rating: string | null
  food_tags: string[]
  source: { name: string; url: string; queried_at: string } | null
  links: { platform: 'dianping' | 'meituan' | 'ctrip'; label: string; url: string; verified_at: string }[]
  queried_at: string
}

const normalize = (value?: string) => (value || '').trim().replace(/\s+/g, '').replace(/（/g, '(').replace(/）/g, ')')
function snapshotStop(stop: MerchantStop): MerchantStop {
  const { merchant } = stop
  return { kind: stop.kind, merchant: { name: merchant.name, address: merchant.address, poi_id: merchant.poi_id,
    location: merchant.location ? { longitude: merchant.location.longitude, latitude: merchant.location.latitude } : merchant.location } }
}
export function merchantKey(city: string, stop: MerchantStop): string {
  const { merchant, kind } = stop
  return JSON.stringify([kind, normalize(city), normalize(merchant.name), normalize(merchant.address),
    merchant.poi_id || '', merchant.location?.longitude ?? null, merchant.location?.latitude ?? null])
}
export function isGenericMerchant(kind: MerchantKind, city: string, name: string): boolean {
  let text = normalize(name)
  const prefix = normalize(city).replace(/市$/, '')
  if (prefix && text.startsWith(prefix)) text = text.slice(prefix.length)
  const candidates = [text, ...(prefix && normalize(name).startsWith(prefix) && text.startsWith('市') ? [text.slice(1)] : [])]
  if (kind === 'hotel') return candidates.some(value => !value || ['酒店', '民宿', '客栈', '经济型酒店', '舒适型酒店', '高档型酒店', '豪华型酒店',
    '当地酒店', '市中心酒店', '待定酒店', '待定住宿'].includes(value))
  return candidates.some(value => !value || /^第[0-9零〇一二三四五六七八九十百]+天[早午晚]餐$/.test(value) || ['早餐', '午餐', '晚餐',
    '酒店早餐', '酒店自助早餐', '民宿早餐', '客栈早餐', '住宿早餐', '当地小吃', '本地小吃', '当地美食', '本地美食',
    '当地特色小吃', '本地特色小吃', '本地菜午餐', '本地菜晚餐', '当地菜午餐', '当地菜晚餐'].includes(value))
}
export function merchantSearch(city: string, name: string, kind: MerchantKind) {
  const keyword = `${city.trim()} ${name.trim()} ${kind === 'food' ? '探店' : '住宿体验'}`
  return { keyword, url: 'https://www.xiaohongshu.com/search_result?' + new URLSearchParams({ keyword }) }
}
export function safeMerchantLink(value: string, platform: 'amap' | MerchantInfo['links'][number]['platform']): string | undefined {
  const safe = safeExternalUrl(value)
  if (!safe) return undefined
  const url = new URL(safe)
  const domain = { amap: 'amap.com', dianping: 'dianping.com', meituan: 'meituan.com', ctrip: 'ctrip.com' }[platform]
  if (!(url.hostname === domain || url.hostname.endsWith('.' + domain))) return undefined
  if (url.port && !['80', '443'].includes(url.port) || /[\u0000-\u001f]/.test(value)) return undefined
  // Only known detail-page shapes, not homepages, login pages or site search.
  if (platform === 'amap') return url.hostname === 'uri.amap.com' && url.pathname === '/marker' && url.searchParams.get('poiid') ? safe : undefined
  const paths = { dianping: /^\/shop\/[A-Za-z0-9_-]+\/?$/, meituan: /^\/(?:meishi|i\/poi|hotel|poi)\/[0-9]+(?:\.html)?\/?$/,
    ctrip: /^\/(?:hotels?|html5\/hotel\/hoteldetail)\/[0-9]+\.html\/?$/ }
  if (!paths[platform].test(url.pathname) && !(platform === 'meituan' && url.hostname === 'hotel.meituan.com' && /^\/[0-9]+\/?$/.test(url.pathname))) return undefined
  if ([...url.searchParams.keys()].some(key => /token|session|password|authorization|cookie|ticket|openid|redirect|return|callback|^code$|^url$/i.test(key))) return undefined
  return safe
}
export function unavailableMerchant(message = '门店资料暂不可获取，可稍后重新打开行程'): MerchantInfo {
  return { match_status: 'unmatched', data_status: 'unavailable', message, place: null, photos: [],
    rating: null, food_tags: [], source: null, links: [], queried_at: '' }
}
export function merchantStatus(info?: MerchantInfo): string {
  if (!info) return '正在核验门店资料…'
  if (info.message) return info.message
  if (info.match_status !== 'matched') return {
    generic: '这是用餐安排，尚未指定具体门店', unmatched: '未找到可确认的同一家门店',
    ambiguous: '存在多家候选门店，暂不附上来源', insufficient: '门店身份信息不足，暂不附上来源',
  }[info.match_status]
  return { available: '', no_data: '暂无更多门店资料', permission_denied: '门店资料暂不可获取（接口权限不可用）',
    timeout: '门店资料查询超时，可稍后重新打开行程', unavailable: '门店资料暂不可获取' }[info.data_status]
}
export function merchantQueryTime(value?: string): string {
  if (!value) return ''
  const date = new Date(value)
  if (!Number.isFinite(date.getTime())) return '未知'
  return new Intl.DateTimeFormat('zh-CN', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit',
    day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).format(date) + '（北京时间）'
}

const TTL_MS = 15 * 60 * 1000
const cache = new Map<string, { expires: number; info: MerchantInfo }>()
const pending = new Map<string, Promise<MerchantInfo>>()
let generation = 0
let active = 0
const waiting: (() => void)[] = []
function takeSlot(): Promise<void> {
  if (active < 3) { active++; return Promise.resolve() }
  return new Promise(resolve => waiting.push(resolve))
}
function releaseSlot() {
  const next = waiting.shift()
  if (next) next()
  else active--
}

async function lookup(city: string, stop: MerchantStop): Promise<MerchantInfo> {
  // A request may wait behind other lookups while the user edits the original object.
  // Bind both the cache key and HTTP parameters to the same immutable identity.
  const snapshot = snapshotStop(stop)
  const key = merchantKey(city, snapshot)
  const cached = cache.get(key)
  if (cached && cached.expires > Date.now()) return cached.info
  cache.delete(key)
  const inFlight = pending.get(key)
  if (inFlight) return inFlight
  const requestGeneration = generation
  const request = (async () => {
    await takeSlot()
    let info = unavailableMerchant()
    try {
      if (requestGeneration !== generation) return info
      const { merchant, kind } = snapshot
      const response = await api.get('/api/poi/merchant-info', {
        params: { kind, city, name: merchant.name, address: merchant.address || '', poi_id: merchant.poi_id || undefined,
          longitude: merchant.location?.longitude, latitude: merchant.location?.latitude }, timeout: 20000,
      })
      if (response.data?.data) {
        info = response.data.data
        if (requestGeneration === generation && ['available', 'no_data'].includes(info.data_status)) {
          cache.set(key, { expires: Date.now() + TTL_MS, info })
          while (cache.size > 512) cache.delete(cache.keys().next().value!)
        }
      }
    } catch (error) {
      // Shared API interceptors expire invalid sessions; never print credentials/config.
      if (error instanceof Error && error.message.includes('登录')) info = unavailableMerchant('登录已失效，请重新登录后查看门店资料')
    } finally { releaseSlot() }
    return info
  })()
  pending.set(key, request)
  try { return await request } finally { if (pending.get(key) === request) pending.delete(key) }
}

/** Display-only enrichment. Never writes properties on the provided itinerary objects. */
export async function loadMerchantInfos(city: string, stops: MerchantStop[], update: (key: string, info: MerchantInfo) => void,
  stopped: () => boolean = () => false): Promise<void> {
  const unique = [...new Map(stops.map(stop => {
    const snapshot = snapshotStop(stop)
    return [merchantKey(city, snapshot), snapshot] as const
  })).entries()]
  let cursor = 0
  async function worker() {
    while (!stopped() && cursor < unique.length) {
      const [key, stop] = unique[cursor++]
      const info = isGenericMerchant(stop.kind, city, stop.merchant.name)
        ? { ...unavailableMerchant(`这是${stop.kind === 'hotel' ? '住宿' : '用餐'}安排，尚未指定具体门店`), match_status: 'generic' as const, data_status: 'no_data' as const }
        : await lookup(city, stop)
      if (!stopped()) update(key, info)
    }
  }
  await Promise.all(Array.from({ length: Math.min(3, unique.length) }, worker))
}

/** Public merchant facts only; the application calls this when the active account changes. */
export function clearMerchantCache() { generation++; cache.clear(); pending.clear() }
