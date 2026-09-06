// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, reactive, type App } from 'vue'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'
import Antd from 'ant-design-vue'
import AppShell from './App.vue'

const fixture = vi.hoisted(() => ({
  auth: undefined as any,
  trips: { items: [], loading: false, error: '', cursor: null, reset: vi.fn(), load: vi.fn() }
}))
vi.mock('@/stores/auth', () => ({ useAuth: () => fixture.auth }))
vi.mock('@/stores/trips', () => ({ useTrips: () => fixture.trips }))

describe('mobile history drawer lifecycle', () => {
  let app: App
  let root: HTMLDivElement
  let router: Router

  beforeEach(async () => {
    vi.clearAllMocks()
    vi.stubGlobal('matchMedia', vi.fn(() => ({
      matches: false, addListener: vi.fn(), removeListener: vi.fn()
    })))
    const getStyle = window.getComputedStyle.bind(window)
    vi.spyOn(window, 'getComputedStyle').mockImplementation(element => getStyle(element))
    fixture.auth = reactive({
      user: { id: 'test-user', email: 'traveler@example.test' } as { id: string; email: string } | null,
      async signOut() {
        fixture.auth.user = null
        // The sidebar can unmount before its awaited logout callback emits navigate.
        await nextTick()
      }
    })
    fixture.trips.load.mockResolvedValue(undefined)
    const page = (text: string) => defineComponent({ setup: () => () => h('h1', text) })
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/trips/:id', component: page('我的行程') },
        { path: '/login', component: page('登录表单') }
      ]
    })
    await router.push('/trips/example')
    await router.isReady()
    root = document.createElement('div')
    document.body.append(root)
    app = createApp(AppShell).use(router).use(Antd)
    app.mount(root)
    await nextTick()
  })

  afterEach(() => {
    app.unmount()
    root.remove()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  async function openDrawer() {
    root.querySelector<HTMLButtonElement>('[aria-label="打开历史行程"]')!.click()
    await vi.waitFor(() => expect(document.querySelector('.ant-drawer-open')).not.toBeNull())
  }

  it('closes the real drawer when logout unmounts its sidebar before navigate is emitted', async () => {
    await openDrawer()
    document.querySelector<HTMLButtonElement>('.ant-drawer .logout')!.click()
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/login'))
    expect(fixture.auth.user).toBeNull()
    expect(root.textContent).toContain('登录表单')
    expect(document.querySelector('.ant-drawer')).toBeNull()
  })

  it('closes on session expiry without requiring a sidebar navigation event', async () => {
    await openDrawer()
    fixture.auth.user = null
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/login'))
    expect(document.querySelector('.ant-drawer')).toBeNull()
  })

  it('closes when navigation happens outside the drawer', async () => {
    await openDrawer()
    await router.push('/trips/another')
    await vi.waitFor(() => expect(document.querySelector('.ant-drawer-open')).toBeNull())
    expect(fixture.auth.user?.id).toBe('test-user')
  })

  it('resets the drawer when switching accounts on the same route', async () => {
    await openDrawer()
    fixture.auth.user = { id: 'other-user', email: 'other@example.test' }
    await vi.waitFor(() => expect(document.querySelector('.ant-drawer-open')).toBeNull())
    expect(router.currentRoute.value.path).toBe('/trips/example')
    expect(fixture.trips.load).toHaveBeenCalledTimes(2)
  })
})
