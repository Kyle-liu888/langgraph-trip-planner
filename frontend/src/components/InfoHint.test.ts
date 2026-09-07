// @vitest-environment jsdom
import { afterEach, expect, it, vi } from 'vitest'
import { createApp, h, nextTick, type App } from 'vue'
import InfoHint from './InfoHint.vue'

let app: App | undefined
let root: HTMLDivElement
function mount() {
  root = document.createElement('div'); document.body.append(root)
  app = createApp({ render: () => h(InfoHint, { label: '来源说明' }, () => h('p', '查询时间及预算说明')) })
  app.mount(root)
  return root.querySelector<HTMLButtonElement>('button')!
}
async function open(button: HTMLButtonElement) { button.click(); await nextTick(); await nextTick() }
afterEach(() => { app?.unmount(); root?.remove(); vi.restoreAllMocks() })

it('keeps secondary content unmounted until explicitly opened with a named button', async () => {
  const button = mount()
  expect(button.type).toBe('button')
  expect(button.getAttribute('aria-label')).toBe('来源说明')
  expect(button.getAttribute('aria-expanded')).toBe('false')
  expect(document.body.textContent).not.toContain('查询时间及预算说明')
  expect(root.querySelector('[data-html2canvas-ignore]')).not.toBeNull()
  await open(button)
  const panel = document.querySelector<HTMLElement>('.info-hint-panel')!
  expect(button.getAttribute('aria-expanded')).toBe('true')
  expect(button.getAttribute('aria-controls')).toBe(panel.id)
  expect(panel.getAttribute('role')).toBe('dialog')
  expect(panel.textContent).toContain('查询时间及预算说明')
  expect(document.activeElement).toBe(panel)
})

it('closes on Escape and restores keyboard focus to the invoking button', async () => {
  const button = mount(); await open(button)
  document.activeElement!.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
  await nextTick()
  expect(document.querySelector('.info-hint-panel')).toBeNull()
  expect(document.activeElement).toBe(button)
  expect(button.getAttribute('aria-expanded')).toBe('false')
})

it('offers an explicit close action and allows toggling without a hover dependency', async () => {
  const button = mount(); await open(button)
  document.querySelector<HTMLButtonElement>('[aria-label="关闭说明"]')!.click(); await nextTick()
  expect(document.activeElement).toBe(button)
  expect(document.querySelector('.info-hint-panel')).toBeNull()
  await open(button); button.click(); await nextTick()
  expect(document.querySelector('.info-hint-panel')).toBeNull()
})

it('dismisses on outside pointer and focus without stealing focus from the next control', async () => {
  const button = mount(); await open(button)
  document.body.dispatchEvent(new Event('pointerdown', { bubbles: true })); await nextTick()
  expect(document.querySelector('.info-hint-panel')).toBeNull()
  await open(button)
  document.body.click(); await nextTick()
  expect(document.querySelector('.info-hint-panel')).toBeNull()
  await open(button)
  const other = document.createElement('button'); root.append(other); other.focus(); await nextTick()
  expect(document.querySelector('.info-hint-panel')).toBeNull()
  expect(document.activeElement).toBe(other)
})

it('clamps the panel to viewport edges and cleans up an open portal on unmount', async () => {
  const button = mount()
  vi.spyOn(button, 'getBoundingClientRect').mockReturnValue({ left: -50, right: -20, top: 9999, bottom: 10020 } as DOMRect)
  await open(button)
  const panel = document.querySelector<HTMLElement>('.info-hint-panel')!
  expect(panel.style.left).toBe('12px')
  expect(Number.parseFloat(panel.style.top)).toBeLessThanOrEqual(window.innerHeight - 12)
  app!.unmount(); app = undefined
  expect(document.querySelector('.info-hint-panel')).toBeNull()
  document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
})
