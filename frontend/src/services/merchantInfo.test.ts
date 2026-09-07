import { beforeEach, expect, it, vi } from 'vitest'
import api from './api'
import { clearMerchantCache, isGenericMerchant, loadMerchantInfos, merchantKey, merchantSearch, safeMerchantLink,
  unavailableMerchant, type MerchantStop } from './merchantInfo'
vi.mock('./api', () => ({ default: { get: vi.fn() } }))
const stop: MerchantStop = { kind: 'food', merchant: { name: '烤鸭馆（王府井店）', address: '王府井大街 1 号', location: { longitude: 116.4, latitude: 39.9 } } }
beforeEach(() => { vi.clearAllMocks(); clearMerchantCache(); vi.useRealTimers() })

it('keeps all identity evidence in the key and encodes the exact search, including branch punctuation', () => {
  const base = merchantKey('北京', stop)
  for (const changed of [
    { ...stop, kind: 'hotel' as const },
    { ...stop, merchant: { ...stop.merchant, name: '烤鸭馆(前门店)' } },
    { ...stop, merchant: { ...stop.merchant, address: '王府井大街 2 号' } },
    { ...stop, merchant: { ...stop.merchant, location: { longitude: 116.5, latitude: 39.9 } } },
  ]) expect(merchantKey('北京', changed)).not.toBe(base)
  expect(merchantKey('上海', stop)).not.toBe(base)
  const search = merchantSearch('北京', '餐馆 & A/B?（一店）', 'food')
  expect(new URL(search.url).searchParams.get('keyword')).toBe('北京 餐馆 & A/B?（一店） 探店')
  expect(merchantSearch('北京', '酒店(一店)', 'hotel').keyword).toBe('北京 酒店(一店) 住宿体验')
})
it('rejects arbitrary schemes, credentials, lookalike hosts and platform homepages', () => {
  for (const url of ['javascript:alert(1)', 'https://user:pass@www.dianping.com/shop/a', 'https://www.dianping.com/',
    'https://m.dianping.com/dphome', 'https://www.dianping.com.evil.test/shop/a', 'https://evil.test/shop/a',
    'https://www.dianping.com/search/keyword/2/0/shop', 'https://account.dianping.com/pclogin', 'https://www.dianping.com/shop/a?token=secret'])
    expect(safeMerchantLink(url, 'dianping')).toBeUndefined()
  expect(safeMerchantLink('https://www.dianping.com/shop/a', 'dianping')).toContain('/shop/a')
  expect(safeMerchantLink('https://uri.amap.com/marker?poiid=B1', 'amap')).toContain('poiid=B1')
  expect(safeMerchantLink('https://uri.amap.com/marker?name=only-name', 'amap')).toBeUndefined()
  expect(safeMerchantLink('https://hotels.ctrip.com/hotels/123.html', 'ctrip')).toBeDefined()
  expect(safeMerchantLink('https://hotel.meituan.com/123/', 'meituan')).toBeDefined()
})
it('skips generic food arrangements without HTTP or fabricated store information', async () => {
  const update = vi.fn()
  for (const name of ['早餐', '午餐', '晚餐', '酒店早餐', '酒店自助早餐', '当地小吃', '北京本地菜午餐', '第1天早餐',
    '本地特色小吃', '当地菜午餐', '当地菜晚餐']) {
    expect(isGenericMerchant('food', '北京', name)).toBe(true)
    await loadMerchantInfos('北京', [{ kind: 'food', merchant: { name } }], update)
  }
  expect(isGenericMerchant('food', '北京', '酒店早餐餐厅(王府井店)')).toBe(false)
  expect(isGenericMerchant('hotel', '北京', '北京市中心酒店')).toBe(true)
  expect(isGenericMerchant('hotel', '北京', '酒店(王府井店)')).toBe(false)
  expect(api.get).not.toHaveBeenCalled()
  expect(update.mock.calls.every(([, info]) => info.match_status === 'generic')).toBe(true)
})
it('deduplicates in-flight lookups, caches repeated hotels and never mutates the plan object', async () => {
  const result = { ...unavailableMerchant(), match_status: 'matched', data_status: 'available' }
  vi.mocked(api.get).mockResolvedValue({ data: { data: result } })
  const before = JSON.stringify(stop)
  const update = vi.fn()
  await Promise.all([loadMerchantInfos('北京', [stop, stop], update), loadMerchantInfos('北京', [stop], update)])
  await loadMerchantInfos('北京', [stop], update)
  expect(api.get).toHaveBeenCalledTimes(1)
  expect(update).toHaveBeenCalledTimes(3)
  expect(JSON.stringify(stop)).toBe(before)
  expect(api.get).toHaveBeenCalledWith('/api/poi/merchant-info', expect.objectContaining({ params: {
    kind: 'food', city: '北京', name: stop.merchant.name, address: stop.merchant.address,
    poi_id: undefined, longitude: 116.4, latitude: 39.9,
  }, timeout: 20000 }))
})
it('expires cache at fifteen minutes', async () => {
  const now = vi.spyOn(Date, 'now').mockReturnValue(1000)
  vi.mocked(api.get).mockResolvedValue({ data: { data: { ...unavailableMerchant(), data_status: 'no_data' } } })
  await loadMerchantInfos('北京', [stop], vi.fn())
  now.mockReturnValue(1000 + 15 * 60 * 1000)
  await loadMerchantInfos('北京', [stop], vi.fn())
  expect(api.get).toHaveBeenCalledTimes(2)
  now.mockRestore()
})
it('limits concurrent loads to three and discards stale responses', async () => {
  let active = 0, peak = 0
  vi.mocked(api.get).mockImplementation(async () => {
    active++; peak = Math.max(peak, active)
    await new Promise(resolve => setTimeout(resolve, 2))
    active--
    return { data: { data: unavailableMerchant() } }
  })
  const stops = Array.from({ length: 9 }, (_, index) => ({ ...stop, merchant: { ...stop.merchant, name: '门店' + index } }))
  let stale = false
  const oldUpdate = vi.fn(), freshUpdate = vi.fn()
  const old = loadMerchantInfos('北京', stops, oldUpdate, () => stale)
  stale = true
  await Promise.all([old, loadMerchantInfos('北京', stops, freshUpdate)])
  expect(peak).toBeLessThanOrEqual(3)
  expect(oldUpdate).not.toHaveBeenCalled()
  expect(freshUpdate).toHaveBeenCalledTimes(9)
})
it('degrades failed requests without swallowing the login instruction or caching transport errors', async () => {
  vi.mocked(api.get).mockRejectedValue(new Error('登录已失效，请重新登录'))
  const update = vi.fn()
  await loadMerchantInfos('北京', [stop], update)
  await loadMerchantInfos('北京', [stop], update)
  expect(api.get).toHaveBeenCalledTimes(2)
  expect(update.mock.calls[0][1].message).toContain('重新登录')
  expect(merchantSearch('北京', stop.merchant.name, stop.kind).url).toContain('xiaohongshu.com')
})
it('retries transient upstream statuses on re-expansion instead of caching a timeout or permission failure', async () => {
  const update = vi.fn()
  for (const data_status of ['timeout', 'permission_denied', 'unavailable']) {
    vi.mocked(api.get).mockResolvedValue({ data: { data: { ...unavailableMerchant(), data_status } } })
    await loadMerchantInfos('北京', [stop], update)
    await loadMerchantInfos('北京', [stop], update)
  }
  expect(api.get).toHaveBeenCalledTimes(6)
})
it('does not reuse or repopulate a previous account generation cache after clearing', async () => {
  const resolvers: ((value: unknown) => void)[] = []
  vi.mocked(api.get).mockImplementation(() => new Promise(resolve => resolvers.push(resolve)))
  const old = loadMerchantInfos('北京', [stop], vi.fn())
  await vi.waitFor(() => expect(resolvers).toHaveLength(1))
  clearMerchantCache()
  const current = loadMerchantInfos('北京', [stop], vi.fn())
  await vi.waitFor(() => expect(resolvers).toHaveLength(2))
  resolvers[0]({ data: { data: { ...unavailableMerchant(), data_status: 'available', rating: 'old' } } })
  await old
  resolvers[1]({ data: { data: { ...unavailableMerchant(), data_status: 'available', rating: 'new' } } })
  await current
  const update = vi.fn()
  await loadMerchantInfos('北京', [stop], update)
  expect(api.get).toHaveBeenCalledTimes(2)
  expect(update.mock.calls[0][1].rating).toBe('new')
})
it('snapshots identities before queued requests so edits cannot cache one branch under another branch key', async () => {
  const resolvers: ((value: unknown) => void)[] = []
  vi.mocked(api.get).mockImplementation(() => new Promise(resolve => resolvers.push(resolve)))
  const occupied = loadMerchantInfos('北京', [0, 1, 2].map(index => ({ kind: 'food', merchant: { name: '占用名额店' + index } })), vi.fn())
  await vi.waitFor(() => expect(resolvers).toHaveLength(3))
  const editable: MerchantStop = JSON.parse(JSON.stringify(stop))
  const originalKey = merchantKey('北京', editable)
  const update = vi.fn()
  const queued = loadMerchantInfos('北京', [editable], update)
  editable.merchant.name = '烤鸭馆(前门店)'
  editable.merchant.address = '前门大街99号'
  editable.merchant.location!.longitude = 117
  const response = { data: { data: { ...unavailableMerchant(), data_status: 'available' } } }
  for (const resolve of resolvers.slice(0, 3)) resolve(response)
  await vi.waitFor(() => expect(resolvers).toHaveLength(4))
  expect(vi.mocked(api.get).mock.calls[3][1]?.params).toMatchObject({
    name: stop.merchant.name, address: stop.merchant.address, longitude: 116.4,
  })
  resolvers[3](response)
  await Promise.all([occupied, queued])
  expect(update.mock.calls[0][0]).toBe(originalKey)
  expect(editable.merchant.name).toBe('烤鸭馆(前门店)')
  await loadMerchantInfos('北京', [stop], vi.fn())
  expect(api.get).toHaveBeenCalledTimes(4)
})
