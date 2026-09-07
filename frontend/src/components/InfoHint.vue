<template>
  <span class="info-hint" data-html2canvas-ignore="true">
    <button ref="trigger" type="button" class="info-hint-trigger" :aria-label="label" :title="label"
      aria-haspopup="dialog" :aria-expanded="open" :aria-controls="open ? panelId : undefined" @click="toggle">
      <span aria-hidden="true">?</span>
    </button>
    <Teleport to="body">
      <div v-if="open" :id="panelId" ref="panel" class="info-hint-panel" role="dialog" tabindex="-1"
        :aria-labelledby="`${panelId}-title`" :style="position">
        <header class="info-hint-header">
          <h5 :id="`${panelId}-title`">{{ label }}</h5>
          <button type="button" class="info-hint-close" aria-label="关闭说明" @click="close(true)">×</button>
        </header>
        <div class="info-hint-content"><slot /></div>
      </div>
    </Teleport>
  </span>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, useId, watch } from 'vue'

defineProps<{ label: string }>()
const panelId = `info-hint-${useId()}`
const open = ref(false)
const trigger = ref<HTMLButtonElement>()
const panel = ref<HTMLDivElement>()
const position = ref({ left: '12px', top: '12px' })
let resizeObserver: ResizeObserver | undefined

function updatePosition() {
  if (!trigger.value || !panel.value) return
  const anchor = trigger.value.getBoundingClientRect()
  const { width, height } = panel.value.getBoundingClientRect()
  const margin = 12
  const viewportWidth = document.documentElement.clientWidth || window.innerWidth
  const below = anchor.bottom + 8
  const top = below + height <= window.innerHeight - margin ? below : anchor.top - height - 8
  position.value = {
    left: `${Math.max(margin, Math.min(anchor.right - width, viewportWidth - width - margin))}px`,
    top: `${Math.max(margin, Math.min(top, window.innerHeight - height - margin))}px`,
  }
}

function close(restoreFocus = false) {
  open.value = false
  if (restoreFocus) trigger.value?.focus({ preventScroll: true })
}
function toggle() { open.value ? close(true) : open.value = true }
function outside(event: Event) {
  if (event.target instanceof Node && !panel.value?.contains(event.target) && !trigger.value?.contains(event.target)) close()
}
function onKey(event: KeyboardEvent) {
  if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close(true) }
}
function removeListeners() {
  resizeObserver?.disconnect(); resizeObserver = undefined
  document.removeEventListener('pointerdown', outside, true)
  document.removeEventListener('click', outside, true)
  document.removeEventListener('focusin', outside)
  document.removeEventListener('keydown', onKey, true)
  window.removeEventListener('resize', updatePosition)
  window.removeEventListener('scroll', updatePosition, true)
}
watch(open, async value => {
  removeListeners()
  if (!value) return
  await nextTick()
  if (!open.value) return
  updatePosition()
  document.addEventListener('pointerdown', outside, true)
  document.addEventListener('click', outside, true)
  document.addEventListener('focusin', outside)
  document.addEventListener('keydown', onKey, true)
  window.addEventListener('resize', updatePosition)
  window.addEventListener('scroll', updatePosition, true)
  if (typeof ResizeObserver !== 'undefined' && panel.value) {
    resizeObserver = new ResizeObserver(updatePosition)
    resizeObserver.observe(panel.value)
  }
  panel.value?.focus({ preventScroll: true })
})
onBeforeUnmount(() => { open.value = false; removeListeners() })
</script>

<style scoped>
.info-hint { display: inline-flex; flex: 0 0 auto; vertical-align: middle; }
.info-hint-trigger, .info-hint-close { display: inline-grid; place-items: center; width: 36px; height: 36px; padding: 0; border: 0; background: transparent; color: var(--color-muted, #657873); font: inherit; cursor: pointer; border-radius: 6px; }
.info-hint-trigger span { display: grid; place-items: center; width: 18px; height: 18px; border: 1px solid currentColor; border-radius: 50%; font-size: 12px; font-weight: 650; line-height: 1; }
.info-hint-trigger:hover, .info-hint-trigger[aria-expanded="true"], .info-hint-close:hover { color: var(--color-primary, #176b5b); background: var(--color-paper, #f7f9f6); }
.info-hint-trigger:focus-visible, .info-hint-close:focus-visible { outline: 2px solid var(--color-primary, #176b5b); outline-offset: 2px; }
.info-hint-panel { position: fixed; z-index: 1100; box-sizing: border-box; width: min(360px, calc(100% - 24px)); max-height: calc(100dvh - 24px); overflow-y: auto; overscroll-behavior: contain; padding: 12px 16px 16px; border: 1px solid var(--color-line, #dce5df); border-radius: 9px; background: var(--color-surface, #fff); color: var(--color-ink, #203c38); box-shadow: 0 8px 28px rgba(32, 60, 56, .16); font-family: inherit; font-size: 13px; font-weight: 400; line-height: 1.8; text-align: left; overflow-wrap: anywhere; }
.info-hint-panel:focus-visible { outline: 2px solid var(--color-primary, #176b5b); outline-offset: 2px; }
.info-hint-header { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 8px; }
.info-hint-header h5 { margin: 0; font: inherit; font-size: 14px; font-weight: 650; }
.info-hint-close { flex: 0 0 auto; font-size: 22px; margin-right: -8px; }
.info-hint-content :deep(p) { margin: 8px 0; }
.info-hint-content :deep(p:last-child) { margin-bottom: 0; }
.info-hint-content :deep(h5), .info-hint-content :deep(h6) { margin: 12px 0 4px; font: inherit; font-weight: 650; }
.info-hint-content :deep(a) { color: var(--color-primary, #176b5b); text-underline-offset: 3px; }
.info-hint-content :deep(a:focus-visible) { outline: 2px solid var(--color-primary, #176b5b); outline-offset: 2px; }
@media (pointer: coarse) { .info-hint-trigger, .info-hint-close { width: 44px; height: 44px; } }
@media print { .info-hint, .info-hint-panel { display: none; } }
</style>
