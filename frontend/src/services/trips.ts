import api from './api'
import type { TripFormData, TripPlan } from '@/types'

export type TripStatus = 'queued' | 'running' | 'completed' | 'fallback' | 'failed' | 'interrupted'
export interface TripRecord {
  id: string; title: string; status: TripStatus; current_node: string | null
  message: string; error_code: string | null; run_id: string; revision: number
  resume_count: number; created_at: string; updated_at: string
  request: TripFormData; plan: TripPlan | null; metadata: Record<string, unknown>
}
export interface ProgressEvent {
  type: string; sequence: number; timestamp: string; run_id: string
  node?: string; label?: string; attempt?: number; elapsed_ms?: number
  error_type?: string; strategy?: string; model?: string; status?: TripStatus
}
export const active = (trip: TripRecord) => ['queued', 'running'].includes(trip.status)
export const statusLabels: Record<TripStatus, string> = {
  queued: '排队中', running: '规划中', completed: '已完成', fallback: '兜底结果', failed: '失败', interrupted: '已中断'
}
export const nodeLabels: Record<string, string> = {
  collect_context: '获取景点、餐饮和天气', build_prompt: '整理规划条件',
  generate_candidate: '模型生成候选行程', validate_candidate: '校验候选行程',
  select_best_candidate: '选择最佳行程', create_fallback: '生成兜底行程'
}
export const getTrip = async (id: string) => (await api.get<TripRecord>(`/api/trips/${id}`)).data
export const createTrip = async (body: TripFormData, key: string) =>
  (await api.post<TripRecord>('/api/trips', body, { headers: { 'X-Idempotency-Key': key } })).data
export const resumeTrip = async (id: string) => (await api.post<TripRecord>(`/api/trips/${id}/resume`)).data
export const saveTripPlan = async (id: string, plan: TripPlan, revision: number) =>
  (await api.put<TripRecord>(`/api/trips/${id}/plan`, { plan, revision })).data
