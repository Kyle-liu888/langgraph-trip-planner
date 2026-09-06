// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createApp, nextTick, type App } from 'vue'
import Antd from 'ant-design-vue'
import TripDetail from './TripDetail.vue'
import type { TripRecord } from '@/services/trips'

const mocks = vi.hoisted(() => ({ getTrip: vi.fn(), resumeTrip: vi.fn(), upsert: vi.fn(), stream: vi.fn() }))
vi.mock('vue-router', () => ({ useRoute: () => ({ params: { id: 'test-trip' } }) }))
vi.mock('@/stores/trips', () => ({ useTrips: () => ({ items: [], upsert: mocks.upsert }) }))
vi.mock('@/services/trips', async importOriginal => ({
  ...await importOriginal<typeof import('@/services/trips')>(), getTrip: mocks.getTrip, resumeTrip: mocks.resumeTrip,
}))
vi.mock('@/services/progress', async importOriginal => ({
  ...await importOriginal<typeof import('@/services/progress')>(), subscribeProgress: mocks.stream,
}))
vi.mock('./Result.vue', () => ({ default: { template: '<div data-testid="result">行程内容</div>' } }))

describe('trip progress presentation', () => {
  let app: App | undefined
  let root: HTMLDivElement
  const record = (status: TripRecord['status']) => ({
    id: 'test-trip', title: '北京三日游', status, current_node: 'generate_candidate',
    message: status === 'completed' ? '行程规划完成' : '规划超时，可稍后继续',
    run_id: 'run-1', plan: status === 'completed' ? {} : null,
  } as TripRecord)

  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: false, addListener: vi.fn(), removeListener: vi.fn() })))
    // Keep the mocked SSE open. Rendering must never start a real planning task.
    mocks.stream.mockImplementation(() => new Promise(() => {}))
    root = document.createElement('div'); document.body.append(root)
  })
  afterEach(() => { app?.unmount(); root.remove(); vi.unstubAllGlobals() })

  async function mount(status: TripRecord['status']) {
    mocks.getTrip.mockResolvedValue(record(status))
    app = createApp(TripDetail).use(Antd); app.mount(root)
    await vi.waitFor(() => expect(root.querySelector('h1')?.textContent).toBe('北京三日游'))
  }

  it('keeps a completed itinerary readable with execution details initially collapsed', async () => {
    await mount('completed')
    expect(root.querySelector('.progress-card')?.classList.contains('is-settled')).toBe(true)
    expect(root.querySelector('details')?.open).toBe(false)
    expect(root.querySelector('.current-node')?.textContent).toContain('行程已准备好')
    expect(root.querySelector('details')?.textContent).toContain('行程规划完成')
    expect(root.querySelector('summary')?.textContent).toContain('查看规划记录')
    expect(root.querySelector('.trace')?.textContent).toContain('运行编号：run-1')
    expect(root.querySelector('[data-testid=result]')).not.toBeNull()
    expect(mocks.resumeTrip).not.toHaveBeenCalled()
  })

  it('shows the actual active node without hiding it in execution details', async () => {
    await mount('running')
    expect(root.querySelector('.current-node')?.textContent).toContain('模型生成候选行程')
    expect(root.querySelector('details .current-node')).toBeNull()
    expect(root.querySelector('[data-testid=result]')).toBeNull()
    expect(mocks.resumeTrip).not.toHaveBeenCalled()
  })

  it('keeps checkpoint recovery and its API cost warning directly available', async () => {
    await mount('failed')
    expect(root.querySelector('.recovery')?.textContent).toContain('可能再次产生 API 费用')
    mocks.resumeTrip.mockResolvedValue(record('running'))
    root.querySelector<HTMLButtonElement>('.recovery button')!.click()
    await vi.waitFor(() => expect(mocks.resumeTrip).toHaveBeenCalledWith('test-trip'))
    await nextTick()
    expect(root.querySelector('.current-node')?.textContent).toContain('模型生成候选行程')
  })
})
