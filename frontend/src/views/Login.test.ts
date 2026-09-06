// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createApp, nextTick, type App } from 'vue'
import { createPinia } from 'pinia'
import Antd from 'ant-design-vue'
import Login from './Login.vue'
import { clearSession } from '@/services/auth'

const { navigate } = vi.hoisted(() => ({ navigate: vi.fn() }))
vi.mock('vue-router', () => ({
  useRouter: () => ({ replace: navigate }),
  useRoute: () => ({ query: { redirect: '/trips/new' } })
}))

describe('local login form submission', () => {
  let app: App
  let root: HTMLDivElement
  let failure: string | undefined
  const request = vi.fn()

  beforeEach(async () => {
    vi.clearAllMocks()
    clearSession()
    failure = undefined
    // Match browser APIs used by the real Ant Design form in this DOM test.
    vi.stubGlobal('matchMedia', vi.fn(() => ({
      matches: false, addListener: vi.fn(), removeListener: vi.fn()
    })))
    vi.stubGlobal('BroadcastChannel', undefined)
    const getStyle = window.getComputedStyle.bind(window)
    vi.spyOn(window, 'getComputedStyle').mockImplementation(element => getStyle(element))
    request.mockImplementation(async (_url: string, options: RequestInit) => {
      if (options.method === 'POST' && failure) {
        return new Response(JSON.stringify({ detail: { message: failure } }), { status: 401 })
      }
      return new Response(JSON.stringify({
        user: options.method === 'POST' ? { id: 'test-user', email: 'traveler@example.com', email_verified: false } : null,
        csrf_token: 'test-csrf'
      }), { status: 200 })
    })
    vi.stubGlobal('fetch', request)
    root = document.createElement('div')
    document.body.append(root)
    app = createApp(Login).use(createPinia()).use(Antd)
    app.mount(root)
    await vi.waitFor(() => expect(request).toHaveBeenCalled())
    await nextTick()
  })

  afterEach(() => {
    app.unmount()
    root.remove()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  async function fill(email = 'traveler@example.com', password = 'test-password') {
    for (const [selector, value] of [['input[type=email]', email], ['input[type=password]', password]]) {
      const input = root.querySelector<HTMLInputElement>(selector)!
      input.value = value
      input.dispatchEvent(new Event('input', { bubbles: true }))
    }
    await nextTick()
  }

  const posts = () => request.mock.calls.filter(([, options]) => options.method === 'POST')
  const clickSubmit = () => root.querySelector<HTMLButtonElement>('button[type=submit]')!.click()

  it('keeps clear form headings, password hints and decorative artwork outside the reading order', async () => {
    expect(root.querySelector('h1')?.textContent).toContain('写进行程里')
    expect(root.querySelector('section[aria-labelledby="form-title"] h2')?.textContent).toBe('欢迎回来')
    expect(root.querySelector('.login-sketch')?.getAttribute('aria-hidden')).toBe('true')
    expect(root.querySelector('input[type=password]')?.getAttribute('autocomplete')).toBe('current-password')
    Array.from(root.querySelectorAll('button')).find(button => button.textContent?.includes('还没有账号'))!.click()
    await nextTick()
    expect(root.querySelector('#form-title')?.textContent).toBe('创建你的账号')
    expect(root.querySelector('input[type=password]')?.getAttribute('autocomplete')).toBe('new-password')
    expect(root.textContent).toContain('邮箱仅作为登录标识，不发送验证邮件')
    expect(posts()).toHaveLength(0)
  })

  it.each([false, true])('submits valid credentials through the real form (register=%s)', async register => {
    if (register) {
      Array.from(root.querySelectorAll('button')).find(button => button.textContent?.includes('还没有账号'))!.click()
      await nextTick()
      expect(root.querySelector('button[type=submit]')!.textContent).toContain('注册账号')
    }
    await fill()
    clickSubmit()
    await vi.waitFor(() => expect(posts()).toHaveLength(1))
    const [url, options] = posts()[0]
    expect(url).toMatch(new RegExp(`/api/auth/${register ? 'register' : 'login'}$`))
    expect(options.credentials).toBe('include')
    expect(options.headers['X-CSRF-Token']).toBe('test-csrf')
    expect(JSON.parse(options.body)).toEqual({ email: 'traveler@example.com', password: 'test-password' })
    await vi.waitFor(() => expect(navigate).toHaveBeenCalledWith('/trips/new'))
  })

  it.each([
    ['', '', '请输入邮箱'],
    ['invalid-email', 'short', '请输入有效的邮箱地址']
  ])('shows validation feedback without sending invalid credentials (%s)', async (email, password, message) => {
    await fill(email, password)
    clickSubmit()
    await vi.waitFor(() => expect(root.textContent).toContain(message))
    expect(root.textContent).toContain('请检查邮箱和密码')
    expect(posts()).toHaveLength(0)
    expect(navigate).not.toHaveBeenCalled()
  })

  it('shows backend login errors and permits retry', async () => {
    failure = '邮箱或密码错误'
    await fill()
    clickSubmit()
    await vi.waitFor(() => expect(root.textContent).toContain('邮箱或密码错误'))
    expect(navigate).not.toHaveBeenCalled()
    failure = undefined
    clickSubmit()
    await vi.waitFor(() => expect(navigate).toHaveBeenCalledWith('/trips/new'))
    expect(posts()).toHaveLength(2)
  })
})
