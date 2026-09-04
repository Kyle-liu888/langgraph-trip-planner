import { ref } from 'vue'
import { defineStore } from 'pinia'
import api from '@/services/api'
import type { TripRecord } from '@/services/trips'

export const useTrips = defineStore('trips', () => {
  const items = ref<TripRecord[]>([])
  const cursor = ref<string | null>(null)
  const loading = ref(false)
  const error = ref('')
  let generation = 0
  function reset() { generation++; items.value = []; cursor.value = null; error.value = ''; loading.value = false }
  async function load(more = false) {
    if (loading.value) return
    const version = generation
    loading.value = true; error.value = ''
    try {
      const { data } = await api.get('/api/trips', { params: { cursor: more ? cursor.value : undefined } })
      if (version !== generation) return
      items.value = more ? [...items.value, ...data.items] : data.items
      cursor.value = data.next_cursor
    } catch (e) { if (version === generation) error.value = (e as Error).message }
    finally { if (version === generation) loading.value = false }
  }
  function upsert(trip: TripRecord) {
    const index = items.value.findIndex(item => item.id === trip.id)
    if (index < 0) items.value.unshift(trip)
    else items.value[index] = trip
  }
  return { items, cursor, loading, error, reset, load, upsert }
})
