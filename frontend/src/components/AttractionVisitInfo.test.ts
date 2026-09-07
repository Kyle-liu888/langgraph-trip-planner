// @vitest-environment jsdom
import { afterEach, expect, it, vi } from 'vitest'
import { createApp, h, nextTick, reactive, type App } from 'vue'
import AttractionVisitInfo from './AttractionVisitInfo.vue'
import { unavailableVisit, type VisitInfo } from '@/services/visitInfo'
let app: App | undefined
let root: HTMLDivElement
function mount(info?: VisitInfo, ticketPrice = 0) {
  const props = reactive({ city: '北京', name: '故宫博物院', visitDate: '2026-09-07', ticketPrice, info, editing: false })
  root = document.createElement('div')
  document.body.append(root)
  app = createApp({ render: () => h(AttractionVisitInfo, props) })
  app.mount(root)
  return props
}
async function openHint(label: string) {
  root.querySelector<HTMLButtonElement>(`button[aria-label="${label}"]`)!.click()
  await nextTick()
  return document.body.querySelector<HTMLElement>('.info-hint-panel[role="dialog"]')!
}
function copyButton() { return root.querySelector<HTMLButtonElement>('.guide-primary button')! }
function expectSafeLinks(container: ParentNode) {
  for (const link of container.querySelectorAll<HTMLAnchorElement>('a')) {
    expect(link.target).toBe('_blank')
    expect(link.rel).toBe('noopener noreferrer')
    expect(new URL(link.href).protocol).toMatch(/^https?:$/)
  }
}
afterEach(() => { app?.unmount(); root?.remove(); vi.restoreAllMocks() })

it('keeps the budget and essential actions visible while explanations and fallback links open on demand', async () => {
  mount(unavailableVisit())
  expect(root.textContent).toContain('门票预算估算：¥0')
  expect(root.textContent).not.toContain('仅预算参考')
  expect(root.textContent).toContain('暂无已核验官方入口')
  expect(root.textContent).toContain('开放时间暂不可获取')
  expect(root.textContent).toContain('小红书攻略搜索')
  expect(root.textContent).toContain('大众点评官网')
  expect(root.textContent).toContain('复制搜索词')
  expect(root.textContent).not.toContain('站外搜索')
  expect(root.querySelectorAll('a[href="https://www.dianping.com/"]')).toHaveLength(1)
  expect(root.querySelector('a[href*="baidu.com"]')).toBeNull()
  for (const text of ['零估算不代表免费', '本次规划未自动校验闭馆日期', '不会自动搜索', '搜索词：', '验证码']) {
    expect(document.body.textContent).not.toContain(text)
  }
  expect(document.body.querySelector('a[href="https://m.dianping.com/dphome"]')).toBeNull()
  expect(document.body.querySelector('.info-hint-panel')).toBeNull()
  expectSafeLinks(root)

  const ticketHint = await openHint('门票与开放信息说明')
  expect(ticketHint.textContent).toContain('非实时票价')
  expect(ticketHint.textContent).toContain('零估算不代表免费')
  expect(ticketHint.textContent).toContain('本次规划未自动校验闭馆日期')
  document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
  await nextTick()
  expect(document.body.querySelector('.info-hint-panel')).toBeNull()

  const guideHint = await openHint('攻略搜索说明')
  expect(guideHint.textContent).toContain('搜索词：北京 故宫博物院 游玩攻略')
  expect(guideHint.textContent).toContain('不会自动搜索')
  expect(guideHint.textContent).toContain('搜索结果未经过本项目审核')
  expect(guideHint.textContent).toContain('登录或验证码')
  expect(guideHint.querySelector('a[href="https://www.xiaohongshu.com/"]')).not.toBeNull()
  expect(guideHint.querySelector('a[href="https://m.dianping.com/dphome"]')).not.toBeNull()
  expectSafeLinks(guideHint)
})

it('keeps opening scope and reservation details visible, while source and verification dates are behind the ticket hint', async () => {
  mount({ ...unavailableVisit(), status: 'available', fetched_at: '2026-09-06T12:30:00+08:00',
    source_name: '高德地图 POI 2.0（参考信息，非景区官方确认）', source_url: 'https://uri.amap.com/marker?poiid=B1',
    opening: { today: 'DO_NOT_SHOW_TODAY', today_date: '2026-09-06', regular: '周二至周日开放', scope: 'reference_only' },
    official: { source_name: '故宫博物院官网', verified_at: '2026-09-01', reservation_note: '故宫博物院小程序预约',
      links: [{ purpose: 'reservation', label: '官方预约说明', url: 'https://www.dpm.org.cn/subject_booking/' }] },
  }, 60)
  expect(root.textContent).not.toContain('DO_NOT_SHOW_TODAY')
  expect(root.textContent).toContain('常规开放安排：周二至周日开放（高德参考）')
  expect(root.textContent).toContain('故宫博物院小程序预约')
  expect(root.textContent).toContain('官方预约说明')
  expect(root.textContent).toContain('在高德查看地点')
  for (const text of ['查询时间：', '人工核验日期：', '上游更新时间：', '高德地图 POI 2.0']) {
    expect(document.body.textContent).not.toContain(text)
  }
  expectSafeLinks(root)
  const hint = await openHint('门票与开放信息说明')
  expect(hint.textContent).toContain('高德地图 POI 2.0（参考信息，非景区官方确认）')
  expect(hint.textContent).toContain('查询时间：2026/09/06 12:30:00（北京时间）')
  expect(hint.textContent).toContain('官方入口来源：故宫博物院官网')
  expect(hint.textContent).toContain('人工核验日期：2026-09-01（非实时核验）')
  expect(hint.textContent).toContain('上游更新时间：未提供')
  expect(document.body.textContent).not.toContain('DO_NOT_SHOW_TODAY')
})

it('shows the precise date and reference label for same-day hours and hides them after changing the visit date', async () => {
  const props = mount({ ...unavailableVisit(), status: 'available',
    opening: { today: '08:30—17:00', today_date: '2026-09-07', regular: null, scope: 'reference_only' },
  })
  expect(root.textContent).toContain('今日开放时间（2026-09-07）：08:30—17:00（高德参考）')
  props.visitDate = '2026-09-08'
  await nextTick()
  expect(root.textContent).not.toContain('08:30—17:00')
})

it.each([
  ['no_data', '暂无开放时间参考'],
  ['unmatched', '地点未匹配'],
  ['permission_denied', '开放时间暂不可获取（接口权限不可用）'],
  ['timeout', '开放时间查询超时，可稍后重试'],
  ['unavailable', '开放时间暂不可获取'],
] as const)('keeps the %s state visible without opening a hint', (status, message) => {
  mount({ ...unavailableVisit(), status })
  expect(root.querySelector('[role="status"]')?.textContent).toBe(message)
  expect(root.textContent).toContain('暂无已核验官方入口')
  expect(root.querySelector('.guide-primary a')).not.toBeNull()
})

it('preserves loading and save-first states', async () => {
  const props = mount()
  expect(root.textContent).toContain('正在查询开放时间…')
  props.editing = true
  await nextTick()
  expect(root.textContent).toContain('保存后查询景点开放信息')
  expect(root.textContent).not.toContain('正在查询开放时间…')
})

it('continues rejecting unsafe source and official links', async () => {
  mount({ ...unavailableVisit(), fetched_at: 'not-a-date', source_url: 'javascript:alert(1)',
    official: { source_name: '官方来源', verified_at: '2026-09-01', reservation_note: '查看官方要求', links: [
      { purpose: 'reservation', label: '不安全入口', url: 'javascript:alert(1)' },
      { purpose: 'price', label: '含凭据入口', url: 'https://user:password@www.dpm.org.cn/' },
    ] },
  })
  expect(root.textContent).not.toContain('不安全入口')
  expect(root.textContent).not.toContain('含凭据入口')
  expect(root.textContent).not.toContain('在高德查看地点')
  const hint = await openHint('门票与开放信息说明')
  expect(hint.textContent).toContain('查询时间：未知')
  expect(document.body.querySelector('a[href^="javascript:"]')).toBeNull()
  expectSafeLinks(document.body)
})

it('updates the search and copies the current keyword without opening a hint', async () => {
  const writeText = vi.fn().mockResolvedValue(undefined)
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } })
  const props = mount(unavailableVisit())
  props.name = '天坛公园'
  await nextTick()
  copyButton().click()
  await vi.waitFor(() => expect(writeText).toHaveBeenCalledWith('北京 天坛公园 游玩攻略'))
  await vi.waitFor(() => expect(root.textContent).toContain('搜索词已复制'))
  expect(new URL(root.querySelector<HTMLAnchorElement>('.guide-primary a')!.href).searchParams.get('keyword')).toBe('北京 天坛公园 游玩攻略')
  expect(root.textContent).not.toContain('搜索词：')
  expect(document.body.querySelector('.info-hint-panel')).toBeNull()
})

it('keeps a selectable keyword visible after clipboard failure and clears stale feedback when the name changes', async () => {
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: undefined })
  const props = mount(unavailableVisit())
  copyButton().click()
  await nextTick()
  expect(root.textContent).toContain('复制失败，请选中下方搜索词手动复制')
  expect(root.querySelector('.guide-section > .search-keyword')?.textContent).toBe('搜索词：北京 故宫博物院 游玩攻略')
  expect(document.body.querySelector('.info-hint-panel')).toBeNull()
  props.name = '天坛公园'
  await nextTick()
  expect(root.textContent).not.toContain('复制失败')
  expect(root.textContent).not.toContain('故宫博物院')
})
