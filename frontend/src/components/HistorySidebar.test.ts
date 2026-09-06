// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'
import Antd from 'ant-design-vue'
import HistorySidebar from './HistorySidebar.vue'

const fixture = vi.hoisted(() => ({
  push: vi.fn(), load: vi.fn(), reset: vi.fn(), signOut: vi.fn(),
  user: { email: 'traveler@example.com' },
  items: [{ id: 'beijing', title: '北京三日慢游', status: 'completed', created_at: '2026-09-06T09:00:00Z' }]
}))
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'beijing' } }),
  useRouter: () => ({ push: fixture.push })
}))
vi.mock('@/stores/auth', () => ({ useAuth: () => ({ user: fixture.user, signOut: fixture.signOut }) }))
vi.mock('@/stores/trips', () => ({ useTrips: () => ({
  items: fixture.items, loading: false, error: '', cursor: null, load: fixture.load, reset: fixture.reset
}) }))

describe('history navigation', () => {
  let app: App
  let root: HTMLDivElement
  const navigate = vi.fn()
  beforeEach(() => {
    vi.clearAllMocks()
    fixture.signOut.mockResolvedValue(undefined)
    root = document.createElement('div')
    document.body.append(root)
    app = createApp(HistorySidebar, { onNavigate: navigate }).use(Antd)
    app.component('RouterLink', defineComponent({
      props: { to: String }, setup: (props, { slots }) => () => h('a', { href: props.to }, slots.default?.())
    }))
    app.mount(root)
  })
  afterEach(() => { app.unmount(); root.remove() })

  it('exposes the selected trip and retains its management control', () => {
    const selected = root.querySelector<HTMLAnchorElement>('[aria-current="page"]')!
    expect(selected.getAttribute('href')).toBe('/trips/beijing')
    expect(selected.textContent).toContain('北京三日慢游')
    expect(selected.textContent).toContain('已完成')
    expect(root.querySelector('[aria-label="管理行程：北京三日慢游"]')).not.toBeNull()
  })

  it('retains new-trip and refresh actions', () => {
    root.querySelector<HTMLButtonElement>('.new-trip')!.click()
    expect(fixture.push).toHaveBeenCalledWith('/trips/new')
    expect(navigate).toHaveBeenCalledOnce()
    root.querySelector<HTMLButtonElement>('[aria-label="刷新历史行程"]')!.click()
    expect(fixture.load).toHaveBeenCalledOnce()
  })

  it('keeps logout connected to session revocation and local history reset', async () => {
    root.querySelector<HTMLButtonElement>('.logout')!.click()
    await nextTick()
    expect(fixture.signOut).toHaveBeenCalledOnce()
    expect(fixture.reset).toHaveBeenCalledOnce()
    expect(fixture.push).toHaveBeenCalledWith('/login')
  })
})
