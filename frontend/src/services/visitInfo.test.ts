import { beforeEach, expect, it, vi } from 'vitest'
import api from './api'
import { guideLinks, loadVisitInfos, safeExternalUrl, unavailableVisit, visitKey, visitStatusLabel } from './visitInfo'
import type { Attraction } from '@/types'
vi.mock('./api', () => ({ default: { get: vi.fn() } }))
const place: Attraction = { name: '故宫博物院', poi_id: 'B1', address: '', location: { longitude: 116.397, latitude: 39.918 }, description: '', visit_duration: 60 }
beforeEach(() => vi.clearAllMocks())

it('encodes complete keywords and opens Dianping itself without a search-engine redirect', () => {
  const links = guideLinks('北京', '故宫 & A/B?')
  expect(new URL(links.xiaohongshu).searchParams.get('keyword')).toBe('北京 故宫 & A/B? 游玩攻略')
  expect(links.keyword).toBe('北京 故宫 & A/B? 游玩攻略')
  expect(links.dianping).toBe('https://www.dianping.com/')
  expect(new URL(links.dianping).search).toBe('')
  expect(new URL(links.xiaohongshu).host).toBe('www.xiaohongshu.com')
})
it('blocks non-web URLs and embedded credentials', () => {
  for (const value of ['javascript:alert(1)', 'data:text/html,bad', '//evil.com', 'https://user:pass@example.com']) expect(safeExternalUrl(value)).toBeUndefined()
  expect(safeExternalUrl('https://www.dpm.org.cn/')).toBe('https://www.dpm.org.cn/')
})
it('passes date and identity, deduplicates stops and distinguishes edits', async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { data: unavailableVisit() } })
  const stop = { place, visitDate: '2026-09-07' }
  const update = vi.fn()
  await loadVisitInfos('北京', [stop, stop], update)
  expect(api.get).toHaveBeenCalledTimes(1)
  expect(api.get).toHaveBeenCalledWith('/api/poi/visit-info', expect.objectContaining({
    params: { name: place.name, city: '北京', poi_id: 'B1', longitude: 116.397, latitude: 39.918, visit_date: '2026-09-07' },
  }))
  expect(visitKey('北京', stop)).not.toBe(visitKey('北京', { ...stop, place: { ...place, name: '天坛公园' } }))
  expect(visitKey('北京', stop)).not.toBe(visitKey('北京', { ...stop, visitDate: '2026-09-08' }))
  expect(update).toHaveBeenCalledTimes(1)
})
it('limits concurrency across overlapping loads and drops obsolete updates', async () => {
  let active = 0, peak = 0
  vi.mocked(api.get).mockImplementation(async () => {
    active++; peak = Math.max(peak, active)
    await new Promise(resolve => setTimeout(resolve, 2))
    active--
    return { data: { data: unavailableVisit() } }
  })
  const stops = Array.from({ length: 8 }, (_, i) => ({ place: { ...place, poi_id: 'B' + i }, visitDate: '2026-09-07' }))
  let obsolete = false
  const oldUpdate = vi.fn()
  const old = loadVisitInfos('北京', stops, oldUpdate, () => obsolete)
  obsolete = true
  const fresh = vi.fn()
  await Promise.all([old, loadVisitInfos('北京', stops, fresh)])
  expect(peak).toBeLessThanOrEqual(3)
  expect(oldUpdate).not.toHaveBeenCalled()
  expect(fresh).toHaveBeenCalledTimes(8)
})
it('degrades API errors without affecting locally generated guide links', async () => {
  vi.mocked(api.get).mockRejectedValue(new Error('offline'))
  const update = vi.fn()
  await loadVisitInfos('北京', [{ place, visitDate: '' }], update)
  expect(update.mock.calls[0][1].status).toBe('unavailable')
  expect(guideLinks('北京', place.name).xiaohongshu).toContain('search_result')
  expect(visitStatusLabel({ ...unavailableVisit(), status: 'permission_denied' })).toContain('权限')
})
