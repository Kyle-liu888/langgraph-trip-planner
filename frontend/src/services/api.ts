import axios from 'axios'
import { useAuth } from '@/stores/auth'

const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim()

export const API_BASE_URL = configuredApiBaseUrl
  ? configuredApiBaseUrl.replace(/\/$/, '')
  : ''

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
})
const requestOwners = new WeakMap<object, string | undefined>()

// 请求拦截器
apiClient.interceptors.request.use(
  async (config) => {
    const owner = useAuth().user?.id
    if (config.url?.startsWith('/api/') && !['get', 'head', 'options'].includes(config.method || 'get'))
      config.headers['X-CSRF-Token'] = useAuth().session?.csrf_token || ''
    if (owner !== useAuth().user?.id) throw new Error('账号已切换，请重新操作')
    requestOwners.set(config, owner)
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    if (requestOwners.get(response.config) !== useAuth().user?.id)
      throw new Error('账号已切换，已忽略原账号的请求结果')
    return response
  },
  (error) => {
    if (error.response?.status === 401 && requestOwners.get(error.config) === useAuth().user?.id)
      useAuth().expire()
    const detail = error.response?.data?.detail
    const requestId = error.response?.data?.request_id || error.response?.headers?.['x-request-id']
    const text = (typeof detail === 'object' ? detail.message : detail) ||
      (error.response?.status === 401 ? '登录已失效，请重新登录' : error.message) || '请求失败'
    // Never expose Axios config: it contains CSRF credentials.
    return Promise.reject(new Error(`${text}${requestId ? `（请求编号 ${requestId}）` : ''}`))
  }
)

/**
 * 生成旅行计划
 */
export async function healthCheck(): Promise<any> {
  try {
    const response = await apiClient.get('/health')
    return response.data
  } catch (error: any) {
    console.error('健康检查失败:', error)
    throw new Error(error.message || '健康检查失败')
  }
}

export default apiClient
