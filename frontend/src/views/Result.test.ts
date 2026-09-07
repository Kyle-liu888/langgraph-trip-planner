// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createApp, nextTick, type App } from 'vue'
import Antd from 'ant-design-vue'
import Result from './Result.vue'
import type { TripRecord } from '@/services/trips'
import { merchantKey, unavailableMerchant, type MerchantStop } from '@/services/merchantInfo'

const mocks = vi.hoisted(() => ({ scroll: vi.fn(), save: vi.fn(), loadPhotos: vi.fn(), loadVisits: vi.fn(), loadMerchants: vi.fn() }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))
vi.mock('@/stores/trips', () => ({ useTrips: () => ({ upsert: vi.fn() }) }))
vi.mock('@/services/trips', async importOriginal => ({
  ...await importOriginal<typeof import('@/services/trips')>(), saveTripPlan: mocks.save,
}))
vi.mock('@/services/photos', async importOriginal => ({
  ...await importOriginal<typeof import('@/services/photos')>(), loadPlacePhotos: mocks.loadPhotos,
}))
vi.mock('@/services/visitInfo', async importOriginal => ({
  ...await importOriginal<typeof import('@/services/visitInfo')>(), loadVisitInfos: mocks.loadVisits,
}))
vi.mock('@/services/merchantInfo', async importOriginal => ({
  ...await importOriginal<typeof import('@/services/merchantInfo')>(), loadMerchantInfos: mocks.loadMerchants,
}))
vi.mock('@amap/amap-jsapi-loader', () => ({ default: { load: () => new Promise(() => {}) } }))

describe('itinerary navigation and presentation', () => {
  let app: App
  let root: HTMLDivElement
  let reducedMotion = false
  const record = {
    id: 'test-trip', revision: 1, plan: {
      city: '北京', start_date: '2026-09-07', end_date: '2026-09-08', overall_suggestions: '出发前核验开放时间',
      budget: { total_attractions: 0, total_hotels: 300, total_meals: 100, total_transportation: 50, total: 450 },
      days: [0, 1].map(day => ({
        day_index: day, date: `2026-09-0${day + 7}`, description: '城市漫步', transportation: '公共交通', accommodation: '酒店', meals: [],
        attractions: [{ name: '颐和园', address: '北京市海淀区', visit_duration: 120, description: '湖畔散步', ticket_price: 0 }],
      })),
    },
  } as unknown as TripRecord

  beforeEach(async () => {
    vi.clearAllMocks(); reducedMotion = false
    vi.stubGlobal('matchMedia', vi.fn((query: string) => ({
      matches: query.includes('prefers-reduced-motion') && reducedMotion, addListener: vi.fn(), removeListener: vi.fn(),
    })))
    Element.prototype.scrollIntoView = mocks.scroll
    mocks.loadPhotos.mockResolvedValue(undefined)
    mocks.loadVisits.mockResolvedValue(undefined)
    mocks.loadMerchants.mockResolvedValue(undefined)
    root = document.createElement('div'); document.body.append(root)
    app = createApp(Result, { record }).use(Antd); app.mount(root)
    await vi.waitFor(() => expect(root.querySelector('nav')).not.toBeNull())
    await nextTick()
  })
  afterEach(() => { app.unmount(); root.remove(); document.documentElement.scrollTop = 0; vi.restoreAllMocks(); vi.unstubAllGlobals() })

  it('provides accessible chapter and day navigation without a second sidebar', async () => {
    const nav = root.querySelector('nav[aria-label="行程章节"]')!
    expect(root.querySelector('.side-nav')).toBeNull()
    const dayButton = Array.from(nav.querySelectorAll('button')).find(button => button.textContent?.includes('第 2 天'))!
    dayButton.click(); await nextTick()
    expect(dayButton.getAttribute('aria-current')).toBe('location')
    expect(mocks.scroll).toHaveBeenCalledWith({ behavior: 'smooth', block: 'start' })
    expect(root.querySelector('#day-1')?.classList.contains('ant-collapse-item-active')).toBe(true)
    expect(mocks.save).not.toHaveBeenCalled()
  })

  it('respects reduced motion when navigating between sections', async () => {
    reducedMotion = true
    root.querySelector<HTMLButtonElement>('nav button')!.click()
    expect(mocks.scroll).toHaveBeenCalledWith({ behavior: 'auto', block: 'start' })
  })

  it('renders a named keyboard-focusable BackTop button through the real Ant Design component', async () => {
    vi.stubGlobal('scrollY', 500)
    document.documentElement.scrollTop = 500
    const scrollTo = vi.spyOn(window, 'scrollTo').mockImplementation(() => {})
    window.dispatchEvent(new Event('scroll'))
    document.dispatchEvent(new Event('scroll'))
    const button = root.querySelector<HTMLButtonElement>('button.back-top-button[aria-label="回到页面顶部"]')!
    expect(button).not.toBeNull()
    // jsdom has no viewport layout; real-browser QA covers scroll visibility.
    // Here we verify that BackTop forwards naming/shape to its actual button,
    // rather than silently discarding a nested default-slot button.
    expect(button.type).toBe('button')
    expect(button.getAttribute('title')).toBe('回到页面顶部')
    expect(button.querySelector('button')).toBeNull()
    expect(button.querySelector('[aria-hidden="true"]')?.textContent).toBe('↑')
    button.focus()
    expect(document.activeElement).toBe(button)
    button.click()
    await vi.waitFor(() => expect(scrollTo.mock.calls.some(([x, y]) => x === 0 && y === 0) || document.documentElement.scrollTop === 0).toBe(true))
  })

  it('preserves budget caveats and edit/cancel actions in the new layout', async () => {
    expect(root.textContent).toContain('景点门票（估算）')
    expect(root.textContent).toContain('¥0（仅预算参考）')
    expect(root.textContent).toContain('是否免费、实际票价及优惠以官方政策为准')
    Array.from(root.querySelectorAll('button')).find(button => button.textContent?.includes('编辑行程'))!.click()
    await nextTick()
    expect(root.querySelector('.attraction-edit')).not.toBeNull()
    Array.from(root.querySelectorAll('button')).find(button => button.textContent?.includes('取消编辑'))!.click()
    await nextTick()
    expect(root.querySelector('.attraction-edit')).toBeNull()
    expect(mocks.save).not.toHaveBeenCalled()
  })

  it('loads only expanded-day merchants and supplements maps without writing source facts into saved history', async () => {
    app.unmount()
    const populated = JSON.parse(JSON.stringify(record)) as TripRecord
    const hotel = { name: '庭院酒店(王府井店)', address: '王府井大街1号', type: '酒店', price_range: '约300元',
      estimated_cost: 300, distance: '步行可达', rating: '9.9' }
    populated.plan!.days[0].hotel = hotel
    populated.plan!.days[1].hotel = { ...hotel }
    populated.plan!.days[0].meals = [{ type: 'lunch', name: '烤鸭馆(王府井店)', address: '王府井大街2号', estimated_cost: 0 }]
    populated.plan!.days[1].meals = [{ type: 'dinner', name: '面馆(前门店)', address: '前门大街3号' }]
    const original = JSON.stringify(populated.plan)
    mocks.loadMerchants.mockClear()
    mocks.loadMerchants.mockImplementation(async (city, stops: MerchantStop[], update) => {
      for (const stop of stops) update(merchantKey(city, stop), { ...unavailableMerchant(''), match_status: 'matched', data_status: 'available',
        place: { poi_id: 'B1', name: stop.merchant.name, city, address: '来源新地址', location: { longitude: 116.4, latitude: 39.9 } },
        source: { name: '高德地图', url: 'https://uri.amap.com/marker?poiid=B1', queried_at: '2026-09-07T12:00:00+08:00' }, rating: '4.7',
      })
    })
    app = createApp(Result, { record: populated }).use(Antd); app.mount(root)
    await vi.waitFor(() => expect(root.textContent).toContain('高德参考评分4.7'))
    expect(mocks.loadMerchants.mock.calls[0][1].map((stop: MerchantStop) => stop.merchant.name)).toEqual([hotel.name, '烤鸭馆(王府井店)'])
    expect(root.textContent).not.toContain('9.9')
    expect(root.querySelector('.daily-map-count')?.textContent).toContain('2 个地点')
    expect(JSON.stringify(populated.plan)).toBe(original)
    const dayButton = Array.from(root.querySelectorAll('nav button')).find(button => button.textContent?.includes('第 2 天')) as HTMLButtonElement
    dayButton.click(); await nextTick()
    await vi.waitFor(() => expect(mocks.loadMerchants.mock.calls.at(-1)![1].map((stop: MerchantStop) => stop.merchant.name)).toEqual([hotel.name, '面馆(前门店)']))
    mocks.save.mockResolvedValue({ ...populated, revision: 2 })
    Array.from(root.querySelectorAll('button')).find(button => button.textContent?.includes('编辑行程'))!.click(); await nextTick()
    Array.from(root.querySelectorAll('button')).find(button => button.textContent?.includes('保存修改'))!.click()
    await vi.waitFor(() => expect(mocks.save).toHaveBeenCalled())
    expect(JSON.stringify(mocks.save.mock.calls[0][1])).toBe(original)
  })
})
