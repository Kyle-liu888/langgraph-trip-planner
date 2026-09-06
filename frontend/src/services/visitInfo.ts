import api from './api'
import type { Attraction } from '@/types'

export interface OfficialVisitSource {
  source_name: string
  verified_at: string
  reservation_note: string
  links: { purpose: 'reservation' | 'price'; label: string; url: string }[]
}
export interface VisitInfo {
  status: 'available' | 'no_data' | 'unmatched' | 'permission_denied' | 'timeout' | 'unavailable'
  match_status: 'matched' | 'unmatched' | 'unknown'
  poi_id: string | null
  visit_date: string | null
  opening: { today: string | null; today_date: string | null; regular: string | null; scope: 'reference_only' }
  source_name: string
  source_url: string | null
  fetched_at: string
  upstream_updated_at: null
  official: OfficialVisitSource | null
  notice: string
}
export interface VisitStop { place: Attraction; visitDate: string }
export const visitKey = (city: string, stop: VisitStop): string =>
  JSON.stringify([city, stop.place.poi_id || '', stop.place.name, stop.place.location?.longitude, stop.place.location?.latitude, stop.visitDate])
export function safeExternalUrl(value?: string | null): string | undefined {
  if (!value) return undefined
  try {
    const url = new URL(value)
    return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password ? url.href : undefined
  } catch { return undefined }
}
export function visitStatusLabel(info?: VisitInfo): string {
  if (!info) return '正在查询开放时间…'
  const labels: Record<VisitInfo['status'], string> = {
    available: '', no_data: '暂无适用于游玩日期的开放时间',
    unmatched: '未确认地点匹配，暂无可靠开放时间',
    permission_denied: '开放时间暂不可获取（接口权限不可用）',
    timeout: '开放时间查询超时，可稍后刷新重试',
    unavailable: '开放时间暂不可获取，请查看官方说明',
  }
  return labels[info.status]
}
export function guideLinks(city: string, name: string) {
  const keyword = city.trim() + ' ' + name.trim() + ' 游玩攻略'
  return {
    keyword,
    // Verified in a browser on 2026-09-06: search title and input match the keyword.
    xiaohongshu: 'https://www.xiaohongshu.com/search_result?' + new URLSearchParams({ keyword }),
    // Dianping's native search could not be verified; this is explicitly an external search.
    dianping: 'https://www.baidu.com/s?' + new URLSearchParams({ wd: 'site:dianping.com ' + keyword }),
  }
}
export const VISIT_NOTICE = '节假日、临时闭馆以官方公告为准；本次规划未自动校验闭馆日期'
export function unavailableVisit(): VisitInfo {
  return { status: 'unavailable', match_status: 'unknown', poi_id: null, visit_date: null,
    opening: { today: null, today_date: null, regular: null, scope: 'reference_only' },
    source_name: '', source_url: null, fetched_at: '', upstream_updated_at: null, official: null, notice: VISIT_NOTICE }
}
let activeRequests = 0
const waiting: (() => void)[] = []
function takeSlot(): Promise<void> {
  if (activeRequests < 3) { activeRequests++; return Promise.resolve() }
  return new Promise(resolve => waiting.push(resolve))
}
function releaseSlot() {
  const next = waiting.shift()
  if (next) next()
  else activeRequests--
}
export async function loadVisitInfos(city: string, stops: VisitStop[],
  update: (key: string, info: VisitInfo) => void, stopped: () => boolean = () => false): Promise<void> {
  const queue = [...new Map(stops.map(stop => [visitKey(city, stop), stop])).entries()]
  let cursor = 0
  async function worker() {
    while (!stopped() && cursor < queue.length) {
      const [key, { place, visitDate }] = queue[cursor++]
      let info = unavailableVisit()
      await takeSlot()
      if (stopped()) { releaseSlot(); return }
      try {
        const result = await api.get('/api/poi/visit-info', {
          params: { name: place.name, city, poi_id: place.poi_id || undefined,
            longitude: place.location?.longitude, latitude: place.location?.latitude,
            visit_date: visitDate || undefined },
          timeout: 20000, // Legacy no-ID records may require two bounded upstream requests.
        })
        if (result.data?.data) info = result.data.data
      } catch { /* Optional facts must not interrupt the plan, maps or guides. */ }
      finally { releaseSlot() }
      if (!stopped()) update(key, info)
    }
  }
  await Promise.all(Array.from({ length: Math.min(3, queue.length) }, worker))
}
