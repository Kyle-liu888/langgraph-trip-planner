import api from './api'
import type { Attraction } from '@/types'

export interface PlacePhoto {
  photo_url: string | null
  source: 'amap' | null
  status: 'available' | 'no_photo' | 'unmatched' | 'unavailable'
}

export const photoKey = (city: string, place: Attraction): string =>
  JSON.stringify([city, place.poi_id || '', place.name, place.location?.longitude, place.location?.latitude])

export const photoLabel = (photo?: PlacePhoto): string => {
  if (!photo) return '正在加载景点图片…'
  if (photo.status === 'available') return '图片来源：高德地图'
  if (photo.status === 'unmatched') return '暂无景点图片（未确认地点匹配）'
  if (photo.status === 'unavailable') return '景点图片暂时无法加载'
  return '暂无景点图片'
}

export async function loadPlacePhotos(
  city: string,
  places: Attraction[],
  update: (key: string, photo: PlacePhoto) => void,
  stopped: () => boolean = () => false,
): Promise<void> {
  const queue = [...new Map(places.map(place => [photoKey(city, place), place])).entries()]
  let cursor = 0
  async function worker() {
    while (!stopped() && cursor < queue.length) {
      const [key, place] = queue[cursor++]
      let photo: PlacePhoto = { photo_url: null, source: null, status: 'unavailable' }
      try {
        const response = await api.get('/api/poi/photo', {
          params: { name: place.name, city, poi_id: place.poi_id || undefined,
            longitude: place.location?.longitude, latitude: place.location?.latitude },
          timeout: 15000,
        })
        const data = response.data.data as PlacePhoto | undefined
        if (data) photo = data
        // Never render legacy/model-supplied or non-HTTP image URLs.
        if (photo.status === 'available' && (photo.source !== 'amap' || !/^https?:\/\//i.test(photo.photo_url || ''))) {
          photo = { photo_url: null, source: null, status: 'unavailable' }
        }
      } catch { /* Optional imagery must not interrupt the itinerary or map. */ }
      if (!stopped()) update(key, photo)
    }
  }
  await Promise.all(Array.from({ length: Math.min(3, queue.length) }, worker))
}
