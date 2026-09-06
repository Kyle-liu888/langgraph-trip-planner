// @vitest-environment jsdom
import { afterEach, expect, it, vi } from 'vitest'
import { createApp, h, nextTick, reactive, type App } from 'vue'
import AttractionVisitInfo from './AttractionVisitInfo.vue'
import { unavailableVisit, type VisitInfo } from '@/services/visitInfo'
let app: App | undefined
let root: HTMLDivElement
function mount(info?: VisitInfo, ticketPrice = 0) {
  const props = reactive({ city: '北京', name: '故宫博物院', visitDate: '2026-09-07', ticketPrice, info })
  root = document.createElement('div')
  document.body.append(root)
  app = createApp({ render: () => h(AttractionVisitInfo, props) })
  app.mount(root)
  return props
}
afterEach(() => { app?.unmount(); root?.remove(); vi.restoreAllMocks() })

it('labels zero as a budget estimate and keeps guides during failure', () => {
  mount(unavailableVisit())
  expect(root.textContent).toContain('门票预算估算：¥0（仅预算参考）')
  expect(root.textContent).not.toContain('已确认免费')
  expect(root.textContent).toContain('暂无已核验官方入口')
  expect(root.textContent).toContain('大众点评官网')
  expect(root.textContent).toContain('不会自动搜索')
  expect(root.textContent).not.toContain('站外搜索')
  expect(root.querySelectorAll('a[href="https://www.dianping.com/"]')).toHaveLength(1)
  expect(root.querySelectorAll('a[href="https://m.dianping.com/dphome"]')).toHaveLength(1)
  expect(root.querySelector('a[href*="baidu.com"]')).toBeNull()
  expect(root.textContent).toContain('本次规划未自动校验闭馆日期')
  for (const link of root.querySelectorAll('a')) {
    expect(link.target).toBe('_blank')
    expect(link.rel).toBe('noopener noreferrer')
    expect(new URL(link.href).protocol).toMatch(/^https?:$/)
  }
})
it('separates source query and manual verification dates; never shows today for a future visit', () => {
  mount({ ...unavailableVisit(), status: 'available', fetched_at: '2026-09-06T12:30:00+08:00',
    source_name: '高德地图 POI 2.0（参考信息，非景区官方确认）', source_url: 'javascript:alert(1)',
    opening: { today: 'DO_NOT_SHOW_TODAY', today_date: '2026-09-06', regular: '周二至周日开放', scope: 'reference_only' },
    official: { source_name: '故宫博物院官网', verified_at: '2026-09-01', reservation_note: '故宫博物院小程序预约',
      links: [{ purpose: 'reservation', label: '官方预约说明', url: 'https://www.dpm.org.cn/subject_booking/' }] },
  }, 60)
  expect(root.textContent).not.toContain('DO_NOT_SHOW_TODAY')
  expect(root.textContent).toContain('常规开放安排：周二至周日开放')
  expect(root.textContent).toContain('查询时间：')
  expect(root.textContent).toContain('人工核验日期：2026-09-01')
  expect(root.textContent).toContain('上游更新时间：未提供')
  expect(root.querySelector('a[href^="javascript:"]')).toBeNull()
})
it('updates guides on edited names and can copy the keyword', async () => {
  const writeText = vi.fn().mockResolvedValue(undefined)
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } })
  const props = mount(unavailableVisit())
  props.name = '天坛公园'
  await nextTick()
  root.querySelector('button')!.click()
  await vi.waitFor(() => expect(writeText).toHaveBeenCalledWith('北京 天坛公园 游玩攻略'))
  await vi.waitFor(() => expect(root.textContent).toContain('搜索词已复制'))
  expect(root.querySelector('a')!.href).toContain(encodeURIComponent('天坛公园'))
})
it('provides manual copying fallback if the clipboard is unavailable', async () => {
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: undefined })
  mount(unavailableVisit())
  root.querySelector('button')!.click()
  await nextTick()
  expect(root.textContent).toContain('复制失败')
  expect(root.textContent).toContain('搜索词：北京 故宫博物院 游玩攻略')
})
