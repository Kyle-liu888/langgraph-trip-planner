// @vitest-environment jsdom
import { afterEach, expect, it, vi } from 'vitest'
import { createApp, h, nextTick, reactive, type App } from 'vue'
import MerchantCard from './MerchantCard.vue'
import { unavailableMerchant, type MerchantInfo, type MerchantKind } from '@/services/merchantInfo'
let app: App | undefined
let root: HTMLDivElement
function mount(info?: MerchantInfo, kind: MerchantKind = 'food', name = '烤鸭馆（王府井店）') {
  const props = reactive({ city: '北京', kind, merchant: { name, address: '行程地址', rating: '9.9' }, estimatedCost: 0,
    description: '试试特色菜', hotelType: '', distance: '', info })
  root = document.createElement('div'); document.body.append(root)
  app = createApp({ render: () => h(MerchantCard, props) }); app.mount(root)
  return props
}
const sourced = (): MerchantInfo => ({ ...unavailableMerchant(''), match_status: 'matched', data_status: 'available',
  place: { poi_id: 'B1', name: '烤鸭馆（王府井店）', city: '北京', address: '核验后的地址', location: null },
  rating: '4.7', food_tags: ['烤鸭'], photos: [{ url: 'https://photos.example.test/a.jpg', title: '图片原始说明' }],
  source: { name: '高德地图', url: 'https://uri.amap.com/marker?poiid=B1', queried_at: '2026-09-07T12:00:00+08:00' },
  links: [{ platform: 'dianping', label: '门店', url: 'https://www.dianping.com/shop/abc', verified_at: '2026-09-01' }],
  queried_at: '2026-09-07T12:00:00+08:00',
})
afterEach(() => { app?.unmount(); root?.remove(); vi.restoreAllMocks() })
async function openHint() {
  root.querySelector<HTMLButtonElement>('button[aria-label="门店资料说明"]')!.click()
  await nextTick()
  return document.body.querySelector<HTMLElement>('.info-hint-panel')!
}

it('keeps budget estimates, hides unsupported model hotel ratings, and retains XHS during failure', async () => {
  mount(unavailableMerchant(), 'hotel')
  expect(root.textContent).toContain('住宿预算估算¥0')
  expect(root.textContent).not.toContain('零估算不代表免费')
  expect(root.textContent).toContain('暂无可核验评分')
  expect(root.textContent).not.toContain('9.9')
  expect(root.textContent).toContain('行程建议：试试特色菜')
  expect(root.textContent).toContain('小红书搜这家酒店')
  expect(root.querySelector('a[href*="baidu.com"]')).toBeNull()
  expect(root.querySelector('[aria-label="平台门店入口"] a')).toBeNull()
  expect(root.textContent).toContain('门店资料暂不可获取，可稍后重试')
  expect((await openHint()).textContent).toContain('零估算不代表免费')
})
it('keeps verified facts and actions visible while one clickable help owns the detailed source explanations', async () => {
  mount({ ...sourced(), message: '门店已核验，资料仅供参考，出行前请核验所有信息' })
  expect(root.textContent).toContain('来源地址核验后的地址')
  expect(root.textContent).toContain('高德参考评分4.7')
  expect(root.textContent).toContain('高德餐饮特色烤鸭')
  expect(root.textContent).toContain('餐饮预算估算¥0')
  expect(root.textContent).toContain('门店参考图 · 高德')
  expect(root.querySelectorAll('button[aria-label="门店资料说明"]')).toHaveLength(1)
  expect(root.querySelector('figcaption')).toBeNull()
  for (const secondary of ['不是完整菜单', '查询时间：', '人工核验日期：', '上游更新时间：', '零估算不代表免费',
    '非实时评价', '拍摄时间', '搜索词：', '可能要求登录', '门店已核验，资料仅供参考']) expect(root.textContent).not.toContain(secondary)
  expect(root.querySelector('.merchant-status')).toBeNull()
  for (const link of root.querySelectorAll('a')) {
    expect(link.target).toBe('_blank'); expect(link.rel).toBe('noopener noreferrer')
    expect(new URL(link.href).protocol).toMatch(/^https?:$/)
  }
  const hint = await openHint()
  for (const secondary of ['不是完整菜单', '查询时间：2026/09/07', '人工核验日期：大众点评 2026-09-01',
    '上游更新时间：未提供', '零估算不代表免费', '并非实时评价', '拍摄时间', '搜索词：北京 烤鸭馆（王府井店） 探店',
    '可能要求登录', '门店已核验，资料仅供参考']) expect(hint.textContent).toContain(secondary)
})
it('keeps generic arrangements brief and places breakfast inclusion uncertainty in help', async () => {
  mount(undefined, 'food', '酒店自助早餐')
  expect(root.textContent).toContain('尚未指定具体门店')
  expect(root.textContent).not.toContain('是否包含早餐请向住处确认')
  expect(root.querySelector('a')).toBeNull()
  expect(root.querySelector('img')).toBeNull()
  expect((await openHint()).textContent).toContain('是否包含早餐请向住处确认')
})
it('places unverified hotel type and distance inside the single help panel', async () => {
  const props = mount(sourced(), 'hotel', '庭院酒店(王府井店)')
  props.hotelType = '经济型酒店'
  props.distance = '步行10分钟'
  await nextTick()
  expect(root.textContent).not.toContain('经济型酒店')
  expect(root.textContent).not.toContain('步行10分钟')
  expect((await openHint()).textContent).toContain('经济型酒店；步行10分钟（行程建议，未独立核验）')
})
it('filters unsafe images, untrusted platform links, unsupported platform types and homepages', () => {
  const info = sourced()
  info.photos = [{ url: 'javascript:alert(1)', title: 'bad' }]
  info.links.push({ platform: 'meituan', label: 'bad', url: 'https://evil.test/shop/a', verified_at: '' },
    { platform: 'ctrip', label: 'wrong-kind', url: 'https://hotels.ctrip.com/hotels/a.html', verified_at: '' },
    { platform: 'dianping', label: 'home', url: 'https://www.dianping.com/', verified_at: '' })
  mount(info)
  expect(root.querySelector('img')).toBeNull()
  expect(root.querySelector('[href*="evil.test"]')).toBeNull()
  expect(root.querySelector('[href*="ctrip.com"]')).toBeNull()
  expect(root.querySelector('[href="https://www.dianping.com/"]')).toBeNull()
})
it('caps photos, removes broken images without losing links and opens an accessible preview', async () => {
  HTMLDialogElement.prototype.showModal = vi.fn(function(this: HTMLDialogElement) { this.open = true })
  HTMLDialogElement.prototype.close = vi.fn(function(this: HTMLDialogElement) { this.open = false })
  const info = sourced()
  info.photos = Array.from({ length: 4 }, (_, index) => ({ url: `https://photos.example.test/${index}.jpg`, title: '' }))
  mount(info)
  expect(root.querySelectorAll('.merchant-photos img')).toHaveLength(3)
  root.querySelector<HTMLButtonElement>('.photo-open')!.click(); await nextTick()
  await vi.waitFor(() => expect(root.querySelector('dialog')?.open).toBe(true))
  root.querySelector<HTMLButtonElement>('.preview-close')!.click(); await nextTick()
  expect(root.querySelector('dialog')?.open).toBe(false)
  root.querySelector('.merchant-photos img')!.dispatchEvent(new Event('error')); await nextTick()
  expect(root.querySelector('.merchant-photos img[src$="0.jpg"]')).toBeNull()
  expect(root.textContent).toContain('在大众点评查看门店')
})
it('recomputes searches after an edit and supplies clipboard/manual fallback', async () => {
  HTMLDialogElement.prototype.close = vi.fn()
  const writeText = vi.fn().mockResolvedValue(undefined)
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } })
  const props = mount(unavailableMerchant())
  expect(root.querySelector('.merchant-search .search-keyword')).toBeNull()
  props.merchant.name = '新店 & A/B?（前门店）'; await nextTick()
  root.querySelector<HTMLButtonElement>('.merchant-search button')!.click()
  await vi.waitFor(() => expect(writeText).toHaveBeenCalledWith('北京 新店 & A/B?（前门店） 探店'))
  expect(root.querySelector('.merchant-search .search-keyword')).toBeNull()
  expect(new URL(root.querySelector<HTMLAnchorElement>('.merchant-search a')!.href).searchParams.get('keyword')).toBe('北京 新店 & A/B?（前门店） 探店')
  writeText.mockRejectedValue(new Error('denied'))
  root.querySelector<HTMLButtonElement>('.merchant-search button')!.click()
  await vi.waitFor(() => expect(root.textContent).toContain('复制失败，请选中上方搜索词手动复制'))
  expect(root.querySelector('.merchant-search .search-keyword')?.textContent).toContain('搜索词：北京 新店 & A/B?（前门店） 探店')
})
it.each([
  ['timeout', '门店资料查询超时，可稍后重试'],
  ['permission_denied', '接口权限不可用，暂无法查询门店资料'],
  ['unavailable', '门店资料暂不可获取，可稍后重试'],
  ['no_data', '暂无更多门店资料'],
] as const)('keeps %s operational status outside the help and avoids long server notices', (data_status, label) => {
  mount({ ...sourced(), data_status, message: '服务端返回的长说明不应直接占满卡片' })
  expect(root.querySelector('.merchant-status')?.textContent).toBe(label)
  expect(root.textContent).not.toContain('服务端返回的长说明')
  expect(root.textContent).toContain('小红书搜这家店')
})
it('keeps session expiration visible rather than hiding it inside source information', () => {
  mount(unavailableMerchant('登录已失效，请重新登录后查看门店资料'))
  expect(root.querySelector('.merchant-status')?.textContent).toBe('登录已失效，请重新登录')
})
