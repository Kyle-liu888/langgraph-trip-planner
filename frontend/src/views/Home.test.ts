// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createApp, nextTick, type App } from 'vue'
import Antd from 'ant-design-vue'
import Home from './Home.vue'

const { get, createTrip, push } = vi.hoisted(() => ({ get: vi.fn(), createTrip: vi.fn(), push: vi.fn() }))
vi.mock('@/services/api', () => ({ default: { get } }))
vi.mock('@/services/trips', () => ({ createTrip }))
vi.mock('@/stores/trips', () => ({ useTrips: () => ({ upsert: vi.fn() }) }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))

describe('travel request presentation', () => {
  let app: App, root: HTMLDivElement
  beforeEach(async () => {
    vi.clearAllMocks()
    vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: false, addListener: vi.fn(), removeListener: vi.fn() })))
    const getStyle = window.getComputedStyle.bind(window)
    vi.spyOn(window, 'getComputedStyle').mockImplementation(el => getStyle(el))
    get.mockResolvedValue({ data: { used: 1, limit: 3, active_trip_id: null } })
    root = document.createElement('div')
    document.body.append(root)
    app = createApp(Home).use(Antd)
    app.component('router-link', { template: '<a><slot /></a>' })
    app.mount(root)
    await nextTick()
  })
  afterEach(() => { app.unmount(); root.remove(); vi.restoreAllMocks(); vi.unstubAllGlobals() })

  it('presents the form, usage and cost information without generating a trip', () => {
    expect(root.querySelector('h1')?.textContent).toContain('下一站')
    expect(root.querySelector('.banner-illustration')?.getAttribute('aria-hidden')).toBe('true')
    expect(root.textContent).toContain('今日已创建 1 / 3 次行程')
    expect(root.textContent).toContain('API 费用')
    expect(root.querySelectorAll('input[type=checkbox]')).toHaveLength(16)
    expect(createTrip).not.toHaveBeenCalled()
    expect(get).toHaveBeenCalledExactlyOnceWith('/api/me/usage')
  })

  it('keeps preference chips interactive and party summary reactive', async () => {
    const checkbox = root.querySelector<HTMLInputElement>('input[type=checkbox]')!
    checkbox.click()
    await nextTick()
    expect(checkbox.checked).toBe(true)
    expect(checkbox.closest('label')?.classList.contains('ant-checkbox-wrapper-checked')).toBe(true)
    const adults = root.querySelector<HTMLInputElement>('#form_item_adults')!
    adults.value = '2'
    adults.dispatchEvent(new Event('input', { bubbles: true }))
    await nextTick()
    expect(root.querySelector('.header-status')?.textContent).toContain('2 人')
    expect(createTrip).not.toHaveBeenCalled()
  })

  it('still validates missing destination and dates before submitting', async () => {
    root.querySelector<HTMLButtonElement>('button[type=submit]')!.click()
    await vi.waitFor(() => expect(root.textContent).toContain('请选择开始日期'))
    expect(root.textContent).toContain('请选择结束日期')
    expect(createTrip).not.toHaveBeenCalled()
    expect(push).not.toHaveBeenCalled()
  })
})
