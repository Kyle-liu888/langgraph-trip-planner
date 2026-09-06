import { beforeEach, expect, it, vi } from 'vitest'
import api from './api'
import { loadPlacePhotos, photoKey, photoLabel } from './photos'
import type { Attraction } from '@/types'

vi.mock('./api', () => ({ default: { get: vi.fn() } }))
const place: Attraction = { name: '翠湖公园', poi_id: 'B123', address: '', location: { longitude: 102.7, latitude: 25.05 }, visit_duration: 60, description: '' }
const available = { photo_url: 'https://example.com/park.jpg', source: 'amap', status: 'available' }
beforeEach(() => vi.clearAllMocks())

it('passes identity, city and coordinates, deduplicates repeated stops', async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { data: available } })
  const update = vi.fn()
  await loadPlacePhotos('昆明', [place, place], update)
  expect(api.get).toHaveBeenCalledTimes(1)
  expect(api.get).toHaveBeenCalledWith('/api/poi/photo', expect.objectContaining({ params: { name: '翠湖公园', city: '昆明', poi_id: 'B123', longitude: 102.7, latitude: 25.05 } }))
  expect(update).toHaveBeenCalledWith(photoKey('昆明', place), available)
  expect(photoKey('昆明', place)).not.toBe(photoKey('北京', place))
})

it('handles API failure and ignores legacy/model image_url', async () => {
  vi.mocked(api.get).mockRejectedValue(new Error('offline'))
  const update = vi.fn()
  await loadPlacePhotos('昆明', [{ ...place, image_url: 'https://example.com/wrong.jpg' }], update)
  expect(update.mock.calls[0][1]).toEqual({ photo_url: null, source: null, status: 'unavailable' })
})

it('rejects unsafe image URLs and explains empty/mismatched images', async () => {
  vi.mocked(api.get).mockResolvedValue({ data: { data: { ...available, photo_url: 'javascript:alert(1)' } } })
  const update = vi.fn()
  await loadPlacePhotos('昆明', [place], update)
  expect(update.mock.calls[0][1].status).toBe('unavailable')
  expect(photoLabel({ photo_url: null, source: null, status: 'unmatched' })).toContain('未确认地点匹配')
  expect(photoLabel({ photo_url: null, source: null, status: 'no_photo' })).toBe('暂无景点图片')
})

it('limits concurrency and ignores results after disposal', async () => {
  let active = 0
  let peak = 0
  vi.mocked(api.get).mockImplementation(async () => {
    active++
    peak = Math.max(peak, active)
    await new Promise(resolve => setTimeout(resolve, 1))
    active--
    return { data: { data: available } }
  })
  const places = Array.from({ length: 8 }, (_, i) => ({ ...place, poi_id: `B${i}` }))
  await loadPlacePhotos('昆明', places, vi.fn())
  expect(peak).toBe(3)
  const update = vi.fn()
  let disposed = false
  const task = loadPlacePhotos('昆明', places, update, () => disposed)
  disposed = true
  await task
  expect(update).not.toHaveBeenCalled()
})
